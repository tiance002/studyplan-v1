"""Deterministic reviewed coverage of the frozen needs-learning set."""
import json
import re
from dataclasses import asdict, dataclass
from graphlib import CycleError, TopologicalSorter

from app.core.errors import ValidationAppError
from app.core.ids import canonical_json, content_hash
from app.domain.planning.capabilities import (
    Capability,
    CapabilityPlan,
    ClaimBinding,
    ConstraintEffect,
    _definitions,
)
from app.domain.planning.capability_policy import CAPABILITY_POLICY


def _reject(field):
    raise ValidationAppError("Reviewed Content Coverage 合同校验失败", field=field)


def _text(value, limit=500):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        _reject("text")
    return value


def _hash(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        _reject("hash")
    return value


def _sequence(values, limit=2000):
    if not isinstance(values, (list, tuple)) or len(values) > limit:
        _reject("sequence")
    return tuple(values)


def _strings(values, limit=2000):
    return tuple(sorted({_text(v) for v in _sequence(values, limit)}))


def _records(values, kind, limit=2000):
    values = _sequence(values, limit)
    if any(type(v) is not kind for v in values):
        _reject("record_type")
    unique = {canonical_json(asdict(v)): v for v in values}
    return tuple(unique[key] for key in sorted(unique))


def _version(value):
    if type(value) is not int or value < 1:
        _reject("version")


def _identity(record):
    return (record.content_id, record.content_version, record.source_id, record.source_version, record.section_id)


def _record_identity(record):
    for field in ("content_id", "source_id", "section_id"):
        _text(getattr(record, field))
    _version(record.content_version)
    _version(record.source_version)


@dataclass(frozen=True, slots=True)
class ReviewEvidence:
    reference: str
    sha256: str
    section_ids: tuple[str, ...]
    supported_outcomes: tuple[str, ...]
    review_depth: str
    limitations: tuple[str, ...]

    def __post_init__(self):
        _text(self.reference)
        _hash(self.sha256)
        _text(self.review_depth)
        for field in ("section_ids", "supported_outcomes", "limitations"):
            object.__setattr__(self, field, _strings(getattr(self, field)))
        if not self.section_ids:
            _reject("evidence_section_ids")


@dataclass(frozen=True, slots=True)
class ReviewedSection:
    content_id: str
    content_version: int
    content_hash: str
    source_id: str
    source_version: int
    section_id: str
    source_verification_status: str
    verification_status: str
    review_depth: str
    review_refs: tuple[str, ...]

    def __post_init__(self):
        _record_identity(self)
        _hash(self.content_hash)
        for field in ("source_verification_status", "verification_status", "review_depth"):
            _text(getattr(self, field))
        object.__setattr__(self, "review_refs", _strings(self.review_refs))


@dataclass(frozen=True, slots=True)
class OutcomeMapping:
    outcome_id: str
    content_id: str
    content_version: int
    source_id: str
    source_version: int
    section_id: str
    review_refs: tuple[str, ...]

    def __post_init__(self):
        _record_identity(self)
        _text(self.outcome_id)
        object.__setattr__(self, "review_refs", _strings(self.review_refs))
        if not self.review_refs:
            _reject("mapping_review_refs")


@dataclass(frozen=True, slots=True)
class ReviewedContentIndex:
    version: str
    sections: tuple[ReviewedSection, ...]
    mappings: tuple[OutcomeMapping, ...]
    evidence: tuple[ReviewEvidence, ...]
    policy_version: str = "v2"

    def __post_init__(self):
        _text(self.version)
        _text(self.policy_version)
        for field, kind, limit in (("sections", ReviewedSection, 2000), ("mappings", OutcomeMapping, 10000),
                                   ("evidence", ReviewEvidence, 2000)):
            object.__setattr__(self, field, _records(getattr(self, field), kind, limit))

    @property
    def index_hash(self):
        return content_hash(asdict(self))


@dataclass(frozen=True, slots=True)
class CoverageContentRef:
    section: ReviewedSection
    outcome_ids: tuple[str, ...]
    evidence: tuple[ReviewEvidence, ...]

    def __post_init__(self):
        if type(self.section) is not ReviewedSection:
            _reject("content_ref_section")
        object.__setattr__(self, "outcome_ids", _strings(self.outcome_ids))
        object.__setattr__(self, "evidence", _records(self.evidence, ReviewEvidence))


@dataclass(frozen=True, slots=True)
class CoverageEntry:
    capability_id: str
    coverage: str
    covered_outcomes: tuple[str, ...]
    missing_outcomes: tuple[str, ...]
    content_refs: tuple[CoverageContentRef, ...]

    def __post_init__(self):
        _text(self.capability_id)
        _text(self.coverage)
        for field in ("covered_outcomes", "missing_outcomes"):
            object.__setattr__(self, field, _strings(getattr(self, field)))
        object.__setattr__(self, "content_refs", _records(self.content_refs, CoverageContentRef))


@dataclass(frozen=True, slots=True)
class CoverageResult:
    source_capability_plan_hash: str
    content_index_version: str
    content_index_hash: str
    entries: tuple[CoverageEntry, ...]

    def __post_init__(self):
        _hash(self.source_capability_plan_hash)
        _text(self.content_index_version)
        _hash(self.content_index_hash)
        entries = _sequence(self.entries, 50)
        if any(type(e) is not CoverageEntry for e in entries):
            _reject("coverage_entries")
        object.__setattr__(self, "entries", tuple(sorted(entries, key=lambda e: e.capability_id)))

    @property
    def result_hash(self):
        return content_hash(asdict(self))

    def to_payload(self):
        return json.loads(canonical_json(asdict(self) | {"result_hash": self.result_hash}))


def _plan_definitions(plan):
    """Recheck frozen structure, without inventing the absent upstream Profile.

    Evidence input_hash and original claim/requirement provenance remain trusted
    Item 2 inputs. Hash syntax here does not re-prove their original binding.
    """
    if type(plan) is not CapabilityPlan or type(plan.schema_version) is not int or plan.schema_version != 1:
        _reject("capability_plan")
    if plan.policy_version != CAPABILITY_POLICY.version or plan.route_kind not in {"systematic_agent_route", "narrow_goal", "other"}:
        _reject("plan_policy_route")
    _hash(plan.source_goal_profile_hash)
    evidence = _sequence(plan.verification_evidence, 1)
    expected_hash = _hash(evidence[0].input_hash) if evidence else ""
    definitions = _definitions(evidence, expected_hash)
    capabilities = _sequence(plan.capabilities, 50)
    if not capabilities or any(type(c) is not Capability for c in capabilities):
        _reject("plan_capabilities")
    ids = {c.capability_id for c in capabilities}
    if len(ids) != len(capabilities):
        _reject("duplicate_capability")
    dependents = {ref for c in capabilities for ref in _sequence(c.prerequisite_refs, 50)}
    for c in capabilities:
        definition = definitions.get(c.capability_id)
        if definition is None or c.title != definition.title:
            _reject("definition")
        if c.disposition not in {"accepted_known", "needs_learning"} or c.learning_requirement not in {"required", "recommended"}:
            _reject("disposition")
        if c.project_usage not in {"required", "optional", "excluded"} or c.desired_depth not in {"foundation", "applied", "deep"}:
            _reject("capability_scope")
        expected_refs = definition.policy_refs
        if plan.route_kind == "systematic_agent_route" and c.capability_id == "mcp":
            expected_refs = tuple(sorted((*expected_refs, CAPABILITY_POLICY.systematic_mcp_policy_ref)))
        if (tuple(c.policy_refs) != expected_refs or tuple(c.prerequisite_refs) != tuple(sorted(definition.real_prerequisites))
                or set(c.prerequisite_refs) - ids or c.capability_id in c.prerequisite_refs
                or tuple(c.learning_outcomes) != CAPABILITY_POLICY.outcomes_for(
                    definition, route_kind=plan.route_kind, desired_depth=c.desired_depth)):
            _reject("definition_authority")
        for field, prefix in (("requirement_refs", "req_"), ("learner_claim_refs", "claim_"), ("learning_target_refs", "req_")):
            refs = _sequence(getattr(c, field), 50)
            if len(refs) != len(set(refs)) or any(not isinstance(r, str) or not r.startswith(prefix) for r in refs):
                _reject("plan_references")
            for ref in refs:
                _hash(ref[len(prefix):])
        if set(c.learning_target_refs) - set(c.requirement_refs):
            _reject("learning_target_refs")
        if c.disposition == "accepted_known" and (not c.learner_claim_refs or c.learning_target_refs):
            _reject("accepted_known")
        if c.disposition == "needs_learning" and c.learner_claim_refs:
            _reject("learning_claim_conflict")
        if not c.requirement_refs and c.capability_id not in dependents and not (
                plan.route_kind == "systematic_agent_route" and c.capability_id == "mcp"):
            _reject("requirement_refs")
    try:
        tuple(TopologicalSorter({c.capability_id: set(c.prerequisite_refs) for c in capabilities}).static_order())
    except CycleError:
        _reject("prerequisite_cycle")
    bindings = _sequence(plan.claim_bindings, 50)
    if any(type(b) is not ClaimBinding for b in bindings) or len(bindings) != len(set(bindings)):
        _reject("claim_bindings")
    for binding in bindings:
        if not isinstance(binding.claim_ref, str) or not binding.claim_ref.startswith("claim_"):
            _reject("claim_ref")
        _hash(binding.claim_ref[6:])
        if binding.capability_id is not None and binding.capability_id not in ids:
            _reject("claim_capability_ref")
        if binding.capability_id is None and any(b.claim_ref == binding.claim_ref and b.capability_id is not None for b in bindings):
            _reject("claim_binding_contradiction")
    for c in capabilities:
        if set(c.learner_claim_refs) != {b.claim_ref for b in bindings if b.capability_id == c.capability_id}:
            _reject("claim_disposition")
    effects = _sequence(plan.constraint_effects, 50)
    if any(type(e) is not ConstraintEffect for e in effects) or len(effects) != len(set(effects)):
        _reject("constraint_effects")
    for effect in effects:
        if not isinstance(effect.constraint_ref, str) or not effect.constraint_ref.startswith("constraint_"):
            _reject("constraint_ref")
        _hash(effect.constraint_ref[11:])
        if effect.exclusion == "not_applicable":
            if effect.capability_id is not None:
                _reject("constraint_scope")
        elif effect.exclusion not in {"learning", "project"} or effect.capability_id not in definitions:
            _reject("constraint_scope")
        for c in capabilities:
            if c.capability_id == effect.capability_id and (
                    effect.exclusion == "learning" and c.disposition == "needs_learning"
                    or effect.exclusion == "project" and c.project_usage != "excluded"):
                _reject("constraint_conflict")
    if plan.route_kind == "systematic_agent_route" and not any(
            c.capability_id == "mcp" and c.learning_requirement == "required" for c in capabilities):
        _reject("systematic_mcp_required")
    _hash(plan.plan_hash)
    return definitions


def _qualified_mappings(index, definitions):
    if type(index) is not ReviewedContentIndex or index.policy_version != CAPABILITY_POLICY.version:
        _reject("content_index_policy")
    sections = {_identity(s): s for s in index.sections}
    evidence = {e.reference: e for e in index.evidence}
    if len(sections) != len(index.sections) or len(evidence) != len(index.evidence):
        _reject("index_identity_conflict")
    allowed_outcomes = {outcome.outcome_id for definition in definitions.values()
                        for outcome in definition.learning_outcomes}
    qualified = {}
    for mapping in index.mappings:
        if mapping.outcome_id not in allowed_outcomes:
            _reject("mapping_outcome_identity")
        section = sections.get(_identity(mapping))
        if section is None or not set(mapping.review_refs) <= set(section.review_refs):
            _reject("mapping_identity_review_refs")
        if (section.source_verification_status != "reviewed" or section.verification_status != "reviewed"
                or section.review_depth != "selected_sections_read"):
            _reject("mapping_body_qualification")
        reviews = []
        for reference in mapping.review_refs:
            review = evidence.get(reference)
            if (review is None or section.section_id not in review.section_ids
                    or mapping.outcome_id not in review.supported_outcomes
                    or review.review_depth != "selected_sections_read"):
                _reject("mapping_review_evidence")
            reviews.append(review)
        qualified.setdefault(mapping.outcome_id, []).append((section, tuple(reviews)))
    return qualified


def _expected(plan, index):
    try:
        definitions = _plan_definitions(plan)
        qualified = _qualified_mappings(index, definitions)
        entries = []
        for capability in plan.learning_capabilities:
            outcome_ids = {o.outcome_id for o in capability.learning_outcomes}
            covered = tuple(sorted(outcome_ids & qualified.keys()))
            missing = tuple(sorted(outcome_ids - qualified.keys()))
            section_refs = {}
            for outcome_id in covered:
                for section, reviews in qualified[outcome_id]:
                    entry = section_refs.setdefault(_identity(section), (section, set(), {}))
                    entry[1].add(outcome_id)
                    entry[2].update({r.reference: r for r in reviews})
            refs = tuple(CoverageContentRef(section, tuple(outcomes), tuple(reviews.values()))
                         for section, outcomes, reviews in section_refs.values())
            coverage = "full" if not missing else "partial" if covered else "none"
            entries.append(CoverageEntry(capability.capability_id, coverage, covered, missing, refs))
        return CoverageResult(plan.plan_hash, index.version, index.index_hash, tuple(entries))
    except (TypeError, ValueError, AttributeError, KeyError):
        _reject("typed_input")


class CoverageEvaluator:
    def evaluate(self, plan: CapabilityPlan, index: ReviewedContentIndex) -> CoverageResult:
        return _expected(plan, index)


class CoverageResultValidator:
    def validate(self, result, *, plan: CapabilityPlan, index: ReviewedContentIndex) -> CoverageResult:
        if type(result) is not CoverageResult or result != _expected(plan, index):
            _reject("coverage_result")
        return result
