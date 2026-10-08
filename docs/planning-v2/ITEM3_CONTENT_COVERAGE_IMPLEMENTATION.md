# Planning V2 Item 3 — Reviewed Content Coverage

日期：2026-10-08。实现确定性的学习结果覆盖判断；本轮没有实施 Item 4，也没有调用产品模型、搜索或 Reader。

## 1. 基线、范围与提交

- Branch：`feat/n1-resource-discovery`；Start HEAD：`91c17a63747ddd205880df488484a4fdf804d5f9`。开始 tracked tree clean，Policy v2 与前置报告一致：12 capabilities、27 outcomes。
- 权威为 [冻结架构合同](PLANNING_V2_ARCHITECTURE_CONTRACT.md)。[Item 2 Policy 修订报告](ITEM2_POLICY_OUTCOME_REFINEMENT.md)与[Item 3 原始预检失败报告](ITEM3_CONTENT_COVERAGE.md)保持原文，没有改写历史失败。
- 只运行 Tool Calling 的一个定向粒度示例，确认参数校验与派发结果拥有独立 ID；没有再次全面审计 outcomes。
- Final HEAD 为包含本报告的本地提交：`git log -1 --format=%H -- docs/planning-v2/ITEM3_CONTENT_COVERAGE_IMPLEMENTATION.md` 可定位；精确 SHA 另存最终答复和 ignored `var/planning-v2-item3-implementation-20261008/final.json`，避免报告自包含其 commit SHA。
- 提交消息：`feat(planning): add v2 reviewed content coverage`。未 push、merge、deploy；既存 `.workbuddy/`、`design-preview/` 未访问、修改或纳入提交。

| 修改文件 | 职责 |
|---|---|
| `backend/app/domain/planning/content_coverage.py` | 冻结覆盖对象、确定性 Evaluator、ResultValidator、输入和映射完整性校验 |
| `backend/app/infrastructure/reviewed_content_coverage.py` | 读取两份既有本地证据；固定身份、版本、hash 和两项 MCP 映射 |
| `backend/tests/unit/test_content_coverage.py` | 算法、分区、A/B、版本、损坏配置、结果篡改和确定性反例 |
| `backend/tests/unit/test_reviewed_content_coverage.py` | 实际 v8 索引/审核记录映射、严格来源 pin、旧版本和范围失效反例 |
| 本报告 | 实施证据、语义判断依据和限制 |
| `docs/implementation/progress.md` | 前置追加当前结果，保留此前全文 |

没有修改 Item 1/2 业务语义、Policy、Schema、旧内容、审核资格、hash 算法、公开 API、Worker、Runtime、数据库或 UI，没有 migration。

## 2. 最终领域合同

`CoverageEvaluator.evaluate(plan, index)` 接收冻结的 `CapabilityPlan` 与只读 `ReviewedContentIndex`，输出 `CoverageResult`。没有读取 raw goal、Profile 或根据资源反推能力。没有模糊匹配、embedding、分数、模型审核器或新数据库。

| 对象 | 字段 |
|---|---|
| CoverageResult | `source_capability_plan_hash`、`content_index_version`、`content_index_hash`、`entries`；确定性 `result_hash` 和 JSON `to_payload()` |
| CoverageEntry | `capability_id`、`coverage`、`covered_outcomes`、`missing_outcomes`、`content_refs` |
| CoverageContentRef | `section`、该 section 支持的 `outcome_ids`、`evidence` |
| ReviewedSection | `content_id/content_version/content_hash`、`source_id/source_version/section_id`、source/section `verification_status`、`review_depth`、`review_refs` |
| ReviewEvidence | `reference`、`sha256`、`section_ids`、`supported_outcomes`、`review_depth`、`limitations` |
| OutcomeMapping | `outcome_id`、content/source/section 身份和版本、`review_refs` |
| ReviewedContentIndex | `version`、`policy_version`、`sections`、`mappings`、`evidence`；确定性 `index_hash` |

