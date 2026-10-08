# Planning V2 Item 5 — Teaching Resource Research

日期：2026-10-08。本轮实现有界、可离线验证的教学资料研究接口。输入来自冻结的 Item 1～4；不生成课程，不接正式 Worker/Run，不开展真实资料研究。

## 1. 基线与范围

- Branch：`feat/n1-resource-discovery`。
- Start HEAD：`37871f0fd861810bcb67c76d02cb96819722dfc1`，与用户预期一致；开始 tracked tree clean。既存 `.workbuddy/`、`design-preview/` 不访问、不修改、不提交。
- 权威：[Planning V2 架构合同](PLANNING_V2_ARCHITECTURE_CONTRACT.md) Item 5、Single Authority、Producer / Consumer Matrix。上游：[Item 4](ITEM4_RESOURCE_GAP_EXTRACTION.md)。未修改架构、Policy v2、Profile、CapabilityPlan、CoverageResult、GapSet、审核映射或 Seed。
- Final HEAD 为包含本报告的本地提交，可用 `git log -1 --format=%H -- docs/planning-v2/ITEM5_TEACHING_RESOURCE_RESEARCH.md` 定位；精确 SHA 另记最终答复及 ignored `var/planning-v2-item5-implementation-20261008/final.json`，避免报告自包含 commit SHA。
- 提交消息：`feat(planning): add v2 teaching resource research`。不 push、merge、deploy。

实施前完成一次有界端口与安全审计，随后列明文件职责。最终范围共 11 个文件：

| 文件 | 修改与职责 |
|---|---|
| `backend/app/domain/planning/resource_research.py` | 新增冻结 Requirement/Result/Evidence、共享预算及内容外 metadata snapshot |
| `backend/app/application/teaching_resource_research.py` | 新增来源校验、审核资料复用、候选发现、临时正文/Reader 协调 |
| `backend/app/domain/planning/research_reader.py` | 新增唯一 Reader 输入/输出协议、chunk/hash 校验及临时正文容器 |
| `backend/app/infrastructure/providers/research_reader_contract.py` | 新增独立 Reader purpose/schema/shape/system，复用 Domain 校验 |
| `backend/app/infrastructure/providers/openai_compatible.py` | 仅新增 22 行 Reader purpose、输出上限、preflight/system/结果校验接缝 |
| `backend/app/infrastructure/resources/teaching_body.py` | 新增固定 GitHub 安全基础上的有界公开正文章节适配 |
| `backend/tests/unit/test_resource_research.py` | Item 4→5、真实本地审核记录、预算、隐私及失败边界 |
| `backend/tests/unit/test_research_reader_provider.py` | Reader 协议与 Mock HTTP Provider 边界 |
| `backend/tests/unit/test_teaching_body.py` | 正文身份、响应、大小、时限与 SSRF/transport 边界 |
| 本报告 | 实现、证据、验证与限制 |
| `docs/implementation/progress.md` | 前置追加本轮结果，保留历史正文 |

## 2. 现状审计与实际复用

| 既有模块/符号 | 本轮结论与用法 |
|---|---|
| `resource_gaps.extract`、`content_coverage` | 重算精确 GapSet 与冻结 Plan/Coverage 来源；复用审核映射资格检查，不重判学习能力 |
| `ResourceIndexPort.find(ResourceQuery)` | 候选发现接口；复用服务端 AuthContext/project scope，未新建搜索系统 |
| `PublicResourceCatalogPort.load_sources` | 读取稳定 source 身份、版本及 canonical URL；现有投影不含正文或免费访问事实，不能仅凭发布状态复用 |
| `GitHubResourceIndex.find/inspect` | find 可返回工程候选；inspect 的 README/目录、ContentEvidence 和 mainline_candidate 不等于教学审核，且不把真实正文提供给 Reader |
| `TavilyResourceIndex.find` | 只提供标题/摘要/URL 候选，`include_raw_content=False`；display URL guard 不能当任意 URL 正文抓取授权 |
| `PinnedPublicTransport`、GitHub URL/path guards | 复用固定 api.github.com:443、全 DNS 地址检查、IP pin、TLS 主机校验、禁代理/重定向/重试、流式字节及总时限保护 |
| `LLMPort`、`OpenAICompatibleLLM` | 复用单次 structured JSON 请求、现有 model/config、usage、finish/truncation、known failure/unknown 分类；未新增 Provider 或模型路由 |
| 既有 Attempt/Receipt/预算机制 | 已绑定旧 Plan/stage/unit，不能直接当作当前 Research Runtime；本轮提供预留/快照接缝，正式持久化接入留给 Item 7 |

