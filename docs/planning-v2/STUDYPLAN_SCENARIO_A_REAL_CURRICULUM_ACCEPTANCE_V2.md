# StudyPlan Scenario A 真实课程连续验收 V2

**最终状态：** `SCENARIO_A_REAL_CURRICULUM_ACCEPTANCE_FAIL`
**产品闭环：** `SCENARIO_A_OWNED_PRODUCT_E2E_NOT_RUN`
**停止阶段：** Item 2 Capability Planning；未重试、未修复响应、未创建第二 Run。

本批完成了派发前门禁，并在同一个新 acceptance / Run 中执行了 Goal Analysis 与 Capability Planning。Goal Analysis 的程序和独立语义验收通过。Capability Planning 返回完整、已计量的响应，但原始结果未通过严格 `CapabilityPlanValidator`，因此没有有效 CapabilityPlan，也没有进入 Coverage、Gap、资料研究或后续课程流程。

## 1. 基线与冻结身份

- 开始与结束 HEAD：`0fd5123e5e780b7c5d1e37ceaf39911e18350b64`
- 分支：`feat/n1-resource-discovery`
- 执行前 tracked 工作树干净；既有未跟踪 `.workbuddy/` 和 `design-preview/` 保持原样。本次没有源码或配置修改；仅新增本报告。未 push、merge、deploy。
- 新 acceptance：`scenario-a-aa45a90ff4ff4642bdf8a0688a00880e`
- 新 Run：`run_d4003937c7df4486832542f79f153050`
- 最终 Run/Job：`failed / failed`，`error_class=capability_plan_invalid`，`next_action=none`。原失败 Run 与历史账本未恢复或改写。
- 语义版本：`planning-v2-product-v2`
- W5 解码辅助代码冻结 SHA-256：`c2f4b97944f2fcc208dfc119a669205180e0cf76b12ba570296e145a53ae748b`
- Prepared packet：`ffa30de12d6438103dbf1d8df5514ccc7f99585735ce538c26d3d7e01e5ccb9c`
- Manifest：`f44eac8759387befd6ea19671d405a44b8409d744b10c49893d18092e15b275b`
- SourceFacts：`1343d6c4666d4d0b2ac7b194256b8f676223bc764f393bc261f733d24d874214`
- 完整 SourceFacts 冻结快照 SHA-256：`43019dfab0b2920f09006a26e04ee209497f319ced6ec8b38359b33ab8915bd7`。独立冷进程读取、解码和 manifest 来源绑定检查 **PASS**；Worker 未在恢复时重建 `created_at`。
- 在两个新隔离 owned PostgreSQL 数据库中执行；未连接正式库。业务库 schema 使用现有 Alembic head `0025`，未新增 migration。synthetic actor/project/session 只在 owned 库创建。

冻结预算：模型最多 9 次、搜索 6 次、正文 6 次操作 / 最多 12 次 HTTP、输出 token 上限 18,432、durable 外部请求 27、正文预约 393,216 bytes、内部预算 `186000 cost_micros`。本批不改变正式默认值。

## 2. 价格、余额及独立价格审查

派发前在获准的 2 次元数据 GET 内完成官方价格及余额核对：DeepSeek `deepseek-flash` cache-miss 输入价格 CNY 2 / 百万 tokens，输出价格 CNY 8 / 百万 tokens；账户返回可用余额 CNY 3.90。独立价格审查 **PASS**，证据 [independent-price-review.json](../../var/planning-v2-scenario-a-curriculum-v2-20261010/acceptance-final/independent-price-review.json)，SHA-256 `00168d3bd7b4973882508bdc697648631c63e105dbd41e49ab55178eee56dede`。

这批仍不存在严格的人民币数学现金硬上限；费用均为按实际 usage 和已核实公开价格计算的估算，不代表实际扣款。未在调用后再次读取余额，因为 2 次官方元数据额度已经用完。独立审查者的实际模型解析为 **NOT OBSERVABLE**。

