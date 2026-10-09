# Item 2 单次真实语义复测：本地冻结准备

任务：`PLANNING_V2_ITEM2_REAL_RETEST_V1`。日期：2026-10-10。

**R0 本地准备 PASS；本次真实程序验收 NOT RUN；本次独立真实语义验收 NOT RUN。**

本 Goal 明确要求 Owner 另行批准外部请求；截至本报告交付，尚未收到该项单独授权。因此价格、余额预检和真实 Item 2 请求均未执行。上一轮184/185的授权已使用，账本剩余容量不构成本轮授权。未把离线请求构造或合成结果当作真实复测 PASS。

## 1. 基线与范围

- Start/source HEAD：`f214f729ec05322c8e179adc2deadc94a90fc731`，与参考一致。
- Branch：`feat/n1-resource-discovery`。
- 起始 tracked tree clean；只有既存 `.workbuddy/`、`design-preview/` untracked，未操作。
- 本报告的文档 checkpoint 是 Final HEAD；提交后准确 SHA 存于 ignored delivery receipt，避免报告自引用自身提交 SHA。
- 复用 [上轮真实 Scenario A](PLANNING_V2_SCENARIO_A_REAL_SEMANTIC.md)、[约束作用域修复](ITEM2_CONSTRAINT_SCOPE_FIX.md) 和 [Item 2 真实失败离线修复](ITEM2_REAL_FAILURE_FIX.md)。权威合同、Policy v2、Schema、Validator、历史 Profile、正式配置和生产源码均未修改。
- 仅新增本报告、前置进度记录；本地冻结脚本和证据保存在 ignored `var/planning-v2-item2-real-retest-20261010/`。
- 主会话实际 model/effort 解析：`NOT OBSERVABLE`；未修改模型全局配置。复用上轮独审，不为本地机械核对重复派审。

## 2. 原真实 Profile 冻结

从 `var/planning-v2-scenario-a-real-20261009/item1.response.body` 的实际 HTTP envelope 提取 `choices[0].message.content`，解析原 JSON，再使用原 `GoalRequirementProfileValidator` 和原 GoalSpec 重建。没有使用合成 witness 作为输入。

核对结果均 PASS：

- 原始响应 SHA256：`5df5001e08e9bdc6d57ebdbc3876b264e95780d67049e5351029a7afd7a69a76`。
- 原 JSON 与历史 `item1.provider.json.payload` 相同。
- 重建 Profile 全文与历史 `item1.json.output` 相同，包括全部 source_refs、三条 constraint_id、learner_claim、项目背景及确定性 hash。
- Profile `status=ready`；hash：`b0386820c14a6aa2b9aa9b1df1aeb1ddc6b5e8925df0a8ec6f70d66dd09f7348`。
- 上轮独立 Item 1 审查的 Profile hash 和原响应 SHA 绑定一致，程序与真实语义 PASS 直接复用；本轮没有重新调用 Item 1。

冻结 GoalSpec：

```json
{
  "target": "我已经会 Python，想系统学习 Agent 的结构化输出与受限工具调用，并把这些能力加入我现有的待办事项 CLI。",
  "scope": ["结构化输出", "受限工具调用", "系统性 Agent 应用学习"],
  "desired_depth": "applied",
  "starting_point": "已经会 Python。",
  "outcome_purpose": "learn",
  "constraints": [
    "保留现有 CLI 和 JSON 任务文件作为持续实践载体",
    "不重新创建演示项目",
    "工具仅操作用户明确允许的本地任务范围"
  ],
  "project_context": "我已有一个 Python 本地待办事项管理 CLI，使用 JSON 文件保存任务，希望在现有程序上逐步增加 Agent 能力。"
}
```

## 3. 实际配置与序列化检查

本地读取现有 LLM 配置，通过正式 `build_llm` 工厂装配 `OpenAICompatibleLLM`，将其 client 替换为 `MockTransport`。真实 `CapabilityPlanner` 消费上述原 Profile，执行 Provider preflight 和请求构造；MockTransport 捕获请求后立即中止，不返回模拟模型答案，也不执行 HTTP/DNS/账户请求。没有启用 endpoint 网络验证。

| 核对项 | 实际结果 |
|---|---|
| Provider / endpoint | `openai_compatible` / `https://api.deepseek.com` |
| 模型 / 输出 / thinking | `deepseek-flash` / `max_tokens=4096` / `thinking.type=disabled` |
| 凭据 | 本地已配置；有效性 NOT RUN，未记录值或认证头 |
| Item 2 Prompt 文件 SHA256 | `b38c2a292577fc3ebcaabeee8f9e463924cc9ed3b41488ac3cc30b634bfd6d8e` |
| 实际加载 Prompt | 请求 system 内容与当前 `CAPABILITY_SYSTEM` 完全一致 |
| 完整 messages canonical UTF-8 | 17,775 bytes，PASS ≤32,768 |
| messages SHA256 | `b911f9af9ef682cea4e82e1c89ba3422d39ff7e5f805f1a4dd964eeb988743aa` |
| 完整 canonical body SHA256 | `630d99817623e3744fa3ca50c319556511c567a11a1181e8210b77aec6c785e1` |
| 新 acceptance / 一次性 request identity | NOT ALLOCATED；授权后新建，不复用184/185或历史 Case 7 |
| 当前价格 / 余额 / 可用账户 | NOT RUN；不把2026-10-09快照当当前事实 |

