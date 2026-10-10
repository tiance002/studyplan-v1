"""Single-authority, versioned Item 2 decisions normalized through the V1 domain contract."""

from app.core.errors import ValidationAppError
from app.domain.planning.capabilities import (
    CapabilityPlanValidator,
    _array,
    _capability_id,
    _definitions,
    _object,
    _refs,
    _text,
    verification_input_hash,
)
from app.domain.planning.capability_policy import CAPABILITY_POLICY
from app.domain.planning.goal_requirements import GoalRequirementProfile

CAPABILITY_DECISION_PROTOCOL = "capability-decision-v2"
CAPABILITY_DECISION_VERSION = 2

DECISION_FIELDS = {
    "decision_version",
    "source_goal_profile_hash",
    "policy_version",
    "route_kind",
    "status",
    "learning_decisions",
    "claim_decisions",
    "constraint_effects",
    "clarification_questions",
}
LEARNING_FIELDS = {
    "capability_id",
    "learning_requirement",
    "project_usage",
    "desired_depth",
    "requirement_refs",
    "learning_target_refs",
    "project_usage_rationale",
    "selection_rationale",
}
CLAIM_DECISION_FIELDS = {
    "capability_id", "claim_mappings", "project_usage", "project_usage_rationale", "requirement_refs"
}
CLAIM_MAPPING_FIELDS = {"claim_ref", "mapping_rationale"}
CONSTRAINT_FIELDS = {"constraint_ref", "capability_id", "exclusion"}


def _reject(field):
    raise ValidationAppError("CapabilityDecisionV2 合同校验失败", field=field)


