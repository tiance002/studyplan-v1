"""Pure V2 entity blueprints; publication and database materialization are P2.

The full frozen context and upstream authorities are explicit arguments because a
digest cannot recover the Profile's claims or accepted capability definitions.
No entity IDs, runtime identities, I/O or curriculum decisions are produced here.
"""
import json
import re
from dataclasses import asdict, dataclass, field, replace

from app.core.errors import ValidationAppError
from app.core.ids import canonical_json, content_hash
from app.domain.planning.capabilities import (
    CAPABILITY_SCHEMA,
    ITEM_FIELDS,
    CapabilityPlan,
    CapabilityPlanValidator,
    validate_capability_planning_input,
)
from app.domain.planning.capability_policy import CAPABILITY_POLICY
from app.domain.planning.content_coverage import CoverageEvaluator, ReviewedContentIndex, _plan_definitions
from app.domain.planning.curriculum import (
    CaseFinding,
    CurriculumContext,
    CurriculumPlan,
    ProjectCase,
    _sort_output_refs,
    curriculum_constraint_assessments,
    prepare_curriculum,
    record_case_findings,
    validate_curriculum_output,
)
from app.domain.planning.domain_verification import reader_authority, validate_domain_evidence
from app.domain.planning.goal_requirements import GoalRequirementProfile
from app.domain.planning.resource_research import ResearchRequirement, ResourceResearchResult

COMPILER_VERSION = "curriculum-compiler-v1"
COMPILED_CONTRACT_VERSION = "CompiledCurriculumV1"
_SERVER_FIELDS = {"compile_sources", "compile_materials", "compile_cases", "compile_context"}


def _reject(field, **details):
    raise ValidationAppError("Curriculum Compiler 合同校验失败", field=field, **details)


@dataclass(frozen=True, slots=True)
class CurriculumSourceFacts:
    """Existing frozen source authorities needed to reproduce Item6 projection.

    This packet carries metadata/review facts, never source bodies. It is passed
    by the server; a caller-authored Context alone is not source authority.
    """
    reviewed_index: ReviewedContentIndex
    catalog_sources: tuple = ()
    access_proofs: tuple = ()
    project_cases: tuple = ()


@dataclass(frozen=True, slots=True)
class PublicKnowledgeBinding:
    """Server-approved exact semantic binding, still requiring P2 DB verification.

    definition_hash covers title, ordered objectives and canonical outcome refs.
    A material/source identity is never treated as a Knowledge identity.
    """
    curriculum_stable_key: str
    public_identity: str
    public_version: str
    definition_hash: str


def knowledge_definition_hash(knowledge):
    return content_hash({"title": knowledge["title"], "objectives": knowledge["objectives"],
        "outcome_refs": sorted(knowledge["outcome_refs"])})


@dataclass(frozen=True, slots=True)
class ExecutionManifest:
    _json: str = field(repr=False)

    def to_payload(self):
        return json.loads(self._json)


@dataclass(frozen=True, slots=True)
class CompiledPlan:
    _json: str = field(repr=False)
    manifest: ExecutionManifest

    @property
    def digest(self):
        return content_hash(self.to_payload())

    def to_payload(self):
        return json.loads(self._json)


