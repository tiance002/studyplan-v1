"""Task 3: frozen batches, per-batch graph, bounded repair and run budget.

These tests pin the *protocol mechanics* only (no real model, no cloud call):

- the frozen manifest keeps every reviewed stage/node key and computes the exact
  request/output caps for the Agent pack (9 structure + 9 practice + 1 outline,
  at most two repairs);
- an unsupported direction is a generic, explicitly unverified ``search_only``
  skeleton whose slot count is a request-budget boundary, not domain coverage;
- a model failure / truncation stops immediately with the exact
  request count and never triggers a later stage or a repair;
- only localisable content errors consume the shared two-repair budget;
- merge is deterministic and rejects duplicates, missing stages and forged
  reviewed keys instead of silently repairing them.
"""

from __future__ import annotations

import pytest
from app.agent_workflows.nodes import PlanningNodes
from app.agent_workflows.planning_batches import (
    PROTOCOL_VERSION,
    attempt_key,
    budget_violation,
    freeze_manifest,
    manifest_is_intact,
    run_batched_planning_graph,
)
from app.application.planning_budget import BudgetPolicy
from app.infrastructure import domain_pack

from tests.helpers.batched_planning import OUTLINE, PRACTICE, REPAIR, STRUCTURE, ScriptedLLM

POLICY = BudgetPolicy(4096, 8192, 4096, 8192, 8192, 393216)
AGENT_GOAL = "从 Python 基础开始学习 Agent 应用开发"


def _pack(goal: str = AGENT_GOAL) -> dict:
    return domain_pack.select_domain_pack(goal)


def _run(pack: dict, llm: ScriptedLLM, *, goal: str = AGENT_GOAL, run_id: str = "run"):
    nodes = PlanningNodes(llm=llm, save_draft=lambda state: {"draft_ref": "draft:1", "draft_hash": "hash:1"})
    return run_batched_planning_graph(nodes, {"goal": goal, "run_id": run_id, "domain_pack": pack})


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------


def test_manifest_preserves_agent_requirements():
    pack = _pack()
    manifest = freeze_manifest(pack, POLICY, "mock:1")
    assert manifest["protocol"] == PROTOCOL_VERSION
    assert manifest["structure_batches_count"] == 9
    assert manifest["practice_batches_count"] == 9
    assert manifest["max_requests"] == 21
    assert manifest["max_output_budget"] == 131072
    assert set(manifest["required_node_keys"]) == set(pack["required_node_keys"])


def test_search_only_manifest_is_a_generic_unverified_budget_boundary():
    pack = _pack("学习水彩构图与水彩技法")
    assert pack["resource_support"] == "search_only"
    manifest = freeze_manifest(pack, POLICY, "mock:1")
    assert manifest["reviewed"] is False
    assert manifest["resource_support"] == "search_only"
    assert manifest["required_node_keys"] == []
    assert manifest["structure_batches_count"] == 4
    assert manifest["practice_batches_count"] == 4
    assert manifest["max_requests"] == 11
    assert manifest["max_output_budget"] == 4096 + 4 * 8192 + 4 * 4096 + 2 * 8192


def test_agent_pack_keeps_nine_stages_and_twenty_seven_keys():
    pack = _pack()
    assert len(pack["stage_blueprints"]) == 9
    assert len(pack["required_node_keys"]) == 27
    manifest = freeze_manifest(pack, POLICY, "mock:1")
    assert len(manifest["stages"]) == 9
    assert len(manifest["required_node_keys"]) == 27
    # A manifest must survive more reviewed nodes than today's pack.
    extended = dict(pack)
    extended["required_node_keys"] = list(pack["required_node_keys"]) + ["node.future"]
    assert "node.future" in freeze_manifest(extended, POLICY, "mock:1")["required_node_keys"]


def test_manifest_tamper_is_detected():
    manifest = freeze_manifest(_pack(), POLICY, "mock:1")
    assert manifest_is_intact(manifest)
    manifest["max_requests"] = 999
    assert not manifest_is_intact(manifest)


def test_attempt_key_is_stable_and_protocol_scoped():
    first = attempt_key("run1", STRUCTURE, "stage.tools", 2)
    assert first == attempt_key("run1", STRUCTURE, "stage.tools", 2)
    assert first != attempt_key("run1", STRUCTURE, "stage.tools", 3)
    assert PROTOCOL_VERSION in first


