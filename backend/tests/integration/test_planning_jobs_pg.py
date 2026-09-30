"""Lease and atomicity tests against a disposable ``studyplan_test_*`` database."""

from __future__ import annotations

import multiprocessing
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.postgres

import psycopg  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND_DIR))

from app.core.errors import ForbiddenError  # noqa: E402
from app.domain.enums import AiRunNextAction, AiRunStatus  # noqa: E402
from app.domain.runs.models import RunRecord  # noqa: E402
from app.infrastructure.db.job_repository import PgPlanningJobRepository  # noqa: E402

from tests.pg_harness import PgTestDatabase, create_test_database  # noqa: E402


@pytest.fixture(scope="module")
def jobs_db() -> PgTestDatabase:
    db = create_test_database(prefix="studyplan_test_b3f2_jobs")
    dsn = db.migrator_dsn.replace("postgresql://", "postgresql+psycopg://")
    env = dict(os.environ, STUDYPLAN_MIGRATION_DSN=dsn)
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(BACKEND_DIR), env=env, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    with psycopg.connect(db.migrator_dsn, autocommit=True) as conn:
        conn.execute(
            "INSERT INTO learning_projects(project_id,owner_actor_id,title,goal_statement,stable_key) "
            "VALUES ('jobs_p1','jobs_a1','one','goal','jobs_k1'), ('jobs_p2','jobs_a2','two','goal','jobs_k2')"
        )
    try:
        yield db
    finally:
        db.drop()


def queued_run(run_id: str, project_id: str = "jobs_p1", actor_id: str = "jobs_a1") -> RunRecord:
    return RunRecord(
        run_id=run_id, actor_id=actor_id, project_id=project_id,
        kind="plan_generate", graph_name="planning", graph_version="b3f2-batch-v1",
        status=AiRunStatus.QUEUED, next_action=AiRunNextAction.WAIT,
        thread_id=f"planning:{run_id}",
    )


@pytest.fixture(autouse=True)
def clear_only_disposable_job_database(jobs_db: PgTestDatabase) -> None:
    with psycopg.connect(jobs_db.migrator_dsn, autocommit=True) as conn:
        conn.execute("TRUNCATE ai_jobs, ai_runs CASCADE")


def count_rows(db: PgTestDatabase, table: str, run_id: str) -> int:
    with psycopg.connect(db.migrator_dsn) as conn:
        return conn.execute(f"SELECT count(*) FROM {table} WHERE run_id=%s", (run_id,)).fetchone()[0]


@pytest.mark.parametrize("fault_step", ["_insert_submission", "_insert_job"])
def test_enqueue_is_atomic_and_idempotent(jobs_db: PgTestDatabase, monkeypatch: pytest.MonkeyPatch, fault_step: str) -> None:
    repo = PgPlanningJobRepository(jobs_db.app_dsn, actor_ids=("jobs_a1",))
    run = queued_run("jobs_run_atomic")
    repo.enqueue(run, {"goal": "test"}, {"max_requests": 19})
    repo.enqueue(run, {"goal": "test"}, {"max_requests": 19})
    assert count_rows(jobs_db, "ai_runs", run.run_id) == 1
    assert count_rows(jobs_db, "ai_jobs", run.run_id) == 1
    assert count_rows(jobs_db, "ai_run_events", run.run_id) == 1

    failed = queued_run("jobs_run_rollback")
    repo2 = PgPlanningJobRepository(jobs_db.app_dsn, actor_ids=("jobs_a1",))
    monkeypatch.setattr(repo2, fault_step, lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("injected")))
    with pytest.raises(RuntimeError, match="injected"):
        repo2.enqueue(failed, {"goal": "test"}, {"max_requests": 19})
    assert count_rows(jobs_db, "ai_runs", failed.run_id) == 0
    assert count_rows(jobs_db, "ai_jobs", failed.run_id) == 0
    assert count_rows(jobs_db, "ai_run_events", failed.run_id) == 0


def test_claim_fences_stale_lease_and_rechecks_project_owner(jobs_db: PgTestDatabase) -> None:
    repo = PgPlanningJobRepository(jobs_db.app_dsn, actor_ids=("jobs_a1", "jobs_a2"))
    run = queued_run("jobs_run_lease")
    repo.enqueue(run, {"goal": "test"}, {"max_requests": 19})
    first = repo.claim("jobs_p1", "worker-one", lease_seconds=30)
    assert first is not None and first.actor_id == "jobs_a1"
    competitor = PgPlanningJobRepository(jobs_db.app_dsn, actor_ids=("jobs_a1", "jobs_a2"))
    assert competitor.claim("jobs_p1", "worker-two", lease_seconds=30) is None
    with psycopg.connect(jobs_db.migrator_dsn, autocommit=True) as conn:
        conn.execute("UPDATE ai_jobs SET lease_expires_at=now()-interval '1 second' WHERE run_id=%s", (run.run_id,))
    assert not repo.renew(first, lease_seconds=30)
    assert not repo.finish(first, "completed")
    second = repo.claim("jobs_p1", "worker-two", lease_seconds=30)
    assert second is not None and second.lease_token != first.lease_token
    assert repo.renew(first, lease_seconds=30) is False
    assert repo.finish(first, "failed") is False
    assert repo.finish(second, "completed") is True
    assert repo.claim("jobs_p2", "worker-two", lease_seconds=30) is None


