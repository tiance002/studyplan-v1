# Agent 强化专项：Browser / Computer-use Agent

> 产品语义：方向描述目标能力，不绑定职业、单个项目、单个框架或单个 Recipe。章节与阶段是可裁剪的默认教学骨架；按目标和起点选取，并尊重实际前置。
>
> Continuous Outcome Carrier 优先使用用户合适项目；范围过大时裁成可维护纵切面。没有项目才推荐 Default Starter Project。能力暂不适合迁入项目时，先做独立 Micro Exercise，再按需要迁回；允许重构/替换实现，保留问题、测试、数据、接口、设计决策与验证证据。下面项目名称及增量列均为默认候选示例，不要求把每项能力装进同一代码仓库。
>
> 项目案例都是可替换候选，审读深度以标准目录为准。阶段验收由用户提交并确认的证据支持，不自动判定 mastery、不自动打分。完整规则见 [PLANNING_SEMANTICS_STANDARD.md](PLANNING_SEMANTICS_STANDARD.md)。

> 类型：Reviewed Specialization Recipe（首批已审核专项参考骨架）；binding=optional，可组合、裁剪、替换，未命中该 Recipe 不阻止规划。Evaluation 横切各阶段，参数训练按目标单独选择。

> 研究快照：2026-10-03。本文给 StudyPlan 提供章节级教学编排，不修改 StudyPlan 代码。Playwright 文档、browser-use 仓库与 AgentScope/Hello-Agents 一样都在变化。本轮设计实验未运行；没有使用真实账户、表单提交、购买、预约或发布动作。

## 路线结论

**Primary 教程 Spine：Playwright Python 官方基础文档；Primary 自主 Agent 项目：browser-use 当前仓库的开源 Python 库。** 两者承担不同教学任务。Playwright 先教授可重复的观测、定位、动作、等待、断言、上下文隔离和 trace；browser-use 再把这些浏览器控制能力放到模型驱动的 observe → reason → act → re-observe 循环中。先把基础动作做稳定，才能看懂 Agent 在哪里做错、怎样重试、如何判成功。

Hello-Agents Extra 11 适合 REVIEW/COMPARE，不替代基础课：它把 DOM、可访问性树与视觉三种观察方式放在一起，讲了 browser state 与 ReAct loop，也用 TinyFish 托管 API 演示接成 Tool。但实作需要第三方账号/API key，可能计费；后半包含 stealth、代理及规避反爬示例。StudyPlan 不应把付费托管或绕过站点防护作为必修练习。仅保留其架构观察，练习只访问自己控制的本地假网站或明确允许自动化的测试站。

browser-use 是持续演进的开源项目，而不是“浏览器 Agent 教程”。当前仓库同时提供 Python/TypeScript Agent、CLI Browser Harness、Browser Use Cloud/托管能力；本路线只选 Python 开源库的 quickstart、Agent/Browser API references、examples 和项目源码/测试。README 与项目代码提示 Python >=3.11，但模型推理及 hosted browser 是另计服务；库的 MIT 开源不意味着模型 API 或云浏览器免费。可以用本地模型探索，但能力、速度和硬件都不保证。

## 与 Hello-Agents 已学内容的关系

