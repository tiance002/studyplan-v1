# Planning V2 Item 6 — Curriculum Composition

本轮只实施离线课程编排合同、Application 和专用 Provider 协议，不创建正式课程实体。机械校验、合成输出测试与真实教学语义验收分开记录；最终结果以本文验证及独立审查章节为准。

## 1. 基线与边界

- Start HEAD：`b707ad8d667b2cd9c3f47ea87a7c5fa177ef2ad1`，分支 `feat/n1-resource-discovery`。
- Final HEAD：本报告随本轮实现一起提交；准确提交 SHA 由最终交付和本地 Git 历史记录，避免报告自引用 commit hash。
- 开始时 tracked tree clean；原有未跟踪 `.workbuddy/`、`design-preview/` 保留，未访问、修改或纳入提交。
- 权威为 `PLANNING_V2_ARCHITECTURE_CONTRACT.md`，复用 Item 1～5 冻结对象及已有 shared ResearchSession，不改变上游 Policy、审核映射、Schema 或 hash 算法。
- 产品模型、GitHub/Web 搜索、Reader、数据库调用均为 0。历史 183/280 及 unknown177/183 保留，不重派。
- 不实施 Item 7，不接 Worker/Run、API/UI、Draft/Plan、数据库、migration 或旧规划链；不 push、merge、deploy。

## 2. 实现与权威

| 文件 | 职责 |
|---|---|
| `backend/app/domain/planning/curriculum.py` | 冻结输入、来源与资料资格、CurriculumPlan 校验、稳定 hash、项目案例元数据 |
| `backend/app/application/curriculum_composition.py` | 单次编排、同一研究 session 的预留与失败传播、条件项目候选检查 |
| `backend/app/infrastructure/providers/curriculum_contract.py` | 专用 purpose/schema/Prompt，复用 Domain 形状和校验 |
| `backend/app/infrastructure/providers/openai_compatible.py` | 新 purpose 的有限预算、输入预检及输出校验；原 JSON/transport/unknown/截断路径复用 |
| 三份 `backend/tests/unit/test_curriculum*.py` | 领域、Application、Provider 离线反例及接口样本 |
| 本报告、`docs/implementation/progress.md` | 验证、限制与 STOP |

开发模型请求：主协调 Sol6.1/high，安全/预算/引用合同 Sol6.1/xhigh，有界 Application 实现 Sol6.1/medium，实体字段清点 Luna/medium。实际解析均 **NOT OBSERVABLE**；不把角色名当实际模型身份，不改全局配置，不使用 max/Astra。文件所有权分开，最多两名同时业务 writer，复用共享 Evidence Packet 和一次最终独立审查。

## 3. CurriculumPlan 与输入合同

入口为 `prepare_curriculum(profile, plan, coverage, research, reviewed_index, *, catalog_sources=(), project_cases=(), access_proofs=())`。先校验 ready Profile、Policy v2 冻结 Plan、与现有审核索引重新计算一致的 Coverage、精确 GapSet，以及 Research 的四个来源 hash 和原学习需求。不是通过标题相似度重新判断能力或覆盖。

Provider purpose 为 `planning.curriculum_composition`，schema 为 `CurriculumPlanV1`。模型输入只包含必要 Profile 事实、B 类能力及原 outcomes/前置、A 类身份、授权资料/案例引用、用户项目背景、约束和冻结来源 hash；不输入 raw goal、整套 Seed、教程正文或源码。输出上限为 8192，服从既有更低 practice/deployment/model 上限；官方 DeepSeek Flash 显式 non-thinking，不改模型和部署预算。

