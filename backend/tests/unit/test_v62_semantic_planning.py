from copy import deepcopy

import pytest
from app.domain.planning.intent import GoalSpec
from app.domain.planning.semantic_content import adapt_semantic_pack


def pack():
    stages = []
    nodes = []
    practices = []
    for tag in ('core', 'rag', 'workflow', 'browser', 'coding', 'agentic_rl'):
        key = 'stage.' + tag
        node = 'node.' + tag
        stages.append({'stable_key': key, 'title': tag, 'section_kind': 'core', 'objective': tag,
            'node_keys': [node], 'resources': [], 'extensions': [],
            'selection': {'default': tag == 'core', 'capabilities': [] if tag == 'core' else [tag]}})
        nodes.append({'stable_key': node, 'title': tag, 'node_type': 'concept', 'objectives': [tag],
                      'prerequisite_keys': [] if tag == 'core' else ['node.core']})
        practices.append({'stable_key': 'practice.' + tag, 'section_key': key, 'title': tag,
            'goal': '正常与失败练习', 'acceptance': ['结果可检查'], 'node_keys': [node]})
    return {'pack_key': 'agent.application', 'version': 5, 'title': 'Agent路线',
        'semantic_policy': {'version': 1, 'direction': 'agent.application', 'starter_title': '研究与行动助手'},
        'stage_blueprints': stages, 'knowledge_blueprints': nodes, 'practice_blueprints': practices,
        'resources': [], 'resource_refs': [], 'required_node_keys': ['node.core']}


def test_user_project_and_three_recipes_do_not_mutate_public_pack():
    public = pack()
    original = deepcopy(public)
    goal = '我已经有一个旅行规划 Agent，希望系统补 Agent 基础，并强化网页信息获取、可恢复规划和知识检索。'
    selected = adapt_semantic_pack(public, goal, GoalSpec(target=goal))
    assert public == original
    assert selected['semantic_context']['carrier_kind'] == 'user_project'
    assert selected['semantic_context']['carrier_title'] == '旅行规划 Agent'
    assert set(selected['semantic_context']['recipe_refs']) == {'browser', 'workflow', 'rag'}
    assert {s['stable_key'] for s in selected['stage_blueprints']} == {'stage.core', 'stage.browser', 'stage.workflow', 'stage.rag'}
    assert '研究与行动助手' not in str(selected['semantic_context'])
    assert all('旅行规划 Agent' in p['goal'] for p in selected['practice_blueprints'])
    assert all('独立' in p['goal'] for p in selected['practice_blueprints'])


def test_no_project_starter_is_replaceable_suggestion_not_binding():
    goal = '我没有项目想法，想系统学习 Agent 应用开发。'
    selected = adapt_semantic_pack(pack(), goal, GoalSpec(target=goal))
    context = selected['semantic_context']
    assert context['carrier_kind'] == 'starter_candidate'
    assert context['carrier_title'] == '研究与行动助手'
    assert context['binding'] == 'optional' and context['replacement_allowed'] is True
    assert context['recipe_refs'] == []
    assert len(selected['stage_blueprints']) == 1


def test_recipe_miss_keeps_reviewed_common_core_and_visible_gap():
    selected = adapt_semantic_pack(pack(), '我想学语音 Agent。', None)
    assert selected['semantic_context']['research_gaps'] == ['voice']
    assert len(selected['stage_blueprints']) == 1
    ext = selected['stage_blueprints'][0]['extensions'][-1]
    assert 'needs_research_or_review' in ext['guidance']
    assert '语音' in ext['guidance']
    assert not ext['required'] and ext['links'] == []


def test_scope_open_recipe_unknown_is_gap_not_closed_enum_or_fatal():
    selected = adapt_semantic_pack(pack(), '学 Agent', GoalSpec(target='学 Agent', scope=('recipe:rag', 'recipe:voice_custom')))
    assert selected['semantic_context']['recipe_refs'] == ['rag']
    assert 'voice_custom' in selected['semantic_context']['research_gaps']
    assert 'stage.rag' in [s['stable_key'] for s in selected['stage_blueprints']]


def test_legacy_pack_and_explicit_no_rl_remain_compatible():
    legacy = pack()
    del legacy['semantic_policy']
    assert adapt_semantic_pack(legacy, '旅行 Agent，RAG', None) == legacy
    selected = adapt_semantic_pack(pack(), 'Agent，学习 RAG，不需要 RL 或训练模型', None)
    assert 'agentic_rl' not in selected['semantic_context']['recipe_refs']


def test_starting_point_existing_project_and_known_module_diagnostic():
    public = pack()
    public['stage_blueprints'][0]['selection']['skip_when_any'] = ['已会基础']
    selected = adapt_semantic_pack(public, '学 coding Agent', GoalSpec(target='学 coding Agent', starting_point='我已有一个工具仓库，已会基础'))
    assert selected['semantic_context']['carrier_title'] == '工具仓库'
    # Necessary dependencies are retained even after a self-reported skip.
    assert 'node.core' in [n['stable_key'] for n in selected['knowledge_blueprints']]
    assert len(selected['stage_blueprints']) == 2


