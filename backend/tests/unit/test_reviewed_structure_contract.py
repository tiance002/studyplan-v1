"""Presentation-only reviewed structures; no real provider requests."""

from copy import deepcopy

import pytest
from app.agent_workflows.nodes import PlanningNodes
from app.agent_workflows.planning_batches import (
    DEFAULT_BUDGET,
    freeze_manifest,
    structure_payload,
    validate_structure_batch,
)
from app.agent_workflows.planning_structure import (
    FOCUS_FORMAT,
    REVIEWED_STRUCTURE_V1,
    allowed_teaching_focus,
    presentation_entry,
    validate_presentation,
)
from app.domain.planning.semantic_content import adapt_semantic_pack
from app.infrastructure.domain_pack import load_pack
from app.infrastructure.providers.fake import FakeLLM


def state():
    goal = "零基础系统学习 Agent 应用开发，先做一个最小应用。"
    pack = adapt_semantic_pack(load_pack("agent-application-v6.json"), goal, None)
    manifest = freeze_manifest(
        pack,
        DEFAULT_BUDGET,
        "mock:contract",
        outline_input_format="stage_skeleton_v1",
        structure_input_format=REVIEWED_STRUCTURE_V1,
    )
    index = next(i for i, s in enumerate(pack["stage_blueprints"]) if s["stage_code"] == "A2")
    return {
        "goal": goal,
        "domain_pack": pack,
        "manifest": manifest,
        "run_id": "contract-fixture",
        "current_structure_index": index,
        "prefs_snapshot": {"language": "zh"},
    }


def valid(s):
    batch = s["manifest"]["structure_batches"][s["current_structure_index"]]
    return {
        "units": [
            {
                "title": "调用边界与失败证据",
                "node_keys": batch["node_keys"],
                "focus_refs": [allowed_teaching_focus(s, batch)[0]["ref"]],
                "objectives": ["解释工具契约并比较正常与受控失败分支"],
            }
        ]
    }


def test_marker_hashed_and_legacy_default_unchanged():
    s = state()
    from app.agent_workflows.planning_batches import manifest_is_intact

    assert manifest_is_intact(s["manifest"])
    s["manifest"].pop("structure_input_format")
    assert not manifest_is_intact(s["manifest"])
    assert "structure_input_format" not in freeze_manifest(s["domain_pack"], DEFAULT_BUDGET, "mock:contract")


def test_minimal_payload_and_canonical_reconstruction():
    s = state()
    b = s["manifest"]["structure_batches"][s["current_structure_index"]]
    p = structure_payload(s, b)
    assert p["_structure_input_format"] == REVIEWED_STRUCTURE_V1
    assert p["allowed_node_keys"] == b["node_keys"]
    assert not {"node_blueprints", "resources", "learning_guidance", "domain_pack", "manifest"} & set(p)
    raw = valid(s)
    assert not validate_presentation(raw, b, allowed_teaching_focus(s, b))
    entry = presentation_entry(raw, s, b)
    assert not validate_structure_batch(entry, b, s["domain_pack"])
    canonical = {n["stable_key"]: n for n in s["domain_pack"]["knowledge_blueprints"]}
    assert entry["nodes"] == [canonical[k] for k in b["node_keys"]]
    assert entry["units"][0]["stable_key"] == "unit." + b["stage_key"] + ".0"


@pytest.mark.parametrize(
    "mutation",
    ["unknown", "delete", "prerequisite", "scope", "acceptance", "partial", "node", "unit_identity"],
)
def test_malicious_response_fail_closed(mutation):
    s = state()
    b = s["manifest"]["structure_batches"][s["current_structure_index"]]
    raw = deepcopy(valid(s))
    if mutation == "unknown":
        raw["units"][0]["node_keys"].append("node.unknown")
    elif mutation == "delete":
        raw["units"][0]["node_keys"] = []
    elif mutation == "partial":
        raw = {"patch": {}}
    elif mutation == "node":
        raw["nodes"] = []
    elif mutation == "unit_identity":
        raw["units"][0]["stable_key"] = "unit.forged"
    else:
        raw["units"][0][mutation] = ["forged"]
    assert validate_presentation(raw, b, allowed_teaching_focus(s, b))
    entry = presentation_entry(raw, s, b)
    assert entry["nodes"] == [] and entry["units"] == [] and entry["relations"] == []


