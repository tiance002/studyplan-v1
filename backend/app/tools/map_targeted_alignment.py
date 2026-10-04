"""v6.12 source-preserving teaching exposures; deterministic and offline.

Only mixed teaching/case responsibilities change. New stages reuse existing
capabilities; candidate identities never gain review.
"""
import hashlib
import json
from copy import deepcopy
from pathlib import Path

from app.domain.domain_packs.validation import validate_seed
from app.infrastructure.domain_pack import load_pack
from app.tools.map_planning_alignment import _full_extensions
from app.tools.map_semantic_content import bounded_extensions

OUTPUT = 'agent-application-v7.json'


def build_targeted_alignment_pack():
    pack = deepcopy(load_pack('agent-application-v6.json'))
    pack['version'] = 7
    pack['semantic_policy']['alignment_version'] = 'v6.12'
    pack['provenance'] += '; v6.12 offline pedagogical exposures, inherited source evidence unchanged; runtime NOT RUN.'
    stages = {s['stage_code']: s for s in pack['stage_blueprints']}
    nodes = {n['stable_key']: n for n in pack['knowledge_blueprints']}
    practices = {p['section_key']: p for p in pack['practice_blueprints']}
    for stage in stages.values():
        stage['extensions'] = _full_extensions(stage)
        stage['pedagogical_role'] = 'specialty_tutorial' if stage['recipe'] else 'common_core'
        if stage['recipe']:
            stage['title'] = '专项教程 · ' + stage['title']

    def bind(stage, source_title, titles, role='supplement'):
        source = next(r for r in pack['resources'] if r['title'] == source_title)
        sections = [s for s in source['sections'] if s['title'] in titles]
        if len(sections) != len(titles):
            raise ValueError(f'Missing inherited reviewed section: {source_title}: {titles}')
        for section in sections:
            section['applicable_node_keys'] = list(dict.fromkeys([*section['applicable_node_keys'], *stage['node_keys']]))
        stage['resources'].append(dict(role=role, source_ref=source['source_id'],
            section_refs=[s['section_id'] for s in sections], source_version=source['source_version'],
            order_index=len(stage['resources']), node_keys=stage['node_keys'][:]))

    def teaching(stage, title, focus, relation='deepen', prerequisites=()):
        stage['title'] = title
        stage['objective'] = focus
        guide = stage['learning_guidance']
        guide['why_now'] = focus
        guide['previous_relation'] = relation.upper() + '：复用已有正常/失败证据，检查不足后补缺；学习安排不代表已验证掌握。'
        guide['learning_focus'] = [focus]
        guide['comparison_focus'] = ['当前参考的实现与已学机制有什么相同边界和新增工程问题？']
        guide['exposure_relation'] = relation
        guide['knowledge_keys'] = stage['node_keys'][:]
        guide['reading_prerequisites'] = list(prerequisites)
        guide['practice_delta']['increment'] = [focus]
        guide['practice_delta']['validation'] = ['保存事实/推断分开的正常与失败证据；阅读、clone和运行成功不等于掌握。']

    a5 = stages['A5']
    a5['selection']['default'] = True
    a5['selection']['capabilities'] = ['framework']
    teaching(a5, 'A5 Framework：一个主框架，一次有状态分支与暂停恢复',
        '一深多浅：默认沿已审 Hello LangGraph 与 Graph API 组织已有 Tool Agent；其他框架只比较抽象、依赖成本与适用边界。', 'compare', ['A2 工具、权限与错误证据；不要求先完成完整 RAG。'])
    bind(a5, 'LangGraph Graph API', ['StateGraph/state/nodes/edges/reducers/loop limit'])
    bind(a5, 'LangGraph Persistence and Checkpointers', ['Checkpoint与Store边界'])
    bind(a5, 'LangGraph Interrupts', ['Checkpoint与稳定thread要求', 'Command resume/approve/reject/edit'])
    nodes[a5['node_keys'][0]].update(title=a5['title'], objectives=['能用一个主框架组织有状态、有分支、有明确失败边界的小应用，解释一次最小暂停/恢复。'],
        scope='已有工具 Agent 的 state、node、branch、失败边界、最小 checkpoint/interrupt；其他框架仅作比较。',
        acceptance=['已有正常/失败链在一个主框架中可解释；一次暂停恢复有证据；比较框架不要求多套实现。'])
    practices[a5['stable_key']].update(title=a5['title'] + '：沿已有项目验证',
        goal='复用已有工具/状态链，用一个主框架组织分支；注入失败或最小暂停恢复。其他框架只做边界比较，不另造项目。',
        acceptance=nodes[a5['node_keys'][0]]['acceptance'][:])
    a6 = stages['A6']
    a6['selection']['default'] = True
    teaching(a6, 'A6 MCP：复用只读 server 与最小 server 边界',
        '理解 host/client/server、transport、tool schema 与模型 tool calling；复用现成受控只读 server，并沿已审教程阅读/验证最小 server。', 'compare', ['A2 工具、输入校验、权限与错误；远程高级认证按目标另选。'])
    practices[a6['stable_key']]['goal'] = '连接受控只读 MCP server，列工具、校验参数与调用；记录未知工具、坏参数、断连；沿 Hello 10.5 阅读或验证最小 server。LCC s14 mock 仅比较，不宣称真实协议互通。'
    nodes[a6['node_keys'][0]]['scope'] = 'MCP host/client/server、transport、schema、只读复用、最小server、输入/权限/超时/外部副作用边界；高级OAuth/多协议按目标另选。'
    nodes[a6['node_keys'][0]].update(title=a6['title'], objectives=[a6['objective']], acceptance=[
        '用一次现成受控只读 server 的列工具、参数校验与调用证据解释 host/client/server、transport 和模型 tool calling 的职责；mock 不等于真实 MCP 互通。',
        '沿已审 Hello 10.5 阅读并解释或验证一个最小 server 的工具 schema、分发与结果边界，保留可检查的示例记录。',
        '保存未知工具、坏参数与断连的失败证据，说明权限、敏感信息、输入校验、超时与外部副作用边界。'])
    practices[a6['stable_key']]['acceptance'] = nodes[a6['node_keys'][0]]['acceptance'][:]
    a8 = stages['A8']
    a8['pedagogical_role'] = 'small_core'
    teaching(a8, 'A8 小型开源核心学习：Pi 的工具与会话主链',
        'whole_core：先看核心地图，再追一条工具请求→执行→结果→下一轮与一条失败链；只读已审 SDK 与 Sessions 文档边界，不全仓遍历。', 'compare',
        ['A2/A4/A7 正常失败与上下文证据；先确认 SDK 示例中函数/对象、Promise/事件的最小阅读能力，不要求完整 Coding 专项。'])
    practices[a8['stable_key']]['goal'] = '任选一个适合的小型真实核心参考，沿当前源码画工具与状态地图、正常/失败链，对照已有项目并验证一项适用机制；不另建强制毕业 Demo。'
    for extension in a8['extensions']:
        if extension['topic'].startswith('项目学习：'):
            extension['guidance'] += '\n外部 Coding Agent 先检查本地已有未提交修改，再打开/定位当前源码；不得覆盖或 reset。用户项目是持续载体，参考候选可替换。'
    for code in ['W0', 'W1']:
        teaching(stages[code], stages[code]['title'], 'REVIEW/COMPARE A5 已学状态、节点与分支；用既有证据进入，不从安装框架重新完整做一遍。', 'review')
    for code in ['W3', 'W4']:
        teaching(stages[code], stages[code]['title'], 'DEEPEN A5 最小暂停恢复：新增跨进程重放、thread/store、失败恢复与幂等副作用边界。', 'deepen')
    for code in ['B0', 'B1', 'B2']:
        stages[code]['pedagogical_role'] = 'browser_entry'
    stages['B0']['learning_guidance']['reading_prerequisites'] = ['先在已审 Playwright 入门示例中辨认 sync/async、await 与页面生命周期；只做自控页面。']

    added = []
    # Repeated canonical is an explicit exposure, never a new capability key.
    def exposure(base_code, code, title, focus, cards, resources, role):
        base = stages[base_code]
        stage = deepcopy(base)
        stage.update(stable_key='stage.v612.agent.application.' + code.lower(), stage_code=code,
            title=title, extensions=deepcopy(cards), resources=deepcopy(resources), pedagogical_role=role)
        teaching(stage, title, focus, 'deepen', [base['title'] + ' 已有证据；whole_core 学习只提供入场，不代表专项通关。'])
        task = deepcopy(practices[base['stable_key']])
        task.update(stable_key='practice.v612.agent.application.' + code.lower(), section_key=stage['stable_key'],
            title=title + '：一个可替换能力任务', goal=focus,
            acceptance=(['选择1–2项适合持续项目的机制，保存最小改动或明确不迁移理由；不因参考项目存在而强制替换用户项目。',
                         '复用已有固定坏例，对照改变前后的正常/失败与回归证据，说明改善、退化和适用边界。']
                        if role == 'transfer_validation' else
                        ['任选一个可替换案例证明同一能力；保存当前实现地图、一条失败链、与已学机制的比较及验证证据。']))
        added.append(stage)
        pack['practice_blueprints'].append(task)
        return stage

    for base_code, mature_code, transfer_code, label in [('G6', 'GR', 'GT', 'RAG 入库、检索与引用'),
            ('C10', 'CR', 'CT', 'Coding 会话、取消与隔离'), ('W5', 'WR', 'WT', 'Workflow 持久化、重放与副作用'),
            ('W7', 'WH', 'WI', '协作运行边界'), ('B7', 'BR', 'BT', 'Browser 动态观察与失败边界')]:
        base = stages[base_code]
        cards = [e for e in base['extensions'] if e['topic'].startswith('项目学习：')]
        mature_sources = {r['source_id'] for r in pack['resources'] if r['title'] == 'OpenHands Software Agent SDK'} if base_code == 'C10' else set()
        cases = [r for r in base['resources'] if r['role'] == 'case_study' or r['source_ref'] in mature_sources]
        base['extensions'] = [e for e in base['extensions'] if not e['topic'].startswith('项目学习：')]
        base['resources'] = [r for r in base['resources'] if r['role'] != 'case_study' and r['source_ref'] not in mature_sources]
        if not cards:
            continue
        mature = exposure(base_code, mature_code, '成熟工程：' + label + '的选定切片',
            'DEEPEN：任选一个受控候选，选定一个 ' + label + ' 问题；沿当前源码定位，研究正常/失败链与工程边界；不通读全仓。', cards, cases, 'mature_slice')
        for extension in mature['extensions']:
            extension['guidance'] += '\n本阶段只任选一个可替换案例完成同一能力任务，不要求每个仓库各做一次。外部AI检查本地未提交修改后定位当前源码；记录实际阅读版本，不锁公共commit/path/function。'
        exposure(base_code, transfer_code, '迁移与验证：' + label,
            '从刚才选定切片提出1–2项适合持续项目的最小改动；复用已有回归/坏例证据，验证一次改变并说明不迁移的理由。', [], [], 'transfer_validation')
    # B7 tutorial becomes a bounded source preparation, BR supplies later deepening.
    stages['B7']['title'] = 'Browser 核心复习：quickstart 与源码观察的区别'
    stages['B7']['learning_guidance']['previous_relation'] = 'REVIEW：A8 已看过 browser-use 核心；此处检查库使用与源码解释的区别，BR 才深化新的失败问题。'
    stages['B7']['learning_guidance']['exposure_relation'] = 'review'
    bind(stages['B7'], 'browser-use open-source quickstart', ['Installation/First Agent/local safe example'], 'reference')
    # Insert each engineering exposure after its associated tutorial, followed by migration.
    pack['stage_blueprints'] = [item for stage in pack['stage_blueprints']
        for item in [stage, *[s for s in added if s['node_keys'] == stage['node_keys']]]]
    for stage in pack['stage_blueprints']:
        stage['extensions'] = bounded_extensions(stage)
    # Publication rows have new identities but inherit exact URLs and review records.
    identities = {}
    for source in pack['resources']:
        identities[source['source_id']] = 'src_v612_' + hashlib.sha256(source['source_id'].encode()).hexdigest()[:24]
        for section in source['sections']:
            identities[section['section_id']] = 'sec_v612_' + hashlib.sha256(section['section_id'].encode()).hexdigest()[:24]
    def remap(value):
        if isinstance(value, str):
            return identities.get(value, value)
        if isinstance(value, list):
            return [remap(v) for v in value]
        if isinstance(value, dict):
            return {identities.get(k, k): remap(v) for k, v in value.items()}
        return value
    return validate_seed(remap(pack))


