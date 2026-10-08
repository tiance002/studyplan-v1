"""Deterministic coverage contracts; synthetic review fixtures are not real reviews."""
from copy import deepcopy
from dataclasses import asdict, replace

import pytest
from app.core.errors import ValidationAppError
from app.core.ids import content_hash
from app.domain.planning.content_coverage import (
    CoverageEvaluator,
    CoverageResultValidator,
    OutcomeMapping,
    ReviewedContentIndex,
    ReviewedSection,
    ReviewEvidence,
)

from backend.tests.unit.test_capability_planning import cap, evidence, known_python, plan, profile, wire

TOOL = ("tool.calling.input_validation", "tool.calling.invoke_result")


def frozen_tool():
    p = profile("学习工具调用")
    return plan(p, wire(p, cap(p, "llm.api"), cap(p, "tool.calling")))


def reviewed_index(outcomes=(), *, source_status="reviewed", status="reviewed", depth="selected_sections_read"):
    ref = "fixture:review:section-one"
    review = ReviewEvidence(ref, content_hash({"fixture": "review record"}), ("sec_fixture",), tuple(outcomes),
                            "selected_sections_read", ("Synthetic review; not real teaching acceptance",))
    section = ReviewedSection("fixture.content", 1, content_hash({"fixture": "content"}), "src_fixture", 1,
                              "sec_fixture", source_status, status, depth, (ref,))
    mappings = tuple(OutcomeMapping(o, "fixture.content", 1, "src_fixture", 1, "sec_fixture", (ref,)) for o in outcomes)
    return ReviewedContentIndex("fixture-index-v1", (section,), mappings, (review,))


def entry(result, key="tool.calling"):
    return next(e for e in result.entries if e.capability_id == key)


def test_parameter_validation_only_support_is_partial_and_complete_partition():
    result = CoverageEvaluator().evaluate(frozen_tool(), reviewed_index(TOOL[:1]))
    item = entry(result)
    assert item.coverage == "partial"
    assert item.covered_outcomes == TOOL[:1] and item.missing_outcomes == TOOL[1:]
    assert not set(item.covered_outcomes) & set(item.missing_outcomes)
    assert set(item.covered_outcomes) | set(item.missing_outcomes) == set(TOOL)


def test_all_supported_outcomes_full_and_same_section_is_reused_once():
    result = CoverageEvaluator().evaluate(frozen_tool(), reviewed_index(TOOL))
    item = entry(result)
    assert item.coverage == "full" and not item.missing_outcomes and set(item.covered_outcomes) == set(TOOL)
    assert len(item.content_refs) == 1
    assert set(item.content_refs[0].outcome_ids) == set(TOOL)
    assert item.content_refs[0].section.section_id == "sec_fixture"


def test_no_mapping_is_normal_none_with_all_outcomes_missing():
    result = CoverageEvaluator().evaluate(frozen_tool(), ReviewedContentIndex("empty", (), (), ()))
    item = entry(result)
    assert item.coverage == "none" and not item.covered_outcomes and not item.content_refs
    assert set(item.missing_outcomes) == set(TOOL)


def test_unmapped_candidate_or_toc_metadata_does_not_prove_coverage():
    index = reviewed_index(source_status="candidate", status="legacy_index", depth="toc_checked")
    result = CoverageEvaluator().evaluate(frozen_tool(), index)
    assert all(e.coverage == "none" for e in result.entries)


def test_accepted_known_never_creates_coverage_entry_and_plan_is_not_mutated():
    p = profile("会Python，学习JSON CLI", claims=("会Python",))
    frozen = plan(p, wire(p, known_python(p), cap(p, "json.cli"), claim_bindings=[
        {"claim_ref": p.learner_claims[0].claim_id, "capability_id": "python.core"}]))
    before = deepcopy(frozen.to_payload())
    index = reviewed_index(("python.core.program_structure",))
    result = CoverageEvaluator().evaluate(frozen, index)
    assert [e.capability_id for e in result.entries] == ["json.cli"]
    assert frozen.to_payload() == before
    assert result.source_capability_plan_hash == frozen.plan_hash


@pytest.mark.parametrize("source_status,status,depth", [
    ("candidate", "reviewed", "selected_sections_read"),
    ("reviewed", "legacy_index", "selected_sections_read"),
    ("reviewed", "reviewed", "toc_checked"),
])
def test_mapped_unqualified_records_are_explicit_integrity_errors(source_status, status, depth):
    index = reviewed_index(TOOL[:1], source_status=source_status, status=status, depth=depth)
    with pytest.raises(ValidationAppError):
        CoverageEvaluator().evaluate(frozen_tool(), index)