| 已有内容 | 已教/练到什么 | 本专项处理 |
|---|---|---|
| Hello-Agents ch4 §4.2 ReAct | 看过 Thought → Action → Observation → 下一轮，并知道 tool error 可能作为 observation 返回。 | 作为浏览器 Agent 控制循环 **REVIEW**；新增页面状态部分可观测、每个点击都有导航/弹窗/延迟/重复提交等外部结果，是 **DEEPEN**。 |
| ch6 工具与 Agent 框架实践、ch7 自建工具注册和执行 | 一般 tool schema、执行、结果回传和 agent loop。 | **REVIEW** 把浏览器包装为 tool；**DEEPEN** 观测快照/截图、浏览器上下文、tab 生命周期、导航等待、坐标动作、认证隔离与动作后复核。 |
| Extra 11 §1.1–1.2.3 | Web/RPA/GUI Agent 区别；DOM、accessibility tree、screenshot 与混合观察；浏览器生命周期和状态挑战概览。 | **REVIEW/COMPARE**，直接复述一张感知选择表；不要再次抄做 TinyFish SDK。它把感知闭环讲清了，但没有系统教授可复现的 locator/wait/input/eval。 |
| Extra 11 §2 TinyFish + Tool 代码 | 第三方托管 Agent 调用、streaming、ReAct Tool 封装示例。 | **VERSION_CONTEXT / 按需观察**：理解“外部 Web 服务也可封装成 tool”，不把 TinyFish API 当 browser-use/Playwright 标准接口；不将账号、计费或 anti-bot bypass 纳入实践。 |
| Hello-Agents ch12 Evaluation | 一般 Agent/工具任务评估入门。 | browser 专项要加 **DEEPEN**：动作后目标状态、URL/domain、安全动作、轨迹、恢复次数；只看自然语言 final answer 不够。 |

## 观察与动作的工作模型

Web 页面提供几种互补观察面，各自有盲点：

| 信号 | 适合什么 | 常见盲点 | 推荐优先级 |
|---|---|---|---|
| Semantic locator（role/name/label/text） | 可见按钮、标题、输入框、链接；与用户看到/辅助技术能命名的 UI 接近。 | 无名称控件、画布、语义标记不良、动态 UI 造成重复匹配。role locator 不是正式 accessibility audit。 | 先用，检查唯一性与操作后状态。 |
| DOM / accessibility tree | 页面结构、角色/名称、链接/表单、准确元素定位；可跟踪交互状态。 | DOM 可能遗漏 canvas/shadow widget；页面内文本是不可信内容，不能当作控制指令；仅能证明页面树中的信息。 | 编程控制优先；browser-use 当前指导优先 AX tree，打印时先过滤而非整树倒入模型。 |
| Screenshot / vision / coordinates | 布局、颜色/位置、Canvas 图、非语义视觉控件。 | OCR/小字/坐标幻觉；受视口/缩放/动画影响；每步图像推理可能增加延迟、token 和费用。 | 页面布局确实决定动作时启用；执行后再以页面状态核对。 |
| URL/network/state | 判断导航和响应、请求失败、服务端状态、tab 与浏览上下文隔离。 | 页面加载完不等于 SPA 数据就绪；网络 200 不保证用户目标完成。 | 对导航、状态提交与错误诊断作为独立信号。 |

每个动作都应以可复核的闭环结束：先观察当下页与可见目标，执行一项明确动作，等待该动作预期的语义变化，再重新观察、断言目标状态。定位失败、超时、导航未完成、权限墙、验证码、服务端错误和“动作成功但目标状态没变”必须分开记日志。**Retry 只对可安全重复且原因可恢复的操作**；对可能已提交但回执丢失的表单，先读页面/假后端状态再决定，不能 blind retry。

## 主教学 Spine：从测试到 Browser Agent

