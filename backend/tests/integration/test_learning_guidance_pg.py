"""Normal auth/HTTP/worker + real isolated PG; model is explicitly Fake."""
import os
import socket
import subprocess
import threading
import time
from dataclasses import replace
from pathlib import Path

import psycopg
import pytest
import uvicorn
from app.composition import build_container
from app.core.config import get_settings
from app.main import create_app
from app.tools.seed_b3 import seed_reviewed_pack
from fastapi.testclient import TestClient

from tests.e2e.test_b2v_http_end_to_end import migrated_db as migrated_db
from tests.unit.test_learning_guidance import guided_pack, repeated_guided_pack

pytestmark = pytest.mark.postgres


def test_worker_edit_publish_reload_and_relogin_preserve_guidance(migrated_db):
    db = migrated_db
    pack = guided_pack()
    pack["version"] = 4  # Isolated acceptance input, never imported into a product DB.
    with psycopg.connect(db.migrator_dsn) as conn:
        seed_reviewed_pack(conn, pack)
    settings = replace(get_settings(), database_url=db.app_dsn, llm_provider="fake",
                       allow_origins=("http://127.0.0.1:5178",),
                       local_session_token="", planning_worker_admission_mode="trusted_server")
    container = build_container(settings)
    with TestClient(create_app(container)) as client:
        registered = client.post("/api/v1/auth/register", json={"username": "指导验收", "password": "Test-pass1!"})
        assert registered.status_code == 200, registered.text
        project = registered.json()["project_ids"][0]
        params = {"project_id": project}
        headers = {"X-CSRF-Token": registered.json()["csrf_token"]}
        response = client.post("/api/v1/plans/generate", params=params, headers=headers,
                               json={"goal": "Agent 应用开发：深入 Tool Calling"})
        assert response.status_code == 202, response.text
        assert container.planning_worker.tick()
        result = client.get(response.json()["status_url"]).json()
        assert result["status"] == "succeeded" and result["next_action"] == "none"
        draft_id = result["result_ref"]
        url = f"/api/v1/plans/drafts/{draft_id}"
        loaded = client.get(url, params=params)
        assert loaded.status_code == 200, loaded.text
        draft = loaded.json()
        guide = next(s["learning_guidance"] for s in draft["stages"] if s["stable_key"] == "stage.tools")
        assert guide["practice_delta"]["validation"] == ["正常工具调用", "未知 Tool", "错误参数", "Tool 抛错"]
        assert guide["exposure_relation"] == "deepen"
        assert guide["source_slice"]["verification_status"] == "suggested"
        # An old client sends only the original stage fields. Its edit cannot erase guidance.
        stages = [{k: v for k, v in s.items() if k != "learning_guidance"} for s in draft["stages"]]
        stages[0]["title"] = "我的必要环境准备"
        edited = client.post(url + "/decision", params=params, headers=headers,
                             json={"decision": "edit", "expected_version": 0,
                                   "draft_hash": draft["draft_hash"], "edited_stages": stages})
        assert edited.status_code == 200, edited.text
        edited_draft = edited.json()["draft"]
        assert next(s["learning_guidance"] for s in edited_draft["stages"] if s["stable_key"] == "stage.tools") == guide
        assert edited_draft["draft_hash"] != draft["draft_hash"]
        approved = client.post(url + "/decision", params=params, headers=headers,
                               json={"decision": "approve", "expected_version": 0,
                                     "draft_hash": edited_draft["draft_hash"], "idempotency_key": "new-guide-acceptance"})
        assert approved.status_code == 200, approved.text
        plan = approved.json()["plan"]
        plan_id = plan["plan_id"]
        workspace = client.get("/api/v1/workspace", params=params)
        assert workspace.status_code == 200, workspace.text
        tools = next(s for s in workspace.json()["stages"] if s["stage"]["stable_key"] == "stage.tools")
        assert tools["stage"]["learning_guidance"] == guide
        assert tools["completion"]["status"] == "incomplete"
        assert "read_file" in tools["tasks"][0]["goal"] and "search_note" in tools["tasks"][0]["goal"]
        assert tools["tasks"][0]["acceptance"] == ["正常工具调用", "未知 Tool", "错误参数", "Tool 抛错"]
        assert client.post("/api/v1/auth/logout", headers=headers).status_code == 200
        assert client.get("/api/v1/workspace", params=params).status_code == 401
    # New container, new session: use PG version metadata, not the original Seed file.
    fresh = build_container(settings)
    with TestClient(create_app(fresh)) as client:
        login = client.post("/api/v1/auth/login", json={"username": "指导验收", "password": "Test-pass1!"})
        assert login.status_code == 200, login.text
        restored = client.get("/api/v1/workspace", params=params)
        assert restored.status_code == 200, restored.text
        assert restored.json()["plan"]["plan_id"] == plan_id
        assert next(s["stage"]["learning_guidance"] for s in restored.json()["stages"] if s["stage"]["stable_key"] == "stage.tools") == guide
        if os.environ.get("STUDYPLAN_GUIDANCE_BROWSER") == "1":
            sock = socket.socket()
            sock.bind(("127.0.0.1", 0))
            server = uvicorn.Server(uvicorn.Config(create_app(fresh), log_level="error"))
            thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
            thread.start()
            try:
                deadline = time.monotonic() + 10
                while not server.started and thread.is_alive() and time.monotonic() < deadline:
                    time.sleep(0.05)
                assert server.started
                root = Path(__file__).resolve().parents[3]
                env = dict(os.environ, STUDYPLAN_GUIDANCE_API=f"http://127.0.0.1:{sock.getsockname()[1]}")
                browser = subprocess.run(["node", "frontend/tests/learning-guidance-pg.browser.cjs"],
                                         cwd=root, env=env, capture_output=True, text=True,
                                         encoding="utf-8", errors="replace", timeout=90)
                assert browser.returncode == 0, browser.stdout + browser.stderr
            finally:
                server.should_exit = True
                thread.join(10)
                sock.close()
        other = client.post("/api/v1/auth/register", json={"username": "另一指导账号", "password": "Test-pass2!"})
        assert other.status_code == 200
        assert client.get("/api/v1/workspace", params=params).status_code == 403
    with psycopg.connect(db.migrator_dsn) as conn:
        saved = conn.execute("SELECT structure FROM plan_revisions WHERE plan_id=%s", (plan_id,)).fetchone()[0]
        assert next(s["learning_guidance"] for s in saved["stages"] if s["stable_key"] == "stage.tools") == guide


