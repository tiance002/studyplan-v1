"""Item 1 contracts; semantic fixtures are examples, not a semantic proof engine."""
import inspect
from copy import deepcopy
from dataclasses import FrozenInstanceError, fields

import pytest
from app.application.goal_requirement_analysis import GoalRequirementAnalyzer
from app.core.errors import ValidationAppError
from app.core.ids import content_hash
from app.domain.planning.goal_requirements import (
    GOAL_REQUIREMENT_PURPOSE,
    GOAL_REQUIREMENT_SCHEMA,
    GoalRequirementProfile,
    GoalRequirementProfileValidator,
)
from app.domain.planning.intent import GoalSpec
from app.infrastructure.providers.fake import FakeLLM
from app.ports.llm import (
    LLMDispatchUnknownError,
    LLMFailure,
    LLMNotDispatchedError,
    LLMResult,
)


def output(**changes):
    return {
        "schema_version": 1,
        "target_summary": "系统学习 Agent 开发",
        "required_requirements": [{"text": "能够开发 Agent", "origin": "explicit",
                                   "source_refs": ["goal.target"], "rationale": ""}],
        "hard_constraints": [], "learner_claims": [],
        "clarification_questions": [], "status": "ready",
    } | changes


def analyze(spec, body=None):
    fake = FakeLLM({GOAL_REQUIREMENT_PURPOSE: lambda purpose, payload: deepcopy(body or output())})
    result = GoalRequirementAnalyzer(fake).analyze(spec, run_id="unit-run", attempt_id="unit-attempt")
    assert len(fake.calls) == 1
    return result


def test_case1_declared_python_is_a_claim_only():
    spec = GoalSpec("我会 Python，想系统学习 Agent 开发。")
    profile = analyze(spec, output(learner_claims=[{"text": "我会 Python", "source_refs": ["goal.target"]}]))
    assert isinstance(profile, GoalRequirementProfile)
    assert profile.learner_claims[0].text == "我会 Python"
    assert [r.text for r in profile.required_requirements] == ["能够开发 Agent"]
    assert not any(word in r.text for r in profile.required_requirements for word in ("Python", "MCP", "RAG"))
    assert not {"stages", "resources", "capabilities", "accepted_known"} & profile.to_payload().keys()


def test_case2_interview_preserved_without_interview_curriculum():
    spec = GoalSpec("做一个只读 GitHub Code Review Agent", outcome_purpose="interview")
    profile = analyze(spec, output(target_summary=spec.target,
        hard_constraints=[{"text": "最终项目只读", "source_refs": ["goal.target"]}]))
    assert profile.outcome_purpose == "interview"
    assert profile.hard_constraints[0].text == "最终项目只读"
    assert [r.text for r in profile.required_requirements] == ["能够开发 Agent"]


def test_case3_project_context_is_own_fact_with_source_trace():
    project = "已经有旅行规划 Agent，希望继续基于它实践"
    spec = GoalSpec("继续学习 Agent 开发", project_context=project)
    profile = analyze(spec, output(required_requirements=[{
        "text": "基于现有项目继续学习 Agent 开发", "origin": "explicit",
        "source_refs": ["goal.target", "project_context"], "rationale": ""}]))
    assert profile.project_context == project
    assert "project_context" in profile.required_requirements[0].source_refs
    assert spec.constraints == () and spec.target == "继续学习 Agent 开发"
    assert all("旅行专项" not in r.text for r in profile.required_requirements)


def test_case4_required_inference_has_rationale_and_input_reference():
    profile = analyze(GoalSpec("最终产生带代码依据的 PR Review"), output(required_requirements=[{
        "text": "Review 结论必须关联代码上下文和依据", "origin": "inferred_required",
        "source_refs": ["goal.target"], "rationale": "没有代码依据就不满足用户指定的最终产物"}]))
    assert profile.required_requirements[0].origin == "inferred_required"
    assert profile.required_requirements[0].rationale


def test_explicit_interview_target_is_a_requirement_not_a_purpose_expansion():
    spec = GoalSpec("系统准备 Agent 技术面试", outcome_purpose="interview")
    profile = analyze(spec, output(required_requirements=[{"text": "准备 Agent 技术面试", "origin": "explicit",
                            "source_refs": ["goal.target"], "rationale": ""}]))
    assert profile.required_requirements[0].origin == "explicit"
    assert profile.required_requirements[0].source_refs == ("goal.target",)


def test_case5_key_ambiguity_and_new_supplemented_input():
    first = analyze(GoalSpec("做一个非常简单且具备生产级全部功能的 Agent"),
        output(status="needs_clarification", required_requirements=[],
               clarification_questions=["首版优先最小可运行原型，还是包含权限和运行保障的完整产品？"]))
    second = analyze(GoalSpec("先做最小可运行 Agent 原型"), output(target_summary="最小可运行原型"))
    assert first.status == "needs_clarification"
    assert 1 <= len(first.clarification_questions) <= 3
    assert second.status == "ready" and first.profile_hash != second.profile_hash


