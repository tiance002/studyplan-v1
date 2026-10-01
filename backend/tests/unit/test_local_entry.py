"""Offline M1.1 tests: unittest runner, no pytest hooks or real DB/network.

Run: .venv/Scripts/python.exe -B -m unittest discover -s backend/tests/unit -p test_local_entry.py -v
"""
import os
import secrets
import unittest
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
from unittest.mock import patch

import httpx
import psycopg
from app.application.container import AppContainer
from app.application.model_settings import ModelSettingsService
from app.application.plan_service import PlanService
from app.application.sessions import InMemorySessionStore, SessionRecord
from app.core.config import get_settings, reset_settings_cache
from app.core.errors import ForbiddenError, UnauthenticatedError
from app.core.startup_guard import StartupSecurityError
from app.domain.enums import AiRunNextAction, AiRunStatus, OutlineSectionKind
from app.domain.planning.models import PlanDraft, PlanStage, PlanUnitLink
from app.domain.runs.models import RunRecord
from app.infrastructure.db.browser_auth import PgBrowserAuth
from app.main import create_app
from app.ports.model_settings import ModelSettingsView
from fastapi.testclient import TestClient

from tests.unit.test_plan_publication import FakePlanRepository


class FakeRuns:
    def __init__(self):
        self.row = RunRecord("run-fixture", "actor-original", "project-b", "plan_generate", "planning",
                             "b3f2-batch-v1", AiRunStatus.WAITING_USER, AiRunNextAction.REVIEW_DRAFT,
                             result_ref="draft-fixture")

    def get_run(self, *, project_id, run_id):
        return self.row if (project_id, run_id) == (self.row.project_id, self.row.run_id) else None

    def get_progress(self, **kwargs):
        return None

    def update_run(self, *, expected_version, **kwargs):
        assert expected_version == self.row.version
        fields = {k: v for k, v in kwargs.items() if k not in {"project_id", "run_id"}}
        fields["status"] = AiRunStatus(fields["status"])
        fields["next_action"] = AiRunNextAction(fields["next_action"])
        self.row = replace(self.row, version=self.row.version + 1, **fields)


class ScopedFakePlans(FakePlanRepository):
    def get_draft(self, *, project_id, draft_id):
        stored = self.drafts.get(draft_id)
        return deepcopy(stored) if stored and stored.project_id == project_id else None


class DenyProvider:
    def __init__(self):
        self.calls = 0

    def generate_structured(self, **kwargs):
        self.calls += 1
        raise AssertionError("Decision must not dispatch any provider")


class FakeModels:
    def get(self, actor):
        if actor != "actor-original":
            raise AssertionError("Wrong model owner")
        return ModelSettingsView(4, "https://api.deepseek.com", "existing-model", "openai", True)


class MemoryConnection:
    """SQL boundary double: ignores RLS so missing explicit owner filters leak data."""
    def __init__(self, users=None):
        self.users = users if users is not None else ["actor-original", "actor-other"]
        self.queries = []
        self.result = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params=()):
        self.queries.append((sql, params))
        if "FROM auth_users" in sql:
            users = [u for u in self.users if u == params[0]] if "WHERE actor_id=%s" in sql else self.users
            self.result = [{"actor_id": u} for u in users]
        elif "FROM learning_projects" in sql:
            rows = [("actor-original", "project-a"), ("actor-original", "project-b"), ("actor-other", "project-other")]
            self.result = [{"project_id": p} for a, p in rows if "owner_actor_id=%s" not in sql or a == params[0]]
        else:
            self.result = []
        return self

    def fetchall(self):
        return self.result


