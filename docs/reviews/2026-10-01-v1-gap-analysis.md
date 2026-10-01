# V1 需求—设计—代码一致性审查

日期：2026-10-01 / S0。范围：D:\studyplan；代码/文档基线为本地 develop `ba7f5f50dc187dd99e75305e08648971440aa675`，其业务代码仍是此前已推送的 `3967168bd84fbbb312cca65ddcea6315dbf6100d`。ba7f5f5 是本地文档合并基线，不宣称当时存在于 GitHub。

权威：用户最新决定 → [补充规格原文](../design-package/supplements/studyplan_requirements_design_supplement_2026-10-01.md) → 对齐正式文档/ADR → 实施任务。原文 SHA256 `C98B4F5D06845B133B7F877B2D106EFFD57013085E6877626C0862DAD3274CFA`。

## 审查方法和边界

核对 design-package 的软件设计/实施方案/B3 设计、ADR 0001–0006、AGENTS、关键 Domain/Ports/Graph/应用容器/API/DB adapter/迁移及前端入口。历史验收按已核对范围引用；未重跑大型测试、未重新独立审核 B3-F2、未访问旧 E 盘或个人 RAG 项目，未调用 provider/创建 Run/写数据库。

这是全套补充章节的规格映射和关键实现入口的静态一致性审查，不宣称所有源文件或运行边界均已独立验证。下表“已收口”表示 S0 文档已落定；后续实现/真实验收保持待完成。

## 事实索引

| 能力 | 代码/证据 | 完成度与限制 |
|---|---|---|
| 规划/版本/发布 | `domain/planning/models.py` build_revision_snapshot、PlanPublicationService；`infrastructure/db/plan_repository.py` publish_revision；B2-V 报告 | Implemented/Integrated；历史测试有报告，本轮 NOT RUN；不能推导本次真实 Draft 已发布 |
| 真实规划与 repair | Acceptance 09 / [结果记录](../acceptance/b3f2/real-provider/2026-10-01-run09-result.md)；checkpoint/DB 已只读核对 | Verified 到 waiting_user，20 请求全成功/1 repair/错误空/Draft 已存；批准与完整闭环 NOT RUN |
| 节点内容身份 | `planning_catalog.py` materialize：namespace = project_id + hash(nodes/units/relations/practice)；迁移 0005 允许 stable_key 多内容版本 | 同内容重复幂等；跨不同生成的逻辑身份不稳定，不能宣称稳定 knowledge_node_id 已完成 |
| 进度与证据 | `domain/enums.py` UnitProgress/EvidenceGrade；`practice/models.py` VerificationRecord/AcceptanceReview | 领域基础 Implemented；知识六态、核验→节点联动和提交 API 未集成 |
| 反思 | `domain/reflections/models.py` SummaryAttempt/Review、`graphs.py` review loop；`0002_business_domain.py` summary tables | 模型/表/测试基础存在；容器/API/前端缺完整用户提交链，版本和 Session 绑定缺失 |
| 会话与助手 | AuthSession/SessionResolver；`SupportingPages.tsx` 会话未开放；LearningAssistantPanel stageTitle、输入禁用 | 认证会话不等于 LearningSession；学习会话与助手仍待实现 |
| 资源/检索 | ResourceIndex/PublicResourceCatalog、`ports/rag.py` | 索引基础可复用；检索 Port 已定义，独立 RAG Adapter/filters/ContextBuilder 未核对或未集成 |
| 本地身份 | `core/config.py` local_actor_id/local_session_token；composition 中 DB 分支改用 PgBrowserAuth；AuthPage | 现有配置不等于本地无登录正式入口，M1.1需补装配/UI/安全验证 |
| 前端布局 | AppShell、panels.ts、ResizableDivider | 11/17/72、600px 及窄窗逻辑 Implemented；历史浏览器证据存在，本轮 NOT RUN |

## A. Requirement Gap：原正式规格未完整沉淀的新要求