| 对象 | 字段及下游职责 |
|---|---|
| 输入来源 | profile_hash、capability_plan_hash、coverage_hash、research_hash、gap_set_hash、reviewed_index_hash、research_checked_at、research_budget_usage |
| CurriculumPlan | schema_version、input_hash、status、stages、carrier、project_study_requirements、unresolved、constraint_refs、source_limitations；服务端附加 compile_sources/materials/cases/context、case_findings、plan_hash |
| Stage | stage_id、title、role、order_index、why_now、what_to_learn、capability_ids、outcome_refs、prerequisite_stage_refs、knowledge、units、assignments、guidance、tasks、project_study_refs |
| Knowledge / Unit | stable_key/title/objectives/outcome_refs；知识关联 material_refs；单元关联 knowledge_refs 和有 outcome_refs 的 rubric |
| Assignment | material_id、PRIMARY/SUPPLEMENT/REFERENCE/CASE_STUDY、outcome_refs、reading_focus；事实身份/版本/证据由冻结输入解析 |
| Guidance / Task | previous_relation、learning_focus、comparison_focus、PracticeDelta 五项；任务目标与范围、outcome_refs、knowledge_refs、carrier/micro_exercise、验收文本及 outcome_refs |
| Carrier | user_project/starter、项目背景 hash、理由和描述、final_artifact/acceptance/outcome_refs |
| ProjectStudyRequirement | requirement_id、problem、whole_core/slices、outcome_refs、avoid_scope、expected_outputs、normal_behavior、failure_behavior、inputs_outputs、design_questions、selected_case_ref |

冻结对象输出新 JSON 副本，结果 hash 绑定课程和服务器案例检查记录；无时间戳/随机 ID 决定课程身份。引用采用确定性规范化，教学阶段和单元保留有意义的顺序。只有获准 B 类引用，required outcome 必须教学安排或明确 unresolved；材料不足、案例未解决及无法机械判定的硬约束不能被模型自报为 complete。

服务器附加的 `compile_sources` 保存原来源 hash 与研究检查时间/用量；`compile_materials` 保存实际引用材料的完整身份、URL、版本、章节、资格、访问证明和审核依据；`compile_cases` 保存被选中的合格案例；`compile_context` 独立完整保留必要 Profile 事实、原 project_context、硬约束、B 能力和 A 身份。模型不能提供这些字段。Compiler 不需要根据 material_id 猜测 URL/版本，也不需要从适配后的实践说明反推原项目背景。

| 代表输入 / 合成课程 | 结果与边界 |
|---|---|
| 已冻结 llm.api + mcp 的系统性路线 | 仅组合这两项获准能力，common_core 与 specialization 可组合，不要求四类阶段齐全；不替 Item 2 补能力 |
| 已会 Python + JSON CLI | 只教 json.cli；Python 作为 A 类前置满足，不增加基础/复习/检查或 Agent/MCP |
| 上游受信领域证据冻结的 Coding + RAG | 可组合两个 specialization；不修改 12 项 Policy、不恢复 Recipe，未知公开需求没有搜索授权描述时仍 unresolved |
| 实际 MCP roles/interfaces 审核 + 合成 minimal_connection 研究证据 | 两类材料同时进入 compile_materials，可形成结构 complete 的合成课程；不能据此宣称真实 MCP 实践教材或课程语义已通过 |
| 缺教材 / 缺 free-access proof / unknown-domain 资料未解决 | 原 outcomes 保留 unresolved、status=incomplete；不得伪造 PRIMARY 或 complete |
| whole_core / slices + 显式合成 bounded_reviewed 证据 | 正常/失败行为、输入输出、设计问题与学习产物可结构化；README/候选资格不能替代此证明 |
| 用户已有旅行 Agent + MCP project_usage=excluded | 保留原项目事实，MCP 仅 micro_exercise；不迫使主项目接入 MCP |
| interview | 当前成果验收可要求解释设计取舍、比较替代方案与失败案例，不新增面试阶段或能力 |

真实本地代表仍是 agent-application-v8，pack SHA256 `6171e7bbed660d3f1d81d0c65b7b102eef0c2ec8dd7a3c40e54d4e3093985d0b`，resource[13] 的 free_public 事实；source `src_mcp101_a7ca881ee83ac722491299cd` / version 2，section `sec_mcp101_09e62ff389cb388eb744e738`。只复用 Item 3 已审核 roles/interfaces，不自动覆盖 minimal_connection，不继承 v7 TOC 资格。`hash_scope=review_record` 明确保留，pack/review hash 不冒充正文 hash。

同 resource_id/version 的不同 qualification、访问状态或证据事实独立冻结；候选或未知访问的 outcome 不能借用另一条记录的 usable 资格。只有标题、目录、URL 或 published 状态不足以成为教学证据。这里机械核对身份和既有审核范围，没有重新阅读或审核正文。