| 阶段 | Why now / JIT 前置 | Primary 章节与具体内容 | 已有知识关系、跳读范围 | 小实践与持续项目增量 | Exit gate |
|---|---|---|---|---|---|
| 0. 入口：把网页变成可测试界面 | **Why now**：在使用自主 Agent 前，先有一个确定性执行器和明确验收条件。**前置**：基础 Python、函数/异常、读写小型 HTML；已学 Hello Agents ch4/ch6/ch7 则 REVIEW tool loop，不从零重讲 Agent。 | Playwright Python Installation/Intro：装 pytest plugin 和浏览器，跑官方简单 test；接着 Writing tests 学 page/fixture 和 web-first expect。教程明确 Playwright 既适合 E2E testing，也能作为 Python sync/async general browser automation。 | Hello-Agents ch4 ReAct 做 **REVIEW**；测试断言与 Agent task judge 是 **COMPARE**。只学 Python 同步或异步的一种，本路线优先沿官方示例先掌握同步测试，接入 browser-use 时再学 async。 | 本地静态页：访问、标题断言、定位一个按钮、断言跳转到成功页。 | 能独立运行测试，失败能区分断言失败与浏览器/环境故障；没有模型调用、真实网站或真实账户。 |
| 1. 定位、表单与 actionability | **Why now**：先选择稳定且语义清楚的目标，再学习页面变化中的等待。**前置**：阶段0。 | Locators 主读：get_by_role/name、label、placeholder、text、test id；定位器组合/筛选、唯一匹配与 assertion。Input/Actions 主读 text fill、checkbox/radio、select、click、keyboard、file input。Actionability 主读 locator uniqueness、visible、stable、receives events、enabled/editable 检查及 assertion auto-retry。 | “按 CSS/XPath 写死”只是早期/目标特定工具，不做默认主法；语义 locator 与 AX tree 共用角色和名称，但 locator 仍不是 accessibility conformance audit。 | 在自造的本地表单用 role/label 填 2 个文本框、checkbox、select；提交到 fake endpoint，断言状态文本、字段值与本地计数各只变一次。 | UI 小改 label/DOM nesting 后主要测试仍通过；能解释何时 locator 不唯一、遮挡、未启用；默认不使用 force click。 |
| 2. Navigation、等待、页面状态与 trace | **Why now**：操作产生导航或新 tab 后要知道何时页面可用；固定 sleep 无法区分浏览器 ready 与业务状态 ready。**前置**：阶段1动作与 assertion。 | Navigations：goto/点击触发的 navigation、load state、SPA history 与多种 ready 条件；用页面语义/业务状态断言，不盲等 sleep。Pages：BrowserContext、Page、多个 tab/new page/popup event 与清理。Trace Viewer：按动作看 snapshots、日志、网络、时间线和失败点。 | Playwright auto-wait 保障 actionability（元素可见/稳定/可交互），**不保证应用业务请求已完成**；要额外 wait/assert 如结果数出现、状态标记变化、URL 变更或本地响应。 | 本地小 SPA：click 后 800ms 延迟出现搜索结果并更新 URL hash；开新 tab 和 popup 各一次。等待结果 locator / URL，不写固定 1 秒睡眠；失败时查看 trace。 | 能区分 navigation、document load、network idle 与具体业务就绪条件；可从 trace 指出哪一动作失败以及当时页面状态。 |
| 3. Dynamic content、异常与可控重试 | **Why now**：只有已定义目标状态，才能判断重试是否合理。**前置**：阶段2。 | Playwright auto-waiting/actionability 与 Assertions；按需选 Network/Mock APIs、Frames、Dialogs、Downloads、Clock sections。browser-use Agent Reference 的 max_failures、per-step timeout、fallback LLM 语义作为目标项目“策略参数”阅读，而非真理。 | Playwright 会等待单次 locator action 满足检查；browser-use 的模型层 retries 可能重新规划/重复动作，二者语义不同 **COMPARE**。别把“网络异常重试”应用到不确定是否提交的写操作。 | 本地站点制造：元素延迟/被遮挡后解除、请求 429 一次后成功、永不出现的元素、按钮被重复点击。对每种记录 action result、DOM state、请求数、重试数；非幂等提交有 submit ID 与模拟后端去重。 | 能对超时、定位错、被遮挡、网络 429、已提交但响应丢失分类；只在明确安全时自动 retry；否则读状态或暂停交给人。 |
| 4. Browser-use Agent 循环与观察策略 | **Why now**：已能用 Playwright 确定性完成任务后，才让 LLM 在观察上选择动作。**前置**：阶段1–3通过；理解模型 API 可能收费。 | Browser-use current open-source quickstart：安装浏览器、最小 Agent.run。Agent reference：Agent config、use_vision、timeouts、max_failures、hooks 与 AgentHistoryList。Browser reference：BrowserSession/context/tab、local browser/cloud browser、storage state、allowed_domains。Examples：keep_alive/session、structured output、sensitive_data。仓库当前 SKILL.md：优先 accessibility tree、过滤后观察、布局相关再 screenshot，导航后 wait_for_load，动作后做 targeted verification，登录墙和敏感交互应停下。 | Hello Extra11 的“三种感知” **REVIEW/COMPARE**；browser-use 默认视觉开启以及当前 SKILL 的 AX-first 提示属于 **VERSION_CONTEXT**，应学习时核对当前版本。Playwright 本身是确定性自动化；LLM 规划和 page observation 是 **NEW**。 | 只让 Agent 读取本地假 catalog 并回答“指定商品的描述”；禁止购买/下单。通过 history 记录 step、action、URL、错误、结果；固定测试集对照 Playwright baseline。 | 能指明 action 是由 agent 哪轮决定、看到哪个证据、动作后哪些状态确认；final_result 与 is_successful 不能单独作为成功判定；域名 allowlist/step 上限/超时都生效。 |
| 5. Authentication、session、安全与权限 | **Why now**：只有流程确实需要登录才讨论 auth；教程可用本地 fake login，不需要真实账户。**前置**：懂 BrowserContext/page 生命周期及受限作用域。 | Playwright Authentication：context.storage_state 导出 cookies/localStorage 等并载入新 context；Isolation 区分测试 profile/context。Browser-use Browser/Examples：storage state persistence、allowed_domains/prohibited_domains、sensitive_data 避免把密码送入 LLM；当前安全指导建议遇到登录墙先停下并确认；若浏览器已有可用 SSO，可按用户任务继续。涉及输入密码、MFA、consent 或有歧义的账号选择时需要本人介入。StudyPlan 应根据具体任务授权和 browser auth 能力判断：缺少授权、需要本人介入或副作用不清楚时停止；授权范围明确且工具能安全完成认证、动作影响经过预检后，才安排执行。 | Playwright context auth state **DEEPEN**；Hello Extra11 对 browser session 的提及只是曝光。存储文件等同凭据，必须避免入库/提交；不把浏览器已登录视作对特定动作授权。 | 只在本机 fake login 保存一份临时 storage state，重建 context 检查登录态，再创建空 context 检查隔离；测试 allowlist 拒绝非本地域；清理凭据。 | 能证明 profile/session 作用域和数据留存；敏感状态不进入模型提示或截图日志。缺少任务授权、需要本人完成 MFA/consent、账号选择有歧义、工具无法安全认证或副作用未知时停止并请求人处理。若具体任务明确授权了发布等已知副作用，需另设目标确认、最小权限、执行前预检和结果核验，不能由默认训练实验触发。 |
| 6. Task success Evaluation 与鲁棒性 | **Why now**：browser agent 会说“已完成”但页面未必改变；需独立 oracle 后才能比较模型/提示/观察策略。**前置**：阶段4有轨迹导出，阶段5有安全边界。 | Playwright Assertions/Trace Viewer 给确定性基线；browser-use AgentHistoryList 里可看 action model outputs、final_result、done/success/error 等字段。Hello-Agents ch12 可作整体 Agent Eval 暴露；浏览器专用指标由本地任务集定义，不把单一排行榜分数当产品质量。 | Agent 一般回答质量 **COMPARE**；Browser 专项增加 page state、URL、正确 tab、DOM expected state、唯一 fake backend side effect、禁止域/越权 action、任务时间/步数/调用成本 **DEEPEN**。LLM-as-judge 仅辅助。 | 8–12 个合成任务含静态提取、延迟 SPA、表单验证、tab、新窗口、fake auth、429、错状态、重复提交、域名拒绝。每个任务留成功条件与禁止动作；随机改变按钮 label/布局/延迟作 hidden variants。 | 评分 oracle 读取页面/本地假后端而不是 agent 自述；报告任务成功率、任务失败类、误动作/越权、重试次数、耗时和模型费用；切出 held-out variations 防过拟合。 |
| 7. Browser-use 源码项目学习 | **Why now**：能跑本地 demo、读轨迹、解释工具与状态隔离；带具体问题去看当前项目才有产出。**前置**：Python async 基础、Playwright control basics、对 Agent loop 熟悉。 | 用仓库当时目录图确定切片：Python agent loop/step、BrowserSession/state & observation、controller/actions、history/events/hooks、storage state/domain policy、testing/examples。小项目先看地图；大项目只选 3–8 切片，按目标逐个读对应当前代码与测试。 | 和 Hello ch7 tool/harness **COMPARE**；和 Playwright locator/wait **DEEPEN**；不只读 root README，不固定源码路径/API。 | 对一个已完成的本地 demo 反向追一条 action→browser state change→history/error 的调用链；加一项单测或设计可复现实验（修改工作仅由用户/Coding Agent另行授权）。 | 能给当前版本结构地图、切片证据和一条可验证迁移；能区分源码事实、工程解释与推断。 |