def test_case6_sufficient_input_ready_without_preference_questions():
    spec = GoalSpec("做只读 PR Review Agent", scope=("PR 代码上下文",), desired_depth="applied",
                    starting_point="会 Python", outcome_purpose="portfolio", constraints=("只读",))
    profile = analyze(spec, output(hard_constraints=[{"text": "只读", "source_refs": ["goal.constraints[0]"]}],
                                  learner_claims=[{"text": "会 Python", "source_refs": ["goal.starting_point"]}]))
    assert profile.status == "ready" and profile.clarification_questions == ()
    assert profile.scope == spec.scope and profile.desired_depth == spec.desired_depth
    assert profile.starting_point == spec.starting_point and profile.outcome_purpose == spec.outcome_purpose


@pytest.mark.parametrize("body", [None, [], "{}", {}, output(schema_version=True), output(schema_version=2),
    output(target_summary=" "), output(status="unknown"), output(required_requirements=[]),
    output(clarification_questions=["增加偏好？"]),
    output(status="needs_clarification", clarification_questions=[]),
    output(status="needs_clarification", clarification_questions=["问题"] * 4),
    output(stages=[]), output(profile_hash="model-owned"), output(scope=[]),
    output(required_requirements=[{"text": "MCP", "origin": "recommended", "source_refs": ["goal.target"], "rationale": ""}]),
    output(required_requirements=[{"text": "依据", "origin": "inferred_required", "source_refs": ["goal.target"], "rationale": " "}]),
    output(required_requirements=[{"text": "开发", "origin": "explicit", "source_refs": ["seed.agent"], "rationale": ""}]),
    output(required_requirements=[{"text": "开发", "origin": "explicit", "source_refs": [], "rationale": ""}]),
    output(required_requirements=[{"text": "开发", "origin": "explicit", "source_refs": ["goal.constraints[0]"], "rationale": ""}]),
    output(learner_claims=[{"text": "Python", "source_refs": ["project_context"]}]),
    output(hard_constraints=[{"text": "只读", "source_refs": ["goal.target"], "risk_score": 9}]),
    output(learner_claims=[{"text": "Python", "source_refs": ["goal.target"], "claim_id": "model-id"}]),
])
def test_cases7_to11_malformed_extra_source_and_status_rejected(body):
    with pytest.raises(ValidationAppError):
        GoalRequirementProfileValidator().validate(body, goal=GoalSpec("Agent"))


@pytest.mark.parametrize("field", ["required_requirements", "hard_constraints", "learner_claims"])
def test_duplicate_generated_ids_rejected(field):
    item = {"text": "同一项", "source_refs": ["goal.target"]}
    if field == "required_requirements":
        item |= {"origin": "explicit", "rationale": ""}
    with pytest.raises(ValidationAppError):
        GoalRequirementProfileValidator().validate(output(**{field: [item, deepcopy(item)]}), goal=GoalSpec("Agent"))


@pytest.mark.parametrize("constraints", [[], [{"text": "尽量只读", "source_refs": ["goal.constraints[0]"]}],
                                       [{"text": "只读", "source_refs": ["goal.target"]}]])
def test_structured_hard_constraints_cannot_be_dropped_changed_or_untraced(constraints):
    with pytest.raises(ValidationAppError):
        GoalRequirementProfileValidator().validate(output(hard_constraints=constraints),
                                                   goal=GoalSpec("Agent", constraints=("只读",)))


def test_case12_canonical_hash_ids_and_runtime_metadata_are_separate():
    spec = GoalSpec("Agent", scope=("工具",))
    raw = output()
    first = analyze(spec, raw)
    other = analyze(spec, dict(reversed(list(raw.items()))))
    assert first == other and first.profile_hash == other.profile_hash
    payload = first.to_payload()
    assert payload.pop("profile_hash") == content_hash(payload)
    assert first.required_requirements[0].requirement_id == other.required_requirements[0].requirement_id
    assert not {"run_id", "attempt_id", "provider", "token_usage", "timestamp", "raw_goal", "goal_spec"} & payload.keys()
    with pytest.raises(FrozenInstanceError):
        first.status = "needs_clarification"


def test_canonical_source_order_and_copy_do_not_leak_mutability():
    spec = GoalSpec("Agent", scope=("工具",))
    raw = output(required_requirements=[{"text": "目标", "origin": "explicit",
                                        "source_refs": ["goal.target", "goal.scope[0]"], "rationale": ""}])
    a = analyze(spec, raw)
    raw["required_requirements"][0]["source_refs"].reverse()
    b = analyze(spec, raw)
    assert a.profile_hash == b.profile_hash
    payload = a.to_payload()
    payload["required_requirements"][0]["text"] = "外部修改"
    assert a.required_requirements[0].text == "目标"