既有 GitHub `_json` 未执行 MIME 检查，且把部分已知无效 JSON 归成 unknown。新正文子类局部实现必要的响应/MIME/流式解析边界，仍复用固定 transport、安全 URL/path、client 与 deadline；没有改写旧 `github.py` 或 `github_transport.py`，没有创建通用爬虫。

## 3. 入口、需求与结果字段

入口：`ResourceResearcher(...).research(gap_set, *, plan, coverage, profile, session, scope, project_id, checked_at)`。

先校验服务端 project scope、`extract(plan, coverage) == gap_set`、Profile 与 Plan hash、现有 Capability 输入合同及共享 session 的输入绑定。输入非法明确拒绝，不读取 raw goal，不修复上游。输入 hash 绑定 Gap/Plan/Coverage/Profile、预算、actor/project 和冻结检查时间。

| 对象 | 字段 |
|---|---|
| `ResearchRequirement` | capability_id、must_teach（原 LearningOutcome ID/text）、importance、desired_depth、requirement_refs、内部 starting_point/hard_constraints/learner_claims；不含 project_context |
| `ResourceResearchResult` | source_gap_set_hash、source_capability_plan_hash、source_coverage_result_hash、source_profile_hash、entries、checked_at、budget_usage；计算 result_hash 与 to_payload |
| `ResearchEntry` | requirement、status（resolved/partial/unresolved）、resources、unresolved_outcomes、reason_codes |
| `ResearchResource` | resource_id、url、version、checked_at、free_access（confirmed/unknown/paid）、qualification（public_reviewed/research_checked/candidate）、evidence、teaching_fit、limitations |
| `ResearchEvidenceRef` | outcome_id、reference、sha256、location、hash_scope（body/review_record） |
| `ResearchBudget` | max_searches、max_candidates、max_body_bytes、max_reader_requests、max_output_tokens、max_total_requests、max_cost_micros；search_cost_micros/reader_cost_micros 为调用方给出的最坏费用预留 |
| `ResearchSnapshot` | run_id、input_hash、budget、usage、blocked、pending_count、unknown_measurement、config_hash、inspected metadata、completed result；没有正文/chunks |

冻结 tuple/dataclass、精确分区、确定性排序及既有 canonical JSON/content_hash 约定保护结果身份。hash 证明身份和来源绑定，不证明资源语义或调用方提供的审核事实必然真实。

只消费 GapSet 的 B 类缺失 outcomes；已 covered/A accepted_known 不研究。required/recommended、深度、原始学习目标与 requirement_refs 原样保留。没有搜索词/score/confidence/Stage/课程角色字段。只有充分支持且免费、连续性/学习者适配/示例/版本检查通过的证据才解决 outcome，Reader partial 仍留作缺口。

## 4. 审核资料复用及代表流程

已有 scoped review 复用需同时具备：Item 3 合格映射、catalog 同 source/version 实际 URL、绑定 section.content_hash 的明确 free_public 访问事实。无证明就保留缺口；不凭 URL、标题、published/reviewed 标签推断免费或完整教学覆盖。

