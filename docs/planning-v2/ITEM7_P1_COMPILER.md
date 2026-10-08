# Planning V2 Item 7 P1 — Deterministic Compiler

日期：2026-10-08。本报告记录 P1 纯编译 checkpoint。依据用户最新连续授权，P1 独立审查及提交通过后继续 P2/P3；本 checkpoint 不包含数据库持久化或 Worker 接线，不进入 Item8/9。

## 1. 基线与边界

- Start HEAD：`f1f3d139d197c29e8d76a0d5d0ce87a045278f4f`；分支 `feat/n1-resource-discovery`；tracked tree clean。
- Final HEAD：本报告随本轮本地提交；准确 SHA 见最终交付及 ignored `var/planning-v2-item7-p1-20261008/final.json`，不制造自引用 hash。
- 已读取架构合同、Item6、Item7 P0 原失败与上游修复报告，保留其历史结论。原 `.workbuddy/`、`design-preview/` 未访问或提交。
- 产品模型、真实 GitHub/Web/Reader、数据库写入均为 0。未重新生成课程样例，未重跑 P0 的 260/150 项包；不修改上游 Prompt/Policy/Schema/审核映射/Seed，不开放 generate，不 reset/rebase/push/merge/deploy。

## 2. 编码前字段流向与现有消费者

本轮流向是冻结 Curriculum + 精确上游来源 → 纯编译 blueprints/来源快照/Manifest → **P2 待实现桥接** → Draft → Revision。表中 P2 列是明确后续承载方案，不是已接线或已持久化声明。

| 冻结事实 | P1 必须保留/核查 | 现有实体与实际消费者 | P2 预期位置及限制 |
|---|---|---|---|
| target_summary/scope/desired_depth/starting_point/outcome_purpose | 原 Profile 全量快照与 hash，不从 raw goal 推导 | `GoalSpec` 六字段、`PlanDraft.goal_snapshot/goal_spec`；`views.draft_view/plan_view`、`PlanSnapshot` | typed V2 来源快照；旧 goal_spec 不代替完整 Profile |
| learner_claims、A/B、claim bindings | 完整 Profile + CapabilityPlan；A 不生成 nodes/units/tasks | 旧 Plan 无 A/B 字段；Learning 使用正式 links，不会自动读取追溯 JSON | Draft/Revision V2 快照；Plan/学习读 API 投影起点与学习集合 |
| Requirement/origin/rationale/source_refs | 精确沿用完整 Profile 与能力 requirement_refs | 旧目标文字不承载结构化 refs | typed V2 快照及必要用户解释投影 |
| Outcome/Policy/version/verification/前置 | 完整冻结 Plan 与来源 hash，精确校验，不重选能力 | `PlanRevision` 无 Policy/outcome 合同；`KnowledgeRelation` 仅节点关系 | V2 快照、版本验证；不能把每个 Stage 依赖猜成全节点笛卡尔积边 |
| Stage ID/role/order/why/what/前置 | 逻辑 identity 与语义 key 区分、保留真正顺序和依赖 | `PlanStage` 仅旧 section_kind、objective、guidance；`StageDetail` 旧 enum | 新 typed curriculum_role/前置；legacy section_kind 兼容需评审，不能硬映射 |
| Knowledge/title/objectives/outcomes/materials | 精确候选语义 key、公开身份可选精确绑定、原文目标 | `KnowledgeNode` title/objectives/version/source_status；Catalog 与 Learning node snapshots | nodes 物化 + 每版本 outcome/material provenance；不因标题相似合并 |
| LearningUnit/objectives/rubric/knowledge refs | 原有序单元与结构 rubric/outcome links | `LearningUnit`、`UnitNodeLink`；Summary rubric snapshot/Assistant | units/links + V2 outcome 快照；结构化 rubric 可在原 JSONB 承载 |
| PRIMARY/SUPPLEMENT/REFERENCE/CASE_STUDY | 原角色对应小写、保留顺序/reading_focus/outcome refs | `StageResourceAssignment`、PlanService resolved resources、学习资源视图 | assignment/来源注册桥接与 V2 元数据；CASE_STUDY 不等同 ProjectStudy |
| source/section/version/hash/review/access/limitations | 全部材料事实独立保留，review_record 与 body 不混用 | `resource_snapshots` 与 Public Resource Catalog；learning exposures | 冻结来源快照与精确注册引用；研究版本字符串不可强转旧 source_version int |
| Guidance / PracticeDelta | 字符串逐项转 singleton list，不截断或新写教学文字 | `LearningGuidance` / `PracticeDelta`；计划、Summary、Assistant | 原字段可容纳的部分映射；旧长度限制超出需显式扩展，不能截断 |
| Task/goal/in_scope/out_scope/验收/outcomes/knowledge refs | 保留任务顺序、文本与结构验收关联 | `PracticeTask` 字符串 acceptance、task_knowledge_links；Practice submissions/Assistant | 旧 task 字段 + V2 structured acceptance/outcome linkage；禁止把dict转str存入验收 |
| 用户项目 / Starter / Micro Exercise | carrier、原 project_context 与 task kind 独立保留 | `practice_projects.idea` 只有文字；无 typed carrier/micro 字段 | V2 carrier/task 快照及正式 Practice/Plan 读 API；不塞进 idea 冒称完整 |
| whole_core / slices / 案例 | requirement 的问题、范围、I/O、正常失败、输出、设计问题及已选合格 case | `SourceSlice` 要求 files/call_chain，不等同本合同 | typed ProjectStudy 快照/读取；不能伪造 reviewed files/call_chain |
| 最终产物与验收 | 精确 final_artifact 与 outcome refs | 原 practice project / Plan 无结构化最终成果字段 | V2 carrier/final_artifact 快照及成果验收消费 |
| hard_constraints/assessment/unresolved/source限制 | 服务端重算/精确对比，未解决不可编译可发布候选 | 旧 content_hash/指纹不覆盖这些结构事实 | typed V2 快照进入确认 hash 与正式指纹；明确诊断/限制投影 |
| Hash/版本/identity mappings | Compiler/合同/上游/input/output digest 与完整映射 | 旧 Draft 当前 hash、Revision 指纹、stage ID remap | manifest/compiled snapshot 进入 hash；P2 生成最终 DB IDs 并记录精确映射 |

