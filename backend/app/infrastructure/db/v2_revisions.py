"""Item8 adapter over existing Draft JSONB and the single Publication transaction."""

from contextlib import contextmanager
from dataclasses import asdict, replace
from uuid import NAMESPACE_URL, uuid5

import psycopg
from app.application.plan_resources import StageResourceView
from app.application.plan_service import DecisionOutcome, DraftBundle
from app.core.errors import (
    ConflictError,
    ForbiddenError,
    IdempotencyConflictError,
    NotFoundError,
    ValidationAppError,
)
from app.core.ids import content_hash
from app.domain.enums import PlanDraftStatus, StageResourceRole
from app.domain.planning.models import PlanDraft, PlanPublicationService, PlanTaskKnowledgeLink
from app.domain.planning.revisions import V2RevisionContext, local_candidate
from app.domain.resources.curation import ResolvedSection
from app.infrastructure.db.plan_repository import PgPlanRepository, to_psycopg_dsn
from app.infrastructure.db.planning_fence import lock_plan_version
from psycopg.rows import dict_row


def _stage_hash(stage):
    return content_hash(asdict(stage))


def capture_progress_basis(conn, current, *, _seen=()):
    """Freeze exact-position bodies, heads, reviews and source selections.

    Hash the complete DB rows, retain only immutable references/digests. Summary
    and user acceptance use the same facts as the existing workspace consumer.
    """
    if current.plan_id in _seen:
        raise ConflictError("Revision history contains a cycle")
    inherited, ancestor_bases = {}, []
    if current.v2_revision is not None:
        ctx = current.v2_revision.to_payload()
        parent = PgPlanRepository("", connection=conn).get_revision(project_id=current.project_id, revision=ctx["base_revision"])
        if (parent is None or parent.plan_id != ctx["base_plan_id"] or parent.revision >= current.revision
                or parent.structure_fingerprint() != ctx["base_structure_hash"]
                or content_hash(parent.v2_execution.to_payload()["manifest"]) != ctx["base_execution_manifest_hash"]):
            raise ConflictError("Historical revision lineage no longer resolves exactly")
        prior_basis = capture_progress_basis(conn, parent, _seen=(*_seen, current.plan_id))
        parent_stages = {s.stage_id: s for s in parent.stages}
        parent_facts = {s["stage_id"]: s for s in prior_basis["stages"]}
        current_stages = {s.stable_key: s for s in current.stages}
        for ref in ctx["lineage"]:
            source = parent_stages.get(ref["source_stage_id"])
            if (source is None or source.stable_key != ref["source_stable_key"]
                    or ref["source_stage_hash"] != _stage_hash(source)):
                raise ConflictError("Historical stage lineage no longer resolves exactly")
            target = ref["target_stable_key"]
            if target is None:
                continue
            if ctx["change_kind"] != "local" or target not in current_stages:
                raise ConflictError("Unverified revision progress correspondence")
            fact = parent_facts[source.stage_id]
            if fact["protected"]:
                if replace(current_stages[target], stage_id=source.stage_id) != source:
                    raise ConflictError("Preserved historical prefix content differs from its exact source")
                inherited[current_stages[target].stage_id] = fact
        ancestor_bases = [{"plan_id": parent.plan_id, "revision": parent.revision,
            "basis_hash": prior_basis["basis_hash"], "records": prior_basis["records"], "stages": prior_basis["stages"]},
            *prior_basis["ancestor_bases"]]
    args = (current.project_id, current.plan_id)
    bodies = {}
    for table in ("learning_exposures", "summary_attempts", "summary_position_heads", "summary_stage_heads",
            "prompt_revisions", "prompt_position_heads", "practice_submissions", "submission_position_heads",
            "learning_resource_selections"):
        bodies[table] = [r["row"] for r in conn.execute(
            f"SELECT to_jsonb(t) AS row FROM {table} t WHERE project_id=%s AND plan_id=%s", args).fetchall()]
    for table, parent_table, key in (("acceptance_reviews", "practice_submissions", "submission_id"),
            ("prompt_reviews", "prompt_revisions", "revision_id"),
            ("prompt_review_bindings", "prompt_revisions", "revision_id"),
            ("prompt_exports", "prompt_revisions", "revision_id"),
            ("summary_reviews", "summary_attempts", "attempt_id"),
            ("summary_review_bindings", "summary_attempts", "attempt_id")):
        bodies[table] = [r["row"] for r in conn.execute(
            f"SELECT to_jsonb(t) AS row FROM {table} t JOIN {parent_table} p ON p.project_id=t.project_id AND p.{key}=t.{key} "
            "WHERE p.project_id=%s AND p.plan_id=%s", args).fetchall()]
    records = []
    for table, rows in bodies.items():
        for row in rows:
            refs = {k: v for k, v in row.items() if k.endswith("_id") or k in {"version", "revision_no", "conclusion", "reviewer_kind", "status"}}
            records.append({"table": table, "refs": refs, "row_hash": content_hash(row)})
    records.sort(key=lambda r: (r["table"], content_hash(r["refs"])))
    active = {r["stage_id"] for table in ("learning_exposures", "summary_attempts", "prompt_revisions",
        "practice_submissions", "learning_resource_selections") for r in bodies[table]}
    summaries = {(r["stage_id"], r["version"]) for r in bodies["summary_attempts"] if r["unit_id"] is None and r["content"].strip()}
    completed_summaries = {r["stage_id"] for r in bodies["summary_stage_heads"] if (r["stage_id"], r["version"]) in summaries}
    accepted_ids = {r["submission_id"] for r in bodies["acceptance_reviews"] if r["conclusion"] == "accepted" and r["reviewer_kind"] == "user"}
    accepted = {(r["stage_id"], r["task_id"]) for r in bodies["practice_submissions"] if r["submission_id"] in accepted_ids}
    boundary = max((s.order_index for s in current.stages if s.stage_id in active), default=-1)
    stages = []
    for stage in current.stages:
        tasks = {link.task_id for link in current.task_links if link.stage_id == stage.stage_id}
        completed = stage.stage_id in completed_summaries and all((stage.stage_id, task) in accepted for task in tasks)
        historical = inherited.get(stage.stage_id)
        historical_status = ((historical["learning_status"] if historical["learning_status"] != "future" else historical["historical_learning_status"])
            if historical else None)
        history_source = None
        if historical is not None and historical_status is not None:
            if historical["learning_status"] != "future":
                history_source = {"source_plan_id": parent.plan_id, "source_revision": parent.revision,
                    "source_stage_id": historical["stage_id"], "source_stage_hash": historical["stage_hash"]}
            else:
                history_source = historical["history_source"]
        stages.append({"stage_id": stage.stage_id, "stable_key": stage.stable_key, "title": stage.title,
            "learning_status": "completed" if completed else "started" if stage.stage_id in active else "future",
            "historical_learning_status": historical_status, "history_source": history_source,
            "protected": stage.order_index <= boundary or historical is not None, "stage_hash": _stage_hash(stage)})
    basis = {"plan_id": current.plan_id, "revision": current.revision, "records": records, "stages": stages,
        "ancestor_bases": ancestor_bases}
    basis["basis_hash"] = content_hash(basis)
    return basis


