"""Atomic persistence and fenced claims over the existing ``ai_jobs`` tables."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from typing import Any

import psycopg
from app.agent_workflows.planning_batches import SHORT_GENERATION_VERSION
from app.core.errors import (
    ConflictError,
    ForbiddenError,
    IdempotencyConflictError,
    NotFoundError,
    ValidationAppError,
    VersionConflictError,
)
from app.core.ids import new_id
from app.domain.planning.v2_runtime import V2_EXECUTION_VERSION
from app.domain.runs.fencing import PlanningWriteFence
from app.domain.runs.models import RunRecord
from app.infrastructure.db.plan_repository import to_psycopg_dsn
from app.infrastructure.db.planning_fence import lock_plan_version, lock_planning_write
from app.infrastructure.db.run_repository import _run_from
from app.ports.planning_jobs import JobClaim, PlanningLeaseLostError
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

__all__ = ["PgPlanningJobRepository"]

_FINISH_STATUSES = frozenset({"completed", "failed", "reconciliation_required"})


class PgPlanningJobRepository:
    """Application-role-only repository with actor/project RLS context.

    Legacy allowlist admission remains available for controlled tests. Explicit
    trusted_server admission uses a narrow database claim function; subsequent
    business reads/writes retain actor/project RLS and lease fencing.
    """

    def __init__(self, dsn: str, *, actor_ids: tuple[str, ...] = (), max_attempts: int = 3,
                 admission_mode: str = "allowlist") -> None:
        if admission_mode not in {"allowlist", "trusted_server"} or not 1 <= max_attempts <= 10:
            raise ValidationAppError("Worker admission 参数无效")
        self._dsn = to_psycopg_dsn(dsn)
        self._actor_ids = tuple(dict.fromkeys(a.strip() for a in actor_ids if a.strip()))
        self._max_attempts = max_attempts
        self._admission_mode = admission_mode
        self._lock_connection: psycopg.Connection[Any] | None = None
        self._transaction_connection: psycopg.Connection[Any] | None = None

    def in_transaction(self, connection):
        """Preserve admission configuration while sharing the caller's decision transaction."""
        bound = PgPlanningJobRepository(self._dsn, actor_ids=self._actor_ids,
            max_attempts=self._max_attempts, admission_mode=self._admission_mode)
        bound._transaction_connection = connection
        return bound

    @contextmanager
    def _tx(self, *, actor_id: str, project_id: str = "") -> Iterator[psycopg.Connection[Any]]:
        if self._transaction_connection is not None:
            yield self._transaction_connection
            return
        with psycopg.connect(self._dsn, row_factory=dict_row) as conn:
            conn.execute(
                "SELECT set_config('app.actor_id', %s, true), set_config('app.project_id', %s, true)",
                (actor_id, project_id),
            )
            yield conn

    def cancel_run(self, *, actor_id: str, project_id: str, run_id: str,
                   expected_version: int, idempotency_key: str) -> RunRecord:
        """Fence dispatch, result writes and pending publication atomically.

        Durable dispatch can precede HTTP start; retain possibly-sent Attempts
        for reconciliation rather than promise that the network was aborted.
        """
        if (type(expected_version) is not int or expected_version < 1
                or not isinstance(idempotency_key, str) or not idempotency_key.strip()
                or len(idempotency_key) > 128):
            raise ValidationAppError("取消请求的版本或幂等键无效")
        key_hash = hashlib.sha256(idempotency_key.encode()).hexdigest()
        fingerprint = hashlib.sha256(json.dumps(
            [actor_id, project_id, run_id, expected_version], ensure_ascii=False,
            separators=(",", ":"),
        ).encode()).hexdigest()
        with self._tx(actor_id=actor_id, project_id=project_id) as conn:
            conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))",
                         (f"studyplan:plan-budget:{run_id}",))
            lock_plan_version(conn, project_id, None)
            row = conn.execute(
                """SELECT r.*, j.status AS job_status FROM ai_jobs j
                JOIN ai_runs r USING(run_id) JOIN learning_projects p ON p.project_id=r.project_id
                WHERE r.run_id=%s AND r.project_id=%s AND r.actor_id=%s
                  AND p.owner_actor_id=%s AND p.archived_at IS NULL
                FOR UPDATE OF j,r,p""", (run_id, project_id, actor_id, actor_id),
            ).fetchone()
            if row is None:
                raise NotFoundError("规划运行不存在或不属于当前账户")
            receipt = conn.execute(
                """SELECT detail FROM ai_run_events WHERE run_id=%s
                AND status='cancel_request' AND detail->>'kind'='planning_cancel'
                AND detail->>'key_hash'=%s ORDER BY event_id LIMIT 1""", (run_id, key_hash),
            ).fetchone()
            if receipt is not None:
                detail = receipt["detail"]
                if detail["body_fingerprint"] != fingerprint:
                    raise IdempotencyConflictError("此取消幂等键已用于其他请求内容")
                snapshot = dict(detail["response"])
                for field in ("created_at", "updated_at"):
                    if snapshot.get(field):
                        snapshot[field] = datetime.fromisoformat(snapshot[field])
                return _run_from(snapshot)
            if (row["kind"] != "plan_generate" or row["graph_version"] not in {SHORT_GENERATION_VERSION, V2_EXECUTION_VERSION}
                    or row["status"] not in {"queued", "running"}
                    or row["job_status"] not in {"pending", "running"}):
                raise ConflictError("只能取消当前协议的活动规划；旧运行和待核对记录保留",
                                    reason="planning_cancel_not_active")
            if row["version"] != expected_version:
                raise VersionConflictError(expected_version=expected_version, actual_version=row["version"])
            drafts = conn.execute(
                "SELECT draft_id,status FROM plan_drafts WHERE project_id=%s AND run_id=%s FOR UPDATE",
                (project_id, run_id),
            ).fetchall()
            if any(draft["status"] == "approved" for draft in drafts):
                raise ConflictError("草案已经确认，不能撤销已发布事实", reason="planning_cancel_published")
            possible_dispatch = conn.execute(
                "SELECT 1 FROM ai_provider_attempts WHERE run_id=%s "
                "AND status IN ('dispatched','reconciliation_required') LIMIT 1", (run_id,),
            ).fetchone() is not None
            status = "reconciliation_required" if possible_dispatch else "cancelled"
            next_action = "reconcile" if possible_dispatch else "none"
            cancelled = conn.execute(
                """UPDATE plan_drafts SET status='cancelled',updated_at=clock_timestamp()
                WHERE project_id=%s AND run_id=%s AND status IN ('pending','awaiting_approval')
                RETURNING draft_id""", (project_id, run_id),
            ).fetchall()
            conn.execute("UPDATE ai_jobs SET status=%s,lease_token=NULL,lease_expires_at=NULL WHERE run_id=%s",
                         (status, run_id))
            updated = conn.execute(
                """UPDATE ai_runs SET status=%s,next_action=%s,version=version+1,
                error_class=%s,updated_at=clock_timestamp() WHERE run_id=%s RETURNING *""",
                (status, next_action, "provider_dispatch_unknown" if possible_dispatch else None, run_id),
            ).fetchone()
            assert updated is not None
            snapshot = {key: value.isoformat() if isinstance(value, datetime) else value
                        for key, value in updated.items()}
            conn.execute("INSERT INTO ai_run_events(run_id,status,detail) VALUES (%s,'cancel_request',%s)",
                (run_id, Jsonb(dict(kind="planning_cancel", key_hash=key_hash,
                    body_fingerprint=fingerprint, response=snapshot,
                    cancelled_draft_ids=[draft["draft_id"] for draft in cancelled]))))
            return _run_from(updated)

    def enqueue(self, run: RunRecord, initial: dict[str, object], manifest: dict[str, object]) -> None:
        """Write run, one submission event, and one queue row in one transaction."""
        if run.status.value != "queued":
            raise ValidationAppError("规划任务只能以 queued 状态入队")
        if run.kind != "plan_generate":
            raise ValidationAppError("此提交接口只接受规划生成任务")
        if self._admission_mode == "allowlist" and run.actor_id not in self._actor_ids:
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
            if self._admission_mode == "trusted_server":
                conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                             (f"studyplan:planning-project:{run.project_id}",))
            owner = conn.execute(
                "SELECT owner_actor_id FROM learning_projects WHERE project_id=%s AND archived_at IS NULL",
                (run.project_id,),
            ).fetchone()
            if owner is None or owner["owner_actor_id"] != run.actor_id:
                raise ForbiddenError("无权为此学习空间提交规划")

            if run.graph_version == V2_EXECUTION_VERSION:
                # Share Publication's project decision lock: two initial callers
                # cannot create separate roots before a current Plan exists.
                lock_plan_version(conn, run.project_id, None)

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

            if run.graph_version == V2_EXECUTION_VERSION:
                from app.domain.planning.revisions import V2RevisionContext
                from app.domain.planning.v2_runtime import V2RecoveryBlocked, manifest_intact
                if not manifest_intact(manifest) or initial.get("manifest") != manifest:
                    raise V2RecoveryBlocked("V2 enqueue requires an intact frozen submission")
                context = V2RevisionContext.from_payload(initial.get("v2_revision"))
                if (context is None and manifest["expected_version"] != 0
                        or (context is None) != ("v2_revision_hash" not in manifest)
                        or context is not None and (
                            context.to_payload()["context_hash"] != manifest["v2_revision_hash"]
                            or context.to_payload()["base_revision"] != manifest["expected_version"])):
                    raise V2RecoveryBlocked("V2 enqueue revision context binding rejected")
                lock_plan_version(conn, run.project_id, manifest["expected_version"])
                if context is None and conn.execute(
                        "SELECT 1 FROM ai_runs WHERE actor_id=%s AND project_id=%s "
                        "AND graph_version=%s AND kind='plan_generate' LIMIT 1",
                        (run.actor_id, run.project_id, V2_EXECUTION_VERSION)).fetchone():
                    raise ConflictError("已有规划运行，请先核对原运行结果", reason="v2_initial_run_exists")

            if self._admission_mode == "trusted_server":
                active = conn.execute(
                    "SELECT 1 FROM ai_runs WHERE project_id=%s AND kind='plan_generate' "
                    "AND status IN ('queued','running','reconciliation_required') LIMIT 1",
                    (run.project_id,),
                ).fetchone()
                if active is not None:
                    raise ConflictError("此学习空间已有活动规划任务", reason="planning_project_active")

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
                      AND r.kind IN ('plan_generate','summary_review','prompt_review','assistant_reply')
                      AND (r.kind='plan_generate' OR (r.kind='assistant_reply' AND r.graph_version='assistant-coaching-v1' AND EXISTS(SELECT 1 FROM assistant_turns b WHERE b.run_id=r.run_id AND b.project_id=r.project_id AND b.actor_id=r.actor_id)) OR ((r.kind='summary_review' AND r.graph_version='summary-review-v1'
                        AND EXISTS(SELECT 1 FROM summary_review_bindings b WHERE b.run_id=r.run_id AND b.project_id=r.project_id AND b.actor_id=r.actor_id)
                        OR r.kind='prompt_review' AND r.graph_version='prompt-review-v1'
                        AND EXISTS(SELECT 1 FROM prompt_review_bindings b WHERE b.run_id=r.run_id AND b.project_id=r.project_id AND b.actor_id=r.actor_id))))
                      AND NOT EXISTS(SELECT 1 FROM ai_provider_attempts a WHERE a.run_id=r.run_id
                          AND a.status IN('dispatched','reconciliation_required'))
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

    def claim_next(self, worker_id: str, lease_seconds: int) -> JobClaim | None:
        if self._admission_mode != "trusted_server":
            raise ForbiddenError("Worker 未启用 trusted_server admission")
        if not worker_id.strip() or not 1 <= len(worker_id) <= 128 or not 1 <= lease_seconds <= 3600:
            raise ValidationAppError("Worker claim 参数无效")
        with psycopg.connect(self._dsn, row_factory=dict_row) as conn:
            row = conn.execute(
                "SELECT * FROM public.claim_next_planning_job(%s,%s,%s)",
                (worker_id, lease_seconds, self._max_attempts),
            ).fetchone()
        return JobClaim(**row) if row else None

    def renew(self, claim: JobClaim, lease_seconds: int) -> bool:
        if not 1 <= lease_seconds <= 3600:
            raise ValidationAppError("Worker lease 必须在 1–3600 秒之间")
        with self._tx(actor_id=claim.actor_id, project_id=claim.project_id) as conn:
            if not self._lock_live_claim(conn, claim):
                return False
            cursor = conn.execute(
                """UPDATE ai_jobs SET lease_expires_at=clock_timestamp()+(%s * interval '1 second')
                WHERE job_id=%s AND run_id=%s AND lease_token=%s AND status='running'
                  AND lease_expires_at>clock_timestamp()""",
                (lease_seconds, claim.job_id, claim.run_id, claim.lease_token),
            )
        return cursor.rowcount == 1

    def check_claim(self, claim: JobClaim) -> bool:
        if self._admission_mode == "allowlist" and claim.actor_id not in self._actor_ids:
            return False
        with self._tx(actor_id=claim.actor_id, project_id=claim.project_id) as conn:
            row = conn.execute(
                """SELECT 1 FROM ai_jobs j JOIN ai_runs r USING(run_id)
                JOIN learning_projects p ON p.project_id=r.project_id
                WHERE j.job_id=%s AND j.run_id=%s AND j.lease_token=%s
                  AND j.status='running' AND j.lease_expires_at>clock_timestamp()
                  AND r.status IN ('queued','running') AND r.actor_id=%s AND r.project_id=%s
                  AND p.owner_actor_id=%s AND p.archived_at IS NULL""",
                (claim.job_id, claim.run_id, claim.lease_token, claim.actor_id, claim.project_id, claim.actor_id),
            ).fetchone()
        return row is not None

    def finish(self, claim: JobClaim, status: str) -> bool:
        if status not in _FINISH_STATUSES:
            raise ValidationAppError("未知 Worker job 终态")
        with self._tx(actor_id=claim.actor_id, project_id=claim.project_id) as conn:
            if not self._lock_live_claim(
                conn, claim, allowed_run_statuses=("queued", "running", "waiting_user", "succeeded", "failed", "reconciliation_required")
            ):
                return False
            cursor = conn.execute(
                """UPDATE ai_jobs SET status=%s,lease_expires_at=NULL
                WHERE job_id=%s AND run_id=%s AND lease_token=%s AND status='running'
                  AND lease_expires_at>clock_timestamp()""",
                (status, claim.job_id, claim.run_id, claim.lease_token),
            )
        return cursor.rowcount == 1

    def publish_progress(self, claim: JobClaim, progress: dict[str, object]) -> bool:
        """Append one fenced business-progress event for the claimed run.

        Fencing: the lease token, a live lease, a non-terminal run and the actor
        are all re-checked **in the same transaction** as the insert, so a Worker
        that lost its claim can never write progress for a run it no longer owns.
        The payload carries absolute indices, so replaying the same checkpoint is
        idempotent rather than additive.
        """
        detail = dict(progress)
        detail["kind"] = "run_progress"
        with self._tx(actor_id=claim.actor_id, project_id=claim.project_id) as conn:
            if not self._lock_live_claim(conn, claim):
                return False
            conn.execute(
                "INSERT INTO ai_run_events(run_id,node_name,attempt_id,status,detail) "
                "VALUES (%s,NULL,NULL,'progress',%s)",
                (claim.run_id, Jsonb(detail)),
            )
        return True

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

    def read_generation_authority(self, actor_id, project_id, run_id):
        with self._tx(actor_id=actor_id, project_id=project_id) as conn:
            run=conn.execute('SELECT actor_id,project_id FROM ai_runs WHERE run_id=%s AND project_id=%s AND actor_id=%s',
                             (run_id,project_id,actor_id)).fetchone()
            if run is None:
                raise ConflictError('Frozen Run scope mismatch', reason='planning_submission_invalid')
            submissions=conn.execute("SELECT detail FROM ai_run_events WHERE run_id=%s AND status='submission' "
                                     "AND detail->>'kind'='planning_submission' ORDER BY event_id",(run_id,)).fetchall()
            if len(submissions)!=1:
                raise ConflictError('Independent frozen submission missing', reason='planning_submission_invalid')
            detail=submissions[0]['detail']
            if detail.get('actor_id')!=actor_id or detail.get('project_id')!=project_id:
                raise ConflictError('Frozen submission owner mismatch', reason='planning_submission_invalid')
            rows=conn.execute("SELECT attempt_id,run_id,schema_name,response_payload FROM ai_provider_attempts "
                              "WHERE run_id=%s AND status='succeeded'",(run_id,)).fetchall()
            receipts=[{'run_id':r['run_id'],'attempt_id':r['attempt_id'],'schema_name':r['schema_name'],
                       'payload':r['response_payload']['payload']} for r in rows]
            from app.agent_workflows.known_json_failure import attest_failure, failure_receipt
            from app.ports.llm import LLMFailure
            failed=conn.execute("SELECT attempt_id,run_id,schema_name,response_payload,input_tokens,output_tokens "
                                "FROM ai_provider_attempts WHERE run_id=%s AND status='failed' "
                                "AND error_class='provider_invalid_json'", (run_id,)).fetchall()
            for row in failed:
                if not isinstance(row['response_payload'], dict):
                    continue
                result = LLMFailure(**row['response_payload'])
                if (result.input_tokens, result.output_tokens) != (row['input_tokens'], row['output_tokens']):
                    raise ConflictError('Known failure usage mismatch', reason='planning_submission_invalid')
                receipt = failure_receipt(attest_failure(result, run_id, row['attempt_id']),
                                          run_id, row['attempt_id'], row['schema_name'])
                if receipt is not None:
                    receipts.append(receipt)
            fake=conn.execute("SELECT detail FROM ai_run_events WHERE run_id=%s AND status='generation_result' "
                              "AND detail->>'kind'='fake_generation_result' ORDER BY event_id",(run_id,)).fetchall()
            receipts.extend(r['detail']['receipt'] for r in fake)
            return {'initial':detail['initial'],'receipts':receipts}

    def record_fake_generation_result(self, actor_id, project_id, run_id, receipt, fence=None):
        with self._tx(actor_id=actor_id,project_id=project_id) as conn:
            if fence is not None:
                lock_plan_version(conn,project_id,None)
                lock_planning_write(conn,project_id=project_id,run_id=run_id,fence=fence)
            run=conn.execute('SELECT actor_id FROM ai_runs WHERE run_id=%s AND project_id=%s', (run_id,project_id)).fetchone()
            if run is None or run['actor_id']!=actor_id or receipt.get('run_id')!=run_id:
                raise ConflictError('Fake generation result scope mismatch',reason='planning_submission_invalid')
            conn.execute("INSERT INTO ai_run_events(run_id,node_name,attempt_id,status,detail) "
                         "VALUES (%s,NULL,%s,'generation_result',%s)",
                         (run_id,receipt['attempt_id'],Jsonb({'kind':'fake_generation_result','receipt':receipt})))

    def read_claim_submission(self, claim: JobClaim) -> dict[str, object]:
        """Read only the live claim's submission under its exact RLS scope."""
        with self._tx(actor_id=claim.actor_id, project_id=claim.project_id) as conn:
            if not self._lock_live_claim(conn, claim):
                raise ConflictError("规划租约已失效", reason="planning_claim_stale")
            rows = conn.execute(
                "SELECT detail FROM ai_run_events WHERE run_id=%s AND status='submission' "
                "AND detail->>'kind' IN('planning_submission','summary_review_submission','prompt_review_submission','assistant_reply_submission') ORDER BY event_id", (claim.run_id,),
            ).fetchall()
            run = conn.execute("SELECT kind,graph_version FROM ai_runs WHERE run_id=%s", (claim.run_id,)).fetchone()
        if len(rows) != 1 or not isinstance(rows[0]["detail"], dict):
            raise ConflictError("规划提交事件缺失或存在矛盾版本", reason="planning_submission_ambiguous")
        detail = rows[0]["detail"]
        if detail.get("actor_id") != claim.actor_id or detail.get("project_id") != claim.project_id:
            raise ConflictError("规划提交归属与 Run 不一致", reason="planning_submission_ambiguous")
        expected_kind = {"plan_generate": "planning_submission", "summary_review": "summary_review_submission", "prompt_review": "prompt_review_submission", "assistant_reply": "assistant_reply_submission"}.get(run["kind"] if run else "")
        if expected_kind is None or detail.get("kind") != expected_kind:
            raise ValidationAppError("Worker 提交种类与 Run 不一致")
        return detail

    @staticmethod
    def _lock_live_claim(conn: Any, claim: JobClaim, *,
                         allowed_run_statuses: tuple[str, ...] = ("queued", "running")) -> bool:
        fence = PlanningWriteFence(job_id=claim.job_id, run_id=claim.run_id,
                                   project_id=claim.project_id, actor_id=claim.actor_id,
                                   lease_token=claim.lease_token)
        try:
            lock_planning_write(conn, project_id=claim.project_id, run_id=claim.run_id,
                                fence=fence, allowed_run_statuses=allowed_run_statuses)
        except PlanningLeaseLostError:
            return False
        return True

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
