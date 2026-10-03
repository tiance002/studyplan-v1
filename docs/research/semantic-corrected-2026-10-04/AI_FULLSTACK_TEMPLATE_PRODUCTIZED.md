# AI 全栈学习模板（章节级编排）

> 产品语义：方向描述目标能力，不绑定职业、单个项目、单个框架或单个 Recipe。章节与阶段是可裁剪的默认教学骨架；按目标和起点选取，并尊重实际前置。
>
> Continuous Outcome Carrier 优先使用用户合适项目；范围过大时裁成可维护纵切面。没有项目才推荐 Default Starter Project。能力暂不适合迁入项目时，先做独立 Micro Exercise，再按需要迁回；允许重构/替换实现，保留问题、测试、数据、接口、设计决策与验证证据。下面项目名称及增量列均为默认候选示例，不要求把每项能力装进同一代码仓库。
>
> 项目案例都是可替换候选，审读深度以标准目录为准。阶段验收由用户提交并确认的证据支持，不自动判定 mastery、不自动打分。完整规则见 [PLANNING_SEMANTICS_STANDARD.md](PLANNING_SEMANTICS_STANDARD.md)。

方向目标：形成可运行、可测试、可部署的AI全栈能力。用户没有合适项目时，Default Starter Project候选为“AI资料工作台”，下面用它展示章节应用。它先服务单人研究工作流，再由真实需要决定是否增加团队登录、文件检索、多个 provider。课程教概念，小练习验证概念，持续项目只应用当前阶段刚学会的能力。

所有教材均为可免费阅读的在线页面；模型 API 使用可能产生费用，只有进入模型阶段后才开启。每阶段均可在能力门槛满足时略过，不要求重复已掌握内容。`REVIEW / COMPARE / DEEPEN / VERSION_CONTEXT / NEW` 含义：已掌握快回顾 / 同一问题对照两种实现 / 学习真实工程边界 / 因版本导致差异 / 全新能力。

## 路线地图

| 阶段 | 学习节点 | 工作台持续成果 | 进入下一阶段的证据 |
|---|---|---|---|
| 0 | 能力盘点（仅诊断） | 做一个准备页面，记录工具与知识缺口 | 记录 JS/Python/Git 现状；除进入 React 前的 JS gate 外，不提前补课 |
| 1 | Web、HTTP、JSON、JS 请求 | 本地静态资料板 | 解释一次 HTTP request/response，处理成功与失败 |
| 2 | React UI 与状态 | 搜索、筛选、编辑的资料板 | 能从数组驱动画面；不重复保存派生状态 |
| 3 | FastAPI API 契约 | UI ↔ JSON API CRUD | 用 `/docs` 操作 API；验证错误和业务错误清楚 |
| 4 | GenAI API + provider | 资料摘要和行动项 | 模型密钥留在后端；结构化输出有 schema 和失败处理 |
| 5 | SQL/持久化 | 刷新后资料、会话仍存在 | 会写基础 CRUD + 两表 JOIN；能解释 FK 和 Session |
| 6 | SSE 流式交互 | 回答逐步出现、可取消/重试 | 处理完成、错误、断线/部分结果与事件顺序 |
| 7 | 测试、限额与错误恢复 | 关键路径被自动验证 | 以 mock 覆盖正常/拒绝/超时/429/错误输出 |
| 8 | Auth / 多用户隔离（按目标） | 同事仅看授权工作区 | A 用户不能查看/修改 B 的对象，行为有测试 |
| 9 | 部署与运行 | 公网可访问工作台 | HTTPS、CORS、secrets、数据库、health 与部署复现有记录 |
| 10 | 专项：知识检索/多模型/评价 | 只增加被用户价值触发的能力 | 用标注小集证明新能力的价值和已知限制 |

## 阶段 0：先做自测，别预先读整套前置

### 0A. JavaScript 小测

