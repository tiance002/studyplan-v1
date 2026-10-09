# Planning V2 Architecture Contract

日期：2026-10-07。状态：**PLANNING_V2_ARCHITECTURE_CONTRACT_FROZEN / IMPLEMENTATION_NOT_STARTED / STOP**。

## 0. 合同地位、基线与本轮边界

本文件是 Planning V2 Item 1～9 的唯一跨模块上位合同。后续单项实施文档只能细化该 Item 的实现、证据和验收，不能另立目标分类、课程决策或发布权威；跨模块合同变化必须先明确评审、更新本文件，再实施。用户后续明确决定优先于本合同。旧规格、旧内容包和历史测试不是恢复旧 Planning 产品语义的授权。

基线 branch：`feat/n1-resource-discovery`；start HEAD：`2ea1bc5d37814d5cbacce49f2ae09a639b1d3fba`。本轮沿用用户指定的现有分支，不回退、重建或合并。基线 tracked 工作树干净；原未跟踪 `.workbuddy/`、`design-preview/` 不操作、不纳入提交。

当前事实与未来要求必须区分：Planning V2 **尚未实现**。普通生成在身份/项目 scope 校验后 fail-closed；Planning 页面只有 unavailable placeholder。旧 selector、fixed-route、semantic/alignment 主干及生产长图已删除。保留内容实体、Draft/Revision、学习/实践/助手及可靠性底座，不表示 V2 已可运行。事实来源为 [唯一当前进度](../implementation/progress.md)、[Residual Cleanup 的完整 HOLD 清单](../acceptance/planning-v2-residual-cleanup-2026-10-07.md) 和 [Legacy Removal](../acceptance/planning-legacy-removal-2026-10-07.md)，并按本节 HEAD 只读核对源码。

本轮只创建本合同、只读审计并本地提交 `docs(planning): freeze v2 architecture contract`。不实现 Item 1，不写 Prompt、DTO、API、migration、Seed，不改 placeholder、Worker、Provider，不接 Reader/WeKnora，不调用产品模型/搜索，不写数据库，不 push/merge/deploy。未来对象与字段均是逻辑合同，**不是已经存在的运行时 symbol、公开 DTO 或已验证 schema**。

本轮路由：主协调请求 `gpt-6.1-sol/high`；机械路径/符号清点请求 `gpt-6-luna/medium`；实际调用链、持久化和独立反向审查请求 `gpt-6.1-sol/medium`。仅具体未解矛盾、高风险合同变化或关键证据冲突才请求 `gpt-6.1-sol/xhigh`；禁止 Luna xhigh、Sol max、6Astra。不修改全局配置。请求参数不能证明实际执行模型；实际解析无工具证据时统一记 **NOT OBSERVABLE**。文末的 model calls=0 指产品模型调用，不包含开发协调/审查代理。

## 1. 产品总目标

用户提供想学什么、当前已经会什么、最终想完成什么、已有项目（如有）和必要限制。StudyPlan 理解目标，确定本次真正需要学习的能力，复用已有高质量教学内容，只针对真实缺口研究资料，组织 Common Core、专项、项目学习与持续实践，生成可学习、可实践、可验收的路线。用户确认后形成正式 Plan；后续真正改变目标时复用同一流程重新规划。

**Goal 决定学习需求；Capability 决定学什么；Content / Resource 决定拿什么教；Curriculum 决定怎么教；Execution 只负责可靠地落库。**

下文九项是逻辑职责，不是九个微服务、九张表、九个 Agent 或九次模型调用。应用层拥有编排和状态转换，Domain 拥有业务规则，Ports 隔离 Provider/Discovery/DB；UI 只提交用户意图与呈现服务端事实。

## 2. 数据流、依赖与唯一接缝

```text
Frontend
  ↓
API（身份 / project scope / 输入边界）
  ↓
Planning V2 Orchestrator（逻辑职责，尚无运行时实现）
  ↓
1 Goal Requirement Analysis
  ↓ GoalRequirementProfile
2 Capability Planning
  └─ 仅存在真实领域不确定性：一次 bounded Domain Verification
  ↓ CapabilityPlan（冻结）
3 Reviewed Content Coverage
  ↓ CoverageResult
4 Resource Gap Extraction（确定性）
  ↓ ResourceGapSet
5 Teaching Resource Research（仅真实缺口；无缺口可跳过外部研究）
  ↓ ResourceResearchResult
6 Curriculum Composition
  └─ 确实需要且缺候选：ProjectStudyRequirement → conditional Project Case Search
       └─ 结果只返回本次 Composition，不另启完整规划
  ↓ CurriculumPlan（完整教学安排 / 冻结）
7 Planning Execution（validate → compile → freeze → persist）
  ↓ PlanDraft → 用户编辑 / approval → PlanRevision
Learning / Practice / Summary / Assistant

横向依赖：
Content Index       → Coverage / Curriculum
Resource Discovery  → Research / conditional Project Case Search
LLM Provider        → Goal / Capability / Reader / Curriculum
Worker / Run / Receipt → 整条异步流程的可靠性
DB / RLS / CAS      → Execution / Plan / Revision

8 Replanning：局部变化 → existing revision/change；语义变化 → 复用 1～7
9 UX：呈现以上事实；不另建业务推导链
```

横向箭头表示依赖方向，不授予下游修改上游权威的权限。研究发现冲突只能报告 unresolved evidence，不能形成 Coverage → Capability 或 Resource → Goal 的隐式反馈循环。确需更改已冻结能力时，结束当前决策分支，经明确目标/能力修订后产生新版本，从受影响边界重新运行；不静默改已完成的输出。

当前可定位接缝（只读事实，不是 V2 接线完成声明）：

| 接缝 | 当前路径与 symbol | V2 责任及限制 |
|---|---|---|
| 用户事实 | `backend/app/domain/planning/intent.py::GoalSpec`、`goal_spec_payload` | 已有 target/scope/desired_depth/starting_point/outcome_purpose/constraints 六类事实；没有 project_context 字段。Item 1 明确输入承载与映射，不假称现有 GoalSpec 已支持它 |
| 生成门面 | `backend/app/application/plan_service.py::PlanService.generate`、`submit_generation` | scope 后拒绝；仅对应 Item 完成评审后可接入新流程，不以内部执行方法绕过公开门禁 |
| 内容实体 | `backend/app/domain/catalog/models.py::KnowledgeNode`、`KnowledgeRelation`、`LearningUnit`；`backend/app/infrastructure/db/planning_catalog.py::PgPlanningCatalog.materialize` | 实体与稳定身份保留；现有 materialize 的旧输入 shape 必须审查，不能直接传 V2 对象 |
| 内容/资料证据 | `backend/app/infrastructure/db/public_resource_catalog.py::PgPublicResourceCatalog`；`backend/app/application/resource_discovery_contract.py::DiscoveryEvidence`、`ContentEvidence` | 版本、章节、hash、检查事实可映射；候选/README/目录检查不自动成为 reviewed outcome coverage |
| 外部资源 | `backend/app/ports/resource_index.py::ResourceIndexPort`、`ResourceInspectionQuery`；`backend/app/infrastructure/resources/github.py::GitHubResourceIndex`；`backend/app/infrastructure/resources/tavily.py::TavilyResourceIndex` | 复用 scope/URL/受控读取/失败回执；现有 topic_overlap/recommended_role 不作为 outcome 覆盖证明，不承诺现 inspect 已提供 Reader 所需正文链 |
| 教学呈现 | `backend/app/domain/planning/guidance.py::LearningGuidance`、`PracticeDelta`、`SourceSlice` | 优先映射教学指导、实践增量和案例切片；不让旧 `stage_guidance` 决定 V2 课程 |
| 草案/正式路线 | `backend/app/domain/planning/models.py::PlanDraft`、`PlanRevision`、`build_revision_snapshot`；`backend/app/infrastructure/db/plan_repository.py::PgPlanRepository` | 复用 current 引用、编辑、指纹、CAS 与原子发布；新合同字段逐项证明持久化与读回 |
| 页面 | `frontend/src/features/planning/PlanningPage.tsx::PlanningPage` | 当前只占位；Item 9 先 HTML 批准，再 React 与截图评审 |

