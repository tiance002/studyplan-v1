"""Item 2 references and frozen definitions; no NLP, curriculum or external I/O."""
import json
import re
from dataclasses import asdict, dataclass, fields
from graphlib import CycleError, TopologicalSorter

from app.core.errors import ValidationAppError
from app.core.ids import canonical_json, content_hash
from app.domain.planning.capability_policy import CAPABILITY_POLICY, CapabilityDefinition, LearningOutcome
from app.domain.planning.goal_requirements import GoalRequirementProfile

CAPABILITY_PURPOSE = "planning.capability_planning"
CAPABILITY_SCHEMA = "CapabilityPlanV1"
CAPABILITY_DECISION_SCHEMA = "CapabilityDecisionV2"
WIRE_FIELDS = {"schema_version", "source_goal_profile_hash", "policy_version", "route_kind", "status",
               "capabilities", "claim_bindings", "constraint_effects", "clarification_questions"}
ITEM_FIELDS = {"capability_id", "disposition", "learning_requirement", "project_usage", "desired_depth",
               "requirement_refs", "policy_refs", "learner_claim_refs", "prerequisite_refs", "learning_target_refs"}


def _reject(field):
    raise ValidationAppError("Capability Planning 合同校验失败", field=field)


def _object(raw, names):
    if not isinstance(raw, dict) or set(raw) != set(names):
        _reject("fields")
    return raw


def _array(raw, limit=50):
    if not isinstance(raw, (list, tuple)) or len(raw) > limit:
        _reject("array")
    return raw


def _text(raw, limit=2000):
    if not isinstance(raw, str) or not raw.strip() or len(raw) > limit:
        _reject("text")
    return raw


def _refs(raw, allowed=None):
    refs = tuple(_text(v, 200) for v in _array(raw, 50))
    if len(refs) != len(set(refs)) or allowed is not None and set(refs) - set(allowed):
        _reject("references")
    return tuple(sorted(refs))


def _capability_id(value):
    if not isinstance(value, str) or len(value) > 128 or not re.fullmatch(r"[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*", value):
        _reject("capability_id")
    return value


def _dag(definitions):
    try:
        tuple(TopologicalSorter({d.capability_id: set(d.real_prerequisites) for d in definitions}).static_order())
    except CycleError:
        _reject("prerequisite_cycle")


def verification_input_hash(profile):
    return content_hash({"profile": profile.to_payload(), "policy": CAPABILITY_POLICY.to_payload()})


@dataclass(frozen=True, slots=True)
class DomainVerificationEvidence:
    evidence_id: str
    input_hash: str
    source_refs: tuple[str, ...]
    limitations: tuple[str, ...]
    evidence_kind: str
    capabilities: tuple[CapabilityDefinition, ...]

    def __post_init__(self):
        for key in ("source_refs", "limitations", "capabilities"):
            object.__setattr__(self, key, tuple(getattr(self, key)))
        _text(self.evidence_id, 128)
        _text(self.input_hash, 128)
        if self.evidence_kind not in {"fixture", "source_verification"}:
            _reject("evidence_kind")
        if not self.source_refs or not self.limitations or not self.capabilities or len(self.capabilities) > 20:
            _reject("verification_evidence")
        _refs(self.source_refs)
        for limitation in _array(self.limitations, 20):
            _text(limitation)
        if any(not isinstance(d, CapabilityDefinition) for d in self.capabilities):
            _reject("verification_definition")

    def to_payload(self):
        return json.loads(canonical_json(asdict(self)))


def _evidence_from_payload(raw):
    raw = _object(raw, {f.name for f in fields(DomainVerificationEvidence)})
    definitions = []
    for entry in _array(raw["capabilities"], 20):
        entry = _object(entry, {f.name for f in fields(CapabilityDefinition)})
        outcomes = tuple(LearningOutcome(**_object(o, {"outcome_id", "text"}))
                         for o in _array(entry["learning_outcomes"], 20))
        definitions.append(CapabilityDefinition(**(entry | {"learning_outcomes": outcomes})))
    return DomainVerificationEvidence(**(raw | {"capabilities": tuple(definitions)}))


def _definitions(evidence, expected_hash):
    evidence = tuple(_array(evidence, 1))
    definitions = {d.capability_id: d for d in CAPABILITY_POLICY.definitions}
    outcome_ids = {o.outcome_id for d in definitions.values() for o in d.learning_outcomes}
    for item in evidence:
        if not isinstance(item, DomainVerificationEvidence) or item.input_hash != expected_hash:
            _reject("verification_input_hash")
        for d in item.capabilities:
            _capability_id(d.capability_id)
            if d.capability_id in definitions or d.policy_refs:
                _reject("verification_definition_override")
            for o in d.learning_outcomes:
                if o.outcome_id in outcome_ids:
                    _reject("outcome_identity")
                outcome_ids.add(o.outcome_id)
            definitions[d.capability_id] = d
    for d in definitions.values():
        if any(ref not in definitions or ref == d.capability_id for ref in d.real_prerequisites):
            _reject("verification_prerequisite")
    _dag(definitions.values())
    return definitions


