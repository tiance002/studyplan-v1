"""P1 compiler tests: synthetic teaching, actual frozen local source metadata."""
import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest
from app.core.errors import ValidationAppError
from app.core.ids import canonical_json, content_hash
from app.domain.planning.content_coverage import ReviewedContentIndex
from app.domain.planning.curriculum import (
    CurriculumPlan,
    ProjectCase,
    prepare_curriculum,
    validate_curriculum_output,
)
from app.domain.planning.curriculum_compiler import (
    CurriculumSourceFacts,
    PublicKnowledgeBinding,
    compile_curriculum,
    knowledge_definition_hash,
)

from backend.tests.unit.test_capability_planning import cap, known_python, plan, profile, wire
from backend.tests.unit.test_curriculum import local_mcp_inputs, output, prepared


def inputs(*, project=None, excluded=False, constraints=(), systematic=False):
    p = replace(profile("学习MCP", constraints=constraints), project_context=project)
    items = [cap(p, "mcp", project_usage="excluded" if excluded else "required")]
    if systematic:
        items.insert(0, cap(p, "llm.api"))
        items.append(cap(p, "tool.calling"))
    frozen = plan(p, wire(p, *items, route_kind="systematic_agent_route" if systematic else "narrow_goal"))
    if systematic:
        from app.domain.planning.content_coverage import CoverageEvaluator
        from app.domain.planning.resource_gaps import extract

        from backend.tests.unit.test_resource_research import Bodies, Search, body, candidate, run

        class DistinctSearch(Search):
            def find(self, query):
                self.calls.append(query)
                return [candidate("https://github.com/demo/tutorial" + str(len(self.calls)))]

        class DistinctBodies(Bodies):
            def read(self, candidate, **kw):
                result = body()
                result.url = candidate.url + "/blob/main/chapter.md"
                result.resource_id = "resource_" + content_hash({"url": result.url})
                chunk = result.chunks[0]
                chunk["resource_id"] = result.resource_id
                chunk["chunk_id"] = "chunk_" + content_hash({k: v for k, v in chunk.items() if k not in {"chunk_id", "text"}})
                self.produced.append(result)
                return result

        index = ReviewedContentIndex("empty", (), (), ())
        coverage = CoverageEvaluator().evaluate(frozen, index)
        research, *_ = run((p, frozen, coverage, extract(frozen, coverage)), github=DistinctSearch(), bodies=DistinctBodies())
        ctx = prepare_curriculum(p, frozen, coverage, research, index)
    else:
        ctx = prepared(p, frozen)
    raw = output(ctx)
    if constraints == ("只使用免费教材",):
        raw["status"] = "complete"
    curriculum = validate_curriculum_output(raw, ctx.to_payload())
    return curriculum, dict(context=ctx, profile=p, capability_plan=frozen,
        source_facts=CurriculumSourceFacts(ReviewedContentIndex("empty", (), (), ())))


def forged(curriculum, change):
    doc = json.loads(curriculum._json)
    change(doc)
    return CurriculumPlan(canonical_json(doc), curriculum._findings)


def test_complete_deterministic_and_frozen():
    curriculum, kw = inputs()
    first = compile_curriculum(curriculum, **kw)
    second = compile_curriculum(curriculum, **kw)
    assert first.digest == second.digest == content_hash(first.to_payload())
    assert first.manifest.to_payload()["compiled_payload_digest"] == first.digest
    payload = first.to_payload()
    payload["stages"].clear()
    assert first.to_payload()["stages"]
    manifest = first.manifest.to_payload()
    manifest["stable_identity_mapping"].clear()
    assert first.manifest.to_payload()["stable_identity_mapping"]


