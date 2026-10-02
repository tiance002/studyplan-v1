"""Real temporary PG reservations; all GitHub/Tavily upstreams are offline doubles."""
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import replace

import psycopg
import pytest
from app.application.learning_resources import LearningResourceService
from app.core.errors import AppError
from app.domain.enums import PreferenceScope
from app.domain.resources.models import ResourcePreference
from app.infrastructure.db.learning_resources import PgLearningResources
from app.ports.resource_index import ResourceInspectionResult

from tests.e2e.test_b2v_http_end_to_end import migrated_db as migrated_db
from tests.integration.test_learning_resources_pg import CountingSearch
from tests.integration.test_learning_resources_pg import scenario as scenario

pytestmark = pytest.mark.postgres


class GitHubFixture(CountingSearch):
    def __init__(self, unknown=False):
        super().__init__()
        self.reads = 0
        self.unknown = unknown

    def find(self, query):
        found = super().find(query)
        found[0].discovery = {"source": "github", "repo": {"owner": "author", "name": "course"}}
        return found

    def inspect(self, query):
        self.reads += 1
        candidate = deepcopy(query.candidate)
        candidate["discovery"] = {**candidate["discovery"], "inspection_status": "chapter_or_index_checked",
            "chapters": [{"path": "ch1.md", "title": "RAG", "order": 0, "status": "read"},
                         {"path": "ch2.md", "title": "Practice", "order": 1, "status": "listed"}],
            "files": [{"path": "README.md", "url": "https://github.com/author/course/blob/main/README.md",
                       "content_hash": "b" * 64, "blob_sha": "a" * 40,
                       "fetched_at": "2026-10-02T00:00:00Z", "line_start": 1, "line_end": 10},
                      {"path": "ch1.md", "url": "https://github.com/author/course/blob/main/ch1.md",
                       "content_hash": "c" * 64, "blob_sha": "d" * 40,
                       "fetched_at": "2026-10-02T00:00:00Z", "line_start": 1, "line_end": 12}],
            "signals": {"topic_overlap": 1, "teaching_structure": True}}
        return ResourceInspectionResult("reconciliation_required" if self.unknown else "succeeded",
            candidate, [{"kind": "content", "path": "/repos/author/course/readme",
                         "status": "reconciliation_required" if self.unknown else "succeeded"}],
            "upstream unknown" if self.unknown else None)


def app(db, github=None, **kwargs):
    return LearningResourceService(PgLearningResources(db.app_dsn), None, 1000,
        github=github or GitHubFixture(), **kwargs)


def test_github_available_without_tavily_freezes_preferences_and_source_intent(scenario):
    db, scope, target = scenario
    github = GitHubFixture()
    preferences = [ResourcePreference(PreferenceScope.UNIT, target["unit_id"], language="en")]
    calls = []
    def resolver(*_):
        calls.append(True)
        return preferences[0]
    service = app(db, github, preference_resolver=resolver)
    first = service.search(scope, target, "RAG", "github-frozen", source="github")
    assert first["source"] == "github" and first["context_snapshot"]["preference"]["language"] == "en"
    preferences[0] = replace(preferences[0], language="zh", version=2)
    assert service.search(scope, target, "RAG", "github-frozen", source="github") == first
    assert len(calls) == 1 and github.calls == 1
    with pytest.raises(AppError) as exc:
        service.search(scope, target, "RAG", "github-frozen", source="web")
    assert exc.value.http_status == 409


def test_node_membership_and_node_intent_are_checked_before_dispatch(scenario):
    db, scope, target = scenario
    github = GitHubFixture()
    service = app(db, github)
    with psycopg.connect(db.migrator_dsn) as conn:
        node = conn.execute("SELECT node_id FROM unit_node_links WHERE project_id=%s AND unit_id=%s LIMIT 1",
                            (target["project_id"], target["unit_id"])).fetchone()[0]
    scoped = dict(target, node_id=node)
    service.search(scope, scoped, "RAG", "node-intent", source="github")
    with pytest.raises(AppError) as exc:
        service.search(scope, target, "RAG", "node-intent", source="github")
    assert exc.value.http_status == 409 and github.calls == 1
    with pytest.raises(AppError) as exc:
        service.search(scope, dict(target, node_id="unknown-node"), "RAG", "bad-node", source="github")
    assert exc.value.http_status == 404 and github.calls == 1


