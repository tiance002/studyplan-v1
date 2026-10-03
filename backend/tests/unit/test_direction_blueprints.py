"""Offline contract checks for independent, incremental direction curricula."""
import hashlib
import json
from pathlib import Path

import pytest
from app.domain.domain_packs.validation import validate_seed
from app.domain.planning.guidance import stage_guidance

CONTENT = Path(__file__).resolve().parents[2] / 'app/infrastructure/content'
DIRECTIONS = ('knowledge-rag', 'coding', 'workflow-automation')


def load(direction):
    return json.loads((CONTENT / f'agent-{direction}-v1.json').read_text(encoding='utf-8'))


def closure(pack):
    nodes = {n['stable_key']: n for n in pack['knowledge_blueprints']}
    required = set()

    def visit(key):
        if key in required:
            return
        required.add(key)
        for dependency in nodes[key].get('prerequisite_keys', []):
            visit(dependency)

    for key in pack['required_node_keys']:
        visit(key)
    return required


@pytest.mark.parametrize('direction', DIRECTIONS)
def test_direction_seed_is_valid_with_ten_required_stages(direction):
    pack = load(direction)
    assert validate_seed(pack) == pack
    stages = pack['stage_blueprints']
    assert len(stages) == 10
    assert [s['stable_key'] for s in stages[:3]] == [
        'stage.python_functions', 'stage.python_files', 'stage.environment']
    assert stages[-1]['stable_key'] == 'stage.capstone'
    assert all(s['inclusion'] == 'required' for s in stages)
    assert all(sum(r['role'] == 'primary' for r in s['resources']) == 1 for s in stages)
    required = closure(pack)
    assert all(set(s['node_keys']) <= required for s in stages)
    assert {'node.python_functions', 'node.python_files', 'node.environment',
            'node.agent_loop', 'node.eval_lite', 'node.reliability'} <= required
    assert 'node.mcp' not in required
    if direction != 'knowledge-rag':
        assert 'node.rag' not in required
    else:
        assert 'node.rag' in required


@pytest.mark.parametrize('direction', DIRECTIONS)
def test_python_author_chapter_order_and_contiguous_primary(direction):
    pack = load(direction)
    python = next(r for r in pack['resources'] if r['canonical_url'].endswith('/tutorial/'))
    assert [int(s['title'].split('.')[0]) for s in python['sections']] == [4, 5, 6, 7, 8, 12]
    catalog = {s['section_id']: i for i, s in enumerate(python['sections'])}
    assert [[catalog[k] for k in s['resources'][0]['section_refs']]
            for s in pack['stage_blueprints'][:3]] == [[0, 1], [3, 4], [5]]
    supplements = pack['stage_blueprints'][1]['resources'][1:]
    assert any(r['section_refs'] == [python['sections'][2]['section_id']] for r in supplements)
    assert {'json', 'pathlib', 'unittest'} <= {
        r['source_ref'].removesuffix('_v1').split('_')[-1] for r in supplements}


@pytest.mark.parametrize('direction', DIRECTIONS)
def test_each_stage_reuses_project_and_exact_practice_acceptance(direction):
    pack = load(direction)
    tasks = {p['section_key']: p for p in pack['practice_blueprints']}
    assert len(tasks) == 10
    for stage in pack['stage_blueprints']:
        guide = stage_guidance(pack, stage)
        task = tasks[stage['stable_key']]
        assert guide is not None
        assert guide.reading_prerequisites and guide.practice_prerequisites
        assert guide.previous_relation != '模板未预置与先前教程的关系；按自己的经历复习，本说明不推断已经掌握。'
        assert guide.practice_delta.increment == (task['goal'],)
        assert guide.practice_delta.validation == tuple(task['acceptance'])
        assert guide.practice_delta.preserved and guide.practice_delta.reuse
        assert '同一' in guide.practice_delta.reuse[0]
        assert guide.knowledge_keys == tuple(task['node_keys'])


def test_direction_resources_have_independent_immutable_ids():
    source_ids, section_ids = set(), set()
    for direction in DIRECTIONS:
        pack = load(direction)
        for source in pack['resources']:
            assert source['source_id'] not in source_ids
            source_ids.add(source['source_id'])
            for section in source['sections']:
                assert section['section_id'] not in section_ids
                section_ids.add(section['section_id'])
    previous = json.loads((CONTENT / 'agent-application-v3.json').read_text(encoding='utf-8'))
    assert not source_ids & {r['source_id'] for r in previous['resources']}
    assert not section_ids & {s['section_id'] for r in previous['resources'] for s in r['sections']}
    assert hashlib.sha256((CONTENT / 'agent-application-v3.json').read_bytes()).hexdigest() == (
        '2f26a2a953280e1ec54cc2ed31f3c304c3eb297ceed0a122d192c3c5c8c844c7')


def test_specialized_readings_cover_bounded_approval_and_patch_questions():
    workflow = load('workflow-automation')
    effects = next(s for s in workflow['stage_blueprints'] if s['stable_key'] == 'stage.workflow_effects')
    sources = {r['source_id']: r for r in workflow['resources']}
    assert sources[effects['resources'][0]['source_ref']]['canonical_url'].endswith('/interrupts')
    coding = load('coding')
    workspace = next(s for s in coding['stage_blueprints'] if s['stable_key'] == 'stage.coding_workspace')
    sources = {r['source_id']: r for r in coding['resources']}
    assert {'https://git-scm.com/docs/git-diff', 'https://git-scm.com/docs/git-apply'} <= {
        sources[r['source_ref']]['canonical_url'] for r in workspace['resources']}
