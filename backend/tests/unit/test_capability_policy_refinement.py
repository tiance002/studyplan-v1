"""Policy v2 identity/scope contracts; no Coverage evaluator or reviewed mapping."""
import json
from copy import deepcopy
from dataclasses import asdict, fields, replace
from pathlib import Path

import pytest
from app.application.capability_planning import CapabilityPlanner
from app.core.ids import content_hash
from app.domain.planning.capabilities import (
    CAPABILITY_SCHEMA,
    Capability,
    CapabilityPlan,
    CapabilityPlanningPending,
    validate_capability_planning_input,
    verification_input_hash,
)
from app.domain.planning.capability_policy import CAPABILITY_POLICY
from app.ports.llm import LLMFailure

from backend.tests.unit.test_capability_planning import (
    Port,
    cap,
    evidence,
    known_python,
    plan,
    profile,
    wire,
)
from backend.tests.unit.test_capability_planning_provider import invoke, output, response, valid_payload

V1 = json.loads((Path(__file__).parents[1] / "fixtures/capability-policy-v1.json").read_text(encoding="utf-8"))["policy"]
SPLIT = {
    "python.core": ("program_structure", "data_structures", "exceptions"),
    "python.async": ("concurrency", "cancellation_lifecycle"),
    "json.cli": ("file_reading", "content_validation", "cli_errors"),
    "llm.api": ("exchange", "usage_cost", "failure_boundary"),
    "structured.output": ("contract_definition", "response_validation"),
    "tool.calling": ("input_validation", "invoke_result"),
    "agent.loop": ("advance", "stop_conditions", "failure_result"),
    "mcp": ("roles", "interfaces", "minimal_connection"),
    "github.api": ("objects", "pagination", "access_failures"),
}


def ids(outcomes):
    return tuple(o.outcome_id for o in outcomes)


@pytest.mark.parametrize("key,suffixes", SPLIT.items())
def test_independently_coverable_tasks_have_new_stable_outcome_identities(key, suffixes):
    definition = CAPABILITY_POLICY.get(key)
    assert ids(definition.learning_outcomes) == tuple(key + "." + suffix for suffix in suffixes)
    old = next(d for d in V1["definitions"] if d["capability_id"] == key)
    assert not set(ids(definition.learning_outcomes)) & {o["outcome_id"] for o in old["learning_outcomes"]}


@pytest.mark.parametrize("key", ["code.review", "error.permission", "eval.lite"])
def test_coherent_single_task_is_unchanged_and_need_not_be_split(key):
    old = next(d for d in V1["definitions"] if d["capability_id"] == key)
    assert [asdict(o) for o in CAPABILITY_POLICY.get(key).learning_outcomes] == old["learning_outcomes"]
    assert len(CAPABILITY_POLICY.get(key).learning_outcomes) == 1


@pytest.mark.parametrize("route,depth,practice", [
    ("systematic_agent_route", "foundation", True),
    ("systematic_agent_route", "applied", True),
    ("systematic_agent_route", "deep", True),
    ("narrow_goal", "foundation", False),
    ("other", "foundation", False),
    ("narrow_goal", "applied", True),
    ("narrow_goal", "deep", True),
    ("other", "applied", True),
])
def test_mcp_outcomes_follow_existing_route_and_depth_with_project_usage_independent(route, depth, practice):
    p = profile("了解MCP概念或按已冻结范围学习最小接入")
    result = plan(p, wire(p, cap(p, "mcp", desired_depth=depth, project_usage="excluded"), route_kind=route))
    assert isinstance(result, CapabilityPlan)
    mcp = result.learning_capabilities[0]
    expected = ("mcp.roles", "mcp.interfaces") + (("mcp.minimal_connection",) if practice else ())
    assert ids(mcp.learning_outcomes) == expected
    assert mcp.project_usage == "excluded" and mcp.learning_requirement == "required"
    assert mcp.desired_depth == depth


def test_uncertain_route_never_freezes_outcomes_into_ready_plan():
    p = profile()
    result = plan(p, wire(p, cap(p, "mcp", desired_depth="foundation"), route_kind="uncertain"))
    assert isinstance(result, CapabilityPlanningPending) and result.status == "needs_clarification"


