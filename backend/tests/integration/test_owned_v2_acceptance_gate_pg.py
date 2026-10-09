"""New owned databases: real stage checkpoints/CAS, synthetic external ports."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import psycopg
import pytest
from app.application.plan_service import PlanService
from app.core.errors import ConflictError, ForbiddenError, IdempotencyConflictError
from app.core.ids import content_hash
from app.domain.planning.content_coverage import ReviewedContentIndex
from app.domain.planning.curriculum_compiler import CurriculumSourceFacts
from app.domain.planning.intent import GoalSpec
from app.domain.planning.resource_research import ResearchBudget
from app.domain.planning.v2_runtime import V2BudgetExceeded, V2RecoveryBlocked
from app.infrastructure.db.browser_auth import PgBrowserAuth
from app.infrastructure.db.job_repository import PgPlanningJobRepository
from app.infrastructure.db.plan_repository import PgPlanRepository
from app.infrastructure.db.public_resource_catalog import PgPublicResourceCatalog
from app.infrastructure.db.run_repository import PgRunRepository
from app.infrastructure.providers.runtime_factory import OwnedV2PlanningRuntimeFactory
from app.infrastructure.worker.planning_worker import PlanningWorker
from app.ports.planning_jobs import PlanningLeaseLostError

from backend.tests.integration import test_v2_planning_runtime_pg as fixture
from backend.tests.integration.test_v2_planning_http_pg import ForbiddenDispatch
from backend.tests.unit.test_research_comparison_v2 import Reader

pytestmark = pytest.mark.postgres
EVIDENCE = Path(__file__).resolve().parents[3] / "var/planning-v2-scenario-a-20261010/owned-gate"


@pytest.fixture(scope="module")
def db():
    old = fixture.EVIDENCE
    fixture.EVIDENCE = EVIDENCE
    generator = fixture.db.__wrapped__()
    try:
        yield next(generator)
    finally:
        fixture.EVIDENCE = old


@pytest.fixture(scope="module")
def checkpoint_db():
    old = fixture.EVIDENCE
    fixture.EVIDENCE = EVIDENCE
    generator = fixture.checkpoint_db.__wrapped__()
    try:
        yield next(generator)
    finally:
        fixture.EVIDENCE = old


class Provider(fixture.PipelineProvider):
    def request_options(self, purpose):
        return {"max_tokens": 1024 if purpose == "planning.research_reader" else 4096}

    def generate_structured(self, **kw):
        result = super().generate_structured(**kw)
        if kw["purpose"] == "planning.research_reader":
            result = replace(result, payload=Reader(tie=True).generate_structured(**kw).payload)
        if kw["purpose"] == "planning.curriculum_composition":
            result.payload.update(schema_version=2, semantics_version=2, permission_obligations=[])
        return result


def make(db, checkpoint_db):
    auth = PgBrowserAuth(db.app_dsn, 3600)
    token = auth.register("gate_" + uuid4().hex[:12], "pytest42", "owned-test")
    scope = auth.resolve(token)
    project = scope.learning_project_scope[0]
    provider, search, bodies, runtimes = Provider(), fixture.PipelineSearch(), fixture.PipelineBodies(), []

    class Factory(OwnedV2PlanningRuntimeFactory):
        def __call__(self, *args, **kw):
            runtime = super().__call__(*args, **kw)
            runtimes.append(runtime)
            return runtime

    factory = Factory(db.app_dsn, checkpoint_db.app_dsn,
        source_facts=CurriculumSourceFacts(ReviewedContentIndex("empty", (), (), ())),
        budget=ResearchBudget(max_searches=6, max_body_bytes=393216, max_reader_requests=6,
            max_output_tokens=18432, max_total_requests=27, max_cost_micros=186000),
        binding_resolver=lambda scope, project: SimpleNamespace(model_ref="test:frozen"),
        provider_resolver=lambda scope, project, run, ref: provider,
        github=search, body_reader=bodies, acceptance_gate="scenario-a-review-v1")
    jobs = PgPlanningJobRepository(db.app_dsn, actor_ids=(scope.actor_id,), max_attempts=4)
    service = PlanService(repository=PgPlanRepository(db.app_dsn), runs=PgRunRepository(db.app_dsn),
        catalog=ForbiddenDispatch(), resources=PgPublicResourceCatalog(db.app_dsn), llm=ForbiddenDispatch(),
        graph_version="", planning_jobs=jobs, v2_runtime_factory=factory)
    run = service.submit_owned_v2(scope=scope, project_id=project, goal_spec=GoalSpec("学习MCP"))
    worker = PlanningWorker(jobs=jobs, execute=service.execute_generation, actor_ids=(scope.actor_id,))
    return scope, project, run, factory, jobs, worker, provider, search, bodies, runtimes


def decide(reviews, scope, project, run, packet, **overrides):
    row = packet["review"]
    return reviews.decide(**({"scope": scope, "project_id": project, "run_id": run,
        "stage": row["stage"], "review_hash": row["digest"], "expected_version": row["run_version"],
        "decision": "approve", "idempotency_key": row["stage"], "evidence_hash": "a" * 64} | overrides))


def test_three_real_pauses_same_run_resume_without_extra_dispatch(db, checkpoint_db):
    scope, project, run, factory, jobs, worker, provider, search, bodies, runtimes = make(db, checkpoint_db)
    reviews = factory.reviews()
    for index, stage in enumerate(("goal_analysis", "capability_planning", "curriculum_composition")):
        assert worker.tick()
        packet = reviews.read(scope=scope, project_id=project, run_id=run)
        assert packet["review"]["stage"] == packet["state"]["stage"] == stage
        assert packet["manifest"]["output_caps"]["planning.curriculum_composition"] == 4096
        assert packet["review"]["budget_root_run_id"] == run
        with psycopg.connect(db.migrator_dsn) as conn:
            row = conn.execute("SELECT r.status,r.next_action,r.result_ref,j.status,j.attempts,j.lease_token FROM ai_runs r JOIN ai_jobs j USING(run_id) WHERE run_id=%s", (run,)).fetchone()
            assert row == ("waiting_user", "review_draft", None, "completed", index + 1, None)
            assert conn.execute("SELECT count(*) FROM plan_drafts WHERE run_id=%s", (run,)).fetchone()[0] == 0
        assert len(provider.calls) == (1 if index == 0 else 2 if index == 1 else 4)
        assert not worker.tick()
        with pytest.raises(PlanningLeaseLostError):
            runtimes[-1].calls.call(step="stale-worker", purpose="research.search", schema="V2ResourceSearchV1",
                payload={}, reserved={}, invoke=lambda _: pytest.fail("stale fence dispatched"), encode=lambda _: ({}, {}))
        assert decide(reviews, scope, project, run, packet) == run
        assert decide(reviews, scope, project, run, packet) == run
        with pytest.raises(IdempotencyConflictError):
            decide(reviews, scope, project, run, packet, evidence_hash="b" * 64)
    before = (len(provider.calls), len(search.calls), len(bodies.calls))
    assert worker.tick()
    assert (len(provider.calls), len(search.calls), len(bodies.calls)) == before == (4, 1, 1)
    with psycopg.connect(db.migrator_dsn) as conn:
        row = conn.execute("SELECT r.status,r.result_ref,j.status,j.attempts FROM ai_runs r JOIN ai_jobs j USING(run_id) WHERE run_id=%s", (run,)).fetchone()
        assert row[0] == "succeeded" and row[1] and row[2:] == ("completed", 4)
        assert conn.execute("SELECT count(*) FROM ai_runs WHERE project_id=%s", (project,)).fetchone()[0] == 1
        assert conn.execute("SELECT count(*) FROM ai_run_events WHERE run_id=%s AND status='v2_owned_review'", (run,)).fetchone()[0] == 3
    assert not worker.tick()


@pytest.mark.parametrize("invalid", ["stale", "wrong_scope", "checkpoint", "unknown", "reject"])
def test_invalid_decision_never_continues(db, checkpoint_db, invalid):
    scope, project, run, factory, jobs, worker, provider, search, bodies, _ = make(db, checkpoint_db)
    assert worker.tick()
    reviews = factory.reviews()
    packet = reviews.read(scope=scope, project_id=project, run_id=run)
    if invalid == "reject":
        assert decide(reviews, scope, project, run, packet, decision="reject") == run
        assert not worker.tick()
        return
    overrides = {}
    if invalid == "stale":
        overrides["expected_version"] = packet["review"]["run_version"] - 1
    elif invalid == "wrong_scope":
        overrides["project_id"] = "not-owned"
    elif invalid == "unknown":
        with psycopg.connect(db.migrator_dsn) as conn:
            conn.execute("UPDATE ai_provider_attempts SET status='reconciliation_required' WHERE run_id=%s", (run,))
    else:
        from app.agent_workflows.runtime import PostgresSaver
        from langgraph.checkpoint.base import empty_checkpoint
        with psycopg.connect(checkpoint_db.migrator_dsn, autocommit=True) as conn:
            saver = PostgresSaver(conn)
            config = {"configurable": {"thread_id": packet["review"]["thread_id"], "checkpoint_ns": "planning-v2-execution-v1"}}
            item = saver.get_tuple(config)
            checkpoint = empty_checkpoint()
            checkpoint["channel_versions"] = {"state": 99}
            checkpoint["channel_values"] = deepcopy(item.checkpoint["channel_values"])
            value = checkpoint["channel_values"]["state"]
            value["state"]["stage"] = "capability_planning"
            value["digest"] = content_hash({k: v for k, v in value.items() if k != "digest"})
            saver.put(item.config, checkpoint, {"source": "update", "step": 99, "parents": {}}, {"state": 99})
    with pytest.raises((ConflictError, ForbiddenError, V2RecoveryBlocked)):
        decide(reviews, scope, project, run, packet, **overrides)
    assert not worker.tick()
    assert len(provider.calls) == 1 and not search.calls and not bodies.calls


def test_purpose_phase_count_and_unknown_purposes_reject_before_invoke(db, checkpoint_db):
    scope, project, run, factory, jobs, worker, provider, search, bodies, _ = make(db, checkpoint_db)
    claim = jobs.claim(project, "purpose-test", 300)
    from app.domain.runs.fencing import PlanningWriteFence
    submission = jobs.read_submission(project, run)
    calls = factory(scope, project, run, manifest=submission["manifest"],
        write_fence=PlanningWriteFence(claim.job_id, run, project, scope.actor_id, claim.lease_token),
        thread_id=PgRunRepository(db.app_dsn).get_run(project_id=project, run_id=run).thread_id,
        guard=lambda: None).calls
    def operation(purpose, step):
        return calls.call(step=step, purpose=purpose, schema="mechanical-test", payload={}, reserved={"total_requests": 1},
            invoke=lambda _: "synthetic", encode=lambda _: ({"kind": "llm", "value": {}}, {}))
    for purpose in ("planning.capability_planning", "research.search", "research.body", "planning.research_reader", "planning.curriculum_composition", "domain.verification", "research.case_inspect", "unknown"):
        with pytest.raises(V2RecoveryBlocked):
            operation(purpose, purpose)
    operation("planning.goal_requirement_analysis", "one")
    with pytest.raises(V2BudgetExceeded):
        operation("planning.goal_requirement_analysis", "two")
    with psycopg.connect(db.migrator_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM ai_provider_attempts WHERE run_id=%s", (run,)).fetchone()[0] == 1
    assert not provider.calls and not search.calls and not bodies.calls


def test_full_worst_reservations_and_each_purpose_limit(db, checkpoint_db):
    """Mechanical ledger boundary, separate from the real-validator pipeline."""
    scope, project, run, factory, jobs, worker, provider, search, bodies, _ = make(db, checkpoint_db)
    reviews = factory.reviews()
    for _ in range(2):
        assert worker.tick()
        packet = reviews.read(scope=scope, project_id=project, run_id=run)
        decide(reviews, scope, project, run, packet)
    claim = jobs.claim(project, "worst-boundary", 300)
    from app.domain.runs.fencing import PlanningWriteFence
    submission = jobs.read_submission(project, run)
    ledger = factory(scope, project, run, manifest=submission["manifest"],
        write_fence=PlanningWriteFence(claim.job_id, run, project, scope.actor_id, claim.lease_token),
        thread_id=PgRunRepository(db.app_dsn).get_run(project_id=project, run_id=run).thread_id,
        guard=lambda: None).calls
    invocations = []
    def operation(purpose, ordinal, reserved):
        def invoke(identity):
            invocations.append(identity)
            # This independent connection proves commit-before-invoke.
            with psycopg.connect(db.migrator_dsn) as conn:
                assert conn.execute("SELECT count(*) FROM ai_run_events WHERE run_id=%s AND attempt_id=%s AND status='v2_reservation'", (run, identity)).fetchone()[0] == 1
            return "mechanical"
        return ledger.call(step=purpose + str(ordinal), purpose=purpose, schema="mechanical-boundary",
            payload={"ordinal": ordinal}, reserved=reserved, invoke=invoke,
            encode=lambda _: ({"kind": "mechanical", "value": {}}, {}))
    groups = (
        ("research.body", 6, {"total_requests": 2, "body_bytes": 65536}),
        ("research.search", 6, {"total_requests": 1, "searches": 1, "cost_micros": 1000}),
        ("planning.research_reader", 6, {"total_requests": 1, "reader_requests": 1, "output_tokens": 1024, "cost_micros": 20000}),
        ("planning.curriculum_composition", 1, {"total_requests": 1, "output_tokens": 4096, "cost_micros": 20000}),
    )
    for purpose, limit, reserved in groups:
        for ordinal in range(limit):
            operation(purpose, ordinal, reserved)
        before = len(invocations)
        with pytest.raises(V2BudgetExceeded):
            operation(purpose, limit, reserved)
        assert len(invocations) == before
    for purpose in ("planning.goal_requirement_analysis", "planning.capability_planning"):
        with pytest.raises(V2BudgetExceeded):
            operation(purpose, 99, {"total_requests": 1})
    usage = ledger.usage()
    assert {k: usage[k] for k in ("total_requests", "output_tokens", "body_bytes", "cost_micros", "searches", "reader_requests")} == {
        "total_requests": 27, "output_tokens": 18432, "body_bytes": 393216,
        "cost_micros": 186000, "searches": 6, "reader_requests": 6,
    }
    assert len(provider.calls) == 2 and len(invocations) == 19
