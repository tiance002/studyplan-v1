"""Synthetic curriculum wire fixtures; real teaching semantics are not asserted."""
import json
from copy import deepcopy
from dataclasses import replace

import pytest
from app.core.errors import ValidationAppError
from app.core.ids import canonical_json, content_hash
from app.domain.planning.content_coverage import CoverageEvaluator, ReviewedContentIndex
from app.domain.planning.curriculum import (
    CURRICULUM_SCHEMA,
    CaseFinding,
    ProjectCase,
    prepare_curriculum,
    record_case_findings,
    valid_curriculum_input,
    validate_curriculum_output,
)

from backend.tests.unit.test_capability_planning import cap, plan, profile, wire
from backend.tests.unit.test_resource_research import run


def context(*, project_context=None, constraints=(), project_usage="required"):
    p = replace(profile("学习MCP", constraints=constraints), project_context=project_context)
    frozen = plan(p, wire(p, cap(p, "mcp", project_usage=project_usage)))
    index = ReviewedContentIndex("empty", (), (), ())
    coverage = CoverageEvaluator().evaluate(frozen, index)
    from app.domain.planning.resource_gaps import extract
    research, *_ = run((p, frozen, coverage, extract(frozen, coverage)))
    return prepare_curriculum(p, frozen, coverage, research, index)


def output(ctx=None, *, project_study=False):
    ctx = ctx or context()
    payload = ctx.to_payload()
    stages = []
    carrier_outcomes = []
    for i, capability in enumerate(payload["capabilities"]):
        key = capability["capability_id"].replace(".", "_")
        outcomes = [outcome["outcome_id"] for outcome in capability["outcomes"]]
        materials = [material for material in payload["materials"] if set(outcomes) & set(material["outcome_refs"]) and material["usable"]]
        refs = [material["material_id"] for material in materials]
        knowledge = "knowledge_" + key
        if capability["project_usage"] != "excluded":
            carrier_outcomes.extend(outcomes)
        stages.append({"stage_id": "stage_" + key, "title": capability["title"], "role": "specialization", "order_index": i,
            "why_now": "缺失能力需要有界教学", "what_to_learn": "解释并实践获准outcomes", "capability_ids": [capability["capability_id"]],
            "outcome_refs": outcomes, "prerequisite_stage_refs": ["stage_" + p.replace(".", "_") for p in capability["prerequisites"]
                if p not in payload["accepted_known"]],
            "knowledge": [{"stable_key": knowledge, "title": capability["title"], "objectives": ["解释获准能力"],
                "outcome_refs": outcomes, "material_refs": refs}],
            "units": [{"stable_key": "unit_" + key, "title": "有界教学单元", "objectives": ["完成教学与实践"], "outcome_refs": outcomes,
                "knowledge_refs": [knowledge], "rubric": [{"text": "可检查解释与示例", "outcome_refs": outcomes}]}],
            "assignments": [{"material_id": material["material_id"], "role": "PRIMARY" if j == 0 else "SUPPLEMENT",
                "outcome_refs": sorted(set(outcomes) & set(material["outcome_refs"])), "reading_focus": "只读对应教学章节"}
                for j, material in enumerate(materials)],
            "guidance": {"previous_relation": "基于已冻结学习起点", "learning_focus": ["精确目标"], "comparison_focus": [],
                "practice_delta": {"baseline": "当前可检查起点", "increment": "本阶段增量", "preserved": "既有行为",
                    "validation": "正常与失败检查", "reuse": "按获准项目范围迁回"}},
            "tasks": [{"stable_key": "task_" + key, "title": "有界练习", "goal": "实际产生检查证据", "in_scope": ["获准能力"],
                "out_scope": ["整仓库重构"], "outcome_refs": outcomes, "knowledge_refs": [knowledge],
                "practice_kind": "micro_exercise" if capability["project_usage"] == "excluded" else "carrier",
                "acceptance": [{"text": "正常与失败行为都有证据", "outcome_refs": outcomes}]}], "project_study_refs": []})
    projects = []
    if project_study:
        outcomes = stages[0]["outcome_refs"]
        projects = [{"requirement_id": "study_main", "problem": "调查一条真实源码请求与失败处理切片", "mode": "slices",
            "outcome_refs": outcomes, "avoid_scope": ["全仓库导览"], "expected_outputs": ["输入输出图和证据定位"],
            "normal_behavior": ["有效输入到输出"], "failure_behavior": ["非法输入明确拒绝"],
            "inputs_outputs": [{"input": "有效或非法请求", "output": "结果或明确错误"}],
            "design_questions": ["权限和失败边界在哪里？"], "selected_case_ref": None}]
        stages[0]["project_study_refs"] = ["study_main"]
    unavailable = [outcome for c in payload["capabilities"] for outcome in c["unavailable_outcomes"]]
    raw = {"schema_version": 1, "input_hash": ctx.input_hash,
        "status": "incomplete" if projects or unavailable or payload["constraints"] else "complete", "stages": stages,
        "carrier": {"kind": "user_project" if payload["profile_context"]["project_context"] else "starter",
            "project_context_hash": payload["profile_context"]["project_context_hash"], "reason": "保留既有项目作为持续实践载体",
            "description": payload["profile_context"]["project_context"] or "最小可维护学习项目",
            "final_artifact": {"description": "可检查学习成果", "acceptance": [{"text": "产出正常与失败证据", "outcome_refs": carrier_outcomes}]}},
        "project_study_requirements": projects,
        "unresolved": [{"outcome_ref": ref, "reason": "source_unavailable"} for ref in unavailable],
        "constraint_refs": [c["constraint_id"] for c in payload["constraints"]], "source_limitations": []}
    # A wire document has no shared Python list aliases between independent fields.
    return json.loads(canonical_json(raw))


