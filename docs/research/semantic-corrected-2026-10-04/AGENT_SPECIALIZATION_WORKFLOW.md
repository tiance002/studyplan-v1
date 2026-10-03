# Agent 强化专项：Workflow / Automation Agent

> 产品语义：方向描述目标能力，不绑定职业、单个项目、单个框架或单个 Recipe。章节与阶段是可裁剪的默认教学骨架；按目标和起点选取，并尊重实际前置。
>
> Continuous Outcome Carrier 优先使用用户合适项目；范围过大时裁成可维护纵切面。没有项目才推荐 Default Starter Project。能力暂不适合迁入项目时，先做独立 Micro Exercise，再按需要迁回；允许重构/替换实现，保留问题、测试、数据、接口、设计决策与验证证据。下面项目名称及增量列均为默认候选示例，不要求把每项能力装进同一代码仓库。
>
> 项目案例都是可替换候选，审读深度以标准目录为准。阶段验收由用户提交并确认的证据支持，不自动判定 mastery、不自动打分。完整规则见 [PLANNING_SEMANTICS_STANDARD.md](PLANNING_SEMANTICS_STANDARD.md)。

> 类型：Reviewed Specialization Recipe（首批已审核专项参考骨架）；binding=optional，可组合、裁剪、替换，未命中该 Recipe 不阻止规划。Evaluation 横切各阶段，参数训练按目标单独选择。

> 研究快照：2026-10-03。本文给 StudyPlan 提供章节级教学编排，不修改 StudyPlan 代码。LangGraph、AgentScope、Dify、FastGPT、MaxKB 等都在快速演进；教程阅读不代表已运行其实验。源码项目学习应在学习当时动态查看当前默认分支，不固定 commit、文件路径或函数名。

## 路线结论

**Primary Spine 选 LangGraph Python Graph API**，但只在学习者已有一个简单 RAG/工具型 Agent 之后进入。Hello-Agents 第6章已经让人搭过小型框架，也用 LangGraph 的 StateGraph 表达过“理解 → 搜索（模拟）→ 回答”；专项应从这个可运行的短图直接深化到状态流转、分支、循环、持久化、恢复和人工审批，不能重新从“什么是 Agent framework”开始。

LangGraph 的优势适合本专项的教学目标：显式 State / Node / Edge 使控制流可读；官方材料从简单图逐步走到路由、并行、编排器—工作器、评审循环；同一套图模型继续讲 checkpoint、interrupt、thread 及服务化。它不替学习者解决外部副作用的 exactly-once：checkpoint 能恢复图状态，但重放可能再次执行节点中的外部调用，应用仍须用幂等键、去重或补偿处理。

AgentScope 放在有明确多 Agent 目标时做比较，不作为所有人都要学的前置。当前 AgentScope 2.x 已发生 API/架构迁移，而其公开 doc.agentscope.io 的不少流程页仍是 1.x 风格；要先读当前 2.x 仓库的迁移说明，再选匹配版本的团队流程章节。Dify、FastGPT、MaxKB 主要是“目标平台就是它”时的 Primary；其他时候只做视觉建模/产品流程的 Reference。它们不能替代理解持久化、重试、副作用及恢复语义。

教程文字、官方文档和公开源码可免费阅读。LangGraph OSS 可以先用固定函数/stub 本地练习，不需付费模型；接模型 API、托管 Agent 服务、云数据库、队列或 Dify Cloud 可能收费。FastGPT、MaxKB 自托管仍需自己的机器与模型资源。不要把任何额度或免费层写成课程的永久前置。

## 与 Hello-Agents 已学内容的关系

当前 Hello-Agents 在线教材的相关顺序为第4章 Agent 范式、第5章低代码平台、第6章框架开发（含 AgentScope 与 LangGraph）、第7章从零构建框架；第8章 Memory/RAG 应先完成一次简单检索纵切面，再考虑 workflow 专项。目录和章节正文核对后，边界如下：

