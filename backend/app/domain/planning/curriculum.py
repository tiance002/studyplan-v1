"""Frozen curriculum composition authority; no runtime or entity writes."""
import ipaddress
import json
import re
from dataclasses import asdict, dataclass, field, replace
from urllib.parse import urlsplit

from app.core.errors import ValidationAppError
from app.core.ids import canonical_json, content_hash
from app.domain.planning.capabilities import CAPABILITY_SCHEMA, validate_capability_planning_input
from app.domain.planning.capability_policy import CAPABILITY_POLICY
from app.domain.planning.constraint_adaptation import (
    constraints_unresolved,
    curriculum_constraint_assessments,
)
from app.domain.planning.content_coverage import CoverageEvaluator
from app.domain.planning.domain_verification import public_outcomes_from_authority, reader_authority
from app.domain.planning.goal_requirements import GoalRequirementProfile
from app.domain.planning.resource_gaps import extract
from app.domain.planning.resource_research import (
    ResearchRequirement,
    ResourceResearchResult,
    ReviewedAccessProof,
)
from app.domain.resources.curation import PublicResourceSource

CURRICULUM_PURPOSE = "planning.curriculum_composition"
CURRICULUM_SCHEMA = "CurriculumPlanV1"
CURRICULUM_SCHEMA_V2 = "CurriculumPlanV2"
CURRICULUM_OUTPUT_CAP = 8192
_ROLES = {"common_core", "specialization", "project_study", "integration"}
_MODES = {"whole_core", "slices"}
_KEY = re.compile(r"[a-z][a-z0-9_.-]{0,127}\Z")


def _reject(field):
    raise ValidationAppError("Curriculum Composition 合同校验失败", field=field)


def _fields(value, expected):
    if type(value) is not dict or set(value) != set(expected):
        _reject("fields")


def _array(value, limit=50, *, nonempty=False):
    if type(value) is not list or len(value) > limit or nonempty and not value:
        _reject("sequence")
    return value


def _text(value, limit=2000, *, empty=False):
    if not isinstance(value, str) or len(value) > limit or not empty and not value.strip():
        _reject("text")
    return value


def _ids(values, allowed=None, *, nonempty=False, limit=50):
    values = _array(values, limit, nonempty=nonempty)
    if any(not isinstance(v, str) for v in values) or len(values) != len(set(values)):
        _reject("references")
    if allowed is not None and set(values) - set(allowed):
        _reject("reference_range")
    return set(values)