def test_valid_complete_fixture_is_frozen_and_deterministic():
    ctx = context()
    assert valid_curriculum_input(ctx.to_payload(), CURRICULUM_SCHEMA)
    first = validate_curriculum_output(output(ctx), ctx.to_payload())
    assert first.status == "complete" and first.input_hash == ctx.input_hash
    assert first.plan_hash == validate_curriculum_output(output(ctx), ctx.to_payload()).plan_hash
    isolated = first.to_payload()
    isolated["stages"].clear()
    assert first.to_payload()["stages"]


def test_unfilled_case_and_candidate_findings_preserve_incomplete_curriculum():
    ctx = context()
    curriculum = validate_curriculum_output(output(ctx, project_study=True), ctx.to_payload())
    requirement = curriculum.project_study_requirements[0]
    candidate = ProjectCase("case_fixture", "https://github.com/demo/tutorial", "unknown", "slices",
                            tuple(requirement["outcome_refs"]), limitations=("Metadata only",))
    updated = record_case_findings(curriculum, (CaseFinding(requirement["requirement_id"], requirement["requirement_hash"],
        (candidate,), ("candidate_only",)),))
    assert updated.status == "incomplete" and updated.to_payload()["stages"] == curriculum.to_payload()["stages"]
    assert updated.to_payload()["case_findings"] and curriculum.to_payload()["case_findings"] == []


@pytest.mark.parametrize("tamper", ["A", "capability", "outcome", "material", "primary", "dependency", "unit_link",
    "task_acceptance", "unit_empty", "guidance", "role", "mode", "input_hash", "unresolved", "source_override"])