| Hello-Agents 内容 | 已教授/实践到什么程度 | Workflow 专项如何处理 |
|---|---|---|
| 第4章 ReAct、Plan-and-Solve、Reflection | 有 Agent 自主选工具/计划与反思循环的概念；Agent 的动态 loop 是重要对照。 | ReAct 的 tool loop 做 **REVIEW**；固定工作流何处让 LLM 决策、何处由代码决定做 **COMPARE**。不要把 ReAct loop 当持久任务/恢复。 |
| 第5章 Dify、n8n | 能看到低代码平台的节点式建模和搭建体验；按章内容做了平台初览。 | 用户目标若是 Dify/n8n 应用，保留为平台入门；否则 **REVIEW** 概念，不再搭第二个相似可视化流程。 |
| 第6章 §6.1 框架抽象、§6.3 AgentScope、§6.5 LangGraph | §6.5.1 触及图、state、node/edge；§6.5.2 搭出 Understand→Search（模拟）→Answer；§6.5.3 讨论优缺点并要求试做条件重试/反思回路。AgentScope 示例展示消息驱动、多 Agent 互动。 | 第6章是 **REVIEW 起点 + DEEPEN 跳板**，并非持久 workflow 完整教程。专项不重复从零定义 Agent 基类/工具注册；重点补运行状态、持久 checkpoint、错误类别、interrupt、人机审批、服务边界与外部效果恢复。 |
| 第7章 从零构建框架 | Agent 抽象、工具注册/链式执行、异步执行等工程练习；练习涉及会话分支与回滚。 | 已完成者只回顾 state 与异步执行概念。不要把“对象/消息历史回滚”误认为 durable checkpoint、跨进程恢复或副作用幂等。 |
| 第8章 Memory / RAG | 先提供知识检索对 Agent 的基本位置和一次实践。 | 先做最小 RAG 再来此处。只把 RAG node 当一个真实工作流节点；重点是 RAG 前后路由、重试与人工复核，而不是重讲检索算法。 |

**概念区分**：State 是一次 workflow 可变的业务数据；checkpoint 是可恢复运行的状态快照；thread 是关联一段执行/交互的 ID；store 是跨 thread 的长期应用数据；conversation memory 是对话产品语义；任务队列则负责何时运行与运行中的 worker 生命周期。StudyPlan 不应将这些词合并为“记忆”。

## 主教学 Spine 与章节级安排

表内 LangGraph 章节指当前官方 Python OSS 文档。先读 Graph API 版本，避免把 Graph API 与 Functional API 当成同一段语法；本路线用 Graph API 讲明确 state/edges，需要装饰器工作流时再选读 Functional API。官方示例里多处调用外部模型，实践可将模型调用替换为固定函数并先验证控制流。