定位依据：`domain/planning/models.py::{PlanStage,PlanDraft,PlanRevision,build_revision_snapshot}`、`domain/catalog/models.py::{KnowledgeNode,LearningUnit,UnitNodeLink}`、`domain/practice/models.py::PracticeTask`、`domain/resources/curation.py::StageResourceAssignment`、`domain/planning/guidance.py::{LearningGuidance,PracticeDelta,SourceSlice}`；持久化与读回为 `infrastructure/db/{planning_catalog,plan_repository,learning_exposures,summaries,practice_submissions}.py`、`api/v1/{schemas,views}.py`。这是有界真实字段清点，不是数据库验收。

## 3. Compiler 与 Manifest

新增纯领域模块 `curriculum_compiler.py`，入口 `compile_curriculum(curriculum, *, context, profile, capability_plan, source_facts, public_knowledge_bindings=())`。显式冻结 Profile/Plan/Context 是因为 hash 无法恢复声明与能力原文；`CurriculumSourceFacts` 携带既有审核索引、catalog 来源、访问证明和项目案例，不含正文。使用现有 CoverageEvaluator/prepare_curriculum 重建确定性来源投影，精确比较整个 Context，拒绝通过重算 hash 提升资料资格。领域证据须批准并绑定实际 Plan；未知 A 不要求进入 B 的 Reader 投影。

`CompiledPlan` 保存 stages/nodes/units/真实 stage prerequisite、guidance、resource assignments、practice、project study、constraints、unresolved/source limitations 及完整 source snapshots。语义 key 与原课程 ID 分开，不生成数据库 ID；按实际顺序保留 Stage/Unit/Task，canonical 对象成员排序不改变 digest。PracticeDelta baseline 保留字符串，其余有序字段明确转为单元素列表，不截断文字。显式公共知识绑定仅核对语义定义与版本，数据库实际身份核验留给 P2，不按标题猜测。

`ExecutionManifest` 包含 compiler_version、contract_version、input curriculum hash、上游来源/Policy hash、compiled payload digest、stable identity mapping 和验证状态。机械完整性/来源绑定 PASS 不代表来源内容语义或数据库身份 PASS；后两项明确 NOT RUN。不预建运行 request/receipt 空字段。Incomplete、required unresolved、未满足约束、旧 Policy/非法 Outcome/来源/前置均拒绝，不补课程。

## 4. 完整/不完整冻结样例与身份

