"""Catch guidance loss at merge, business projection, hashing and version rebuild."""
import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest
from app.agent_workflows.nodes import PlanningNodes
from app.agent_workflows.planning_batches import run_batched_planning_graph
from app.application.draft_projection import CatalogIds, project_draft
from app.domain.planning.models import PlanDraft, revision_from_draft
from app.infrastructure.domain_pack import load_pack

from tests.helpers.batched_planning import ScriptedLLM

FIXTURE = Path(__file__).resolve().parents[3] / "docs/curriculum/tool-calling-vertical-fixture-2026-10-03.json"


def guided_pack():
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    pack = deepcopy(load_pack("agent-application-v3.json"))
    stage = next(s for s in pack["stage_blueprints"] if s["stable_key"] == fixture["stage_key"])
    stage["learning_guidance"] = fixture["learning_guidance"]
    practice = next(p for p in pack["practice_blueprints"] if p["section_key"] == fixture["stage_key"])
    practice.update(goal="给已有聊天 Agent 增加 read_file 和 search_note，保留普通聊天",
                    acceptance=fixture["learning_guidance"]["practice_delta"]["validation"])
    return pack


def test_generated_tool_calling_guidance_survives_business_projection_and_revision():
    pack = guided_pack()
    llm = ScriptedLLM(pack)
    nodes = PlanningNodes(llm=llm, save_draft=lambda state: {"draft_ref": "new-fixture", "draft_hash": "fixture"})
    trace = run_batched_planning_graph(nodes, {"goal": "理解 Tool Calling", "run_id": "new-fixture", "domain_pack": pack})
    draft = project_draft(project_id="fixture-project", run_id="new-fixture", goal_snapshot="理解 Tool Calling",
                          revision_candidate=1, state=trace.state, catalog=CatalogIds(
                              node_ids={n["stable_key"]: "kn_" + n["stable_key"] for n in trace.state["nodes"]},
                              unit_ids={u["stable_key"]: "unit_" + u["stable_key"] for u in trace.state["units"]},
                              practice_project_id="practice_fixture",
                              task_ids={t["stable_key"]: "task_" + t["stable_key"] for t in trace.state["practice_proposal"]["tasks"]}))
    stage = next(s for s in draft.stages if s.stable_key == "stage.tools")
    guide = stage.learning_guidance
    assert guide is not None
    assert guide.practice_delta.baseline == "已有最小聊天 Agent"
    assert guide.practice_delta.validation == ("正常工具调用", "未知 Tool", "错误参数", "Tool 抛错")
    assert guide.exposure_relation == "deepen"
    assert "第三个 Tool" in guide.comparison_focus[0]
    assert guide.source_slice.optional is True
    assert guide.source_slice.verification_status == "suggested"
    revision = revision_from_draft(draft, revision=1)
    copied = next(s for s in revision.stages if s.stable_key == "stage.tools")
    assert copied.stage_id != stage.stage_id
    assert copied.learning_guidance == guide
    structure_call = next(c for c in llm.calls if c["purpose"] == "planning.structure" and c["payload"]["stage"]["stable_key"] == "stage.tools")
    assert structure_call["payload"]["learning_guidance"]["practice_delta"]["baseline"] == "已有最小聊天 Agent"
    task = next(t for t in trace.state["practice_proposal"]["tasks"] if t["section_key"] == "stage.tools")
    assert "read_file" in task["goal"] and "search_note" in task["goal"]
    assert task["acceptance"] == ["正常工具调用", "未知 Tool", "错误参数", "Tool 抛错"]


def test_guidance_changes_confirmation_hash_but_legacy_stage_is_compatible():
    from app.domain.enums import OutlineSectionKind
    from app.domain.planning.guidance import guidance_from_payload
    from app.domain.planning.models import PlanStage
    guide = guidance_from_payload(json.loads(FIXTURE.read_text(encoding="utf-8"))["learning_guidance"])
    stage = PlanStage.create(stable_key="stage.tools", title="工具", section_kind=OutlineSectionKind.CORE, order_index=0)
    draft = PlanDraft("draft", "project", "run", "工具", 1, stages=(stage,))
    old_hash = draft.content_hash
    old_revision = revision_from_draft(draft, revision=1).structure_fingerprint()
    draft.stages = (replace(stage, learning_guidance=guide),)
    assert draft.content_hash != old_hash
    assert revision_from_draft(draft, revision=1).structure_fingerprint() != old_revision
    assert replace(draft.stages[0], learning_guidance=None) == stage


