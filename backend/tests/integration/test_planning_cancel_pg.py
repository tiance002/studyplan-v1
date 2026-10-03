"""Owned PostgreSQL cancellation lifecycle; no real provider calls."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Event

import psycopg
import pytest
from app.agent_workflows.planning_batches import SHORT_GENERATION_VERSION
from app.application.plan_service import _ScopedLLM
from app.core.errors import AppError
from app.domain.enums import AiRunNextAction, AiRunStatus
from app.infrastructure.db.job_repository import PgPlanningJobRepository
from app.infrastructure.db.run_repository import PgRunRepository
from app.ports.llm import LLMResult
from app.ports.planning_jobs import PlanningLeaseLostError

from tests.integration.test_planning_dispatch_fence_pg import RecordingProvider, call, scenario
from tests.integration.test_planning_jobs_pg import jobs_db as jobs_db
from tests.integration.test_planning_jobs_pg import queued_run

pytestmark = pytest.mark.postgres


@pytest.fixture(autouse=True)
def clear_owned_cancel_database(jobs_db):
    with psycopg.connect(jobs_db.migrator_dsn, autocommit=True) as conn:
        conn.execute("TRUNCATE ai_provider_attempts, ai_jobs, ai_runs, plan_drafts CASCADE")


def setup_run(db, *, running=False, graph_version=SHORT_GENERATION_VERSION):
    jobs = PgPlanningJobRepository(db.app_dsn, actor_ids=("jobs_a1",))
    run = replace(queued_run("cancel_run"), graph_version=graph_version)
    jobs.enqueue(run, {"goal": "synthetic"}, {"max_requests": 19})
    claim = jobs.claim("jobs_p1", "cancel_worker", 30) if running else None
    return jobs, claim, PgRunRepository(db.app_dsn).get_run(project_id="jobs_p1", run_id=run.run_id)


def cancel(jobs, run, **overrides):
    args = dict(actor_id="jobs_a1", project_id="jobs_p1", run_id=run.run_id,
                expected_version=run.version, idempotency_key="cancel_request_1")
    return jobs.cancel_run(**{**args, **overrides})


@pytest.mark.parametrize("running", [False, True])
def test_cancel_invalidates_job_and_is_idempotent(jobs_db, running):
    jobs, claim, run = setup_run(jobs_db, running=running)
    result = cancel(jobs, run)
    assert result.status == AiRunStatus.CANCELLED and result.next_action == AiRunNextAction.NONE
    assert result.version == run.version + 1
    assert cancel(jobs, run) == result  # same request replays even with original CAS
    assert jobs.claim("jobs_p1", "late_worker", 30) is None
    if claim:
        assert not jobs.check_claim(claim)
        assert not jobs.renew(claim, 30)
        assert not jobs.finish(claim, "completed")
    with psycopg.connect(jobs_db.migrator_dsn) as conn:
        assert conn.execute("SELECT status,lease_token FROM ai_jobs WHERE run_id=%s", (run.run_id,)).fetchone() == ("cancelled", None)
        assert conn.execute("SELECT count(*) FROM ai_run_events WHERE run_id=%s AND status='cancel_request'", (run.run_id,)).fetchone()[0] == 1


@pytest.mark.parametrize("attempt_status", ["dispatched", "reconciliation_required", "succeeded"])
def test_cancel_retains_attempt_and_marks_possible_dispatch_unknown(jobs_db, attempt_status):
    jobs, claim, run = setup_run(jobs_db, running=True)
    with psycopg.connect(jobs_db.migrator_dsn, autocommit=True) as conn:
        conn.execute("INSERT INTO ai_provider_attempts(attempt_id,run_id,provider,model_id,prompt_version,status) VALUES ('cancel_attempt',%s,'fake','fake','test',%s)", (run.run_id, attempt_status))
    result = cancel(jobs, run)
    unknown = attempt_status in {"dispatched", "reconciliation_required"}
    assert result.status == (AiRunStatus.RECONCILIATION_REQUIRED if unknown else AiRunStatus.CANCELLED)
    assert result.next_action == (AiRunNextAction.RECONCILE if unknown else AiRunNextAction.NONE)
    assert not jobs.check_claim(claim)
    with psycopg.connect(jobs_db.migrator_dsn) as conn:
        assert conn.execute("SELECT status FROM ai_provider_attempts WHERE attempt_id='cancel_attempt'").fetchone()[0] == attempt_status


@pytest.mark.parametrize("overrides", [
    {"actor_id": "jobs_a2"}, {"project_id": "jobs_p2"}, {"expected_version": 99},
])
def test_foreign_and_stale_cancel_does_not_mutate(jobs_db, overrides):
    jobs, _, run = setup_run(jobs_db)
    with pytest.raises(AppError):
        cancel(jobs, run, **overrides)
    assert PgRunRepository(jobs_db.app_dsn).get_run(project_id="jobs_p1", run_id=run.run_id) == run


def test_changed_idempotent_body_conflicts(jobs_db):
    jobs, _, run = setup_run(jobs_db)
    cancel(jobs, run)
    with pytest.raises(AppError) as err:
        cancel(jobs, run, expected_version=run.version + 1)
    assert err.value.code.value == "idempotency_conflict"


@pytest.mark.parametrize("status,next_action", [
    ("succeeded", "none"), ("failed", "none"), ("cancelled", "none"),
    ("waiting_user", "review_draft"), ("reconciliation_required", "reconcile"),
])
def test_nonactive_runs_are_not_cancelled_or_replayed(jobs_db, status, next_action):
    jobs, _, run = setup_run(jobs_db)
    with psycopg.connect(jobs_db.migrator_dsn, autocommit=True) as conn:
        conn.execute("UPDATE ai_runs SET status=%s,next_action=%s WHERE run_id=%s", (status, next_action, run.run_id))
    with pytest.raises(AppError):
        cancel(jobs, run)


def test_old_protocol_is_not_consumed(jobs_db):
    jobs, _, run = setup_run(jobs_db, graph_version="b3f2-batch-v1")
    with pytest.raises(AppError):
        cancel(jobs, run)


@pytest.mark.parametrize("draft_status", ["pending", "approved"])
def test_saved_draft_cancel_is_atomic_and_preserves_payload(jobs_db, draft_status):
    jobs, claim, run = setup_run(jobs_db, running=True)
    with psycopg.connect(jobs_db.migrator_dsn, autocommit=True) as conn:
        conn.execute("INSERT INTO plan_drafts(draft_id,project_id,run_id,status,content_hash,payload) VALUES ('saved_cancel_draft','jobs_p1',%s,%s,'immutable_hash','{\"kept\":true}'::jsonb)", (run.run_id, draft_status))
    if draft_status == "approved":
        with pytest.raises(AppError):
            cancel(jobs, run)
        assert jobs.check_claim(claim)  # published business fact wins, no undo
    else:
        cancel(jobs, run)
        assert not jobs.check_claim(claim)
    with psycopg.connect(jobs_db.migrator_dsn) as conn:
        assert conn.execute("SELECT status,content_hash,payload FROM plan_drafts WHERE draft_id='saved_cancel_draft'").fetchone() == ("approved" if draft_status == "approved" else "cancelled", "immutable_hash", {"kept": True})


def test_actual_cancel_between_guard_and_ledger_prevents_dispatch(jobs_db):
    jobs, run, fence, provider, ledger = scenario(jobs_db)
    current = PgRunRepository(jobs_db.app_dsn).get_run(project_id=run.project_id, run_id=run.run_id)
    scoped = _ScopedLLM(ledger, run.project_id, lambda: cancel(jobs, current), write_fence=fence)
    with pytest.raises(PlanningLeaseLostError):
        call(scoped, run)
    assert provider.calls == 0
    with psycopg.connect(jobs_db.migrator_dsn) as conn:
        assert conn.execute('SELECT count(*) FROM ai_provider_attempts').fetchone()[0] == 0


def test_actual_dispatch_then_cancel_retains_late_result_and_reconciliation(jobs_db):
    dispatched, release = Event(), Event()

    def block_sent_provider():
        dispatched.set()
        assert release.wait(20)

    provider = RecordingProvider(on_dispatch=block_sent_provider)
    jobs, run, fence, _, ledger = scenario(jobs_db, provider=provider)
    with ThreadPoolExecutor(max_workers=1) as pool:
        result = pool.submit(call, ledger, run, fence)
        try:
            assert dispatched.wait(20)
            current = PgRunRepository(jobs_db.app_dsn).get_run(project_id=run.project_id, run_id=run.run_id)
            stopped = cancel(jobs, current)
            assert stopped.status == AiRunStatus.RECONCILIATION_REQUIRED
        finally:
            release.set()
        assert isinstance(result.result(timeout=20), LLMResult)
    assert provider.calls == 1
    latest = PgRunRepository(jobs_db.app_dsn).get_run(project_id=run.project_id, run_id=run.run_id)
    assert latest.status == AiRunStatus.RECONCILIATION_REQUIRED and latest.version == stopped.version
    with psycopg.connect(jobs_db.migrator_dsn) as conn:
        assert conn.execute('SELECT status FROM ai_provider_attempts WHERE run_id=%s', (run.run_id,)).fetchone()[0] == 'succeeded'
