"""v6.10 next-version content delta; offline, retaining all audited source facts."""
import hashlib
import json
from copy import deepcopy
from pathlib import Path

from app.domain.domain_packs.validation import validate_seed
from app.infrastructure.domain_pack import load_pack
from app.tools.map_semantic_content import bounded_extensions, parts

BASES = {'agent.application': 'agent-application-v5.json', 'ai.fullstack': 'ai-fullstack-v2.json',
         'cloud.services': 'cloud-services-v2.json'}
OUTPUTS = {'agent.application': 'agent-application-v6.json', 'ai.fullstack': 'ai-fullstack-v3.json',
           'cloud.services': 'cloud-services-v3.json'}

ABILITIES = {
    'A0': '能区分模型请求、程序执行与结果消息，用固定响应解释正常和失败路径。',
    'A1': '能实现有停止条件的 Agent loop，追踪工具请求与结果配对，避免无限循环。',
    'A2': '能定义和派发工具，校验参数与权限，保留未知工具和执行失败的证据。',
    'A3': '能用有限文档检索和对应引用回答问题；证据不足时明确无答案。',
    'A4': '能区分历史、事实和临时约束，解释召回、裁剪与摘要的上下文预算边界。',
    'A8': '能解释一个规模可控 Runtime 的工具、状态和失败边界，比较自己的实现并验证一项迁移。',
    'C1': '能追踪 coding loop 的 tool-use 配对和停止，比较 A1 已见循环与软件任务的新边界。',
    'G0': '能区分索引链路与查询链路，比较 A3 已见证据回答与新增检索失败分类。',
}


def _full_extensions(stage):
    """Undo only mapper fragments locally before rebuilding the next version."""
    extensions = []
    groups = set()
    for extension in stage.get('extensions', []):
        group = extension.get('fragment_group')
        if group and group in groups:
            continue
        if group:
            groups.add(group)
        item = deepcopy(extension)
        item['guidance'] = item.pop('original_guidance', item['guidance'])
        for key in ('fragment_group', 'fragment_index', 'fragment_count'):
            item.pop(key, None)
        extensions.append(item)
    return extensions


