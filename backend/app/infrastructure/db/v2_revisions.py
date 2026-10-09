"""Item8 adapter over existing Draft JSONB and the single Publication transaction."""

from contextlib import contextmanager
from dataclasses import asdict, replace
from types import SimpleNamespace
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
from app.domain.enums import AiRunNextAction, AiRunStatus, PlanDraftStatus, StageResourceRole
from app.domain.planning.intent import GoalSpec, goal_spec_payload
from app.domain.planning.models import PlanDraft, PlanPublicationService, PlanTaskKnowledgeLink
from app.domain.planning.revisions import V2RevisionContext, execution_facts, local_candidate
from app.domain.planning.v2_runtime import V2_EXECUTION_VERSION, V2RecoveryBlocked, manifest_intact
from app.domain.resources.curation import ResolvedSection
from app.domain.runs.models import RunRecord
from app.infrastructure.db.plan_repository import PgPlanRepository, to_psycopg_dsn
from app.infrastructure.db.planning_fence import lock_plan_version
from psycopg.rows import dict_row


def frozen_submission(conn, *, actor_id, project_id, run_id, _seen=()):
    if run_id in _seen or len(_seen) > 3:
        raise V2RecoveryBlocked("Clarification ancestry contains a cycle or exceeds its bound")
    rows = conn.execute("SELECT e.detail,r.graph_version,r.kind,r.actor_id,r.project_id FROM ai_run_events e "
        "JOIN ai_runs r USING(run_id) WHERE e.run_id=%s AND e.status='submission' "
        "AND e.detail->>'kind'='planning_submission' ORDER BY e.event_id", (run_id,)).fetchall()
    if len(rows) != 1:
        raise V2RecoveryBlocked("Revision requires one durable original submission")
    row, detail = rows[0], rows[0]["detail"]
    manifest = detail.get("manifest")
    if (row["graph_version"] != V2_EXECUTION_VERSION or row["kind"] != "plan_generate"
            or row["actor_id"] != actor_id or row["project_id"] != project_id
            or detail.get("actor_id") != actor_id or detail.get("project_id") != project_id
            or not manifest_intact(manifest) or detail.get("initial", {}).get("manifest") != manifest):
        raise V2RecoveryBlocked("Revision original submission scope or manifest rejected")
    raw = detail["initial"].get("v2_revision")
    clarification = detail["initial"].get("v2_clarification")
    ctx = V2RevisionContext.from_payload(raw)
    if (ctx is None and manifest["expected_version"] != 0
            or (ctx is None) != ("v2_revision_hash" not in manifest)
            or ctx is not None and (ctx.to_payload()["change_kind"] != "semantic"
                or ctx.to_payload()["actor_id"] != actor_id or ctx.to_payload()["project_id"] != project_id
                or ctx.to_payload()["context_hash"] != manifest.get("v2_revision_hash")
                or manifest["goal_hash"] != content_hash(ctx.to_payload()["approved_goal_spec"])
                or manifest["expected_version"] != ctx.to_payload()["base_revision"]
                or content_hash(detail["initial"].get("goal_spec")) != manifest["goal_hash"])):
        raise V2RecoveryBlocked("Revision submission context binding rejected")
    if (clarification is None) != ("v2_clarification_hash" not in manifest):
        raise V2RecoveryBlocked("Clarification marker/context mismatch")
    if clarification is not None:
        from app.infrastructure.db.v2_clarifications import validate_continuation
        validate_continuation(conn, actor_id=actor_id, project_id=project_id, run_id=run_id,
            submission=detail, seen=(*_seen, run_id))
    if ctx is None and clarification is None:
        roots = conn.execute("SELECT DISTINCT r.run_id FROM ai_runs r LEFT JOIN ai_run_events e "
            "ON e.run_id=r.run_id AND e.status='submission' AND e.detail->>'kind'='planning_submission' "
            "WHERE r.actor_id=%s AND r.project_id=%s AND r.graph_version=%s AND r.kind='plan_generate' "
            "AND e.detail#>>'{initial,v2_revision}' IS NULL "
            "AND e.detail#>>'{initial,v2_clarification}' IS NULL", (actor_id, project_id, V2_EXECUTION_VERSION)).fetchall()
        if len(roots) != 1 or roots[0]["run_id"] != run_id:
            raise V2RecoveryBlocked("Multiple initial V2 roots require reconciliation")
    return detail


