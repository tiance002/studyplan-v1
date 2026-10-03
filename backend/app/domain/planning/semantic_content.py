"""Private, deterministic selection of a published semantic content snapshot.

This prepares the existing batch input. It neither publishes content nor changes
old manifests, graphs, project identities, or completion evidence.
"""
import re
import unicodedata
from copy import deepcopy

from app.domain.planning.guidance import guidance_payload, stage_guidance
from app.domain.planning.intent import required_module_closure


def _normal(text):
    return unicodedata.normalize('NFKC', text).casefold()


def _user_project(text):
    for pattern in (
        r'(?:用户项目|已有项目|我的项目)\s*[:：]\s*([^，,。；;\n]{1,100})',
        r'(?:我)?(?:已经|已)?有(?:一个|一套)?\s*([^，,。；;\n]{1,100}?)(?=，|,|。|；|;|\n|希望|想把|想学|想要|$)',
    ):
        match = re.search(pattern, text)
        if match and not re.search(r'没有|暂无|无项目|没项目', match.group(0)):
            value = match.group(1).strip()
            if not re.search(r'用户项目|已有项目|我的项目|一个|一套|已经有|已有', match.group(0)) and not re.search(
                r'项目|仓库|应用|后台|服务|助手|网站|(?i:\bagent\b|\bapi\b)', value
            ):
                continue
            if value and not re.search(r'项目想法|项目点子|项目建议', value):
                return value
    return ''


