# Scenario A 连续真实产品验收：Capability 语义 FAIL，STOP

任务：`PLANNING_V2_SCENARIO_A_CONTINUOUS_ACCEPTANCE_V1`。执行日期：2026-10-10。

本批真实 Goal 程序/语义均 PASS；真实 Capability 程序 PASS、独立语义 FAIL。模型将 MCP 的项目使用输出为 `excluded`，而本次验收要求 optional，原始 Goal 也没有排除 MCP 项目使用的限制。原生审查门禁已拒绝该阶段并使同一 Run/Job 结束为 failed。未进入教材研究、Reader、Curriculum、Compiler 或产品课程闭环。

最终状态：`SCENARIO_A_CAPABILITY_SEMANTIC_FAIL` / `REAL_RESOURCE_CURRICULUM_ACCEPTANCE_NOT_RUN` / `SCENARIO_A_OWNED_PRODUCT_E2E_NOT_RUN` / `STOP`。没有达到 `SCENARIO_A_REAL_CURRICULUM_ACCEPTED` 或 `SCENARIO_A_OWNED_PRODUCT_E2E_PASS`。

## 1. 基线、授权与真实业务身份

- 分支：`feat/n1-resource-discovery`。
- Start HEAD 与最终执行源码 HEAD：`9c0cd9a171362e61ec1ae1572764653807b40368`。执行期间 HEAD/全部冻结 tracked 文件保持一致；本报告及 progress 在 STOP 后写入，最终文档 checkpoint SHA 以本次 Git 提交及交付消息为准。
- 开始 tracked tree clean；只有原有 untracked `.workbuddy/`、`design-preview/`，未读取、修改或提交这两个目录。
- Owner 单独明确批准 9 模型（Goal1、Capability1、Reader6、Curriculum1）、搜索6、正文6操作/12HTTP、官方价格余额合计2GET，并接受没有严格人民币数学现金上限的残余风险。禁止 retry/repair/换模型/充值/超额；本批并非现金硬门禁 PASS。
- 新 acceptance：`scenario-a-continuous-cb833a0eb699`。
- 唯一新 Run/root：`run_1c29a4cf8b854ce69f26cdcf7238a70c`；项目 `lpr_1580a0e1dea941c093a19a538700ef30`。
- 新 owned 业务库 `studyplan_test_real_product_714ba0aa`、checkpoint 库 `studyplan_test_real_product_checkpoint_6b781422`。应用既有 migration，未新增 migration、全局角色或修改正式数据库。
- Manifest：`73d3b1046b347b9220d9c91d2a1ad29e73cb6d32498e652facc9304ba7dabc59`，冻结 `planning-v2-product-v2` / `scenario-a-review-v1`。

原始证据仅位于 ignored `var/planning-v2-scenario-a-continuous-20261010/`。两次新请求同时追加到原 `.git/v2-paid-quota-20261001/` 账本；旧记录未重写。报告不包含凭据、认证头或教材全文。

## 2. 来源完整冻结及冷进程实际执行

复用已提交的完整 SourceFacts 冻结/严格解码方案，没有重新实施来源平台或 Runtime。新快照与可信引用在 `build_submission`/manifest 前已 fsync 持久化；Worker 读取同一绝对路径，恢复过程没有重新生成 `created_at`，没有 fallback。

| 事实 | 本批证据 |
| --- | --- |
| 快照路径 | `D:\studyplan\var\planning-v2-scenario-a-continuous-20261010\source-facts.json` |
| 快照版本 | `owned-source-facts-v1` |
| canonical 来源内容大小 | 5684 bytes |
| 字节 SHA-256 | `9cce96e13f880b423fc529cbdb7ee61bd5e92a4e6926c2bcc910bc42d518e268` |
| SourceFacts hash | `c0d9c2b810dc31eb46ba0dc7b9af005b5329ccdbad967e6f95d9f74d6d638540` |
| 独立进程 | 提交前父进程 PID56724、冷进程 PID10144，不同 cwd；实际完整 typed facts/canonical 内容相同 |
| 实际 Worker | 两次独立 tick 都通过 frozen manifest 来源检查，形成真实模型预约及 checkpoint |

新 evidence 目录取消继承后仅 owner SID1001、SYSTEM、Administrators 有访问规则；snapshot/ref 实际继承该规则。只调整新目录，不改旧目录、全局权限或配置。snapshot、ref、preflight、ACL 和 harness hash 均在执行前冻结。这里证明同机 owned 进程可恢复，不宣称多机部署已验证。

