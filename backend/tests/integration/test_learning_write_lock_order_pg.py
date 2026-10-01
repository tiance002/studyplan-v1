"""Real generation fence and interactive writers share one lock order."""
import threading
from concurrent.futures import ThreadPoolExecutor

import psycopg
import pytest
from app.domain.runs.fencing import PlanningWriteFence
from app.infrastructure.db import learning_exposures, learning_resources
from app.infrastructure.db.learning_exposures import PgLearningExposures
from app.infrastructure.db.learning_resources import PgLearningResources
from app.infrastructure.db.planning_fence import lock_plan_version, lock_planning_write
from psycopg.rows import dict_row

from tests.e2e.test_b2v_http_end_to_end import migrated_db as migrated_db
from tests.integration.test_learning_resources_pg import scenario as scenario

pytestmark = pytest.mark.postgres


@pytest.mark.parametrize("kind", ["resource", "exposure"])
def test_interactive_write_does_not_deadlock_actual_generation_fence(scenario, monkeypatch, kind):
    db, scope, target = scenario
    with psycopg.connect(db.migrator_dsn, row_factory=dict_row) as conn:
        job = conn.execute("SELECT j.* FROM ai_jobs j JOIN ai_runs r USING(run_id) WHERE r.project_id=%s "
                           "ORDER BY j.created_at LIMIT 1",
                           (target["project_id"],)).fetchone()
        conn.execute("UPDATE ai_jobs SET status='running',lease_token='lock-order-test',"
                     "lease_expires_at=clock_timestamp()+interval '30 seconds' WHERE job_id=%s", (job["job_id"],))
    fence = PlanningWriteFence(job["job_id"], job["run_id"], target["project_id"], scope.actor_id, "lock-order-test")
    advisory_held = threading.Event()
    interactive_at_advisory = threading.Event()
    module = learning_resources if kind == "resource" else learning_exposures
    def observed_lock(conn, project_id, expected_version):
        interactive_at_advisory.set()
        lock_plan_version(conn, project_id, expected_version)
    monkeypatch.setattr(module, "lock_plan_version", observed_lock)
    def generation():
        with psycopg.connect(db.app_dsn, row_factory=dict_row) as conn:
            conn.execute("SELECT set_config('app.project_id',%s,true),set_config('app.actor_id',%s,true)",
                         (target["project_id"], scope.actor_id))
            lock_plan_version(conn, target["project_id"], None)
            advisory_held.set()
            assert interactive_at_advisory.wait(5)
            lock_planning_write(conn, project_id=target["project_id"], run_id=job["run_id"],
                                fence=fence, allowed_run_statuses=("succeeded",))
    def interactive():
        assert advisory_held.wait(5)
        adapter = PgLearningResources(db.app_dsn) if kind == "resource" else PgLearningExposures(db.app_dsn)
        context = adapter._connection(scope, target, current=True, lock=True) if kind == "resource" else \
            adapter._connection(scope, target["project_id"], write=True)
        with context:
            pass
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(generation), pool.submit(interactive)]
        for future in futures:
            future.result(timeout=10)
    with psycopg.connect(db.migrator_dsn) as conn:
        conn.execute("UPDATE ai_jobs SET status=%s,lease_token=%s,lease_expires_at=%s WHERE job_id=%s",
                     (job["status"], job["lease_token"], job["lease_expires_at"], job["job_id"]))