def validate_capability_planning_input(payload, schema_name, *, allow_clarification=False):
    """Provider preflight checks serialized authority, never reinterprets raw GoalSpec."""
    try:
        _object(payload, {"profile", "policy", "verification_evidence"})
        if schema_name not in {CAPABILITY_SCHEMA, CAPABILITY_DECISION_SCHEMA}:
            return False
        raw = _object(payload["profile"], {f.name for f in fields(GoalRequirementProfile)} | {"profile_hash"})
        _text(raw["target_summary"])
        if raw["desired_depth"] not in {"unspecified", "foundation", "applied", "deep"}:
            return False
        if raw["outcome_purpose"] not in {"learn", "interview", "portfolio", "internship", "production"}:
            return False
        scope = tuple(_text(v, 300) for v in _array(raw["scope"], 20))
        if not isinstance(raw["starting_point"], str) or len(raw["starting_point"]) > 1000:
            return False
        if raw["project_context"] is not None:
            _text(raw["project_context"], 2000)
        questions = tuple(_text(v, 500) for v in _array(raw["clarification_questions"], 3))
        if raw["status"] not in {"ready", "needs_clarification"}:
            return False
        if raw["status"] == "needs_clarification" and (not allow_clarification or not questions):
            return False
        if raw["status"] == "ready" and (questions or not raw["required_requirements"]):
            return False
        allowed_sources = {"goal.target", "goal.desired_depth", "goal.outcome_purpose"}
        if scope:
            allowed_sources.add("goal.scope")
            allowed_sources.update(f"goal.scope[{i}]" for i in range(len(scope)))
        if raw["starting_point"].strip():
            allowed_sources.add("goal.starting_point")
        if raw["project_context"] is not None:
            allowed_sources.add("project_context")
        # Profile does not retain raw constraints. Only their bounded source
        # syntax is checkable here; original index existence remains Item 1's
        # validated provenance, never something a recomputed hash proves.
        allowed_sources.add("goal.constraints")
        allowed_sources.update(f"goal.constraints[{i}]" for i in range(20))
        # As with raw constraint indices, Item1 proves actual answer membership.
        # Downstream only retains bounded source syntax from the hashed Profile.
        allowed_sources.update(f"clarification.answers[{i}]" for i in range(6))
        body = {k: v for k, v in raw.items() if k != "profile_hash"}
        if (raw["schema_version"] != 1 or type(raw["schema_version"]) is not int
                or raw["profile_hash"] != content_hash(body)
                or canonical_json(payload["policy"]) != canonical_json(CAPABILITY_POLICY.to_payload())):
            return False
        for field, names, id_field, prefix in (
            ("required_requirements", {"requirement_id", "text", "origin", "source_refs", "rationale"}, "requirement_id", "req_"),
            ("hard_constraints", {"constraint_id", "text", "source_refs"}, "constraint_id", "constraint_"),
            ("learner_claims", {"claim_id", "text", "source_refs"}, "claim_id", "claim_"),
        ):
            ids = []
            for item in _array(raw[field], 50 if field == "required_requirements" else 20):
                _object(item, names)
                _text(item["text"])
                if field == "required_requirements":
                    if item["origin"] not in {"explicit", "inferred_required"}:
                        return False
                    if not isinstance(item["rationale"], str) or len(item["rationale"]) > 2000:
                        return False
                    if item["origin"] == "inferred_required" and not item["rationale"].strip():
                        return False
                if not _refs(_array(item["source_refs"], 10), allowed_sources):
                    return False
                expected = prefix + content_hash({k: v for k, v in item.items() if k != id_field})
                if item[id_field] != expected:
                    return False
                ids.append(item[id_field])
            if len(ids) != len(set(ids)):
                return False
        evidence = tuple(_evidence_from_payload(e) for e in _array(payload["verification_evidence"], 1))
        expected = content_hash({"profile": raw, "policy": payload["policy"]})
        _definitions(evidence, expected)
        return True
    except (ValidationAppError, TypeError, ValueError, AttributeError, KeyError):
        return False


@dataclass(frozen=True, slots=True)
class ClaimBinding:
    claim_ref: str
    capability_id: str | None


@dataclass(frozen=True, slots=True)
class ConstraintEffect:
    constraint_ref: str
    capability_id: str | None
    exclusion: str


