"""Bounded research metadata; temporary teaching body is never retained here."""
import json
import re
from dataclasses import asdict, dataclass, fields, replace
from datetime import datetime

from app.core.errors import ValidationAppError
from app.core.ids import canonical_json, content_hash
from app.domain.planning.capability_policy import LearningOutcome
from app.domain.planning.goal_requirements import HardConstraint, LearnerClaim

METRICS = ("searches", "candidates", "body_bytes", "reader_requests", "output_tokens", "total_requests", "cost_micros")


def reject(field):
    raise ValidationAppError("Teaching Resource Research 合同校验失败", field=field)


def _hash(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        reject("hash")


def _text(value, limit=500):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        reject("text")


def _amount(value):
    if type(value) is not int or not 0 <= value <= 10**12:
        reject("budget_amount")


def _tuple(value, kind, limit):
    if not isinstance(value, (tuple, list)) or len(value) > limit or any(type(v) is not kind for v in value):
        reject("metadata_sequence")
    return tuple(value)


def _timestamp(value):
    _text(value, 100)
    try:
        if datetime.fromisoformat(value).tzinfo is None:
            reject("timestamp")
    except ValueError:
        reject("timestamp")


@dataclass(frozen=True, slots=True)
class ResearchBudget:
    max_searches: int = 4
    max_candidates: int = 8
    max_body_bytes: int = 262144
    max_reader_requests: int = 4
    max_output_tokens: int = 4096
    max_total_requests: int = 16
    max_cost_micros: int = 100000
    search_cost_micros: int = 1000
    reader_cost_micros: int = 20000

    def __post_init__(self):
        # cost_micros is the same integer micro-cost unit as provider accounting.
        for field in fields(self):
            _amount(getattr(self, field.name))


@dataclass(frozen=True, slots=True)
class ReviewedAccessProof:
    source_id: str
    source_version: int
    content_hash: str
    reference: str
    access: str

    def __post_init__(self):
        _text(self.source_id)
        _text(self.reference, 1024)
        _hash(self.content_hash)
        if type(self.source_version) is not int or self.source_version < 1 or self.access not in {"free_public", "unknown", "paid"}:
            reject("access_proof")


@dataclass(frozen=True, slots=True)
class ResearchRequirement:
    capability_id: str
    must_teach: tuple[LearningOutcome, ...]
    importance: str
    desired_depth: str
    requirement_refs: tuple[str, ...]
    starting_point: str
    hard_constraints: tuple[HardConstraint, ...]
    learner_claims: tuple[LearnerClaim, ...]

    def __post_init__(self):
        _text(self.capability_id, 200)
        outcomes = _tuple(self.must_teach, LearningOutcome, 20)
        if not outcomes or len({o.outcome_id for o in outcomes}) != len(outcomes):
            reject("requirement_outcomes")
        for outcome in outcomes:
            if replace(outcome) != outcome:
                reject("requirement_outcome")
        object.__setattr__(self, "must_teach", outcomes)
        if self.importance not in {"required", "recommended"} or self.desired_depth not in {"foundation", "applied", "deep"}:
            reject("requirement_scope")
        refs = _tuple(self.requirement_refs, str, 50)
        if len(refs) != len(set(refs)):
            reject("requirement_refs")
        for ref in refs:
            if not ref.startswith("req_"):
                reject("requirement_refs")
            _hash(ref[4:])
        object.__setattr__(self, "requirement_refs", refs)
        if not isinstance(self.starting_point, str) or len(self.starting_point) > 1000:
            reject("starting_point")
        for name, kind in (("hard_constraints", HardConstraint), ("learner_claims", LearnerClaim)):
            facts = _tuple(getattr(self, name), kind, 20)
            if any(type(f.source_refs) is not tuple or not f.source_refs or any(type(r) is not str for r in f.source_refs)
                   or not isinstance(f.text, str) or len(f.text) > 2000 for f in facts):
                reject("requirement_facts")
            object.__setattr__(self, name, facts)


@dataclass(frozen=True, slots=True)
class ResearchEvidenceRef:
    outcome_id: str
    reference: str
    sha256: str
    location: str
    hash_scope: str

    def __post_init__(self):
        for value in (self.outcome_id, self.reference, self.location):
            _text(value, 1024)
        _hash(self.sha256)
        if self.hash_scope not in {"body", "review_record"}:
            reject("hash_scope")


@dataclass(frozen=True, slots=True)
class ResearchResource:
    resource_id: str
    url: str
    version: str
    checked_at: str
    free_access: str
    qualification: str
    evidence: tuple[ResearchEvidenceRef, ...]
    teaching_fit: tuple[tuple[str, str], ...]
    limitations: tuple[str, ...]

    def __post_init__(self):
        for value in (self.resource_id, self.url, self.version, self.checked_at):
            _text(value, 4096)
        if self.free_access not in {"confirmed", "unknown", "paid"} or self.qualification not in {
                "public_reviewed", "research_checked", "candidate"}:
            reject("resource_qualification")
        _timestamp(self.checked_at)
        object.__setattr__(self, "evidence", _tuple(self.evidence, ResearchEvidenceRef, 40))
        fit = _tuple(self.teaching_fit, tuple, 5)
        if any(len(pair) != 2 or any(type(v) is not str or len(v) > 160 for v in pair) for pair in fit):
            reject("teaching_fit")
        object.__setattr__(self, "teaching_fit", tuple(sorted(fit)))
        object.__setattr__(self, "limitations", _tuple(self.limitations, str, 12))
        if len(self.evidence) > 40 or any(type(ref) is not ResearchEvidenceRef for ref in self.evidence):
            reject("research_evidence")
        object.__setattr__(self, "evidence", tuple(sorted(set(self.evidence), key=lambda r: (r.outcome_id, r.reference))))
        if len(self.limitations) > 12 or any(not isinstance(v, str) or len(v) > 160 for v in self.limitations):
            reject("limitations")


@dataclass(frozen=True, slots=True)
class ResearchEntry:
    requirement: ResearchRequirement
    status: str
    resources: tuple[ResearchResource, ...]
    unresolved_outcomes: tuple[LearningOutcome, ...]
    reason_codes: tuple[str, ...]

    def __post_init__(self):
        if type(self.requirement) is not ResearchRequirement or replace(self.requirement) != self.requirement:
            reject("research_requirement")
        resources = _tuple(self.resources, ResearchResource, 500)
        if any(replace(r) != r for r in resources) or len({(r.resource_id, r.version) for r in resources}) != len(resources):
            reject("entry_resources")
        object.__setattr__(self, "resources", tuple(sorted(resources, key=lambda r: (r.resource_id, r.version))))
        missing = _tuple(self.unresolved_outcomes, LearningOutcome, 20)
        if len({o.outcome_id for o in missing}) != len(missing) or any(o not in self.requirement.must_teach for o in missing):
            reject("unresolved_outcomes")
        wanted = {o.outcome_id for o in self.requirement.must_teach}
        supported = {ref.outcome_id for resource in resources for ref in resource.evidence}
        if supported - wanted:
            reject("resource_outcome_range")
        resolved = {ref.outcome_id for resource in resources if resource.free_access == "confirmed"
                    and resource.qualification in {"public_reviewed", "research_checked"} for ref in resource.evidence}
        if set(o.outcome_id for o in missing) != wanted - resolved:
            reject("research_partition")
        expected = "resolved" if not missing else "partial" if len(missing) < len(wanted) else "unresolved"
        if self.status != expected:
            reject("research_status")
        reasons = _tuple(self.reason_codes, str, 20)
        if missing and not reasons or any(not re.fullmatch(r"[a-z_]{1,80}", reason) for reason in reasons):
            reject("reason_codes")
        object.__setattr__(self, "reason_codes", tuple(sorted(set(reasons))))
        object.__setattr__(self, "unresolved_outcomes", missing)


@dataclass(frozen=True, slots=True)
class ResourceResearchResult:
    source_gap_set_hash: str
    source_capability_plan_hash: str
    source_coverage_result_hash: str
    source_profile_hash: str
    entries: tuple[ResearchEntry, ...]
    checked_at: str
    budget_usage: tuple[tuple[str, int], ...]

    def __post_init__(self):
        for value in (self.source_gap_set_hash, self.source_capability_plan_hash,
                      self.source_coverage_result_hash, self.source_profile_hash):
            _hash(value)
        _timestamp(self.checked_at)
        entries = _tuple(self.entries, ResearchEntry, 50)
        if any(replace(e) != e for e in entries) or len({e.requirement.capability_id for e in entries}) != len(entries):
            reject("research_entries")
        object.__setattr__(self, "entries", tuple(sorted(entries, key=lambda e: e.requirement.capability_id)))
        usage = _tuple(self.budget_usage, tuple, len(METRICS))
        if any(len(item) != 2 for item in usage) or len(usage) != len(METRICS) or set(dict(usage)) != set(METRICS):
            reject("budget_usage")
        for _, value in usage:
            _amount(value)
        object.__setattr__(self, "budget_usage", tuple(sorted(usage)))

    @property
    def result_hash(self):
        return content_hash(asdict(self))

    def to_payload(self):
        return json.loads(canonical_json(asdict(self) | {"result_hash": self.result_hash}))


@dataclass(frozen=True, slots=True)
class ResearchSnapshot:
    run_id: str
    input_hash: str
    budget: ResearchBudget
    usage: tuple[tuple[str, int], ...]
    blocked: bool
    pending_count: int
    unknown_measurement: bool
    config_hash: str
    inspected: tuple[tuple[str, tuple[ResearchResource, ...]], ...]
    completed: ResourceResearchResult | None


class ResearchSession:
    def __init__(self, run_id, input_hash, budget):
        _text(run_id, 200)
        _hash(input_hash)
        if type(budget) is not ResearchBudget:
            reject("budget")
        self.run_id, self.input_hash, self.budget = run_id, input_hash, budget
        self.usage = dict.fromkeys(METRICS, 0)
        self.blocked = False
        self.unknown_measurement = False
        self.config_hash = ""
        self.inspected = {}
        self.completed = None
        self._pending = {}
        self._next = 0

    def reserve(self, kind, **amounts):
        if self.blocked:
            return None
        if set(amounts) - set(METRICS):
            reject("budget_metric")
        for metric, value in amounts.items():
            _amount(value)
            if self.usage[metric] + value > getattr(self.budget, "max_" + metric):
                return None
        self._next += 1
        self._pending[self._next] = dict(amounts)
        for metric, value in amounts.items():
            self.usage[metric] += value
        return self._next

    def settle(self, reservation, **actual):
        reserved = self._pending[reservation]
        if set(actual) - set(reserved):
            self.blocked = True
            reject("settlement_metric")
        # Validate the entire receipt before changing any debit. Invalid data
        # leaves the reservation held and prevents another dispatch.
        try:
            for measured in actual.values():
                if measured is not None:
                    _amount(measured)
        except ValidationAppError:
            self.blocked = True
            raise
        self._pending.pop(reservation)
        exceeded = False
        for metric, worst in reserved.items():
            measured = actual.get(metric)
            if measured is None:
                self.unknown_measurement = True
                continue
            self.usage[metric] += measured - worst
            exceeded |= measured > worst
        # Account for all observed metrics even if an earlier one overran its
        # reservation; omitted/unknown measurements keep their worst debit.
        if exceeded:
            self.blocked = True
            reject("reservation_exceeded")

    def mark_unknown(self):
        self.blocked = True

    def snapshot(self):
        # Typed, content-free checkpoint boundary. Item 7 owns durable encoding
        # and save-before-dispatch. This in-memory object is not crash safety.
        return ResearchSnapshot(self.run_id, self.input_hash, self.budget, tuple(sorted(self.usage.items())),
            self.blocked, len(self._pending), self.unknown_measurement, self.config_hash,
            tuple(sorted(self.inspected.items())), self.completed)

    @classmethod
    def restore(cls, snapshot):
        if type(snapshot) is not ResearchSnapshot:
            reject("research_snapshot")
        session = cls(snapshot.run_id, snapshot.input_hash, snapshot.budget)
        _amount(snapshot.pending_count)
        if type(snapshot.blocked) is not bool or type(snapshot.unknown_measurement) is not bool:
            reject("snapshot_state")
        if snapshot.config_hash:
            _hash(snapshot.config_hash)
        if set(dict(snapshot.usage)) != set(METRICS):
            reject("snapshot_usage")
        for metric, value in snapshot.usage:
            _amount(value)
            if value > getattr(snapshot.budget, "max_" + metric) and not snapshot.blocked:
                reject("snapshot_usage")
        session.usage = dict(snapshot.usage)
        session.blocked = snapshot.blocked or snapshot.pending_count > 0
        session.unknown_measurement = snapshot.unknown_measurement
        session.config_hash = snapshot.config_hash
        inspected = _tuple(snapshot.inspected, tuple, 500)
        for key, findings in inspected:
            _text(key, 4096)
            _tuple(findings, ResearchResource, 500)
            if any(replace(f) != f for f in findings):
                reject("snapshot_findings")
        if len(dict(inspected)) != len(inspected):
            reject("snapshot_findings")
        session.inspected = dict(inspected)
        if snapshot.completed is not None and (type(snapshot.completed) is not ResourceResearchResult
                or replace(snapshot.completed) != snapshot.completed):
            reject("snapshot_result")
        session.completed = snapshot.completed
        return session


def research_input_hash(gap_set, plan, coverage, profile, budget, *, project_id, checked_at, actor_id):
    return content_hash({"gap_set": gap_set.result_hash, "plan": plan.plan_hash, "coverage": coverage.result_hash,
        "profile": profile.profile_hash, "budget": asdict(budget), "project_id": project_id,
        "actor_id": actor_id, "checked_at": checked_at})
