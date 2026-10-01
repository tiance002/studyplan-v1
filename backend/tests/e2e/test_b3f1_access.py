"""Persistent browser auth and workspace acceptance, real isolated PostgreSQL."""

import json
from dataclasses import replace

import pytest
from app.composition import build_container
from app.core.config import get_settings
from app.main import create_app
from fastapi.testclient import TestClient

from tests.e2e.test_b2v_http_end_to_end import migrated_db as b2v_database_fixture
from tests.helpers.planning_worker import configure_test_worker


@pytest.fixture(scope="module")
def migrated_db(request):
    import psycopg
    from app.infrastructure.domain_pack import load_pack
    from app.tools.seed_b3 import seed_reviewed_pack

    for database in b2v_database_fixture.__wrapped__():
        with psycopg.connect(database.migrator_dsn) as conn:
            seed_reviewed_pack(conn, load_pack("agent-application-v2.json"))
        yield database


pytestmark = pytest.mark.postgres


def test_browser_registration_persistence_csrf_logout_and_isolation(migrated_db):
    settings = replace(
        get_settings(),
        database_url=migrated_db.app_dsn,
        llm_provider="fake",
        local_session_token="",
        session_cookie_secure=False,
        planning_worker_admission_mode="allowlist",  # Explicit legacy admission safety scenario.
    )

    def client():
        return TestClient(create_app(build_container(settings)))

    a, b = client(), client()
    # V2 guidance replaces the old 6–12 registration fixtures, retaining safety assertions.
    payload = {"username": "学习者甲", "password": "密码123456长口令用于学习"}
    registered = a.post("/api/v1/auth/register", json=payload)
    assert registered.status_code == 200, registered.text
    session = registered.json()
    assert "HttpOnly" in registered.headers["set-cookie"]
    assert session["username"] == "学习者甲"
    project = session["project_ids"][0]
    unserved = a.post(f"/api/v1/plans/generate?project_id={project}", json={"goal": "Agent开发"},
                      headers={"X-CSRF-Token": session["csrf_token"]})
    assert unserved.status_code == 403
    assert "Worker" in unserved.json()["message"]
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
        b.post("/api/v1/auth/register", json={"username": "学习者乙", "password": "long passphrase for learning"}).status_code
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
    response = client.post("/api/v1/auth/register", json={"username": "Ａlpha中文", "password": "long passphrase for learning"})
    assert response.status_code == 200
    assert (
        client.post("/api/v1/auth/register", json={"username": "alpha中文", "password": "long passphrase for learning"}).status_code
        == 409
    )
    assert (
        client.post("/api/v1/auth/login", json={"username": "ALPHA中文", "password": "long passphrase for learning"}).status_code
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
    for password in ["12345", "a" * 14, "a" * 129, "\ud800" + "a" * 15]:
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


def test_new_passphrase_code_points_and_existing_short_hash_login(migrated_db):
    """Only new registration policy changes; existing hashes keep working."""
    import psycopg
    from app.application.browser_auth import HASHER

    settings = replace(
        get_settings(), database_url=migrated_db.app_dsn, llm_provider="fake", local_session_token=""
    )
    client = TestClient(create_app(build_container(settings)))
    payload = {"username": "旧密码兼容", "password": "😀" * 128}
    registered = client.post("/api/v1/auth/register", json=payload)
    assert registered.status_code == 200, registered.text
    projects = registered.json()["project_ids"]
    assert client.post("/api/v1/auth/login", json=payload).status_code == 200
    # Test-only persisted legacy hash in this harness-owned isolated database.
    with psycopg.connect(migrated_db.migrator_dsn) as conn:
        conn.execute(
            "UPDATE auth_users SET password_hash=%s WHERE username_key=%s",
            (HASHER.hash("123456"), "旧密码兼容"),
        )
    legacy = {"username": "旧密码兼容", "password": "123456"}
    login = client.post("/api/v1/auth/login", json=legacy)
    assert login.status_code == 200, login.text
    assert login.json()["project_ids"] == projects
    rejected = client.post("/api/v1/auth/register", json={**legacy, "username": "新短密码"})
    assert rejected.status_code == 422
    assert "123456" not in rejected.text


def test_real_plan_workspace_edit_publish_refresh(migrated_db):
    settings = replace(
        get_settings(), database_url=migrated_db.app_dsn, llm_provider="fake", local_session_token=""
    )
    client = TestClient(create_app(build_container(settings)))
    s = client.post("/api/v1/auth/register", json={"username": "业务验收", "password": "long passphrase for learning"}).json()
    worker = configure_test_worker(client)
    headers = {"X-CSRF-Token": s["csrf_token"]}
    suffix = f"?project_id={s['project_ids'][0]}"
    response = client.post(
        "/api/v1/plans/generate" + suffix, json={"goal": "学习 Agent 开发"}, headers=headers
    )
    assert response.status_code == 202
    assert worker.tick()
    run = client.get("/api/v1/runs/" + response.json()["run_id"] + suffix).json()
    assert run["status"] == "succeeded" and run["next_action"] == "none", run
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


def test_healthy_long_run_is_not_interrupted_by_wall_clock(migrated_db):
    """A live lease may run for arbitrarily long; wall-clock time never interrupts.

    The old total-duration heuristic is gone. Only a lost lease / unknown paid
    dispatch moves a run to ``reconciliation_required`` — never "it took a while".
    """
    import psycopg

    settings = replace(get_settings(), database_url=migrated_db.app_dsn, llm_provider="fake", local_session_token="")
    client = TestClient(create_app(build_container(settings)))
    session = client.post("/api/v1/auth/register", json={"username": "中断恢复", "password": "long passphrase for learning"}).json()
    worker = configure_test_worker(client)
    suffix = f'?project_id={session["project_ids"][0]}'
    result = client.post("/api/v1/plans/generate" + suffix, json={"goal": "Agent 开发"}, headers={"X-CSRF-Token": session["csrf_token"]}).json()
    assert worker.tick()
    url = "/api/v1/runs/" + result["run_id"] + suffix
    assert client.get(url).json()["status"] == "succeeded"

    # Backdate the projection far beyond any former timeout while the run is
    # still "running": GET must report it as running, not reconcile it.
    with psycopg.connect(migrated_db.migrator_dsn) as conn:
        conn.execute(
            "UPDATE ai_runs SET status='running',next_action='wait',"
            "updated_at=now()-interval '30 days' WHERE run_id=%s",
            (result["run_id"],),
        )
    view = client.get(url).json()
    assert view["status"] == "running", view
    assert view["next_action"] == "wait"
    assert view["error"] is None
    repeated = client.get(url).json()
    assert repeated["status"] == view["status"] and repeated["version"] == view["version"]


def test_unknown_dispatch_run_requires_reconcile_without_retry(migrated_db):
    """An unknown paid dispatch is surfaced as reconcile, never as a retry."""
    import psycopg

    settings = replace(get_settings(), database_url=migrated_db.app_dsn, llm_provider="fake", local_session_token="")
    client = TestClient(create_app(build_container(settings)))
    session = client.post("/api/v1/auth/register", json={"username": "核对结果", "password": "long passphrase for learning"}).json()
    worker = configure_test_worker(client)
    suffix = f'?project_id={session["project_ids"][0]}'
    result = client.post("/api/v1/plans/generate" + suffix, json={"goal": "Agent 开发"}, headers={"X-CSRF-Token": session["csrf_token"]}).json()
    assert worker.tick()
    url = "/api/v1/runs/" + result["run_id"] + suffix
    with psycopg.connect(migrated_db.migrator_dsn) as conn:
        conn.execute(
            "UPDATE ai_runs SET status='reconciliation_required',next_action='reconcile',"
            "error_class='provider_dispatch_unknown' WHERE run_id=%s",
            (result["run_id"],),
        )
    view = client.get(url).json()
    assert view["status"] == "reconciliation_required", view
    assert view["next_action"] == "reconcile"
    assert view["error"]["code"] == "provider_dispatch_unknown"
    assert "重试" not in view["error"]["message"]
    repeated = client.get(url).json()
    assert repeated["status"] == view["status"] and repeated["version"] == view["version"]