## 3. 九项逻辑职责

### Item 1 — Goal Requirement Analysis

输入为 GoalSpec / 用户自然语言与明确补充信息。保留 target、scope、desired_depth、starting_point、outcome_purpose、constraints、可空 project_context；不丢失原始事实及其最小来源定位。输出 **GoalRequirementProfile**：target_summary、required_requirements[]、hard_constraints[]、learner_claims[]、project_context、outcome_purpose、clarification_questions[]、status。范围与深度必须以规范化事实进入合同，不能只压成摘要；完整消费关系见第 6 节。

每条 Requirement 有稳定引用 identity、要求文本、`explicit / inferred_required`、最小 source reference / rationale。推断仅补充实现目标不可缺少的需求，不能产生 recommended 技术清单。冲突或关键事实不清时输出一小批可理解的澄清问题，非 ready 状态不得进入能力冻结。澄清答案由 Item 1 形成新 profile 版本；下游不解析 raw goal。

本项不产生 Stage，不搜资源、不选 Seed、不加入 MCP/RAG 等课程政策，不因 interview 自动加阶段。用户说“我会 Python”即作为当前规划事实接受；不测试 Python、不安排 Python Review、不搜 Python 教材、不推断其其实不会。用户后续发现不会，自行调整学习或明确发起新请求，不属于首次规划器的自动评估职责。接受声明不等于写入 Knowledge VERIFIED 或 mastery。

### Item 2 — Capability Planning

将 ready 的 Profile 转成“为了实现目标，需要具备哪些能力”。CapabilityPlan 区分 A：目标需要但用户已明确声明会的能力；B：本次真正需要安排学习的能力。A 保留为已满足前置和可追溯事实；只有 B 的 learning outcomes 进入 Coverage、Gap、Research 和 Curriculum 的学习安排。不能借依赖展开、Common Core 或 DEEPEN/REVIEW 再插回 A。声明按明确语义范围匹配，不用“会 Python”推断用户已会全部其他领域能力，也不以此反向否定其 Python 声明。

已知能力使用小型、版本化、只读 Capability Policy，描述 capability_id、title、core learning outcomes、real prerequisites、curriculum policy、default depth。不是新数据库、CRUD 平台或另一套固定方向选择器。策略版本随 Plan 来源保留；新版本不改旧 Run。

计划项至少表达 capability_id、learning_requirement、project_usage、desired_depth、learning_outcomes[]、requirement_refs[]、policy_refs[]，并明确 accepted_known / needs_learning 处置及真实 prerequisite refs。`learning_requirement` 表示本次 required / recommended 教学重要性；`project_usage` 单独表示目标项目是否需要实际使用，不能从学习 required 推导项目必用。没有真实目标/政策根据的 recommended 能力不加入。

对未知领域，若“目标所需能力/关键前置”存在真实不确定性，允许一次 **bounded Domain Verification**，技术事实优先官方文档、specification、必要时成熟源码。它属于 Item 2 冻结前的有界子步骤，只修正目标所需能力，不搜教材、不借机扩课；结论、证据 refs、限制与决策留存。验证仍不足时澄清或显式 unresolved，不无限调查。完成的验证在重启时复用，不能再次派发。

系统性 Agent 学习路线的 MCP 学习是 StudyPlan Curriculum Policy required，不是“所有 Agent 项目必须使用 MCP”的技术事实。最终项目可以不使用 MCP。用户明确排除 required 政策时暴露冲突并请求决定适用范围/路线类型，不能静默覆盖用户排除或把不满足政策的路线宣称为该系统性路线。最终决定形成新 Profile/CapabilityPlan 版本后再继续；资源层无权裁决。

本项不生成 Stage、Resource 或 NEW / REVIEW / DEEPEN / COMPARE 教学关系；后者只由 Item 6 在获准的学习集合内决定。

### Item 3 — Reviewed Content Coverage

输入为 B 学习集合与已有 Content / Knowledge / Resource / Evidence 索引。仅有 Seed/Content JSON、URL、标题相似、目录或候选推荐标志不构成 reviewed coverage。必须有足够的现有 review/source evidence，以及稳定 learning outcome ID → reviewed content / section refs 的明确映射；不靠标题猜覆盖，不调用模型自由判断覆盖，不联网。

按 learning outcomes 确定性输出 full / partial / none、covered_outcomes、missing_outcomes、content_refs；两集合不得交叉且完整划分本次输入。full 仅表示在明确版本和审核范围内全部覆盖，不能代表学习者已掌握。无可信映射即未证明覆盖，登记 missing；不能把旧包整体标 reviewed 来追绿。不改 CapabilityPlan，不新建课程、embedding/vector DB 或 0～100 分数。

### Item 4 — Resource Gap Extraction

确定性转换 CapabilityPlan + CoverageResult → ResourceGapSet。条目包含 capability_id、missing_outcomes[]、importance（required / recommended）、desired_depth、requirement_refs[]。只取 B 中仍缺失的 outcomes；A 永不形成资料缺口。full 无 gap；partial/none 精确继承缺失项。空 gap 是合法结果。本项没有模型、搜索、新表或 UI，不做 domain_gap/content_gap 等复杂分类。

### Item 5 — Teaching Resource Research

只为真实 missing outcomes 研究教学资料，首先复用已有 reviewed resource。工程类默认候选发现顺序为 **Reviewed Resource → GitHub 教学资源 → Web 教程/课程 → 官方资料补充精确行为和版本细节**。这是工程类教材发现政策；技术事实验证可直接官方优先，其他领域不套 GitHub First。

最终教材按教学连续性、缺失 outcomes 覆盖、当前学习者适配、正文免费、示例/实践质量、版本适配比较。GitHub 来源本身不代表高质量；质量和覆盖基本相当时中文优先，不能为中文降低明显的教学质量。输出 ResourceResearchResult 给 Curriculum，不能新增能力、删 required 能力或提前决定 Primary/Supplement 等教学角色。

公开正文可临时读取，长期只留资源 identity、URL、可得 version/commit、section/location index、content hash、outcome mapping、review result、limitations、checked_at 及必要 evidence/chunk identity。不得建设全文教程库、默认长期保留整套正文，或把全文写进业务 DB、Run/checkpoint/log/receipt。临时正文应有有界生命周期与清理机制，异常日志不得回显正文；实现 Item 5 时证明其边界，不在本轮新增缓存服务。

