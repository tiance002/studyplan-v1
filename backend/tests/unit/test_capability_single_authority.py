"""Versioned Item 2 decision wire; synthetic decisions over frozen real profile facts."""

import json
from copy import deepcopy

import httpx
import pytest
from app.application.capability_planning import CapabilityPlanner
from app.core.errors import ValidationAppError
from app.domain.planning.capabilities import (
    CAPABILITY_DECISION_SCHEMA,
    CAPABILITY_PURPOSE,
    CAPABILITY_SCHEMA,
    CapabilityPlan,
    CapabilityPlanningPending,
    CapabilityPlanValidator,
)
from app.domain.planning.capability_decisions import (
    CAPABILITY_DECISION_PROTOCOL,
    normalize_capability_decision,
)
from app.domain.planning.capability_policy import CAPABILITY_POLICY
from app.domain.planning.content_coverage import CoverageEvaluator, ReviewedContentIndex
from app.domain.planning.resource_gaps import extract
from app.domain.planning.v2_runtime import build_v2_manifest, manifest_intact, purpose_schema
from app.infrastructure.providers.capability_planning_decision_contract import (
    CAPABILITY_DECISION_SHAPE,
    CAPABILITY_DECISION_SYSTEM,
)
from app.infrastructure.providers.openai_compatible import OpenAICompatibleLLM
from app.ports.llm import LLMResult

from backend.tests.unit.test_item2_real_failure_contract import real_profile


def _base_decision(profile):
    by_text = {item.text: item.requirement_id for item in profile.required_requirements}
    structured = next(key for text, key in by_text.items() if "结构化输出" in text)
    tool = next(key for text, key in by_text.items() if "受限工具调用" in text)
    integration = next(key for text, key in by_text.items() if "加入我现有" in text)
    background = next(key for text, key in by_text.items() if "已有一个" in text or "已有一个 Python" in text)
    depth = next(key for text, key in by_text.items() if "应用级" in text)
    purpose = next(key for text, key in by_text.items() if "用途是学习" in text)
    target_ids = [r.requirement_id for r in profile.required_requirements if r.origin == "explicit"
                  and ("结构化输出" in r.text or "受限工具调用" in r.text)]
    return {
        "decision_version": 2,
        "source_goal_profile_hash": profile.profile_hash,
        "policy_version": CAPABILITY_POLICY.version,
        "route_kind": "systematic_agent_route",
        "status": "ready",
        "learning_decisions": [
            {"capability_id": "llm.api", "learning_requirement": "required", "project_usage": "optional",
             "desired_depth": "applied", "requirement_refs": [structured, tool],
             "learning_target_refs": [], "project_usage_rationale": "模型基础能力不必作为本版主项目的独立功能。",
             "selection_rationale": "实际模型交互是所选输出与工具调用能力的真实先修。"},
            {"capability_id": "structured.output", "learning_requirement": "required", "project_usage": "required",
             "desired_depth": "applied", "requirement_refs": [structured, integration, depth, purpose],
             "learning_target_refs": [target_ids[0]], "project_usage_rationale": "用户明确要求将该能力加入现有CLI。",
             "selection_rationale": "用户明确要系统学习结构化输出，并把它加入现有CLI。"},
            {"capability_id": "tool.calling", "learning_requirement": "required", "project_usage": "required",
             "desired_depth": "applied", "requirement_refs": [tool, integration, depth, purpose],
             "learning_target_refs": [target_ids[1]], "project_usage_rationale": "用户明确要求将受限工具调用加入现有CLI。",
             "selection_rationale": "用户明确要系统学习受限工具调用，并把它加入现有CLI。"},
            {"capability_id": "mcp", "learning_requirement": "required", "project_usage": "optional",
             "desired_depth": "applied", "requirement_refs": [], "learning_target_refs": [],
             "project_usage_rationale": "MCP学习与现有项目是否集成分开，暂无强制集成依据。",
             "selection_rationale": "系统性Agent路线的MCP学习由冻结StudyPlan课程政策要求；项目集成保持可选。"},
        ],
        "claim_decisions": [{
            "capability_id": "python.core",
            "claim_mappings": [{"claim_ref": profile.learner_claims[0].claim_id,
                                "mapping_rationale": "用户明确声明已经会Python，对应Python基础能力。"}],
            "project_usage": "optional",
            "project_usage_rationale": "Python是学习起点，不是本版项目必须实现的独立功能。",
            "requirement_refs": [background],
        }],
        "constraint_effects": [{"constraint_ref": item.constraint_id, "capability_id": None,
                                "exclusion": "not_applicable"} for item in profile.hard_constraints],
        "clarification_questions": [],
    }


