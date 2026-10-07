"""Semantic route assertions, inherited source levels and exposure boundaries."""
from copy import deepcopy

import pytest

from app.domain.domain_packs.validation import validate_seed
from app.domain.planning.intent import GoalSpec
from app.infrastructure.domain_pack import CURRENT_PACKS, load_pack
from app.tools.map_targeted_alignment import build_targeted_alignment_pack, build_targeted_alignment_packs




def codes(pack):
    return [s['stage_code'] for s in pack['stage_blueprints']]


def test_only_changed_direction_gets_new_version_and_no_new_canonical_keys():
    old = load_pack('agent-application-v6.json')
    new = build_targeted_alignment_pack()
    assert validate_seed(new) == new
    assert {n['stable_key'] for n in old['knowledge_blueprints']} == {n['stable_key'] for n in new['knowledge_blueprints']}
    assert CURRENT_PACKS['agent.application'] == 'agent-application-v8.json'
    assert CURRENT_PACKS['ai.fullstack'] == 'ai-fullstack-v4.json'
    assert CURRENT_PACKS['cloud.services'] == 'cloud-services-v4.json'


@pytest.mark.parametrize('base,output', [('agent-application-v6.json', 'agent-application-v7.json'),
    ('ai-fullstack-v3.json', 'ai-fullstack-v4.json'), ('cloud-services-v3.json', 'cloud-services-v4.json')])
def test_source_review_and_chapter_facts_never_increase(base, output):
    old = load_pack(base)
    new = build_targeted_alignment_packs()[output]
    assert len(old['resources']) == len(new['resources'])
    for before, after in zip(old['resources'], new['resources']):
        for field in ('canonical_url', 'review_depth', 'verification_status', 'review_evidence',
                      'source_review_record', 'runtime_validation', 'content_access', 'source_version'):
            assert before.get(field) == after.get(field)
        assert len(before['sections']) == len(after['sections'])
        for b, a in zip(before['sections'], after['sections']):
            assert {k: v for k, v in b.items() if k not in {'section_id', 'applicable_node_keys'}} == {
                k: v for k, v in a.items() if k not in {'section_id', 'applicable_node_keys'}}






def test_successor_objectives_and_mcp_proof_match_actual_teaching_role():
    pack = load_pack('agent-application-v7.json')
    stages = {s['stage_code']: s for s in pack['stage_blueprints']}
    assert '只在复杂度' not in stages['A5']['objective']
    assert '一深多浅' in stages['A5']['objective']
    assert '只读 server' in stages['A6']['objective']
    node = next(n for n in pack['knowledge_blueprints'] if n['stable_key'] in stages['A6']['node_keys'])
    practice = next(p for p in pack['practice_blueprints'] if p['section_key'] == stages['A6']['stable_key'])
    assert practice['acceptance'] == node['acceptance']
    assert all(term in str(practice['acceptance']) for term in ['只读 server', '最小 server', '未知工具', '坏参数', '断连', 'mock'])
    assert '选定' in stages['GR']['objective']
    assert '持续项目的最小改动' in stages['GT']['objective']
    task = next(p for p in pack['practice_blueprints'] if p['section_key'] == stages['GT']['stable_key'])
    assert '不迁移理由' in str(task['acceptance'])
    assert '改变前后' in str(task['acceptance']) and '回归证据' in str(task['acceptance'])
    assert '当前实现地图' not in str(task['acceptance'])
