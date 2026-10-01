"""Trusted local worker admission, tested only on a harness-owned database."""

import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from app.core.errors import ConflictError, ForbiddenError, ValidationAppError
from app.domain.enums import AiRunNextAction, AiRunStatus
from app.domain.runs.models import RunRecord
from app.infrastructure.db.browser_auth import PgBrowserAuth
from app.infrastructure.db.job_repository import PgPlanningJobRepository
from app.infrastructure.worker.planning_worker import PlanningWorker

from tests.pg_harness import create_test_database

pytestmark = pytest.mark.postgres


@pytest.fixture(scope="module")
def admission_db():
    db = create_test_database(prefix="studyplan_test_worker_admission")
    try:
        env = dict(os.environ, STUDYPLAN_MIGRATION_DSN=db.migrator_dsn.replace("postgresql://", "postgresql+psycopg://"))
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=Path(__file__).resolve().parents[2], env=env, capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stderr
        yield db
    finally:
        db.drop()


@pytest.fixture()
def fresh(admission_db):
    with psycopg.connect(admission_db.migrator_dsn) as conn:
        conn.execute("TRUNCATE public.ai_jobs, public.ai_runs, public.ai_provider_attempts, public.auth_sessions, public.auth_users, public.auth_throttle, public.learning_projects CASCADE")
    auth = PgBrowserAuth(admission_db.app_dsn, 3600)
    token = auth.register("新学习者", "long passphrase for admission", "new-peer")
    row, projects = auth.detail(token)
    run = RunRecord(
        run_id="admission_run", actor_id=row["actor_id"], project_id=projects[0],
        kind="plan_generate", graph_name="planning", graph_version="b3f2-short-v2",
        status=AiRunStatus.QUEUED, next_action=AiRunNextAction.WAIT,
    )
    repo = PgPlanningJobRepository(admission_db.app_dsn, admission_mode="trusted_server")
    return admission_db, repo, run


def test_fresh_registered_actor_worker_needs_no_whitelist(fresh):
    db, repo, run = fresh
    repo.enqueue(run, {"goal": "learn"}, {})
    executed = []

    def execute(project_id, run_id, *, guard, claim):
        guard()
        assert repo.read_claim_submission(claim)["initial"] == {"goal": "learn"}
        executed.append((project_id, run_id, claim.actor_id))

    worker = PlanningWorker(jobs=repo, execute=execute, actor_ids=(), admission_mode="trusted_server")
    assert worker.tick()
    assert executed == [(run.project_id, run.run_id, run.actor_id)]
    assert not worker.tick()
    with psycopg.connect(db.app_dsn) as conn:
        for table in ("ai_jobs", "ai_runs", "ai_run_events", "learning_projects"):
            assert conn.execute(f"SELECT count(*) FROM public.{table}").fetchone()[0] == 0


def test_claim_function_privileges_and_fixed_search_path(fresh):
    db, _, _ = fresh
    with psycopg.connect(db.migrator_dsn) as conn:
        row = conn.execute("""SELECT p.prosecdef,p.proconfig,pg_catalog.pg_get_userbyid(p.proowner),
            pg_catalog.has_function_privilege('studyplan_app',p.oid,'EXECUTE'),
            EXISTS (SELECT 1 FROM pg_catalog.aclexplode(p.proacl) a WHERE a.grantee=0 AND a.privilege_type='EXECUTE')
            FROM pg_catalog.pg_proc p JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace
            WHERE n.nspname='public' AND p.proname='claim_next_planning_job'""").fetchone()
    assert row == (True, ["search_path=pg_catalog"], "studyplan_migrator", True, False)
    # Built-in non-app role tests inherited PUBLIC privilege without creating,
    # altering or granting any cluster role. SET LOCAL affects this connection.
    with psycopg.connect(db.admin_dsn) as conn:
        conn.execute("SET LOCAL ROLE pg_monitor")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("SELECT * FROM public.claim_next_planning_job('public-test',30,3)")