def test_all_original_facts_and_blueprints_are_retained():
    curriculum, kw = inputs(project="已有CLI，不新建演示项目", excluded=True)
    result = compile_curriculum(curriculum, **kw).to_payload()
    doc = curriculum.to_payload()
    assert result["source_snapshots"]["curriculum"] == doc
    assert result["source_snapshots"]["goal_requirement_profile"] == kw["profile"].to_payload()
    assert result["source_snapshots"]["capability_plan"] == kw["capability_plan"].to_payload()
    assert result["practice"]["carrier"] == doc["carrier"]
    assert result["practice"]["tasks"][0]["practice_kind"] == "micro_exercise"
    assert result["practice"]["final_artifact"] == doc["carrier"]["final_artifact"]
    assert result["stages"][0]["curriculum_role"] == "specialization"
    assert "section_kind" not in result["stages"][0]
    assert result["units"][0]["rubric"] == doc["stages"][0]["units"][0]["rubric"]
    assert result["guidance"][0]["practice_delta"]["baseline"] == doc["stages"][0]["guidance"]["practice_delta"]["baseline"]
    assert result["guidance"][0]["practice_delta"]["increment"] == [doc["stages"][0]["guidance"]["practice_delta"]["increment"]]
    assert result["resource_assignments"][0]["role"] == "primary"
    assert result["resource_assignments"][0]["source_snapshot"] == doc["compile_materials"][0]
    assert "node_id" not in result["nodes"][0]


@pytest.mark.parametrize("field", ["compile_sources", "compile_materials", "compile_cases", "compile_context"])
def test_server_snapshots_cannot_be_forged(field):
    curriculum, kw = inputs()
    bad = forged(curriculum, lambda d: d.__setitem__(field, {}))
    with pytest.raises(ValidationAppError):
        compile_curriculum(bad, **kw)


@pytest.mark.parametrize("kind", ["policy", "outcomes", "refs", "claims", "profile"])
def test_frozen_upstream_is_revalidated(kind):
    curriculum, kw = inputs()
    frozen = kw["capability_plan"]
    c = frozen.capabilities[0]
    if kind == "policy":
        kw["capability_plan"] = replace(frozen, policy_version="obsolete")
    elif kind == "outcomes":
        kw["capability_plan"] = replace(frozen, capabilities=(replace(c, learning_outcomes=()),))
    elif kind == "refs":
        kw["capability_plan"] = replace(frozen, capabilities=(replace(c, requirement_refs=("req_" + "a" * 64,)),))
    elif kind == "claims":
        kw["capability_plan"] = replace(frozen, capabilities=(replace(c, disposition="accepted_known"),))
    else:
        kw["profile"] = replace(kw["profile"], target_summary="changed")
    with pytest.raises(ValidationAppError):
        compile_curriculum(curriculum, **kw)


@pytest.mark.parametrize("field,value", [("material_id", "bad"), ("role", "UNKNOWN")])
def test_illegal_assignment_rejected(field, value):
    curriculum, kw = inputs()
    bad = forged(curriculum, lambda d: d["stages"][0]["assignments"][0].__setitem__(field, value))
    with pytest.raises(ValidationAppError):
        compile_curriculum(bad, **kw)


def test_incomplete_has_original_diagnostics_and_no_candidate():
    p = profile("学习MCP")
    frozen = plan(p, wire(p, cap(p, "mcp")))
    ctx = prepared(p, frozen, unresolved=True)
    curriculum = validate_curriculum_output(output(ctx), ctx.to_payload())
    with pytest.raises(ValidationAppError) as error:
        compile_curriculum(curriculum, context=ctx, profile=p, capability_plan=frozen,
            source_facts=CurriculumSourceFacts(ReviewedContentIndex("empty", (), (), ())))
    assert error.value.details["diagnostics"]["unresolved"] == curriculum.to_payload()["unresolved"]


def test_pending_hard_constraint_rejected():
    curriculum, kw = inputs(constraints=("不向外部服务发送用户数据",))
    assert curriculum.status == "incomplete"
    with pytest.raises(ValidationAppError) as error:
        compile_curriculum(curriculum, **kw)
    assert error.value.details["diagnostics"]["constraint_assessments"]


def test_accepted_python_is_only_prerequisite_not_teaching():
    p = profile("会Python，学习JSON CLI", claims=("会Python",))
    frozen = plan(p, wire(p, known_python(p), cap(p, "json.cli"), claim_bindings=[
        {"claim_ref": p.learner_claims[0].claim_id, "capability_id": "python.core"}]))
    ctx = prepared(p, frozen)
    result = compile_curriculum(validate_curriculum_output(output(ctx), ctx.to_payload()),
        context=ctx, profile=p, capability_plan=frozen,
        source_facts=CurriculumSourceFacts(ReviewedContentIndex("empty", (), (), ()))).to_payload()
    assert result["source_snapshots"]["curriculum"]["compile_context"]["accepted_known"] == ["python.core"]
    assert [c for s in result["stages"] for c in s["capability_ids"]] == ["json.cli"]


