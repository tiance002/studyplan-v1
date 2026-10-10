# Item 2 Capability 单一权威输出修复

**任务：** `STUDYPLAN_CAPABILITY_SINGLE_AUTHORITY_FIX_V1`

**状态：** `CAPABILITY_SINGLE_AUTHORITY_OFFLINE_PASS`

**真实课程验收：** `REAL_RESOURCE_CURRICULUM_ACCEPTANCE_NOT_RUN`

**结束：** `STOP`

## 基线与范围

- 分支：`feat/n1-resource-discovery`
- Start HEAD：`0fd5123e5e780b7c5d1e37ceaf39911e18350b64`
- 实现 checkpoint：`b311eb8f35ef0bc96c6e21c2cc123aa8cf28a6d7`
- 报告与进度在实现 checkpoint 后另作本地文档 checkpoint；本地 Final HEAD 见最终交付，没有 push、merge 或 deploy。
- 本轮模型、搜索、正文、Reader、价格/余额请求均为 **0**。
- 原有 `.workbuddy/`、`design-preview/` 和未跟踪的课程验收报告均保留，未纳入提交。

没有修改上位架构合同、Capability Policy、Goal Profile、标准 CapabilityPlan Schema/Validator、数据库、migration、历史 Receipt、旧 Run 或正式配置。本次只为 Item 2 新增一个显式版本化的决策 wire；规范化后的 `CapabilityPlan` 仍遵循现有 V1 Domain 合同及其确定性 hash。

## 第193次失败：原始证据与复现

从 ignored 的本地验收证据目录只读读取：

`var/planning-v2-scenario-a-curriculum-v2-20261010/acceptance-final/`

原始 `external-model-193-response.body` SHA-256 为 `cff138e9601d96576648b9e85f2c6a58843c4f9eba52c131136fd5d52f8ed5d9`。响应为 `deepseek-flash`、HTTP 200、`finish_reason=stop`，usage 为 4559 input / 1303 output / 5862 total。根据同目录的冻结 `prepared.json` 与原第192次 Provider Goal Profile payload，重新运行原 `GoalRequirementProfileValidator`，得到 Profile hash `71ffa724242a6ceea352eb701671ee361ad692c7325926fe2f14f3158b5203e6`，与第193次响应中的 `source_goal_profile_hash` 完全一致。

对从原始 HTTP 响应提取的**未修改模型 JSON**运行原 `CapabilityPlanValidator`，准确拒绝在 `claim_binding`：模型把 Python claim 绑定至 `python.core`，但能力行只有 `llm.api`、`structured.output`、`tool.calling`、`mcp`，而且全都标为 `needs_learning`，缺少 `python.core / accepted_known`。因此两处独立输出共同表达同一已知能力事实，彼此不一致。失败仍保持失败；原响应、Receipt、Run 和账本均未重写。

自动化 RED 回归使用对应缺陷形状确认 V1 Validator 继续拒绝悬空 claim。它不将修改过的真实响应伪装成新协议成功。另有一次真实冻结 Profile 离线 witness：输入正是上述第193次 Profile 与当前 Policy；当合成 claim 决策未给出已知 Python 与项目应用之间的 `requirement_refs` 时，原 Validator 以 `capability_without_requirement` 拒绝，服务端没有推断该引用。随后由合成模型决策明确把现有 CLI 应用需求关联到 Python 项目载体，规范化生成稳定 `CapabilityPlan`，Coverage/Gap 接口接受该标准对象，`python.core` 保持 `accepted_known` 且未生成 Python gap。这个关联只作结构见证，是否为真实目标的最佳语义映射仍应由独立 Stage Review 判断；它不是模型语义 PASS。

## 历史案例区分

