"""Offline purpose/transport boundaries; not a real curriculum quality eval."""
import json

import httpx
import pytest
from app.application.planning_budget import BudgetPolicy
from app.infrastructure.providers.openai_compatible import OpenAICompatibleLLM
from app.ports.llm import LLMFailure, LLMResult

PURPOSE = "planning.curriculum_composition"
SCHEMA = "CurriculumPlanV1"


def test_curriculum_uses_existing_deployment_budget_and_non_thinking_mode():
    llm = OpenAICompatibleLLM(base_url="https://api.deepseek.com", api_key="offline-only", model="deepseek-flash",
                             budget_policy=BudgetPolicy(4096, 8192, 8192, 8192, 8192, 393216))
    options = llm.request_options(PURPOSE)
    assert options == {"model": "deepseek-flash", "max_tokens": 8192, "thinking": {"type": "disabled"}}


def test_curriculum_invalid_input_rejected_before_http():
    calls = []
    with httpx.Client(transport=httpx.MockTransport(lambda request: calls.append(request))) as client:
        llm = OpenAICompatibleLLM(base_url="https://provider.example", api_key="offline-only", model="test", client=client)
        result = llm.generate_structured(purpose=PURPOSE, payload={"raw_goal": "PRIVATE"}, schema_name=SCHEMA,
                                         run_id="offline", attempt_id="one")
    assert isinstance(result, LLMFailure) and result.error_class == "curriculum_input_invalid"
    assert result.details["dispatched"] is False and not calls


def fixtures():
    from backend.tests.unit.test_curriculum import context, output

    ctx = context()
    return ctx, output(ctx)


def response(document, *, finish="stop"):
    return httpx.Response(200, json={"model": "offline-model", "usage": {
        "prompt_tokens": 100, "completion_tokens": 40}, "choices": [{"finish_reason": finish,
        "message": {"content": json.dumps(document, ensure_ascii=False)}}]})


def run_provider(handler, payload):
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        llm = OpenAICompatibleLLM(base_url="https://api.deepseek.com", api_key="offline-only",
                                 model="deepseek-flash", client=client)
        return llm.generate_structured(purpose=PURPOSE, payload=payload, schema_name=SCHEMA,
                                       run_id="offline", attempt_id="single")


def test_complete_json_response_uses_only_dedicated_curriculum_protocol():
    ctx, document = fixtures()
    requests = []

    def handler(request):
        requests.append(json.loads(request.content))
        return response(document)

    result = run_provider(handler, ctx.to_payload())
    assert isinstance(result, LLMResult) and result.payload == document
    assert (result.input_tokens, result.output_tokens, result.finish_reason) == (100, 40, "stop")
    assert len(requests) == 1 and requests[0]["thinking"] == {"type": "disabled"}
    message = json.loads(requests[0]["messages"][1]["content"])
    assert message["purpose"] == PURPOSE and message["schema"] == SCHEMA
    assert message["context"] == ctx.to_payload() and "domain_pack" not in message
    system = requests[0]["messages"][0]["content"]
    assert "accepted_known" in system and "unresolved" in system and "ProjectStudy" in system
    assert "For planning.outline" not in system and "planning.repair" not in system


@pytest.mark.parametrize("fault,expected,unknown", [
    ("timeout", "provider_transport_unknown", True),
    ("server", "provider_server_unknown", True),
    ("truncated", "provider_output_truncated", False),
    ("invalid_json", "provider_invalid_json", False),
    ("invalid_contract", "curriculum_output_invalid", False),
])
def test_single_attempt_preserves_failure_and_never_echoes_model_payload(fault, expected, unknown):
    ctx, document = fixtures()
    calls = []

    def handler(request):
        calls.append(request)
        if fault == "timeout":
            raise httpx.ReadTimeout("PRIVATE_MODEL_TEXT", request=request)
        if fault == "server":
            return httpx.Response(503, text="PRIVATE_MODEL_TEXT")
        if fault == "truncated":
            return response(document, finish="length")
        if fault == "invalid_json":
            return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {
                "content": "PRIVATE_MODEL_TEXT{"}}]})
        return response({**document, "unauthorized": "PRIVATE_MODEL_TEXT"})

    result = run_provider(handler, ctx.to_payload())
    assert isinstance(result, LLMFailure) and result.error_class == expected
    assert result.dispatch_unknown is unknown and len(calls) == 1
    assert "PRIVATE_MODEL_TEXT" not in repr(result)


@pytest.mark.parametrize("change", ["schema", "extra", "input_hash", "source_hash"])
def test_curriculum_source_envelope_rejected_before_dispatch(change):
    ctx, _ = fixtures()
    payload = ctx.to_payload()
    schema = SCHEMA
    if change == "schema":
        schema = "CurriculumPlanV2"
    elif change == "extra":
        payload["raw_goal"] = "PRIVATE"
    elif change == "input_hash":
        payload["input_hash"] = "f" * 64
    else:
        payload["sources"]["capability_plan_hash"] = "f" * 64
    calls = []
    with httpx.Client(transport=httpx.MockTransport(lambda r: calls.append(r))) as client:
        llm = OpenAICompatibleLLM(base_url="https://provider.example", api_key="offline-only",
                                 model="test", client=client)
        result = llm.generate_structured(purpose=PURPOSE, payload=payload, schema_name=schema,
                                         run_id="offline", attempt_id="one")
    assert result.error_class == "curriculum_input_invalid" and not calls
    assert result.details["dispatched"] is False


def test_curriculum_obeys_lower_deployment_cap_and_other_endpoint_options():
    llm = OpenAICompatibleLLM(base_url="https://provider.example", api_key="offline-only", model="test",
                             budget_policy=BudgetPolicy(4096, 8192, 8192, 8192, 2048, 393216))
    assert llm.request_options(PURPOSE) == {"model": "test", "max_tokens": 2048}
