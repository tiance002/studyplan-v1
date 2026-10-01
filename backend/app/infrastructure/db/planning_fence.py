"""Validate a generation claim under the same transaction as its result write."""

from typing import Any

from app.core.errors import VersionConflictError
from app.domain.runs.fencing import PlanningWriteFence
from app.ports.planning_jobs import PlanningLeaseLostError


def lock_plan_version(conn: Any, project_id: str, expected_version: int | None) -> None:
    conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (f"plan-decision:{project_id}",))
    if expected_version is not None:
        row = conn.execute("SELECT revision FROM plan_revisions "
                           "WHERE project_id=%s AND status='approved'", (project_id,)).fetchone()
        actual = int(row["revision"]) if row else 0
        if actual != expected_version:
            raise VersionConflictError("计划已被其他操作修改，请刷新后重试",
                                       expected_version=expected_version, actual_version=actual)


def lock_planning_write(conn: Any, *, project_id: str, run_id: str, fence: PlanningWriteFence,
                        allowed_run_statuses: tuple[str, ...] = ("queued", "running")) -> None:
    if fence.project_id != project_id or fence.run_id != run_id:
        raise PlanningLeaseLostError("规划提交范围与领取任务不一致")
    conn.execute("SELECT set_config('app.actor_id', %s, true)", (fence.actor_id,))
    locked = conn.execute(
        """SELECT 1 FROM ai_jobs j JOIN ai_runs r USING(run_id)
        JOIN learning_projects p ON p.project_id=r.project_id
        WHERE j.job_id=%s AND j.run_id=%s AND r.project_id=%s AND r.actor_id=%s
          AND p.owner_actor_id=%s
        FOR UPDATE OF j,r,p""",
        (fence.job_id, run_id, project_id, fence.actor_id, fence.actor_id),
    ).fetchone()
    if locked is None:
        raise PlanningLeaseLostError("规划 Worker 的结果提交租约已失效")
    # A blocked row lock can outlive the lease. Recheck in a fresh statement
    # after acquisition, using the wall clock rather than transaction-start now().
    valid = conn.execute(
        """SELECT 1 FROM ai_jobs j JOIN ai_runs r USING(run_id)
        JOIN learning_projects p ON p.project_id=r.project_id
        WHERE j.job_id=%s AND j.run_id=%s AND j.lease_token=%s
          AND j.status='running' AND j.lease_expires_at>clock_timestamp()
          AND r.project_id=%s AND r.actor_id=%s AND r.status=ANY(%s)
          AND p.owner_actor_id=%s AND p.archived_at IS NULL""",
        (fence.job_id, run_id, fence.lease_token, project_id, fence.actor_id,
         list(allowed_run_statuses), fence.actor_id),
    ).fetchone()
    if valid is None:
        raise PlanningLeaseLostError("规划 Worker 的结果提交租约已失效")
