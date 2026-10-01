# 学习规划助手——需求与软件设计补充计划

> 跨会话决策收口版 | 2026-10-01

**用途：** 作为当前需求文档、软件设计、ADR、IMPLEMENTATION_PLAN 与 AGENTS.md 的补充规格，并作为下一轮需求—设计—代码一致性审查的上位输入。

# 一、文档定位与统一口径

## 文档用途

本文件是现有需求文档、软件设计、ADR、IMPLEMENTATION_PLAN 与 AGENTS.md 的补充规格。它不用于重新推翻当前方案，而用于把此前跨会话中已经形成共识、但尚未完整沉淀进正式文档或代码约束的设计决策统一收口。

后续接手者应先用本文件与当前仓库进行需求—设计—代码一致性审查，再决定具体改动；不应拿到本文件后直接开始大规模编码。

## 当前唯一实现基线

新版工程 D:\studyplan 作为唯一正式实现基线。旧版 E:\codex_workspace\study-plan 只允许作为只读参考、思路来源或局部代码复用来源。

新版不承担旧数据迁移、旧 API 兼容、双 Schema、双执行流程、旧认证逻辑或任何为了兼容旧版而产生的长期维护成本。

## V1 总原则

V1 以个人本地使用和完整学习闭环为目标，优先验证产品价值，而不是提前建设平台化能力。

V1 不做多用户 SaaS、登录注册、复杂 RBAC、MCP、Sandbox、Skills Runtime、多 Agent 自组织、GraphRAG、复杂知识图谱推理、模板市场、高并发专项优化。

但数据模型、模块边界和接口设计应为未来云端、多用户、模板复用和外部工具接入留出扩展点。

# 二、产品目标与学习闭环

## 核心问题

产品不是“生成一张学习计划表”，而是帮助一个不知道如何系统学习的人，从目标定义一路走到通过实践证明自己真正掌握。

典型问题包括：不知道从哪里开始；课程零散；不知道前置关系；不知道哪些知识只需了解、哪些必须掌握；不知道理论如何落地；不知道 RAG、MCP、Memory、LangGraph 等子领域学到什么程度；不知道技术方案在不同场景下如何取舍。

## 目标闭环

统一闭环：学习目标 → 知识结构 → 学习路径 → 学习资料 → 阶段学习 → 用户总结 → AI 反馈 → 实践任务 → 实际成果 → 验收证据 → 路径调整。

V1 的成功不以 Agent 数量、测试数量或代码规模判断，而以一个真实用户是否可以顺畅完成上述闭环判断。

## 从零开始，不做复杂能力诊断

V1 默认用户从零开始。用户可以主动跳过已掌握节点、改变资料形式、调整学习顺序、要求展开某个子领域。

暂不建立复杂入门测评、能力画像、0–100 mastery score、知识掌握概率或自动评级体系，避免评测系统先于产品闭环。

# 三、核心领域模型与状态设计

## Knowledge Node 是稳定连接点

知识结构和学习计划必须分离，但通过稳定的 knowledge_node_id 连接。知识结构描述“这个领域包含什么以及知识之间有什么关系”，学习计划描述“当前用户以什么顺序、什么资料和什么实践去学习这些知识”。

禁止把知识树和学习计划做成两套复制的数据结构。

## 建议的 KnowledgeNode 字段

id、title、description、prerequisites[]、subtopics[]、learning_objectives[]、recommended_resources[]、reflection_prompts[]、practice_refs[]、optional_extensions[]、status。

## 知识节点状态

建议统一为 NOT_STARTED、LEARNING、LEARNED、VERIFIED、REVIEW_NEEDED、SKIPPED。

阅读完成或用户自称会了只能进入 LEARNED；VERIFIED 必须来自可检查的真实证据，如总结、实践任务、项目成果、测试结果、代码、运行结果或 Agent 验收。

## PracticeTask 与知识节点双向关联

