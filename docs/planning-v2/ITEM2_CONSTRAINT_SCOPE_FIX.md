# Planning V2 Item 2 Constraint Scope Fix

任务：`PLANNING_V2_ITEM2_CONSTRAINT_SCOPE_FIX_V1`。日期：2026-10-09。

结果：`ITEM2_CONSTRAINT_SCOPE_FIX_PASS`。`REAL_SEMANTIC_ACCEPTANCE_NOT_RUN`。STOP。

本轮只解决冻结 Scenario A 的 Item 2 约束准入。没有执行真实模型、搜索、Reader、正文或账户预检；没有证明真实 CapabilityPlan 语义或完整课程可确认。

## 基线与修改范围

- Branch：`feat/n1-resource-discovery`。
- Start HEAD：`18b8474e7c9b17839675213ed28e44811854e19d`，与请求一致。
- Final HEAD：本报告所属本地提交；可用 `git rev-parse checkpoint-planning-v2-item2-constraint-scope-20261009^{commit}` 精确定位。最终 SHA 同时保存于 ignored delivery receipt，避免文档内自引用提交 SHA。
- 起始 tracked tree clean；仅有既存 untracked `.workbuddy/`、`design-preview/`，未操作。
- 权威仍为 [冻结架构合同](PLANNING_V2_ARCHITECTURE_CONTRACT.md)。沿用 [前次本地语义准备](PLANNING_V2_REAL_SEMANTIC_SMOKE.md) 的 Scenario A，不改输入、不重派历史请求。

修改文件只有：

1. `backend/app/domain/planning/constraint_adaptation.py`：两个 exact phrase 规则、逐规则版本及显式旧版解释入口。
2. `backend/app/application/teaching_resource_research.py`：仅受新规则影响的 Research config hash 绑定新局部适配版本。
3. `backend/tests/unit/test_item2_constraint_scope.py`：有界准入、拒绝、下游及版本反例。
4. 本报告。
5. `docs/implementation/progress.md`：前置本轮记录，原历史字节保留。

没有修改 Provider、Planner、Composer、Schema、Capability Policy v2、GoalSpec、ID/hash 算法、Runtime、数据库、迁移、前端、配置或旧报告。

## D0：实际消费接缝

| 消费方 | 原有检查及本轮结论 |
|---|---|
| `CapabilityPlanner.plan` → `OpenAICompatibleLLM.preflight` | 合法 Profile 仍须通过领域输入与 `composition_dispatch_allowed()`；原两条约束 unclassified 会产生 `capability_planning_input_invalid / dispatched=false`。本轮只改变这两个精确原文的分类。 |
| `ResourceResearcher.research` | `research_permissions()` 控制本地复用与外部研究；config hash 在完成缓存返回、预算预约前核对。新 scope 不重推能力；约束随冻结资料要求保留。 |
| `CurriculumComposer.compose` → Provider | 相同外部准入保护。新的可识别分类允许理解事实，但不提供满足证据。 |
| `CurriculumValidator` | `assess_curriculum` 由真实载体和可信资料事实产生状态，`constraints_unresolved` 继续导致 incomplete。模型安全承诺不是证据。 |
| Compiler / `V2ExecutionSnapshot.from_payload` | 会消费 Validator 与冻结 compile_context；不能假设历史 readback 完全不使用当前验证器，因此必须保持旧规则判断、引用及 hash。 |

## D1：两条精确规则及满足条件

| 不变的原约束 | 分类 / Curriculum scope | 允许的效果 | 不自动证明的事实 |
|---|---|---|---|
| `保留现有 CLI 和 JSON 任务文件作为持续实践载体` | `existing_carrier` / `practice_carrier` | Item 2 可以理解已有载体要求，复用既有 carrier 校验 | 仅识别成功不代表项目保留已满足 |
| `工具仅操作用户明确允许的本地任务范围` | `local_tool_scope` / `practice_permission_scope` | 识别为实践权限边界，允许 Item 2 与资料研究准入 | 不授予任何工具/本地文件权限；不验证模型声称的安全性 |

只有完整原文精确相等才匹配。没有关键词包含、相似度、NLP 分类器、第二模型或字符串替换。复合约束、附加权限、网络限制以及非精确变体仍 unclassified。

