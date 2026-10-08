# Planning V2 Item 3 — Outcome Granularity Precheck

日期：2026-10-08。结论：ITEM3_BLOCKED_BY_OUTCOME_GRANULARITY / ITEM2_MINIMAL_POLICY_REVISION_REQUIRED / STOP。

本轮在用户要求的编码前接口预检处停止，未实现 Coverage Evaluator、CoverageResult 或内容映射。本文是最小 Item 2 Policy 修订建议，不是 Item 3 实施通过报告。

## 1. 基线与范围

- Branch：feat/n1-resource-discovery。
- Start / Final HEAD：53c8b0851098d8905722d5867cfae27643672267，与用户预期一致；开始时 tracked tree clean。仅本报告及 progress 前置追加是本轮工作树修改，未提交；用户指定的功能提交只在预检及实施验收通过后执行，本轮未满足该条件。
- 唯一上位合同：[PLANNING_V2_ARCHITECTURE_CONTRACT.md](PLANNING_V2_ARCHITECTURE_CONTRACT.md) 的 Item 2/3/4 与 Producer/Consumer Matrix。Coverage 必须按稳定 outcome ID 完整划分 covered/missing，不能静默修改冻结 CapabilityPlan。
- Item 1 仍为 CONDITIONALLY_ACCEPTED；Case 7 真实验收未完成、unknown177/183 和旧报告均保持。Item 2 离线实现完成，真实语义验收未完成；Item 3 编码未开始，Item 4 未开始。
- 主协调沿用请求 gpt-6.1-sol/high；复用独立审查代理请求 gpt-6.1-sol/medium，实际模型解析 NOT OBSERVABLE。未切换全局配置或启用新的高档升级。
- 产品模型、搜索、Reader 调用均为 0；无数据库、migration、UI、Worker、公共生成接线修改，无 push/merge/deploy。

## 2. 可机械证明的粒度限制

读取 [capability_policy.py](../../backend/app/domain/planning/capability_policy.py) 的 CAPABILITY_POLICY，全部 12 个 capability 当前各有一个 outcome。Policy 数据和 [CapabilityPlan.learning_capabilities / learning_outcomes](../../backend/app/domain/planning/capabilities.py) 并没有单 outcome 内可独立引用的教学要求 identity。

对某能力的目标集合 O={唯一 outcome ID}，若 covered 与 missing 不交叉且并集等于 O，则只有两种结果：

| covered | missing | coverage |
|---|---|---|
| O | 空 | full |
| 空 | O | none |

不存在两个集合都非空的合法分区，因此当前任一单能力的 partial 不可达。全 Plan 汇总中混合 full/none，不能替代用户要求的单能力 partial。

只有一个 outcome 本身不是错误：一个连贯、可整体验收的目标可以保持单 ID。阻断发生在这个 ID 内实际合并了需要分别审核并保留缺口的独立教学任务。对这类目标，把只讲其中一部分的材料标为 covered 会虚报 full；保守标 missing 虽不会虚报，却不能表达已支持部分，也会让后续缺口包含已经有依据的部分。

本轮 ignored 离线脚本 var/planning-v2-item3-preflight-20261008/inspect.py 通过 AST 提取真实 Policy，枚举 ID 分区，结果：12 个定义、12 个单 outcome、可表达 partial 的单能力为 0。证据提取 PASS，接口预检 FAIL。该脚本不是 Coverage 实现或真实资料覆盖测试。

## 3. 重点五项与最小明确阻断集

以下反例是教学范围分析，不把假设章节当成真实 reviewed 映射。