@dataclass(frozen=True, slots=True)
class Capability:
    capability_id: str
    title: str
    disposition: str
    learning_requirement: str
    project_usage: str
    desired_depth: str
    learning_outcomes: tuple[LearningOutcome, ...]
    requirement_refs: tuple[str, ...]
    policy_refs: tuple[str, ...]
    learner_claim_refs: tuple[str, ...]
    prerequisite_refs: tuple[str, ...]
    learning_target_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CapabilityPlanningIssue:
    code: str
    refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CapabilityPlanningPending:
    status: str
    source_goal_profile_hash: str
    policy_version: str
    issues: tuple[CapabilityPlanningIssue, ...]
    clarification_questions: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CapabilityPlan:
    schema_version: int
    source_goal_profile_hash: str
    policy_version: str
    route_kind: str
    capabilities: tuple[Capability, ...]
    claim_bindings: tuple[ClaimBinding, ...]
    constraint_effects: tuple[ConstraintEffect, ...]
    verification_evidence: tuple[DomainVerificationEvidence, ...]

    @property
    def plan_hash(self):
        return content_hash(asdict(self))

    @property
    def learning_capabilities(self):
        return tuple(c for c in self.capabilities if c.disposition == "needs_learning")

    @property
    def accepted_known_capabilities(self):
        return tuple(c for c in self.capabilities if c.disposition == "accepted_known")

    @property
    def learning_outcomes(self):
        return tuple(o for c in self.learning_capabilities for o in c.learning_outcomes)

    def to_payload(self):
        return json.loads(canonical_json(asdict(self) | {"plan_hash": self.plan_hash}))


