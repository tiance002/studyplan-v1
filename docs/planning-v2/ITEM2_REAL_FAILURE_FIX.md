# Item 2 真实失败定向离线修复

任务：`PLANNING_V2_ITEM2_REAL_FAILURE_FIX_V1`。日期：2026-10-09。

**`ITEM2_REAL_FAILURE_OFFLINE_FIX_PASS`**。

**`ITEM2_REAL_SEMANTIC_RETEST_NOT_RUN`**。

本轮只改善 Item 2 专用 Prompt 与 field shape 的规则表达。离线测试和独立审查通过，不能据此宣称 DeepSeek 已更可靠或真实语义失败已关闭。原第185次失败及其证据保持原样。

## 1. 基线、范围和证据

- Start/source HEAD：`b7b7aff07386648b61bea97a5df1591f15bfdd95`；branch `feat/n1-resource-discovery`，与请求一致。
- 起始 tracked tree clean，只有既存 `.workbuddy/`、`design-preview/` untracked，未操作。
- Final HEAD 为本报告所属本地 checkpoint：`checkpoint-planning-v2-item2-real-failure-fix-20261009^{commit}`。准确 SHA 另存 ignored delivery receipt，避免提交文档自引用 SHA。
- 权威仍为 [Planning V2 架构合同](PLANNING_V2_ARCHITECTURE_CONTRACT.md)。直接复用 [真实 Scenario A 验收](PLANNING_V2_SCENARIO_A_REAL_SEMANTIC.md) 和 [约束作用域修复](ITEM2_CONSTRAINT_SCOPE_FIX.md)，不重复 Item 1、Backend、PG、React、浏览器矩阵。
- 共享证据目录：`var/planning-v2-item2-real-failure-fix-20261009/`。

修改文件仅五个：

1. `backend/app/infrastructure/providers/capability_planning_contract.py`：Item 2 Prompt／field shape，唯一生产源码变更。
2. `backend/tests/unit/test_item2_real_failure_contract.py`：本次失败的定向行为及合同表达测试。
3. `backend/tests/fixtures/planning_v2/item2_scenario_a_failure.json`：合成 Scenario A 的**实际历史模型 payload 副本**，用于 CI 原样复现；注明真实184/185来源及原 response hash，不是新的真实模型结果。
4. 本报告。
5. `docs/implementation/progress.md`：前置本轮记录，保留旧历史字节。

未修改架构、Capability Policy v2、Item 1 Profile、CapabilityPlan Schema／Validator、约束适配版本、hash 算法、Provider 流程、Run／Worker／Receipt／预算、数据库、前端或正式配置。

## 2. F0：原始失败与一次完整定位

首先从真实原 response 解析 payload，重建原 Item 1 Profile，再将原 Item 2 payload **未经修改**送入现有 Validator。首拒仍为 `definition_refs`。测试在修复前后都要求该历史失败继续拒绝；没有逐项补字段后把旧响应追成 PASS。

| 问题类别 | 原始证据 | 本轮处理 |
|---|---|---|
| 结构／定义引用 | json.cli、llm.api、structured.output、tool.calling、agent.loop、error.permission、eval.lite 共7项 `policy_refs=[]` | 明确已选 Policy 能力逐项精确复制自身定义引用及前置；Validator 不自动补全 |
| 实践约束误成能力排除 | 保留CLI/JSON → json.cli project exclusion；本地工具范围 → tool.calling project exclusion；两者又 project_usage required | 解释 exclusion 的真正排除含义；载体／权限范围在能力层是 not_applicable，后续验证保留 |
| MCP 来源归因 | 把 `学习成果用途是学习` 当明确 MCP learning target | 区分用户目标和系统路线政策；普通 learn 用途不推出 MCP 技术目标 |
| Requirement 覆盖 | `学习深度为应用级` 未被任何 capability 引用 | 规划条件可引用真正受其影响的能力，不能伪装成技术 learning target |
| 项目背景扩课 | 因已有JSON CLI而选择完整 json.cli needs_learning，缺少必须补学的独立目标依据 | 已有项目既不证明完整能力掌握，也不要求重新学习；选择需真实目标／前置依据 |

第185次 JSON／HTTP明确返回成功，但没有形成合法 Plan；本报告未改变该事实。模型关于 Python accepted_known、核心两能力及 MCP 学习与项目分离的局部正确结果也不等于整案通过。

原 Item 1 response SHA-256：`5df5001e08e9bdc6d57ebdbc3876b264e95780d67049e5351029a7afd7a69a76`。

原 Item 2 response SHA-256：`94fdf2be78bb721b23345b1507ed0c0373b0370d30dffe50ce56070e52b59268`。