def test_systematic_route_cannot_downgrade_required_mcp_learning():
    p = profile("系统学习Agent")
    result = plan(p, wire(p, cap(p, "mcp", learning_requirement="recommended", project_usage="optional"),
                          route_kind="systematic_agent_route"))
    assert isinstance(result, CapabilityPlanningPending)
    assert "systematic_mcp_required" in {issue.code for issue in result.issues}


def test_concept_and_applied_mcp_scopes_produce_different_frozen_hashes_without_new_schema():
    p = profile("学习MCP")
    concept = plan(p, wire(p, cap(p, "mcp", desired_depth="foundation", project_usage="optional")))
    applied = plan(p, wire(p, cap(p, "mcp", desired_depth="applied", project_usage="optional")))
    assert isinstance(concept, CapabilityPlan) and isinstance(applied, CapabilityPlan)
    assert concept.plan_hash != applied.plan_hash
    assert set(ids(concept.learning_outcomes)) < set(ids(applied.learning_outcomes))
    assert concept.source_goal_profile_hash == applied.source_goal_profile_hash == p.profile_hash


def test_policy_projection_declares_same_mcp_applicability_used_at_freeze():
    payload = CAPABILITY_POLICY.to_payload()
    rule = payload["outcome_selection"]["mcp"]
    assert rule["practice_outcome_id"] == "mcp.minimal_connection"
    assert rule["required_for_route_kinds"] == ["systematic_agent_route"]
    assert rule["required_for_depths"] == ["applied", "deep"]
    assert rule["concept_only_depth"] == "foundation"
    assert rule["project_usage_not_forced"] is True
    assert CAPABILITY_POLICY.outcomes_for(CAPABILITY_POLICY.get("mcp"), route_kind="narrow_goal",
                                         desired_depth="foundation") == CAPABILITY_POLICY.get("mcp").learning_outcomes[:2]


def test_other_policy_and_unknown_evidence_definitions_are_not_filtered_by_mcp_rule():
    p = profile("调用ROS2 Action")
    ev = evidence(p)
    unknown = plan(p, wire(p, cap(p, "ros2.action", desired_depth="foundation")), verification_evidence=(ev,))
    assert unknown.capabilities[0].learning_outcomes == ev.capabilities[0].learning_outcomes
    for key in ("code.review", "llm.api"):
        definition = CAPABILITY_POLICY.get(key)
        assert CAPABILITY_POLICY.outcomes_for(definition, route_kind="narrow_goal", desired_depth="foundation") == definition.learning_outcomes


def test_known_definitions_are_server_owned_and_accepted_known_stays_outside_learning():
    p = profile("会Python，学习Agent", claims=("会Python",))
    raw = wire(p, known_python(p), cap(p, "llm.api"), cap(p, "mcp", project_usage="optional"),
               route_kind="systematic_agent_route", claim_bindings=[
                   {"claim_ref": p.learner_claims[0].claim_id, "capability_id": "python.core"}])
    result = plan(p, raw)
    assert isinstance(result, CapabilityPlan)
    assert "python.core" not in {c.capability_id for c in result.learning_capabilities}
    assert not any(o.outcome_id.startswith("python.core.") for o in result.learning_outcomes)
    assert next(c for c in result.capabilities if c.capability_id == "llm.api").learning_outcomes == CAPABILITY_POLICY.get("llm.api").learning_outcomes
    raw["capabilities"][1]["learning_outcomes"] = [{"outcome_id": "fabricated", "text": "model override"}]
    assert isinstance(plan(p, raw), LLMFailure)


