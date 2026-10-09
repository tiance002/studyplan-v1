"""Actual frozen 184/187 inputs, synthetic resources, and no external I/O."""
import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import httpx
import pytest
from app.core.errors import ValidationAppError
from app.domain.planning.capabilities import CapabilityPlanValidator
from app.domain.planning.content_coverage import CoverageEvaluator
from app.domain.planning.curriculum import prepare_curriculum, validate_curriculum_output
from app.domain.planning.goal_requirements import GoalRequirementProfileValidator
from app.domain.planning.intent import GoalSpec
from app.domain.planning.resource_gaps import extract
from app.domain.planning.resource_research import ResearchBudget, ResearchSession, research_input_hash
from app.infrastructure.providers.openai_compatible import OpenAICompatibleLLM
from app.infrastructure.reviewed_content_coverage import load_reviewed_content_index
from app.ports.llm import LLMResult

from backend.tests.unit import test_resource_research as f
from backend.tests.unit.test_curriculum_product_v2 import SCOPE, arrange_scope, fixture
from backend.tests.unit.test_research_comparison_v2 import V2, Bodies, Reader


def actual_inputs():
    data = json.loads((Path(__file__).parents[1] / "fixtures/planning_v2/product_fix_184_187.json").read_text(encoding="utf8"))
    profile = GoalRequirementProfileValidator().validate(data["item1"], goal=GoalSpec(**data["goal"]))
    plan = CapabilityPlanValidator().validate(data["item2"], profile=profile)
    assert profile.profile_hash == data["profile_hash"]
    assert plan.plan_hash == data["plan_hash"]
    index = load_reviewed_content_index()
    coverage = CoverageEvaluator().evaluate(plan, index)
    return profile, plan, coverage, extract(plan, coverage)


def test_actual_six_gaps_required_first_bounded_joint_scope_and_no_python():
    values = actual_inputs()
    p, plan, coverage, gaps = values
    before = plan.to_payload(), gaps.to_payload()
    budget = ResearchBudget()
    session = ResearchSession("offline-real-inputs", research_input_hash(gaps, plan, coverage, p, budget,
        project_id="project", actor_id="actor", checked_at=f.STAMP, rules_version=V2), budget, rules_version=V2)
    reader, bodies = Reader(), Bodies()
    result, _, github, _, _, _, _ = f.run(values, session=session, github=f.Search([f.candidate()]),
        bodies=bodies, reader=reader)
    assert "llm.api.exchange" in github.calls[0].node_keys
    assert "python.core" not in {e.requirement.capability_id for e in result.entries}
    assert all(len(c["payload"]["must_teach"]) <= 6 for c in reader.calls)
    first_scope = {o["outcome_id"] for o in reader.calls[0]["payload"]["must_teach"]}
    assert first_scope & {"structured.output.contract_definition", "tool.calling.input_validation"}
    mcp_scope = next(c["payload"]["must_teach"] for c in reader.calls
        if any(o["outcome_id"] == "mcp.minimal_connection" for o in c["payload"]["must_teach"]))
    assert {o["outcome_id"] for o in mcp_scope} == {"mcp.minimal_connection"}
    assert [e.requirement.capability_id for e in result.entries] == [g.capability_id for g in gaps.gaps]
    assert len(reader.calls) <= budget.max_reader_requests
    assert (plan.to_payload(), gaps.to_payload()) == before
    assert all(not b.chunks for b in bodies.produced)


def test_provider_v2_reader_and_curriculum_use_versioned_shapes_without_real_http():
    from backend.tests.unit.test_research_reader_provider import reader_output, reader_payload
    payload = reader_payload() | {"rules_version": V2}
    raw = reader_output(payload)
    chunk = payload["chunks"][0]
    raw["quality_evidence"] = {d: {"category": "adequate", "rationale": "Synthetic referenced quality opinion",
        "evidence_refs": [{"chunk_id": chunk["chunk_id"], "content_hash": chunk["content_hash"]}]}
        for d in ("continuity", "beginner_fit", "examples", "version_fit")}
    ctx, curriculum, _ = fixture(constraints=(SCOPE,))
    arrange_scope(curriculum, ctx)
    requests = []
    def handle(request):
        body = json.loads(request.content)
        message = json.loads(body["messages"][1]["content"])
        requests.append(body)
        output = raw if message["schema"] == "ResearchReaderV2" else curriculum
        return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(output)}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 100}})
    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        provider = OpenAICompatibleLLM(base_url="https://api.deepseek.com", api_key="offline-only", model="deepseek-flash", client=client)
        for purpose, schema, body in [("planning.research_reader", "ResearchReaderV2", payload),
                ("planning.curriculum_composition", "CurriculumPlanV2", ctx.to_payload())]:
            result = provider.generate_structured(purpose=purpose, schema_name=schema, payload=body, run_id="offline", attempt_id=schema)
            assert isinstance(result, LLMResult), result
    assert len(requests) == 2
    assert requests[0]["max_tokens"] <= 1024
    assert requests[0]["thinking"] == {"type": "disabled"}
    assert "quality_evidence" in json.loads(requests[0]["messages"][1]["content"])["field_shape"]
    assert "permission_obligations" in json.loads(requests[1]["messages"][1]["content"])["field_shape"]