class FakeAuth(PgBrowserAuth):
    """Persistent fixture across containers; only external storage is replaced."""
    def __init__(self):
        super().__init__("postgresql://unused/unused", 1200)
        self.rows = {}
        self.projects = {"actor-original": ["project-a", "project-b"], "actor-other": ["project-other"]}
        self.issues = 0

    def connection(self):
        raise AssertionError("Fake fixture must not use a database")

    def local_binding(self, actor, project):
        projects = self.projects.get(actor, [])
        if project not in projects:
            raise ForbiddenError("本地绑定不可用")
        return projects

    def issue(self, actor, *, cleanup=True):
        self.issues += 1
        token = secrets.token_urlsafe(32)
        self.rows[token] = {"actor_id": actor, "session_id": f"session-{self.issues}",
                            "csrf_token": secrets.token_urlsafe(32), "username": "original",
                            "issued_at": datetime.now(timezone.utc)}
        return token

    def detail(self, token):
        if token not in self.rows:
            raise UnauthenticatedError()
        row = self.rows[token]
        return row, self.projects[row["actor_id"]]

    def logout(self, token):
        self.rows.pop(token, None)

    def login(self, username, password, peer):
        if (username, password) != ("fixture", "Pass123"):
            raise UnauthenticatedError()
        return self.issue("actor-original")


class LocalConfigTests(unittest.TestCase):
    def test_explicit_enable_flag_is_read_and_default_is_disabled(self):
        with patch.dict(os.environ, {"STUDYPLAN_LOCAL_ENTRY_ENABLED": "true"}, clear=True):
            reset_settings_cache()
            self.assertTrue(getattr(get_settings(), "local_entry_enabled", False))
        with patch.dict(os.environ, {}, clear=True):
            reset_settings_cache()
            self.assertFalse(getattr(get_settings(), "local_entry_enabled", True))
        reset_settings_cache()


class LocalEntryTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {"APP_ENV": "development", "LLM_PROVIDER": "fake", "STUDYPLAN_LOCAL_ENTRY_ENABLED": "true",
                                          "STUDYPLAN_REPOSITORY_BACKEND": "memory"}, clear=True)
        self.env.start()
        reset_settings_cache()
        self.db = patch.object(psycopg, "connect", side_effect=AssertionError("NO DATABASE"))
        self.net = patch.object(httpx.HTTPTransport, "handle_request", side_effect=AssertionError("NO HTTP NETWORK"))
        self.async_net = patch.object(httpx.AsyncHTTPTransport, "handle_async_request", side_effect=AssertionError("NO HTTP NETWORK"))
        self.db_guard = self.db.start()
        self.http_guard = self.net.start()
        self.async_http_guard = self.async_net.start()
        self.addCleanup(self.env.stop)
        self.addCleanup(self.db.stop)
        self.addCleanup(self.net.stop)
        self.addCleanup(self.async_net.stop)
        self.addCleanup(reset_settings_cache)
        self.settings = replace(get_settings(), local_actor_id="actor-original",
                                local_project_id="project-b", planning_worker_actor_ids=("actor-original",))
        self.auth = FakeAuth()

    def tearDown(self):
        self.assertEqual(self.db_guard.call_count, 0, "Unexpected database attempt")
        self.assertEqual(self.http_guard.call_count + self.async_http_guard.call_count, 0,
                         "Unexpected real HTTP attempt")

    def client(self, settings=None, peer="127.0.0.1", auth=None, service=None, models=None):
        cfg = settings or self.settings
        adapter = auth or self.auth
        container = AppContainer(settings=cfg, sessions=adapter, browser_auth=adapter, plan_service=service,
                                 model_settings_service=models)
        return TestClient(create_app(container), base_url="http://127.0.0.1:8000", client=(peer, 12345))

    def enter(self, client, **kwargs):
        return client.post("/api/v1/session/local",
                           json=kwargs.pop("json", {}), headers=kwargs.pop("headers", {"Origin": "http://localhost:5173"}), **kwargs)

    def test_original_scope_and_explicit_project_survive_container_restart(self):
        c = self.client()
        response = self.enter(c)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["project_ids"], ["project-a", "project-b"])
        self.assertEqual(response.json()["default_project_id"], "project-b")
        self.assertTrue(response.json()["csrf_token"])
        self.assertIn("HttpOnly", response.headers["set-cookie"])
        self.assertIn("SameSite=strict", response.headers["set-cookie"])
        c2 = self.client()
        c2.cookies.update(c.cookies)
        self.assertEqual(c2.get("/api/v1/session").json()["project_ids"], ["project-a", "project-b"])
        self.assertEqual(self.auth.issues, 1)

    def test_missing_placeholder_unknown_actor_and_worker_mismatch_issue_nothing(self):
        cases = [replace(self.settings, local_actor_id=a) for a in ("", " ", "local_actor", "actor-missing", "a,b")]
        cases += [replace(self.settings, planning_worker_actor_ids=()),
                  replace(self.settings, local_project_id="local_project"),
                  replace(self.settings, local_project_id="project-other")]
        for cfg in cases:
            with self.subTest(actor=cfg.local_actor_id, project=cfg.local_project_id):
                r = self.enter(self.client(cfg))
                self.assertIn(r.status_code, (403, 503), r.text)
        self.assertEqual(self.auth.issues, 0)

    def test_client_actor_and_project_cannot_be_selected(self):
        c = self.client()
        self.assertEqual(self.enter(c, json={"actor_id": "actor-other"}).status_code, 422)
        r = self.enter(c, headers={"Origin": "http://localhost:5173", "X-Actor-Id": "actor-other"})
        self.assertEqual(r.status_code, 200)
        token = c.cookies.get(self.settings.session_cookie_name)
        self.assertEqual(self.auth.resolve(token).actor_id, "actor-original")
        foreign = self.auth.issue("actor-other")
        c.cookies.set(self.settings.session_cookie_name, foreign)
        self.assertEqual(c.get("/api/v1/session").status_code, 403)

    def test_nonloopback_peer_and_forwarded_spoof_rejected(self):
        for peer in ("192.168.1.20", "example.com"):
            with self.subTest(peer=peer):
                self.assertEqual(self.enter(self.client(peer=peer), headers={"Origin": "http://localhost:5173", "X-Forwarded-For": "127.0.0.1"}).status_code, 403)
        self.assertEqual(self.auth.issues, 0)

    def _assert_loopback_forwarded_header_rejected(self, header, value):
        auth = FakeAuth()
        with self.client(peer="127.0.0.1", auth=auth) as client:
            response = self.enter(client, headers={"Origin": "http://localhost:5173", header: value})
        self.assertEqual(response.status_code, 403, response.text)
        self.assertEqual(auth.issues, 0)
        self.assertEqual(len(auth.rows), 0)

    def test_loopback_forwarded_header_rejected_before_session_issue(self):
        self._assert_loopback_forwarded_header_rejected("Forwarded", "for=127.0.0.1;host=localhost:5173")

    def test_loopback_x_forwarded_for_rejected_before_session_issue(self):
        self._assert_loopback_forwarded_header_rejected("X-Forwarded-For", "127.0.0.1")

    def test_loopback_x_forwarded_host_rejected_before_session_issue(self):
        self._assert_loopback_forwarded_header_rejected("X-Forwarded-Host", "localhost:5173")

    def test_untrusted_hosts_origins_and_cross_site_requests_rejected_before_issue(self):
        for headers in ({"Host": "attacker.example:8000", "Origin": "http://localhost:5173"},
                        {"Host": "127.0.0.1.attacker.example", "Origin": "http://localhost:5173"},
                        {"Host": "localhost:9001", "Origin": "http://localhost:5173"},
                        {"Origin": "http://attacker.example"}, {},
                        {"Origin": "null"},
                        {"Origin": "http://localhost:5173", "Sec-Fetch-Site": "cross-site"}):
            with self.subTest(headers=headers):
                self.assertEqual(self.enter(self.client(), headers=headers).status_code, 403)
        self.assertEqual(self.auth.issues, 0)

    def test_existing_business_writes_require_csrf_even_without_origin(self):
        c = self.client()
        csrf = self.enter(c).json()["csrf_token"]
        for headers in ({}, {"X-CSRF-Token": "wrong"}, {"X-CSRF-Token": csrf, "Origin": "http://evil.example"}):
            self.assertEqual(c.post("/api/v1/auth/logout", json={}, headers=headers).status_code, 403)
        self.assertEqual(c.post("/api/v1/auth/logout", json={}, headers={"X-CSRF-Token": csrf}).status_code, 200)

    def test_cli_password_login_retained_and_csrf_still_required(self):
        c = self.client()
        r = c.post("/api/v1/auth/login", json={"username": "fixture", "password": "Pass123"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(c.post("/api/v1/auth/logout", json={}).status_code, 403)
        self.assertEqual(c.post("/api/v1/auth/logout", json={}, headers={"X-CSRF-Token": r.json()["csrf_token"]}).status_code, 200)

    def test_legacy_token_and_registration_cannot_bypass_local_binding(self):
        c = self.client()
        self.assertEqual(c.post("/api/v1/session", json={"token": "pretend"}).status_code, 403)
        self.assertEqual(c.post("/api/v1/auth/register", json={"username": "fixture", "password": "Pass123"}).status_code, 403)
        self.assertEqual(self.auth.issues, 0)

    def test_mode_off_does_not_enable_passwordless_entry(self):
        c = self.client(replace(self.settings, local_entry_enabled=False))
        self.assertEqual(c.get("/api/v1/session/entry-mode").json(), {"local_entry_enabled": False})
        self.assertEqual(self.enter(c).status_code, 403)
        self.assertEqual(self.auth.issues, 0)

    def test_unsafe_listener_and_configured_origins_fail_startup(self):
        for cfg in (replace(self.settings, app_host="0.0.0.0"),
                    replace(self.settings, app_host="localhost"),
                    replace(self.settings, allow_origins=("http://evil.example",)),
                    replace(self.settings, csrf_enabled=False)):
            with self.subTest(host=cfg.app_host):
                with self.assertRaises(StartupSecurityError):
                    self.client(cfg)

    def test_missing_persistent_adapter_fails_closed(self):
        sessions = InMemorySessionStore((SessionRecord("fixture-token", "actor-original", "fixture-session", ("project-b",)),))
        c = TestClient(create_app(AppContainer(settings=self.settings, sessions=sessions)),
                       base_url="http://127.0.0.1:8000", client=("127.0.0.1", 12345))
        self.assertEqual(self.enter(c).status_code, 503)
        c.cookies.set(self.settings.session_cookie_name, "fixture-token")
        self.assertEqual(c.post("/api/v1/auth/logout", json={}).status_code, 503)

    def historical_fixture(self):
        repo = ScopedFakePlans()
        stage = PlanStage("stage-existing", "stage.basic", "Existing stage", OutlineSectionKind.FOUNDATION, 0)
        draft = PlanDraft("draft-fixture", "project-b", "run-fixture", "Original goal", 1,
                          stages=(stage,), unit_links=(PlanUnitLink(stage.stage_id, "unit-existing", 0),))
        repo.drafts[draft.draft_id] = draft
        runs, provider = FakeRuns(), DenyProvider()
        service = PlanService(repository=repo, runs=runs, catalog=None, resources=None, llm=provider,
                              graph_version="b3f2-batch-v1")
        return repo, runs, provider, self.client(service=service, models=ModelSettingsService(FakeModels(), lambda url: url))

    def test_original_models_run_draft_and_cross_project_read_write_scope(self):
        repo, runs, provider, c = self.historical_fixture()
        csrf = self.enter(c).json()["csrf_token"]
        self.assertEqual(c.get("/api/v1/model-settings").json()["model_id"], "existing-model")
        run = c.get("/api/v1/runs/run-fixture?project_id=project-b")
        self.assertEqual(run.status_code, 200, run.text)
        self.assertEqual(run.json()["status"], "waiting_user")
        self.assertEqual(c.get("/api/v1/plans/drafts/draft-fixture?project_id=project-b").status_code, 200)
        for project in ("project-other", "project-nonexistent"):
            self.assertEqual(c.get(f"/api/v1/runs/run-fixture?project_id={project}").status_code, 403)
            self.assertEqual(c.get(f"/api/v1/plans/drafts/draft-fixture?project_id={project}").status_code, 403)
            r = c.post(f"/api/v1/plans/drafts/draft-fixture/decision?project_id={project}",
                       json={"decision": "cancel", "expected_version": 0}, headers={"X-CSRF-Token": csrf})
            self.assertEqual(r.status_code, 403)
        self.assertEqual(str(runs.row.status), "waiting_user")
        self.assertEqual(len(repo.revisions), 0)
        self.assertEqual(provider.calls, 0)

    def test_fake_old_waiting_user_approve_readback_replay_and_stale_guards(self):
        repo, runs, provider, c = self.historical_fixture()
        csrf = self.enter(c).json()["csrf_token"]
        url = "/api/v1/plans/drafts/draft-fixture/decision?project_id=project-b"
        original_hash = repo.drafts["draft-fixture"].content_hash
        body = {"decision": "approve", "expected_version": 0, "draft_hash": original_hash, "idempotency_key": "fixture-approve"}
        for invalid in ({**body, "draft_hash": "stale"}, {**body, "expected_version": 8}):
            self.assertEqual(c.post(url, json=invalid, headers={"X-CSRF-Token": csrf}).status_code, 409)
        self.assertEqual(c.post(url, json=body).status_code, 403)
        self.assertEqual(c.post(url, json=body, headers={"X-CSRF-Token": csrf, "Origin": "http://evil.example"}).status_code, 403)
        first = c.post(url, json=body, headers={"X-CSRF-Token": csrf})
        self.assertEqual(first.status_code, 200, first.text)
        repeated = c.post(url, json=body, headers={"X-CSRF-Token": csrf})
        self.assertEqual(repeated.status_code, 200, repeated.text)
        current = c.get("/api/v1/plans/current?project_id=project-b")
        self.assertEqual(current.json(), first.json()["plan"])
        self.assertEqual(repeated.json()["plan"], first.json()["plan"])
        self.assertEqual(current.json()["unit_links"][0]["unit_id"], "unit-existing")
        self.assertEqual(len(repo.revisions), 1)
        self.assertEqual(repo.drafts["draft-fixture"].content_hash, original_hash)
        self.assertEqual(runs.row.status, AiRunStatus.SUCCEEDED)
        self.assertEqual(provider.calls, 0)

    def test_fake_cancel_uses_separate_fixture_and_dispatches_nothing(self):
        repo, runs, provider, c = self.historical_fixture()
        csrf = self.enter(c).json()["csrf_token"]
        r = c.post("/api/v1/plans/drafts/draft-fixture/decision?project_id=project-b",
                   json={"decision": "cancel", "expected_version": 0}, headers={"X-CSRF-Token": csrf})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(runs.row.status, AiRunStatus.CANCELLED)
        self.assertEqual(len(repo.revisions), 0)
        self.assertEqual(provider.calls, 0)

    def test_invalid_session_payload_never_echoes_credential_input(self):
        marker = "fixture-secret-never-echo"
        c = self.client()
        r = self.enter(c, json={"api_key": marker, "Authorization": marker})
        self.assertEqual(r.status_code, 422)
        self.assertNotIn(marker, r.text)
        self.assertEqual(self.auth.issues, 0)

    def test_pg_adapter_reads_existing_identity_and_explicit_ownership_without_cleanup(self):
        adapter = PgBrowserAuth("postgresql://unused/unused", 1200)
        connection = MemoryConnection()
        with patch.object(adapter, "connection", return_value=connection):
            self.assertEqual(adapter.local_binding("actor-original", "project-b"), ["project-a", "project-b"])
            with self.assertRaises(ForbiddenError):
                adapter.local_binding("actor-original", "project-other")
            token = adapter.issue_local("actor-original", "project-b")
        self.assertTrue(token)
        self.assertEqual(sum("INSERT INTO auth_sessions" in sql for sql, _ in connection.queries), 1)
        self.assertFalse(any("DELETE" in sql or "UPDATE" in sql for sql, _ in connection.queries))
        self.assertTrue(any(sql == "SET TRANSACTION READ ONLY" for sql, _ in connection.queries))

    def test_pg_adapter_unknown_or_ambiguous_actor_issues_no_session(self):
        for users in ([], ["actor-original", "actor-original"]):
            adapter = PgBrowserAuth("postgresql://unused/unused", 1200)
            connection = MemoryConnection(users)
            with patch.object(adapter, "connection", return_value=connection):
                with self.assertRaises(ForbiddenError):
                    adapter.issue_local("actor-original", "project-b")
            self.assertFalse(any("INSERT" in sql for sql, _ in connection.queries))


if __name__ == "__main__":
    unittest.main()