| 阶段 | Why now / JIT 前置 | Primary 章节与具体学习重点 | 重复关系、跳读范围 | 小实践与持续项目升级 | Exit gate |
|---|---|---|---|---|---|
| 0. 入场复习：从 Agent flow 到固定流程 | **Why now**：手上已有最小 RAG/工具 Agent，存在重复步骤或需要确定分支。**前置**：会 Python 函数、dict/TypedDict、异常、基本异步；Hello-Agents ch6.5 已做过则直接画旧图。 | Hello-Agents ch6.5.1–.3 快速回顾；LangGraph “Workflows and agents” 开头，先区分 predetermined workflow 与 dynamic agent。把自己的检索/回答流程画成输入、状态、节点、结束条件。 | Hello ch6.5 是 **REVIEW**；LangGraph 术语和控制流是 **DEEPEN**。不重读 ch6 全章，也不先学服务部署。 | 画出研究助手：输入 → 校验 → 检索 → 有证据/无证据路由 → 草拟答复 → 输出。暂不使用模型或副作用。 | 能指出哪些边必须固定、哪些决策确实需要模型；能说清每个状态字段由谁写、下游谁读。 |
| 1. Deterministic state、branch、loop | **Why now**：先将普通 Python 控制流转成可观察有向图，之后再讨论恢复。**前置**：阶段0；若需要单独补 Pydantic/TypedDict，只学一次性字段校验，不预修一整门课程。 | LangGraph “Workflows and agents”：Prompt chaining、Parallelization、Routing、Orchestrator-worker、Evaluator-optimizer、Agents 例子；Graph API 的 StateGraph、state schema、nodes/edges、conditional edges、reducers、START/END；理解并行写共享字段需 reducer。Send 动态 worker 属于有不定量子任务时才需要。 | Hello ch4 ReAct loop **COMPARE**；ch6.5 state/edge **REVIEW→DEEPEN**。仅需要固定流程时跳 Agent pattern 和 LLM 动态拆解；不为“用上框架”加 orchestrator-worker。 | 用固定 Python 函数模拟分类、检索、答案检查；实现 2 分支与“至多两次修复后终止”的有界 loop。注入空检索/低置信度、生成失败、超出重试上限。 | 能从图和轨迹还原控制流；每个 loop 有退出条件/步数上限；分支标签受 schema 约束；路由异常会进入显式默认路径。 |
| 2. Retry 与错误恢复语义 | **Why now**：控制流确定后，才可讨论节点失败应如何改变运行。**前置**：阶段1；理解异常与超时。 | “Thinking in LangGraph” 从节点职责、状态 schema 读到错误处理与完整 email support 示例：Transient 网络/限流用 RetryPolicy + timeout；可由 LLM 自我修复的输出错误保存问题后回环；需要用户补资料用 interrupt；达到上限则走错误处理/补偿节点；意外错误交给调用层。读 retry、human review、error handler 示例。 | Hello ch6 的练习只要求加条件重试，属 **DEEPEN**：新增错误分类、每类不同动作、重试预算与补偿。LangGraph 页面标注部分 API（例如 error_handler 需特定当前版本）需在实践前回查，属于 **VERSION_CONTEXT**。 | 用可控 stub 按固定序列返回 429、无效结构化输出、用户资料不足、永久错误。断言 transient 才重试、最多 N 次；validation 错误走修正支路；永久错误保留诊断。 | 能回答“什么错可重试、最多几次、是否可安全重跑、错误写到哪里、耗尽后系统处于什么状态”。 |
| 3. Checkpoint、persistence、thread / store | **Why now**：只有当流程会跨请求、长于一次进程或要暂停后继续时，持久化才有实际价值。**前置**：阶段2；区分内存 state 与数据库记录。 | Persistence 总览 → Checkpointers：thread-scoped graph snapshot、每 super-step checkpoint、thread_id 的创建/复用策略；本地 InMemorySaver 进程重启即丢；SQLite 适合本地验证，生产需选择持久 backend；Store 用于跨 thread 的 key-value/偏好而不是运行 checkpoint。研读 crash/replay 和 durability mode。 | Hello ch7 的会话分支/回滚 **COMPARE**：消息/对象层回退不等于 runtime checkpoint；第8章 Memory **COMPARE**：长期知识≠运行状态。 | 用 SQLite 或可在本机获得的持久 checkpointer；在节点中人为崩溃/停止进程，重启后从上一个成功节点恢复。两个 thread 的状态必须隔离；清掉一个 thread 不影响另一个。 | 能演示进程重启后的可恢复性；解释 thread_id 作为隔离键；知道 InMemorySaver 只能演示，不可宣称生产持久化；说明 Store 与 checkpoint 的边界。 |
| 4. Interrupt、HITL、approval、幂等副作用 | **Why now**：先有 checkpoint 才能暂停与恢复。只有工作流要执行高影响/不可逆动作或需要用户改稿，才引入审批。**前置**：阶段3。 | Interrupts 文档：interrupt(payload)、同一稳定 thread_id + Command(resume=...)、拒绝/编辑/通过三种结果、持久 checkpointer、JSON 可序列化 payload。重点读规则：resume 时节点从头开始，interrupt() 之前的代码会重跑；审批前非幂等副作用须移到 interrupt 后/独立节点或用幂等操作；业务审批需保存审批人、对象版本、决定和时间。 | Hello ch6.5 没有 durable HITL **NEW**；ch7 回滚不是审批凭据 **COMPARE**。区分“模型请用户澄清”与“人批准一个明确外部动作”：后者需授权主体、具体对象、决定、审计和过期策略。 | 只用 fake side effect：本地表/内存计数模拟“发布草稿”，保存稳定 idempotency key；第一次暂停，模拟服务重启，再用同一 thread_id 批准/拒绝；验证批准最多应用一次，拒绝不应用，审批前不发生 effect。 | 能展示暂停→人工决定→续跑全链；重启不丢状态；重复 resume/重放不会制造重复效果；批准内容与最终执行对象一致；有拒绝路径和超时/过期行为。 |
| 5. 运行可观测、测试与评估 | **Why now**：在加服务、并行 agent 前必须能发现状态偏差与重复执行。**前置**：已具备最小图、失败注入和可持久 thread。 | Graph API 的 stream/state 更新、LangSmith trace（有账户/调用可能产生费用）；先测试 node/route/graph 状态变化；记录 run/thread ID、node 名、输入摘要、开始/结束、attempt、错误类别、checkpoint、interrupt 与副作用 idempotency key。 | Hello-Agents ch12 Evaluation **COMPARE/DEEPEN**：对 Agent 输出测成功率不能替代 workflow 的状态/恢复断言。Tracing 与业务审计 log 不可互相替代。 | 建 8–12 个确定性用例：两条正常分支、不可回答、瞬态故障恢复、永久故障终止、重启恢复、人工拒绝/批准、重复事件、超过循环上限。断言结束状态、调用序列、外部 effect 次数。 | 同一输入可复现；每类失败有可读轨迹；配置改动前后可跑同一回归集；LLM Judge 不作为对状态/副作用的唯一 oracle。 |
| 6. Background / multi-session / service（按目标深化） | **Why now**：仅当用户需要 HTTP API、后台长任务、定时运行或多用户隔离才进入；本地 demo 不需要先搭队列。**前置**：阶段3–5，有具体 SLA / 输入并发 / 生命周期要求。 | LangGraph Agent Server 文档了解 Assistants、Threads、Runs、后台 run、队列、streaming、cron、API/worker/Postgres 角色；从单机 dev 部署读到按并发拆分的部署拓扑。单独核对 LangSmith 当前 hosted/self-host 功能、许可、计费和 DB/队列运维。 | FastAPI/HTTP API 是服务基础 **COMPARE**；workflow runtime API 才是运行管理 **NEW**。课程不默认学 Kubernetes/队列全部实现。 | 本地或测试服务提交一个只读研究任务，返回 run ID；提供状态轮询/取消/结果查看；同一用户 thread 分隔，用户间不可读取。重启 worker 后检查任务状态。 | 能说明 API 层、worker、持久 DB/队列分别负责什么；并发、取消、重复提交及用户隔离有验收；模型/托管费用与数据保存边界被标注。 |
| 7. 多 Agent / handoff（条件分支） | **Why now**：只有存在可并行的异质角色、独立上下文/工具权限或可证明更优的协作目标时再学。**前置**：阶段5评测能够比较单 Agent baseline 与多 Agent 方案。 | 若确定用 LangGraph：workflow guide 的 orchestrator-worker 与 subgraph / handoff 指南；先将角色作为显式节点和输入/输出契约。若项目目标是 AgentScope：先读官方 repo NEWS.md、2.x FAQ 和当前 quickstart，再读 2.x matching 的 team/pipeline 文档；不要把 v1 MsgHub、sequential/fanout pipeline 代码直接复制给 v2。 | Hello ch6.3 AgentScope / 三队游戏是 **REVIEW + COMPARE**；图中并行节点不是天然 Agent team。AgentScope 2.x 与已教材/公开 1.x 教程间是 **VERSION_CONTEXT**。 | 比较单 Agent 与两个角色（检索、事实核查）在同一小集上的任务成功率、错误传播、耗时/模型调用数；去掉一个角色做 ablation。 | 多 Agent 只有在目标指标改善且没有不可接受的成本/协调失败时保留；协作状态和 handoff 有明确协议，不把“多 Agent”当默认架构。 |