def test_actor_project_listing_and_process_lock_are_scoped(jobs_db: PgTestDatabase) -> None:
    owner = PgPlanningJobRepository(jobs_db.app_dsn, actor_ids=("jobs_a1",))
    other = PgPlanningJobRepository(jobs_db.app_dsn, actor_ids=("jobs_a2",))
    run = queued_run("jobs_run_scope")
    owner.enqueue(run, {"goal": "private"}, {"max_requests": 19})
    assert owner.list_projects("jobs_a1") == ("jobs_p1",)
    assert other.list_projects("jobs_a2") == ("jobs_p2",)
    assert other.claim("jobs_p1", "wrong-actor", lease_seconds=30) is None
    with pytest.raises(ForbiddenError, match="actor"):
        other.list_projects("jobs_a1")
    with psycopg.connect(jobs_db.app_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM ai_jobs").fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM ai_runs").fetchone()[0] == 0

    assert owner.acquire_worker_lock() is True
    assert other.acquire_worker_lock() is False
    owner.release_worker_lock()
    assert other.acquire_worker_lock() is True
    other.release_worker_lock()


def _blocking_worker_process(dsn, sentinel):
    from threading import Event

    from app.infrastructure.worker.planning_worker import PlanningWorker

    repo = PgPlanningJobRepository(dsn, actor_ids=("jobs_a1",))

    def execute(project_id, run_id, *, guard, claim=None):
        guard()
        sentinel.put(run_id)
        Event().wait(30)

    PlanningWorker(jobs=repo, execute=execute, actor_ids=("jobs_a1",), lease_seconds=3).run()


def test_killed_worker_releases_process_lock_and_expired_claim(jobs_db: PgTestDatabase) -> None:
    repo = PgPlanningJobRepository(jobs_db.app_dsn, actor_ids=("jobs_a1",))
    run = queued_run("jobs_run_killed")
    repo.enqueue(run, {"goal": "test"}, {})
    context = multiprocessing.get_context("spawn")
    sentinel = context.Queue()
    process = context.Process(target=_blocking_worker_process, args=(jobs_db.app_dsn, sentinel))
    process.start()
    try:
        assert sentinel.get(timeout=15) == run.run_id
        assert repo.acquire_worker_lock() is False
        process.kill()
        process.join(timeout=10)
        assert not process.is_alive()
        deadline = time.monotonic() + 5
        while not repo.acquire_worker_lock() and time.monotonic() < deadline:
            time.sleep(0.05)
        assert repo.acquire_worker_lock()
        with psycopg.connect(jobs_db.migrator_dsn, autocommit=True) as conn:
            conn.execute("UPDATE ai_jobs SET lease_expires_at=now()-interval '1 second' WHERE run_id=%s", (run.run_id,))
        recovered = repo.claim("jobs_p1", "replacement", lease_seconds=30)
        assert recovered is not None and recovered.run_id == run.run_id
    finally:
        if process.is_alive():
            process.kill()
            process.join(timeout=10)
        repo.release_worker_lock()
        sentinel.close()


@pytest.mark.parametrize("status", ["failed", "waiting_user", "reconciliation_required", "succeeded", "cancelled"])
def test_finished_or_unknown_runs_are_never_claimed(jobs_db, status):
    repo = PgPlanningJobRepository(jobs_db.app_dsn, actor_ids=("jobs_a1",))
    run = queued_run("jobs_run_ineligible")
    repo.enqueue(run, {"goal": "test"}, {})
    with psycopg.connect(jobs_db.migrator_dsn) as conn:
        conn.execute("UPDATE ai_runs SET status=%s WHERE run_id=%s", (status, run.run_id))
    assert repo.claim("jobs_p1", "worker", 30) is None


def test_spoofed_owner_and_conflicting_submission_are_rejected(jobs_db):
    from app.core.errors import ConflictError

    repo = PgPlanningJobRepository(jobs_db.app_dsn, actor_ids=("jobs_a1", "jobs_a2"))
    with pytest.raises(ForbiddenError):
        repo.enqueue(queued_run("jobs_spoof", actor_id="jobs_a2"), {}, {})
    assert count_rows(jobs_db, "ai_runs", "jobs_spoof") == 0
    run = queued_run("jobs_submission")
    repo.enqueue(run, {"goal": "original"}, {})
    with pytest.raises(ConflictError):
        repo.enqueue(run, {"goal": "different"}, {})
    assert repo.read_submission("jobs_p1", run.run_id)["initial"] == {"goal": "original"}
    with psycopg.connect(jobs_db.migrator_dsn) as conn:
        conn.execute("INSERT INTO ai_run_events(run_id,status,detail) SELECT run_id,status,detail FROM ai_run_events WHERE run_id=%s", (run.run_id,))
    with pytest.raises(ConflictError):
        repo.read_submission("jobs_p1", run.run_id)