def budget_family(conn, *, actor_id, project_id, run_id):
    """Use original durable caps and every sibling's original immutable ledger."""
    own = frozen_submission(conn, actor_id=actor_id, project_id=project_id, run_id=run_id)
    from app.infrastructure.db.v2_clarifications import root_of
    root = root_of(own, run_id)
    original = frozen_submission(conn, actor_id=actor_id, project_id=project_id, run_id=root)
    if original["initial"].get("v2_revision") is not None or original["initial"].get("v2_clarification") is not None:
        raise V2RecoveryBlocked("Budget root must resolve to the original planning authority")
    rows = conn.execute("SELECT DISTINCT e.run_id FROM ai_run_events e JOIN ai_runs r USING(run_id) "
        "WHERE r.project_id=%s AND r.actor_id=%s AND e.status='submission' "
        "AND (e.detail->'initial'->'v2_revision'->>'budget_root_run_id'=%s "
        "OR e.detail->'initial'->'v2_clarification'->>'budget_root_run_id'=%s)", (project_id, actor_id, root, root)).fetchall()
    manifests = {root: original["manifest"]}
    for row in rows:
        detail = frozen_submission(conn, actor_id=actor_id, project_id=project_id, run_id=row["run_id"])
        if detail["manifest"]["budget"] != original["manifest"]["budget"]:
            raise V2RecoveryBlocked("Replanning cannot replace the original shared budget cap")
        manifests[row["run_id"]] = detail["manifest"]
    if run_id not in manifests:
        raise V2RecoveryBlocked("Revision run is not a member of its frozen budget root")
    return root, manifests


def revision_budget_root(conn, revision, actor_id):
    if revision.v2_revision:
        return revision.v2_revision.to_payload()["budget_root_run_id"]
    run = revision.v2_execution.to_payload()["bindings"]["run_id"]
    return budget_family(conn, actor_id=actor_id, project_id=revision.project_id, run_id=run)[0] if run else run


def published_v2_draft(conn, *, actor_id, project_id, run_id, draft_id):
    """Allow only completion of this exact already-published V2 result."""
    if conn.execute("SELECT 1 FROM plan_drafts d JOIN ai_runs r USING(run_id) "
            "WHERE d.project_id=%s AND r.project_id=%s AND r.actor_id=%s "
            "AND r.run_id=%s AND d.draft_id=%s AND d.status='approved' "
            "AND r.graph_version=%s AND r.kind='plan_generate' "
            "AND EXISTS(SELECT 1 FROM plan_publications p WHERE p.project_id=d.project_id "
                "AND p.draft_hash=d.content_hash)",
            (project_id, project_id, actor_id, run_id, draft_id, V2_EXECUTION_VERSION)).fetchone() is None:
        return False
    detail = frozen_submission(conn, actor_id=actor_id, project_id=project_id, run_id=run_id)
    draft = PgPlanRepository("", connection=conn).get_draft(project_id=project_id, draft_id=draft_id)
    if (draft is None or draft.run_id != run_id or draft.v2_execution is None
            or draft.v2_execution.to_payload()["bindings"]["run_id"] != run_id
            or (draft.v2_revision.to_payload() if draft.v2_revision else None) != detail["initial"].get("v2_revision")):
        raise V2RecoveryBlocked("Published result differs from its exact V2 submission")
    return True