## 什么时候选可视化平台做 Primary

| 目标 | 材料角色 | 应学的内容 | 进入门槛/限制 |
|---|---|---|---|
| 目标是交付/维护 Dify 应用，团队在 Dify 里协作 | **Dify 可作为 Primary** | 当前 Quick Start 的 Workflow 示例：User Input → 参数抽取 → IF/ELSE → List Operator/Iteration（其内可并行）→ 结构化输出/模板整理；理解节点输入输出、分支条件、运行调试和应用发布。再按目标接着读 Variables、iteration、error handling 与发布/运维章节。 | Hello ch5 §5.3 已做平台首次曝光可 REVIEW；若课程走平台 primary，仍需在 Dify 内实际构建而不只看截屏。云模型调用可能收费；Cloud 当前 sandbox credit 是一次性，不是通用永久免费额度。 |
| 目标是 FastGPT 知识库问答/视觉工作流 | **FastGPT 可作为 Primary** | 快速开始中的内容合规示例：检索规则 → AI 分类 → 条件路由 → 改写 → 用户确认；再按目标学 Workflow intro、Loop Run 的数组/条件循环与 Loop Break、User Selection 暂停/恢复及日志。 | 需要有一个明确 FastGPT 产品项目；loop 和表单节点行为有版本界限（官方当前说明 Loop Run 在 4.15+），学习当日核对版本。 |
| MaxKB（本轮不进入教材 Primary） | **仅候选，metadata_only** | 后续若用户目标明确是 MaxKB，可另开目标型研究：从当时的 Quick Start 逐步核对 workflow、知识库、MCP/RAG、部署与权限。 | 本轮只核对官方项目简介与 release 页，未读教程章节/代码示例；不把它列为本轮课程 Primary 或断言其恢复语义。 |
| 目标未绑定平台，只想理解工作流语义 | Dify/FastGPT/MaxKB **Reference/COMPARE** | 用一个简短 visual flow 与 LangGraph 同题对照：分支、循环、暂停、错误输出在 UI 与代码接口中如何表达；记录平台锁定与可测试性取舍。 | 不要求把同一工作流三平台重建一遍，也不把配置页面经验等同于可靠性知识。 |