完整及不完整合成课程 JSON 保存于 ignored evidence 的 `example-complete.json`、`example-incomplete.json`，显式标注非真实模型验收。完整样例一阶段同时引用两种资料；不完整样例一阶段保留 `mcp.roles / mcp.interfaces / mcp.minimal_connection` 三项 unresolved，没有伪造教材。独立导出脚本首次缺少 backend import 路径，纠正后完成，不属于产品失败或实际外部调用。

## 4. 项目学习、持续实践与共享预算

Project Study 先形成问题、`whole_core / slices`、outcome_refs、avoid_scope、expected_outputs，再处理案例。现有项目卡的 reviewed_candidate 学习范围说明不能自动取得源码行为审核资格。README/目录检查所得候选继续保持候选身份，不通过另一个模型或 Reader 升级。

用户自己的项目作为持续实践载体，与学习别人的案例分开。MCP 必要学习与 project_usage 分离，主项目不适合采用时使用 Micro Exercise。Interview/Portfolio/Production 只能影响当前能力的成果和验收，不能新增课程能力。

条件搜索复用同一 `ResearchSession`，没有第二套账本。既有 GitHub `.find` 最多一次 HTTP；`.inspect` 最多 README 加两个文本章节，即三次 HTTP/256KiB/15 秒，必须按最坏界限在共享预算预留后调用。只使用获准 Policy outcome 的公开描述，不外发用户项目和研究问题原文。当前只通过离线 Fake/Mock 检查分支。

Item 5 的 completed result 绑定当时 budget_usage；Item 6 继续消费同一 session 后不能把它作为原 Item 5 completed replay 重跑。当前是向前消费冻结结果，不是已经实现持久化重启或跨 Worker 幂等。

单次课程调用预留真实 Provider 输出 cap、总请求和调用方给出的最坏费用界限，不占 Reader 次数。明确未派发才归还；已知失败结算可得输出用量并停止；费用不可得保留最坏预留。Unknown 保留 pending 并冻结 session。若 unknown 同时携带可信的已观察 token/检查字节超额，只对本次预留以上部分抬高公共 usage 下界，不弹出 pending、不二次派发。Item 7 reconciliation 必须识别这个已抬高下界，避免重复结算。

已有合格案例但模型尚未选择时，返回 `case_selection_pending`，保持 incomplete；不把 qualified case 写成新的候选、不搜索、不额外调用模型。新 GitHub 检查仅产生 reviewed_candidate，不能自动回写 selected_case_ref 或改变课程完整性。

## 5. 与 Item 7 的接口

Item 7 必须只做确定性编译，不重新决定能力、阶段、资料或实践范围。当前输出并非可直接确认的正式 Plan；incomplete 或未审核限制不能绕过将来的发布门禁。

现有实体承载核对：PlanStage 使用 stable_key；KnowledgeNode 使用 stable_key/objectives/content_version；LearningUnit 使用 stable_key/objectives/rubric/rubric_version；学习指导沿用 why_now/previous_relation/learning_focus/comparison_focus/PracticeDelta；任务使用 stable_key/goal/in_scope/out_scope/acceptance 及知识关联；教材安排使用 source_ref/section_refs/source_version/role。新的课程逻辑角色与旧实体 section_kind 是不同概念，未来 Compiler 必须显式决定合法映射，不能把逻辑角色直接塞入旧 enum。

本轮不写数据库实体，不伪造 node_id、unit_id、task_id、PlanRevision 或源码文件行号。Existing source/section identity 与将来教学实体 stable identity 不能凭标题相似度视为同一个知识实体。候选 stable_key 是本次课程语义键，不声称已复用已发布教学实体；未来 Compiler 按冻结映射建立版本实体和关联。

阶段 order_index 与有序 units/tasks 可确定性形成既有阶段/单元/任务顺序；知识目标、rubric、验收和知识关联均有结构化字段。PracticeDelta 字符串可逐项映射为现有列表表示，材料角色可确定性映射为既有小写 role。项目学习 requirement 不冒充现有 SourceSlice 的具体 files/call_chain；没有源码审核时不能编造 reviewed files。逻辑角色、项目学习及来源限制的正式持久化表示和 Draft 发布门禁仍由 Item 7 明确实现。本轮只提供冻结、足够细的输入，没有验证实际 Compiler 或宣称其已可运行。

## 6. RED/GREEN、定向回归与独立审查

证据位于 ignored `var/planning-v2-item6-implementation-20261008/`，保留 RED 和先前失败，不用最终 GREEN 覆写原记录。