def test_invalid_curriculum_matrix_rejected(tamper):
    ctx = context()
    raw = output(ctx, project_study=tamper == "mode")
    stage = raw["stages"][0]
    if tamper in {"A", "capability"}:
        stage["capability_ids"] = ["python.core" if tamper == "A" else "kubernetes"]
    elif tamper == "outcome":
        stage["outcome_refs"].append("invented.outcome")
    elif tamper == "material":
        stage["assignments"][0]["material_id"] = "material_forged"
    elif tamper == "primary":
        stage["assignments"].append(deepcopy(stage["assignments"][0]))
    elif tamper == "dependency":
        stage["prerequisite_stage_refs"] = [stage["stage_id"]]
    elif tamper == "unit_link":
        stage["units"][0]["knowledge_refs"] = ["knowledge_unknown"]
    elif tamper == "task_acceptance":
        stage["tasks"][0]["acceptance"][0]["outcome_refs"] = ["python.core.program_structure"]
    elif tamper == "unit_empty":
        stage["units"] = []
    elif tamper == "guidance":
        del stage["guidance"]["practice_delta"]["increment"]
    elif tamper == "role":
        stage["role"] = "interview"
    elif tamper == "mode":
        raw["project_study_requirements"][0]["mode"] = "full_repo_clone"
    elif tamper == "input_hash":
        raw["input_hash"] = "f" * 64
    elif tamper == "unresolved":
        raw["unresolved"] = [{"outcome_ref": "not.authorized", "reason": "missing"}]
    else:
        stage["assignments"][0]["version"] = "forged"
    with pytest.raises(ValidationAppError):
        validate_curriculum_output(raw, ctx.to_payload())


def prepared(p, frozen, index=None, *, catalog_sources=(), access_proofs=(), project_cases=(), unresolved=False):
    from app.domain.planning.resource_gaps import extract
    from app.domain.planning.resource_research import ResearchBudget
    index = index or ReviewedContentIndex("empty", (), (), ())
    coverage = CoverageEvaluator().evaluate(frozen, index)
    research, *_ = run((p, frozen, coverage, extract(frozen, coverage)),
                       budget=ResearchBudget(max_searches=0) if unresolved else None)
    return prepare_curriculum(p, frozen, coverage, research, index, catalog_sources=catalog_sources,
                              access_proofs=access_proofs, project_cases=project_cases)


def test_accepted_python_satisfies_cli_prerequisite_without_extra_courses():
    from backend.tests.unit.test_capability_planning import known_python
    p = profile("会Python，学习JSON CLI", claims=("会Python",))
    frozen = plan(p, wire(p, known_python(p), cap(p, "json.cli"), claim_bindings=[
        {"claim_ref": p.learner_claims[0].claim_id, "capability_id": "python.core"}]))
    ctx = prepared(p, frozen)
    result = validate_curriculum_output(output(ctx), ctx.to_payload())
    assert ctx.to_payload()["accepted_known"] == ["python.core"]
    assert [c for s in result.to_payload()["stages"] for c in s["capability_ids"]] == ["json.cli"]
    assert "mcp" not in repr(result.to_payload())


def test_systematic_agent_has_only_frozen_common_core_and_mcp():
    p = profile("系统学习Agent")
    frozen = plan(p, wire(p, cap(p, "llm.api"), cap(p, "mcp"), route_kind="systematic_agent_route"))
    ctx = prepared(p, frozen)
    raw = output(ctx)
    raw["stages"][0]["role"] = "common_core"
    result = validate_curriculum_output(raw, ctx.to_payload())
    assert {c for s in result.to_payload()["stages"] for c in s["capability_ids"]} == {"llm.api", "mcp"}
    assert len(result.to_payload()["stages"]) == 2


def test_unresolved_required_cannot_become_complete_or_invent_primary():
    p = profile("学习MCP")
    ctx = prepared(p, plan(p, wire(p, cap(p, "mcp"))), unresolved=True)
    raw = output(ctx)
    assert validate_curriculum_output(raw, ctx.to_payload()).status == "incomplete"
    raw["status"], raw["unresolved"] = "complete", []
    with pytest.raises(ValidationAppError):
        validate_curriculum_output(raw, ctx.to_payload())


def test_true_prerequisite_cannot_be_reversed_or_omitted():
    p = profile("学习工具调用")
    ctx = prepared(p, plan(p, wire(p, cap(p, "llm.api"), cap(p, "tool.calling"))))
    raw = output(ctx)
    validate_curriculum_output(raw, ctx.to_payload())
    raw["stages"][1]["prerequisite_stage_refs"] = []
    with pytest.raises(ValidationAppError):
        validate_curriculum_output(raw, ctx.to_payload())


