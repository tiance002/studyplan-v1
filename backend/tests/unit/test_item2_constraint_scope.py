"""Scoped phrase adaptation; offline mechanics never prove model/tool behavior."""
import json
from copy import deepcopy
from dataclasses import asdict, replace

import pytest
from app.application.capability_planning import CapabilityPlanner
from app.core.errors import ValidationAppError
from app.core.ids import content_hash
from app.domain.planning.constraint_adaptation import (
    CONSTRAINT_POLICY,
    CONSTRAINT_SCOPE_POLICY,
    assess_curriculum,
    composition_dispatch_allowed,
    constraint_kind,
    constraints_unresolved,
    research_permissions,
)
from app.domain.planning.curriculum import validate_curriculum_output
from app.domain.planning.domain_verification import public_outcomes
from app.domain.planning.goal_requirements import GoalRequirementProfileValidator
from app.domain.planning.intent import GoalSpec
from app.domain.planning.resource_research import ResearchBudget, ResearchSession
from app.infrastructure.providers.openai_compatible import OpenAICompatibleLLM
from app.ports.llm import LLMFailure

from backend.tests.unit.test_constraint_adaptation import fixture
from backend.tests.unit.test_curriculum import output
from backend.tests.unit.test_resource_research import inputs, run

CARRIER = "保留现有 CLI 和 JSON 任务文件作为持续实践载体"
TOOL_SCOPE = "工具仅操作用户明确允许的本地任务范围"
GOAL = GoalSpec(
    target="我已经会 Python，想系统学习 Agent 的结构化输出与受限工具调用，并把这些能力加入我现有的待办事项 CLI。",
    starting_point="已经会 Python。", scope=("结构化输出", "受限工具调用", "系统性 Agent 应用学习"),
    desired_depth="applied", outcome_purpose="learn",
    constraints=(CARRIER, "不重新创建演示项目", TOOL_SCOPE),
    project_context="我已有一个 Python 本地待办事项管理 CLI，使用 JSON 文件保存任务，希望在现有程序上逐步增加 Agent 能力。",
)


def ready_profile(goal=GOAL):
    return GoalRequirementProfileValidator().validate({
        "schema_version": 1, "target_summary": goal.target,
        "required_requirements": [{"text": goal.target, "origin": "explicit", "source_refs": ["goal.target"], "rationale": ""}],
        "hard_constraints": [{"text": t, "source_refs": [f"goal.constraints[{i}]"]} for i, t in enumerate(goal.constraints)],
        "learner_claims": [{"text": goal.starting_point, "source_refs": ["goal.starting_point"]}],
        "status": "ready", "clarification_questions": [],
    }, goal=goal)


class CaptureStop(RuntimeError):
    pass