def _validate_authorities(context, profile, plan, source_facts):
    if type(context) is not CurriculumContext or type(profile) is not GoalRequirementProfile or type(plan) is not CapabilityPlan:
        _reject("frozen_input_types")
    if profile.status != "ready" or plan.source_goal_profile_hash != profile.profile_hash:
        _reject("profile_binding")
    if not validate_capability_planning_input({"profile": profile.to_payload(), "policy": CAPABILITY_POLICY.to_payload(),
        "verification_evidence": [e.to_payload() for e in plan.verification_evidence]}, CAPABILITY_SCHEMA):
        _reject("profile_authority")
    _plan_definitions(plan)
    items = []
    for capability in plan.capabilities:
        item = {name: asdict(capability)[name] for name in ITEM_FIELDS}
        # Validator adds this server policy fact after validating the original wire.
        if plan.route_kind == "systematic_agent_route" and capability.capability_id == "mcp":
            item["policy_refs"] = [ref for ref in item["policy_refs"] if ref != CAPABILITY_POLICY.systematic_mcp_policy_ref]
        items.append(item)
    rebuilt = CapabilityPlanValidator().validate({"schema_version": plan.schema_version,
        "source_goal_profile_hash": plan.source_goal_profile_hash, "policy_version": plan.policy_version,
        "route_kind": plan.route_kind, "status": "ready", "capabilities": items,
        "claim_bindings": [asdict(b) for b in plan.claim_bindings],
        "constraint_effects": [asdict(e) for e in plan.constraint_effects], "clarification_questions": []},
        profile=profile, verification_evidence=plan.verification_evidence)
    if rebuilt != plan:
        _reject("capability_plan_authority")
    payload = context.to_payload()
    if not validate_domain_evidence(profile, plan.verification_evidence, domain_approvals=context._domain_approvals):
        _reject("domain_approval_required")
    if any(not any(a.plan_hash == plan.plan_hash and a.evidence == e for a in context._domain_approvals)
           for e in plan.verification_evidence):
        _reject("domain_plan_approval_binding")
    authority = reader_authority(plan, domain_approvals=context._domain_approvals)
    if canonical_json(payload.get("domain_authority")) != canonical_json(authority):
        _reject("domain_authority_binding")
    sources = payload["sources"]
    research = context.research
    if type(research) is not ResourceResearchResult or replace(research) != research:
        _reject("research_authority")
    expected_sources = {"profile_hash": profile.profile_hash, "capability_plan_hash": plan.plan_hash,
        "coverage_hash": research.source_coverage_result_hash, "research_hash": research.result_hash,
        "gap_set_hash": research.source_gap_set_hash, "reviewed_index_hash": payload["sources"]["reviewed_index_hash"],
        "research_checked_at": research.checked_at, "research_budget_usage": dict(research.budget_usage)}
    if (sources != expected_sources or research.source_profile_hash != profile.profile_hash
            or research.source_capability_plan_hash != plan.plan_hash):
        _reject("context_source_binding")
    profile_context = {"project_context": profile.project_context,
        "project_context_hash": content_hash({"project_context": profile.project_context}),
        "starting_point": profile.starting_point, "outcome_purpose": profile.outcome_purpose,
        "requirements": [asdict(r) for r in profile.required_requirements]}
    if (canonical_json(payload["profile_context"]) != canonical_json(profile_context)
            or canonical_json(payload["constraints"]) != canonical_json([asdict(c) for c in profile.hard_constraints])
            or payload["accepted_known"] != sorted(c.capability_id for c in plan.accepted_known_capabilities)):
        _reject("context_profile_binding")
    by_id = {c.capability_id: c for c in plan.learning_capabilities}
    if len(payload["capabilities"]) != len(by_id):
        _reject("context_capability_binding")
    available = {ref for material in payload["materials"] if material["usable"] for ref in material["outcome_refs"]}
    unresolved = {o.outcome_id for entry in research.entries for o in entry.unresolved_outcomes}
    for entry in payload["capabilities"]:
        capability = by_id.get(entry["capability_id"])
        if capability is None:
            _reject("context_capability_binding")
        expected = {"capability_id": capability.capability_id, "title": capability.title,
            "importance": capability.learning_requirement, "desired_depth": capability.desired_depth,
            "project_usage": capability.project_usage, "outcomes": [asdict(o) for o in capability.learning_outcomes],
            "prerequisites": list(capability.prerequisite_refs), "requirement_refs": list(capability.requirement_refs),
            "unavailable_outcomes": sorted(o.outcome_id for o in capability.learning_outcomes
                if o.outcome_id not in available or o.outcome_id in unresolved)}
        if canonical_json(entry) != canonical_json(expected):
            _reject("context_capability_binding")
    researched = set()
    for entry in research.entries:
        c = by_id.get(entry.requirement.capability_id)
        if c is None or c.capability_id in researched or any(o not in c.learning_outcomes for o in entry.requirement.must_teach):
            _reject("research_requirement_binding")
        researched.add(c.capability_id)
        expected = ResearchRequirement(c.capability_id, entry.requirement.must_teach, c.learning_requirement,
            c.desired_depth, c.requirement_refs, profile.starting_point, profile.hard_constraints, profile.learner_claims)
        if entry.requirement != expected:
            _reject("research_requirement_binding")
    if (type(source_facts) is not CurriculumSourceFacts or type(source_facts.reviewed_index) is not ReviewedContentIndex
            or any(type(getattr(source_facts, name)) is not tuple for name in ("catalog_sources", "access_proofs", "project_cases"))):
        _reject("source_facts")
    # Reuse Item6's authoritative deterministic producer. Self-consistent hashes
    # in a forged Context cannot promote research qualification, URL/version or
    # evidence, nor can they modify covered-content review/access facts.
    index = source_facts.reviewed_index
    rebuilt_context = prepare_curriculum(profile, plan, CoverageEvaluator().evaluate(plan, index), context.research, index,
        catalog_sources=source_facts.catalog_sources, access_proofs=source_facts.access_proofs,
        project_cases=source_facts.project_cases, domain_approvals=context._domain_approvals)
    if canonical_json(rebuilt_context.to_payload()) != canonical_json(payload):
        _reject("source_context_projection_binding")
    return payload


