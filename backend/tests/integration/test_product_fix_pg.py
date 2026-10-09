"""New owned PG only: v2 facts survive Draft/Revision/HTTP fresh readback."""
import json
from dataclasses import replace
from pathlib import Path

import pytest
from app.domain.planning.curriculum import validate_curriculum_output
from app.domain.planning.models import PlanPublicationService
from app.infrastructure.db.plan_repository import PgPlanRepository
from app.infrastructure.db.v2_planning_persistence import PgV2PlanningPersistence

from backend.tests.integration import test_v2_planning_persistence_pg as old
from backend.tests.unit.test_curriculum_product_v2 import SCOPE, arrange_scope, fixture

pytestmark = pytest.mark.postgres
EVIDENCE = Path(__file__).resolve().parents[3] / "var/planning-v2-product-fix-20261010/pg"


@pytest.fixture(scope="module")
def db():
    # Reuse proven owned harness; point its evidence writes to this new packet.
    previous = old.EVIDENCE
    old.EVIDENCE = EVIDENCE
    generator = old.db.__wrapped__()
    try:
        yield next(generator)
    finally:
        try:
            next(generator)
        except StopIteration:
            pass
        old.EVIDENCE = previous


@pytest.fixture
def scope(db):
    return old.scope.__wrapped__(db)


@pytest.mark.parametrize("mode", ["permission", "recommended"])
def test_new_v2_facts_persist_confirm_and_fresh_readback(db, monkeypatch, mode):
    from uuid import uuid4

    from app import main
    from app.application.container import AppContainer
    from app.application.plan_service import PlanService
    from app.core.config import get_settings
    from app.infrastructure.db.browser_auth import PgBrowserAuth
    from app.infrastructure.db.public_resource_catalog import PgPublicResourceCatalog
    from app.infrastructure.db.run_repository import PgRunRepository
    from fastapi.testclient import TestClient

    from backend.tests.integration.test_v2_planning_http_pg import ForbiddenDispatch

    auth = PgBrowserAuth(db.app_dsn, 3600)
    token = auth.register("product_v2_" + uuid4().hex[:12], "pytest42", "owned-test")
    scope = auth.resolve(token)
    ctx, raw, args = fixture(constraints=(SCOPE,) if mode == "permission" else (), recommended=mode == "recommended")
    if mode == "permission":
        arrange_scope(raw, ctx)
    else:
        optional = raw["stages"].pop()
        refs = set(optional["outcome_refs"])
        raw["carrier"]["final_artifact"]["acceptance"][0]["outcome_refs"] = [r for r in raw["carrier"]["final_artifact"]["acceptance"][0]["outcome_refs"] if r not in refs]
        raw["status"] = "complete"
    curriculum = validate_curriculum_output(raw, ctx.to_payload())
    project = scope.learning_project_scope[0]
    draft = PgV2PlanningPersistence(db.app_dsn, allow_unbound_preview=True).persist(scope=scope,
        project_id=project, run_id="", expected_version=0, curriculum=curriculum, **args)
    repo = PgPlanRepository(db.app_dsn)
    fresh_draft = repo.get_draft(project_id=project, draft_id=draft.draft_id)
    assert fresh_draft.content_hash == draft.content_hash
    assert fresh_draft.v2_execution.to_payload() == draft.v2_execution.to_payload()
    published = PlanPublicationService(repo).publish(draft=fresh_draft, presented_hash=draft.content_hash,
        expected_version=0, idempotency_key="product-v2-" + mode)
    fresh = PgPlanRepository(db.app_dsn).get_current(project_id=project)
    assert fresh.plan_id == published.plan_id
    assert fresh.v2_execution.semantic_payload() == draft.v2_execution.semantic_payload()
    view = fresh.v2_execution.user_content()
    if mode == "permission":
        assert view["constraints"]["permission_obligations"] == curriculum.to_payload()["permission_obligations"]
        assert view["constraints"]["assessments"][0]["runtime_status"] == "unverified"
    else:
        assert view["unresolved"] == raw["unresolved"]
        assert view["unresolved"]
    settings = replace(get_settings(), app_env="development", session_cookie_secure=False)
    monkeypatch.setattr(main, "get_settings", lambda: settings)
    service = PlanService(repository=repo, runs=PgRunRepository(db.app_dsn), catalog=ForbiddenDispatch(),
        resources=PgPublicResourceCatalog(db.app_dsn), llm=ForbiddenDispatch(), graph_version="",
        v2_persistence=PgV2PlanningPersistence(db.app_dsn, allow_unbound_preview=True))
    container = AppContainer(settings=settings, sessions=auth, browser_auth=auth, plan_service=service)
    with TestClient(main.create_app(container)) as client:
        client.cookies.set(settings.session_cookie_name, token)
        params = {"project_id": project}
        current = client.get("/api/v1/plans/current", params=params)
        history = client.get("/api/v1/plans/revisions/1", params=params)
        assert current.status_code == history.status_code == 200
        assert current.json() == history.json()
        assert current.json()["v2_content"] == view
        csrf = {"X-CSRF-Token": auth.detail(token)[0]["csrf_token"]}
        assert client.post("/api/v1/plans/generate", params=params, headers=csrf,
            json={"goal": "synthetic"}).status_code == 503
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / (mode + "-readback.json")).write_text(json.dumps({"database": db.name,
        "project": project, "draft_hash": draft.content_hash, "plan_id": fresh.plan_id,
        "user_content": view, "snapshot": fresh.v2_execution.to_payload()}, ensure_ascii=False, indent=2), encoding="utf8")