代表性真实本地记录来自冻结 `agent-application-v8.json`：pack SHA256 `6171e7bbed660d3f1d81d0c65b7b102eef0c2ec8dd7a3c40e54d4e3093985d0b`，resource[13] 的 `content_access=free_public`；source `src_mcp101_a7ca881ee83ac722491299cd` / version 2，MCP10.2 section `sec_mcp101_09e62ff389cb388eb744e738`。只沿用 Item 3 已核对的 roles/interfaces 两项 scoped review，不把 minimal_connection 一起覆盖，也不继承 v7 TOC 资格。

测试从实际 pack 和 `load_reviewed_content_index()` 读取这些身份/事实，catalog seam 为合成只读投影；不是新正文审核。既有 review 没有 10.2 正文 hash，输出明确 `hash_scope=review_record`，不把 pack/review hash 冒充教程正文 hash。proof.reference 定位到该 pack 的 resources/13/content_access。

| 场景 | 行为与结果 |
|---|---|
| Item 3 已 full 的窄 MCP | Item 4 空 GapSet；Item 5 空 entries，零外部派发 |
| 合成 none Coverage + 真实本地 MCP scoped review | 仅证明合法复用路径；foundation 两概念 resolved、零搜索/Reader；真实 Item 3 已 covered 时不会再次进入此路径 |
| GitHub 正文 + Mock Reader 全支持 | research_checked / resolved，停止 Web；不取得公共 reviewed 身份 |
| Mock Reader 只支持三个 MCP outcomes 中一项 | partial，精确保留另外两项原 missing outcomes；同 URL metadata 复用不重复 Reader |
| README/目录、未知免费访问、付费/不可读候选 | 不调用 Reader 冒充正文；保留 unresolved，允许有预算的 Web 候选发现 |
| 无证据、预算耗尽、已知失败或 unknown | 保留 required/recommended 原缺口和明确原因，不伪造 resolved |

工程候选按 GitHub→剩余需求的 Web 顺序处理；不为完成固定流程而强制搜索。查询仅来自已批准的 Policy outcome 原文和 tutorial/guide/examples 同义描述，不外发项目名称、原 project_context、起点/claim/constraint 私有文本。同等检查顺序中中文优先，不用 Stars 或 mainline_candidate 证明教学适配。

## 5. 临时正文、Reader 与隐私

`GitHubTeachingBody.read` 仅支持匿名公开 GitHub repository 的 README 索引中最多一个允许文本章节；README 本身不算教学正文。最多两次 HTTP，最多 64KiB aggregate wire、16KiB decoded UTF-8、15 秒 total deadline；限制 MIME/Content-Encoding、路径/ref、重定向、DNS/IP/TLS，不执行脚本、代码或递归抓取。版本为实际 `git-blob:<40hex sha>`，不是 repo commit；另以实际 UTF-8 字节计算正文 SHA 和位置/chunk identity。BOM 保留在正文 hash 中。

Reader purpose `planning.research_reader`、schema `ResearchReaderV1`，输出 cap 不超过 1024 且服从现有更低部署上限，不更换已配置模型。输入严格只有 must_teach、受控 chunks、匿名 learner_context（已知 capability IDs + depth）；不能携带完整 Profile 或私有原文。外部正文作为不可信数据，无 tools、业务写入或课程决策权限。

Reader 输出每个 outcome 的 supported/partial/unsupported、当前 chunk/hash evidence_refs、最多三项 160 字符 limitation、240 字符 rationale，以及 continuity/beginner_fit/examples/version_fit/language。程序检查精确 outcome 集合、真实 chunk、单资源/版本、SHA/身份、位置及范围；Provider 在产生可进入 receipt 的 LLMResult 前执行同一校验。拒绝额外字段、tools、越界引用、整段 chunk 的原样/空白规范化复制，以及跨字段/不同 outcomes 拆分复制的完整片段覆盖。

正文容器 repr 隐藏 chunks；Application 在 finally 中清理 payload、close chunks，不写正文到 Result、metadata cache、snapshot、DB、日志或 receipt。保留短审核意见与定位；这不代表 Python 内存安全擦除，也不保证模型语义正确。