def test_user_project_micro_exercise_and_hard_constraint_boundary():
    ctx = context(project_context="已有旅行Agent，保留现有接口", project_usage="excluded")
    raw = output(ctx)
    result = validate_curriculum_output(raw, ctx.to_payload())
    assert result.to_payload()["carrier"]["kind"] == "user_project"
    assert raw["stages"][0]["tasks"][0]["practice_kind"] == "micro_exercise"
    raw["stages"][0]["tasks"][0]["practice_kind"] = "carrier"
    with pytest.raises(ValidationAppError):
        validate_curriculum_output(raw, ctx.to_payload())
    constrained = context(constraints=("不向外部服务发送用户数据",))
    raw = output(constrained)
    assert validate_curriculum_output(raw, constrained.to_payload()).status == "incomplete"
    raw["status"] = "complete"
    with pytest.raises(ValidationAppError):
        validate_curriculum_output(raw, constrained.to_payload())


@pytest.mark.parametrize("mode", ["whole_core", "slices"])
def test_project_modes_require_real_qualified_case_not_readme_metadata(mode):
    base = context()
    refs = tuple(o["outcome_id"] for o in base.to_payload()["capabilities"][0]["outcomes"])
    case = ProjectCase("case_fixture", "https://github.com/demo/tutorial", "fixture-behavior-v1", mode, refs,
        (("fixture:bounded-behavior-evidence", content_hash({"synthetic": True})),), "bounded_reviewed", ("Synthetic case",))
    p = profile("学习MCP")
    ctx = prepared(p, plan(p, wire(p, cap(p, "mcp"))), project_cases=(case,))
    raw = output(ctx, project_study=True)
    raw["project_study_requirements"][0].update(mode=mode, selected_case_ref=case.case_id)
    raw["status"] = "complete"
    assert validate_curriculum_output(raw, ctx.to_payload()).status == "complete"
    bad = replace(case, qualification="reviewed_candidate")
    ctx = prepared(p, plan(p, wire(p, cap(p, "mcp"))), project_cases=(bad,))
    raw["input_hash"] = ctx.input_hash
    with pytest.raises(ValidationAppError):
        validate_curriculum_output(raw, ctx.to_payload())


def test_verified_unknown_coding_and_rag_can_combine_without_policy_rewrite_or_public_query():
    from app.domain.planning.capability_policy import CapabilityDefinition, LearningOutcome

    from backend.tests.unit.test_capability_planning import evidence
    p = profile("组合Coding与RAG目标")
    ev = replace(evidence(p), capabilities=(
        CapabilityDefinition("coding.review", "Coding审查切片", (LearningOutcome("coding.review.finding", "定位一个真实缺陷并解释证据"),), (), "applied", ()),
        CapabilityDefinition("rag.retrieval", "RAG检索切片", (LearningOutcome("rag.retrieval.result", "比较检索结果并解释来源"),), (), "applied", ())))
    frozen = plan(p, wire(p, cap(p, "coding.review"), cap(p, "rag.retrieval")), verification_evidence=(ev,))
    ctx = prepared(p, frozen)
    result = validate_curriculum_output(output(ctx), ctx.to_payload())
    assert {c for s in result.to_payload()["stages"] for c in s["capability_ids"]} == {"coding.review", "rag.retrieval"}
    assert result.status == "incomplete"
    assert "rag.retrieval.result" not in ctx.public_outcome_texts


@pytest.mark.parametrize("field", ["source_gap_set_hash", "source_capability_plan_hash", "source_coverage_result_hash", "source_profile_hash"])
def test_prepare_rejects_research_source_hash_mismatch(field):
    from app.domain.planning.resource_gaps import extract
    p = profile("学习MCP")
    frozen = plan(p, wire(p, cap(p, "mcp")))
    index = ReviewedContentIndex("empty", (), (), ())
    coverage = CoverageEvaluator().evaluate(frozen, index)
    research, *_ = run((p, frozen, coverage, extract(frozen, coverage)))
    with pytest.raises(ValidationAppError):
        prepare_curriculum(p, frozen, coverage, replace(research, **{field: "f" * 64}), index)