所有输出集合规范化为确定性顺序与 tuple，JSON 使用规范化数组/对象。仅 `plan.learning_capabilities` 生成 entries；A 类保留上游真前置作用，不生成教学覆盖条目或 Python 复习。相同 section 支持两个 outcomes 时合并引用，不创建教学资产。

covered/missing 是所选 outcomes 的完整不相交分区：全覆盖为 full，严格部分为 partial，零覆盖为 none。单 outcome 能力仍可只有 full/none。ResultValidator 根据冻结输入重建期望结果并比较完整对象，拒绝错误状态、缺失/交叠分区、多余能力、来源 hash 或引用不一致。

输入重查当前 Policy v2、Schema、能力与 outcome 定义、route/depth 选集、引用结构、A/B、前置 DAG 和既有 MCP 规则；不修复上游。已知 Policy 的全部合法 outcomes 与本 Plan 受信领域定义形成映射 ID 范围；标为 v2 的旧 v1 ID/拼写错误也明确拒绝。映射无须仅包含本次所选能力，因此固定 MCP 索引可用于只学习 Tool Calling 的 Plan。

没有映射正常 missing。已配置映射的身份/版本、正文审核资格或必要证据不一致，抛 `ValidationAppError` 并指出完整性字段，不伪装成成功的 none。未映射的候选/目录元数据可以存在，但不能支持 covered。配置整体完整性校验不把 A 加入学习集合。

## 3. 现有内容的有界核查

只核对当前映射需要的本地内容和既有审核记录，没有阅读新公开教程或重新审核整套 Seed。

- `PublicResourceSource/PublicResourceSection`（`backend/app/domain/resources/curation.py`）提供稳定身份、来源版本与状态；`checked_at` 本身不证明教学质量。
- `PgPublicResourceCatalog` 所在的 `backend/app/infrastructure/db/public_resource_catalog.py` 是身份/状态投影，不能替代完整审核范围；本轮没有连接或调用数据库 catalog。
- KnowledgeNode/LearningUnit、Content JSON 的存在、发布或合法 hash 不自动建立 outcome 覆盖。候选来源、URL、README、目录和历史索引均没有隐式映射。
- v7 的 MCP 10.1 是 `legacy_index/toc_checked`；v8 的 10.1 新增正文审核是另一份特定范围证据。本轮使用 **10.2** 的既有审核，没有把 10.1 的正文 hash 或资格移给 10.2，也没有让 v7 继承 v8 资格。

### 实际启用的唯一 section

| 字段 | 冻结值 |
|---|---|
| Content | `agent.application`，version `8` |
| source_id / source_version | `src_mcp101_a7ca881ee83ac722491299cd` / `2` |
| section_id | `sec_mcp101_09e62ff389cb388eb744e738`（10.2 MCP） |
| source/section 状态 | `reviewed` / `reviewed` |
| review_depth | `selected_sections_read` |
| Index version / Policy | `planning-v2-reviewed-v1` / `v2` |
| index_hash | `0e0ca1a7fffc0d3b4d5cdcadfbb55ec7434d7a4dfa1b805e73fd80f985434fe6` |

| 引用 | SHA256 与含义 |
|---|---|
| `backend/app/infrastructure/content/agent-application-v8.json` | `6171e7bbed660d3f1d81d0c65b7b102eef0c2ec8dd7a3c40e54d4e3093985d0b`，完整本地 pack 字节 |
| 上述文件 `#/resources/13/sections/1` | `8278e9f8bae2291a5446080f771f0080381b02ce9c5734e0cc994f9ef74e9b38`，canonical section 索引记录 |
| 上述文件 `#/resources/13/review_evidence/chapter_review` | `2be64ad62fee6b73832ff08fd404bed705ba9a4b8b47120bdc46c4b9bd3cbd07`，canonical 既有章节审核记录 |
| `docs/research/semantic-corrected-2026-10-04/AGENT_APPLICATION_DEEP_REVIEW.md#L197-L205` | `3349acbc6b407d48560a48a9c7891ac20856aaa8dddf8702faf9823797bab55c`，既有审核文档完整字节 |