Reader 可用低成本/免费 Provider，仅执行 **真实正文 → outcome evidence**。无工具执行权、路线修改权、DB 修改权；外部正文均为 untrusted content，正文里的命令/提示不能升级为系统指令。Reader 必须引用本次真实读取的 evidence/chunk identity。程序在正文可用时校验存在性、资源归属、identity/hash；正文释放后只保留验证回执/定位，不宣称仅凭 hash 就再次验证了正文。需要重新核对时按同版本受控读取；内容已变或无法取得即保留不确定性，不伪造历史证据。引用合法不证明语义正确；明显冲突或关键证据不足才请求高质量模型复核，不能每个候选都强模型审读。

整个 Planning Run 共享有界研究预算，覆盖搜索、读取、Reader、必要复核及条件 Project Case Search，并与 Run 总费用/请求预算联动；Domain Verification 也受 Run 总预算约束。不能按 gap/candidate 无限叠加。dispatch 前预留，完成回执后结算，unknown 保留待 reconciliation 的额度，重启不重置。搜索/Reader 的具体数量和上限留待真实验收后配置，不在合同写死最佳数字。无适合免费教材或预算用尽时保留未解决 required 缺口与原因，不编造资源、不降成“已覆盖”；必要教学无法成立时不得声称路线可学习或放行确认。recommended 缺口可显式保留供用户决定，不机械阻断无关能力。

### Item 6 — Curriculum Composition

输入为 Profile、冻结的 CapabilityPlan（B 学习集合及 A 已满足前置）、reviewed content、ResourceResearchResult 和用户项目。**只有本项决定** Stage 边界、顺序、能力合并、Primary / Supplement / Reference / Case Study、实践增量及是否需要 Project Study。不能根据资源热度反推新增 required 能力；不能因找不到教材删除 required 能力。

教学角色为 Common Core、Specialization、Project Study、Integration，优先映射现有 Stage/Guidance/Resource/Practice，不预设新表。Common Core 是本次需学习的共性能力，不是每人固定复习课。Specialization 如 RAG/Coding/Workflow/Browser 按真实依赖与教学连续性形成合理少量阶段，不是“一 Recipe 一 Stage”。教学关系只作用于 B；不得把 accepted_known 能力安排为 NEW/REVIEW/DEEPEN/COMPARE。

Project Study 可无。有界小型真实项目用 **whole_core** 学完整核心行为链；成熟大项目用 **slices** 按工程问题学习切片。大小按“学习范围能否在有界阶段完整理解”判断，禁止固定 LOC 门槛。确有必要时先形成小型 ProjectStudyRequirement：问题、whole_core/slices、avoid_scope、expected learning output，并关联已授权 outcomes。先复用/检查 reviewed Project Candidate 或用户明确指定项目；只有缺合格候选才触发 GitHub Project Case Search。搜索不扩大该 requirement；失败保留缺口。该条件子步骤完成后继续当前 Composition，不做两次完整课程规划。

用户自己的项目优先作为 **Continuous Outcome Carrier**。Project Study 是看别人怎么实现；Practice 是把知识应用到自己的项目，两者在合同与 UI 均分开。不适合加入主项目的能力用 Micro Exercise，并说明预期产物。Interview / Portfolio / Production 主要影响项目范围、实践深度、artifact expectations 和最终验收；不能机械增加面试、Kubernetes 等阶段。

CurriculumPlan 必须完整到无需 Execution 补课程：阶段及依赖、why now/what to learn、教材章节与角色、知识/单元安排、实践 baseline/increment/preserved/validation/reuse、任务/outcome links、必要案例、最终项目/验收、未解决缺口。映射已审内容优先复用稳定 identity。

输出过长可在**能力、阶段边界、资源和实践范围已冻结**后分段补齐教学内容；每段绑定冻结版本/hash 和所属阶段。只补内容，不改变规划决策；完成片段复用，冲突/超范围拒绝。未完整补齐不生成可确认 Draft。分段属于 Item 6，不得在 Item 7 改名为 outline/structure/practice 模型协议。

### Item 7 — Planning Execution

职责严格为 **validate → compile → freeze → persist → Draft → approval → Plan**。CurriculumPlan 是用户编辑前的课程语义权威；Execution 不再调用旧 outline、structure、practice 模型，不做课程决策，不修饰缺口为通过。

Compiler 通过确定性映射输出现有 Knowledge、Relation、Stage、LearningUnit、Resource Assignment、LearningGuidance、Practice、Task links、Draft/Revision。先验证引用、required requirement/outcome 完整性、真实 prerequisite、来源/版本、scope、教学完整性及安全约束；再编译并校验无丢失/替换。若现有实体无法表达语义，报告证据并评审最小扩展；禁止悄悄截字段、随意挤进文字、调用模型补齐。V2 不构成重建公共 knowledge 的理由；相同稳定语义实体优先复用，内容与历史版本分别处理。

复用 Worker、Run、Job、Attempt、Receipt、budget、fence、cancel、unknown/reconciliation、checkpoint、CAS、publication、RLS、source validation 的可靠性职责，具体拆分见第 7 节。提交/恢复/保存前绑定合同版本、输入/output hash、refs、决策与 dispatch identity；中间状态仅留必要合同与追溯信息，资源正文不进入 Planning state。Run 完成持久化草案后以 succeeded + none 结束，普通批准由业务发布事务处理，不恢复旧 waiting_user graph。

已成功完成步骤在 Worker restart 时必须复用持久化结果/receipt，不再次调用模型或搜索。receipt 成功而 checkpoint 未落时应校验并重建进度；unknown 不 blind retry、不改成 known failure，先 reconciliation；失败不能自动新建 Run 重派。late result 仍受 claim/lease/fence/cancel 防护。截断单独识别为截断失败，不能当普通 JSON repair；仅已知、适用的错误可在原有 bounded repair、receipt、预算边界内处理，不扩大 repair 上限。

优先现有 Run/Job/checkpoint/schema，但不承诺绝对无 migration。真实 schema、容量、hash 覆盖或事务一致性不足时，由对应 Item 先提交字段流向/容量/一致性证据与最小 migration 理由再评审；本轮 migrations=0。既有发布 migration 不改写。

### Item 8 — Replanning & Revision

不开发第二套 planner。不改变目标/能力语义的 Local Change 复用现有 revision/change 基础，仍须完整校验、用户决定、CAS 与历史。改变 target、scope、depth、required capability、specialization、project direction 或 hard constraint 的 Semantic Replanning 复用 1～7；不经旧 selector/generated-operation 重新分类。

已发布 Plan 保持 Revision 历史，完成的过去阶段及其 Summary/Practice/来源快照不倒改。未来部分重新规划，以精确稳定 identity 和原 revision 绑定保留历史；不以相似标题重映射过去。新 prerequisite 若只由过去尚无证据的内容满足，必须暴露冲突，不伪造“已完成/已掌握”，也不自动重测 accepted learner claim。

用户编辑 Draft 后，确认对象为**当前 draft revision/hash**，不能要求与最初 CurriculumPlan 字节级 hash 相同。原 Curriculum hash 只证明来源；编辑结果经 required requirement、真实 prerequisite、安全和教学完整性校验后，形成新 Draft hash 与验证结果。语义改变转回 1～7；非语义编辑可以通过新 hash 确认。过期 hash、expected_version 冲突、无效来源或删除 required 内容均拒绝，不能执行模型“修回”用户稿。正式发布仍是单一原子事务与幂等结果，不由 checkpoint 代表业务已发布。

### Item 9 — Planning UX & Acceptance

主页仅 Goal 输入、补充信息按钮、生成计划；补充信息放 Dialog/Drawer。需要澄清时只显示一小批人类可理解问题，不显示 Run/requirement/Seed ID。进度文案为“正在理解目标 / 正在规划学习内容 / 正在检查资料 / 正在组织路线 / 正在生成草案”，不暴露内部模型协议。

