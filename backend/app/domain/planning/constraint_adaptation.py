"""Small, closed phrase policy plus fact checks; never a general NLP classifier.

Only exact reviewed expressions are interpreted. Unknown/combined prose remains
pending. A rule selects a check, never supplies evidence that the check passed.
"""
from dataclasses import asdict, dataclass

from app.core.ids import content_hash

CONSTRAINT_POLICY = "constraint-adaptation:v1"
# Additive scope rules have their own reference. Never relabel v1 assessments
# or reinterpret a persisted v1 research configuration as the new rules.
CONSTRAINT_SCOPE_POLICY = "constraint-adaptation:v2"
_PHRASES = {
    "free_material": ("免费教材", "教程免费", "教程要求免费", "只使用免费教材", "教材必须免费"),
    "existing_carrier": ("不要重新创建演示项目", "不重新创建演示项目", "不要重新建立演示项目"),
    "readonly_practice": ("只读，不允许代码修改", "只读运行", "不允许自动修改代码", "禁止自动修改代码"),
    "no_network": ("禁止联网", "禁止任何网络连接", "不允许外部调用"),
    "chinese_material": ("只使用中文教材", "教材必须为中文"),
    "chinese_preference": ("中文优先", "优先中文教材"),
}
_SCOPED_PHRASES = {
    "existing_carrier": ("保留现有 CLI 和 JSON 任务文件作为持续实践载体",),
    "local_tool_scope": ("工具仅操作用户明确允许的本地任务范围",),
}


def constraint_kind(text, *, policy_ref=None):
    if policy_ref not in {None, CONSTRAINT_POLICY, CONSTRAINT_SCOPE_POLICY}:
        raise ValueError("Unknown constraint adaptation policy")
    if policy_ref != CONSTRAINT_POLICY:
        scoped = next((kind for kind, phrases in _SCOPED_PHRASES.items() if text in phrases), None)
        if scoped is not None:
            return scoped
    return next((kind for kind, phrases in _PHRASES.items() if text in phrases), "unclassified")


def constraint_policy_ref(text):
    return CONSTRAINT_SCOPE_POLICY if any(text in phrases for phrases in _SCOPED_PHRASES.values()) else CONSTRAINT_POLICY


def research_constraint_policy(constraints):
    """Only affected inputs change the persisted research configuration hash."""
    return CONSTRAINT_SCOPE_POLICY if any(constraint_policy_ref(c.text) == CONSTRAINT_SCOPE_POLICY for c in constraints) else CONSTRAINT_POLICY


@dataclass(frozen=True, slots=True)
class ConstraintAssessment:
    constraint_ref: str
    source_refs: tuple[str, ...]
    scope: str
    status: str
    evidence_refs: tuple[str, ...]
    reason: str
    policy_ref: str = CONSTRAINT_POLICY


def research_permissions(constraints):
    """Allow only known checks; no-network still allows local reviewed reuse.

    Free body access is always checked by Researcher, regardless of a user
    constraint. Language requirements lack a trusted language proof today.
    """
    kinds = {constraint_kind(c.text) for c in constraints}
    allowed = not kinds & {"unclassified", "chinese_material"}
    return bool(allowed), "no_network" not in kinds


def composition_dispatch_allowed(constraints):
    # The composer uses an external model; unclassified restrictions cannot
    # grant permission to send context, nor can a local material release a
    # blanket no-network restriction.
    return all(constraint_kind(c["text"]) not in {"no_network", "unclassified"} for c in constraints)


