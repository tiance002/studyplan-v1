# Planning V2 Item 1 — Hard Constraint Semantic Fix

日期：2026-10-08（Asia/Shanghai）。本轮只进行离线 Prompt 修复、测试和独立开发审查，产品模型调用授权及实际调用均为 **0**。

## 基线和交付范围

- Start HEAD：`e025f2f05b5b8216905f312a5ff80a6888b5e2d1`；Branch：`feat/n1-resource-discovery`，与预期一致。
- 开始 tracked tree 干净；既有 `.workbuddy/`、`design-preview/` 未跟踪目录未访问、修改或提交。不 reset、不重新开旧生成链。
- 权威：[Architecture Contract](PLANNING_V2_ARCHITECTURE_CONTRACT.md)；失败证据：[Item 1 Real Semantic Smoke](ITEM1_REAL_SEMANTIC_SMOKE.md)。两份原文与旧真实响应保持。
- 本地提交消息：`fix(planning): preserve explicit goal constraints`；Final HEAD/commit SHA 在提交后答复与 ignored final evidence 中记录，避免自引用。
- 主协调请求 Sol6.1/high；有界 Prompt/测试实施与独立审查请求 Sol6.1/medium。实际解析均 NOT OBSERVABLE；未使用 HARD 升级、Luna xhigh、Sol max 或 Astra，未改全局配置。

## 根因及最小修正

真实 Case 2 的 `goal.constraints=[]`，target 明确要求“只读”“不允许自动修改代码”。模型将文字保留在摘要/required_requirements，却输出 `hard_constraints=[]`。这不是 JSON 或来源校验错误，而是目标要求与实现边界的分类遗漏：上位合同要求硬约束作为独立字段供适配、校验和冲突展示消费，另一字段保留文字不能替代。

旧 Prompt 的“hard_constraints仅记录真实用户限制”已经给出一般原则，但紧接着只具体要求结构化 `goal.constraints` 原文复制，未明确 target 等其他输入的显式限制具有同等效力，也未说明已写入 requirement 不能替代 constraint。shape 中约束的示例来源也是 structured index。这些是可观察的指导缺口；不能据此声称已证明模型内部为何遗漏。本次保留 shape，只在专用 system Prompt 中补足分类指导。

唯一生产改动为 `goal_requirement_contract.py::GOAL_REQUIREMENT_SYSTEM` 新增八个字符串片段：

1. 从所有获准非空输入提取显式禁止、技术/实现、使用范围、资源/费用强制限制；即使 `goal.constraints` 为空，target 等输入中的明确限制也必须进入 hard_constraints 并引用真实来源。
2. 用只读不能修改代码、仅使用本地文件、教程必须免费说明限制类别；这些是模型理解示例，没有程序关键词分类器。
3. requirements 表达目标要做到什么，constraints 表达实现边界；同一事实可同时表达两种作用，不能因前者已有文字而漏后者，也不能把所有目标都改为限制。
4. target 与结构化项同义时可合并条目，但 text 取结构化原文、合并真实 source_refs；原有每项逐字/index 保护保留。不同结构化原文不能因所谓同义而丢失其中一项。
5. 没有明确限制时输出空 constraints；真实冲突保留两侧事实并按需澄清，不能删除用户限制。
6. 能力声明和用途本身不是限制；会 Python 保存为 learner_claim，interview 用途不自动扩课。原有“target 明确要求面试准备可作为需求”规则保持。

没有新抽象、NLP/黑名单、额外模型步骤或产品 Reviewer；没有改 Schema、SHAPE、Validator、Analyzer、source_refs 范围、ID/hash 算法、预算、错误处理、调用次数或全局 prompt_version。去掉 SYSTEM 赋值后的模块 AST 与 start HEAD 完全相等。

## RED、七类场景与验证边界

新增 `backend/tests/unit/test_goal_requirement_hard_constraints.py`，先完成测试、运行原 Prompt 的 RED，再修改 Prompt。

