"""Finite constraint adaptation; model fixtures never prove real semantic quality."""
from dataclasses import asdict, replace

import pytest
from app.application.teaching_resource_research import ResourceResearcher
from app.core.errors import ValidationAppError
from app.core.ids import content_hash
from app.domain.planning.content_coverage import CoverageEvaluator, ReviewedContentIndex
from app.domain.planning.curriculum import ProjectCase, prepare_curriculum, validate_curriculum_output
from app.domain.planning.resource_gaps import extract

from backend.tests.unit.test_capability_planning import cap, plan, profile, wire
from backend.tests.unit.test_curriculum import local_mcp_inputs, output
from backend.tests.unit.test_resource_research import Bodies, Reader, Search, body, run


def fixture(constraints=(), *, full=False, project=None, access="free_public"):
    _, _, actual, source, proof = local_mcp_inputs()
    p = replace(profile("学习MCP概念", constraints=constraints), project_context=project)
    frozen = plan(p, wire(p, cap(p, "mcp", desired_depth="foundation", project_usage="excluded")))
    index = actual if full else ReviewedContentIndex("empty", (), (), ())
    coverage = CoverageEvaluator().evaluate(frozen, index)
    gaps = extract(frozen, coverage)

    class Catalog:
        def load_sources(self, *, source_ids):
            return {source.source_id: source}

    gh, web, bodies, reader = Search([]), Search([]), Bodies(), Reader()
    proofs = () if access is None else (replace(proof, access=access),)
    researcher = ResourceResearcher(github=gh, web=web, body_reader=bodies, llm=reader,
        reviewed_index=actual, catalog=Catalog(), access_proofs=proofs)
    research, *_ = run((p, frozen, coverage, gaps), researcher=researcher)
    ctx = prepare_curriculum(p, frozen, coverage, research, index,
        catalog_sources=(source,), access_proofs=proofs)
    return p, frozen, research, ctx, (gh, web, bodies, reader)


@pytest.mark.parametrize("constraint", ["免费教材", "只使用免费教材", "教程免费"])
def test_actual_reviewed_free_material_reused_with_explicit_free_constraint(constraint):
    p, _, result, _, ports = fixture((constraint,))
    assert result.entries[0].status == "resolved"
    assert result.entries[0].resources[0].free_access == "confirmed"
    assert result.entries[0].requirement.hard_constraints == p.hard_constraints
    assert not any(port.calls for port in ports)


def test_full_actual_mcp_free_proof_allows_complete_and_server_records_assessment():
    _, _, research, ctx, ports = fixture(("只使用免费教材",), full=True)
    assert not research.entries
    raw = output(ctx)
    raw["status"] = "complete"
    doc = validate_curriculum_output(raw, ctx.to_payload()).to_payload()
    assessments = doc["compile_context"]["constraint_assessments"]
    assert assessments[0]["status"] == "satisfied" and assessments[0]["evidence_refs"]
    assert doc["compile_context"]["constraints"] == ctx.to_payload()["constraints"]
    assert not any(port.calls for port in ports)


@pytest.mark.parametrize("access", [None, "unknown", "paid"])
def test_missing_or_paid_proof_never_resolves_or_completes(access):
    _, _, research, ctx, _ = fixture(("免费教材",), access=access)
    assert research.entries[0].status == "unresolved"
    raw = output(ctx)
    assert validate_curriculum_output(raw, ctx.to_payload()).status == "incomplete"
    raw["status"], raw["unresolved"] = "complete", []
    with pytest.raises(ValidationAppError):
        validate_curriculum_output(raw, ctx.to_payload())


def test_existing_project_constraint_does_not_block_materials_but_requires_actual_carrier():
    _, _, result, ctx, ports = fixture(("不要重新创建演示项目",), full=False, project="已有本地待办CLI")
    assert result.entries[0].status == "resolved"
    raw = output(ctx)
    raw["status"] = "complete"
    doc = validate_curriculum_output(raw, ctx.to_payload()).to_payload()
    assert doc["carrier"]["kind"] == "user_project"
    assert doc["stages"][0]["tasks"][0]["practice_kind"] == "micro_exercise"
    assert doc["compile_context"]["constraint_assessments"][0]["status"] == "satisfied"
    raw["carrier"]["kind"] = "starter"
    with pytest.raises(ValidationAppError):
        validate_curriculum_output(raw, ctx.to_payload())
    assert not any(port.calls for port in ports)


def test_no_existing_project_cannot_satisfy_do_not_create_starter():
    _, _, _, ctx, _ = fixture(("不要重新创建演示项目",), full=True)
    raw = output(ctx)
    assert validate_curriculum_output(raw, ctx.to_payload()).status == "incomplete"
    raw["status"] = "complete"
    with pytest.raises(ValidationAppError):
        validate_curriculum_output(raw, ctx.to_payload())


