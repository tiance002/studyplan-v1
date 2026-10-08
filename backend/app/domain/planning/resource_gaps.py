"""Deterministic missing-outcome projection; no research or coverage decisions."""
import json
import re
from dataclasses import asdict, dataclass, replace

from app.core.errors import ValidationAppError
from app.core.ids import canonical_json, content_hash
from app.domain.planning.capabilities import CapabilityPlan
from app.domain.planning.capability_policy import LearningOutcome
from app.domain.planning.content_coverage import (
    CoverageContentRef,
    CoverageEntry,
    CoverageResult,
    ReviewedSection,
    ReviewEvidence,
    _plan_definitions,
)


def _reject(field):
    raise ValidationAppError("Resource Gap Extraction 合同校验失败", field=field)


def _hash(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        _reject("hash")


def _tuple(values, limit=50):
    if type(values) is not tuple or len(values) > limit:
        _reject("tuple")
    return values


def _identity(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 500:
        _reject("identity")


def _requirement_refs(values):
    values = _tuple(values)
    if len(values) != len(set(values)) or tuple(sorted(values)) != values:
        _reject("requirement_refs")
    for value in values:
        if not isinstance(value, str) or not value.startswith("req_"):
            _reject("requirement_ref")
        _hash(value[4:])


def _canonical(record, kind):
    # Invoke existing typed producer normalization and scalar validation without
    # re-evaluating body qualification or loading the absent source index.
    if type(record) is not kind or replace(record) != record:
        _reject("noncanonical_coverage")


@dataclass(frozen=True, slots=True)
class ResourceGap:
    capability_id: str
    missing_outcomes: tuple[LearningOutcome, ...]
    importance: str
    desired_depth: str
    requirement_refs: tuple[str, ...]

    def __post_init__(self):
        _identity(self.capability_id)
        if self.importance not in {"required", "recommended"} or self.desired_depth not in {"foundation", "applied", "deep"}:
            _reject("gap_scope")
        values = _tuple(self.missing_outcomes, 20)
        if not values or any(type(o) is not LearningOutcome for o in values):
            _reject("missing_outcomes")
        for outcome in values:
            _canonical(outcome, LearningOutcome)
        if len({o.outcome_id for o in values}) != len(values):
            _reject("duplicate_outcome")
        object.__setattr__(self, "missing_outcomes", tuple(sorted(values, key=lambda o: o.outcome_id)))
        _requirement_refs(self.requirement_refs)


@dataclass(frozen=True, slots=True)
class ResourceGapSet:
    source_capability_plan_hash: str
    source_coverage_result_hash: str
    gaps: tuple[ResourceGap, ...]

    def __post_init__(self):
        _hash(self.source_capability_plan_hash)
        _hash(self.source_coverage_result_hash)
        values = _tuple(self.gaps)
        if any(type(g) is not ResourceGap for g in values) or len({g.capability_id for g in values}) != len(values):
            _reject("gaps")
        for gap in values:
            _canonical(gap, ResourceGap)
        object.__setattr__(self, "gaps", tuple(sorted(values, key=lambda g: g.capability_id)))

    @property
    def result_hash(self):
        return content_hash(asdict(self))

    def to_payload(self):
        return json.loads(canonical_json(asdict(self) | {"result_hash": self.result_hash}))


def extract(capability_plan: CapabilityPlan, coverage_result: CoverageResult) -> ResourceGapSet:
    """Project exact missing objects; trust original Profile/index provenance.

    These two inputs permit structural validation and byte-identity binding.
    They cannot re-prove the absent Profile or source Index/body authenticity.
    """
    try:
        _plan_definitions(capability_plan)
        _tuple(capability_plan.capabilities)
        for capability in capability_plan.capabilities:
            _requirement_refs(capability.requirement_refs)
        plan_hash = content_hash(asdict(capability_plan))
        if capability_plan.plan_hash != plan_hash:
            _reject("computed_plan_hash")
        _canonical(coverage_result, CoverageResult)
        coverage_hash = content_hash(asdict(coverage_result))
        if coverage_result.result_hash != coverage_hash or coverage_result.source_capability_plan_hash != plan_hash:
            _reject("coverage_source_hash")
        capabilities = {c.capability_id: c for c in capability_plan.learning_capabilities}
        entries = _tuple(coverage_result.entries)
        if (len(entries) != len(capabilities) or len({e.capability_id for e in entries}) != len(entries)
                or {e.capability_id for e in entries} != set(capabilities)):
            _reject("coverage_entry_set")
        gaps = []
        for entry in entries:
            _canonical(entry, CoverageEntry)
            capability = capabilities[entry.capability_id]
            outcomes = {o.outcome_id: o for o in capability.learning_outcomes}
            covered = set(entry.covered_outcomes)
            missing = set(entry.missing_outcomes)
            if covered & missing or covered | missing != set(outcomes):
                _reject("coverage_partition")
            expected_status = "full" if not missing else "partial" if covered else "none"
            if entry.coverage != expected_status:
                _reject("coverage_status")
            referenced = set()
            section_ids = set()
            for reference in entry.content_refs:
                _canonical(reference, CoverageContentRef)
                _canonical(reference.section, ReviewedSection)
                section = reference.section
                identity = (section.content_id, section.content_version, section.source_id,
                            section.source_version, section.section_id)
                if identity in section_ids or not reference.outcome_ids or not set(reference.outcome_ids) <= covered:
                    _reject("coverage_content_ref")
                section_ids.add(identity)
                referenced.update(reference.outcome_ids)
                supported = set()
                for review in reference.evidence:
                    _canonical(review, ReviewEvidence)
                    if review.reference not in section.review_refs or section.section_id not in review.section_ids:
                        _reject("coverage_evidence_ref")
                    supported.update(review.supported_outcomes)
                if not set(reference.outcome_ids) <= supported:
                    _reject("coverage_evidence_outcomes")
            if referenced != covered:
                _reject("covered_reference_partition")
            if missing:
                gaps.append(ResourceGap(capability.capability_id, tuple(outcomes[key] for key in sorted(missing)),
                                        capability.learning_requirement, capability.desired_depth,
                                        capability.requirement_refs))
        return ResourceGapSet(plan_hash, coverage_hash, tuple(gaps))
    except (TypeError, ValueError, AttributeError, KeyError):
        _reject("typed_input")
