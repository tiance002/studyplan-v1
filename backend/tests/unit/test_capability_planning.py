"""Item 2 deterministic boundaries; semantic selection fixtures are not AI evals."""
import inspect
import json
from copy import deepcopy
from dataclasses import asdict, replace

import pytest
from app.application.capability_planning import CapabilityPlanner
from app.application.goal_requirement_analysis import GoalRequirementAnalyzer
from app.core.errors import ValidationAppError
from app.core.ids import content_hash
from app.domain.planning.capabilities import (
    CAPABILITY_PURPOSE,
    CapabilityPlan,
    CapabilityPlanningPending,
    DomainVerificationEvidence,
    validate_capability_planning_input,
    verification_input_hash,
)
from app.domain.planning.capability_policy import (
    CAPABILITY_POLICY,
    CapabilityDefinition,
    LearningOutcome,
)
from app.domain.planning.goal_requirements import GOAL_REQUIREMENT_PURPOSE, GoalRequirementProfileValidator
from app.domain.planning.intent import GoalSpec
from app.infrastructure.providers.fake import FakeLLM
from app.ports.llm import LLMDispatchUnknownError, LLMFailure, LLMResult


def profile(target="开发 Agent", *, claims=(), constraints=(), ready=True):
    spec = GoalSpec(target, constraints=tuple(constraints))
    return GoalRequirementProfileValidator().validate({
        "schema_version": 1, "target_summary": target,
        "required_requirements": [{"text": target, "origin": "explicit", "source_refs": ["goal.target"],
                                   "rationale": ""}],
        "hard_constraints": [{"text": text, "source_refs": [f"goal.constraints[{i}]"]}
                             for i, text in enumerate(constraints)],
        "learner_claims": [{"text": text, "source_refs": ["goal.target"]} for text in claims],
        "clarification_questions": [] if ready else ["首版要实现什么行为？"],
        "status": "ready" if ready else "needs_clarification",
    }, goal=spec)


def cap(p, capability_id, **changes):
    definition = CAPABILITY_POLICY.get(capability_id)
    return {"capability_id": capability_id, "disposition": "needs_learning", "learning_requirement": "required",
            "project_usage": "required", "desired_depth": "applied",
            "requirement_refs": [p.required_requirements[0].requirement_id],
            "policy_refs": list(definition.policy_refs) if definition else [], "learner_claim_refs": [],
            "prerequisite_refs": list(definition.real_prerequisites) if definition else [],
            "learning_target_refs": []} | changes


def wire(p, *items, **changes):
    return {"schema_version": 1, "source_goal_profile_hash": p.profile_hash,
            "policy_version": CAPABILITY_POLICY.version, "route_kind": "narrow_goal", "status": "ready",
            "capabilities": list(items),
            "claim_bindings": [{"claim_ref": c.claim_id, "capability_id": None} for c in p.learner_claims],
            "constraint_effects": [{"constraint_ref": c.constraint_id, "capability_id": None,
                                    "exclusion": "not_applicable"} for c in p.hard_constraints],
            "clarification_questions": []} | changes


class Port:
    def __init__(self, result):
        self.result, self.calls = result, []

    def generate_structured(self, **kw):
        self.calls.append(deepcopy(kw))
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def plan(p, raw, **kwargs):
    port = Port(LLMResult(raw, "test", "fixture"))
    result = CapabilityPlanner(port).plan(p, run_id="offline-run", attempt_id="one", **kwargs)
    assert len(port.calls) == 1
    return result


def known_python(p):
    claim = p.learner_claims[0].claim_id
    return cap(p, "python.core", disposition="accepted_known", learner_claim_refs=[claim])


