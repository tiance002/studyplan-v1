# Planning V2 Item 2 — Capability Planning

日期：2026-10-08。结论：PLANNING_V2_ITEM2_CAPABILITY_PLANNING_COMPLETE。仅完成离线 Domain / Service / Provider 合同与验证；未完成整条 Planning V2 产品接线或真实语义验收。

## 1. 基线、授权与交付身份

- Branch：feat/n1-resource-discovery。
- Start HEAD：18ff5cca095e5a2037ab1742d0bfcfb275adc2c2，与用户预期一致；开始时 tracked tree clean。既有未跟踪 .workbuddy/、design-preview/ 未访问或修改。
- Final HEAD：包含本报告的本地提交，消息为 feat(planning): add v2 capability planning。可用 git log -1 --format=%H -- docs/planning-v2/ITEM2_CAPABILITY_PLANNING.md 定位；提交后的精确 SHA 同时记录在最终答复与 ignored evidence 的 final.json，避免在报告自身嵌入不可能自包含的 commit hash。
- 权威：[冻结架构合同](PLANNING_V2_ARCHITECTURE_CONTRACT.md)。本轮未修改合同，未发现需要改合同的 BLOCKER。
- Item 1 仅按本轮用户授权为 ITEM1_CONDITIONALLY_ACCEPTED。[Case 7 最终真实复测](ITEM1_CASE7_FINAL_SEMANTIC_RETEST.md) 的 unknown183、历史 unknown177、Case 7 真实验收未完成及 Item 1 完整端到端未验收均保留；未改写旧报告或标记完整 PASS。
- 产品模型 / 搜索 / Reader 授权与实际新增请求均为 0；本轮不使用剩余额度，不重派历史 unknown。未 push、merge、deploy，未进入 Item 3。
- 开发主协调请求 gpt-6.1-sol/high；有界实现与独立审查请求 gpt-6.1-sol/medium，实际解析均 NOT OBSERVABLE。未修改全局模型配置，未使用 Sol max / Astra 或进行 HARD 升级。

## 2. 修改文件及职责

正式修改前已限定下列九文件，没有扩大到 Item 1、组合根、数据库或前端。

| 文件 | 职责 |
|---|---|
| [capability_policy.py](../../backend/app/domain/planning/capability_policy.py) | 小型、冻结、版本化定义及产品 MCP 政策 |
| [capabilities.py](../../backend/app/domain/planning/capabilities.py) | Plan/Pending、输入与输出机械校验、证据绑定、引用、DAG、canonical hash |
| [capability_planning.py](../../backend/app/application/capability_planning.py) | 仅接 Profile 的单次模型选择服务，失败直接传播 |
| [capability_planning_contract.py](../../backend/app/infrastructure/providers/capability_planning_contract.py) | 专用 purpose/schema/shape/prompt，与 Domain 共用输入边界 |
| [openai_compatible.py](../../backend/app/infrastructure/providers/openai_compatible.py) | 新 purpose 的 shape、预算复用、preflight、system prompt 四处有限接入 |
| [test_capability_planning.py](../../backend/tests/unit/test_capability_planning.py) | A/B、政策、未知领域、输入/输出引用、失败与接口合同 |
| [test_capability_planning_provider.py](../../backend/tests/unit/test_capability_planning_provider.py) | Mock HTTP 下的实际 adapter 接线、错误与预算合同 |
| 本报告 | 交付证据、限制与 STOP |
| [progress.md](../implementation/progress.md) | 前置追加当前结果，完整保留原历史正文 |

## 3. 最终对象及来源追踪

CapabilityPlan 冻结字段：schema_version、source_goal_profile_hash、policy_version、route_kind、capabilities、claim_bindings、constraint_effects、verification_evidence；plan_hash 为服务器计算的派生属性，to_payload 输出 JSON 兼容副本并包含该 hash。

每个 Capability：capability_id、title、disposition、learning_requirement、project_usage、desired_depth、learning_outcomes、requirement_refs、policy_refs、learner_claim_refs、prerequisite_refs、learning_target_refs。LearningOutcome 只有稳定 outcome_id 与 text。

disposition 为 accepted_known / needs_learning；learning_requirement 为 required / recommended；project_usage 为 required / optional / excluded；desired_depth 为 foundation / applied / deep。已知能力 title、outcomes、真实前置来自 Policy，模型不能重新输出或改写这些定义。

新增字段都有本轮消费者：route_kind 驱动系统性 MCP 政策；claim_bindings 完整覆盖声明并校验 A 归属；constraint_effects 完整覆盖限制并识别 learning/project 排除冲突；learning_target_refs 保护明确学习目标；verification_evidence 供未知定义及来源绑定校验。这些字段均进入最终 hash，没有 score、Stage、教材、URL、Seed、Recipe、Task 或课程章节。