| 场景 | 离线验证内容 | 不能证明的语义质量 |
|---|---|---|
| 只读 Code Review target | 正确分类 fixture 可表达自然语言约束并引用 goal.target；实际 Provider adapter 经 MockTransport 捕获的新 system 指导 | 真实模型一定会把只读放入 hard_constraints |
| 免费教程/本地文件 | target 来源支持费用/使用范围约束 | 真实模型没有遗漏或扩展限制 |
| 已会 Python | 正确 fixture 保留 claim、用途，不需要新增约束；已有 Item1 测试保护不生成 Python 学习任务 | 真实模型每次正确分类能力声明 |
| structured constraints | 原文、索引引用仍必须存在；遗漏/改写/缺索引均被拒绝 | 自然语言约束的完整抽取 |
| target 与 structured 同义 | 以 structured 原文和 target/index 联合 refs 合并，稳定 identity/hash | 真实模型正确判断所有语义等价关系 |
| 没有明确限制 | 空 hard_constraints 合法，不由程序自动补限制 | 真实模型不编造限制 |
| 约束与目标冲突 | 两侧事实可完整表示，needs_clarification 与问题一致 | 真实模型识别冲突、提出必要且可回答的问题 |

共12项：七个正确分类 fixtures、一个生产 adapter/模拟 HTTP system 接线测试、三个 structured 拒绝反例、一个自然语言漏约束仍结构合法的反例。最后一项刻意保留 SEMANTIC_EVAL_REQUIRED：程序仍不能靠合法 source_ref 证明约束抽取完整。没有把正确 fixture 或 Mock 返回等同于真实语义修复 PASS。

| 检查 | 状态 | 实际证据 |
|---|---|---|
| 修改前 RED | FAIL | `red.xml/log`：1 FAIL、11 PASS；失败是实际请求 system 缺少“所有获准非空输入”指导，非真实模型抽取失败的新测量 |
| Prompt 修改后新测试 | PASS | `green.xml/log`：12 PASS |
| Item1 targeted | PASS | 统一回归中的104项：analysis52/input9/provider31/本次12；不重复累加单独 green12 |
| 受影响既有回归 | PASS | 同次94项：GoalSpec intent5、legacy/fail-closed10、residual4、b3_provider8、b3f2_planning9、known_json_repair58 |
| 统一回归 | PASS | `regression.xml/log`，exit0，198 PASS、0 FAIL/ERROR/SKIP |
| Backend collection | PASS | `collection.log`，exit0，2061 collected/146 modules；对 pytest quiet 模块计数求和，无 collection/import error，不是全量执行 |
| Ruff | PASS | 专用 contract 与新测试完整规则，`ruff-final.log`，exit0 |
| 非 Prompt AST / 不变量 | PASS | `prompt-scope.json`、`intermediate-evidence.json`；合同/代码/配置/历史账本与真实响应保全，最终统计见 final audit |
| git diff --check | PASS | 提交前/后核对；没有扩大代码改动范围 |
| 产品真实模型语义复测 | NOT RUN | 本轮授权0，实际0；仍待单独授权 |
| 真实 PG/checkpoint / 浏览器 / frontend build | NOT RUN | 无相关实现变化，不以静态/Mock冒充真实服务验收 |
| 全 backend 测试执行 | NOT RUN | 本轮只执行上述有界回归；既有旧 partial-content 夹具失败未重做、未追绿 |

使用现有 `.venv/Scripts/python.exe`，未安装依赖。旧 launcher-location 提示与已知控制台编码问题不代表访问或操作受保护目录；XML及证据以 UTF-8 保存。

执行命令（证据均在 ignored `var/planning-v2-item1-constraint-fix-20261008/`）：

```text
.venv/Scripts/python.exe -m pytest --confcutdir=backend/tests/unit backend/tests/unit/test_goal_requirement_hard_constraints.py -q --junitxml=var/planning-v2-item1-constraint-fix-20261008/red.xml
# Prompt 修改后以相同文件运行 green.xml
.venv/Scripts/python.exe -m pytest --confcutdir=backend/tests/unit backend/tests/unit/test_goal_requirement_analysis.py backend/tests/unit/test_goal_requirement_input.py backend/tests/unit/test_goal_requirement_provider.py backend/tests/unit/test_goal_requirement_hard_constraints.py backend/tests/unit/test_planning_intent.py backend/tests/unit/test_planning_legacy_removal.py backend/tests/unit/test_planning_residual_cleanup.py backend/tests/unit/test_b3_provider.py backend/tests/unit/test_b3f2_planning.py backend/tests/unit/test_known_json_repair.py -q --junitxml=var/planning-v2-item1-constraint-fix-20261008/regression.xml
.venv/Scripts/python.exe -m pytest --confcutdir=backend/tests/unit --collect-only -q backend
.venv/Scripts/python.exe -m ruff check backend/app/infrastructure/providers/goal_requirement_contract.py backend/tests/unit/test_goal_requirement_hard_constraints.py
git diff --check
```