def adapt_semantic_pack(pack, goal, goal_spec, *, stage_keys=None):
    policy = pack.get('semantic_policy') or {}
    if policy.get('version') != 1:
        return pack
    result = deepcopy(pack)
    target = goal_spec.target if goal_spec else goal
    starting = goal_spec.starting_point if goal_spec else ''
    scope = list(goal_spec.scope) if goal_spec else []
    constraints = list(goal_spec.constraints) if goal_spec else []
    text = _normal('\n'.join([target, goal, *scope, *constraints]))
    diagnostic = _normal(starting)
    carrier = _user_project(target) or _user_project(goal) or _user_project(starting)
    carrier_kind = 'user_project' if carrier else 'starter_candidate'
    if not carrier:
        carrier = policy['starter_title']
    # These are phrase recognizers, not a closed Recipe type. Content supplies
    # the available open labels; explicit recipe:<label> remains extensible.
    signals = {
        'rag': r'\brag\b|知识检索|知识库|知识助手|资料检索|检索增强|证据回答',
        'workflow': r'\bworkflow\b|工作流|可恢复|恢复规划|审批|流程自动化',
        'browser': r'\bbrowser\b|网页|浏览器|动态页面|信息获取',
        'coding': r'\bcoding\b|编程(?:智能体|助手)|代码(?:智能体|助手)|软件任务',
        'evaluation': r'\bevaluation\b|系统评估|系统评价|模型评测',
        'agentic_rl': r'(?<![a-z])(?:rl|ppo|grpo)(?![a-z])|强化学习|参数训练|训练模型',
    }
    requested = {tag for tag, pattern in signals.items() if re.search(pattern, text)}
    requested.update(re.findall(r'recipe\s*[:：]\s*([a-z][a-z0-9_.-]*)', text))
    excluded = set()
    if re.search(r'(?:不(?:需要|要求|做|学|进行|想(?:做|学|进行)?|打算(?:做|学|进行)?)|无需(?:做|学|进行)?)[^，,。；;\n]*?(?:(?<![a-z])rl(?![a-z])|训练|强化学习)', text):
        excluded.update(('agentic_rl', 'training'))
        requested.difference_update(excluded)
    stages = result.get('stage_blueprints') or []
    available = {c for s in stages for c in (s.get('selection') or {}).get('capabilities', [])}
    gaps = sorted(requested - available)
    if re.search(r'语音|\bvoice\b|\bspeech\b', text):
        gaps.append('voice')
    requested.intersection_update(available)
    selected = set()
    for stage in stages:
        selection = stage.get('selection') or {}
        triggered = bool(requested.intersection(selection.get('capabilities', [])))
        triggered = triggered or any(_normal(term) in text for term in selection.get('when_any', []))
        include = selection.get('default', True) or triggered
        if selection.get('fallback_only') and carrier_kind == 'user_project':
            include = False
        if excluded.intersection(selection.get('capabilities', [])) or stage.get('recipe') in excluded:
            include = False
        if any(_normal(term) in diagnostic for term in selection.get('skip_when_any', [])):
            include = False
        if include:
            selected.add(stage['stable_key'])
    if stage_keys is not None:
        # Existing finite changes already decide their exact route. Adapt its
        # carrier and evidence wording without adding newly matched recipes.
        selected = set(stage_keys)
    # Preserve necessary dependencies, even when a starting point self-report
    # suggests a skip. It never upgrades knowledge to mastered/verified.
    nodes = result.get('knowledge_blueprints') or []
    roots = [n for s in stages if s['stable_key'] in selected for n in s.get('node_keys', [])]
    closure = set(required_module_closure(nodes, roots))
    for stage in stages:
        if closure.intersection(stage.get('node_keys', [])):
            selected.add(stage['stable_key'])
    chosen = [s for s in stages if s['stable_key'] in selected]
    if not chosen:
        # No recipe/diagnostic should erase the published Common Core entirely.
        chosen = [s for s in stages if (s.get('selection') or {}).get('default', True)][:1]
        selected = {s['stable_key'] for s in chosen}
    roots = [n for s in chosen for n in s.get('node_keys', [])]
    closure = set(required_module_closure(nodes, roots))
    result['stage_blueprints'] = chosen
    result['knowledge_blueprints'] = [n for n in nodes if n['stable_key'] in closure]
    result['required_node_keys'] = [n for n in result.get('required_node_keys', []) if n in closure]
    result['practice_blueprints'] = [p for p in result.get('practice_blueprints', []) if p.get('section_key') in selected]
    context = {
        'carrier_kind': carrier_kind, 'carrier_title': carrier,
        'carrier_slice': '先选一条用户故事的可维护纵切面；实现可替换，保留测试、接口、数据、决策与证据',
        'binding': 'optional', 'replacement_allowed': True,
        'recipe_refs': sorted(requested), 'research_gaps': sorted(set(gaps)),
        'evaluation': '横切每个工具、检索、状态与模型能力；不是排他职业分支',
    }
    result['semantic_context'] = context
    label = ('用户项目：' if carrier_kind == 'user_project' else '默认项目候选（可替换）：') + carrier
    carrier_note = label + '。适合时沿一个纵切面增量实践；不适合时保留独立 Micro Exercise，不强制迁入。'
    for stage in chosen:
        # Adapt only private carrier wording. Public chapter titles, review
        # evidence and optional project identities retain their original text.
        if carrier_kind == 'user_project':
            for field in ('title', 'objective'):
                stage[field] = stage.get(field, '').replace(policy['starter_title'], carrier)
        guide = guidance_payload(stage_guidance(result, stage))
        if carrier_kind == 'user_project':
            for field in ('why_now', 'previous_relation'):
                guide[field] = guide[field].replace(policy['starter_title'], carrier)
            for field in ('increment', 'preserved', 'validation', 'reuse'):
                guide['practice_delta'][field] = [
                    value.replace(policy['starter_title'], carrier)
                    for value in guide['practice_delta'][field]
                ]
        guide['practice_delta']['baseline'] = carrier_note
        stage['learning_guidance'] = guide
        for extension in stage.get('extensions', []):
            if extension.get('topic', '').startswith('项目学习：'):
                extension['required'] = False
                extension['guidance'] += '\n项目案例（可选）：可由用户项目替换；不要求选择或安装该仓库。'
    for practice in result['practice_blueprints']:
        practice['goal'] = carrier_note + '\n' + practice['goal']
    if chosen:
        chosen[0].setdefault('extensions', []).append({
            'topic': '持续成果载体与可组合专项', 'concepts': [label, *sorted(requested)],
            'guidance': carrier_note + '\nEvaluation 贯穿；选中能力可组合，默认候选不定义用户归属。',
            'links': [], 'search_hints': [], 'thinking_prompts': ['哪项能力适合当前项目，哪项更适合独立练习？'], 'required': False,
        })
        if gaps:
            chosen[0]['extensions'].append({
                'topic': '资料缺口：需要补充研究与审核', 'concepts': sorted(set(gaps)),
                'guidance': 'needs_research_or_review：' + ('语音（voice）' if 'voice' in gaps else '、'.join(gaps))
                    + ' 尚无足够的已审核专门教学范围。先学已审 Common Core 与适用能力，不编造章节，不自动发布新资料。',
                'links': [], 'search_hints': [], 'thinking_prompts': ['需要哪项能力和哪些可检查的资料证据？'], 'required': False,
            })
    return result