def test_durable_scope_receipt_recovery_binds_new_candidate_version(db):
    import psycopg
    from app.core.ids import content_hash
    from app.domain.planning.resource_research import ResearchSession
    from app.infrastructure.checkpointer.v2_planning_runtime import DurableBody, DurableResourceResearcher
    from app.infrastructure.providers.v2_attempts import PgV2Calls
    from psycopg.types.json import Jsonb

    from backend.tests.integration import test_v2_planning_runtime_pg as runtime_fixture
    from backend.tests.unit import test_resource_research as resources
    from backend.tests.unit.test_research_comparison_v2 import Bodies, Reader

    scope, run, fence, facts, manifest = runtime_fixture.bound.__wrapped__(db)
    # This synthetic submission has never dispatched. Freeze its explicit v2
    # marker before the first call; all existing numeric caps remain identical.
    manifest["product_semantics"] = "planning-v2-product-v2"
    manifest["manifest_hash"] = content_hash({k: v for k, v in manifest.items() if k != "manifest_hash"})
    with psycopg.connect(db.migrator_dsn) as conn:
        detail = conn.execute("SELECT detail FROM ai_run_events WHERE run_id=%s AND status='submission'", (run,)).fetchone()[0]
        detail["manifest"] = detail["initial"]["manifest"] = manifest
        conn.execute("UPDATE ai_run_events SET detail=%s WHERE run_id=%s AND status='submission'", (Jsonb(detail), run))

    class Provider(Reader):
        configuration_ref = "test:frozen"
        model = "synthetic"
        def request_options(self, purpose):
            return {"max_tokens": 1024}

    class VersionBodies(Bodies):
        def read(self, candidate, **kwargs):
            body = super().read(candidate, **kwargs)
            body.version = "git-blob:" + candidate.discovery.get("body_version", "a" * 40)
            for chunk in body.chunks:
                chunk["version"] = body.version
                chunk["chunk_id"] = "chunk_" + content_hash({k: chunk[k] for k in ("resource_id", "version", "content_hash", "location")})
            return body

    provider, bodies = Provider(tie=True), VersionBodies()
    p, plan, coverage, gaps = resources.inputs()
    requirement = resources.run()[0].entries[0].requirement
    candidate = replace(resources.candidate(), project_id=fence.project_id)
    def inspect(candidate, desired_depth=None):
        ledger = PgV2Calls(db.app_dsn, scope=scope, project_id=fence.project_id, run_id=run,
            manifest=manifest, fence=fence, provider=provider)
        researcher = DurableResourceResearcher(ledger, github=None, web=None,
            body_reader=DurableBody(ledger, bodies), llm=ledger)
        session = ResearchSession(run, "c" * 64, resources.ResearchBudget(max_cost_micros=1000000), rules_version="research_comparison_v2")
        scoped = replace(requirement, desired_depth=desired_depth) if desired_depth else requirement
        return researcher._inspect(candidate, scoped, scoped.must_teach, plan, session, manifest["checked_at"])
    first, _ = inspect(candidate)
    recovered, _ = inspect(candidate)
    assert recovered == first
    assert len(provider.calls) == len(bodies.calls) == 1
    changed = replace(candidate, discovery={"body_version": "b" * 40})
    new, _ = inspect(changed)
    assert len(provider.calls) == len(bodies.calls) == 2
    assert new[0].version != first[0].version
    deeper, _ = inspect(changed, "deep")
    assert deeper
    assert len(provider.calls) == len(bodies.calls) == 3
    again, _ = inspect(changed, "deep")
    assert again == deeper
    assert len(provider.calls) == len(bodies.calls) == 3
    assert all(not body.chunks for body in bodies.produced)