@pytest.mark.parametrize("worker,lease,attempts", [("", 30, 3), (" " * 128, 30, 3), ("w" * 129, 30, 3), ("w", 0, 3), ("w", 3601, 3), ("w", 30, 0), ("w", 30, 11)])
def test_claim_function_validates_direct_sql_inputs(fresh, worker, lease, attempts):
    db, _, _ = fresh
    with psycopg.connect(db.app_dsn) as conn:
        with pytest.raises(psycopg.errors.InvalidParameterValue):
            conn.execute("SELECT * FROM public.claim_next_planning_job(%s,%s,%s)", (worker, lease, attempts))


@pytest.mark.parametrize("condition", ["archived", "wrongowner", "succeeded", "failed", "cancelled", "waiting_user", "reconciliation_required", "unknown_attempt", "terminal_job", "exhausted"])
def test_unclaimable_jobs_never_dispatch(fresh, condition):
    db, repo, run = fresh
    repo.enqueue(run, {}, {})
    with psycopg.connect(db.migrator_dsn) as conn:
        if condition == "archived":
            conn.execute("UPDATE public.learning_projects SET archived_at=now()")
        elif condition == "wrongowner":
            conn.execute("UPDATE public.learning_projects SET owner_actor_id='different-owner'")
        elif condition == "unknown_attempt":
            conn.execute("INSERT INTO public.ai_provider_attempts(attempt_id,run_id,provider,model_id,status) VALUES ('unknown',%s,'test','test','dispatched')", (run.run_id,))
        elif condition == "terminal_job":
            conn.execute("UPDATE public.ai_jobs SET status='completed'")
        elif condition == "exhausted":
            conn.execute("UPDATE public.ai_jobs SET attempts=3")
        else:
            conn.execute("UPDATE public.ai_runs SET status=%s", (condition,))
    assert repo.claim_next("worker", 30) is None


def test_concurrent_claim_and_stale_or_forged_claim_are_fenced(fresh):
    db, repo, run = fresh
    repo.enqueue(run, {"private": "submission"}, {})
    with ThreadPoolExecutor(max_workers=2) as pool:
        claims = list(pool.map(lambda worker: repo.claim_next(worker, 30), ("one", "two")))
    winners = [claim for claim in claims if claim is not None]
    assert len(winners) == 1
    first = winners[0]
    for bad in (replace(first, lease_token="forged"), replace(first, actor_id="wrong-actor"), replace(first, project_id="wrong-project")):
        assert not repo.check_claim(bad)
        assert not repo.renew(bad, 30)
        assert not repo.finish(bad, "completed")
        assert not repo.publish_progress(bad, {"stage": 99})
        with pytest.raises(ConflictError):
            repo.read_claim_submission(bad)
    with psycopg.connect(db.migrator_dsn) as conn:
        conn.execute("UPDATE public.ai_jobs SET lease_expires_at=now()-interval '1 second'")
    second = repo.claim_next("replacement", 30)
    assert second and second.lease_token != first.lease_token
    assert not repo.check_claim(first)
    assert not repo.renew(first, 30)
    assert not repo.finish(first, "failed")
    with pytest.raises(ConflictError):
        repo.read_claim_submission(first)
    assert repo.read_claim_submission(second)["initial"] == {"private": "submission"}


