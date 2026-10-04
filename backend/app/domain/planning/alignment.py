"""Bounded v6.10 goal rules, before freezing a private canonical snapshot.

Policy v1 and all frozen historical Runs retain their original behavior. This
module uses published content and explicit text only; no model or network IO.
"""
import re
from copy import deepcopy

from app.core.errors import ValidationAppError
from app.domain.planning.guidance import guidance_payload, stage_guidance
from app.domain.planning.intent import required_module_closure

SIGNALS = {
    'rag': r'(?<![a-z])rag(?![a-z])|知识检索|知识库|知识助手|文档问答|资料问答|检索增强|证据回答',
    'workflow': r'(?<![a-z])workflow(?![a-z])|工作流|可恢复|恢复规划|审批|流程自动化',
    'browser': r'(?<![a-z])browser(?![a-z])|网页|浏览器|动态页面|信息获取',
    'coding': r'(?<![a-z])coding(?![a-z])|编程(?:智能体|助手)|代码(?:智能体|助手)|软件任务',
    'evaluation': r'\bevaluation\b|系统评估|系统评价|模型评测',
    'agentic_rl': r'(?<![a-z])(?:rl|ppo|grpo)(?![a-z])|强化学习|参数训练|训练模型',
    'mcp': r'(?<![a-z])mcp(?![a-z])|远程工具|外部协议',
    'framework': r'framework|框架',
}
NEGATIVE = r'不(?:需要|要求|做|学|进行|想|打算)|无需|排除|不要|暂不'


def _signals(text):
    return {tag for tag, pattern in SIGNALS.items() if re.search(pattern, text)}


def _clauses(text):
    return re.split(r'[，,。；;\n]|(?:但|而)是', text)


def _adapt_words(text, carrier, direction):
    """Only authored business labels/example identifiers, never capability keys."""
    replacements = {'研究与行动助手': carrier, 'AI 资料工作台': carrier, 'Task Service': carrier}
    if '旅行' in carrier:
        replacements.update({'资料查询': '目的地与行程信息查询', '合成短文': '合成目的地说明',
            '研究→证据检查→人工审批→行动': '行程提案→证据检查→用户确认→行动',
            '旧事实': '旧行程事实', '临时约束': '临时行程约束'})
    if direction == 'ai.fullstack' and re.search(r'电商|商品|商城', carrier):
        replacements.update({'WorkspacePage': 'CommercePage', 'SearchBar': 'ProductSearch',
            'SourceList': 'ProductList', 'SourceRow': 'ProductRow', '/sources': '/products',
            'source(': 'product(', 'source_id': 'product_id',
            'source_url': 'product_url', '资料对象': '商品对象', '资料条目': '商品条目',
            'source 表': 'product 表', 'workspace/source': 'store/product', 'workspace': 'store'})
    chunks = re.split(r'(https?://[^\s)>\]]+)', text)
    for index, chunk in enumerate(chunks):
        if re.match(r'https?://', chunk):
            continue
        for before, after in sorted(replacements.items(), key=lambda item: -len(item[0])):
            chunk = chunk.replace(before, after)
        chunks[index] = chunk
    return ''.join(chunks)