- **为什么现在**：React 正文用 JavaScript 表达式、对象、数组 `filter/map`、函数和事件；API 需要异步请求。
- **前置**：基本 HTML/CSS 能搭一张卡片；不要求已学 React。
- **主读/选读**：先打开 [MDN Scripting](https://developer.mozilla.org/zh-CN/docs/Learn_web_development/Core/Scripting) 的目录。最低测：变量/字符串/数组/对象、if/loop、function/return、事件处理、JSON、`fetch`、Promise/`async-await`、`map/filter`。
- **按缺口进入**：无 JS 基础就顺着 MDN 的「变量→数学/字符串→数组→条件/循环→函数→事件→对象→DOM→网络请求→JSON→调试」学核心；HTTP 请求不会时专门读 [MDN 使用 Fetch API](https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API/Using_Fetch) 与 MDN [异步 JavaScript](https://developer.mozilla.org/en-US/docs/Learn_web_development/Extensions/Async_JS)。`javascript.info` 的 [Fetch](https://javascript.info/fetch)、[Promise chaining](https://javascript.info/promise-chaining)、[async/await](https://javascript.info/async-await) 按解释缺口选读。
- **重复处理**：MDN 已学过的基础语法 → **REVIEW** 小测，不整套重读；MDN 异步与 javascript.info 对应章节 → **COMPARE** 仅在 Promise 状态、响应体一次性读取、HTTP status 概念有疑问时对照；Array `filter/map` 用 15 分钟补 React 实际要求。
- **小实践**：给定 6 个本地资料对象，通过输入框过滤标题；按钮点击后 `fetch` 一个公开 JSON 接口，分别显示 loading/data/404/error。
- **项目增量**：确定数据字段（`id/title/source_url/note/created_at`）并画出 `Browser → HTTP → API → response JSON → UI`；先不写 React。
- **出口**：能口头解释 404 为什么不会让 `fetch()` Promise 自动 reject；能看出 response parsing 和 error check 是两个步骤；熟悉数组、函数、事件、对象。
- **来源边界**：javascript.info 是全站免费在线教程，电子书有单独付费选项；路线仅用免费网页。

## 阶段 1：Web 心智模型和第一个浏览器请求

- **为什么现在**：后面所有“前后端联调、CORS、SSE、密钥放置”都建立在浏览器发起请求、服务端回响应上。
- **前置**：阶段 0 编程自测通过，或已有基础。
- **主读**：[MDN HTTP Overview](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Overview) 的 client/server、stateless/session、request、response/status、HTTP-based APIs 部分；MDN [Fetch API](https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API/Using_Fetch) 的 GET 与 POST JSON 示例。读到能画请求结构为止，不进 TCP/TLS/缓存/代理细节。
- **补充**：[FastAPI CORS](https://fastapi.tiangolo.com/zh/tutorial/cors/) 只先看 origin = protocol + host + port 的解释；具体配置留到阶段 3。
- **重复关系**：Agent 路线若讲过工具调用/服务端请求，它与浏览器 HTTP 流程不是同一边界；服务端对模型的请求可 **COMPARE**，用户浏览器的同源/CORS 是 **NEW**。
- **小实践**：打开 DevTools Network 观察一条 GET 和一条 POST：方法、URL、Request Headers、JSON body、Status、Response Body。
- **项目增量**：搭一个静态 HTML 页面，展示 6 条固定资料；输入框过滤并有清空按钮。
- **出口**：能指认 request method/path/header/body 与 status/response body；能说明请求由浏览器开始；知道 API key 放浏览器代码里会泄露。

## 阶段 2：React 的 UI 与交互

- **为什么现在**：在开始 API 前先把界面状态理顺，免得把网络状态、搜索状态和模型会话混成一个巨型组件。
- **前置**：JavaScript 函数、数组、对象、模块导入导出、map/filter、自定义事件处理过关；HTML/CSS 足以读 JSX。
- **主读（顺序就是练习顺序）**：
  1. [React Quick Start](https://zh-hans.react.dev/learn)：作全局预览，略过不懂的 hook 深度细节。
  2. [Describing the UI](https://zh-hans.react.dev/learn/describing-the-ui)：组件/导出/JSX/JS 表达式/props/条件/列表与 key/纯组件。
  3. [Thinking in React](https://zh-hans.react.dev/learn/thinking-in-react)：从静态组件树定位最小 state，派生过滤结果，状态上提。
  4. [Adding Interactivity](https://zh-hans.react.dev/learn/adding-interactivity)：事件、useState、快照/更新队列、表单、数组对象不可变更新。
  5. [Managing State](https://zh-hans.react.dev/learn/managing-state)：状态结构与共享状态；Reducer/context 先只了解其存在。
  6. [You Might Not Need an Effect](https://zh-hans.react.dev/learn/you-might-not-need-an-effect) → [Synchronizing with Effects](https://zh-hans.react.dev/learn/synchronizing-with-effects)：先认识何时不用 Effect，再学真正的同步情形。
- **补充**：[Vite Guide](https://vite.dev/guide/) 用来建项目；[Build](https://vite.dev/guide/build)、[Static Deploy](https://vite.dev/guide/static-deploy) 留到部署。暂不引入 TypeScript、Redux、TanStack Query、Tailwind、Next.js。
- **暴露处理**：JSX/数组操作是已有 JS 的 **REVIEW**；组件树、state 快照、纯 render 是 **NEW**；“派生值不存第二份”属 **DEEPEN**；旧教程里 lifecycle/class components 与当前函数组件 docs 有差异则标 **VERSION_CONTEXT**，初版不学旧 API。
- **小实践**：把资料条目数组拆成 `WorkspacePage / SearchBar / SourceList / SourceRow`；加过滤、归档切换和编辑 modal；派生后的 filtered list 不放入 state。
- **项目增量**：本地研究板达到可点击的产品界面，使用假数组；添加 `loading / empty / error / ready` 的 UI 空态占位。
- **出口**：可以解释组件为什么拆成这些部分、搜索输入状态在哪、何时 state 要上提；能为列表项使用稳定 id key；能区分用户点击提交与外部系统同步。

## 阶段 3：FastAPI API 契约、验证与错误

- **为什么现在**：静态资料板已经明确有哪些字段、操作和 UI 空态，正好把隐式需求变成 API 契约。
- **前置**：了解 HTTP/JSON；Python 缺口此时才补，不在阶段 0 预先要求掌握。
- **JIT Python 补缺（仅有缺口时）**：FastAPI route 是 Python 函数，body/response 用 Pydantic/type hints，依赖也用函数。先做入场测：能读懂函数、list/dict、type hints、异常和 `async def` 示例则直接继续；否则查官方 [Python Tutorial](https://docs.python.org/3/tutorial/) 的 3.1–3.2、4.1/4.2/4.8、5.1/5.5、6、8.2–8.4。该教程明确面向会编程但新学 Python 的人，不是零编程入门。用一条练习将阶段 0 的资料数组筛选改写为 Python 函数，能读 FastAPI 代码即止；不提前学完整 Python 课程。
- **主读**：沿 FastAPI [Tutorial](https://fastapi.tiangolo.com/zh/tutorial/) 依序选读：
  - [First Steps](https://fastapi.tiangolo.com/zh/tutorial/first-steps/) → 用 `/docs` 调 `GET /health` 与简单 route。
  - [Path Parameters](https://fastapi.tiangolo.com/zh/tutorial/path-params/) → `/sources/{source_id}`。
  - [Query Parameters](https://fastapi.tiangolo.com/zh/tutorial/query-params/) → search/limit/offset。
  - [Request Body](https://fastapi.tiangolo.com/zh/tutorial/body/) → `SourceCreate`/`SourceUpdate` JSON。
  - [Query validation](https://fastapi.tiangolo.com/zh/tutorial/query-params-str-validations/) → 字符长度、分页范围；[Path/Numeric validation](https://fastapi.tiangolo.com/zh/tutorial/path-params-numeric-validations/) → ID 范围。
  - [Response Model](https://fastapi.tiangolo.com/zh/tutorial/response-model/) → 输出 DTO；[Status Codes](https://fastapi.tiangolo.com/zh/tutorial/response-status-code/) → 201/204；[Handling Errors](https://fastapi.tiangolo.com/zh/tutorial/handling-errors/) → 404/422/业务冲突与通用服务器异常。
  - [Dependencies](https://fastapi.tiangolo.com/zh/tutorial/dependencies/) → request-level shared policy；复杂组合以后再学。
- **补充**：MDN HTTP methods/status codes 只查所用状态码；[`javascript.info/fetch`](https://javascript.info/fetch) 复核浏览器要 `response.ok`。
- **暴露处理**：MDN 写 request/response 思路为 **REVIEW**；前端用 OpenAPI 自动 API docs 是 **NEW**；输入模型、持久化模型、公开响应分离是 **DEEPEN**。
- **小实践**：手动给一个 POST 送有效 JSON、缺字段、错误类型、超长字段；让学员看到 OpenAPI 对应的 422；`GET /sources/{id}` 不存在回 404。
- **项目增量**：React 页面改为调用 FastAPI 的 `GET/POST/PATCH/DELETE /sources`；分页/搜索使用 query 参数。先用内存数组保存，重启丢失可接受。
- **出口**：能画 API 表（method/path/input/status/output/error），能用 Swagger 文档手工调用，能解释 422 是输入校验而非 provider 失败；可以本地独立启动 FE/BE 并查 CORS。

## 阶段 4：把 GenAI 作为一项服务能力接进来

- **为什么现在**：已有稳定 API 入口、输入模型和错误面；现在给一个资料增加清楚的用户价值，而不是先堆 Prompt 专题。
- **前置**：服务端能接收/返回 JSON；async/network 概念；完成服务端环境变量练习。
- **主读**：Microsoft GenAI for Beginners [Lesson 01](https://github.com/microsoft/generative-ai-for-beginners/tree/main/01-introduction-to-genai) 的 token/生成局限/非确定性；[Lesson 04](https://github.com/microsoft/generative-ai-for-beginners/tree/main/04-prompt-engineering-fundamentals) 中 role / task / input / few-shot 概念；[Lesson 06](https://github.com/microsoft/generative-ai-for-beginners/tree/main/06-text-generation-apps) 只读当前 API 接入、服务端调用、代码示例并辨别 provider 设定。
- **接口权威**：OpenAI [Text generation](https://developers.openai.com/api/docs/guides/text) 的 Responses API 起步；[Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs) 定义摘要结果如 `summary:string, actions:string[], open_questions:string[]`。每次上线前按已选 provider 当前指南复核 model/SDK/参数，固定版本和回归测试。
- **暴露处理**：前序 Agent 项目学过 prompt/LLM 时概念 **REVIEW**；prompt 针对 Web 业务、数据长度、成本和回归测试是 **DEEPEN**；模型 API/SDK 和 JSON schema 是 **NEW**；Azure API vs OpenAI Responses 是 **COMPARE + VERSION_CONTEXT**。
- **小实践**：给 10 段同一主题短文固定输入，让模型生成符合 Pydantic schema 的摘要；对照输出字段是否完整、拒绝/截断状态。不要一开始让模型在数据库上任意调用工具。
- **项目增量**：新增 `POST /sources/{id}/summary`。后端从 Secret 环境变量读取 key，adapter 隔离 provider，模型结果先返回不保存；手写 5 个正常输入/错误输入/超长文本 case。
- **出口**：key 没出现在浏览器/HTML/网络 request；输出要经 schema 校验；能区分 provider 失败和用户输入错；能描述模型的非确定性与费用上界。

## 阶段 5：SQL 第一次出现——保存资料、会话和消息

- **为什么现在**：学员已经实际看到状态丢失，能列出要保存的对象；数据库不再是脱离需求的理论课。
- **前置**：能够描述实体字段及关联；API 至少有内存 CRUD。
- **主读顺序**：
  1. 中文概念练习：[Wonderful SQL ch01](https://github.com/datawhalechina/wonderful-sql/blob/main/ch01_%E5%88%9D%E8%AF%86%E6%95%B0%E6%8D%AE%E5%BA%93.md) 的表/行/列、类型、`NOT NULL`、主键、建表、插入/更新/删除；只做到能理解结构。
  2. [ch02](https://github.com/datawhalechina/wonderful-sql/blob/main/ch02_%E5%9F%BA%E7%A1%80%E6%9F%A5%E8%AF%A2%E4%B8%8E%E6%8E%92%E5%BA%8F.md) 的 `SELECT`、`WHERE`、排序/limit、聚合/分组；先在自己的小表里运行，再用其练习题检验。
  3. [PostgreSQL 官方教程 JOIN](https://www.postgresql.org/docs/current/tutorial-join.html) 与 [Table Expressions](https://www.postgresql.org/docs/current/queries-table-expressions.html) 对照 inner/left join；先明确列名并写 `ON`。
  4. [FastAPI SQL Databases](https://fastapi.tiangolo.com/zh/tutorial/sql-databases/) 使用 SQLModel + SQLite 创建 table、session dependency、Create/Read/Update/Delete；读 input/table/public models 区别。
  5. 需要更多中文 join 讲解时再读 [Wonderful SQL ch04](https://github.com/datawhalechina/wonderful-sql/blob/main/ch04_%E9%9B%86%E5%90%88%E8%BF%90%E7%AE%97.md) 4.2；暂不学 Natural Join。
- **暂不学**：SQL 面试题、窗口函数、存储过程、索引调优、数据库内部原理、多数据库部署、异步 ORM。索引在测量到慢查询后再进；迁移工具在 schema 需要升级时再进。
- **重复处理/校正**：SQL 课程重复介绍 CRUD → **REVIEW** 但需做题；ORM 和手写 SQL 同一行为 → **COMPARE**（它们是表达方式，不是互斥语义）；MySQL 示例迁到 SQLite/Postgres → **VERSION_CONTEXT**；FK/session/model boundaries → **DEEPEN**。Wonderful SQL 有个别不准确/方言特定说明，关键规则由 DB 官方文档与本地运行校正。
- **小实践**：手写三表 ERD `workspace(id)`、`source(id, workspace_id)`、`message(id, conversation_id, role, content, created_at)`；写 `SELECT`（where/order/limit）、insert source、update title、delete message、JOIN 查会话中的消息。运行前对 `UPDATE/DELETE` 确认 where 条件。
- **项目增量**：把内存 list 换 SQLite/SQLModel；保存资料、生成摘要、会话和消息。至少验证重启服务数据仍在，删除资源时外键/级联策略有意图。
- **出口**：在空白表上写基础 CRUD/inner join；能解释主键、外键、nullable/unique、input/table/public model 和 per-request session；知道 SQLModel 教程不是完整 SQL 教程。

## 阶段 6：Streaming 与 UI 流状态

- **为什么现在**：整体响应已能正确保存和显示；此时处理流能区分“内容生成体验”和“业务数据完整性”。
- **前置**：阶段 4 的单次完整响应可工作；阶段 5 可保存完整响应；懂 HTTP body/connection 但无需掌握底层传输细节。
- **主读**：[MDN HTTP overview 的 HTTP APIs/SSE 部分](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Overview) 了解 SSE 为服务器向浏览器的一向 event stream；OpenAI [Streaming API responses](https://developers.openai.com/api/docs/guides/streaming-responses) 的 `response.created / response.output_text.delta / response.completed / error` 生命周期；FastAPI [Server-Sent Events](https://fastapi.tiangolo.com/zh/tutorial/server-sent-events/) 的服务端事件样例、`Last-Event-ID`/断线恢复说明。注意当前 FastAPI 教程页标注新增于 0.135.0，选用较低版要按版本查通用 StreamingResponse。
- **补充**：React interactivity/state 重新 **REVIEW**，专注 pending partial/error/cancel。
- **小实践**：独立写 SSE “倒计时/字符串分块”服务端和浏览器 EventSource，再接 provider streaming；前端将 delta append 到当前 AI 消息，完成后写入 DB。
- **项目增量**：摘要/问答增量出现；提供停止、重新生成、断线提示；请求发起和完成状态显式存储。检查关闭浏览器时服务能停止或安全丢弃，部分答案不冒充完整完成。
- **出口**：能画 4 种事件路径、说明哪个事件代表最终完成；可诊断被代理缓冲导致“并未实时显示”的边界；能区分输入 POST 与 SSE 输出连接；会在 UI 上展示中断和重试。

## 阶段 7：测试、provider 可靠性、成本限额

- **为什么现在**：接入真实模型、流式和持久化后，错误开始影响数据和费用；部署前要能用可重复测试证明关键边界。
- **前置**：FastAPI app 有独立 route/service/provider 层；核心请求和响应 shape 已确定。
- **主读**：FastAPI [Testing](https://fastapi.tiangolo.com/zh/tutorial/testing/) 中 TestClient/pytest/`assert`；OpenAI [Rate limits](https://developers.openai.com/api/docs/guides/rate-limits)、[Error codes](https://developers.openai.com/api/docs/guides/error-codes)、[Production Best Practices](https://developers.openai.com/api/docs/guides/production-best-practices)。
- **重复关系**：前序 Agent eval/模型测试 → **REVIEW**；Web 产品要覆盖 schema、用户错误、权限、并发双击、数据库故障、API usage → **DEEPEN**。SDK 版本可能内建 retries 是 **VERSION_CONTEXT**，每次升级读取 SDK docs/release behavior。
- **小实践**：将 provider mock 成 fixture；固定 5 个摘要 case，对正常输出/结构化拒绝/不完整结果/超时/429 分别断言状态码和 UI message；数据库集成用临时 SQLite DB。
- **项目增量**：加入服务器 request id、结构化日志（不记录完整敏感输入）、客户端请求大小限制、模型 token/input size guardrail、每用户或匿名开发环境调用预算、超时与单一 retry policy。遇 429 遵 `Retry-After`，无效/缺失时指数退避加随机抖动；设置 attempts + 总时限；额度/账单错误不重试。若 SDK retries 打开，禁用 app 重试或纳入总次数。
- **出口**：任意模型 API 未配置/超限不能让 UI 假死；生产密钥来自环境变量/secret manager；能看到哪些错误可重试、哪些不能；不使用真实在线模型做大批次无界测试。

## 阶段 8：Auth、权限和多租户（目标触发）

- **为什么现在**：只有当用户要邀请同事、公开访问或保存他人数据时，登录才解决真实问题；此时数据库已经有 workspace ownership。
- **前置**：SQL FK 和查询习惯；测试会做；HTTP cookie/header 基本概念。若工作台始终本地个人使用，可跳过这一步。
- **教程读法**：FastAPI [Security First Steps](https://fastapi.tiangolo.com/zh/tutorial/security/first-steps/) 与 [Get Current User](https://fastapi.tiangolo.com/zh/tutorial/security/get-current-user/) 学 `Depends` 和 Bearer 接口形态；[OAuth2/JWT](https://fastapi.tiangolo.com/zh/tutorial/security/oauth2-jwt/) 选读哈希/过期/校验/异常部分，并和 [RFC 9700 §2.4](https://www.rfc-editor.org/rfc/rfc9700.html#section-2.4) 比较 password grant。
- **安全规范**：RFC 9700 规定 Resource Owner Password Credentials grant 不应使用；因此 FastAPI password flow 示例是教学上易懂的旧流程，不可作为现代公网上线模板。实际产品优先使用提供 Authorization Code + PKCE/OIDC 的维护型 IdP，按部署语境选安全 session/cookie 或服务端 token；权限判断仍由 API 对每个资源执行。
- **小实践**：两测试用户 A/B，各自建立 workspace/source；同一 `GET /sources/{id}` 和修改/删除在跨用户访问时拒绝且不泄露对象存在细节。
- **项目增量**：加 workspace memberships/role（先只 owner/member），所有查询从已验证 user 的 membership 范围筛选；模型 provider key 始终用服务端 project secret，跟用户 token 隔离。
- **出口**：A 无法列出/读取/更改 B 的资源；所有关键 route permission 测试通过；理解“登录成功”和“有权访问该 workspace”是不同检查。

## 阶段 9：上线一个小版本

- **为什么现在**：产品有一条可端到端使用的路径、DB 和基本测试，可以通过部署暴露配置/进程/跨域问题。
- **前置**：React production build、FastAPI start command、env config、测试都清楚。
- **主读**：Vite [Production Build](https://vite.dev/guide/build) + [Static Deploy](https://vite.dev/guide/static-deploy)；FastAPI [Deployment Concepts](https://fastapi.tiangolo.com/zh/deployment/concepts/) + [Docker](https://fastapi.tiangolo.com/zh/deployment/docker/)；FastAPI [CORS](https://fastapi.tiangolo.com/zh/tutorial/cors/) 与 [Settings](https://fastapi.tiangolo.com/zh/advanced/settings/)。读当前部署平台的免费/付费限额与 Python runtime 文档，不在学习模板中锁定厂商。
- **补充读**：Vite `preview` 是本地预览，不是生产 server；FastAPI 文档讲部署概念和可选 FastAPI Cloud、Docker，不代表必须使用那个宿主。先分开静态 UI 与 API，或明确同域反代；托管 Postgres 替换本地 SQLite 时重新跑测试/迁移。
- **小实践**：在 staging 用假的 model secret 启动，再用可撤销密钥；确认 `/health` 不泄露配置；网页 DevTools 请求走 HTTPS、只允许预期 origin；作一次错误配置演练。
- **项目增量**：上线一个只用于个人/小组试用的版本；README 记录架构图、run/test/deploy、环境变量名、模型费用控制、数据备份/恢复和已知限制。真实 DB 密码和 API key 不进入 git。
- **出口**：可复现部署；健康检查通过；前端无明文 key；错误日志不泄露全文 prompt/key；可恢复 DB；有清楚的退回前一版本办法。

## 阶段 10：只选择一项 AI 产品强化

依据工作台真实目标选择，不默认一口气全部加入：

| 触发需求 | 挑选学习方向 | 入口/出口 |
|---|---|---|
| “根据内部文档回答且给出出处” | 文件上传/大小控制、解析、chunk、embedding、稀疏与密集检索、RRF/排序、citation、retrieval/answer eval、权限传播 | Microsoft [08 Search](https://github.com/microsoft/generative-ai-for-beginners/tree/main/08-building-search-applications) 与 [15 RAG](https://github.com/microsoft/generative-ai-for-beginners/tree/main/15-rag-and-vector-databases) 只用于概念起步；还需另选系统化 RAG Spine，不能把 15 课示例当生产全链路。验收要有标注问答/坏例和来源 ACL。 |
| “摘要类型增加或模型结果更严格” | Structured output schema、拒绝/不完整结果、模型变更回归 | OpenAI Structured Outputs 或选中 provider 的对应文档；十条真实样例可回归。 |
| “生成很慢，需边出边用” | SSE 生命周期、取消、缓冲、partial/complete persistence、断线恢复 | 阶段 6 扩充；没有先用非流式行为与用户需求对比就不盲目 stream。 |
| “多 provider/价格/可靠性” | provider adapter、能力差异、路由/回退、质量/成本对照 | 第二家 provider **COMPARE**，共享接口但不假设参数/流事件一致；有带标注的离线评测集。 |
| “团队访问量增加/配额紧” | 限流、队列、幂等、后台生成、观测、数据库迁移/备份 | 以当前并发/失败数据决定；先做最便宜控制，不先引进 Kubernetes/复杂消息系统。 |

完成出口：学员能说明该专项的用户价值、系统新增边界、至少一组真实坏例、测试与回滚方法；如无法讲出这些，回到 MVP，不添加新框架。

## 每个 PR/版本应留下的学习证据

- 本阶段前后用户能做什么（一个句子）。
- 被读取的章节和 review depth；未读材料不可伪装成完成。
- 小练习的输入/输出或接口测试。
- 持续项目增量、API/ERD/简化时序图中最相关一项。
- 已知限制和下一阶段触发条件。
- 如果使用模型：模型/SDK/provider 与日期、prompt version、测试样本集、预算/限额控制。


## 可替换与可裁剪规则

用户已有产品（例如旅行规划前后端）时，将资料列表/摘要/会话示例分别映射为用户自己的实体、AI功能与状态，不强迫改做资料工作台。团队/多租户不是终点要求；认证授权仅由私有数据和访问需求触发。SSE、复杂数据库、RAG、多provider和团队能力按用户目标展开，省略后保留已选阶段的章级任务与exit gate，不删除基础错误/密钥/数据边界。能力暂不适合产品时采用micro exercise，允许用新实现替换旧实现。