@pytest.mark.parametrize("mode", ["whole_core", "slices"])
def test_project_study_case_is_independent_of_practice(mode):
    curriculum, kw = inputs(project="已有CLI")
    refs = tuple(kw["context"].to_payload()["capabilities"][0]["outcomes"][i]["outcome_id"] for i in range(3))
    case = ProjectCase("case_fixture", "https://github.com/demo/tutorial", "fixture-v1", mode, refs,
        (("fixture:bounded-behavior", content_hash({"synthetic": True})),), "bounded_reviewed")
    ctx = prepared(kw["profile"], kw["capability_plan"], project_cases=(case,))
    raw = output(ctx, project_study=True)
    raw["project_study_requirements"][0].update(mode=mode, selected_case_ref=case.case_id)
    raw["status"] = "complete"
    validated = validate_curriculum_output(raw, ctx.to_payload())
    result = compile_curriculum(validated, **(kw | {"context": ctx,
        "source_facts": replace(kw["source_facts"], project_cases=(case,))})).to_payload()
    assert result["project_study"][0]["requirement"] == validated.to_payload()["project_study_requirements"][0]
    assert result["project_study"][0]["case"]["case_id"] == case.case_id
    assert result["practice"]["carrier"]["kind"] == "user_project"


def test_systematic_policy_and_real_stage_dependencies_preserved():
    curriculum, kw = inputs(systematic=True)
    result = compile_curriculum(curriculum, **kw).to_payload()
    assert [s["curriculum_role"] for s in result["stages"]] == [s["role"] for s in curriculum.to_payload()["stages"]]
    assert result["relations"] == [{"kind": "stage_prerequisite", "prerequisite_stage_ref": "stage_llm_api", "stage_ref": "stage_tool_calling"}]


@pytest.mark.parametrize("field", ["title", "why_now", "what_to_learn"])
def test_necessary_content_changes_digest(field):
    curriculum, kw = inputs()
    raw = output(kw["context"])
    raw["stages"][0][field] += "（新内容）"
    changed = validate_curriculum_output(raw, kw["context"].to_payload())
    assert compile_curriculum(changed, **kw).digest != compile_curriculum(curriculum, **kw).digest


def test_reference_sets_canonical_but_ordered_units_and_tasks_are_meaningful():
    curriculum, kw = inputs()
    raw = output(kw["context"])
    stage = raw["stages"][0]
    stage["units"].append(deepcopy(stage["units"][0]) | {"stable_key": "unit_second", "title": "第二单元"})
    stage["tasks"].append(deepcopy(stage["tasks"][0]) | {"stable_key": "task_second", "title": "第二任务"})
    first = validate_curriculum_output(raw, kw["context"].to_payload())
    stage["outcome_refs"].reverse()
    assert compile_curriculum(first, **kw).digest == compile_curriculum(validate_curriculum_output(raw, kw["context"].to_payload()), **kw).digest
    stage["units"].reverse()
    stage["tasks"].reverse()
    second = compile_curriculum(validate_curriculum_output(raw, kw["context"].to_payload()), **kw)
    assert second.digest != compile_curriculum(first, **kw).digest
    assert second.to_payload()["units"][0]["stable_key"] == "unit_second"


@pytest.mark.parametrize("complete", [True, False])
def test_original_item6_bytes_are_consumed(complete):
    path = Path(__file__).parents[3] / "var/planning-v2-item6-implementation-20261008" / ("example-complete.json" if complete else "example-incomplete.json")
    if not path.exists():
        pytest.skip("original ignored Item6 evidence unavailable")
    original_bytes = path.read_bytes()
    doc = json.loads(original_bytes)["curriculum"]
    p, frozen, index, source, proof = local_mcp_inputs()
    ctx = prepared(p, frozen, index if complete else None, catalog_sources=(source,) if complete else (),
        access_proofs=(proof,) if complete else (), unresolved=not complete)
    facts = CurriculumSourceFacts(index, (source,), (proof,)) if complete else CurriculumSourceFacts(ReviewedContentIndex("empty", (), (), ()))
    # Original files predate the empty constraint_assessments field; preserve original bytes/hash.
    findings = doc.pop("case_findings")
    original_hash = doc.pop("plan_hash")
    curriculum = CurriculumPlan(canonical_json(doc), canonical_json(findings))
    assert curriculum.plan_hash == original_hash and curriculum.input_hash == ctx.input_hash
    if complete:
        result = compile_curriculum(curriculum, context=ctx, profile=p, capability_plan=frozen, source_facts=facts)
        materials = result.to_payload()["source_snapshots"]["curriculum"]["compile_materials"]
        assert {m["kind"] for m in materials} == {"covered_content", "researched_resource"}
        assert {m["qualification"] for m in materials} == {"public_reviewed", "research_checked"}
    else:
        with pytest.raises(ValidationAppError):
            compile_curriculum(curriculum, context=ctx, profile=p, capability_plan=frozen, source_facts=facts)
    assert path.read_bytes() == original_bytes