Draft 显示学习目标、当前起点、路线阶段、为什么现在学、学什么、Primary 教材、Practice、可选 Project Study、最终项目和必要未解决缺口。明确区分“真实项目拆解学习”与“自己的持续实践”。缺口和失败不伪装为生成完成；确认仅对服务端当前有效 Draft/hash。

实施顺序固定 **HTML Prototype → 用户批准 → React → Browser Screenshot review**。DOM/测试通过不能代替截图视觉评审；原型批准不等于端到端事实完整、可靠性或负责人产品接受。当前 placeholder 本轮保持。

## 4. Single Authority

| 权威对象/阶段 | 唯一拥有者 | 下游可做 | 下游禁止 |
|---|---|---|---|
| GoalRequirementProfile | Item 1 | 读取规范化需求/事实/ref，报告不清楚处 | 再读 raw goal 做第二套分类/路由；从用途推课程 |
| CapabilityPlan | Item 2 | 引用冻结能力和 outcomes、已满足前置 | 因缺教材删除 required；资源新增能力；让包/关键词反选目标 |
| CoverageResult | Item 3 | 消费已有审核映射及缺口 | 标题猜测、模型自由猜、用研究结果篡改原 coverage |
| ResourceGapSet | Item 4 | 研究精确缺失 outcomes | 扩大 gap 或把 A 变成缺口 |
| ResourceResearchResult | Item 5 | 为获准 outcomes 提供资料证据与限制 | 改能力/目标、决定课程阶段、把合法引用当语义正确证明 |
| ProjectStudyRequirement | Item 6 | 条件搜索满足其有界问题的案例 | 无条件搜索；搜索方扩大课程范围 |
| CurriculumPlan | Item 6 | Execution 校验/编译/冻结；UI 显示 | Execution 重规划、补课程或调用旧模型链 |
| 当前编辑 Draft | 用户意图 + Item 7/8 服务端校验 | 以当前 hash 确认 | 用初始 curriculum hash 拒绝所有编辑；UI 自行认定合法 |
| 正式 PlanRevision | 原子 publication/current reference | 下游学习/实践读取当时版本 | 以 Run/checkpoint/最大 revision 冒充当前 Plan；倒改历史 |

raw goal 仅供 Item 1 与必要来源审计保存，不作为下游提示词里的第二套决策输入。下游可呈现 target_summary/规范化事实；source reference 是定位依据，不授予重新解释目标的权限。不得把 Seed、UI 文案、发现候选评分或 Reader 输出变成新权威。

## 5. StudyPlan Product Policies 与技术事实

以下是产品政策，**不是外部技术世界的普遍事实**：系统性 Agent 路线要求学习 MCP；正文教程免费（API 实践可以收费，但仍须费用授权）；工程类候选 GitHub 教学资源优先；同质量中文优先；用户明确声明已会的能力直接接受；用户项目优先作为持续实践载体；面试主要提高成果/项目验收，不默认增加阶段。

Policy 必须有版本/ref 和适用条件。技术事实验证只回答行为、版本、所需能力和真实前置，不证明某项产品政策普遍成立。政策与用户 hard constraint 冲突由 Item 1/2 暴露并获得明确决定；不能由 Resource 或 Execution 静默变更政策、覆盖用户或伪称满足。

## 6. Producer / Consumer Matrix

本矩阵是**未来必须实现并验证的实际消费合同**，不是当前 V2 已接线声明。I1～I9 对应上文 Item；“校验器/Compiler”是明确责任而非已存在 symbol。每个字段组中各字段必须被所列 Consumer 实际读取；只有追溯用途的 hash/ref 也须由恢复、验证或来源读取消费，不能写而不读。Item 验收需给出具体生产路径/函数与 DB→API→UI 读回证据；若不能实现所列 Consumer，应删除非必要字段或先评审合同，不能留“未来可能用”。

Persistence 约定：**C** = 必要的版本化 Run/checkpoint 合同或已有持久化引用（具体容器待 Item 证明）；**R** = 现有资料 metadata/review/index 或有界合同记录，不含全文；**D** = Draft 及其来源/验证快照；**P** = 正式 Revision/source snapshot/current 引用。C/R/D/P 不代表新增四张表。共同的 contract version/hash、父对象 refs 由生产者冻结，恢复/validator 消费；scope 来自服务端身份，不由模型填写。原始目标审计内容仅 I1 使用。字段内的 identity/ref 都是精确引用，不能靠相似标题补全。