def build_directional_exposures(filename, version, splits):
    """Split already authored project cards from tutorials, without new facts."""
    pack = deepcopy(load_pack(filename))
    pack['version'] = version
    pack['semantic_policy']['alignment_version'] = 'v6.12'
    pack['provenance'] += '; v6.12 stage-only case/tutorial separation; inherited review levels and runtime NOT RUN.'
    sequence = []
    practices = {p['section_key']: p for p in pack['practice_blueprints']}
    for stage in pack['stage_blueprints']:
        stage['extensions'] = _full_extensions(stage)
        sequence.append(stage)
        if stage['stage_code'] not in splits:
            continue
        code, title, mode = splits[stage['stage_code']]
        cards = [e for e in stage['extensions'] if e['topic'].startswith('项目学习：')]
        if not cards:
            raise ValueError('Missing original project cards: ' + stage['stage_code'])
        cases = [r for r in stage['resources'] if r['role'] == 'case_study']
        stage['resources'] = [r for r in stage['resources'] if r['role'] != 'case_study']
        stage['extensions'] = [e for e in stage['extensions'] if not e['topic'].startswith('项目学习：')]
        if pack['pack_key'] == 'cloud.services' and stage['stage_code'] == 'S8':
            stage['title'] = '专项教程：遥测架构、官方 Demo 文档与故障观察'
            stage['learning_guidance']['previous_relation'] = 'REVIEW/COMPARE：先沿已审官方架构/Telemetry/部署/故障文档观察；后继SR才对当前源码的选定工程问题做DEEPEN。'
        source = deepcopy(stage)
        source.update(stable_key='stage.v612.' + pack['pack_key'] + '.' + code.lower(), stage_code=code,
            title=title, resources=cases, extensions=cards,
            pedagogical_role='small_core' if mode == 'whole_core' else 'mature_slice')
        if pack['pack_key'] == 'ai.fullstack' and stage['stage_code'] == 'F6':
            entry = next(s for s in pack['stage_blueprints'] if s['stage_code'] == 'F4')
            source['node_keys'] = entry['node_keys'][:]
            source['selection'] = deepcopy(entry['selection'])
            source['learning_guidance'] = deepcopy(entry['learning_guidance'])
            for assignment in source['resources']:
                assignment['node_keys'] = source['node_keys'][:]
        guide = source['learning_guidance']
        focus = ('whole_core：任选一个可替换真实参考，研究当前核心地图、正常/失败链，与已学教程对照；不通读全仓。'
                 if mode == 'whole_core' else 'DEEPEN：任选一个真实成熟候选的目标相关子系统，定位当前实现与失败边界；一次只研究一个问题。')
        source['objective'] = focus
        guide.update(why_now=focus, learning_focus=[focus],
            previous_relation='COMPARE/DEEPEN：对应教程已经安排，利用已有证据进入；用户自述、阅读和运行不代表掌握。',
            comparison_focus=['教程中的接口/数据/失败边界与当前参考实现有什么差异？'],
            exposure_relation='compare' if mode == 'whole_core' else 'deepen', knowledge_keys=source['node_keys'][:],
            reading_prerequisites=[stage['title'] + ' 的对应教程、正常/失败证据；不补一套无关语言。'])
        guide['practice_delta']['increment'] = [focus]
        guide['practice_delta']['validation'] = ['一个可替换案例的地图、正常/失败链和事实/推断区分；不要求另建毕业Demo。']
        for card in cards:
            card['guidance'] = '学习方式：' + mode + '\n' + card['guidance']
            if pack['pack_key'] == 'ai.fullstack' and code == 'FS':
                card['guidance'] = '本次边界：仅追一条 UI→API→模型adapter→响应/错误的核心链；下方流式/产品强化线索为后续对照，不作为本次必修。\n' + card['guidance']
            card['guidance'] += '\n任选一个可替换案例完成同一能力任务；外部AI检查本地未提交修改后定位当前源码，记录版本；不覆盖/reset，不锁公共commit/path/function。'
            card['required'] = False
        task = deepcopy(practices[stage['stable_key']])
        task.update(stable_key='practice.v612.' + pack['pack_key'] + '.' + code.lower(),
            section_key=source['stable_key'], title=title + '：一个可替换能力任务', goal=focus,
            node_keys=source['node_keys'][:],
            acceptance=['任选一个案例完成核心/目标切片地图、正常与失败证据、与已学机制比较；不要求所有候选各实现一次。'])
        sequence.append(source)
        pack['practice_blueprints'].append(task)
    pack['stage_blueprints'] = sequence
    if pack['pack_key'] == 'ai.fullstack':
        small = next(s for s in sequence if s['stage_code'] == 'FS')
        sequence.remove(small)
        index = next(i for i, s in enumerate(sequence) if s['stage_code'] == 'F4')
        sequence.insert(index + 1, small)
        small['learning_guidance']['reading_prerequisites'] = ['F2 React、F3 API 与 F4 GenAI 请求/响应教程先于源码；Streaming 后续按目标深化。']
    identities = {}
    for resource in pack['resources']:
        identities[resource['source_id']] = 'src_v612_' + hashlib.sha256(resource['source_id'].encode()).hexdigest()[:24]
        for section in resource['sections']:
            identities[section['section_id']] = 'sec_v612_' + hashlib.sha256(section['section_id'].encode()).hexdigest()[:24]
    def remap(value):
        if isinstance(value, str):
            return identities.get(value, value)
        if isinstance(value, list):
            return [remap(v) for v in value]
        if isinstance(value, dict):
            return {identities.get(k, k): remap(v) for k, v in value.items()}
        return value
    for stage in sequence:
        stage['extensions'] = bounded_extensions(stage)
    return validate_seed(remap(pack))


def build_targeted_alignment_packs():
    return {
        OUTPUT: build_targeted_alignment_pack(),
        'ai-fullstack-v4.json': build_directional_exposures('ai-fullstack-v3.json', 4, {
            'F6': ('FS', '小型开源核心学习：AI 对话的请求、响应与错误主链', 'whole_core'),
            'F9': ('FP', '小型服务参考：现有技术栈的 API 与数据闭环', 'whole_core'),
            'F10': ('FR', '成熟工程：AI 产品的选定数据或会话子系统', 'targeted_deep_dive')}),
        'cloud-services-v4.json': build_directional_exposures('cloud-services-v3.json', 4, {
            'S2': ('SC', '小型服务核心学习：Compose 网络、健康与持久化', 'whole_core'),
            'S8': ('SR', '成熟工程：遥测链路与失败定位的选定切片', 'targeted_deep_dive')}),
    }


if __name__ == '__main__':
    directory = Path(__file__).resolve().parents[1] / 'infrastructure/content'
    for filename, pack in build_targeted_alignment_packs().items():
        destination = directory / filename
        if destination.exists():
            raise RuntimeError('Refusing to overwrite published candidate: ' + filename)
        destination.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