PracticeTask 至少包含 id、related_knowledge_nodes[]、objective、requirements、expected_output、acceptance_criteria、evidence[]、result。

系统必须能回答两个问题：为什么我要做这个实践；这个实践究竟验证了哪些知识。

## 计划版本化

学习计划会随着跳过节点、增加子主题、修改顺序、调整资料而变化，因此禁止覆盖式修改。

建议使用 Plan、PlanVersion、PlanNode；每次结构性调整形成新版本，旧版本永久保留。总结、实践、会话和验收结果应继续关联当时的 plan_version。

# 四、学习内容组织、资源与实践

## 围绕一个真实主项目组织

尽量避免大量互不关联的小练习。对工程型方向，应围绕一个可以逐步演化的主项目组织阶段实践。

例如 Agent 开发可按：最简单 Agent → Tool Calling → RAG → Memory → LangGraph → Evaluation → 后续 MCP/Sandbox 逐步演化。

最终用户得到的不只是“完成了若干任务”，而是一个能够持续扩展、可以用于复盘和简历展示的真实项目。

## 正式固化学习阶段流程

推荐阶段流程：学习资料 → 用户学习 → 用户总结 → AI 检查理解 → 指出遗漏/误解 → 实践任务 → 用户先提出实现思路或 Prompt → AI 评审 → 外部 Codex/IDE 实现 → 提交成果 → Agent 验收 → 更新节点状态。

## 教学目标不止是“知道是什么”

在合适的学习节点加入三个问题：作者为什么这样设计；还有哪些替代方案；换一个业务场景后这个方案是否仍合适。

目标是训练技术选择能力，而不是只记住 API。

## 学习资源策略

优先选择连贯作者、连贯课程或连贯项目主线，而不是完全按单页相关性拼装材料。重复知识不一定删除，可视为计划内复习。

Resource 建议至少保存 title、author、source、url、version、sections、related_nodes[]、resource_type、difficulty、validation_status。

平台主要保存学习索引，不应大量复制第三方教程正文、视频内容或文档。大型资料优先保存 URL、目录、版本、哈希、更新时间和可检索索引；小型资料可以进入知识库。

## 动态资源偏好

视频、文字教程、官方文档、项目源码、中文、英文等偏好应是可随时改变的配置，不做复杂 Persona。

学习路径和目标保持稳定，资源选择层根据偏好调整。

## 路径外知识探索

当用户临时询问 GraphRAG 等路径外主题时，先判断它属于哪个 Knowledge Node，再判断是核心、扩展、高级还是无关内容，然后解释并在必要时提出计划调整建议。

LLM 只能提出 Proposal，不能直接修改知识树或计划结构。结构修改必须经过 Proposal → Schema Validation → Domain Rules → Plan Update。

# 五、LangGraph、Agent 与模型路由

## LangGraph 的职责

项目继续采用 LangGraph，但它只负责 Workflow 编排，Domain Service 负责业务规则。

State 中只保留当前执行必要字段，如 goal_id、current_stage、candidate_nodes、selected_resources、pending_decision、errors。完整用户数据、完整知识树、数据库对象、完整聊天历史和大段文档必须通过 ID/Repository 获取，不能塞进 State。

## 避免 Mega Agent

建议拆成有边界的 PlanningGraph、LearningGraph、ReflectionGraph、PracticeGraph、PlanAdjustmentGraph。

每个 Workflow 必须输入明确、状态有限、最大步骤有限、有终止条件和错误边界。禁止 Agent 自己反复重新规划而形成不可预测循环。

## 模型路由三层

L0 确定性逻辑：权限、状态机、Schema、数据库查询、工具参数、节点状态、精确命令。

L1 本地小模型：意图分类、query rewrite、简单分类、简单摘要、低风险轻问答。

L2 云端模型：学习规划、复杂问答、多资料推理、学习反馈、实践设计、方案比较、计划调整、成果验收。

