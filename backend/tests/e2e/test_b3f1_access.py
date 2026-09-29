"""Persistent browser auth and workspace acceptance, real isolated PostgreSQL."""

import json
from dataclasses import replace

import pytest
from app.composition import build_container
from app.core.config import get_settings
from app.main import create_app
from fastapi.testclient import TestClient

from tests.e2e.test_b2v_http_end_to_end import migrated_db as b2v_database_fixture


@pytest.fixture(scope="module")
def migrated_db(request):
    yield from b2v_database_fixture.__wrapped__()


pytestmark = pytest.mark.postgres


def test_browser_registration_persistence_csrf_logout_and_isolation(migrated_db):
    settings = replace(
        get_settings(),
        database_url=migrated_db.app_dsn,
        llm_provider="fake",
        local_session_token="",
        session_cookie_secure=False,
    )

    def client():
        return TestClient(create_app(build_container(settings)))

    a, b = client(), client()
    payload = {"username": "学习者甲", "password": "密码123456"}
    registered = a.post("/api/v1/auth/register", json=payload)
    assert registered.status_code == 200, registered.text
    session = registered.json()
    assert "HttpOnly" in registered.headers["set-cookie"]
    assert session["username"] == "学习者甲"
    project = session["project_ids"][0]
    assert (
        a.post(
            "/api/v1/auth/login", json=payload, headers={"Origin": "https://untrusted.invalid"}
        ).status_code
        == 403
    )
    assert a.post("/api/v1/session", json={"token": "arbitrary-token"}).status_code == 403
    assert (
        a.post(f"/api/v1/plans/generate?project_id={project}", json={"goal": "Agent开发"}).status_code == 403
    )
    restarted = client()
    restarted.cookies.update(a.cookies)
    assert restarted.get("/api/v1/session").json()["project_ids"] == [project]
    assert (
        b.post("/api/v1/auth/register", json={"username": "学习者乙", "password": "123456"}).status_code
        == 200
    )
    assert b.get(f"/api/v1/plans/current?project_id={project}").status_code == 403
    assert b.get(f"/api/v1/workspace?project_id={project}").status_code == 403
    assert b.post("/api/v1/auth/logout", headers={"X-CSRF-Token": session["csrf_token"]}).status_code == 403
    assert a.post("/api/v1/auth/logout", headers={"X-CSRF-Token": session["csrf_token"]}).status_code == 200
    assert restarted.get("/api/v1/session").status_code == 401
    assert a.post("/api/v1/auth/login", json=payload).status_code == 200
    assert a.post("/api/v1/auth/login", json={**payload, "password": "错误123456"}).status_code == 401


def test_auth_database_default_deny_expiry_and_normalized_username(migrated_db):
    import psycopg

    settings = replace(
        get_settings(), database_url=migrated_db.app_dsn, llm_provider="fake", local_session_token=""
    )
    client = TestClient(create_app(build_container(settings)))
    response = client.post("/api/v1/auth/register", json={"username": "Ａlpha中文", "password": "abcdef"})
    assert response.status_code == 200
    assert (
        client.post("/api/v1/auth/register", json={"username": "alpha中文", "password": "abcdef"}).status_code
        == 409
    )
    assert (
        client.post("/api/v1/auth/login", json={"username": "ALPHA中文", "password": "abcdef"}).status_code
        == 200
    )
    with psycopg.connect(migrated_db.app_dsn) as conn:
        for table in ("auth_users", "auth_sessions", "auth_throttle"):
            assert conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == 0
    with psycopg.connect(migrated_db.migrator_dsn) as conn:
        rows = conn.execute("SELECT password_hash FROM auth_users WHERE username_key='alpha中文'").fetchall()
        assert rows and rows[0][0].startswith("$argon2id$")
        conn.execute(
            "UPDATE auth_sessions SET expires_at=now()-interval '1 second' WHERE actor_id IN (SELECT actor_id FROM auth_users WHERE username_key='alpha中文')"
        )
    assert client.get("/api/v1/session").status_code == 401


