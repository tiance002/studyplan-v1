# StudyPlan Scenario A 真实课程连续验收（当前 HEAD）

**最终状态：** `SCENARIO_A_CAPABILITY_PROGRAM_FAIL_STOPPED`

**真实课程验收：** `NOT RUN`；**Owned 产品 E2E：** `NOT RUN`；**公开生成：** 保持关闭。

**决定：** `STOP`，不修补或重派本次失败。

## 执行范围与基线

本轮按 Owner 对新批次的明确授权开始。开始和结束 HEAD 均为 `8131326403372bd2129085a95d4159e3929b1bc1`，分支为 `feat/n1-resource-discovery`。执行验收前 tracked tree clean；执行期间未修改源码。最终仅新增本报告并更新 `docs/implementation/progress.md`；`.workbuddy/` 与 `design-preview/` 仍是原有忽略目录，未读取或修改其内容。

新 Acceptance：`scenario-a-3c9a3e1ad0094b5dbdac39bee0d84df8`。新 Run/root：`run_50aad9f56ce642489bbcafeb03ed9839`，在同一 Run 中先完成 Goal，再执行一次 Capability。没有恢复、覆盖或重用历史失败 Run。冻结 manifest 使用 `planning-v2-product-v2`、`capability-decision-v2`、`research_chapter_v3` 和 `scenario-a-review-v1`。

新 Acceptance 在第一次模型调用前冻结完整 SourceFacts。其持久快照 SHA-256 为 `78d235a221d861fcf869815ed7aeef9467ccf33eda212efc8551a9c8aaf6ade0`，规范来源 hash 为 `32dd42edab1533f6a5d4469b598570c35c5232e1bd042303ea2d59c52a679e5d`。独立冷启动进程读取实际快照内容并得到相同 hash；来源与 manifest 绑定检查通过。新 Acceptance packet SHA 为 `2c43292c8ebd8f278a77ac5b1f88f7befe54cdf1f9e343d200a6709f5d9a8566`，manifest hash 为 `86b749a65351ec2a63b05230edc62d54cb4d2fb6f56229cc4adedc2d9ed9acec`。

使用新创建的 owned 业务库和 checkpoint 库；没有创建正式数据库角色或触碰正式数据库。官方价格与余额预检用尽授权的 2 次 metadata GET。价格依据为[DeepSeek 官方 Flash 价目](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/)：未命中缓存按输入 CNY 2/百万 tokens、输出 CNY 8/百万 tokens估算；价格响应 HTTP 200，正文 hash `5a7b1832592387340f2fc456399b34b89b05f3fa167c2e35909e2fa4afe021e3`。独立价格审查为 **PASS**，审查结果已绑定到本 Acceptance（审查文件 SHA `ac77d4bfaefe08b89fa9f9f02411c201a9955d21a3dd7b5d76ea32cb4e0ded66`）。余额从官方 `GET https://api.deepseek.com/user/balance` 查询，在 `2026-10-10T23:12:28+08:00` 返回 CNY 3.89（响应 body SHA `b443a0ca2bcc1e1aa6fb5ec69ec24591aec008212b08cbbef7344a2fd36ff2e0`）。此余额是查询时点事实，不保证后续余额或整批可用费用；本批仍没有严格人民币数学硬上限，也没有充值。

## 分阶段结果

| 阶段 | 程序结果 | 独立语义结果 | 结论 |
|---|---|---|---|
| SourceFacts、身份、预算与价格门禁 | PASS | 价格审查 PASS | 允许本批派发 |
| Goal Analysis（产品请求 #194） | PASS | PASS | 同一 Run 通过审查并续接 |
| Capability Planning（产品请求 #195） | **FAIL** | **AMBIGUOUS** | Validator 拒绝，Run 失败；停止后续阶段 |
| Coverage / Gap / Research / Reader | NOT RUN | NOT RUN | 未派发 |
| Curriculum / Compiler / Draft / Revision | NOT RUN | NOT RUN | 未派发、未到达 |
| HTTP / React 浏览器读回 | NOT RUN | NOT RUN | 未执行 |

### Goal Analysis（#194）

真实 Provider：`deepseek-flash`，HTTP 200，`finish_reason=stop`，`usage=1239 input / 319 output`，延迟 5,159 ms，单次派发。无重试。Profile hash 为 `2ea320907983106c1f79270b4ecd574c4c1b7c623e03624b6a39bf3345548193`。程序 Validator **PASS**：状态 ready，4 条 required requirements、3 条 hard constraints、1 条 learner claim、无澄清问题。Python 已有基础以 learner claim 保留，没有生成 Python 学习要求；现有本地待办 CLI 与 JSON 文件、持续实践载体和授权范围约束均保留。独立审查者对原始 response body、Profile 与检查点复核后，程序和语义均为 **PASS**。Goal 审查在原 Run 上完成 CAS，随后同一 Run 续接 Capability；未新建第二个 Run。

### Capability Planning（#195）