任务稍微复杂时优先进入 L2，不能为了省一次云调用构建一个比云调用本身更复杂的 Router。

## 隐私与失败边界

本地模型失败后禁止在用户无感知情况下自动把私有内容发送云端。

模型调用层至少应表达 allow_cloud、allow_external_data、budget、privacy_scope 等边界。

# 六、RAG、Context 与 Memory

## RAG 与 StudyPlan 解耦

个人多模态 RAG 已作为独立项目发展，StudyPlan 不应再次复制完整 RAG 实现。

StudyPlan 只依赖 KnowledgeRetrievalPort，例如 retrieve(query, scope, filters) -> Evidence[]。底层可替换 Simple Keyword、pgvector、独立 RAG Service、WeKnora Adapter 或其他 Retriever。

StudyPlan 不应该依赖具体 embedding 模型名称。

## 检索目标是提供证据

推荐管线：Query → Restricted Rewrite → Keyword/Vector → RRF → Dedup → Version Filter → Optional Reranker → Evidence Gate → Context Builder → LLM → Citation Verification。

不是所有问题都必须走完整检索管线，应根据问题复杂度控制。

## 证据不足处理

Evidence Quality 和 Model Capability 必须分开。检索不到证据不能简单换更强模型。

正确流程是 Evidence insufficient → Targeted retrieval → 仍不足则明确告诉用户证据不足，不让模型猜。

## ContextBuilder 独立化

上下文不能简单把全部聊天历史拼入 Prompt。建议 ContextBuilder 统一管理 Current Goal、Current Plan Node、Current Knowledge Node、Recent Session、Relevant Memory、Retrieved Evidence、Practice State 与 Token Budget。

## Memory 与 Conversation 分离

至少区分 Raw Conversation、Structured Memory、Summary、Project State。Raw Conversation 是原始证据，Summary 只是导航，不能生成摘要后删除原始上下文。

Summary 应能够通过 source_event_ids 回溯原始会话。

## Memory Scope 与写入策略

数据模型建议保留 USER、PROJECT、SESSION 三种 scope；V1 可只真正启用 PROJECT 和 SESSION，为未来云端版本保留 USER。

长期记忆不能由模型自由写入。建议 Conversation → Memory Candidate → Memory Policy → Deduplicate → Conflict Detection → Persist。记忆记录来源、时间、类型、置信度和是否经用户明确确认。

# 七、前端信息架构与交互规则

## 最终布局比例

默认布局继续采用 Navigation 11% / Plan 17% / Canvas 72%，记为 N / P / C / A，其中 A 为右侧学习助手。

## 学习助手定位

学习助手不是右下角聊天浮窗，而是右侧独立区域。用户打开助手后仍应同时看到当前学习目标、节点、子知识、前置知识和资料，不应因为对话而脱离学习上下文。

学习助手必须与 current_node_id 绑定。

## 四区联动

默认 N + P + C；打开 A 时自动折叠 N，形成 P + C + A；若用户主动重新打开 N，则折叠 P，形成 N + C + A。

原则是始终保证主 Canvas 可用宽度。Canvas 建议不低于约 600px；A 支持拖拽调宽，并在达到阈值时自动折叠左侧栏。

## Canvas 内容

Canvas 不应只展示课程列表，而应围绕当前节点展示：当前目标、当前知识节点、为什么要学、前置知识、核心概念、子知识、学习资料、思考问题、用户总结、AI 反馈、实践任务、阶段成果。

## 会话与学习过程绑定

Conversation 不是普通聊天历史。Session 建议记录 session_id、plan_version、knowledge_node_id、stage_id、session_type。

用户重新打开旧 Session 时，应恢复当时正在学习什么，而不是只恢复几条消息文本。

## 视觉方向

保持简洁但不单调：暖白、石墨灰、克制强调色、内容优先，接近知识工具/编辑器。避免大面积深绿色、大量渐变、发光按钮、AI SaaS 模板化视觉和首页堆满聊天框。

