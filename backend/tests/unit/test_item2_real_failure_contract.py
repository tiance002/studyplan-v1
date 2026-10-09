"""Retained real failure plus synthetic boundaries; no real-model quality claim."""

import json
from copy import deepcopy
from dataclasses import asdict, replace
from pathlib import Path

import httpx
import pytest
from app.application.capability_planning import CapabilityPlanner
from app.core.errors import ValidationAppError
from app.domain.planning.capabilities import (
    CapabilityPlan,
    CapabilityPlanningPending,
    CapabilityPlanValidator,
)
from app.domain.planning.capability_policy import CAPABILITY_POLICY
from app.domain.planning.constraint_adaptation import assess_curriculum, constraints_unresolved
from app.domain.planning.goal_requirements import GoalRequirementProfileValidator
from app.domain.planning.intent import GoalSpec
from app.infrastructure.providers.capability_planning_contract import CAPABILITY_SHAPE, CAPABILITY_SYSTEM
from app.infrastructure.providers.openai_compatible import OpenAICompatibleLLM
from app.ports.llm import LLMFailure

from backend.tests.unit.test_capability_planning import evidence
from backend.tests.unit.test_capability_planning import profile as synthetic_profile

PACKET = json.loads(
    (Path(__file__).parents[1] / "fixtures/planning_v2/item2_scenario_a_failure.json").read_text(
        encoding="utf-8"
    )
)


def real_profile():
    return GoalRequirementProfileValidator().validate(
        deepcopy(PACKET["profile_response"]), goal=GoalSpec(**PACKET["goal"])
    )


def synthetic_selection(p):
    """Fresh synthetic selection, not an edited historical response or AI answer."""
    by_text = {r.text: r.requirement_id for r in p.required_requirements}
    background = by_text[PACKET["goal"]["project_context"]]
    structured = by_text["系统学习 Agent 的结构化输出"]
    tools = by_text["系统学习 Agent 的受限工具调用"]
    integration = by_text["把这些能力加入我现有的待办事项 CLI"]
    conditions = [by_text["学习深度为应用级"], by_text["学习成果用途是学习"]]

    def item(key, refs, targets=()):
        definition = CAPABILITY_POLICY.get(key)
        return dict(
            capability_id=key,
            disposition="needs_learning",
            learning_requirement="required",
            project_usage="required",
            desired_depth="applied",
            requirement_refs=refs,
            policy_refs=list(definition.policy_refs),
            prerequisite_refs=list(definition.real_prerequisites),
            learner_claim_refs=[],
            learning_target_refs=list(targets),
        )

    python = item("python.core", [background])
    python.update(
        disposition="accepted_known",
        learning_requirement="recommended",
        desired_depth="foundation",
        learner_claim_refs=[p.learner_claims[0].claim_id],
    )
    mcp = item("mcp", [])
    mcp["project_usage"] = "optional"
    return dict(
        schema_version=1,
        source_goal_profile_hash=p.profile_hash,
        policy_version="v2",
        route_kind="systematic_agent_route",
        status="ready",
        capabilities=[
            python,
            item("llm.api", [structured, tools]),
            item("structured.output", [structured, integration, *conditions], [structured]),
            item("tool.calling", [tools, integration, *conditions], [tools]),
            mcp,
        ],
        claim_bindings=[{"claim_ref": p.learner_claims[0].claim_id, "capability_id": "python.core"}],
        constraint_effects=[
            {"constraint_ref": c.constraint_id, "capability_id": None, "exclusion": "not_applicable"}
            for c in p.hard_constraints
        ],
        clarification_questions=[],
    )


def test_retained_real_response_still_rejects_without_editing_either_payload():
    before = deepcopy(PACKET)
    with pytest.raises(ValidationAppError) as error:
        CapabilityPlanValidator().validate(PACKET["failed_capability_response"], profile=real_profile())
    assert error.value.details["field"] == "definition_refs"
    assert PACKET == before
    assert real_profile().profile_hash == "b0386820c14a6aa2b9aa9b1df1aeb1ddc6b5e8925df0a8ec6f70d66dd09f7348"