| 现有 outcome | 预检判断 | 必要原因与最小拆分方向 |
|---|---|---|
| tool.calling.dispatch：按工具合同校验参数并派发调用 | 必须拆分 | 参数校验与合同内派发是两个可独立验证的行为。可能已有校验教材而缺派发教材，或派发示例直接执行未校验参数。最小分为“工具参数合同及校验”和“按合同派发工具调用”。不新增权限系统或工具框架要求。 |
| agent.loop.termination：组织工具调用循环、终止条件与失败返回 | 必须拆分 | 正常循环推进不能证明终止控制或失败返回；三者可以分别有充分证据或缺口。最小分为“工具调用循环推进”“终止条件”“失败返回”。不新增持久化恢复、重试或多 Agent 要求。 |
| mcp.protocol：解释 MCP 客户端、服务端和工具协议边界 | 必须拆分 | 角色职责与工具协议边界有不同的章节审核范围，知道 client/server 角色不能证明工具协议合同。最小分为“客户端/服务端职责与协作”和“工具协议边界”。不按每个角色机械拆 ID，不增加 transport 实测、安全部署或其他协议课程。 |
| code.review.evidence：将 Review 结论关联到代码上下文与可检查依据 | 不要求机械拆分 | 核心是一条完整证据关联任务。只生成评论或只定位代码都不能满足它；应要求审核依据支持完整关联，不能分别当作可替代的 covered 部分。 |
| error.permission.denial：区分输入错误、权限拒绝、执行失败与未知结果 | 不要求机械拆分 | 核心是完整分类辨别任务，列举的四类是判别维度。只讲一种错误的材料不足以证明整个区分目标，应保留 missing；无需为每个名词增加一个 ID。 |

eval.lite.cases 同样可以保持整体案例验证任务，不因涉及正常/失败分支就机械拆分。

独立审查还指出六个复合候选：python.core.functions、python.async.cancellation、json.cli.io、llm.api.request、structured.output.validation、github.api.scope。它们分别可能合并函数/数据结构/异常、并发/取消、读取/校验/CLI 错误、请求响应/费用/失败、合同定义/响应校验、对象/分页/权限失败。本报告保留这些发现，留给单独 Policy 修订任务定向收敛，不在 Item 3 扩成全面能力词典细化，也不承诺只拆重点三项就足以通过下一次完整接口预检。

## 4. 现有内容的有界只读佐证

在接口预检范围内，仅读取当前内容 registry、MCP 代表章节审核记录及实体/证据字段，没有全量拼接 Seed、研究新资料或建立 outcome 映射。

- [domain_pack.py](../../backend/app/infrastructure/domain_pack.py) 的 CURRENT_PACKS 当前将 agent.application 指向 agent-application-v8.json；load_pack 的 published 检查不能代替 outcome 审核覆盖。
- 该实际 JSON 的 pack_key=agent.application、version=8，文件 SHA256=6171e7bbed660d3f1d81d0c65b7b102eef0c2ec8dd7a3c40e54d4e3093985d0b。
- 章节来源 source_id=src_mcp101_a7ca881ee83ac722491299cd、source_version=2。10.1 section_id=sec_mcp101_18e647c993d34f4e0eb316e5，明确 selected_sections_read；另有 10.2 与真实 MCP 协议边界的独立 section identity。记录存在不等于本轮判定覆盖。
- [map_mcp101_review.py::BODY_REVIEW](../../backend/app/tools/map_mcp101_review.py) 及 JSON 留存的 10.1.1–10.1.4 审读明确：“不代替host/client/server深入章节”；其他章节继承旧审核，本次没有重新审读。runtime_validation=not_run，SDK 互通、安全、transport、部署成功不是该证据证明的事实。
- [既有 Agent 审读](../research/semantic-corrected-2026-10-04/AGENT_APPLICATION_DEEP_REVIEW.md) 的第 10 章记录了不同范围的 10.2 审读及静态示例限制。两组记录支持分范围审核的必要性，不能将 10.1 新增审核直接继承为整个 mcp.protocol 的 full。旧文档中的推荐路线也不成为 V2 Policy。

已核对的来源类型边界：

| 类型 | 本轮事实及限制 |
|---|---|
| 有正文审核范围的内容 | 上述 MCP selected_sections_read 有审读范围/hash/limitations，可作为以后人工受控映射的输入；尚未证明任何当前 outcome 已完整覆盖 |
| 只有目录或章节索引 | v7 的同章 10.1 在既有 test_mcp101_reviewed_successor 中为 legacy_index / toc_checked；不能因后继新增审核倒写旧版本 |
| 候选元数据 | DiscoveryEvidence 明确 metadata_only/readme_read/chapter_or_index_checked 等状态及 recommended_role；URL、章节标题、推荐角色都不是完整 outcome 覆盖证据 |
| 历史教学材料/实体 | 旧 pack 及 KnowledgeNode/LearningUnit 的稳定键、content_version/rubric_version/source_status 保留，但存在、published 或 ai_draft 身份不自动取得 reviewed coverage |