def adapt_alignment_pack(pack, goal, goal_spec, *, stage_keys=None):
    # Import legacy lexical helpers without duplicating their project guard.
    from app.domain.planning.semantic_content import _normal, _user_project

    result = deepcopy(pack)
    policy = result['semantic_policy']
    targeted = policy.get('alignment_version') == 'v6.12'
    target = goal_spec.target if goal_spec else goal
    scope = list(goal_spec.scope) if goal_spec else []
    constraints = list(goal_spec.constraints) if goal_spec else []
    starting = goal_spec.starting_point if goal_spec else ''
    depth = goal_spec.desired_depth if goal_spec else 'unspecified'
    text = _normal('\n'.join([target, goal, *scope, *constraints]))
    positive = '\n'.join(c for c in _clauses(text) if not re.search(NEGATIVE, c))
    excluded = set().union(*[_signals(c) for c in _clauses(text) if re.search(NEGATIVE, c)])
    if 'agentic_rl' in excluded:
        excluded.add('training')
    explicit_scope = '\n'.join(_normal(c) for c in scope if not re.search(NEGATIVE, _normal(c)))
    if _signals(explicit_scope) & excluded:
        raise ValidationAppError('目标范围与排除限制存在冲突，请明确本次需要的专题。')
    if re.search(r'只(?:想|需要)?(?:学|学习)|仅(?:学|学习|需要)|窄专题|仅.*专题', positive):
        scope_mode = 'narrow'
    else:
        scope_mode = 'complete'
    requested = _signals(positive) - excluded
    requested.update(re.findall(r'recipe\s*[:：]\s*([a-z][a-z0-9_.-]*)', positive))
    if 'agentic_rl' in requested:
        requested.add('training')
    stages = result['stage_blueprints']
    available = {c for s in stages for c in (s.get('selection') or {}).get('capabilities', [])}
    gaps = requested - available
    if re.search(r'语音|\bvoice\b|\bspeech\b', positive):
        gaps.add('voice')
    requested &= available
    secondary = set()
    if targeted and re.search(r'主(?:学|要|目标).*workflow|主(?:学|要|目标).*工作流', positive) and re.search(r'辅以|辅助|辅助.*能力', positive):
        secondary = requested & {'rag', 'browser'}
    carrier = _user_project(target) or _user_project(goal) or _user_project(starting)
    carrier_kind = 'user_project' if carrier else 'starter_candidate'
    carrier = carrier or policy['starter_title']
    selected = set()
    for stage in stages:
        selection = stage.get('selection') or {}
        code, recipe = stage.get('stage_code'), stage.get('recipe')
        capabilities = set(selection.get('capabilities', []))
        trigger = bool(requested & capabilities) or any(_normal(term) in positive for term in selection.get('when_any', []))
        include = bool(selection.get('default', True) or trigger)
        if pack['pack_key'] == 'agent.application':
            if scope_mode == 'narrow':
                include = (code == 'A6' and 'mcp' in requested)
                if 'rag' in requested:
                    include |= code in {'G0', 'G1', 'G2', 'G3'}
                if 'workflow' in requested:
                    include |= code == 'A5'
                if 'coding' in requested:
                    include |= code in {'C1', 'C2'}
                if 'browser' in requested:
                    include |= code in {'B0', 'B1'}
            elif code == 'A8' or (targeted and code in {'A5', 'A6'}):
                include = True
            if depth == 'foundation' and recipe and not (targeted and recipe in requested):
                include = False
            if targeted and scope_mode == 'narrow' and stage.get('pedagogical_role') in {'mature_slice', 'transfer_validation'}:
                include = False
            if targeted and code in {'CR', 'CT'} and not re.search(r'隔离|workspace|工作区|服务化|成熟|深入工程', positive):
                include = False
            if targeted and recipe in secondary:
                include = code in ({'G0', 'G1', 'G2', 'G3'} if recipe == 'rag' else {'B0', 'B1', 'B2'})
            if code == 'A3' and 'rag' in excluded:
                include = False
        if excluded & capabilities or recipe in excluded:
            include = False
        if selection.get('fallback_only') and carrier_kind == 'user_project':
            include = False
        if include:
            selected.add(stage['stable_key'])
    if stage_keys is not None:
        selected = set(stage_keys)
    nodes = result['knowledge_blueprints']
    roots = [n for s in stages if s['stable_key'] in selected for n in s['node_keys']]
    closure = set(required_module_closure(nodes, roots))
    chosen = [s for s in stages if s['stable_key'] in selected or (
        closure.intersection(s['node_keys']) and not (targeted and s.get('pedagogical_role') in {'mature_slice', 'transfer_validation'}))]
    if not chosen:
        raise ValidationAppError('当前已审内容没有匹配本次专题范围，请明确目标或选用基础路线。')
    selected = {s['stable_key'] for s in chosen}
    # A forbidden specialization may not reappear silently through a dependency.
    if any(s.get('recipe') in excluded
           or excluded.intersection((s.get('selection') or {}).get('capabilities', []))
           or (s.get('stage_code') == 'A3' and 'rag' in excluded) for s in chosen):
        raise ValidationAppError('目标范围的必要前置与排除限制存在冲突，请确认前置范围。')
    if carrier_kind == 'user_project' and any((s.get('selection') or {}).get('fallback_only') for s in chosen):
        raise ValidationAppError('已有项目与强制 Starter 前置存在冲突，请确认实践载体范围。')
    result['stage_blueprints'] = chosen
    result['knowledge_blueprints'] = [n for n in nodes if n['stable_key'] in closure]
    result['required_node_keys'] = [n for n in result['required_node_keys'] if n in closure]
    result['practice_blueprints'] = [p for p in result['practice_blueprints'] if p.get('section_key') in selected]
    diagnostic = _normal(starting + '\n' + goal)
    positive_diagnostic = '\n'.join(c for c in _clauses(diagnostic) if not re.search(r'不会|不懂|不熟悉|没(?:有|学)|零基础', c))
    reports_known = bool(re.search(r'会|熟悉|具备|有.*基础|已学|已经学|基础.*调用', positive_diagnostic))
    review_keys = []
    for stage in chosen:
        code = stage.get('stage_code', '')
        node = next(n for n in nodes if n['stable_key'] == stage['node_keys'][0])
        # New exposure stages teach different problems through one protected
        # canonical capability. Retain their authored stage objective; the
        # capability objectives remain the local canonical authority.
        if not targeted:
            stage['objective'] = '；'.join(node['objectives'])
        if pack['pack_key'] == 'cloud.services' and code == 'S3':
            # Inherited S2 primary container reading is useful here. Its Todo
            # case study belongs to S2's paired extension, not S3's scope.
            stage['resources'] = [r for r in stage.get('resources', []) if r['role'] != 'case_study']
        review = reports_known and (
            (code in {'A0', 'A1', 'A2'} and re.search(r'tool|工具|agent.*基础', positive_diagnostic))
            or (targeted and code == 'A5' and re.search(r'框架|framework|langgraph|state|branch', positive_diagnostic))
            or (code in {'F0', 'F1', 'F2'} and re.search(r'react|\bjs\b|javascript', positive_diagnostic))
            or (code == 'F5' and 'sql' in positive_diagnostic))
        guide = guidance_payload(stage_guidance(result, stage))
        label = ('用户项目：' if carrier_kind == 'user_project' else '默认项目候选（可替换）：') + carrier
        guide['practice_delta']['baseline'] = label + '。持续实践载体；参考成熟项目另选，初学 Demo 不代表成熟工程认识。'
        if carrier_kind == 'user_project':
            for field in ('title', 'objective'):
                stage[field] = _adapt_words(stage[field], carrier, pack['pack_key'])
            for field in ('why_now', 'previous_relation'):
                guide[field] = _adapt_words(guide[field], carrier, pack['pack_key'])
            for field in ('learning_focus', 'comparison_focus', 'reading_prerequisites', 'practice_prerequisites'):
                if field in guide:
                    guide[field] = [_adapt_words(v, carrier, pack['pack_key']) for v in guide[field]]
            for field in ('increment', 'preserved', 'validation', 'reuse'):
                guide['practice_delta'][field] = [_adapt_words(v, carrier, pack['pack_key']) for v in guide['practice_delta'][field]]
        if pack['pack_key'] == 'cloud.services' and code in {'S3', 'S7', 'S13'}:
            guide['previous_relation'] = '当前先做隔离本地 Micro Exercise；云商、目标语言/数据库专门操作仍待选/待审。' + guide['previous_relation']
            guide['practice_delta']['increment'] = ['待选环境与对应资料核对后执行；当前本地检查不等于完成：' + v for v in guide['practice_delta']['increment']]
            guide['practice_delta']['validation'] = ['待选环境与对应资料核对后才核验；本地检查不等于通过：' + v for v in guide['practice_delta']['validation']]
        if review:
            review_keys.append(stage['stable_key'])
            guide['previous_relation'] = '简短复习/进入检查：用户自述已有基础，不代表已核验掌握；未通过检查按需补齐。'
            guide['exposure_relation'] = 'review'
            guide['learning_focus'] = ['先以当前项目的一条正常/失败路径检查已有基础；通过后继续，未通过再按章节补缺。', *guide['learning_focus'][:19]]
        stage['learning_guidance'] = guide
        for extension in stage.get('extensions', []):
            if pack['pack_key'] == 'cloud.services' and code in {'S3', 'S7', 'S13'} and extension['topic'] == '通用本地演练与待选范围':
                # Existing draft UI consumes explicit gap topics as well as the
                # workspace; expose the same limitation before confirmation.
                extension['topic'] = '资料缺口：通用本地演练与待选范围'
            if extension['topic'].startswith('项目学习：'):
                extension['required'] = False
            elif carrier_kind == 'user_project':
                extension['guidance'] = _adapt_words(extension['guidance'], carrier, pack['pack_key'])
                for field in ('concepts', 'thinking_prompts', 'search_hints'):
                    extension[field] = [_adapt_words(v, carrier, pack['pack_key']) for v in extension.get(field, [])]
            if pack['pack_key'] == 'cloud.services' and code in {'S3', 'S7', 'S13'} and extension['topic'] == '本阶段章级练习与教学边界':
                extension['concepts'] = ['后续待选/待审：' + v for v in extension.get('concepts', [])]
                extension['guidance'] = '以下专门部署/观测/恢复细项是后续待选/待审范围；当前只做任务中明确的隔离本地练习，不代表这些细项完成。\n' + extension['guidance']
    for practice in result['practice_blueprints']:
        code = next(s.get('stage_code', '') for s in chosen if s['stable_key'] == practice['section_key'])
        original = practice['goal']
        adapted = _adapt_words(original, carrier, pack['pack_key'])
        # Source/framework-specific examples remain separate if their language
        # does not naturally match the explicitly existing service.
        pending_cloud = pack['pack_key'] == 'cloud.services' and code in {'S3', 'S7', 'S13'}
        micro = code == 'A8' or pending_cloud or (pack['pack_key'] == 'cloud.services' and re.search(r'FastAPI|SQLModel|Postgres|pg_dump|pg_restore', adapted)
                                and re.search(r'node|go|java', _normal(carrier)))
        practice['adaptation_mode'] = 'micro_exercise' if micro else 'carrier'
        if micro:
            practice['goal'] = '独立 Micro Exercise：' + adapted + '\n用途：比较/验证本次能力，适合后再迁入用户载体 ' + carrier + '；不要求改原项目语言或数据。'
        else:
            practice['goal'] = '持续实践载体：' + carrier + '\n' + adapted
            if '旅行' in carrier:
                practice['goal'] += '\n业务输入使用目的地/日期/预算，输出行程候选；保留原工具、证据、状态和失败验收。'
            elif pack['pack_key'] == 'ai.fullstack' and re.search(r'电商|商品|商城', carrier):
                practice['goal'] += '\n业务输入使用商品目录与客服请求，输出商品文案或客服候选；保留原 schema、拒绝、权限与失败验收。'
            elif pack['pack_key'] == 'cloud.services' and carrier_kind == 'user_project':
                practice['goal'] += '\n用现有服务的启动命令、路由与测试；语言与数据库沿用现有项目，具体运维实验只在隔离环境执行。'
        if practice['section_key'] in review_keys:
            practice['goal'] = '简短复习检查（用户自述，不代表已核验掌握）：先跑已有正常/失败样例；未通过再补缺。\n' + practice['goal']
        if carrier_kind == 'user_project':
            practice['acceptance'] = [_adapt_words(a, carrier, pack['pack_key']) for a in practice.get('acceptance', [])]
        if pending_cloud:
            local = {
                'S3': '沿已审 Docker/Compose 内容，在隔离本机以现有 API 检查启动、健康端点、日志与容器网络边界。',
                'S7': '对照已审通用日志与健康检查范围，保存一条正常请求与失败请求的日志/时间/边界证据；先确认现有服务的观测缺口。',
                'S13': '在隔离本机沿已审 Compose named volume 范围验证一个合成文件的持久化/重建；列出数据库恢复方案和待核对证据。',
            }[code]
            practice['goal'] = ('独立 Micro Exercise：当前可做：' + local + ' 用户载体：' + carrier
                + '\n待选/待审（needs_research_or_review）：先明确云商/目标语言/数据库并核对对应教材，才执行下述平台或数据库专门操作：'
                + adapted + '\n本地演练不等于云端部署、Node OTel instrumentation 或数据库恢复已经完成。'
                '不操作原库/正式入口；后续专门验收仍需完整证据。')
            practice['acceptance'] = ['待选环境与对应资料核对后才核验本项；本地检查不等于通过：' + a
                                      for a in practice['acceptance']]
        if depth == 'foundation':
            practice['goal'] = '本次基础深度：先沿一条正常/失败链理解核心；不展开额外专项，原验收仍完整保留。\n' + practice['goal']
        elif depth == 'deep':
            practice['goal'] = '本次深入深度：对比两种失败边界，分别保存证据并解释取舍；原验收仍完整保留。\n' + practice['goal']
    context = {'carrier_kind': carrier_kind, 'carrier_title': carrier, 'reference_role': 'study_reference_candidate',
        'carrier_slice': '现有项目的一条可维护用户故事；不自然适配时独立 Micro Exercise',
        'binding': 'optional', 'replacement_allowed': True, 'recipe_refs': sorted(requested),
        'research_gaps': sorted(gaps), 'excluded_recipe_refs': sorted(excluded), 'scope_mode': scope_mode,
        'desired_depth': depth, 'review_stage_keys': review_keys,
        'evaluation': '横切工具、状态与结果；自述和打开资料不代表已核验掌握'}
    result['semantic_context'] = context
    if targeted and pack['pack_key'] == 'agent.application':
        context['specialty_status'] = 'selected' if requested & {'rag', 'coding', 'workflow', 'browser'} else '专项待选'
        if context['specialty_status'] == '专项待选':
            context['pending_specialties'] = ['rag', 'coding', 'workflow', 'browser']
    first = chosen[0]
    later = ('后续专项：RAG / Coding / Workflow / MCP / Browser / 深入 Evaluation 可按目标组合；RL 为另选可选专题。未选专项没有自动生成或完成。'
             '匹配的大型成熟项目在对应前置满足后按3–8个目标相关 slice 学习，一次一个，不要求全仓掌握。'
             if pack['pack_key'] == 'agent.application' else '后续深化按平台和业务目标选择；未审细项保留待审。')
    explanation = ('完整学习路线；当前首步先完成基础与最小应用，然后轻量真实工程认识。' if scope_mode == 'complete'
                   else '本次为窄专题，只展开目标和必要前置；已有基础简短复习检查，不强塞完整方向。')
    explanation += '\n本次深度：' + depth + '；foundation 后置专项深讲，deep 展开已选专项；自述不代表已核验掌握。\n' + later
    if depth == 'deep' and not requested:
        explanation += '\n当前深入核心的证据与边界对比；后续专项仍需用户选择方向，不因 deep 自动展开全部专项。'
    if excluded:
        explanation += '\n显式排除：' + '、'.join(sorted(excluded)) + '；必要前置仍保留并可复习，不暗中开启全套专项。'
    first['extensions'].append({'topic': '本次范围与后续学习路径', 'concepts': [scope_mode, depth],
        'guidance': explanation, 'links': [], 'search_hints': [], 'thinking_prompts': ['现在先做什么？下一步为何需要？'], 'required': False})
    first['extensions'].append({'topic': '持续成果载体与可组合专项', 'concepts': [carrier, *sorted(requested)],
        'guidance': ('用户项目：' if carrier_kind == 'user_project' else '默认项目候选（可替换）：') + carrier
        + '。Evaluation 贯穿，可组合专项与参考学习项目不代替自己的实践载体。', 'links': [], 'search_hints': [],
        'thinking_prompts': ['哪项任务能自然适配，哪项要独立练习？'], 'required': False})
    if gaps:
        first['extensions'].append({'topic': '资料缺口：需要补充研究与审核', 'concepts': sorted(gaps),
            'guidance': 'needs_research_or_review：' + ('语音（voice）' if 'voice' in gaps else '、'.join(sorted(gaps)))
            + ' 尚无足够的已审核专门教学范围；不编造章节。', 'links': [], 'search_hints': [],
            'thinking_prompts': ['需要哪项能力和可检查的资料证据？'], 'required': False})
    reference = re.search(r'参考(?:学习)?项目\s*[:：]\s*(https://github\.com/[\w.-]+/[\w.-]+)(?:\s|[，,。；;]|$)', target + '\n' + goal)
    reference_stage = next((s for s in chosen if s.get('stage_code') == 'A8'), None)
    if reference and reference_stage:
        reference_stage['extensions'].append({'topic': '项目学习：用户指定参考（资格待确认）', 'concepts': ['成熟度与目标匹配待确认'],
            'guidance': '学习方式：whole_core；用户指定参考候选需先确认成熟度、目标匹配与可读范围。'
            '不因提供 URL 自动升级为已审内容，不把初学 Demo 当成熟工程；通过确认后可替换默认参考候选。',
            'links': [reference.group(1)], 'search_hints': [], 'thinking_prompts': ['这个项目是否包含本次要比较的真实工程边界？'], 'required': False})
    return result