@pytest.mark.parametrize("field,value", [
    ("source_version", 2), ("content_version", 2), ("source_id", "wrong"),
    ("section_id", "missing"), ("content_id", "wrong"), ("review_refs", ("missing-review",)),
])
def test_mapping_identity_version_and_evidence_mismatch_is_not_quiet_missing(field, value):
    index = reviewed_index(TOOL[:1])
    index = replace(index, mappings=(replace(index.mappings[0], **{field: value}),))
    with pytest.raises(ValidationAppError):
        CoverageEvaluator().evaluate(frozen_tool(), index)


@pytest.mark.parametrize("changes", [
    {"sha256": "bad"}, {"section_ids": ("other-section",)},
    {"supported_outcomes": (TOOL[1],)}, {"review_depth": "readme_read"},
])
def test_invalid_or_insufficient_evidence_cannot_support_covered(changes):
    index = reviewed_index(TOOL[:1])
    with pytest.raises(ValidationAppError):
        broken = replace(index, evidence=(replace(index.evidence[0], **changes),))
        CoverageEvaluator().evaluate(frozen_tool(), broken)


@pytest.mark.parametrize("changes", [
    {"policy_version": "v1"}, {"schema_version": 2}, {"source_goal_profile_hash": "bad"},
    {"route_kind": "uncertain"},
])
def test_invalid_or_wrong_version_plan_is_rejected(changes):
    with pytest.raises(ValidationAppError):
        CoverageEvaluator().evaluate(replace(frozen_tool(), **changes), reviewed_index())


def test_forged_outcome_or_duplicate_capability_cannot_be_covered():
    frozen = frozen_tool()
    tool = next(c for c in frozen.capabilities if c.capability_id == "tool.calling")
    wrong = replace(tool, learning_outcomes=tool.learning_outcomes[:1])
    for caps in (tuple(wrong if c.capability_id == tool.capability_id else c for c in frozen.capabilities),
                 frozen.capabilities + (tool,)):
        with pytest.raises(ValidationAppError):
            CoverageEvaluator().evaluate(replace(frozen, capabilities=caps), reviewed_index())


def test_v1_outcome_index_is_rejected_without_automatic_upgrade():
    with pytest.raises(ValidationAppError):
        CoverageEvaluator().evaluate(frozen_tool(), replace(reviewed_index(), policy_version="v1"))


@pytest.mark.parametrize("outcome_id", ["mcp.protocol", "tool.calling.dispatch", "tool.calling.typo"])
def test_v2_label_cannot_hide_old_or_invalid_mapped_outcome_identity(outcome_id):
    # Even self-consistent evidence cannot grant authority to a stale/typo ID.
    index = reviewed_index((outcome_id,))
    with pytest.raises(ValidationAppError):
        CoverageEvaluator().evaluate(frozen_tool(), index)


@pytest.mark.parametrize("change", ["overlap", "omitted", "false_full", "extra_capability", "wrong_source_hash"])
def test_result_validator_rejects_incomplete_or_tampered_partition(change):
    frozen, index = frozen_tool(), reviewed_index(TOOL[:1])
    result = CoverageEvaluator().evaluate(frozen, index)
    item = entry(result)
    if change == "wrong_source_hash":
        result = replace(result, source_capability_plan_hash="0" * 64)
    elif change == "extra_capability":
        result = replace(result, entries=result.entries + (replace(item, capability_id="python.core"),))
    else:
        changed = {"overlap": replace(item, missing_outcomes=TOOL),
                   "omitted": replace(item, missing_outcomes=()),
                   "false_full": replace(item, coverage="full")}[change]
        result = replace(result, entries=tuple(changed if e.capability_id == item.capability_id else e for e in result.entries))
    with pytest.raises(ValidationAppError):
        CoverageResultValidator().validate(result, plan=frozen, index=index)


def test_stable_sorted_result_hash_and_serialization_with_frozen_inputs():
    frozen, index = frozen_tool(), reviewed_index(TOOL)
    first = CoverageEvaluator().evaluate(frozen, index)
    second = CoverageEvaluator().evaluate(frozen, replace(index, mappings=tuple(reversed(index.mappings))))
    assert first.to_payload() == second.to_payload()
    assert first.result_hash == content_hash(asdict(first))
    assert first.content_index_version == index.version and first.content_index_hash == index.index_hash
    assert CoverageResultValidator().validate(first, plan=frozen, index=index) == first


@pytest.mark.parametrize("mapped", [False, True])
def test_verified_unknown_capability_uses_bound_outcome_identity_without_model_guessing(mapped):
    p = profile("调用ROS2 Action")
    frozen = plan(p, wire(p, cap(p, "ros2.action")), verification_evidence=(evidence(p),))
    index = reviewed_index(("ros2.action.lifecycle",)) if mapped else ReviewedContentIndex("empty", (), (), ())
    result = CoverageEvaluator().evaluate(frozen, index)
    assert result.entries[0].coverage == ("full" if mapped else "none")
    assert result.entries[0].missing_outcomes == (() if mapped else ("ros2.action.lifecycle",))