## 小实践：可复现但本轮未运行

本轮**没有搭建或执行**下面的实验。StudyPlan 生成计划时可把它作为本地练习规格；仅使用本机虚构页面/假接口，不用真实账户、第三方登录、真实购买、预约或发布动作。

### 本地假网站与用例

建立一页虚构的 Team Research Board，包含无外部依赖的假登录页、搜索框、延迟渲染结果、只在某 tab 显示的详情、可编辑草稿、假提交按钮。提交请求只能写内存/临时本地文件中的 event counter，不能连到真实服务；每个假请求包含 task ID 与 idempotency key。测试可以故障注入：响应 429 一次、页面延迟、DOM 元素遮挡、某结果不存在、点击后响应丢失、链接目标不在 allowlist。

1. **确定性 Playwright baseline**：通过 role/label 定位；填表、选择、勾选；提交 fake endpoint；断言摘要/目标 URL/计数。展示 web-first expect 的等待。
2. **Dynamic wait**：触发异步结果后等目标状态、URL 或结果数量；对比盲目固定 sleep 的脆弱性。保留 trace 诊断。
3. **页面/视觉对照**：同一个具名控件可从 role/name 找到；另一个 canvas-like fake tile 只在 screenshot/layout 下能定位。比较 DOM/AX 与截图能提供哪些证据，避免让 screenshot 作常态。
4. **Browser context/auth**：fake login 后保存临时 storage state，重载 context 验证可恢复；空 context 应匿名；确保隔离。文件写到临时目录并删除，不进入 Git。
5. **browser-use agent**：只做本地 read-only 数据提取，设置域名 allowlist、最大 steps 和 timeout；对每步记录 observed state、action、action result、postcondition；目标网站不可达时应结束并报告。
6. **错误与重试**：在只读任务中允许可控的瞬时错误重试；对假提交引入“后端计数增长但响应丢失”，agent 必须先检查假后端 state/页面回执，不可盲目再次提交；用幂等键证明无重复记录。
7. **评估**：12 条任务，至少 4 条 held-out variation；对 deterministic Playwright 与 browser-use agent 报告任务完成、禁止动作、wrong-domain、步骤数、错误/重试、延迟与调用费用。判定使用 DOM/假后端，不采用模型自报成功作为唯一事实。

