"""Server-owned approval boundary for frozen Item 2 extensions.

Approval objects are injected dependencies, never reconstructed from model JSON.
Source definitions/public descriptors are curated registry facts; a source label
or a matching hash supplied by a model cannot create an approval.
"""
import re
from dataclasses import asdict, dataclass, field, fields
from urllib.parse import urlsplit

from app.core.errors import ValidationAppError
from app.core.ids import canonical_json, content_hash
from app.domain.planning.capabilities import (
    CAPABILITY_SCHEMA,
    Capability,
    CapabilityPlan,
    ClaimBinding,
    ConstraintEffect,
    DomainVerificationEvidence,
    _definitions,
    _evidence_from_payload,
    validate_capability_planning_input,
    verification_input_hash,
)
from app.domain.planning.capability_policy import CAPABILITY_POLICY, CapabilityDefinition, LearningOutcome
from app.domain.planning.goal_requirements import GoalRequirementProfile

_ISSUER = object()  # Process-local only: not serialized, persisted, or rebuilt from JSON.


class _IssuedApproval:
    __slots__ = ("_key", "_digest")

    def __init__(self, key, digest):
        if key is not _ISSUER:
            _reject()
        object.__setattr__(self, "_key", key)
        object.__setattr__(self, "_digest", digest)

    def __setattr__(self, name, value):
        raise AttributeError("Issued approval marker is immutable")


def _reject():
    raise ValidationAppError("Domain verification authority rejected")


def _digest(value, length=64):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{%d}" % length, value):
        _reject()


def _profile(profile):
    if type(profile) is not GoalRequirementProfile:
        _reject()
    if not validate_capability_planning_input({"profile": profile.to_payload(), "policy": CAPABILITY_POLICY.to_payload(),
        "verification_evidence": []}, CAPABILITY_SCHEMA):
        _reject()


@dataclass(frozen=True, slots=True)
class TrustedDomainSource:
    source_id: str
    version: str
    repo_url: str
    commit_sha: str
    path: str
    blob_sha: str
    body_sha256: str
    capabilities: tuple[CapabilityDefinition, ...]
    public_outcome_ids: tuple[str, ...]
    limitations: tuple[str, ...]

    def __post_init__(self):
        _source(self)

    @property
    def source_hash(self):
        return content_hash(asdict(self))

    @property
    def reference(self):
        return "domain-source:" + self.source_id + "@" + self.version + "#" + self.source_hash


def _source(source):
    if type(source) is not TrustedDomainSource:
        _reject()
    for value in (source.source_id, source.version):
        if not isinstance(value, str) or not re.fullmatch(r"[a-zA-Z0-9_.-]{1,40}", value):
            _reject()
    if not isinstance(source.repo_url, str) or not re.fullmatch(
        r"https://github\.com/[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}", source.repo_url):
        _reject()
    if any(p in {".", ".."} for p in urlsplit(source.repo_url).path.split("/")[1:]):
        _reject()
    if (not isinstance(source.path, str) or len(source.path) > 255 or source.path.startswith("/")
        or any(p in {"", ".", ".."} for p in source.path.split("/"))
        or any(ord(c) <= 32 or c in "\\?#%:" for c in source.path)
        or not source.path.lower().endswith((".md", ".txt", ".rst"))):
        _reject()
    _digest(source.commit_sha, 40)
    _digest(source.blob_sha, 40)
    _digest(source.body_sha256)
    if any(type(getattr(source, name)) is not tuple for name in ("capabilities", "public_outcome_ids", "limitations")):
        _reject()
    probe = DomainVerificationEvidence("registry-check", "0" * 64, ("registry:server",), source.limitations,
        "source_verification", source.capabilities)
    _definitions((probe,), probe.input_hash)
    all_ids = {o.outcome_id for d in source.capabilities for o in d.learning_outcomes}
    # A full frozen plan carries definitions, so public approval is all-or-none
    # for this small source record, never a partial release of private text.
    if len(source.public_outcome_ids) != len(set(source.public_outcome_ids)) or source.public_outcome_ids and set(source.public_outcome_ids) != all_ids:
        _reject()
    if len(canonical_json(asdict(source)).encode("utf-8")) > 32768:
        _reject()


@dataclass(frozen=True, slots=True)
class DomainApproval:
    profile_hash: str
    source: TrustedDomainSource
    evidence: DomainVerificationEvidence
    plan_hash: str | None = None
    _issuer: object = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        _approval(self)

    @property
    def approval_hash(self):
        _approval(self)
        return _approval_digest(self)


