# Planning V2 Item 2 — Policy Outcome Refinement

日期：2026-10-08。本轮只修订能力 outcomes 及必要适用规则，不实现 Item 3 Coverage 或 Reviewed Content Mapping。

## 1. 基线与预期工作树

- Branch：feat/n1-resource-discovery。
- Start HEAD：53c8b0851098d8905722d5867cfae27643672267。
- 开始时 tracked 修改仅 progress，另有未跟踪的 ITEM3_CONTENT_COVERAGE.md；逐项核对 diff 后确认均为用户指出的两份文档。原报告完整保留，progress 只前置追加。既存 .workbuddy/、design-preview/ 未访问、修改或纳入提交。
- 权威：[冻结架构合同](PLANNING_V2_ARCHITECTURE_CONTRACT.md)。上一轮[预检失败报告](ITEM3_CONTENT_COVERAGE.md)仍是原时点事实，没有改成通过或覆盖其失败证据。
- 本地提交消息：fix(planning): refine v2 capability learning outcomes。Final HEAD 为包含本报告的本地提交，可通过 git log -1 --format=%H -- docs/planning-v2/ITEM2_POLICY_OUTCOME_REFINEMENT.md 定位；精确 SHA 同时记录在最终答复及 ignored final.json，避免自包含 commit SHA 问题。
- 主协调请求 gpt-6.1-sol/high；单一生产实现与独立开发审查沿用 gpt-6.1-sol/medium，实际解析 NOT OBSERVABLE。未改全局模型配置或使用额外高档升级。

## 2. 为什么需要新 Policy 版本

v1 每个能力只有一个 outcome，Tool Calling、Agent Loop、MCP 等复合 ID 内包含可能被不同教学章节独立覆盖的任务，单 ID 无法完整划分已覆盖部分和仍缺部分。修订只拆既有教学范围，保持 12 个 capability ID、标题、真实前置、default_depth、A/B 与项目使用语义。

CAPABILITY_POLICY.version=v2；定义及系统性 MCP 规则引用采用 capability-policy:v2。拆分项使用新 ID，旧复合 ID 不被缩义复用，也没有别名自动继承旧审核映射。三个连贯整体目标保持原 ID 和文本。

没有实际 v1 Planning Run 消费者：当前生产引用只在 Capability Policy、Domain Validator 和 application CapabilityPlanner，未接 Worker/公开生成/持久化。历史 v1 报告和冻结证据原样保留；测试新增一份注明来源 commit 的完整 v1 Policy 快照，用于拒绝旧版本输入。未开发双版本 Runtime 注册平台。

## 3. 最终 Outcome 映射

| Capability | v1 outcome | v2 outcomes 与学习目标 | 拆分或保留理由 |
|---|---|---|---|
| python.core | python.core.functions | python.core.program_structure：函数与程序组织；python.core.data_structures：数据结构；python.core.exceptions：异常机制 | 三类基础任务可能分别有教材缺口；通用错误分类不是 Python 异常教学 |
| python.async | python.async.cancellation | python.async.concurrency：协程及并发组织；python.async.cancellation_lifecycle：取消生命周期 | 并发示例不等于取消传播/清理；Agent 终止不能替代协程取消 |
| json.cli | json.cli.io | json.cli.file_reading：JSON 文件读取；json.cli.content_validation：内容校验；json.cli.cli_errors：CLI 错误反馈 | 文件读取、有效性判断和命令行失败反馈可分别缺失；不新增 JSON 写入目标 |
| llm.api | llm.api.request | llm.api.exchange：模型请求与响应；llm.api.usage_cost：用量与费用；llm.api.failure_boundary：模型调用失败边界 | 成功调用、计量和模型请求失败具有独立证据；失败项限定 LLM 场景，不能靠通用分类继承覆盖 |
| structured.output | structured.output.validation | structured.output.contract_definition：输出合同定义；structured.output.response_validation：模型响应校验 | 定义合同与处理不合合同的返回有不同教学产物；工具参数校验不替代模型输出校验 |
| tool.calling | tool.calling.dispatch | tool.calling.input_validation：参数合同及输入校验；tool.calling.invoke_result：有效请求派发并处理结果 | 两个独立行为，演示调用不能证明校验；只懂校验不能证明派发与结果处理 |
| agent.loop | agent.loop.termination | agent.loop.advance：循环推进；agent.loop.stop_conditions：终止条件；agent.loop.failure_result：失败结果返回与处理 | 正常循环、停止控制、失败路径可分别有证据；不增加持久化恢复/多 Agent/高级重试 |
| mcp | mcp.protocol | mcp.roles：Client/Server 职责与协作；mcp.interfaces：Tool/Resource 接口边界；mcp.minimal_connection：最小接入并验证一次工具调用结果 | 理论角色、协议接口和动手接入需要独立教学证据；接口范围明确，不用“等”隐含额外要求；实践适用范围见下节 |
| github.api | github.api.scope | github.api.objects：对象与调用；github.api.pagination：分页；github.api.access_failures：权限及失败边界 | 单页访问示例不证明分页或权限范围；通用分类不替代 GitHub 专属访问语义 |
| code.review | code.review.evidence | code.review.evidence：原完整证据关联任务，原文不变 | 结论、代码定位与依据是一条完整关联，不按名词拆分 |
| error.permission | error.permission.denial | error.permission.denial：原错误/权限/执行失败/未知结果辨别任务，原文不变 | 是一项完整分类辨别任务，不把各类别机械拆成课程 |
| eval.lite | eval.lite.cases | eval.lite.cases：原可检查案例验证任务，原文不变 | 正常与失败案例共同构成验证目标，不单纯为出现 partial 拆分 |

