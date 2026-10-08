# Planning V2 Item7 — P1～P3 实施与独立审查交付

日期：2026-10-08。P1～P3 独立审查均 PASS，ITEM7_IMPLEMENTATION_COMPLETE；下方原P0失败报告完整保留，旧P1_P3_NOT_STARTED是历史时点。

## 基线与本地checkpoint

Item7 Start HEAD：`f1f3d139d197c29e8d76a0d5d0ce87a045278f4f`，分支 `feat/n1-resource-discovery`。连续实施、独立审查、范围内自动修复和本地checkpoint均由用户明确授权。之前P0阻塞已在 [上游修复报告](ITEM7_P0_UPSTREAM_UNBLOCK.md)处理，本轮不改写它的历史结论。

| 阶段 | 本地checkpoint | 报告 |
|---|---|---|
| P1 Compiler | `52a326bf5d11d297fd47623cea346d4f6b55ff0e` | [P1报告](ITEM7_P1_COMPILER.md) |
| P2 Persistence | `f7eeab33eeb59d6824b2bc23d3e1a355c3a83340` | [P2报告](ITEM7_P2_PERSISTENCE.md) |
| P3 Runtime | 提交后写入最终交付回执，不在自身提交内容内形成hash循环 | [P3报告](ITEM7_P3_RUNTIME.md) |

各阶段均有annotated本地checkpoint tag。未push、merge、deploy。主协调请求Sol6.1 high，关键实现/独审Sol6.1 xhigh，实际解析NOT OBSERVABLE；未改全局配置，无Sol max/6Astra。

## 核心调用链和字段消费矩阵

`受控owned提交 → 现有Run/Job/Worker → V2版本适配 → Item1 → Item2 → Item3 → Item4 → Item5 → Item6 → compile_curriculum → PgV2PlanningPersistence → Draft → 明确当前hash确认 → 原子publication → 正式PlanRevision/current → 学习与实践读取`。

执行层只校验/编译/冻结/保存，课程决策仍由Item6负责。正常生成终态为succeeded+none；Plan发布依赖明确用户确认。非语义标题/描述编辑经原Item6 Validator及同一Compiler产生当前Draft hash，初始Curriculum hash只证明来源。语义改变不由Execution偷偷改写。

| 事实/字段组 | 实际承载/校验 | 实际消费者及证据 |
|---|---|---|
| Profile target/scope/depth/starting_point/purpose/project_context | typed原快照、source/hash、compiler_packet | Compiler、Draft/Plan v2_content；隐私上下文只取必要教学事实 |
| requirements/origin/rationale/source_refs/learner_claims | 原Profile与能力requirement/claim绑定 | Compiler完整性、Draft解释、A/B排除测试；A不产生教学实体 |
| Capability/Policy/outcomes/importance/depth/前置 | 冻结CapabilityPlan/Context/Manifest | Coverage→Gap→Research→Curriculum→Compiler；实体links和正式投影 |
| Stage title/role/order/why_now/what_to_learn/前置 | normalized Stage + typed映射；section_kind=v2_curriculum与快照双向校验 | 当前/历史Plan、Stage读取；长描述无截断；role独立保留 |
| Knowledge identity/title/objectives/outcomes/materials | 精确稳定identity/version语义匹配；公共实体可复用 | Catalog/Knowledge/Exposure；不按标题合并或重建公共knowledge |
| LearningUnit objectives/rubric/knowledge refs | 实体/links + 结构化rubric/outcomes | 真实PG学习、Prompt/Summary读取和源关联 |
| 材料role/order/reading_focus/source/section/version/hash/review/access/限制 | 公共reviewed首次独立冻结来源核查；research_checked项目资源typed绑定 | 正式reading/Exposure；版本字符串保留、不晋升公共审核资格 |
| Guidance/comparison/PracticeDelta全部字段 | 同一Compiler纯映射 + typed快照/原列 | Plan/PgPrompts/PgSummaries/Exposure实际投影 |
| Task目标/范围/验收/outcomes/knowledge refs/order/kind | PracticeTask + 结构化验收和正式links | Practice/Prompt/Summary；不把dict转str或省略验收 |
| 已有项目/Starter/Micro Exercise/final_artifact | 独立carrier/task kind/final_artifact与原project_context | 正式Plan/实践上下文；不强迫重建项目 |
| ProjectStudy whole_core/slices/问题/范围/I-O/设计问题/案例 | 独立typed ProjectStudy，保留requirement与case资格 | 两种模式真实PG round-trip；不冒充旧SourceSlice或持续实践 |
| hard_constraints/assessment/unresolved/source limitations | 来源hash保护，服务端重算/精确比对 | 编译与确认门禁、正式解释投影；未完整不可Draft |
| 原Curriculum/当前Compiled/当前Draft/Revision hash与identity映射 | V2ExecutionSnapshotV1：version/compiled/manifest/bindings/compiler_packet/original_curriculum_hash | 固定类型解码、重编译全投影核验、CAS/publication/current/history |
| Run/Job/Attempt/receipt/预算/来源/配置/dispatch identity | 原表与版本化manifest；服务器冻结提交再次核对 | PgV2Calls/PgV2Checkpoints/guarded transport/实际Worker；恢复和cancel/fence |