def test_password_policy_secret_redaction_and_rate_limit(migrated_db):
    settings = replace(
        get_settings(), database_url=migrated_db.app_dsn, llm_provider="fake", local_session_token=""
    )
    client = TestClient(create_app(build_container(settings)))
    for password in ["12345", "1234567890123", "\ud800abcde"]:
        response = client.post(
            "/api/v1/auth/register",
            content=json.dumps({"username": "非法测试", "password": password}),
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code in (400, 422)
        assert password not in response.text
    for _ in range(12):
        response = client.post("/api/v1/auth/login", json={"username": "不存在", "password": "123456"})
    assert response.status_code == 429


def test_real_plan_workspace_edit_publish_refresh(migrated_db):
    settings = replace(
        get_settings(), database_url=migrated_db.app_dsn, llm_provider="fake", local_session_token=""
    )
    client = TestClient(create_app(build_container(settings)))
    s = client.post("/api/v1/auth/register", json={"username": "业务验收", "password": "123456"}).json()
    headers = {"X-CSRF-Token": s["csrf_token"]}
    suffix = f"?project_id={s['project_ids'][0]}"
    response = client.post(
        "/api/v1/plans/generate" + suffix, json={"goal": "学习 Agent 开发"}, headers=headers
    )
    assert response.status_code == 202
    run = client.get("/api/v1/runs/" + response.json()["run_id"] + suffix).json()
    assert run["status"] == "waiting_user", run
    draft_url = "/api/v1/plans/drafts/" + run["result_ref"]
    draft = client.get(draft_url + suffix).json()
    stages = draft["stages"]
    stages[0]["title"] = "调整后的基础准备"
    body = {
        "decision": "edit",
        "expected_version": 0,
        "draft_hash": draft["draft_hash"],
        "edited_stages": stages,
    }
    edited = client.post(draft_url + "/decision" + suffix, json=body, headers=headers)
    assert edited.status_code == 200, edited.text
    assert client.post(draft_url + "/decision" + suffix, json=body, headers=headers).status_code == 409
    body = {
        "decision": "approve",
        "expected_version": 0,
        "draft_hash": edited.json()["draft"]["draft_hash"],
        "idempotency_key": "stable-acceptance-key",
    }
    published = client.post(draft_url + "/decision" + suffix, json=body, headers=headers)
    assert published.status_code == 200, published.text
    assert (
        client.post(draft_url + "/decision" + suffix, json=body, headers=headers).json()["plan"]
        == published.json()["plan"]
    )
    fresh = TestClient(create_app(build_container(settings)))
    fresh.cookies.update(client.cookies)
    workspace = fresh.get("/api/v1/workspace" + suffix)
    assert workspace.status_code == 200, workspace.text
    data = workspace.json()
    assert data["plan"] == fresh.get("/api/v1/plans/current" + suffix).json()
    assert data["stages"][0]["stage"]["title"] == stages[0]["title"]
    assert data["total_units"] > 0 and data["completed_units"] == 0
    assert data["stages"][0]["nodes"]


def test_interrupted_running_becomes_reconciliation_without_retry(migrated_db):
    import psycopg

    settings = replace(get_settings(), database_url=migrated_db.app_dsn, llm_provider="fake", local_session_token="")
    client = TestClient(create_app(build_container(settings)))
    session = client.post("/api/v1/auth/register", json={"username": "中断恢复", "password": "123456"}).json()
    suffix = f'?project_id={session["project_ids"][0]}'
    result = client.post("/api/v1/plans/generate" + suffix, json={"goal": "Agent 开发"}, headers={"X-CSRF-Token": session["csrf_token"]}).json()
    url = "/api/v1/runs/" + result["run_id"] + suffix
    with psycopg.connect(migrated_db.migrator_dsn) as conn:
        conn.execute("UPDATE ai_runs SET updated_at=now()-interval '2 hours' WHERE run_id=%s", (result["run_id"],))
    assert client.get(url).json()["status"] == "waiting_user"
    with psycopg.connect(migrated_db.migrator_dsn) as conn:
        conn.execute("UPDATE ai_runs SET status='running',next_action='wait' WHERE run_id=%s", (result["run_id"],))
    view = client.get(url).json()
    assert view["status"] == "reconciliation_required", view
    assert view["next_action"] == "reconcile"
    assert view["error"]["code"] == "run_interrupted"
    assert "重试" not in view["error"]["message"]
    repeated = client.get(url).json()
    assert repeated["status"] == view["status"] and repeated["version"] == view["version"]