def _normalized_mapping_document(document, payload):
    """Canonical mapping input; frozen source bytes/hash remain a separate argument.

    Reuse Item6's set representation and the exact historical empty-constraint
    compatibility. This mechanical function grants no input/domain authority.
    """
    doc = json.loads(canonical_json(document))
    wire = {key: value for key, value in doc.items() if key not in _SERVER_FIELDS | {"case_findings", "plan_hash"}}
    _sort_output_refs(wire)
    doc.update(wire)
    actual_context = doc["compile_context"]
    if ("constraint_assessments" not in actual_context and not payload["constraints"]
            and curriculum_constraint_assessments(wire, payload) == []):
        doc["compile_context"] = actual_context | {"constraint_assessments": []}
    return doc


def _validated_curriculum(curriculum, context, payload):
    if type(curriculum) is not CurriculumPlan:
        _reject("curriculum_type")
    document = curriculum.to_payload()
    raw = {key: value for key, value in document.items() if key not in _SERVER_FIELDS | {"case_findings", "plan_hash"}}
    # Production compilation never enables fixture domain authority.
    rebuilt = validate_curriculum_output(raw, payload, domain_approvals=context._domain_approvals)
    expected = rebuilt.to_payload()
    actual_context = _normalized_mapping_document(document, payload)["compile_context"]
    for name in _SERVER_FIELDS:
        actual = actual_context if name == "compile_context" else document[name]
        if canonical_json(actual) != canonical_json(expected[name]):
            _reject("server_snapshot_binding", snapshot=name)
    findings = []
    for item in document["case_findings"]:
        candidates = tuple(ProjectCase(**(c | {"outcome_refs": tuple(c["outcome_refs"]),
            "evidence_refs": tuple(tuple(e) for e in c["evidence_refs"]), "limitations": tuple(c["limitations"])}))
            for c in item["candidates"])
        findings.append(CaseFinding(item["requirement_id"], item["requirement_hash"], candidates, tuple(item["reason_codes"])))
    checked_findings = record_case_findings(rebuilt, tuple(findings)).to_payload()["case_findings"]
    if checked_findings != document["case_findings"]:
        _reject("case_findings_binding")
    if document["status"] != "complete":
        _reject("incomplete", diagnostics={"status": document["status"], "unresolved": document["unresolved"],
            "constraint_assessments": expected["compile_context"]["constraint_assessments"],
            "source_limitations": document["source_limitations"],
            "unselected_project_study": [r for r in document["project_study_requirements"] if not r["selected_case_ref"]],
            "case_findings": checked_findings})
    # Reference sets use the validator's canonical representation; source snapshot
    # still retains the exact originally frozen payload and original plan hash.
    return _normalized_mapping_document(expected | {"case_findings": checked_findings}, payload)


