# AI 全栈路线深审：从 Web 心智模型到可上线的 AI 产品

> 产品语义：方向描述目标能力，不绑定职业、单个项目、单个框架或单个 Recipe。章节与阶段是可裁剪的默认教学骨架；按目标和起点选取，并尊重实际前置。
>
> Continuous Outcome Carrier 优先使用用户合适项目；范围过大时裁成可维护纵切面。没有项目才推荐 Default Starter Project。能力暂不适合迁入项目时，先做独立 Micro Exercise，再按需要迁回；允许重构/替换实现，保留问题、测试、数据、接口、设计决策与验证证据。下面项目名称及增量列均为默认候选示例，不要求把每项能力装进同一代码仓库。
>
> 项目案例都是可替换候选，审读深度以标准目录为准。阶段验收由用户提交并确认的证据支持，不自动判定 mastery、不自动打分。完整规则见 [PLANNING_SEMANTICS_STANDARD.md](PLANNING_SEMANTICS_STANDARD.md)。

研究日期：2026-10-03。此审查只覆盖 AI 全栈方向；资源按实际阅读深度标注，不等于对整个课程/仓库逐行审计。免费在线教材是路线主体；API 费用可能产生，按阶段启用且先设预算。没有修改 StudyPlan 仓库。

## 建议

把路线压成一条连续的产品主线：先做一个浏览器里的资料列表，再让它通过 HTTP 调用 FastAPI；随后接入一次非流式模型调用、保存资料和会话、加上流式交互与错误恢复，最后按是否真的要多人使用决定认证和部署。默认贯穿项目候选用“AI资料工作台”，但第一版是本地单用户研究工作台；先让“资料条目—AI 摘要/行动项—会话历史”闭环成立，仅当用户目标需要时扩成团队共享。这样能在每一阶段保留一个可运行成果，也不会为了路线完整而过早制造团队权限、上传解析和 RAG。

推荐的学习次序是：

1. 复核浏览器、HTTP、JSON，以及刚好够 React 用的 JavaScript；补 FastAPI 所需 Python 时也只补当前缺口。
2. React 组件、Props、列表、状态和表单，先用本地假数据做界面。
3. FastAPI 的路由、请求/响应模型、验证、错误、依赖；先用 `/docs` 观察和手工调试契约。
4. 在后端连接生成模型，先返回完整 JSON，再处理结构化输出和 provider 边界。
5. 当用户明确需要保存之后再讲 SQL 和 SQLModel，建立真实持久化。
6. 读通 SSE 生命周期并做前端增量渲染；之后补测试、限流、密钥、认证和部署。
7. 只有产品目标确实需要“从团队资料里找证据回答”时，才把文件摄取、RAG、引用和评测作为后续专项。

它不是“先把 JavaScript、React、FastAPI、SQL、RAG 各学完，再开始项目”。每一项都由下一个垂直切片触发。路线的目标是让学员能解释一次用户请求如何从浏览器组件、HTTP 请求、FastAPI 验证、模型 provider、SQL 持久化返回到浏览器，并能用测试和部署检查证明它工作。

## 前置审计：哪些门槛该刚好出现

### JavaScript 不是无条件先修

React 的实际章节例子直接使用函数组件、对象、JSX 中的表达式、`filter()`/`map()` 和稳定 `key`；加上 API 接入需要 Promise、`async/await`、`fetch` 和 JSON。若学员已经能读写变量、字符串、数组/对象、条件、循环、函数与返回值、事件处理、JSON、异步请求，就通过小测跳过 MDN 全套。若缺异步或网络请求，仅补 MDN 网络请求/JSON/异步 JavaScript。若连基础语法都不稳，再按 MDN Scripting 模块顺序补核心部分。

建议的最低自测：用一份资料数组写 `filter` 与 `map`；注册按钮事件；`fetch` 一个 JSON API 并处理状态码、解析结果和失败；将一条记录序列化为 JSON。能够解释“HTTP 404 不等于网络 Promise reject”后再进 React API 阶段。MDN Scripting 的正式前置是 HTML 和基础 CSS，而不是“必须先上完整 JavaScript 课程”；它通过变量、运算、字符串、数组、条件、循环、函数、事件、对象、DOM、network requests、JSON 和错误处理循序渐进。异步章节要求已具备稳固 JS 基础，因此这里按缺口进入。