@pytest.mark.parametrize(
    "rules",
    [
        ("完整、精确复制", "definition.policy_refs", "definition.real_prerequisites", "不要额外添加"),
        (
            "保留现有 CLI",
            "工具仅操作",
            "not_applicable不表示约束已满足",
            "不在最终项目使用 MCP",
            "限制 MCP 工具操作范围",
        ),
        ("普通learn用途不是MCP学习目标", "MCP的requirement_refs和learning_target_refs可为空", "服务端"),
        ("已有JSON CLI不证明", "不自动新增json.cli", "agent.loop", "error.permission", "eval.lite"),
        ("所有required_requirements", "深度和用途", "不能为了覆盖引用", "learning_target_refs"),
    ],
)
def test_prompt_explicitly_addresses_each_real_failure_class(rules):
    assert all(rule in CAPABILITY_SYSTEM for rule in rules)


def test_shape_explains_reference_arrays_instead_of_suggesting_default_empty_values():
    item = CAPABILITY_SHAPE["capabilities"][0]
    assert item["policy_refs"] and "definition.policy_refs" in item["policy_refs"][0]
    assert item["prerequisite_refs"] and "definition.real_prerequisites" in item["prerequisite_refs"][0]
    assert "规划条件" in item["requirement_refs"][0]
    assert "技术学习目标" in item["learning_target_refs"][0]
    assert "title" not in item and "learning_outcomes" not in item and "plan_hash" not in CAPABILITY_SHAPE


def test_real_profile_has_a_valid_synthetic_mapping_without_json_cli_or_metadata_learning():
    p = real_profile()
    before = p.to_payload()
    raw = synthetic_selection(p)
    plan = CapabilityPlanValidator().validate(raw, profile=p)
    assert isinstance(plan, CapabilityPlan)
    assert {c.capability_id for c in plan.accepted_known_capabilities} == {"python.core"}
    assert {c.capability_id for c in plan.learning_capabilities} == {
        "llm.api",
        "structured.output",
        "tool.calling",
        "mcp",
    }
    assert {r.requirement_id for r in p.required_requirements} == {
        ref for c in plan.capabilities for ref in c.requirement_refs
    }
    mcp = next(c for c in plan.capabilities if c.capability_id == "mcp")
    assert mcp.learning_requirement == "required" and mcp.project_usage == "optional"
    assert mcp.requirement_refs == mcp.learning_target_refs == ()
    assert CAPABILITY_POLICY.systematic_mcp_policy_ref in mcp.policy_refs
    assert next(c for c in raw["capabilities"] if c["capability_id"] == "mcp")["policy_refs"] == [
        "capability-policy:v2#mcp"
    ]
    assert {ref for c in plan.capabilities for ref in c.learning_target_refs} == {
        r.requirement_id
        for r in p.required_requirements
        if r.text in ("系统学习 Agent 的结构化输出", "系统学习 Agent 的受限工具调用")
    }
    assert (
        p.to_payload() == before
        and plan.plan_hash == CapabilityPlanValidator().validate(deepcopy(raw), profile=p).plan_hash
    )
    assessments = assess_curriculum(
        [asdict(c) for c in p.hard_constraints],
        [],
        p.project_context,
        {"kind": "user_project", "description": p.project_context},
    )
    assert constraints_unresolved(assessments)
    assert next(a for a in assessments if a["scope"] == "practice_permission_scope")["status"] == "pending"


@pytest.mark.parametrize(
    "bad",
    [
        "missing_policy",
        "borrowed_policy",
        "extra_systematic_policy",
        "wrong_prerequisite",
        "missing_depth_ref",
    ],
)
def test_strict_validator_still_rejects_reference_and_coverage_errors(bad):
    p = real_profile()
    raw = synthetic_selection(p)
    item = next(c for c in raw["capabilities"] if c["capability_id"] == "structured.output")
    if bad == "missing_policy":
        item["policy_refs"] = []
    elif bad == "borrowed_policy":
        item["policy_refs"] = ["capability-policy:v2#tool.calling"]
    elif bad == "extra_systematic_policy":
        raw["capabilities"][-1]["policy_refs"].append(CAPABILITY_POLICY.systematic_mcp_policy_ref)
    elif bad == "wrong_prerequisite":
        item["prerequisite_refs"] = []
    else:
        depth = next(r.requirement_id for r in p.required_requirements if r.text == "学习深度为应用级")
        for c in raw["capabilities"]:
            c["requirement_refs"] = [r for r in c["requirement_refs"] if r != depth]
    with pytest.raises(ValidationAppError) as error:
        CapabilityPlanValidator().validate(raw, profile=p)
    assert error.value.details["field"] == (
        "required_requirement_coverage" if bad == "missing_depth_ref" else "definition_refs"
    )


