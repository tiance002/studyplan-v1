from copy import deepcopy

import pytest
from app.core.errors import ValidationAppError
from app.domain.planning.intent import GoalSpec
from app.domain.planning.semantic_content import adapt_semantic_pack
from app.infrastructure.domain_pack import load_pack, runtime_pack_key_for_goal


def select(goal, *, key='agent.application', starting='', depth='unspecified', scope=(), constraints=()):
    filename = {'agent.application': 'agent-application-v6.json', 'ai.fullstack': 'ai-fullstack-v3.json',
                'cloud.services': 'cloud-services-v3.json'}[key]
    return adapt_semantic_pack(load_pack(filename), goal, GoalSpec(
        target=goal, starting_point=starting, desired_depth=depth, scope=scope, constraints=constraints))


def codes(pack):
    return {s['stage_code'] for s in pack['stage_blueprints']}


def test_explicit_ai_agent_target_wins_over_generic_ai():
    assert runtime_pack_key_for_goal('系统学习 AI Agent 应用开发。') == 'agent.application'
    assert runtime_pack_key_for_goal('开发 AI 全栈应用') == 'ai.fullstack'
    assert runtime_pack_key_for_goal('学习云服务部署') == 'cloud.services'


def test_system_agent_first_small_app_keeps_real_engineering_and_later_choices():
    result = select('零基础系统学习 Agent 应用开发，先做一个最小应用。')
    assert {'A0', 'A1', 'A2', 'A7', 'A8'} <= codes(result)
    assert not any(s.get('recipe') for s in result['stage_blueprints'])
    stage = next(s for s in result['stage_blueprints'] if s['stage_code'] == 'A8')
    assert any(e['topic'].startswith('项目学习：') for e in stage['extensions'])
    assert any(r['role'] == 'case_study' for r in stage['resources'])
    assert '后续专项' in str(result['stage_blueprints'][0]['extensions'])


def test_mcp_topic_only_expands_necessary_prerequisites():
    result = select('我只想学 MCP；已经会基础 Tool 调用。', starting='已经会基础 Tool 调用')
    assert 'A6' in codes(result)
    assert not {'A3', 'A4', 'A7', 'A8'} & codes(result)
    assert not any(s.get('recipe') for s in result['stage_blueprints'])
    assert result['semantic_context']['scope_mode'] == 'narrow'
    assert result['semantic_context']['review_stage_keys']


def test_exclusion_beats_positive_recipe_trigger_and_does_not_drop_dependencies():
    result = select('系统学 Agent，暂时不学 RAG 和浏览器，重点是工具与可恢复工作流。')
    assert not any(s.get('recipe') in {'rag', 'browser'} for s in result['stage_blueprints'])
    assert 'A3' not in codes(result)
    assert {'A2', 'A5', 'A8'} <= codes(result)
    keys = {n['stable_key'] for n in result['knowledge_blueprints']}
    assert all(set(n.get('prerequisite_keys', [])) <= keys for n in result['knowledge_blueprints'])


def test_explicit_scope_constraints_conflict_asks_for_scope_in_existing_error():
    with pytest.raises(ValidationAppError, match='范围.*冲突'):
        select('学习 Agent', scope=('必须学 RAG',), constraints=('不学 RAG',))


def test_self_report_changes_review_practice_without_claiming_mastery():
    goal = '系统学 AI 全栈应用'
    novice = select(goal, key='ai.fullstack', starting='零基础')
    familiar = select(goal, key='ai.fullstack', starting='已熟悉 React/JS/SQL')
    assert familiar['semantic_context']['review_stage_keys']
    assert familiar['practice_blueprints'] != novice['practice_blueprints']
    assert '用户自述' in str(familiar['stage_blueprints'])
    assert '不代表已核验掌握' in str(familiar['stage_blueprints'])


def test_depth_changes_current_recipe_detail_but_keeps_complete_map():
    goal = '系统学 Agent，重点 RAG'
    foundation = select(goal, depth='foundation')
    deep = select(goal, depth='deep')
    assert len(foundation['stage_blueprints']) < len(deep['stage_blueprints'])
    assert 'A8' in codes(foundation) and 'A8' in codes(deep)
    assert '后续专项' in str(foundation['stage_blueprints'][0]['extensions'])


@pytest.mark.parametrize('goal,key,unwanted', [
    ('我已有一个旅行规划 Agent，想系统补 Agent 能力', 'agent.application', '研究与行动助手'),
    ('我已有一个电商后台，想开发 AI 全栈商品文案与客服', 'ai.fullstack', 'SourceRow'),
    ('我已有一个 Node.js API，学部署、监控、自动发布和恢复', 'cloud.services', 'Task Service'),
])
def test_specific_tasks_are_adapted_or_marked_micro_exercise(goal, key, unwanted):
    result = select(goal, key=key)
    assert result['semantic_context']['carrier_kind'] == 'user_project'
    for task in result['practice_blueprints']:
        assert task.get('adaptation_mode') in {'carrier', 'micro_exercise'}
        if unwanted in task['goal']:
            assert '独立 Micro Exercise' in task['goal']
    assert result['semantic_context']['reference_role'] != result['semantic_context']['carrier_kind']


