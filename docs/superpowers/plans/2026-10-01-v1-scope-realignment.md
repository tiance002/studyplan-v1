# V1 补充规格收口与下一步实施计划

> **For agentic workers:** 实施时使用 superpowers:executing-plans，逐任务执行。先完成本计划的 S0，再为选定的业务切片编写实现计划；不同时启动全部里程碑。

**Goal:** 以 2026-10-01 补充规格为优先输入，形成有代码证据的 Gap Analysis、统一正式规格和 M0–M4.5 路线，再按真实学习闭环补齐必要能力。

**Architecture:** 复用现有 API → Application → Domain → Ports → Infrastructure、稳定知识节点、不可变计划版本和受控 Provider 机制。LangGraph 仅编排有限工作流；业务规则留在领域/应用服务。个人 RAG 通过现有检索端口接入，按新契约适配。

**Tech Stack:** 当前仓库的 FastAPI/Pydantic、PostgreSQL、LangGraph、React/TypeScript/Vite；本轮 S0 交付文档，不引入依赖。

**Spec:** `C:/Users/22088/Downloads/studyplan_requirements_design_supplement_2026-10-01.md`。用户明确：与旧计划冲突时新计划优先。S0 应将原文逐字保存至 `docs/design-package/supplements/studyplan_requirements_design_supplement_2026-10-01.md`，避免长期依赖 Downloads 路径。

## Global Constraints

- 唯一正式实现基线：`D:\studyplan`；旧工程只读参考，不承担旧数据迁移或旧 API 兼容。
- V1 面向个人本地完整学习闭环；登录注册、多用户 SaaS、复杂 RBAC、MCP/Sandbox/Skills Runtime、多 Agent 自组织、GraphRAG 等不作为 V1 产品交付项。
- 稳定知识节点连接知识结构与计划；结构性调整新增版本，历史保留。
- `VERIFIED` 需要可检查证据；阅读完成、自述、模型建议不直接等同于核验通过。
- 模型仅提出 Proposal，经过 Schema/Domain 校验和批准后更新结构。
- 私有内容不得在本地模型失败后无感知发送云端；明确外部数据许可、隐私和预算。
- 优先 Unit → Targeted Integration → Critical E2E；完整验证放在 Milestone Verification。
- 付费验收必须新授权、新 Acceptance ID；不复用已消费 ID，不改写历史 Attempt/journal/evidence。
- 短分支从 develop 开始，完成后 `--no-ff` 集成；不 merge master，不 rebase/force push 共享历史。
- 保留 `.workbuddy/`、`design-preview/`；历史数据库迁移不改写。

## Review Focus

1. 本地单用户入口变更后，原 Project、个人模型配置和 Run 仍归属原 actor；不能信任请求自报 actor 或使历史数据不可达。归属 S0 Task 2、本地身份实现切片。
2. 旧计划版本的总结/成果/Session 在新版本产生后仍可恢复当时上下文。归属 S0 Task 2、M1/M2/M4。
3. 用户自述、阅读完成、模型评审与可检查证据区分清楚，不能错误升级 VERIFIED。归属 S0 Task 2、M2/M4。
4. 检索不足和本地模型失败时，明确缺证据/外发授权，不能伪造引用或静默云端降级。归属 S0 Task 2、M3。
5. 改造 State 或图版本时，当前 waiting_user Run 可正常批准/取消，不能因新部署解释变化而重复付费。归属 S0 Task 1/2、State 收缩切片。

## 当前基线与证据等级

- develop 基线：`3967168bd84fbbb312cca65ddcea6315dbf6100d`。
- Acceptance 09：`run_62d758209c954936ba26697550c89b6f`。
- 20 个真实 provider Attempts 全部 succeeded，含 1 次 structure repair；最终三类错误为空。
- Run = waiting_user / review_draft；Draft `drf_6d80a1b5f5724970b122616861f13be0` = awaiting_approval。
- 已核对数据库与 checkpoint：真实生成、局部 repair、最终校验、Draft 持久化、待审批暂停可标为 Verified。
- 本次真实 Draft 的批准/发布、学习执行和后续产品闭环尚未 Verified。
- B3-F2 最近定向测试 153 PASS、2 个需要提权的 symlink 用例 NOT RUN；仅对其已验证输入范围复用证据，不用测试数量代替产品验收。
- 下方差异来自有限静态对照，不是完整独立审核结论；完整五类 Gap 在 S0 产出。