def test_raw_goal_and_source_body_are_not_valid_frozen_input():
    ctx = context()
    payload = ctx.to_payload() | {"raw_goal": "private", "body": "full tutorial"}
    assert not valid_curriculum_input(payload, CURRICULUM_SCHEMA)


def test_interview_changes_artifact_acceptance_without_interview_stage():
    p = replace(profile("学习MCP用于面试"), outcome_purpose="interview")
    ctx = prepared(p, plan(p, wire(p, cap(p, "mcp"))))
    raw = output(ctx)
    raw["carrier"]["final_artifact"]["acceptance"][0]["text"] = "解释核心调用与设计取舍，比较替代方案并分析真实失败"
    result = validate_curriculum_output(raw, ctx.to_payload())
    assert {s["role"] for s in result.to_payload()["stages"]} == {"specialization"}


def local_mcp_inputs():
    """Actual pinned review/pack facts, with synthetic Item5 evidence for the missing outcome."""
    import hashlib
    import json
    from pathlib import Path

    from app.domain.planning.resource_research import ReviewedAccessProof
    from app.domain.resources.curation import PublicResourceSource
    from app.infrastructure.reviewed_content_coverage import load_reviewed_content_index
    index = load_reviewed_content_index()
    path = Path(__file__).parents[2] / "app/infrastructure/content/agent-application-v8.json"
    pack_bytes = path.read_bytes()
    record = json.loads(pack_bytes.decode("utf-8-sig"))["resources"][13]
    assert record["content_access"] == "free_public"
    source = PublicResourceSource(record["source_id"], record["canonical_url"], record["title"], record["creator"],
        record["media_type"], record["language"], source_version=record["source_version"])
    section = index.sections[0]
    pack_hash = hashlib.sha256(pack_bytes).hexdigest()
    assert pack_hash == section.content_hash
    proof = ReviewedAccessProof(section.source_id, section.source_version, section.content_hash,
        "repo:backend/app/infrastructure/content/agent-application-v8.json@sha256:" + pack_hash
        + "#/resources/13/content_access", "free_public")
    p = profile("学习MCP")
    frozen = plan(p, wire(p, cap(p, "mcp")))
    return p, frozen, index, source, proof


def test_actual_local_review_and_synthetic_research_both_consumed_with_compile_snapshot():
    p, frozen, index, source, proof = local_mcp_inputs()
    ctx = prepared(p, frozen, index, catalog_sources=(source,), access_proofs=(proof,))
    assert valid_curriculum_input(ctx.to_payload(), CURRICULUM_SCHEMA)
    result = validate_curriculum_output(output(ctx), ctx.to_payload())
    doc = result.to_payload()
    materials = doc["compile_materials"]
    assert {m["kind"] for m in materials} == {"covered_content", "researched_resource"}
    assert {m["qualification"] for m in materials} == {"public_reviewed", "research_checked"}
    covered = next(m for m in materials if m["kind"] == "covered_content")
    assert covered["url"] == source.canonical_url and covered["source_version"] == "source:2"
    assert covered["section_refs"] == [index.sections[0].section_id]
    assert covered["access_proof"]["reference"] == proof.reference
    assert covered["content_hash"] == index.sections[0].content_hash
    assert all(ref["hash_scope"] == "review_record" for ref in covered["evidence_refs"])
    assert doc["compile_sources"] == ctx.to_payload()["sources"]
    assert doc["compile_context"]["accepted_known"] == []
    assert result.status == "complete"


def test_reviewed_content_does_not_imply_free_access_and_conflicting_proof_rejected():
    p, frozen, index, source, proof = local_mcp_inputs()
    ctx = prepared(p, frozen, index, catalog_sources=(source,))
    assert set(ctx.to_payload()["capabilities"][0]["unavailable_outcomes"]) == {"mcp.roles", "mcp.interfaces"}
    doc = validate_curriculum_output(output(ctx), ctx.to_payload()).to_payload()
    assert doc["status"] == "incomplete"
    assert all(m["kind"] != "covered_content" for m in doc["compile_materials"])
    with pytest.raises(ValidationAppError):
        prepared(p, frozen, index, catalog_sources=(source,), access_proofs=(proof, replace(proof, access="paid")))