非 ready 使用独立 CapabilityPlanningPending：status、source_goal_profile_hash、policy_version、issues(code/refs)、clarification_questions。关键冲突返回 needs_clarification，必要事实待验证返回 needs_verification，不伪造完整 CapabilityPlan。route_kind=uncertain 或服务器发现冲突但模型没有问题时，服务器补一个可回答问题，无额外模型请求。

CapabilityPlanValidator.validate 对 schema、枚举、引用、ID、Policy 权威、约束映射及 DAG 进行机械检查，在返回 Pending 前仍拒绝非法引用/未知业务字段。source_goal_profile_hash 精确匹配输入 Profile，policy_version 精确匹配只读 Policy。capabilities、refs 与 binding/effect 进行规范排序；同一输入/输出及不同能力数组顺序得到相同 hash。

输入边界 validate_capability_planning_input 同时供 Service 和 Provider 使用，验证 Profile 字段、类型、枚举、状态/问题、inferred_required rationale、来源拼写、条目 ID、profile_hash 与 Policy 一致性。Service 只对合法上游 needs_clarification 零派发返回；Provider 默认只接 ready。

来源真实性限制：Profile 未保存原始 structured constraints 数组，Item 2 只能检查 goal.constraints 引用语法与 0..19 下标范围，不能重新证明原下标实际存在；原始来源存在性仍由 Item 1 已验证的接口保证。不会为了补证读取 raw goal。hash 证明内容绑定及完整性，不是来源认证签名；该内部对象不是新增公开目标提交入口。

## 4. 小型只读 Capability Policy

CapabilityPolicy / CapabilityDefinition / LearningOutcome 均为 frozen dataclass；CAPABILITY_POLICY.version=v1。to_payload 返回 JSON 兼容副本；没有 DB、CRUD、路线整包或复杂图谱。首版 12 条可组合定义，每条一个稳定核心 outcome：

| capability_id | outcome_id | real_prerequisites | default_depth |
|---|---|---|---|
| python.core | python.core.functions | 无 | foundation |
| python.async | python.async.cancellation | python.core | deep |
| json.cli | json.cli.io | python.core | applied |
| llm.api | llm.api.request | 无 | applied |
| structured.output | structured.output.validation | llm.api | applied |
| tool.calling | tool.calling.dispatch | llm.api | applied |
| agent.loop | agent.loop.termination | tool.calling | applied |
| mcp | mcp.protocol | 无 | applied |
| error.permission | error.permission.denial | 无 | applied |
| eval.lite | eval.lite.cases | 无 | applied |
| github.api | github.api.scope | 无 | applied |
| code.review | code.review.evidence | 无 | applied |

每条 policy_refs 使用 capability-policy:v1#加 capability_id；系统性 MCP 政策另为 capability-policy:v1#systematic-agent-mcp。Prompt 将 Profile 的明确深度优先使用，未指定时参考 default_depth。核心条目是本轮有限规划定义，不宣称已完成各行业技术事实或完整教学质量验收。

真实前置必须精确匹配所选定义且存在，拒绝自依赖、悬空与循环；A 可满足前置。llm.api 不以 Python 为普遍前置；MCP 没有仅基于推荐教学顺序的 Tool Calling 硬边。教学顺序优化留给后续 Item 6。

## 5. A/B 划分、MCP 与语义边界

- A 路径：CapabilityPlanValidator 验证 accepted_known 必须绑定具体 learner_claim_refs、不得带 learning_target_refs；claim_bindings 与能力声明引用必须一致。CapabilityPlan.accepted_known_capabilities 单独投影，不生成 Review、mastery 检查或学习任务。
- B 路径：needs_learning 不得带已会 claim_refs；CapabilityPlan.learning_capabilities 仅返回 B，learning_outcomes 也仅展开 B。它们是后续 Item 3～6 的输入接口；本轮未实现这些消费者，不能宣称已验证完整 Coverage/Research/Curriculum 链路。
- Python 基础与 python.async 分开；explicit 进阶学习目标通过 learning_target_refs 保留，不能被同一能力的 accepted_known 处理吞掉。前置展开不把已绑定 A 重新列成 B。
- systematic_agent_route 要求 mcp 的 learning_requirement=required；project_usage 可 optional / excluded，绝不因学习政策强制项目使用 MCP。这是 StudyPlan 产品政策，不是所有 Agent 的技术必需事实。
- route_kind 由模型对规范化 Profile 的语义选择，窄目标不能只因包含 Agent 就整包扩课。明确排除 MCP 学习与系统性路线政策冲突返回 Pending；保留用户限制，不自行删除。
- Validator 只能证明声明引用、排除映射与政策结构一致，不能证明自然语言含义都被正确选择。合法 Python claim 被错绑 GitHub、错误 route_kind、漏标 learning_target_refs 或错误 not_applicable 仍须真实语义审查。两条 SEMANTIC_EVAL_REQUIRED 反例测试明确演示该限制；Fake PASS 不等于真实模型 PASS。

