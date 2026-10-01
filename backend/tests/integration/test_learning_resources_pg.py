"""Real PG resource isolation/idempotency; search transport is explicitly deterministic."""
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime

import psycopg
import pytest
from app.application.learning_resources import LearningResourceService
from app.composition import build_container
from app.core.config import get_settings
from app.core.errors import AppError
from app.domain.enums import MediaType, ResourceProvenance, ResourceVerificationStatus
from app.domain.resources.models import ResourceRecord, UnavailableResult
from app.domain.workspace.models import AuthContext
from app.infrastructure.db.learning_resources import PgLearningResources
from app.infrastructure.domain_pack import load_pack
from app.tools.seed_b3 import seed_reviewed_pack

from tests.e2e.test_b2v_http_end_to_end import migrated_db as migrated_db

pytestmark = pytest.mark.postgres


class CountingSearch:
    def __init__(self, fail=False):
        self.calls = 0
        self.fail = fail

    def find(self, query):
        self.calls += 1
        if self.fail == "exception":
            raise RuntimeError("must-not-leak-private-provider-key")
        if self.fail:
            return UnavailableResult("搜索响应未知，请核对后再显式发起新搜索")
        return [ResourceRecord(
            resource_id="candidate-1", url="https://docs.python.org/3/", title="Python documentation",
            project_id=query.extra["project_id"], media_type=MediaType.TEXT, language="en",
            provenance=ResourceProvenance.COMMUNITY,
            verification_status=ResourceVerificationStatus.UNVERIFIED,
        )]


@pytest.fixture(scope="module")
def scenario(migrated_db):
    with psycopg.connect(migrated_db.migrator_dsn) as conn:
        seed_reviewed_pack(conn, load_pack("agent-application-v3.json"))
    settings = replace(get_settings(), database_url=migrated_db.app_dsn, llm_provider="fake",
                       local_session_token="", planning_worker_admission_mode="trusted_server")
    container = build_container(settings)
    token = container.browser_auth.register("资源选择用户", "Test-pass1!", "isolated-peer")
    # BrowserAuth exposes its server-side context through the actual persisted session.
    scope = container.browser_auth.resolve(token)
    project = scope.learning_project_scope[0]
    run = container.plan_service.submit_generation(scope=scope, project_id=project, goal="学习 Agent 应用开发")
    assert container.planning_worker.tick()
    completed = container.plan_service.get_run(scope=scope, project_id=project, run_id=run)
    draft = container.plan_service.get_draft(scope=scope, project_id=project, draft_id=completed.run.result_ref)
    from app.application.plan_service import DecisionCommand
    from app.domain.enums import DraftDecision
    published = container.plan_service.decide(scope=scope, project_id=project,
        draft_id=draft.draft.draft_id, command=DecisionCommand(decision=DraftDecision.APPROVE, expected_version=0,
        draft_hash=draft.draft.content_hash, idempotency_key="resources-publish"))
    plan = published.plan
    link = plan.unit_links[0]
    target = {"project_id": project, "plan_id": plan.plan_id,
              "stage_id": link.stage_id, "unit_id": link.unit_id}
    return migrated_db, scope, target


def service(db, *, limit=1000, search=None):
    return LearningResourceService(PgLearningResources(db.app_dsn), search or CountingSearch(), limit)


def test_same_search_key_is_one_dispatch_and_different_query_conflicts(scenario):
    db, scope, target = scenario
    adapter = CountingSearch()
    app = service(db, search=adapter)
    first = app.search(scope, target, "Python documentation", "same-search")
    assert first["status"] == "succeeded" and adapter.calls == 1
    assert app.search(scope, target, "Python documentation", "same-search") == first
    with pytest.raises(AppError) as exc:
        app.search(scope, target, "different", "same-search")
    assert exc.value.http_status == 409 and adapter.calls == 1


def test_zero_budget_and_invalid_unicode_never_dispatch(scenario):
    db, scope, target = scenario
    adapter = CountingSearch()
    app = service(db, limit=0, search=adapter)
    with pytest.raises(AppError) as exc:
        app.search(scope, target, "Python docs", "disabled-search")
    assert exc.value.http_status == 429
    with pytest.raises(AppError) as exc:
        app.search(scope, target, "invalid\ud800", "invalid-search")
    assert exc.value.http_status == 400 and adapter.calls == 0


def test_concurrent_budget_last_slot_is_reserved_once(scenario):
    db, scope, target = scenario
    with psycopg.connect(db.migrator_dsn) as conn:
        before = conn.execute("SELECT request_count FROM search_usage_counter").fetchone()[0]
    adapter = CountingSearch()
    app = service(db, limit=before + 1, search=adapter)
    def attempt(index):
        try:
            return app.search(scope, target, "Python docs", f"last-slot-{index}")["status"]
        except AppError as exc:
            return exc.http_status
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(attempt, range(2)))
    assert sorted(map(str, outcomes)) == ["429", "succeeded"] and adapter.calls == 1