两个明确的保守边界：未知领域尚无安全批准的公开描述时，返回 public_descriptor_unapproved；任意 hard_constraints 尚无安全、明确的上游适配判断时，内部保留原文并返回 constraints_pending，零外发，不猜测约束已经满足。当前实现没有私有文本脱敏模型/关键词分类器。正文适配仅 GitHub；Web 只能发现候选，不能据标题/摘要解决缺口。

## 6. 共享预算与失败

整个 session 共用搜索、候选、正文、Reader、输出 token、总请求和费用上限；不是每 gap 重置。派发前 reserve：search 一次请求；body 最多两次请求及 64KiB；Reader 一次请求、1024 输出 token 及最坏费用。这里只是有界调用方参数，未声称默认值经过真实价格/质量调优，也未增加既有产品预算。

成功回执先验证全部实际指标，再完整结算可得量；cost/token 不可得保留最坏预留并标 unknown_measurement，不当作零。多个指标同时超额时先记录全部已知实际用量，最后统一阻断/报错，不因第一个超额漏记费用。无效回执保留 pending/最坏预留。实际观测超出预留的字节保留真实 debit，不静默截成预算内成功。正文流式拒绝 chunk 也可能已被观察到，因此 size failure 的实测 bytes_read 可超过上限一个 transport chunk；该 chunk 不进入正文缓冲。

transport unknown 保留 pending/预留并停止整个 session，不 retry、repair、换身份；pending snapshot 恢复仍 blocked。已知 Reader 错误结算可得输出量、保留未知费用，以 reader_failed/reader_invalid 停止，不伪称 unknown。明确未派发可归还预留。无证据/候选、免费不足、约束待判、预算耗尽均保留明确 reason code。

既有搜索 `UnavailableResult` 没有 typed dispatch/usage 分类；本轮不从中文错误文字猜测，统一 search_unclassified 保留预留并保守停止，待后续 reconciliation。相同冻结 Run 的 URL 仅复用已核对 metadata/匹配 outcome 引用，不缓存正文、不自动探测移动版本，不把未审过的其他 outcome 算作已支持。completed 回放前核对四个来源 hash、检查时间、预算 usage 和精确需求集合；inspected metadata 额外核对 URL/仓库归属、RID/blob version、时间及 outcome 范围，拒绝错源缓存。首个失败保留具体 reason，后续未派发 gap 标 research_stopped，避免把已知失败误记 unknown。

## 7. RED/GREEN、回归及独立审查

证据位于 ignored `var/planning-v2-item5-implementation-20261008/`，保留原始 RED 与首次 GREEN，不以最后通过覆盖失败历史。

| 项目 | 结果与证据 |
|---|---|
| Research 行为先 RED | 16 FAIL / exit 1：research-red.log/xml；实现后首轮 16 PASS、首批 20 PASS，保留原证据 |
| 正文行为先 RED | 75 FAIL / exit 1：teaching-body-red.txt；最终新正文 83 PASS |
| Reader 协议先 RED | 11 FAIL，补公有描述隐私 2 FAIL；分别保留 reader-red、reader-privacy-red |
| 独立安全/汇总审查反例 | 短完整 chunk 及分段复制分别 RED 2 FAIL；reader-echo-red、reader-split-red 保留，最终 Reader 17 PASS |
| 预算/来源绑定合并 RED/GREEN | research-hard-red.txt：23 FAIL / 21 PASS → research-hard-green.txt：44 PASS；含多指标结算、错源 replay/cache、失败分类及 A/B+recommended 合并 fixture |
| 三个新定向套件最终整合 | final-targeted-2.log/xml：144 PASS / exit 0（Research44、Body83、Reader17）；首批 aggregate118PASS 保留 |
| 既有资源安全回归 | GitHub transport/predispatch/index + Tavily 75 PASS；与 Body 合跑 158 PASS，teaching-body-green.txt |
| 既有 Provider / 最小 fail-closed | capability23、goal31、shared JSON/transport4、generate/submit2，共 60 PASS；与当时 Reader13 合跑 provider-regression 73 PASS |
| Ruff | 新八个 Python 文件完整规则 PASS；既有 Provider 沿用基线 E701/I001 排除 PASS，无全文件风格重写 |
| collection/import | collection.log：279 项受影响测试收集 PASS / exit 0；执行共 279 个不同用例 PASS（新144 + 既有135），未重复全量 Backend |
| diff、最终保护审计 | git diff --check / cached diff PASS；820 受保护 tracked 文件除允许 Provider/progress 外不变，378 历史账本与 .env hash 不变；旧 progress 正文保留 |
| 独立汇总审查 | 首轮 FAIL，发现分段正文、组合超额费用、completed 错源回放三项 BLOCKER；同批最小修正及反例后有限复核 PASS，无剩余具体阻断 |