# 八、系统架构、接口和安全边界

## 后端模块边界

保持 API → Application → Domain → Ports → Infrastructure。建议模块包括 catalog、planning、resources、learning、reflections、practice、progress、memory、retrieval、ai_gateway、integrations。

避免 PlatformService、AppManager、SystemState 等万能服务承载所有逻辑。

## 前后端严格分离

React 不应理解 LangGraph、Provider、RAG 实现、Prompt 或 Agent State，只消费稳定业务 API。

可采用类似 GET /plans/{id}、GET /knowledge-nodes/{id}、POST /reflections、POST /practice/{id}/submit、POST /assistant/messages、POST /plan-adjustments 的业务接口。

## 模型输出不可信

模型产生的 JSON、工具调用、计划、节点和参数全部视为不可信输入，必须经过 Schema Validation + Domain Validation。

工具调用必须经过 Tool Whitelist + Parameter Validation，禁止模型凭空创造不存在的工具。

## 错误分类

至少区分 INPUT_ERROR、DOMAIN_ERROR、RETRIEVAL_ERROR、MODEL_ERROR、PROVIDER_ERROR、VALIDATION_ERROR、INFRA_ERROR。

禁止把所有异常都吞掉并统一返回“AI generation failed”，否则后期无法定位是用户输入、模型、JSON、RAG 还是数据库问题。

# 九、V1/V2 边界与未来扩展

## V1 必须冻结的核心能力

Goal → Knowledge Outline → Plan → Resources → Learning Session → Reflection → AI Feedback → Practice → Evidence → Acceptance → Progress → Plan Adjustment。

## 明确从 V1 删除

MCP、Sandbox、Skills Runtime、通用工具市场、多 Agent 自组织、GraphRAG、复杂知识图谱推理、多用户 SaaS、RBAC、登录注册、团队协作、高并发专项优化、课程交易市场、完整模板商业平台、复杂 mastery score、全自动互联网爬虫、AI 自动修改 Knowledge Graph。

## 未来 Learning Template / Knowledge Pack

云端阶段可以为同一方向沉淀 Learning Template、Resource Index、Knowledge Pack、Practice Template。后续用户在模板基础上结合个人目标、资源偏好、学习速度和已掌握节点生成 Personal Plan。

模板改进可以利用哪些资料有效、哪些节点常被跳过、哪些练习常失败等聚合信息，但用户私人学习行为和成果是否用于公共模板改进必须显式授权。

## 领域扩展方式

不要声称系统天然支持所有领域。建议首个完整领域继续使用 Agent 应用开发，后续 Cloud、AI Full Stack、RAG、Backend、Frontend、DevOps 等通过 DomainPack 扩展。

一个 Pack 可以包含 knowledge_nodes、dependencies、resources、practice_templates、reflection_prompts、acceptance_rules。

# 十、复用策略与工程治理

## 减少重复造轮子

复杂能力实现前依次判断：当前项目是否已有；个人 RAG 项目是否已有；成熟开源库是否已有；是否真的需要自己实现。

默认优先顺序：Reuse → Adapter → Extend → Build。

## 开源参考原则

可参考 WeKnora、LightRAG、LangGraph、Codex Memory、Tencent Agent Memory 等成熟项目，但重点吸收模块边界、数据模型、检索管线、Memory 策略、工具安全、Context 构建和 UI 信息结构，不为“显得完整”把整个框架搬入项目。

代码复用应记录来源、License、版本、修改点、依赖和采用原因。

## 失败矩阵

继续采用 P0/P1/P2/P3。P0 数据破坏、安全问题、主流程不可用，必须修；P1 核心功能明显错误，当前阶段必须修；P2 边缘或低频错误，可以延期但必须负责人确认；P3 体验优化和小问题进入 backlog。

不要因为 P2/P3 让一个里程碑无限 Debug。

## 完成定义

功能状态至少区分 Implemented、Tested、Integrated、Verified。关键功能只有到 Verified 才算真正完成。

