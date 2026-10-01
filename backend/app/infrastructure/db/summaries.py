"""One transaction per immutable save/admission/result; exact owner RLS."""
import base64
import json
from contextlib import contextmanager
from datetime import datetime

import psycopg
from app.core.errors import (
    ConflictError,
    ForbiddenError,
    IdempotencyConflictError,
    NotFoundError,
    ValidationAppError,
    VersionConflictError,
)
from app.core.ids import content_hash, new_id
from app.domain.runs.fencing import PlanningWriteFence
from app.domain.summaries import SUMMARY_PROTOCOL, summary_manifest_intact
from app.infrastructure.db.learning_exposures import PgLearningExposures, _json
from app.infrastructure.db.plan_repository import to_psycopg_dsn
from app.infrastructure.db.planning_fence import lock_plan_version, lock_planning_write
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


class PgSummaries:
    def __init__(self, dsn):
        self.dsn = to_psycopg_dsn(dsn)

    @contextmanager
    def _tx(self, scope, project_id, *, write=False, fenced=False):
        scope.require_project(project_id)
        with psycopg.connect(self.dsn, row_factory=dict_row) as conn:
            conn.execute("SELECT set_config('app.actor_id',%s,true),set_config('app.project_id',%s,true)",
                         (scope.actor_id, project_id))
            if write:
                lock_plan_version(conn, project_id, None)
            if not conn.execute("SELECT 1 FROM learning_projects WHERE project_id=%s AND owner_actor_id=%s "
                "AND archived_at IS NULL" + (" FOR UPDATE" if write and not fenced else ""), (project_id, scope.actor_id)).fetchone():
                raise ForbiddenError()
            yield conn

    @staticmethod
    def _receipt(conn, scope, project, key, action, fingerprint):
        row = conn.execute("SELECT * FROM summary_receipts WHERE project_id=%s AND actor_id=%s AND idempotency_key=%s",
                           (project, scope.actor_id, key)).fetchone()
        if row:
            if row["action"] != action or row["input_hash"] != fingerprint:
                raise IdempotencyConflictError()
            return row["response_snapshot"]
        return None

    @staticmethod
    def _record(conn, scope, project, key, action, fingerprint, response):
        conn.execute("INSERT INTO summary_receipts(receipt_id,project_id,actor_id,idempotency_key,action,input_hash,response_snapshot) "
                     "VALUES(%s,%s,%s,%s,%s,%s,%s)",
                     (new_id("sumrcpt"), project, scope.actor_id, key, action, fingerprint, Jsonb(_json(response))))

    @staticmethod
    def _attempt(conn, project, attempt_id):
        row = conn.execute("SELECT * FROM summary_attempts WHERE project_id=%s AND attempt_id=%s",
                           (project, attempt_id)).fetchone()
        if row is None:
            raise NotFoundError("总结修订不存在")
        binding = conn.execute("SELECT b.run_id,r.status FROM summary_review_bindings b JOIN ai_runs r USING(run_id) "
                               "WHERE b.project_id=%s AND b.attempt_id=%s", (project, attempt_id)).fetchone()
        review = conn.execute("SELECT * FROM summary_reviews WHERE project_id=%s AND attempt_id=%s",
                              (project, attempt_id)).fetchone()
        snapshot = row["rubric_snapshot"] or {"snapshot_status": "legacy_unfrozen",
            "warning": "此旧总结没有保存当时路线位置与评分依据；未继承当前路线资料。"}
        result = {k: row[k] for k in ("attempt_id", "project_id", "plan_id", "stage_id", "unit_id",
                                       "attempt_no", "version", "content", "created_at")}
        result.update(content_hash=row["content_hash"] or content_hash({"content": row["content"]}),
            rubric_snapshot=snapshot, review=None,
            legacy_review=None, legacy_review_recorded_at=None,
            run_id=binding["run_id"] if binding else row["run_id"], run_status=binding["status"] if binding else None)
        if review:
            from app.domain.summaries import validate_feedback
            raw = review["review"]
            feedback = {k: raw[k] for k in ("conclusion", "covered", "gaps", "misconceptions", "questions") if k in raw} if isinstance(raw, dict) else {}
            if (isinstance(raw, dict) and not validate_feedback(feedback)
                    and type(raw.get("rubric_version")) is int and review["run_id"]):
                result["review"] = dict(feedback, rubric_version=raw["rubric_version"], review_id=review["review_id"], attempt_id=attempt_id,
                                        run_id=review["run_id"], created_at=review["created_at"])
            else:
                result["legacy_review"] = raw if isinstance(raw, dict) else {"retained_content": raw}
                result["legacy_review_recorded_at"] = review["created_at"]
                result["rubric_snapshot"] = dict(snapshot, legacy_review_warning="当时反馈以旧格式保存，未重新推断评审结论。")
        return _json(result)

    def _thread(self, conn, position):
        project, plan_id, stage, unit = position
        PgLearningExposures._plan(conn, project, plan_id)
        PgLearningExposures._position(conn, position)
        unit_row = conn.execute("SELECT objectives FROM learning_units WHERE project_id=%s AND unit_id=%s", (project, unit)).fetchone()
        objectives = unit_row["objectives"] if unit_row else []
        window = conn.execute("""SELECT h.version AS head_version,a.attempt_id FROM
            (SELECT coalesce((SELECT version FROM summary_position_heads WHERE project_id=%s AND plan_id=%s
                AND stage_id=%s AND unit_id=%s),0) AS version) h
            LEFT JOIN LATERAL(SELECT attempt_id FROM summary_attempts WHERE project_id=%s AND plan_id=%s
                AND stage_id=%s AND unit_id=%s ORDER BY version DESC LIMIT 21) a ON true""",
            (*position, *position)).fetchall()
        version = window[0]["head_version"]
        rows = [row for row in window if row["attempt_id"] is not None]
        return {"project_id": project, "plan_id": plan_id, "stage_id": stage, "unit_id": unit,
            "version": version,
            "questions": ["本次学习你理解了什么？", "还有哪些疑问或下一步想尝试的事？",
                          "结合本单元目标，举一个自己的解释或应用例子：" + "；".join(str(x) for x in objectives)],
            "attempts": [self._attempt(conn, project, row["attempt_id"]) for row in reversed(rows[:20])],
            "history_truncated": len(rows) > 20}

    def thread(self, scope, project_id, plan_id, stage_id, unit_id):
        with self._tx(scope, project_id) as conn:
            return self._thread(conn, (project_id, plan_id, stage_id, unit_id))

    def save(self, scope, command):
        with self._tx(scope, command.project_id, write=True) as conn:
            prior = self._receipt(conn, scope, command.project_id, command.idempotency_key, "save", command.input_hash())
            if prior:
                return dict(prior, replayed=True)
            plan = PgLearningExposures._plan(conn, command.project_id, command.plan_id, current=True)
            PgLearningExposures._position(conn, command.position)
            head = conn.execute("SELECT version FROM summary_position_heads WHERE project_id=%s AND plan_id=%s "
                                "AND stage_id=%s AND unit_id=%s", command.position).fetchone()
            version = head["version"] if head else 0
            if version != command.expected_version:
                raise VersionConflictError(actual_version=version, expected_version=command.expected_version)
            unit = conn.execute("SELECT * FROM learning_units WHERE project_id=%s AND unit_id=%s",
                                (command.project_id, command.unit_id)).fetchone()
            nodes, sources = PgLearningExposures._snapshots(conn, command.position, plan)
            frozen = (plan["structure"] or {}).get("resource_snapshots", [])
            sources["published_resource_snapshots"] = [item for item in frozen if item.get("stage_id") == command.stage_id]
            sources["published_metadata_status"] = "frozen" if sources["published_resource_snapshots"] else "legacy_unfrozen"
            stage = conn.execute("SELECT stable_key,title,objective,section_kind,order_index FROM plan_stages "
                                 "WHERE project_id=%s AND plan_id=%s AND stage_id=%s",
                                 command.position[:3]).fetchone()
            snapshot = _json({"snapshot_status": "frozen", "unit_id": command.unit_id,
                "unit_stable_key": unit["stable_key"], "unit_title": unit["title"],
                "rubric_version": unit["rubric_version"], "objectives": unit["objectives"], "rubric": unit["rubric"],
                "plan_id": command.plan_id, "plan_revision": plan["revision"], "stage_id": command.stage_id,
                "plan_snapshot": {"plan_id": command.plan_id, "revision": plan["revision"],
                                  "structure_hash": content_hash(plan["structure"] or {}), "stage": stage},
                "node_snapshot": nodes, "source_snapshot": sources,
                "source_pack_key": plan["source_pack_key"], "source_pack_version": plan["source_pack_version"]})
            count = conn.execute("SELECT coalesce(max(attempt_no),0)+1 AS n FROM summary_attempts WHERE unit_id=%s",
                                 (command.unit_id,)).fetchone()["n"]
            identifier = new_id("sum")
            conn.execute("""INSERT INTO summary_attempts(attempt_id,project_id,unit_id,content,attempt_no,rubric_version,
                plan_id,stage_id,version,content_hash,rubric_snapshot) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (identifier, command.project_id, command.unit_id, command.content, count, unit["rubric_version"],
                 command.plan_id, command.stage_id, version+1, content_hash({"content": command.content}), Jsonb(snapshot)))
            conn.execute("""INSERT INTO summary_position_heads(project_id,plan_id,stage_id,unit_id,version)
                VALUES(%s,%s,%s,%s,%s) ON CONFLICT(project_id,plan_id,stage_id,unit_id) DO UPDATE SET version=excluded.version""",
                (*command.position, version+1))
            result = {"thread": self._thread(conn, command.position), "attempt": self._attempt(conn, command.project_id, identifier),
                      "replayed": False}
            self._record(conn, scope, command.project_id, command.idempotency_key, "save", command.input_hash(), result)
            return result

    def attempt(self, scope, project_id, attempt_id):
        with self._tx(scope, project_id) as conn:
            return self._attempt(conn, project_id, attempt_id)

    def history(self, scope, project_id, cursor=None, limit=20):
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValidationAppError("总结历史分页大小无效")
        boundary = None
        if cursor:
            try:
                if len(cursor) > 1024:
                    raise ValueError()
                body = json.loads(base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)))
                if set(body) != {"project", "time", "id"} or body["project"] != project_id:
                    raise ValueError()
                boundary = (datetime.fromisoformat(body["time"]), body["id"])
                if boundary[0].tzinfo is None or not isinstance(body["id"], str) or not 1 <= len(body["id"]) <= 512:
                    raise ValueError()
            except (ValueError, TypeError, KeyError, UnicodeError):
                raise ValidationAppError("总结历史游标无效") from None
        with self._tx(scope, project_id) as conn:
            rows = conn.execute("SELECT attempt_id,created_at FROM summary_attempts WHERE project_id=%s "
                + ("AND (created_at,attempt_id)<(%s,%s) " if boundary else "")
                + "ORDER BY created_at DESC,attempt_id DESC LIMIT %s",
                (project_id, *boundary, limit+1) if boundary else (project_id, limit+1)).fetchall()
            page = rows[:limit]
            next_cursor = None
            if len(rows) > limit:
                last = page[-1]
                next_cursor = base64.urlsafe_b64encode(json.dumps({"project": project_id,
                    "time": last["created_at"].isoformat(), "id": last["attempt_id"]}).encode()).decode().rstrip("=")
            return {"items": [self._attempt(conn, project_id, row["attempt_id"]) for row in page], "next_cursor": next_cursor}

    @staticmethod
    def _handle(run, attempt_id):
        return {"run_id": run["run_id"], "attempt_id": attempt_id, "status": run["status"],
                "next_action": run["next_action"], "version": run["version"],
                "status_url": f"/api/v1/runs/{run['run_id']}?project_id={run['project_id']}"}

    def review_receipt(self, scope, project_id, attempt_id, key):
        with self._tx(scope, project_id) as conn:
            self._attempt(conn, project_id, attempt_id)
            return self._receipt(conn, scope, project_id, key, "review", content_hash({"attempt_id": attempt_id, "consent_to_model": True}))

    def enqueue_review(self, scope, project_id, attempt_id, key, manifest):
        fingerprint = content_hash({"attempt_id": attempt_id, "consent_to_model": True})
        with self._tx(scope, project_id, write=True) as conn:
            previous = self._receipt(conn, scope, project_id, key, "review", fingerprint)
            if previous:
                return previous
            attempt = self._attempt(conn, project_id, attempt_id)
            binding = conn.execute("SELECT r.* FROM summary_review_bindings b JOIN ai_runs r USING(run_id) "
                "WHERE b.project_id=%s AND b.attempt_id=%s", (project_id, attempt_id)).fetchone()
            if binding:
                result = self._handle(binding, attempt_id)
            else:
                if not summary_manifest_intact(manifest):
                    raise ValidationAppError("总结评审预算或协议无效")
                if attempt["rubric_snapshot"].get("snapshot_status") != "frozen":
                    raise ValidationAppError("旧总结没有当时评分依据，请先保存新的总结修订")
                active = conn.execute("SELECT count(*) AS n FROM ai_runs WHERE project_id=%s AND actor_id=%s "
                    "AND kind='summary_review' AND status IN('queued','running','reconciliation_required')",
                    (project_id, scope.actor_id)).fetchone()["n"]
                if active >= 3:
                    raise ConflictError("当前学习空间最多保留三个待处理总结反馈，请先处理已有任务")
                run_id = new_id("run")
                conn.execute("""INSERT INTO ai_runs(run_id,actor_id,project_id,kind,graph_name,graph_version,status,next_action,thread_id)
                    VALUES(%s,%s,%s,'summary_review','summary_review_graph',%s,'queued','wait',%s)""",
                    (run_id, scope.actor_id, project_id, SUMMARY_PROTOCOL, run_id + "::" + SUMMARY_PROTOCOL))
                conn.execute("INSERT INTO summary_review_bindings(project_id,attempt_id,run_id,actor_id,manifest) VALUES(%s,%s,%s,%s,%s)",
                    (project_id, attempt_id, run_id, scope.actor_id, Jsonb(manifest)))
                submission = {"kind": "summary_review_submission", "actor_id": scope.actor_id,
                              "project_id": project_id, "attempt_id": attempt_id, "manifest": manifest}
                conn.execute("INSERT INTO ai_run_events(run_id,status,detail) VALUES(%s,'submission',%s)", (run_id, Jsonb(submission)))
                conn.execute("INSERT INTO ai_jobs(job_id,run_id,job_key,status) VALUES(%s,%s,%s,'pending')",
                             (new_id("job"), run_id, "summary:" + run_id))
                run = conn.execute("SELECT * FROM ai_runs WHERE run_id=%s", (run_id,)).fetchone()
                result = self._handle(run, attempt_id)
            self._record(conn, scope, project_id, key, "review", fingerprint, result)
            return result

    def has_review_binding(self, scope, project_id, attempt_id):
        with self._tx(scope, project_id) as conn:
            return conn.execute("SELECT 1 FROM summary_review_bindings WHERE project_id=%s AND attempt_id=%s",
                                (project_id, attempt_id)).fetchone() is not None

    def cancel_review(self, scope, project_id, attempt_id, run_id, expected_version, key):
        fingerprint = content_hash({"attempt_id": attempt_id, "run_id": run_id, "expected_version": expected_version})
        with self._tx(scope, project_id, write=True, fenced=True) as conn:
            prior = self._receipt(conn, scope, project_id, key, "cancel", fingerprint)
            if prior:
                return prior
            run = conn.execute("""SELECT r.* FROM ai_runs r JOIN ai_jobs j USING(run_id)
                JOIN summary_review_bindings b USING(run_id) JOIN learning_projects p ON p.project_id=r.project_id
                WHERE r.project_id=%s AND r.actor_id=%s AND r.kind='summary_review'
                    AND b.attempt_id=%s AND b.project_id=%s AND r.run_id=%s
                    AND p.owner_actor_id=%s AND p.archived_at IS NULL FOR UPDATE OF j,r,p""",
                (project_id, scope.actor_id, attempt_id, project_id, run_id, scope.actor_id)).fetchone()
            if not run:
                raise NotFoundError("总结反馈任务不存在")
            if run["version"] != expected_version:
                raise VersionConflictError(actual_version=run["version"], expected_version=expected_version)
            if run["status"] not in {"queued", "running", "cancelled"}:
                raise ConflictError("此总结反馈任务已经结束或需要核对，不能取消")
            if run["status"] != "cancelled":
                run = conn.execute("UPDATE ai_runs SET status='cancelled',next_action='none',version=version+1,updated_at=clock_timestamp() "
                    "WHERE run_id=%s RETURNING *", (run_id,)).fetchone()
                conn.execute("UPDATE ai_jobs SET status='cancelled',lease_token=NULL,lease_expires_at=NULL WHERE run_id=%s", (run_id,))
            result = self._handle(run, attempt_id)
            self._record(conn, scope, project_id, key, "cancel", fingerprint, result)
            return result

    @staticmethod
    def _claim_scope(claim):
        from datetime import UTC

        from app.domain.workspace.models import AuthContext
        return AuthContext(claim.actor_id, "worker-claim", datetime.now(UTC), (claim.project_id,))

    @staticmethod
    def _fence(claim):
        return PlanningWriteFence(job_id=claim.job_id, run_id=claim.run_id, project_id=claim.project_id,
                                  actor_id=claim.actor_id, lease_token=claim.lease_token)

    def review_submission(self, claim):
        with self._tx(self._claim_scope(claim), claim.project_id, write=True, fenced=True) as conn:
            lock_planning_write(conn, project_id=claim.project_id, run_id=claim.run_id, fence=self._fence(claim))
            row = conn.execute("""SELECT b.* FROM summary_review_bindings b JOIN ai_runs r USING(run_id)
                WHERE b.project_id=%s AND b.run_id=%s AND b.actor_id=%s AND r.kind='summary_review'
                AND r.graph_version=%s""", (claim.project_id, claim.run_id, claim.actor_id, SUMMARY_PROTOCOL)).fetchone()
            if row is None or not summary_manifest_intact(row["manifest"]):
                raise ValidationAppError("总结反馈任务提交缺失或预算协议无效")
            return {"attempt": self._attempt(conn, claim.project_id, row["attempt_id"]), "manifest": row["manifest"]}

    def finish_review(self, claim, attempt_id, review=None, *, error_class=None, unknown=False):
        with self._tx(self._claim_scope(claim), claim.project_id, write=True, fenced=True) as conn:
            lock_planning_write(conn, project_id=claim.project_id, run_id=claim.run_id, fence=self._fence(claim))
            binding = conn.execute("SELECT 1 FROM summary_review_bindings b JOIN ai_runs r USING(run_id) WHERE b.project_id=%s "
                "AND b.run_id=%s AND b.attempt_id=%s AND b.actor_id=%s AND r.kind='summary_review' AND r.graph_version=%s",
                (claim.project_id, claim.run_id, attempt_id, claim.actor_id, SUMMARY_PROTOCOL)).fetchone()
            if not binding:
                raise ForbiddenError()
            attempt = self._attempt(conn, claim.project_id, attempt_id)
            identifier = None
            if review is not None:
                from app.domain.summaries import validate_feedback
                if validate_feedback(review):
                    raise ValidationAppError("总结反馈校验失败")
                identifier = new_id("srv")
                body = dict(review, rubric_version=attempt["rubric_snapshot"]["rubric_version"])
                lock_planning_write(conn, project_id=claim.project_id, run_id=claim.run_id, fence=self._fence(claim))
                conn.execute("INSERT INTO summary_reviews(review_id,project_id,attempt_id,review,run_id) VALUES(%s,%s,%s,%s,%s)",
                    (identifier, claim.project_id, attempt_id, Jsonb(body), claim.run_id))
            status = "succeeded" if identifier else ("reconciliation_required" if unknown else "failed")
            action = "reconcile" if unknown else "none"
            conn.execute("UPDATE ai_runs SET status=%s,next_action=%s,result_ref=%s,error_class=%s,version=version+1,updated_at=clock_timestamp() "
                "WHERE run_id=%s", (status, action, identifier, error_class, claim.run_id))
            conn.execute("UPDATE ai_jobs SET status=%s,lease_token=NULL,lease_expires_at=NULL WHERE job_id=%s",
                         ("completed" if identifier else ("reconciliation_required" if unknown else "failed"), claim.job_id))
            return identifier or ""