所有 pytest 进程预加载 SSL/httpx/httpcore 后禁真实 socket/getaddrinfo，禁额外插件并排除上层 PG conftest；MockTransport 是合成响应，不能当真实 API 或真实 Reader 语义通过。首次安全测试 harness 在 SSL 初始化顺序上失败，调整 guard 安装顺序后有效重跑。最终 runner 从 ignored 文件执行时未包含仓库 root import path，首次 collection error 保留在 final-targeted.log；补充 root path 后 final-targeted-2 成功。两者如实记录为验证环境问题，不算产品失败或真实网络调用。

主协调请求 Sol6.1/high；有界实现/汇总独立审查请求 Sol6.1/medium；URL/正文及 Reader 安全审计请求 Sol6.1/xhigh，符合当前 AGENTS 安全/预算/引用路由。实际解析均 NOT OBSERVABLE，不把角色名当实际身份，不改全局配置，不使用 max/Astra。最多两名同时业务 writer，各自文件所有权分离。

## 8. 未验证与 Item 7 接线义务

- 真实产品模型、GitHub/Web 搜索、Reader、DB 操作均 0；历史账本 183/280、unknown177/183 不重派、不覆盖。没有新 Run/Job/Draft/Plan mutation、migration、Worker/Runtime/UI 接线或公共 generate 开放。
- 真实 PG 行计数、浏览器、外部 API、安全联网验收、真实 Reader/教材语义、大规模质量/稳定性、全量 Backend、Planning 整链 E2E 均 NOT RUN。真实 MCP 只复用已有 scoped review，不开展新正文审读。Item 1 条件接受、Item 2 真实语义待整链的限制不变。
- Item 7 必须在任何派发前把 request identity、共享 reservation/state 与冻结 inputs/config 持久化，恢复 pending/unknown 时先 reconciliation；与已有总请求/费用账本、fence/cancel/receipt 绑定。typed snapshot 本身不是持久化恢复、真实用量计量或并发互斥。不能直接注册当前服务就宣称这些义务已经完成。
- 正式 Runtime 必须提供可信 catalog/free-access proof、已批准公开需求投影及必要硬约束判断，维护配置/来源冻结与缓存校验；不能把用户文本直接塞入查询/Reader，也不能靠失效或自报 proof 放行。
- Item 6 消费本结果时必须保留 unresolved required gaps，才能判断教材适配/教学可行性及课程角色。本轮没有 Curriculum、Stage、Primary/Supplement、Project Case Research 或 Item 7 正式接线。

本轮离线实现及独立审查通过，没有需要改变上位架构的阻塞。真实 Reader/教材质量验收和正式 Runtime 接线仍未完成；不得据此声称整个 Planning V2 已可用。

`PLANNING_V2_ITEM5_TEACHING_RESEARCH_COMPLETE`

`ITEM6_NOT_STARTED`

`STOP`