def two_knowledge_nodes(*, different_title=False):
    _, kw = inputs()
    raw = output(kw["context"])
    stage = raw["stages"][0]
    stage["knowledge"].append(deepcopy(stage["knowledge"][0]) | {"stable_key": "knowledge_second"})
    if different_title:
        stage["knowledge"][1]["title"] += "独立知识"
    stage["units"][0]["knowledge_refs"].append("knowledge_second")
    return validate_curriculum_output(raw, kw["context"].to_payload()), kw


def binding(node, *, identity="public:mcp", version="v1", **changes):
    return PublicKnowledgeBinding(node["stable_key"], identity, version, knowledge_definition_hash(node), **changes)


def test_same_public_identity_can_serve_multiple_nodes_and_units():
    curriculum, kw = two_knowledge_nodes()
    raw = {key: value for key, value in curriculum.to_payload().items()
        if key not in {"compile_sources", "compile_materials", "compile_cases", "compile_context", "case_findings", "plan_hash"}}
    stage = raw["stages"][0]
    stage["units"].append(deepcopy(stage["units"][0]) | {"stable_key": "second_public_unit"})
    curriculum = validate_curriculum_output(raw, kw["context"].to_payload())
    nodes = curriculum.to_payload()["stages"][0]["knowledge"]
    result = compile_curriculum(curriculum, **kw, public_knowledge_bindings=tuple(binding(n) for n in nodes))
    mapped = result.manifest.to_payload()["stable_identity_mapping"]["knowledge"]
    assert len(mapped) == 2 and {n["public_binding"]["public_identity"] for n in mapped} == {"public:mcp"}
    assert result.to_payload()["units"][0]["knowledge_refs"] == ["knowledge_mcp", "knowledge_second"]
    assert result.to_payload()["units"][1]["knowledge_refs"] == ["knowledge_mcp", "knowledge_second"]


@pytest.mark.parametrize("conflict", ["title", "version", "definition_hash", "unknown_key", "duplicate"])
def test_public_identity_rejects_conflicting_or_unbound_definitions(conflict):
    curriculum, kw = two_knowledge_nodes(different_title=conflict == "title")
    nodes = curriculum.to_payload()["stages"][0]["knowledge"]
    bindings = [binding(n) for n in nodes]
    if conflict == "version":
        bindings[1] = replace(bindings[1], public_version="v2")
    elif conflict == "definition_hash":
        bindings[1] = replace(bindings[1], definition_hash="0" * 64)
    elif conflict == "unknown_key":
        bindings[1] = replace(bindings[1], curriculum_stable_key="not_authorized")
    elif conflict == "duplicate":
        bindings[1] = bindings[0]
    with pytest.raises(ValidationAppError):
        compile_curriculum(curriculum, **kw, public_knowledge_bindings=tuple(bindings))


def test_title_similarity_and_material_source_do_not_merge_knowledge():
    curriculum, kw = two_knowledge_nodes(different_title=True)
    result = compile_curriculum(curriculum, **kw).to_payload()
    assert [n["identity_kind"] for n in result["nodes"]] == ["curriculum_candidate", "curriculum_candidate"]
    assert len({n["stable_key"] for n in result["nodes"]}) == 2
    assert all("public_binding" not in n for n in result["nodes"])


@pytest.mark.parametrize("constraint,allowed", [("只使用免费教材", True), ("只读，不允许代码修改", False),
    ("禁止联网", False), ("只使用中文教材", False)])
