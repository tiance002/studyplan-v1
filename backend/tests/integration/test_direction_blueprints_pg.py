"""Immutable Seed -> ordinary Cookie/CSRF -> Worker -> draft -> publication.

The database is owned and temporary. Model responses are explicitly Fake.
"""
from dataclasses import replace

import psycopg
import pytest
from app.composition import build_container
from app.core.config import get_settings
from app.core.ids import new_id
from app.domain.domain_packs.validation import seed_digest
from app.infrastructure.db.domain_pack_catalog import DomainPackUnavailableError, PgDomainPackCatalog
from app.infrastructure.domain_pack import DIRECTION_PACK_FILES, load_pack
from app.main import create_app
from app.tools.seed_b3 import seed_reviewed_pack
from fastapi.testclient import TestClient

from tests.e2e.test_b2v_http_end_to_end import migrated_db as migrated_db  # noqa: F401

pytestmark = pytest.mark.postgres


@pytest.fixture(scope="module")
def direction_db(migrated_db):
    packs = [load_pack(filename) for filename in DIRECTION_PACK_FILES.values()]
    with psycopg.connect(migrated_db.migrator_dsn) as conn:
        for pack in packs:
            seed_reviewed_pack(conn, pack)
            seed_reviewed_pack(conn, pack)
        assert conn.execute("SELECT count(*) FROM domain_packs WHERE pack_key = ANY(%s)",
                            (list(DIRECTION_PACK_FILES),)).fetchone()[0] == 3
    return migrated_db


@pytest.mark.parametrize("target,key,special", [
    ("Knowledge / RAG Agent", "agent.knowledge_rag", "stage.rag"),
    ("Python Coding Agent", "agent.coding", "stage.coding_workspace"),
    ("Workflow / Automation Agent", "agent.workflow_automation", "stage.workflow_effects"),
])
def test_normal_generation_edit_publish_restart_preserves_selected_direction(direction_db, target, key, special):
    db = direction_db
    settings = replace(get_settings(), database_url=db.app_dsn, llm_provider="fake",
                       local_session_token="", planning_worker_admission_mode="trusted_server")
    container = build_container(settings)
    username = "方向" + new_id("usr")[-10:]
    params = {}
    with TestClient(create_app(container)) as client:
        auth = client.post("/api/v1/auth/register", json={"username": username, "password": "Test-pass1!"})
        assert auth.status_code == 200, auth.text
        params = {"project_id": auth.json()["project_ids"][0]}
        headers = {"X-CSRF-Token": auth.json()["csrf_token"]}
        queued = client.post("/api/v1/plans/generate", params=params, headers=headers,
                             json={"goal": "Agent 学习（以具体目标为准）", "goal_spec": {
                                 "target": target, "starting_point": "有基础编程认知", "constraints": ["正文免费"]}})
        assert queued.status_code == 202, queued.text
        assert container.planning_worker.tick()
        run = client.get(queued.json()["status_url"]).json()
        assert run["status"] == "succeeded" and run["next_action"] == "none", run
        draft_url = "/api/v1/plans/drafts/" + run["result_ref"]
        response = client.get(draft_url, params=params)
        assert response.status_code == 200, response.text
        draft = response.json()
        pack = load_pack(DIRECTION_PACK_FILES[key])
        assert [s["stable_key"] for s in draft["stages"]] == [s["stable_key"] for s in pack["stage_blueprints"]]
        assert special in {s["stable_key"] for s in draft["stages"]}
        if key != "agent.knowledge_rag":
            assert "stage.rag" not in {s["stable_key"] for s in draft["stages"]}
        assert all(s["learning_guidance"] for s in draft["stages"])
        stages = draft["stages"]
        stages[0]["title"] = "我的 Python 必要基础"
        edited = client.post(draft_url + "/decision", params=params, headers=headers, json={
            "decision": "edit", "expected_version": 0, "draft_hash": draft["draft_hash"], "edited_stages": stages})
        assert edited.status_code == 200, edited.text
        updated = edited.json()["draft"]
        body = {"decision": "approve", "expected_version": 0, "draft_hash": updated["draft_hash"],
                "idempotency_key": "direction-confirm"}
        confirmed = client.post(draft_url + "/decision", params=params, headers=headers, json=body)
        assert confirmed.status_code == 200, confirmed.text
        assert client.post(draft_url + "/decision", params=params, headers=headers, json=body).json() == confirmed.json()
        plan = confirmed.json()["plan"]
        current = client.get("/api/v1/plans/current", params=params)
        assert current.status_code == 200, current.text
        assert current.json() == plan
        workspace = client.get("/api/v1/workspace", params=params)
        assert workspace.status_code == 200, workspace.text
        assert workspace.json()["total_stages"] == 10
        assert workspace.json()["completed_stages"] == 0
        assert all(s["completion"]["status"] == "incomplete" for s in workspace.json()["stages"])
        assert client.post("/api/v1/auth/logout", headers=headers).status_code == 200
    # Fresh services use immutable PG snapshots; no file fallback or repeated generation.
    fresh = build_container(settings)
    with TestClient(create_app(fresh)) as client:
        auth = client.post("/api/v1/auth/login", json={"username": username, "password": "Test-pass1!"})
        assert auth.status_code == 200, auth.text
        assert client.get("/api/v1/plans/current", params=params).json() == plan
        persisted = client.get("/api/v1/workspace", params=params).json()
        assert persisted["plan"]["goal_spec"]["target"] == target
        assert next(s for s in persisted["stages"] if s["stage"]["stable_key"] == special)["stage"]["learning_guidance"]
        assert not fresh.planning_worker.tick()
        assert not fresh.plan_service._llm.calls
    with psycopg.connect(db.migrator_dsn) as conn:
        snapshot, digest = conn.execute("SELECT published_payload,content_digest FROM domain_packs WHERE pack_key=%s AND version=1",
                                        (key,)).fetchone()
        assert snapshot == pack and digest == seed_digest(pack)
        saved = conn.execute("SELECT structure FROM plan_revisions WHERE plan_id=%s", (plan["plan_id"],)).fetchone()[0]
        assert saved["goal_spec"]["target"] == target


