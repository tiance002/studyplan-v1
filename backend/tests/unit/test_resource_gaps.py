"""Item4 exact frozen missing outcomes; no research or content re-review."""
from copy import deepcopy
from dataclasses import asdict, replace

import pytest
from app.core.errors import ValidationAppError
from app.core.ids import content_hash
from app.domain.planning.capabilities import CapabilityPlan
from app.domain.planning.content_coverage import CoverageEvaluator, CoverageResult
from app.domain.planning.resource_gaps import ResourceGapSet, extract
from app.infrastructure.reviewed_content_coverage import load_reviewed_content_index

from backend.tests.unit.test_capability_planning import cap, known_python, plan, profile, wire
from backend.tests.unit.test_content_coverage import TOOL, frozen_tool, reviewed_index
from backend.tests.unit.test_reviewed_content_coverage import mcp_plan


def covered(plan, outcomes=()):
    return CoverageEvaluator().evaluate(plan, reviewed_index(outcomes))


def corrupt(record, **fields):
    # Constructors normalize producer output. Deliberately forge frozen state to
    # verify consumer rejection rather than accidentally testing normalization.
    record = deepcopy(record)
    for key, value in fields.items():
        object.__setattr__(record, key, value)
    return record


@pytest.mark.parametrize("depth,expected", [("foundation", ()), ("applied", ("mcp.minimal_connection",))])
def test_real_item3_mcp_index_full_or_partial_is_exact_gap_interface(depth, expected):
    frozen = mcp_plan(depth)
    coverage = CoverageEvaluator().evaluate(frozen, load_reviewed_content_index())
    result = extract(frozen, coverage)
    assert isinstance(result, ResourceGapSet)
    assert tuple(o.outcome_id for gap in result.gaps for o in gap.missing_outcomes) == expected
    assert len(result.gaps) == (1 if expected else 0)
    assert result.source_capability_plan_hash == frozen.plan_hash
    assert result.source_coverage_result_hash == coverage.result_hash
    if expected:
        original = next(c for c in frozen.learning_capabilities if c.capability_id == "mcp")
        assert result.gaps[0].missing_outcomes == tuple(o for o in original.learning_outcomes if o.outcome_id in expected)


def test_none_groups_both_tool_outcomes_and_preserves_exact_text():
    frozen = frozen_tool()
    result = extract(frozen, covered(frozen))
    tool = next(g for g in result.gaps if g.capability_id == "tool.calling")
    original = next(c for c in frozen.capabilities if c.capability_id == "tool.calling")
    assert tuple(o.outcome_id for o in tool.missing_outcomes) == TOOL
    assert tool.missing_outcomes == original.learning_outcomes
    assert tool.requirement_refs == original.requirement_refs
    assert len([g for g in result.gaps if g.capability_id == "tool.calling"]) == 1


def test_accepted_known_python_never_has_gap_and_b_still_keeps_missing():
    p = profile("会Python，学习JSON CLI", claims=("会Python",))
    frozen = plan(p, wire(p, known_python(p), cap(p, "json.cli"), claim_bindings=[
        {"claim_ref": p.learner_claims[0].claim_id, "capability_id": "python.core"}]))
    result = extract(frozen, covered(frozen))
    assert [g.capability_id for g in result.gaps] == ["json.cli"]
    original = next(c for c in frozen.capabilities if c.capability_id == "json.cli")
    assert result.gaps[0].missing_outcomes == tuple(sorted(original.learning_outcomes, key=lambda o: o.outcome_id))


def test_importance_depth_and_policy_only_empty_requirement_refs_are_preserved():
    p = profile("系统学习Agent")
    frozen = plan(p, wire(p,
        cap(p, "llm.api", learning_requirement="recommended", desired_depth="foundation"),
        cap(p, "mcp", requirement_refs=[], desired_depth="deep", project_usage="excluded"),
        route_kind="systematic_agent_route"))
    result = extract(frozen, covered(frozen))
    for gap in result.gaps:
        original = next(c for c in frozen.learning_capabilities if c.capability_id == gap.capability_id)
        assert (gap.importance, gap.desired_depth, gap.requirement_refs) == (
            original.learning_requirement, original.desired_depth, original.requirement_refs)
    mcp = next(g for g in result.gaps if g.capability_id == "mcp")
    assert mcp.importance == "required" and mcp.requirement_refs == ()
    assert next(g for g in result.gaps if g.capability_id == "llm.api").importance == "recommended"


def test_all_full_is_legal_empty_set_and_does_not_invent_research():
    frozen = frozen_tool()
    outcomes = tuple(o.outcome_id for o in frozen.learning_outcomes)
    result = extract(frozen, covered(frozen, outcomes))
    assert result.gaps == () and result.to_payload()["gaps"] == []