def test_python_claim_is_accepted_known_and_never_a_learning_input():
    p = profile("我会Python，系统学习Agent", claims=("会Python",))
    raw = wire(p, known_python(p), cap(p, "llm.api"), cap(p, "mcp", project_usage="optional"),
               route_kind="systematic_agent_route", claim_bindings=[
                   {"claim_ref": p.learner_claims[0].claim_id, "capability_id": "python.core"}])
    result = plan(p, raw)
    assert isinstance(result, CapabilityPlan)
    assert [c.capability_id for c in result.accepted_known_capabilities] == ["python.core"]
    assert "python.core" not in {c.capability_id for c in result.learning_capabilities}
    assert all(o.outcome_id not in {x.outcome_id for x in CAPABILITY_POLICY.get("python.core").learning_outcomes}
               for o in result.learning_outcomes)


def test_broad_python_claim_does_not_swallow_specific_async_learning_target():
    p = profile("会Python，明确学习asyncio取消与并发", claims=("会Python",))
    specific = cap(p, "python.async", learning_target_refs=[p.required_requirements[0].requirement_id])
    raw = wire(p, known_python(p), specific, claim_bindings=[
        {"claim_ref": p.learner_claims[0].claim_id, "capability_id": "python.core"}])
    result = plan(p, raw)
    assert [c.capability_id for c in result.learning_capabilities] == ["python.async"]
    raw["capabilities"][1].update(disposition="accepted_known", learner_claim_refs=[p.learner_claims[0].claim_id])
    assert isinstance(plan(p, raw), LLMFailure)


def test_systematic_mcp_learning_is_required_but_project_use_can_be_excluded():
    p = profile()
    result = plan(p, wire(p, cap(p, "llm.api"), cap(p, "mcp", project_usage="excluded"),
                          route_kind="systematic_agent_route"))
    mcp = next(c for c in result.learning_capabilities if c.capability_id == "mcp")
    assert mcp.learning_requirement == "required" and mcp.project_usage == "excluded"
    assert "tool.calling" not in mcp.prerequisite_refs  # preference is not a hard prerequisite


def test_narrow_python_json_cli_does_not_expand_agent_or_mcp():
    p = profile("用Python读取JSON文件的CLI", claims=("会Python",))
    result = plan(p, wire(p, known_python(p), cap(p, "json.cli"), claim_bindings=[
        {"claim_ref": p.learner_claims[0].claim_id, "capability_id": "python.core"}]))
    assert {c.capability_id for c in result.capabilities} == {"python.core", "json.cli"}


def test_coding_agent_selects_composable_capabilities_without_other_specialty_packs():
    p = profile("基于GitHub API做Code Review")
    result = plan(p, wire(p, cap(p, "github.api"), cap(p, "code.review")))
    assert {c.capability_id for c in result.learning_capabilities} == {"github.api", "code.review"}


def test_systematic_mcp_exclusion_is_explicit_pending_not_silent_override():
    p = profile("系统学习Agent", constraints=("不学习MCP",))
    raw = wire(p, cap(p, "mcp", project_usage="excluded"), route_kind="systematic_agent_route",
               constraint_effects=[{"constraint_ref": p.hard_constraints[0].constraint_id,
                                    "capability_id": "mcp", "exclusion": "learning"}])
    result = plan(p, raw)
    assert isinstance(result, CapabilityPlanningPending) and result.status == "needs_clarification"
    assert "constraint_learning_conflict" in {i.code for i in result.issues}
    assert result.clarification_questions


def evidence(p):
    return DomainVerificationEvidence(evidence_id="fixture-ros2-v1", input_hash=verification_input_hash(p),
        source_refs=("fixture:ros2-action-contract",), limitations=("离线fixture，未核验真实ROS2版本",),
        evidence_kind="fixture", capabilities=(CapabilityDefinition(
            capability_id="ros2.action", title="ROS2 Action调用", default_depth="applied",
            learning_outcomes=(LearningOutcome("ros2.action.lifecycle", "解释Action目标、反馈和结果生命周期"),),
            real_prerequisites=(), policy_refs=()),))


