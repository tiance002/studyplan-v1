"""Optional project input must preserve old hashes and existing publication shape."""
from dataclasses import replace

import pytest
from app.api.v1.schemas import PlanGenerateRequest
from app.core.errors import ValidationAppError
from app.core.ids import canonical_json, content_hash
from app.domain.enums import OutlineSectionKind
from app.domain.planning.intent import GoalSpec, goal_spec_from_payload, goal_spec_payload
from app.domain.planning.models import PlanDraft, PlanStage, revision_from_draft
from app.infrastructure.db.plan_repository import _draft_payload, _structure_payload


def test_empty_project_context_preserves_legacy_six_field_payload_and_hash():
    expected = {"target": "Agent", "scope": (), "desired_depth": "unspecified",
                "starting_point": "", "outcome_purpose": "learn", "constraints": ()}
    before = GoalSpec("Agent")
    assert goal_spec_payload(before) == expected
    assert content_hash(goal_spec_payload(before)) == content_hash(expected)
    assert goal_spec_payload(GoalSpec("Agent", project_context=None)) == expected
    assert goal_spec_payload(GoalSpec("Agent", project_context="  ")) == expected
    assert goal_spec_from_payload(expected) == before


def test_project_context_roundtrips_request_and_own_field():
    spec = GoalSpec("Agent", project_context="  已有旅行 Agent  ")
    request = PlanGenerateRequest(goal="Agent", goal_spec=spec)
    restored = goal_spec_from_payload(request.goal_spec.model_dump(mode="json"))
    assert restored == spec and spec.project_context == "已有旅行 Agent"
    assert goal_spec_payload(spec)["project_context"] == spec.project_context
    assert spec.target == "Agent" and spec.constraints == ()


@pytest.mark.parametrize("value", [False, 12, [], {}, "x" * 2001])
def test_project_context_type_and_size_bounded(value):
    with pytest.raises(ValidationAppError):
        GoalSpec("Agent", project_context=value)


def test_optional_project_changes_only_new_draft_revision_identity_and_is_serialized():
    stage = PlanStage.create(stable_key="stage", title="阶段", section_kind=OutlineSectionKind.CORE, order_index=0)
    draft = PlanDraft("draft", "project", "run", "Agent", 1, stages=(stage,), goal_spec=GoalSpec("Agent"))
    empty = replace(draft, goal_spec=GoalSpec("Agent", project_context=None))
    context = replace(draft, goal_spec=GoalSpec("Agent", project_context="已有项目"))
    assert draft.content_hash == empty.content_hash != context.content_hash
    old = revision_from_draft(draft, revision=1)
    new = revision_from_draft(context, revision=1)
    assert old.structure_fingerprint() != new.structure_fingerprint()
    assert "project_context" not in canonical_json(_draft_payload(draft))
    assert _draft_payload(context)["goal_spec"]["project_context"] == "已有项目"
    assert _structure_payload(new)["goal_spec"]["project_context"] == "已有项目"
    assert goal_spec_from_payload(_draft_payload(context)["goal_spec"]) == context.goal_spec


def test_project_context_does_not_open_public_generate():
    from app.api.v1.routes import generate_plan
    from app.core.errors import DependencyUnavailableError

    from tests.unit.test_planning_legacy_removal import scope, service

    instance, denied = service()
    request = PlanGenerateRequest(goal="Agent", goal_spec=GoalSpec("Agent", project_context="现有项目"))
    with pytest.raises(DependencyUnavailableError):
        generate_plan(request, project_id="cleanup-project", scope=scope(), service=instance)
    assert denied.calls == []