@pytest.mark.parametrize("mutation", ["marker_drop", "marker_unknown", "pack", "manifest"])
@pytest.mark.parametrize("phase", ["generate_structure_batch", "repair_batch"])
def test_frozen_tamper_never_dispatches(mutation, phase):
    s = state()
    b = s["manifest"]["structure_batches"][s["current_structure_index"]]
    s["structure_batches"] = [{}] * s["current_structure_index"] + [presentation_entry(valid(s), s, b)]
    s["repair_target"] = {
        "kind": "structure",
        "stage_key": b["stage_key"],
        "batch_index": s["current_structure_index"],
    }
    if mutation == "marker_drop":
        s["manifest"].pop("structure_input_format")
    elif mutation == "marker_unknown":
        s["manifest"]["structure_input_format"] = "unknown"
    elif mutation == "pack":
        s["domain_pack"]["knowledge_blueprints"][0]["scope"] = ["forged"]
    else:
        s["manifest"]["max_repairs"] = 9
    fake = FakeLLM({"planning.structure": lambda *_: valid(s), "planning.repair": lambda *_: valid(s)})
    delta = getattr(PlanningNodes(llm=fake, save_draft=lambda _: "unused"), phase)(s)
    assert delta["generation_errors"] and not fake.calls


def test_partial_repair_retains_complete_presentation_contract():
    s = state()
    b = s["manifest"]["structure_batches"][s["current_structure_index"]]
    index = s["current_structure_index"]
    s["structure_batches"] = [{}] * index + [presentation_entry({"units": []}, s, b)]
    s["repair_target"] = {"kind": "structure", "stage_key": b["stage_key"], "batch_index": index}
    s["structure_errors"] = ["original validator error"]
    captured = {}

    def handler(_, payload):
        captured.update(payload)
        return {"patch": {"units": valid(s)["units"]}}

    nodes = PlanningNodes(llm=FakeLLM({"planning.repair": handler}), save_draft=lambda _: "unused")
    s.update(nodes.repair_batch(s))
    assert s["repair_count"] == 1
    assert captured["_structure_input_format"] == REVIEWED_STRUCTURE_V1
    assert captured["batch"] == {"units": []}
    assert captured["errors"] == ["original validator error"]
    assert "nodes" not in captured["batch"] and "relations" not in captured["batch"]
    assert nodes.validate_structure_batch_node(s)["structure_errors"]


@pytest.mark.parametrize("phase", ["planning.structure", "planning.repair"])
def test_real_adapter_mock_wire_has_presentation_only_responsibilities(phase):
    import json

    import httpx
    from app.agent_workflows.planning_structure import STRUCTURE_SCHEMA
    from app.infrastructure.providers.openai_compatible import OpenAICompatibleLLM

    s = state()
    b = s["manifest"]["structure_batches"][s["current_structure_index"]]
    payload = structure_payload(s, b)
    if phase == "planning.repair":
        payload = {
            "_structure_input_format": REVIEWED_STRUCTURE_V1,
            "_structure_focus_format": FOCUS_FORMAT,
            "context": payload,
            "batch": {"units": []},
            "errors": ["units empty"],
            "target": {"kind": "structure"},
        }
    seen = {}

    def respond(request):
        seen.update(json.loads(request.content))
        return httpx.Response(
            200, json={"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(valid(s))}}]}
        )

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        provider = OpenAICompatibleLLM(
            base_url="https://api.deepseek.com/v1", api_key="synthetic", model="deepseek-flash", client=client
        )
        result = provider.generate_structured(
            purpose=phase,
            payload=payload,
            schema_name=STRUCTURE_SCHEMA,
            run_id="offline",
            attempt_id="offline",
        )
    assert result.payload == valid(s)
    wire = json.loads(seen["messages"][1]["content"])
    assert set(wire["field_shape"]) == {"units"}
    assert set(wire["field_shape"]["units"][0]) == {"title", "node_keys", "focus_refs", "objectives"}
    assert "complete learning routes" not in seen["messages"][0]["content"]
    assert "Add necessary branches" not in seen["messages"][0]["content"]
    assert "never a patch" in seen["messages"][0]["content"]
    assert sum(len(m["content"]) for m in seen["messages"]) < 15000
    assert seen["max_tokens"] == 8192