def test_unknown_domain_waits_for_verification_then_accepts_bound_fixture_definition():
    p = profile("开发调用ROS2 Action的Agent")
    raw = wire(p, cap(p, "ros2.action"))
    missing = plan(p, raw)
    assert isinstance(missing, CapabilityPlanningPending) and missing.status == "needs_verification"
    verified = plan(p, raw, verification_evidence=(evidence(p),))
    assert isinstance(verified, CapabilityPlan)
    assert verified.capabilities[0].learning_outcomes[0].outcome_id == "ros2.action.lifecycle"
    assert verified.verification_evidence[0].evidence_kind == "fixture"
    assert verified.verification_evidence[0].limitations


def test_accepted_known_exact_binding_satisfies_real_prerequisite_without_review():
    p = profile("开发Python JSON CLI", claims=("会Python", "会Rust"))
    bindings = [{"claim_ref": p.learner_claims[0].claim_id, "capability_id": "python.core"},
                {"claim_ref": p.learner_claims[1].claim_id, "capability_id": None}]
    result = plan(p, wire(p, known_python(p), cap(p, "json.cli"), claim_bindings=bindings))
    assert result.learning_capabilities[0].prerequisite_refs == ("python.core",)
    assert len(result.accepted_known_capabilities) == 1
    assert next(b for b in result.claim_bindings if b.claim_ref == p.learner_claims[1].claim_id).capability_id is None


@pytest.mark.parametrize("field,value", [("requirement_refs", ["wrong"]), ("policy_refs", ["wrong"]),
    ("learner_claim_refs", ["wrong"]), ("prerequisite_refs", ["wrong"]),
    ("learning_target_refs", ["wrong"]), ("outcomes", []), ("stages", []), ("title", "model override")])
def test_invalid_refs_or_model_definition_fields_are_rejected(field, value):
    p = profile()
    item = cap(p, "llm.api") | {field: value}
    assert isinstance(plan(p, wire(p, item)), LLMFailure)


def test_cycles_and_forged_profile_hash_are_rejected():
    p = profile("未知领域")
    ev = evidence(p)
    cyclic = replace(ev, capabilities=(replace(ev.capabilities[0], real_prerequisites=("ros2.action",)),))
    port = Port(LLMFailure("never", "must not dispatch"))
    assert isinstance(CapabilityPlanner(port).plan(p, run_id="r", attempt_id="a",
                                                 verification_evidence=(cyclic,)), LLMFailure)
    assert not port.calls
    assert isinstance(plan(p, wire(p, cap(p, "llm.api"), source_goal_profile_hash="forged")), LLMFailure)


def test_two_node_verification_cycle_rejects_before_dispatch():
    p = profile("未知领域")
    first = replace(evidence(p).capabilities[0], real_prerequisites=("ros2.client",))
    second = CapabilityDefinition("ros2.client", "ROS2客户端", (LearningOutcome("ros2.client.request", "发送请求"),),
                                  ("ros2.action",), "applied", ())
    cyclic = replace(evidence(p), capabilities=(first, second))
    port = Port(LLMFailure("never", "must not dispatch"))
    result = CapabilityPlanner(port).plan(p, run_id="r", attempt_id="a", verification_evidence=(cyclic,))
    assert isinstance(result, LLMFailure) and result.details == {"dispatched": False}
    assert not port.calls


def test_known_definition_is_server_owned_and_hash_stable():
    p = profile()
    raw = wire(p, cap(p, "llm.api"))
    first, second = plan(p, raw), plan(p, deepcopy(raw))
    assert first.plan_hash == second.plan_hash
    assert first.capabilities[0].title == CAPABILITY_POLICY.get("llm.api").title
    assert first.capabilities[0].learning_outcomes == CAPABILITY_POLICY.get("llm.api").learning_outcomes
    assert first.source_goal_profile_hash == p.profile_hash


@pytest.mark.parametrize("extra", ["stages", "resources", "seed_id", "confidence_score"])
def test_curriculum_or_unknown_business_fields_cannot_freeze(extra):
    p = profile()
    assert isinstance(plan(p, wire(p, cap(p, "llm.api")) | {extra: []}), LLMFailure)


