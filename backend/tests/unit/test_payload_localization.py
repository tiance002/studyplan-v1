"""Capture the real node dispatch and the provider's final HTTP message."""

import json

import httpx
import pytest
from app.agent_workflows.nodes import PlanningNodes
from app.agent_workflows.planning_batches import run_batched_planning_graph
from app.infrastructure.domain_pack import load_pack
from app.infrastructure.providers.openai_compatible import OpenAICompatibleLLM

from tests.helpers.batched_planning import OUTLINE, PRACTICE, REPAIR, STRUCTURE, ScriptedLLM

GOAL = "从零学习 Agent 应用开发，并完成一个可验收的知识库 Agent 项目"


@pytest.fixture(params=[
    ("agent-application-v1.json", 9, 27, 20),
    ("agent-knowledge-rag-v1.json", 10, 12, 22),
    ("agent-coding-v1.json", 10, 12, 22),
    ("agent-workflow-automation-v1.json", 10, 12, 22),
])
def curriculum_input(request):
    # This is a payload isolation regression, independent of evolving goal
    # routing. Retain the original large 27-node case and add all new inputs.
    filename, stages, nodes, repaired_calls = request.param
    return load_pack(filename), stages, nodes, repaired_calls


def _run(llm, pack):
    nodes = PlanningNodes(llm=llm, save_draft=lambda state: {"draft_ref": "d", "draft_hash": "h"})
    return run_batched_planning_graph(nodes, {"goal": GOAL, "run_id": "local", "domain_pack": pack})


def _assert_local(payload, pack, stage_key):
    serialized = json.dumps(payload, ensure_ascii=False)
    assert "domain_pack" not in payload
    for stage in pack["stage_blueprints"]:
        if stage["stable_key"] != stage_key:
            assert stage["stable_key"] not in serialized
    # Declared prerequisite keys may name external nodes, but their blueprints
    # and other stages' practice/resource context must never be retransmitted.
    context = payload.get("context", payload)
    assert context["stage"]["stable_key"] == stage_key
    if "node_blueprints" in context:
        own = next(s["node_keys"] for s in pack["stage_blueprints"] if s["stable_key"] == stage_key)
        assert {n["stable_key"] for n in context["node_blueprints"]} == set(own)
        assert context["required_unit_node_keys"] == own
        assert not set(context["required_unit_node_keys"]) & set(context["declared_external_prerequisite_keys"])
        expected_resources = next(s.get("resources", []) for s in pack["stage_blueprints"]
                                  if s["stable_key"] == stage_key)
        assert context["resources"] == expected_resources
    else:
        assert all(u["section_key"] == stage_key for u in context["structure"]["units"])
        assert context["practice_blueprint"]["section_key"] == stage_key


def test_outline_dispatch_preserves_complete_stage_and_node_catalog(curriculum_input):
    pack, expected_stages, expected_nodes, _ = curriculum_input
    llm = ScriptedLLM(pack)
    trace = _run(llm, pack)
    assert trace.stopped_at == "await_approval"
    call = llm.calls[0]
    assert call["purpose"] == OUTLINE
    assert len(call["payload"]["domain_pack"]["stage_blueprints"]) == expected_stages
    assert len(call["payload"]["manifest"]["required_node_keys"]) == expected_nodes


@pytest.mark.parametrize("purpose", [STRUCTURE, PRACTICE])
def test_all_final_batch_dispatches_are_stage_local(purpose, curriculum_input):
    pack, expected_stages, _, _ = curriculum_input
    llm = ScriptedLLM(pack)
    trace = _run(llm, pack)
    assert trace.stopped_at == "await_approval"
    calls = [c for c in llm.calls if c["purpose"] == purpose]
    assert len(calls) == expected_stages
    for call in calls:
        _assert_local(call["payload"], pack, call["payload"]["stage"]["stable_key"])


@pytest.mark.parametrize("invalid_purpose", [STRUCTURE, PRACTICE])
def test_repair_dispatch_contains_only_failed_batch_and_local_context(invalid_purpose, curriculum_input):
    pack, _, _, _ = curriculum_input
    llm = ScriptedLLM(pack, invalid_at=(invalid_purpose, 1))
    trace = _run(llm, pack)
    assert trace.stopped_at == "await_approval"
    repair = next(c["payload"] for c in llm.calls if c["purpose"] == REPAIR)
    stage_key = pack["stage_blueprints"][0]["stable_key"]
    _assert_local(repair, pack, stage_key)
    assert repair["errors"]
    assert repair["batch"]
    assert set(repair["manifest"]) <= {"protocol", "manifest_hash", "pack_hash", "max_repairs"}


@pytest.mark.parametrize("purpose", [STRUCTURE, PRACTICE, REPAIR])
def test_provider_never_injects_constructor_pack_into_http_body(purpose, curriculum_input):
    pack, _, _, _ = curriculum_input
    requests = []

    def reply(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}]})

    with httpx.Client(transport=httpx.MockTransport(reply)) as client:
        llm = OpenAICompatibleLLM(base_url="https://provider.example", api_key="mock", model="mock",
                                  client=client, domain_pack=pack)
        llm.generate_structured(purpose=purpose, payload={"stage": {"stable_key": "stage.only"}},
                                schema_name="KnowledgeStructureV1", run_id="r", attempt_id="a")
    message = json.loads(requests[0]["messages"][1]["content"])
    assert "domain_pack" not in message
    assert message["context"] == {"stage": {"stable_key": "stage.only"}}
    assert all(s["stable_key"] not in json.dumps(message) for s in pack["stage_blueprints"])


@pytest.mark.parametrize("invalid_purpose", [STRUCTURE, PRACTICE])
def test_graph_through_provider_http_preserves_local_scope_and_repair_shape(invalid_purpose, curriculum_input):
    pack, _, _, expected_calls = curriculum_input
    fake = ScriptedLLM(pack, invalid_at=(invalid_purpose, 1))
    messages = []

    def reply(request):
        body = json.loads(request.content)
        message = json.loads(body["messages"][1]["content"])
        messages.append(message)
        context = dict(message["context"])
        if "domain_pack" in message:
            context["domain_pack"] = message["domain_pack"]
        result = fake.generate_structured(purpose=message["purpose"], payload=context,
                                         schema_name=message["schema"], run_id="local", attempt_id="http")
        return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {
            "content": json.dumps(result.payload, ensure_ascii=False),
        }}]})

    with httpx.Client(transport=httpx.MockTransport(reply)) as client:
        llm = OpenAICompatibleLLM(base_url="https://provider.example", api_key="mock", model="mock",
                                  client=client, domain_pack=pack)
        trace = _run(llm, pack)
    assert trace.stopped_at == "await_approval"
    assert len(messages) == expected_calls
    assert messages[0]["domain_pack"] == pack
    for message in messages[1:]:
        assert "domain_pack" not in message
        context = message["context"]
        key = context["target"]["stage_key"] if message["purpose"] == REPAIR else context["stage"]["stable_key"]
        _assert_local(context, pack, key)
        if message["purpose"] == REPAIR:
            assert "practice_proposal" not in message["field_shape"]
            assert ("tasks" in message["field_shape"]) == (invalid_purpose == PRACTICE)
