"""Observed parent omissions remain rejected; the generation contract names them."""

import json
from pathlib import Path

import httpx
import pytest
from app.agent_workflows.planning_batches import (
    DEFAULT_BUDGET,
    freeze_manifest,
    structure_payload,
    validate_structure_batch,
)
from app.infrastructure.domain_pack import load_pack
from app.infrastructure.providers.openai_compatible import OpenAICompatibleLLM
from app.ports.llm import LLMResult

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "b3f2_run06_unit_coverage.json"


@pytest.mark.parametrize("stage", ["stage.tools", "stage.rag", "stage.context"])
@pytest.mark.parametrize("purpose", ["planning.structure", "planning.repair"])
def test_http_contract_requires_frozen_parent_coverage_and_never_silently_attaches(stage, purpose):
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    original = data["original"][stage]
    pack = load_pack("agent-application-v1.json")
    manifest = freeze_manifest(pack, DEFAULT_BUDGET, "mock")
    spec = next(b for b in manifest["structure_batches"] if b["stage_key"] == stage)
    context = structure_payload({"manifest": manifest, "domain_pack": pack}, spec)
    parent = "node." + stage.removeprefix("stage.")
    assert parent in context["required_unit_node_keys"]
    assert context["required_unit_node_keys"] == spec["node_keys"]
    assert not set(context["required_unit_node_keys"]) & set(spec["declared_external_prerequisite_keys"])
    errors = validate_structure_batch(original, spec, pack)
    assert errors == [f"结构批次知识节点未关联到学习单元：{parent}（{stage}）"]
    payload = context if purpose == "planning.structure" else {
        "target": {"kind": "structure", "stage_key": stage},
        "batch": original, "errors": errors, "context": context,
    }
    requests = []

    def reply(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {
            "content": json.dumps(original),
        }}]})

    with httpx.Client(transport=httpx.MockTransport(reply)) as client:
        provider = OpenAICompatibleLLM(base_url="https://provider.example", api_key="mock", model="mock",
                                      client=client)
        result = provider.generate_structured(purpose=purpose, payload=payload, schema_name="KnowledgeStructureV1",
                                              run_id="offline", attempt_id="offline")
    assert len(requests) == 1
    system = requests[0]["messages"][0]["content"]
    assert "Every emitted node, including parent/skill nodes" in system
    assert "contains relations do not satisfy unit coverage" in system
    message = json.loads(requests[0]["messages"][1]["content"])
    sent = message["context"] if purpose == "planning.structure" else message["context"]["context"]
    assert sent["required_unit_node_keys"] == spec["node_keys"]
    assert isinstance(result, LLMResult)
    assert result.payload == original  # No synthetic unit or injected node association.
    assert validate_structure_batch(result.payload, spec, pack) == errors


@pytest.mark.parametrize("stage", ["stage.tools", "stage.rag"])
def test_retained_successful_repairs_restore_coverage_without_changing_relations(stage):
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    pack = load_pack("agent-application-v1.json")
    manifest = freeze_manifest(pack, DEFAULT_BUDGET, "mock")
    spec = next(b for b in manifest["structure_batches"] if b["stage_key"] == stage)
    original, repaired = data["original"][stage], data["repaired"][stage]
    assert validate_structure_batch(repaired, spec, pack) == []
    assert repaired["nodes"] == original["nodes"]
    assert repaired["relations"] == original["relations"]


def test_generic_stage_does_not_invent_frozen_node_inventory():
    pack = {"resource_support": "search_only"}
    manifest = freeze_manifest(pack, DEFAULT_BUDGET, "mock")
    context = structure_payload({"manifest": manifest, "domain_pack": pack}, manifest["structure_batches"][0])
    assert context["required_unit_node_keys"] == []