| 检查 | 结果 |
|---|---|
| Domain RED/GREEN | 初始业务 stub：31 FAIL（domain-red.txt）→ 初始 31 PASS；引用乱序反例 1 FAIL / 50 PASS（domain-order-red.txt）→ Domain 51 PASS |
| Application RED/GREEN | 有效 compose stub：25 FAIL / 0 collection error（app-red.log/xml）→ 25 PASS；unknown 检查已观察超额：1 FAIL → 26 PASS |
| Provider RED/GREEN | 新 purpose/输入预检 2 FAIL（provider-red.log/xml）→ 最终 13 PASS；涵盖有效响应、严格输入、lower cap、unknown/server、截断、JSON/输出合同错误与无敏感回显 |
| 独审反例 | 已有合格案例超集未选择路径、unknown 已观察输出超额，两项各 RED 1 FAIL（app-review-red.log/xml）→ App 28 PASS |
| 最终新三套件 | final-targeted-2.log/xml：92 PASS（Domain51 + App28 + Provider13），exit 0；初次统一 92 PASS 也保留 |
| 受影响既有合同 | provider-regression.log/xml：77 PASS，exit 0；Capability Provider23、Goal Provider31、Reader17、共享 JSON/预算/transport4、generate/submit fail-closed2 |
| import / collection | collection.log：169 tests collected，exit 0；对应本轮执行的 169 个不同受影响用例，无全量 Backend 回归 |
| Ruff | 六个新增 Python 文件完整规则 PASS；既有 Provider 沿用原 E701/I001 基线排除 PASS，不做全文件格式重写 |
| diff / 保护 | PASS：829 个原 tracked 文件中，除允许 Provider 小改外 828 个 hash 不变；378 个历史账本、.env hash 及旧 progress 全文不变；精确九文件范围匹配，staged diff --check PASS，Git 规范化后的旧 progress 全文后缀保留 |
| 独立审查 | PASS：首轮两项具体阻断已修；最后源码差异、报告/progress 与 92/77/169、Ruff、staged diff 证据均有限复核，无剩余具体阻断。最终文档 SHA 清单在报告定稿后刷新，不需要重跑业务测试 |

统一 Ruff 首次 FAIL 为 Domain import 顺序和局部闭包 B023；改为有界迭代依赖遍历并整理 import，最终 92 项重新通过。App 的独审增量 import 排序失败也保留，修后 PASS。没有因验证工具失败更改业务范围。

所有 pytest 进程先加载 SSL/httpx/httpcore，再禁止真实 socket/getaddrinfo，禁额外插件并排除上层 PG conftest；MockTransport 只返回合成响应。Item 1～5 接口通过真实领域校验、CoverageEvaluator/extract 和 Item 5 离线 fixture 贯通；没有把 Fake Reader/模型调用算作真实外部验收。结构通过不证明标题、指导或课程生成文本在教学上充分；自然语言约束在没有可信适配事实时保守 incomplete，不让模型自评放行。

## 7. 未验证与剩余风险

- 真实模型能否生成教学上合理、连贯、范围适当的课程：NOT RUN。Fake/Mock 不证明课程质量。
- 真实 GitHub/Web/Reader、真实 PG 行计数、浏览器、整链 E2E、全量 Backend：NOT RUN。
- Item 1 条件接受及 Item 2 真实语义待整链验证的限制不变。
- Item 5 Web 仍只能发现候选，没有新的 Web 正文适配器；任意自然语言硬约束的教学适配没有被规则分类器或模型自评证明。
- Item 7 仍须在派发前持久化请求身份、冻结输入/config、共享 reservation/state，并绑定既有总账、fence/cancel/receipt；pending/unknown 恢复先 reconciliation。内存对象和 snapshot 不证明持久化恢复或并发互斥。
- 现有项目卡不自动证明具体源码正常/失败行为。新增 qualified 合成案例只用于算法反例；没有开展新教材或项目语义审核。

本轮没有发现必须改变架构合同或上游权威才能完成离线实现的阻塞。真实教学质量与 Item 7 正式编译/持久化尚未完成；这些风险保留，不以机械 PASS 覆盖。

`PLANNING_V2_ITEM6_CURRICULUM_COMPOSITION_COMPLETE`

`ITEM7_NOT_STARTED`

`STOP`