def test_profile_is_sole_input_and_upstream_clarification_makes_zero_calls():
    port = Port(LLMFailure("never", "must not call"))
    result = CapabilityPlanner(port).plan(profile(ready=False), run_id="r", attempt_id="a")
    assert isinstance(result, CapabilityPlanningPending) and not port.calls
    assert "raw_goal" not in inspect.signature(CapabilityPlanner.plan).parameters
    assert "goal_spec" not in inspect.signature(CapabilityPlanner.plan).parameters
    with pytest.raises(ValidationAppError):
        CapabilityPlanner(port).plan(GoalSpec("raw"), run_id="r", attempt_id="a")


def test_single_call_payload_owns_only_profile_policy_and_evidence():
    p = profile()
    fake = FakeLLM({CAPABILITY_PURPOSE: lambda purpose, payload: wire(p, cap(p, "llm.api"))})
    service = CapabilityPlanner(fake)
    assert isinstance(service.plan(p, run_id="r", attempt_id="a"), CapabilityPlan)
    port = Port(LLMResult(wire(p, cap(p, "llm.api")), "test", "fixture"))
    CapabilityPlanner(port).plan(p, run_id="r", attempt_id="a")
    payload = port.calls[0]["payload"]
    assert set(payload) == {"profile", "policy", "verification_evidence"}
    assert "goal" not in payload and "target" not in payload["profile"]
    assert validate_capability_planning_input(payload, "CapabilityPlanV1")
    assert json.loads(json.dumps(payload)) == payload
    assert validate_capability_planning_input(json.loads(json.dumps(payload)), "CapabilityPlanV1")
    assert not validate_capability_planning_input(payload | {"raw_goal": "raw"}, "CapabilityPlanV1")


def test_unknown_failure_and_exception_never_retry_or_create_ready_plan():
    p = profile()
    failure = LLMFailure("provider_transport_unknown", "unknown", dispatch_unknown=True)
    port = Port(failure)
    assert CapabilityPlanner(port).plan(p, run_id="r", attempt_id="a") is failure
    assert len(port.calls) == 1
    port = Port(LLMDispatchUnknownError("unknown"))
    with pytest.raises(LLMDispatchUnknownError):
        CapabilityPlanner(port).plan(p, run_id="r", attempt_id="a")
    assert len(port.calls) == 1


def test_evidence_wrong_binding_or_repeat_bundle_is_rejected_without_dispatch():
    p = profile()
    port = Port(LLMFailure("never", "no dispatch"))
    bad = replace(evidence(p), input_hash="forged")
    result = CapabilityPlanner(port).plan(p, run_id="r", attempt_id="a", verification_evidence=(bad,))
    assert isinstance(result, LLMFailure) and not port.calls
    result = CapabilityPlanner(port).plan(p, run_id="r", attempt_id="a", verification_evidence=(evidence(p), evidence(p)))
    assert isinstance(result, LLMFailure) and not port.calls


def test_mapped_claim_cannot_be_reintroduced_as_learning_and_all_facts_have_dispositions():
    p = profile(claims=("会Python",), constraints=("免费教材",))
    raw = wire(p, cap(p, "python.core"), claim_bindings=[
        {"claim_ref": p.learner_claims[0].claim_id, "capability_id": "python.core"}])
    assert isinstance(plan(p, raw), LLMFailure)
    raw = wire(p, cap(p, "llm.api"), constraint_effects=[])
    assert isinstance(plan(p, raw), LLMFailure)


def test_injected_semantic_overreach_is_not_proved_by_structural_validation():
    p = profile("用Python读JSON")
    result = plan(p, wire(p, cap(p, "mcp")))
    assert isinstance(result, CapabilityPlan)
    # SEMANTIC_EVAL_REQUIRED: refs/shape cannot prove capability applicability.


def test_valid_claim_ref_with_wrong_semantic_binding_remains_semantic_eval_required():
    p = profile("会Python，开发GitHub集成", claims=("会Python",))
    claim = p.learner_claims[0].claim_id
    result = plan(p, wire(p, cap(p, "github.api", disposition="accepted_known", learner_claim_refs=[claim]),
                          claim_bindings=[{"claim_ref": claim, "capability_id": "github.api"}]))
    assert isinstance(result, CapabilityPlan)
    assert result.accepted_known_capabilities[0].capability_id == "github.api"
    # SEMANTIC_EVAL_REQUIRED: an existing claim ID does not prove that Python means GitHub proficiency.