def _manifest(**kwargs):
    from app.domain.planning.curriculum_compiler import CurriculumSourceFacts

    from scripts.planning_v2_scenario_a import scenario_budget

    return build_v2_manifest(
        "系统学习Agent结构化输出和工具调用",
        model_ref="mock:bound",
        source_facts=CurriculumSourceFacts(ReviewedContentIndex("empty", (), (), ())),
        budget=scenario_budget(),
        checked_at="2026-10-10T00:00:00+00:00",
        product_semantics="planning-v2-product-v2",
        acceptance_gate="scenario-a-review-v1",
        **kwargs,
    )


def test_historical_193_duplicate_claim_binding_is_reproduced_without_rewriting_record():
    profile = real_profile()
    legacy = _base_decision(profile)
    # Simulate the old wire's two authorities: a claim points at Python, but
    # the independently emitted capability array omits its accepted-known row.
    old_wire = {
        "schema_version": 1,
        "source_goal_profile_hash": profile.profile_hash,
        "policy_version": CAPABILITY_POLICY.version,
        "route_kind": legacy["route_kind"],
        "status": "ready",
        "capabilities": [],
        "claim_bindings": [{"claim_ref": profile.learner_claims[0].claim_id, "capability_id": "python.core"}],
        "constraint_effects": legacy["constraint_effects"],
        "clarification_questions": [],
    }
    with pytest.raises(ValidationAppError) as error:
        CapabilityPlanValidator().validate(old_wire, profile=profile)
    assert error.value.details["field"] == "claim_binding"
    assert "claim_decisions" not in old_wire


def test_single_claim_decision_generates_python_known_row_from_policy_and_never_a_python_gap():
    profile = real_profile()
    raw = _base_decision(profile)
    result = normalize_capability_decision(raw, profile=profile)
    assert isinstance(result, CapabilityPlan)
    python = next(item for item in result.accepted_known_capabilities if item.capability_id == "python.core")
    definition = CAPABILITY_POLICY.get("python.core")
    assert python.title == definition.title
    assert python.learning_outcomes == definition.learning_outcomes
    assert python.policy_refs == definition.policy_refs
    assert python.prerequisite_refs == definition.real_prerequisites
    assert python.learner_claim_refs == (profile.learner_claims[0].claim_id,)
    assert "python.core" not in {item.capability_id for item in result.learning_capabilities}
    coverage = CoverageEvaluator().evaluate(result, ReviewedContentIndex("empty", (), (), ()))
    gaps = extract(result, coverage)
    assert all(gap.capability_id != "python.core" for gap in gaps.gaps)
    mcp = next(item for item in result.learning_capabilities if item.capability_id == "mcp")
    assert mcp.learning_requirement == "required" and mcp.project_usage == "optional"
    assert CAPABILITY_POLICY.systematic_mcp_policy_ref in mcp.policy_refs


def test_unmapped_claim_is_explicit_null_and_server_never_infers_python_known():
    profile = real_profile()
    raw = _base_decision(profile)
    raw["claim_decisions"] = [{"capability_id": None,
        "claim_mappings": [{"claim_ref": profile.learner_claims[0].claim_id,
                            "mapping_rationale": "没有足够依据把该声明绑定到具体冻结能力。"}],
        "project_usage": None, "project_usage_rationale": None, "requirement_refs": []}]
    by_id = {item.text: item.requirement_id for item in profile.required_requirements}
    background = next(key for text, key in by_id.items() if "已有一个" in text or "已有一个 Python" in text)
    next(item for item in raw["learning_decisions"] if item["capability_id"] == "tool.calling")[
        "requirement_refs"].append(background)
    result = normalize_capability_decision(raw, profile=profile)
    assert isinstance(result, CapabilityPlan)
    assert result.accepted_known_capabilities == ()
    assert next(binding for binding in result.claim_bindings
                if binding.claim_ref == profile.learner_claims[0].claim_id).capability_id is None