真实 Provider：`deepseek-flash`，HTTP 200，`finish_reason=stop`，`usage=3694 input / 1798 output`，延迟 15,062 ms，单次派发。原始 response body SHA-256 为 `2d63700d551ec8f5e046b9f1534866221f0f8893e772d993d5d28a457526347d`；Provider 投影 SHA-256 为 `f685a8cbd7d337d98af17687f2f411626f50addba7b1ba18d775e24c34612938`。Profile hash 与上游 Goal 输出一致。

响应中的主要能力选择本身包含 `llm.api`、`structured.output`、`tool.calling`、`agent.loop`、`mcp`；Python claim 映射到 `python.core`，没有把 Python 加入学习能力。MCP 学习为 required、项目使用为 optional。Validator 在 `constraint_effects` 拒绝结果：合同规定 `exclusion="not_applicable"` 时 `capability_id` 必须为 `null`。原响应的两项违反为：

| 路径 | 原始语义 | 原值 | 结果 |
|---|---|---|---|
| `constraint_effects[0]` | 保留现有 CLI/JSON 作为实践载体 | `capability_id="json.cli"`、`exclusion="not_applicable"` | FAIL |
| `constraint_effects[1]` | 不新建演示项目 | `capability_id=null`、`exclusion="not_applicable"` | 通过该字段规则 |
| `constraint_effects[2]` | 工具仅操作用户明确允许的本地范围 | `capability_id="tool.calling"`、`exclusion="not_applicable"` | FAIL |

原 Validator 和 normalizer 未修改。真实未改写响应由验收环境 `.venv` 中的原验证链只读复核，稳定拒绝为 `ValidationAppError(field="constraint_effect")`，运行错误类别为 `capability_plan_invalid`。因此没有 CapabilityPlan、Capability 审查 checkpoint 或可供后续阶段消费的结果。实际 Run 最终为 `failed`；没有继续续接、approve 或建立第二 Run。

独立审查结论为程序 **FAIL**、语义 **AMBIGUOUS**。审查者直接比对真实输入、未修改的原始 response bytes、Provider 投影、Policy 与 Validator。审查认为 Python known 映射、两项学习目标、MCP 的课程与项目使用分离、现有项目没有被替换等局部选择合理；但正面的项目/权限事实被写成无法执行的 `not_applicable + capability_id` 组合，硬约束效果因此未闭合。此外模型返回 `needs_verification`，却没有解释需要核实的未知能力或事实。审查者没有把合法 JSON、部分正确的选择或修改后的合成输出认作语义 PASS。无 Capability review checkpoint 是预期失败传播：Validator 在 review gate 前拒绝，不能伪造 checkpoint。独立结论摘要保存在本地 ignored 证据 `var/planning-v2-scenario-a-r01r05-20261010/independent-review-result-capability_planning.json`，SHA-256 `C0E71FA48149A023A8A888A5DD346348CF61086B688BA638F45445156B4BB998`。

## 调用、预算与账本

- 产品模型：2/9 次；均为一次请求，无重试。输入合计 4,933 tokens，输出合计 2,117 tokens，总计 7,050 tokens。
- 按官方未命中缓存价计算的费用估算：Goal CNY 0.005030，Capability CNY 0.021772，合计 **CNY 0.026802**。这是估算，不是实际扣款证明或数学上限。
- 官方价格/余额 metadata：2/2 次。
- 教材搜索：0/6；正文操作：0/6；HTTP 正文请求：0/12；Reader：0。
- 冻结预算中的 `max_cost_micros=186000` 是既有内部预算单位，不是人民币。未修改该预算。
- 全局模型账本现有 195 对 request/result；本批使用第 194、195 次。历史 unknown 177/183 未重派、未改写。搜索账本保持既有 6/1000，无新请求。
- 本批无 transport unknown、超时、截断或 usage 缺失。Capability 是 Provider 成功返回、应用合同校验失败；不将它归类成网络 unknown。

## 边界与交付状态

本批在 Capability 阶段失败后立即停止。没有触发搜索、正文、Reader、课程生成、课程编译、Draft/Revision、API 或浏览器流程；这些阶段均为 **NOT RUN**，不能据此宣称有真实教材覆盖、完整课程或产品 E2E。没有修改源码、Prompt、Policy、Validator、数据库 schema、正式配置、历史 Run、Receipt 或账本；没有增加 migration；公开 `/plans/generate` 仍保持关闭。未使用的授权次数不自动续到其他 Run，也不据此申请扩额。

审查代理实际解析的模型/effort **NOT OBSERVABLE**。审查只依据本批原始证据和源码；报告不把代理的请求档位当作已核实身份。今后的子代理调用遵守 Owner 最新指示，不使用 `gpt-6.1-sol/xhigh`。

本轮唯一停止原因是真实 Capability 响应的硬约束效果格式不符合现有严格 Validator，且 `needs_verification` 缺少可核实理由。按授权边界保留原 Run 为失败，不修改输出追绿、不 retry、不 repair、不重发。任何后续修复或真实复测都应作为新的 Owner 决策与新 Acceptance 处理。

**结果：** `SCENARIO_A_CAPABILITY_PROGRAM_FAIL_STOPPED` / `CAPABILITY_SEMANTIC_AMBIGUOUS` / `REAL_CURRICULUM_ACCEPTANCE_NOT_COMPLETE` / `OWNED_PRODUCT_E2E_NOT_RUN` / `STOP`
