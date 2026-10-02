from copy import deepcopy
from dataclasses import replace

import pytest
from app.core.errors import ValidationAppError
from app.domain.enums import OutlineSectionKind, StageResourceRole
from app.domain.generated_plan_changes import GeneratedPlanChangeCommand, compose_generated_draft
from app.domain.planning.guidance import LearningGuidance, PracticeDelta
from app.domain.planning.intent import GoalSpec
from app.domain.planning.models import (
    PlanDraft,
    PlanStage,
    PlanTaskKnowledgeLink,
    PlanTaskLink,
    PlanUnitLink,
)
from app.domain.resources.curation import KnowledgeExtension, StageResourceAssignment


def draft(prefix, keys=('a', 'c', 'final')):
    guide = LearningGuidance(f'{prefix}-why', f'{prefix}-previous', (f'{prefix}-focus',), (),
                            PracticeDelta(f'{prefix}-baseline', ('add',), ('keep',), ('check',), ('reuse',)))
    stages = tuple(PlanStage(f'{prefix}-{k}', k, k, OutlineSectionKind.CORE, i,
                             learning_guidance=guide) for i, k in enumerate(keys))
    resources = tuple(StageResourceAssignment(f'{prefix}-res-{s.stable_key}', 'p', '', s.stage_id,
                     StageResourceRole.PRIMARY, fallback_search_terms=('search',)) for s in stages)
    return PlanDraft(f'{prefix}-draft', 'p', f'{prefix}-run', 'Learn', 2, stages=stages,
        unit_links=tuple(PlanUnitLink(s.stage_id, f'{prefix}-unit-{s.stable_key}', 0) for s in stages),
        task_links=tuple(PlanTaskLink(s.stage_id, f'{prefix}-task-{s.stable_key}', 0) for s in stages),
        task_knowledge_links=tuple(PlanTaskKnowledgeLink(f'{prefix}-task-{s.stable_key}',
                                   f'{prefix}-node-{s.stable_key}') for s in stages),
        stage_resources=resources,
        extensions=tuple(KnowledgeExtension(f'{prefix}-ext-{s.stable_key}', 'p', '', s.stage_id,
                                           'topic') for s in stages),
        resource_snapshots=tuple({'assignment_id': a.assignment_id, 'content': {'title': prefix}}
                                 for a in resources), source_pack_key='pack', source_pack_version=1,
        goal_spec=GoalSpec('Learn'))


def metadata(**values):
    return {'operation': 'regenerate_future_plan', 'before_stage_keys': ['a', 'c', 'final'],
            'after_stage_keys': ['a', 'c', 'final'], 'retained_stage_keys': ['a'], **values}


def test_regeneration_preserves_prefix_and_filters_removed_optional_stage_everywhere():
    current, generated = draft('old'), draft('new', ('a', 'optional', 'c', 'final'))
    generated = replace(generated, unit_refs=('optional-unit',), task_refs=('optional-task',),
                        node_stable_keys=('optional-node',))
    originals = deepcopy((current, generated))
    result = compose_generated_draft(current, generated, metadata())
    assert [s.stable_key for s in result.stages] == ['a', 'c', 'final']
    assert result.stages[0] == current.stages[0]
    assert result.stages[1] == replace(generated.stages[2], order_index=1)
    for field in ('unit_links', 'task_links', 'task_knowledge_links', 'stage_resources',
                  'extensions', 'resource_snapshots'):
        assert getattr(result, field) == (getattr(current, field)[0],
                                         *getattr(generated, field)[2:])
    assert result.draft_id == generated.draft_id and result.run_id == generated.run_id
    assert result.revision_candidate == generated.revision_candidate
    assert result.unit_refs == result.task_refs == result.node_stable_keys == ()
    assert (current, generated) == originals
    result.resource_snapshots[0]['content']['title'] = 'modified'
    assert current.resource_snapshots[0]['content']['title'] == 'old'