def test_wrong_python_to_github_mapping_is_preserved_for_semantic_rejection_not_auto_corrected():
    profile = real_profile()
    raw = _base_decision(profile)
    raw["claim_decisions"] = [{"capability_id": "github.api",
        "claim_mappings": [{"claim_ref": profile.learner_claims[0].claim_id,
                            "mapping_rationale": "错误示例：只根据Python声明就认定用户已掌握GitHub API。"}],
        "project_usage": "optional", "project_usage_rationale": "声明对该项目功能并非必用。",
        "requirement_refs": [raw["claim_decisions"][0]["requirement_refs"][0]]}]
    result = normalize_capability_decision(raw, profile=profile)
    assert isinstance(result, CapabilityPlan)
    assert {item.capability_id for item in result.accepted_known_capabilities} == {"github.api"}
    assert result.accepted_known_capabilities[0].learner_claim_refs == (profile.learner_claims[0].claim_id,)
    # This is a structurally valid but semantically false witness. The retained
    # decision rationale makes the mistake reviewable; no server keyword rule
    # silently rewrites it into python.core.
    assert "GitHub API" in raw["claim_decisions"][0]["claim_mappings"][0]["mapping_rationale"]


def test_one_claim_can_support_multiple_capabilities_and_multiple_claims_can_share_one():
    from backend.tests.unit.test_capability_planning import profile as narrow_profile

    multi_claim_profile = narrow_profile("使用GitHub API分析PR并提供代码审查依据",
        claims=("熟悉GitHub API对象和代码审查依据",))
    claim = multi_claim_profile.learner_claims[0].claim_id
    requirement = multi_claim_profile.required_requirements[0].requirement_id
    raw = {"decision_version": 2, "source_goal_profile_hash": multi_claim_profile.profile_hash,
        "policy_version": CAPABILITY_POLICY.version, "route_kind": "narrow_goal", "status": "ready",
        "learning_decisions": [], "claim_decisions": [
            {"capability_id": "github.api", "claim_mappings": [{"claim_ref": claim,
                "mapping_rationale": "声明明确包含GitHub API对象处理。"}], "project_usage": "required",
                "project_usage_rationale": "目标需要分析GitHub云端PR。", "requirement_refs": [requirement]},
            {"capability_id": "code.review", "claim_mappings": [{"claim_ref": claim,
                "mapping_rationale": "声明明确包含代码审查依据方法。"}], "project_usage": "required",
                "project_usage_rationale": "目标要求输出可追溯审查依据。", "requirement_refs": [requirement]},
        ], "constraint_effects": [], "clarification_questions": []}
    result = normalize_capability_decision(raw, profile=multi_claim_profile)
    assert isinstance(result, CapabilityPlan)
    assert {binding.capability_id for binding in result.claim_bindings if binding.claim_ref == claim} == {
        "code.review", "github.api"}

    two_claim_profile = narrow_profile("使用GitHub API分析PR并提供代码审查依据",
        claims=("熟悉GitHub API", "经常处理GitHub REST API对象"))
    requirement = two_claim_profile.required_requirements[0].requirement_id
    two = {"decision_version": 2, "source_goal_profile_hash": two_claim_profile.profile_hash,
        "policy_version": CAPABILITY_POLICY.version, "route_kind": "narrow_goal", "status": "ready",
        "learning_decisions": [], "claim_decisions": [{"capability_id": "github.api", "claim_mappings": [
        {"claim_ref": claim_item.claim_id, "mapping_rationale": "两条声明均明确指向GitHub API经验。"}
        for claim_item in two_claim_profile.learner_claims], "project_usage": "optional",
        "project_usage_rationale": "该能力支撑目标，但主项目采用范围可选。",
        "requirement_refs": [requirement]}], "constraint_effects": [], "clarification_questions": []}
    combined = normalize_capability_decision(two, profile=two_claim_profile)
    assert isinstance(combined, CapabilityPlan)
    known = next(item for item in combined.accepted_known_capabilities if item.capability_id == "github.api")
    assert set(known.learner_claim_refs) == {claim_item.claim_id for claim_item in two_claim_profile.learner_claims}


def test_definition_and_prerequisite_are_server_owned_but_missing_prerequisite_selection_rejects():
    profile = real_profile()
    raw = _base_decision(profile)
    result = normalize_capability_decision(raw, profile=profile)
    structured = next(item for item in result.learning_capabilities if item.capability_id == "structured.output")
    assert structured.policy_refs == CAPABILITY_POLICY.get("structured.output").policy_refs
    assert structured.prerequisite_refs == ("llm.api",)
    no_api = deepcopy(raw)
    no_api["learning_decisions"] = [item for item in no_api["learning_decisions"]
                                     if item["capability_id"] != "llm.api"]
    with pytest.raises(ValidationAppError) as error:
        normalize_capability_decision(no_api, profile=profile)
    assert error.value.details["field"] == "prerequisite_refs"