| ID / 优先级 | 新规格来源与旧文档缺口 | S0 处置 / 主责任 | 验收 |
|---|---|---|---|
| A1 / P1 | §3/§7：节点六态、Session plan_version/node 绑定；原设计 §3只写 UnitProgress | DOMAIN_MODEL/LEARNING_WORKFLOW 已收口；实现 M2 | 重开旧 Session 恢复旧目标；自述不升 VERIFIED |
| A2 / P1 | §5/§6：外发许可与 Raw/Summary/Memory 来源，原设计未形成 CallPolicy/来源契约 | MODEL_ROUTING/MEMORY_CONTEXT 已收口；M2 原始会话、M3 Context/许可 | 禁云请求0、summary可回原事件、无静默外发 |
| A3 / P1 | §8/§11：七类错误与八场景，原方案泛 planning_failed/旧 B6 列表 | ARCHITECTURE/EVALUATION_ACCEPTANCE 已收口；M1.4安全错误、各场景对应阶段 | 安全原因可定位、八场景有原始证据 |
| A4 / P2 | §4：设计动机/替代方案/业务取舍及连贯资源 | PRODUCT_SCOPE/LEARNING_WORKFLOW/RAG_DESIGN 已收口；M3 | 教学卡片/反馈可解释取舍，资源有作者/主线/来源 |

## B. Design Gap：目标设计与实际结构不同

| ID / 优先级 | 具体实现证据与影响 | S0 决定 / 主责任 | 验收 |
|---|---|---|---|
| B1 / P1 | materialize namespace 包含整份内容 hash；任一批次变化可让未变 stable_key 节点得到新 node_id（§3） | ADR-0009稳定逻辑身份+内容映射，旧物理ID/FK保留；M1.2 | 两版部分内容改变，未变语义节点逻辑ID相同，旧版内容/成果仍可读 |
| B2 / P1 | PlanningState 同时保存 domain_pack、nodes/units/relations、structure/practice batches（§5） | ADR-0008候选存Repository/State用引用；M1.4，不改历史图 | 新图有限State；旧 waiting_user 批准/取消新增provider请求0 |
| B3 / P1 | SummaryAttempt 有 unit/rubric/run，却无 plan_version/learning_session/node 绑定（§3/§7） | DOMAIN_MODEL版本来源契约；M2 | 修改计划后原总结恢复原版本/目标/rubric |
| B4 / P1 | RAGPort仅scope/query/limit，目标filters/version、ContextBuilder和引用Gate缺装配（§6） | 复用单一Port适配，复用个人RAG；M3 | 越界/错误版本过滤、缺证据明确、引用真实 |

## C. Implementation Gap：冻结规格对应的缺失链路

| ID / 优先级 | 证据 / 实际缺口 | 主责任 / 处置 | 验收 |
|---|---|---|---|
| C1 / P1 | KnowledgeNode无六态；workspace reader node.progress=None | M2，追加节点学习事实与Domain迁移门 | 学习/跳过/返回/核验/复习可追溯，单元完成不批量核验 |
| C2 / P1 | composition/AppContainer/API仅装配规划/模型/认证/workspace，SummaryDetail未开放 | M2，接Reflection持久化、review和API/前端 | 一节点提交原文→反馈，原文/来源/修订保留 |
| C3 / P1 | AuthSession已实现，但无LearningSession/原事件/历史恢复入口 | M2，单独学习会话，非复制认证逻辑 | S7、切节点异步回答不串Session |
| C4 / P1 | PracticeSubmission/AcceptanceReview存在，PracticeDetail说明提交评审未开放 | M4，方案→导出→成果→实际核验→状态 | S6，同一主项目、证据不足不通过 |
| C5 / P1 | 有PlanRevision/发布/取消，未暴露完整调整Proposal与跳过/重排流程 | M1.3，确定性最小调整优先，模型只提建议 | S2/S8、新版本旧证据保留、重复命令幂等 |
| C6 / P1 | 当前真实Run只到waiting_user，不能以此证明发布/全闭环 | M1人工批准/读回；M4.5全流程 | S1读回正式路线；八场景和完整闭环 |
| C7 / P1 | LLMPurpose/预算基础存在，七类业务错误/许可外发字段未形成统一DTO/调用Gate | M1.4错误与M3许可（主责任M3） | stage/details无秘密；禁云0请求，本地失败不转云 |

