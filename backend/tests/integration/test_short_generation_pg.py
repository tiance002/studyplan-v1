"""New lifecycle and business decisions on an isolated, disposable PostgreSQL DB.

Provider output is deterministic test data; no external model is dispatched.
"""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
from threading import Barrier, Event

import psycopg
import pytest
from app.agent_workflows.graphs import graph_thread_id
from app.agent_workflows.planning_batches import PROTOCOL_VERSION
from app.agent_workflows.runtime import PostgresSaver
from app.application.plan_service import DecisionCommand
from app.core.errors import ConflictError, ForbiddenError, VersionConflictError
from app.domain.enums import AiRunNextAction, AiRunStatus, DraftDecision, PlanDraftStatus
from app.domain.runs.models import RunRecord
from app.domain.workspace.models import AuthContext
from app.infrastructure.checkpointer.planning_executor import PgPlanningExecutor
from app.ports.planning_jobs import PlanningLeaseLostError

from tests.e2e.test_b2v_http_end_to_end import ACTOR_A1, GOAL_A, PROJECT_P1, _container
from tests.e2e.test_b2v_http_end_to_end import db as db
from tests.e2e.test_b2v_http_end_to_end import migrated_db as migrated_db

pytestmark = pytest.mark.postgres
SHORT_VERSION = "b3f2-short-v2"


@pytest.fixture
def service(db):
    with PostgresSaver.from_conn_string(db.migrator_dsn) as saver:
        saver.setup()
    container = _container(db)
    service = container.plan_service
    service._executor = PgPlanningExecutor(db.migrator_dsn, llm=service._llm)
    return service


def scope(project=PROJECT_P1):
    return AuthContext(actor_id=ACTOR_A1, session_id="short-test",
                       issued_at=datetime.now(timezone.utc), learning_project_scope=(project,))


def generated(service):
    run_id = service.submit_generation(scope=scope(), project_id=PROJECT_P1, goal=GOAL_A)
    queued = service.get_run(scope=scope(), project_id=PROJECT_P1, run_id=run_id).run
    assert queued.status == AiRunStatus.QUEUED
    assert len(service._llm.calls) == 0
    claim = service._planning_jobs.claim(PROJECT_P1, "short-test", 30)
    assert claim is not None
    service.execute_generation(PROJECT_P1, run_id,
        guard=lambda: _assert_claim(service, claim), claim=claim)
    assert service._planning_jobs.finish(claim, "completed")
    run = service.get_run(scope=scope(), project_id=PROJECT_P1, run_id=run_id).run
    assert run.status == AiRunStatus.SUCCEEDED
    assert run.next_action == AiRunNextAction.NONE
    assert run.graph_version == SHORT_VERSION
    draft = service.get_draft(scope=scope(), project_id=PROJECT_P1, draft_id=run.result_ref).draft
    return run, draft


def _assert_claim(service, claim):
    assert service._planning_jobs.check_claim(claim)


def decision(service, draft, kind, *, version=0, hash=None, stages=None, key="publish-short"):
    return service.decide(scope=scope(), project_id=PROJECT_P1, draft_id=draft.draft_id,
        command=DecisionCommand(decision=kind, expected_version=version,
            draft_hash=draft.content_hash if hash is None else hash,
            idempotency_key=key, edited_stages=stages))


def checkpoint(service, run):
    with PostgresSaver.from_conn_string(service._executor.dsn) as saver:
        saved = saver.get_tuple({"configurable": {"thread_id": run.thread_id}})
        return deepcopy(saved.checkpoint)


def test_draft_success_has_no_interrupt_and_approval_preserves_run_result(service):
    run, draft = generated(service)
    before = checkpoint(service, run)
    calls = len(service._llm.calls)
    service._executor.finish = lambda **kwargs: pytest.fail("business approval resumed Graph")
    first = decision(service, draft, DraftDecision.APPROVE)
    second = decision(service, draft, DraftDecision.APPROVE)
    assert first.plan.plan_id == second.plan.plan_id
    assert first.created and not second.created
    after = service.get_run(scope=scope(), project_id=PROJECT_P1, run_id=run.run_id).run
    assert after == run
    assert checkpoint(service, run) == before
    assert len(service._llm.calls) == calls


def test_completed_checkpoint_recovery_reads_result_without_redispatch(service):
    run, draft = generated(service)
    calls = len(service._llm.calls)
    submission = service._planning_jobs.read_submission(PROJECT_P1, run.run_id)
    nodes = service._build_nodes(project_id=PROJECT_P1, run_id=run.run_id, goal=GOAL_A)
    recovered = service._executor.execute_or_resume(nodes, submission["initial"], run.thread_id,
                                                     run.graph_version, lambda: None)
    assert recovered.stopped_at is None
    assert recovered.state["draft_ref"] == draft.draft_id
    assert len(service._llm.calls) == calls