def test_voice_gap_keeps_valid_core_and_does_not_invent_recipe():
    result = select('我要做语音 Agent，已有 Python 基础')
    assert 'voice' in result['semantic_context']['research_gaps']
    assert not any(s.get('recipe') == 'voice' for s in result['stage_blueprints'])


def test_commerce_schema_uses_actual_product_entities_before_freeze():
    result = select('我已有一个电商后台，想开发 AI 全栈商品文案与客服', key='ai.fullstack')
    task = next(p for p in result['practice_blueprints'] if p['section_key'].endswith('.f5'))
    assert 'product(' in task['goal']
    assert 'source(' not in task['goal']


def test_cloud_gaps_cannot_claim_pending_platform_steps_completed_by_local_check():
    result = select('我已有一个 Node.js API，学部署、监控、自动发布和恢复', key='cloud.services')
    for code in ('s3', 's7', 's13'):
        task = next(p for p in result['practice_blueprints'] if p['section_key'].endswith('.' + code))
        assert task['adaptation_mode'] == 'micro_exercise'
        assert '当前可做' in task['goal'] and '待选/待审' in task['goal']
        assert all('本地检查不等于通过' in a for a in task['acceptance'])
        stage = next(s for s in result['stage_blueprints'] if s['stage_code'].lower() == code)
        assert any(e['topic'].startswith('资料缺口：') and 'needs_research_or_review' in e['guidance'] for e in stage['extensions'])


def test_broad_depth_changes_evidence_work_without_inventing_specializations():
    foundation = select('系统学习 Agent 应用开发', depth='foundation')
    deep = select('系统学习 Agent 应用开发', depth='deep')
    assert codes(foundation) == codes(deep)
    assert foundation['practice_blueprints'] != deep['practice_blueprints']
    assert '两种失败边界' in str(deep['practice_blueprints'])


def test_explicit_future_route_cannot_override_negative_scope():
    pack = load_pack('agent-application-v6.json')
    spec = GoalSpec(target='系统学 Agent，不学 RAG', constraints=('不学 RAG',))
    with pytest.raises(ValidationAppError, match='冲突'):
        adapt_semantic_pack(pack, spec.target, spec, stage_keys=['stage.v62.agent.application.a3'])


def test_no_public_source_mutation_and_old_format_still_supported():
    public = load_pack('agent-application-v5.json')
    original = deepcopy(public)
    result = adapt_semantic_pack(public, '系统学 Agent', None)
    assert public == original
    assert result['version'] == 5


@pytest.mark.parametrize('old,new', [('agent-application-v5.json', 'agent-application-v6.json'),
    ('ai-fullstack-v2.json', 'ai-fullstack-v3.json'), ('cloud-services-v2.json', 'cloud-services-v3.json')])
def test_new_publication_keeps_source_depth_and_original_body_evidence(old, new):
    before, after = load_pack(old), load_pack(new)
    assert len(before['resources']) == len(after['resources'])
    for source, revised in zip(before['resources'], after['resources'], strict=True):
        assert source['source_id'] != revised['source_id']
        for field in ('canonical_url', 'title', 'verification_status', 'review_evidence', 'metadata', 'runtime_validation'):
            assert source.get(field) == revised.get(field), field
        assert len(source['sections']) == len(revised['sections'])
        for section, revised_section in zip(source['sections'], revised['sections'], strict=True):
            for field in ('title', 'url', 'verification_status', 'review_evidence', 'review_note', 'anchor'):
                assert section.get(field) == revised_section.get(field), field
        assert not str(revised.get('public_seed_status', '')).startswith('hold_')


def test_private_teaching_instructions_match_carrier_and_preserve_reference_urls():
    result = select('我已有一个 Node.js API，学部署、监控、自动发布和恢复', key='cloud.services')
    for stage in result['stage_blueprints']:
        assert 'Task Service' not in str(stage['learning_guidance'])
        assert not any('Task Service' in str({k: e.get(k) for k in ('topic', 'guidance', 'concepts', 'thinking_prompts', 'search_hints')})
                       for e in stage['extensions'] if not e['topic'].startswith('项目学习：'))
    from app.domain.planning.alignment import _adapt_words
    assert _adapt_words('SourceRow https://example.com/workspace/sources', '电商后台', 'ai.fullstack') == 'ProductRow https://example.com/workspace/sources'