def test_all_accepted_known_empty_b_is_legal_empty_gap_set():
    p = profile("已会Python", claims=("会Python",))
    frozen = plan(p, wire(p, known_python(p), claim_bindings=[
        {"claim_ref": p.learner_claims[0].claim_id, "capability_id": "python.core"}]))
    coverage = covered(frozen)
    assert coverage.entries == () and extract(frozen, coverage).gaps == ()


@pytest.mark.parametrize("change", ["source_binding", "plan_hash", "coverage_hash", "raw_claimed_hash"])
def test_invalid_source_or_claimed_hash_is_rejected(change, monkeypatch):
    frozen = frozen_tool()
    coverage = covered(frozen)
    if change == "source_binding":
        coverage = replace(coverage, source_capability_plan_hash="0" * 64)
    elif change == "raw_claimed_hash":
        coverage = coverage.to_payload() | {"result_hash": "0" * 64}
    elif change == "plan_hash":
        monkeypatch.setattr(CapabilityPlan, "plan_hash", property(lambda _: "0" * 64))
        coverage = replace(coverage, source_capability_plan_hash="0" * 64)
    else:
        monkeypatch.setattr(CoverageResult, "result_hash", property(lambda _: "0" * 64))
    with pytest.raises(ValidationAppError):
        extract(frozen, coverage)


@pytest.mark.parametrize("change", ["v1", "profile_hash", "outcome_id", "outcome_text"])
def test_invalid_or_stale_plan_is_rejected_without_replanning(change):
    frozen = frozen_tool()
    coverage = covered(frozen)
    if change in {"v1", "profile_hash"}:
        frozen = replace(frozen, **({"policy_version": "v1"} if change == "v1" else {"source_goal_profile_hash": "bad"}))
    else:
        tool = next(c for c in frozen.capabilities if c.capability_id == "tool.calling")
        outcome = replace(tool.learning_outcomes[0], **(
            {"outcome_id": "tool.calling.dispatch"} if change == "outcome_id" else {"text": "改写学习目标"}))
        altered = replace(tool, learning_outcomes=(outcome,) + tool.learning_outcomes[1:])
        frozen = replace(frozen, capabilities=tuple(altered if c == tool else c for c in frozen.capabilities))
        coverage = replace(coverage, source_capability_plan_hash=frozen.plan_hash)
    with pytest.raises(ValidationAppError):
        extract(frozen, coverage)


@pytest.mark.parametrize("change", ["extra_entry", "duplicate_entry", "omitted_entry", "wrong_id", "old_id",
                                    "duplicate_outcome", "omitted_outcome", "overlap", "wrong_status",
                                    "index_version", "index_hash", "section_version"])
def test_invalid_coverage_identity_partition_or_metadata_is_rejected(change):
    frozen = frozen_tool()
    coverage = covered(frozen, TOOL[:1])
    tool = next(e for e in coverage.entries if e.capability_id == "tool.calling")
    if change == "extra_entry":
        coverage = replace(coverage, entries=coverage.entries + (replace(tool, capability_id="python.core"),))
    elif change == "duplicate_entry":
        coverage = replace(coverage, entries=coverage.entries + (tool,))
    elif change == "omitted_entry":
        coverage = replace(coverage, entries=(tool,))
    elif change in {"index_version", "index_hash"}:
        coverage = corrupt(coverage, **({"content_index_version": ""} if change == "index_version" else {"content_index_hash": "bad"}))
    else:
        changes = {"wrong_id": {"missing_outcomes": ("agent.loop.advance",)},
                   "old_id": {"missing_outcomes": ("tool.calling.dispatch",)},
                   "duplicate_outcome": {"missing_outcomes": (TOOL[1], TOOL[1])},
                   "omitted_outcome": {"missing_outcomes": ()},
                   "overlap": {"missing_outcomes": TOOL},
                   "wrong_status": {"coverage": "full"}}
        if change == "section_version":
            ref = tool.content_refs[0]
            changes[change] = {"content_refs": (replace(ref, section=corrupt(ref.section, source_version=0)),)}
        altered = corrupt(tool, **changes[change])
        coverage = corrupt(coverage, entries=tuple(altered if e == tool else e for e in coverage.entries))
    with pytest.raises(ValidationAppError):
        extract(frozen, coverage)


def test_same_frozen_inputs_have_stable_hash_and_no_input_mutation():
    frozen = frozen_tool()
    coverage = covered(frozen, TOOL[:1])
    before = deepcopy((frozen.to_payload(), coverage.to_payload()))
    first = extract(frozen, coverage)
    second = extract(frozen, coverage)
    assert first.to_payload() == second.to_payload()
    assert first.result_hash == content_hash(asdict(first))
    assert (frozen.to_payload(), coverage.to_payload()) == before
    assert set(first.to_payload()) == {"source_capability_plan_hash", "source_coverage_result_hash", "gaps", "result_hash"}
    assert set(first.to_payload()["gaps"][0]) == {"capability_id", "missing_outcomes", "importance", "desired_depth", "requirement_refs"}