完整原始字段清点在P1报告，实际PG消费表在P2报告。JSONB里存在不是接线证明：本轮使用真实PG、实际Repository/Service/HTTP消费者验证。Assistant继承共享context/隐私投影已代码及PG helper核对，完整Assistant对话与Provider仍NOT RUN。

## 独立审查发现、修复与真实验证

三阶段独审均在独立上下文中查看实际源码、diff、冻结合同和执行证据，主动构造反例；未让实施者自报PASS取代独审。

- P1：一致重算hash可提升资料资格；未知accepted_known错误要求B类Reader权限。修复后独立反例PASS，无资格放宽。
- P2：非空Run缺fence仍保存、首次公共source可自证替换、compiled/Manifest一致重哈希分叉、原完整样例缺空assessment造成快照失败。逐项RED→GREEN；共享原Compiler规范化，不修改历史样例或初始hash。真实PG确认单事务回滚/幂等/CAS/当前hash确认/Revision历史/Fresh Readback。
- P3：正文回显可从envelope进入receipt、已知Reader错误误分类、预算重放阻断、checkpoint实际Run绑定、候选预算持久化、PG适配依赖方向、Run终态与Job不一致、Worker接管恢复错误及Composer本地预算传播。仅局部适配和受影响反例修复，详见P3报告；最后一项实际RED→GREEN、独审确认关闭，11源码/测试SHA256差异0。

| 层与证据 | 实际结果 | 解释 |
|---|---|---|
| P1 Compiler | PASS 62；相邻PASS56 | 离线结构/确定性；两组有重叠 |
| P2 Compiler/Snapshot | PASS69；相邻PASS114 | 含原P1用例，不累计冒称全新测试 |
| P2真实owned PG | PASS20 + 新fenced正例PASS1 | 既有migration0025，新库/复用角色，不操作正式库 |
| P2真实HTTP | PASS1；DTO PASS9 | 实际Cookie/CSRF/scope、编辑确认/current/history、public503 |
| P3真实owned PG | 主矩阵PASS20；预算终态PASS5；传播闭环PASS3 | 三批去重共25不同PG用例；原16PASS1FAIL和Composer RED1FAIL保留 |
| P3真实HTTP | PASS1；DTO PASS9 | 受控202、实际Worker、Draft、明确确认、current/history；完成后派发增量0 |
| P3相邻离线 | PASS23 | 仅模型绑定/RC预算/旧Planning去接线3文件 |
| Ruff / diff / import-collection | PASS；最终collection26项 | collection与执行分开，不替代PG验收 |
| 真实产品模型/搜索/Reader | NOT RUN（请求0） | 外部返回明确为合成/Mock，未消费产品预算 |
| 浏览器/完整用户E2E/真实教学语义 | NOT RUN | 不声明大规模可靠性或产品READY |

成功receipt无checkpoint可重建完整进度；删全部V2 checkpoint后同Draft/hash、0重复外部派发。实际Worker于Draft落库后中断、新租约接管也零重复派发，旧fence失效。未知专项完整自动触发和可信registry/receipt恢复通过实际DomainVerifier+Mock transport测试，不代表真实领域来源语义已验收。unknown/pending不重派、不换请求身份；历史unknown177/183未操作。纯body成功而无Reader成功receipt的中断保持阻断，不能伪造正文或自动重读。

## 修改范围、保全与剩余门禁

P1新增纯Compiler/测试；P2新增typed执行快照、PG桥接与读取消费，必要现有Domain/Repository/API契约适配；P3新增纯版本manifest、PG runtime/checkpoint/receipt/transport适配和owned入口/Worker接线。完整路径清单由各checkpoint diff及阶段报告给出；最终交付回执保存源文件hash。