def test_inspection_reserves_once_freezes_result_and_selection_uses_evidence(scenario):
    db, scope, target = scenario
    github = GitHubFixture()
    service = app(db, github)
    search = service.search(scope, target, "RAG", "inspect-search", source="github")
    with psycopg.connect(db.migrator_dsn) as conn:
        before = conn.execute("SELECT content_reserved,metadata_reserved FROM resource_read_usage_counter").fetchone()
    first = service.inspect(scope, target, search["search_id"], "candidate-1", "inspect-one")
    assert first["status"] == "succeeded" and len(first["receipts"]) == 1
    assert service.inspect(scope, target, search["search_id"], "candidate-1", "inspect-one") == first
    assert service.get_inspection_by_key(scope, target, "inspect-one") == first
    selected = service.select(scope, target, search["search_id"], "candidate-1")
    assert selected["resource"]["discovery"]["inspection_status"] == "chapter_or_index_checked"
    assert selected["resource"]["verification_status"] == "unverified"
    with psycopg.connect(db.migrator_dsn) as conn:
        after = conn.execute("SELECT content_reserved,metadata_reserved FROM resource_read_usage_counter").fetchone()
    assert after == (before[0] + 3, before[1] + 2) and github.reads == 1
    with pytest.raises(AppError) as exc:
        service.inspect(scope, target, search["search_id"], "candidate-1", "inspect-one", paths=["ch1.md"])
    assert exc.value.http_status == 409
    with pytest.raises(AppError):
        service.get_inspection(scope, dict(target, unit_id="missing"), first["inspection_id"])


def test_inspection_unknown_no_replay_and_zero_content_or_metadata_budget_no_dispatch(scenario):
    db, scope, target = scenario
    github = GitHubFixture(unknown=True)
    service = app(db, github)
    search = service.search(scope, target, "RAG", "unknown-inspect-search", source="github")
    first = service.inspect(scope, target, search["search_id"], "candidate-1", "unknown-inspect")
    assert first["status"] == "reconciliation_required"
    assert service.inspect(scope, target, search["search_id"], "candidate-1", "unknown-inspect") == first
    for kwargs in ({"content_limit": 0}, {"metadata_limit": 0}):
        with pytest.raises(AppError) as exc:
            app(db, github, **kwargs).inspect(scope, target, search["search_id"], "candidate-1", "no-budget-" + next(iter(kwargs)))
        assert exc.value.http_status == 429
    assert github.reads == 1


def test_requested_chapters_require_actual_index_and_preserve_author_order(scenario):
    db, scope, target = scenario
    github = GitHubFixture()
    service = app(db, github)
    search = service.search(scope, target, "RAG", "path-search", source="github")
    with pytest.raises(AppError) as exc:
        service.inspect(scope, target, search["search_id"], "candidate-1", "arbitrary-path", paths=["secret.md"])
    assert exc.value.http_status == 400 and github.reads == 0
    service.inspect(scope, target, search["search_id"], "candidate-1", "index-first")
    for paths in (["secret.md"], ["ch2.md", "ch1.md"]):
        with pytest.raises(AppError):
            service.inspect(scope, target, search["search_id"], "candidate-1", "invalid-order", paths=paths)
    checked = service.inspect(scope, target, search["search_id"], "candidate-1", "indexed-path", paths=["ch1.md", "ch2.md"])
    assert checked["status"] == "succeeded" and github.reads == 2


def test_legacy_web_hash_same_key_replies_without_dispatch(scenario):
    db, scope, target = scenario
    old_hash = hashlib.sha256(json.dumps([target, "legacy query"], sort_keys=True).encode()).hexdigest()
    with psycopg.connect(db.migrator_dsn) as conn:
        conn.execute("""INSERT INTO resource_search_requests(search_id,project_id,plan_id,stage_id,unit_id,
            actor_id,idempotency_key,input_hash,query,status) VALUES('legacy-web-search',%s,%s,%s,%s,%s,
            'legacy-web-key',%s,'legacy query','succeeded')""",
            (*PgLearningResources._position(target), scope.actor_id, old_hash))
    adapter = CountingSearch()
    service = LearningResourceService(PgLearningResources(db.app_dsn), adapter, 1000)
    cached = service.search(scope, target, "legacy query", "legacy-web-key")
    assert cached["search_id"] == "legacy-web-search" and adapter.calls == 0
    with pytest.raises(AppError) as exc:
        service.search(scope, target, "changed legacy query", "legacy-web-key")
    assert exc.value.http_status == 409