载体的实际 satisfied 条件保持原样：存在原 `project_context`，`carrier.kind == user_project`，且 `carrier.description` **完全等于原 project_context**；证据引用绑定该背景的 content hash。缺载体或改写 description 为 pending，starter 为 violated。没有具体失败证据，不放宽此条件。

工具范围始终 pending，reason 为 `runtime_permission_evidence_pending`，没有证据 refs。含此约束的 Curriculum 继续 incomplete，伪装 complete 被 Validator 拒绝，Compiler 不生成可确认的完整结果。因此冻结 A 的 **Item 2 准入阻塞已解决，最终 complete Draft 仍受实际权限证据缺口限制**；本轮没有补造证据或另建权限验证系统。

原 Profile 原文、source_refs、constraint_id 均保留；没有删除 hard_constraints 或跳过准入校验。

## 局部版本与历史可解释性

旧 `CONSTRAINT_POLICY = constraint-adaptation:v1` 及原短语表保持不变。两个新增 exact rules 使用 `constraint-adaptation:v2`，这是局部约束适配版本，**不是 Capability Policy v2 的修改**。

- 默认旧短语 assessment 继续 v1，canonical 内容/hash 不变；显式选择 v2 也不能把旧规则重新标记成 v2。
- 显式 `policy_ref=v1` 时，新短语仍按旧规则产生 unclassified/pending；未知版本在入口拒绝，空约束也不能绕过。
- Research config 仅在输入使用新精确规则时绑定 v2；所有其他输入仍绑定 v1。
- 已存在的 v1 Research 配置若包含这些新短语，恢复时明确拒绝 `session_configuration`，包括已完成缓存；不改旧记录、不把旧预算/成果重新解释为新规则、不派发恢复请求。
- 新短语在旧合同下为 pending，不存在经当前完整性合同合法发布的 complete 成果。本轮没有修改任何历史 Run、Receipt、Revision 或账本。

独立审查用基线源码作为 oracle：19 个旧短语 × 3 资料组合 × 2 项目条件 × 4 carrier = **456** 个 canonical assessment 均保持相等；另用旧 complete 合成教学 fixture 核对 Curriculum、Compiler、typed snapshot hash 与 `from_payload` 读回。此为离线兼容验证，真实历史 PG 读回本轮 NOT RUN。

## D2 / D3：程序验证证据

原始证据位于 ignored `var/planning-v2-item2-constraint-scope-fix-20261009/`。不含 API Key 或认证头；合成 Profile/教学 fixture 不是实际模型输出。

| 验证 | 结果与证据 |
|---|---|
| 初始 RED | 4 FAIL / 8 PASS；失败为两规则准入、carrier、工具 scope、Research 下游。`red.txt`。 |
| 显式 v1 RED | 1 FAIL，原接口不支持版本选择。`red-version.txt`。 |
| 独审反例 RED | 2 FAIL：空约束未知版本未拒绝、显式 v2 重标旧规则；修复后纳入合并回归。`review-red.txt`。 |
| 最终 GREEN / 定向回归 | **123 PASS，2.62s，exit 0**。包含新 scope、原约束、Item 2 Provider、Curriculum Provider、Research 及 4 个 Compiler 保全/不完整保护测试；`regression.txt`。 |
| Ruff | 三个变更 Python 文件 PASS；仅纠正测试 import 排序。 |
| Import / collection | 上述实际执行的 123 测试已完成，PASS。未另跑全量 collection。 |
| 原始 Goal / Profile 保全 | Goal 与前次冻结 Scenario A 逐字段一致；本轮合成 ready Profile 在真实 Planner/Provider 调用前后 payload/hash 相同。 |
| 实际 Item 2 serializer | CaptureOnly 到达真实 Provider 的请求构造路径；无真实 HTTP delegate，无伪造模型返回。完整 messages JSON UTF-8 **12,970 bytes**，32,768 byte 检查 PASS；content 合计 12,189 bytes。 |
| 模型参数 | 实际构造 `deepseek-flash`、非思考模式、单次输出 cap 4,096；未请求模型。32 KiB 是开发期数据大小防护，不是 token/cash 上界。 |
| 负向保护 | 8 个网络、外部发送、未知隐私及附加权限/复合约束反例均在实际 Provider invoke 前拒绝，`dispatched=false`，CaptureOnly 调用 0。 |
| 下游 | 真实本地 reviewed MCP 索引复用，冻结能力 hash / 三约束保留；scope 不重新解释能力。合成 task 安全承诺不能使 pending → satisfied；删除 constraint refs 或伪装 complete 均拒绝。 |
| v1 旧绑定 | 根脚本旧 complete fixture 全文重建相等，plan hash 不变；独审另核对旧消费者、6 个旧配置恢复反例及新 carrier 合成 snapshot。 |
| 范围与历史保护 | `git diff --check`、既有 tracked hashes、原 progress 历史后缀、`.env`、模型/搜索账本集体 hash 在交付检查中核对；记录 `protection.json`。 |