Codex 报告“52 passed”属于 Reported Evidence。关键里程碑还应核对命令、exit code、测试结果、commit 和 artifact 后再标记 Verified。

## 版本冻结

重要里程碑继续使用 make verify-mX；通过后 commit、负责人确认并打 git tag。

冻结 Schema、OpenAPI、Prompt、模型、Embedding、Evaluation Dataset、Acceptance Evidence 等关键证据，确保可复现。

## 受控真实模型验收

真实 Provider 调用继续采用 ConfirmPaidRun、AcceptanceId、ProjectId 等显式控制。

记录 submission_intent、provider attempt、result、evidence；同一个 Acceptance ID 不允许重复消费，以控制成本、重复执行和验收证据。

## 测试策略降复杂度

日常开发优先 Unit → Targeted Integration → Critical E2E。完整测试放到 Milestone Verification，不再每改一行代码就跑整个系统。

目标是减少此前开发时间被过度 Debug 和重复测试占用的问题。

# 十一、评测与真实验收

## 评测围绕产品问题

重点验证 Plan Quality、Resource Quality、Grounding、Learning Progress、Practice Quality、Cost。指标服务产品，而不是让产品服务指标。

## 最小真实验收集

场景 1：从零学习 Agent，验证完整规划。

场景 2：用户跳过 Prompt，验证计划调整。

场景 3：用户偏好视频，验证资源替换。

场景 4：用户突然询问 GraphRAG，验证路径外知识处理。

场景 5：用户总结错误，验证 AI Feedback。

场景 6：用户提交实践，验证 Evidence → VERIFIED。

场景 7：重新打开旧 Session，验证学习上下文恢复。

场景 8：修改学习计划，验证 Plan Version。

## V1 最终真实流程

至少完成一次：创建学习目标 → 生成学习路径 → 选择节点 → 访问资料 → 学习 → 写总结 → AI 反馈 → 实践任务 → Codex/IDE 实施 → 上传成果 → 验收 → 更新状态 → 调整计划。

全部真实运行成功以后，才定义为 V1 可交付。

# 十二、必须补齐或修订的正式文档

## PRODUCT_SCOPE.md

明确产品解决什么问题、V1 是什么、V1 不是什么、V2 是什么。

## DOMAIN_MODEL.md

定义 Goal、KnowledgeNode、Plan、PlanVersion、PlanNode、Resource、LearningSession、Reflection、PracticeTask、Evidence、AcceptanceResult、Memory 及关系。

## ARCHITECTURE.md

描述 Frontend、Backend、LangGraph、RAG、Memory、AI Gateway、Database 的模块边界和依赖方向。

## LEARNING_WORKFLOW.md

正式描述 Plan → Learn → Reflect → Practice → Verify，并定义每一阶段输入、输出和状态变化。

## RAG_DESIGN.md

明确 Retrieval Port、Evidence、Citation、ContextBuilder，说明 StudyPlan 与独立 RAG 服务的边界。

## MEMORY_CONTEXT.md

明确 raw conversation、summary、structured memory、scope、source traceability 和 token budget。

## MODEL_ROUTING.md

明确 L0 Rules / L1 Local / L2 Cloud，以及隐私、预算和失败降级边界。

## FRONTEND_INTERACTION.md

固化 11/17/72、N/P/C/A、侧栏折叠、拖拽阈值、会话恢复、节点与助手联动。

## EVALUATION_ACCEPTANCE.md

明确验收场景、Evidence、P0–P3、Real Provider Acceptance 和 V1 最终验收标准。

## ADR/

记录重要不可逆或长期影响决策，如新版不兼容旧版、LangGraph 定位、RAG 解耦、Plan Version 等。

## AGENTS.md

作为 AI 开发总入口：权威文档、V1 范围、禁止事项、当前里程碑、验证方式、延期规则、允许命令和需要审批的操作。

