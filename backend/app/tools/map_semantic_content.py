"""Offline, deterministic v6.2 research-to-pack mapping. No network or database IO.

The authored teaching rows/bodies remain verbatim in teaching_evidence. Bounded
guidance is an additional view, never a replacement for those detailed records.
Run from the repository: python -m app.tools.map_semantic_content --write.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from app.domain.domain_packs.validation import validate_seed

ROOT = Path(__file__).resolve().parents[3]
RESEARCH = ROOT / 'docs/research/semantic-corrected-2026-10-04'
CONTENT = ROOT / 'backend/app/infrastructure/content'
FILES = {'agent.application': 'agent-application-v5.json', 'ai.fullstack': 'ai-fullstack-v2.json',
         'cloud.services': 'cloud-services-v2.json'}
VERSIONS = {'agent.application': 5, 'ai.fullstack': 2, 'cloud.services': 2}
STARTERS = {'agent.application': '研究与行动助手', 'ai.fullstack': 'AI 资料工作台', 'cloud.services': 'Task Service'}
DATE = '2026-10-03T00:00:00+08:00'
CARRIER = ('优先用户已有合适项目；过大时裁成纵切面，无项目才建议默认候选。'
           '不自然适配时保留独立 Micro Exercise；允许更换实现，保留问题、接口、数据、测试与验证证据。')
EVAL = ('评价贯穿：记录 input/tool/args/result/final/outcome；确定性规则与环境终态优先，'
        '保留失败、未跑项与费用；judge只辅助并人工校准。用户提交和确认证据后更新学习进度，'
        '打开章节不等于掌握，不自动评分。')


def clean(value):
    return re.sub(r'\*\*|`', '', value).strip()


def parts(value, limit=1000):
    """Lossless bounded text partition; reject overload rather than drop content."""
    text = clean(value) or '本阶段没有新增该类材料；沿当前学习证据按需核对。'
    values = []
    while len(text) > limit:
        stop = max(text.rfind(mark, 0, limit) for mark in ('。', '；', '\n', '，', ' '))
        stop = stop + 1 if stop >= limit // 3 else limit
        values.append(text[:stop])
        text = text[stop:]
    if text:
        values.append(text)
    if len(values) > 20:
        raise ValueError('Teaching field exceeds bounded guidance; split the authored unit')
    return values


def blocks(text, pattern):
    matches = list(re.finditer(pattern, text, re.M))
    result = []
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        level = len(text[match.start():].split(' ', 1)[0])
        next_heading = re.search(r'^#{1,' + str(level) + r'} ', text[match.end():end], re.M)
        if next_heading:
            end = match.end() + next_heading.start()
        result.append((match.group(1), match.group(2).strip(), text[match.end():end].strip()))
    return result


def labeled(body, labels):
    hits = []
    continuing = False
    for line in body.splitlines():
        if any(label in line for label in labels):
            hits.append(clean(line.lstrip('- ')))
            continuing = True
        elif continuing and (line.startswith(' ') or re.match(r'^\d+\.', line)):
            hits.append(clean(line))
        elif line.strip():
            continuing = False
    return '\n'.join(hits)


def prose_evidence(title, body):
    why = labeled(body, ['为什么现在', 'Why now']) or title
    prerequisite = labeled(body, ['前置', '入场测', '先诊断']) or '按本阶段首次使用能力做诊断；已会者跳过，缺口才即时补齐。'
    primary = labeled(body, ['主读', 'Primary', '教程读法', '主资料', '主读/主做', '主读顺序'])
    if not primary:
        primary = '\n'.join(p for p in body.split('\n\n') if any(s in p for s in ('主读', '连续读', '先读', '这是本路线原创练习')))
    primary = primary or '本阶段使用自身任务和独立合成数据练习，不假设存在额外已审教程。'
    supplement = labeled(body, ['补充', 'JIT', '选读', '补缺', '略过', '跳过', '暂不学', '按需'])
    exposure = labeled(body, ['重复', '暴露', '关系', 'REVIEW', 'COMPARE', 'DEEPEN', 'VERSION_CONTEXT'])
    practice = labeled(body, ['小实践', '练习：', '学习实验', '实验：'])
    if not practice:
        practice = '\n'.join(p for p in body.split('\n\n') if any(s in p for s in ('小实践', '小练习', '用Python标准库', '练习：')))
    increment = labeled(body, ['项目增量', 'Task Service 增量', '持续增量', '持续助手增量', '持续增量是', '持续工作台'])
    exit_gate = labeled(body, ['出口', '退出', '退出标准', '退出成果', '退出产物'])
    return dict(why_now=why, jit_prerequisite=prerequisite, primary_chapters=primary,
                supplement_comparison=supplement or '没有新增必修补充；教材之外的资料仅按具体缺口选读。',
                exposure_relation=exposure or 'NEW：新增能力；已有者以诊断证据 REVIEW，框架差异按 COMPARE。',
                small_practice=practice or '用本段给出的合成任务、输入与反例执行独立练习；完整规格见原教学单元。',
                outcome_increment=increment or '将本阶段可验证的能力按需要迁回用户载体；否则保留独立练习。',
                exit_gate=exit_gate or '保存完整教学单元要求的结果、失败解释和独立验证证据。', raw_body=body)


def table_rows(text, prefix):
    rows = []
    for line in text.splitlines():
        if not line.startswith('|'):
            continue
        cells = [x.strip() for x in line.strip('|').split('|')]
        if re.match(prefix, cells[0]):
            rows.append(cells)
    return rows


def authored_stages(read):
    result = {'agent.application': [], 'ai.fullstack': [], 'cloud.services': []}
    for cells in table_rows(read('AGENT_APPLICATION_TEMPLATE_PRODUCTIZED.md'), r'A[0-8]\s'):
        title, pre, primary, exposure, practice, increment, gate = cells
        code = title.split()[0]
        result['agent.application'].append((code, title, '', dict(why_now=title, jit_prerequisite=pre,
            primary_chapters=primary, supplement_comparison=primary,
            exposure_relation=exposure, small_practice=practice, outcome_increment=increment,
            exit_gate=gate, raw_body='| ' + ' | '.join(cells) + ' |')))
    specs = [('rag', 'AGENT_SPECIALIZATION_RAG.md', r'[0-7]\. '),
             ('coding', 'AGENT_SPECIALIZATION_CODING.md', r'C(?:[1-9]|10) '),
             ('workflow', 'AGENT_SPECIALIZATION_WORKFLOW.md', r'[0-7]\. '),
             ('browser', 'AGENT_SPECIALIZATION_BROWSER.md', r'[0-7]\. ')]
    for recipe, filename, pattern in specs:
        for i, cells in enumerate(table_rows(read(filename), pattern)):
            if recipe == 'coding':
                title, pre, primary, exposure, practice, increment, gate = cells
                code = title.split()[0]
            else:
                title, pre, primary, exposure, practice, gate = cells
                increment = practice
                code = {'rag': 'G', 'workflow': 'W', 'browser': 'B'}[recipe] + str(i)
            result['agent.application'].append((code, title, recipe, dict(why_now=title + '；' + pre,
                jit_prerequisite=pre, primary_chapters=primary, supplement_comparison=exposure,
                exposure_relation=exposure, small_practice=practice, outcome_increment=increment,
                exit_gate=gate, raw_body='| ' + ' | '.join(cells) + ' |')))
    for recipe, filename, pattern in [('evaluation', 'AGENT_EVALUATION_PATH.md', r'^## (E[0-7])：([^\n]+)'),
                                     ('agentic_rl', 'AGENTIC_RL_PATH.md', r'^## (R[0-9])：([^\n]+)')]:
        for code, title, body in blocks(read(filename), pattern):
            # Last stage stops at the next non-stage heading; retain later detail as source document evidence.
            result['agent.application'].append((code, title, recipe, prose_evidence(title, body)))
    for key, filename, pattern, prefix in [
        ('ai.fullstack', 'AI_FULLSTACK_TEMPLATE_PRODUCTIZED.md', r'^## 阶段 (\d+)：([^\n]+)', 'F'),
        ('cloud.services', 'CLOUD_SERVICES_TEMPLATE_PRODUCTIZED.md', r'^### 阶段 (-?\d+)：([^\n]+)', 'S')]:
        for code, title, body in blocks(read(filename), pattern):
            result[key].append((prefix + ('m1' if code == '-1' else code), title, '', prose_evidence(title, body)))
    return result


# Explicit bindings are audited chapter selections, not an automatic import of catalog tags.
# A title locates a teaching subsection; the catalog URL may be a course/root entry.
def b(scope, role, *chapters):
    return (scope, role, list(chapters))


def HELLO(n):
    return f'hello-common-ch{n}'


BINDINGS = {
 'A0': [b(HELLO(1), 'primary', '1.1/1.2 Agent概念', '1.4 Workflow与Agent'), b(HELLO(2), 'supplement', '历史概览（选读）'), b(HELLO(3), 'supplement', '3.2.1–3.2.4 应用基础', '3.3.2 生成局限'), b('python-zh-jit', 'supplement', '4.1/4.2/4.8 函数循环', '5.5 字典', '7.2/7.2.2 文件JSON', '8.2/8.3 异常')],
 'A1': [b(HELLO(4), 'primary', '4.1 LLM与工具入口', '4.2 ReAct', '4.3 Plan-and-Solve', '4.4 Reflection'), b('lcc-coding-spine', 'comparison', 's01 Agent Loop', 's02 Tool Use'), b(HELLO(12), 'supplement', '12.1 评价对象（Eval-Lite预读）')],
 'A2': [b(HELLO(7), 'primary', '7.1–7.3 Agent与LLM抽象', '7.4–7.5 Tool与registry'), b('lcc-coding-spine', 'supplement', 's03 Permission', 's04 Hooks')],
 'A3': [b(HELLO(8), 'primary', '8.1–8.2 Memory', '8.3 RAG', '8.4 文档问答助手'), b('all-in-rag-spine', 'supplement', 'ch1 最小RAG四步')],
 'A4': [b(HELLO(9), 'primary', '9.1/9.2 上下文原则', '9.3 ContextBuilder', '9.4 NoteTool', '9.5 TerminalTool'), b('lcc-coding-spine', 'comparison', 's08 Context Compact', 's09 Memory')],
 'A5': [b(HELLO(6), 'primary', '6.1 框架位置', '6.3 AgentScope（按目标）', '6.5 LangGraph图基础（按目标）'), b('langgraph-workflows', 'comparison', 'Workflows与Agents区别')],
 'A6': [b(HELLO(10), 'reference', '10.1 协议角色'), b(HELLO(10), 'primary', '10.2 MCP', '10.5 自建server（按目标）'), b('lcc-coding-spine', 'comparison', 's14 MCP mock工具池')],
 'A7': [b(HELLO(12), 'primary', '12.1 评价入口', '12.2 工具调用评价', '12.3 任务成功', '12.4 Judge'), b('langsmith-evaluation-types', 'supplement', 'Unit/Regression/Benchmarking/Pairwise')],
 'A8': [],
 'G0': [b('all-in-rag-spine', 'primary', 'ch1 RAG导论/最小链路'), b('hello-rag-context-bridge', 'comparison', '8.3–8.4 Agent中的RAG')],
 'G1': [b('all-in-rag-spine', 'primary', 'ch2/04 数据加载', 'ch2/05 文本切块', 'ch8/02 数据准备/父子块')],
 'G2': [b('all-in-rag-spine', 'primary', 'ch3/06 文本Embedding', 'ch3/08 向量数据库')],
 'G3': [b('all-in-rag-spine', 'primary', 'ch4/11 检索基础', 'ch6/18 系统评估'), b('ragas-evaluation', 'supplement', 'Context Precision/Recall定义与口径')],
 'G4': [b('all-in-rag-spine', 'primary', 'ch4/11 Hybrid', 'ch4/12 查询构造', 'ch4/14 查询改写', 'ch8/03 BM25+dense+RRF'), b('bge-m3-retrieval-modes', 'comparison', 'Dense/Learned sparse与独立BM25基线')],
 'G5': [b('all-in-rag-spine', 'primary', 'ch4/15 高级检索/Rerank', 'ch5/16 格式化生成', 'ch8/04 回答集成'), b('rag-citation-contract', 'supplement', '来源元数据与claim支持性', 'Cohere结构化citation对象')],
 'G6': [b('all-in-rag-spine', 'primary', 'ch6/19 评估工具（按需）', 'ch8/01 环境与架构', 'ch8/02 数据准备', 'ch8/03 索引检索', 'ch8/04 生成集成')],
 'G7': [b('all-in-rag-spine', 'primary', 'ch7/20 KG-RAG（图需求触发）', 'ch7/21 Agentic RAG（有基线坏例才进入）')],
 'C1': [b('lcc-coding-spine', 'primary', 's01 Agent Loop', 's02 Tool Use'), b(HELLO(4), 'comparison', '4.2 ReAct文本范式')],
 'C2': [b('lcc-coding-spine', 'primary', 's02 文件工具', 's03 Permission', 's04 Hooks')],
 'C3': [b('lcc-coding-spine', 'primary', 's05 TodoWrite', 's10 Todo与Task对照')],
 'C4': [b('lcc-coding-spine', 'primary', 's06 Subagent', 's07 Skill Loading', 's08 Context Compact'), b(HELLO(9), 'comparison', '9.3 ContextBuilder选择与压缩')],
 'C5': [b('lcc-coding-spine', 'primary', 's09 Memory', 's10 Task System')],
 'C6': [b('lcc-coding-spine', 'primary', 's11 Background', 's12 Cron（只有定时目标）', 's15 恢复边界')],
 'C7': [b('lcc-coding-spine', 'primary', 's13 Agent Teams（协作目标）', 's15 团队任务集成')],
 'C8': [b('lcc-coding-spine', 'primary', 's14 MCP mock工具池', 's15 Integrated Harness'), b(HELLO(10), 'comparison', '10.2 真实MCP协议边界')],
 'C9': [b('lcc-coding-spine', 'primary', 's16 Workflow Runtime', 's17 Goal Loop')],
 'C10': [b('pi-sdk-case', 'comparison', 'SDK lifecycle/storage/prompting/events', 'Sessions and Context', 'Extensions lifecycle/events/tools', 'Security/Containerization'), b('openhands-sdk-case', 'reference', 'Getting Started', 'Security/Persistence/Docker Sandbox（目录候选，正文待审）')],
 'W0': [b('langgraph-workflows', 'primary', 'Predetermined workflow与dynamic agent'), b('hello-workflow-bridge', 'comparison', '6.5.1–6.5.3 图基础')],
 'W1': [b('langgraph-workflows', 'primary', 'Prompt chaining', 'Parallelization', 'Routing', 'Evaluator-optimizer', 'Agents（比较）'), b('langgraph-graph-api', 'supplement', 'StateGraph/state/nodes/edges/reducers/loop limit')],
 'W2': [b('langgraph-thinking', 'primary', 'State/node设计', 'Transient/LLM-recoverable/user-fixable/unexpected errors', 'Retry/timeout/compensation')],
 'W3': [b('langgraph-persistence', 'primary', 'Checkpoint与Store边界', 'thread_id与backend', 'Crash/replay/durability')],
 'W4': [b('langgraph-interrupts', 'primary', 'Checkpoint与稳定thread要求', 'Command resume/approve/reject/edit', '节点重跑与幂等副作用')],
 'W5': [b('langgraph-graph-api', 'primary', '节点/路由/状态确定性测试'), b('langsmith-evaluation-types', 'supplement', 'Regression与评价对象')],
 'W6': [b('langgraph-agent-server', 'primary', 'Assistants/Threads/Runs', 'Background/worker/queue/取消/隔离')],
 'W7': [b('langgraph-workflows', 'primary', 'Orchestrator-worker与动态Send（目标需要）'), b('agentscope-current-case', 'comparison', '2.x NEWS/迁移/版本匹配团队入口'), b('agentscope-v1-comparison', 'comparison', 'v1 pipeline与handoff版本对照')],
 'B0': [b('playwright-python-spine', 'primary', 'Intro/Installation', 'Writing tests')],
 'B1': [b('playwright-python-spine', 'primary', 'Locators', 'Input/Actions', 'Actionability/Assertions')],
 'B2': [b('playwright-python-spine', 'primary', 'Navigations', 'Pages/context/tabs', 'Trace Viewer')],
 'B3': [b('playwright-python-spine', 'primary', 'Actionability/auto-wait与web-first断言'), b('playwright-python-spine', 'reference', 'Network/Frames/Dialogs（按需）'), b('browser-use-api-reference', 'comparison', 'max_failures/timeouts与安全重试')],
 'B4': [b('browser-use-quickstart', 'primary', 'Installation/First Agent/local safe example'), b('browser-use-api-reference', 'supplement', 'Agent/Browser/History/Examples'), b('browser-use-observation-guidance', 'supplement', 'AX-first/过滤观察/动作后验证'), b('hello-browser-extra', 'comparison', 'Extra11/1.1–1.2.3 DOM/AX/vision')],
 'B5': [b('playwright-python-spine', 'primary', 'Authentication/storage state', 'Pages/context isolation'), b('browser-use-api-reference', 'comparison', 'Domain allowlist/sensitive_data/session')],
 'B6': [b('playwright-python-spine', 'primary', 'Writing tests/web-first assertions', 'Trace Viewer'), b('browser-use-api-reference', 'comparison', 'History/final_result与独立oracle')],
 'B7': [],
 'E0': [b(HELLO(12), 'primary', '12.1 评价对象/Eval-Lite'), b(HELLO(4), 'comparison', '工具循环轨迹')],
 'E1': [b('langsmith-complex-agent-eval', 'primary', 'Final response', 'Single step'), b('langsmith-evaluation-types', 'supplement', 'Benchmarking/Unit/Regression/Pairwise'), b('openai-eval-best-practices', 'supplement', 'Metric/human/judge与edge cases')],
 'E2': [b('langsmith-complex-agent-eval', 'primary', 'Trajectory evaluator'), b('agentevals-comparison', 'comparison', 'Strict/unordered/subset/superset/tool args'), b('openai-eval-best-practices', 'supplement', '位置/冗长偏差与人工校准')],
 'E3': [b('langsmith-rag-eval', 'primary', 'Create dataset', 'Define evaluators', 'Run evaluation')],
 'E4': [b('lcc-coding-spine', 'comparison', 's03 Permission', 's17 Goal Loop')],
 'E5': [b('langgraph-interrupts', 'comparison', 'Interrupt重放与副作用'), b('playwright-python-spine', 'comparison', 'Assertions/Trace Viewer')],
 'E6': [b('langsmith-evaluation-types', 'primary', 'Regression/benchmarking/pairwise'), b('openai-evals-transition', 'reference', '退役提示与流程概览（历史快照）'), b('openai-agent-evals-concepts', 'supplement', 'Traces→datasets概念')],
 'E7': [b('hf-llm-grpo', 'supplement', '12/4 数据与独立评估')],
 'R0': [b(HELLO(11), 'primary', 'Agent轨迹/reward/RL应用背景')],
 'R1': [b('hf-deep-rl-introduction', 'primary', 'Process/Markov/state-observation/action/rewards/discount'), b('hf-llm-grpo', 'comparison', '12/2 后训练背景')],
 'R2': [b('hf-llm-grpo', 'primary', '12/4 Reward Function Design', '12/5 Define reward'), b('deepseek-r1-paper', 'supplement', '2.2.2 可验证奖励与限制')],
 'R3': [b('hf-llm-grpo', 'primary', '12/3 Group Formation', '12/4 Dataset Format')],
 'R4': [],
 'R5': [b('hf-llm-sft', 'primary', '11/2 Chat Templates', '11/3 SFT', '11/4 LoRA'), b('hf-llm-grpo', 'supplement', '12/2 Post-training')],
 'R6': [b('hf-llm-grpo', 'primary', '12/3 GRPO', '12/4 最小实现'), b('hf-policy-gradient', 'supplement', 'Getting big picture/Objective/Reinforce'), b('hf-ppo', 'comparison', 'Ratio/advantage/clipped objective')],
 'R7': [b('trl-grpo-api', 'primary', 'Tools', 'Environments', 'Logged metrics（执行前核stable）')],
 'R8': [b('agent-lightning-paper', 'primary', '3.1 数据接口', '3.2 MDP', '3.3 Credit assignment'), b('agent-lightning-framework', 'comparison', 'Basics/QuickStart硬件/Calc-X')],
 'R9': [b('hf-llm-grpo', 'primary', '12/5 完整实践与独立评估')],
 'F0': [b('mdn-javascript-jit', 'primary', 'JSON/Fetch网络请求诊断'), b('javascript-info-supplement', 'supplement', 'Fetch/Promise chaining/async-await按缺口')],
 'F1': [b('mdn-http-mental-model', 'primary', 'Client/server', 'HTTP flow', 'Requests/Responses/status'), b('mdn-javascript-jit', 'supplement', 'Fetch GET/POST与response.ok')],
 'F2': [b('react-learn-spine', 'primary', 'Quick Start', 'Describing the UI', 'Thinking in React', 'Adding Interactivity', 'Managing State', 'You Might Not Need an Effect', 'Synchronizing with Effects'), b('vite-build-deploy', 'supplement', 'Guide/create/development server')],
 'F3': [b('fastapi-api-spine', 'primary', 'First Steps', 'Path Parameters', 'Query Parameters', 'Request Body', 'Response Model', 'Handling Errors', 'Dependencies'), b('fastapi-api-spine', 'reference', 'Query/Path validation（待明确正文审读）', 'Status Codes（待明确正文审读）'), b('python-en-jit', 'supplement', '4.1/4.2/4.8/5.1/5.5/8.2–8.4按缺口'), b('javascript-info-supplement', 'comparison', 'Fetch response.ok')],
 'F4': [b('microsoft-genai-beginners', 'primary', '01 GenAI/token/局限', '04 Prompt概念', '06 服务端Text Generation'), b('openai-provider-api', 'supplement', 'Responses Text', 'Structured Outputs/refusal/incomplete')],
 'F5': [b('wonderful-sql-practice', 'primary', 'ch01 表/约束/CRUD', 'ch02 SELECT/WHERE/order/aggregate', 'ch04/4.2 JOIN（按需）'), b('postgresql-sql-semantics', 'supplement', 'JOIN/ON/explicit columns', 'Table Expressions'), b('fastapi-sqlmodel-bridge', 'comparison', 'Engine/models', 'Session dependency', 'CRUD/input-table-public')],
 'F6': [b('openai-provider-api', 'primary', 'Streaming created/delta/completed/error'), b('fastapi-api-spine', 'supplement', 'Server-Sent Events（版本边界）'), b('mdn-http-mental-model', 'comparison', 'HTTP APIs/SSE单向事件')],
 'F7': [b('fastapi-api-spine', 'primary', 'Testing/TestClient/pytest'), b('openai-provider-api', 'supplement', 'Rate Limits', 'Error Codes', 'Production Best Practices')],
 'F8': [b('fastapi-api-spine', 'primary', 'Security First Steps', 'Get Current User', 'OAuth2/JWT概念（非生产方案）'), b('oauth-security-rfc9700', 'comparison', '2.4 Password grant禁用与原因')],
 'F9': [b('fastapi-api-spine', 'primary', 'Deployment Concepts', 'Docker', 'CORS', 'Settings'), b('vite-build-deploy', 'supplement', 'Build', 'Static Deploy')],
 'F10': [b('microsoft-genai-beginners', 'supplement', '08 Search/15 RAG仅概念'), b('openai-provider-api', 'supplement', 'Structured Outputs/Streaming/provider比较按目标')],
 'Sm1': [b('fastapi-api-spine', 'primary', 'First Steps', 'Path/Query Params', 'Request Body', 'Response Model', 'Handling Errors', 'Testing', 'Settings（按需）'), b('fastapi-sqlmodel-bridge', 'supplement', 'Engine/model', 'Session dependency', 'CRUD'), b('python-en-jit', 'supplement', '函数/list/dict/异常按缺口')],
 'S0': [],
 'S1': [b('docker-run-app', 'primary', 'Before you start', 'Run a container', 'Run an application stack', 'Build an image', 'Share the image', 'Clean up', 'What you learned/Next'), b('docker-runtime-concepts', 'supplement', 'What is a container', 'Writing a Dockerfile', 'Publishing ports')],
 'S2': [b('docker-compose-spine', 'primary', 'Step1 Project/Dockerfile/env', 'Step2 Define services', 'Step3 DB healthcheck/depends_on', 'Step4 Watch（可选）', 'Step5 Named volume', 'Step6 Multiple files/include（可选）', 'Step7 config/logs/exec')],
 'S3': [], 'S4': [],
 'S5': [b('kubernetes-basics', 'primary', 'Module1 Create cluster', 'Module2 Deploy app', 'Module3 Explore Pod/Node', 'Module4 Expose Service', 'Module5 Scale', 'Module6 Update/rollback')],
 'S6': [b('kubernetes-basics', 'reference', '基础对象复习；probe/config/secret详细正文另按需求核查')],
 'S7': [],
 'S8': [b('otel-demo-case', 'primary', 'Architecture', 'Telemetry Features', 'Docker Deployment', 'Feature flag/recommendation-cache', 'Collector troubleshooting', 'Kubernetes Deployment（按需）')],
 'S9': [b('github-actions-ci-deploy', 'primary', 'Workflow/events/jobs/runners/steps', 'Example workflow', 'Python build/test（按项目语言替换）', 'Artifacts与cache')],
 'S10': [b('github-actions-ci-deploy', 'primary', 'Control deployments/environment/concurrency', 'Secure use/action pinning'), b('github-actions-ci-deploy', 'reference', 'OIDC provider（目标选定后）')],
 'S11': [b('terraform-docker-spine', 'primary', 'Infrastructure as Code', 'Install', 'Build', 'Change', 'Destroy', 'Variables', 'Outputs')],
 'S12': [b('terraform-aws-comparison', 'comparison', 'Create', 'Manage', 'Destroy与费用清理')],
 'S13': [],
}


def author_order(scope, title):
    """Keep selected sections in source order, independent of stage scheduling."""
    if scope == 'lcc-coding-spine':
        return int(re.search(r's(\d+)', title).group(1)) * 100
    if scope == 'all-in-rag-spine':
        match = re.search(r'ch(\d+)(?:/(\d+))?', title)
        return int(match.group(1)) * 1000 + int(match.group(2) or 0) if match else 0
    if scope.startswith('hello-common-ch') or scope.startswith('hello-'):
        match = re.search(r'(\d+)\.(\d+)', title)
        return int(match.group(1)) * 100 + int(match.group(2)) if match else 0
    if scope == 'react-learn-spine':
        return ['Quick Start', 'Describing the UI', 'Thinking in React', 'Adding Interactivity',
                'Managing State', 'You Might Not Need an Effect', 'Synchronizing with Effects'].index(title)
    return 0


SECTION_QUALIFICATION_LIMITS = {
    ('hello-common-ch10', '10.1 协议角色'): '只有chapter structure/summary记录，明确正文为10.2与10.5.1。',
    ('playwright-python-spine', 'Network/Frames/Dialogs（按需）'): '实际审读只明确docs index；不认证可选专题正文。',
    ('github-actions-ci-deploy', 'OIDC provider（目标选定后）'): 'recommended_scope候选，实际审读没有provider policy正文。',
    ('fastapi-api-spine', 'Query/Path validation（待明确正文审读）'): 'recommended_scope列出；actual_scope没有独立该页正文记录。',
    ('fastapi-api-spine', 'Status Codes（待明确正文审读）'): 'recommended_scope列出；actual_scope没有独立该页正文记录。',
}


def selection(key, code, recipe):
    default = not recipe
    capabilities, when, skip = [], [], []
    if recipe:
        default = False
        capabilities = [recipe]
        when = {'rag': ['RAG', '知识检索', '知识库', '文档问答'], 'coding': ['Coding', '代码', '编程', '软件任务'],
                'workflow': ['Workflow', '工作流', '可恢复', '恢复规划'],
                'browser': ['Browser', '网页', '浏览器', '信息获取'],
                'evaluation': ['系统评估', 'Evaluation', '评价体系'],
                'agentic_rl': ['RL', '奖励', '轨迹', '强化学习']}[recipe]
        if code in {'R5', 'R6', 'R7', 'R8', 'R9', 'E7'}:
            capabilities = ['training']
            when = ['参数训练', '训练模型', 'GRPO', 'PPO', 'SFT', '训练研究']
        if code in {'G7', 'C7', 'W6', 'W7', 'B5'}:
            when = {'G7': ['Agentic RAG', 'GraphRAG', '多跳'], 'C7': ['多Agent', '团队协作'],
                    'W6': ['后台', '多会话', '服务化'], 'W7': ['多Agent', 'handoff', '协作'],
                    'B5': ['浏览器登录', '网页认证', 'session']}[code]
            capabilities = [code.lower()]
    elif key == 'agent.application':
        capabilities = ['common_core']
        if code in {'A5', 'A6', 'A8'}:
            default = False
            capabilities = {'A5': ['workflow'], 'A6': ['mcp', 'protocol'], 'A8': ['project_study']}[code]
            when = {'A5': ['框架', '工作流', '恢复', 'Workflow'], 'A6': ['MCP', '协议', '远程工具'],
                    'A8': ['源码', '真实项目', '项目学习']}[code]
    elif key == 'ai.fullstack':
        capabilities = ['web', 'api', 'ai_product']
        if code in {'F6', 'F8', 'F9', 'F10'}:
            default = False
            capabilities = {'F6': ['streaming'], 'F8': ['auth'], 'F9': ['deployment'],
                            'F10': ['rag', 'multi_provider', 'evaluation']}[code]
            when = {'F6': ['流式', 'Streaming', 'SSE'], 'F8': ['多人', '团队', '认证', '授权', '私有数据', '公开访问'],
                    'F9': ['部署', '上线', '发布'], 'F10': ['知识检索', 'RAG', '多模型', '多provider', '评价']}[code]
    else:
        capabilities = ['service', 'container']
        if code == 'Sm1':
            skip = ['已有服务', '已有API', '已经有一个', 'Node.js', 'Go服务', 'Java服务']
        if code not in {'Sm1', 'S0', 'S1', 'S2'}:
            default = False
            capabilities = {'S3': ['deployment'], 'S4': ['multi_service'], 'S5': ['kubernetes'],
                            'S6': ['kubernetes'], 'S7': ['observability'], 'S8': ['observability'],
                            'S9': ['ci'], 'S10': ['cicd', 'deployment'], 'S11': ['iac'],
                            'S12': ['cloud_iac', 'platform'], 'S13': ['restore']}[code]
            when = {'S3': ['云', '部署', '上线'], 'S4': ['多服务', 'worker', '队列'],
                    'S5': ['Kubernetes', 'K8s', '集群'], 'S6': ['Kubernetes', 'K8s', '集群'],
                    'S7': ['监控', '可观测', 'OTel', 'Observability'], 'S8': ['监控', '可观测', 'OTel'],
                    'S9': ['CI', '自动发布', '流水线', 'Actions'], 'S10': ['自动发布', 'CD', '流水线'],
                    'S11': ['Terraform', 'IaC', '基础设施代码'], 'S12': ['云IaC', '平台工程', 'Terraform云'],
                    'S13': ['备份', '恢复', 'Restore', '持久数据']}[code]
    result = dict(default=default, capabilities=capabilities, when_any=when, skip_when_any=skip)
    if key == 'cloud.services' and code == 'Sm1':
        result['fallback_only'] = True
    return result


def project_cards(text):
    """Read nine-field authored cards, including Markdown bullet and table forms."""
    cards = []
    chunks = re.split(r'^## ', text, flags=re.M)
    required = ['repo_url', 'why_now', 'prerequisites', 'learning_focus', 'desired_depth',
                'important_questions', 'avoid_scope', 'expected_outputs', 'migration_candidates']
    for chunk in chunks:
        if 'status: reviewed_candidate' not in chunk:
            continue
        title = chunk.splitlines()[0]
        values = {}
        current = None
        for line in chunk.splitlines():
            table = re.match(r'^\|\s*([a-z_]+)\s*\|\s*(.*?)\s*\|$', line)
            bullet = re.match(r'^-\s*(?:\*\*|`)?([a-z_]+)(?:\*\*|`)?[：:]\s*(.*)', line)
            match = table or bullet
            if match:
                current, value = match.groups()
                values[current] = clean(value)
            elif current and re.match(r'^\s+\d+\.', line):
                values[current] += '\n' + clean(line)
            elif line.strip() and not line.startswith(' '):
                current = None
        if any(not values.get(k) for k in required):
            raise ValueError(f'Incomplete authored project card: {title}')
        values.update(title=title, binding='optional', replacement_allowed=True, status='reviewed_candidate')
        cards.append(values)
    if len(cards) != 12:
        raise ValueError('Expected 12 reviewed candidate identities')
    return cards


def build_all(research=RESEARCH):
    research = Path(research)
    cache = {}

    def read(filename):
        if filename not in cache:
            cache[filename] = (research / filename).read_text(encoding='utf-8-sig')
        return cache[filename]

    catalog = json.loads(read('RESOURCE_CATALOG_NORMALIZED_DRAFT.json'))
    by_scope = {r['scope_key']: r for r in catalog['resources']}
    authored = authored_stages(read)
    cards = project_cards(read('PROJECT_STUDY_CARDS_NORMALIZED.md'))
    # Full surrounding explanations remain as publication metadata, not runtime instructions.
    for filename in ['EXPOSURE_MATRIX_ALL.md', 'PREREQUISITE_MATRIX_ALL.md', 'RESEARCH_LOG.md',
                     'PLANNING_SEMANTICS_STANDARD.md', 'SPECIALIZATION_RECIPES.md']:
        read(filename)
    packs = []
    audit = []
    holds = {r['scope_key']: r['public_seed_status'] for r in catalog['resources']
             if r['public_seed_status'].startswith('hold_')}
    for key, units in authored.items():
        ns = key.replace('.', '_') + '_v' + str(VERSIONS[key]) + '_v62'
        pack = dict(pack_key=key, version=VERSIONS[key], status='published', title=key + '：章级可裁剪教学路线',
                    supported_scope='按用户目标、起点与实际前置选择章级教学；用户项目优先，候选与专项可组合替换。',
                    resource_support='reviewed_index', provenance='v6.2 controlled content mapping 2026-10-04; '
                    'research snapshot 2026-10-03; no new web review or execution. Review scope is explicit; '
                    'runtime/model/cloud validation NOT RUN. Source IDs isolated by pack/version.',
                    semantic_policy=dict(version=1, starter_title=STARTERS[key], direction=key),
                    stage_blueprints=[], knowledge_blueprints=[], practice_blueprints=[], resources=[],
                    resource_refs=[], required_node_keys=[], curriculum_review={'status': 'chapter_mapping_reviewed',
                    'runtime_validation': 'not_run', 'reviewed_at': '2026-10-04'})
        source_map = {}
        section_maps = {}

        def source(scope, source_map=source_map, ns=ns, section_maps=section_maps, pack=pack):
            if scope in source_map:
                return source_map[scope]
            r = by_scope[scope]
            if scope in holds:
                raise ValueError(f'Cannot publish held resource: {scope}')
            s = dict(source_id='src_' + ns + '_' + scope, canonical_url=r['url'], title=r['title'],
                     creator='原始官方/作者来源，见catalog审读记录', media_type=r['media_type'], language=r['language'],
                     source_version=1, documentation_version='研究快照2026-10-03；学习时核对当前兼容版本',
                     verification_status='legacy_index' if r['review_depth'] in {'metadata_only', 'toc_checked'} else 'reviewed',
                     checked_at=DATE, sections=[], review_depth=r['review_depth'], content_access=r['content_access'],
                     public_seed_status='published_controlled_subset', catalog_public_seed_status=r['public_seed_status'],
                     runtime_validation=r['runtime_validation'], metadata={k: r[k] for k in r if k != 'source_review_record'},
                     review_evidence=r['source_review_record'], review_note=r['review_note'])
            source_map[scope] = s
            section_maps[scope] = {}
            pack['resources'].append(s)
            pack['resource_refs'].append(s['source_id'])
            return s

        def bind(stage, scope, role, titles, source=source, section_maps=section_maps, ns=ns):
            s = source(scope)
            if role == 'primary' and (s['review_depth'] not in {'selected_sections_read', 'deep_reviewed'} or
                                     s['content_access'] not in {'free_public', 'free_account'}):
                raise ValueError(f'Insufficient Primary evidence: {scope}')
            ids = []
            for title in titles:
                if title not in section_maps[scope]:
                    depth = s['review_depth']
                    if scope == 'openhands-sdk-case' and 'Security/Persistence' in title:
                        depth = 'toc_checked'
                    # No 5.1 body claim: this subsection was TOC-only in the actual research log.
                    if scope == 'python-zh-jit' and '5.1' in title:
                        depth = 'toc_checked'
                    limitation = SECTION_QUALIFICATION_LIMITS.get((scope, title))
                    if limitation:
                        depth = 'toc_checked'
                    if role == 'primary' and depth in {'toc_checked', 'metadata_only'}:
                        raise ValueError(f'Insufficient Primary subsection evidence: {scope}: {title}')
                    section_id = 'sec_' + ns + '_' + scope + '_' + hashlib.sha256(title.encode()).hexdigest()[:10]
                    note = ('教学选择：' + title + '。URL可能为作者目录/入口，不假设直达细节。实际审读：' + s['review_note'])
                    if limitation:
                        note += '；保守资格限制：' + limitation
                    section = dict(section_id=section_id, title=title, url=s['canonical_url'], anchor='', order_index=0,
                                   verification_status='legacy_index' if depth in {'metadata_only', 'toc_checked'} else 'reviewed',
                                   checked_at=DATE, review_note=note, review_depth=depth,
                                   applicable_node_keys=[], selection_scope=title, runtime_validation='not_run')
                    if scope == 'rag-citation-contract' and title.startswith('Cohere'):
                        section['url'] = 'https://docs.cohere.com/docs/rag-citations'
                        section['review_note'] += '；原source_urls明确记录Cohere正文与citation对象。'
                    section_maps[scope][title] = section
                    s['sections'].append(section)
                section = section_maps[scope][title]
                if stage['node_keys'][0] not in section['applicable_node_keys']:
                    section['applicable_node_keys'].append(stage['node_keys'][0])
                ids.append(section['section_id'])
            stage['resources'].append(dict(role=role, source_ref=s['source_id'], section_refs=ids,
                                           source_version=1, order_index=len(stage['resources']), node_keys=stage['node_keys']))

        previous = {}
        primary_continuations = []
        for code, title, recipe, evidence in units:
            stage_key = 'stage.v62.' + key + '.' + code.lower()
            node_key = 'node.v62.' + key + '.' + code.lower()
            sel = selection(key, code, recipe)
            relation_text = clean(evidence['exposure_relation'])
            relation = next((v for v in ('version_context', 'compare', 'deepen', 'review') if v.upper() in relation_text), 'unknown')
            prerequisites = []
            # Recipe-specific chains retain actual minima, never the entire preceding recipe.
            chain = recipe or key
            if chain in previous:
                prerequisites.append(previous[chain])
            if recipe and chain not in previous and code not in {'E0', 'R0'}:
                prerequisites.append('node.v62.agent.application.a1')
            if recipe == 'agentic_rl' and code == 'R0':
                prerequisites.extend(['node.v62.agent.application.a1', 'node.v62.agent.application.e1'])
            # Cloud optional topics are separate, with only the actual blocker as an edge.
            if key == 'cloud.services':
                cloud_deps = {'Sm1': [], 'S0': [], 'S1': ['S0'], 'S2': ['S1'], 'S3': ['S2'],
                              'S4': ['S3'], 'S5': ['S1'], 'S6': ['S5'], 'S7': ['S0'], 'S8': ['S7'],
                              'S9': ['S0', 'S1'], 'S10': ['S3', 'S9'], 'S11': ['S1'],
                              'S12': ['S3', 'S11'], 'S13': ['S0']}
                prerequisites = ['node.v62.cloud.services.' + c.lower() for c in cloud_deps[code]]
            if key == 'ai.fullstack':
                ai_deps = {'F0': [], 'F1': [], 'F2': ['F1'], 'F3': ['F2'], 'F4': ['F3'], 'F5': ['F3'],
                           'F6': ['F4', 'F5'], 'F7': ['F4'], 'F8': ['F5', 'F7'], 'F9': ['F5', 'F7'], 'F10': ['F4', 'F7']}
                prerequisites = ['node.v62.ai.fullstack.' + c.lower() for c in ai_deps[code]]
            if key == 'agent.application' and not recipe:
                core_deps = {'A0': [], 'A1': ['A0'], 'A2': ['A1'], 'A3': ['A2'], 'A4': ['A3'],
                             'A5': ['A2'], 'A6': ['A2'], 'A7': ['A1'], 'A8': ['A3', 'A4', 'A7']}
                prerequisites = ['node.v62.agent.application.' + c.lower() for c in core_deps[code]]
            if key == 'agent.application' and recipe:
                optional_safe = {'C8': ['C2'], 'C9': ['C5', 'C6'], 'C10': ['C9'],
                                 'W6': ['W3', 'W5'], 'W7': ['W5'], 'B6': ['B4'],
                                 'E0': ['A1'], 'E1': ['E0'], 'E2': ['E1'],
                                 'E3': ['E1'], 'E4': ['E1'], 'E5': ['E1'],
                                 'E6': ['E1'], 'E7': ['E1', 'R5']}
                if code in optional_safe:
                    prerequisites = ['node.v62.agent.application.' + c.lower() for c in optional_safe[code]]
            previous[chain] = node_key
            guide = dict(why_now=clean(evidence['why_now'])[:1200],
                         previous_relation=relation_text[:1200], exposure_relation=relation,
                         knowledge_keys=[node_key], learning_focus=parts(evidence['primary_chapters']),
                         comparison_focus=parts(evidence['supplement_comparison']) if relation == 'compare' else [],
                         reading_prerequisites=parts(evidence['jit_prerequisite']),
                         practice_prerequisites=[CARRIER, '先确认本次选定前置的证据；需要付费/账号/外部副作用时按实际授权执行。'],
                         practice_delta=dict(baseline=CARRIER, increment=parts(evidence['outcome_increment']),
                             preserved=['保留问题、数据、输入输出、接口、测试、决策与历史证据；可重构或替换实现。'],
                             validation=parts(evidence['exit_gate']), reuse=['按适用性迁回用户载体；不自然适配时保留独立练习；不继承旧accepted状态。']))
            stage = dict(stable_key=stage_key, stage_code=code, recipe=recipe, title=clean(title),
                         section_kind='foundation' if code in {'A0', 'F0', 'F1', 'Sm1', 'S0'} else 'core',
                         objective=clean(evidence['why_now'])[:1200], inclusion='required' if sel['default'] else 'optional',
                         node_keys=[node_key], resources=[], extensions=[], learning_guidance=guide,
                         selection=sel, teaching_evidence=evidence)
            # Full small-practice and author row are visible in the existing extension surface.
            stage['extensions'].append(dict(topic='本阶段章级练习与教学边界', concepts=parts(evidence['primary_chapters']),
                guidance='前置：' + evidence['jit_prerequisite'] + '\n重复关系：' + evidence['exposure_relation'] +
                '\n补充/比较：' + evidence['supplement_comparison'] + '\n小实践：' + evidence['small_practice'] +
                '\n载体与增量：' + evidence['outcome_increment'] + '\n出口：' + evidence['exit_gate'] + '\n' + CARRIER,
                links=[], search_hints=[], thinking_prompts=['解释一条正常与一条失败路径，说明证据如何支持退出条件。'],
                required=False, order_index=0))
            stage['extensions'].append(dict(topic='贯穿评价与证据', concepts=['独立结果判据', '失败分类', '数据与成本边界'],
                guidance=EVAL, links=[], search_hints=[], thinking_prompts=['本阶段哪个结果必须用环境状态或测试证明？'],
                required=False, order_index=1))
            if code in {'S3', 'S6', 'S7', 'S13'}:
                stage['extensions'].append(dict(topic='按当前目标核对资料范围', concepts=['当前官方正文', '版本与访问资格'],
                    guidance='本阶段完整教学规格已保留；细项未形成独立catalog受审切片，执行前按目标核查当前官方资料。'
                    'needs_research_or_review；不把未审页自动升级为公共Primary。', links=[],
                    search_hints=[{'S3': '目标云商 官方容器部署 预算 TLS 备份恢复',
                                   'S6': 'Kubernetes 官方 probes ConfigMap Secret requests limits PV',
                                   'S7': 'OpenTelemetry 官方 当前项目语言 instrumentation Collector OTLP',
                                   'S13': '目标数据库 官方 backup restore pg_dump pg_restore 当前版本'}[code]],
                    thinking_prompts=['当前资料究竟教授了哪个边界，哪些内容仍未审或未运行？'], required=False,
                    order_index=2))
            for scope, role, titles in BINDINGS.get(code, []):
                bind(stage, scope, role, titles)
            pack['stage_blueprints'].append(stage)
            pack['knowledge_blueprints'].append(dict(stable_key=node_key, title=stage['title'], node_type='concept',
                prerequisite_keys=prerequisites, objectives=parts(evidence['primary_chapters']),
                scope=evidence['primary_chapters'], acceptance=parts(evidence['exit_gate'])))
            if sel['default']:
                pack['required_node_keys'].append(node_key)
            pack['practice_blueprints'].append(dict(stable_key='practice.v62.' + key + '.' + code.lower(),
                title=stage['title'] + '：小实践与证据', goal=clean(evidence['small_practice']), section_key=stage_key,
                node_keys=[node_key], acceptance=parts(evidence['exit_gate']),
                design_status='not_run', carrier_policy='user_project_first_or_micro_exercise'))
        # Project candidates use root identity only; no catalog depth borrowed from tutorial documentation.
        targets = {'Pi': 'C10', 'RAGFlow': 'G6', 'WeKnora': 'G6', 'OpenHands': 'C10', 'LangGraph': 'W5',
                   'browser-use': 'B7', 'AgentScope': 'W7', 'OpenTelemetry Demo': 'S8',
                   'Docker Getting Started Todo App': 'S2', 'FastAPI Full Stack': 'F9',
                   'OpenAI Responses Starter': 'F6', 'Open WebUI': 'F10'}
        for card in cards:
            target = next((code for name, code in targets.items() if name in card['title']), None)
            stage = next((s for s in pack['stage_blueprints'] if s['stage_code'] == target), None)
            if stage is None:
                continue
            root_url = card['repo_url']
            token = root_url.split('/')[-1].lower()
            candidate_source = dict(source_id='src_' + ns + '_case_' + token, canonical_url=root_url,
                title=card['title'], creator='已核对原包项目身份；未新增源码/网页审核', media_type='repo', language='en',
                source_version=1, documentation_version='', verification_status='legacy_index', checked_at=DATE,
                sections=[], review_depth='metadata_only', content_access='free_public',
                public_seed_status='published_optional_candidate_identity', runtime_validation='not_run',
                metadata=dict(binding='optional', replacement_allowed=True, source_document='PROJECT_STUDY_CARDS_NORMALIZED.md',
                              identity_only=True, review_note='原包候选身份/适用范围，不认证全仓源码、部署或运行。'))
            pack['resources'].append(candidate_source)
            pack['resource_refs'].append(candidate_source['source_id'])
            stage['resources'].append(dict(role='case_study', source_ref=candidate_source['source_id'], section_refs=[],
                                           source_version=1, order_index=len(stage['resources']), node_keys=stage['node_keys']))
            guidance = '\n'.join(label + '：' + card[field] for label, field in [
                ('为什么现在', 'why_now'), ('重点', 'learning_focus'), ('必要前置', 'prerequisites'),
                ('学习深度', 'desired_depth'), ('暂不涉及', 'avoid_scope'), ('思考问题', 'important_questions'),
                ('预期产物', 'expected_outputs'), ('迁移候选', 'migration_candidates')])
            guidance += '\n可选且可替换；用户项目优先。小项目先地图，大项目3–8个动态切片，一次一个；'
            guidance += '事实/解释/推断分开，最多迁移1–2项；使用当前源码，不固定commit/branch/path/function。'
            stage['extensions'].append(dict(topic='项目学习：' + card['title'], concepts=parts(card['learning_focus']),
                guidance=guidance, links=[root_url], search_hints=[], thinking_prompts=parts(card['important_questions']),
                required=False, order_index=len(stage['extensions']), project_study_card=card))
        # Stable author ordering; equal-number alternative scopes are deterministic by title.
        for scope, s in source_map.items():
            s['sections'].sort(key=lambda section: author_order(scope, section['title']))
            for order, section in enumerate(s['sections']):
                section['order_index'] = order
        for stage in pack['stage_blueprints']:
            continuations = []
            for assignment in stage['resources']:
                s = next(s for s in pack['resources'] if s['source_id'] == assignment['source_ref'])
                order = {sec['section_id']: sec['order_index'] for sec in s['sections']}
                assignment['section_refs'].sort(key=order.__getitem__)
                refs = assignment['section_refs']
                if assignment['role'] == 'primary' and refs:
                    end = 1
                    while end < len(refs) and order[refs[end]] == order[refs[end-1]] + 1:
                        end += 1
                    if end < len(refs):
                        primary_continuations.append(dict(stage_key=stage['stable_key'], stage_code=stage['stage_code'],
                            source_ref=s['source_id'], catalog_scope=s['metadata']['scope_key'],
                            original_teaching_scope=stage['teaching_evidence']['primary_chapters'],
                            original_section_refs=list(refs),
                            original_section_titles=[next(sec['title'] for sec in s['sections'] if sec['section_id'] == ref) for ref in refs],
                            primary_section_refs=refs[:end], supplement_section_refs=refs[end:]))
                        # The existing consumer permits one contiguous mainline.
                        # Preserve authored later selections as explicit supplements,
                        # never insert unselected/unreviewed material to fill gaps.
                        assignment['section_refs'] = refs[:end]
                        continuations.append({**assignment, 'role': 'supplement', 'section_refs': refs[end:],
                                              'original_teaching_role': 'primary',
                                              'mapping_note': '作者精选的非连续后续章节；同一Spine，原始章级编排完整保留。'})
            stage['resources'].extend(continuations)
            for i, assignment in enumerate(stage['resources']):
                assignment['order_index'] = i
        pack['publication_evidence'] = dict(input_sha256={name: hashlib.sha256((research / name).read_bytes()).hexdigest()
            for name, text in sorted(cache.items())}, selection='Only explicit authored teaching/candidate bindings',
            holds=holds, scope_notes=['No external research; chapter/root entry URLs do not guarantee direct subsection navigation.',
                                     'review_depth is reading scope, not execution or learner mastery.'],
            surrounding_teaching_documents={name: text for name, text in cache.items()
                if name.endswith('.md') and name != 'RESEARCH_LOG.md'})
        validate_seed(pack)
        packs.append(pack)
        audit.append(dict(pack_key=key, version=pack['version'], stages=len(pack['stage_blueprints']),
                          knowledge_nodes=len(pack['knowledge_blueprints']), sources=len(pack['resources']),
                          sections=sum(len(s['sections']) for s in pack['resources']),
                          source_depth_counts=dict(Counter(s['review_depth'] for s in pack['resources'])),
                          primary_continuations=primary_continuations,
                          resources=[dict(source_id=s['source_id'], catalog_scope=s.get('metadata', {}).get('scope_key'),
                              url=s['canonical_url'], review_depth=s['review_depth'], content_access=s['content_access'],
                              verification_status=s['verification_status'], runtime_validation=s['runtime_validation'],
                              sections=[{k: sec[k] for k in ('section_id', 'title', 'order_index', 'review_depth', 'verification_status')}
                                        for sec in s['sections']]) for s in pack['resources']]))
    report = dict(catalog_records=len(catalog['resources']), catalog_depth_counts=dict(Counter(r['review_depth'] for r in catalog['resources'])),
                  holds=holds, publication_records=audit, research_date='2026-10-03', mapping_date='2026-10-04',
                  runtime_validation='NOT RUN', validation='PASS',
                  section_qualification_limits=[dict(catalog_scope=scope, section_title=title, reason=reason,
                                                     review_depth='toc_checked', verification_status='legacy_index')
                                                for (scope, title), reason in SECTION_QUALIFICATION_LIMITS.items()],
                  limits=['No new web review, paid calls, DB writes or project execution.',
                          'Python zh 5.1 is TOC-only and not published as reviewed body.',
                          'OpenHands Security/Persistence/Docker Sandbox stays TOC-only.',
                          'Case roots are legacy_index identity, independent of tutorial catalog qualification.'])
    return packs, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    packs, report = build_all()
    if args.write:
        for pack in packs:
            (CONTENT / FILES[pack['pack_key']]).write_text(json.dumps(pack, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        (RESEARCH / 'CONTENT_MAPPING_REPORT.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps([{k: r[k] for k in ('pack_key', 'version', 'stages', 'knowledge_nodes', 'sources', 'sections')}
                      for r in report['publication_records']], ensure_ascii=False))


if __name__ == '__main__':
    main()