# ---------------------------------------------------------------------------
# Fail-fast request counts
# ---------------------------------------------------------------------------


def test_truncation_at_outline_stops_with_a_single_request():
    pack = _pack()
    llm = ScriptedLLM(pack, fail_at=(OUTLINE, 1))
    trace = _run(pack, llm)
    assert trace.stopped_at == "failed"
    assert llm.count() == 1
    assert llm.count(REPAIR) == 0


def test_truncation_at_fifth_structure_batch_stops_with_six_requests():
    pack = _pack()
    llm = ScriptedLLM(pack, fail_at=(STRUCTURE, 5))
    trace = _run(pack, llm)
    assert trace.stopped_at == "failed"
    assert llm.count(STRUCTURE) == 5
    assert llm.count() == 6
    assert llm.count(PRACTICE) == 0
    assert llm.count(REPAIR) == 0
    # Previously validated batches survive the stop.
    assert len(trace.state["structure_batches"]) == 4


def test_truncation_at_third_practice_batch_stops_with_thirteen_requests():
    pack = _pack()
    llm = ScriptedLLM(pack, fail_at=(PRACTICE, 3))
    trace = _run(pack, llm)
    assert trace.stopped_at == "failed"
    assert llm.count(STRUCTURE) == 9
    assert llm.count(PRACTICE) == 3
    assert llm.count() == 13
    assert llm.count(REPAIR) == 0


def test_empty_practice_object_enters_content_repair():
    pack = _pack()
    llm = ScriptedLLM(pack, empty_at=(PRACTICE, 1))
    trace = _run(pack, llm)
    assert trace.stopped_at == "await_approval"
    assert llm.count(REPAIR) == 1
    repair = next(c for c in llm.calls if c["purpose"] == REPAIR)
    assert repair["payload"]["batch"] == {}
    assert any("缺少必需字段：tasks" in error for error in repair["payload"]["errors"])


# ---------------------------------------------------------------------------
# Successful run
# ---------------------------------------------------------------------------


def test_full_agent_run_merges_a_complete_route_in_nineteen_requests():
    pack = _pack()
    llm = ScriptedLLM(pack)
    trace = _run(pack, llm)
    assert trace.stopped_at == "await_approval"
    assert llm.count() == 19
    assert (llm.count(OUTLINE), llm.count(STRUCTURE), llm.count(PRACTICE)) == (1, 9, 9)
    assert llm.count(REPAIR) == 0
    assert set(pack["required_node_keys"]) <= {node["stable_key"] for node in trace.state["nodes"]}
    assert len(trace.state["practice_proposal"]["tasks"]) == 9
    assert trace.state["route_status"] == "reviewed"
    assert trace.state["resource_support"] == "reviewed_index"


def test_search_only_run_is_flagged_generic_unverified():
    goal = "学习水彩构图与水彩技法"
    pack = _pack(goal)
    llm = ScriptedLLM(pack)
    trace = _run(pack, llm, goal=goal, run_id="other")
    assert trace.stopped_at == "await_approval"
    assert llm.count() == 9  # 1 outline + 4 structure + 4 practice
    assert trace.state["route_scope"] == "search_only"
    assert trace.state["route_status"] == "generic_unverified"
    assert trace.state["resource_support"] == "needs_resource_review"
    assert len(trace.state["outline"]["sections"]) == 4
    assert not any("complete" in str(s.get("title", "")).lower()
                   for s in trace.state["outline"]["sections"])


# ---------------------------------------------------------------------------
# Bounded repair
# ---------------------------------------------------------------------------


def test_local_content_error_is_repaired_once_within_budget():
    pack = _pack()
    llm = ScriptedLLM(pack, invalid_at=(STRUCTURE, 2))
    trace = _run(pack, llm)
    assert trace.stopped_at == "await_approval"
    assert llm.count(REPAIR) == 1
    assert trace.state["repair_count"] == 1


def test_shared_repair_budget_is_capped_at_two():
    pack = _pack()
    llm = ScriptedLLM(pack, persistent_invalid=(STRUCTURE, 2))
    trace = _run(pack, llm)
    assert trace.stopped_at == "failed"
    assert llm.count(REPAIR) == 2
    assert trace.state["repair_count"] == 2