def test_item1_analyzer_profile_is_consumed_by_item2_service_without_raw_goal():
    spec = GoalSpec("学习LLM API请求")
    response = {"schema_version": 1, "target_summary": "学习LLM API请求",
                "required_requirements": [{"text": "学习LLM API请求", "origin": "explicit",
                                           "source_refs": ["goal.target"], "rationale": ""}],
                "hard_constraints": [], "learner_claims": [], "clarification_questions": [], "status": "ready"}
    item1_port = Port(LLMResult(response, "test", "offline-fixture"))
    p = GoalRequirementAnalyzer(item1_port).analyze(spec, run_id="r", attempt_id="item1")
    assert item1_port.calls[0]["purpose"] == GOAL_REQUIREMENT_PURPOSE
    item2_port = Port(LLMResult(wire(p, cap(p, "llm.api")), "test", "offline-fixture"))
    result = CapabilityPlanner(item2_port).plan(p, run_id="r", attempt_id="item2")
    payload = item2_port.calls[0]["payload"]
    assert isinstance(result, CapabilityPlan) and result.source_goal_profile_hash == p.profile_hash
    assert payload == {"profile": p.to_payload(), "policy": CAPABILITY_POLICY.to_payload(), "verification_evidence": []}
    assert "goal" not in payload and "target" not in payload["profile"]
    assert len(item1_port.calls) == len(item2_port.calls) == 1
    # Both ports are offline fixtures: this proves service wiring, not model semantic accuracy.


@pytest.mark.parametrize("field,value", [
    ("desired_depth", "expert"), ("outcome_purpose", "unknown"), ("scope", "raw scope"),
    ("scope", ("",)), ("scope", ("x" * 301,)), ("scope", ("x",) * 21),
    ("starting_point", []), ("starting_point", "x" * 1001),
    ("project_context", []), ("project_context", ""), ("project_context", "x" * 2001),
    ("target_summary", ""), ("clarification_questions", {}),
    ("status", "invalid"), ("status", "needs_clarification"),
])
def test_rehashed_profile_invalid_scalar_fields_reject_before_dispatch(field, value):
    p = replace(profile(), **{field: value})
    port = Port(LLMFailure("never", "input must fail"))
    result = CapabilityPlanner(port).plan(p, run_id="r", attempt_id="a")
    assert isinstance(result, LLMFailure) and not port.calls


@pytest.mark.parametrize("changes", [
    {"origin": "model_guess"}, {"origin": "inferred_required", "rationale": ""},
    {"source_refs": ("goal.project_context",)}, {"source_refs": ("goal.scope",)},
    {"source_refs": ("goal.scope[0]",)}, {"source_refs": ("goal.starting_point",)},
    {"source_refs": ("project_context",)}, {"source_refs": ("goal.constraints[20]",)},
    {"source_refs": ("goal.constraints[-1]",)}, {"source_refs": ("unknown",)},
])
def test_rehashed_requirement_invalid_origin_rationale_or_source_ref_rejects(changes):
    p = profile()
    requirement = replace(p.required_requirements[0], **changes)
    body = {k: v for k, v in asdict(requirement).items() if k != "requirement_id"}
    requirement = replace(requirement, requirement_id="req_" + content_hash(body))
    p = replace(p, required_requirements=(requirement,))
    port = Port(LLMFailure("never", "input must fail"))
    result = CapabilityPlanner(port).plan(p, run_id="r", attempt_id="a")
    assert isinstance(result, LLMFailure) and not port.calls


def test_server_detected_route_uncertainty_has_answerable_clarification():
    p = profile()
    result = plan(p, wire(p, cap(p, "llm.api"), route_kind="uncertain"))
    assert isinstance(result, CapabilityPlanningPending) and result.clarification_questions