def test_legacy_waiting_draft_approval_needs_no_checkpoint_resume(service):
    run_id, _, initial, _ = service._freeze_submission(scope=scope(), project_id=PROJECT_P1, goal=GOAL_A)
    initial["graph_version"] = PROTOCOL_VERSION
    thread = graph_thread_id(run_id=run_id, graph_version=PROTOCOL_VERSION)
    service._runs.create_run(RunRecord(run_id=run_id, actor_id=ACTOR_A1, project_id=PROJECT_P1,
        kind="plan_generate", graph_name="planning", graph_version=PROTOCOL_VERSION,
        status=AiRunStatus.RUNNING, next_action=AiRunNextAction.WAIT, thread_id=thread))
    nodes = service._build_nodes(project_id=PROJECT_P1, run_id=run_id, goal=GOAL_A,
                                  selected_pack=initial["domain_pack"])
    trace = service._executor.execute_or_resume(nodes, initial, thread, PROTOCOL_VERSION, lambda: None)
    assert trace.stopped_at == "await_approval"
    service._update_run(project_id=PROJECT_P1, run_id=run_id, status=AiRunStatus.WAITING_USER,
        next_action=AiRunNextAction.REVIEW_DRAFT, result_ref=trace.state["draft_ref"])
    run = service._runs.get_run(project_id=PROJECT_P1, run_id=run_id)
    before = checkpoint(service, run)
    draft = service.get_draft(scope=scope(), project_id=PROJECT_P1, draft_id=run.result_ref).draft
    calls = len(service._llm.calls)
    service._executor.finish = lambda **kwargs: pytest.fail("legacy business approval resumed Graph")
    result = decision(service, draft, DraftDecision.APPROVE)
    assert result.plan is not None
    assert service._runs.get_run(project_id=PROJECT_P1, run_id=run_id).status == AiRunStatus.SUCCEEDED
    assert checkpoint(service, run) == before
    assert len(service._llm.calls) == calls


@pytest.mark.parametrize("kind", [DraftDecision.EDIT, DraftDecision.CANCEL])
def test_edit_and_cancel_reject_stale_version_and_hash(service, kind):
    _, draft = generated(service)
    kwargs = {"stages": draft.stages} if kind == DraftDecision.EDIT else {}
    with pytest.raises(VersionConflictError):
        decision(service, draft, kind, version=99, **kwargs)
    with pytest.raises(ConflictError):
        decision(service, draft, kind, hash="stale", **kwargs)
    current = service.get_draft(scope=scope(), project_id=PROJECT_P1, draft_id=draft.draft_id).draft
    assert current.status == PlanDraftStatus.AWAITING_APPROVAL
    assert current.content_hash == draft.content_hash


def test_edit_then_stale_cancel_is_rejected_and_valid_cancel_keeps_success(service):
    run, draft = generated(service)
    edited = tuple(replace(s, title=s.title + " edited") for s in draft.stages)
    result = decision(service, draft, DraftDecision.EDIT, stages=edited)
    assert result.draft.content_hash != draft.content_hash
    with pytest.raises(ConflictError):
        decision(service, draft, DraftDecision.CANCEL)
    cancelled = decision(service, result.draft, DraftDecision.CANCEL)
    assert cancelled.draft.status == PlanDraftStatus.CANCELLED
    assert service._runs.get_run(project_id=PROJECT_P1, run_id=run.run_id) == run
    with pytest.raises(ConflictError):
        decision(service, result.draft, DraftDecision.APPROVE)


def test_cross_project_draft_decision_is_forbidden(service):
    _, draft = generated(service)
    with pytest.raises(ForbiddenError):
        service.decide(scope=scope("other"), project_id=PROJECT_P1, draft_id=draft.draft_id,
            command=DecisionCommand(DraftDecision.APPROVE, 0, draft.content_hash, "foreign"))


def test_concurrent_duplicate_approve_returns_same_published_result(service, monkeypatch):
    _, draft = generated(service)
    barrier = Barrier(2)
    publish = service._repo.publish_revision

    def simultaneous_publish(**kwargs):
        barrier.wait(timeout=10)
        return publish(**kwargs)

    monkeypatch.setattr(service._repo, "publish_revision", simultaneous_publish)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(decision, service, draft, DraftDecision.APPROVE) for _ in range(2)]
        outcomes = [f.result(timeout=20) for f in futures]
    assert len({o.plan.plan_id for o in outcomes}) == 1
    assert sorted(o.created for o in outcomes) == [False, True]
    assert len(service._repo.list_revisions(project_id=PROJECT_P1)) == 1