def test_same_resource_identity_cannot_lend_access_or_review_to_another_capability():
    from app.domain.planning.resource_gaps import extract
    p = profile("学习LLM与MCP")
    frozen = plan(p, wire(p, cap(p, "llm.api"), cap(p, "mcp")))
    index = ReviewedContentIndex("empty", (), (), ())
    coverage = CoverageEvaluator().evaluate(frozen, index)
    research, *_ = run((p, frozen, coverage, extract(frozen, coverage)))
    first, second = research.entries
    prototype = first.resources[0]
    unsupported = replace(prototype, qualification="candidate", free_access="unknown", evidence=tuple(
        replace(prototype.evidence[0], outcome_id=o.outcome_id) for o in second.requirement.must_teach))
    second = replace(second, resources=(unsupported,),
        status="unresolved", unresolved_outcomes=second.requirement.must_teach, reason_codes=("candidate_only",))
    assert first.resources[0].resource_id == second.resources[0].resource_id
    research = replace(research, entries=(first, second))
    ctx = prepare_curriculum(p, frozen, coverage, research, index)
    materials = ctx.to_payload()["materials"]
    assert len(materials) == 2 and sum(m["usable"] for m in materials) == 1
    unsafe = next(m for m in materials if not m["usable"])
    assert unsafe["qualification"] == "candidate" and unsafe["free_access"] == "unknown"
    capability = next(c for c in ctx.to_payload()["capabilities"] if c["capability_id"] == second.requirement.capability_id)
    assert set(capability["unavailable_outcomes"]) == {o.outcome_id for o in second.requirement.must_teach}
    assert validate_curriculum_output(output(ctx), ctx.to_payload()).status == "incomplete"


def test_policy_only_capability_refs_can_be_empty_and_foundation_is_preserved():
    p = profile("系统学习Agent")
    mcp = cap(p, "mcp", desired_depth="foundation")
    mcp["requirement_refs"] = []
    frozen = plan(p, wire(p, cap(p, "llm.api"), mcp, route_kind="systematic_agent_route"))
    ctx = prepared(p, frozen)
    assert valid_curriculum_input(ctx.to_payload(), CURRICULUM_SCHEMA)
    assert next(c for c in ctx.to_payload()["capabilities"] if c["capability_id"] == "mcp")["requirement_refs"] == []
    assert next(c for c in ctx.to_payload()["capabilities"] if c["capability_id"] == "mcp")["desired_depth"] == "foundation"
    validate_curriculum_output(output(ctx), ctx.to_payload())


def rehash(payload):
    payload["input_hash"] = content_hash({k: v for k, v in payload.items() if k != "input_hash"})
    return payload


@pytest.mark.parametrize("change", ["cycle", "depth", "material_access", "material_id", "material_extra", "source_hash", "budget", "schema"])
def test_preflight_rejects_bad_inner_input_even_with_recomputed_outer_digest(change):
    p = profile("学习工具调用")
    ctx = prepared(p, plan(p, wire(p, cap(p, "llm.api"), cap(p, "tool.calling"))))
    payload = ctx.to_payload()
    if change == "cycle":
        payload["capabilities"][0]["prerequisites"] = [payload["capabilities"][1]["capability_id"]]
    elif change == "depth":
        payload["capabilities"][0]["desired_depth"] = "invented"
    elif change == "material_access":
        payload["materials"][0]["free_access"] = "unknown"
        material = payload["materials"][0]
        material["material_id"] = "material_" + content_hash({k: v for k, v in material.items() if k != "material_id"})
    elif change == "material_id":
        payload["materials"][0]["material_id"] = "material_forged"
    elif change == "material_extra":
        payload["materials"][0]["text"] = "Full tutorial forbidden"
    elif change == "source_hash":
        payload["sources"]["research_hash"] = "not_sha256"
    elif change == "budget":
        payload["sources"]["research_budget_usage"]["total_requests"] = True
    else:
        payload["schema_version"] = True
    assert not valid_curriculum_input(rehash(payload), CURRICULUM_SCHEMA)


