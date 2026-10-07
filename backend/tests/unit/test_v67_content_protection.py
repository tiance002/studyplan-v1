"""Offline v6.7 canonical merge and immutable format contracts."""
import hashlib
import json
from copy import deepcopy

import pytest
from app.agent_workflows.planning_batches import (
    DEFAULT_BUDGET,
    freeze_manifest,
    manifest_is_intact,
    merge_batches,
    practice_payload,
    structure_payload,
)
from app.domain.planning.intent import GoalSpec, purpose_requirements
from app.infrastructure.domain_pack import load_pack
from tests.helpers.reviewed_content import reviewed_fixture
from app.agent_workflows.planning_structure import presentation_entry
from tests.helpers.planning_responses import selected_output


def generated(pack=None, spec=None):
    pack = pack or reviewed_fixture('agent-application-v5.json', tuple('stage.v62.agent.application.' + key for key in ('a0', 'a1', 'a2', 'a3', 'a4', 'a7')))
    manifest = freeze_manifest(pack, DEFAULT_BUDGET, 'mock:v67', goal_spec=spec,
                               outline_input_format='stage_skeleton_v1', structure_input_format='reviewed_structure_v1')
    state = {'goal': '学习 Agent', 'domain_pack': pack, 'manifest': manifest, 'structure_batches': []}
    outline = {'sections': [{'stable_key': s['stage_key'], 'title': s['title'], 'objective': s['objective']}
                            for s in manifest['stages']]}
    for batch in manifest['structure_batches']:
        state['structure_batches'].append({'stage_key': batch['stage_key'],
            **presentation_entry(selected_output('planning.structure', structure_payload(state, batch)), state, batch)})
    practices = [{'stage_key': b['stage_key'], 'payload': selected_output('planning.practice',
                 practice_payload(state, b['stage_key']))} for b in manifest['practice_batches']]
    return pack, manifest, outline, state['structure_batches'], practices


def merged(case):
    p, m, o, s, t = case
    return merge_batches(o, s, t, p, manifest=m)


def test_manifest_marker_is_optional_hashed_and_rejects_unknown_format():
    p = load_pack('agent-application-v5.json')
    legacy = freeze_manifest(p, DEFAULT_BUDGET, 'mock:v67')
    assert legacy['manifest_hash'] == '79f9dbff819d7e1b0c6177b9c5653012f3f231a9689d5bf3afe82e1855f375a4'
    assert legacy == freeze_manifest(p, DEFAULT_BUDGET, 'mock:v67', outline_input_format=None)
    assert 'outline_input_format' not in legacy
    marked = freeze_manifest(p, DEFAULT_BUDGET, 'mock:v67', outline_input_format='stage_skeleton_v1')
    assert marked['outline_input_format'] == 'stage_skeleton_v1'
    assert manifest_is_intact(marked)
    body = {k: v for k, v in marked.items() if k != 'manifest_hash'}
    digest = hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False,
                            separators=(',', ':')).encode()).hexdigest()
    assert marked['manifest_hash'] == digest != legacy['manifest_hash']
    del marked['outline_input_format']
    assert not manifest_is_intact(marked)
    with pytest.raises(ValueError, match='outline_input_format'):
        freeze_manifest(p, DEFAULT_BUDGET, 'mock:v67', outline_input_format='unknown')


@pytest.mark.parametrize('filename', ['agent-application-v5.json', 'cloud-services-v2.json', 'ai-fullstack-v2.json'])
def test_all_reviewed_knowledge_text_and_graph_fields_are_canonical(filename):
    case = generated(load_pack(filename))
    p, m, o, structures, practices = case
    for s in structures:
        for n in s['nodes']:
            n.update(title='forged', objectives=['forged'], scope='forged', acceptance=['forged'],
                     node_type='skill', parent_key='forged', prerequisite_keys=['forged'])
        s['relations'] = [{'from_stable_key': 'forged', 'to_stable_key': n['stable_key'],
                          'relation_type': 'prerequisite'} for n in s['nodes']]
    result = merged(case)
    blueprints = {n['stable_key']: n for n in p['knowledge_blueprints']}
    for n in result['nodes']:
        source = blueprints[n['stable_key']]
        for field in ('title', 'objectives', 'scope', 'acceptance', 'node_type'):
            assert n.get(field) == source.get(field)
        assert n.get('parent_key', '') == source.get('parent_key', '')
        assert n.get('prerequisite_keys', []) == source.get('prerequisite_keys', [])
    expected = {(dep, n['stable_key'], 'prerequisite') for n in p['knowledge_blueprints']
                for dep in n.get('prerequisite_keys', [])}
    expected |= {(n['parent_key'], n['stable_key'], 'contains') for n in p['knowledge_blueprints']
                 if n.get('parent_key')}
    assert {(r['from_stable_key'], r['to_stable_key'], r['relation_type'])
            for r in result['relations']} == expected


