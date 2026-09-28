import httpx
from app.agent_workflows.validators import validate_plan_structure
from app.infrastructure.providers.openai_compatible import OpenAICompatibleLLM
from app.ports.llm import LLMFailure, LLMResult


def test_real_provider_protocol_and_timeout():
    calls = []
    def reply(request):
        calls.append(request)
        return httpx.Response(200, json={"model":"test-model", "choices":[{"message":{"content":'{"sections":[],"outline_ref":"o"}'},"finish_reason":"stop"}], "usage":{"prompt_tokens":10,"completion_tokens":4}})
    llm = OpenAICompatibleLLM(base_url="https://provider.example/v1", api_key="test", model="test-model", client=httpx.Client(transport=httpx.MockTransport(reply)))
    result = llm.generate_structured(purpose="planning.outline", payload={"goal":"Python"}, schema_name="PlanOutlineV1", run_id="r", attempt_id="a")
    assert isinstance(result, LLMResult)
    assert result.input_tokens == 10 and result.output_tokens == 4
    assert calls[0].url.path == "/v1/chat/completions"
    assert calls[0].headers["Authorization"] == "Bearer test"
    def timeout(request):
        raise httpx.ReadTimeout("outcome unknown")
    llm = OpenAICompatibleLLM(base_url="https://provider.example/v1", api_key="test", model="test-model", client=httpx.Client(transport=httpx.MockTransport(timeout)))
    result = llm.generate_structured(purpose="planning.outline", payload={}, schema_name="PlanOutlineV1", run_id="r", attempt_id="a")
    assert isinstance(result, LLMFailure) and result.dispatch_unknown and not result.retryable


def test_structure_and_repair_prompt_define_valid_relation_contract():
    import json
    contexts = []
    def reply(request):
        contexts.append(json.loads(json.loads(request.content)["messages"][1]["content"]))
        return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}]})
    llm = OpenAICompatibleLLM(base_url="https://provider.example",api_key="test",model="test",
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