这些是 pack/索引记录/审核记录/文档 hash，**不是教程 10.2 正文 hash**。Loader 固定本地文件和 JSON pointer，任何来源字节改变都要求明确复核并更新映射，不能自动滚动到 CURRENT_PACKS 或另一个版本。

### 映射语义判断与机械检查分开

| Outcome | 既有审核依据及本轮判断 |
|---|---|
| `mcp.roles` | chapter_review.teaches 明确记录 MCP host-client-server model；审核文档 199–201 行记录实际阅读范围及 Host/Client/Server 职责。支持 Client/Server 职责协作这一完整概念目标。 |
| `mcp.interfaces` | 同一审核记录明确列 Tools/Resources/Prompts，文档记录协议能力边界；支持 Tool/Resource 接口目标。没有因标题为 MCP 自动外推。 |
| `mcp.minimal_connection` | 不映射。虽然记录提到本地 stdio 与 client/server 示例，保留材料不足以证明“最小接入并验证一次工具调用结果”这一完整教学任务。静态阅读未运行也是限制，但不能仅由未运行反推概念教学无效。 |
| `tool.calling.input_validation/invoke_result` | 不映射。既有工具/ReAct/章节索引不充分证明参数合同与输入校验、有效请求派发及结果处理各完整目标。未开展新的教程审核来补齐。 |

`ReviewEvidence.supported_outcomes` 是本轮小型人工受控映射的范围，不冒称历史审核原本已有 Policy v2 ID。原始审核引用、hash、section 范围与 limitations 均保留。limitations 包含静态示例未启动、远程服务/部署未验证、transport sketches、SDK 版本差异、第三方平台与权限安全限制。两个开发代理分别对照原始审核记录判断映射语义；程序只检查身份和范围闭合，不证明教材语义必然正确。

## 4. 代表结果

| 输入冻结范围 / 索引 | covered / missing | 结果 |
|---|---|---|
| Tool Calling 两 outcomes，合成受控证据仅支持 input_validation | input_validation / invoke_result | partial；只证明算法与接口，不证明现有 Tool Calling 教材资格 |
| MCP，narrow_goal + foundation，真实索引 | roles、interfaces / 空 | full，仅针对所选两个概念 outcomes |
| MCP，narrow_goal + applied，真实索引 | roles、interfaces / minimal_connection | partial |
| MCP，systematic_agent_route + foundation，真实索引 | roles、interfaces / minimal_connection | partial；不降低系统性实践要求 |
| Tool Calling 及真前置 llm.api，真实索引 | 无 / 各自全部所选 outcomes | none，保留 required 能力与学习深度 |

full 不表示学习者已掌握；none 不表示外部世界没有教材。已知 A 类不重新进入任何教学条目。离线代表的完整规范化输入/输出与 hash 留在 ignored `examples.json`，单元测试也固定核对这些分区。

## 5. RED、GREEN 与定向验证

验证只运行本轮及直接相邻边界，不重复 Item 1/2 大量回归或全量 Backend。

| 检查 | 结果 |
|---|---|
| 编码前 Tool Calling 分区预检 | PASS，1 项定向参数实例 |
| Domain 初始缺模块 | FAIL，collection error；不称为行为断言失败 |
| Domain API stub 行为 RED | FAIL，31 项，均进入未实现 API，0 collection/setup errors |
| Index 首次 RED | FAIL，5 行为失败、7 sandbox temp setup errors；原日志保留 |
| Index 改用新的仓库内 basetemp 后行为 RED | FAIL，12 项，均进入未实现 API，0 setup errors |
| 初次 Domain / Index GREEN | PASS，31 / 12 项 |
| 独立审查发现 v2 标签下旧/拼错映射 ID 的负例 | FAIL，3 项 DID NOT RAISE；先保留 RED 再局部修复 |
| 最终定向回归 | PASS，56 项：新 Domain 35、真实本地索引 12、接口分区 3、既有内容审核 3、fail-closed 3；0 FAIL/ERROR/SKIP |
| 必要 import / collection | PASS，同一范围 56 项；未进行全量 Backend collection |
| Ruff / git diff --check | PASS，四份新增 Python 文件及本轮完整 diff |