原 ignored `var/planning-v2-item6-implementation-20261008/example-complete.json` 和 `example-incomplete.json` 均存在。开始时记录原字节 SHA256，结束核对不改；它们标注为合成课程，不能冒充真实模型结果。样例只有课程，没有完整 Profile/Context，编译测试的来源依赖必须以已提交可追溯 fixture 重建，并核对原 input/source hashes，不能改写旧课程追绿。

完整原样例经实际 Compiler PASS：Curriculum hash `8d2b20c9573efbc3809ded6ba7bb1fdeed6f4ec13d98e8acb4efa55a59129df4`，compiled digest `002f913c52b7a9fbc002c83d4da9948865a3d76fc0d7a2f597db5f4ff42a9ce0`。不完整原样例明确拒绝并保留原 MCP 三个 source_unavailable 缺口，未产生可发布对象。原文件 SHA256 分别为 `dbc1ab0bf3fc1f9edc3d3769a0726894b897138d1f899f61d1921c1b5f66b876` / `6acbe06c47cbf29f62887d03d98998be1398ff06f6ece78758d029721a20537c`，结束字节核对一致。

完整 compiled payload/Manifest 与拒绝诊断保存在 ignored `var/planning-v2-item7-p1-20261008/compiled-examples.json`。MCP 理论沿用实际本地审核索引，实践研究为合成来源，两种资格分开；测试也覆盖 Python accepted_known、已有项目、Micro Exercise、whole_core/slices。原无约束样例缺少后来添加的空 assessment 字段，仅对确实 constraints=[] 且重算 assessment=[] 的历史表示兼容，不豁免任何非空约束。

## 5. P2 可行性与最小后续修订

### 5.1 现有容器不能直接无损消费

`PlanDraft.content_hash`、`PlanRevision.structure_fingerprint` 和共享 `_structure_payload` 只枚举旧字段。数据库 `_draft_payload/_structure_payload` 与读回构造器也只有白名单，额外 JSON key 不自动读回。Revision 正式结构取 normalized 子表，现 `structure` JSONB 只为 guidance/goal/resource snapshots 等明确字段提供补充；不能写一个未消费的 JSON blob 就宣称正式路线完整。

合理的最小方向：在已有 Draft payload 和 Revision structure JSONB 中增加**显式 typed V2 compiled snapshot + Manifest**，涵盖完整来源、角色/依赖/outcomes、材料资格、carrier、ProjectStudy、微练习及最终成果；同时增加 Domain 字段、序列化/反序列化、`build_revision_snapshot` 精确复制/映射、确认 hash/正式指纹及读取投影。该对象是课程/来源事实的合适容器，不是借用 objective/idea/route_change/resource_snapshots 塞无关结构；不需新建中间表或第二套知识库。

需要明确权威分工：normalized 实体负责教学实体与真实 links，V2 typed snapshot 负责其版本化业务语义和来源，保存/加载时验证语义 key ↔ 物化 ID/版本一致，不能两份结构任意分叉。用户合法编辑必须重校验/重编译当前候选并形成新 hash，不能仅保留初始 Manifest 继续确认。

### 5.2 Stage 与资源桥接

当前 `PlanStage.section_kind` / `StageDetail.section_kind` 是 `foundation/core/practice/advanced`；V2 `common_core/specialization/project_study/integration` 是独立维度，不存在无损的一对一映射。`0003_contract_alignment.py` 给 `plan_stages.section_kind` 建立 text NOT NULL DEFAULT core，无 CHECK。独立审查接受后续使用 `v2_curriculum` 作为协议 marker 的无迁移方向，真实 curriculum_role 与前置从 typed V2 snapshot 正式读回；marker 与合法快照必须双向绑定，旧 Planner/编辑不得生成无快照 marker 或保留失效 Manifest。不以 core fallback 伪装 V2 角色。**本 checkpoint 没有新增或修改 migration**；后续真实 PG 决定该承载方向是否可行。

已有 resource assignment 的 source_version 为公共 catalog 的整数版本；Reader 的 git/blob/unknown 等版本是另一类身份。P2 必须在合格元数据注册/解析后建立整数 catalog引用，同时保留原阅读版本与证据，不能截断、强转或把 research_checked 升为 public_reviewed。若不能合法注册，拒绝物化；不能复用旧 normalize fallback 默默将必需教材降为搜索建议。

### 5.3 物化、公共身份与事务

