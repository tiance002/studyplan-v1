import httpx
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