32 KiB 仅为开发期异常大输入保护，不是 Token 上界或现金数学硬上限。获得授权后，实际序列化消息必须再次检查并绑定同次 identity；本地 capture 不替代请求入账前的检查。真实执行应先保存不可变 body/输入 identity、检查并 fsync 原 append-only 账本预约，再发送同一冻结 wire body。不得运行上轮已经消费的两次请求入口。

## 4. 最新账本与历史保护

只读检查发现 request/result 连续配对1–185，unknown仍为177、183。付费账本 JSON 文件383个，清单 SHA256 `9f796b705ada8858b224fe039e16f3b7d4cc86116d1163a8df5d950aa1128c72`；搜索账本 JSON 文件12个，清单 SHA256 `f6a2829b1c4557a3cd2f320ee2f2d54a67f07303420cb0103f2bab5ed5bcad2a`。清单采用按文件名排序的 `name SHA256\n` 拼接后哈希。

本轮模型、元数据、搜索、Reader、正文请求均0；未追加 authorization、request 或 result。历史184/185响应、unknown、账本及 `.env` 保留字节哈希。旧280累计容量不等于本次可派发权限。

## 5. 获得授权后的单次结果判定

| 层次 / 返回 | 判定与停止条件 |
|---|---|
| Provider | HTTP、实际 response model、finishReason、可信整数 usage 必须核对；unknown、截断、不可信 usage 或异常立即 STOP，不换身份重派 |
| CapabilityPlan | 原 Validator 严格验证原 JSON：Policy refs、前置、MCP来源、需求覆盖、claim_bindings、constraint_effects、disposition/project_usage 一致及 plan_hash；不补字段、不改响应 |
| CapabilityPlanningPending | 与合法 Plan、Provider failure 分开保存（dataclass 完整字段）；程序合法不等于该 pending 语义合理，独立审查实际冲突依据；无 Plan 时没有 plan_hash |
| Validator FAIL | 保存第一拒绝字段和必要离线诊断，保留原响应，STOP，不逐字段追绿 |
| 独立语义 | 开发审查代理读取原 Goal、原 Profile 和新实际响应逐项判断；程序 PASS 不能代替语义 PASS |

独立语义预期：Python accepted_known且不复习/测试；structured.output、tool.calling符合目标；llm.api及辅助能力有实际必要性；系统性 Agent 的 MCP 学习 required但最终 CLI 不强制集成；现有 CLI/JSON保留且不重建；工具范围不是能力禁用；背景不自动导致完整json.cli学习或掌握结论；applied/learn不是明确技术目标；不扩展固定路线。一次成功只证明本次 Scenario A。

原场景不存在已确认的能力排除冲突；若模型返回 pending，必须审查其理由，不能仅因为返回类型合法就宣布业务通过。合法 pending、无依据 pending、程序错误分别记录。

无论响应 PASS、FAIL 或 pending，均只有一次请求并立即结束；双层 PASS仅冻结本次 Plan，不进入 Coverage、Research或Curriculum。

## 6. 与185失败的差异及课程限制

第185次原响应仍保留：Provider成功、Validator首拒 `definition_refs`、项目载体与工具范围被错误当作project排除、MCP归因/元数据技术目标和部分requirement覆盖错误。本轮没有新响应，因此没有证据证明这些真实语义缺陷已关闭。

最新 Prompt明确逐能力精确复制Policy定义引用/前置、特殊MCP政策由服务端处理、区分实际排除与实践条件、区分技术目标与规划条件、避免由JSON项目机械增加能力。上轮117项定向回归、20项修复测试、Ruff及独立审查PASS在源码未变时复用，不重复执行。合成 witness只证明合法映射可表达。

`existing_carrier` 识别不等于最终课程已复用项目；`local_tool_scope` 的not_applicable不等于实际权限已验证。后续缺乏可信项目载体或工具权限满足证据时，Curriculum继续pending/incomplete。本次Item2即使双层PASS，也不能声称教材、课程、Draft或端到端完整通过。

## 7. 执行证据和下一步

本轮运行：`.venv/Scripts/python.exe var/planning-v2-item2-real-retest-20261010/prepare.py`，exit0，本地冻结及 MockTransport请求截获 PASS。启动器存在旧Python路径提示，但实际脚本正常退出；未操作受保护目录。证据为 `baseline.json`、`goal.json`、`profile.json`、`item2.offline-request.json` 和原历史证据。没有生成新模型响应、usage、费用或Plan hash。

| 验收项目 | 状态 |
|---|---|
| 原184真实Profile重建/全文/hash/来源一致 | PASS |
| 最新配置、Prompt、Provider preflight及32 KiB请求构造 | PASS（本地） |
| 185失败修复的既有定向回归与独审 | PASS（复用） |
| 本次真实价格/余额、真实Item2、程序验收 | NOT RUN |
| 本次真实独立语义审查、usage及费用估算 | NOT RUN |
| 全量Backend、PG、React/浏览器、Worker、Item3–7 | NOT RUN |

本轮无生产代码变更。公开generate保护源码未变，沿用原503证据；本轮没有HTTP探测或启用正式生成。正式数据库、历史Receipt、配置、架构合同均未操作；未push/merge/deploy。

下一步需 Owner **单独明确授权**：最多1次新的DeepSeek Item2请求、官方价格/余额GET合计最多2次，4096输出且thinking关闭、实际消息≤32KiB，并接受无严格现金数学硬上限的残余风险。禁止充值、换模型、重试、repair及搜索/Reader/正文/其他模型。本报告没有批准该范围。

**`ITEM2_REAL_SEMANTIC_RETEST_NOT_RUN`**

**`EXTERNAL_AUTHORIZATION_PENDING`**

**STOP。**
