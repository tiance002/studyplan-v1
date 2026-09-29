"""Atomic persistence and fenced claims over the existing ``ai_jobs`` tables."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import psycopg
from app.core.errors import ConflictError, ForbiddenError, ValidationAppError
from app.core.ids import new_id
from app.domain.runs.models import RunRecord
from app.infrastructure.db.plan_repository import to_psycopg_dsn
from app.ports.planning_jobs import JobClaim
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

__all__ = ["PgPlanningJobRepository"]

_FINISH_STATUSES = frozenset({"completed", "failed", "reconciliation_required"})


class PgPlanningJobRepository:
    """Application-role-only repository with actor/project RLS context.

    ``actor_ids`` is deliberately an explicit local-validation allowlist. It is
    not a cloud open-registration mechanism; the Worker CLI rejects production
    use until an owner-independent, RLS-safe claim path exists.
    """

    def __init__(self, dsn: str, *, actor_ids: tuple[str, ...] = (), max_attempts: int = 3) -> None:
        self._dsn = to_psycopg_dsn(dsn)
        self._actor_ids = tuple(dict.fromkeys(a.strip() for a in actor_ids if a.strip()))
        self._max_attempts = max_attempts
        self._lock_connection: psycopg.Connection[Any] | None = None

    @contextmanager
    def _tx(self, *, actor_id: str, project_id: str = "") -> Iterator[psycopg.Connection[Any]]:
        with psycopg.connect(self._dsn, row_factory=dict_row) as conn:
            conn.execute(
                "SELECT set_config('app.actor_id', %s, true), set_config('app.project_id', %s, true)",
                (actor_id, project_id),
            )
            yield conn

    def enqueue(self, run: RunRecord, initial: dict[str, object], manifest: dict[str, object]) -> None:
        """Write run, one submission event, and one queue row in one transaction."""
        if run.status.value != "queued":
            raise ValidationAppError("规划任务只能以 queued 状态入队")
        if run.actor_id not in self._actor_ids:
            raise ForbiddenError("后台 Worker 尚未配置服务当前账户；请联系部署管理员")
        submission: dict[str, object] = {
            "kind": "planning_submission",
            "actor_id": run.actor_id,
            "project_id": run.project_id,
            "initial": initial,
            "manifest": manifest,
        }
        job_key = f"planning:{run.run_id}"
        with self._tx(actor_id=run.actor_id, project_id=run.project_id) as conn:
            owner = conn.execute(
                "SELECT owner_actor_id FROM learning_projects WHERE project_id=%s",
                (run.project_id,),
            ).fetchone()
            if owner is None or owner["owner_actor_id"] != run.actor_id:
                raise ForbiddenError("无权为此学习空间提交规划")

            # Serialize duplicate enqueue attempts without requiring a new table
            # or relying on a run row that does not exist yet.
            conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (job_key,))
            existing = conn.execute(
                "SELECT run_id FROM ai_runs WHERE run_id=%s AND project_id=%s",
                (run.run_id, run.project_id),
            ).fetchone()
            if existing is not None:
                events = conn.execute(
                    "SELECT detail FROM ai_run_events WHERE run_id=%s AND status='submission' "
                    "AND detail->>'kind'='planning_submission' ORDER BY event_id",
                    (run.run_id,),
                ).fetchall()
                job = conn.execute("SELECT job_key FROM ai_jobs WHERE run_id=%s", (run.run_id,)).fetchone()
                if len(events) == 1 and events[0]["detail"] == submission and job == {"job_key": job_key}:
                    return
                raise ConflictError("同一 Run 已存在但提交内容或队列记录不一致", reason="planning_enqueue_conflict")

            conn.execute(
                """INSERT INTO ai_runs
                (run_id,actor_id,project_id,kind,graph_name,graph_version,status,next_action,
                 thread_id,result_ref,error_class,version)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (run.run_id, run.actor_id, run.project_id, run.kind, run.graph_name,
                 run.graph_version, run.status.value, run.next_action.value,
                 run.thread_id, run.result_ref, run.error_class, run.version),
            )
            self._insert_submission(conn, run.run_id, submission)
            self._insert_job(conn, run.run_id, job_key)

    @staticmethod
    def _insert_submission(conn: psycopg.Connection[Any], run_id: str, detail: dict[str, object]) -> None:
        conn.execute(
            "INSERT INTO ai_run_events(run_id,node_name,attempt_id,status,detail) "
            "VALUES (%s,NULL,NULL,'submission',%s)",
            (run_id, Jsonb(detail)),
        )

    @staticmethod
    def _insert_job(conn: psycopg.Connection[Any], run_id: str, job_key: str) -> None:
        conn.execute(
            "INSERT INTO ai_jobs(job_id,run_id,job_key,status) VALUES (%s,%s,%s,'pending')",
            (new_id("job"), run_id, job_key),
        )

    def list_projects(self, actor_id: str) -> tuple[str, ...]:
        """Read only active projects owned by this configured actor under RLS."""
        if actor_id not in self._actor_ids:
            raise ForbiddenError("Worker actor 不在 PLANNING_WORKER_ACTOR_IDS 范围内")
        with self._tx(actor_id=actor_id) as conn:
            rows = conn.execute(
                "SELECT project_id FROM learning_projects WHERE owner_actor_id=%s "
                "AND archived_at IS NULL ORDER BY project_id",
                (actor_id,),
            ).fetchall()
        return tuple(str(row["project_id"]) for row in rows)

    def claim(self, project_id: str, worker_id: str, lease_seconds: int) -> JobClaim | None:
        if not project_id or not worker_id or lease_seconds < 1:
            raise ValidationAppError("Worker claim 参数无效")
        for actor_id in self._actor_ids:
            with self._tx(actor_id=actor_id, project_id=project_id) as conn:
                owner = conn.execute(
                    "SELECT owner_actor_id FROM learning_projects WHERE project_id=%s AND archived_at IS NULL",
                    (project_id,),
                ).fetchone()
                if owner is None or owner["owner_actor_id"] != actor_id:
                    continue
                row = conn.execute(
                    """SELECT j.job_id,j.run_id,r.actor_id
                    FROM ai_jobs j JOIN ai_runs r ON r.run_id=j.run_id
                    WHERE r.project_id=%s AND r.actor_id=%s AND r.status IN ('queued','running')
                      AND (j.status='pending' OR (j.status='running' AND j.lease_expires_at < now()))
                      AND j.available_at <= now() AND j.attempts < %s
                    ORDER BY j.created_at,j.job_id
                    FOR UPDATE OF j SKIP LOCKED LIMIT 1""",
                    (project_id, actor_id, self._max_attempts),
                ).fetchone()
                if row is None:
                    continue
                token = new_id("lease")
                updated = conn.execute(
                    """UPDATE ai_jobs SET status='running',lease_token=%s,
                    lease_expires_at=now()+(%s * interval '1 second'),worker_id=%s,attempts=attempts+1
                    WHERE job_id=%s RETURNING job_id,run_id""",
                    (token, lease_seconds, worker_id, row["job_id"]),
                ).fetchone()
                changed = conn.execute(
                    """UPDATE ai_runs SET status='running',next_action='wait',version=version+1,updated_at=now()
                    WHERE run_id=%s AND project_id=%s AND status IN ('queued','running')""",
                    (row["run_id"], project_id),
                )
                if updated is None or changed.rowcount != 1:
                    raise ConflictError("Run 在领取规划任务时已变化", reason="planning_claim_stale")
                return JobClaim(
                    job_id=str(updated["job_id"]), run_id=str(updated["run_id"]),
                    project_id=project_id, actor_id=actor_id, lease_token=token,
                )
        return None

    def renew(self, claim: JobClaim, lease_seconds: int) -> bool:
        if lease_seconds < 1:
            raise ValidationAppError("Worker lease 必须为正数")
        with self._tx(actor_id=claim.actor_id, project_id=claim.project_id) as conn:
            cursor = conn.execute(
                """UPDATE ai_jobs SET lease_expires_at=now()+(%s * interval '1 second')
                WHERE job_id=%s AND run_id=%s AND lease_token=%s AND status='running'
                  AND lease_expires_at > now()""",
                (lease_seconds, claim.job_id, claim.run_id, claim.lease_token),
            )
        return cursor.rowcount == 1

    def check_claim(self, claim: JobClaim) -> bool:
        if claim.actor_id not in self._actor_ids:
            return False
        with self._tx(actor_id=claim.actor_id, project_id=claim.project_id) as conn:
            row = conn.execute(
                """SELECT 1 FROM ai_jobs j JOIN ai_runs r USING(run_id)
                JOIN learning_projects p ON p.project_id=r.project_id
                WHERE j.job_id=%s AND j.run_id=%s AND j.lease_token=%s
                  AND j.status='running' AND j.lease_expires_at>now()
                  AND r.status IN ('queued','running') AND r.actor_id=%s
                  AND p.owner_actor_id=%s AND p.archived_at IS NULL""",
                (claim.job_id, claim.run_id, claim.lease_token, claim.actor_id, claim.actor_id),
            ).fetchone()
        return row is not None

    def finish(self, claim: JobClaim, status: str) -> bool:
        if status not in _FINISH_STATUSES:
            raise ValidationAppError("未知 Worker job 终态")
        with self._tx(actor_id=claim.actor_id, project_id=claim.project_id) as conn:
            cursor = conn.execute(
                """UPDATE ai_jobs SET status=%s,lease_expires_at=NULL
                WHERE job_id=%s AND run_id=%s AND lease_token=%s AND status='running'
                  AND lease_expires_at > now()""",
                (status, claim.job_id, claim.run_id, claim.lease_token),
            )
        return cursor.rowcount == 1

    def read_submission(self, project_id: str, run_id: str) -> dict[str, object]:
        actor_id = ""
        rows: list[dict[str, object]] = []
        for candidate in self._actor_ids:
            with self._tx(actor_id=candidate, project_id=project_id) as conn:
                run = conn.execute(
                    "SELECT actor_id FROM ai_runs WHERE run_id=%s AND project_id=%s",
                    (run_id, project_id),
                ).fetchone()
                if run is None or str(run["actor_id"]) != candidate:
                    continue
                actor_id = candidate
                rows = conn.execute(
                    """SELECT detail FROM ai_run_events WHERE run_id=%s AND status='submission'
                    AND detail->>'kind'='planning_submission' ORDER BY event_id""",
                    (run_id,),
                ).fetchall()
                break
        if not actor_id:
            raise ConflictError("规划提交不存在或不属于当前项目", reason="planning_submission_missing")
        if len(rows) != 1 or not isinstance(rows[0]["detail"], dict):
            raise ConflictError("规划提交事件缺失或存在矛盾版本", reason="planning_submission_ambiguous")
        detail = rows[0]["detail"]
        if detail.get("actor_id") != actor_id or detail.get("project_id") != project_id:
            raise ConflictError("规划提交归属与 Run 不一致", reason="planning_submission_ambiguous")
        return detail

    def acquire_worker_lock(self) -> bool:
        """Hold a PostgreSQL session advisory lock for the life of one Worker."""
        if self._lock_connection is not None:
            return True
        conn = psycopg.connect(self._dsn, autocommit=True)
        lock_row = conn.execute(
            "SELECT pg_try_advisory_lock(hashtextextended('studyplan:planning-worker:v1',0))"
        ).fetchone()
        if lock_row is None or not lock_row[0]:
            conn.close()
            return False
        self._lock_connection = conn
        return True

    def release_worker_lock(self) -> None:
        conn, self._lock_connection = self._lock_connection, None
        if conn is None:
            return
        try:
            conn.execute("SELECT pg_advisory_unlock(hashtextextended('studyplan:planning-worker:v1',0))")
        finally:
            conn.close()