def _approval(approval):
    if (type(approval) is not DomainApproval or type(approval._issuer) is not _IssuedApproval
        or approval._issuer._key is not _ISSUER or approval._issuer._digest != _approval_digest(approval)):
        _reject()
    _source(approval.source)
    _digest(approval.profile_hash)
    if approval.plan_hash is not None:
        _digest(approval.plan_hash)
    evidence = approval.evidence
    if type(evidence) is not DomainVerificationEvidence or evidence.evidence_kind != "source_verification":
        _reject()
    _digest(evidence.input_hash)
    expected_id = "domain_" + content_hash({"input_hash": evidence.input_hash, "source_hash": approval.source.source_hash})
    if (evidence.evidence_id != expected_id or evidence.source_refs != (approval.source.reference,)
        or evidence.capabilities != approval.source.capabilities or evidence.limitations != approval.source.limitations):
        _reject()
    _definitions((evidence,), evidence.input_hash)


def _approval_digest(approval):
    return content_hash({"profile_hash": approval.profile_hash, "source": asdict(approval.source),
        "evidence": asdict(approval.evidence), "plan_hash": approval.plan_hash})


def _issue_approval(profile, source):
    _profile(profile)
    _source(source)
    input_hash = verification_input_hash(profile)
    evidence = DomainVerificationEvidence("domain_" + content_hash({"input_hash": input_hash, "source_hash": source.source_hash}),
        input_hash, (source.reference,), source.limitations, "source_verification", source.capabilities)
    return _issue_bound_content(profile.profile_hash, source, evidence, None)


def _issue_bound_content(profile_hash, source, evidence, plan_hash):
    digest = content_hash({"profile_hash": profile_hash, "source": asdict(source), "evidence": asdict(evidence), "plan_hash": plan_hash})
    return DomainApproval(profile_hash, source, evidence, plan_hash, _IssuedApproval(_ISSUER, digest))


def bind_domain_approval(approval, plan):
    """Server-only transition after Item2 freezes the actual selected Plan."""
    from app.domain.planning.content_coverage import _plan_definitions
    _approval(approval)
    _plan_definitions(plan)
    if approval.profile_hash != plan.source_goal_profile_hash or approval.evidence not in plan.verification_evidence:
        _reject()
    if approval.plan_hash is not None:
        if approval.plan_hash != plan.plan_hash:
            _reject()
        return approval
    return _issue_bound_content(approval.profile_hash, approval.source, approval.evidence, plan.plan_hash)


def validate_domain_evidence(profile, evidence, *, domain_approvals=(), allow_fixture_domains=False):
    """Application/Provider dispatch gate; structural Item2 checks remain shared."""
    try:
        _profile(profile)
        _definitions(evidence, verification_input_hash(profile))
        approvals = _approval_map(domain_approvals)
        for item in evidence:
            if item.evidence_kind == "fixture":
                if not allow_fixture_domains:
                    return False
            elif not any(a.profile_hash == profile.profile_hash and a.evidence == item for a in approvals.values()):
                return False
        return True
    except (ValidationAppError, TypeError, ValueError, AttributeError):
        return False


def valid_provider_domain_evidence(payload, *, domain_approvals=()):
    """Only injected issued approvals authorize source evidence in a real Provider."""
    try:
        if not validate_capability_planning_input(payload, CAPABILITY_SCHEMA):
            return False
        approvals = _approval_map(domain_approvals)
        expected = content_hash({"profile": payload["profile"], "policy": payload["policy"]})
        for raw in payload["verification_evidence"]:
            evidence = _evidence_from_payload(raw)
            if evidence.evidence_kind != "source_verification" or evidence.input_hash != expected:
                return False
            if not any(a.profile_hash == payload["profile"]["profile_hash"] and a.evidence == evidence for a in approvals.values()):
                return False
        return True
    except (ValidationAppError, TypeError, ValueError, KeyError, AttributeError):
        return False


def curriculum_public_input_allowed(payload, *, domain_approvals=()):
    """Real Provider only; offline structural fixtures do not authorize export."""
    try:
        if "domain_authority" in payload:
            allowed = public_outcomes_from_authority(payload["domain_authority"], domain_approvals=domain_approvals)
            return all(allowed.get(o["outcome_id"]) == o["text"] for c in payload["capabilities"] for o in c["outcomes"])
        definitions = _definitions((), "")
        for cap in payload["capabilities"]:
            definition = definitions.get(cap["capability_id"])
            if definition is None or cap["title"] != definition.title:
                return False
            allowed = {o.outcome_id: o.text for o in definition.learning_outcomes}
            if any(allowed.get(o["outcome_id"]) != o["text"] for o in cap["outcomes"]):
                return False
        return True
    except (ValidationAppError, TypeError, ValueError, KeyError, AttributeError):
        return False


def _approval_map(approvals):
    if type(approvals) not in {tuple, list} or len(approvals) > 20:
        _reject()
    result = {}
    for approval in approvals:
        _approval(approval)
        if approval.approval_hash in result:
            _reject()
        result[approval.approval_hash] = approval
    return result


@dataclass(frozen=True, slots=True)
class DomainVerificationResult:
    status: str
    evidence: DomainVerificationEvidence | None = None
    approval: DomainApproval | None = None
    reason: str = ""
    requests: int = 0
    bytes_read: int = 0