统一回归范围：两份新测试；Item 2→3 三个冻结分区参数实例；既有 MCP 审核 successor 的旧版本保持、授权范围及可重现映射三项；公共 generate/submit_generation 与 API boot 的三个 fail-closed 实例。测试只复用本地 Fake/冻结 CapabilityPlan 来构造上游输入，没有产品模型网络调用。

统一命令使用 `.venv/Scripts/python.exe -m pytest --confcutdir=backend/tests/unit --basetemp=<新的仓库内独立目录> <上述定向节点> -q --junitxml=<证据路径>`；同一节点 collection-only。Ruff 仅检查两个新增模块与两份新增测试。日志/XML 和规范化 examples 保留于 ignored `var/planning-v2-item3-implementation-20261008/`。没有删除失败证据或修改系统 Python 配置。

## 6. 独立审查与保护边界

独立审查 **PASS**，无剩余合同级 BLOCKER。已确认真实 MCP 两项概念映射有具体审核依据，最小实践和 Tool Calling 保留 missing 恰当。Plan 重查只保护冻结定义/结构/投影，没有重新理解 raw goal 或重判 learner claim。独立审查发现的旧/错 outcome ID 缺口按上述 RED 局部收口，没有扩大 Policy 或引入新审核平台。独立报告存于 ignored `independent-review.md`；审查员只读代码、原审核文本及保存的测试证据，没有为形式复核重复执行测试。最终 56 项结果由主协调汇总，额外未知领域映射正例只证明受信定义兼容性。

主协调请求 `gpt-6.1-sol/high`，单一领域实现、真实证据清点与独立审查请求/沿用 `gpt-6.1-sol/medium`，实际解析均 **NOT OBSERVABLE**。没有把提示词中的角色称谓当作实际模型证明，没有全局配置修改或 HARD 升级。

812 个受保护 tracked 文件、378 个历史账本文件与 `.env` hash 保持；旧预检报告、架构、Policy、内容和历史审核记录不变。progress 仅前置追加，旧正文完整保留。

产品模型请求 **0**、搜索 **0**、Reader **0**。历史账本仍 183/280，unknown177/183 未覆盖、删除或重派。没有运行 DB/Run/Job/Draft/Plan 写入路径；最小 fail-closed 测试拒绝依赖访问。真实 PG 行计数 **NOT RUN**，因此不冒称数据库前后行数已验证。

## 7. 未验证部分与下一项边界

- 真实 PG、浏览器、产品模型语义、外部接口、新教程正文或示例执行、完整 Backend 回归、整链 E2E：**NOT RUN**。
- 原始 Profile 不在 Item 3 输入中。引用结构和当前 Policy 可机械重查，但原 requirement/claim 事实、领域 evidence.input_hash 与原 Profile 的真实性绑定仍依赖 Item 2 上游；本模块不构造假 Profile 来冒充重验。
- 教材语义范围依赖保留的既有审核与独立人工判断。record/document hash 只防漂移，不证明教学内容正确、最新或已被学习者掌握。最小索引没有穷尽全库；无映射的 none 只表示当前受控索引无法证明覆盖。
- Item 1 仍 CONDITIONALLY_ACCEPTED，Item 2 真实语义验收仍待整链；本轮不把确定性 Coverage 测试替代这两项真实验收。
- 输出已能把精确 missing outcomes 交给未来 Item 4，当前没有 Coverage 合同级前置阻塞。是否实施 Item 4 需下一项用户授权，本轮不构造 ResourceGapSet 或资料搜索。

最终：`PLANNING_V2_ITEM3_CONTENT_COVERAGE_COMPLETE`；`ITEM4_NOT_STARTED`；STOP。