无冻结架构/Item1～6核心语义/Policy/Prompt/Schema/审核映射/Seed修改，无migration/全局角色修改，无正式数据/历史Run/Receipt/unknown修改，无产品外部调用。原378份历史账本证据、.env、原Item6样例及progress历史由最终保全检查逐hash核对。受保护未跟踪目录未访问/修改/提交。

尚需另行授权：真实Provider/搜索/Reader整链语义、真实官方未知领域注册证据、课程和教材教学质量、实际浏览器与完整用户接受。默认正式入口保持关闭，未切正式Worker/原数据库；这次只在显式装配的隔离owned路径证明实现。回退应正常revert本地阶段提交，不改历史、恢复旧Planning或自动迁移/删除owned证据。

最终状态：ITEM7_IMPLEMENTATION_COMPLETE；ITEM8_NOT_STARTED；STOP。仅技术实施完成，真实语义与完整端到端验收待单独授权，产品NOT_READY。

---

# 以下为原P0历史报告（原字节完整保留）

# Planning V2 Item 7 — P0 产品符合性预检

日期：2026-10-08。结论：`ITEM7_PRODUCT_FIT_BLOCKED`、`P1_P3_NOT_STARTED`、`ITEM8_NOT_STARTED`、`STOP`。

## 1. 基线、授权与决策

- Start / Final HEAD：`5ca50020864bae52475fd0318a35677bb7ef203f`；分支 `feat/n1-resource-discovery`。
- 开始时 tracked tree clean；仅存在既有未跟踪 `.workbuddy/`、`design-preview/`，未访问、修改或提交。
- 唯一上位合同为 `PLANNING_V2_ARCHITECTURE_CONTRACT.md`，有界读取 Item2～7、Single Authority、Product Policies、Producer / Consumer Matrix，并复用 Item1～6 前置报告。
- 本轮产品模型、真实 GitHub/Web 搜索、真实 Reader、真实用户数据库写入均为 0。历史账本 183/280、unknown177/183 不重派；378 份历史账本/证据文件哈希保持。
- 用户本轮 P0 决策明确要求：若需改变 Item1～6 业务语义或新增独立基础能力才能修复产品阻塞，STOP，暂不进入 P1～P3。因此没有编写 Compiler、Manifest、Orchestrator 或持久化代码，也没有以先做确定性部分绕过前置门禁。
- 当前问题不是缺少本轮被禁止的外部验收：合法免费教材限制会触发确定性门禁，即使已有可信本地教材也不能完成路径。上游既有保守边界在本轮代表目标下构成产品阻塞，不将其改称网络测试 NOT RUN。

## 2. 证据方法与边界

新增报告之外，没有修改生产代码、Prompt、Schema、Policy v2、审核映射、Seed、数据库、Worker、Runtime、前端或架构合同。

本机 ignored 证据目录：`var/planning-v2-item7-p0-20261008/`。`probe.py` 使用真实 GoalRequirementAnalyzer、CapabilityPlanner、CoverageEvaluator、Gap extractor、ResourceResearcher、Curriculum Validator；模型输出和能力选择显式采用合成 fixture。脚本禁止 socket/DNS 外联。`p0-evidence.json` 保存合成输入、各层冻结对象、来源/hash、诊断对照与结果。证据未包含 API Key、认证头或真实私人项目正文，未纳入 Git。

真实本地证据复用 `load_reviewed_content_index()` 与 `test_curriculum.local_mcp_inputs()`：实际 `agent-application-v8.json` 的 resources[13]、`source:2`、MCP 章节的现有 review records、与该文件实际 SHA256 绑定的 `free_public` 访问证明。只支持 `mcp.roles`、`mcp.interfaces`，不扩展为最小接入实践或其他能力的审核资格。`hash_scope=review_record`，不冒称教程正文 hash 或重新进行教材语义审核。

合成输出通过结构 Validator，只证明下游机械行为；不证明真实模型能正确选择全部能力、真实教学质量或整链产品可用。Case B 的最小 fixture 仅用 `json.cli` 暴露约束门禁，不宣称已完整拆解独立异常处理目标；中文在本例作为偏好保留于合成需求文本，没有把“中文”自动升级为强制条件。

## 3. P0 代表路径与第一阻塞