def test_free_proofs_are_used_but_other_pending_constraints_are_not_waived(constraint, allowed):
    curriculum, kw = inputs(constraints=(constraint,))
    if allowed:
        raw = output(kw["context"])
        raw["status"] = "complete"
        curriculum = validate_curriculum_output(raw, kw["context"].to_payload())
        result = compile_curriculum(curriculum, **kw)
        assert result.to_payload()["constraints"]["assessments"][0]["status"] == "satisfied"
    else:
        with pytest.raises(ValidationAppError) as error:
            compile_curriculum(curriculum, **kw)
        assert error.value.details["diagnostics"]["constraint_assessments"][0]["status"] == "pending"


@pytest.mark.parametrize("field", ["source_profile_hash", "source_capability_plan_hash", "source_coverage_result_hash", "source_gap_set_hash"])
def test_context_research_binding_cannot_be_rehashed_away(field):
    curriculum, kw = inputs()
    kw["context"] = replace(kw["context"], research=replace(kw["context"].research, **{field: "e" * 64}))
    with pytest.raises(ValidationAppError):
        compile_curriculum(curriculum, **kw)


def test_context_research_requirement_must_match_frozen_profile():
    curriculum, kw = inputs()
    research = kw["context"].research
    first = research.entries[0]
    research = replace(research, entries=(replace(first, requirement=replace(first.requirement, starting_point="forged")),))
    kw["context"] = replace(kw["context"], research=research)
    with pytest.raises(ValidationAppError):
        compile_curriculum(curriculum, **kw)


@pytest.mark.parametrize("field", ["accepted_known", "profile_context", "capabilities"])
def test_context_profile_and_capabilities_cannot_be_rehashed_away(field):
    curriculum, kw = inputs()
    ctx = kw["context"].to_payload()
    if field == "accepted_known":
        ctx[field] = ["python.core"]
    elif field == "profile_context":
        ctx[field]["starting_point"] = "forged"
    else:
        ctx[field][0]["outcomes"][0]["text"] = "forged"
    ctx["input_hash"] = content_hash({k: v for k, v in ctx.items() if k != "input_hash"})
    kw["context"] = replace(kw["context"], _json=canonical_json(ctx))
    with pytest.raises(ValidationAppError):
        compile_curriculum(curriculum, **kw)


def test_approved_unknown_domain_compiles_but_missing_approval_and_fixture_cannot():
    from backend.tests.unit.test_domain_verification import researched_domain

    p, frozen, approval, index, coverage, _, research, *_ = researched_domain()
    ctx = prepare_curriculum(p, frozen, coverage, research, index, domain_approvals=(approval,))
    curriculum = validate_curriculum_output(output(ctx), ctx.to_payload(), domain_approvals=(approval,))
    facts = CurriculumSourceFacts(index)
    assert compile_curriculum(curriculum, context=ctx, profile=p, capability_plan=frozen, source_facts=facts).to_payload()["stages"][0]["capability_ids"] == ["ros2.action"]
    with pytest.raises(ValidationAppError):
        compile_curriculum(curriculum, context=replace(ctx, _domain_approvals=()), profile=p, capability_plan=frozen, source_facts=facts)
    p, frozen, _, index, coverage, _, research, *_ = researched_domain(fixture=True)
    ctx = prepare_curriculum(p, frozen, coverage, research, index, allow_fixture_domains=True)
    curriculum = validate_curriculum_output(output(ctx), ctx.to_payload(), allow_fixture_domains=True)
    with pytest.raises(ValidationAppError):
        compile_curriculum(curriculum, context=ctx, profile=p, capability_plan=frozen, source_facts=CurriculumSourceFacts(index))


def test_illegal_prerequisite_and_stage_order_are_rejected():
    curriculum, kw = inputs(systematic=True)
    raw = output(kw["context"])
    raw["stages"][0]["prerequisite_stage_refs"] = [raw["stages"][1]["stage_id"]]
    with pytest.raises(ValidationAppError):
        compile_curriculum(forged(curriculum, lambda d: d.__setitem__("stages", raw["stages"])), **kw)
    raw = output(kw["context"])
    raw["stages"].reverse()
    for index, stage in enumerate(raw["stages"]):
        stage["order_index"] = index
    with pytest.raises(ValidationAppError):
        compile_curriculum(forged(curriculum, lambda d: d.__setitem__("stages", raw["stages"])), **kw)