`source-preflight.json`、`source-facts-ref.json`、`execution-freeze.json`、`gate-review.json`、`submission.json` 保存完整接线证据。独立审查确认新 harness 仅改新身份/保护清单/严格来源恢复/受控文件绑定；旧 8 项 owned PG、9 项 Mock 门禁和来源修复 48 项 unit+PG 证据直接复用，没有重跑大矩阵。

原失败 Run `run_65b8443b2e6b45ddb38a21c11b687603` 及其两库保持原 reconciliation_required/v2_recovery_blocked 状态。只读全量状态 hash 仍为 `c58e821b2aed95a3bb8c2324c8f8e04cadbccae95239cdf48e304f12d662f351`；未补造旧来源快照、修改旧 manifest 或恢复旧 Run。

## 3. 实际 Provider 与预算准入

授权后仅执行两次官方元数据 GET，均 HTTP200：价格页和 `/user/balance`。本批新核实 `deepseek-flash` 对应 DeepSeek-V4.1-Flash；高峰缓存未命中输入 CNY2/百万 tokens，输出 CNY8/百万 tokens。价格依据：`price-source.json`，官方页面 <https://api-docs.deepseek.com/zh-cn/quick_start/pricing/>；02:56 UTC 的余额读数 CNY3.92、账户 available。余额是预检时点值，没有消费额后再次读取。

实际 Provider 为现有 `openai_compatible` → `https://api.deepseek.com`，请求/响应模型都为 `deepseek-flash`。基础输出4096、Reader1024，`thinking.type=disabled`；未换模型或修改 `.env`。完整 messages 在序列化后、账本预约/HTTP 前检查 ≤32768 UTF-8 bytes，并绑定同次输入 hash。

新 owned manifest 显式冻结搜索6、候选8、正文393216 bytes、Reader6、durable总请求27、输出18432、内部 `cost_micros` 186000。27=9模型+6搜索+12正文HTTP，18432=3×4096+6×1024。该内部预算不是人民币。正式默认预算保持不变；每次真实派发使用原预约、fence、CAS 和 purpose 次数保护。

## 4. 冻结 Scenario A 与真实 Goal

本次 GoalSpec 与原 Scenario A 完全一致，没有把旧184 Profile或187 Plan当作新结果。

```text
target: 我已经会 Python，想系统学习 Agent 的结构化输出与受限工具调用，并把这些能力加入我现有的待办事项 CLI。
scope: 结构化输出；受限工具调用；系统性 Agent 应用学习
starting_point: 已经会 Python。
desired_depth: applied
outcome_purpose: learn
constraints:
  保留现有 CLI 和 JSON 任务文件作为持续实践载体
  不重新创建演示项目
  工具仅操作用户明确允许的本地任务范围
project_context: 我已有一个 Python 本地待办事项管理 CLI，使用 JSON 文件保存任务，希望在现有程序上逐步增加 Agent 能力。
```

Goal hash `39d6309578c3870a67d68c2d49f8d3a3ed34b05a4cd0863bfbc6f9cace65f2d0`。真实第188次响应经原 Validator 得到 ready Profile：

- Profile hash `0d7515fa81ea94170f94725361b3076a14ae44542fb38e55bb8fb57f82ab5282`。
- 五条 explicit requirements：结构化输出、受限工具调用、系统性 Agent 应用、向原 CLI 加入这两类能力、基于已有项目继续实践。
- 三条 hard constraints 原文保留，分别引用 `goal.constraints[0..2]`；Python learner claim 引用 `goal.starting_point`。
- 原 project_context、scope、applied 深度及 learn 用途保持；没有要求新建演示项目或 Python 复习，也没有无必要澄清。

程序 PASS：原响应→Provider→attempt→Validator Profile、来源及确定性 hash 完整一致。独立语义 PASS：逐项对照真实原始目标，未把已有基础误当新增任务、未遗漏硬约束或编造学习目标。

真实 checkpoint 为 goal_analysis/version3。独立 PASS 绑定 review digest `50bffaa4395fca40f70628f134295ce4619713bc555c42335ba18b4edcf1eca1` 后，原生 decide/CAS 将同一 Run/root 继续到 Capability，没有重派 Goal。

原始 request/response/provider 见 `model-188-*`；严格结果及独审见 `review-packet-goal_analysis.json`、`independent-goal_analysis.json`、`decision-goal_analysis.json`。