### Case A — 系统性 Agent / Python 已会 / 免费 / 已有 CLI

输入：

> 我已经会 Python，想系统学习 Agent 开发，希望使用免费教程，并把学到的知识逐步应用到已有的本地待办事项管理 CLI 中，不要重新创建演示项目。

合成 Profile 保留免费、不得重新创建演示项目的硬约束（引用 `goal.target`）、Python learner claim 和已有项目背景。项目背景为该句中已有本地 CLI 事实的合成独立字段，不包含私人程序资料。

| 层 | 实际离线结果 |
|---|---|
| GoalProfile | ready；自然语言限制与已有能力保留；模型响应为 fixture |
| CapabilityPlan | Policy v2；Python 为 accepted_known；B 为 llm.api、structured.output、tool.calling、agent.loop、mcp、error.permission、eval.lite |
| Coverage | MCP partial（roles/interfaces）；其余 B none；A 不进入覆盖 |
| Gap | 7 个 capability gaps；MCP 仅 minimal_connection；没有 Python gap |
| Research | 7 entries 全部 unresolved / constraints_pending；没有教材资源；Fake 搜索/正文/Reader 派发也为 0 |
| Curriculum | 合成课程经 Validator 得到 incomplete；保留 unresolved、已有项目 carrier；MCP project_usage=excluded，其练习为 micro_exercise |

首阻塞：Item5 的无条件硬约束门禁。分类 **PRODUCT_FIT_BLOCKER**（确定性实现原因）。MCP 学习 required 与项目必须使用 MCP 仍分离；这些离线事实不是已完成真实课程编排验收。

### Case B — 窄 JSON / 文件异常 / CLI / 免费中文教材

输入：

> 我会 Python 基础，想学习 JSON 文件处理、异常处理，并开发一个小型 CLI 工具。希望使用免费中文教材。

| 层 | 实际离线结果 |
|---|---|
| GoalProfile | ready；Python 基础声明与免费硬约束保留，需求文本保留中文偏好 |
| CapabilityPlan | 最小诊断 fixture：Python accepted_known、json.cli needs_learning；没有 Agent/MCP/RAG |
| Coverage → Gap | json.cli none；3 个固定 outcomes 精确进入一个 gap，A 不进入 |
| Research | unresolved / constraints_pending；0 Fake 搜索/正文/Reader 派发 |
| Curriculum | incomplete；未虚构任何可用教材 |

首阻塞同 Case A，分类 **PRODUCT_FIT_BLOCKER**。本例在首门禁前没有证明能力选择充分覆盖“异常处理”独立学习诉求，也没有证明真实模型不会把 Python 基础声明解释过宽；这些仍属语义待验，不能以该最小 fixture 宣称目标完整通过。免费资料缺失应在适配/研究之后按证据判断，而当前根本没有执行该步骤。

### Case C — 未知专项的有界对照

采用一个代表：在已有本地待办 CLI 中学习 RAG 检索并解释来源，已会 Python；不添加免费限制，以隔离未知领域问题。未完整生成 Workflow Agent 和 Agentic RL 三套路线。

| 层 | 实际离线结果 |
|---|---|
| GoalProfile | 合成 ready Profile，保留已有项目与 Python 声明 |
| CapabilityPlan（未注入验证） | needs_verification；RAG 不在当前固定 Policy 中 |
| CapabilityPlan（单独诊断） | 注入明确标记 `evidence_kind=fixture` 的受绑定定义后可冻结；rag.retrieval 的真实前置形状显式为 llm.api，A 不重复教学 |
| Coverage → Gap | llm.api / rag.retrieval 均 none，各自精确生成 gap |
| Research（fixture 分支） | llm.api 可被 Fake 搜索/正文/Reader 解析为 resolved；rag.retrieval 无资源，public_descriptor_unapproved |
| Curriculum（fixture 分支） | incomplete；保留未知能力缺口，不虚构覆盖或固定 Recipe |

第一阻塞是 Item2 尚无生产 Domain Verification producer；注入仅证明消费接口存在。第二个独立阻塞是 Item5/Reader 的固定 Policy 公开描述门禁，即使有合法受控定义也不能研究其缺口。分类 **PRODUCT_FIT_BLOCKER**。真实技术前置、版本和教材质量另属 **EXTERNAL_EVIDENCE_PENDING**。