`PgPlanningCatalog.materialize` 只能作为局部底座。其 `nodes/units/relations/practice` 只消费已列字段，会忽略 V2 provenance；当前任务 acceptance 是字符串列表，需要 P2 明确将文本投影到旧列并在 typed V2 snapshot 保留原结构关联。它使用整个 bundle 的 hash 形成 namespace；改变无关内容也会改变 ID，不能凭 stable_key 宣称自动复用公共知识。`existing_node_ids` 已支持 scope/key/version 核对，可在 P2 用服务端已核查的精确 identity binding 接入；没有明确绑定就保留候选身份，不靠教材标题/URL猜节点。

`PlanService._persist_draft` 先调用 Catalog（独立 `_tx`）再调用 repository.save_draft（另一事务）。P2 应提供同一业务事务的显式编译快照消费：先 scope/完整性/来源/版本校验，再锁/CAS/fence、身份复用、实体/links、Draft 和候选绑定一起提交；失败整体回滚，幂等同键同digest复用、异体拒绝。现路径不能直接作为已经证明的 V2 原子写入入口。公共资源只读审核事实不得因此更新。

### 5.4 必须读回的产品事实

正式 Plan 与学习页需读回起点/A/B、学习 outcomes、真实前置、Stage角色/学习说明、教材章节/版本/阅读重点/资格限制、Guidance/PracticeDelta、用户项目与微练习、ProjectStudy whole_core/slices 和案例、任务验收及 outcome 关联、最终成果/验收、硬约束处置和未解限制。内部完整 hash/refs/Manifest 供来源校验和历史追溯；UI 只呈现必要业务事实，不显示内部 ID。现 `PlanSnapshot/StageDetail` 与 Learning/Practice/Assistant 的旧投影没有全部字段，P2 必须扩展服务端读写，前端呈现仍按对应后续授权执行。

以上均为有明确承载方案的 P2 接入工作，不要求在 P1 修改上游课程合同，也不表示 P2 已通过。本轮真实 PG、事务 rollback、共享知识复用与 Draft/Revision round-trip 均 NOT RUN。

## 6. RED/GREEN、独立审查与验证范围

关键实现 RED：25 FAIL（NotImplementedError，非 collection 错误）；初始 GREEN 51 PASS。独立审查主动发现两项缺陷：可一致重算 hash 后将 research_checked 提升为 public_reviewed；合法已批准未知 A 被错误要求具有 B Reader authority。root 实测复现第一项，worker 同批新增 RED 5 FAIL 后修复，最终 Compiler 62 PASS（1.44s）。反例还覆盖材料证据/URL/版本/访问证明一致篡改、缺审核 source facts、未知 A 缺批准。

直接受影响回归 56 PASS（Item6 Domain、完整 hash/Revision remap、public generate fail-closed），与 Compiler 包不相加冒称全新用例。独立审查按冻结合同检查实际源码及 diff，发现两项并在修复后仅定向复核，结论 PASS，无剩余具体阻断。审查者未自己执行测试，执行证据来自实际日志/XML。新增文件 Ruff PASS，git diff --check PASS；没有重复 Item1～6 全矩阵。

证据位于 ignored `var/planning-v2-item7-p1-20261008/`：compiler-red.log、compiler-review-red.log、compiler-review-final.log/xml、regression.log/xml、review-red.json、compiled-examples.json、persistence-boundary.json。网络 guard 禁外联及 DNS；HTTP 用例仅允许 Windows asyncio 本地 self-pipe。真实模型/搜索/Reader 0；真实 PG/行数/事务/恢复/浏览器/教学语义 NOT RUN。只读 PG preflight 可达且既有角色属性满足要求，未修改角色或数据库。

## 7. 修改、剩余限制与最终状态

修改文件：新增 `backend/app/domain/planning/curriculum_compiler.py`、`backend/tests/unit/test_curriculum_compiler.py`、本报告；更新 `docs/implementation/progress.md`，历史全文保留。冻结架构、Item1～6 业务语义、Policy/Schema/Prompt、审核映射/Seed、迁移与旧 Runtime 均未改变；历史 378 份证据、原样例和 .env 按基线 hash 核对。

主协调请求 Sol6.1 high，实施 Sol6.1 medium，来源独审 Sol6.1 xhigh，字段清点 Luna medium；实际解析 NOT OBSERVABLE，不改全局配置、不使用 max/Astra。P1 独立审查 PASS，状态 `ITEM7_P1_COMPILER_COMPLETE`。在本 checkpoint 时 P2/P3 尚未实现；按最新连续授权继续后续阶段，不将纯编译通过宣称完整 Item7 或全产品 READY。正式生成继续关闭，不 push/merge/deploy，不进入 Item8。