def test_missing_specific_seed_never_falls_back_to_generic(monkeypatch):
    from contextlib import nullcontext

    class EmptyCatalog:
        def execute(self, query, args):
            assert args == ("agent.coding",)
            return self

        def fetchone(self):
            return None

    monkeypatch.setattr(psycopg, "connect", lambda *args: nullcontext(EmptyCatalog()))
    with pytest.raises(DomainPackUnavailableError):
        PgDomainPackCatalog("postgresql://unused/unused").select("Coding Agent")


def test_three_direction_real_browser(direction_db):
    import os
    import socket
    import subprocess
    import threading
    import time
    from pathlib import Path

    import uvicorn

    if os.environ.get("STUDYPLAN_DIRECTION_BROWSER") != "1":
        pytest.skip("owned Chrome acceptance explicitly enabled separately")
    settings = replace(get_settings(), database_url=direction_db.app_dsn, llm_provider="fake",
                       local_session_token="", planning_worker_admission_mode="trusted_server",
                       allow_origins=("http://127.0.0.1:5178",))
    container = build_container(settings)
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    server = uvicorn.Server(uvicorn.Config(create_app(container), log_level="error"))
    server_thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    stop = threading.Event()
    errors = []

    def work():
        while not stop.is_set():
            try:
                container.planning_worker.tick()
            except Exception as exc:
                errors.append(type(exc).__name__)
                return
            stop.wait(0.1)

    worker_thread = threading.Thread(target=work, daemon=True)
    server_thread.start()
    worker_thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started and server_thread.is_alive() and time.monotonic() < deadline:
            time.sleep(0.05)
        assert server.started
        result = subprocess.run(["node", "frontend/tests/direction-blueprints-pg.browser.cjs"],
                                cwd=Path(__file__).resolve().parents[3],
                                env=dict(os.environ, STUDYPLAN_DIRECTION_API=f"http://127.0.0.1:{sock.getsockname()[1]}"),
                                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
        assert result.returncode == 0, result.stdout + result.stderr
        assert not errors
    finally:
        stop.set()
        worker_thread.join(10)
        server.should_exit = True
        server_thread.join(10)
        sock.close()