**解释边界**：本地小页只能检验小测试集中的脚本/模型行为，不能推断真实站点成功率、验证码处理能力、商业浏览器/模型质量、生产安全性或跨域鲁棒性。对外部模型调用应记录供应商/版本和实际用量；本轮没有估算任何价格，也没有声称免费额度。Playwright 自动等待的是动作可执行状态，不是业务事务成功；LLM Judge 不能替代确定性 oracle。

## 默认贯穿项目候选示例：研究与行动助手

| 版本 | 为什么自然出现 | 安全增量 / Exit |
|---|---|---|
| V0（RAG 后） | 需要阅读公开资料并带引用汇总，先从用户提供的 HTML/本地页面开始。 | 只做只读抽取；来源 URL、抓取时间、引用片段与错误明确记录。 |
| V1 | 需要访问一个自建的本地研究板，浏览器检查页面动态呈现和站点内容。 | Playwright 测试页面语义、动态加载、来源引用和页面无结果。 |
| V2 | 希望 Agent 自主发现要点击的搜索结果与详情页。 | browser-use 仅受 allowlist 限定，只读浏览；每个动作验证后再继续，任务结果由 URL/DOM/引用 oracle 检查。 |
| V3（按需） | 研究资料草稿需用户编辑/批准后导出。 | 本阶段默认只做本地假导出或下载临时文件，并留下暂停/审批记录。若实际产品目标后来要求外部发布、发信或购买，应先有明确用户授权、受支持的认证路径、影响预检和单独的审批/验收，再加入项目。 |
| V4（按需） | 页面状态复杂、跨多个 tab，需独立隔离 session。 | 只用本地 fake login/session；storage state 受控并可清理；跨 session 测试不会共享数据。 |