def test_v2_version_refs_stable_hash_and_immutable_v1_identity():
    assert CAPABILITY_POLICY.version == "v2"
    assert {d.capability_id for d in CAPABILITY_POLICY.definitions} == {d["capability_id"] for d in V1["definitions"]}
    assert all(d.policy_refs == (f"capability-policy:v2#{d.capability_id}",) for d in CAPABILITY_POLICY.definitions)
    assert CAPABILITY_POLICY.systematic_mcp_policy_ref == "capability-policy:v2#systematic-agent-mcp"
    p = profile()
    raw = wire(p, cap(p, "llm.api"), cap(p, "mcp", project_usage="optional"), route_kind="systematic_agent_route")
    first = plan(p, raw)
    second_raw = deepcopy(raw)
    second_raw["capabilities"].reverse()
    second = plan(p, second_raw)
    assert first.plan_hash == second.plan_hash and first.source_goal_profile_hash == p.profile_hash
    assert first.plan_hash == content_hash(asdict(first))
    assert first.plan_hash != replace(first, policy_version="v1").plan_hash
    assert verification_input_hash(p) != content_hash({"profile": p.to_payload(), "policy": V1})
    assert V1["policy_version"] == "v1"


def test_v1_wire_refs_and_evidence_cannot_be_consumed_as_current_v2():
    p = profile()
    raw = wire(p, cap(p, "llm.api"))
    assert isinstance(plan(p, raw | {"policy_version": "v1"}), LLMFailure)
    old_ref = deepcopy(raw)
    old_ref["capabilities"][0]["policy_refs"] = ["capability-policy:v1#llm.api"]
    assert isinstance(plan(p, old_ref), LLMFailure)
    old_evidence = replace(evidence(p), input_hash=content_hash({"profile": p.to_payload(), "policy": V1}))
    port = Port(LLMFailure("never", "must not dispatch"))
    result = CapabilityPlanner(port).plan(p, run_id="r", attempt_id="a", verification_evidence=(old_evidence,))
    assert isinstance(result, LLMFailure) and not port.calls
    assert not validate_capability_planning_input({"profile": p.to_payload(), "policy": V1, "verification_evidence": []}, CAPABILITY_SCHEMA)


def test_provider_receives_v2_policy_scope_and_rejects_actual_v1_snapshot_before_http():
    payload = valid_payload()
    assert payload["policy"]["policy_version"] == "v2"
    result, calls, _ = invoke(lambda request: response(json.dumps(output(payload))), payload=payload)
    assert len(calls) == 1
    body = json.loads(calls[0].content)
    assert json.loads(body["messages"][1]["content"])["context"]["policy"] == CAPABILITY_POLICY.to_payload()
    assert "policy.outcome_selection" in body["messages"][0]["content"]
    assert result.payload["policy_version"] == "v2"
    failure, calls, _ = invoke(lambda request: pytest.fail("v1 must not dispatch"), payload=payload | {"policy": V1})
    assert isinstance(failure, LLMFailure) and not calls


@pytest.mark.parametrize("key", ["tool.calling", "agent.loop", "mcp"])
def test_minimal_future_item3_partition_can_keep_independent_missing_identity_without_evaluator(key):
    # Set contract only: no content fixtures/mapping or Coverage implementation.
    p = profile("按冻结范围学习工具能力")
    dependencies = {"tool.calling": ("llm.api",), "agent.loop": ("llm.api", "tool.calling"), "mcp": ()}
    frozen = plan(p, wire(p, *(cap(p, c) for c in (*dependencies[key], key))))
    assert isinstance(frozen, CapabilityPlan)
    capability = next(c for c in frozen.learning_capabilities if c.capability_id == key)
    outcomes = set(ids(capability.learning_outcomes))
    first_id = capability.learning_outcomes[0].outcome_id
    covered, missing = {first_id}, outcomes - {first_id}
    assert covered and missing and not covered & missing and covered | missing == outcomes


def test_refinement_does_not_change_capability_plan_or_capability_schema():
    assert {f.name for f in fields(CapabilityPlan)} == {
        "schema_version", "source_goal_profile_hash", "policy_version", "route_kind", "capabilities",
        "claim_bindings", "constraint_effects", "verification_evidence"}
    assert {f.name for f in fields(Capability)} == {
        "capability_id", "title", "disposition", "learning_requirement", "project_usage", "desired_depth",
        "learning_outcomes", "requirement_refs", "policy_refs", "learner_claim_refs", "prerequisite_refs", "learning_target_refs"}
