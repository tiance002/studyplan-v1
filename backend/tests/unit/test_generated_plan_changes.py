from copy import deepcopy
from dataclasses import replace

import pytest
from app.core.errors import ValidationAppError
from app.domain.enums import OutlineSectionKind, StageResourceRole
from app.domain.generated_plan_changes import (
    GeneratedPlanChangeCommand,
    added_topic_route,
    compose_generated_draft,
)
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


def topic_pack():
    return {'knowledge_blueprints': [
        {'stable_key': 'base'}, {'stable_key': 'parent', 'prerequisite_keys': ['base']},
        {'stable_key': 'topic', 'parent_key': 'parent'},
        {'stable_key': 'future', 'prerequisite_keys': ['topic']},
        {'stable_key': 'final', 'prerequisite_keys': ['future']}],
        'stage_blueprints': [
            {'stable_key': 'a', 'node_keys': ['base']},
            {'stable_key': 'optional', 'node_keys': ['parent', 'topic']},
            {'stable_key': 'c', 'node_keys': ['future']},
            {'stable_key': 'final', 'node_keys': ['final']}]}


def test_add_topic_expands_parent_prerequisite_and_inserts_before_dependent():
    pack = topic_pack()
    original = deepcopy(pack)
    route = added_topic_route(pack, ('a', 'c', 'final'), ('topic',), 0)
    assert route == {'after_stage_keys': ('a', 'optional', 'c', 'final'),
                     'added_node_keys': ('parent', 'topic'), 'added_stage_keys': ('optional',),
                     'retained_stage_keys': ('a', 'c', 'final')}
    assert pack == original


@pytest.mark.parametrize('topics,boundary', [(('unknown',), 0), (('base',), 0),
                                          (('topic',), 1), (('topic', 'topic'), 0)])
def test_add_topic_rejects_unknown_noop_protected_dependency_and_duplicates(topics, boundary):
    with pytest.raises(ValidationAppError):
        added_topic_route(topic_pack(), ('a', 'c', 'final'), topics, boundary)


def test_add_topic_rejects_cycle_and_ambiguous_exposure_but_accepts_declared_owner():
    pack = topic_pack()
    pack['knowledge_blueprints'][1]['prerequisite_keys'] = ['topic']
    with pytest.raises(ValidationAppError):
        added_topic_route(pack, ('a', 'c', 'final'), ('topic',), 0)
    pack = topic_pack()
    pack['stage_blueprints'].append({'stable_key': 'duplicate', 'node_keys': ['topic']})
    with pytest.raises(ValidationAppError):
        added_topic_route(pack, ('a', 'c', 'final'), ('topic',), 0)
    pack['knowledge_blueprints'][2]['section_key'] = 'optional'
    assert added_topic_route(pack, ('a', 'c', 'final'), ('topic',), 0)['added_stage_keys'] == ('optional',)


def test_add_topic_composition_preserves_old_links_and_invalidates_future_guidance():
    current, generated = draft('old'), draft('new', ('a', 'optional', 'c', 'final', 'discard'))
    original = deepcopy((current, generated))
    meta = metadata(operation='add_topic', after_stage_keys=['a', 'optional', 'c', 'final'],
                    retained_stage_keys=['a', 'c', 'final'], protected_through=0,
                    added_stage_keys=['optional'])
    result = compose_generated_draft(current, generated, meta)
    assert result.stages[0] == current.stages[0]
    assert result.stages[0] is current.stages[0]
    assert result.stages[1] == generated.stages[1]
    assert result.stages[2].stage_id == current.stages[1].stage_id
    assert result.stages[2].learning_guidance.why_now != current.stages[1].learning_guidance.why_now
    assert result.stages[2].learning_guidance.practice_delta.baseline != 'old-baseline'
    for field in ('unit_links', 'task_links', 'task_knowledge_links', 'stage_resources', 'extensions',
                  'resource_snapshots'):
        assert getattr(result, field) == (*getattr(current, field), getattr(generated, field)[1])
    assert (current, generated) == original


