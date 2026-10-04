"""Semantic route assertions, inherited source levels and exposure boundaries."""
from copy import deepcopy

import pytest

from app.domain.domain_packs.validation import validate_seed
from app.domain.planning.intent import GoalSpec
from app.domain.planning.semantic_content import adapt_semantic_pack
from app.infrastructure.domain_pack import CURRENT_PACKS, load_pack
from app.tools.map_targeted_alignment import build_targeted_alignment_pack, build_targeted_alignment_packs


def route(goal, starting='', depth='unspecified'):
    return adapt_semantic_pack(load_pack('agent-application-v7.json'), goal,
        GoalSpec(target=goal, starting_point=starting, desired_depth=depth))


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


def test_full_agent_has_real_framework_mcp_and_pending_specialty():
    result = route('从零系统学习 Agent 应用开发，先做最小应用')
    assert codes(result) == ['A0', 'A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'A7', 'A8']
    assert result['semantic_context']['specialty_status'] == '专项待选'
    a5 = next(s for s in result['stage_blueprints'] if s['stage_code'] == 'A5')
    sources = {r['source_id']: r['title'] for r in result['resources']}
    assert {'LangGraph Graph API', 'LangGraph Persistence and Checkpointers', 'LangGraph Interrupts'} <= {
        sources[r['source_ref']] for r in a5['resources']}
    assert '多套实现' in str(result['practice_blueprints'])
    assert '最小 server' in str(next(s for s in result['stage_blueprints'] if s['stage_code'] == 'A6'))


def test_full_rag_has_visible_detailed_tutorial_mature_and_transfer_in_order():
    result = route('从零系统学 Agent 应用，重点 RAG 资料问答；不做 RL、Browser、Coding 完整专项', depth='foundation')
    ordered = codes(result)
    assert ordered == [*[f'A{i}' for i in range(9)], *[f'G{i}' for i in range(7)], 'GR', 'GT']
    stages = {s['stage_code']: s for s in result['stage_blueprints']}
    assert all(stages[f'G{i}']['resources'] for i in range(7))
    assert not any(e['topic'].startswith('项目学习：') for e in stages['G6']['extensions'])
    cards = [e for e in stages['GR']['extensions'] if e['topic'].startswith('项目学习：')]
    assert len(cards) == 2
    tasks = [p for p in result['practice_blueprints'] if p['section_key'] == stages['GR']['stable_key']]
    assert len(tasks) == 1 and '任选一个' in tasks[0]['goal']
    assert stages['GR']['node_keys'] == stages['GT']['node_keys'] == stages['G6']['node_keys']
    for code in ['GR', 'GT']:
        assert list(stages[code]['learning_guidance']['knowledge_keys']) == stages[code]['node_keys']
        assert stages[code]['learning_guidance']['exposure_relation'] == 'deepen'


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
    selected = route('从零系统学 Agent，重点 RAG')
    actual = {s['stage_code']: s for s in selected['stage_blueprints']}
    assert actual['GR']['objective'] == stages['GR']['objective']
    assert actual['GT']['objective'] == stages['GT']['objective']


def test_narrow_mcp_does_not_sneak_repeated_exposures_through_closure():
    result = route('只学MCP，已经会基础 Tool 调用', starting='已经会基础 Tool 调用')
    assert codes(result) == ['A0', 'A1', 'A2', 'A6']
    assert result['semantic_context']['scope_mode'] == 'narrow'
    assert result['semantic_context']['review_stage_keys']


def test_excluded_rag_can_use_tool_agent_framework_without_hidden_dependency():
    result = route('系统学Agent，但不学RAG，重点工作流')
    assert 'A3' not in codes(result)
    assert {'A5', 'A6', 'WR', 'WT'} <= set(codes(result))
    assert not any(s['recipe'] == 'rag' for s in result['stage_blueprints'])


def test_browser_playwright_async_entry_precedes_real_small_core():
    result = route('系统学习Browser Agent，以browser-use为小型核心参考')
    ordered = codes(result)
    assert ordered.index('B0') < ordered.index('B1') < ordered.index('B2') < ordered.index('A8') < ordered.index('B3')
    stages = {s['stage_code']: s for s in result['stage_blueprints']}
    assert 'async' in str(stages['B0']['learning_guidance'])
    assert 'browser-use' in stages['A8']['title']
    assert 'whole_core' in str(stages['A8']['extensions'])
    assert 'Pi' not in str(stages['A8']['resources'])
    assert 'DEEPEN' in str(stages['BR']['learning_guidance'])
    nodes = {n['stable_key']: n for n in result['knowledge_blueprints']}
    assert set(stages['B2']['node_keys']) <= set(nodes[stages['A8']['node_keys'][0]]['prerequisite_keys'])


def test_coding_entry_is_bounded_and_language_gap_is_honest():
    result = route('系统学Coding Agent，先理解Pi核心')
    ordered = codes(result)
    assert ordered.index('A8') < ordered.index('C1') < ordered.index('C6')
    assert 'CR' not in ordered
    core = next(s for s in result['stage_blueprints'] if s['stage_code'] == 'A8')
    assert 'Promise' in str(core['learning_guidance'])
    assert 'needs_research_or_review' in str(core['extensions'])


def test_framework_known_self_report_is_review_and_workflow_adds_replay_depth():
    result = route('系统学习 Agent 和可恢复 Workflow', starting='已熟悉 LangGraph state branch 框架')
    stages = {s['stage_code']: s for s in result['stage_blueprints']}
    assert stages['A5']['learning_guidance']['exposure_relation'] == 'review'
    assert stages['W0']['learning_guidance']['exposure_relation'] == 'review'
    assert '跨进程' in str(stages['W3']['learning_guidance'])
    assert '不代表已核验掌握' in str(stages['A5']['learning_guidance'])


def test_composition_primary_workflow_does_not_copy_three_full_specialties():
    result = route('已有旅行Agent，主学可恢复Workflow，辅以Browser/RAG')
    assert {'W0', 'W3', 'WR', 'WT', 'G1', 'B2'} <= set(codes(result))
    assert not {'G4', 'GR', 'GT', 'B3', 'BR', 'BT'} & set(codes(result))


def test_old_pack_routing_and_inputs_are_not_reinterpreted():
    old = load_pack('agent-application-v6.json')
    before = deepcopy(old)
    result = adapt_semantic_pack(old, '系统学习 Agent', GoalSpec(target='系统学习 Agent'))
    assert old == before
    assert 'A5' not in codes(result) and 'A6' not in codes(result)
    assert 'GR' not in codes(result)


@pytest.mark.parametrize('filename,goal', [('ai-fullstack-v3.json', '已有React电商后台，希望开发AI商品文案客服'),
    ('cloud-services-v3.json', '已有一个 Node API，学习部署、监控、自动发布和恢复')])
def test_other_directions_reuse_current_semantics(filename, goal):
    pack = load_pack(filename)
    result = adapt_semantic_pack(pack, goal, GoalSpec(target=goal))
    assert result['version'] == 3
    assert result['semantic_context']['carrier_kind'] == 'user_project'


@pytest.mark.parametrize('filename,goal,previous,source', [
    ('ai-fullstack-v4.json', '已有React电商后台，希望开发AI商品文案客服', 'F4', 'FS'),
    ('cloud-services-v4.json', '已有一个 Node API，学习部署、监控、自动发布和恢复', 'S2', 'SC')])
def test_directional_tutorial_precedes_bounded_reference(filename, goal, previous, source):
    pack = load_pack(filename)
    result = adapt_semantic_pack(pack, goal, GoalSpec(target=goal))
    order = codes(result)
    assert order.index(previous) < order.index(source)
    stages = {s['stage_code']: s for s in result['stage_blueprints']}
    assert not any(e['topic'].startswith('项目学习：') for e in stages[previous]['extensions'])
    assert 'whole_core' in str(stages[source]['extensions'])
    assert list(stages[source]['learning_guidance']['knowledge_keys']) == stages[source]['node_keys']
    assert len([p for p in result['practice_blueprints'] if p['section_key'] == stages[source]['stable_key']]) == 1
    assert {n['stable_key'] for n in load_pack(filename.replace('-v4', '-v3'))['knowledge_blueprints']} == {
        n['stable_key'] for n in pack['knowledge_blueprints']}
