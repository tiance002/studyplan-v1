"""Explicit Fake presentation and known semantic escapes; no provider dispatch."""

import json
from copy import deepcopy

import pytest
from app.agent_workflows.nodes import PlanningNodes
from app.agent_workflows.planning_batches import (
    DEFAULT_BUDGET,
    freeze_manifest,
    manifest_is_intact,
    structure_payload,
)
from app.agent_workflows.planning_structure import (
    FOCUS_FORMAT,
    REVIEWED_STRUCTURE_V1,
    presentation_entry,
    presentation_message_ceiling,
    uses_reviewed_structure,
)
from app.infrastructure.providers.fake import FakeLLM
from app.infrastructure.providers.planning_demo import build_planning_demo

from tests.unit.test_reviewed_structure_contract import state, valid


@pytest.mark.parametrize(
    "mutation",
    ["foreign_focus", "cross_stage", "nodes", "canonical_rubric", "k8s", "training", "payment", "extra_task"],
)
def test_known_presentation_escapes_rejected(mutation):
    s = state()
    b = s["manifest"]["structure_batches"][s["current_structure_index"]]
    raw = valid(s)
    if mutation == "foreign_focus":
        raw["units"][0]["focus_refs"] = ["forged"]
    elif mutation == "cross_stage":
        raw["units"][0]["node_keys"] = ["node.v62.agent.application.a0"]
    elif mutation == "nodes":
        raw["nodes"] = []
    elif mutation == "canonical_rubric":
        raw["units"][0]["rubric"] = {"canonical_knowledge": {}}
    else:
        raw["units"][0]["objectives"] = [
            {
                "k8s": "必须部署 Kubernetes 集群",
                "training": "必须训练模型",
                "payment": "必须支付完成付款",
                "extra_task": "必须新建额外项目，新增必做任务",
            }[mutation]
        ]
    entry = presentation_entry(raw, s, b)
    assert entry["_presentation_errors"] and not entry["nodes"] and not entry["units"]


def test_a2_three_visible_fake_units_same_canonical_no_extra_tasks():
    s = state()
    b = s["manifest"]["structure_batches"][s["current_structure_index"]]
    fake = build_planning_demo()
    nodes = PlanningNodes(llm=fake, save_draft=lambda _: None)
    s.update(nodes.generate_structure_batch(s))
    entry = s["structure_batches"][0]
    assert len(entry["nodes"]) == 1 and len(entry["units"]) == 3
    assert all(
        u["node_keys"] == b["node_keys"] and u["rubric"]["teaching"]["focus_refs"] for u in entry["units"]
    )
    assert len({u["title"] for u in entry["units"]}) == 3
    assert not nodes.validate_structure_batch_node(
        {**s, "structure_batches": [{}] * s["current_structure_index"] + [entry]}
    )["structure_errors"]


def test_repair_budget_is_enforced_at_dispatch_boundary():
    s = state()
    s["repair_count"] = 2
    fake = FakeLLM({"planning.repair": lambda *_: valid(s)})
    assert PlanningNodes(llm=fake).repair_batch(s)["generation_errors"]
    assert not fake.calls


def test_mixed_batch_eligibility_and_old_marker_wire_preserved():
    s = state()
    pack = deepcopy(s["domain_pack"])
    pack["stage_blueprints"][-1]["node_keys"] = []
    m = freeze_manifest(pack, DEFAULT_BUDGET, "mock:mixed", structure_input_format=REVIEWED_STRUCTURE_V1)
    assert m["structure_focus_format"] == FOCUS_FORMAT and manifest_is_intact(m)
    assert uses_reviewed_structure(m, m["structure_batches"][0])
    assert not uses_reviewed_structure(m, m["structure_batches"][-1])
    assert "_structure_input_format" not in structure_payload(
        {"manifest": m, "domain_pack": pack}, m["structure_batches"][-1]
    )
    old = freeze_manifest(
        s["domain_pack"], DEFAULT_BUDGET, "mock:old", structure_input_format=REVIEWED_STRUCTURE_V1
    )
    old.pop("structure_focus_format")
    for b in old["structure_batches"]:
        b.pop("structure_input_format", None)
    from app.agent_workflows.planning_batches import _canonical_hash

    old.pop("manifest_hash")
    old["manifest_hash"] = _canonical_hash(old)
    payload = structure_payload({**s, "manifest": old}, old["structure_batches"][0])
    assert "_structure_focus_format" not in payload and "allowed_teaching_focus" not in payload
    raw = {
        "units": [
            {
                "title": "旧候选组织",
                "node_keys": old["structure_batches"][0]["node_keys"],
                "objectives": ["解释当前阶段"],
            }
        ]
    }
    assert not presentation_entry(raw, {**s, "manifest": old}, old["structure_batches"][0])[
        "_presentation_errors"
    ]


def test_scope_strings_not_character_slices_and_input_local():
    s = state()
    b = s["manifest"]["structure_batches"][s["current_structure_index"]]
    p = structure_payload(s, b)
    assert p["canonical_capabilities"][0]["scope"][0].startswith("能定义")
    assert len(p["allowed_teaching_focus"]) > 1
    serialized = json.dumps(p, ensure_ascii=False)
    assert len(serialized) < presentation_message_ceiling(p)
    assert all(x not in p for x in ("publication_evidence", "resources", "domain_pack"))


def test_search_only_remains_open():
    s = state()
    pack = deepcopy(s["domain_pack"])
    pack["resource_support"] = "search_only"
    from app.agent_workflows.planning_structure import has_canonical_inventory

    assert not has_canonical_inventory(pack)
    m = freeze_manifest(pack, DEFAULT_BUDGET, "mock:open")
    assert "structure_input_format" not in m
    assert "_structure_input_format" not in structure_payload(
        {"manifest": m, "domain_pack": pack}, m["structure_batches"][0]
    )