def _base(conn, project_id):
    current = PgPlanRepository("", connection=conn).get_current(project_id=project_id)
    if current is None or current.v2_execution is None:
        raise ValidationAppError("当前版本必须是合法V2学习计划")
    return current


def validate_revision_basis(conn, owner, *, expected_version=None, domain_approvals=()):
    """Run inside the existing project decision lock, including Publication."""
    ctx = owner.v2_revision.to_payload()
    if owner.project_id != ctx["project_id"] or owner.v2_execution is None:
        raise ConflictError("Revision scope or execution binding mismatch")
    if conn.execute("SELECT 1 FROM learning_projects WHERE project_id=%s AND owner_actor_id=%s AND archived_at IS NULL FOR UPDATE",
            (owner.project_id, ctx["actor_id"])).fetchone() is None:
        raise ForbiddenError()
    current = _base(conn, owner.project_id)
    if (current.plan_id != ctx["base_plan_id"] or current.revision != ctx["base_revision"]
            or expected_version is not None and expected_version != current.revision
            or current.structure_fingerprint() != ctx["base_structure_hash"]
            or content_hash(current.v2_execution.to_payload()["manifest"]) != ctx["base_execution_manifest_hash"]):
        raise ConflictError("原当前版本已变化，请重新生成预览", reason="revision_basis_stale")
    progress = capture_progress_basis(conn, current)
    if progress != ctx["progress_basis"]:
        raise ConflictError("学习进度或成果已变化，请重新生成预览", reason="revision_progress_stale")
    wanted = []
    for fact, stage in zip(progress["stages"], current.stages, strict=True):
        wanted.append({"source_plan_id": current.plan_id, "source_revision": current.revision,
            "source_stage_id": stage.stage_id, "source_stable_key": stage.stable_key,
            "source_stage_hash": _stage_hash(stage), "learning_status": fact["learning_status"],
            "target_stable_key": stage.stable_key if ctx["change_kind"] == "local" else None})
    if wanted != ctx["lineage"]:
        raise ConflictError("Exact revision lineage mismatch")
    if ctx["change_kind"] == "local":
        by_key = {s.stable_key: s for s in owner.stages}
        remap = {s.stable_key: s.stage_id for s in current.stages}
        if set(by_key) != set(remap):
            raise ValidationAppError("Local change cannot remove required stages")
        candidate = tuple(replace(s, stage_id=remap[s.stable_key]) for s in owner.stages)
        prior = {s.stage_id: s for s in current.stages}
        protected = {s["stage_id"] for s in progress["stages"] if s["protected"]}
        if any(s != prior[s.stage_id] for s in candidate if s.stage_id in protected):
            raise ValidationAppError("Historical prefix was modified")
        rebuilt = current.v2_execution.recompile_local(candidate, domain_approvals=domain_approvals)
        if rebuilt.semantic_payload() != owner.v2_execution.semantic_payload():
            raise ValidationAppError("Local change altered frozen required outcomes, sources, tasks or project facts")
    return current