def assess_curriculum(constraints, materials, project_context, carrier=None, *, policy_ref=None):
    """Check selected facts, not model assertions. Runtime restrictions defer.

    Materials must already have passed the curriculum source/access validator.
    Chinese language and readonly behavior cannot be proved by task prose.
    """
    if policy_ref not in {None, CONSTRAINT_POLICY, CONSTRAINT_SCOPE_POLICY}:
        raise ValueError("Unknown constraint adaptation policy")
    results = []
    for constraint in constraints:
        kind = constraint_kind(constraint["text"], policy_ref=policy_ref)
        status, reason, evidence = "pending", "no_trusted_check", ()
        scope = {"free_material": "material_access", "existing_carrier": "practice_carrier",
            "readonly_practice": "practice_behavior", "local_tool_scope": "practice_permission_scope", "no_network": "external_dispatch",
            "chinese_material": "material_language", "chinese_preference": "material_preference"}.get(kind, "unclassified")
        if kind == "free_material":
            if materials and all(m["usable"] and m["free_access"] == "confirmed" for m in materials):
                status, reason = "satisfied", "all_selected_materials_verified_free"
                evidence = tuple(sorted(m["material_id"] for m in materials))
            elif any(m["free_access"] == "paid" for m in materials):
                status, reason = "violated", "paid_material_selected"
            else:
                reason = "free_access_evidence_pending"
        elif kind == "existing_carrier":
            if project_context and carrier and carrier["kind"] == "user_project" and carrier["description"] == project_context:
                status, reason = "satisfied", "exact_existing_carrier_preserved"
                evidence = ("project_context:" + content_hash({"project_context": project_context}),)
            elif carrier and carrier["kind"] == "starter":
                status, reason = "violated", "starter_disallowed"
            else:
                reason = "existing_carrier_evidence_pending"
        elif kind == "chinese_preference":
            # Existing research sorts Chinese candidates first; a preference
            # is not a mandatory source qualification or fabricated proof.
            status, reason = "not_applicable", "preference_not_mandatory_material_constraint"
        elif kind == "readonly_practice":
            reason = "task_prose_does_not_prove_readonly_behavior"
        elif kind == "local_tool_scope":
            # Understanding the practice boundary grants no tool/file access.
            # No trusted runtime permission evidence exists at composition time.
            reason = "runtime_permission_evidence_pending"
        elif kind == "no_network":
            reason = "downstream_network_boundary_pending"
        elif kind == "chinese_material":
            reason = "trusted_language_proof_pending"
        results.append(asdict(ConstraintAssessment(constraint["constraint_id"], tuple(constraint["source_refs"]),
            scope, status, evidence, reason,
            CONSTRAINT_POLICY if policy_ref == CONSTRAINT_POLICY else constraint_policy_ref(constraint["text"]))))
    return results


def curriculum_constraint_assessments(document, payload):
    selected = {a["material_id"] for s in document["stages"] for a in s["assignments"]}
    selected.update(ref for s in document["stages"] for k in s["knowledge"] for ref in k["material_refs"])
    assessments = assess_curriculum(payload["constraints"], [m for m in payload["materials"] if m["material_id"] in selected],
        payload["profile_context"]["project_context"], document["carrier"])
    # A bounded behavior review of a separate project case currently carries
    # no access proof. Do not lend the tutorial's free proof to that case.
    if any(r["selected_case_ref"] for r in document["project_study_requirements"]):
        free_ids = {c["constraint_id"] for c in payload["constraints"] if constraint_kind(c["text"]) == "free_material"}
        for assessment in assessments:
            if assessment["constraint_ref"] in free_ids:
                assessment.update(status="pending", reason="case_free_access_evidence_pending", evidence_refs=())
    if payload.get("semantics_version") == 2:
        obligations = {item["constraint_ref"]: item for item in document["permission_obligations"]}
        for assessment in assessments:
            if assessment["scope"] == "practice_permission_scope":
                arranged = assessment["constraint_ref"] in obligations
                assessment.update(planning_status="arranged" if arranged else "pending", runtime_status="unverified")
                if arranged:
                    item = obligations[assessment["constraint_ref"]]
                    assessment.update(status="planning_arranged", reason="bound_permission_teaching_obligation_arranged",
                        evidence_refs=(item["task_ref"], *item["acceptance_refs"]))
    return assessments


def constraints_unresolved(assessments):
    # not_applicable is only used for a non-mandatory preference here, never
    # to release a carrier/behavior/network constraint at curriculum level.
    return any(a["status"] in {"pending", "violated"} for a in assessments)
