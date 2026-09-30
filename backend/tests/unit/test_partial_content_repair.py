"""Valid partial JSON travels through the HTTP provider into bounded repair."""

import json
from copy import deepcopy

import httpx
import pytest
from app.agent_workflows.nodes import PlanningNodes
from app.agent_workflows.planning_batches import run_batched_planning_graph
from app.infrastructure.domain_pack import select_domain_pack
from app.infrastructure.providers.openai_compatible import OpenAICompatibleLLM
from app.ports.llm import LLMFailure

from tests.helpers.batched_planning import PRACTICE, REPAIR, STRUCTURE, ScriptedLLM

GOAL = "从 Python 基础开始学习 Agent 应用开发"


@pytest.mark.parametrize("purpose,field", [
    (STRUCTURE, "nodes"), (STRUCTURE, "units"), (STRUCTURE, "relations"),
    (PRACTICE, "stable_key"), (PRACTICE, "title"), (PRACTICE, "idea"),
    (PRACTICE, "tasks"), (PRACTICE, "task_knowledge_links"),
])
@pytest.mark.parametrize("persistent", [False, True])
def test_partial_object_is_preserved_and_repaired_within_shared_cap(purpose, field, persistent):
    pack = select_domain_pack(GOAL)
    fake = ScriptedLLM(pack)
    messages = []
    dispatches = []
    partial = None

    def reply(request):
        nonlocal partial
        message = json.loads(json.loads(request.content)["messages"][1]["content"])
        messages.append(message)
        result = fake.generate_structured(purpose=message["purpose"], payload=message["context"],
                                          schema_name="mock", run_id="offline", attempt_id=str(len(messages)))
        produced = deepcopy(result.payload)
        if (message["purpose"] == purpose and fake.count(purpose) == 1) or (
            persistent and message["purpose"] == REPAIR
        ):
            produced.pop(field)
            partial = deepcopy(produced)
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(produced)},
                                                     "finish_reason": "stop"}]})

    class Capture:
        def generate_structured(self, **kwargs):
            dispatches.append(kwargs)
            return provider.generate_structured(**kwargs)

    with httpx.Client(transport=httpx.MockTransport(reply)) as client:
        provider = OpenAICompatibleLLM(base_url="https://provider.example", api_key="offline", model="mock",
                                      client=client)
        nodes = PlanningNodes(llm=Capture(), save_draft=lambda state: {"draft_ref": "d", "draft_hash": "h"})
        trace = run_batched_planning_graph(nodes, {"goal": GOAL, "run_id": "offline", "domain_pack": pack})

    repairs = [m for m in messages if m["purpose"] == REPAIR]
    assert len(repairs) == (2 if persistent else 1)
    assert trace.stopped_at == ("failed" if persistent else "await_approval")
    assert len(messages) <= 21
    if not persistent:
        assert len(messages) == 20
    schema = "KnowledgeStructureV1" if purpose == STRUCTURE else "PracticeProposalV1"
    for repair in repairs:
        local = repair["context"]
        assert field not in local["batch"]
        original = {k: v for k, v in local["batch"].items() if k not in {"stage_key", "batch_index"}}
        assert original == partial
        stage = local["target"]["stage_key"]
        assert local["context"]["stage"]["stable_key"] == stage
        assert f"{schema} 缺少必需字段：{field}（{stage}）" in local["errors"]
        assert repair["schema"] == schema
        assert local["manifest"]["max_repairs"] == 2
    ids = [c["attempt_id"] for c in dispatches]
    assert len(ids) == len(set(ids))
    assert all("b3f2-batch-v1" in identity for identity in ids)
    assert [c["attempt_id"].rsplit(":", 1)[-1] for c in dispatches if c["purpose"] == REPAIR] == (
        ["1", "2"] if persistent else ["1"]
    )


@pytest.mark.parametrize("content,finish,error", [
    ('{"nodes":', "stop", "provider_invalid_json"),
    ('{}', "length", "provider_output_truncated"),
    ('[]', "stop", "provider_invalid_shape"),
])
def test_provider_failures_still_stop_without_content_repair(content, finish, error):
    pack = select_domain_pack(GOAL)
    fake = ScriptedLLM(pack)
    requests = []

    def reply(request):
        requests.append(request)
        if len(requests) == 1:
            context = json.loads(json.loads(request.content)["messages"][1]["content"])["context"]
            body = json.dumps(fake._skeleton(context))
            reason = "stop"
        else:
            body, reason = content, finish
        return httpx.Response(200, json={"choices": [{"message": {"content": body}, "finish_reason": reason}]})

    class Capture:
        def generate_structured(self, **kwargs):
            result = provider.generate_structured(**kwargs)
            if isinstance(result, LLMFailure):
                assert result.error_class == error
                assert result.retryable is False
            return result

    with httpx.Client(transport=httpx.MockTransport(reply)) as client:
        provider = OpenAICompatibleLLM(base_url="https://provider.example", api_key="offline", model="mock",
                                      client=client)
        nodes = PlanningNodes(llm=Capture(), save_draft=lambda state: {})
        trace = run_batched_planning_graph(nodes, {"goal": GOAL, "run_id": "offline", "domain_pack": pack})
    assert trace.stopped_at == "failed"
    assert len(requests) == 2
    assert trace.state.get("repair_count", 0) == 0


def test_rag_object_missing_all_three_fields_reaches_local_repair_without_unwrapping():
    pack = select_domain_pack(GOAL)

    class PartialRag(ScriptedLLM):
        def _structure(self, payload):
            full = super()._structure(payload)
            if payload["stage"]["stable_key"] == "stage.rag" and self.count(REPAIR) == 0:
                return {"nested_content": full}
            return full

    fake = PartialRag(pack)
    nodes = PlanningNodes(llm=fake, save_draft=lambda state: {"draft_ref": "d", "draft_hash": "h"})
    trace = run_batched_planning_graph(nodes, {"goal": GOAL, "run_id": "offline", "domain_pack": pack})
    assert trace.stopped_at == "await_approval"
    assert fake.count() == 20
    repair = next(c for c in fake.calls if c["purpose"] == REPAIR)
    local = repair["payload"]
    assert local["target"]["stage_key"] == "stage.rag"
    assert "nested_content" in local["batch"]
    for field in ("nodes", "units", "relations"):
        assert field not in local["batch"]
        assert f"KnowledgeStructureV1 缺少必需字段：{field}（stage.rag）" in local["errors"]