实际离线 Profile hash：`38341605df3e74eac7b6bf3d59c1dc12aba3aec36910db9b00f10ae5bb336589`。请求 body SHA-256：`a62d1281c4a4fc6fbe7a65e02d2220e547ba50b0f0ddf2751049059331bf2b7e`。旧完整 fixture plan hash：`291c3b57904e7a9a340bca92366dba79fbf81b9af06de5be35a7e702dff1a009`。详见 `wire-and-legacy.json`；这些不是新模型响应或真实计费证据。

最终回归命令：

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='backend;.'
.venv/Scripts/python.exe -m pytest backend/tests/unit/test_item2_constraint_scope.py backend/tests/unit/test_constraint_adaptation.py backend/tests/unit/test_capability_planning_provider.py backend/tests/unit/test_curriculum_provider.py backend/tests/unit/test_resource_research.py backend/tests/unit/test_curriculum_compiler.py::test_complete_deterministic_and_frozen backend/tests/unit/test_curriculum_compiler.py::test_all_original_facts_and_blueprints_are_retained backend/tests/unit/test_curriculum_compiler.py::test_pending_hard_constraint_rejected backend/tests/unit/test_curriculum_compiler.py::test_incomplete_has_original_diagnostics_and_no_candidate -o addopts='' -q
.venv/Scripts/python.exe -m ruff check backend/app/domain/planning/constraint_adaptation.py backend/app/application/teaching_resource_research.py backend/tests/unit/test_item2_constraint_scope.py
git diff --check
```

## D4：独立审查与剩余边界

独立代理读取实际源码、diff、冻结合同及测试，不采用实施者 PASS 替代验证。请求模型 `gpt-6.1-sol/xhigh`，实际解析 **NOT OBSERVABLE**；主会话模型/effort 不可由工具切换或核实，未修改全局配置。完整结论与两个反例关闭记录保存在 `independent-review.md/json`。

独审重点包括精确匹配、旧 v1 字节兼容、缓存前配置拒绝、typed snapshot 消费、载体真实证据与权限 pending。两处显式版本入口问题已先 RED 后修复并由独审逐项关闭；最终独立审查 **PASS**，`open_findings=[]`。

本轮没有新增授权或产品请求身份，真实模型、搜索、Reader、正文和账户预检均 **0**。模型历史 183/280、unknown177/183、搜索 6/1000 仅为当前本地账本记录，hash 不变，不代表可消费授权。公开 generate 保持既有 fail-closed；入口及配置源码未动，复用有效边界证据，没有本轮启用。

真实 PG、Worker/HTTP/React/浏览器、全量 Backend、实际 CapabilityPlan 与教学语义均 **NOT RUN**。不新增 Run/Job/Draft/Revision，不做正式数据库写入；实际正式库行数未核验。没有 migration 或完整运行链启动，没有 push/merge/deploy。

下一步最小工作仍是 Owner 另行授权有界 Item 1–2 真实语义测试；此前现金硬上界缺口没有被本修复解决。真实输出还需独立核对已知 Python、原 CLI/JSON 背景、动态能力与 MCP 政策。下游工具权限缺乏可信满足证据应继续报告 incomplete；本轮不提前改变课程核心语义或权限合同。

`ITEM2_CONSTRAINT_SCOPE_FIX_PASS`

`REAL_SEMANTIC_ACCEPTANCE_NOT_RUN`

STOP。