@pytest.mark.parametrize("constraint", ["只读，不允许代码修改", "禁止联网", "只使用中文教材", "付费也可以但必须免费"])
def test_unproven_runtime_language_or_conflicting_constraint_cannot_complete(constraint):
    _, _, _, ctx, _ = fixture((constraint,), full=True)
    raw = output(ctx)
    assert validate_curriculum_output(raw, ctx.to_payload()).status == "incomplete"
    raw["status"] = "complete"
    with pytest.raises(ValidationAppError):
        validate_curriculum_output(raw, ctx.to_payload())


def test_no_network_constraint_reuses_local_only_never_dispatches():
    _, _, result, _, ports = fixture(("禁止联网",))
    assert result.entries[0].status == "resolved"
    assert not any(port.calls for port in ports)
    p = profile("学习MCP", constraints=("禁止联网",))
    frozen = plan(p, wire(p, cap(p, "mcp")))
    index = ReviewedContentIndex("empty", (), (), ())
    cov = CoverageEvaluator().evaluate(frozen, index)
    result, _, gh, web, bodies, reader, _ = run((p, frozen, cov, extract(frozen, cov)))
    assert result.entries[0].status == "unresolved" and "network_forbidden" in result.entries[0].reason_codes
    assert not any((gh.calls, web.calls, bodies.calls, reader.calls))


def test_readonly_only_applies_to_practice_not_tutorial_discovery():
    _, _, research, ctx, _ = fixture(("只读，不允许代码修改",))
    assert research.entries[0].status == "resolved"
    assert validate_curriculum_output(output(ctx), ctx.to_payload()).status == "incomplete"


def test_arbitrary_text_containing_free_is_not_approved_by_keyword():
    _, _, result, _, ports = fixture(("先免费，但之后的私有收费模式必须按秘密规则处理",))
    assert result.entries[0].reason_codes == ("constraints_pending",)
    assert not any(port.calls for port in ports)


def test_provider_cannot_add_satisfied_assessment_or_drop_original_ref():
    _, _, _, ctx, _ = fixture(("免费教材",), full=True)
    raw = output(ctx)
    raw["constraint_assessments"] = [{"status": "satisfied"}]
    with pytest.raises(ValidationAppError):
        validate_curriculum_output(raw, ctx.to_payload())
    raw = output(ctx)
    raw["status"], raw["constraint_refs"] = "complete", []
    with pytest.raises(ValidationAppError):
        validate_curriculum_output(raw, ctx.to_payload())


def test_free_unread_candidate_does_not_become_verified_teaching():
    p = profile("学习MCP", constraints=("免费教材",))
    frozen = plan(p, wire(p, cap(p, "mcp")))
    index = ReviewedContentIndex("empty", (), (), ())
    cov = CoverageEvaluator().evaluate(frozen, index)
    result, *_ = run((p, frozen, cov, extract(frozen, cov)), bodies=Bodies(body(status="unknown_access")))
    assert result.entries[0].status == "unresolved" and not result.entries[0].resources


def test_no_network_prevents_curriculum_model_and_case_dispatch_before_reservation():
    from backend.tests.unit.test_curriculum_composition import Projects, compose, setup
    _, _, _, ctx, _ = fixture(("禁止联网",), full=True)
    ctx, session, model = setup(ctx=ctx)
    projects = Projects()
    before = session.snapshot()
    result = compose(ctx, session, model, projects)
    assert result.error_class == "curriculum_constraints_pending"
    assert not model.calls and not projects.find_calls and not projects.inspect_calls
    assert session.snapshot() == before


def test_mandatory_chinese_stays_pending_without_trusted_language_proof():
    _, _, result, _, ports = fixture(("只使用中文教材",))
    assert result.entries[0].reason_codes == ("constraints_pending",)
    assert not any(port.calls for port in ports)


def test_chinese_preference_does_not_become_mandatory_qualification():
    _, _, result, ctx, _ = fixture(("中文优先",), full=True)
    assert not result.entries
    raw = output(ctx)
    raw["status"] = "complete"
    assert validate_curriculum_output(raw, ctx.to_payload()).status == "complete"


def test_free_tutorial_proof_cannot_be_lent_to_separate_project_study_case():
    _, _, _, ctx, _ = fixture(("免费教材",), full=True)
    payload = ctx.to_payload()
    refs = tuple(o["outcome_id"] for o in payload["capabilities"][0]["outcomes"])
    case = ProjectCase("case_bounded", "https://github.com/demo/tutorial", "synthetic-v1", "slices", refs,
        (("fixture:behavior-only", "a" * 64),), "bounded_reviewed", ("No free-access proof",))
    # Controlled input fixture: behavior qualification is not access proof.
    import json
    payload["project_cases"] = json.loads(json.dumps([asdict(case)]))
    payload["input_hash"] = content_hash({k: v for k, v in payload.items() if k != "input_hash"})
    raw = output(ctx, project_study=True)
    raw["input_hash"] = payload["input_hash"]
    raw["project_study_requirements"][0]["selected_case_ref"] = case.case_id
    assert validate_curriculum_output(raw, payload).status == "incomplete"
    raw["status"] = "complete"
    with pytest.raises(ValidationAppError):
        validate_curriculum_output(raw, payload)