def test_selected_resource_is_private_version_bound_and_persisted(scenario):
    db, scope, target = scenario
    app = service(db)
    found = app.search(scope, target, "Python docs", "select-search")
    selected = app.select(scope, target, found["search_id"], "candidate-1")
    assert app.select(scope, target, found["search_id"], "candidate-1") == selected
    assert service(db).list_selected(scope, target) == [selected]
    assert selected["resource"]["verification_status"] == "unverified"
    assert selected["resource"]["checked_at"] is None
    wrong = AuthContext(actor_id="other", session_id="other", issued_at=datetime.now(UTC),
                        learning_project_scope=(target["project_id"],))
    with pytest.raises(AppError):
        app.list_selected(wrong, target)
    forged = dict(target, unit_id="missing-unit")
    with pytest.raises(AppError):
        app.select(scope, forged, found["search_id"], "candidate-1")
    with psycopg.connect(db.app_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM learning_resource_selections").fetchone()[0] == 0


@pytest.mark.parametrize("failure", [True, "exception"])
def test_unknown_search_is_persisted_and_never_redispatched(scenario, failure):
    db, scope, target = scenario
    adapter = CountingSearch(fail=failure)
    app = service(db, search=adapter)
    key = f"unknown-search-{failure}"
    first = app.search(scope, target, "Python docs", key)
    assert first["status"] == "reconciliation_required"
    assert service(db, search=adapter).search(scope, target, "Python docs", key) == first
    assert "private-provider-key" not in str(first)
    assert adapter.calls == 1


def test_manual_url_has_no_provider_call_and_preserves_removed_history(scenario):
    db, scope, target = scenario
    adapter = CountingSearch()
    app = service(db, search=adapter)
    item = app.add_manual(scope, target, "https://github.com/langchain-ai/langgraph", "LangGraph repo")
    assert adapter.calls == 0 and item["resource"]["provenance"] == "user_provided"
    assert app.remove(scope, target, item["selection_id"])
    assert item not in app.list_selected(scope, target)
    with psycopg.connect(db.migrator_dsn) as conn:
        assert conn.execute("SELECT removed_at IS NOT NULL FROM learning_resource_selections WHERE selection_id=%s",
                            (item["selection_id"],)).fetchone()[0]
    with pytest.raises(AppError):
        app.add_manual(scope, target, "http://172.16.1.1/internal", "private")
    safe = app.add_manual(scope, target, "https://fcs.example.org/docs", "Public DNS name starting with fc")
    assert safe["resource"]["url"] == "https://fcs.example.org/docs" and adapter.calls == 0
    with pytest.raises(AppError):
        app.add_manual(scope, target, "https://example.org/docs", "invalid\ud800")


def test_resource_write_rechecks_plan_after_waiting_for_publication(scenario):
    db, scope, target = scenario
    app = service(db)
    pool = ThreadPoolExecutor(max_workers=1)
    blocker = psycopg.connect(db.migrator_dsn)
    try:
        blocker.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))",
                        (f"plan-decision:{target['project_id']}",))
        future = pool.submit(app.add_manual, scope, target, "https://example.org/stale-version", "stale")
        waiting = False
        deadline = time.monotonic() + 3
        with psycopg.connect(db.migrator_dsn, autocommit=True) as observer:
            while time.monotonic() < deadline and not future.done():
                waiting = observer.execute("""SELECT EXISTS(SELECT 1 FROM pg_locks
                    WHERE database=(SELECT oid FROM pg_database WHERE datname=current_database())
                    AND locktype='advisory' AND NOT granted)""").fetchone()[0]
                if waiting:
                    break
                time.sleep(0.02)
        assert waiting, "Resource write must wait for the same publication lock"
        blocker.execute("UPDATE plan_revisions SET status='superseded' WHERE plan_id=%s", (target["plan_id"],))
        blocker.commit()
        with pytest.raises(AppError) as exc:
            future.result(timeout=5)
        assert exc.value.http_status == 404
    finally:
        blocker.rollback()
        blocker.close()
        pool.shutdown(wait=True)
        with psycopg.connect(db.migrator_dsn) as conn:
            conn.execute("UPDATE plan_revisions SET status='approved' WHERE plan_id=%s", (target["plan_id"],))


def test_resource_http_contract_csrf_read_key_and_selection(scenario):
    from app.main import create_app
    from fastapi.testclient import TestClient
    db, scope, target = scenario
    settings = replace(get_settings(), database_url=db.app_dsn, llm_provider="fake", local_session_token="")
    container = build_container(settings)
    adapter = CountingSearch()
    container = replace(container, resource_service=service(db, search=adapter))
    with TestClient(create_app(container)) as client:
        client.cookies.set(settings.session_cookie_name, container.browser_auth.issue(scope.actor_id))
        headers = {"X-CSRF-Token": client.get("/api/v1/session").json()["csrf_token"]}
        body = {k: v for k, v in target.items() if k != "project_id"}
        query = {"project_id": target["project_id"]}
        searching = dict(body, query="Python docs", idempotency_key="http-search")
        assert client.post("/api/v1/resources/searches", params=query, json=searching).status_code == 403
        response = client.post("/api/v1/resources/searches", params=query, json=searching, headers=headers)
        assert response.status_code == 200, response.text
        found = response.json()
        read = client.get("/api/v1/resources/searches/by-key/http-search", params={**target})
        assert read.status_code == 200 and read.json() == found and adapter.calls == 1
        selected = client.post("/api/v1/resources/selections", params=query, headers=headers,
            json=dict(body, search_id=found["search_id"], candidate_id="candidate-1"))
        assert selected.status_code == 200, selected.text
        listing = client.get("/api/v1/resources/selections", params=target)
        assert listing.status_code == 200 and selected.json() in listing.json()
        removed = client.delete(f"/api/v1/resources/selections/{selected.json()['selection_id']}",
                                params=target, headers=headers)
        assert removed.status_code == 200
        notfound = client.get("/api/v1/resources/searches/by-key/never-dispatched", params=target)
        assert notfound.status_code == 404 and adapter.calls == 1
