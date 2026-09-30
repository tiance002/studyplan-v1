import json

import httpx
from app.agent_workflows.validators import validate_plan_structure
from app.application.planning_budget import BudgetPolicy
from app.infrastructure.providers.openai_compatible import OpenAICompatibleLLM
from app.ports.llm import LLMFailure, LLMResult


def test_real_provider_protocol_and_timeout():
    calls = []
    def reply(request):
        calls.append(request)
        return httpx.Response(200, json={"model":"test-model", "choices":[{"message":{"content":'{"sections":[],"outline_ref":"o"}'},"finish_reason":"stop"}], "usage":{"prompt_tokens":10,"completion_tokens":4}})
    budget = BudgetPolicy(4096,8192,4096,8192,8192,393216)
    llm = OpenAICompatibleLLM(base_url="https://provider.example/v1", api_key="test", model="test-model", budget_policy=budget, client=httpx.Client(transport=httpx.MockTransport(reply)))
    result = llm.generate_structured(purpose="planning.outline", payload={"goal":"Python"}, schema_name="PlanOutlineV1", run_id="r", attempt_id="a")
    assert isinstance(result, LLMResult)
    assert result.input_tokens == 10 and result.output_tokens == 4
    assert calls[0].url.path == "/v1/chat/completions"
    assert calls[0].headers["Authorization"] == "Bearer test"
    def timeout(request):
        raise httpx.ReadTimeout("outcome unknown")
    llm = OpenAICompatibleLLM(base_url="https://provider.example/v1", api_key="test", model="test-model", budget_policy=budget, client=httpx.Client(transport=httpx.MockTransport(timeout)))
    result = llm.generate_structured(purpose="planning.outline", payload={}, schema_name="PlanOutlineV1", run_id="r", attempt_id="a")
    assert isinstance(result, LLMFailure) and result.dispatch_unknown and not result.retryable


def test_transport_failure_records_exception_type_without_leaking_or_retrying():
    api_key = "test-secret-api-key"
    requests = []

    def fail_transport(request):
        requests.append(request)
        raise httpx.ReadError(f"failed Authorization: Bearer {api_key}")

    with httpx.Client(transport=httpx.MockTransport(fail_transport)) as client:
        llm = OpenAICompatibleLLM(base_url="https://provider.example", api_key=api_key,
                                  model="test-model", client=client)
        result = llm.generate_structured(purpose="planning.structure", payload={},
                                         schema_name="KnowledgeStructureV1", run_id="r", attempt_id="a")

    assert isinstance(result, LLMFailure)
    assert result.error_class == "provider_transport_unknown"
    assert result.dispatch_unknown is True
    assert result.retryable is False
    assert result.details["transport_exception_type"] == "ReadError"
    assert len(requests) == 1
    safe_diagnostics = json.dumps(result.details)
    assert api_key not in safe_diagnostics
    assert "Authorization" not in safe_diagnostics


def test_structure_and_repair_prompt_define_valid_relation_contract():
    import json
    contexts = []
    def reply(request):
        contexts.append(json.loads(json.loads(request.content)["messages"][1]["content"]))
        return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}]})
    budget = BudgetPolicy(4096,8192,4096,8192,8192,393216)
    llm = OpenAICompatibleLLM(base_url="https://provider.example",api_key="test",model="test", budget_policy=budget,
                              client=httpx.Client(transport=httpx.MockTransport(reply)))
    for purpose in ("planning.structure", "planning.repair"):
        llm.generate_structured(purpose=purpose,payload={},schema_name="KnowledgeStructureV1",run_id="r",attempt_id=purpose)
    for context in contexts:
        relations = context["field_shape"]["relations"]
        assert relations
        keys = {item[key] for item in relations for key in ("from_stable_key", "to_stable_key")}
        outcome = validate_plan_structure(nodes=[{"stable_key":key} for key in keys],
                                           units=[],relations=relations,tasks=[])
        assert outcome.errors == []


def test_injected_purpose_policy_sets_actual_http_output_budget():
    requests = []
    budget = BudgetPolicy(3072, 7168, 2048, 6144, 8192, 16384)

    def reply(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={"model": "other", "choices": [{
            "message": {"content": '{"outline_ref":"o","sections":[{"stable_key":"s"}]}'},
            "finish_reason": "stop",
        }], "usage": {"prompt_tokens": 3, "completion_tokens": 2}})

    with httpx.Client(transport=httpx.MockTransport(reply)) as client:
        llm = OpenAICompatibleLLM(base_url="https://provider.example", api_key="mock", model="other",
                                  budget_policy=budget, client=client)
        for purpose in ("planning.outline", "planning.structure", "planning.practice", "planning.repair"):
            llm.generate_structured(purpose=purpose, payload={}, schema_name="test", run_id="r", attempt_id=purpose)

    assert [body["max_tokens"] for body in requests] == [3072, 7168, 2048, 6144]


def test_success_with_missing_usage_keeps_unknown_values_null():
    budget = BudgetPolicy(4096,8192,4096,8192,8192,16384)
    body = {"outline_ref": "o", "sections": [{"stable_key": "stage.a"}]}
    response = httpx.Response(200, json={"model": "explicit-model", "choices": [{
        "message": {"content": json.dumps(body)}, "finish_reason": "stop",
    }]})
    with httpx.Client(transport=httpx.MockTransport(lambda request: response)) as client:
        llm = OpenAICompatibleLLM(base_url="https://provider.example", api_key="mock", model="explicit-model",
                                  budget_policy=budget, client=client)
        result = llm.generate_structured(purpose="planning.outline", payload={}, schema_name="test",
                                         run_id="r", attempt_id="a")
    assert isinstance(result, LLMResult)
    assert result.input_tokens is None
    assert result.output_tokens is None
    assert result.cost_micros is None
    assert result.diagnostics["max_tokens"] == 4096
    assert result.diagnostics["requested_model"] == "explicit-model"