静态有界检查确认固定 12 项 Policy 不含 RAG、Workflow、Agentic RL 专项；未据此猜测三者应共用同一组基础或凭空添加能力，也未声称已验证它们的真实 DAG。

## 4. 确定性阻塞证据与最小对照

### B1：Item5 跳过已审核、已证明免费的内容

`backend/app/application/teaching_resource_research.py::ResourceResearcher.research:98–103`：

```python
if profile.hard_constraints:
    reasons.append("constraints_pending")
elif CAPABILITY_POLICY.get(requirement.capability_id) is None:
    reasons.append("public_descriptor_unapproved")
```

该分支位于 `_reviewed`、缓存、搜索、正文及 Reader 之前；可信 review/free proof 实际消费在 `_reviewed:182–205`。能力层的 `constraint_effects.not_applicable` 不等于资料约束已满足。

单独诊断使用合成空 Coverage 索引构造 MCP 概念 gap，再将真实本地 reviewed index + catalog + free proof 注入 Researcher；这不是重写实际 Coverage 结论，而是检查复用接口：

| 对照 | 实际审核索引/免费证明 | 结果 | 外部/Fake 派发 |
|---|---|---|---|
| 无约束 | 相同、有效 | resolved / public_reviewed | 0 |
| 免费教材约束 | 相同、有效 | unresolved / constraints_pending，资源空 | 0 |

精确边界：不是一定抛异常或把 session.blocked 置真，而是每个非空 gap 无条件保持 unresolved。若 gap 集合为空，Item5 可正常返回空 entries。

### B2：Item6 将约束存在等同于约束未解决

`backend/app/domain/planning/curriculum.py::_validate_output:710`：

```python
expected_status = "incomplete" if unresolved or unfilled or payload["constraints"] else "complete"
```

另一对照直接使用真实本地 MCP 概念 full Coverage，Gap=空、Research entries=空、所有教学材料 usable、无 unresolved、无 ProjectStudy 待选项：

| 对照 | 缺失 outcomes | 原样约束引用 | 实际 Validator 结果 |
|---|---|---|---|
| 无约束 | 0 | 空 | complete |
| 免费教材 | 0；同一份免费证明 | 保留 | incomplete；将 status 单独改成 complete 被拒绝 |

因此不只是缺少教材。Compiler 如果删除 constraints 或强行改 status，将越权改变上游权威并绕过 Validator。

### B3：未知领域验证及批准公开描述不贯通

- `backend/app/application/capability_planning.py::CapabilityPlanner.plan:22` 只消费 `verification_evidence` 参数。
- `backend/app/domain/planning/capabilities.py::DomainVerificationEvidence:67`、`_definitions:105` 有 input hash / 来源 / 定义覆盖保护 / 前置 DAG 校验；这些是合法消费合同，不是实际来源验证 producer。生产代码中未找到获取、核验并生成该证据的实现；Item2 报告也保留此未实现项。
- 即使进入批准定义分支，Item5:100 仍仅允许 `CAPABILITY_POLICY.get` 命中能力。
- `backend/app/domain/planning/research_reader.py::validate_reader_input:34–44` 只允许固定 Policy 的 exact outcome ID/text。
- `backend/app/application/curriculum_composition.py::_find_case:140–147` 只允许现有 `context.public_outcome_texts`，未知专项不能靠这个入口自动获准公共查询。

单纯连接“验证子步骤→CapabilityPlanner”不能打通后半链；把证据类型标签改为 source_verification 也不能证明真实来源充分。

### 其他边界

Item5 Web 当前只发现候选，没有正文读取/验证路径；这是已有适配器范围限制，不能据此断言外界没有教材，也不能以标题/URL补齐缺口。GitHub/Reader 真实教学质量、语言适配、项目案例选择均未获本轮真实验证。中文优先排序不等于满足用户将来可能明确提出的“必须中文”。上述外部质量待验不替代 B1～B3 的确定性阻塞。

## 5. 数据库与消费者接口预检（只读）

仓库迁移单链为 `0001` → … → `0025`，包含早期 `0005_catalog_versions`；文件末项 `backend/alembic/versions/0025_learning_assistant.py`，revision=`0025`、down_revision=`0024`。真实数据库当前 applied revision **NOT RUN**；没有新增/执行 migration。