def test_regeneration_copies_metadata_and_rejects_frozen_pack_mismatch():
    meta = metadata(source_pack_key='pack', source_pack_version=1)
    result = compose_generated_draft(draft('old'), draft('new'), meta)
    meta['retained_stage_keys'].append('c')
    assert result.route_change['retained_stage_keys'] == ['a']
    with pytest.raises(ValidationAppError):
        compose_generated_draft(draft('old'), draft('new'), metadata(source_pack_version=2))


@pytest.mark.parametrize('retained', [[], ['a', 'c']])
def test_regeneration_supports_empty_or_multiple_protected_stages(retained):
    current, generated = draft('old'), draft('new')
    result = compose_generated_draft(current, generated, metadata(retained_stage_keys=retained))
    count = len(retained)
    assert result.stages[:count] == current.stages[:count]
    assert result.stages[count:] == generated.stages[count:]
    assert result.task_links == (*current.task_links[:count], *generated.task_links[count:])


@pytest.mark.parametrize('changes', [
    {'after_stage_keys': ['a', 'final']},
    {'retained_stage_keys': ['c']},
    {'retained_stage_keys': ['a', 'final']},
    {'retained_stage_keys': ['a', 'c', 'final']},
    {'after_stage_keys': ['a', 'c', 'c']},
    {'before_stage_keys': ['a', 'c', 'unknown']},
])
def test_regeneration_rejects_truncation_nonprefix_no_future_and_duplicate_metadata(changes):
    with pytest.raises(ValidationAppError):
        compose_generated_draft(draft('old'), draft('new'), metadata(**changes))


@pytest.mark.parametrize('changes', [
    {'source_pack_key': 'other'}, {'source_pack_version': 2}, {'goal_snapshot': 'Other'},
    {'goal_spec': GoalSpec('Other')}, {'project_id': 'other'},
    {'stages': draft('new', ('a', 'a', 'final')).stages},
    {'stages': draft('new', ('a', 'final')).stages},
])
def test_regeneration_rejects_generated_identity_or_route_mismatch(changes):
    with pytest.raises(ValidationAppError):
        compose_generated_draft(draft('old'), replace(draft('new'), **changes), metadata())


def test_goal_change_replaces_whole_route_goal_and_spec():
    generated = replace(draft('new', ('other', 'final')), goal_snapshot='New goal',
                        goal_spec=GoalSpec('New goal'), source_pack_key='new-pack')
    meta = metadata(operation='change_goal', after_stage_keys=['other', 'final'],
                    retained_stage_keys=[])
    result = compose_generated_draft(draft('old'), generated, meta)
    assert result.stages == generated.stages
    assert result.goal_snapshot == 'New goal' and result.goal_spec == generated.goal_spec
    assert result.source_pack_key == 'new-pack'
    assert result is not generated
    with pytest.raises(ValidationAppError):
        compose_generated_draft(draft('old'), generated, {**meta, 'retained_stage_keys': ['a']})


def command(**values):
    return GeneratedPlanChangeCommand('p', 'plan', 1, 'key', **values)


def test_command_trims_goal_and_accepts_optional_spec():
    cmd = command(operation='change_goal', goal='  Learn  ', goal_spec=GoalSpec('Learn'))
    assert cmd.goal == 'Learn'
    assert command(operation='regenerate_future_plan').goal_spec is None


@pytest.mark.parametrize('values', [
    {'operation': 'add_topic'}, {'operation': 'change_goal', 'goal': ''},
    {'operation': 'change_goal', 'goal': 'x' * 2001},
    {'operation': 'change_goal', 'goal': 'Learn', 'goal_spec': {}},
    {'operation': 'regenerate_future_plan', 'goal': 'Learn'},
    {'operation': 'regenerate_future_plan', 'goal_spec': GoalSpec('Learn')},
])
def test_command_rejects_out_of_bounds_or_operation_specific_values(values):
    with pytest.raises(ValidationAppError):
        command(**values)


@pytest.mark.parametrize('changes', [{'expected_version': True}, {'expected_version': -1},
                                   {'project_id': ''}, {'idempotency_key': 'x' * 201}])
def test_command_preserves_existing_identifier_and_version_bounds(changes):
    cmd = command(operation='regenerate_future_plan')
    with pytest.raises(ValidationAppError):
        replace(cmd, **changes)
