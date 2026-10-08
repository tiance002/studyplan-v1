"""Item 2 uses the shared transport with offline HTTP simulation only."""
import json

import httpx
import pytest
from app.application.planning_budget import BudgetPolicy
from app.domain.planning.goal_requirements import GoalRequirementProfileValidator
from app.domain.planning.intent import GoalSpec
from app.infrastructure.providers.openai_compatible import OpenAICompatibleLLM
from app.ports.llm import LLMFailure, LLMResult

PURPOSE = "planning.capability_planning"
SCHEMA = "CapabilityPlanV1"


def valid_payload():
    from app.domain.planning.capability_policy import CAPABILITY_POLICY

    profile = GoalRequirementProfileValidator().validate(dict(
        schema_version=1, target_summary="实现严格JSON输出", required_requirements=[dict(
            text="实现严格JSON输出", origin="explicit", source_refs=["goal.target"], rationale="")],
        hard_constraints=[], learner_claims=[], clarification_questions=[], status="ready"),
        goal=GoalSpec(target="实现严格JSON输出"))
    return {"profile": profile.to_payload(), "policy": CAPABILITY_POLICY.to_payload(), "verification_evidence": []}


def output(payload):
    return dict(schema_version=1, source_goal_profile_hash=payload["profile"]["profile_hash"],
                policy_version=payload["policy"]["policy_version"], route_kind="narrow_goal", status="ready",
                capabilities=[], claim_bindings=[], constraint_effects=[], clarification_questions=[])


def response(content, finish="stop", usage=True):
    body = dict(model="resolved-test", choices=[dict(message=dict(content=content), finish_reason=finish)])
    if usage:
        body["usage"] = dict(prompt_tokens=17, completion_tokens=29)
    return httpx.Response(200, json=body)


def invoke(handler, *, payload, schema=SCHEMA, policy=None):
    calls = []

    def respond(request):
        calls.append(request)
        return handler(request)

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        llm = OpenAICompatibleLLM(base_url="https://provider.example/v1", api_key="test-secret",
            model="test-model", client=client, budget_policy=policy)
        result = llm.generate_structured(purpose=PURPOSE, payload=payload,
                                        schema_name=schema, run_id="item2-run", attempt_id="item2-attempt")
    return result, calls, llm


@pytest.mark.parametrize("payload,schema", [
    ({}, SCHEMA),
    ({"profile": {}, "policy": {}, "verification_evidence": []}, "PlanOutlineV1"),
    ({"goal": {"target": "raw goal"}}, SCHEMA),
    ({"profile": {}, "policy": {}, "verification_evidence": [], "domain_pack": {}}, SCHEMA),
    ({"profile": {}, "policy": {}, "verification_evidence": [], "_outline_input_format": "stage_skeleton_v1"}, SCHEMA),
])
def test_invalid_input_rejected_before_http(payload, schema):
    result, calls, _ = invoke(lambda request: pytest.fail("must not dispatch"), payload=payload, schema=schema)
    assert isinstance(result, LLMFailure)
    assert result.error_class == "capability_planning_input_invalid"
    assert result.details["dispatched"] is False
    assert calls == []


def test_new_purpose_uses_existing_minimum_budget():
    llm = OpenAICompatibleLLM(base_url="https://provider.example/v1", api_key="unused", model="test-model",
                             budget_policy=BudgetPolicy(90, 90, 80, 90, 70, 60))
    assert llm.request_options(PURPOSE)["max_tokens"] == 60


def test_actual_wire_isolates_system_shape_and_profile_context():
    payload = valid_payload()
    wire = output(payload)
    result, calls, llm = invoke(lambda request: response(json.dumps(wire)), payload=payload)
    assert isinstance(result, LLMResult) and result.payload == wire
    assert len(calls) == 1
    body = json.loads(calls[0].content)
    assert body["response_format"] == {"type": "json_object"}
    system = body["messages"][0]["content"]
    for forbidden in ("complete, actionable learning routes", "node_blueprint", "Resource role must", "PracticeProposalV1",
                      "你仅执行 Goal Requirement Analysis"):
        assert forbidden not in system
    for required in ("accepted_known", "needs_learning", "learning_requirement", "project_usage", "needs_verification",
                     "systematic_agent_route", "claim_bindings", "constraint_effects", "not_applicable"):
        assert required in system
    message = json.loads(body["messages"][1]["content"])
    assert message["purpose"] == PURPOSE and message["schema"] == SCHEMA
    assert message["context"] == payload
    assert set(message["field_shape"]) == set(wire)
    item_shape = message["field_shape"]["capabilities"][0]
    assert "title" not in item_shape and "learning_outcomes" not in item_shape
    assert result.input_tokens == 17 and result.output_tokens == 29
    assert llm.prompt_version == "v2-g2-v8-resource-roles"


@pytest.mark.parametrize("field,value", [
    ("raw_goal", "raw input"), ("goal_spec", {}), ("domain_pack", {}),
    ("_structure_input_format", "anything"), ("business_task", {}),
])
def test_extra_inputs_cannot_bypass_shared_preflight(field, value):
    payload = valid_payload() | {field: value}
    result, calls, _ = invoke(lambda request: pytest.fail("must not dispatch"), payload=payload)
    assert isinstance(result, LLMFailure) and result.error_class == "capability_planning_input_invalid"
    assert result.details["dispatched"] is False and calls == []


@pytest.mark.parametrize("field,value", [("profile_hash", "bad"), ("status", "needs_clarification"), ("raw_goal", "bad")])
def test_invalid_profile_rejected_before_http(field, value):
    payload = valid_payload()
    payload["profile"][field] = value
    result, calls, _ = invoke(lambda request: pytest.fail("must not dispatch"), payload=payload)
    assert isinstance(result, LLMFailure) and result.error_class == "capability_planning_input_invalid"
    assert calls == []


@pytest.mark.parametrize("content,finish,error", [
    ('{"schema_version":', "stop", "provider_invalid_json"),
    ('```json\n{}\n```', "stop", "provider_invalid_json"),
    ('[]', "stop", "provider_invalid_shape"),
    ('{}', "stop", "provider_invalid_shape"),
    ('{"schema_version":', "length", "provider_output_truncated"),
])
def test_known_response_failure_keeps_usage_and_never_repairs(content, finish, error):
    result, calls, _ = invoke(lambda request: response(content, finish), payload=valid_payload())
    assert isinstance(result, LLMFailure) and result.error_class == error
    assert not result.dispatch_unknown and not result.retryable and len(calls) == 1
    assert result.input_tokens == 17 and result.output_tokens == 29


@pytest.mark.parametrize("mode,error", [("timeout", "provider_transport_unknown"), ("server", "provider_server_unknown")])
def test_unknown_is_preserved_without_retry(mode, error):
    def handler(request):
        if mode == "timeout":
            raise httpx.ReadTimeout("Bearer test-secret private input")
        return httpx.Response(503)
    result, calls, _ = invoke(handler, payload=valid_payload())
    assert isinstance(result, LLMFailure) and result.error_class == error
    assert result.dispatch_unknown and not result.retryable and len(calls) == 1
    assert "test-secret" not in json.dumps(result.details)


def test_business_extras_are_retained_for_domain_validator_with_missing_usage():
    payload = valid_payload()
    wire = output(payload) | {"stages": [{"title": "forbidden downstream"}]}
    result, calls, _ = invoke(lambda request: response(json.dumps(wire), usage=False), payload=payload)
    assert isinstance(result, LLMResult) and result.payload == wire and len(calls) == 1
    assert result.input_tokens is None and result.output_tokens is None