class CaptureOnly:
    def __init__(self):
        self.calls = []

    def post(self, url, **kwargs):
        body = kwargs["json"]
        assert url == "https://api.deepseek.com/chat/completions"
        # Complete messages JSON, not just target length; a development guard.
        size = len(json.dumps(body["messages"], ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        assert size <= 32768
        assert body["model"] == "deepseek-flash" and body["max_tokens"] == 4096
        assert body["thinking"] == {"type": "disabled"}
        self.calls.append(body)
        raise CaptureStop("No real HTTP delegate exists")


def provider(client):
    return OpenAICompatibleLLM(base_url="https://api.deepseek.com", api_key="", model="deepseek-flash", client=client)


def test_original_scenario_a_reaches_item2_serializer_without_changing_facts():
    p = ready_profile()
    before, digest = deepcopy(p.to_payload()), p.profile_hash
    assert constraint_kind(CARRIER) == "existing_carrier"
    assert constraint_kind(TOOL_SCOPE) == "local_tool_scope"
    assert research_permissions(p.hard_constraints) == (True, True)
    assert composition_dispatch_allowed([asdict(c) for c in p.hard_constraints])
    capture = CaptureOnly()
    with pytest.raises(CaptureStop):
        CapabilityPlanner(provider(capture)).plan(p, run_id="offline-scope", attempt_id="item2")
    assert len(capture.calls) == 1
    context = json.loads(capture.calls[0]["messages"][1]["content"])["context"]
    assert context["profile"] == before
    assert p.to_payload() == before and p.profile_hash == digest
    assert [c.text for c in p.hard_constraints] == list(GOAL.constraints)


@pytest.mark.parametrize("forbidden", [
    "禁止联网", "不允许外部调用", "禁止把数据发送给外部模型", "保留未知隐私要求",
    CARRIER + "，禁止联网", TOOL_SCOPE + "，不允许外部调用",
    TOOL_SCOPE + "，允许访问任意本地文件", "工具仅操作用户明确允许的本地任务范围，但数据不得外发",
])
def test_network_privacy_and_compound_restrictions_still_reject_before_invoke(forbidden):
    p = ready_profile(replace(GOAL, constraints=(*GOAL.constraints, forbidden)))
    capture = CaptureOnly()
    result = CapabilityPlanner(provider(capture)).plan(p, run_id="offline-scope", attempt_id="negative")
    assert isinstance(result, LLMFailure)
    assert result.error_class == "capability_planning_input_invalid" and result.details["dispatched"] is False
    assert not capture.calls
    allowed, external = research_permissions(p.hard_constraints)
    assert not allowed or not external


def test_new_carrier_uses_existing_exact_context_proof_not_classification_as_evidence():
    p = ready_profile()
    constraints = [asdict(p.hard_constraints[0])]
    for carrier, expected in ((None, "pending"), ({"kind": "starter", "description": GOAL.project_context}, "violated"),
        ({"kind": "user_project", "description": "改写的项目背景"}, "pending"),
        ({"kind": "user_project", "description": GOAL.project_context}, "satisfied")):
        assessment = assess_curriculum(constraints, [], GOAL.project_context, carrier)[0]
        assert assessment["scope"] == "practice_carrier" and assessment["status"] == expected
        assert bool(assessment["evidence_refs"]) == (expected == "satisfied")


def test_local_tool_scope_remains_pending_even_with_safe_task_prose():
    p = ready_profile()
    assessment = assess_curriculum([asdict(p.hard_constraints[2])], [], GOAL.project_context,
        {"kind": "user_project", "description": GOAL.project_context})[0]
    assert assessment["scope"] == "practice_permission_scope"
    assert assessment["status"] == "pending" and not assessment["evidence_refs"]
    assert constraints_unresolved([assessment])
    original, frozen, _, ctx, _ = fixture((TOOL_SCOPE,), full=True, project=GOAL.project_context)
    raw = output(ctx)
    raw["stages"][0]["tasks"][0]["acceptance"][0]["text"] = "工具只在允许范围操作，保证安全"
    curriculum = validate_curriculum_output(raw, ctx.to_payload())
    assert curriculum.status == "incomplete"
    assert curriculum.to_payload()["compile_context"]["constraints"] == ctx.to_payload()["constraints"]
    from app.domain.planning.curriculum_compiler import CurriculumSourceFacts, compile_curriculum

    from backend.tests.unit.test_curriculum import local_mcp_inputs
    _, _, index, source, proof = local_mcp_inputs()
    with pytest.raises(ValidationAppError) as error:
        compile_curriculum(curriculum, context=ctx, profile=original, capability_plan=frozen,
            source_facts=CurriculumSourceFacts(index, (source,), (proof,)))
    assert error.value.details["field"] == "incomplete"
    raw["status"] = "complete"
    with pytest.raises(ValidationAppError):
        validate_curriculum_output(raw, ctx.to_payload())
    raw = output(ctx)
    raw["constraint_refs"] = []
    with pytest.raises(ValidationAppError):
        validate_curriculum_output(raw, ctx.to_payload())


def test_reviewed_research_keeps_frozen_plan_and_constraints():
    p, frozen, research, _, ports = fixture(GOAL.constraints, full=False, project=GOAL.project_context)
    assert research.entries[0].status == "resolved"
    assert research.source_capability_plan_hash == frozen.plan_hash
    assert research.entries[0].requirement.hard_constraints == p.hard_constraints
    assert not any(port.calls for port in ports)


def test_old_rule_assessment_bytes_and_explicit_v1_interpretation_are_preserved():
    p = ready_profile()
    old = asdict(p.hard_constraints[1])
    current = assess_curriculum([old], [], GOAL.project_context)[0]
    assert CONSTRAINT_POLICY == "constraint-adaptation:v1"
    assert current == {
        "constraint_ref": old["constraint_id"], "source_refs": tuple(old["source_refs"]),
        "scope": "practice_carrier", "status": "pending", "evidence_refs": (),
        "reason": "existing_carrier_evidence_pending", "policy_ref": "constraint-adaptation:v1",
    }
    for c in (p.hard_constraints[0], p.hard_constraints[2]):
        legacy = assess_curriculum([asdict(c)], [], GOAL.project_context, policy_ref=CONSTRAINT_POLICY)[0]
        assert legacy["scope"] == "unclassified" and legacy["status"] == "pending"
        assert legacy["policy_ref"] == CONSTRAINT_POLICY
        new = assess_curriculum([asdict(c)], [], GOAL.project_context)[0]
        assert new["policy_ref"] == "constraint-adaptation:v2"
    with pytest.raises(ValueError):
        constraint_kind(CARRIER, policy_ref="constraint-adaptation:unknown")


@pytest.mark.parametrize("constraint", ["免费教材", TOOL_SCOPE])
def test_research_config_only_versions_new_rules_and_rejects_old_binding_without_mutation(constraint):
    values = inputs(constraints=(constraint,))
    p, frozen, *_ = values
    digest = frozen.plan_hash
    budget = ResearchBudget(max_searches=0)
    _, session, *_, researcher = run(values, budget=budget)
    fields = {"reviewed_index": None, "access_proofs": [], "public_outcomes": public_outcomes(frozen)}
    version = CONSTRAINT_SCOPE_POLICY if constraint == TOOL_SCOPE else CONSTRAINT_POLICY
    assert session.config_hash == content_hash(fields | {"constraint_policy": version})
    if constraint == TOOL_SCOPE:
        legacy = ResearchSession.restore(replace(session.snapshot(), config_hash=content_hash(fields | {"constraint_policy": CONSTRAINT_POLICY})))
        before = legacy.snapshot()
        with pytest.raises(ValidationAppError) as error:
            run(values, budget=budget, session=legacy, researcher=researcher)
        assert error.value.details["field"] == "session_configuration"
        assert legacy.snapshot() == before
    assert frozen.plan_hash == digest and session.completed.source_profile_hash == p.profile_hash


@pytest.mark.parametrize("boundary", ["empty_unknown_version", "explicit_v2_old_rule"])
def test_explicit_version_cannot_skip_validation_or_relabel_old_rule(boundary):
    if boundary == "empty_unknown_version":
        with pytest.raises(ValueError):
            assess_curriculum([], [], None, policy_ref="constraint-adaptation:unknown")
    else:
        old = asdict(ready_profile().hard_constraints[1])
        assert assess_curriculum([old], [], GOAL.project_context, policy_ref=CONSTRAINT_SCOPE_POLICY) == assess_curriculum([old], [], GOAL.project_context)