## D. Overengineering：超出当前 V1 的已实现内容

| ID | 证据 | 处理 / 主责任 |
|---|---|---|
| D1 / P2 范围收缩 | ADR-0006、browser_auth、AuthPage、0008/0009包含注册/密码/认证会话/限流；新§1/§9排除登录注册 | M1.1提供正式本地入口并停止扩张账号产品；已存身份/数据、历史迁移、安全约束保留，不做批量删除 |

未在已核对运行入口发现需要删除的 MCP/Sandbox/Skills Runtime、GraphRAG、多 Agent 系统；这些作为排除项登记，不虚构“已过度实现”。PostgreSQL/RLS/队列/checkpoint/幂等/Attempt服务已验证成本和数据边界，复用，不因个人本地范围整体拆除。

## E. Conflict：旧新决策的优先关系

| ID | 旧要求 | 新要求 | 决定 / 实现归属 |
|---|---|---|---|
| E1 | ADR-0006/原实施方案开放注册与口令限制是V1要求 | §1/§9个人本地、不做登录注册 | ADR-0007取代产品范围；原ADR原文保留；M1.1安全过渡 |
| E2 | ADR-0005限定恰好三图、成果验收不能第四图 | §5建议按Planning/Learning/Reflection/Practice/Adjustment边界划分 | ADR-0008取代固定数量禁令，保留单引擎/有界性；需要才建图 |
| E3 | README仍说B2/B3待开始，原B0–B6以注册/重登陆为交付路径 | §13 M0–M4.5以真实学习闭环为门槛 | IMPLEMENTATION_PLAN/README更新；旧验收/历史排期可追溯 |
| E4 | “稳定实体引用”可能被理解为当前node_id已跨重生成稳定 | §3稳定knowledge_node_id跨知识结构/计划连接 | ADR-0009明确逻辑身份与内容快照不同；M1.2，既有ID不改写 |

## 规格覆盖与首个实现切片

| 补充章节 | 当前正式落点 |
|---|---|
| §1/§2/§9/§15 定位/目标/范围/交付 | PRODUCT_SCOPE、IMPLEMENTATION_PLAN、ADR-0007、EVALUATION_ACCEPTANCE |
| §3 领域/状态/版本 | DOMAIN_MODEL、ADR-0009 |
| §4 内容/资源/实践 | LEARNING_WORKFLOW、RAG_DESIGN、DOMAIN_MODEL |
| §5 Graph/路由/隐私 | ARCHITECTURE、MODEL_ROUTING、ADR-0008 |
| §6 RAG/Context/Memory | RAG_DESIGN、MEMORY_CONTEXT |
| §7 前端/会话 | FRONTEND_INTERACTION、MEMORY_CONTEXT |
| §8 架构/API/错误 | ARCHITECTURE、SOFTWARE_DESIGN |
| §10 治理/验收/测试 | AGENTS、EVALUATION_ACCEPTANCE |
| §11 场景与闭环 | EVALUATION_ACCEPTANCE |
| §12–§14 文档/路线/Gap | README、IMPLEMENTATION_PLAN、本文、S0计划 |

优先级：先M1.1本地入口安全衔接与M1.2稳定身份，再M1.3版本调整，随后M2一个节点学习纵向切片。已有Acceptance09人工审核/批准与正式读回可先单独完成，无须重新生成；它是用户业务决定，S0未执行。

S0文档收口不使以上实现缺口消失。P1实现缺口必须在所属里程碑验收前完成；P2需负责人确认延期，S0未替负责人自动批准延期。