实际 Profile hash：`b0386820c14a6aa2b9aa9b1df1aeb1ddc6b5e8925df0a8ec6f70d66dd09f7348`，全文／source_refs／约束／claim 均保持。新 fixture 与历史 payload 逐字段相等，原 body／账本没有覆写。

## 3. F1／F2：最小 Prompt／输出说明变化

原 field shape 的引用数组全为 `[]`，原 Prompt 只说“仅引用该能力 Policy 条目”，没有清晰表达“必须完整复制且不能省略”。本轮将关键数组的占位说明改为精确复制／合法来源说明，明确占位字符串不能作为实际引用输出；没有改变 wire 字段或 Enum。

新增／替换说明：

- 已选 Policy 能力按 capability_id 查自己的 definition；`policy_refs` 与 `prerequisite_refs` 分别完整复制 `definition.policy_refs`、`definition.real_prerequisites`，包括 accepted_known；禁止缺失、伪造、借用其他能力或增加教学顺序前置。
- 不输出定义全文、outcomes、title 或 plan_hash；MCP `#systematic-agent-mcp` 特殊课程引用由既有服务端添加，模型不能额外写入原 policy_refs。
- 一个引用复制示例只说明已选能力怎样复制字段，明确不是能力选择模板，最终以输入 Policy 为准。
- `learning` 是真实排除学习；`project` 是真实排除项目使用；`not_applicable` 是当前能力层不构成排除，capability_id 为 null。
- 保留CLI/JSON、不重建项目及工具允许范围都不是整项能力禁用；模型不能把它们输出成 project exclusion。not_applicable **不表示原约束已满足，不授予权限**，后续仍需真实载体和工具权限证据，pending／incomplete 保持。
- 对照“不在最终项目使用 MCP”与“限制 MCP 工具操作范围”：前者可 project exclusion、project_usage excluded，学习仍可 required；后者不是能力排除，也不意味着项目必用 MCP。

两个新的 MCP 示例只提供模型语义指导，没有新增 constraint exact phrase allowlist。当前真实 Provider 对这些未知文案仍 fail-closed；Domain 能表达排除不意味着外部派发已获得准入。本轮不扩大隐私／联网权限。

## 4. F3：真实六条需求的可表达性

独立审查先核查现有合同，没有发现必须跨范围修改的矛盾。以下是**人工合成的最小合法映射 witness**，不是编辑历史185响应、固定路线或真实课程标准答案：

| 原真实 requirement | 合成 mapping 中的真实用途 |
|---|---|
| R1 原 Python CLI／JSON 背景全文，含继续增加 Agent 能力 | python.core accepted_known 的项目背景引用，绑定原 Python claim，learning_target_refs 空；结构化输出／工具使用原项目的实际实践要求另由 R4 表达 |
| R2 系统学习 Agent 结构化输出 | structured.output 的技术 learning target，并为 llm.api 先修提供目标依据 |
| R3 系统学习 Agent 受限工具调用 | tool.calling 的技术 learning target，并为 llm.api 先修提供目标依据 |
| R4 将这些能力加入原 CLI | structured.output／tool.calling 的应用项目引用 |
| R5 学习深度为应用级 | 引用到选择 applied 的 structured.output／tool.calling，仅规划条件 |
| R6 学习成果用途是学习 | 引用到实际待学习的 structured.output／tool.calling，仅用途条件，不是 MCP 技术目标 |

MCP 在系统路线由 Policy 引入：`learning_requirement=required`、项目 optional、直接 requirement_refs／learning_target_refs 可空；wire 只复制自身 `#mcp` 定义引用，特殊系统政策引用由 Validator 现有逻辑补入冻结 Plan。

合成 witness 不选 json.cli；Python accepted_known 不进入学习集合。没有借条件随意关联无关能力，也没有删改历史 Profile。后续模型仍可在目标必要性成立时选择 agent.loop／error.permission／eval.lite，不能把这份五能力 witness 变成统一模板。判断教材／课程是否足以实现目标不在本轮证明范围。

## 5. F4：RED／GREEN、受影响回归与 Provider 边界

