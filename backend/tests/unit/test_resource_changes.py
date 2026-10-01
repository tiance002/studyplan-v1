"""Replacement semantics reuse immutable plans and exact business identities."""
from dataclasses import replace

import pytest
from app.core.errors import ValidationAppError
from app.domain.enums import OutlineSectionKind
from app.domain.planning.models import PlanDraft, PlanStage, revision_from_draft
from app.domain.resource_changes import ResourceChangeCommand


def command(**overrides):
    values = dict(project_id="p", plan_id="plan", stage_id="stage", assignment_id="assignment",
                  source_ref="source", source_version=2, section_refs=("a", "b"), expected_version=1,
                  copy_policy="copy_active", idempotency_key="preview-key")
    return ResourceChangeCommand(**(values | overrides))


def test_copy_policy_and_ordered_sections_are_explicit_semantics():
    original = command()
    assert original.input_hash() == replace(original, idempotency_key="another").input_hash()
    assert len({original.input_hash(), command(section_refs=("b", "a")).input_hash(),
                command(copy_policy="keep_history_only").input_hash(),
                command(expected_version=2).input_hash()}) == 4
    for values in ({"copy_policy": "implicit"}, {"source_version": 0}, {"section_refs": ()},
                   {"section_refs": ("a", "a")}, {"expected_version": True}):
        with pytest.raises(ValidationAppError):
            command(**values)


def test_frozen_resource_metadata_survives_remap_and_participates_in_hash():
    from app.domain.enums import StageResourceRole
    from app.domain.resources.curation import StageResourceAssignment

    stage = PlanStage("old-stage", "semantic-stage", "Stage", OutlineSectionKind.CORE, 0)
    assignment = StageResourceAssignment.create(project_id="p", stage_id=stage.stage_id,
        role=StageResourceRole.PRIMARY, source_ref="source", section_refs=("a",), source_version=2)
    snapshot = {"assignment_id": assignment.assignment_id, "stage_id": stage.stage_id,
        "stage_key": stage.stable_key, "role": "primary", "order_index": 0,
        "source_ref": "source", "source_version": 2, "snapshot_status": "frozen",
        "source": {"title": "Frozen title", "canonical_url": "https://example.com/original"},
        "sections": [{"section_id": "a", "title": "Original section", "url": "https://example.com/a"}]}
    draft = PlanDraft("draft", "p", "", "goal", 2, stages=(stage,), stage_resources=(assignment,),
                      resource_snapshots=(snapshot,))
    first = revision_from_draft(draft, revision=2)
    second = revision_from_draft(draft, revision=2)
    assert first.structure_fingerprint() == second.structure_fingerprint()
    frozen = first.resource_snapshots[0]
    assert frozen["stage_id"] == first.stages[0].stage_id != stage.stage_id
    assert frozen["assignment_id"] == first.stage_resources[0].assignment_id != assignment.assignment_id
    assert frozen["source"] == snapshot["source"]
    changed = replace(draft, resource_snapshots=({**snapshot, "source": {"title": "Changed title"}},))
    assert changed.content_hash != draft.content_hash