def test_product_policy_boundary_records_semantic_eval_required():
    # SEMANTIC_EVAL_REQUIRED: structural validity cannot prove that MCP was requested.
    poisoned = output(required_requirements=[{"text": "必须学习 MCP", "origin": "explicit",
        "source_refs": ["goal.target"], "rationale": ""}])
    result = analyze(GoalSpec("系统学习 Agent"), poisoned)
    assert isinstance(result, GoalRequirementProfile)
    assert result.required_requirements[0].text == "必须学习 MCP"
    normal = analyze(GoalSpec("系统学习 Agent"))
    assert [x.text for x in normal.required_requirements] == ["能够开发 Agent"]


def test_raw_goal_authority_boundary_profile_is_only_downstream_object():
    profile = analyze(GoalSpec("Agent", starting_point="会 Python"))
    assert isinstance(profile, GoalRequirementProfile)
    assert "goal" not in {f.name for f in fields(profile)}
    assert not {"raw_goal", "goal_spec", "raw_target"} & profile.to_payload().keys()
    assert list(inspect.signature(GoalRequirementAnalyzer.analyze).parameters) == ["self", "goal", "run_id", "attempt_id", "clarification"]


class ResultPort:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def generate_structured(self, **kwargs):
        self.calls.append(kwargs)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


@pytest.mark.parametrize("failure", [
    LLMFailure("not_dispatched", "拒绝", details={"dispatched": False}),
    LLMFailure("provider_http_rejected", "明确失败"),
    LLMFailure("provider_invalid_json", "无效JSON", input_tokens=12, output_tokens=9),
    LLMFailure("provider_output_truncated", "截断"),
    LLMFailure("provider_transport_unknown", "未知", dispatch_unknown=True),
])
def test_provider_failure_unchanged_no_retry_repair_or_profile(failure):
    port = ResultPort(failure)
    assert GoalRequirementAnalyzer(port).analyze(GoalSpec("Agent"), run_id="r", attempt_id="a") is failure
    assert len(port.calls) == 1


@pytest.mark.parametrize("error", [LLMNotDispatchedError("preflight"), LLMDispatchUnknownError("unknown")])
def test_typed_dispatch_exception_unchanged(error):
    port = ResultPort(error)
    with pytest.raises(type(error)) as exc:
        GoalRequirementAnalyzer(port).analyze(GoalSpec("Agent"), run_id="r", attempt_id="a")
    assert exc.value is error and len(port.calls) == 1


def test_invalid_business_response_is_known_failure_with_usage_not_authority():
    port = ResultPort(LLMResult(output(stages=[]), "test", "mock", input_tokens=10, output_tokens=7))
    result = GoalRequirementAnalyzer(port).analyze(GoalSpec("Agent"), run_id="r", attempt_id="a")
    assert isinstance(result, LLMFailure) and result.error_class == "goal_requirement_profile_invalid"
    assert result.input_tokens == 10 and result.output_tokens == 7 and not result.dispatch_unknown
    assert len(port.calls) == 1


def test_truncated_custom_port_response_cannot_become_authority_or_repair():
    port = ResultPort(LLMResult(output(), "test", "mock", finish_reason="length", input_tokens=3, output_tokens=2))
    result = GoalRequirementAnalyzer(port).analyze(GoalSpec("Agent"), run_id="r", attempt_id="a")
    assert isinstance(result, LLMFailure) and result.error_class == "provider_output_truncated"
    assert result.input_tokens == 3 and len(port.calls) == 1


def test_analyzer_uses_only_new_contract_and_accepts_natural_language():
    port = ResultPort(LLMResult(output(), "test", "mock"))
    profile = GoalRequirementAnalyzer(port).analyze("系统学习 Agent", run_id="r", attempt_id="a")
    assert isinstance(profile, GoalRequirementProfile)
    call = port.calls[0]
    assert call["purpose"] == GOAL_REQUIREMENT_PURPOSE and call["schema_name"] == GOAL_REQUIREMENT_SCHEMA
    assert set(call["payload"]) == {"goal"} and call["payload"]["goal"]["target"] == "系统学习 Agent"


@pytest.mark.parametrize("run,attempt", [("", "a"), ("r", " ")])
def test_missing_call_identity_rejected_before_port(run, attempt):
    port = ResultPort(LLMResult(output(), "test", "mock"))
    with pytest.raises(ValidationAppError):
        GoalRequirementAnalyzer(port).analyze(GoalSpec("Agent"), run_id=run, attempt_id=attempt)
    assert port.calls == []