| 检查 | 实际结果及范围 |
|---|---|
| 原始真实失败重放 | PASS：原样仍拒绝 definition_refs，原 Profile hash 不变 |
| 初始 RED | **6 FAIL／14 PASS，10.32s**；五类 Prompt 规则说明及 shape 空引用提示未满足，其他既有机械边界已通过；`red.txt` |
| 合并定向 GREEN | **117 PASS，1.70s**；新20例＋既有 CapabilityPlanner／Provider／scope边界，`green.txt` |
| 新测试最终格式检查后 | **20 PASS，1.57s**；`final-targeted.txt`。仅测试 import／单行代码格式整理，不再重复117套件 |
| Ruff | PASS；`ruff-final.txt`。初始 lint 记录保留，没有放宽检查 |
| Import／collection | 上述实际执行已完成，PASS；没有全量 Backend collection |
| Strict Validator 反例 | 缺失／跨能力借用Policy／额外MCP特殊引用／错误前置继续 definition_refs 拒绝；深度引用丢失仍 required_requirement_coverage 拒绝 |
| 合法绑定与下游 | 真正 project exclusion 与范围限制可区别；not_applicable 后原 scope assessment 仍 pending，不释放完整性保护 |
| 权限／领域保护 | no_network、外发隐私、未知隐私、fixture领域证据均在 actual Provider invoke 前拒绝；继承的复合约束反例仍 PASS |
| 实际 Provider wire | MockTransport 一次，完整 system/user messages JSON **17,775 bytes／32,768**；4096、非思考、真实原 Profile，新专用 system／field shape实际进入body，synthetic返回合法Plan |
| 真实模型质量改善 | **NOT RUN**；Prompt 文案与合成合法输出不证明模型会生成相同决定 |

wire hash：`630d99817623e3744fa3ca50c319556511c567a11a1181e8210b77aec6c785e1`，见 `wire.json`／`item2.offline-wire.json`。32 KiB 是开发期大小限制，不是 token 或现金硬上限；本轮没有新的真实 usage 或费用估算。

测试命令：

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='backend;.'
.venv/Scripts/python.exe -m pytest backend/tests/unit/test_item2_real_failure_contract.py backend/tests/unit/test_capability_planning_provider.py backend/tests/unit/test_capability_planning.py backend/tests/unit/test_item2_constraint_scope.py -o addopts='' -q
.venv/Scripts/python.exe -m pytest backend/tests/unit/test_item2_real_failure_contract.py -o addopts='' -q
.venv/Scripts/python.exe -m ruff check backend/app/infrastructure/providers/capability_planning_contract.py backend/tests/unit/test_item2_real_failure_contract.py
git diff --check
```

## 6. 独立审查与交付保护

独立代理先验证 F3 可表达性，再检查完整源码差异、原响应 fixture、Policy／Validator／约束适配未变、wire 及反例证据；结论 **PASS，无开放问题**。未把实施者测试结论当真实模型语义结论。审查证据 `independent-review.py/json/md`。

请求开发模型 `gpt-6.1-sol/xhigh`，实际解析 **NOT OBSERVABLE**。主会话档位不能由工具切换或核实，没有修改全局模型配置。

`.env`、所有旧账本 JSON、历史 response／receipt／报告／证据 hash 保持；模型请求仍 **185/280**，历史 unknown177／183保持，不重派184／185，也没有新增授权账或模型身份。搜索账本仍6/1000，未使用算术余量。progress 历史后缀字节保留；最终 `protection.json` 记录 diff／历史核对。

真实产品模型、搜索、Reader、正文、账户／价格 preflight 全部 **0**。正式数据库／Run／Worker／Draft／Revision没有调用，无 migration；PG行数、真实业务PG／React／浏览器、完整教材课程端到端及真实语义复测 **NOT RUN**。公开生成保持既有503，源码／配置未开放。不 push、merge、deploy。

## 7. 仅复测 Item 2 的准备状态与限制

**具备有界离线准备条件**：已保留独立真实语义通过的 Item 1 原 Profile，新 Item 2 contract 可以进入 actual Provider preflight 与32 KiB序列化，合成 witness 能通过原严格 Validator；不需要再次请求 Item 1。

真正执行前仍需新的 Owner 外部授权、当前价格／余额和参数核对、新独立 acceptance／一次性 Item2身份、实际新body的派发前尺寸／来源绑定及 append-only预约。旧付费 entry 的基线保护不能直接复用派发；必须针对新 HEAD／Prompt hash 重新冻结入口，不能换身份重派历史失败。此前两次授权已用完，本轮额度0。

仍未证明：模型是否遵守新的精确引用、是否准确区分所有约束作用域、是否合理选择辅助能力、是否将元数据正确归因。现有 Validator 仍只机械验证引用／完整性，不能证明语义真实；后续单次真实结果还需独立评审。工具运行权限证据缺口仍让后续 Curriculum pending／incomplete；本轮没有关闭现金硬上界或完整产品验收。

建议后续只授权 **1 次新 Item 2** 复测，消费同一原真实 Profile，另由 Owner明确必要外部 preflight范围和费用风险；不自动启动该复测。

`ITEM2_REAL_FAILURE_OFFLINE_FIX_PASS`

`ITEM2_REAL_SEMANTIC_RETEST_NOT_RUN`

STOP。