def test_repeated_module_keeps_one_node_and_independent_pg_exposures(migrated_db):
    from app.application.plan_service import DecisionCommand
    from app.domain.enums import DraftDecision, UnitProgress
    from app.domain.learning_exposures import ExposureCommand
    db = migrated_db
    pack = repeated_guided_pack()
    pack["version"] = 5
    with psycopg.connect(db.migrator_dsn) as conn:
        seed_reviewed_pack(conn, pack)
    settings = replace(get_settings(), database_url=db.app_dsn, llm_provider="fake",
                       local_session_token="", planning_worker_admission_mode="trusted_server")
    container = build_container(settings)
    token = container.browser_auth.register("复习验收", "Test-pass1!", "repeat-test")
    scope = container.browser_auth.resolve(token)
    project = scope.learning_project_scope[0]
    service = container.plan_service
    run_id = service.submit_generation(scope=scope, project_id=project, goal="Agent工具复习")
    assert container.planning_worker.tick()
    run = service.get_run(scope=scope, project_id=project, run_id=run_id).run
    assert run.status.value == "succeeded"
    draft = service.get_draft(scope=scope, project_id=project, draft_id=run.result_ref).draft
    plan = service.decide(scope=scope, project_id=project, draft_id=draft.draft_id,
        command=DecisionCommand(decision=DraftDecision.APPROVE, expected_version=0,
                                draft_hash=draft.content_hash, idempotency_key="repeat-publish")).plan
    tool_stage = next(s for s in plan.stages if s.stable_key == "stage.tools")
    review_stage = next(s for s in plan.stages if s.stable_key == "stage.tools.review")
    positions = container.exposure_service.list(scope, project, plan.plan_id)
    first = next(p for p in positions if p["stage_id"] == tool_stage.stage_id)
    second = next(p for p in positions if p["stage_id"] == review_stage.stage_id)
    assert first["exposure_id"] != second["exposure_id"]
    container.exposure_service.change(scope, ExposureCommand(project_id=project, plan_id=plan.plan_id,
        stage_id=first["stage_id"], unit_id=first["unit_id"], status=UnitProgress.COMPLETED,
        expected_version=0, idempotency_key="first-only"))
    positions = container.exposure_service.list(scope, project, plan.plan_id)
    assert next(p for p in positions if p["exposure_id"] == second["exposure_id"])["recorded"] is False
    with psycopg.connect(db.migrator_dsn) as conn:
        ids = conn.execute("SELECT node_id FROM knowledge_nodes WHERE project_id=%s AND stable_key='node.tools'", (project,)).fetchall()
        assert len(ids) == 1
        linked = conn.execute("SELECT unit_id FROM unit_node_links WHERE project_id=%s AND node_id=%s", (project, ids[0][0])).fetchall()
        assert {x[0] for x in linked} == {first["unit_id"], second["unit_id"]}
    with TestClient(create_app(build_container(settings))) as client:
        client.cookies.set(settings.session_cookie_name, token)
        workspace = client.get("/api/v1/workspace", params={"project_id": project})
        assert workspace.status_code == 200, workspace.text
        appearances = {s["stage"]["stable_key"]: s for s in workspace.json()["stages"]}
        assert appearances["stage.tools"]["stage"]["learning_guidance"]["exposure_relation"] == "deepen"
        assert appearances["stage.tools.review"]["stage"]["learning_guidance"]["exposure_relation"] == "review"
        assert appearances["stage.tools.review"]["completion"]["status"] == "incomplete"