def test_string_is_not_silently_split_into_learning_focus_items():
    from app.core.errors import ValidationAppError
    from app.domain.planning.guidance import guidance_from_payload
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))["learning_guidance"]
    raw["learning_focus"] = "schema"
    with pytest.raises(ValidationAppError):
        guidance_from_payload(raw)


def test_model_cannot_supply_claims_of_previous_learning_or_source_review():
    from app.agent_workflows.planning_batches import merge_batches
    pack = guided_pack()
    outline = {"sections": [{"stable_key": "stage.tools", "learning_guidance": {"previous_relation": "已经掌握所有工具", "source_slice": {"verification_status": "reviewed"}}}]}
    merged = merge_batches(outline, [], [], pack)
    guide = merged["outline"]["sections"][0]["learning_guidance"]
    assert guide["source_slice"]["verification_status"] == "suggested"
    assert "fixture" in guide["previous_relation"]


def test_seed_guidance_unknown_module_is_rejected_before_generation():
    from app.agent_workflows.planning_batches import DEFAULT_BUDGET, freeze_manifest
    from app.core.errors import ValidationAppError
    pack = guided_pack()
    next(s for s in pack["stage_blueprints"] if s["stable_key"] == "stage.tools")["learning_guidance"]["knowledge_keys"] = ["foreign.module"]
    with pytest.raises(ValidationAppError):
        freeze_manifest(pack, DEFAULT_BUDGET, "fixture")


def test_invalid_guidance_is_rejected_before_seed_import_writes():
    from app.core.errors import ValidationAppError
    from app.domain.domain_packs.validation import validate_seed
    pack = guided_pack()
    next(s for s in pack["stage_blueprints"] if s["stable_key"] == "stage.tools")["learning_guidance"]["knowledge_keys"] = ["foreign.module"]
    with pytest.raises((ValueError, ValidationAppError)):
        validate_seed(pack)


def test_replacing_primary_invalidates_old_source_relationship_but_keeps_practice():
    from app.domain.planning.guidance import changed_resource_guidance, guidance_from_payload
    guide = guidance_from_payload(json.loads(FIXTURE.read_text(encoding="utf-8"))["learning_guidance"])
    replacement = changed_resource_guidance(guide)
    assert replacement.exposure_relation == "unknown"
    assert replacement.comparison_focus == () and replacement.source_slice is None
    assert replacement.practice_delta == guide.practice_delta
    assert guide.source_slice is not None and guide.exposure_relation == "deepen"


def repeated_guided_pack():
    pack = guided_pack()
    first = next(s for s in pack["stage_blueprints"] if s["stable_key"] == "stage.tools")
    repeated = deepcopy(first)
    repeated.update(stable_key="stage.tools.review", title="再次复习工具分派", node_keys=["node.tools"], resources=[])
    repeated["learning_guidance"].update(exposure_relation="review", previous_relation="已安排过工具实现，这次只复习错误边界")
    pack["stage_blueprints"].append(repeated)
    practice = deepcopy(next(p for p in pack["practice_blueprints"] if p["section_key"] == "stage.tools"))
    practice.update(stable_key="task.tools.review", section_key="stage.tools.review", node_keys=["node.tools"])
    pack["practice_blueprints"].append(practice)
    return pack


def test_controlled_repeat_reuses_one_knowledge_identity_with_two_exposures():
    pack = repeated_guided_pack()
    nodes = PlanningNodes(llm=ScriptedLLM(pack), save_draft=lambda state: {"draft_ref": "repeat-fixture", "draft_hash": "fixture"})
    trace = run_batched_planning_graph(nodes, {"goal": "Tool Calling 实现后再复习", "run_id": "repeat-fixture", "domain_pack": pack})
    assert trace.state.get("draft_ref") == "repeat-fixture", trace.state.get("structure_errors")
    assert [n["stable_key"] for n in trace.state["nodes"]].count("node.tools") == 1
    units = [u for u in trace.state["units"] if "node.tools" in u["node_keys"]]
    assert len(units) == 2 and len({u["stable_key"] for u in units}) == 2
    stages = {s["stable_key"]: s for s in trace.state["outline"]["sections"]}
    assert stages["stage.tools"]["learning_guidance"]["exposure_relation"] == "deepen"
    assert stages["stage.tools.review"]["learning_guidance"]["exposure_relation"] == "review"