def _normalize(raw, *, profile, verification_evidence=()):
    if not isinstance(profile, GoalRequirementProfile) or profile.status != "ready":
        _reject("upstream_profile")
    data = _object(raw, DECISION_FIELDS)
    if (type(data["decision_version"]) is not int or data["decision_version"] != CAPABILITY_DECISION_VERSION
            or data["source_goal_profile_hash"] != profile.profile_hash
            or data["policy_version"] != CAPABILITY_POLICY.version):
        _reject("source_identity")
    route = data["route_kind"]
    status = data["status"]
    if route not in {"systematic_agent_route", "narrow_goal", "other", "uncertain"}:
        _reject("route_kind")
    if status not in {"ready", "needs_clarification", "needs_verification"}:
        _reject("status")
    questions = tuple(_text(q, 500) for q in _array(data["clarification_questions"], 3))
    if (status == "ready" and questions) or (status == "needs_clarification" and not questions):
        _reject("clarification_questions")

    definitions = _definitions(verification_evidence, verification_input_hash(profile))
    requirements = {r.requirement_id: r for r in profile.required_requirements}
    claims = {c.claim_id for c in profile.learner_claims}
    constraints = {c.constraint_id for c in profile.hard_constraints}
    learning = []
    learning_ids = set()
    for item in _array(data["learning_decisions"], 50):
        item = _object(item, LEARNING_FIELDS)
        key = _capability_id(item["capability_id"])
        if key in learning_ids:
            _reject("duplicate_capability")
        learning_ids.add(key)
        if item["learning_requirement"] not in {"required", "recommended"}:
            _reject("learning_requirement")
        if item["project_usage"] not in {"required", "optional", "excluded"}:
            _reject("project_usage")
        if item["desired_depth"] not in {"foundation", "applied", "deep"}:
            _reject("desired_depth")
        req_refs = _refs(item["requirement_refs"], requirements)
        target_refs = _refs(item["learning_target_refs"], req_refs)
        if any(requirements[ref].origin != "explicit" for ref in target_refs):
            _reject("explicit_learning_target")
        _text(item["project_usage_rationale"], 2000)
        _text(item["selection_rationale"], 2000)
        definition = definitions.get(key)
        learning.append({
            "capability_id": key,
            "disposition": "needs_learning",
            "learning_requirement": item["learning_requirement"],
            "project_usage": item["project_usage"],
            "desired_depth": item["desired_depth"],
            "requirement_refs": list(req_refs),
            "policy_refs": list(definition.policy_refs) if definition else [],
            "learner_claim_refs": [],
            "prerequisite_refs": list(definition.real_prerequisites) if definition else [],
            "learning_target_refs": list(target_refs),
        })

    claim_bindings = []
    claim_mapping_caps = {claim: set() for claim in claims}
    mapped_known = {}
    seen_group_ids = set()
    null_group_seen = False
    for group in _array(data["claim_decisions"], 50):
        group = _object(group, CLAIM_DECISION_FIELDS)
        key = group["capability_id"]
        req_refs = _refs(group["requirement_refs"], requirements)
        mappings = []
        for mapping in _array(group["claim_mappings"], 50):
            mapping = _object(mapping, CLAIM_MAPPING_FIELDS)
            ref = _text(mapping["claim_ref"], 200)
            if ref not in claims:
                _reject("claim_binding")
            _text(mapping["mapping_rationale"], 2000)
            mappings.append(ref)
        if not mappings or len(mappings) != len(set(mappings)):
            _reject("claim_binding")
        if key is None:
            if (null_group_seen or group["project_usage"] is not None
                    or group["project_usage_rationale"] is not None or req_refs):
                _reject("unmapped_claim_decision")
            null_group_seen = True
            for ref in mappings:
                claim_mapping_caps[ref].add(None)
                claim_bindings.append({"claim_ref": ref, "capability_id": None})
            continue

        key = _capability_id(key)
        if key in seen_group_ids:
            _reject("duplicate_claim_capability")
        seen_group_ids.add(key)
        definition = definitions.get(key)
        if definition is None:
            _reject("known_claim_definition")
        if key in learning_ids:
            _reject("known_learning_overlap")
        if group["project_usage"] not in {"required", "optional", "excluded"}:
            _reject("project_usage")
        _text(group["project_usage_rationale"], 2000)
        known_claim_refs = tuple(sorted(mappings))
        for ref in known_claim_refs:
            claim_mapping_caps[ref].add(key)
            claim_bindings.append({"claim_ref": ref, "capability_id": key})
        mapped_known[key] = {
            "capability_id": key,
            "disposition": "accepted_known",
            # Known capabilities are outside B/learning; this neutral legacy
            # field is not used to create coverage or a learning obligation.
            "learning_requirement": "recommended",
            "project_usage": group["project_usage"],
            "desired_depth": definition.default_depth,
            "requirement_refs": list(req_refs),
            "policy_refs": list(definition.policy_refs),
            "learner_claim_refs": list(known_claim_refs),
            "prerequisite_refs": list(definition.real_prerequisites),
            "learning_target_refs": [],
        }

    for _claim, capability_ids in claim_mapping_caps.items():
        if not capability_ids or None in capability_ids and capability_ids != {None}:
            _reject("claim_binding_coverage")
    for key in mapped_known:
        if key in learning_ids:
            _reject("known_learning_overlap")

    constraint_effects = []
    for item in _array(data["constraint_effects"], 20):
        item = _object(item, CONSTRAINT_FIELDS)
        if item["constraint_ref"] not in constraints:
            _reject("constraint_effect")
        if item["exclusion"] not in {"learning", "project", "not_applicable"}:
            _reject("constraint_effect")
        constraint_effects.append(dict(item))

    standard_wire = {
        "schema_version": 1,
        "source_goal_profile_hash": profile.profile_hash,
        "policy_version": CAPABILITY_POLICY.version,
        "route_kind": route,
        "status": status,
        "capabilities": list(mapped_known.values()) + learning,
        "claim_bindings": claim_bindings,
        "constraint_effects": constraint_effects,
        "clarification_questions": list(questions),
    }
    # The frozen V1 Domain validator remains the one source of standard
    # CapabilityPlan identity, dependency, Policy and pending semantics.
    return CapabilityPlanValidator().validate(
        standard_wire, profile=profile, verification_evidence=verification_evidence
    )


def normalize_capability_decision(raw, *, profile, verification_evidence=()):
    """Normalize the V2 decision wire into the unchanged, strict standard Plan."""
    try:
        return _normalize(raw, profile=profile, verification_evidence=tuple(verification_evidence))
    except (TypeError, ValueError, KeyError, AttributeError):
        _reject("typed_input")