def test_guidance_above_legacy_limits_is_exact_and_manifest_has_no_runtime_placeholders():
    curriculum, kw = inputs()
    raw = output(kw["context"])
    raw["stages"][0]["guidance"]["practice_delta"]["increment"] = "完整内容" * 400
    curriculum = validate_curriculum_output(raw, kw["context"].to_payload())
    result = compile_curriculum(curriculum, **kw)
    assert result.to_payload()["guidance"][0]["practice_delta"]["increment"] == ["完整内容" * 400]
    assert set(result.manifest.to_payload()) == {"compiler_version", "contract_version", "input_curriculum_plan_hash",
        "upstream_sources", "compiled_payload_digest", "stable_identity_mapping", "validation"}


def test_research_outcome_text_not_authorized_even_with_recomputed_envelopes():
    curriculum, kw = inputs()
    research = kw["context"].research
    first = research.entries[0]
    outcomes = list(first.requirement.must_teach)
    outcomes[0] = replace(outcomes[0], text="Changed research teaching authority")
    research = replace(research, entries=(replace(first, requirement=replace(first.requirement, must_teach=tuple(outcomes))),))
    ctx = kw["context"].to_payload()
    ctx["sources"]["research_hash"] = research.result_hash
    ctx["input_hash"] = content_hash({k: v for k, v in ctx.items() if k != "input_hash"})
    context = replace(kw["context"], _json=canonical_json(ctx), research=research)
    raw = output(context)
    curriculum = validate_curriculum_output(raw, ctx)
    with pytest.raises(ValidationAppError) as error:
        compile_curriculum(curriculum, **(kw | {"context": context}))
    assert error.value.details["field"] == "research_requirement_binding"


def test_research_unresolved_cannot_be_removed_from_context_by_rehashing():
    curriculum, kw = inputs()
    context = prepared(kw["profile"], kw["capability_plan"], unresolved=True)
    ctx = context.to_payload()
    ctx["capabilities"][0]["unavailable_outcomes"] = []
    ctx["input_hash"] = content_hash({k: v for k, v in ctx.items() if k != "input_hash"})
    context = replace(context, _json=canonical_json(ctx))
    with pytest.raises(ValidationAppError) as error:
        compile_curriculum(curriculum, **(kw | {"context": context}))
    assert error.value.details["field"] == "context_capability_binding"


def test_stage_semantic_keys_are_legal_and_manifest_mapping_matches_blueprints():
    import re

    curriculum, kw = inputs(systematic=True)
    result = compile_curriculum(curriculum, **kw)
    stages = result.to_payload()["stages"]
    mappings = result.manifest.to_payload()["stable_identity_mapping"]["stages"]
    assert [s["stable_key"] for s in stages] == [m["semantic_key"] for m in mappings]
    assert all(re.fullmatch(r"[a-z][a-z0-9_.-]{0,127}", s["stable_key"]) for s in stages)
    assert [s["order_index"] for s in stages] == [0, 1, 2]


def test_json_object_member_order_does_not_change_compilation():
    curriculum, kw = inputs()
    original = json.loads(curriculum._json)
    reversed_members = dict(reversed(list(original.items())))
    reordered = CurriculumPlan(json.dumps(reversed_members, ensure_ascii=False), curriculum._findings)
    assert compile_curriculum(reordered, **kw).digest == compile_curriculum(curriculum, **kw).digest


@pytest.mark.parametrize("change", ["qualification", "evidence", "url", "version"])
def test_research_material_forgery_with_coherent_context_hashes_is_rejected(change):
    _, kw = inputs()
    ctx = kw["context"].to_payload()
    material = ctx["materials"][0]
    if change == "qualification":
        material["qualification"] = "public_reviewed"
    elif change == "evidence":
        material["evidence_refs"][0]["reference"] += "forged"
    elif change == "url":
        material["url"] = "https://example.com/forged"
    else:
        material["source_version"] = "forged-v2"
    material["material_id"] = "material_" + content_hash({k: v for k, v in material.items() if k != "material_id"})
    ctx["input_hash"] = content_hash({k: v for k, v in ctx.items() if k != "input_hash"})
    context = replace(kw["context"], _json=canonical_json(ctx))
    curriculum = validate_curriculum_output(output(context), ctx)
    with pytest.raises(ValidationAppError):
        compile_curriculum(curriculum, **(kw | {"context": context}))