## 5. 真实 Capability：程序 PASS、语义 FAIL

第189次真实模型实际消费本次新 Profile，经原 CapabilityPlanValidator 形成合法 Plan：

- Plan hash `1acaea6f80c40095bb979843253943363c15f60ce07c75c12a9832e7f3815685`。
- Policy v2；systematic_agent_route；六能力，其中 Python accepted_known，其余五能力 needs_learning。
- 所有 required requirement_refs、policy_refs、prerequisite_refs、claim binding 与 constraint effects 均通过；未修改模型响应或补齐字段。

| 能力 | 本次结果 | 独立语义判断 |
| --- | --- | --- |
| python.core | accepted_known，project optional | PASS；绑定实际已有 Python 声明，不安排基础补学 |
| llm.api | required/applied，project required | PASS；结构化输出及工具调用的冻结前置 |
| structured.output | required/applied，project required | PASS；真实目标及原 CLI 应用引用充分 |
| tool.calling | required/applied，project required | PASS；受限工具目标并非禁用工具 |
| agent.loop | required/applied，project required | PASS；明确系统性 Agent 学习与 CLI 集成可合理支持该能力；未强加持久化恢复或多 Agent |
| mcp | required/foundation，project **excluded** | 学习政策及三个冻结 outcomes 合法；**项目排除语义 FAIL** |

MCP 来源正确地使用 `capability-policy:v2#mcp` 和服务端附加的 systematic-agent-mcp 政策；不是将 learn 用途伪装为用户显式 MCP 目标。三条 constraint_effects 都为 not_applicable/null，正确区分了项目载体/工具权限条件与能力排除，约束仍保留并没有被标记满足。

关键问题仅为 `mcp.project_usage=excluded`：原目标没有禁止原 CLI 采用 MCP，本轮执行要求为项目 optional。`excluded` 在下游有真实行为影响：`curriculum.py` 的 carrier task 校验拒绝引用 excluded 能力，`carrier_allowed` 排除其 outcomes；它比“不强制采用”更强，不能当作 optional 同义词。

独立审查逐项核对原输入、189原始 JSON、实际 normalized Plan 和 checkpoint，判定此偏离足以阻断后续研究。程序 PASS 没有升级为语义 PASS。未执行 Coverage/Gap，因此不把旧184/187的六组 Gap或缺口数量移植成这次新 Run 的实际结果。

Capability review digest `0b9419092be1388e37c34d1edf76b247705c4008f761e50c1d3c773acece611f`。root 写入独立 FAIL 证据后使用原生 `decide(reject)`，Run/Job均 failed、Run version7、`next_action=none`、`error_class=owned_acceptance_rejected`、`result_ref=NULL`。STOP.json 同时阻止本 harness 的后续入口；没有人为制造崩溃、fake checkpoint 或更换身份。

原始证据：`model-189-*`、`tick-2.json`、`review-packet-capability_planning.json`、`independent-capability_planning.json`、`decision-capability_planning.json`、`STOP.json`。

## 6. 实际请求、usage、费用与剩余预约

| 账本 | purpose | HTTP/finish | messages bytes | input/output tokens | Provider latency | 峰值估算CNY |
| --- | --- | --- | --- | --- | --- | --- |
| 188 | Goal Analysis | 200 / stop | 5692 | 1239 / 324 | 1829ms | 0.005070 |
| 189 | Capability Planning | 200 / stop | 18510 | 4560 / 1811 | 5827ms | 0.023608 |
| 合计 | 两次新模型 | 无截断、无 unknown | 均≤32768 | 5799 / 2135 | 两笔合计7656ms | **0.028678** |

费用按新核实的高峰缓存未命中单价计算，没有使用缓存折扣，也不是实际扣款或数学现金硬上限。实际 model total_tokens=7934；usage 是响应中的可信整数并与 Provider 返回相符。

| 外部类别 | 实际 / 本批上限 |
| --- | --- |
| 产品模型 | 2 / 9：Goal1、Capability1、Reader0、Curriculum0 |
| 教材搜索 | 0 / 6 |
| 正文操作 / HTTP | 0 / 6；0 / 12 |
| 官方价格余额元数据 | 2 / 2 |
| retry / repair / 第二 Run | 0 / 0 / 0 |