`javascript.info` 用作查漏解释器，不与 MDN 双修。MDN 是结构化入门主线；javascript.info Fetch 正文明确 `fetch()` 遇到 HTTP 404/500 仍会兑现为 `Response`，应查 `response.ok/status`，而后才读 body。这一点直接转化为项目中的错误状态处理。它也有 Promise chaining 和 async/await 的可运行示例。高级原型、类、装饰器等不阻塞本路线。

### Python 是按需补，不与 JavaScript 交叉堆课

FastAPI 样例以类型注解、函数、字典/列表、异常、模块、环境配置和 `async` 为主。官方 Python Tutorial 明说自己面向“会编程但不熟 Python”的人，因此不适合作为零编程起点。先借第一阶段 JS 练习熟悉变量、循环和函数；到了 FastAPI 阶段，用 Python 官方教程的 3.1–3.2、4.1/4.2/4.8、5.1/5.5、6、8.2–8.4 按缺口映射，能读懂 FastAPI 示例即止。跳过 `match`、装饰器深挖、复杂参数形式、数据结构全套、旧式格式化和高级语言机制。

### SQL 应在持久化需求第一次成立时出现

API 暂时无状态时，学员还不能体会“为什么需要表、主键、约束和查询”。当工作台要在刷新后保留资料、会话、消息时，引入关系型表、主键/外键、非空/唯一约束、`SELECT/WHERE/ORDER BY/LIMIT`、`INSERT/UPDATE/DELETE` 和 `JOIN`。先画 2–3 张表（`workspace`/`source`/`message`），手写 SQL，再用 FastAPI 的 SQLModel/SQLite 页面搭 session dependency 和 CRUD。FastAPI SQLModel 页作者明确说它是短入门而非 SQL 课程，不能把 ORM 示例误认为数据库课程。

中文 Datawhale Wonderful SQL 有可执行数据库示例和连续章节，可作中文讲解补充，但不宜独自充当语义权威：课程基于 MySQL 8.0，SQL 方言不同于路线初始 SQLite；第 1 章把 `COMMIT/ROLLBACK` 归在 DCL，且把 MongoDB 举为 KVS；第 2 章“逻辑执行顺序”例子次序写错；对 `GROUP BY` alias 的规则也不宜泛化。用 PostgreSQL 官方教程作为 SQL 语义核对，按 `SELECT`、表表达式与 JOIN 学对应概念；本练习先用 SQLite/SQLModel 运行，明确 `AUTOINCREMENT/日期/布尔值/冲突更新` 等方言差异，不在同一周要求学员装 MySQL 和 PostgreSQL。

## 主 Spine 的教学质量与边界

| Spine | 已读的教学顺序和示例 | 适合主教的部分 | 不能替代/需要补足 |
|---|---|---|---|
| MDN Learn Web Development / JavaScript | 已查看目录及正文示例：变量到函数/事件、对象与 DOM，再到 network request、JSON、debugging；另读 async JS、Promise、Fetch 表单提交示例。 | 若 JavaScript 真是新知识，按其顺序补核心；REST/Fetch 首次入门；浏览器事件和请求错误。 | 不教 React 组件状态模型、后端 API 契约或现代 app 架构。`map/filter` 需单独快速练。 |
| React Learn 官方文档 | 已读 Quick Start、Describing the UI、Thinking in React、Adding Interactivity、Managing State、You Might Not Need an Effect、Synchronizing with Effects 的正文/示例。 | **主前端 Spine**：先描述 UI，再交互/状态、状态结构/上提，最后 Effects 作为外部系统同步逃生口。 | 不负责 FastAPI 或数据层；官方文档是主题化参考，不是每个主题都需完成。部署构建接 Vite。 |
| FastAPI 教程 | 已读教程目录和 First Steps、Path/Query、Request Body、Response Model、Errors、Dependencies、SQL Databases、Testing、SSE、Settings 等正文；Security/CORS 与示例另读。 | **主后端/API Spine**：参数绑定和验证、Pydantic、OpenAPI、response model、HTTP 错误、依赖、测试、SQLModel 接入、SSE。 | SQL 页面明确很短；OAuth2 password 演示与最新安全最佳实践冲突；部署/鉴权/限流仍需额外核对。中文译页标注 AI 与人类协作，困难点双看英文。 |
| Microsoft Generative AI for Beginners + OpenAI 当前 API 文档 | 读了 Microsoft 仓库当前目录与第 1、4、6、7、8、13、14、15 课的正文片段/示例；另读 OpenAI 当前 API text、streaming、structured outputs、production、rate limits、errors 页面。 | GenAI 课 01/04 建 LLM 与 prompt 直觉，06 可见服务端应用连 API 的入门代码；当前 API 文档约束 OpenAI 接口边界。 | GenAI 课程不教 React/FastAPI/关系型持久化/auth/生产架构。仓库在 2026-07 标注 GitHub Models 退役，2026-10 不应照旧运行该 provider 示例。课程中 Azure/OpenAI 片段混合，不能当最新 endpoint 契约。 |
| SQLModel + PostgreSQL 官方 SQL + Wonderful SQL | 已读 SQLModel FastAPI SQL 数据库章节全段例子；PostgreSQL `JOIN` 示例；Wonderful SQL ch01、ch02/ch04/ch05 选段。 | Datawhale 讲概念与小题，Postgres 帮核语义，SQLModel 把表/DTO/session 接进 API。 | 不要把多种 DBMS/ORM/迁移一次塞进起步；先关系、简单 SQL，再 repository/ORM，迁移工具作为部署增量。 |