| 符号/路径 | 机械字段与消费事实 | 本轮结论边界 |
|---|---|---|
| `plan_service.py::_persist_draft:621`；`planning_catalog.py::materialize:89` | 物化 nodes/units/relations/practice，带 write_fence/expected_plan_version；随后 project_draft、资源规范化、save_draft | 旧路径存在；V2 未调用，未证明新语义可无损物化 |
| `domain/planning/models.py::PlanDraft.content_hash:469` | project/goal/可选 GoalSpec/revision_candidate/route_change/stages/unit_refs/task_refs/node_stable_keys/结构来源/source pack/practice_project_idea | 不因 JSONB 或 hash 存在宣称覆盖全部 V2 必需字段 |
| 同文件 `_structure_payload:160` | unit/task/task-knowledge links、stage resources、extensions、可选 resource snapshots；资源快照去除易变 assignment/stage/time 字段 | 当前定义的字段受 hash 保护，V2 manifest/全部约束等尚未映射 |
| 同文件 `PlanRevision.structure_fingerprint:335` | project/goal/GoalSpec/stages/共用结构/source pack；不含 revision 序号/时间 | 仅清点表达式，不批准 V2 发布等价性 |
| `infrastructure/db/plan_repository.py::_draft_payload:182` | goal、revision_candidate、stages、各类 refs/links/resources/extensions/snapshots/source pack/practice idea/warnings | V2 专有结构化事实不能直接传给旧 DTO 期待自动保存 |
| 同文件 `_structure_payload:165`、`_load_revision:509` | JSONB 有审计快照；正式读回仍主要加载 normalized stages/links/resources/extensions，部分 guidance 从结构快照读取 | 无真实 PG fresh readback，不认定完整保存/当前发布通过 |
| `models.py::build_revision_snapshot:543` / `revision_from_draft:652` | 新 stage ID 与 links/remap；转交 GoalSpec、资源快照和来源版本等 | 未验证 V2 语义 key、知识 identity 与实体 ID 的完整映射 |

`PlanningCatalogPort` 在 `backend/app/ports/runs.py:59`；`PlanRepositoryPort` 在 `backend/app/domain/planning/models.py:898`。current/revision/history/publication/草案方法已存在，不代表本轮已接 V2。

下游读取入口：`PgLearningExposures._plan/_snapshots`（`learning_exposures.py:48/64`）、`PgPracticeSubmissions._context/_snapshot`（`practice_submissions.py:24/50`）、`PgSummaries._stage/save`（`summaries.py:130/163`）、`PgAssistant.create/_view`（`assistant.py:169/116`）和 `PgPrompts._context`（`prompts.py:33`）。这些沿用 revision/scope、关系表与历史快照；不能从符号存在推断新 Curriculum 全字段已经消费。

P0 先触发上游产品 STOP，故本轮未做逐字段 V2 编译映射、实体容量/事务实验或迁移必要性裁决。没有足够证据要求 migration，也没有宣称现 schema 必然足够。P2 必须重新证明无损、hash 覆盖、编辑与原子发布，而非把本清单当批准。

## 6. 精简 Producer / Consumer 矩阵

| 链接 | 实现/测试事实 | 当前状态 |
|---|---|---|
| Profile → Capability | Analyzer/Planner 独立服务、严格 Validator；本轮合成输入实调接口 | 已实现并离线测试；真实模型选择未验 |
| Capability → Coverage → Gap | B-only、真实 MCP partial/none、exact missing | 已实现并离线测试；未重新审核教材 |
| Gap → Resource | Researcher 与既有端口、review/free proof 接口 | 已实现；合法硬约束及未知领域产品路径仍受阻 |
| Resource → Curriculum | prepare + 专用编排合同/Validator、carrier/micro/来源绑定 | 已实现并离线测试；所有非空约束强制 incomplete，真实语义待验 |
| Curriculum → CompiledPlan / Manifest → Draft | 本轮 P1/P2 前置未通过 | 尚未接线；NOT RUN |
| Draft → Revision | 既有 publication/current/CAS 基础存在 | V2 未接线；owned PG/编辑/确认/fresh readback NOT RUN |
| Revision → Learning/Practice/Summary/Assistant | 既有 revision/scope/关系及来源快照读取 | 既有能力保留；V2 事实完整消费 NOT RUN |

## 7. 测试、审查与边界记录