| Object / Field | Producer | Persistence | Consumer（必需） | Can Modify? | User-visible? | Trace / Authority |
|---|---|---|---|---|---|---|
| GoalRequirementProfile：target_summary、scope、desired_depth | I1 | C→D/P 目标快照 | I2 需求/深度；I6 路线；I9 目标展示 | I1 新版本；语义修改走 I8 | 是，人类文本 | 用户事实/ref，禁止 raw goal 二次分类 |
| required_requirements[]：requirement_id、text、explicit/inferred_required、source_ref、rationale | I1 | C→D/P 必要追溯 | I2 requirement_refs；I7/8 required 完整性；I9 必要解释 | I1 经澄清版本化 | 文本/必要理由；内部 ID 隐藏 | 原始事实/推断理由，不含课程政策 |
| hard_constraints[]：约束内容及 source_ref | I1 | C→D/P | I2/5/6 适配；I7/8 硬约束校验；I9 冲突展示 | 明确用户决定后 I1 新版本 | 是 | 用户约束权威 |
| learner_claims[]：声明内容、source_ref；starting_point | I1 | C→D/P | I2 A/B 处置；I6 已满足前置；I7/8 禁止重加；I9 起点 | 用户纠正后新版本 | 是 | 声明直接接受，不写 mastery |
| project_context（可空）、outcome_purpose | I1 | C→D/P | I2 project_usage；I6 carrier/实践验收；I9 项目展示 | 用户决定后新版本 | 是 | project_context 不假称已有 GoalSpec 字段 |
| clarification_questions[]、status | I1 | C | Orchestrator 门禁；I9 澄清；I1 消费答案 | 仅 I1 更新版本 | 问题/状态的人类表示 | 非 ready 不进入 I2 冻结 |
| CapabilityPlan：capability_id、title、learning_requirement、project_usage、desired_depth | I2 | C→D/P 必要快照/ref | I3/4 重要性/范围；I6 教学与项目；I7/8 校验；I9 能力说明 | I2 冻结前；之后新版本 | 是，ID 隐藏 | Profile 与 policy refs；学习必需≠项目必用 |
| disposition：accepted_known / needs_learning、learner_claim_refs | I2 | C→D/P | I3/4/5 仅 B；I6/7 禁止 A 变课程 | 仅依据新用户事实重新冻结 | 起点/需学习说明 | A 可满足前置，不能变教材任务 |
| learning_outcomes[]：outcome_id、text；requirement_refs[]、policy_refs[]（含版本） | I2 | C→D/P | I3 明确映射；I4/5 精确缺口；I6/7/8 覆盖与来源校验 | I2 冻结后只新版本 | outcomes 文本；IDs 隐藏 | 不用标题作为键 |
| prerequisite_refs；必要 Domain Verification decision/evidence_refs/limitations | I2（验证子步骤） | C→D/P 必要依据 | I6 排序；I7/8 依赖/版本校验；恢复复用验证 | 冻结前 I2；不由研究修改 | 必要前置/限制 | 真实前置与政策分开，验证最多一次 |
| CoverageResult：capability_id、full/partial/none、covered_outcomes、missing_outcomes | I3 确定性 | C | I4 生成 gap；I6 内容取用；I7 coverage 一致性 | 上游/审核索引版本变更后重算 | 必要缺口说明 | 输入 B 的完整分区 |
| content_refs：content/section identity、version、review/source evidence refs、outcome mapping | I3 读取已有索引 | C/R 引用→D/P | I6 教材章节；I7 来源/映射校验；I9 教材读取 | 更换输入版本后重算 | 教材/章节/来源 | Seed 存在不等于审核覆盖 |
| ResourceGapSet：capability_id、missing_outcomes[]、importance、desired_depth、requirement_refs[] | I4 确定性 | C | I5 限定研究与预算优先；I6/7 未解决 gap 校验 | 随上游重算，不手改 | 缺口的人类描述 | 只来自 frozen B + missing |
| ResourceResearchResult：resource identity、URL、version/commit（可空）、section/location index、content hash、checked_at | I5 | R/C→D/P 来源引用 | I6 选择/章节；I7 identity/hash/source；I9 教材链接；恢复校验 | 新检查产生新记录/版本 | 链接/版本/章节；hash 隐藏 | identity/hash 属同一读取资源 |
| outcome mapping、evidence/chunk identity、review result、limitations | I5 Reader 提取 + 程序核对 + 必要语义复核 | R/C→D/P 必要映射/限制 | I6 适配决策；I7 来源与未解检查；I9 限制；复核按 refs 读取 | 只记录新审读决定，不覆盖旧证据 | 覆盖/限制；内部 chunk 隐藏 | 引用真≠语义必真，不保存正文 |
| unresolved outcomes、reason（含预算/免费资源不足） | I5 | C→D/P | I6 可学习性；I7/8 确认门禁；I9 缺口展示 | 获得新证据后新版本 | 是 | 不能删 required 或编造教材 |
| ProjectStudyRequirement：problem、whole_core/slices、avoid_scope、expected_learning_output、outcome_refs | I6 仅必要时 | C→D/P 最终案例安排 | 条件 Project Case Search 限定范围；I6 候选选择；I7 校验；I9 案例说明 | I6 冻结前；不是搜索方 | 是 | 显式 required-by-curriculum 决策；缺候选才搜 |
| CurriculumPlan：stage identity/title/role/order、outcome_refs、prerequisite refs、why_now、what_to_learn | I6 | C→D/P | I7 Compiler→Stage/Knowledge/Relation/Unit/Guidance；I9 展示；I8 未来重规划 | I6 冻结后不可原地改；用户编辑是新 Draft | 是 | capability 集合是上界；Stage ID 映射确定性 |
| resource assignments：resource/section/version refs、Primary/Supplement/Reference/Case Study、order | I6 | C→D/P | I7→StageResourceAssignment/source snapshot；I9 Primary/章节；学习资源读取 | 同上 | 是 | 只能引用 I3/I5 或条件案例的有据候选 |
| knowledge/unit refs 与教学正文；practice 范围、baseline/increment/preserved/validation/reuse、task/outcome links | I6 | C→D/P 及既有实体 | I7→Knowledge/LearningUnit/LearningGuidance/Practice/Task links；Learning/Practice/Assistant | 冻结片段只补授权内容；之后编辑校验 | 是 | I7 不补课程，公共知识稳定 identity 优先 |
| continuous carrier / micro exercise、可选 Project Study 安排、final outcome/artifact expectations | I6 | C→D/P | I7→Practice/Guidance/案例映射；I9 两类项目分开展示；成果验收 | 冻结前 I6；之后 I8 | 是 | 用户项目与研究别人项目分开 |
| unresolved gaps、composition decisions、冻结版本/hash 与分段 refs（仅分段时） | I6 | C→D/P 必要限制/来源 | I7 完整性/确认门禁；恢复不重派；I9 限制；I8 来源读取 | 新版本/新增已校验片段 | 限制/理由可见；hash/片段ID隐藏 | 未补齐不能可确认 Draft |
| ExecutionManifest：合同/Compiler版本、上游 hash/refs、编译输出 digest、stable identity mapping | I7 确定性 | C→D/P 必要来源绑定 | 保存前校验；重启恢复；publication来源验证；I8 精确映射 | 生成即冻结，变化产生新 manifest | 否 | 禁止套旧 stage_skeleton shape |
| ExecutionManifest：step/request identity、budget reservation/usage refs、attempt/receipt refs、decision/checkpoint refs | Orchestrator/Worker + I7 可靠性流程 | 既有 Run/Job/Attempt/Receipt/C | dispatch guard、重启/unknown reconciliation、fence/cancel、费用核对 | 账本追加/受控状态转换；旧回执不覆写 | 只显示人类进度/错误 | 不能以 checkpoint 代替业务发布 |
| PlanDraft：scope/project、draft identity、revision candidate、current content hash、status、来源/约束/验证 refs | I7；用户编辑经 I7/8 校验 | D | I9 当前草案；edit/approve/cancel；仓储 CAS；I8 语义变更判断 | 允许合法编辑形成新 hash；来源不改写 | 内容/状态可见，内部ID隐藏 | 当前 hash 是确认对象，初始 Curriculum hash 是来源 |
| PlanDraft：goal/profile 事实、完整编译教学/实体 links、资源快照、practice carrier、未解限制 | I7 从 I6 编译 | D + 既有实体精确引用 | publication→P；API→React；Learning预览；I8 校验 | 仅合法用户编辑与重新校验 | 是 | 必须证明现 schema/序列化/hash 不丢字段 |
| PlanRevision：revision identity、current ref/version、structure fingerprint、source/goal/约束快照、完整教学与 links | 业务 publication 单一事务 | P + 既有实体/来源版本 | Learning/Practice/Summary/Assistant；current/history API；I8；I9 | 正式结构不可变；新 Revision | 是，内部 trace 隐藏 | 不取最大 revision；过去阶段与成果保留 |

共同合同 envelope 的 `version/hash/parent refs` 由各对象 Producer 生成，Persistence=C 或其 D/P 来源引用，Consumer=恢复校验/I7 来源验证/I8 revision 追溯；不可原地篡改，不向用户展示内部 ID。不得另外添加无 Consumer 的 generic score、推荐技术清单、全文缓存、未来标签。

## 7. HOLD_FOR_V2 复用合同

依据 Residual Cleanup 的 **14 行**逐项核对。下列 H01～H14 是本文件的清点编号，不新增运行时对象。三类按**职责/片段**划分，同一文件可同时出现在三表，不能把“部分允许”理解为整个文件批准复用或删除。REVIEW_DURING_ITEM 是未来证明义务，不是本轮 BLOCKER 或允许立即重构。

### 7.1 当前清单与实际 symbol