def test_merge_keeps_carrier_and_curated_exit_when_model_reintroduces_starter():
    from app.agent_workflows.nodes import PlanningNodes
    from app.agent_workflows.planning_batches import run_batched_planning_graph

    from tests.helpers.batched_planning import ScriptedLLM

    selected = adapt_semantic_pack(pack(), '我已有一个旅行 Agent，学 RAG', None)

    class ReintroducedStarter(ScriptedLLM):
        def _practice(self, payload):
            result = super()._practice(payload)
            result['tasks'][0]['goal'] = '强制研究与行动助手'
            result['tasks'][0]['acceptance'] = ['只展示安装成功']
            return result

    trace = run_batched_planning_graph(PlanningNodes(llm=ReintroducedStarter(selected), save_draft=lambda s: 'draft'),
        {'goal': '旅行 Agent', 'run_id': 'v62-unit', 'domain_pack': selected})
    assert trace.stopped_at == 'await_approval', trace.state.get('validation_errors')
    proposal = trace.state['practice_proposal']
    assert proposal['title'] == '用户项目：旅行 Agent'
    assert '强制研究与行动助手' not in str(proposal)
    assert all('结果可检查' in t['acceptance'] for t in proposal['tasks'])


def test_current_runtime_uses_composable_agent_spine_and_existing_service():
    from app.infrastructure.domain_pack import runtime_pack_key_for_goal

    assert runtime_pack_key_for_goal('我已有一个知识库项目，想系统学习 RAG') == 'agent.application'
    assert runtime_pack_key_for_goal('Coding Agent 和 RAG Agent') == 'agent.application'
    assert runtime_pack_key_for_goal('我已经有一个 Node.js API，想学习如何部署、监控、自动发布和恢复。') == 'cloud.services'


def test_actual_training_selection_and_negative_training_are_not_confused():
    from app.infrastructure.domain_pack import load_pack

    public = load_pack('agent-application-v5.json')
    selected = adapt_semantic_pack(public, '我想训练模型，学习 Agent GRPO 参数训练', None)
    codes = {s['stage_code'] for s in selected['stage_blueprints']}
    assert {'R5', 'R6', 'R7', 'R8', 'R9'} <= codes
    selected = adapt_semantic_pack(public, '学习 Agent，不需要 RL 或训练模型', None)
    assert not any(s.get('recipe') == 'agentic_rl' for s in selected['stage_blueprints'])


def test_actual_cloud_user_project_is_not_labeled_as_the_default_starter():
    from app.infrastructure.domain_pack import load_pack

    public = load_pack('cloud-services-v2.json')
    selected = adapt_semantic_pack(public, '我已经有一个 Node.js API，想学习部署、监控、自动发布和恢复。', None)
    assert not any('Task Service' in s['title'] for s in selected['stage_blueprints'])
    assert not any(s.get('selection', {}).get('fallback_only') for s in selected['stage_blueprints'])


def test_knowledge_starting_point_does_not_override_an_explicit_project():
    goal = '我已经有一个 Node.js API，想学习部署、监控、自动发布和恢复。'
    spec = GoalSpec(target=goal, starting_point='有基础编程认知；初学者')
    selected = adapt_semantic_pack(pack(), goal, spec)
    assert selected['semantic_context']['carrier_title'] == 'Node.js API'
    selected = adapt_semantic_pack(pack(), '学习 Agent', GoalSpec(target='学习 Agent', starting_point='有基础编程认知；初学者'))
    assert selected['semantic_context']['carrier_kind'] == 'starter_candidate'


@pytest.mark.parametrize('goal', ['我不想学强化学习，只想做Agent应用', '我不打算学RL，只想做Agent应用', '无需训练模型，我想做Agent应用'])
def test_explicit_application_only_goal_does_not_select_training(goal):
    from app.infrastructure.domain_pack import load_pack
    selected = adapt_semantic_pack(load_pack('agent-application-v5.json'), goal, None)
    assert not any(s.get('recipe') == 'agentic_rl' for s in selected['stage_blueprints'])


def test_original_goal_keeps_carrier_and_capabilities_when_spec_target_is_broad():
    goal = '我已经有一个旅行规划 Agent，希望重点做网页抓取'
    selected = adapt_semantic_pack(pack(), goal, GoalSpec(target='Agent应用开发', starting_point='会Python'))
    assert selected['semantic_context']['carrier_title'] == '旅行规划 Agent'
    assert 'browser' in selected['semantic_context']['recipe_refs']


def test_finite_route_keeps_exact_keys_and_user_carrier_without_expanding_recipes():
    selected = adapt_semantic_pack(pack(), '我已有一个旅行 Agent，做网页和RAG', None, stage_keys=['stage.core', 'stage.rag'])
    assert [s['stable_key'] for s in selected['stage_blueprints']] == ['stage.core', 'stage.rag']
    assert selected['semantic_context']['carrier_title'] == '旅行 Agent'
    assert all('旅行 Agent' in p['goal'] for p in selected['practice_blueprints'])