保持项目边界为只读研究和用户审批后的本地整理。不要为了“browser agent 能力”塞入机票预订、支付、账号注册、批量注册、社交发帖、验证码处理、反爬或隐身代理需求。

## 真实项目卡：browser-use

| 字段 | 内容 |
|---|---|
| repo_url | https://github.com/browser-use/browser-use |
| why_now | 已用 Playwright 完成确定性浏览器任务、理解定位/等待/验证；现在研究模型控制循环如何增量获取观测和执行动作。 |
| prerequisites | Python async、browser context/page、locator、navigation wait、trace、Agent loop/Tool result、页面任务成功 oracle。 |
| known_knowledge | Hello-Agents ch4 ReAct / ch6-7 工具与框架；Extra11 DOM/AX/vision 概念；Playwright locators/actionability/auth/eval。 |
| study_mode | 若本机无 repo，由 Coding Agent clone 当前官方仓库；先看当前目录和 Python package/skills/examples/tests 分布，提出 3–8 个切片，一次学一个。 |
| learning_focus | 按目标从 agent loop, observation/state, browser session, controller/actions, history/events, wait/navigation, domain/auth policy, tests/examples 中动态选切片。 |
| desired_depth | 追一条从 task → observation → model action → browser change → history/postcondition 的端到端轨迹；再读对应失败测试。 |
| important_questions | Observation 是 DOM/AX/截图哪种？页面如何被筛选压缩？如何约束域名与动作？工具错误与 LLM 错误如何分开？重试怎么限制？auth state 如何持久化与清理？成功如何独立判定？ |
| avoid_scope | 不连接用户真实 Chrome/Profile；不跑 root README 的真实预约/购买/CAPTCHA 示例；不研究隐身、代理或绕过保护；不直接接入 Cloud 服务。 |
| expected_outputs | 当前 repo 架构地图；一个 action 生命周期切片；对应测试说明；事实/解释/推断分开；一个本地 fake-site 验证方案。 |
| migration_candidates | 只提 1–2 项可迁移设计，如每步观察/验证钩子、域名 allowlist 或 trace 记录，并明确不是自动采纳。 |

外部 Coding Agent 提示模板：

    请研究当前官方仓库：https://github.com/browser-use/browser-use
    目标是理解 browser-use 如何对本地假网站执行“只读研究和来源抽取”。
    若本机没有仓库，请 clone 当前官方默认分支，检查状态、贡献说明与当前目录。不要引用固定源码路径或旧 commit；不要使用我的真实 Chrome Profile、账户或任何网站登录。
    先提供小项目整体地图；大项目只给 3–8 个与 agent loop、browser state/observation、action/result、safety/eval 相关的切片候选。等待我选择后一次读一个切片。
    每条结论标“事实 / 解释 / 推断”，用当前源码和测试支持；说明输入、观测、动作、页面状态改变、错误/恢复/验证。不要打开账户、绕验证码、反爬或发送外部请求。
    最后只提出 1–2 项迁移到我选定的 Continuous Outcome Carrier（有用户项目优先）的候选设计、适用条件和可复现实验。

## 资源与研究记录

教程/项目的完整目录字段、原始来源链接、证据摘要和 review_depth 见 [RESOURCE_CATALOG_NORMALIZED_DRAFT.json](RESOURCE_CATALOG_NORMALIZED_DRAFT.json)；实际检查范围、版本风险和未覆盖限制见 [RESEARCH_LOG.md](RESEARCH_LOG.md)。所有本地实验均为**建议设计，未运行**。