Policy 共 27 个稳定 outcomes，单能力仍可只有一个 outcome。六个候选各做一次有界审查，不因为其他 Capability 有相似术语就删除该场景的教学要求。没有新增 capability、领域词典、层级或评分。

## 4. MCP 理论与最小接入的适用范围

Policy.outcomes_for(definition, *, route_kind, desired_depth) 依据现有字段唯一决定已知 MCP 的冻结集合；同一规则通过 Policy 的 outcome_selection 投影给模型。专用 Prompt 只指明该规则的权威与窄概念范围，不另存第二张选择表。

| 已有 route / capability desired_depth | 冻结的 MCP outcomes |
|---|---|
| systematic_agent_route，任意合法深度 | roles、interfaces、minimal_connection |
| narrow_goal / other，foundation | roles、interfaces |
| narrow_goal / other，applied / deep | roles、interfaces、minimal_connection |
| uncertain | 原有 Pending 澄清路径，不冻结 ready Plan |

系统性路线的最小接入是学习要求，可通过独立、有界练习满足。project_usage=optional/excluded 不删除学习实践，也不要求用户主项目采用 MCP；本轮不生成实际 Practice Task 或 Curriculum。

模型继续根据规范化 Profile 选择既有 route/depth，服务器据这些字段确定性回填 outcomes。是否正确理解“只想了解概念”仍是模型语义责任，本轮 Fake/Mock HTTP 不证明真实模型选择正确。其他能力与未知领域 evidence 定义不受 MCP 过滤规则改变。

## 5. 修改范围、版本与 hash

| 文件 | 本轮职责 |
|---|---|
| backend/app/domain/planning/capability_policy.py | v2 outcomes、版本/ref、最小 MCP 选择规则及输入投影 |
| backend/app/domain/planning/capabilities.py | 最终回填处调用 Policy 的 outcome 选择方法 |
| backend/app/infrastructure/providers/capability_planning_contract.py | 指明 Policy 适用规则及独立教学接入边界 |
| backend/tests/unit/test_capability_policy_refinement.py | 新最小规则/引用/版本/分区/适用边界测试，复用既有 fixture helper |
| backend/tests/fixtures/capability-policy-v1.json | 修订前真实 Policy 的只读测试快照，注明基线 commit；无 Runtime Consumer |
| docs/planning-v2/ITEM3_CONTENT_COVERAGE.md | 原样纳入本次提交，不改其历史失败结论 |
| 本报告 | 修订理由、结果与限制 |
| docs/implementation/progress.md | 前置追加当前结果，保留两轮旧正文 |

Validator 与 Prompt 的小接缝改动在正式修改前已说明：仅静态修改 outcomes 会让所有 MCP 目标被强制应用实践；必须使用现有 route/depth 冻结适用集合。未改 GoalRequirementProfile、CapabilityPlan/Capability dataclass 字段、Schema、A/B、模型调用次数/transport、错误传播或 hash 算法。

新 Policy 版本/内容、实际选择的 outcomes 自然进入 plan_hash；DomainVerificationEvidence.input_hash 继续绑定 Profile+Policy，因此 v1 evidence 不可充当 v2 evidence。source_goal_profile_hash 仍对应原 Profile，不因 Policy 修订改变。旧模型输出 policy_version/v1 refs、完整 v1 Policy 输入和 v1 evidence 绑定均拒绝，不自动升级。

## 6. 验证、独立审查与剩余风险

原始 RED 与后续 GREEN 输出留存在 ignored var/planning-v2-policy-outcomes-20261008/，不覆盖历史失败。