def public_outcomes(plan, *, domain_approvals=(), allow_fixture_domains=False):
    from app.domain.planning.content_coverage import _plan_definitions
    _plan_definitions(plan)
    approvals = _approval_map(domain_approvals)
    allowed = {o.outcome_id: o.text for d in CAPABILITY_POLICY.definitions for o in d.learning_outcomes}
    for evidence in plan.verification_evidence:
        if evidence.evidence_kind == "fixture" and allow_fixture_domains:
            allowed.update((o.outcome_id, o.text) for d in evidence.capabilities for o in d.learning_outcomes)
        elif evidence.evidence_kind == "source_verification":
            for approval in approvals.values():
                if (approval.profile_hash == plan.source_goal_profile_hash and approval.evidence == evidence
                    and approval.plan_hash == plan.plan_hash):
                    allowed.update((o.outcome_id, o.text) for d in evidence.capabilities for o in d.learning_outcomes
                        if o.outcome_id in approval.source.public_outcome_ids)
    return {o.outcome_id: o.text for o in plan.learning_outcomes if allowed.get(o.outcome_id) == o.text}


def reader_authority(plan, *, domain_approvals=(), allow_fixture_domains=False):
    allowed = public_outcomes(plan, domain_approvals=domain_approvals, allow_fixture_domains=allow_fixture_domains)
    policy_ids = {o.outcome_id for d in CAPABILITY_POLICY.definitions for o in d.learning_outcomes}
    if not set(allowed) - policy_ids:
        return None
    hashes = [a.approval_hash for a in domain_approvals if a.profile_hash == plan.source_goal_profile_hash
        and a.plan_hash == plan.plan_hash and a.evidence in plan.verification_evidence and a.source.public_outcome_ids]
    authority = {"plan": plan.to_payload(), "approval_hashes": sorted(hashes)}
    if any(e.evidence_kind == "fixture" for e in plan.verification_evidence):
        authority["fixture"] = True
    if len(canonical_json(authority).encode("utf-8")) > 65536:
        _reject()
    return authority


def public_outcomes_from_authority(authority, *, domain_approvals=(), allow_fixture_domains=False):
    plan, allowed = resolve_reader_authority(authority, domain_approvals=domain_approvals,
        allow_fixture_domains=allow_fixture_domains)
    return allowed


def resolve_reader_authority(authority, *, domain_approvals=(), allow_fixture_domains=False):
    if type(authority) is not dict or set(authority) not in ({"plan", "approval_hashes"}, {"plan", "approval_hashes", "fixture"}):
        _reject()
    if "fixture" in authority and (authority["fixture"] is not True or not allow_fixture_domains):
        _reject()
    if len(canonical_json(authority).encode("utf-8")) > 65536:
        _reject()
    approvals = _approval_map(domain_approvals)
    hashes = authority["approval_hashes"]
    if type(hashes) is not list or len(hashes) != len(set(hashes)) or set(hashes) - set(approvals):
        _reject()
    plan = _plan_from_payload(authority["plan"])
    selected = tuple(approvals[h] for h in hashes)
    allowed = public_outcomes(plan, domain_approvals=selected, allow_fixture_domains=allow_fixture_domains)
    for evidence in plan.verification_evidence:
        if evidence.evidence_kind == "fixture":
            if authority.get("fixture") is not True:
                _reject()
        elif not any(a.profile_hash == plan.source_goal_profile_hash and a.plan_hash == plan.plan_hash and a.evidence == evidence
            and a.source.public_outcome_ids for a in selected):
            _reject()
    return plan, allowed


def _plan_from_payload(raw):
    if type(raw) is not dict or set(raw) != {f.name for f in fields(CapabilityPlan)} | {"plan_hash"}:
        _reject()
    data = dict(raw)
    digest = data.pop("plan_hash")
    caps = []
    for item in data["capabilities"]:
        if type(item) is not dict or set(item) != {f.name for f in fields(Capability)}:
            _reject()
        caps.append(Capability(**(item | {"learning_outcomes": tuple(LearningOutcome(**o) for o in item["learning_outcomes"]),
            **{k: tuple(item[k]) for k in ("requirement_refs", "policy_refs", "learner_claim_refs", "prerequisite_refs", "learning_target_refs")}})))
    data.update(capabilities=tuple(caps), claim_bindings=tuple(ClaimBinding(**b) for b in data["claim_bindings"]),
        constraint_effects=tuple(ConstraintEffect(**e) for e in data["constraint_effects"]),
        verification_evidence=tuple(_evidence_from_payload(e) for e in data["verification_evidence"]))
    plan = CapabilityPlan(**data)
    if plan.plan_hash != digest:
        _reject()
    return plan


def verification_session_hash(profile, source, *, budget, actor_id, project_id):
    _profile(profile)
    _source(source)
    return content_hash({"verification_input_hash": verification_input_hash(profile), "source_hash": source.source_hash,
        "budget": asdict(budget), "actor_id": actor_id, "project_id": project_id})