# 十三、M0 到 M4.5 实施顺序

## M0 / S0：规格冻结

完成 PRODUCT_SCOPE、DOMAIN_MODEL、ARCHITECTURE、V1/V2 Boundary、ADR Index、AGENTS.md。

清理正式文档中的旧版兼容、登录注册、SaaS、MCP、Sandbox、Skills 等已失效描述。

## M1：核心领域模型

优先打通 Goal、KnowledgeNode、Plan、PlanVersion、PlanNode、Resource。

完成 Goal → Knowledge Outline → Plan；此阶段不要引入复杂 AI。

## M2：学习执行闭环

加入 LearningSession、Reflection、AI Feedback、Progress。

完成 Learn → Summary → Feedback。

## M3：资源与知识检索

加入 ResourceIndex、KnowledgeRetrievalPort、Evidence、Citation、ContextBuilder。

优先复用已有个人 RAG 项目能力，不重新实现第二套大型 RAG。

## M4：实践与验收

加入 PracticeTask、Evidence、AcceptanceResult。

完成 Practice → Evidence → Verify → Progress。

## M4.5：真实完整流程验收

跑通创建目标、规划、资料、学习、总结、反馈、实践、实现、提交成果、验收、状态更新和计划调整。

M4.5 是 V1 可交付门槛。

## V2 之后

V2 再引入 MCP、Sandbox、Skills、Tool Approval、External Calendar、Browser Agent、Execution Environment。

更后期才考虑 Multi User、Template Library、Knowledge Pack Marketplace、Shared Resource Index、Community Feedback、Template Optimization。

# 十四、接手者执行规则与 Gap Analysis

## 十条实施规则

1. 不要因为发现旧代码就重新加入兼容层。

2. 不要因为某个边缘测试失败让整个开发停数天。

3. 不要为了展示 Agent 能力构建复杂 Agent。

4. 不要让 LangGraph 变成业务数据库。

5. 不要让 LLM 直接修改核心结构。

6. 不要为了省一次云模型调用构建复杂模型 Router。

7. 不要重新实现已经存在于个人 RAG 项目的成熟能力。

8. 不要把所有学习资料复制到系统。

9. 不要在核心闭环完成前做高并发和大规模性能优化。

10. 每次新增复杂度都必须回答：它是否直接帮助用户完成一次完整学习闭环？如果不是，后置。

## 接手后的第一项工作

不要直接按当前代码继续堆功能。先执行一次需求—设计—代码一致性审查。

比较本补充计划 + 现有需求文档 + 软件设计 + ADR + IMPLEMENTATION_PLAN + 当前代码。

## 必须产出的 Gap Analysis

- A. Requirement Gap：哪些已经讨论确认的需求尚未进入正式规格。

- B. Design Gap：哪些设计已经确定，但代码仍采用旧结构。

- C. Implementation Gap：哪些规格已经存在，但实现尚不存在。

- D. Overengineering：哪些已经实现的内容超出 V1。

- E. Conflict：哪些旧文档与当前决策冲突。

## Gap Analysis 后的顺序

先修改正式需求文档，再修改软件设计、ADR、IMPLEMENTATION_PLAN、AGENTS.md；重新映射 M0–M4.5；最后才开始实际代码改造。

文档目标不是无限扩充，而是把已经讨论清楚的产品思想转换为一致、可执行、可验收的软件设计。

# 十五、V1 交付判断标准

## 唯一核心标准

项目是否能让一个真实用户输入“我要从零学习 Agent 开发”，然后知道应该学什么、为什么要学、先学什么后学什么、去哪里找可靠资料、知识之间有什么关系、如何总结和接受反馈、如何把知识应用到真实项目、如何用证据证明学会并继续下一阶段。

如果这一流程顺畅成立，V1 成功；如果流程尚未成立，却已经拥有 MCP、Sandbox、多 Agent、复杂 GraphRAG、上千测试和大量基础设施，核心产品仍未完成。