def test_approved_unknown_accepted_known_does_not_require_reader_publication():
    from app.application.domain_verification import DomainVerifier
    from app.domain.planning.capabilities import CapabilityPlanValidator
    from app.domain.planning.domain_verification import bind_domain_approval

    from backend.tests.unit.test_domain_verification import pinned_reader, source, verification_session
    from backend.tests.unit.test_resource_research import SCOPE

    p = profile("已会ROS2，学习MCP", claims=("会ROS2 Action",))
    s = source(public=False)
    reader, _ = pinned_reader()
    result = DomainVerifier(reader, sources=(s,)).verify(p, source_id=s.source_id,
        session=verification_session(p, s), scope=SCOPE, project_id="project")
    claim = p.learner_claims[0].claim_id
    frozen = CapabilityPlanValidator().validate(wire(p,
        cap(p, "ros2.action", disposition="accepted_known", learner_claim_refs=[claim]), cap(p, "mcp"),
        claim_bindings=[{"claim_ref": claim, "capability_id": "ros2.action"}]),
        profile=p, verification_evidence=(result.evidence,))
    approval = bind_domain_approval(result.approval, frozen)
    ctx = prepared(p, frozen)
    ctx = replace(ctx, _domain_approvals=(approval,))
    curriculum = validate_curriculum_output(output(ctx), ctx.to_payload(), domain_approvals=(approval,))
    assert ctx.to_payload().get("domain_authority") is None
    result = compile_curriculum(curriculum, context=ctx, profile=p, capability_plan=frozen,
        source_facts=CurriculumSourceFacts(ReviewedContentIndex("empty", (), (), ())))
    assert [c for stage in result.to_payload()["stages"] for c in stage["capability_ids"]] == ["mcp"]
    with pytest.raises(ValidationAppError):
        compile_curriculum(curriculum, context=replace(ctx, _domain_approvals=()), profile=p, capability_plan=frozen,
            source_facts=CurriculumSourceFacts(ReviewedContentIndex("empty", (), (), ())))


@pytest.mark.parametrize("change", ["qualification", "evidence", "url", "version", "access_proof"])
def test_covered_material_forgery_with_coherent_context_hashes_is_rejected(change):
    p, frozen, index, source, proof = local_mcp_inputs()
    context = prepared(p, frozen, index, catalog_sources=(source,), access_proofs=(proof,))
    ctx = context.to_payload()
    material = next(m for m in ctx["materials"] if m["kind"] == "covered_content")
    if change == "qualification":
        material["qualification"] = "research_checked"
    elif change == "evidence":
        material["evidence_refs"][0]["sha256"] = "a" * 64
    elif change == "url":
        material["url"] = "https://example.com/forged"
    elif change == "version":
        material["source_version"] = "source:999"
        material["access_proof"]["source_version"] = 999
    else:
        material["access_proof"]["reference"] = "fixture:forged-free-access-proof"
    material["material_id"] = "material_" + content_hash({k: v for k, v in material.items() if k != "material_id"})
    ctx["input_hash"] = content_hash({k: v for k, v in ctx.items() if k != "input_hash"})
    context = replace(context, _json=canonical_json(ctx))
    curriculum = validate_curriculum_output(output(context), ctx)
    with pytest.raises(ValidationAppError) as error:
        compile_curriculum(curriculum, context=context, profile=p, capability_plan=frozen,
            source_facts=CurriculumSourceFacts(index, (source,), (proof,)))
    assert error.value.details["field"] == "source_context_projection_binding"


def test_missing_covered_source_facts_cannot_lend_existing_context_qualification():
    p, frozen, index, source, proof = local_mcp_inputs()
    ctx = prepared(p, frozen, index, catalog_sources=(source,), access_proofs=(proof,))
    curriculum = validate_curriculum_output(output(ctx), ctx.to_payload())
    with pytest.raises(ValidationAppError):
        compile_curriculum(curriculum, context=ctx, profile=p, capability_plan=frozen,
            source_facts=CurriculumSourceFacts(index))
