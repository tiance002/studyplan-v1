# Planning V2 Scenario A 真实 Item 1–2 语义验收

任务：`PLANNING_V2_SCENARIO_A_REAL_SEMANTIC_V1`。执行日期：2026-10-09，北京时间。

**结果：Item 1 程序 PASS、独立真实语义 PASS；Item 2 程序 FAIL、独立真实语义 FAIL。整批验收 FAIL，已 STOP。** 没有合法 CapabilityPlan 或 Plan hash，不重试、不 repair、不进入教材研究。

## 基线与授权

- Start/source HEAD：`1fdd5d4e845b22e74e4168399e9ca14ec070bd3d`，branch `feat/n1-resource-discovery`，与请求一致。
- 开始 tracked tree clean；仅有既存 `.workbuddy/`、`design-preview/` untracked，未操作。
- Final HEAD 为本报告所属本地文档 checkpoint，`checkpoint-planning-v2-scenario-a-real-semantic-20261009^{commit}` 可精确解析；SHA 同时记录于 ignored `delivery-receipt.json`。
- 复用 [本地准备](PLANNING_V2_REAL_SEMANTIC_SMOKE.md)、[约束作用域修复](ITEM2_CONSTRAINT_SCOPE_FIX.md) 及其 123 PASS／独审／历史保护证据，不重复离线回归。
- 初始请求本身不授权外部调用；随后 Owner **明确单独授权** Item 1／2 各一次新 `deepseek-flash`、合计两次官方价格／余额读取、4096 output／非思考／32 KiB 防异常大输入，并接受无严格数学现金硬上限的残余风险。
- 本轮没有更改冻结架构、Policy、Prompt、Schema、Provider 或正式配置。所有调用使用本地 ignored 独立入口，不启动 Worker，也不调用 Coverage、Research、Reader、Curriculum、领域验证或其他产品模型。

## 冻结输入

沿用前置报告原 Scenario A，与既存 `scenario-a.goal.json` 逐字段一致；不是历史 Case 7 的重新派发。

```json
{
  "target": "我已经会 Python，想系统学习 Agent 的结构化输出与受限工具调用，并把这些能力加入我现有的待办事项 CLI。",
  "starting_point": "已经会 Python。",
  "scope": ["结构化输出", "受限工具调用", "系统性 Agent 应用学习"],
  "desired_depth": "applied",
  "outcome_purpose": "learn",
  "constraints": ["保留现有 CLI 和 JSON 任务文件作为持续实践载体", "不重新创建演示项目", "工具仅操作用户明确允许的本地任务范围"],
  "project_context": "我已有一个 Python 本地待办事项管理 CLI，使用 JSON 文件保存任务，希望在现有程序上逐步增加 Agent 能力。"
}
```

## 实时 preflight、身份与费用

官方元数据 **2/2**，无跳转、重试或额外 GET：

1. [DeepSeek 当前模型价格](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/)：HTTP 200；官方模型名 `deepseek-flash`，页面版本 DeepSeek-V4.1-Flash。CNY／百万 tokens：缓存未命中输入高峰 2、空闲 1，输出高峰 8、空闲 4。实时页面文本/hash 保存为 `price.txt`、`price-source.json`。
2. 官方 `/user/balance`：HTTP 200，`is_available=true`；2026-10-09 15:04:15 UTC 可用余额 **CNY 1.96**。认证信息不入证据。没有再请求执行后余额。

Provider 白名单、现有凭据配置、公共 HTTPS endpoint guard、实际两 purpose 的 `request_options` 已核对；每次请求均 `model=deepseek-flash`、`max_tokens=4096`、`thinking.type=disabled`、JSON mode。响应原始 envelope 的 model 与 finish_reason 均显式核对，不使用 Provider 缺字段默认回填作为证据。

费用按实际可信 usage × **当前高峰缓存未命中价格**估算，不使用缓存折扣，也不把 `cost_micros=None` 当费用 0。派发均在空闲时段，该估算有意使用更高价格；账单实际扣款 NOT RUN。32 KiB 仅限制输入数据大小，没有证明 token 或现金数学硬上界。Owner 的风险接受不构成现金硬门禁 PASS。

新独立 acceptance：`scenario-a-real-5cf165c5a344`，仅为外部测试身份，不创建业务 Planning Run。

| 项目 | Item 1 | Item 2 |
|---|---|---|
| Ledger 请求号 | 184 | 185 |
| Attempt identity | `scenario-a-real-5cf165c5a344:item1:1` | `scenario-a-real-5cf165c5a344:item2:1` |
| Purpose | `planning.goal_requirement_analysis` | `planning.capability_planning` |
| 请求与响应模型 | deepseek-flash | deepseek-flash |
| HTTP / finishReason | 200 / stop | 200 / stop |
| 完整 messages JSON UTF-8 | 5,692 bytes | 14,238 bytes |
| 输入 / 输出 tokens | 1,239 / 522 | 3,710 / 2,064 |
| Provider latency | 3,104 ms | 6,347 ms |
| 应用 wall time | 3,243 ms | 6,490 ms |
| 高峰价费用估算 CNY | 0.006654 | 0.023932 |
| Provider JSON 结果 | 明确 LLMResult | 明确 LLMResult |
| Domain 程序验收 | PASS / ready Profile | FAIL / capability_plan_invalid |
| 独立真实语义 | PASS | FAIL |

