from copy import deepcopy

import pytest
from app.agent_workflows.nodes import PlanningNodes
from app.agent_workflows.planning_batches import run_batched_planning_graph
from app.application.plan_resources import restrict_pack_resources
from app.infrastructure.domain_pack import load_pack

from tests.helpers.batched_planning import ScriptedLLM


@pytest.mark.parametrize("filename", ["ai-fullstack-v1.json", "agent-application-v4.json", "cloud-services-v1.json"])
def test_missing_or_replaced_outline_facts_are_restored_without_erasing_personal_titles(filename):
    pack = load_pack(filename)
    class MissingFacts(ScriptedLLM):
        def _skeleton(self, payload):
            result = super()._skeleton(payload)
            for section in result["sections"]:
                section.update(title="我的阶段 " + section["stable_key"], resources=[], extensions=[], section_kind="general")
            return result
    trace = run_batched_planning_graph(PlanningNodes(llm=MissingFacts(pack), save_draft=lambda s: "draft"),
                                      {"goal": "personal goal", "run_id": "v61", "domain_pack": pack})
    assert trace.stopped_at == "await_approval", trace.state.get("validation_errors")
    for section, blueprint in zip(trace.state["outline"]["sections"], pack["stage_blueprints"], strict=True):
        assert section["title"].startswith("我的阶段")
        assert section["resources"] == blueprint["resources"]
        assert section["extensions"] == blueprint["extensions"]
        assert section["section_kind"] == blueprint["section_kind"]
        assert list(section["learning_guidance"]["learning_focus"]) == blueprint["learning_guidance"]["learning_focus"]
    filtered = restrict_pack_resources(trace.state, pack)
    stage = next(s for s in filtered["outline"]["sections"] if any(r["role"] == "case_study" for r in s["resources"]))
    case = next(r for r in stage["resources"] if r["role"] == "case_study")
    source = next(s for s in pack["resources"] if s["source_id"] == case["source_ref"])
    assert case["source_version"] == source["source_version"] and case["section_refs"] == []
    assert any(source["canonical_url"] in e["links"] for e in stage["extensions"])
    assert all(r["source_ref"] for s in filtered["outline"]["sections"] for r in s["resources"])


def test_root_only_exception_does_not_accept_forged_source_or_unverified_repository():
    pack = load_pack("ai-fullstack-v1.json")
    stage = deepcopy(pack["stage_blueprints"][-1])
    case = next(r for r in stage["resources"] if r["role"] == "case_study")
    source = next(s for s in pack["resources"] if s["source_id"] == case["source_ref"])
    source["verification_status"] = "unverified"
    filtered = restrict_pack_resources({"outline": {"sections": [stage]}}, pack)
    assert not next(r for r in filtered["outline"]["sections"][0]["resources"] if r["role"] == "case_study")["source_ref"]
    stage["extensions"][0]["links"] = ["https://evil.example/unknown/repo"]
    filtered = restrict_pack_resources({"outline": {"sections": [stage]}}, pack)
    assert not filtered["outline"]["sections"][0]["extensions"][0]["links"]
