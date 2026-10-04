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
            if not re.search(r'(?:用户项目|已有项目|我的项目)\s*[:：]', match.group(0)) and re.search(
                r'(?:经验|基础|认知|知识|能力|了解|背景|经历)$', value
            ):
                continue
            if not re.search(r'用户项目|已有项目|我的项目|一个|一套|已经有|已有', match.group(0)) and not re.search(
                r'项目|仓库|应用|后台|服务|助手|网站|(?i:\bagent\b|\bapi\b)', value
            ):
                continue
            if value and not re.search(r'项目想法|项目点子|项目建议', value):
                return value
    return ''


def adapt_semantic_pack(pack, goal, goal_spec, *, stage_keys=None):
    policy = pack.get('semantic_policy') or {}
    if policy.get('version') == 2:
        from app.domain.planning.alignment import adapt_alignment_pack
        selected = adapt_alignment_pack(pack, goal, goal_spec, stage_keys=stage_keys)
        if policy.get('alignment_version') == 'v6.12' and pack.get('pack_key') == 'agent.application':
            return _targeted_reference_route(selected)
        return selected
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


def _targeted_reference_route(pack):
    """Order source-bound entry exposures before the selected small core.

    This runs before freezing; old published versions/Run snapshots are untouched.
    """
    stages = pack['stage_blueprints']
    context = pack['semantic_context']
    recipes = set(context['recipe_refs'])
    core = next((s for s in stages if s.get('stage_code') == 'A8'), None)
    if not core:
        return pack
    if 'browser' in recipes and 'coding' not in recipes:
        # The same generic Runtime capability is taught through a different
        # actual candidate. Only already reviewed documentation is assigned.
        source = next(r for r in pack['resources'] if r['title'] == 'browser-use Agent, Browser and Examples references')
        sections = [s for s in source['sections'] if s['title'] == 'Agent/Browser/History/Examples']
        for section in sections:
            section['applicable_node_keys'] = list(dict.fromkeys([*section['applicable_node_keys'], *core['node_keys']]))
        core['title'] = 'A8 小型开源核心学习：browser-use 的观察、动作与历史主链'
        core['resources'] = [dict(role='case_study', source_ref=source['source_id'],
            section_refs=[s['section_id'] for s in sections], source_version=source['source_version'],
            order_index=0, node_keys=core['node_keys'][:])]
        core['extensions'] = [e for e in core['extensions'] if not e['topic'].startswith('项目学习：')]
        core['extensions'].append(dict(topic='项目学习：browser-use 小型核心（可替换）',
            concepts=['观察', '动作', '历史', '停止与失败'],
            guidance='学习方式：whole_core（有界核心整体）\n前置：Playwright B0/B1/B2 的页面、定位、等待与 async 入场。'
                '\n沿当前公开源码定位 Agent/Browser/History 的一次观察→动作→结果→下一轮与失败链；只研究足够解释核心的范围。'
                '\n比较自己的工具loop；当前资料为 selected_sections_read 文档，实际源码阅读与运行 NOT RUN，不认证全仓已审。'
                '\n产物：核心地图、正常/失败证据与一项小验证；不读全部Cloud/CLI/部署。'
                '\n外部Coding Agent先检查已有未提交修改，再定位当前源码并记录版本；不得覆盖/reset。候选可替换，与持续用户项目分开。',
            links=['https://github.com/browser-use/browser-use'], search_hints=[],
            thinking_prompts=['观察何时过期，失败何时终止？'], required=False))
        core['learning_guidance']['learning_focus'] = ['whole_core：browser-use 的观察、动作与历史主链；必要页面/异步入场先于源码，后续专门失败问题才深化。']
        entries = [s for s in stages if s.get('stage_code') in {'B0', 'B1', 'B2'}]
        core['learning_guidance']['reading_prerequisites'] = [s['title'] for s in entries]
        node = next(n for n in pack['knowledge_blueprints'] if n['stable_key'] in core['node_keys'])
        node['prerequisite_keys'] = list(dict.fromkeys([*node.get('prerequisite_keys', []), *[k for s in entries for k in s['node_keys']]]))
        preceding = [s for s in stages if s.get('stage_code', '').startswith('A') and s is not core]
        pack['stage_blueprints'] = preceding + entries + [core] + [s for s in stages if s not in preceding and s not in entries and s is not core]
        core['learning_guidance']['previous_relation'] = 'COMPARE：先补 Playwright/async 最小入场，再看核心；B3/B5/B6/BR 后续研究新的动态、权限、评价问题。'
        for practice in pack['practice_blueprints']:
            if practice['section_key'] == core['stable_key']:
                practice['goal'] = '任选一个适合的 Browser 小型核心参考，追观察→动作→结果的一条正常与失败链；比较现有工具loop并做自控页面的小验证。无需新建毕业Demo。'
    elif 'coding' in recipes:
        core['learning_guidance']['reading_prerequisites'] = ['先在已审 Pi SDK 示例检查函数/对象、Promise/事件与工具调用的最小阅读能力；不足先补，不要求完整C组先通关。']
        core['extensions'].append(dict(topic='Pi 核心阅读的最小语言入场', concepts=['Promise', '事件', '工具接口'],
            guidance='先用已审 SDK lifecycle/storage/prompting/events 示例辨认工具函数、对象、Promise和事件顺序。'
                '这是源码阅读入场检查，未绑定独立TypeScript语法课程；不能通过检查时语言教程仍 needs_research_or_review，先补齐再进入核心。'
                'A8只读工具/会话主链，C组后续深化上下文、任务与取消；不把一段SDK阅读当完整Coding专项。',
            links=[], search_hints=[], thinking_prompts=['能解释示例中一次异步调用与事件的先后吗？'], required=False))
    return pack
