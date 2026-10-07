"""Item 1 exercises the existing transport with simulated HTTP only."""
import json

import httpx
import pytest
from app.application.planning_budget import BudgetPolicy
from app.core.errors import ValidationAppError
from app.infrastructure.providers.openai_compatible import OpenAICompatibleLLM
from app.ports.llm import LLMFailure, LLMNotDispatchedError, LLMResult

PURPOSE = "planning.goal_requirement_analysis"
SCHEMA = "GoalRequirementProfileV1"


def goal():
    return dict(target="做只读 Code Review Agent", scope=["PR review"], desired_depth="applied",
                starting_point="我会 Python", outcome_purpose="interview", constraints=["只读"],
                project_context="已有旅行 Agent")


def output():
    return dict(schema_version=1, target_summary="代码审查", required_requirements=[
        dict(text="Review 结论关联代码依据", origin="inferred_required", source_refs=["goal.target"], rationale="Review 需有依据")],
        hard_constraints=[dict(text="只读", source_refs=["goal.constraints[0]"])],
        learner_claims=[dict(text="会 Python", source_refs=["goal.starting_point"])],
        clarification_questions=[], status="ready")


def invoke(handler, *, payload=None, schema=SCHEMA, guard=None, policy=None):
    calls = []

    def respond(request):
        calls.append(request)
        return handler(request)

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        llm = OpenAICompatibleLLM(base_url="https://provider.example/v1", api_key="test-secret",
            model="test-model", client=client, endpoint_guard=guard, budget_policy=policy)
        result = llm.generate_structured(purpose=PURPOSE, payload={"goal": goal()} if payload is None else payload,
                                        schema_name=schema, run_id="test-run", attempt_id="test-attempt")
    return result, calls, llm


def response(content=None, finish="stop", usage=True):
    body = dict(model="resolved-test", choices=[dict(message=dict(content=json.dumps(output(), ensure_ascii=False)
                if content is None else content), finish_reason=finish)])
    if usage:
        body["usage"] = dict(prompt_tokens=17, completion_tokens=29)
    return httpx.Response(200, json=body)


def test_new_purpose_uses_isolated_prompt_shape_and_goal_context():
    result, calls, llm = invoke(lambda request: response())
    assert isinstance(result, LLMResult)
    assert result.payload == output()
    assert len(calls) == 1
    body = json.loads(calls[0].content)
    assert body["response_format"] == {"type": "json_object"}
    system = body["messages"][0]["content"]
    for forbidden in ("complete, actionable learning routes", "node_blueprint", "Resource role must", "PracticeProposalV1"):
        assert forbidden not in system
    for required in ("inferred_required", "outcome_purpose", "learner_claims", "source_refs", "project_context"):
        assert required in system
    assert "结构化goal.constraints每项必须原文记录为hard_constraints并引用相应goal.constraints[i]" in system
    message = json.loads(body["messages"][1]["content"])
    assert message["purpose"] == PURPOSE and message["schema"] == SCHEMA
    assert message["context"] == {"goal": goal()}
    assert set(message["field_shape"]) == set(output())
    assert "profile_hash" not in message["field_shape"]
    assert "requirement_id" not in message["field_shape"]["required_requirements"][0]
    assert result.input_tokens == 17 and result.output_tokens == 29
    assert llm.prompt_version == "v2-g2-v8-resource-roles"


@pytest.mark.parametrize("payload,schema", [
    ({"goal": goal()}, "PlanOutlineV1"),
    ({"goal": goal(), "domain_pack": {}}, SCHEMA),
    ({"goal": goal(), "_outline_input_format": "stage_skeleton_v1"}, SCHEMA),
    ({"goal": goal(), "_structure_input_format": "anything"}, SCHEMA),
    ({"goal": {**goal(), "stage_blueprints": []}}, SCHEMA),
    ({"goal": {**goal(), "target": ""}}, SCHEMA),
    ({"goal": {**goal(), "target": "x" * 2001}}, SCHEMA),
    ({"goal": {**goal(), "scope": "bad"}}, SCHEMA),
    ({"goal": {**goal(), "desired_depth": []}}, SCHEMA),
    ({"goal": {**goal(), "project_context": 123}}, SCHEMA),
    ({"goal": {"target": "incomplete"}}, SCHEMA),
    ({"goal": []}, SCHEMA),
    ({}, SCHEMA),
])
def test_invalid_contract_is_rejected_before_http(payload, schema):
    result, calls, _ = invoke(lambda request: pytest.fail("must not dispatch"), payload=payload, schema=schema)
    assert isinstance(result, LLMFailure)
    assert result.error_class == "goal_requirement_input_invalid"
    assert result.details["dispatched"] is False
    assert calls == []