## 6. 未知领域最小边界

DomainVerificationEvidence 包含 evidence_id、input_hash、source_refs、limitations、evidence_kind、capabilities。最多一份 bundle、最多 20 个定义；kind 显式 fixture / source_verification，来源及限制不能为空。input_hash 绑定准确 Profile + 当前 Policy。

_definitions 只补充未知能力：不得覆盖已知定义、伪造 Policy 引用、重复 outcome ID 或引入非法/循环前置。定义、来源、kind、limitations 均保留在最终 Plan 并参与 hash。缺证据的未知候选返回 needs_verification，既不直接拒绝用户领域，也不宣称模型已验证全部事实。

fixture 仅证明注入边界与冻结行为；source_verification 也只是受信调用方提供的类型标识，不代表本轮存在联网验证器。input_hash 不能证明来源真实、最新或充分。真实外部查询、官方来源核验、每个 Run 的持久化次数门禁/去重、缓存与 receipt、Run 编排及澄清 UI 留给后续授权集成，当前均未接线。单 bundle 校验不冒充跨 Run 零重复请求证明。

## 7. 实际 Item 1 → Item 2 接口及 Provider 复用

GoalRequirementAnalyzer.analyze(...) 返回 GoalRequirementProfile；CapabilityPlanner.plan(profile: GoalRequirementProfile, *, run_id, attempt_id, verification_evidence=()) 返回 CapabilityPlan / CapabilityPlanningPending / LLMFailure。接口测试 test_item1_analyzer_profile_is_consumed_by_item2_service_without_raw_goal 实际调用两项服务对象，使用 Fake LLM，Item 2 payload 只有 profile、policy、verification_evidence。

Service 拒绝 GoalSpec / 字典 / 字符串作为 Profile，不重读 target、不调用旧 selector、semantic/alignment 或 Seed。合法待澄清 Profile 零模型调用；ready Profile 每次最多一笔 generate_structured。LLMFailure 原样传播、已知派发异常直接传播、length 转为 provider_output_truncated、非法最终对象为 capability_plan_invalid；不 retry/repair、不持久化。

新 purpose=planning.capability_planning，schema=CapabilityPlanV1，专用 Prompt/Shape；复用 LLMPort → OpenAICompatibleLLM 的共享 HTTP、严格 JSON、usage、finish reason、transport unknown 与预算保护。预算使用既有 min(practice, deployment_cap, model_cap)，没有提高产品预算。adapter 移除四处明确 Item 2 接口改动后，与基线 AST 等价检查 PASS；没有新 Worker/Receipt/repair 或组合根注册。

## 8. RED / GREEN 与回归证据

原始输出均保留在 ignored var/planning-v2-item2-20261008/，未用最终结果覆盖历史失败。测试结果仅指离线规则与 Mock HTTP。

| 验证 | 结果及解释 |
|---|---|
| Domain 初始 RED | FAIL：1 collection error，模块未实现；不能描述成行为断言已失败 |
| Provider 初始 RED | FAIL：6 个断言，purpose/输入/预算接线尚未实现 |
| Domain 首次 GREEN 尝试 | FAIL：27 PASS / 1 FAIL，fixture 错期望派发 1 次，实际 preflight 正确拒绝为 0；修正测试后 30 PASS |
| 独立审查后机械输入 RED | FAIL：25 个负例，初版仅验证 hash/ID 不足以保证 Profile 结构合法 |
| Provider 首次 GREEN 尝试 | FAIL：22 PASS / 1 FAIL，tuple/list JSON 表示不一致；使用 canonical JSON roundtrip 后 23 PASS，未改 hash 算法 |
| Domain 增量 GREEN | PASS：56；随后真实双节点环测试初次因误用 LLMFailure.code FAIL，改为现有 details 后 1 PASS |
| 最终统一定向回归 | PASS：269，failures/errors/skips 均 0；下表为唯一计数，不叠加前次执行 |
| Backend Collection | PASS：收集 2146 项，exit 0；不表示执行全量 Backend 测试 |
| Ruff 新六份代码/测试 | PASS：完整规则 |
| Ruff 既有 adapter | PASS：沿用基线 E701 / I001 排除；基线三处诊断未扩大修改，不宣称全文件零豁免 |
| git diff --check | PASS |