def test_real_prerequisites_can_be_ordered_units_within_one_stage():
    p = profile("学习工具调用")
    ctx = prepared(p, plan(p, wire(p, cap(p, "llm.api"), cap(p, "tool.calling"))))
    raw = output(ctx)
    first, second = raw["stages"]
    for name in ("capability_ids", "outcome_refs", "knowledge", "units", "tasks"):
        first[name].extend(second[name])
    first["assignments"].extend(a | {"role": "SUPPLEMENT"} for a in second["assignments"])
    raw["stages"] = [first]
    validate_curriculum_output(raw, ctx.to_payload())
    first["units"].reverse()
    with pytest.raises(ValidationAppError):
        validate_curriculum_output(raw, ctx.to_payload())


def test_missing_required_teaching_and_invented_dependencies_are_rejected():
    ctx = context()
    raw = output(ctx)
    raw["stages"] = []
    with pytest.raises(ValidationAppError):
        validate_curriculum_output(raw, ctx.to_payload())
    p = profile("学习LLM与MCP")
    ctx = prepared(p, plan(p, wire(p, cap(p, "llm.api"), cap(p, "mcp"))))
    raw = output(ctx)
    raw["stages"][1]["prerequisite_stage_refs"] = [raw["stages"][0]["stage_id"]]
    with pytest.raises(ValidationAppError):
        validate_curriculum_output(raw, ctx.to_payload())


def test_compile_metadata_is_server_owned_and_original_user_project_survives():
    ctx = context(project_context="原项目事实必须保留")
    raw = output(ctx)
    raw["carrier"]["description"] = "适配后的持续实践说明"
    result = validate_curriculum_output(raw, ctx.to_payload())
    assert result.to_payload()["compile_context"]["profile_context"]["project_context"] == "原项目事实必须保留"
    raw["compile_materials"] = []
    with pytest.raises(ValidationAppError):
        validate_curriculum_output(raw, ctx.to_payload())


@pytest.mark.parametrize("change", ["binding", "promotion", "mode", "outcome"])
def test_case_findings_cannot_rewrite_or_promote_frozen_curriculum(change):
    ctx = context()
    result = validate_curriculum_output(output(ctx, project_study=True), ctx.to_payload())
    req = result.project_study_requirements[0]
    candidate = ProjectCase("case_fixture", "https://github.com/demo/tutorial", "candidate-v1", "slices", tuple(req["outcome_refs"]))
    digest = req["requirement_hash"]
    if change == "binding":
        digest = "f" * 64
    elif change == "promotion":
        candidate = replace(candidate, qualification="bounded_reviewed", evidence_refs=(("fixture:proof", "a" * 64),))
    elif change == "mode":
        candidate = replace(candidate, mode="whole_core")
    else:
        candidate = replace(candidate, outcome_refs=("python.core.program_structure",))
    with pytest.raises(ValidationAppError):
        record_case_findings(result, (CaseFinding(req["requirement_id"], digest, (candidate,), ("candidate_only",)),))


def test_reference_order_is_canonical_but_unit_teaching_order_is_retained():
    ctx = context()
    raw = output(ctx)
    first = validate_curriculum_output(raw, ctx.to_payload())
    stage = raw["stages"][0]
    stage["outcome_refs"].reverse()
    stage["knowledge"][0]["outcome_refs"].reverse()
    stage["units"][0]["outcome_refs"].reverse()
    stage["units"][0]["rubric"][0]["outcome_refs"].reverse()
    stage["assignments"][0]["outcome_refs"].reverse()
    stage["tasks"][0]["outcome_refs"].reverse()
    stage["tasks"][0]["acceptance"][0]["outcome_refs"].reverse()
    raw["carrier"]["final_artifact"]["acceptance"][0]["outcome_refs"].reverse()
    second = validate_curriculum_output(raw, ctx.to_payload())
    assert first.plan_hash == second.plan_hash
    assert first.to_payload() == second.to_payload()