@pytest.mark.parametrize("status", ["queued", "running", "reconciliation_required"])
def test_active_generation_conflict_preserves_same_run_idempotency(fresh, status):
    db, repo, run = fresh
    repo.enqueue(run, {"goal": "original"}, {})
    with psycopg.connect(db.migrator_dsn) as conn:
        conn.execute("UPDATE public.ai_runs SET status=%s", (status,))
    repo.enqueue(run, {"goal": "original"}, {})
    with pytest.raises(ConflictError):
        repo.enqueue(replace(run, run_id="second-run"), {"goal": "new"}, {})
    with pytest.raises(ConflictError):
        repo.enqueue(run, {"goal": "changed"}, {})
    with psycopg.connect(db.migrator_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM public.ai_jobs").fetchone()[0] == 1


def test_archived_and_spoofed_enqueue_denied_and_legacy_whitelist_retained(fresh):
    db, repo, run = fresh
    legacy = PgPlanningJobRepository(db.app_dsn)
    with pytest.raises(ForbiddenError):
        legacy.enqueue(run, {}, {})
    with pytest.raises(ForbiddenError):
        repo.enqueue(replace(run, actor_id="spoofed"), {}, {})
    with psycopg.connect(db.migrator_dsn) as conn:
        conn.execute("UPDATE public.learning_projects SET archived_at=now()")
    with pytest.raises(ForbiddenError):
        repo.enqueue(run, {}, {})


@pytest.mark.parametrize("mode,attempts", [("typo", 3), ("trusted_server", 0), ("trusted_server", 11)])
def test_repository_rejects_bad_admission_configuration(admission_db, mode, attempts):
    with pytest.raises(ValidationAppError):
        PgPlanningJobRepository(admission_db.app_dsn, admission_mode=mode, max_attempts=attempts)


def test_concurrent_enqueues_admit_only_one_project_generation(fresh):
    db, repo, run = fresh

    def enqueue(run_id):
        try:
            repo.enqueue(replace(run, run_id=run_id), {"goal": run_id}, {})
            return "accepted"
        except ConflictError:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(enqueue, ("race-one", "race-two")))
    assert sorted(outcomes) == ["accepted", "conflict"]
    with psycopg.connect(db.migrator_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM public.ai_runs").fetchone()[0] == 1
        assert conn.execute("SELECT count(*) FROM public.ai_jobs").fetchone()[0] == 1


@pytest.mark.parametrize("operation", ["renew", "finish", "progress", "read"])
def test_claim_waiting_for_row_lock_rechecks_actual_time_after_expiry(fresh, operation):
    db, _, run = fresh
    marker = "lease-wait-" + uuid4().hex
    repo = PgPlanningJobRepository(
        psycopg.conninfo.make_conninfo(db.app_dsn, application_name=marker), admission_mode="trusted_server"
    )
    repo.enqueue(run, {"private": "retained"}, {})
    claim = repo.claim_next("worker", 30)
    assert claim is not None
    with psycopg.connect(db.migrator_dsn) as setup:
        setup.execute("UPDATE public.ai_jobs SET lease_expires_at=clock_timestamp()+interval '3 seconds'")

    def attempt():
        if operation == "renew":
            return repo.renew(claim, 30)
        if operation == "finish":
            return repo.finish(claim, "completed")
        if operation == "progress":
            return repo.publish_progress(claim, {"stage": 99})
        try:
            repo.read_claim_submission(claim)
        except ConflictError:
            return False
        return True

    with psycopg.connect(db.migrator_dsn) as blocker, ThreadPoolExecutor(max_workers=1) as pool:
        blocker.execute("SELECT job_id FROM public.ai_jobs FOR UPDATE")
        pending = pool.submit(attempt)
        try:
            with psycopg.connect(db.admin_dsn, autocommit=True) as observer:
                deadline = time.monotonic() + 5
                while not observer.execute(
                    "SELECT 1 FROM pg_catalog.pg_stat_activity WHERE application_name=%s AND wait_event_type='Lock'",
                    (marker,),
                ).fetchone():
                    assert time.monotonic() < deadline, "operation did not reach the blocked row lock"
                    time.sleep(0.01)
                # Wait to the database's own recorded expiry, not an assumed wall clock.
                observer.execute("SELECT pg_catalog.pg_sleep(GREATEST(0,EXTRACT(EPOCH FROM lease_expires_at-clock_timestamp()))+0.05) FROM public.ai_jobs")
        finally:
            # Release even on assertion failure before the executor waits for its thread.
            blocker.commit()
        assert pending.result(timeout=5) is False
    with psycopg.connect(db.migrator_dsn) as conn:
        assert conn.execute("SELECT status,lease_expires_at < clock_timestamp() FROM public.ai_jobs").fetchone() == ("running", True)
        assert conn.execute("SELECT count(*) FROM public.ai_run_events WHERE status='progress'").fetchone()[0] == 0


@pytest.mark.parametrize("status,allowed", [("succeeded", True), ("failed", True), ("cancelled", False), ("reconciliation_required", False)])
def test_job_finish_accepts_completed_projection_but_never_canceled_or_unknown(fresh, status, allowed):
    db, repo, run = fresh
    repo.enqueue(run, {}, {})
    claim = repo.claim_next("worker", 30)
    assert claim is not None
    with psycopg.connect(db.migrator_dsn) as conn:
        conn.execute("UPDATE public.ai_runs SET status=%s", (status,))
    assert not repo.renew(claim, 30)
    assert not repo.publish_progress(claim, {})
    assert repo.finish(claim, "completed") is allowed