## 3. 真实请求与账本

两次调用均使用 `deepseek-flash`、`max_tokens=4096`、`thinking.type=disabled`。每次完整序列化消息都低于 32 KiB。W5 原始响应记录、解码记录、Provider 结果与 append-only 全局额度账本身份相互绑定。历史全局模型账本从 191 增至 193；未重用旧 request/attempt 身份。

| 全局序号 / 阶段 | Attempt ID | 请求 SHA-256 | 解码响应 SHA-256 | HTTP / finish / 状态 | UTF-8 消息大小 | Usage（input / output / total） | 延迟 | 估算费用 |
|---|---|---|---|---|---:|---:|---:|---:|
| 192 / Goal Analysis | `run_d4003937c7df4486832542f79f153050:v2:goal-analysis:9a5d74e658e6f0566b54f7a2` | `7b476715bcf047083da6c2054488a235a0dd08e6f099fc5cdbcc93c62ad976d8` | `5be7928f30c3d6799bd449982b30bf1d12357509af5bf924e80c77ad53a0bec8` | 200 / `stop` / complete, known success | 5,692 bytes | 1,239 / 393 / 1,632 | 3,894 ms | CNY 0.005622 |
| 193 / Capability Planning | `run_d4003937c7df4486832542f79f153050:v2:capability-planning:7c579faf5a0e3270f0daf24d` | `a446e1961c1928b06d506a03ec83743cd8dee189f2bd35be5839c342ae3237a9` | `cff138e9601d96576648b9e85f2c6a58843c4f9eba52c131136fd5d52f8ed5d9` | 200 / `stop` / complete, known success | 18,706 bytes | 4,559 / 1,303 / 5,862 | 6,526 ms | CNY 0.019542 |

本批共 2 / 9 次产品模型请求，合计 input 5,798、output 1,696、total 7,494 tokens；估算费用合计 CNY 0.025164。请求 192 与 193 的 append-only 结果分别见 `.git/v2-paid-quota-20261001/result-192.json`（SHA-256 `dde10c005f78255625108fcbd7fddb288bd87785e341e8536604b7bbf794bae8`）和 `result-193.json`（SHA-256 `a1381ca775e2c9f920afdcea32a34f60b0dae49c1c6fef2d87b1714f20848969`）。两份记录的 usage、`finish_reason=stop`、HTTP 200、`response_complete=true` 与 `unknown=false` 均与 Provider 原始审计记录一致。PG attempt 行的规范化 `input_tokens` 列为空，但其摘要绑定的 `response_payload.value.input_tokens` 保存了相同用量；全局额度账本也保存了相同 usage。Provider 报告的 `cost_micros` 为空，费用估算保存在独立调用账本中。

| 外部操作 | 使用量 | 本批上限 | 状态 |
|---|---:|---:|---|
| 官方价格 / 余额元数据 GET | 2 | 2 | PASS |
| DeepSeek 产品模型 | 2 | 9 | PASS；第二阶段业务结果 FAIL |
| 教材搜索 | 0 | 6 | NOT RUN |
| 正文操作 / HTTP | 0 / 0 | 6 / 12 | NOT RUN |
| Reader / Curriculum 模型 | 0 | 已包含在 9 次内 | NOT RUN |
| 自动重试、repair、换模型、充值 | 0 | 0 | PASS |

## 4. Goal Analysis

- **程序合同：PASS。** 原始 Goal 响应通过既有 `GoalRequirementProfileValidator`；Profile 为 `ready`，有 4 条 required requirements、3 条 hard constraints、1 条 learner claim、0 条澄清问题。Profile hash `71ffa724242a6ceea352eb701671ee361ad692c7325926fe2f14f3158b5203e6` 与 checkpoint 完全一致。
- **独立语义：PASS。** [independent-goal_analysis.json](../../var/planning-v2-scenario-a-curriculum-v2-20261010/acceptance-final/independent-goal_analysis.json)，SHA-256 `08cda58363e1c62746caf8a543c26be6a3418e77e5ac88ab1cd989301714246b`，绑定 acceptance、packet、Run、review digest 与 checkpoint hash。审查确认 Python 仅保留为学习者声明；原待办 CLI / JSON 项目、三条约束、应用深度和 learn 用途均保留，没有安排 Python 基础复习或额外扩课。