| 案例 | 失败/结果类型 | 对本次单一权威修复的意义 |
|---|---|---|
| #185 | Policy/前置引用缺失导致 `definition_refs`；同一批还存在载体、工具范围等语义误分类 | 引用复制是结构职责问题；约束误分类是独立语义问题，本协议不声称修复后者。 |
| #186 | `required_requirement_coverage` 缺少项目整合目标与规划条件引用 | 这是需求归因/覆盖遗漏，不只是字段重复。 |
| #187 | 一次真实 CapabilityPlan 通过，包含 Python 已知及 MCP 学习 required、项目使用 optional | 是一次成功证据，不证明重复输出错误已可靠消除。 |
| #189 | 结构可接受，但 MCP 项目使用被无依据设为 excluded | 属真实语义判断问题，需要独立 review，不能由规范化器“纠正”。 |
| #191 | HTTP 压缩解码与 W5 审计路径不一致，导致 `usage_untrusted` | 是 Provider/W5 传输审计问题，不是能力语义。 |
| #193 | claim 指向 `python.core`，能力列表缺少对应 accepted-known 行，原 Validator 报 `claim_binding` | 首要反例：拆除两处重复权威，由一份 claim 决策生成一致标准 Plan。 |

以上旧案例均保持原始结果；没有用新协议重新解释其历史响应或 hash。

## 实现

新增 `CapabilityDecisionV2`（协议标记 `capability-decision-v2`）。模型只提供能力选择、importance/depth/project usage、真实 requirement/learning-target 引用、选择理由、claim 映射、约束效果、澄清/验证状态。它不再输出能力 title、outcomes、固定 Policy refs、真实 prerequisites、`accepted_known` 清单或第二份 `claim_bindings`。

服务端从当前受信 Policy 和已有领域验证定义规范化：

- 为每个已选能力填充冻结定义、outcomes、Policy refs 和真实 prerequisites；不自动增加缺失的学习能力，遗漏前置仍由原 Validator 拒绝。
- 从唯一的 `claim_decisions` 生成 `accepted_known` 对象及标准 `claim_bindings`。每个 Profile claim 必须映射到一个或多个明确能力，或显式归入一个 `capability_id=null` 组；不能从未映射声明推断用户已会某能力，也拒绝重复、矛盾 null/mapped、与 learning 能力重叠及无定义映射。
- 已知能力的 project usage、相关 requirement refs 和理由必须由模型明确提供；Policy 可确定的定义与默认深度由服务端提供。规范化器没有猜测项目用途或补造需求引用。
- 约束、所需引用、MCP 系统性路线要求、dependency cycle、状态及完整性最终仍由原严格 Validator 判断。未知领域保持 pending/verification，不虚构定义。

为了兼容旧 Domain 对 accepted-known 行的枚举，规范化时该行的 `learning_requirement` 使用 legacy `recommended` 占位；其 disposition 仍为 `accepted_known`，不进入 `learning_capabilities`。Coverage/Gap 只读取学习集合；Curriculum 将已知能力单独放入 `accepted_known`。真实第193次 Profile 的离线检查确认 Python 没有转为学习缺口。原 hash 算法、标准对象字段和下游接口没有改变。

选择理由保留在 W5 的原始 Provider 响应 Receipt（Response payload）；标准 `CapabilityPlan` hash 仍只覆盖其既有字段。Receipt 与 Plan 的关联由 W5 的 request/manifest 身份及持久化回执绑定。独立审查应查看决策回执，而不能只从 Plan hash 推断模型理由。

### 旧 Run 与新 Run 的协议隔离

- 只有新的 owned V2 acceptance 可冻结 `capability_output_protocol=capability-decision-v2`；构造器和 manifest builder 对其他组合拒绝。
- marker 进入 manifest hash；`purpose_schema()` 只对明确有 marker 的 Run 选择 `CapabilityDecisionV2`。没有 marker 的既有 `planning-v2-product-v2` manifest 继续选择 `CapabilityPlanV1`。
- 实际 Provider schema 名进入 W5 reservation/attempt/Receipt identity；checkpoint 经 `manifest_hash` 绑定该选择。旧 manifest 不能恢复使用新 marker 的 checkpoint。
- Scenario A 准备 CLI 仅在显式传入新协议选项时冻结 marker 和 request-plan schema；其默认/旧 packet 格式不变。