| 编号 | 当前路径 / symbol（相对仓库） |
|---|---|
| H01 | `backend/app/agent_workflows/planning_outline.py::frozen_pack_is_intact`、`outline_payload`、`STAGE_SKELETON_V1` |
| H02 | `backend/app/agent_workflows/planning_structure.py::check_frozen_structure`、presentation/focus helpers、`_negated_teaching_action`；后者被 `backend/app/domain/assistant_teaching.py` 直接消费 |
| H03 | `backend/app/agent_workflows/planning_batches.py::freeze_manifest`、`manifest_is_intact`、`attempt_key`、batch runner/merge |
| H04 | `backend/app/agent_workflows/nodes.py::PlanningNodes` 的 generate/validate/repair/save 与 batch 方法 |
| H05 | `backend/app/infrastructure/providers/openai_compatible.py::SHAPES`、`OpenAICompatibleLLM.preflight`、`generate_structured` 的 planning 分支 |
| H06 | `backend/app/infrastructure/checkpointer/planning_executor.py::PgPlanningExecutor`、`builder_for_version`；`backend/app/infrastructure/providers/runtime_factory.py::PersonalPlanningRuntimeFactory` |
| H07 | `backend/app/infrastructure/db/generated_plan_changes.py::PgGeneratedPlanChanges.existing_submission`、`validate_generation`、`save_generated` 及 current/hash helpers；同名 port 在 `backend/app/ports/generated_plan_changes.py` |
| H08 | `backend/app/domain/generated_plan_changes.py::added_topic_route`、`compose_generated_draft`；consumer `backend/app/infrastructure/db/plan_changes.py::PgPlanChanges.context` |
| H09 | `backend/app/application/plan_changes.py::PlanChangeService`、`backend/app/application/practice_changes.py::PracticeChangeService` 的 context/preview/get/decide，委托各自 PG adapter |
| H10 | `backend/app/api/v1/plan_change_schemas.py::PlanChangeContext`、`PlanChangePreviewView`、`GeneratedOperation` 及生成 TS 历史契约 |
| H11 | `frontend/src/api/client.ts::api` 的 planChangeContext/previewPlanChange/planChange/confirmPlanChange/cancelPlanChange、run/runs/cancelRun/draft/current/decide |
| H12 | `frontend/tests/current-learning-loop-pg.browser.cjs` 的 `controlledE2` 分支；backend wrapper 在 `backend/tests/integration/test_current_learning_loop_pg.py` |
| H13 | retained PG fixtures / generated-change cases：`backend/tests/helpers/frozen_planning.py`、`backend/tests/integration/test_generated_plan_changes_pg.py`、`test_plan_changes_pg.py`、`test_planning_cancel_http_pg.py`、`test_run_history_pg.py` |
| H14 | `backend/tests/helpers/planning_responses.py::selected_output` / `build_planning_demo`；`backend/tests/helpers/retained_planning_graph.py::TransitionNodes` 与历史 graph helpers（只在 tests） |

### 7.2 REUSE_ALLOWED — 保留职责

| 项 | 允许复用的保护/能力；条件 |
|---|---|
| H01 | digest、冻结输入完整性、size guard；须与旧 outline shape 分离 |
| H02 | 通用 canonical/source/integrity 验证；否定动作 helper 的助手 consumer 保留；须验证语义可独立 |
| H03 | manifest/hash、request identity、budget、receipt、bounded repair、reconciliation、checkpoint reliability；只复用可靠性职责 |
| H04 | 可分离的校验、error channels、repair 边界、保存防护；不能沿用生成方法即视为 V2 |
| H05 | structured JSON transport、usage、finish/truncation 识别、budget、receipts、known-invalid JSON 严格处理 |
| H06 | checkpoint integrity、恢复/绑定校验、fence、receipt-before-checkpoint、zero-duplicate dispatch 的不变量 |
| H07 | idempotency、actor/project、fence、source snapshot、CAS、发布事务与历史读取 |
| H08 | 有消费者的 closure/validation、history 保护；仅证明确实通用的部分 |
| H09 | scope、diff、CAS、idempotency、用户决定、局部 revision 历史 |
| H10 | 现有历史投影/决定/read 兼容边界，供原 consumer 使用 |
| H11 | 读取、取消、发布/决定基础客户端与 Summary/Prompt 等非规划 run consumer |
| H12 | 现有 e2 分支的学习/原文/历史/账号隔离断言 |
| H13 | 独立 RLS/CAS/cancel/receipt/publication 保护与明确适用 fixture |
| H14 | 历史协议的内容/JSON/预算/恢复反例与 test-only transition 证据 |

### 7.3 REUSE_FORBIDDEN — 不得成为 V2 产品语义

| 项 | 禁止复用 |
|---|---|
| H01 | 旧 OUTLINE_SYSTEM/OUTLINE_SHAPE、固定 stage_skeleton 作为 V2 输出合同 |
| H02 | 旧 structure/focus/presentation shape 或教学规则强制套 V2；通过降 canonical/source 门禁追绿 |
| H03 | old outline/structure/practice 分阶段规划语义、固定阶段生成与旧课程决策 |
| H04 | 恢复旧模型规划链或旧 approval graph；让 validate/repair 补课程决策 |
| H05 | 旧 planning prompts/SHAPES 成为 V2 prompt contract；length 当普通 JSON repair |
| H06 | 直接恢复旧 short/long business graph；恢复历史 failed/unknown 或盲重派；把支持旧版本当 V2 已接通 |
| H07 | 恢复已关闭的 prepare 目标决策/生成入口；以旧变更流程绕过新能力权威 |
| H08 | added-topic/fixed-route 组合重新决定 V2 能力与阶段；从旧 operation 推新目标分类 |
| H09 | 有限变更门面充当第二套 Semantic Replanning planner；未经合同判断目标语义 |
| H10 | 旧 GeneratedOperation 字段成为 V2 业务分类权威；把现 DTO 当新合同的完整承载证明 |
| H11 | 恢复已删除旧生成 UI，或由 client 直接推导/批准业务合法性 |
| H12 | 为让旧默认 bootstrap 通过而重开旧生成；将旧浏览器结果当 V2 视觉/内容通过 |
| H13 | 恢复删除的 selector/prepare/历史 shape 来跑绿旧 fixture；用旧语义测试批准 V2 |
| H14 | app 导入 tests，生产注册 Fake fallback；历史长图/示例成为 V2 产品事实 |

### 7.4 REVIEW_DURING_ITEM — 具体证明义务

| 项 | 对应 Item 与需确认的边界 |
|---|---|
| H01 | I6/7：新的冻结课程 envelope/digest/size 与 source 校验怎样分离；不复用旧 marker 解释新合同 |
| H02 | I6/7：canonical/source 检查输入适配、教学关系表达；助手否定 helper 不受影响 |
| H03 | I5/6/7：研究/分段/compile 的 identity、预算/receipt/checkpoint；旧 manifest 的 stage 结构不能直接套用 |
| H04 | I7：拆分纯校验/保存与生成语义；哪些保护迁移、哪些保持历史 test-only |
| H05 | I1/2/5/6：各已授权输出 shape/截断/错误与回执适配；新 Prompt 在对应 Item 评审，本轮不写 |
| H06 | I7：新流程版本命名空间、重启恢复、receipt 校验、绑定/fence；现 builder 仅支持旧 SHORT_GENERATION_VERSION，不能直接复用接线 |
| H07 | I7/8：新 manifest 与当前 revision/source/fence 的验证与原子事务；保留历史消费者 |
| H08 | I8：Local Change 与 Semantic Replanning 边界；closure 通用部分与旧 route 组合剥离 |
| H09 | I8：context/diff/get/decide 的生产调用链、已完成阶段保护与并发版本 |
| H10 | I8/9：新事实所需最小 DTO/来源映射；公开历史字段是否继续消费，不自动删除 |
| H11 | I9：新页面仅消费服务端新事实；旧 API helper 有无非规划 consumer、发布/取消如何保留 |
| H12 | I7/9：以预发布 Plan fixture 替换默认生成 bootstrap，再验证完整学习与截图；当前默认模式 NOT RUN |
| H13 | I7/8：迁移 fixture，分开保留可靠性反例与删除的产品语义；真实 PG 必须另验，不拿静态检查替代 |
| H14 | I7：历史保护如何映射新协议；保留 test-only 边界，不能把历史测试数当产品验收 |