def _public_bindings(bindings, nodes):
    if type(bindings) is not tuple or len(bindings) > 250:
        _reject("public_knowledge_bindings")
    by_key = {node["stable_key"]: node for node in nodes}
    resolved, public = {}, {}
    for binding in bindings:
        if type(binding) is not PublicKnowledgeBinding or binding.curriculum_stable_key not in by_key:
            _reject("public_knowledge_binding")
        if binding.curriculum_stable_key in resolved:
            _reject("duplicate_public_binding")
        if any(not isinstance(value, str) or not value.strip() or len(value) > 200
               for value in (binding.public_identity, binding.public_version)):
            _reject("public_knowledge_identity")
        digest = knowledge_definition_hash(by_key[binding.curriculum_stable_key])
        if not isinstance(binding.definition_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", binding.definition_hash) or digest != binding.definition_hash:
            _reject("public_knowledge_definition")
        fact = (binding.public_version, digest)
        if binding.public_identity in public and public[binding.public_identity] != fact:
            _reject("public_knowledge_conflict")
        public[binding.public_identity] = fact
        resolved[binding.curriculum_stable_key] = asdict(binding)
    return resolved


def compile_curriculum(curriculum, *, context, profile, capability_plan, source_facts, public_knowledge_bindings=()):
    """Validate frozen authorities, compile lossless blueprints, freeze a manifest.

    Output is a publishable *candidate* only, requiring the P2 typed snapshot,
    identity/version checks and atomic persistence bridge documented separately.
    """
    try:
        payload = _validate_authorities(context, profile, capability_plan, source_facts)
        doc = _validated_curriculum(curriculum, context, payload)
        return _compile_validated(doc, curriculum=curriculum, payload=payload, profile=profile,
            capability_plan=capability_plan, context=context, public_knowledge_bindings=public_knowledge_bindings)
    except (TypeError, ValueError, AttributeError, KeyError, RecursionError):
        _reject("input_shape")


def _compile_validated(doc, *, curriculum, payload, profile, capability_plan, context, public_knowledge_bindings=()):
    """Single deterministic mapping after authority validation; no qualification is issued here."""
    stages, nodes, units, guidance, tasks, assignments, relations = [], [], [], [], [], [], []
    materials = {m["material_id"]: m for m in doc["compile_materials"]}
    for stage in doc["stages"]:
        ref = stage["stage_id"]
        stages.append({key: value for key, value in stage.items()
            if key not in {"role", "knowledge", "units", "guidance", "tasks", "assignments"}}
            | {"stable_key": "v2.stage." + content_hash({"curriculum_stage_id": ref}),
                "curriculum_role": stage["role"], "knowledge_refs": [n["stable_key"] for n in stage["knowledge"]],
                "unit_refs": [u["stable_key"] for u in stage["units"]], "task_refs": [t["stable_key"] for t in stage["tasks"]]})
        nodes.extend(node | {"stage_ref": ref, "identity_kind": "curriculum_candidate"} for node in stage["knowledge"])
        units.extend(unit | {"stage_ref": ref} for unit in stage["units"])
        guidance.append(stage["guidance"] | {"stage_ref": ref, "why_now": stage["why_now"],
            "practice_delta": {key: value if key == "baseline" else [value]
                for key, value in stage["guidance"]["practice_delta"].items()}})
        tasks.extend(task | {"stage_ref": ref, "order_index": index} for index, task in enumerate(stage["tasks"]))
        for index, assignment in enumerate(stage["assignments"]):
            assignments.append(assignment | {"stage_ref": ref, "order_index": index,
                "role": assignment["role"].lower(), "source_snapshot": materials[assignment["material_id"]]})
        relations.extend({"kind": "stage_prerequisite", "prerequisite_stage_ref": prior, "stage_ref": ref}
            for prior in stage["prerequisite_stage_refs"])
    bindings = _public_bindings(public_knowledge_bindings, nodes)
    for node in nodes:
        if node["stable_key"] in bindings:
            node.update(identity_kind="public_knowledge", public_binding=bindings[node["stable_key"]])
    cases = {c["case_id"]: c for c in doc["compile_cases"]}
    projects = [{"requirement": requirement, "case": cases[requirement["selected_case_ref"]]}
        for requirement in doc["project_study_requirements"]]
    identities = {"stages": [{"curriculum_stage_id": s["stage_id"], "semantic_key": s["stable_key"]} for s in stages],
        "knowledge": [{"curriculum_stable_key": n["stable_key"], "identity_kind": n["identity_kind"],
            **({"public_binding": n["public_binding"]} if "public_binding" in n else {})} for n in nodes],
        "units": [{"curriculum_stable_key": u["stable_key"]} for u in units],
        "tasks": [{"curriculum_stable_key": t["stable_key"]} for t in tasks],
        "materials": [{key: m[key] for key in ("material_id", "source_id", "source_version", "section_refs", "content_hash")}
            for m in doc["compile_materials"]]}
    compiled = {"compiler_version": COMPILER_VERSION, "contract_version": COMPILED_CONTRACT_VERSION,
        "stages": stages, "nodes": nodes, "units": units, "relations": relations, "guidance": guidance,
        "resource_assignments": assignments, "practice": {"carrier": doc["carrier"], "tasks": tasks,
            "final_artifact": doc["carrier"]["final_artifact"]}, "project_study": projects,
        "constraints": {"hard_constraints": payload["constraints"], "constraint_refs": doc["constraint_refs"],
            "assessments": doc["compile_context"]["constraint_assessments"]},
        "unresolved": doc["unresolved"], "source_limitations": doc["source_limitations"],
        "source_snapshots": {"curriculum": curriculum.to_payload(), "curriculum_context": payload,
            "goal_requirement_profile": profile.to_payload(), "capability_plan": capability_plan.to_payload()}}
    manifest = {"compiler_version": COMPILER_VERSION, "contract_version": COMPILED_CONTRACT_VERSION,
        "input_curriculum_plan_hash": curriculum.plan_hash, "upstream_sources": doc["compile_sources"]
            | {"curriculum_input_hash": context.input_hash, "policy_version": capability_plan.policy_version,
                "policy_hash": content_hash(CAPABILITY_POLICY.to_payload())},
        "compiled_payload_digest": content_hash(compiled), "stable_identity_mapping": identities,
        "validation": {"completeness": "PASS", "source_binding": "PASS", "upstream_authority": "PASS",
            "source_content_semantics": "NOT RUN", "public_identity_database": "NOT RUN"}}
    return CompiledPlan(canonical_json(compiled), ExecutionManifest(canonical_json(manifest)))