总计 **2/2 模型请求**，输入 **4,949**、输出 **2,586**、合计 **7,535 tokens**；高峰无缓存折扣估算 **CNY 0.030586**。无本批 unknown、截断或 usage 缺失；历史 unknown177／183 原样保留。

## 派发与来源门禁的实际执行

Ignored `entry.py` 复用真实 `GoalRequirementAnalyzer / CapabilityPlanner → OpenAICompatibleLLM`，HTTP 客户端只增加本批派发记录、防护和原始响应保存，实际发送官方请求；没有 Fake 返回。

每次实际 body 构造后，验证完整 system/user 消息文本结构及 UTF-8 JSON 大小 ≤32,768；冻结整份 canonical wire bytes，绑定 messages／body／Goal／实际输入 Profile／价格快照 hash，随后 exclusive-create、fsync append-only request，最后发送**同一份已绑定 bytes**。不是用旧离线尺寸放行新输入。无自动裁剪、repair 或重试；每个 Item 的 exclusive start marker 阻止复执行。

S2 等待 S1 独立语义 PASS 文件落盘后才执行：原 HTTP response `choices[0].message.content` 与保留的 provider payload 相同；由其重建的 Profile 全文和 hash 同时等于 S1 输出及独审记录。S2 请求内真实 Profile 与该对象一致，没有使用此前合成 fixture。

原 usage 的 prompt/completion/total 为非负整数，合计一致、completion ≤4096，且与 Provider typed tokens 一致。finishReason 原值为 stop；模型原值 deepseek-flash。账本先请求后 HTTP，失败结果和费用估算也保留；unknown 将标记 reconciliation 并停止，不能重派。

两次 request body SHA-256：

- Item 1：`1fefc184724df362b7257e7c217f9fa59cc160234869feb7b1e148cd5baa9d23`。
- Item 2：`1a2d6623cdafe626a15141204654e212a8f2dbc0c82e8ca838f813a0add81da1`。

## S1：真实 Profile 与独立审查

实际 Profile `status=ready`；原响应重新通过 Validator 后全文相等，source_refs／ID／hash 重建 PASS。

Profile hash：`b0386820c14a6aa2b9aa9b1df1aeb1ddc6b5e8925df0a8ec6f70d66dd09f7348`。

真实输出概要：

- target_summary：在已会 Python 的基础上，系统学习 Agent 的结构化输出与受限工具调用，并将能力加入现有待办事项 CLI。
- learner_claims：`已经会 Python。`，引用 `goal.starting_point`；没有转成 Python 学习／复习要求。
- 三条 hard_constraints 原文逐条保留，来源分别为 `goal.constraints[0]`、`[1]`、`[2]`。
- 原 project_context 全文不变，项目背景引用为合法 `project_context`。
- explicit requirements 保留结构化输出、受限工具调用、原 CLI 持续实践，并含项目背景、应用深度及 learn 用途事实；来源有效。
- 无澄清问题、无新项目要求、无无依据新技术要求。

独立审查 **PASS**。深度与用途同时列在 requirements 中是冗余事实，但没有产生额外课程，不构成本轮关键语义失败。原始模型没有自己充当裁判。

完整原始 response、模型 JSON 与最终 Profile 分别在 `item1.response.body`、`item1.provider.json`、`item1.json`；独审在 `review-item1.json/md`，绑定原响应 SHA 和 Profile hash。

## S2：真实返回与失败原因

实际返回的是候选 JSON，**没有通过 Validator，没有冻结 CapabilityPlan，也没有合法 plan_hash 或最终 learning_outcomes**。不要将以下局部正确决策宣称为完整能力规划通过。

| 模型候选能力 | disposition | learning_requirement | project_usage |
|---|---|---|---|
| python.core | accepted_known | recommended | required |
| json.cli | needs_learning | recommended | required |
| llm.api | needs_learning | required | required |
| structured.output | needs_learning | required | required |
| tool.calling | needs_learning | required | required |
| agent.loop | needs_learning | required | required |
| error.permission | needs_learning | required | required |
| eval.lite | needs_learning | recommended | required |
| mcp | needs_learning | required | optional |

route 为 `systematic_agent_route`，引用真实 Profile hash；Python claim 正确绑定 accepted_known，结构化输出／工具调用／LLM 先修及 MCP 学习 required、项目 optional 有局部正确判断。

**程序失败：**原输出未经任何修改，离线复现真实 Validator 的首个拒绝为 `ValidationAppError.details.field = definition_refs`。`json.cli`、`llm.api`、`structured.output`、`tool.calling`、`agent.loop`、`error.permission`、`eval.lite` 共 **7** 个已知能力的 `policy_refs=[]`，不等于冻结定义要求的 `capability-policy:v2#<capability_id>`。这是既有合同正确拒绝，不放宽 Validator。