- **PASS**：`probe.py` 的 A/B 首门禁、C pending/注入 fixture 后半门禁、MCP 全覆盖约束对照、真实 reviewed/free 复用对照。此 PASS 是诊断可重复；P0 产品符合性结果为 **FAIL**。
- **PASS**：4 个已有定向用例：generated route fail-closed、真实本地 MCP review/free 复用、未知领域 pending→绑定 fixture、carrier/micro/硬约束合同。
- 首次 5 用例运行：**FAIL**（1 FAIL / 4 PASS）。全 socket 禁用的离线 runner 阻止了 Windows asyncio 创建本地 self-pipe，TestClient 尚未执行；不是产品代码失败。
- 修正 ignored 测试 runner：只允许本地 loopback self-pipe，审计钩子禁止非 loopback connect 和所有 DNS；仅复核失败 HTTP 用例，**PASS**（1 PASS）。验证 `/api/v1/plans/generate` 未认证401、认证503，零 storage access，current读取及session仍保留。未启动对外监听服务。
- 全部 5 个不同既有定向用例最终 **PASS**；不重复 Item1～6 全套或全 Backend 回归。
- **PASS**：独立 Sol6.1 medium 只读审查了用户 P0 决策、共享 probe/JSON 与有限上游接口，确认诊断证据充分、P0 产品结果 **FAIL**、应 STOP；复核 B1/B2 的真实本地对照及 C 前后两道门禁，未发现可只靠 Compiler/Worker 接线消除的方案。审查明确要求保留 A/B/C 合成选择、B 异常处理未完整验证、C 仅 RAG 代表、MCP 既有审核资格/空索引诊断和 PG 未验限制，均已记录；不将 Fake 结构通过等同于真实产品语义通过。
- 真实 PG / owned PG 行计数、迁移 applied version、P1 Compiler、P2 fresh readback、P3 Worker/checkpoint/receipt/recovery/budget/cancel/fence、owned 业务 HTTP 链、浏览器、真实 Provider/搜索/Reader/教材质量：**NOT RUN**。
- 本轮未创建 Run/Job/Draft/Plan、未调用 publication 或历史恢复；这是无操作记录，不冒充数据库前后行数实测。正式 generate 保持 fail-closed；历史 unknown 未重派。
- 没有修改或恢复旧 outline/structure/batches/stage_skeleton 语义，没有新旧流程切换，没有持久预算或未知请求 reconciliation 的实现声明。

## 8. 最小修正建议（未实施）

1. **Item5/6 约束适配**：为免费/明确语言要求等已识别且有可信证据可判断的限制提供有限、受信、绑定 Profile/constraint ID 的适配事实；Item5 按事实决定是否复用/研究，未知或冲突限制继续 unresolved。Item6 按未解决的评估决定 incomplete，不能把“约束非空”当作永远未满足。限制原文/ref 仍完整保留，不能把所有限制默认为满足或直接删除。
2. **Item2 受控领域验证**：落实有界验证 producer 的输入、来源/版本/前置/局限与允许公共投影；批准的 unknown 定义及 hash/证据身份必须被 Item5/Reader/必要案例查询消费，禁止仅移除固定 Policy guard 或把私人目标直接发到搜索。
3. 后续仍需另行授权真实模型/教学证据验收，并有界核对 Case B 已知 Python 基础与显式异常处理学习目标的边界。不要靠扩词典或追加固定 Recipe 假装专项可组合。

这些建议触及上游语义和独立验证职责；本轮不实施、不变更架构合同、不新建泛化约束平台或第二个模型 Reviewer。可信 catalog 注入、既有服务顺序连接、共享 durable budget/receipt 本可属 Item7，但不能解决上述无条件判定，故不能据此越过 P0。

## 9. 修改、模型路由与 STOP

仅新增本报告，前置更新 `docs/implementation/progress.md`，完整保留其旧正文。ignored 目录另存诊断脚本/JSON/检查点，不作为生产实现或真实语义接受证据。

主协调请求 GPT-6.1 Sol high；实际调用链/独立审查请求 GPT-6.1 Sol medium；字段与迁移枚举请求 GPT-6 Luna medium。实际模型解析均 **NOT OBSERVABLE**，不把任务角色当模型身份、不改全局配置、不用 Sol max/Astra。独立分工只读，无并行业务写入。

P0 未通过，没有使用“P0～P3 通过后”的 checkpoint 提交授权；报告与进度保持未提交，Start=Final HEAD。不 push、merge、deploy。

`ITEM7_PRODUCT_FIT_BLOCKED`

`P1_P3_NOT_STARTED`

`ITEM8_NOT_STARTED`

`STOP`