def test_cancel_preflight_cannot_cancel_concurrently_edited_draft(service, monkeypatch):
    _, draft = generated(service)
    cancel_started, resume_cancel = Event(), Event()
    cancel = service._repo.cancel_draft

    def delayed_cancel(**kwargs):
        cancel_started.set()
        assert resume_cancel.wait(timeout=10)
        return cancel(**kwargs)

    monkeypatch.setattr(service._repo, "cancel_draft", delayed_cancel)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(decision, service, draft, DraftDecision.CANCEL)
        assert cancel_started.wait(timeout=10)
        edited = tuple(replace(s, title=s.title + " edited") for s in draft.stages)
        result = decision(service, draft, DraftDecision.EDIT, stages=edited)
        resume_cancel.set()
        with pytest.raises(ConflictError):
            future.result(timeout=20)
    current = service.get_draft(scope=scope(), project_id=PROJECT_P1, draft_id=draft.draft_id).draft
    assert current.status == PlanDraftStatus.AWAITING_APPROVAL
    assert current.content_hash == result.draft.content_hash


def test_generation_cannot_commit_against_changed_submission_base(service):
    _, old_draft = generated(service)
    run_id = service.submit_generation(scope=scope(), project_id=PROJECT_P1, goal=GOAL_A)
    decision(service, old_draft, DraftDecision.APPROVE)
    claim = service._planning_jobs.claim(PROJECT_P1, "base-change", 30)
    assert claim is not None and claim.run_id == run_id
    service.execute_generation(PROJECT_P1, run_id,
        guard=lambda: _assert_claim(service, claim), claim=claim)
    assert service._planning_jobs.finish(claim, "completed")
    run = service._runs.get_run(project_id=PROJECT_P1, run_id=run_id)
    assert run.status == AiRunStatus.FAILED
    assert run.result_ref is None
    assert service._repo.get_current(project_id=PROJECT_P1).revision == 1


@pytest.mark.parametrize("target", ["catalog", "catalog_cancelled", "catalog_archived", "draft", "run"])
def test_lost_claim_between_guard_and_commit_cannot_accept_late_result(service, db, monkeypatch, target):
    run_id = service.submit_generation(scope=scope(), project_id=PROJECT_P1, goal=GOAL_A)
    claim = service._planning_jobs.claim(PROJECT_P1, "fence-test", 30)
    assert claim is not None

    def steal_claim():
        # Only this test's disposable DB; simulate a replacement's claim token.
        with psycopg.connect(db.migrator_dsn) as conn:
            if target == "catalog_cancelled":
                conn.execute("UPDATE ai_runs SET status='cancelled',next_action='none',version=version+1 "
                             "WHERE run_id=%s", (run_id,))
            elif target == "catalog_archived":
                conn.execute("UPDATE learning_projects SET archived_at=clock_timestamp() WHERE project_id=%s",
                             (PROJECT_P1,))
            else:
                conn.execute("UPDATE ai_jobs SET lease_token='replacement-token' WHERE job_id=%s", (claim.job_id,))

    if target.startswith("catalog"):
        original = service._catalog.materialize

        def race(**kwargs):
            steal_claim()
            return original(**kwargs)

        monkeypatch.setattr(service._catalog, "materialize", race)
    elif target == "draft":
        original = service._repo.save_draft

        def race(draft, **kwargs):
            steal_claim()
            return original(draft, **kwargs)

        monkeypatch.setattr(service._repo, "save_draft", race)
    else:
        original = service._runs.update_run

        def race(**kwargs):
            steal_claim()
            return original(**kwargs)

        monkeypatch.setattr(service._runs, "update_run", race)

    # Simulates loss immediately after a successful preflight guard.
    with pytest.raises(PlanningLeaseLostError):
        service.execute_generation(PROJECT_P1, run_id, guard=lambda: None, claim=claim)
    run = service._runs.get_run(project_id=PROJECT_P1, run_id=run_id)
    assert run.status == (AiRunStatus.CANCELLED if target == "catalog_cancelled" else AiRunStatus.RUNNING)
    assert run.result_ref is None
    with psycopg.connect(db.migrator_dsn) as conn:
        count = conn.execute("SELECT count(*) FROM plan_drafts WHERE run_id=%s", (run_id,)).fetchone()[0]
    assert count == (1 if target == "run" else 0)
    if target.startswith("catalog"):
        with psycopg.connect(db.migrator_dsn) as conn:
            assert conn.execute("SELECT count(*) FROM knowledge_nodes").fetchone()[0] == 0
            assert conn.execute("SELECT count(*) FROM learning_units").fetchone()[0] == 0
            assert conn.execute("SELECT count(*) FROM practice_tasks").fetchone()[0] == 0
    if target == "catalog_archived":
        # Restore only this disposable fixture's project for its next test.
        with psycopg.connect(db.migrator_dsn) as conn:
            conn.execute("UPDATE learning_projects SET archived_at=NULL WHERE project_id=%s", (PROJECT_P1,))


