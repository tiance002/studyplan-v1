"""Prompt originals specialize the existing immutable review transaction boundary."""

from app.core.errors import NotFoundError, ValidationAppError, VersionConflictError
from app.core.ids import content_hash, new_id
from app.domain.practice.models import PromptExport, PromptRevision
from app.domain.prompts import (
    PROMPT_PROTOCOL,
    implementation_export,
    prompt_manifest_intact,
    validate_prompt_feedback,
)
from app.infrastructure.db.learning_exposures import PgLearningExposures, _json
from app.infrastructure.db.summaries import PgSummaries
from psycopg.types.json import Jsonb


class PgPrompts(PgSummaries):
    receipt_table = "prompt_receipts"
    original_table = "prompt_revisions"
    binding_table = "prompt_review_bindings"
    review_table = "prompt_reviews"
    subject_column = "revision_id"
    snapshot_column = "task_snapshot"
    run_kind = "prompt_review"
    subject_label = "Prompt"
    protocol = PROMPT_PROTOCOL
    job_prefix = "prompt:"
    review_id_prefix = "prv"
    manifest_valid = staticmethod(prompt_manifest_intact)
    feedback_valid = staticmethod(validate_prompt_feedback)

    @staticmethod
    def _context(conn, position):
        project, plan, stage, task_id = position
        row = conn.execute(
            """SELECT t.* FROM plan_task_links l JOIN practice_tasks t
            ON t.project_id=l.project_id AND t.task_id=l.task_id
            WHERE l.project_id=%s AND l.plan_id=%s AND l.stage_id=%s AND l.task_id=%s""",
            position,
        ).fetchone()
        if not row:
            raise NotFoundError("此路线阶段没有指定实践任务")
        practice = conn.execute(
            "SELECT practice_project_id,title,idea,repo_url,status,version FROM practice_projects "
            "WHERE project_id=%s AND practice_project_id=%s",
            (project, row["practice_project_id"]),
        ).fetchone()
        if not practice:
            raise NotFoundError("实践项目不存在")
        links = conn.execute(
            """SELECT n.node_id,n.stable_key,n.title,n.content_version,l.role
            FROM plan_task_knowledge_links l JOIN knowledge_nodes n ON n.project_id=l.project_id AND n.node_id=l.node_id
            WHERE l.project_id=%s AND l.plan_id=%s AND l.task_id=%s ORDER BY l.order_index,l.link_id""",
            (project, plan, task_id),
        ).fetchall()
        task = {
            k: row[k] for k in ("task_id", "title", "goal", "in_scope", "out_scope", "acceptance", "status")
        }
        task["knowledge_links"] = links
        return _json(practice), _json(task)

    @staticmethod
    def _attempt(conn, project, revision_id):
        row = conn.execute(
            "SELECT * FROM prompt_revisions WHERE project_id=%s AND revision_id=%s", (project, revision_id)
        ).fetchone()
        if row is None:
            raise NotFoundError("Prompt 修订不存在")
        binding = conn.execute(
            "SELECT b.run_id,r.status FROM prompt_review_bindings b JOIN ai_runs r USING(run_id) "
            "WHERE b.project_id=%s AND b.revision_id=%s",
            (project, revision_id),
        ).fetchone()
        review = conn.execute(
            "SELECT * FROM prompt_reviews WHERE project_id=%s AND revision_id=%s", (project, revision_id)
        ).fetchone()
        snapshot = row["task_snapshot"] or {
            "snapshot_status": "legacy_unfrozen",
            "warning": "旧 Prompt 未保存当时的路线位置和任务要求；未继承当前要求。",
        }
        result = {
            k: row[k]
            for k in (
                "revision_id",
                "project_id",
                "plan_id",
                "stage_id",
                "task_id",
                "version",
                "user_draft",
                "created_at",
            )
        }
        result.update(
            revision_no=row["revision"],
            content_hash=row["content_hash"] or content_hash({"user_draft": row["user_draft"]}),
            task_snapshot=snapshot,
            review=None,
            legacy_review=None,
            legacy_review_recorded_at=None,
            run_id=binding["run_id"] if binding else row.get("run_id"),
            run_status=binding["status"] if binding else None,
        )
        if review:
            raw = review["review"]
            feedback = (
                {k: raw[k] for k in ("strengths", "gaps", "suggestions") if k in raw}
                if isinstance(raw, dict)
                else {}
            )
            if isinstance(raw, dict) and not validate_prompt_feedback(feedback) and review["run_id"]:
                result["review"] = dict(
                    feedback,
                    review_id=review["review_id"],
                    revision_id=revision_id,
                    task_id=row["task_id"],
                    run_id=review["run_id"],
                    created_at=review["created_at"],
                )
            else:
                result["legacy_review"] = raw if isinstance(raw, dict) else {"retained_content": raw}
                result["legacy_review_recorded_at"] = review["created_at"]
                result["task_snapshot"] = dict(
                    snapshot, legacy_review_warning="旧格式反馈已保留，未重新推断结论。"
                )
        return _json(result)

    def _thread(self, conn, position):
        project, plan, stage, task = position
        PgLearningExposures._plan(conn, project, plan)
        practice, context = self._context(conn, position)
        rows = conn.execute(
            """SELECT h.version AS head_version,a.revision_id FROM
            (SELECT coalesce((SELECT version FROM prompt_position_heads WHERE project_id=%s AND plan_id=%s
                AND stage_id=%s AND task_id=%s),0) AS version) h
            LEFT JOIN LATERAL(SELECT revision_id FROM prompt_revisions WHERE project_id=%s AND plan_id=%s
                AND stage_id=%s AND task_id=%s ORDER BY version DESC LIMIT 21) a ON true""",
            (*position, *position),
        ).fetchall()
        window = [row for row in rows if row["revision_id"] is not None]
        return dict(
            project_id=project,
            plan_id=plan,
            stage_id=stage,
            task_id=task,
            version=rows[0]["head_version"],
            practice_project=practice,
            task=context,
            revisions=[self._attempt(conn, project, row["revision_id"]) for row in reversed(window[:20])],
            history_truncated=len(window) > 20,
        )

    def save(self, scope, command):
        with self._tx(scope, command.project_id, write=True) as conn:
            prior = self._receipt(
                conn, scope, command.project_id, command.idempotency_key, "save", command.input_hash()
            )
            if prior:
                return dict(prior, replayed=True)
            plan = PgLearningExposures._plan(conn, command.project_id, command.plan_id, current=True)
            practice, task = self._context(conn, command.position)
            head = conn.execute(
                "SELECT version FROM prompt_position_heads WHERE project_id=%s AND plan_id=%s AND stage_id=%s AND task_id=%s",
                command.position,
            ).fetchone()
            version = head["version"] if head else 0
            if version != command.expected_version:
                raise VersionConflictError(actual_version=version, expected_version=command.expected_version)
            stage = conn.execute(
                "SELECT stable_key,title,objective,section_kind,order_index FROM plan_stages "
                "WHERE project_id=%s AND plan_id=%s AND stage_id=%s",
                command.position[:3],
            ).fetchone()
            public = conn.execute(
                "SELECT source_ref,source_version,section_refs,role FROM stage_resource_assignments "
                "WHERE project_id=%s AND plan_id=%s AND stage_id=%s ORDER BY order_index,assignment_id",
                command.position[:3],
            ).fetchall()
            frozen = [
                item
                for item in (plan["structure"] or {}).get("resource_snapshots", [])
                if item.get("stage_id") == command.stage_id
            ]
            snapshot = _json(
                dict(
                    snapshot_status="frozen",
                    practice_project=practice,
                    task=task,
                    plan_id=command.plan_id,
                    plan_revision=plan["revision"],
                    stage_id=command.stage_id,
                    stage_title=stage["title"],
                    plan_snapshot={"stage": stage, "structure_hash": content_hash(plan["structure"] or {})},
                    source_snapshot={
                        "kind": "assigned_source_bindings",
                        "public_assignments": public,
                        "published_resource_snapshots": frozen,
                        "published_metadata_status": "frozen" if frozen else "legacy_unfrozen",
                    },
                )
            )
            number = conn.execute(
                "SELECT coalesce(max(revision),0)+1 AS n FROM prompt_revisions WHERE task_id=%s",
                (command.task_id,),
            ).fetchone()["n"]
            identifier = new_id("prm")
            conn.execute(
                """INSERT INTO prompt_revisions(revision_id,project_id,task_id,revision,user_draft,plan_id,stage_id,version,content_hash,task_snapshot)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    identifier,
                    command.project_id,
                    command.task_id,
                    number,
                    command.user_draft,
                    command.plan_id,
                    command.stage_id,
                    version + 1,
                    content_hash({"user_draft": command.user_draft}),
                    Jsonb(snapshot),
                ),
            )
            conn.execute(
                """INSERT INTO prompt_position_heads(project_id,plan_id,stage_id,task_id,version) VALUES(%s,%s,%s,%s,%s)
                ON CONFLICT(project_id,plan_id,stage_id,task_id) DO UPDATE SET version=excluded.version""",
                (*command.position, version + 1),
            )
            result = dict(
                thread=self._thread(conn, command.position),
                revision=self._attempt(conn, command.project_id, identifier),
                replayed=False,
            )
            self._record(
                conn, scope, command.project_id, command.idempotency_key, "save", command.input_hash(), result
            )
            return result

    def _review_body(self, attempt, review):
        return review

    def export(self, scope, project_id, revision_id, format, key):
        if format not in {"raw", "implementation"}:
            raise ValidationAppError("Prompt 导出格式无效")
        fingerprint = content_hash({"revision_id": revision_id, "format": format})
        with self._tx(scope, project_id, write=True) as conn:
            prior = self._receipt(conn, scope, project_id, key, "export", fingerprint)
            if prior:
                return prior
            revision = self._attempt(conn, project_id, revision_id)
            result = conn.execute(
                "SELECT * FROM prompt_exports WHERE project_id=%s AND revision_id=%s AND format=%s",
                (project_id, revision_id, format),
            ).fetchone()
            if result is None:
                text = revision["user_draft"] if format == "raw" else implementation_export(revision)
                domain_revision = PromptRevision.create(
                    task_id=revision["task_id"],
                    user_draft=revision["user_draft"],
                    revision_no=revision["revision_no"],
                )
                PromptExport.create(task_id=revision["task_id"], revision=domain_revision, export_text=text)
                result = conn.execute(
                    """INSERT INTO prompt_exports(export_id,project_id,task_id,revision_id,revision_no,format,export_text,content_hash)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *""",
                    (
                        new_id("pex"),
                        project_id,
                        revision["task_id"],
                        revision_id,
                        revision["revision_no"],
                        format,
                        text,
                        content_hash({"export_text": text}),
                    ),
                ).fetchone()
            result = _json(result)
            self._record(conn, scope, project_id, key, "export", fingerprint, result)
            return result

    def get_export(self, scope, project_id, export_id):
        with self._tx(scope, project_id) as conn:
            row = conn.execute(
                "SELECT * FROM prompt_exports WHERE project_id=%s AND export_id=%s", (project_id, export_id)
            ).fetchone()
            if row is None:
                raise NotFoundError("Prompt 导出不存在")
            return _json(row)