## React 章节的编排判断

不要把 `useEffect` 当“接口请求钩子”从第一天教。推荐章节顺序：

1. [Quick Start](https://zh-hans.react.dev/learn)：作为 1 小时全貌预览，不把它当独立完结课；观察组件、JSX、props、事件和 `useState`。
2. [Describing the UI](https://zh-hans.react.dev/learn/describing-the-ui)：顺读组件、导入导出、JSX、在 JSX 中写 JavaScript、props、条件渲染、列表/`key`、纯函数组件。正文示例从 `Profile/Card/Avatar` 展开；数组章节实际写 `filter()` 与 `map()` 并说明数据库 ID 适合作为 `key`。
3. [Thinking in React](https://zh-hans.react.dev/learn/thinking-in-react)：用静态产品表格设计组件树，找最小状态、从状态推导结果，并把共享状态上提。先静态结构再 state，正适合工作台的资料列表和搜索。
4. [Adding Interactivity](https://zh-hans.react.dev/learn/adding-interactivity)：事件、状态快照、更新队列、表单输入与不可变更新；用于本地资料筛选、编辑和提交。
5. [Managing State](https://zh-hans.react.dev/learn/managing-state)：何时上提、避免重复状态、组件 key 重置、复杂状态何时考虑 reducer。初版只教最小 state 和上提；reducer/context 按复杂度再读。
6. 先读 [You Might Not Need an Effect](https://zh-hans.react.dev/learn/you-might-not-need-an-effect)，再读 [Synchronizing with Effects](https://zh-hans.react.dev/learn/synchronizing-with-effects)。两章教用户把“从点击提交 prompt 的 POST”留在事件 handler，把纯派生状态直接计算；Effect 只连接组件外部系统/同步生命周期。若首屏加载要同步远程数据，可到该切片再看取消/清理/竞态，或在之后引入 server-state 工具，不能把 Effect 变成万能状态机。

与 MDN 关系：语法、函数、数组、事件如果已会属 **REVIEW**；React 将它们组织为组件树、Props、state 与纯 render 属 **NEW**。对 UI 中重复保存“可由其它状态计算出来”的值，React 的例子是 **DEEPEN**：从单纯 JS 变量转为响应式 render 约束。不同资料讲同一语法不用重读整套。

Vite 只承担轻量脚手架和交付：以官方 `guide`/`build`/`static-deploy` 阅读建立开发服务器、生产静态构建和 preview 的差异。`vite preview` 仅用于本地预览构建产物，不当生产 server。路线暂不要求 TypeScript/Tailwind/状态管理框架，避免和 Python 同时引入第二种类型系统及过多工具面。

## FastAPI 章节的编排判断

将 FastAPI 教程当连续 API 主课，但只读为当前一条产品切片服务的章节：

- [First Steps](https://fastapi.tiangolo.com/zh/tutorial/first-steps/) → 浏览器地址、路径操作、HTTP 方法、`/docs` 和 `/openapi.json`。
- [Path Parameters](https://fastapi.tiangolo.com/zh/tutorial/path-params/) 与 [Query Parameters](https://fastapi.tiangolo.com/zh/tutorial/query-params/) → 资源 ID、分页/搜索条件、类型解析、路径排序问题。
- [Request Body](https://fastapi.tiangolo.com/zh/tutorial/body/) → Pydantic 输入对象和 JSON；GET request body 先不使用。
- [Query / String validations](https://fastapi.tiangolo.com/zh/tutorial/query-params-str-validations/) 与 [Path / Numeric validations](https://fastapi.tiangolo.com/zh/tutorial/path-params-numeric-validations/) → 先验证类型和长度，模型调用前拒绝空白/过长输入，避免无效花费。
- [Response Model](https://fastapi.tiangolo.com/zh/tutorial/response-model/) → 分开公开输出和内部模型，避免把 provider key、内部字段一并序列化。
- [Response Status Code](https://fastapi.tiangolo.com/zh/tutorial/response-status-code/) 与 [Handling Errors](https://fastapi.tiangolo.com/zh/tutorial/handling-errors/) → 区分验证错误、预期业务拒绝和意外 5xx；让前端显示 retry/empty/error 状态。
- [Dependencies](https://fastapi.tiangolo.com/zh/tutorial/dependencies/) → 在有模型客户端/DB session/当前用户之后抽出依赖；不要提前教通用依赖注入框架。
- [Settings and Environment Variables](https://fastapi.tiangolo.com/zh/advanced/settings/) → 把模型密钥与配置放服务端环境变量/secret store。
- [Testing](https://fastapi.tiangolo.com/zh/tutorial/testing/) → pytest + HTTPX TestClient 调路由、核 status/JSON；UI 与 API 合并后补契约/端到端。
- [SQL Databases](https://fastapi.tiangolo.com/zh/tutorial/sql-databases/) → SQLite/SQLModel 的 Session dependency、表模型与 DTO 分离、CRUD。
- [CORS](https://fastapi.tiangolo.com/zh/tutorial/cors/) → 只有前后端 origin 不同就会遇到；协议、域名、端口任一不同都算不同 origin。开发时只放本机前端 origin；部署时显式 allowlist，不用 `*` 和凭据混搭。
- [Server-Sent Events](https://fastapi.tiangolo.com/zh/tutorial/server-sent-events/) → 在非流式端点和 UI 状态已可靠后读，了解 event id、断线恢复等；当前教程页说明 FastAPI 0.135.0 加入 SSE 支持，锁版本/检查安装版本。若学习目标要求更早版本，先读通用 streaming response，不复制新 API。
- [Deployment Concepts](https://fastapi.tiangolo.com/zh/deployment/concepts/) → 进部署阶段再读 HTTPS、worker、启动/重启、进程和容器概念；云厂商操作单独按目标宿主补。

错误类型是教学核心：Pydantic 自动处理的 422 不能误当模型异常；明确的资源不存在/未授权以 HTTPException 状态表达；模型 provider 超时/限额要被包装成有界、可测试、用户可恢复的业务错误；未预期异常日志保留 request id 而不把堆栈曝给客户端。

### Auth：教程样例可读，生产姿势不能照搬

Auth 放在 DB 已分区后、多用户公开前：此时已经有 `workspace_id`/`owner_id` 可以真正验证隔离，不然只增加登录页而无权限故事。阅读 FastAPI [Security First Steps](https://fastapi.tiangolo.com/zh/tutorial/security/first-steps/)、[Get Current User](https://fastapi.tiangolo.com/zh/tutorial/security/get-current-user/)、[Simple OAuth2](https://fastapi.tiangolo.com/zh/tutorial/security/simple-oauth2/) 和 [OAuth2/JWT](https://fastapi.tiangolo.com/zh/tutorial/security/oauth2-jwt/) 是为理解 `Depends`、Bearer header、用户依赖、哈希、过期 token 和 OpenAPI 集成。实际示例包含内存假用户、示例 secret key 和密码式 OAuth 流。RFC 9700 §2.4（2025）明确要求不使用 Resource Owner Password Credentials grant；所以该 FastAPI 教程里的 password flow 只能作为学习代码/历史上下文，公网产品用已维护身份系统提供的 OIDC/OAuth Authorization Code + PKCE、适合部署的 session/cookie 策略，或有明确安全设计的 IdP 集成。每个数据查询都从已验证身份求 workspace ownership，测试 A 用户不能读写 B 用户资源。模型供应商 API key 是服务器身份密钥，与用户登录 access token 完全分开；绝不传给浏览器。

## GenAI 内容的复核

主线只需抓“模型调用作为一项不确定、收费、外部 I/O”的工程边界：

- Microsoft [01 Introduction](https://github.com/microsoft/generative-ai-for-beginners/tree/main/01-introduction-to-genai)：token/LLM 下一 token 生成、非确定性、局限，可当概念复习；没有教全栈业务服务。
- [04 Prompt Engineering Fundamentals](https://github.com/microsoft/generative-ai-for-beginners/tree/main/04-prompt-engineering-fundamentals)：system/task/input/示例等 prompt 结构和 Jupyter 练习，有 API key/runtime prerequisite；已有 prompt 经验用 **REVIEW**，本路线把重点移到可测试 prompt 版本和服务边界，是 **DEEPEN**。
- [06 Text Generation Apps](https://github.com/microsoft/generative-ai-for-beginners/tree/main/06-text-generation-apps)：实际展示 SDK 接入与 Responses 风格代码，适合作为概念演练；但整课也保留 Azure API version 环境示例、provider 差异和占位符 key。当前 OpenAI 文档说新文本应用建议 Responses API；接口、model、参数支持按供应商/版本查当前文档，不照抄旧的 temperature/endpoint 假设。
- [07 Chat applications](https://github.com/microsoft/generative-ai-for-beginners/tree/main/07-building-chat-applications)：可取聊天 UX、上下文/架构讨论，别把其概要章节当 persistence/auth/SSE 的完整教程。
- [08 Search applications](https://github.com/microsoft/generative-ai-for-beginners/tree/main/08-building-search-applications)、[15 RAG and vector databases](https://github.com/microsoft/generative-ai-for-beginners/tree/main/15-rag-and-vector-databases)：只有团队工作台需要“找来源并引用”时升级为 **NEW** 专项；本次抽读到的 RAG 代码展示 embedding/chunking/vector db 入门，不构成可靠完整的解析、检索评测和生产 ingestion pipeline。
- [13 Securing AI Applications](https://github.com/microsoft/generative-ai-for-beginners/tree/main/13-securing-ai-applications)、[14 GenAI application lifecycle](https://github.com/microsoft/generative-ai-for-beginners/tree/main/14-the-generative-ai-application-lifecycle)：在上线前补风险、评估、监控；若 Agent 路线已学模型安全/评测，只 **REVIEW** 概念并 **DEEPEN** 到 Web 产品中的数据隔离、误用、成本和生产回归。

当前 provider 参考以 [OpenAI text guide](https://developers.openai.com/api/docs/guides/text)、[Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)、[Streaming](https://developers.openai.com/api/docs/guides/streaming-responses)、[Rate Limits](https://developers.openai.com/api/docs/guides/rate-limits)、[Errors](https://developers.openai.com/api/docs/guides/error-codes)、[Production best practices](https://developers.openai.com/api/docs/guides/production-best-practices) 为一组选页；这些是供应商级具体实践，不应包装成所有 LLM provider 通用规范。文档建议新文本应用选择 Responses API；结构化输出要求按 schema 约束但仍需处理 refusal 与 token 截断；stream 读 `response.created`、`response.output_text.delta`、`response.completed`、`error` 生命周期；429/503 先遵 `Retry-After`，否则 exponential backoff + jitter，限制重试次数和总耗时，billing/quota error 不盲重试；SDK 本身可能带 retries，需避免嵌套重试放大请求。生产 API key 放环境变量或 Secret Manager，不能留在客户端仓库。

“多 provider”不要在第一版抽象成插件平台：先把业务入口依赖一个 `LLMProvider.generate()`/stream 接口，将 provider 配置限制在后端 adapter。等需要切模型、回退、测成本时再比较第二家 provider，这属于 **COMPARE**；不同 API 是否一致属于 **VERSION_CONTEXT**，以运行时包版本、当前官方文档、针对性契约测试为准。

## 持续项目审查：“AI 团队资料工作台”是否自然

它可以自然贯穿，但要改成逐级价值，而不是从第 1 周就需要“团队”：

| 版本 | 真实用户动作 | 新知识自然解决什么 | 交付证据 |
|---|---|---|---|
| v0 本地研究板 | 浏览、搜索、标记几条资料；先由固定数组供数 | React 组件、列表、事件/状态 | 可交互静态页面；未需要 API/账号 |
| v1 资料 API | 工作台列表来自 FastAPI，可新增/改名/归档资料 | HTTP、JSON、请求/响应 schema、验证/错误、CORS | UI → API 完整 CRUD；`/docs` 可试 |
| v2 AI 助理 | 点击“为此资料生成摘要和 3 个行动项” | provider adapter、prompt、结构化输出、超时/错误/预算 | API key 仅后端；结果可验证 JSON |
| v3 可恢复状态 | 刷新仍能看资料、会话和生成结果 | SQL、FK/约束、CRUD/transaction、session/ORM | 两三张表、手写 SQL 题、SQLModel tests |
| v4 可读的聊天 | 对话实时显示生成；重试/停止/错误可见 | SSE、stream state、partial completion/error | 前后端 streaming path；断线和失败行为有测试 |
| v5 多人工作区（可选） | 同事登录后只看自己获授权的工作区 | Auth、membership、tenant isolation、权限测试 | 用两个用户证明交叉访问被拒绝 |
| v6 上线分享 | 别人通过公网使用、出错可追踪 | 部署、HTTPS、CORS、secret、数据库备份、日志与模型花费 | 可打开网址、健康检查、部署说明/回滚记录 |
| v7 证据型检索（可选专项） | 上传资料并回答“依据是什么” | 解析、chunk、检索、引用、坏例评测、来源权限 | 一组标注问题和检索/回答评测表 |

初学者友好性：**通过限定第一用户/功能后适合**。若第一周就要求团队、OAuth、文件解析、向量数据库、管理员、审批、Stripe，则范围不友好。Optional Career Overlay：仅career_goal=interview/project_showcase时使用；表达素材较丰富；具备用户故事、API schema、表结构、prompt schema、故障路径和部署链接时，能讲明端到端及设计理由。学习路径的验收成果要包含一段请求时序、ERD、API 契约、关键测试和 2 个已知限制，而非只有漂亮聊天框。

## 真实项目推荐卡候选（供后续 StudyPlan 生成，不锁版本/源码位置）

### A. 可控全栈垂直切片：FastAPI Full Stack Template 的单条 Item 闭环

- `repo_url`: https://github.com/fastapi/full-stack-fastapi-template
- 身份核查：仓库位于 FastAPI 官方 GitHub 组织，项目描述是 FastAPI + React + SQLModel + PostgreSQL + Vite；README 列有类型验证、JWT/密码哈希、Playwright、pytest、Docker Compose、CI/CD。
- `why_now`: 学完 React、HTTP、FastAPI、SQL 基础且已做过自己的 CRUD 后，观察真实全栈如何把 API、DB、UI、测试接起来。
- `prerequisites`: 能说清 CRUD 请求/响应与 Pydantic/React 状态；会 Git 基本操作；SQL/ORM 知道 PK/FK/session；尚未学 TS 不要从大模板全盘照抄。
- `scope`: 只走一个实体的 list/create/update/delete 垂直切片，从 OpenAPI/API schema 到前端列表与测试；若只为读代码，可看模板项目说明、后端/前端 README、测试结构。
- `learning_focus`: 比较前后端分离/同域部署、生成 API client、实体/DTO、错误传递和测试边界；观察但不立即实施 auth、邮件恢复、管理员仪表盘、Traefik 和 CI/CD。
- `desired_depth`: 先整体地图，再一个 CRUD 切片，建立带标注的请求路径图；不追完整生产模板。
- `risk_and_boundary`: repo 本身功能丰富且使用 TypeScript、Tailwind、TanStack、Postgres、Docker，完整模板对新手过大。把“可控”定义为一次只学一个实体闭环；如果用户想逐文件写入，先用自建小项目，模板仅做对照。
- `study_mode`: 当前源码动态定位，不绑定 commit/文件/函数。

### B. AI 产品参考：OpenAI Responses Starter App 的一轮对话/流式垂直切片

- `repo_url`: https://github.com/openai/openai-responses-starter-app
- 身份核查：公开仓库在 OpenAI GitHub 组织下，README 明确它是 Next.js starter，基于 Responses API；展示 multi-turn、stream/tool、文件搜索、MCP、第一方 Google connectors，MIT。
- `why_now`: 学员已理解浏览器—server boundary、基本 API 与模型限制后，可对照一个正在使用当前 Responses API 的 AI app 样例，把“model call”提升为真实产品行为。
- `prerequisites`: React 基础、服务端 route/secret 概念、至少一个非流式生成端点；读 TypeScript/Next.js 不是本路线先决条件。
- `scope`: 只拆“提交一条输入 → server 调 Responses API → stream 回 UI → 处理错误/多轮状态”或只拆“文件搜索工具配置”；一次一个切片。
- `learning_focus`: 多轮状态如何传递、delta stream 的显示、provider tool 与 app state 边界、server env key、引用注释/工具选择。
- `desired_depth`: 中层学习样例，先看 README 和高层请求图，再根据当前源码定位一个切片；不需要照搬 Next.js 到 FastAPI。
- `risk_and_boundary`: Next.js 全栈服务和 FastAPI 架构不同；带多种高级工具、Google OAuth 和外部配置，会扩大范围。只用作 **COMPARE**/产品设计参照，不使用用户个人邮箱连接器当起步依赖。

### C. 大型 AI 产品目标切片：Open WebUI 的会话/Provider/RAG 其一

- `repo_url`: https://github.com/open-webui/open-webui
- 身份核查：该仓库 README 自述为 Open WebUI 主项目并链接官方文档；支持 Ollama 和 OpenAI-compatible APIs。README 当前列出多模型、channels、持久化、SQLite/Postgres、多个向量库、身份/SCIM、OpenTelemetry、Redis/多节点等成熟平台功能。
- `why_now`: 自己的 v1–v6 可用并能解释 API、数据库、认证、部署后，才用来学习真实平台一个明确目标；不做全仓导览式“读完项目”。
- `prerequisites`: 全栈基础、SQL/FK、多用户 auth 基础、provider 调用、测试/部署概念；选择 RAG 切片时还需完成 RAG 专项。
- `scope`: 一个学习阶段先聚焦1个切片（总体目标可组合多个）：A 会话保存与跨 provider 数据形态；B provider adapter 与 model config；C workspace/用户隔离；D 一个检索/引用路径；E 按一个行为追测试。由学习目标决定，不同时分析五个。
- `learning_focus`: 自建工作台做出来的能力如何在大型平台遇到配置层、扩展点、多 provider、迁移兼容和观测要求。
- `desired_depth`: 3–8 个问题组成的专项片段，一次解一个；先运行地图，再动态定位当前实现，以源码事实、解释、推断分开写。
- `risk_and_boundary`: 功能矩阵远大于初学路径；不要把其多后端/向量库/LDAP/SCIM/集群配置纳入课程基本 Spine，也不固定源码位置或 commit。

## 汇总与改版决策

1. 保留 React 官方 Learn + FastAPI 官方 Tutorial 作为前后端两条主教 Spine；其它教程只按缺口补充。
2. MDN JavaScript 是先决自测未过后的 JIT 补课，而非所有人必须完成的门槛。javascript.info 做精选解释，不进行整站学习。
3. SQL 进入点放在第一次保存用户资料之后；Datawhale 可读但 PostgreSQL 官方和真实 SQLite/SQLModel 查询共同校正其版本/规则。
4. GenAI 学概念、prompt、模型调用，但接口契约用当前 provider 文档；不直接照抄 2026-07 退役的 GitHub Models 示例。
5. Streaming 放在完整 response + UI error/loading 已稳定之后；Auth 放到数据库有租户/归属模型之后；Deployment 在单条端到端 vertical slice 和最小测试之后。
6. 无用户项目时可从单用户AI资料工作台默认候选MVP开始。团队 Auth、上传/RAG、多 provider、复杂向量栈都是按真实目标触发的专项，不是基础毕业条件。
7. 生产认证示例存在规范冲突：FastAPI 示例可教依赖和 Bearer/JWT 结构，但遵 RFC 9700；不把 Password Grant 配置列为公网上线出口条件。

资源正文范围和 `review_depth` 详见同目录 [fullstack_resources.json](RESOURCE_CATALOG_NORMALIZED_DRAFT.json)，逐项证据与打开过的 URL 详见 [fullstack_research.md](RESEARCH_LOG.md)。