def test_forged_reviewed_node_is_rejected_not_silently_kept():
    pack = _pack()
    llm = ScriptedLLM(pack, forged_node_key="node.invented")
    trace = _run(pack, llm)
    assert trace.stopped_at == "failed"
    assert any("未审核知识节点" in error for error in trace.state["validation_errors"])


def test_forged_resource_source_is_rejected():
    pack = _pack()
    llm = ScriptedLLM(pack, forged_resource_stage="stage.tools")
    trace = _run(pack, llm)
    assert trace.stopped_at == "failed"
    assert any("资源来源未在受审核清单中" in error for error in trace.state["validation_errors"])


def test_demo_provider_completes_the_batched_agent_route():
    from app.infrastructure.providers.planning_demo import build_planning_demo

    pack = _pack()
    nodes = PlanningNodes(llm=build_planning_demo(),
                          save_draft=lambda state: {"draft_ref": "draft:demo", "draft_hash": "hash:demo"})
    trace = run_batched_planning_graph(nodes, {"goal": AGENT_GOAL, "run_id": "demo", "domain_pack": pack})
    assert trace.stopped_at == "await_approval"
    assert set(pack["required_node_keys"]) <= {node["stable_key"] for node in trace.state["nodes"]}
    assert len(trace.state["practice_proposal"]["tasks"]) == 9
    assert trace.state["route_status"] == "reviewed"


# ---------------------------------------------------------------------------
# Deterministic merge
# ---------------------------------------------------------------------------


def _successful_state(pack: dict) -> tuple[PlanningNodes, dict]:
    llm = ScriptedLLM(pack)
    nodes = PlanningNodes(llm=llm, save_draft=lambda state: "draft")
    trace = run_batched_planning_graph(nodes, {"goal": AGENT_GOAL, "run_id": "run", "domain_pack": pack})
    assert trace.stopped_at == "await_approval"
    return nodes, dict(trace.state)


def test_merge_rejects_a_stage_without_units():
    pack = _pack()
    nodes, state = _successful_state(pack)
    state["structure_batches"][0]["units"] = []
    result = nodes.merge_and_validate(state)
    assert any("阶段缺少学习单元" in error for error in result["structure_errors"])


def test_merge_rejects_duplicate_node_keys():
    pack = _pack()
    nodes, state = _successful_state(pack)
    state["structure_batches"][1]["nodes"] = state["structure_batches"][0]["nodes"]
    result = nodes.merge_and_validate(state)
    assert any("知识节点重复" in error for error in result["structure_errors"])


def test_merge_rejects_missing_required_node():
    pack = _pack()
    nodes, state = _successful_state(pack)
    state["structure_batches"][3]["nodes"] = []
    state["structure_batches"][3]["units"] = []
    result = nodes.merge_and_validate(state)
    assert result["structure_errors"]


# ---------------------------------------------------------------------------
# Budget guard (pure)
# ---------------------------------------------------------------------------


def test_budget_guard_blocks_over_cap_and_unknown_stage():
    manifest = freeze_manifest(_pack(), POLICY, "mock:1")
    assert budget_violation(manifest, request_count=0, reserved_output=0,
                            stage_key="stage.tools", purpose=STRUCTURE) is None
    assert budget_violation(manifest, request_count=21, reserved_output=0,
                            stage_key="stage.tools", purpose=STRUCTURE) == "run_budget_exhausted"
    assert budget_violation(manifest, request_count=0, reserved_output=131073,
                            stage_key="stage.tools", purpose=STRUCTURE) == "run_budget_exhausted"
    assert budget_violation(manifest, request_count=0, reserved_output=0,
                            stage_key="stage.unknown", purpose=STRUCTURE) == "run_manifest_violation"


@pytest.mark.parametrize("purpose", [OUTLINE, STRUCTURE, PRACTICE, REPAIR])
def test_budget_guard_accepts_all_frozen_purposes(purpose):
    manifest = freeze_manifest(_pack(), POLICY, "mock:1")
    assert budget_violation(manifest, request_count=0, reserved_output=0,
                            stage_key="stage.tools", purpose=purpose) is None
