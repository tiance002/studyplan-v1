from copy import deepcopy
from dataclasses import replace

import pytest
from app.agent_workflows.nodes import PlanningNodes
from app.agent_workflows.planning_batches import (
    DEFAULT_BUDGET,
    freeze_manifest,
    practice_payload,
    run_batched_planning_graph,
    structure_payload,
)
from app.api.v1.schemas import PlanGenerateRequest
from app.core.errors import ValidationAppError
from app.domain.enums import OutlineSectionKind
from app.domain.planning.guidance import guidance_from_payload, guidance_payload
from app.domain.planning.intent import GoalSpec, goal_spec_from_payload, required_module_closure
from app.domain.planning.models import PlanDraft, PlanStage, revision_from_draft

from tests.helpers.batched_planning import ScriptedLLM
from tests.unit.test_learning_guidance import guided_pack


def test_required_closure_is_transitive_ordered_and_does_not_require_optional():
    nodes = [
        {"stable_key": "tools", "prerequisite_keys": ["chat"]},
        {"stable_key": "python", "prerequisite_keys": []},
        {"stable_key": "chat", "parent_key": "python", "prerequisite_keys": []},
        {"stable_key": "optional", "prerequisite_keys": []},
    ]
    assert required_module_closure(nodes, ["tools", "tools"]) == ("python", "chat", "tools")
    assert required_module_closure(list(reversed(nodes)), ["tools"]) == ("python", "chat", "tools")
    for bad in ([{"stable_key": "tools", "prerequisite_keys": ["absent"]}],
                [{"stable_key": "tools", "prerequisite_keys": ["tools"]}]):
        with pytest.raises(ValidationAppError):
            required_module_closure(bad, ["tools"])
    with pytest.raises(ValidationAppError):
        required_module_closure(nodes, ["tools"], limit=2)


def test_structured_goal_is_explicit_bounded_and_legacy_optional():
    assert PlanGenerateRequest(goal="Agent").goal_spec is None
    spec = GoalSpec(target="Tool Calling", scope=("tool dispatch",), desired_depth="applied",
                    starting_point="会Python；见过Tool概念", outcome_purpose="interview",
                    constraints=("教材正文免费",))
    request = PlanGenerateRequest(goal="Agent", goal_spec=spec)
    assert goal_spec_from_payload(request.goal_spec.model_dump()) == spec
    for invalid in ({"outcome_purpose": "mastered"}, {"scope": "strings are not lists"},
                    {"constraints": ("x" * 301,)}, {"target": " "}):
        with pytest.raises((ValidationAppError, ValueError)):
            GoalSpec(**({"target": "Agent"} | invalid))


def test_frozen_context_reaches_batches_and_is_in_draft_revision_hash():
    pack = guided_pack()
    original = deepcopy(pack)
    spec = GoalSpec(target="Agent工具实现", outcome_purpose="interview", starting_point="基础Python")
    manifest = freeze_manifest(pack, DEFAULT_BUDGET, "fake", goal_spec=spec)
    assert pack == original
    assert manifest["goal_spec"]["outcome_purpose"] == "interview"
    assert set(manifest["required_node_keys"]) >= set(pack["required_node_keys"])
    state = {"domain_pack": pack, "manifest": manifest, "goal": "Agent", "structure_batches": []}
    assert structure_payload(state, manifest["structure_batches"][0])["goal_spec"] == manifest["goal_spec"]
    final_key = manifest["stages"][-1]["stage_key"]
    assert "2分钟" in " ".join(practice_payload(state, final_key)["required_outputs"])
    assert practice_payload(state, manifest["stages"][0]["stage_key"])["required_outputs"] == []
    stage = PlanStage.create(stable_key="tools", title="Tools", section_kind=OutlineSectionKind.CORE, order_index=0)
    draft = PlanDraft("draft", "project", "run", "Agent", 1, stages=(stage,))
    contextual = replace(draft, goal_spec=spec)
    assert contextual.content_hash != draft.content_hash
    revision = revision_from_draft(contextual, revision=1)
    assert revision.goal_spec == spec
    assert revision.structure_fingerprint() != revision_from_draft(draft, revision=1).structure_fingerprint()


def test_purpose_requirements_survive_generation_merge_and_only_affect_final_practice():
    pack = guided_pack()
    spec = GoalSpec(target="Agent", outcome_purpose="interview")
    manifest = freeze_manifest(pack, DEFAULT_BUDGET, "fake", goal_spec=spec)
    llm = ScriptedLLM(pack)
    nodes = PlanningNodes(llm=llm, save_draft=lambda state: {"draft_ref": "fixture", "draft_hash": "fixture"})
    trace = run_batched_planning_graph(nodes, {"goal": "Agent", "run_id": "intent-fixture", "domain_pack": pack,
                                            "manifest": manifest})
    assert trace.state.get("draft_ref") == "fixture"
    last = trace.state["outline"]["sections"][-1]
    assert "2分钟" in " ".join(last["learning_guidance"]["practice_delta"]["validation"])
    tasks = trace.state["practice_proposal"]["tasks"]
    assert sum("2分钟" in " ".join(t["acceptance"]) for t in tasks) == 1


def test_reading_and_practice_prerequisites_are_bounded_and_frozen():
    pack = guided_pack()
    stage = next(s for s in pack["stage_blueprints"] if s["stable_key"] == "stage.tools")
    raw = stage["learning_guidance"]
    assert "reading_prerequisites" not in guidance_payload(guidance_from_payload(raw))
    raw.update(reading_prerequisites=["先快速回顾Tool概念，最多1节"],
               practice_prerequisites=["已有聊天Agent可运行，普通聊天测试通过"])
    guide = guidance_from_payload(raw)
    assert guide.reading_prerequisites == ("先快速回顾Tool概念，最多1节",)
    manifest = freeze_manifest(pack, DEFAULT_BUDGET, "fake")
    frozen = next(s for s in manifest["stages"] if s["stage_key"] == "stage.tools")
    assert frozen["learning_guidance"]["practice_prerequisites"] == guide.practice_prerequisites
    with pytest.raises(ValidationAppError):
        guidance_from_payload({**raw, "reading_prerequisites": ["x"] * 21})