class CapabilityPlanValidator:
    """Proves reference/authority rules, not truth of semantic model bindings."""

    def validate(self, raw, *, profile, verification_evidence=()):
        if not isinstance(profile, GoalRequirementProfile) or profile.status != "ready":
            _reject("upstream_profile")
        definitions = _definitions(verification_evidence, verification_input_hash(profile))
        data = _object(raw, WIRE_FIELDS)
        if (type(data["schema_version"]) is not int or data["schema_version"] != 1
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
        if status == "ready" and questions or status == "needs_clarification" and not questions:
            _reject("clarification_questions")
        requirements = {r.requirement_id: r for r in profile.required_requirements}
        claims = {c.claim_id for c in profile.learner_claims}
        constraints = {c.constraint_id for c in profile.hard_constraints}
        items = []
        ids = []
        for item in _array(data["capabilities"]):
            item = _object(item, ITEM_FIELDS)
            key = _capability_id(item["capability_id"])
            ids.append(key)
            disposition = item["disposition"]
            if disposition not in {"accepted_known", "needs_learning"}:
                _reject("disposition")
            if item["learning_requirement"] not in {"required", "recommended"}:
                _reject("learning_requirement")
            if item["project_usage"] not in {"required", "optional", "excluded"}:
                _reject("project_usage")
            if item["desired_depth"] not in {"foundation", "applied", "deep"}:
                _reject("desired_depth")
            req_refs = _refs(item["requirement_refs"], requirements)
            claim_refs = _refs(item["learner_claim_refs"], claims)
            targets = _refs(item["learning_target_refs"], req_refs)
            if any(requirements[r].origin != "explicit" for r in targets):
                _reject("explicit_learning_target")
            if disposition == "accepted_known" and (not claim_refs or targets):
                _reject("accepted_known_learning_target")
            if disposition == "needs_learning" and claim_refs:
                _reject("learning_claim_conflict")
            prereqs = _refs(item["prerequisite_refs"])
            policy_refs = _refs(item["policy_refs"])
            definition = definitions.get(key)
            if definition:
                if set(prereqs) != set(definition.real_prerequisites) or set(policy_refs) != set(definition.policy_refs):
                    _reject("definition_refs")
            elif policy_refs:
                _reject("unknown_policy_ref")
            items.append((item, req_refs, claim_refs, targets, prereqs, policy_refs))
        if len(ids) != len(set(ids)):
            _reject("duplicate_capability")
        for _, _, _, _, prereqs, _ in items:
            if set(prereqs) - set(ids):
                _reject("prerequisite_refs")
        try:
            tuple(TopologicalSorter({i[0]["capability_id"]: set(i[4]) for i in items}).static_order())
        except CycleError:
            _reject("prerequisite_cycle")
        bindings = []
        for binding in _array(data["claim_bindings"]):
            _object(binding, {"claim_ref", "capability_id"})
            if binding["claim_ref"] not in claims or binding["capability_id"] is not None and binding["capability_id"] not in ids:
                _reject("claim_binding")
            bindings.append(ClaimBinding(**binding))
        if {b.claim_ref for b in bindings} != claims or len(bindings) != len(set(bindings)):
            _reject("claim_binding_coverage")
        if any(b.capability_id is None and any(other.claim_ref == b.claim_ref and other.capability_id is not None
                                               for other in bindings) for b in bindings):
            _reject("claim_binding_contradiction")
        for item, _, claim_refs, _, _, _ in items:
            bound = {b.claim_ref for b in bindings if b.capability_id == item["capability_id"]}
            if bound != set(claim_refs):
                _reject("claim_disposition")
        effects = []
        for effect in _array(data["constraint_effects"]):
            _object(effect, {"constraint_ref", "capability_id", "exclusion"})
            if effect["constraint_ref"] not in constraints or effect["exclusion"] not in {"learning", "project", "not_applicable"}:
                _reject("constraint_effect")
            key = effect["capability_id"]
            if effect["exclusion"] == "not_applicable":
                if key is not None:
                    _reject("constraint_effect")
            elif key not in definitions:
                _reject("constraint_capability_ref")
            effects.append(ConstraintEffect(**effect))
        if {e.constraint_ref for e in effects} != constraints or len(effects) != len(set(effects)):
            _reject("constraint_effect_coverage")
        issues = []
        for item, _, _, _, _, _ in items:
            for effect in effects:
                if effect.capability_id != item["capability_id"]:
                    continue
                if effect.exclusion == "learning" and item["disposition"] == "needs_learning":
                    issues.append(CapabilityPlanningIssue("constraint_learning_conflict", (effect.constraint_ref, effect.capability_id)))
                if effect.exclusion == "project" and item["project_usage"] != "excluded":
                    issues.append(CapabilityPlanningIssue("constraint_project_conflict", (effect.constraint_ref, effect.capability_id)))
        if route == "systematic_agent_route":
            mcp = next((i[0] for i in items if i[0]["capability_id"] == "mcp"), None)
            if mcp is None or mcp["learning_requirement"] != "required":
                issues.append(CapabilityPlanningIssue("systematic_mcp_required", (CAPABILITY_POLICY.systematic_mcp_policy_ref,)))
        unknown = tuple(key for key in ids if key not in definitions)
        if route == "uncertain":
            issues.append(CapabilityPlanningIssue("route_requires_clarification", ()))
        if status != "ready":
            issues.append(CapabilityPlanningIssue("model_" + status, ()))
        if unknown:
            issues.append(CapabilityPlanningIssue("domain_verification_required", unknown))
        if issues:
            pending_status = "needs_clarification" if any(i.code not in {"domain_verification_required", "model_needs_verification"}
                                                         for i in issues) else "needs_verification"
            if pending_status == "needs_clarification" and not questions:
                if route == "systematic_agent_route":
                    questions = ("请选择系统性Agent学习路线（包含MCP学习），还是保留当前限制并调整目标范围？",)
                elif any(i.code.startswith("constraint_") for i in issues):
                    questions = ("该限制与所选能力冲突：希望保留限制并调整目标范围，还是修改限制？",)
                else:
                    questions = ("本次是系统学习Agent开发，还是只完成所述具体目标？",)
            return CapabilityPlanningPending(pending_status, profile.profile_hash, CAPABILITY_POLICY.version,
                                             tuple(issues), questions)
        if not items or set(requirements) - {r for i in items for r in i[1]}:
            _reject("required_requirement_coverage")
        dependents = {ref for i in items for ref in i[4]}
        capabilities = []
        for item, req_refs, claim_refs, targets, prereqs, policy_refs in items:
            key = item["capability_id"]
            if not req_refs and key not in dependents and not (route == "systematic_agent_route" and key == "mcp"):
                _reject("capability_without_requirement")
            definition = definitions[key]
            if route == "systematic_agent_route" and key == "mcp":
                policy_refs = tuple(sorted((*policy_refs, CAPABILITY_POLICY.systematic_mcp_policy_ref)))
            capabilities.append(Capability(key, definition.title, item["disposition"], item["learning_requirement"],
                item["project_usage"], item["desired_depth"], CAPABILITY_POLICY.outcomes_for(
                    definition, route_kind=route, desired_depth=item["desired_depth"]),
                req_refs, policy_refs, claim_refs, prereqs, targets))
        return CapabilityPlan(1, profile.profile_hash, CAPABILITY_POLICY.version, route,
                              tuple(sorted(capabilities, key=lambda c: c.capability_id)),
                              tuple(sorted(bindings, key=lambda b: (b.claim_ref, b.capability_id or ""))),
                              tuple(sorted(effects, key=lambda e: (e.constraint_ref, e.capability_id or "", e.exclusion))),
                              tuple(verification_evidence))