def build_alignment_packs():
    result = {}
    for key, filename in BASES.items():
        pack = deepcopy(load_pack(filename))
        pack['version'] += 1
        pack['provenance'] += '; v6.10 offline alignment delta: existing audited facts retained; no new body/source review.'
        pack['semantic_policy']['version'] = 2
        pack['semantic_policy']['alignment_version'] = 'v6.10'
        nodes = {n['stable_key']: n for n in pack['knowledge_blueprints']}
        stages = {s['stage_code']: s for s in pack['stage_blueprints']}
        for stage in stages.values():
            stage['extensions'] = _full_extensions(stage)
            code = stage['stage_code']
            node = nodes[stage['node_keys'][0]]
            ability = '能以正常与失败证据验证：' + '；'.join(node.get('acceptance') or [stage['objective']])
            node['objectives'] = parts(ability)
            node['scope'] = '本阶段能力与验收边界；具体阅读范围见精确章节安排。'
            if code in ABILITIES and key == 'agent.application':
                ability = ABILITIES[code]
                stage['objective'] = ability
                nodes[stage['node_keys'][0]]['objectives'] = [ability]
                nodes[stage['node_keys'][0]]['scope'] = ability
                stage['learning_guidance']['learning_focus'] = [ability]
            for extension in stage['extensions']:
                if extension['topic'].startswith('项目学习：'):
                    extension['guidance'] = '学习方式：targeted_deep_dive（目标相关切片）\n' + extension['guidance']
                    extension['guidance'] += '\n参考学习项目与持续实践载体分开；初学 Demo 不代表成熟工程认识。'
        if key == 'agent.application':
            # Context does not depend on learning an entire RAG topic. A8 is a
            # light runtime comparison, not completion of every specialization.
            nodes[stages['A4']['node_keys'][0]]['prerequisite_keys'] = stages['A2']['node_keys'][:]
            nodes[stages['A8']['node_keys'][0]]['prerequisite_keys'] = [
                stages[c]['node_keys'][0] for c in ('A2', 'A4', 'A7')]
            pi = next(r for r in pack['resources'] if r['title'] == 'Pi Coding Agent' and r['verification_status'] == 'reviewed')
            stage = stages['A8']
            reviewed = pi['sections'][:2]
            for section in reviewed:
                section['applicable_node_keys'] = list(dict.fromkeys([*section['applicable_node_keys'], *stage['node_keys']]))
            stage['resources'].append({'role': 'case_study', 'source_ref': pi['source_id'],
                'section_refs': [s['section_id'] for s in reviewed], 'source_version': pi['source_version'],
                'order_index': len(stage['resources']), 'node_keys': stage['node_keys'][:]})
            stage['learning_guidance']['reading_prerequisites'] = [
                '先确认工具、上下文与基础评价的正常/失败证据；未完成先补齐，不要求先学完整 Coding 专项。']
            stage['learning_guidance']['comparison_focus'] = ['同一工具请求：自己的 loop 与成熟 Runtime 如何保存状态、报告失败和停止？']
            for extension in stage['extensions']:
                if extension['topic'] == '本阶段章级练习与教学边界':
                    extension['guidance'] = '前置：工具/上下文/基础评价证据；不要求完整 Coding 或任一专项通关。'
                    extension['guidance'] += '\n小实践：认识当前 Runtime 的核心地图与一条正常/失败链，再比较自己的实现。'
                    extension['guidance'] += '\n出口：调用地图、明确边界和一项迁移验证；clone 或运行成功本身不证明掌握。'
            stage['extensions'].append({'topic': '项目学习：Pi 轻量 Runtime', 'concepts': ['工具循环', '状态边界', '失败路径'],
                'guidance': '学习方式：whole_core（有界核心整体认识）\n为什么现在：已有教程基础和最小实践，开始认识真实工程边界。'
                '\n重点：工具请求→派发→结果→下一轮，以及会话状态；先画核心地图，再读一条正常和失败链。'
                '\n学习深度：只使用已审 SDK lifecycle/storage/prompting/events 与 Sessions and Context 文档范围；'
                '项目身份是候选，不声明全仓深审或已经运行。\n暂不涉及：全仓掌握、安装部署、Coding 全专项和安全隔离平台。'
                '\n思考问题：谁执行工具？状态保存在哪里？重复或失败如何处理？自己的 Demo 有哪些边界尚不存在？'
                '\n预期产物：一张核心调用地图、一个可检查的失败样例、一份事实/推断分开的比较记录。'
                '\n迁移候选：最多选择1–2项适合现有实践载体的改进并验证；可选且可替换，匹配的成熟用户项目可承担参考角色。',
                'links': [pi['canonical_url']], 'search_hints': [], 'thinking_prompts': ['自己的 Demo 与参考 Runtime 的边界有哪些差异？'],
                'required': False})
            for code in ('C1', 'G0'):
                stage = stages[code]
                prior = 'A1' if code == 'C1' else 'A3'
                stage['learning_guidance']['previous_relation'] = f'REVIEW/COMPARE：{prior} 已安排相关概念，不代表已掌握；先确认，再比较本专项新增边界。'
                stage['learning_guidance']['exposure_relation'] = 'compare'
                stage['learning_guidance']['comparison_focus'] = ['重复的循环/检索机制有哪些？当前软件任务/索引链路新增什么失败边界？']
        if key == 'cloud.services':
            stages['S3']['resources'] = deepcopy(stages['S2']['resources'])
            for resource in stages['S3']['resources']:
                resource['node_keys'] = stages['S3']['node_keys'][:]
                source = next(r for r in pack['resources'] if r['source_id'] == resource['source_ref'])
                for section in source['sections']:
                    if section['section_id'] in resource['section_refs']:
                        section['applicable_node_keys'] = list(dict.fromkeys([*section['applicable_node_keys'], *resource['node_keys']]))
            for code in ('S3', 'S7', 'S13'):
                stage = stages[code]
                stage['extensions'].append({'topic': '通用本地演练与待选范围', 'concepts': ['现有服务', '隔离演练', '待选平台'],
                    'guidance': '本次以自己的 API 做通用本地容器/健康检查、观测结果与恢复演练，沿已审 Docker/Compose/Actions 内容。'
                    '云商未选时先保留本地路径；云商部署、Node 对应 OTel instrumentation、数据库备份恢复细项仍 needs_research_or_review。'
                    '本地演练不宣称已经部署云端或覆盖所有数据库恢复。下一步先选择平台/数据库与目标边界，再核对相应教材；不强迫改语言或数据库。',
                    'links': [], 'search_hints': [], 'thinking_prompts': ['当前平台和数据库是什么？哪些操作可以在隔离环境验证？'], 'required': False})
        for stage in stages.values():
            stage['extensions'] = bounded_extensions(stage)
        # Public source rows inherit pack provenance and are immutable too.
        # The new publication therefore gets its own bounded source/section
        # identities, with URLs, review evidence and depth exactly inherited.
        identities = {}
        for source in pack['resources']:
            identities[source['source_id']] = 'src_v610_' + hashlib.sha256((key + str(pack['version']) + source['source_id']).encode()).hexdigest()[:24]
            for section in source['sections']:
                identities[section['section_id']] = 'sec_v610_' + hashlib.sha256((key + str(pack['version']) + section['section_id']).encode()).hexdigest()[:24]
        def remap(value, ids=identities):
            if isinstance(value, str):
                return ids.get(value, value)
            if isinstance(value, list):
                return [remap(item) for item in value]
            if isinstance(value, dict):
                return {ids.get(k, k): remap(v) for k, v in value.items()}
            return value
        pack = remap(pack)
        validate_seed(pack)
        result[key] = pack
    return result


if __name__ == '__main__':
    directory = Path(__file__).resolve().parents[1] / 'infrastructure/content'
    for key, pack in build_alignment_packs().items():
        destination = directory / OUTPUTS[key]
        if destination.exists():
            raise RuntimeError(f'Refusing to overwrite existing content version: {destination.name}')
        destination.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
