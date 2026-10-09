"""``RunRepositoryPort`` 的 PostgreSQL 实现（对外运行状态投影 ``ai_runs``）。

## 事务与并发

每次调用一个连接、一个事务；``update_run`` 用 ``version = version + 1``
配合 WHERE version = expected_version 做**乐观并发**并返回新记录。RLS 保证跨项目读写被数据库拒绝。

## 为什么不是业务事实

``ai_runs`` 只回答「跑到哪、下一步做什么、结果在哪」。任何「计划是否已发布」
之类的判断都必须读 ``plan_revisions``，**不得**信任本表。
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import psycopg
from app.agent_workflows.planning_batches import SHORT_GENERATION_VERSION
from app.core.errors import ConflictError, ValidationAppError
from app.domain.enums import AiRunNextAction, AiRunStatus
from app.domain.planning.v2_runtime import V2_EXECUTION_VERSION
from app.domain.runs.fencing import PlanningWriteFence
from app.domain.runs.models import RunRecord
from app.infrastructure.db.plan_repository import to_psycopg_dsn
from app.infrastructure.db.planning_fence import lock_plan_version, lock_planning_write
from psycopg.rows import dict_row

__all__ = ["PgRunRepository"]


def _run_from(row: dict[str, Any]) -> RunRecord:
    return RunRecord(
        run_id=str(row["run_id"]),
        actor_id=str(row["actor_id"]),
        project_id=str(row["project_id"]),
        kind=str(row["kind"]),
        graph_name=str(row.get("graph_name") or ""),
        graph_version=str(row.get("graph_version") or ""),
        status=AiRunStatus(str(row["status"])),
        next_action=AiRunNextAction(str(row.get("next_action") or "none")),
        version=int(row.get("version") or 1),
        thread_id=str(row.get("thread_id") or ""),
        result_ref=(str(row["result_ref"]) if row.get("result_ref") else None),
        error_class=(str(row["error_class"]) if row.get("error_class") else None),
        created_at=row.get("created_at"),  # type: ignore[arg-type]
        updated_at=row.get("updated_at"),  # type: ignore[arg-type]
    )


class PgRunRepository:
    def __init__(self, dsn: str) -> None:
        self._dsn = to_psycopg_dsn(dsn)

    @contextmanager
    def _tx(self, project_id: str) -> Iterator[psycopg.Connection[dict[str, Any]]]:
        with psycopg.connect(
            self._dsn, row_factory=dict_row
        ) as conn:  # type: psycopg.Connection[dict[str, Any]]
            conn.execute("SELECT set_config('app.project_id', %s, true)", (project_id,))
            yield conn

    def create_run(self, run: RunRecord) -> None:
        with self._tx(run.project_id) as conn:
            conn.execute(
                """
                INSERT INTO ai_runs
                    (run_id, actor_id, project_id, kind, graph_name, graph_version,
                     status, next_action, thread_id, result_ref, error_class, version)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    run.run_id,
                    run.actor_id,
                    run.project_id,
                    run.kind,
                    run.graph_name,
                    run.graph_version,
                    run.status.value,
                    run.next_action.value,
                    run.thread_id or None,
                    run.result_ref,
                    run.error_class,
                    run.version,
                ),
            )

    def get_run(self, *, project_id: str, run_id: str) -> RunRecord | None:
        with self._tx(project_id) as conn:
            row = conn.execute(
                "SELECT * FROM ai_runs WHERE project_id = %s AND run_id = %s",
                (project_id, run_id),
            ).fetchone()
        return _run_from(row) if row is not None else None

    def get_progress(self, *, project_id: str, run_id: str) -> dict[str, Any] | None:
        """Latest business progress event, corrected by the paid-attempt ledger.

        The event holds only stable business fields (phase, stage index/title,
        completed batch counts, frozen request cap). Request and token totals are
        recomputed from ``ai_provider_attempts`` here, never trusted from the
        event, so a replayed or stale event can never inflate them.

        Missing usage stays ``None`` (never ``0``): ``usage_complete`` tells the
        caller whether the reported subtotal covers every recorded attempt.
        """
        with self._tx(project_id) as conn:
            row = conn.execute(
                """SELECT detail FROM ai_run_events
                WHERE run_id = %s AND status = 'progress' AND detail->>'kind' = 'run_progress'
                ORDER BY event_id DESC LIMIT 1""",
                (run_id,),
            ).fetchone()
            if row is None or not isinstance(row["detail"], dict):
                return None
            progress: dict[str, Any] = dict(row["detail"])
            ledger = conn.execute(
                """SELECT count(*) AS requests,
                          count(*) FILTER (
                              WHERE input_tokens IS NULL OR output_tokens IS NULL
                          ) AS unknown_usage,
                          sum(input_tokens) AS input_tokens,
                          sum(output_tokens) AS output_tokens
                FROM ai_provider_attempts WHERE run_id = %s""",
                (run_id,),
            ).fetchone()
        assert ledger is not None
        requests = int(ledger["requests"] or 0)
        progress["request_count"] = requests
        progress["input_tokens"] = (
            None if ledger["input_tokens"] is None else int(ledger["input_tokens"])
        )
        progress["output_tokens"] = (
            None if ledger["output_tokens"] is None else int(ledger["output_tokens"])
        )
        progress["usage_complete"] = requests > 0 and int(ledger["unknown_usage"] or 0) == 0
        return progress

    def list_runs(self, *, project_id: str, actor_id: str, limit: int) -> tuple[RunRecord, ...]:
        if not 1 <= limit <= 20:
            raise ValidationAppError("运行列表一次最多读取20条")
        with self._tx(project_id) as conn:
            conn.execute("SELECT set_config('app.actor_id', %s, true)", (actor_id,))
            rows = conn.execute(
                """SELECT * FROM ai_runs WHERE project_id=%s AND actor_id=%s
                AND kind='plan_generate' ORDER BY created_at DESC, run_id DESC LIMIT %s""",
                (project_id, actor_id, limit),
            ).fetchall()
        return tuple(_run_from(row) for row in rows)

    def get_clarification(self, *, scope, project_id, run_id):
        from app.infrastructure.db.v2_clarifications import PgV2Clarifications
        return PgV2Clarifications(self._dsn).read(scope=scope, project_id=project_id, run_id=run_id)

    def get_planning_issues(self, *, scope, project_id, run_id):
        from app.infrastructure.db.v2_clarifications import read_planning_issues
        return read_planning_issues(self._dsn, scope=scope, project_id=project_id, run_id=run_id)

    def update_run(
        self,
        *,
        project_id: str,
        run_id: str,
        expected_version: int,
        status: str,
        next_action: str,
        result_ref: str | None = None,
        error_class: str | None = None,
        write_fence: PlanningWriteFence | None = None,
        expected_plan_version: int | None = None,
    ) -> RunRecord:
        with self._tx(project_id) as conn:
            if expected_plan_version is not None:
                lock_plan_version(conn, project_id, None)
                # A user may publish the saved draft before the Worker records
                # completion. Its own atomic publication advances the base
                # revision; that fact must not turn this successful Run failed.
                published_result = None
                if status == "succeeded" and next_action == "none" and result_ref:
                    published_result = conn.execute(
                        """SELECT 1 FROM plan_drafts d JOIN ai_runs r USING(run_id)
                        WHERE d.project_id=%s AND r.project_id=%s AND r.run_id=%s
                          AND d.draft_id=%s AND d.status='approved'
                          AND r.kind='plan_generate' AND r.graph_version=%s
                          AND EXISTS(SELECT 1 FROM plan_publications p
                              WHERE p.project_id=d.project_id AND p.draft_hash=d.content_hash)""",
                        (project_id, project_id, run_id, result_ref, SHORT_GENERATION_VERSION),
                    ).fetchone()
                    if published_result is None and write_fence is not None:
                        from app.infrastructure.db.v2_revisions import published_v2_draft
                        version = conn.execute("SELECT graph_version FROM ai_runs WHERE run_id=%s AND project_id=%s",
                            (run_id, project_id)).fetchone()
                        if version and version["graph_version"] == V2_EXECUTION_VERSION and published_v2_draft(conn,
                                actor_id=write_fence.actor_id, project_id=project_id, run_id=run_id, draft_id=result_ref):
                            published_result = True
                if published_result is None:
                    lock_plan_version(conn, project_id, expected_plan_version)
            if write_fence is not None:
                lock_planning_write(conn, project_id=project_id, run_id=run_id, fence=write_fence)
            cursor = conn.execute(
                """
                UPDATE ai_runs
                SET status = %s,
                    next_action = %s,
                    result_ref = COALESCE(%s, result_ref),
                    error_class = %s,
                    version = version + 1,
                    updated_at = now()
                WHERE project_id = %s AND run_id = %s AND version = %s
                  AND status NOT IN ('succeeded', 'failed', 'cancelled')
                """,
                (status, next_action, result_ref, error_class, project_id, run_id, expected_version),
            )
            if cursor.rowcount != 1:
                raise ConflictError("Run version changed or missing", reason="run_stale")
            row = conn.execute(
                "SELECT * FROM ai_runs WHERE project_id = %s AND run_id = %s",
                (project_id, run_id),
            ).fetchone()
        assert row is not None
        return _run_from(row)