Durable 两笔预约合计 total_requests2、output_tokens8192、内部 cost_micros40000。相对 manifest 剩余25请求、10240预约输出、内部146000；搜索/Reader/正文预约未使用。账本从187到189，整体 cap280未改变；搜索账仍6。历史 unknown177/183保持，新 unknown0。

未用7次模型以及其他本批额度没有被继续消费，不能当作失败后自动重发、恢复此 failed Run 或新建第二 Run 的许可。

## 7. 验收、持久化与历史保护矩阵

| 项目 | 状态 | 实际边界/证据 |
| --- | --- | --- |
| 冷进程来源冻结及真实 manifest 绑定 | PASS | 两次 Worker 均通过原 hash，真实新预约/checkpoint存在 |
| 新 Goal：程序 / 独立语义 | PASS / PASS | 188原始响应及严格 Profile |
| 新 Capability：程序 / 独立语义 | PASS / FAIL | 189原始响应，MCP project excluded 阻断 |
| 原生审批续接/拒绝 | PASS | 同Run/root；Goal approve、Capability reject，fence/CAS落库 |
| owned PG Run/attempt/checkpoint真实读回 | PASS | 2 succeeded attempts、2 reservations、2 checkpoint rows；Job attempts2；最终 failed |
| Coverage / Gap 实际执行 | NOT RUN | Capability门禁已拒绝 |
| 真实教材资格、正文/Reader、质量比较与跨能力复用 | NOT RUN | 搜索/正文/Reader均0，没有本批教材结论 |
| required / recommended 新缺口解决 | NOT RUN | 新 Coverage/Research 不存在 |
| Curriculum教学语义及 complete/incomplete | NOT RUN | 没有课程模型结果，不能虚报完整或材料不足 |
| Compiler / Draft / 确认 / Revision / current-history | NOT RUN | 新项目 Draft0、Revision0；没有用户或合成确认 |
| React / 浏览器课程读回 | NOT RUN | 未形成合格课程，不重复旧浏览器矩阵 |
| public generate503最小保护 | PASS | 单项 `test_api_boot_and_generation_fail_closed_without_any_storage_access`，pytest exit0；正式入口没有开放 |
| 旧账/unknown/旧失败Run/.env保护 | PASS | 506受保护文件及执行期tracked hash保持；旧失败库全量状态hash不变 |

真实持久化审计为 `final-audit-verified.json`，只读查新旧 owned 库，不冒充完整课程数据库验收。审计脚本第一次查询不存在的 `ai_jobs.max_attempts` 字段失败，随后只修本地只读查询；正文计数核对改为实际 harness 文件命名，最终还核查 durable research.body 预约为0。两次均没有数据库写入、Worker执行或外部请求。原中间 `final-audit.json` 保留，最终以 verified 文件为准。

本轮没有生产源码、Prompt、Schema、Policy、hash、预算默认值、正式配置、migration或前端变更。tracked 交付仅本报告及 progress 前置新增记录；ignored harness只装配新身份/完整来源快照及保护边界。最终收口不重复283项回归、全量Backend/React/PG或旧业务测试。

## 8. 独立审查及下一处最小问题

独立代理 `continuous_acceptance_review` 在独立上下文读取实际 harness diff/严格恢复、原请求与响应、冻结Goal/Policy、真实 checkpoint 和数据库读回。门禁、Goal语义 PASS；Capability明确 FAIL，root通过native拒绝执行。请求开发审查模型为 `gpt-6.1-sol/xhigh`，实际解析值 **NOT OBSERVABLE**，不把角色名当成真实模型身份；没有第二个产品 Reviewer 调用。

下一处最小产品问题是 **MCP项目可选与排除的语义边界**。现有Prompt已说明“不强制采用”与“按真实项目需求决定”，但本次真实模型仍错误缩窄为 excluded。建议下一独立Goal有界核查专用输出说明：没有真实排除依据时，不能把非必用解释为禁止；针对本次原始输入/输出做一组 optional/excluded 反例。是否需要改变权威职责或增加确定性检查须先按合同审议，不能自动补写模型字段或把历史失败升级为 PASS。

本轮遵守关键能力语义错误立即STOP的授权边界，未修Prompt追绿、未再调用模型、未开启第二Run。当前真实教材/课程质量仍未验证，不推断其一定可闭合，也不将此前旧Plan成功扩大为本次成功。未push、merge、deploy，公开generate保持关闭；本地文档checkpoint后STOP，下一阶段由Owner决定。