| 最终回归文件/分组 | PASS 数 |
|---|---|
| test_capability_planning.py | 57 |
| test_capability_planning_provider.py | 23 |
| Item 1 analysis/input/provider/hard_constraints/project_context_refs | 52 + 9 + 31 + 12 + 5 = 109 |
| test_b3_provider.py | 8 |
| test_known_json_repair.py | 58 |
| legacy removal / residual cleanup（含 public fail-closed） | 10 + 4 = 14 |
| 合计 | 269（新 Item 2 80 + 既有受影响 189） |

用户要求的十二类场景均覆盖：Python A、显式具体技术 B、系统性 MCP 学习/项目分离、窄 JSON CLI、可组合 Coding 能力、MCP 排除冲突、未知领域待验证/fixture、A 满足前置、错误引用/定义、环/非法 hash、稳定 hash、禁止课程/未知业务字段。额外只补机械输入、错误传播和本项接口反例。

pytest 使用 .venv/Scripts/python.exe -m pytest --confcutdir=backend/tests/unit，避免探测真实 PG。统一命令执行上述十一份文件，-q --junitxml=var/planning-v2-item2-20261008/regression.xml；Collection 为同一解释器 -m pytest --collect-only -q --confcutdir=backend/tests/unit backend/tests。完整命令输出、XML、metadata.json、共享接口包与独立审查原文保留在该 ignored 目录。

离线 fixture 冻结样例 sample.json 显式标记 OFFLINE_FIXTURE_NOT_REAL_SEMANTIC_PASS；source Profile hash=bcb96b83bf8d9c981286a2507336bf32ef65ff165513ea2ec85ff26d686babd7；plan_hash=f041a584a5c3e06a0ba26ec08db0c5485c3d07c69c95786975ec776740207754。反转能力数组顺序的对象及 hash 仍一致。未发送真实模型。

## 9. 独立审查与实施收口

独立开发审查代理对照原始 Goal、共享接口、代码与测试，结论 PASS：没有未解决代码 BLOCKER 或架构合同冲突。审查逐项覆盖固定路线、Policy 权威、A/B、MCP 项目使用、真前置、未知领域、raw goal、抽象/字段消费者和来源 hash；未让被测 Provider 自评。

审查指出初版输入只检 hash/ID 的机械边界不足。owner 先增加 25 个 RED 负例，再在同一共享 preflight 中完善类型/枚举/来源/状态/rationale 检查；没有改 Item 1 语义、没有另立验证器或读取 raw goal。后续只增量复核修正及可回答澄清问题，没有重复全仓审计。独立审查之后主协调补双节点环测试并汇总最终 269 PASS。

审查明确保留真实语义、原始 constraints 来源存在性、证据真实性与后续 Run 门禁限制；未将离线 PASS 宣传成大规模语义可靠性或完整产品验收。

## 10. 边界、未执行项及结束状态

- baseline/final hash audit：800 个受保护 tracked 文件、.env、378 个产品调用账本文件全部保持。progress 仅追加前缀，旧全文保持；架构合同、Item 1、历史报告、Seed/Content、迁移和前端均未改。
- 产品模型新增 0；账本保持 183/280，unknown177 / unknown183 原样保留。产品搜索 0、Reader 0；未调用 GitHub/Web、WeKnora 或在线 Domain Verification。
- public /plans/generate 仍在身份/范围门禁后返回 503，测试证明未触及 Run/Job/Plan 依赖；没有组合根注册新服务、恢复旧 Planning Graph 或旧 Fake fallback。Planning 占位页保持。
- 本轮未启动数据库、Worker 或创建业务 Run/Job/Draft/Plan，migration 新增 0。Run/Job/Plan mutation 为本轮无调用路径与依赖 spy 证据，真实 PG 行计数 NOT RUN；不冒充真实数据库计数。
- 真实模型语义、真实外部 Provider、在线领域验证/搜索/Reader、真实 PG/checkpoint、Planning Run 端到端、浏览器视觉验收均 NOT RUN。完整 Backend 执行 NOT RUN；仅执行本项必要定向回归及全量 collection。
- 回滚仅需正常 revert 本次本地提交；没有数据库或数据迁移需回滚。未修改产品配置、费用上限或历史调用状态。
- 与冻结合同无已知偏差，剩余是明确延期的真实语义验收与整链集成，不以本项 COMPLETE 代替整个 Planning V2 READY。

PLANNING_V2_ITEM2_CAPABILITY_PLANNING_COMPLETE

ITEM1_CONDITIONALLY_ACCEPTED

ITEM3_NOT_STARTED

STOP。