只读定位：KnowledgeNode / LearningUnit 位于 backend/app/domain/catalog/models.py；PgPublicResourceCatalog 位于 backend/app/infrastructure/db/public_resource_catalog.py；ContentEvidence / DiscoveryEvidence 位于 backend/app/application/resource_discovery_contract.py。本轮未调用 DB adapter，未读取真实 PG 内容行，未把测试 helper 的 reviewed_fixture 名称当审核依据。完整只读内容索引预检及 Coverage 映射资格验收因前置门禁失败而 NOT RUN。

## 5. 单独 Item 2 修订的最小影响范围建议

本节仅建议，未实施。保持 capability_id、A/B、required/recommended、MCP 学习与项目使用分离、真实前置、深度及 Profile 语义不变；只对确需独立保留覆盖/缺口的任务提供新的稳定 outcome ID 和原范围内文本。

- 字段：CapabilityDefinition.learning_outcomes 与其 Policy version/policy_refs。重点三个旧 ID 不应静默重新解释或自动兼容成不同范围的新 ID；新 Policy 版本用于未来新冻结输入，历史 v1 Plan 及报告保持。
- 对象：Capability.learning_outcomes 继续由 Policy 提供；CapabilityPlan.policy_version、plan_hash 和 DomainVerificationEvidence.input_hash 将因新 Policy 内容自然变化。source_goal_profile_hash 不变，hash 算法与 Plan Schema 不需改变。
- 实现定位：capability_policy.py::_definition 当前写入 v1 引用，若未来发布新版本须同步处理定义引用与 CAPABILITY_POLICY 版本，不能只换 outcome 文案而沿用旧身份。是否需要历史版本读取路径须根据未来实际消费者决定，不在本轮搭版本管理平台。
- Item 2 测试：更新受影响 Policy/outcome fixture 与稳定 ID 断言；验证模型仍不能重定义核心 outcomes、新 Policy 与证据绑定一致、同输入 hash 稳定、旧冻结值不被覆写。保持 Python A 排除、具体目标 B、MCP 项目分离、前置与失败传播保护。Provider Shape 是否需改应按真实 diff 判断，不能为了拆 Policy 默认改服务或 transport。
- Item 3 后续 RED：用修订后的真实 outcome 集合证明“只覆盖参数校验、不覆盖派发”等情况能产出 partial，并验证 covered/missing 完整无交叉、失效审核引用失去资格、实际章节样本不凭状态推 full、无可信映射为 none。不能使用新建的虚构 reviewed 状态证明真实内容覆盖。

无需为该修订改架构合同、增加子 outcome 层、评分、数据库或别名兼容层。Policy 修订后仍应重新通过受影响接口预检，才能继续 Item 3；本轮不自动执行修订或请求外部资料。

## 6. 独立复核、验证与 STOP

独立开发审查读取真实 Policy，并复用主协调的本地 MCP 章节证据作一次增量判断：确认重点三项足以阻断，另外六项发现应保留但不扩大本轮实施范围；单 outcome 不必一律拆分。未让产品 Provider 自评，未将章节索引或 hash 当语义正确性证明。

| 验证 | 结果 |
|---|---|
| HEAD/branch/开始 tracked tree | PASS |
| 12 个真实 Policy 定义及分区枚举 | PASS（事实提取）；接口粒度门禁 FAIL |
| 独立预检复核 | PASS：确认阻断与最小建议边界，不代表 Item 3 验收通过 |
| 生产文件、历史报告、.env、调用账本保持 | PASS，最终本地 hash audit |
| 文档链接 / git diff --check | PASS |
| Item 3 RED/GREEN、Item2→3接口、内容回归、Backend Collection、Ruff | NOT RUN：编码前 STOP，无实现或测试修改，不重复基线回归 |
| 本轮 public generate 执行测试 | NOT RUN；生产代码及上次 fail-closed 证据对应输入未变化，不宣称本轮重新执行 |
| 真实 PG / 产品 Provider / 在线搜索 / Reader | NOT RUN；新增调用均 0 |

ignored evidence：var/planning-v2-item3-preflight-20261008/ 的 baseline.json、preflight.json、final.json，以及 var/codex-goals/planning-v2-item3.json。只修改本报告及 progress，不创建 Item 3 生产代码或测试，不提交指定功能 commit。

ITEM3_BLOCKED_BY_OUTCOME_GRANULARITY

ITEM2_MINIMAL_POLICY_REVISION_REQUIRED

ITEM4_NOT_STARTED

STOP。