## 5. Capability Planning

真实响应为完整 HTTP 成功，但未形成合法 CapabilityPlan。原始 JSON 的能力集合是 `llm.api`、`structured.output`、`tool.calling`、`mcp`；`structured.output` 和 `tool.calling` 声明 `llm.api` 前置；MCP 标记为 required 学习、optional 项目使用；三条 constraint effects 均为 `not_applicable`。模型将 Python learner claim 绑定到 `python.core`，但 `capabilities` 中没有对应的 `python.core` / `accepted_known` 项。

- **程序合同：FAIL。** 使用冻结 Goal Profile 与原始第 193 次模型输出离线重放原 Validator，精确拒绝字段为 `claim_binding`：claim binding 的能力 ID 不存在于输出能力集合。Worker 保存 `error_class=capability_plan_invalid`，Run 与 Job 均进入 `failed`；没有 `CapabilityPlan`、plan hash 或 Capability review checkpoint。没有补字段、修改模型响应、放宽 Validator 或再次派发。
- **独立语义：AMBIGUOUS。** 独立审查认为四项新学习能力、`llm.api` 前置、MCP 学习/项目使用区分和三条约束作用域均有语义依据；但由于缺少 `python.core` 的正式能力行，无法证明该已知能力实际成为 `accepted_known`。因此整体不标语义 PASS。独立审查记录 [independent-capability_planning.json](../../var/planning-v2-scenario-a-curriculum-v2-20261010/acceptance-final/independent-capability_planning.json)，SHA-256 `b1f22516b93f842c643471bc24ff4518fed56e069aab200547ae40f1a6b476ec`，绑定本 acceptance、Run、attempt、raw response SHA 和 Profile hash，并明确 `gate_approval=false`、`usable_by_runner_decide=false`。

Capability 格式缺陷是本次真实响应的确定失败；其不是压缩解码、transport unknown 或 usage 缺失。第 193 次是已知成功响应，未重派。

## 6. 后续阶段与产品闭环

由于 Capability Planning 失败且未生成有效冻结计划，以下阶段均 **NOT RUN**：

- Coverage / Resource Gap；
- GitHub / Web 教材搜索及 Reader 正文审读；
- Curriculum Composition、独立课程语义评审；
- Compiler、Draft 创建、Revision / current / history 读回；
- HTTP / React 浏览器验收。

本次只创建了失败的 owned Run / Job 和其调用回执；没有创建 Draft、Plan Revision 或正式学习计划。公开 `/plans/generate` 未启动，正式生成保持未开放；无 migration、无正式数据库修改。没有调用 Tavily、GitHub 搜索、Reader、正文端口或其他模型。

## 7. 结论与最小后续事项

本批未达到真实课程验收。最小已证实问题是模型遗漏了 learner claim 所绑定的 `python.core` 能力项，导致原 Validator 在 `claim_binding` 拒绝整份计划。可在新的离线工作中检查 Item 2 专用契约是否清楚要求：每条已有基础 claim 都要绑定到能力集合中的合法 `accepted_known` 项，且不要为此安排学习任务。任何新的真实请求或新 Run 都需要 Owner 另行决定；本批不重试、不 repair、不继续消费剩余 7 次请求额度。

**状态：** `SCENARIO_A_REAL_CURRICULUM_ACCEPTANCE_FAIL`
**Draft / React 闭环：** `NOT RUN`
**停止：** 本报告完成后 STOP；不自动进入 Item 3–7 或另开 acceptance。
