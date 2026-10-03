"""v6.1 representative routes: ordinary HTTP/worker/Fake + owned real PG."""
from dataclasses import replace

import psycopg
import pytest
from app.composition import build_container
from app.core.config import get_settings
from app.core.ids import new_id
from app.infrastructure.domain_pack import CURRENT_PACKS, load_pack
from app.main import create_app
from app.tools.seed_b3 import seed_reviewed_pack
from fastapi.testclient import TestClient

from tests.e2e.test_b2v_http_end_to_end import migrated_db as migrated_db  # noqa: F401

pytestmark = pytest.mark.postgres
GOALS = [
    ("零基础系统学 Agent，后面重点 RAG。", "agent.application", "stage.runtime_repo"),
    ("做 AI 资料工作台。", "ai.fullstack", "stage.repo"),
    ("学习云服务，能开发、部署和运维 API。", "cloud.services", "stage.repo"),
]

@pytest.fixture(scope="module")
def v61_db(migrated_db):
    with psycopg.connect(migrated_db.migrator_dsn) as conn:
        for filename in CURRENT_PACKS.values():
            data = load_pack(filename)
            seed_reviewed_pack(conn, data)
            seed_reviewed_pack(conn, data)
    return migrated_db

@pytest.mark.parametrize("goal,key,special", GOALS)
def test_representative_normal_generate_confirm_restart(v61_db, goal, key, special):
    settings = replace(get_settings(), database_url=v61_db.app_dsn, llm_provider="fake",
                       local_session_token="", planning_worker_admission_mode="trusted_server")
    container = build_container(settings)
    username = "v61" + new_id("usr")[-12:]
    pack = load_pack(CURRENT_PACKS[key])
    with TestClient(create_app(container)) as client:
        auth = client.post("/api/v1/auth/register", json={"username": username, "password": "Test-pass1!"})
        assert auth.status_code == 200, auth.text
        params = {"project_id": auth.json()["project_ids"][0]}
        headers = {"X-CSRF-Token": auth.json()["csrf_token"]}
        queued = client.post("/api/v1/plans/generate", params=params, headers=headers,
            json={"goal": goal, "goal_spec": {"target": goal, "starting_point": "初学者", "constraints": ["最低进入能力"]}})
        assert queued.status_code == 202, queued.text
        assert container.planning_worker.tick()
        run = client.get(queued.json()["status_url"]).json()
        assert (run["status"], run["next_action"]) == ("succeeded", "none"), run
        url = "/api/v1/plans/drafts/" + run["result_ref"]
        draft = client.get(url, params=params).json()
        assert draft["source_pack_key"] == key and draft["source_pack_version"] == pack["version"]
        assert [s["stable_key"] for s in draft["stages"]] == [s["stable_key"] for s in pack["stage_blueprints"]]
        stage = next(s for s in draft["stages"] if s["stable_key"] == special)
        case = next(r for r in draft["stage_resources"] if r["stage_id"] == stage["stage_id"] and r["role"] == "case_study")
        assert case["source_ref"] and case["source_version"] == 1 and case["media_type"] == "repo"
        assert case["ordered_sections"] == [] and case["verification_status"] == "legacy_index"
        ext = next(e for e in draft["extensions"] if e["stage_id"] == stage["stage_id"] and e["topic"].startswith("项目学习："))
        assert len(ext["links"]) == 1 and ext["concepts"] and ext["thinking_prompts"]
        assert all(r["source_ref"] for r in draft["stage_resources"])
        body = {"decision": "approve", "expected_version": 0, "draft_hash": draft["draft_hash"], "idempotency_key": "v61-confirm"}
        approved = client.post(url + "/decision", params=params, headers=headers, json=body)
        assert approved.status_code == 200, approved.text
        assert client.post(url + "/decision", params=params, headers=headers, json=body).json() == approved.json()
        plan = approved.json()["plan"]
        assert client.get("/api/v1/plans/current", params=params).json() == plan
        workspace = client.get("/api/v1/workspace", params=params).json()
        assert workspace["plan"]["extensions"] == plan["extensions"]
        assert workspace["completed_stages"] == 0
        assert client.post("/api/v1/auth/logout", headers=headers).status_code == 200
    fresh = build_container(settings)
    with TestClient(create_app(fresh)) as client:
        assert client.post("/api/v1/auth/login", json={"username": username, "password": "Test-pass1!"}).status_code == 200
        assert client.get("/api/v1/workspace", params=params).json()["plan"] == plan
        assert not fresh.planning_worker.tick() and not fresh.plan_service._llm.calls


def test_representative_three_direction_browser(v61_db):
    import os
    import socket
    import subprocess
    import threading
    import time
    from pathlib import Path

    import uvicorn

    if os.environ.get("STUDYPLAN_V61_BROWSER") != "1":
        pytest.skip("owned Chrome enabled explicitly")
    settings = replace(get_settings(), database_url=v61_db.app_dsn, llm_provider="fake", local_session_token="",
        planning_worker_admission_mode="trusted_server", allow_origins=("http://127.0.0.1:5178",))
    container = build_container(settings)
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    server = uvicorn.Server(uvicorn.Config(create_app(container), log_level="error"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
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
    worker = threading.Thread(target=work, daemon=True)
    thread.start()
    worker.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started and thread.is_alive() and time.monotonic() < deadline:
            time.sleep(0.05)
        assert server.started
        result = subprocess.run(["node", "frontend/tests/v61-directions-pg.browser.cjs"],
            cwd=Path(__file__).resolve().parents[3], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180,
            env=dict(os.environ, STUDYPLAN_V61_API=f"http://127.0.0.1:{sock.getsockname()[1]}"))
        assert result.returncode == 0, result.stdout + result.stderr
        assert not errors
    finally:
        stop.set()
        worker.join(10)
        server.should_exit = True
        thread.join(10)
        sock.close()