## 小实践设计（未运行）

下列为可复现实验规格，**本轮没有执行这些实验，也没有验证代码**。所有动作均应在本机假数据和 fake side effect 上运行，不接真实账户、不发邮件、不发布、不付款、不写入外部系统。

1. 造一个 4 节点有向图：validate → retrieve_stub → evidence_gate → draft_stub。测试可回答/不可回答两个出口；断言不满足证据门槛不会到 draft。
2. 在 retrieve_stub 按调用编号抛一次 transient error，然后成功；再测试连续失败直到预算耗尽。比较调用数、attempt 记录与最终状态。
3. 把错误输出校验设计为有限 feedback loop；尝试无效输出后修正，最大 2 次，超限进入 needs_human 而不自旋。
4. 配 SQLite 持久 checkpoint，在节点中人为崩溃/停止进程并重启；分别测试同一 thread resume 和新 thread 隔离。
5. 增加人工审批 interrupt，payload 只放 fake 草稿、内容 hash 与“批准/拒绝”；在模拟 side effect 前再校验版本/hash 和 approval ID。重复事件重复投递两次，使用相同 idempotency key 确认只有一个假记录。
6. 建 8–12 条全确定性回归测试，包含分支覆盖、循环上限、瞬时/永久故障、并行失败、审批拒绝、重复 resume、崩溃恢复。记录输出状态与假效果次数，不用 LLM Judge 代替状态断言。

这些测试只能证明该实验代码和局部设置中的控制流/恢复契约。它们不能证明真实第三方 API 的 exactly-once、安全性、生产 SLA、云端可用性或任何模型质量指标。若后来接数据库/支付/通知服务，要针对服务的幂等、事务边界、超时语义与补偿方法单独验证。

## 默认贯穿项目候选示例：研究与行动助手

该项目能自然承载本专项，但应从“单轮查资料并附引用”逐步升级，不能一开始就做自动行动平台。

| 版本 | 自然新增能力 | 应保留的证据/验收 |
|---|---|---|
| V0（在 RAG 专项完成） | 用户提交问题 → 检索 → 带来源草拟回答。 | 固定检索结果、出处、不可回答样本。 |
| V1 | 把校验、检索、证据判定、草稿拆成确定性节点，缺证据分支明确返回资料不足。 | 每节点输入/输出 schema、路由测试、流程图。 |
| V2 | 检索服务偶发失败时有限重试；模型输出不合格时一次修正；失败落入可解释状态。 | 注入的瞬时/永久故障轨迹、最大 attempt。 |
| V3 | 审查草稿、编辑或批准“导出为本地文件”前暂停；先只写临时文件/内存假记录。 | interrupt/resume 演示、审批记录、重复动作测试。真实外部发布/发送不属于本轮项目默认功能。 |
| V4（目标驱动） | 跨会话、后台运行、多用户 API。 | 稳定 thread/用户隔离、取消和恢复实验、数据留存说明。 |
| V5（目标驱动） | 多 Agent 协作做平行检索/独立事实核查。 | 对照单 Agent baseline 与 ablation；只有实测产生收益才保留。 |

**为什么适合**：每段都从资料研究本身长出需求，早期可用假数据/本地文件，成果能以流程图、bad case、恢复日志和测试说明。**不应强行加入**：自动邮件、发帖、采购、定时爬取或多租户后台。那些会把学习目标推向账户安全与外部副作用治理；仅在用户明确产品目标时再独立规划。

## 真实项目卡：LangGraph 与 AgentScope

### LangGraph 仓库卡