## 验证证据

| 检查 | 结果 | 证据边界 |
|---|---|---|
| 第193次真实原始输出 + 对应真实 Profile，原 Validator 重放 | **FAIL（预期保留）** | 原样在 `claim_binding` 拒绝；这是未修改的历史失败，不算本轮通过。 |
| CapabilityDecisionV2 新单一权威、claim→accepted-known、未映射/错映射/多对多、Policy/ref/prerequisite/constraint/unknown 反例 | **PASS** | 14 项新定向 unit tests；错语义映射不会由服务端自动改正，仍须独立语义审查。 |
| 真实第193次冻结 Profile 的合成决策 → 标准 Plan → Coverage/Gap | **PASS** | Profile hash `71ffa...`; plan hash `2c2be81c7b864be8a427f94f5f70c611c6bb8c3190a16768206b64551f182745`; Python 不进 Gap。仅证明确定性合同和下游接口。 |
| Mock Provider + W5 owned PostgreSQL attempt/receipt、同身份重放及 checkpoint 恢复 | **PASS** | 新隔离 owned PG 测试 1 项通过；同一 Receipt 重放没有第二次 HTTP；原 schema 不同的 manifest 无法加载 V2 checkpoint。数据库仅为本测试隔离创建，未改正式 DB。 |
| Item 2/W5 相关 Provider、Policy、manifest、Scenario A prep、owned gate 回归 | **PASS** | 11 个定向测试模块合并执行，`pytest` exit 0；包含上述新 PG 测试。首次默认临时目录运行受沙箱 temp 创建权限影响，使用仓库 `var/` 的 `--basetemp` 重跑通过；保留了该环境性失败事实。 |
| Ruff / `git diff --check` | **PASS** | 本次所有变更 Python 文件 Ruff 通过；Git whitespace 检查通过。 |
| 独立开发审查 | **PASS，无阻塞项** | 审查者独立复核当前 diff、#193 原始响应及 Profile；另做 10 项 malformed claim/reference probes。审查者没有重跑 PG。实际开发模型解析：`NOT OBSERVABLE`。 |

新 owned PG 测试以 mock HTTP transport 运行，seed 的 Goal review 只是隔离 Capability 派发阶段的合成审批事实，不代表真实 Goal 阶段通过。完整 Backend/React、真实 Worker 的产品语义、真实 DeepSeek、教材、Reader、Curriculum、正式 Draft/页面闭环均为 **NOT RUN**。

## 独立审查结论与剩余风险

独立审查确认：V2 消除了同一已知能力由 `claim_bindings` 与独立能力列表分别声明的冲突；旧 V1 manifest 不会自动切换；服务端只补冻结 Policy 定义和由已映射 claim 产生的标准字段，没有补做模型遗漏的能力选择或项目决定；Coverage/Gap 仍排除 accepted-known。

结构上合法的错误语义映射仍可能通过原 Validator，例如把 Python claim 指向一个不相关但合法的 Policy capability。服务端不能根据关键词纠正它；新的 owned review 必须检查原始决策 Receipt 和标准 Plan。模型理由保存在原始回执，不在标准 Plan 内。仅靠本轮 Mock/合成证据不能证明真实 DeepSeek 会一次正确生成新协议，需另外获得新的真实请求授权后单独复测，且不得恢复 #193 失败 Run。

本轮没有启动教材研究或资源课程验收。真实产品调用、Reader/正文、搜索及官方价格/余额均为0；公开生成、历史 Run/Receipt、旧失败及正式数据库保持既有状态。

**`CAPABILITY_SINGLE_AUTHORITY_OFFLINE_PASS`**

**`REAL_RESOURCE_CURRICULUM_ACCEPTANCE_NOT_RUN`**

**`STOP`**