@pytest.mark.parametrize(
    "text,exclusion", [("不在最终项目使用 MCP", "project"), ("限制 MCP 工具操作范围", "not_applicable")]
)
def test_true_project_exclusion_is_distinct_from_tool_scope_at_domain_boundary(text, exclusion):
    # Domain binding fixture only. Unknown prose still cannot grant Provider dispatch.
    p = synthetic_profile("系统学习Agent", constraints=(text,))
    from backend.tests.unit.test_capability_planning import cap, wire

    raw = wire(
        p,
        cap(p, "mcp", project_usage="excluded" if exclusion == "project" else "optional"),
        route_kind="systematic_agent_route",
        constraint_effects=[
            {
                "constraint_ref": p.hard_constraints[0].constraint_id,
                "capability_id": "mcp" if exclusion == "project" else None,
                "exclusion": exclusion,
            }
        ],
    )
    assert isinstance(CapabilityPlanValidator().validate(raw, profile=p), CapabilityPlan)
    if exclusion == "project":
        raw["capabilities"][0]["project_usage"] = "required"
        result = CapabilityPlanValidator().validate(raw, profile=p)
        assert isinstance(result, CapabilityPlanningPending)
        assert "constraint_project_conflict" in {i.code for i in result.issues}


def test_actual_provider_mock_wire_uses_unchanged_real_profile_and_new_contract_below_32k():
    p = real_profile()
    raw = synthetic_selection(p)
    calls = []

    def handle(request):
        body = json.loads(request.content)
        calls.append(body)
        assert (
            len(json.dumps(body["messages"], ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
            <= 32768
        )
        assert (
            body["model"] == "deepseek-flash"
            and body["max_tokens"] == 4096
            and body["thinking"] == {"type": "disabled"}
        )
        assert body["messages"][0]["content"] == CAPABILITY_SYSTEM
        context = json.loads(body["messages"][1]["content"])
        assert context["context"]["profile"] == p.to_payload()
        assert context["field_shape"] == CAPABILITY_SHAPE
        return httpx.Response(
            200,
            json={
                "model": "deepseek-flash",
                "choices": [{"message": {"content": json.dumps(raw)}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1},
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        result = CapabilityPlanner(
            OpenAICompatibleLLM(
                base_url="https://api.deepseek.com", api_key="mock", model="deepseek-flash", client=client
            )
        ).plan(p, run_id="offline-fix", attempt_id="one")
    assert isinstance(result, CapabilityPlan) and len(calls) == 1


@pytest.mark.parametrize("restriction", ["禁止联网", "禁止把数据发送给外部模型", "未知隐私限制"])
def test_new_prompt_does_not_release_network_or_unknown_privacy_preflight(restriction):
    goal = replace(GoalSpec(**PACKET["goal"]), constraints=(*PACKET["goal"]["constraints"], restriction))
    raw = deepcopy(PACKET["profile_response"])
    raw["hard_constraints"].append({"text": restriction, "source_refs": ["goal.constraints[3]"]})
    p = GoalRequirementProfileValidator().validate(raw, goal=goal)
    with httpx.Client(
        transport=httpx.MockTransport(lambda request: pytest.fail("must reject before invoke"))
    ) as client:
        result = CapabilityPlanner(
            OpenAICompatibleLLM(
                base_url="https://api.deepseek.com", api_key="mock", model="deepseek-flash", client=client
            )
        ).plan(p, run_id="offline", attempt_id="negative")
    assert isinstance(result, LLMFailure) and result.details["dispatched"] is False


def test_fixture_domain_authority_still_rejects_before_provider_http():
    p = real_profile()
    with httpx.Client(
        transport=httpx.MockTransport(lambda request: pytest.fail("must reject before invoke"))
    ) as client:
        result = CapabilityPlanner(
            OpenAICompatibleLLM(
                base_url="https://api.deepseek.com", api_key="mock", model="deepseek-flash", client=client
            )
        ).plan(p, run_id="offline", attempt_id="domain", verification_evidence=(evidence(p),))
    assert isinstance(result, LLMFailure) and result.details["dispatched"] is False