**独立语义 FAIL：**

1. “保留 CLI／JSON 持续载体”被映射为 `json.cli` 的 `exclusion=project`；它实际表示保留使用，不是排除该项目能力。
2. “工具仅操作允许的本地任务范围”被映射为 `tool.calling` 的 `exclusion=project`；范围限制不等于排除整个工具调用。两项能力又同时 `project_usage=required`，形成直接矛盾。
3. MCP 虽选为学习 required／项目 optional，却把 `outcome_purpose=learn` 的 requirement 当作明确 MCP 学习目标引用；系统性 MCP 应由课程政策提供理由，普通 learn 用途不能独立推出特定技术目标。
4. 应用深度 requirement 没有被任何 capability 引用。原样静态清点记录此覆盖缺口；首拒在更早的 definition_refs，未通过修补输出逐层追绿。

JSON 解析、明确服务响应、输入来源绑定、size 与 usage 检查均 PASS；最终 Domain Validator／语义分别 FAIL。Profile→真实请求的来源绑定是正确的，失败来自模型实际返回。实际分类是 `capability_plan_invalid`、`dispatch_unknown=false`；不是 timeout、unknown 或未派发。

完整证据：`item2.response.body`、`item2.provider.json`、`item2.json`、`item2.validator-diagnosis.json`、`review-item2.json/md`、`STOP.json`。未改写或“修好”历史输出，不再派发请求。

## 独立审查、修改及保护

独立代理实际读取源码、入口、原始响应与冻结输入，逐笔判断，S1 PASS 才让 S2 继续。请求开发模型 `gpt-6.1-sol/xhigh`；实际模型解析 **NOT OBSERVABLE**，没有修改全局配置；开发代理与被测 DeepSeek 是分离裁判。

派发前独审发现两个 ignored harness 接缝并关闭：S2 原始响应／Profile 全文 hash 绑定，以及原 model／finishReason 缺失时不能使用 Provider 默认值背书；根协调者另纠正 CapabilityPlan 无 status 字段的本地入口检查。全部修正发生在模型请求 0 时，冻结源码 hash 为 `ad0bb3d2d5cd54d21d8faf8e8ac08298c665283beade0a89ebcf09b2f8015464`，执行时不变。它们不是生产代码修改或修补模型输出。

tracked 修改只有本报告及 progress 前置记录；原历史字节保留。本地原始证据目录：`var/planning-v2-scenario-a-real-20261009/`，不含凭据、认证头或教材全文。账本新文件仅授权记录和 request/result184、185；旧 request/result／unknown／授权记录、`.env`、源码和搜索账本 hash 保持。

模型累计 **183 →185 /280**，当前可算术余量 95，但本批 2 次已全部使用，**不自动授权继续**。未知仍仅历史177／183；搜索保持 6/1000，没有本批新增。

| 未运行／边界 | 结果 |
|---|---|
| Tavily／GitHub教材搜索、Reader、教材正文、领域验证及其他产品模型 | 0 请求 |
| 完整 Worker、Coverage、Research、Curriculum、教材资格与端到端教学质量 | NOT RUN |
| 真实 PG、正式库行数、React／浏览器、全量 Backend 回归 | NOT RUN |
| 新 Planning Run／Job、Draft／Revision 或数据库写入 | 无业务入口调用，不创建、不修改；正式行数未冒称核验 |
| 正式公开 generate | 保持既有 503；源码／配置无变化，复用有效边界证据，没有开放 |
| 真实现金数学硬门禁／实际扣款 | NOT RUN／未证明；只是 Owner 接受风险的开发测试 |
| 新 migration、push、merge、deploy | 0 |

## 最小下一步与 STOP

只建议另一个有界离线任务审查 Item 2 专用 Prompt／实际 wire 合同：明确 known capability 必须引用 Policy，区分约束“满足方式”与真正 exclusion，正确引用系统性 MCP 政策，并保证所有冻结 requirements 来源覆盖。先针对本次原始失败写 RED，再做最小修复与独审；不改 Schema／Policy／Validator 追绿。`json.cli` 的新增学习是否必要也应在此证据内有界审查，不能仅由已有项目背景自动推出必须再学完整 CLI。

本轮不实施这些建议、不增加调用、不进入收费教材研究。未来真实复测需要新明确授权，不复用本批或历史身份；本次失败原样保留。

**Scenario A Item 1–2 整体：FAIL。**

`ITEM1_REAL_SEMANTIC_PASS`

`ITEM2_PROGRAM_FAIL`

`ITEM2_REAL_SEMANTIC_FAIL`

`PLANNING_V2_SCENARIO_A_REAL_SEMANTIC_FAIL`

`REAL_FULL_PRODUCT_ACCEPTANCE_NOT_RUN`

STOP。