def test_existing_caps_bound_new_purpose_without_changing_global_policy():
    policy = BudgetPolicy(90, 90, 80, 90, 70, 60)
    result, calls, _ = invoke(lambda request: response(), policy=policy)
    assert isinstance(result, LLMResult)
    assert json.loads(calls[0].content)["max_tokens"] == 60


@pytest.mark.parametrize("content,finish,error", [
    ('{"schema_version":', "stop", "provider_invalid_json"),
    ('```json\n{}\n```', "stop", "provider_invalid_json"),
    ('[]', "stop", "provider_invalid_shape"),
    ('{}', "stop", "provider_invalid_shape"),
    ('{"schema_version":', "length", "provider_output_truncated"),
    (json.dumps(output()), "length", "provider_output_truncated"),
])
def test_known_response_failures_do_not_retry_or_repair(content, finish, error):
    result, calls, _ = invoke(lambda request: response(content, finish))
    assert isinstance(result, LLMFailure) and result.error_class == error
    assert not result.dispatch_unknown and not result.retryable
    assert result.input_tokens == 17 and result.output_tokens == 29
    assert len(calls) == 1
    assert "known_failed_attempt" not in result.details


@pytest.mark.parametrize("status,error,unknown", [
    (503, "provider_server_unknown", True), (401, "provider_http_rejected", False),
])
def test_http_failure_boundary(status, error, unknown):
    result, calls, _ = invoke(lambda request: httpx.Response(status))
    assert isinstance(result, LLMFailure) and result.error_class == error
    assert result.dispatch_unknown is unknown and not result.retryable
    assert len(calls) == 1


def test_transport_unknown_does_not_leak_or_retry():
    def fail(request):
        raise httpx.ReadTimeout("Bearer test-secret private input")
    result, calls, _ = invoke(fail)
    assert isinstance(result, LLMFailure) and result.error_class == "provider_transport_unknown"
    assert result.dispatch_unknown and not result.retryable and len(calls) == 1
    assert "test-secret" not in json.dumps(result.details)


@pytest.mark.parametrize("body", [[], {}, {"choices": []}, {"choices": [{"message": {}}]}])
def test_invalid_response_envelope_is_known_failure(body):
    result, calls, _ = invoke(lambda request: httpx.Response(200, json=body))
    assert isinstance(result, LLMFailure) and result.error_class == "provider_invalid_envelope"
    assert not result.dispatch_unknown and not result.retryable and len(calls) == 1


def test_endpoint_rejection_preserves_not_dispatched_exception():
    def reject(url):
        raise ValidationAppError("reject endpoint")
    with pytest.raises(LLMNotDispatchedError):
        invoke(lambda request: pytest.fail("must not dispatch"), guard=reject)


def test_transport_preserves_business_extras_for_server_validator_and_null_usage():
    wire = {**output(), "unexpected_business_field": "reject downstream"}
    result, calls, _ = invoke(lambda request: response(json.dumps(wire), usage=False))
    assert isinstance(result, LLMResult) and result.payload == wire
    assert result.input_tokens is None and result.output_tokens is None
    assert len(calls) == 1


def test_empty_optional_project_context_is_supported():
    data = goal()
    del data["project_context"]
    result, calls, _ = invoke(lambda request: response(), payload={"goal": data})
    assert isinstance(result, LLMResult)
    assert json.loads(json.loads(calls[0].content)["messages"][1]["content"])["context"] == {"goal": data}