## 初步差异：指导审查，不直接触发改码

| 事项 | 当前证据 | 新规格下的处理方向 |
|---|---|---|
| 本地单用户 / 注册登录 | ADR-0006、IMPLEMENTATION_PLAN、AuthPage 和 browser_auth 明确开放注册登录 | 标记旧产品决策被新范围取代；设计本地身份入口及原 actor 数据衔接，保持授权边界，后续小切片实现 |
| 知识状态 | `domain/enums.py` 的 UnitProgress 为四态、作用于单元；KnowledgeNode 无该六态 | 定义节点六态与单元进度的关系及证据门，不直接将单元 COMPLETED 映射成 VERIFIED |
| 计划版本 | `domain/planning/models.py` 已有 PlanRevision、稳定节点/单元/任务链接和不可变发布 | 先判断 PlanRevision 是否承接 PlanVersion 语义；不为术语差异建立第二套版本模型 |
| 学习 Session / 总结 / 成果 | SupportingPages 显示相关功能尚未开放；领域已有总结/实践/证据模型 | 按真实 API/持久化/前端链路判定完成度，不把类定义视作已完成业务 |
| 节点绑定助手 | AppShell 有选中 nodeId；LearningAssistantPanel 仅 stageTitle，输入禁用 | M2 绑定节点、版本和 Session，支持恢复学习上下文 |
| RAG | `ports/rag.py` 已有带 scope 的 RAGPort、Evidence、Citation | 对齐 KnowledgeRetrievalPort 所需 filters/版本/证据语义，优先适配已有端口及个人 RAG |
| Graph State | PlanningState 保存 domain_pack、完整生成节点/单元/关系、结构/实践 batches | 区分必要有限候选输出与业务事实复制；规划按引用持久化，保护旧 waiting_user 的 graph_version，不马上重构已验证链路 |
| 模型路由 | LLMPort / 个人云模型 / budget 已存在 | 先 L0 确定性 + L2 明确授权；L1 按确实有收益的任务增量接入，不强制先搭 Router |
| 正式文档状态 | design-package/README 仍写 B2/B3 待开始；旧 B0–B6 排期继续包含注册 | 更新事实与排期映射；旧验收报告保留为历史证据 |
| MCP 学习主题 | Agent DomainPack 的学习阶段包含 MCP | 产品运行能力后置与课程主题分开，禁止仅因 V1 不接 MCP 工具就删除学习内容 |

## S0：下一轮应执行的唯一 Goal

建议名称：**V1 需求—设计—代码一致性审查与规格收口**。

边界：正式文档、ADR、实施计划、AGENTS。不修改业务代码、不操作生产数据、不批准真实 Draft、不调用真实 provider。采用当前代码与验收证据；无需重新做 B3-F2 全量独立审核。

### Task 1：保存新规格与建立事实索引

**Files:**
- Create: `docs/design-package/supplements/studyplan_requirements_design_supplement_2026-10-01.md`
- Create: `docs/reviews/2026-10-01-v1-gap-analysis.md`
- Read: `docs/design-package/README.md`、`SOFTWARE_DESIGN.md`、`IMPLEMENTATION_PLAN.md`、`docs/adr/*`、`AGENTS.md`。
- Read: `backend/app/domain/{catalog,planning,reflections,practice}/models.py`、`backend/app/domain/enums.py`、`backend/app/ports/rag.py`、`backend/app/agent_workflows/{state,nodes,planning_batches}.py`、`backend/app/api/v1/*.py`、前端学习/助手/认证组件。

**Interfaces:** 输入补充原文、当前 HEAD、既有正式文档与关键实现；输出可定位的事实索引及五类 Gap 表。

