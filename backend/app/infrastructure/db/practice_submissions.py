"""Immutable manual work and USER decisions in the existing owner transaction."""

from dataclasses import asdict

from app.core.errors import ConflictError, NotFoundError, VersionConflictError
from app.core.ids import content_hash, new_id
from app.domain.enums import AcceptanceConclusion, PracticeTaskStatus, ReviewerKind
from app.domain.practice.models import AcceptanceReview, PracticeTask
from app.domain.practice_submissions import ARTIFACT_KINDS, OUTCOME_TITLES
from app.infrastructure.db.learning_exposures import PgLearningExposures, _json
from app.infrastructure.db.prompts import PgPrompts
from app.infrastructure.db.summaries import PgSummaries
from psycopg.types.json import Jsonb


class PgPracticeSubmissions(PgSummaries):
    # Fixed receipt/history specialization only; no inherited review/queue method is exposed.
    receipt_table = "submission_receipts"
    original_table = "practice_submissions"
    subject_column = "submission_id"
    subject_label = "成果"

    @staticmethod
    def _context(conn, position, *, lock=False):
        row = conn.execute(
            """SELECT t.* FROM plan_task_links l JOIN practice_tasks t
            ON t.project_id=l.project_id AND t.task_id=l.task_id
            WHERE l.project_id=%s AND l.plan_id=%s AND l.stage_id=%s AND l.task_id=%s"""
            + (" FOR UPDATE OF t" if lock else ""),
            position,
        ).fetchone()
        if row is None:
            raise NotFoundError("任务不属于指定路线和阶段")
        if lock:
            conn.execute(
                "SELECT practice_project_id FROM practice_projects WHERE project_id=%s AND practice_project_id=%s FOR SHARE",
                (position[0], row["practice_project_id"]),
            )
            conn.execute(
                """SELECT n.node_id FROM plan_task_knowledge_links l JOIN knowledge_nodes n
                ON n.project_id=l.project_id AND n.node_id=l.node_id
                WHERE l.project_id=%s AND l.plan_id=%s AND l.task_id=%s ORDER BY n.node_id FOR SHARE OF n,l""",
                (position[0], position[1], position[3]),
            )
        practice, task = PgPrompts._context(conn, position)
        task.update(stable_key=row["stable_key"], version=row["version"])
        return practice, task

    @staticmethod
    def _snapshot(conn, position, plan, practice, task):
        stage = conn.execute(
            "SELECT title FROM plan_stages WHERE project_id=%s AND plan_id=%s AND stage_id=%s", position[:3]
        ).fetchone()
        return _json(
            dict(
                snapshot_status="frozen",
                plan_id=position[1],
                plan_revision=plan["revision"],
                stage_id=position[2],
                stage_title=stage["title"],
                practice_project=practice,
                task=task,
                warning=None,
            )
        )

    @staticmethod
    def _requirements(snapshot):
        # Only workflow status/version may change without invalidating these saved requirements.
        return {
            name: {key: value for key, value in snapshot[name].items() if key not in {"status", "version"}}
            for name in ("practice_project", "task")
        }

    @staticmethod
    def _attempt(conn, project, submission_id):
        row = conn.execute(
            "SELECT * FROM practice_submissions WHERE project_id=%s AND submission_id=%s",
            (project, submission_id),
        ).fetchone()
        if row is None:
            raise NotFoundError("成果提交不存在")
        frozen = bool(row["plan_id"] and row["task_snapshot"].get("snapshot_status") == "frozen")
        snapshot = (
            row["task_snapshot"]
            if frozen
            else dict(
                snapshot_status="legacy_unfrozen",
                plan_id=row["plan_id"],
                plan_revision=None,
                stage_id=row["stage_id"],
                stage_title=None,
                practice_project=None,
                task=None,
                warning="旧成果缺少当时任务和路线快照；原证据等级及反馈仅按历史记录保留，未重新核验或继承当前要求。",
            )
        )
        review = conn.execute(
            "SELECT * FROM acceptance_reviews WHERE project_id=%s AND submission_id=%s",
            (project, submission_id),
        ).fetchone()
        public_review = None
        if review:
            public_review = {
                key: review[key]
                for key in ("review_id", "submission_id", "conclusion", "reviewer_kind", "created_at")
            }
            public_review.update(
                rationale=review["rationale"] or "",
                coverage=review["coverage"] if review["actor_id"] else [],
                acknowledge_verification_limit=review["acknowledge_verification_limit"],
                manual_confirmation=review["reviewer_kind"] == "user",
            )
        result = {
            key: row[key]
            for key in (
                "submission_id",
                "project_id",
                "plan_id",
                "stage_id",
                "task_id",
                "submission_no",
                "version",
                "repo_url",
                "artifact_kind",
                "parent_submission_id",
                "evidence_grade",
                "created_at",
            )
        }
        result.update(
            note=row["note"] or "",
            evidence=row["evidence_details"] if frozen else [],
            legacy_evidence=[] if frozen else row["evidence"],
            task_snapshot=snapshot,
            content_hash=row["content_hash"]
            or content_hash(dict(note=row["note"], evidence=row["evidence"], repo_url=row["repo_url"])),
            verification_available=False,
            source_check_available=False,
            review=public_review,
        )
        return _json(result)

    def _thread(self, conn, position):
        project, plan_id, stage, task_id = position
        PgLearningExposures._plan(conn, project, plan_id)
        practice, task = self._context(conn, position)
        rows = conn.execute(
            """SELECT p.revision AS plan_version,t.version AS task_version,t.status AS task_status,
            h.version AS head_version,a.submission_id FROM plan_revisions p JOIN practice_tasks t ON t.project_id=p.project_id
            CROSS JOIN LATERAL(SELECT coalesce((SELECT version FROM submission_position_heads
                WHERE project_id=%s AND plan_id=%s AND stage_id=%s AND task_id=%s),0) AS version) h
            LEFT JOIN LATERAL(SELECT submission_id FROM practice_submissions WHERE project_id=%s AND plan_id=%s
                AND stage_id=%s AND task_id=%s ORDER BY version DESC LIMIT 21) a ON true
            WHERE p.project_id=%s AND p.plan_id=%s AND t.task_id=%s""",
            (*position, *position, project, plan_id, task_id),
        ).fetchall()
        window = [row for row in rows if row["submission_id"] is not None]
        task.update(version=rows[0]["task_version"], status=rows[0]["task_status"])
        return dict(
            project_id=project,
            plan_id=plan_id,
            stage_id=stage,
            task_id=task_id,
            plan_version=rows[0]["plan_version"],
            version=rows[0]["head_version"],
            task_version=task["version"],
            practice_project=practice,
            task=task,
            submissions=[self._attempt(conn, project, row["submission_id"]) for row in reversed(window[:20])],
            history_truncated=len(window) > 20,
            platform_execution_available=False,
            source_check_available=False,
        )

    def thread(self, scope, project_id, plan_id, stage_id, task_id):
        with self._tx(scope, project_id) as conn:
            return self._thread(conn, (project_id, plan_id, stage_id, task_id))

    def get(self, scope, project_id, submission_id):
        with self._tx(scope, project_id) as conn:
            return self._attempt(conn, project_id, submission_id)

    @staticmethod
    def _head(conn, position):
        row = conn.execute(
            "SELECT version FROM submission_position_heads WHERE project_id=%s AND plan_id=%s AND stage_id=%s AND task_id=%s FOR UPDATE",
            position,
        ).fetchone()
        return row["version"] if row else 0

    @staticmethod
    def _versions(command, plan, task, head):
        if (plan["revision"], task["version"], head) != (
            command.expected_plan_version,
            command.expected_task_version,
            command.expected_version,
        ):
            raise VersionConflictError("路线、任务或成果版本已变化，请读取最新记录后再决定")

    @staticmethod
    def _task_status(conn, project, task, target):
        if task["status"] == "accepted":
            return task["status"], task["version"]
        entity = PracticeTask(
            task_id=task["task_id"],
            practice_project_id="",
            project_id=project,
            stable_key=task["stable_key"],
            title=task["title"],
            goal=task["goal"],
            status=PracticeTaskStatus(task["status"]),
            version=task["version"],
        )
        entity.transition_to(PracticeTaskStatus(target), source=ReviewerKind.USER)
        if entity.version != task["version"]:
            conn.execute(
                "UPDATE practice_tasks SET status=%s,version=%s WHERE project_id=%s AND task_id=%s",
                (entity.status.value, entity.version, project, entity.task_id),
            )
        return entity.status.value, entity.version

    def save(self, scope, command):
        with self._tx(scope, command.project_id, write=True) as conn:
            prior = self._receipt(
                conn, scope, command.project_id, command.idempotency_key, "save", command.input_hash()
            )
            if prior is not None:
                return prior
            plan = PgLearningExposures._plan(conn, command.project_id, command.plan_id, current=True)
            practice, task = self._context(conn, command.position, lock=True)
            head = self._head(conn, command.position)
            self._versions(command, plan, task, head)
            if command.parent_submission_id is not None:
                parent = self._attempt(conn, command.project_id, command.parent_submission_id)
                if (
                    tuple(parent[key] for key in ("project_id", "plan_id", "stage_id", "task_id"))
                    != command.position
                    or parent["version"] > head
                ):
                    raise ConflictError("补充证据只能关联同一保存位置的已有成果")
            identifier = new_id("psb")
            snapshot = self._snapshot(conn, command.position, plan, practice, task)
            conn.execute(
                """INSERT INTO practice_submissions(submission_id,project_id,task_id,note,repo_url,evidence,evidence_grade,
                plan_id,stage_id,actor_id,submission_no,version,content_hash,task_snapshot,evidence_details,artifact_kind,parent_submission_id)
                VALUES(%s,%s,%s,%s,%s,'[]',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    identifier,
                    command.project_id,
                    command.task_id,
                    command.note,
                    command.repo_url,
                    command.grade.value,
                    command.plan_id,
                    command.stage_id,
                    scope.actor_id,
                    head + 1,
                    head + 1,
                    command.original_hash(),
                    Jsonb(snapshot),
                    Jsonb([asdict(item) for item in command.evidence]),
                    command.artifact_kind,
                    command.parent_submission_id,
                ),
            )
            conn.execute(
                """INSERT INTO submission_position_heads(project_id,plan_id,stage_id,task_id,version) VALUES(%s,%s,%s,%s,%s)
                ON CONFLICT(project_id,plan_id,stage_id,task_id) DO UPDATE SET version=EXCLUDED.version""",
                (*command.position, head + 1),
            )
            self._task_status(conn, command.project_id, task, "awaiting_evidence")
            result = _json(
                dict(
                    thread=self._thread(conn, command.position),
                    submission=self._attempt(conn, command.project_id, identifier),
                    replayed=False,
                )
            )
            self._record(
                conn, scope, command.project_id, command.idempotency_key, "save", command.input_hash(), result
            )
            return result

    def decide(self, scope, command):
        with self._tx(scope, command.project_id, write=True) as conn:
            prior = self._receipt(
                conn, scope, command.project_id, command.idempotency_key, "decide", command.input_hash()
            )
            if prior is not None:
                return prior
            saved = self._attempt(conn, command.project_id, command.submission_id)
            if saved["task_snapshot"]["snapshot_status"] != "frozen":
                raise ConflictError("旧成果没有当时任务依据，不能重新标记为当前人工验收")
            position = tuple(saved[key] for key in ("project_id", "plan_id", "stage_id", "task_id"))
            plan = PgLearningExposures._plan(conn, command.project_id, saved["plan_id"], current=True)
            practice, task = self._context(conn, position, lock=True)
            head = self._head(conn, position)
            self._versions(command, plan, task, head)
            if saved["version"] != head or saved["review"] is not None:
                raise ConflictError("只可判定最新且尚未判定的此位置成果")
            current_snapshot = self._snapshot(conn, position, plan, practice, task)
            if self._requirements(current_snapshot) != self._requirements(saved["task_snapshot"]):
                raise VersionConflictError("当前任务或知识要求已不同于此成果保存依据")
            command.validate_basis(
                saved["task_snapshot"]["task"]["acceptance"], len(saved["evidence"]), saved["evidence_grade"]
            )
            review = AcceptanceReview.create(
                submission_id=command.submission_id,
                task_id=saved["task_id"],
                conclusion=AcceptanceConclusion(command.conclusion),
                rationale=command.rationale,
                reviewer_kind=ReviewerKind.USER,
            )
            conn.execute(
                """INSERT INTO acceptance_reviews(review_id,project_id,submission_id,conclusion,reviewer_kind,rationale,
                created_at,actor_id,coverage,acknowledge_verification_limit,basis_snapshot) VALUES(%s,%s,%s,%s,'user',%s,%s,%s,%s,%s,%s)""",
                (
                    review.review_id,
                    command.project_id,
                    command.submission_id,
                    review.conclusion.value,
                    command.rationale,
                    review.created_at,
                    scope.actor_id,
                    Jsonb([asdict(item) for item in command.coverage]),
                    command.acknowledge_verification_limit,
                    Jsonb(saved["task_snapshot"]),
                ),
            )
            target = {
                "accepted": "accepted",
                "needs_more_evidence": "awaiting_evidence",
                "not_passed": "implementing",
            }[command.conclusion]
            status, version = self._task_status(conn, command.project_id, task, target)
            result = _json(
                dict(
                    submission=self._attempt(conn, command.project_id, command.submission_id),
                    task_status=status,
                    task_version=version,
                    created=True,
                    manual_confirmation=True,
                )
            )
            self._record(
                conn,
                scope,
                command.project_id,
                command.idempotency_key,
                "decide",
                command.input_hash(),
                result,
            )
            return result

    def outcomes(self, scope, project_id, cursor=None, limit=20):
        page = self.history(scope, project_id, cursor, limit)
        with self._tx(scope, project_id) as conn:
            counts = {
                row["artifact_kind"]: row["n"]
                for row in conn.execute(
                    "SELECT artifact_kind,count(*) AS n FROM practice_submissions WHERE project_id=%s GROUP BY artifact_kind",
                    (project_id,),
                ).fetchall()
            }
        groups = []
        for kind, title in zip(ARTIFACT_KINDS, OUTCOME_TITLES, strict=True):
            items = []
            for row in page["items"]:
                if row["artifact_kind"] != kind:
                    continue
                snapshot = row["task_snapshot"]
                review = row["review"]
                items.append(
                    {
                        key: row[key]
                        for key in ("submission_id", "artifact_kind", "evidence_grade", "created_at")
                    }
                    | dict(
                        plan_revision=snapshot["plan_revision"],
                        stage_title=snapshot["stage_title"],
                        task_title=(snapshot["task"] or {}).get("title"),
                        project_title=(snapshot["practice_project"] or {}).get("title"),
                        conclusion=review["conclusion"] if review else None,
                        manual_confirmation=review["manual_confirmation"] if review else False,
                    )
                )
            groups.append(dict(kind=kind, title=title, total_records=counts.get(kind, 0), items=items))
        return dict(project_id=project_id, groups=groups, next_cursor=page["next_cursor"])