def test_cycle_in_source_verification_is_still_rejected_before_normalization():
    from dataclasses import replace

    from backend.tests.unit.test_capability_planning import evidence

    profile = __import__("backend.tests.unit.test_capability_planning", fromlist=["profile"]).profile("未知ROS2领域")
    evidence_item = evidence(profile)
    cyclic_definition = replace(evidence_item.capabilities[0], real_prerequisites=("ros2.action",))
    cyclic_evidence = replace(evidence_item, capabilities=(cyclic_definition,))
    raw = {"decision_version": 2, "source_goal_profile_hash": profile.profile_hash,
        "policy_version": CAPABILITY_POLICY.version, "route_kind": "narrow_goal", "status": "needs_verification",
        "learning_decisions": [{"capability_id": "ros2.action", "learning_requirement": "required",
            "project_usage": "optional", "desired_depth": "applied",
            "requirement_refs": [profile.required_requirements[0].requirement_id],
            "learning_target_refs": [profile.required_requirements[0].requirement_id],
            "project_usage_rationale": "该未知能力尚待验证，不要求应用于项目。",
            "selection_rationale": "需要该未知领域能力。"}],
        "claim_decisions": [], "constraint_effects": [], "clarification_questions": []}
    with pytest.raises(ValidationAppError):
        normalize_capability_decision(raw, profile=profile, verification_evidence=(cyclic_evidence,))


def test_constraint_exclusion_conflict_remains_pending_and_wrong_reference_is_rejected():
    profile = real_profile()
    raw = _base_decision(profile)
    raw["learning_decisions"][-1]["project_usage"] = "optional"
    raw["constraint_effects"][0] = {"constraint_ref": profile.hard_constraints[0].constraint_id,
        "capability_id": "mcp", "exclusion": "project"}
    pending = normalize_capability_decision(raw, profile=profile)
    assert isinstance(pending, CapabilityPlanningPending)
    assert "constraint_project_conflict" in {issue.code for issue in pending.issues}
    bad = _base_decision(profile)
    bad["constraint_effects"][0]["constraint_ref"] = "constraint_wrong"
    with pytest.raises(ValidationAppError):
        normalize_capability_decision(bad, profile=profile)


def test_unknown_domain_without_trusted_evidence_stays_pending():
    profile = __import__("backend.tests.unit.test_capability_planning", fromlist=["profile"]).profile("未知领域Agent")
    requirement = profile.required_requirements[0].requirement_id
    raw = {"decision_version": 2, "source_goal_profile_hash": profile.profile_hash,
        "policy_version": CAPABILITY_POLICY.version, "route_kind": "narrow_goal", "status": "needs_verification",
        "learning_decisions": [{"capability_id": "unknown.vendor.protocol", "learning_requirement": "required",
            "project_usage": "optional", "desired_depth": "applied", "requirement_refs": [requirement],
            "learning_target_refs": [requirement], "project_usage_rationale": "待验证前不作为正式项目集成要求。",
            "selection_rationale": "此协议需要来源验证。"}],
        "claim_decisions": [], "constraint_effects": [], "clarification_questions": []}
    result = normalize_capability_decision(raw, profile=profile)
    assert isinstance(result, CapabilityPlanningPending)
    assert result.status == "needs_verification"
    assert "unknown.vendor.protocol" in {ref for issue in result.issues for ref in issue.refs}


def test_standard_capability_plan_hash_and_coverage_gap_are_deterministic():
    profile = real_profile()
    raw = _base_decision(profile)
    first = normalize_capability_decision(raw, profile=profile)
    second = normalize_capability_decision(deepcopy(raw), profile=profile)
    assert first.plan_hash == second.plan_hash
    index = ReviewedContentIndex("empty", (), (), ())
    coverage = CoverageEvaluator().evaluate(first, index)
    gaps = extract(first, coverage)
    assert gaps.source_capability_plan_hash == first.plan_hash
    assert "python.core" not in {gap.capability_id for gap in gaps.gaps}