- [ ] 记录 HEAD、tracked diff 和原文 SHA256；逐字复制新规格，确认源文件与仓库副本哈希相同。
- [ ] 建立权威顺序：用户最新明确决定 → 本补充 → 已对齐正式文档/ADR → 实施任务；冲突项给出旧条款、新条款及优先结论。
- [ ] 按 A Requirement Gap / B Design Gap / C Implementation Gap / D Overengineering / E Conflict 建立表。每项包含来源章节、代码路径、已核对证据、业务影响、处理方式、归属里程碑和验收。
- [ ] 对已有能力分别标记 Implemented / Tested / Integrated / Verified；缺乏证据写清“未核对”，避免由文件名或历史 README 推断完成。
- [ ] 核对 B3-F2 的生成与发布边界，保留 Acceptance 09 待审批事实；将人工 Draft 内容审核/批准列为单独后续验证，不为记录收口重新生成计划。

### Task 2：先统一产品与领域规则，再更新设计/ADR

**Files:**
- Create/update under `docs/design-package/`: `PRODUCT_SCOPE.md`、`DOMAIN_MODEL.md`、`ARCHITECTURE.md`、`LEARNING_WORKFLOW.md`、`RAG_DESIGN.md`、`MEMORY_CONTEXT.md`、`MODEL_ROUTING.md`、`FRONTEND_INTERACTION.md`、`EVALUATION_ACCEPTANCE.md`。
- Modify: `docs/design-package/SOFTWARE_DESIGN.md`、`docs/adr/README.md`。
- Create as needed: `docs/adr/ADR-0007-v1-local-user-scope.md`、`docs/adr/ADR-0008-workflow-state-boundaries.md`、`docs/adr/ADR-0009-plan-version-learning-context.md`。先核对现有 ADR 覆盖，再记录新决策；历史 ADR 内容保留，索引明确 superseded 关系。

**Interfaces:** 消费 Task 1 的已确认差异；输出可用于后端/前端实现的统一领域状态、版本、证据、隐私和工作流契约。

- [ ] PRODUCT_SCOPE 固定首个 Agent 开发领域、V1 全闭环、V2 能力；明确本地单用户产品入口与已存在 actor/project/model 配置的数据衔接方案。
- [ ] DOMAIN_MODEL 映射现有实体到新术语；复用稳定 node_id、PlanRevision。定义 NOT_STARTED、LEARNING、LEARNED、VERIFIED、REVIEW_NEEDED、SKIPPED 六态、证据来源、降回 REVIEW_NEEDED 规则，以及 UnitProgress 的独立语义。
- [ ] LEARNING_WORKFLOW 固定资料→总结→反馈→方案评审→外部实现→提交证据→验收→进度→调整，逐步列出输入/输出、版本绑定、确定性动作和模型动作。
- [ ] ARCHITECTURE/SOFTWARE_DESIGN 固定业务事实、Run 投影、checkpoint 三者职责；提出 State 收缩步骤及旧图安全恢复策略，不要求一次替换全部工作流。
- [ ] RAG_DESIGN 固定 retrieval scope/filters、Evidence 来源/版本/引用、证据不足路径、个人 RAG Adapter 边界；不在 StudyPlan 建第二套检索引擎。
- [ ] MEMORY_CONTEXT 固定原始会话保留、source_event_ids、PROJECT/SESSION 范围和受控 Memory Candidate 写入；长期记忆功能按产品需要实施。
- [ ] MODEL_ROUTING 定义 allow_cloud/allow_external_data/budget/privacy_scope 的业务边界；L1 为可选增量，云端失败/本地失败/检索不足分别处理。
- [ ] FRONTEND_INTERACTION 固定 11/17/72、N/P/C/A、Canvas 约 600px 下限及窄窗规则、助手拖拽、current_node_id 与 Session 绑定。
- [ ] EVALUATION_ACCEPTANCE 将八个真实场景逐项挂到 M1–M4.5，定义 P0/P1 门槛与 P2/P3 延期登记。
- [ ] 对 Review Focus 五项分别写具体验收：原 actor 数据可达、旧版 Session 恢复、自述不升 VERIFIED、无静默外发/虚构引用、旧 waiting_user 安全恢复且新增付费请求为 0。

### Task 3：更新实施路线与开发入口

**Files:**
- Modify: `docs/design-package/IMPLEMENTATION_PLAN.md`、`docs/design-package/README.md`、`AGENTS.md`。
- Finalize: `docs/reviews/2026-10-01-v1-gap-analysis.md`。

**Interfaces:** 消费统一规格；输出每轮 Goal 的依赖、已完成基础、实际缺口、允许文件、定向验收及停止点。

