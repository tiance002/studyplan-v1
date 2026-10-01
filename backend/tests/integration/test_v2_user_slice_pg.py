"""New registered user → durable task → draft → publication → relogin, real PG.

The provider is explicitly Fake; this test does not prove cloud-model success.
"""
from dataclasses import replace

import psycopg
import pytest
from app.composition import build_container
from app.core.config import get_settings
from app.infrastructure.domain_pack import load_pack
from app.main import create_app
from app.tools.seed_b3 import seed_reviewed_pack
from fastapi.testclient import TestClient

from tests.e2e.test_b2v_http_end_to_end import migrated_db as migrated_db

pytestmark = pytest.mark.postgres


def test_new_user_requires_no_actor_whitelist_and_status_url_survives_relogin(migrated_db):
    with psycopg.connect(migrated_db.migrator_dsn) as conn:
        seed_reviewed_pack(conn, load_pack("agent-application-v3.json"))
    settings = replace(get_settings(), database_url=migrated_db.app_dsn, llm_provider="fake",
                       local_session_token="", planning_worker_admission_mode="trusted_server",
                       planning_worker_actor_ids=())
    container = build_container(settings)
    credentials = {"username": "新用户纵向切片", "password": "我的学习口令😀" * 3}
    with TestClient(create_app(container)) as client:
        registered = client.post("/api/v1/auth/register", json=credentials)
        assert registered.status_code == 200, registered.text
        session = registered.json()
        project = session["project_ids"][0]
        headers = {"X-CSRF-Token": session["csrf_token"]}
        generated = client.post("/api/v1/plans/generate", params={"project_id": project},
                                json={"goal": "学习 Agent 应用开发"}, headers=headers)
        assert generated.status_code == 202, generated.text
        handle = generated.json()
        queued = client.get(handle["status_url"])
        assert queued.status_code == 200, queued.text
        assert queued.json()["status"] == "queued"
        duplicate = client.post("/api/v1/plans/generate", params={"project_id": project},
                                json={"goal": "学习 Agent 应用开发"}, headers=headers)
        assert duplicate.status_code == 409, duplicate.text
        assert container.planning_worker.tick()
        run = client.get(handle["status_url"]).json()
        assert run["status"] == "succeeded" and run["next_action"] == "none", run
        draft_url = f"/api/v1/plans/drafts/{run['result_ref']}?project_id={project}"
        draft = client.get(draft_url).json()
        assert draft["status"] == "awaiting_approval" and draft["source_pack_version"] == 3
        stages = [dict(stage) for stage in draft["stages"]]
        stages[0]["title"] = "我保存的基础阶段"
        edited = client.post(draft_url.replace("?", "/decision?"), headers=headers, json={
            "decision": "edit", "expected_version": 0, "draft_hash": draft["draft_hash"],
            "edited_stages": stages,
        })
        assert edited.status_code == 200, edited.text
        draft = edited.json()["draft"]
        body = {"decision": "approve", "expected_version": 0, "draft_hash": draft["draft_hash"],
                "idempotency_key": "v2-user-confirm"}
        approved = client.post(draft_url.replace("?", "/decision?"), headers=headers, json=body)
        assert approved.status_code == 200, approved.text
        repeated = client.post(draft_url.replace("?", "/decision?"), headers=headers, json=body)
        assert repeated.status_code == 200 and repeated.json()["plan"] == approved.json()["plan"]
        assert client.get(handle["status_url"]).json()["result_ref"] == draft["draft_id"]
        plan = approved.json()["plan"]
        assert client.post("/api/v1/auth/logout", headers=headers).status_code == 200
    # A fresh application process and session read the identical persisted version.
    with TestClient(create_app(build_container(settings))) as restarted:
        login = restarted.post("/api/v1/auth/login", json=credentials)
        assert login.status_code == 200, login.text
        assert restarted.get(f"/api/v1/plans/current?project_id={project}").json() == plan
        assert restarted.get(draft_url).json()["stages"][0]["title"] == "我保存的基础阶段"
        assert restarted.get(handle["status_url"]).status_code == 200
    with TestClient(create_app(build_container(settings))) as outsider:
        registered = outsider.post("/api/v1/auth/register", json={
            "username": "另一个纵向用户", "password": "different long learning passphrase",
        })
        assert registered.status_code == 200, registered.text
        assert outsider.get(handle["status_url"]).status_code == 403
        assert outsider.get(draft_url).status_code == 403