def test_decision_v2_is_explicit_in_manifest_and_legacy_product_v2_stays_v1():
    legacy = _manifest()
    assert purpose_schema(legacy, CAPABILITY_PURPOSE) == CAPABILITY_SCHEMA
    new = _manifest(capability_output_protocol=CAPABILITY_DECISION_PROTOCOL)
    assert manifest_intact(new)
    assert new["manifest_hash"] != legacy["manifest_hash"]
    assert purpose_schema(new, CAPABILITY_PURPOSE) == CAPABILITY_DECISION_SCHEMA
    changed = deepcopy(new)
    changed["capability_output_protocol"] = "unknown-protocol"
    from app.core.ids import content_hash
    changed["manifest_hash"] = content_hash({k: v for k, v in changed.items() if k != "manifest_hash"})
    assert not manifest_intact(changed)


def test_w5_request_plan_freezes_v2_schema_only_for_explicit_new_manifest():
    from scripts.planning_v2_scenario_a import request_plan

    legacy = _manifest()
    assert "schema_names" not in request_plan(legacy)
    decision = _manifest(capability_output_protocol=CAPABILITY_DECISION_PROTOCOL)
    assert request_plan(decision)["schema_names"][CAPABILITY_PURPOSE] == CAPABILITY_DECISION_SCHEMA


def test_decision_v2_provider_and_w5_planner_dispatch_exact_frozen_schema_with_mock_transport():
    profile = real_profile()
    raw = _base_decision(profile)
    captured = []

    def handle(request):
        body = json.loads(request.content)
        captured.append(body)
        assert body["model"] == "deepseek-flash"
        message_bytes = json.dumps(body["messages"], ensure_ascii=False, separators=(",", ":")).encode()
        assert len(message_bytes) <= 32768
        assert body["messages"][0]["content"] == CAPABILITY_DECISION_SYSTEM
        user = json.loads(body["messages"][1]["content"])
        assert user["schema"] == CAPABILITY_DECISION_SCHEMA
        assert user["field_shape"] == CAPABILITY_DECISION_SHAPE
        return httpx.Response(200, json={"model": "deepseek-flash",
            "choices": [{"message": {"content": json.dumps(raw, ensure_ascii=False)}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1}})

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        provider = OpenAICompatibleLLM(base_url="https://api.deepseek.com", api_key="mock",
                                       model="deepseek-flash", client=client)
        # Provider wire is exercised directly, then the same frozen schema is
        # asserted on the W5/application call path without real HTTP.
        provider_result = provider.generate_structured(purpose=CAPABILITY_PURPOSE,
            schema_name=CAPABILITY_DECISION_SCHEMA,
            payload={"profile": profile.to_payload(), "policy": CAPABILITY_POLICY.to_payload(),
                     "verification_evidence": []}, run_id="offline", attempt_id="one")
    assert provider_result.payload == raw and len(captured) == 1
    # A W5-bound call must choose from the already-frozen manifest, not infer
    # the newest protocol from product_semantics or deployment defaults.
    class FrozenCalls:
        manifest = _manifest(capability_output_protocol=CAPABILITY_DECISION_PROTOCOL)
        provider = OpenAICompatibleLLM(base_url="https://api.deepseek.com", api_key="mock",
                                      model="deepseek-flash")

        def request_options(self, purpose):
            return self.provider.request_options(purpose)

        def preflight(self, *, purpose, payload, schema_name):
            self.last_schema = schema_name
            return None

        def generate_structured(self, **kwargs):
            self.last_schema = kwargs["schema_name"]
            return LLMResult(raw, "deepseek-flash", "stop")

    calls = FrozenCalls()
    result = CapabilityPlanner(calls).plan(profile, run_id="offline", attempt_id="w5",
        output_protocol=CAPABILITY_DECISION_PROTOCOL)
    assert isinstance(result, CapabilityPlan)
    assert calls.last_schema == CAPABILITY_DECISION_SCHEMA


def test_new_decision_wire_does_not_copy_policy_owned_fields_or_duplicate_known_rows():
    assert set(CAPABILITY_DECISION_SHAPE) == {
        "decision_version", "source_goal_profile_hash", "policy_version", "route_kind", "status",
        "learning_decisions", "claim_decisions", "constraint_effects", "clarification_questions"}
    assert "accepted_known" not in json.dumps(CAPABILITY_DECISION_SHAPE)
    assert "policy_refs" not in json.dumps(CAPABILITY_DECISION_SHAPE)
    assert "prerequisite_refs" not in json.dumps(CAPABILITY_DECISION_SHAPE)
    assert "learning_outcomes" not in json.dumps(CAPABILITY_DECISION_SHAPE)