def test_scope_cache_identity_changes_with_source_metadata():
    from app.application.teaching_resource_research import ResourceResearcher
    candidate = f.candidate()
    changed = replace(candidate, discovery={"source_version": "new"})
    assert candidate.url == changed.url
    assert ResourceResearcher._cache_key(candidate, "applied") != ResourceResearcher._cache_key(changed, "applied")
    assert ResourceResearcher._cache_key(candidate, "foundation") != ResourceResearcher._cache_key(candidate, "deep")


def test_required_missing_and_selected_recommended_still_block():
    ctx, raw, _ = fixture(recommended=True)
    raw["status"] = "complete"
    with pytest.raises(ValidationAppError):
        validate_curriculum_output(raw, ctx.to_payload())


def test_explicit_recommended_with_available_resources_cannot_be_silently_omitted():
    from app.domain.planning.content_coverage import ReviewedContentIndex

    from backend.tests.unit.test_capability_planning import cap, profile, wire
    from backend.tests.unit.test_capability_planning import plan as freeze
    from backend.tests.unit.test_curriculum import output
    from backend.tests.unit.test_research_comparison_v2 import execute
    p = profile("明确学习LLM和MCP")
    selected = freeze(p, wire(p, cap(p, "llm.api"), cap(p, "mcp", learning_requirement="recommended",
        project_usage="excluded", learning_target_refs=[p.required_requirements[0].requirement_id])))
    index = ReviewedContentIndex("empty", (), (), ())
    coverage = CoverageEvaluator().evaluate(selected, index)
    research, *_ = execute(values=(p, selected, coverage, extract(selected, coverage)))
    ctx = prepare_curriculum(p, selected, coverage, research, index, semantics_version=2)
    raw = output(ctx) | {"schema_version": 2, "semantics_version": 2, "permission_obligations": []}
    assert not raw["unresolved"]
    omitted = raw["stages"].pop()
    refs = set(omitted["outcome_refs"])
    raw["carrier"]["final_artifact"]["acceptance"][0]["outcome_refs"] = [r for r in raw["carrier"]["final_artifact"]["acceptance"][0]["outcome_refs"] if r not in refs]
    raw["status"] = "complete"
    with pytest.raises(ValidationAppError):
        validate_curriculum_output(raw, ctx.to_payload())


def test_v2_reader_quality_refs_cannot_lend_other_source_or_body_echo():
    from app.domain.planning.research_reader import validate_reader_output

    from backend.tests.unit.test_research_reader_provider import reader_output, reader_payload
    payload = reader_payload() | {"rules_version": V2}
    raw = reader_output(payload)
    chunk = payload["chunks"][0]
    raw["quality_evidence"] = {d: {"category": "strong", "rationale": "Bounded synthetic opinion",
        "evidence_refs": [{"chunk_id": chunk["chunk_id"], "content_hash": chunk["content_hash"]}]}
        for d in ("continuity", "beginner_fit", "examples", "version_fit")}
    for field in ("source", "echo"):
        bad = deepcopy(raw)
        if field == "source":
            bad["quality_evidence"]["examples"]["evidence_refs"][0]["content_hash"] = "0" * 64
        else:
            bad["quality_evidence"]["examples"]["rationale"] = chunk["text"]
        with pytest.raises(ValueError):
            validate_reader_output(bad, payload)


@pytest.mark.parametrize("category", ["unknown", "insufficient"])
def test_negative_quality_is_a_valid_missing_result_not_a_qualified_resource(category):
    class NegativeReader(Reader):
        def generate_structured(self, **kwargs):
            response = super().generate_structured(**kwargs)
            payload = deepcopy(response.payload)
            opinion = payload["quality_evidence"]["examples"]
            opinion["category"] = category
            opinion["rationale"] = "Synthetic evidence cannot establish suitable examples"
            if category == "unknown":
                opinion["evidence_refs"] = []
            return replace(response, payload=payload)

    values = f.inputs()
    p, frozen, coverage, gaps = values
    budget = ResearchBudget()
    session = ResearchSession("negative-quality", research_input_hash(gaps, frozen, coverage, p, budget,
        project_id="project", checked_at=f.STAMP, actor_id="actor", rules_version=V2), budget, rules_version=V2)
    result, *_ = f.run(values, session=session, reader=NegativeReader(), bodies=Bodies())
    assert not result.entries[0].resources
    assert result.entries[0].status == "unresolved"
    assert "teaching_fit_unresolved" in result.entries[0].reason_codes
    assert not session.blocked


def test_v2_unknown_does_not_redispatch_after_restore():
    values = f.inputs()
    p, frozen, coverage, gaps = values
    budget = ResearchBudget()
    session = ResearchSession("unknown-v2", research_input_hash(gaps, frozen, coverage, p, budget,
        project_id="project", checked_at=f.STAMP, actor_id="actor", rules_version=V2), budget, rules_version=V2)
    reader, bodies, search = f.Reader("unknown"), Bodies(), f.Search()
    _, session, _, _, _, _, researcher = f.run(values, session=session, reader=reader, bodies=bodies, github=search)
    reserved = dict(session.usage)
    restored = ResearchSession.restore(session.snapshot())
    f.run(values, session=restored, researcher=researcher)
    assert restored.blocked and restored.usage == reserved
    assert len(reader.calls) == len(bodies.calls) == len(search.calls) == 1