- [ ] 把 B0–B6 保留为历史交付索引，建立 M0–M4.5 映射；修正 README 的过时完成状态。
- [ ] 每个 Gap 只分配一个主责任里程碑；先复用/适配，再新增，停止重复实现已有版本/证据/Provider 能力。
- [ ] 每轮采用 Goal / Constraints / Allowed changes / Non-goals / Tests / Evidence / Rollback；S0 结束后只启动最小可验收的 M1 剩余切片。
- [ ] AGENTS 加入权威文档顺序、V1 范围、当前状态、验证策略、延期规则与付费 Gate；保留 Git/迁移历史规则。
- [ ] 自审八场景、五类 Gap 和全部新规格章节的覆盖；定位未分配或相互矛盾的条款。
- [ ] 运行 `git diff --check`，检查文档链接与原文副本哈希。业务测试/真实模型均 NOT RUN；记录原因是文档收口。
- [ ] 文档分支 commit 后 `--no-ff` 合入 develop；提交规格收口结果供负责人确认，不创建 milestone tag。

**S0 完成条件:** 五类 Gap 有来源/证据/处置，正式规格一致，现有能力有证据等级，新排期完整映射，首个实现 Goal 可独立执行。没有业务改码/数据库写入/真实模型请求。

## S0 后的执行路线：按剩余缺口推进

| 阶段 | 复用基础 | 剩余交付重点 | 通过门槛 |
|---|---|---|---|
| M0 / S0 | 现有设计、ADR、AGENTS、受控验收证据 | 上述审查与统一规格 | 一个权威口径、一个路线图，无冲突遗漏 |
| M1 | 稳定知识节点、PlanRevision、发布事务、资源索引、真实规划 | 现有 Draft 内容审核/人工确认与正式计划读回；补齐版本/节点/状态/局部调整契约实际缺口，本地身份入口按冻结方案实现 | 创建目标→生成→确认→浏览→跳过/调整，旧版本及稳定关联保留 |
| M2 | 现有总结模型、review 图和工作区组件 | LearningSession、原始会话持久化、节点/版本绑定、Reflection 提交、AI Feedback、恢复旧 Session、节点学习状态 | 一个节点完成学习→总结→反馈；错误总结获具体反馈；阅读/自述不直接 VERIFIED |
| M3 | 现有 ResourceIndex、偏好、RAGPort/Evidence/Citation | 资源替换、最小 ContextBuilder、检索适配、引用验证、路径外主题分类及调整 Proposal | 视频偏好切换；缺证据明确告知；GraphRAG 归类为扩展/高级时不直接修改计划 |
| M4 | 实践/Prompt/证据/VerificationRecord/AcceptanceReview 领域基础 | 一个主项目的方案评审→外部 Codex/IDE→成果提交→可检查证据→验收→节点状态；历史绑定和最小计划调整流程 | 实际成果与知识关联可查；不足证据不通过；有效验收可更新 VERIFIED |
| M4.5 | 前述已验证切片 | 八场景和一次真实全链路；冻结 Schema/OpenAPI/Prompt/模型/证据，负责人确认交付 | 从目标一直走到验收、进度和调整；无未解决 P0/P1；P2/P3 已登记确认 |

MCP/Sandbox/Skills Runtime 等产品运行能力进入 V2 backlog。RRF/reranker、复杂 Memory、L1 Router 仅在实际场景需要时纳入，不作为早期门槛。场景“跳过 Prompt/修改计划”需在 M1/M2 前冻结最小调整契约，在 M4.5 完成真实验证，避免最终验收才发现模型/API 缺口。

## 接下来的最短顺序

1. S0：只做五类 Gap 和正式规格/ADR/计划/AGENTS 收口。
2. 单独人工审核 Acceptance 09 Draft；按照批准后的现有业务 API 验证发布与正式计划读回。这个动作会写业务数据，规划阶段不代为执行。
3. 按 Gap 选 M1 必要补齐项；随后优先 M2 的“一个节点→总结→反馈→恢复 Session”纵向切片。
4. M3/M4 逐步把资源、实践、证据和调整串入同一主项目。
5. M4.5 才作完整 V1 可交付判断；新付费验证始终单独授权。

本文件是下一步规划；尚未执行完整 Gap Analysis、修改正式规格或实现新业务功能。