| 验证 | 结果与范围 |
|---|---|
| 生产修改前 RED | FAIL：31 项中 25 FAIL / 6 PASS，errors/skips=0；失败覆盖旧复合 ID、缺失 MCP 选择规则、版本隔离与不可表达部分分区 |
| 新测试 GREEN | PASS：33 项；在原 RED 后补充系统性 MCP 不得降为 recommended、概念/应用冻结 hash 区分两项边界 |
| 最终定向回归 | PASS：113 项，failures/errors/skips=0；新33 + 既有 Domain/Service57 + Item2 Provider23，不累计重复执行次数 |
| 最小 import/collection | PASS：仅上述三份文件共113项，包含所有受影响模块导入；没有运行全量 Backend Collection |
| Ruff | PASS：三个生产文件与一份新测试，完整规则，无新增豁免 |
| git diff --check / 文档链接 | PASS |
| 独立有限 diff 审查 | PASS，无未解决代码 BLOCKER 或架构合同冲突 |
| Domain AST 比较 | PASS：还原唯一 outcome 回填接缝后与基线 AST 等价；Schema、A/B、hash 算法、其他校验没有改变 |
| Prompt 比较 | PASS：除一条 Policy 适用权威指引外与基线一致；共享 adapter/transport 未修改 |
| 保护审计 | PASS：805个其他 tracked 文件、378个账本文件、.env、原 Item3 报告及旧 progress 正文保持 |

最终命令使用 .venv/Scripts/python.exe -m pytest --confcutdir=backend/tests/unit，执行 test_capability_policy_refinement.py、test_capability_planning.py、test_capability_planning_provider.py，-q --junitxml=var/planning-v2-policy-outcomes-20261008/regression-final.xml；collection 仅同三文件使用 --collect-only。未启动真实 PG 或全量 Backend 回归。

首轮统一113 PASS 后，只收紧四条 Policy 文本：角色协作、循环失败处理/明确返回、最小接入一次工具调用结果、Tool/Resource 闭合接口范围；分区测试改为读取实际 Service 冻结 Plan。因受验证输入变化，完成同范围最终113 PASS；原轮输出保留，没有扩大回归范围。

独立审查一次检查六候选及 MCP 设计，再审最终有限 diff；指出 MCP 接口“等”会造成开放审核范围，已消除，没有为通过放宽检查。审查读取 RED/GREEN 与最终回归 XML，未重复运行测试。完整原文在 ignored independent-review.md。

v1 Policy content hash=bda2150013bce875e6d29e9f880e1c98ba22d3bb766564d5f958c31f58656ff2；v2=9893fcdbf393be46b3fd9952aaf16ad00ea3c6c9628f1c1f4dd4a7be622777de。离线样例的窄概念 Plan hash=ad2f238094419727aba76f775e6eb5501c46a316af32c139bb1f537ec378d928，窄应用=8b1cd4752a8e8cb18d0c1c455527b921a9f19c60b9d2f854b13750fea2e7ad9a，系统性 foundation=8125f1a05804f55724efb6516e159b5d70e4ec844af9f6f4350b0ed0d7af14fa；完整输入/对象位于 samples.json，明确标记 OFFLINE_POLICY_SCOPE_FIXTURE_NOT_REAL_SEMANTIC_ACCEPTANCE。

本轮只证明 outcome identity 能支持后续独立覆盖分区，不证明任何真实教材已覆盖，也不实现 CoverageEvaluator、CoverageResult 或 Reviewed Content Mapping。三个重点能力的集合测试仅检查 covered/missing 可完整无交叉地保留部分 ID，不产出产品 Coverage 判断。

产品模型、GitHub/Web 搜索、Reader 新增调用均为 0。真实 PG、浏览器、真实模型语义、在线资料验证、全量 Backend 回归、Item 3 内容映射及实现均 NOT RUN。没有新数据库表/migration/API/Provider/Worker/UI，没有改 Seed、审核资格或学习数据。

public generate 保持 fail-closed：入口、组合根、Worker、前端及其既有验证输入受保护未改；本轮未重复执行公开入口测试，不将历史测试说成本轮执行。未创建 Run/Job/Draft/Plan 或变更业务数据；真实 PG 行计数 NOT RUN。账本仍183/280，unknown177/183保持未重派。回滚仅涉及正常 revert 此本地修订，无数据库迁移或数据恢复步骤。

Item 1 保持 CONDITIONALLY_ACCEPTED；unknown177/183、Case 7 未完成及 Item 2 真实语义待整链验证均不改写。完成仅表示可以重新评审 Item 3 前置接口，不自动宣称 Item 3 已通过或开工。

ITEM2_POLICY_OUTCOME_REFINEMENT_COMPLETE

ITEM3_READY_FOR_PRECHECK_REVIEW

ITEM3_IMPLEMENTATION_NOT_STARTED

STOP。