@pytest.mark.parametrize('changes', [
    {'retained_stage_keys': ['a']}, {'added_stage_keys': ['other']},
    {'after_stage_keys': ['a', 'optional', 'final', 'c']}, {'protected_through': 1},
    {'after_stage_keys': ['a', 'optional', 'final']},
])
def test_add_topic_composition_rejects_mutated_server_route_decisions(changes):
    meta = metadata(operation='add_topic', after_stage_keys=['a', 'optional', 'c', 'final'],
                    retained_stage_keys=['a', 'c', 'final'], protected_through=0,
                    added_stage_keys=['optional'])
    with pytest.raises(ValidationAppError):
        compose_generated_draft(draft('old'), draft('new', ('a', 'optional', 'c', 'final')),
                                {**meta, **changes})


def test_add_topic_reuses_existing_repeated_exposure_and_rejects_missing_ownership():
    pack = topic_pack()
    pack['stage_blueprints'][1]['node_keys'].append('base')
    assert added_topic_route(pack, ('a', 'c', 'final'), ('topic',), 0)['added_stage_keys'] == ('optional',)
    pack['stage_blueprints'][1]['node_keys'].remove('topic')
    with pytest.raises(ValidationAppError):
        added_topic_route(pack, ('a', 'c', 'final'), ('topic',), 0)


def test_add_topic_expands_companion_nodes_and_their_transitive_stage_dependencies():
    pack = topic_pack()
    pack['knowledge_blueprints'].extend([
        {'stable_key': 'companion', 'prerequisite_keys': ['extra']},
        {'stable_key': 'extra', 'prerequisite_keys': ['extra-base']},
        {'stable_key': 'extra-base', 'prerequisite_keys': None}])
    pack['stage_blueprints'][1]['node_keys'].append('companion')
    pack['stage_blueprints'][1:1] = [
        {'stable_key': 'extra-base-stage', 'node_keys': ['extra-base']},
        {'stable_key': 'extra-stage', 'node_keys': ['extra']}]
    original = deepcopy(pack)
    route = added_topic_route(pack, ('a', 'c', 'final'), ('topic',), 0)
    assert route['after_stage_keys'] == ('a', 'extra-base-stage', 'extra-stage', 'optional', 'c', 'final')
    assert set(route['added_node_keys']) == {'parent', 'topic', 'companion', 'extra', 'extra-base'}
    assert route['added_node_keys'].index('extra-base') < route['added_node_keys'].index('extra')
    assert route['added_node_keys'].index('extra') < route['added_node_keys'].index('companion')
    assert pack == original


def test_added_stage_guidance_is_invalidated_when_controlled_pack_predecessor_differs():
    current = draft('old')
    generated = draft('new', ('a', 'discard', 'optional', 'c', 'final'))
    meta = metadata(operation='add_topic', after_stage_keys=['a', 'optional', 'c', 'final'],
                    retained_stage_keys=['a', 'c', 'final'], protected_through=0,
                    added_stage_keys=['optional'])
    result = compose_generated_draft(current, generated, meta)
    guide = result.stages[1].learning_guidance
    assert guide.previous_relation != generated.stages[2].learning_guidance.previous_relation
    assert guide.practice_delta.baseline != generated.stages[2].learning_guidance.practice_delta.baseline


def test_topic_command_normalizes_and_rejects_cross_operation_parameters():
    assert command(operation='add_topic', topic_keys=['topic']).topic_keys == ('topic',)
    for values in ({'operation': 'add_topic', 'topic_keys': ('topic',), 'goal': 'Learn'},
                   {'operation': 'change_goal', 'goal': 'Learn', 'topic_keys': ('topic',)},
                   {'operation': 'regenerate_future_plan', 'topic_keys': ('topic',)},
                   {'operation': 'add_topic', 'topic_keys': tuple(f'n{i}' for i in range(21))}):
        with pytest.raises(ValidationAppError):
            command(**values)