def _resources(owner):
    views = []
    for snapshot in owner.resource_snapshots:
        data = dict(snapshot["view"])
        data["role"] = StageResourceRole(data["role"])
        data["ordered_sections"] = tuple(ResolvedSection(**s) for s in data["ordered_sections"])
        for field in ("fallback_search_terms", "warnings", "node_ids"):
            data[field] = tuple(data.get(field, ()))
        views.append(StageResourceView(**data))
    if len(views) != len(owner.stage_resources):
        raise ConflictError("Revision source snapshots are incomplete")
    return tuple(views)


class PgV2Revisions:
    def __init__(self, dsn, *, planning_jobs=None, runtime_factory=None, domain_approvals=()):
        self.dsn = to_psycopg_dsn(dsn)
        self.planning_jobs, self.runtime_factory = planning_jobs, runtime_factory
        self.domain_approvals = tuple(domain_approvals)

    @contextmanager
    def _connection(self, scope, project_id):
        scope.require_project(project_id)
        with psycopg.connect(self.dsn, row_factory=dict_row) as conn:
            conn.execute("SELECT set_config('app.project_id',%s,true),set_config('app.actor_id',%s,true)", (project_id, scope.actor_id))
            lock_plan_version(conn, project_id, None)
            if conn.execute("SELECT 1 FROM learning_projects WHERE project_id=%s AND owner_actor_id=%s AND archived_at IS NULL FOR UPDATE",
                    (project_id, scope.actor_id)).fetchone() is None:
                raise ForbiddenError()
            yield conn

    @staticmethod
    def _identity(scope, project_id, idempotency_key, kind):
        if type(idempotency_key) is not str or not 1 <= len(idempotency_key.strip()) <= 128:
            raise ValidationAppError("幂等键不能为空或过长")
        return ("drf_" if kind == "local" else "run_") + uuid5(NAMESPACE_URL,
            content_hash(["v2-revision", kind, scope.actor_id, project_id, idempotency_key])).hex

    def context(self, *, scope, project_id):
        with self._connection(scope, project_id) as conn:
            current = _base(conn, project_id)
            basis = capture_progress_basis(conn, current)
            return {"plan_id": current.plan_id, "revision": current.revision, "goal": current.goal_snapshot,
                "stages": [{k: v for k, v in s.items() if k not in {"stage_hash", "history_source"}} for s in basis["stages"]],
                "supported_local_operations": ["future_stage_descriptions", "future_stage_order"],
                "history_policy": "历史记录保留原版本，新版本不自动继承进度。"}

    def preview_local(self, *, scope, project_id, expected_version, current_plan_id, idempotency_key, stage_edits=(), stage_order=None):
        draft_id = self._identity(scope, project_id, idempotency_key, "local")
        fingerprint = content_hash({"expected_version": expected_version, "current_plan_id": current_plan_id,
            "stage_edits": [asdict(e) for e in stage_edits], "stage_order": stage_order})
        with self._connection(scope, project_id) as conn:
            repo = PgPlanRepository(self.dsn, connection=conn, v2_domain_approvals=self.domain_approvals)
            old = repo.get_draft(project_id=project_id, draft_id=draft_id)
            if old:
                if old.v2_revision is None or old.v2_revision.to_payload()["input_hash"] != fingerprint:
                    raise IdempotencyConflictError("同一预览身份已绑定不同修改")
                return DraftBundle(old, _resources(old))
            current = _base(conn, project_id)
            if current.plan_id != current_plan_id or current.revision != expected_version:
                raise ConflictError("当前版本已变化", reason="revision_basis_stale")
            progress = capture_progress_basis(conn, current)
            protected = {s["stage_id"] for s in progress["stages"] if s["protected"]}
            stages = local_candidate(current.v2_execution, current.stages, stage_edits, stage_order=stage_order, protected_stage_ids=protected)
            execution = current.v2_execution.recompile_local(stages, domain_approvals=self.domain_approvals)
            source = execution.to_payload()
            source["bindings"]["run_id"] = ""
            execution = execution.from_payload(source)
            before = {s.stage_id: s for s in current.stages}
            modified = [{"stage": s.title, "before_title": before[s.stage_id].title,
                "before_description": before[s.stage_id].objective, "description": s.objective,
                "before_order": before[s.stage_id].order_index, "order": s.order_index}
                for s in stages if s != before[s.stage_id]]
            lineage = [{"source_plan_id": current.plan_id, "source_revision": current.revision,
                "source_stage_id": stage.stage_id, "source_stable_key": stage.stable_key,
                "source_stage_hash": _stage_hash(stage), "learning_status": fact["learning_status"],
                "target_stable_key": stage.stable_key} for fact, stage in zip(progress["stages"], current.stages, strict=True)]
            context = V2RevisionContext.create(change_kind="local", actor_id=scope.actor_id, project_id=project_id,
                base_plan_id=current.plan_id, base_revision=current.revision, base_structure_hash=current.structure_fingerprint(),
                base_execution_manifest_hash=content_hash(current.v2_execution.to_payload()["manifest"]), progress_basis=progress,
                change_diff={"preserved_stages": [s.title for s in stages if s == before[s.stage_id]], "modified_stages": modified,
                    "removed_stages": [], "added_stages": [], "outcomes_changed": False, "prerequisites_changed": False,
                    "materials_changed": False, "practice_changed": False, "unresolved": []}, lineage=lineage,
                approved_goal_spec=None, budget_root_run_id=(current.v2_revision.to_payload()["budget_root_run_id"]
                    if current.v2_revision else current.v2_execution.to_payload()["bindings"]["run_id"]), input_hash=fingerprint)
            unit_order = {s.stage_id: i for i, s in enumerate(stages)}
            c = execution.to_payload()["compiled"]
            draft = PlanDraft(draft_id=draft_id, project_id=project_id, run_id="", goal_snapshot=current.goal_snapshot,
                revision_candidate=current.revision + 1, stages=stages,
                unit_links=tuple(sorted(current.unit_links, key=lambda link: (unit_order[link.stage_id], link.order_index))),
                task_links=tuple(sorted(current.task_links, key=lambda link: (unit_order[link.stage_id], link.order_index))),
                task_knowledge_links=tuple(PlanTaskKnowledgeLink(source["bindings"]["tasks"][task["stable_key"]],
                    source["bindings"]["nodes"][node]) for task in c["practice"]["tasks"] for node in task["knowledge_refs"]),
                stage_resources=tuple(sorted(current.stage_resources, key=lambda a: (unit_order[a.stage_id], a.order_index))),
                resource_snapshots=current.resource_snapshots, unit_refs=tuple(u["stable_key"] for u in c["units"]),
                task_refs=tuple(t["stable_key"] for t in c["practice"]["tasks"]), node_stable_keys=tuple(n["stable_key"] for n in c["nodes"]),
                v2_execution=execution, v2_revision=context)
            validate_revision_basis(conn, draft, expected_version=expected_version, domain_approvals=self.domain_approvals)
            repo.save_draft(draft, expected_version=expected_version)
            return DraftBundle(draft, _resources(draft))

    def get_preview(self, *, scope, project_id, draft_id):
        with self._connection(scope, project_id) as conn:
            draft = PgPlanRepository(self.dsn, connection=conn, v2_domain_approvals=self.domain_approvals).get_draft(project_id=project_id, draft_id=draft_id)
            if draft is None or draft.v2_revision is None or draft.v2_revision.to_payload()["actor_id"] != scope.actor_id:
                raise NotFoundError("变更预览不存在")
            return DraftBundle(draft, _resources(draft))

    def confirm(self, *, scope, project_id, draft_id, expected_version, draft_hash, idempotency_key):
        with self._connection(scope, project_id) as conn:
            repo = PgPlanRepository(self.dsn, connection=conn, v2_domain_approvals=self.domain_approvals)
            draft = repo.get_draft(project_id=project_id, draft_id=draft_id)
            if draft is None or draft.v2_revision is None or draft.v2_revision.to_payload()["actor_id"] != scope.actor_id:
                raise NotFoundError("变更预览不存在")
            if expected_version != draft.v2_revision.to_payload()["base_revision"]:
                raise ConflictError("确认请求版本与预览不一致")
            draft.verify_hash(draft_hash)
            result = PlanPublicationService(repo).publish(draft=draft, presented_hash=draft_hash,
                expected_version=expected_version, idempotency_key=idempotency_key)
            saved = repo.get_draft(project_id=project_id, draft_id=draft_id)
            plan = repo.get_revision(project_id=project_id, revision=result.revision)
            return DecisionOutcome(draft.run_id, saved, _resources(saved), plan, _resources(plan), result.created)

    def cancel(self, *, scope, project_id, draft_id, expected_version, draft_hash, idempotency_key=None):
        with self._connection(scope, project_id) as conn:
            repo = PgPlanRepository(self.dsn, connection=conn, v2_domain_approvals=self.domain_approvals)
            draft = repo.get_draft(project_id=project_id, draft_id=draft_id)
            if draft is None or draft.v2_revision is None or draft.v2_revision.to_payload()["actor_id"] != scope.actor_id:
                raise NotFoundError("变更预览不存在")
            draft.verify_hash(draft_hash)
            if expected_version != draft.v2_revision.to_payload()["base_revision"]:
                raise ConflictError("取消请求版本与预览不一致")
            if draft.status == PlanDraftStatus.CANCELLED:
                return DecisionOutcome(draft.run_id, draft, _resources(draft))
            repo.cancel_draft(project_id=project_id, draft_id=draft_id, expected_hash=draft_hash, expected_version=expected_version)
            saved = repo.get_draft(project_id=project_id, draft_id=draft_id)
            return DecisionOutcome(saved.run_id, saved, _resources(saved))

    def submit_semantic(self, **kwargs):
        from app.core.errors import DependencyUnavailableError
        raise DependencyUnavailableError("V2 owned replanning is not configured")