| 字段 | 内容 |
|---|---|
| repo_url | https://github.com/langchain-ai/langgraph |
| why_now | LangGraph 小图和课程实验已可解释；现在带着恢复/审批问题看真实库如何分层。 |
| prerequisites | Python graph control flow、state/checkpoint/thread/interrupt 基本概念；能读测试和追一条调用链。 |
| known_knowledge | Hello-Agents ch6.5 LangGraph 图基础；本路线已学条件边、reducer、持久化、重放及 interrupt 幂等限制。 |
| study_mode | 只读仓库地图与 3–8 个目标切片，一次研究一个；使用学习当时的当前默认分支，不保存固定 commit/path。 |
| learning_focus | 图状态/运行时、checkpointer backend、checkpoint 写入/恢复、interrupt 协议、服务运行时/API/测试边界，按用户目标挑选。 |
| desired_depth | 解释 1 个端到端“调用→状态变化→checkpoint→错误/恢复”切片，并从当前源码/测试引用证据。 |
| important_questions | 状态在哪些边界更新？并行节点如何合并写入？失败和待完成 writes 怎么处理？恢复时哪些节点重跑？具体存储后端保证什么？服务如何将 run 绑定 thread？ |
| avoid_scope | 不通读全 monorepo；不锁旧教程中的 API；不把 replay 描述成 external side effect exactly-once；未确认前不部署托管服务。 |
| expected_outputs | 一页当前架构地图；3–8 个切片候选；一个经用户选择的切片说明；事实/解释/推断分离；一条本地验证建议。 |
| migration_candidates | 最多迁移 1–2 个模式到研究助手，写明适用条件、成本与验证方式。 |

### AgentScope 项目卡（条件触发）

| 字段 | 内容 |
|---|---|
| repo_url | https://github.com/agentscope-ai/agentscope |
| why_now | 目标确实要求 2.x message-driven multi-agent/team runtime 或 session/service 语义时，用其做架构对照。 |
| prerequisites | 已能运行单 Agent/单 graph workflow；已核对所学教材与当前库版本。 |
| known_knowledge | Hello-Agents ch6.3 使用的 AgentScope 介绍/示例与公开 v1 文档需做 VERSION_CONTEXT；了解 v2 breaking changes。 |
| study_mode | 当前 repo/Docs 目录地图 → NEWS/迁移说明 → 当前版 tutorial → 目标代码切片，动态定位。 |
| learning_focus | 2.x teams/pipeline/handoff/session/runtime/service 里与目标相关的一项；对照 LangGraph 显式状态图。 |
| desired_depth | 一条 handoff/team workflow 的状态协议、失败行为、session scope 和测试；不要求熟悉全部 team API。 |
| important_questions | 消息事件与业务状态分别是什么？session 如何隔离？handoff 如何退出/回流？失败时 team 状态如何恢复？文档版本与安装版本相符吗？ |
| avoid_scope | 不复制 AgentScope 1.x MsgHub / pipeline 教程到 2.x；不因多 agent demo 就重构本项目；不读旧 Runtime 文档作为 current truth。 |
| expected_outputs | 当前版本/文档来源说明；当前架构小图；一个对比表；事实/解释/推断分栏。 |
| migration_candidates | 最多 1 个团队协作协议或 session 设计，不迁整个框架。 |

外部 Coding Agent 提示模板：

    请研究当前官方仓库：<repo_url>，目标是“我选定项目中的 workflow 持久化/审批”。
    若本机没有仓库，请 clone 当前官方默认分支；检查当前状态、贡献说明、目录结构和版本迁移说明。不要引用旧教程固定路径，也不要修改仓库或运行外部副作用。
    先给小项目整体地图；如果仓库较大，只提出 3–8 个与目标相关的源码/测试切片。等我选定后一次研究一个切片。
    每个结论标为“事实”“解释”或“推断”，以当前源码、测试和文档证据支持。说明输入、状态改变、恢复/失败处理和测试。最后只提 1–2 项可能迁移的设计、适用条件及可复现实验。

## 资源与研究记录

资源完整字段、原始来源链接、证据摘要与 review_depth 见 [RESOURCE_CATALOG_NORMALIZED_DRAFT.json](RESOURCE_CATALOG_NORMALIZED_DRAFT.json)；逐条实际检查范围、未覆盖限制和版本风险见 [RESEARCH_LOG.md](RESEARCH_LOG.md)。本专项的实验都是**设计而未运行**。