def test_base_change_after_saved_draft_prevents_succeeded_projection(service, monkeypatch):
    _, old_draft = generated(service)
    run_id = service.submit_generation(scope=scope(), project_id=PROJECT_P1, goal=GOAL_A)
    claim = service._planning_jobs.claim(PROJECT_P1, "base-final-race", 30)
    assert claim is not None
    original = service._runs.update_run
    changed = False

    def update_with_base_race(**kwargs):
        nonlocal changed
        if kwargs["run_id"] == run_id and kwargs["status"] == "succeeded" and not changed:
            changed = True
            decision(service, old_draft, DraftDecision.APPROVE)
        return original(**kwargs)

    monkeypatch.setattr(service._runs, "update_run", update_with_base_race)
    service.execute_generation(PROJECT_P1, run_id, guard=lambda: _assert_claim(service, claim), claim=claim)
    run = service._runs.get_run(project_id=PROJECT_P1, run_id=run_id)
    assert changed
    assert run.status == AiRunStatus.FAILED
    assert run.result_ref is None
    assert service._repo.get_current(project_id=PROJECT_P1).revision == 1


def test_approve_cancel_competition_has_one_business_winner(service):
    run, draft = generated(service)
    barrier = Barrier(2)

    def compete(kind):
        barrier.wait(timeout=10)
        try:
            return decision(service, draft, kind)
        except (ConflictError, VersionConflictError):
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(compete, kind) for kind in (DraftDecision.APPROVE, DraftDecision.CANCEL)]
        outcomes = [f.result(timeout=20) for f in futures]
    assert sum(outcome is not None for outcome in outcomes) == 1
    final = service._repo.get_draft(project_id=PROJECT_P1, draft_id=draft.draft_id)
    plan = service._repo.get_current(project_id=PROJECT_P1)
    assert (final.status == PlanDraftStatus.APPROVED) == (plan is not None)
    assert service._runs.get_run(project_id=PROJECT_P1, run_id=run.run_id) == run


def test_crash_after_draft_commit_recovers_one_draft_without_redispatch(service, db, monkeypatch):
    run_id = service.submit_generation(scope=scope(), project_id=PROJECT_P1, goal=GOAL_A)
    first_claim = service._planning_jobs.claim(PROJECT_P1, "before-crash", 30)
    original = service._repo.save_draft

    def crash_after_commit(draft, **kwargs):
        original(draft, **kwargs)
        raise SystemExit("simulated process exit before final checkpoint")

    monkeypatch.setattr(service._repo, "save_draft", crash_after_commit)
    with pytest.raises(SystemExit):
        service.execute_generation(PROJECT_P1, run_id, guard=lambda: None, claim=first_claim)
    calls = len(service._llm.calls)
    with psycopg.connect(db.migrator_dsn) as conn:
        original_draft = conn.execute("SELECT draft_id FROM plan_drafts WHERE run_id=%s", (run_id,)).fetchone()[0]
        conn.execute("UPDATE ai_jobs SET lease_expires_at=clock_timestamp()-interval '1 second' "
                     "WHERE job_id=%s", (first_claim.job_id,))
    monkeypatch.setattr(service._repo, "save_draft", original)
    second_claim = service._planning_jobs.claim(PROJECT_P1, "after-crash", 30)
    assert second_claim is not None and second_claim.lease_token != first_claim.lease_token
    service.execute_generation(PROJECT_P1, run_id, guard=lambda: None, claim=second_claim)
    run = service._runs.get_run(project_id=PROJECT_P1, run_id=run_id)
    assert run.status == AiRunStatus.SUCCEEDED
    assert run.result_ref == original_draft
    assert len(service._llm.calls) == calls
    with psycopg.connect(db.migrator_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM plan_drafts WHERE run_id=%s", (run_id,)).fetchone()[0] == 1
