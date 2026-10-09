"""Retained request 186 and independent synthetic bindings; no model quality proof."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import httpx
import pytest
from app.application.capability_planning import CapabilityPlanner
from app.core.errors import ValidationAppError
from app.domain.planning.capabilities import CapabilityPlan, CapabilityPlanValidator
from app.domain.planning.capability_policy import CAPABILITY_POLICY
from app.infrastructure.providers.capability_planning_contract import CAPABILITY_SHAPE, CAPABILITY_SYSTEM
from app.infrastructure.providers.openai_compatible import OpenAICompatibleLLM

from backend.tests.unit.test_item2_real_failure_contract import real_profile, synthetic_selection

FIXTURE = Path(__file__).parents[1] / "fixtures/planning_v2/item2_requirement_binding_failure.json"
PACKET = json.loads(FIXTURE.read_text(encoding="utf-8"))
APPLICATION = "req_31f0e2d9e8cedf68a82afaa4d2a24a69caca334d808b1d3e2428501284b89121"
PURPOSE = "req_ef9a96e06fdb82a3b722992b257e488669318f9820ae438c433808b60b87491a"


@pytest.mark.parametrize(
    "rules",
    [
        ("输出最终JSON前", "逐个遍历profile.required_requirements", "稳定requirement_id", "遗漏任何一条"),
        ("项目应用需求", "用途/深度规划条件", "技术学习目标"),
        (
            "项目应用由实际承担能力",
            "把这些能力加入",
            "structured.output",
            "tool.calling",
            "学习成果用途是学习",
        ),
        ("禁止把所有requirement_id复制到所有能力", "不能转移到MCP"),
        ("覆盖检查", "不证明语义正确"),
    ],
)
def test_prompt_requires_explicit_per_id_preoutput_binding_review(rules):
    assert all(rule in CAPABILITY_SYSTEM for rule in rules)


def test_retained_186_rejects_unchanged_with_exact_coverage_failure():
    before = deepcopy(PACKET)
    raw = PACKET["failed_capability_response"]
    with pytest.raises(ValidationAppError) as error:
        CapabilityPlanValidator().validate(raw, profile=real_profile())
    assert error.value.details["field"] == "required_requirement_coverage"
    assert PACKET == before
    assert {c["capability_id"] for c in raw["capabilities"]} == {
        "python.core",
        "llm.api",
        "structured.output",
        "tool.calling",
        "mcp",
    }
    covered = {r for c in raw["capabilities"] for r in c["requirement_refs"]}
    assert {r.requirement_id for r in real_profile().required_requirements} - covered == {
        APPLICATION,
        PURPOSE,
    }
    root = Path(__file__).parents[3]
    for source in PACKET["sources"]:
        path = root / source["path"]
        if path.exists():  # Portable fixture remains usable when local var evidence is absent.
            assert hashlib.sha256(path.read_bytes()).hexdigest() == source["sha256"]
    response_path = root / PACKET["sources"][0]["path"]
    if response_path.exists():
        response = json.loads(response_path.read_text(encoding="utf-8"))
        assert json.loads(response["choices"][0]["message"]["content"]) == raw


def test_fresh_synthetic_five_capabilities_cover_six_requirements_semantically():
    p = real_profile()
    before = p.to_payload()
    raw = synthetic_selection(p)
    raw_before = deepcopy(raw)
    plan = CapabilityPlanValidator().validate(raw, profile=p)
    assert isinstance(plan, CapabilityPlan)
    assert len(plan.capabilities) == 5 and len(p.required_requirements) == 6
    assert {c.capability_id for c in plan.capabilities} == {
        c["capability_id"] for c in PACKET["failed_capability_response"]["capabilities"]
    }
    assert {r.requirement_id for r in p.required_requirements} == {
        r for c in plan.capabilities for r in c.requirement_refs
    }
    by_id = {c.capability_id: c for c in plan.capabilities}
    for key in ("structured.output", "tool.calling"):
        assert {APPLICATION, PURPOSE} <= set(by_id[key].requirement_refs)
    metadata = {
        r.requirement_id
        for r in p.required_requirements
        if r.text in ("学习成果用途是学习", "学习深度为应用级", "把这些能力加入我现有的待办事项 CLI")
    }
    assert not metadata & {r for c in plan.capabilities for r in c.learning_target_refs}
    assert by_id["mcp"].requirement_refs == by_id["mcp"].learning_target_refs == ()
    assert by_id["mcp"].learning_requirement == "required" and by_id["mcp"].project_usage == "optional"
    assert CAPABILITY_POLICY.systematic_mcp_policy_ref in by_id["mcp"].policy_refs
    assert by_id["python.core"].disposition == "accepted_known"
    assert by_id["python.core"].learner_claim_refs == (p.learner_claims[0].claim_id,)
    assert plan.plan_hash == CapabilityPlanValidator().validate(deepcopy(raw), profile=p).plan_hash
    assert raw == raw_before and p.to_payload() == before


@pytest.mark.parametrize("omitted", [(APPLICATION,), (PURPOSE,), (APPLICATION, PURPOSE)])
def test_omitting_application_or_purpose_still_rejects(omitted):
    p = real_profile()
    raw = synthetic_selection(p)
    for c in raw["capabilities"]:
        c["requirement_refs"] = [r for r in c["requirement_refs"] if r not in omitted]
    with pytest.raises(ValidationAppError) as error:
        CapabilityPlanValidator().validate(raw, profile=p)
    assert error.value.details["field"] == "required_requirement_coverage"


@pytest.mark.parametrize("bad", ["policy", "prerequisite", "profile"])
def test_binding_fix_preserves_definition_and_source_identity_rejection(bad):
    p = real_profile()
    raw = synthetic_selection(p)
    item = next(c for c in raw["capabilities"] if c["capability_id"] == "structured.output")
    if bad == "policy":
        item["policy_refs"] = ["capability-policy:v2#tool.calling"]
    elif bad == "prerequisite":
        item["prerequisite_refs"] = []
    else:
        raw["source_goal_profile_hash"] = "0" * 64
    with pytest.raises(ValidationAppError) as error:
        CapabilityPlanValidator().validate(raw, profile=p)
    assert error.value.details["field"] == ("source_identity" if bad == "profile" else "definition_refs")


def synthetic_bad_binding(p, bad):
    """Fresh review witness, never a modified retained Provider response."""
    raw = synthetic_selection(p)
    mcp = next(c for c in raw["capabilities"] if c["capability_id"] == "mcp")
    if bad == "learn_as_mcp_target":
        mcp["requirement_refs"] = [PURPOSE]
        mcp["learning_target_refs"] = [PURPOSE]
    elif bad == "application_to_mcp":
        for c in raw["capabilities"]:
            c["requirement_refs"] = [r for r in c["requirement_refs"] if r != APPLICATION]
        mcp["requirement_refs"] = [APPLICATION]
    elif bad == "all_ids_everywhere":
        for c in raw["capabilities"]:
            c["requirement_refs"] = [r.requirement_id for r in p.required_requirements]
    else:
        definition = CAPABILITY_POLICY.get("json.cli")
        background = next(r.requirement_id for r in p.required_requirements if r.text == p.project_context)
        raw["capabilities"].append(
            dict(
                capability_id="json.cli",
                disposition="needs_learning",
                learning_requirement="required",
                project_usage="required",
                desired_depth="applied",
                requirement_refs=[background],
                policy_refs=list(definition.policy_refs),
                prerequisite_refs=list(definition.real_prerequisites),
                learner_claim_refs=[],
                learning_target_refs=[],
            )
        )
    return raw


@pytest.mark.parametrize(
    "bad", ["learn_as_mcp_target", "application_to_mcp", "all_ids_everywhere", "new_json_cli"]
)
def test_semantically_bad_synthetic_witness_can_pass_mechanical_validator(bad):
    """These are REVIEW FAIL witnesses, never evidence of semantic acceptance.

    Independent human/agent review must reject them. No production semantic
    validator is introduced: reference coverage cannot establish meaning.
    """
    p = real_profile()
    raw = synthetic_bad_binding(p, bad)
    assert isinstance(CapabilityPlanValidator().validate(raw, profile=p), CapabilityPlan)


def test_actual_provider_mocktransport_loads_new_prompt_and_unchanged_profile_below_32k():
    """Actual adapter and planner, synthetic reply, zero external dispatch."""
    p = real_profile()
    before = p.to_payload()
    raw = synthetic_selection(p)
    calls = []

    def handle(request):
        body = json.loads(request.content)
        calls.append(body)
        assert len(json.dumps(body["messages"], ensure_ascii=False, separators=(",", ":")).encode()) <= 32768
        assert body["model"] == "deepseek-flash" and body["max_tokens"] == 4096
        assert body["thinking"] == {"type": "disabled"}
        assert body["messages"][0]["content"] == CAPABILITY_SYSTEM
        context = json.loads(body["messages"][1]["content"])
        assert context["context"]["profile"] == before and context["field_shape"] == CAPABILITY_SHAPE
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
                base_url="https://api.deepseek.com",
                api_key="mock",
                model="deepseek-flash",
                client=client,
            )
        ).plan(p, run_id="offline-requirement-binding", attempt_id="synthetic-one")
    assert isinstance(result, CapabilityPlan) and len(calls) == 1
    assert p.to_payload() == before