def validate_semantic_input(conn, *, actor_id, project_id, run_id, manifest, context):
    detail = frozen_submission(conn, actor_id=actor_id, project_id=project_id, run_id=run_id)
    if detail["manifest"] != manifest or detail["initial"].get("v2_revision") != context.to_payload():
        raise V2RecoveryBlocked("Semantic execution differs from its durable submission")
    validate_revision_basis(conn, SimpleNamespace(project_id=project_id, v2_revision=context, v2_execution=True),
        expected_version=context.to_payload()["base_revision"])


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
        parent_root = revision_budget_root(conn, parent, ctx["actor_id"])
        if ctx["budget_root_run_id"] != parent_root:
            raise ConflictError("Historical revision changed its exact ancestor budget root")
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
    root = revision_budget_root(conn, current, ctx["actor_id"])
    if ctx["budget_root_run_id"] != root:
        raise ConflictError("Revision cannot replace its exact ancestor budget root")
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
        if owner.goal_spec != current.goal_spec:
            raise ConflictError("Local change altered the approved goal")
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
    elif hasattr(owner, "run_id"):
        submission = frozen_submission(conn, actor_id=ctx["actor_id"], project_id=owner.project_id, run_id=owner.run_id)
        if (submission["initial"].get("v2_revision") != ctx
                or owner.v2_execution.to_payload()["bindings"]["run_id"] != owner.run_id
                or goal_spec_payload(owner.goal_spec) != goal_spec_payload(GoalSpec(**ctx["approved_goal_spec"]))):
            raise ConflictError("Semantic Draft lost its original goal or durable run binding")
        budget_family(conn, actor_id=ctx["actor_id"], project_id=owner.project_id, run_id=owner.run_id)
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
                approved_goal_spec=None, budget_root_run_id=revision_budget_root(conn, current, scope.actor_id), input_hash=fingerprint)
            unit_order = {s.stage_id: i for i, s in enumerate(stages)}
            c = execution.to_payload()["compiled"]
            draft = PlanDraft(draft_id=draft_id, project_id=project_id, run_id="", goal_snapshot=current.goal_snapshot,
                goal_spec=current.goal_spec,
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

    def submit_semantic(self, *, scope, project_id, expected_version, current_plan_id, idempotency_key, goal_spec):
        from app.core.errors import DependencyUnavailableError
        from app.domain.planning.v2_runtime import wire
        factory = self.runtime_factory
        scope.require_project(project_id)
        if factory is None or getattr(factory, "owned_only", False) is not True or self.planning_jobs is None:
            raise DependencyUnavailableError("V2 owned replanning is not configured")
        if (to_psycopg_dsn(getattr(factory, "dsn", "")) != self.dsn
                or to_psycopg_dsn(getattr(self.planning_jobs, "_dsn", "")) != self.dsn):
            raise DependencyUnavailableError("Owned replanning dependencies must share the same business database")
        if type(goal_spec) is not GoalSpec or type(expected_version) is not int or expected_version < 1:
            raise ValidationAppError("Semantic change requires an explicit typed goal and current version")
        goal_payload = wire(goal_spec_payload(goal_spec))
        run_id = self._identity(scope, project_id, idempotency_key, "semantic")
        fingerprint = content_hash({"expected_version": expected_version, "current_plan_id": current_plan_id,
            "goal_spec": goal_payload})
        with self._connection(scope, project_id) as conn:
            if conn.execute("SELECT 1 FROM ai_runs WHERE run_id=%s", (run_id,)).fetchone():
                previous = frozen_submission(conn, actor_id=scope.actor_id, project_id=project_id, run_id=run_id)
                if previous["initial"].get("v2_revision", {}).get("input_hash") != fingerprint:
                    raise IdempotencyConflictError("同一重规划身份已绑定不同目标")
                return run_id
            current = _base(conn, project_id)
            if current.plan_id != current_plan_id or current.revision != expected_version:
                raise ConflictError("当前版本已变化", reason="revision_basis_stale")
            root = revision_budget_root(conn, current, scope.actor_id)
            if not root:
                raise ValidationAppError("Semantic replanning requires the original durable V2 run")
            original = frozen_submission(conn, actor_id=scope.actor_id, project_id=project_id, run_id=root)
            _, family = budget_family(conn, actor_id=scope.actor_id, project_id=project_id, run_id=root)
            if conn.execute("SELECT 1 FROM ai_provider_attempts WHERE run_id=ANY(%s) "
                    "AND status IN('dispatched','reconciliation_required') LIMIT 1", (list(family),)).fetchone():
                raise V2RecoveryBlocked("Original or sibling unknown dispatch blocks new replanning")
            manifest = factory.build_submission(scope, project_id, goal_spec, expected_version)
            if manifest["budget"] != original["manifest"]["budget"]:
                raise ValidationAppError("Replanning cannot reset or increase the original shared budget")
            progress = capture_progress_basis(conn, current)
            lineage = [{"source_plan_id": current.plan_id, "source_revision": current.revision,
                "source_stage_id": stage.stage_id, "source_stable_key": stage.stable_key,
                "source_stage_hash": _stage_hash(stage), "learning_status": fact["learning_status"],
                "target_stable_key": None} for fact, stage in zip(progress["stages"], current.stages, strict=True)]
            context = V2RevisionContext.create(change_kind="semantic", actor_id=scope.actor_id, project_id=project_id,
                base_plan_id=current.plan_id, base_revision=current.revision, base_structure_hash=current.structure_fingerprint(),
                base_execution_manifest_hash=content_hash(current.v2_execution.to_payload()["manifest"]),
                progress_basis=progress, lineage=lineage, approved_goal_spec=goal_payload, budget_root_run_id=root,
                input_hash=fingerprint, change_diff={"before": execution_facts(current.v2_execution, progress=progress),
                    "before_goal": current.goal_snapshot, "approved_goal_spec": goal_payload,
                    "history_retained": True, "progress_inherited": False})
            manifest["v2_revision_hash"] = context.to_payload()["context_hash"]
            manifest["manifest_hash"] = content_hash({k: v for k, v in manifest.items() if k != "manifest_hash"})
            initial = {"goal": goal_spec.target, "goal_spec": goal_payload, "manifest": manifest,
                "v2_revision": context.to_payload()}
            run = RunRecord(run_id, scope.actor_id, project_id, "plan_generate", "planning", V2_EXECUTION_VERSION,
                AiRunStatus.QUEUED, AiRunNextAction.WAIT, thread_id="thread_" + run_id[4:])
            self.planning_jobs.in_transaction(conn).enqueue(run, initial, manifest)
            return run_id