## 独立审查

独立审查 **PASS**，无本轮离线修复 BLOCKER。审查范围为有限 Prompt/test diff 和同一 RED/GREEN/回归 Evidence Packet，不重复全仓审计，不让被测 Provider 自评。完整审查在 ignored `independent-review.md`。

审查确认：分类指导覆盖实际缺陷但不把所有目标变成限制；structured 同义合并仍逐条保留原文/index；“用途本身不是限制”与明确面试 target 可成为需求相容；Python声明/来源/Schema/ID/hash/接线边界保持；没有不必要抽象或调用；测试明确保留真实语义 PENDING。旧真实 Case2 FAIL 没有被离线 GREEN 覆盖。

## 修改文件、操作边界和回滚

仅四个 tracked 文件：

- `backend/app/infrastructure/providers/goal_requirement_contract.py`：仅 Item1 SYSTEM Prompt。
- `backend/tests/unit/test_goal_requirement_hard_constraints.py`：新增12项分层离线测试。
- `docs/planning-v2/ITEM1_HARD_CONSTRAINT_FIX.md`：本报告。
- `docs/implementation/progress.md`：新增本轮进度，历史原文保持。

公开 `/plans/generate` 继续 scope 后503，未注册 Fake Planning、未恢复旧语义，Planning 占位页不变。无新 Run/Job/Draft/Plan mutation，依据为本轮未接DB和 fail-closed依赖访问测试，真实PG行计数 NOT RUN。产品模型/搜索/Reader0、DB写入0、migration0。上一轮 request/result175～177、unknown177、真实输出/失败报告、账本总cap280/已用177/unknown1均保持；不重派 unknown，不消费旧剩余次数。无 push/merge/deploy。

回滚采用正常 revert 本地修复提交；无迁移或数据库回滚，不恢复旧Planning。Schema/hash/架构合同不变，本轮没有需架构评审的合同变化。全产品继续 STAGING_BLOCKED / NOT_READY。

## 单独真实模型复测申请（尚未授权、未执行）

申请下一单独 Goal 最多 **5次新真实请求、每案一次、无 retry/repair**，继续使用届时免费预检确认的既有 Provider/模型及既有4096上限，不自动更换收费模型或增加累计cap。先核对账户权限/余额/账本及无其他未解决调度冲突；任一 unknown/timeout/truncation 停止后续，不能把原 unknown177 改为已知失败或恢复它。

| 新案例 | 新输入/必须验证 |
|---|---|
| 修复后的 Case2 | 原只读 Code Review target + outcome_purpose=interview；hard_constraints必须包含只读/禁止修改、引用target，不扩面试课程 |
| Case4 必要推断 | 原PR分析/潜在问题/可追溯依据目标；检查explicit/inferred_required与实质rationale，不为制造推断而发明框架 |
| Case5 冲突 | 原完全离线/禁止网络与实时GitHub目标；保留双方事实，needs_clarification、1～3必要问题 |
| Case6 窄目标 | 原Python JSON/异常处理/本地CLI/免费教程目标；ready、无无关课程，免费限制进入hard_constraints |
| 独立 project_context | 工具错误处理/任务恢复目标 + 已有旅行规划Agent背景；新Acceptance/attempt身份，保留背景、不强制新项目，不属于旧Case3重试 |

这是一份具体复测申请，不是调用授权。只有用户另行明确授权后才能执行；本轮继续 STOP。真实语义接受仍 PENDING，Item2未启动。

**ITEM1_HARD_CONSTRAINT_FIX_READY_FOR_REAL_RETEST**

**ITEM1_REAL_SEMANTIC_ACCEPTANCE_PENDING**

**ITEM2_NOT_STARTED**

**STOP**