def test_reviewed_practice_exact_tasks_and_links_remove_secondary_starter_and_conflicts():
    case = generated()
    p, m, o, s, practices = case
    template = p['practice_blueprints'][0]
    template.update(required=True, optional=False, deliverable='canonical artifact',
                    in_scope=['canonical scope'], out_scope=['canonical exclusion'])
    # Fixture blueprint changes precede freezing, as a real reviewed submission.
    m.update(freeze_manifest(p, DEFAULT_BUDGET, 'mock:v67', outline_input_format='stage_skeleton_v1', structure_input_format='reviewed_structure_v1'))
    first = practices[0]['payload']['tasks'][0]
    first.update(stable_key='forged-identity', goal='forced Starter', acceptance=['conflicting mandatory'],
                 in_scope=['forged'], out_scope=[], required=False, optional=True,
                 deliverable='mandatory Starter', knowledge_links=[])
    extra = deepcopy(first)
    extra.update(stable_key='supplemental-but-required', order_index=1)
    practices[0]['payload']['tasks'].append(extra)
    practices[0]['payload']['task_knowledge_links'] = [{'task_stable_key': extra['stable_key'],
                                      'node_stable_key': template['node_keys'][0], 'role': 'core'}]
    result = merged(case)
    tasks = result['practice_proposal']['tasks']
    assert len(tasks) == len(p['practice_blueprints'])
    task = tasks[0]
    for field in ('stable_key', 'goal', 'acceptance', 'required', 'optional', 'deliverable', 'in_scope', 'out_scope'):
        assert task[field] == template[field]
    assert task['knowledge_links'] == [{'node_stable_key': k, 'role': 'core'} for k in template['node_keys']]
    assert result['practice_proposal']['task_knowledge_links'][0]['task_stable_key'] == template['stable_key']
    assert 'forced Starter' not in str(tasks)
    assert 'conflicting mandatory' not in str(tasks)


def test_missing_canonical_acceptance_restored_and_final_goal_outputs_retained():
    spec = GoalSpec(target='Agent', outcome_purpose='interview')
    case = generated(spec=spec)
    for batch in case[-1]:
        batch['payload']['tasks'][0]['acceptance'] = ['forged']
    result = merged(case)
    tasks = result['practice_proposal']['tasks']
    assert tasks[0]['acceptance'] == case[0]['practice_blueprints'][0]['acceptance']
    assert set(purpose_requirements(spec)) <= set(tasks[-1]['acceptance'])
    assert 'forged' not in str(tasks)


def test_multiple_reviewed_tasks_are_restored_by_identity_not_model_position():
    case = generated()
    p, m, o, structures, practices = case
    second = deepcopy(p['practice_blueprints'][0])
    second.update(stable_key='practice.canonical.second', goal='second reviewed task',
                  acceptance=['second exact acceptance'], required=True, optional=False)
    p['practice_blueprints'].insert(1, second)
    m.update(freeze_manifest(p, DEFAULT_BUDGET, 'mock:v67', outline_input_format='stage_skeleton_v1', structure_input_format='reviewed_structure_v1'))
    candidate = deepcopy(practices[0]['payload']['tasks'][0])
    candidate.update(stable_key=second['stable_key'], goal='forced Starter', acceptance=['forged'], required=True)
    practices[0]['payload']['tasks'].insert(0, candidate)
    result = merged(case)
    assert [t['stable_key'] for t in result['practice_proposal']['tasks'][:2]] == [
        p['practice_blueprints'][0]['stable_key'], second['stable_key']]
    saved = result['practice_proposal']['tasks'][1]
    assert saved['goal'] == second['goal'] and saved['acceptance'] == second['acceptance']
    assert saved['optional'] is False and saved['required'] is True


def test_current_reviewed_task_default_cannot_inherit_model_required_or_deliverable():
    case = generated()
    task = case[-1][0]['payload']['tasks'][0]
    task.update(required=True, optional=False, deliverable='mandatory Starter')
    saved = merged(case)['practice_proposal']['tasks'][0]
    assert 'required' not in saved and 'optional' not in saved and 'deliverable' not in saved


def test_merge_does_not_mutate_any_frozen_or_provider_inputs():
    case = generated()
    before = deepcopy(case)
    merged(case)
    assert case == before




def test_new_reviewed_unit_rubric_persists_all_canonical_knowledge_and_practice():
    case = generated()
    for batch in case[3]:
        for unit in batch['units']:
            unit['rubric'] = {'mandatory Starter': 'forged conflicting acceptance'}
    result = merged(case)
    nodes = {n['stable_key']: n for n in case[0]['knowledge_blueprints']}
    tasks = {t['stable_key']: t for t in result['practice_proposal']['tasks']}
    for unit in result['units']:
        rubric = unit['rubric']
        assert set(rubric) == {'canonical_knowledge', 'canonical_practice'}
        for key in unit['node_keys']:
            assert rubric['canonical_knowledge'][key] == nodes[key]
        assert rubric['canonical_practice'] == {k: v for k, v in tasks.items()
                                                if v['section_key'] == unit['section_key']}


def test_model_practice_hints_are_not_persisted_as_rubric_authority():
    case = generated()
    candidate = case[-1][0]['payload']['tasks'][0]
    candidate['hints'] = ['mandatory Starter acceptance as a hint']
    candidate['description'] = 'forged criterion in description'
    result = merged(case)
    assert candidate['hints'] == result['practice_proposal']['tasks'][0]['hints']
    assert 'mandatory Starter' not in str(result['units'][0]['rubric'])
    assert 'forged criterion' not in str(result['units'][0]['rubric'])


@pytest.mark.parametrize('flag', [{'optional': True}, {'required': False}])
def test_optional_canonical_task_fails_closed_before_publication(flag):
    p = load_pack('agent-application-v5.json')
    p['practice_blueprints'][0].update(flag)
    with pytest.raises(ValueError, match='optional practice'):
        freeze_manifest(p, DEFAULT_BUDGET, 'mock:v67', outline_input_format='stage_skeleton_v1')
    # Frozen old manifests retain their previous allowed shape and hash behavior.
    assert manifest_is_intact(freeze_manifest(p, DEFAULT_BUDGET, 'mock:v67'))