def _hash(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        _reject("hash")


def _url(value, *, github=False):
    _text(value, 4096)
    parsed = urlsplit(value)
    if (parsed.scheme not in {"https", "http"} or not parsed.hostname or parsed.username is not None
        or parsed.password is not None or "\\" in value or any(ord(c) <= 32 or ord(c) == 127 for c in value)):
        _reject("url")
    host = parsed.hostname.lower().rstrip(".")
    if host == "localhost" or host.endswith((".localhost", ".local", ".internal", ".localdomain")):
        _reject("url")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        if len(host.split(".")) < 2:
            _reject("url")
    else:
        if not address.is_global or address.is_multicast:
            _reject("url")
    if github and (parsed.scheme != "https" or parsed.netloc != "github.com" or parsed.query or parsed.fragment
        or not re.fullmatch(r"/[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}", parsed.path)
        or any(part in {".", ".."} for part in parsed.path.split("/")[1:])):
        _reject("case_url")


def _strings(value, limit=20, *, nonempty=False, text_limit=2000):
    for item in _array(value, limit, nonempty=nonempty):
        _text(item, text_limit)


def _key(value):
    if not isinstance(value, str) or not _KEY.fullmatch(value):
        _reject("stable_key")


def _case(case):
    if type(case) is not ProjectCase:
        _reject("project_case")
    _key(case.case_id)
    _url(case.repo_url, github=True)
    _text(case.version, 200)
    if case.mode not in _MODES or case.qualification not in {"reviewed_candidate", "bounded_reviewed"}:
        _reject("case_qualification")
    _ids(list(case.outcome_refs), nonempty=True)
    _strings(list(case.limitations), 12, text_limit=160)
    if len(case.evidence_refs) > 20 or case.qualification == "bounded_reviewed" and not case.evidence_refs:
        _reject("case_evidence")
    for pair in case.evidence_refs:
        if type(pair) not in {tuple, list} or len(pair) != 2:
            _reject("case_evidence")
        reference, digest = pair
        _text(reference, 1024)
        _hash(digest)
    return asdict(case)


@dataclass(frozen=True, slots=True)
class ProjectCase:
    case_id: str
    repo_url: str
    version: str
    mode: str
    outcome_refs: tuple[str, ...]
    evidence_refs: tuple[tuple[str, str], ...] = ()
    qualification: str = "reviewed_candidate"
    limitations: tuple[str, ...] = ()

    def __post_init__(self):
        for name in ("outcome_refs", "evidence_refs", "limitations"):
            value = getattr(self, name)
            if type(value) is not tuple:
                _reject("case_tuple")
        _case(self)


@dataclass(frozen=True, slots=True)
class CaseFinding:
    requirement_id: str
    requirement_hash: str
    candidates: tuple[ProjectCase, ...] = ()
    reason_codes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CurriculumContext:
    _json: str = field(repr=False)
    research: ResourceResearchResult = field(repr=False)
    _domain_approvals: tuple = field(default=(), repr=False)
    _allow_fixture_domains: bool = field(default=False, repr=False)

    @property
    def input_hash(self):
        return self.to_payload()["input_hash"]

    def to_payload(self):
        return json.loads(self._json)

    @property
    def public_outcome_texts(self):
        authority = self.to_payload().get("domain_authority")
        if authority is not None:
            return public_outcomes_from_authority(authority, domain_approvals=self._domain_approvals,
                                                 allow_fixture_domains=self._allow_fixture_domains)
        return {o.outcome_id: o.text for d in CAPABILITY_POLICY.definitions for o in d.learning_outcomes}

    def expected_session_hash(self, budget, *, actor_id, project_id):
        from dataclasses import asdict
        source = self.to_payload()["sources"]
        payload = {"gap_set": source["gap_set_hash"], "plan": source["capability_plan_hash"],
            "coverage": source["coverage_hash"], "profile": source["profile_hash"], "budget": asdict(budget),
            "actor_id": actor_id, "project_id": project_id, "checked_at": source["research_checked_at"]}
        if self.research.rules_version != "legacy":
            payload["rules_version"] = self.research.rules_version
        return content_hash(payload)


@dataclass(frozen=True, slots=True)
class CurriculumPlan:
    _json: str = field(repr=False)
    _findings: str = field(default="[]", repr=False)

    @property
    def input_hash(self):
        return json.loads(self._json)["input_hash"]

    @property
    def status(self):
        return json.loads(self._json)["status"]

    @property
    def plan_hash(self):
        return content_hash({"curriculum": json.loads(self._json), "case_findings": json.loads(self._findings)})

    @property
    def project_study_requirements(self):
        return [item | {"requirement_hash": content_hash(item)}
            for item in json.loads(self._json)["project_study_requirements"]]

    def to_payload(self):
        return json.loads(self._json) | {"case_findings": json.loads(self._findings), "plan_hash": self.plan_hash}


def prepare_curriculum(profile, plan, coverage, research, reviewed_index, *, catalog_sources=(), project_cases=(), access_proofs=(),
                       domain_approvals=(), allow_fixture_domains=False, semantics_version=1):
    try:
        if type(semantics_version) is not int or semantics_version not in {1, 2}:
            _reject("semantics_version")
        if type(profile) is not GoalRequirementProfile or profile.status != "ready" or profile.profile_hash != plan.source_goal_profile_hash:
            _reject("profile_binding")
        if not validate_capability_planning_input({"profile": profile.to_payload(), "policy": CAPABILITY_POLICY.to_payload(),
            "verification_evidence": [item.to_payload() for item in plan.verification_evidence]}, CAPABILITY_SCHEMA):
            _reject("profile")
        if CoverageEvaluator().evaluate(plan, reviewed_index) != coverage:
            _reject("coverage_binding")
        gaps = extract(plan, coverage)
        if type(research) is not ResourceResearchResult or replace(research) != research:
            _reject("research")
        if semantics_version == 1 and research.rules_version != "legacy":
            _reject("research_version")
        if (research.source_gap_set_hash, research.source_capability_plan_hash, research.source_coverage_result_hash,
            research.source_profile_hash) != (gaps.result_hash, plan.plan_hash, coverage.result_hash, profile.profile_hash):
            _reject("research_binding")
        expected = tuple(ResearchRequirement(g.capability_id, g.missing_outcomes, g.importance, g.desired_depth,
            g.requirement_refs, profile.starting_point, profile.hard_constraints, profile.learner_claims) for g in gaps.gaps)
        if tuple(entry.requirement for entry in research.entries) != expected:
            _reject("research_requirements")
        sources = {}
        for source in catalog_sources:
            if type(source) is not PublicResourceSource or source.source_id in sources:
                _reject("catalog_source")
            _url(source.canonical_url)
            sources[source.source_id] = source
        for proof in access_proofs:
            if type(proof) is not ReviewedAccessProof or replace(proof) != proof:
                _reject("access_proof")
        proof_keys = [(p.source_id, p.source_version, p.content_hash) for p in access_proofs]
        if len(proof_keys) != len(set(proof_keys)):
            _reject("access_proof_conflict")
        materials = {}
        for entry in coverage.entries:
            for reference in entry.content_refs:
                section = reference.section
                source = sources.get(section.source_id)
                source = source if source and source.source_version == section.source_version else None
                proof = next((p for p in access_proofs if p.source_id == section.source_id
                    and p.source_version == section.source_version and p.content_hash == section.content_hash), None)
                free = "confirmed" if proof and proof.access == "free_public" else "paid" if proof and proof.access == "paid" else "unknown"
                key = (section.source_id, section.source_version, section.section_id)
                material = materials.setdefault(key, {"kind": "covered_content", "source_id": section.source_id,
                    "source_version": f"source:{section.source_version}", "section_refs": [section.section_id],
                    "content_hash": section.content_hash, "url": source.canonical_url if source else "",
                    "title": source.title if source else section.content_id, "outcome_refs": [], "qualification": "public_reviewed",
                    "free_access": free, "usable": bool(source and free == "confirmed"), "evidence_refs": [],
                    "access_proof": asdict(proof) if proof else None, "limitations": []})
                material["outcome_refs"].extend(reference.outcome_ids)
                for evidence in reference.evidence:
                    material["evidence_refs"].append({"reference": evidence.reference, "sha256": evidence.sha256,
                        "location": section.section_id, "hash_scope": "review_record"})
                    material["limitations"].extend(evidence.limitations)
        for entry in research.entries:
            for resource in entry.resources:
                _url(resource.url)
                # Identity alone cannot lend one resource's access or review to another outcome.
                frozen_resource = asdict(resource)
                if research.rules_version == "legacy":
                    frozen_resource.pop("quality_evidence")
                key = ("research", canonical_json(frozen_resource))
                material = materials.setdefault(key, {"kind": "researched_resource", "source_id": resource.resource_id,
                    "source_version": resource.version, "section_refs": [], "content_hash": content_hash(frozen_resource),
                    "url": resource.url, "title": resource.resource_id, "outcome_refs": [], "qualification": resource.qualification,
                    "free_access": resource.free_access, "usable": resource.free_access == "confirmed"
                        and resource.qualification in {"public_reviewed", "research_checked"}, "evidence_refs": [],
                    "access_proof": None, "limitations": list(resource.limitations)})
                material["outcome_refs"].extend(ref.outcome_id for ref in resource.evidence)
                material["section_refs"].extend(ref.location for ref in resource.evidence)
                material["evidence_refs"].extend({"reference": ref.reference, "sha256": ref.sha256,
                    "location": ref.location, "hash_scope": ref.hash_scope} for ref in resource.evidence)
        allowed = []
        for material in materials.values():
            for key in ("outcome_refs", "section_refs", "limitations"):
                material[key] = sorted(set(material[key]))
            material["evidence_refs"] = sorted({canonical_json(e): e for e in material["evidence_refs"]}.values(), key=canonical_json)
            material["material_id"] = "material_" + content_hash(material)
            allowed.append(material)
        allowed.sort(key=lambda m: m["material_id"])
        available = {ref for material in allowed if material["usable"] for ref in material["outcome_refs"]}
        upstream_unresolved = {ref.outcome_id for entry in research.entries for ref in entry.unresolved_outcomes}
        capabilities = [{"capability_id": c.capability_id, "title": c.title, "importance": c.learning_requirement,
            "desired_depth": c.desired_depth, "project_usage": c.project_usage, "outcomes": [asdict(o) for o in c.learning_outcomes],
            "prerequisites": list(c.prerequisite_refs), "requirement_refs": list(c.requirement_refs),
            "unavailable_outcomes": sorted(o.outcome_id for o in c.learning_outcomes
                if o.outcome_id not in available or o.outcome_id in upstream_unresolved)}
            for c in plan.learning_capabilities]
        if semantics_version == 2:
            for entry, capability in zip(capabilities, plan.learning_capabilities, strict=True):
                entry["learning_target_refs"] = list(capability.learning_target_refs)
        cases = [_case(case) for case in project_cases]
        if len(cases) > 50 or len({case["case_id"] for case in cases}) != len(cases):
            _reject("project_cases")
        payload = {"schema_version": 1, "sources": {"profile_hash": profile.profile_hash, "capability_plan_hash": plan.plan_hash,
            "coverage_hash": coverage.result_hash, "research_hash": research.result_hash, "gap_set_hash": gaps.result_hash,
            "reviewed_index_hash": reviewed_index.index_hash, "research_checked_at": research.checked_at,
            "research_budget_usage": dict(research.budget_usage)}, "capabilities": capabilities,
            "accepted_known": sorted(c.capability_id for c in plan.accepted_known_capabilities), "materials": allowed,
            "project_cases": sorted(cases, key=lambda c: c["case_id"]), "profile_context": {
                "project_context": profile.project_context, "project_context_hash": content_hash({"project_context": profile.project_context}),
                "starting_point": profile.starting_point, "outcome_purpose": profile.outcome_purpose,
                "requirements": [asdict(r) for r in profile.required_requirements]},
            "constraints": [asdict(c) for c in profile.hard_constraints]}
        authority = reader_authority(plan, domain_approvals=domain_approvals, allow_fixture_domains=allow_fixture_domains)
        if authority is not None:
            payload["domain_authority"] = authority
        if semantics_version == 2:
            payload.update(schema_version=2, semantics_version=2)
            payload["research_comparisons"] = [{"capability_id": entry.requirement.capability_id,
                "status": entry.comparison_status, "resource_order": list(entry.comparison_order),
                "reasons": list(entry.comparison_reasons), "resources": [{"resource_id": resource.resource_id,
                    "source_version": resource.version, "outcome_refs": sorted({r.outcome_id for r in resource.evidence}),
                    "teaching_fit": dict(resource.teaching_fit), "quality_evidence": [asdict(q) for q in resource.quality_evidence],
                    "limitations": list(resource.limitations)} for resource in entry.resources]}
                for entry in research.entries]
        payload = json.loads(canonical_json(payload))
        payload["input_hash"] = content_hash(payload)
        if len(canonical_json(payload).encode("utf-8")) > 131072:
            _reject("input_size")
        return CurriculumContext(canonical_json(payload), research, tuple(domain_approvals), allow_fixture_domains)
    except (TypeError, AttributeError, KeyError, ValueError):
        _reject("input")


def curriculum_semantics(payload):
    # A missing marker means historical v1; even an explicit marker=1 is not
    # accepted because it would change the old authority's frozen shape/hash.
    if "semantics_version" not in payload:
        return 1
    if type(payload["semantics_version"]) is not int or payload["semantics_version"] != 2:
        _reject("semantics_version")
    return 2


def curriculum_schema(payload):
    return CURRICULUM_SCHEMA_V2 if curriculum_semantics(payload) == 2 else CURRICULUM_SCHEMA


def valid_curriculum_input(payload, schema_name, *, domain_approvals=(), allow_fixture_domains=False):
    try:
        if schema_name != curriculum_schema(payload):
            return False
        _validate_input(payload, domain_approvals=domain_approvals, allow_fixture_domains=allow_fixture_domains)
        return True
    except (ValidationAppError, TypeError, ValueError, KeyError, AttributeError, RecursionError):
        return False


def _validate_input(payload, *, domain_approvals=(), allow_fixture_domains=False):
    version = curriculum_semantics(payload)
    _fields(payload, {"schema_version", "input_hash", "sources", "capabilities", "accepted_known", "materials",
        "project_cases", "profile_context", "constraints"} | ({"domain_authority"} if "domain_authority" in payload else set())
        | ({"semantics_version", "research_comparisons"} if version == 2 else set()))
    if type(payload["schema_version"]) is not int or payload["schema_version"] != version:
        _reject("schema")
    _hash(payload["input_hash"])
    if len(canonical_json(payload).encode("utf-8")) > 131072 or content_hash(
        {k: v for k, v in payload.items() if k != "input_hash"}) != payload["input_hash"]:
        _reject("input_digest")
    source = payload["sources"]
    _fields(source, {"profile_hash", "capability_plan_hash", "coverage_hash", "research_hash", "gap_set_hash",
        "reviewed_index_hash", "research_checked_at", "research_budget_usage"})
    for name in ("profile_hash", "capability_plan_hash", "coverage_hash", "research_hash", "gap_set_hash", "reviewed_index_hash"):
        _hash(source[name])
    from app.domain.planning.resource_research import METRICS
    _fields(source["research_budget_usage"], METRICS)
    for value in source["research_budget_usage"].values():
        if type(value) is not int or value < 0:
            _reject("budget_usage")
    from datetime import datetime
    checked = datetime.fromisoformat(source["research_checked_at"].replace("Z", "+00:00"))
    if checked.tzinfo is None:
        _reject("checked_at")
    known = _ids(payload["accepted_known"])
    capabilities, outcomes = {}, set()
    for cap in _array(payload["capabilities"], 50):
        _fields(cap, {"capability_id", "title", "importance", "desired_depth", "project_usage", "outcomes",
            "prerequisites", "requirement_refs", "unavailable_outcomes"} | ({"learning_target_refs"} if version == 2 else set()))
        _key(cap["capability_id"])
        if cap["capability_id"] in known or cap["capability_id"] in capabilities:
            _reject("B_only")
        _text(cap["title"], 200)
        if cap["importance"] not in {"required", "recommended"} or cap["project_usage"] not in {"required", "optional", "excluded"}:
            _reject("capability_scope")
        if cap["desired_depth"] not in {"foundation", "applied", "deep"}:
            _reject("depth")
        refs = set()
        for outcome in _array(cap["outcomes"], 20, nonempty=True):
            _fields(outcome, {"outcome_id", "text"})
            _key(outcome["outcome_id"])
            _text(outcome["text"], 2000)
            if outcome["outcome_id"] in outcomes or not outcome["outcome_id"].startswith(cap["capability_id"] + "."):
                _reject("outcome_identity")
            refs.add(outcome["outcome_id"])
            outcomes.add(outcome["outcome_id"])
        _ids(cap["unavailable_outcomes"], refs)
        _ids(cap["requirement_refs"])
        if version == 2:
            _ids(cap["learning_target_refs"], cap["requirement_refs"])
        _ids(cap["prerequisites"])
        capabilities[cap["capability_id"]] = cap
    for cap in capabilities.values():
        if set(cap["prerequisites"]) - (set(capabilities) | known) or cap["capability_id"] in cap["prerequisites"]:
            _reject("prerequisite_range")
    if "domain_authority" in payload:
        authority = payload["domain_authority"]
        public = public_outcomes_from_authority(authority, domain_approvals=domain_approvals,
                                                allow_fixture_domains=allow_fixture_domains)
        if (authority["plan"]["plan_hash"] != source["capability_plan_hash"]
                or authority["plan"]["source_goal_profile_hash"] != source["profile_hash"]):
            _reject("domain_plan_binding")
        frozen = {c["capability_id"]: c for c in authority["plan"]["capabilities"] if c["disposition"] == "needs_learning"}
        if set(frozen) != set(capabilities):
            _reject("domain_capability_binding")
        for key, cap in capabilities.items():
            upstream = frozen[key]
            if any(cap[name] != upstream[other] for name, other in (("title", "title"), ("importance", "learning_requirement"),
                ("desired_depth", "desired_depth"), ("project_usage", "project_usage"), ("outcomes", "learning_outcomes"),
                ("prerequisites", "prerequisite_refs"), ("requirement_refs", "requirement_refs"))):
                _reject("domain_capability_binding")
            if version == 2 and cap["learning_target_refs"] != upstream["learning_target_refs"]:
                _reject("domain_capability_binding")
            if any(public.get(o["outcome_id"]) != o["text"] for o in cap["outcomes"]):
                _reject("domain_public_binding")
    _ancestors(capabilities)
    material_ids = set()
    for material in _array(payload["materials"], 100):
        _fields(material, {"material_id", "kind", "source_id", "source_version", "section_refs", "content_hash", "url",
            "title", "outcome_refs", "qualification", "free_access", "usable", "evidence_refs", "access_proof", "limitations"})
        if material["material_id"] != "material_" + content_hash({k: v for k, v in material.items() if k != "material_id"}):
            _reject("material_identity")
        if material["material_id"] in material_ids:
            _reject("material_duplicate")
        material_ids.add(material["material_id"])
        if material["kind"] not in {"covered_content", "researched_resource"}:
            _reject("material_kind")
        _text(material["source_id"], 200)
        _text(material["source_version"], 200)
        _hash(material["content_hash"])
        _text(material["title"], 500)
        if material["url"]:
            _url(material["url"])
        _ids(material["outcome_refs"], outcomes, nonempty=True)
        _strings(material["section_refs"], 50, text_limit=1024)
        _strings(material["limitations"], 30, text_limit=1000)
        if material["qualification"] not in {"public_reviewed", "research_checked", "candidate"} or material["free_access"] not in {"confirmed", "unknown", "paid"}:
            _reject("material_qualification")
        expected = bool(material["url"] and material["free_access"] == "confirmed"
            and material["qualification"] in {"public_reviewed", "research_checked"})
        if type(material["usable"]) is not bool or material["usable"] != expected:
            _reject("material_access")
        for evidence in _array(material["evidence_refs"], 100, nonempty=True):
            _fields(evidence, {"reference", "sha256", "location", "hash_scope"})
            _text(evidence["reference"], 4096)
            _hash(evidence["sha256"])
            _text(evidence["location"], 1024)
            _text(evidence["hash_scope"], 100)
        proof = material["access_proof"]
        if material["kind"] == "covered_content":
            if proof is not None:
                parsed = ReviewedAccessProof(**proof)
                if (parsed.source_id, f"source:{parsed.source_version}", parsed.content_hash) != (
                    material["source_id"], material["source_version"], material["content_hash"]):
                    _reject("access_binding")
            if material["usable"] and (proof is None or proof["access"] != "free_public"):
                _reject("access_proof")
        elif proof is not None:
            _reject("access_proof")
    if version == 2:
        _validate_research_comparisons(payload, capabilities)
    case_ids = set()
    for case in _array(payload["project_cases"], 50):
        parsed = ProjectCase(**(case | {"outcome_refs": tuple(case["outcome_refs"]),
            "evidence_refs": tuple(tuple(p) for p in case["evidence_refs"]), "limitations": tuple(case["limitations"])}))
        _ids(list(parsed.outcome_refs), outcomes)
        if parsed.case_id in case_ids:
            _reject("case_duplicate")
        case_ids.add(parsed.case_id)
    context = payload["profile_context"]
    _fields(context, {"project_context", "project_context_hash", "starting_point", "outcome_purpose", "requirements"})
    for name in ("project_context", "starting_point", "outcome_purpose"):
        if context[name] is not None:
            _text(context[name], 5000, empty=True)
    if context["project_context_hash"] != content_hash({"project_context": context["project_context"]}):
        _reject("project_binding")
    requirement_ids = set()
    for requirement in _array(context["requirements"], 50):
        _fields(requirement, {"requirement_id", "text", "origin", "source_refs", "rationale"})
        _text(requirement["requirement_id"], 200)
        _text(requirement["text"], 2000)
        if requirement["origin"] not in {"explicit", "inferred_required"}:
            _reject("requirement_origin")
        _ids(requirement["source_refs"], nonempty=True)
        _text(requirement["rationale"], 2000, empty=True)
        requirement_ids.add(requirement["requirement_id"])
    for cap in capabilities.values():
        _ids(cap["requirement_refs"], requirement_ids)
    constraints = set()
    for constraint in _array(payload["constraints"], 30):
        _fields(constraint, {"constraint_id", "text", "source_refs"})
        _text(constraint["constraint_id"], 200)
        _text(constraint["text"], 2000)
        _ids(constraint["source_refs"], nonempty=True)
        if constraint["constraint_id"] in constraints:
            _reject("constraint_duplicate")
        constraints.add(constraint["constraint_id"])


def _validate_research_comparisons(payload, capabilities):
    """Validate retained comparison structure; this never proves teaching quality."""
    materials = {(m["source_id"], m["source_version"]) for m in payload["materials"]}
    seen = set()
    for entry in _array(payload["research_comparisons"], 50):
        _fields(entry, {"capability_id", "status", "resource_order", "reasons", "resources"})
        key = entry["capability_id"]
        if key not in capabilities or key in seen or entry["status"] not in {"legacy", "sufficient", "insufficient"}:
            _reject("research_comparison_scope")
        seen.add(key)
        _strings(entry["reasons"], 20, text_limit=160)
        identities = set()
        allowed = {o["outcome_id"] for o in capabilities[key]["outcomes"]}
        for resource in _array(entry["resources"], 100):
            _fields(resource, {"resource_id", "source_version", "outcome_refs", "teaching_fit", "quality_evidence", "limitations"})
            _text(resource["resource_id"], 200)
            _text(resource["source_version"], 200)
            if (resource["resource_id"], resource["source_version"]) not in materials:
                _reject("research_comparison_source")
            if resource["resource_id"] in identities:
                _reject("research_comparison_duplicate")
            identities.add(resource["resource_id"])
            _ids(resource["outcome_refs"], allowed)
            _strings(resource["limitations"], 12, text_limit=160)
            if type(resource["teaching_fit"]) is not dict or len(resource["teaching_fit"]) > 5:
                _reject("research_comparison_fit")
            for name, value in resource["teaching_fit"].items():
                _text(name, 160)
                _text(value, 160)
            dimensions = set()
            for quality in _array(resource["quality_evidence"], 4):
                _fields(quality, {"dimension", "category", "rationale", "evidence"})
                if quality["dimension"] not in {"continuity", "beginner_fit", "examples", "version_fit"} or quality["dimension"] in dimensions:
                    _reject("research_comparison_quality")
                dimensions.add(quality["dimension"])
                if quality["category"] not in {"adequate", "strong"}:
                    _reject("research_comparison_quality")
                _text(quality["rationale"], 160)
                for ref in _array(quality["evidence"], 2, nonempty=True):
                    _fields(ref, {"outcome_id", "reference", "sha256", "location", "hash_scope"})
                    _key(ref["outcome_id"])
                    _text(ref["reference"], 1024)
                    _hash(ref["sha256"])
                    _text(ref["location"], 1024)
                    if ref["hash_scope"] != "body":
                        _reject("research_comparison_evidence")
            if dimensions and dimensions != {"continuity", "beginner_fit", "examples", "version_fit"}:
                _reject("research_comparison_quality")
        if _ids(entry["resource_order"], identities) != identities and entry["status"] != "legacy":
            _reject("research_comparison_order")
        if entry["status"] == "sufficient" and (len(identities) < 2 or any(not r["quality_evidence"] for r in entry["resources"])):
            _reject("research_comparison_claim")


def _ancestors(capabilities):
    complete, visiting = {}, set()
    def visit(key):
        if key in visiting:
            _reject("prerequisite_cycle")
        if key in complete:
            return complete[key]
        visiting.add(key)
        refs = set(capabilities[key]["prerequisites"])
        for parent in tuple(refs):
            if parent in capabilities:
                refs.update(visit(parent))
        visiting.remove(key)
        complete[key] = refs
        return refs
    for key in capabilities:
        visit(key)
    return complete


def _acceptance(value, allowed, *, permit_empty_refs=False):
    seen = set()
    for item in _array(value, 30, nonempty=True):
        _fields(item, {"text", "outcome_refs"})
        _text(item["text"], 2000)
        seen.update(_ids(item["outcome_refs"], allowed, nonempty=not permit_empty_refs))
    return seen


def _sort_output_refs(value):
    # These fields denote sets. Teaching order, objectives and task text retain their order.
    refs = {"capability_ids", "outcome_refs", "prerequisite_stage_refs", "material_refs", "knowledge_refs",
        "project_study_refs", "constraint_refs", "source_refs", "acceptance_refs"}
    if type(value) is dict:
        for key, child in value.items():
            if key in refs:
                child.sort()
            else:
                _sort_output_refs(child)
    elif type(value) is list:
        for child in value:
            _sort_output_refs(child)


def validate_curriculum_output(raw, payload, *, domain_approvals=(), allow_fixture_domains=False):
    try:
        _validate_input(payload, domain_approvals=domain_approvals, allow_fixture_domains=allow_fixture_domains)
        if len(canonical_json(raw).encode("utf-8")) > 131072:
            _reject("output_size")
        document = json.loads(canonical_json(raw))
        _validate_output(document, payload)
        _sort_output_refs(document)
        selected = {assignment["material_id"] for stage in document["stages"] for assignment in stage["assignments"]}
        selected.update(ref for stage in document["stages"] for knowledge in stage["knowledge"] for ref in knowledge["material_refs"])
        cases = {r["selected_case_ref"] for r in document["project_study_requirements"] if r["selected_case_ref"]}
        # Compile facts are copied only by the server, outside the model's output schema.
        document.update(compile_sources=payload["sources"],
            compile_materials=[m for m in payload["materials"] if m["material_id"] in selected],
            compile_cases=[c for c in payload["project_cases"] if c["case_id"] in cases],
            compile_context={"profile_context": payload["profile_context"], "constraints": payload["constraints"],
                "capabilities": payload["capabilities"], "accepted_known": payload["accepted_known"],
                "constraint_assessments": curriculum_constraint_assessments(document, payload),
                **({"domain_authority": payload["domain_authority"]} if "domain_authority" in payload else {})})
        return CurriculumPlan(canonical_json(document))
    except (TypeError, ValueError, KeyError, AttributeError, RecursionError):
        _reject("output")


def _validate_output(document, payload):
    version = curriculum_semantics(payload)
    _fields(document, {"schema_version", "input_hash", "status", "stages", "carrier", "project_study_requirements",
        "unresolved", "constraint_refs", "source_limitations"} | ({"semantics_version", "permission_obligations"} if version == 2 else set()))
    if (type(document["schema_version"]) is not int or document["schema_version"] != version
            or curriculum_semantics(document) != version or document["input_hash"] != payload["input_hash"]):
        _reject("input_binding")
    if document["status"] not in {"complete", "incomplete"}:
        _reject("status")
    capabilities = {c["capability_id"]: c for c in payload["capabilities"]}
    outcome_caps = {o["outcome_id"]: c["capability_id"] for c in capabilities.values() for o in c["outcomes"]}
    outcomes = set(outcome_caps)
    ancestors = _ancestors(capabilities)
    cap_outcomes = {key: {o["outcome_id"] for o in cap["outcomes"]} for key, cap in capabilities.items()}
    unresolved = set()
    for item in _array(document["unresolved"], 100):
        _fields(item, {"outcome_ref", "reason"})
        if item["outcome_ref"] not in outcomes or item["outcome_ref"] in unresolved:
            _reject("unresolved_range")
        _text(item["reason"], 1000)
        unresolved.add(item["outcome_ref"])
    unavailable = {ref for c in capabilities.values() for ref in c["unavailable_outcomes"]}
    if unavailable - unresolved:
        _reject("source_unavailable")
    _ids(document["constraint_refs"], {c["constraint_id"] for c in payload["constraints"]})
    if set(document["constraint_refs"]) != {c["constraint_id"] for c in payload["constraints"]}:
        _reject("constraint_preservation")
    _strings(document["source_limitations"], 30, text_limit=1000)
    materials = {m["material_id"]: m for m in payload["materials"]}
    cases = {c["case_id"]: c for c in payload["project_cases"]}
    requirements, unfilled = {}, False
    for req in _array(document["project_study_requirements"], 20):
        _fields(req, {"requirement_id", "problem", "mode", "outcome_refs", "avoid_scope", "expected_outputs",
            "normal_behavior", "failure_behavior", "inputs_outputs", "design_questions", "selected_case_ref"})
        _key(req["requirement_id"])
        if req["requirement_id"] in requirements or req["mode"] not in _MODES:
            _reject("project_requirement")
        refs = _ids(req["outcome_refs"], outcomes, nonempty=True)
        _text(req["problem"], 2000)
        for field_name in ("avoid_scope", "expected_outputs", "normal_behavior", "failure_behavior", "design_questions"):
            _strings(req[field_name], 20, nonempty=True)
        for pair in _array(req["inputs_outputs"], 20, nonempty=True):
            _fields(pair, {"input", "output"})
            _text(pair["input"], 2000)
            _text(pair["output"], 2000)
        selected = req["selected_case_ref"]
        if selected is None:
            unfilled = True
        elif not isinstance(selected, str) or selected not in cases:
            _reject("case_reference")
        else:
            case = cases[selected]
            if case["qualification"] != "bounded_reviewed" or case["mode"] != req["mode"] or refs - set(case["outcome_refs"]):
                _reject("case_not_qualified")
        requirements[req["requirement_id"]] = req
    stages = _array(document["stages"], 20)
    if any(type(s) is not dict or type(s.get("order_index")) is not int for s in stages):
        _reject("stage_order")
    stages.sort(key=lambda s: s["order_index"])
    if [s["order_index"] for s in stages] != list(range(len(stages))):
        _reject("stage_order")
    stage_map, stable_keys, staged, project_refs = {}, set(), set(), set()
    for stage in stages:
        _fields(stage, {"stage_id", "title", "role", "order_index", "why_now", "what_to_learn", "capability_ids",
            "outcome_refs", "prerequisite_stage_refs", "knowledge", "units", "assignments", "guidance", "tasks", "project_study_refs"})
        _key(stage["stage_id"])
        if stage["stage_id"] in stable_keys or stage["role"] not in _ROLES:
            _reject("stage_identity")
        stable_keys.add(stage["stage_id"])
        for name in ("title", "why_now", "what_to_learn"):
            _text(stage[name], 2000)
        stage_caps = _ids(stage["capability_ids"], capabilities, nonempty=True)
        stage_outcomes = _ids(stage["outcome_refs"], outcomes, nonempty=True)
        if {outcome_caps[o] for o in stage_outcomes} != stage_caps:
            _reject("stage_capability_binding")
        staged.update(stage_outcomes)
        dependency_ids = _ids(stage["prerequisite_stage_refs"], stage_map)
        needed_caps = set().union(*(ancestors[c] for c in stage_caps))
        for dependency in dependency_ids:
            if not set(stage_map[dependency]["capability_ids"]) & needed_caps:
                _reject("invented_dependency")
        dependency_outcomes, visited_dependencies = set(), set()
        pending_dependencies = list(dependency_ids)
        while pending_dependencies:
            dependency = pending_dependencies.pop()
            if dependency in visited_dependencies:
                continue
            visited_dependencies.add(dependency)
            dependency_outcomes.update(stage_map[dependency]["outcome_refs"])
            pending_dependencies.extend(stage_map[dependency]["prerequisite_stage_refs"])
        stage_materials, assigned = set(), set()
        primary, assigned_ids = 0, set()
        for assignment in _array(stage["assignments"], 30):
            _fields(assignment, {"material_id", "role", "outcome_refs", "reading_focus"})
            material = materials.get(assignment["material_id"])
            if not material or not material["usable"] or assignment["material_id"] in assigned_ids:
                _reject("material_assignment")
            assigned_ids.add(assignment["material_id"])
            if assignment["role"] not in {"PRIMARY", "SUPPLEMENT", "REFERENCE", "CASE_STUDY"}:
                _reject("assignment_role")
            primary += assignment["role"] == "PRIMARY"
            if primary > 1:
                _reject("primary_count")
            refs = _ids(assignment["outcome_refs"], stage_outcomes & set(material["outcome_refs"]), nonempty=True)
            _text(assignment["reading_focus"], 2000)
            assigned.update(refs)
            stage_materials.add(material["material_id"])
        knowledge, knowledge_outcomes, material_outcomes = {}, set(), set()
        for node in _array(stage["knowledge"], 30, nonempty=True):
            _fields(node, {"stable_key", "title", "objectives", "outcome_refs", "material_refs"})
            _key(node["stable_key"])
            if node["stable_key"] in stable_keys:
                _reject("stable_identity_duplicate")
            stable_keys.add(node["stable_key"])
            _text(node["title"], 500)
            _strings(node["objectives"], 20, nonempty=True)
            refs = _ids(node["outcome_refs"], stage_outcomes, nonempty=True)
            source_ids = _ids(node["material_refs"], stage_materials)
            covered = set().union(*(set(materials[m]["outcome_refs"]) for m in source_ids)) if source_ids else set()
            if refs - unresolved - covered:
                _reject("knowledge_source")
            knowledge[node["stable_key"]] = refs
            knowledge_outcomes.update(refs)
            material_outcomes.update(covered & refs)
        unit_outcomes = set()
        for unit in _array(stage["units"], 30, nonempty=True):
            _fields(unit, {"stable_key", "title", "objectives", "outcome_refs", "knowledge_refs", "rubric"})
            _key(unit["stable_key"])
            if unit["stable_key"] in stable_keys:
                _reject("stable_identity_duplicate")
            stable_keys.add(unit["stable_key"])
            _text(unit["title"], 500)
            _strings(unit["objectives"], 20, nonempty=True)
            refs = _ids(unit["outcome_refs"], stage_outcomes, nonempty=True)
            links = _ids(unit["knowledge_refs"], knowledge, nonempty=True)
            if refs - set().union(*(knowledge[k] for k in links)) or refs - _acceptance(unit["rubric"], refs):
                _reject("unit_binding")
            for cap_id in {outcome_caps[o] for o in refs}:
                for prerequisite in capabilities[cap_id]["prerequisites"]:
                    if prerequisite in payload["accepted_known"]:
                        continue
                    required = cap_outcomes[prerequisite]
                    if required - (unit_outcomes | dependency_outcomes):
                        _reject("prerequisite_before_use")
            unit_outcomes.update(refs)
        guidance = stage["guidance"]
        _fields(guidance, {"previous_relation", "learning_focus", "comparison_focus", "practice_delta"})
        _text(guidance["previous_relation"], 2000)
        _strings(guidance["learning_focus"], 20, nonempty=True)
        _strings(guidance["comparison_focus"], 20)
        _fields(guidance["practice_delta"], {"baseline", "increment", "preserved", "validation", "reuse"})
        for value in guidance["practice_delta"].values():
            _text(value, 2000)
        task_outcomes = set()
        for task in _array(stage["tasks"], 30, nonempty=True):
            _fields(task, {"stable_key", "title", "goal", "in_scope", "out_scope", "outcome_refs", "knowledge_refs",
                "practice_kind", "acceptance"})
            _key(task["stable_key"])
            if task["stable_key"] in stable_keys:
                _reject("stable_identity_duplicate")
            stable_keys.add(task["stable_key"])
            for name in ("title", "goal"):
                _text(task[name], 2000)
            _strings(task["in_scope"], 20, nonempty=True)
            _strings(task["out_scope"], 20)
            refs = _ids(task["outcome_refs"], stage_outcomes & unit_outcomes, nonempty=True)
            links = _ids(task["knowledge_refs"], knowledge, nonempty=True)
            if refs - set().union(*(knowledge[k] for k in links)) or refs - _acceptance(task["acceptance"], refs):
                _reject("task_binding")
            if task["practice_kind"] not in {"carrier", "micro_exercise"}:
                _reject("practice_kind")
            if task["practice_kind"] == "carrier" and any(capabilities[outcome_caps[o]]["project_usage"] == "excluded" for o in refs):
                _reject("project_exclusion")
            task_outcomes.update(refs)
        if stage_outcomes - knowledge_outcomes or stage_outcomes - unit_outcomes or stage_outcomes - task_outcomes:
            _reject("teaching_completeness")
        if stage_outcomes - unresolved - (assigned & material_outcomes):
            _reject("teaching_source")
        refs = _ids(stage["project_study_refs"], requirements)
        for ref in refs:
            if set(requirements[ref]["outcome_refs"]) - stage_outcomes:
                _reject("project_study_binding")
        project_refs.update(refs)
        stage_map[stage["stage_id"]] = stage
    if set(requirements) - project_refs:
        _reject("unassigned_project_study")
    required = required_curriculum_outcomes(payload)
    if required - (staged | unresolved):
        _reject("required_outcome_omitted")
    carrier = document["carrier"]
    _fields(carrier, {"kind", "project_context_hash", "reason", "description", "final_artifact"})
    if carrier["kind"] not in {"user_project", "starter"} or carrier["project_context_hash"] != payload["profile_context"]["project_context_hash"]:
        _reject("carrier_binding")
    if payload["profile_context"]["project_context"] and carrier["kind"] != "user_project":
        _reject("user_project_preservation")
    for name in ("reason", "description"):
        _text(carrier[name], 5000)
    _fields(carrier["final_artifact"], {"description", "acceptance"})
    _text(carrier["final_artifact"]["description"], 5000)
    carrier_allowed = {o for o in staged if capabilities[outcome_caps[o]]["project_usage"] != "excluded"}
    _acceptance(carrier["final_artifact"]["acceptance"], carrier_allowed, permit_empty_refs=not carrier_allowed)
    if version == 2:
        _validate_permission_obligations(document, payload)
    assessments = curriculum_constraint_assessments(document, payload)
    blocking = blocking_unresolved_outcomes(document, payload)
    expected_status = "incomplete" if blocking or unfilled or constraints_unresolved(assessments) else "complete"
    if document["status"] != expected_status:
        _reject("completeness")


def blocking_unresolved_outcomes(document, payload):
    unresolved = {item["outcome_ref"] for item in document["unresolved"]}
    if curriculum_semantics(payload) == 1:
        return unresolved
    required = required_curriculum_outcomes(payload)
    selected = {ref for stage in document["stages"] for ref in stage["outcome_refs"]}
    # Explicit source requirements are selected teaching too, even if a future
    # carrier uses a different stage projection.
    selected.update(ref for req in document["project_study_requirements"] for ref in req["outcome_refs"])
    return unresolved & (required | selected)


def required_curriculum_outcomes(payload):
    capabilities = {c["capability_id"]: c for c in payload["capabilities"]}
    closure = {key for key, cap in capabilities.items() if cap["importance"] == "required"}
    if curriculum_semantics(payload) == 2:
        closure.update(key for key, cap in capabilities.items() if cap["learning_target_refs"])
        ancestors = _ancestors(capabilities)
        closure.update(parent for key in tuple(closure) for parent in ancestors[key] if parent in capabilities)
    return {o["outcome_id"] for key in closure for o in capabilities[key]["outcomes"]}


def _validate_permission_obligations(document, payload):
    from app.domain.planning.constraint_adaptation import constraint_kind

    constraints = {c["constraint_id"]: c for c in payload["constraints"]}
    tasks = {task["stable_key"]: task for stage in document["stages"] for task in stage["tasks"]}
    kinds = {"allowed", "unauthorized", "out_of_scope", "invalid_parameters", "execution_failure", "json_protection"}
    seen = set()
    for item in _array(document["permission_obligations"], 30):
        _fields(item, {"constraint_ref", "source_refs", "project_context_hash", "task_ref", "outcome_refs", "acceptance_refs",
            "authorization_before_execution", "default_deny", "allowed_scope", "input_validation", "cases", "practice_artifact"})
        constraint = constraints.get(item["constraint_ref"])
        if (constraint is None or constraint_kind(constraint["text"]) != "local_tool_scope"
                or item["constraint_ref"] in seen):
            _reject("permission_constraint")
        seen.add(item["constraint_ref"])
        if (_ids(item["source_refs"], nonempty=True) != set(constraint["source_refs"])
                or item["project_context_hash"] != payload["profile_context"]["project_context_hash"]
                or not payload["profile_context"]["project_context"]):
            _reject("permission_source_binding")
        task = tasks.get(item["task_ref"])
        if task is None:
            _reject("permission_task_binding")
        refs = _ids(item["outcome_refs"], task["outcome_refs"], nonempty=True)
        acceptances = {task["stable_key"] + ".acceptance." + str(i): acceptance for i, acceptance in enumerate(task["acceptance"])}
        acceptance_refs = _ids(item["acceptance_refs"], acceptances, nonempty=True, limit=30)
        if any(not refs & set(acceptances[ref]["outcome_refs"]) for ref in acceptance_refs):
            _reject("permission_acceptance_binding")
        if (item["authorization_before_execution"] is not True or item["default_deny"] is not True
                or item["input_validation"] is not True or item["allowed_scope"] != "user_authorized_local_tasks"):
            _reject("permission_boundary")
        _text(item["practice_artifact"], 2000)
        cases = _array(item["cases"], 6, nonempty=True)
        case_kinds, case_refs, artifacts, texts = set(), set(), set(), set()
        for case in cases:
            _fields(case, {"kind", "acceptance_ref", "artifact"})
            if case["kind"] not in kinds or case["kind"] in case_kinds or case["acceptance_ref"] not in acceptance_refs:
                _reject("permission_case_binding")
            _text(case["artifact"], 2000)
            case_kinds.add(case["kind"])
            case_refs.add(case["acceptance_ref"])
            artifacts.add(case["artifact"].strip())
            texts.add(acceptances[case["acceptance_ref"]]["text"].strip())
        # Distinct cases must have inspectable case-specific records. This is
        # a structural check; independent review still assesses their meaning.
        if case_kinds != kinds or len(case_refs) != 6 or len(artifacts) != 6 or len(texts) != 6:
            _reject("permission_case_completeness")


def record_case_findings(curriculum, findings):
    try:
        if type(curriculum) is not CurriculumPlan or type(findings) is not tuple or len(findings) > 20:
            _reject("case_findings")
        requirements = {req["requirement_id"]: req for req in curriculum.project_study_requirements}
        existing = json.loads(curriculum._findings)
        for finding in findings:
            if type(finding) is not CaseFinding:
                _reject("case_finding")
            req = requirements.get(finding.requirement_id)
            if req is None or finding.requirement_hash != req["requirement_hash"]:
                _reject("case_finding_binding")
            if type(finding.candidates) is not tuple or len(finding.candidates) > 5 or type(finding.reason_codes) is not tuple:
                _reject("case_finding_shape")
            _strings(list(finding.reason_codes), 12, text_limit=100)
            candidates = []
            for candidate in finding.candidates:
                case = _case(candidate)
                if candidate.mode != req["mode"] or set(candidate.outcome_refs) - set(req["outcome_refs"]):
                    _reject("case_finding_scope")
                if candidate.qualification != "reviewed_candidate":
                    _reject("case_finding_promotion")
                candidates.append(case)
            if len({c["case_id"] for c in candidates}) != len(candidates):
                _reject("case_finding_duplicate")
            existing.append({"requirement_id": finding.requirement_id, "requirement_hash": finding.requirement_hash,
                "candidates": sorted(candidates, key=lambda c: c["case_id"]), "reason_codes": sorted(set(finding.reason_codes))})
        existing = sorted({canonical_json(f): f for f in existing}.values(), key=canonical_json)
        if len(existing) > 20 or len(canonical_json(existing).encode("utf-8")) > 32768:
            _reject("case_finding_size")
        return CurriculumPlan(curriculum._json, canonical_json(existing))
    except (TypeError, ValueError, KeyError, AttributeError):
        _reject("case_findings")


CURRICULUM_SHAPE = {
    "schema_version": 1, "input_hash": "copy input_hash", "status": "complete|incomplete",
    "stages": [{"stage_id": "stage_mcp", "title": "教学阶段", "role": "common_core|specialization|project_study|integration",
        "order_index": 0, "why_now": "为何现在学", "what_to_learn": "本阶段教学范围",
        "capability_ids": ["mcp"], "outcome_refs": ["精确B outcome ID"], "prerequisite_stage_refs": [],
        "knowledge": [{"stable_key": "knowledge_mcp", "title": "知识点", "objectives": ["目标"],
            "outcome_refs": ["精确B outcome ID"], "material_refs": ["输入material ID"]}],
        "units": [{"stable_key": "unit_mcp", "title": "学习单元", "objectives": ["目标"],
            "outcome_refs": ["精确B outcome ID"], "knowledge_refs": ["knowledge_mcp"],
            "rubric": [{"text": "检查标准", "outcome_refs": ["精确B outcome ID"]}]}],
        "assignments": [{"material_id": "输入material ID", "role": "PRIMARY|SUPPLEMENT|REFERENCE|CASE_STUDY",
            "outcome_refs": ["精确材料支持的outcome ID"], "reading_focus": "具体阅读重点"}],
        "guidance": {"previous_relation": "与已有证据的关系", "learning_focus": ["学习重点"], "comparison_focus": [],
            "practice_delta": {"baseline": "起点", "increment": "新增", "preserved": "保留",
                "validation": "如何核验", "reuse": "怎样迁回"}},
        "tasks": [{"stable_key": "task_mcp", "title": "实践", "goal": "目标", "in_scope": ["范围"], "out_scope": [],
            "outcome_refs": ["精确B outcome ID"], "knowledge_refs": ["knowledge_mcp"], "practice_kind": "carrier|micro_exercise",
            "acceptance": [{"text": "实际检查标准", "outcome_refs": ["精确B outcome ID"]}]}], "project_study_refs": []}],
    "carrier": {"kind": "user_project|starter", "project_context_hash": "copy input profile_context.project_context_hash",
        "reason": "载体选择理由", "description": "保留用户项目或最小starter",
        "final_artifact": {"description": "最终可检查成果", "acceptance": [{"text": "验收标准", "outcome_refs": []}]}},
    "project_study_requirements": [{"requirement_id": "study_mcp", "problem": "需要调查的问题", "mode": "whole_core|slices",
        "outcome_refs": ["精确B outcome ID"], "avoid_scope": ["不读整仓库"], "expected_outputs": ["产出"],
        "normal_behavior": ["正常行为"], "failure_behavior": ["失败行为"], "inputs_outputs": [{"input": "输入", "output": "输出"}],
        "design_questions": ["设计问题"], "selected_case_ref": None}],
    "unresolved": [{"outcome_ref": "仍未解决B outcome ID", "reason": "source_unavailable"}],
    "constraint_refs": [], "source_limitations": [],
}