def test_legacy_node_hash_proves_exact_node_for_get_key_and_same_body_retry(scenario):
    db, scope, target = scenario
    with psycopg.connect(db.migrator_dsn) as conn:
        node = conn.execute("SELECT node_id FROM unit_node_links WHERE project_id=%s AND unit_id=%s LIMIT 1",
                            (target["project_id"], target["unit_id"])).fetchone()[0]
        scoped = dict(target, node_id=node)
        old_hash = hashlib.sha256(json.dumps([scoped, "legacy node"], sort_keys=True).encode()).hexdigest()
        conn.execute("""INSERT INTO resource_search_requests(search_id,project_id,plan_id,stage_id,unit_id,
            actor_id,idempotency_key,input_hash,query,status) VALUES('legacy-node-search',%s,%s,%s,%s,%s,
            'legacy-node-key',%s,'legacy node','succeeded')""",
            (*PgLearningResources._position(target), scope.actor_id, old_hash))
    adapter = CountingSearch()
    service = LearningResourceService(PgLearningResources(db.app_dsn), adapter, 1000)
    original = service.get_search(scope, scoped, "legacy-node-search")
    assert service.get_search_by_key(scope, scoped, "legacy-node-key") == original
    assert service.search(scope, scoped, "legacy node", "legacy-node-key") == original
    with pytest.raises(AppError) as exc:
        service.get_search(scope, target, "legacy-node-search")
    assert exc.value.http_status == 404 and adapter.calls == 0


def test_private_mapping_requires_allowed_keys_and_read_contiguous_chapters(scenario):
    db, scope, target = scenario
    service = app(db)
    search = service.search(scope, target, "RAG", "mapping-search", source="github")
    service.inspect(scope, target, search["search_id"], "candidate-1", "mapping-inspect")
    allowed = service.repository.allowed_module_keys(scope, target)
    assert allowed
    for modules, paths in [(["forged-key"], ["ch1.md"]), (allowed[:1], ["ch2.md"]), (allowed[:1], ["ch1.md", "ch2.md"])]:
        with pytest.raises(AppError):
            service.select(scope, target, search["search_id"], "candidate-1", module_keys=modules, chapter_paths=paths)
    selected = service.select(scope, target, search["search_id"], "candidate-1",
        module_keys=allowed[:1], chapter_paths=["ch1.md"], role="supplement")
    mapping = selected["resource"]["discovery"]["selection_mapping"]
    assert mapping == {"module_keys": allowed[:1], "chapter_paths": ["ch1.md"],
        "role": "supplement", "basis": "user_selected_read_chapters"}
    assert selected["resource"]["verification_status"] == "unverified"


def test_last_inspection_budget_slot_is_atomic_under_concurrency(scenario):
    db, scope, target = scenario
    github = GitHubFixture()
    service = app(db, github)
    search = service.search(scope, target, "RAG", "concurrent-read-search", source="github")
    with psycopg.connect(db.migrator_dsn) as conn:
        content, metadata = conn.execute("SELECT content_reserved,metadata_reserved FROM resource_read_usage_counter").fetchone()
    limited = app(db, github, content_limit=content + 3, metadata_limit=metadata + 2)
    def inspect(index):
        try:
            return limited.inspect(scope, target, search["search_id"], "candidate-1", f"concurrent-inspect-{index}")["status"]
        except AppError as exc:
            return exc.http_status
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(inspect, [1, 2]))
    assert sorted(map(str, outcomes)) == ["429", "succeeded"] and github.reads == 1
    with psycopg.connect(db.migrator_dsn) as conn:
        assert conn.execute("SELECT content_reserved,metadata_reserved FROM resource_read_usage_counter").fetchone() == (content + 3, metadata + 2)


def test_inspection_http_roundtrip_and_cross_actor_access_rejected(scenario):
    from app.composition import build_container
    from app.core.config import get_settings
    from app.main import create_app
    from fastapi.testclient import TestClient
    db, scope, target = scenario
    github = GitHubFixture()
    service = app(db, github)
    container = build_container(replace(get_settings(), database_url=db.app_dsn, llm_provider="fake", local_session_token=""))
    container = replace(container, resource_service=service)
    search = service.search(scope, target, "RAG", "inspection-http-search", source="github")
    body = {k: v for k, v in target.items() if k != "project_id"}
    query = {"project_id": target["project_id"]}
    with TestClient(create_app(container)) as client:
        client.cookies.set(container.settings.session_cookie_name, container.browser_auth.issue(scope.actor_id))
        csrf = {"X-CSRF-Token": client.get("/api/v1/session").json()["csrf_token"]}
        request = dict(body, search_id=search["search_id"], candidate_id="candidate-1", idempotency_key="inspection-http")
        assert client.post("/api/v1/resources/inspections", params=query, json=request).status_code == 403
        result = client.post("/api/v1/resources/inspections", params=query, json=request, headers=csrf)
        assert result.status_code == 200, result.text
        assert client.get("/api/v1/resources/inspections/by-key/inspection-http", params=target).json() == result.json()
        assert client.get("/api/v1/resources/inspections/" + result.json()["inspection_id"], params=target).json() == result.json()
        # Actual persisted owner checks reject a server context that only claims
        # this project in its scope tuple.
        other = replace(scope, actor_id="forged-owner")
        with pytest.raises(AppError) as exc:
            service.get_inspection(other, target, result.json()["inspection_id"])
        assert exc.value.http_status == 403 and github.reads == 1