所有十四项均有三类明确条目，没有未分类“整文件可复用”。当前 `stage_skeleton_v1` /旧 shape 的完整性校验说明历史绑定存在，不授权套用新对象。现有文件不在本轮拆分或删除。

## 8. 持久化、隐式耦合及 Item 接入门禁

1. `GoalSpec` 只有六类字段，project_context 需 I1 明确承载；不要修改旧用户事实语义或从 raw goal 再路由。I1 的模型/公开输入/落库实现需该 Item 自身授权，本轮只冻结职责。
2. `PersonalPlanningRuntimeFactory.__call__`、executor 模块的 `builder_for_version` 和 `PlanningNodes` 仍与旧 frozen submission/short graph 绑定。I7 必须提供新的流程版本命名空间、state/checkpoint/manifest/purpose/attempt identity 与恢复适配证明，不能直接接入旧图、重新解释旧 thread 并改名字。
3. `PlanDraft.content_hash`、`PlanRevision.structure_fingerprint`、`backend/app/infrastructure/db/plan_repository.py::_draft_payload` / `_structure_payload` 只枚举既有结构。额外 V2 字段不会自动被持久化或 hash 覆盖。I7 必须逐项核对第 6 节目标、能力、资源、课程、来源/约束、案例/实践与缺口的写入/读回/API/UI路径，缺一项即接入门禁 FAIL。
4. `PlanService._persist_draft` 在保存 Draft 前调用 `PgPlanningCatalog.materialize`，会写 knowledge/unit/relation/practice/task/link 实体，不是无副作用的 JSONB 草案保存。V2 逻辑课程候选、编译后的学习实体与可发布快照必须有明确 bridge：先校验完整课程与引用，再确定性编译并受控落库；编辑先在逻辑/候选内容上校验，再重编译形成新发布快照与 hash，不能先改共享公共实体再检查。来源 marker、canonical 和 snapshot 验证不能绕过，也不能要求新语义先伪装成旧 outline。I7 必须证明实体写入与 Draft 的事务边界/幂等恢复，中断不留下可发布半草案或重复公共知识；旧 `_persist_draft` 不直接接新 DTO。
5. `build_revision_snapshot` / `revision_from_draft` 统一重映射 stage/link/assignment 身份；publication/当前引用是事务事实。revision 更新不得把新的 stage_id 与旧历史位置混用；idempotency 同键同体复用、异体拒绝，CAS 必须比较服务端当前版本。
6. 现 `GitHubResourceIndex.inspect` / `DiscoveryEvidence` 是有界发现/检查能力，不等于 Reader 语义审查或稳定 outcome mapping。I3 不给旧元数据追授 reviewed 资格；I5 证明临时正文、证据归属、hash、生命周期和研究预算的实际消费。
7. `PlanService._edit` 当前只支持保留全部 stage IDs 的阶段编辑，不代表 V2 逻辑内容都可编辑。I7/8 必须定义合法编辑字段与逻辑候选→编译快照的失效/重建关系；确认 hash 覆盖实际发布内容与必要来源/约束/基线绑定，禁止仅验证旧白名单 hash。`PgPlanChanges.context` 仍用旧 pack blueprints、`added_topic_route` 和旧请求数公式；这些只保留其当前 consumer，不决定 V2 预算或能力。未来变更预览后，学习/summary/prompt/practice 或 current revision 等 basis 变化使旧确认失效的保护必须保留。

以上是已知实施门禁，**没有需要在 Item 1 前先修改生产代码或解决的 BLOCKER**。它们不得被宣称为已经解决；若对应 Item 发现无法在现 schema/容量/一致性下表达，提交最小扩展证据并先评审。各 Item 只读取自己的必要前置与共享证据，不重复全仓审计。

## 9. 非目标与禁止过度设计

本轮及首版不因“架构更完整”新增：九个微服务、九张 Planning 中间表、全文教程仓库、新 RAG/vector DB、Capability CRUD 平台、Curriculum optimization solver、Knowledge Graph 重建、多 Agent Planning 框架、Project 源码分析平台、自动 mastery assessment、Python quick check、每候选强模型 Reviewer、第二套 Replanning 算法、全局 AI 审读缓存中心、模型市场/自动比价系统。

优先现有实体、Ports 与可靠性保护；逻辑职责可以在同一应用流程内实现。允许的最小 migration 必须有真实证据，不能以此预建中间数据平台。开发分工代理不是产品多 Agent 功能。

## 10. 实施顺序与每项 STOP / REVIEW

```text
Contract（本轮） → STOP
Item 1 Goal Requirement Analysis → STOP / REVIEW
Item 2 Capability Planning      → STOP / REVIEW
Item 3 Coverage                 → STOP / REVIEW
Item 4 Gap Extraction           → STOP / REVIEW
Item 5 Resource Research        → STOP / REVIEW
Item 6 Curriculum Composition   → STOP / REVIEW
Item 7 Planning Execution       → STOP / REVIEW
Item 8 Replanning               → STOP / REVIEW
Item 9 UX（HTML → 用户批准 → React → 截图评审）
  ↓
End-to-End Product Acceptance
```

不得一个 Goal 自动完成 1～9；本次合同冻结不授权 Item 1 或任何真实收费调用。各项冻结输入/输出/消费者、失败分支/恢复与必要证据；完成后评审实际结果再进入下一单项。缺外部授权只暂停受影响验证，不编造通过，不自动消耗旧余额或恢复历史 Run。

## 11. 最终产品验收合同（未来执行）

最终成功定义是以下三个产品结果，单元测试数量不能替代。模型/搜索的真实验收另需明确授权，本轮均 NOT RUN。

### A. 真实目标生成合理路线

| 代表场景 | 必须检查的结果/反例 |
|---|---|
| Agent 零基础 | Common Core/专项基于能力和真实前置；系统性路线明确 MCP 政策；不是整包固定阶段 |
| Agent 已会 Python | 接受声明；没有 Python 测试/Review/教材搜索/借前置重加 |
| Coding Agent + interview | 目标能力与项目范围合理；提高产物与验收，不机械新增面试阶段 |
| RAG + existing project | 项目优先持续实践；Project Study 与自己项目的 Practice 分开 |
| Workflow | 依赖与教学连续性拆阶段，Recipe 不直接等同 Stage |
| Python 窄目标 | 只学习目标必要能力，不误加 Agent/MCP/RAG 或整套 Python 课程 |
| 陌生领域 + Agent | 真实不确定性触发一次有界验证；不假设模型全知，不扩课 |
| 目标过大 | 清楚澄清/范围决定，不能暗删 required 来容纳预算 |
| 冲突约束 | 暴露冲突、保持事实；未解决不静默通过 |
| 找不到合适免费资源 | 保留 required gap/限制，无假 URL/假覆盖，不宣称可学习完整路线 |
| 用户明确排除某课程政策 | 暴露并处理适用范围冲突，不覆盖用户或隐藏不合规 |
| 已有项目继续学习 | 保留过去阶段、成果和 Revision；只规划未来，精确稳定引用 |

### B. 实际教材支撑对应 learning outcomes

对所用章节、版本和适配的代表 outcomes 做真实正文语义核验，说明能教什么、缺什么及限制。URL 存在、JSON 合法、chunk 存在、hash 匹配都不足以证明教学有效；不能仅凭程序引用校验宣称语义准确。必要关键冲突再升级复核，不默认每候选强模型。

### C. 最终事实完整到页面

验证 **Goal → Capability → Resource → Curriculum → Draft → DB → API → React UI**，逐项核对关键要求/能力/教材/专项/Project Study/Practice 没有丢失、替换或被旧逻辑二次推导。必要的逻辑内部 IDs 不展示给用户；对应的业务事实必须保留。覆盖用户编辑后的 current hash/CAS、拒绝破坏 required 内容、正式 Revision 历史、重启零重复模型/搜索、unknown 不盲重派、取消/迟到结果，以及真实浏览器截图评审。

规则/Fake、真实 PG、真实外部接口、真实浏览器分别记录 PASS / FAIL / NOT RUN。Fake/静态文档验证不能代表 V2 真实产品完成或用户接受；全产品仍 STAGING_BLOCKED / NOT_READY，不能因本合同冻结改为 READY。

## 12. 本轮验证、独立反向审查与回滚

本轮只做文档验证，不重复历史昂贵产品测试。验证范围为本文件及 start HEAD 的只读证据：九项职责、第 6 节十个核心对象及字段 Consumer、H01～H14 三类、引用路径/symbol、无实施差异、diff whitespace。业务单元/PG/provider/browser 产品验收 **NOT RUN**。

独立反向审查以本合同及已汇总证据为输入，逐项检查并先修合同，不通过实施代码规避问题：

| 检查 | 冻结合同结论/对应保障 |
|---|---|
| 错误前提 | 当前 V2 未实现、GoalSpec 无 project_context、旧 executor 绑定和持久化白名单均明确；不假称现状已具备 |
| 职责循环 | 主链单向；领域验证在 I2 冻结前，案例搜索是 I6 有界子步骤，冲突走明确新版本 |
| 双业务权威 | Single Authority 明确 Profile/Capability/Curriculum/编辑 Draft/正式 Plan 各自权威 |
| 无 Consumer 字段 | 第 6 节每个关键字段有具体职责 Consumer；实施时须证明生产函数读取，无消费即删除/评审 |
| 旧 Seed/固定方向回流 | 内容是资产，禁止 selector/shape/旧 operation 决定新路线；HOLD 禁止表完整 |
| 政策冒充技术事实 | 第 5 节明确产品政策，MCP 学习与项目使用分离 |
| 无用途服务/表/Agent | 九项是逻辑职责，非目标禁止平台化扩张 |
| Python 已会仍重加 | A/B 分离贯穿 Coverage/Gap/Research/Curriculum/Compiler；禁止 Review/前置旁路 |
| 资源不足删 required | 精确未解缺口、确认门禁与冻结能力上界，不允许下游删能力 |
| Execution 再次改课程 | I6 完整课程/有界补齐，I7 确定性编译且无旧模型链 |
| 无条件项目搜索 | I6 先必要性与 requirement，再复用候选，最后仅缺候选才搜 |
| 教程正文长期保存 | 临时正文生命周期、metadata/ref/hash 的持久化边界、异常日志与 checkpoint 禁止全文 |

最终文档核对结果：`git diff --check` **PASS**；路径/symbol 与当前 HOLD 清单核对 **PASS**；九项职责及 Producer/Consumer Matrix **PASS**；独立 architecture reverse review 修订后 **PASS**。没有 Item 1 前置 BLOCKER。生产代码差异0，产品 model calls=0、search calls=0、DB writes=0、migrations=0；无 push/merge/deploy。

回滚只需经评审正常 revert 本次文档提交；不改写历史、不恢复旧规划产品语义、不回滚数据库。确切 final HEAD 在提交后的答复报告，避免自引用提交 hash。本轮到此 STOP，等待下一单项 Goal。

## 13. 2026-10-10 授权的局部产品语义修订

授权依据：`PLANNING_V2_CURRICULUM_RESEARCH_PRODUCT_FIX_V1`。本节在实现前记录最小差异；此前版本、已冻结 Run、Receipt、Revision 和原始验收证据不改写。

新 owned 提交显式冻结 `product_semantics = planning-v2-product-v2`；无此标记的历史 manifest 仍按 v1 运行及重验。标记参与 manifest hash、研究输入身份和课程输入身份，恢复不得升级或降级版本。仍使用现有 JSONB 快照及事务、fence、预算保护，不新增 migration。

1. **课程权限义务与运行事实分离。** `CurriculumPlanV2` 对 `local_tool_scope` 提供结构化教学义务，绑定原 constraint ID/source refs、原项目上下文及实际 Task/outcome/acceptance。安排未来执行前用户授权、默认拒绝、允许范围、输入校验、越权拒绝，以及允许、未经授权、越界、非法参数、执行失败、原 JSON 数据保护的验收与可检查产物。服务器验证引用和结构；内容真实承担教学义务仍需独立语义评审。规划义务通过只表示教学已安排；运行权限始终未验证，不授予任何工具执行权限。其他约束的拒绝保护及 existing_carrier 原文要求不变。v1 不追授此义务状态。
2. **完整必学课程与未完成建议分离。** v2 允许仅 recommended 的未解决 outcomes 在未纳入实际教学、未作为 required 的真实先修、未违背用户明确选择时保留为可见建议而不阻断 complete。required 缺教材/安排或真实先修缺失仍 incomplete；已选内容必须有真实支撑。原 importance、未解决原因及来源完整保留至 Compiler、Draft、Revision 和读回。v1 的 complete 判断不变。
3. **有界研究质量与范围证据。** `research_comparison_v2` 的派发先 required 后 recommended，保持原 Gap 身份与结果 canonical 顺序。获准候选在共享预算内进行有限比较，记录 outcome 覆盖、连贯教学、起点适配、示例/实践、版本及审读限制的来源证据；仅质量基本相当时中文优先。研究不决定 PRIMARY，也不声称全局最佳；不足以比较须明确记录。`ResearchReaderV2` 保持 1024 输出上限，联合审读最多六个已批准相关 outcomes；新的范围需真实证据且计入原预算。缓存绑定 URL、来源版本和已审范围，同 URL 不扩张资格。已有成功范围复用，新增范围不冒用旧响应，正文仍仅瞬态保存。

联合审读限于相关且相同 desired_depth 的能力；不同深度必须另行审读，缓存及 durable 派发身份绑定深度、来源和范围。Reader 可返回 inadequate 的事实：`insufficient` 或 `unknown` 质量意见不产生合格教材，保留缺口及比较不足，不能升级为覆盖。

新 Research/Reader、Curriculum/Compiler/执行快照具有显式版本绑定。旧 hash 与序列化不能因新增默认字段而改变；旧版本只读取旧字段，未知版本及派发/恢复版本不匹配拒绝。新 Curriculum 可消费冻结的 legacy Research 事实，但比较状态仍为 legacy，不追授新质量证据、不重解释其原 result_hash；新 owned Runtime 本身只生产新 Research 版本。已有结构如无法无损承载上述事实，停止该部分，报告最小阻塞，不能静默迁移历史数据。此修订不授权任何真实外部调用、正式生成或正式数据库写入。
