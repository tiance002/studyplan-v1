# Coding Agent：从受控工具循环到可验证的软件任务

> 产品语义：方向描述目标能力，不绑定职业、单个项目、单个框架或单个 Recipe。章节与阶段是可裁剪的默认教学骨架；按目标和起点选取，并尊重实际前置。
>
> Continuous Outcome Carrier 优先使用用户合适项目；范围过大时裁成可维护纵切面。没有项目才推荐 Default Starter Project。能力暂不适合迁入项目时，先做独立 Micro Exercise，再按需要迁回；允许重构/替换实现，保留问题、测试、数据、接口、设计决策与验证证据。下面项目名称及增量列均为默认候选示例，不要求把每项能力装进同一代码仓库。
>
> 项目案例都是可替换候选，审读深度以标准目录为准。阶段验收由用户提交并确认的证据支持，不自动判定 mastery、不自动打分。完整规则见 [PLANNING_SEMANTICS_STANDARD.md](PLANNING_SEMANTICS_STANDARD.md)。

> 类型：Reviewed Specialization Recipe（首批已审核专项参考骨架）；binding=optional，可组合、裁剪、替换，未命中该 Recipe 不阻止规划。Evaluation 横切各阶段，参数训练按目标单独选择。

研究日期：2026-10-03。所有教程正文免费；真实模型推理可能产生 API 费用。本文是教学编排，不是已完成实现或运行验收。课程目录链接用于定位教材；真实项目卡不锁源码路径或 commit。

## 选择与阅读边界

Primary： [learn-claude-code](https://github.com/shareAI-lab/learn-claude-code)，采用根目录新版 s01–s17。已检查完整新版目录、中文课程正文及 s02/s04/s08 等选定代码；未实际调用模型运行。旧 `docs/zh` 是过渡线，不能把旧 s03 Todo 与新 s03 Permission 混为一谈。课程各章有独立机制示例，常回到 s04 kernel，不是每章都累加全部前章功能；s15 才展示集成。

Comparison / 工程深化：[Pi](https://github.com/earendil-works/pi)。已读 SDK、Sessions、Security、Containerization 正文、Extensions 前半核心契约及 SDK 最小/工具选择示例。它不是 Python 零基础课程：第一次读 TypeScript 前才补函数类型、Promise/await、模块 import 和事件回调。

Reference / 大系统专项：[OpenHands SDK](https://docs.openhands.dev/sdk/getting-started)，已核查安装示例与 Security、Persistence、Docker Sandbox 的目录；后几篇需要学习时继续正文核查。不把“文档页成功打开”当成深入读完。

ZCode 暂不进入必修链。检索发现至少 Softorize/zcode（Zig）和 zerx-lab/zcode（oh-my-pi 下游）等同名项目；附件没有唯一 URL。不能把其中任意一个的架构安到用户所说 ZCode 上。身份澄清前仅列候选，课程不会因此阻塞，Pi 足以承担当前工程比较。

## 基础知识的语义变化

| 已有概念 | 基础已会 | Coding 场景新增 | 关系与验证 |
|---|---|---|---|
| Tool | schema、分发、结果回填 | 文件路径、编码、读改写冲突、shell 退出码、截断 | DEEPEN：同一工具调用成功不代表软件任务完成 |
| Permission | 允许/拒绝/审批 | shell 间接调用、网络、凭证、进程、挂载 | DEEPEN：字符串拒绝表不是沙箱 |
| Context | 选择与压缩 | 代码结构探索、最新 diff、日志预算、变更后重读 | COMPARE：预索引与按需搜索；不强制 Repo RAG |
| Memory | 保存/召回 | 项目惯例与过期实现分开、用户临时命令不持久化 | DEEPEN：修改源码后需刷新事实 |
| Task | 用户目标与规划 | TODO、依赖图、owner、跨进程恢复 | NEW：能恢复任务状态，不等于能恢复运行进程 |
| Subagent | 委派 | 独立上下文、共享工作区、worktree 分工、合并审查 | DEEPEN：上下文隔离不等于文件隔离 |
| Evaluation | 一组问答判分 | 补丁正确、回归、隐藏测试、禁止改评分器 | NEW：必须验证真实软件行为 |

## 章节级教学链

下表的“实践”是本轮设计，未在本轮运行。默认贯穿项目候选为“研究与行动助手”；优先使用用户项目，Coding也可直接服务用户的软件项目，Coding 是可选工作区适配器，只处理独立练习仓库，不强迫助手成为通用 IDE。

| 阶段 / why now | 必要前置 | 主读章节、补充 | 与基础关系 | 小实践 | 持续项目增量 | 出口 |
|---|---|---|---|---|---|---|
| C1 让模型看到行动结果 | 函数/字典/JSON/循环；不会才补 | [s01 Agent Loop](https://github.com/shareAI-lab/learn-claude-code/tree/main/s01_agent_loop)；s02 Tool Use | Hello ch4 REVIEW 范式，COMPARE 原生 tool_use 与文本 ReAct | 使用固定响应，手工追踪两次工具调用及停止；未知工具、漏参数各一例 | 文件只读查询工具；统一错误结果 | 能画消息输入输出，解释 tool_use_id 配对；不会把模型输出当执行结果 |
| C2 文件与 shell 边界 | Path、异常；exit code在首次运行命令前补 | s02 文件工具；s03 Permission；s04 Hooks | Hello ch7 工具 DEEPEN；ch9 Terminal COMPARE | 临时目录读改写；制造 old_text 不存在、重复 old_text、越界路径；列出审批/拒绝矩阵 | 写入前审批、目标目录固定、审计记录 | 能说清限制覆盖哪个工具；指出 shell=True 和字串拒绝表的局限 |
| C3 计划可见而非口头承诺 | 状态枚举、列表 | s05 TodoWrite；s10只先看 Todo vs Task 比较 | ch4 Plan REVIEW；TODO持久化 NEW | 三步微重构，插入一次测试失败，观察计划是否更新 | 输出带步骤状态与验证证据的任务报告 | completed 必须有产物和验证证据；知道s05进程内清单不能跨重启恢复 |
| C4 控制大型代码上下文 | C1–3；文件搜索、token概念 | s06 Subagent；s07 Skill Loading；s08 Context Compact | ch9选择 REVIEW；四步管线DEEPEN | 给固定超长日志：转存→裁剪→旧结果引用→摘要；摘要保留用户约束；检查工具配对 | 大日志按需读取、只加载相关规范 | 字符预算不冒充token精算；恢复路径可读取；子agent共享文件系统须说明 |
| C5 项目记忆与任务恢复 | JSON读写、稳定ID | s09 Memory；s10 Task System | ch8存取 REVIEW；项目过期/依赖校验 DEEPEN | 保存永久偏好与“本轮不写文件”；重启后前者可召回、后者不保留；建立A→B→C依赖 | 存项目惯例、任务JSON、来源和更新时间 | 区分Memory、transcript、TODO、task store；循环依赖拒绝；不能拿旧事实覆盖新源码 |
| C6 长运行与取消 | 线程/进程概念只在此补；timeout | s11 Background；s12 Cron选读；s15恢复段 | 普通Task DEEPEN | 固定慢命令：返回占位→完成通知；失败退出码；取消与重启 | 慢分析作业状态、取消请求、结果事件 | 说明占位不是成功；s11结果只后续轮次收集；daemon线程不能保证重启恢复 |
| C7 持续协作（目标需要才学） | C5/6，git分支与worktree最小知识 | s13 Agent Teams；s15团队/任务集成 | s06 COMPARE 一次性子任务与持久队友 | 两个只读worker；随后在练习worktree独立改不同文件；注入旧审批和重复认领 | 分工仅用于可独立资料/代码切片 | owner认领原子；审批关联task/version；worktree不是沙箱；能解释合并冲突由谁处理 |
| C8 外部能力与集成 | 工具注册、错误处理 | s14 MCP Tools；s15 Integrated Harness | Hello ch10 MCP COMPARE | docs mock动态加入；两服务同名工具；未知工具和参数错误；真实MCP另用官方Quickstart | 可选文档/测试能力adapter | s14是进程内模拟服务，未实现真实transport；宿主策略决定权限 |
| C9 完成判断与恢复 | 已有测试和状态证据 | s16 Workflow Runtime；s17 Goal Loop | ch12评估 DEEPEN；workflow另见专项 | 固定runner demo和resume；改输入后缓存失效；Goal收到“我完成了”但没有退出码 | 可信产物日志、有限续跑、失败/无法完成出口 | 判断器只能看到记录、不能自行验证；workflow完成≠用户目标完成 |
| C10 真实编辑/测试边界 | C1–9必要切片；pytest最小测试 | Pi SDK→tools→sessions→extensions；生产工程参考OpenHands | Python harness与TS session COMPARE | 修复独立练习仓库一个小bug；diff审查、回归、隐藏用例，取消后检查进程 | coding adapter具备proposal→patch→test→review流程 | 不改测试来“通过”；不把cwd/审批误认为完整隔离 |

## 关键章节阅读顺序与跳过范围

s01–s05保持小型机制连续性；s06–s10按上下文→技能→压缩→记忆→任务的顺序理解。s11慢操作后才加入s12定时。s13团队可选，s14协议可独立读，s15用于整合核查。s16、s17分别解决编排与目标出口，不要求所有用户实现17章全功能。

已掌握基础的用户：s01–s02只做固定轨迹回顾，重点直接进入s03/04及C4。不会编程的用户禁止跳过JSON/函数/异常后直接运行shell agent。不学：完整TUI渲染、全provider适配、所有MCP server、cron的全部表达式、所有团队模式。只有目标涉及长期无人值守任务才加cron；只有任务独立且串行成为瓶颈才加teams。

## 真实代码核查发现

- s02 `run_edit` 对old_text只替换第一次。未找到返回错误，但多个相同片段可能改错位置。因此练习要求先计数并检查diff，进阶再比较哈希锚定/结构化编辑；不能声称教程已经教授强健的补丁冲突算法。
- s02文件工具调用safe_path，shell仍能触及宿主有权访问的资源。s03明确只是教学拒绝表。s04代码中有破坏命令正则与路径审批，中文README权限片段比实际代码更简化；学习以当前代码核验，不能照抄README宣称安全。
- s08优先转存、归档与确定性缩减，最后才摘要；字符估计与一次too-long补救是教学边界。可恢复日志不等于所有副作用可重放。
- s14 docs/deploy是mock server。应把Hello ch10真实协议实现与之COMPARE；不能把动态tool pool示例验收成MCP网络互通。
- s15中文正文工具总数与末尾对照表存在26/25不一致。资源卡不固化这个数字；读者应根据当前工具注册表确认。
- s16 resume采用调用语义缓存，并不自动为任意外部写操作提供exactly-once。练习应分清缓存结果与副作用幂等键。
- s17没有工具的独立判断器只读对话；若证据没进日志就无法可靠判断。真实测试仍由测试工具完成。

## Pi 项目阶段

入口门槛：能独立解释一个issue的“发现文件→读当前代码→提出补丁→运行测试→审查diff→汇报证据”，完成至少一个正常和一个失败轨迹。首次TypeScript阅读只补Promise/await、事件注册、类型/interface，避免先学一整门TS。

学习顺序：SDK Session lifecycle / storage → Prompting / abort → Subscribing to events → tools example → Sessions and Context → Extensions 的lifecycle/events/tools → Security / Containerization。SDK与CLI默认资源加载不同必须核对；关注agent_end与最终settled的差别、恢复session与直接改messages的差别。Extensions读取选择性正文，不要求TUI API全读。

输出：一张session与tool事件地图、一次取消轨迹、一个只读工具扩展、一个并发文件写入反例。迁移：1）取消信号贯穿工具；2）最终状态与中途run_end分开。不要直接迁移全部Pi代码。

## OpenHands 与 ZCode 的进入时机

OpenHands：Pi切片已学会、Docker最小知识具备，并且目标是隔离执行/服务化/多workspace时进入。先 Getting Started，然后 Security & Action Confirmation、Persistence、Docker Sandbox，各自查当前正文与示例。大型项目限3–5切片：工具事件、workspace、确认、会话恢复、成本追踪。不研究完整云控制台/全部infra。

ZCode：先给唯一repo_url，再核实是否目标所需。若是Zig项目，语言门槛与当前Python/TS教学成本不相称，可延后到运行时工程；若是Pi下游，先比较“上游已知能力与下游真实新增”，别重学一遍Pi。身份确认前不推荐安装。

## Coding Eval（接入统一Evaluation路线）

Eval-Lite从C1出现：工具选错/参数错/未知工具/轮数上限。C2加拒绝绕过与错误恢复；C4加压缩约束遗失；C6加超时/取消/重启；C9加误宣告成功；C10加补丁正确和回归。

数据切分以issue或功能族划分，训练/提示调参集不能复用held-out。确定性grader优先看退出码、输出契约和行为测试；LLM judge仅审解释质量/不完备行为，不代替测试。报告分母、失败分类、token、耗时、重试、未跑项。消融只改一个因素，如不用compact或不用subagent；必须保持模型、任务及预算一致。

最小练习集建议：文件搜索2题、受控编辑2题、bug修复3题、权限/取消/恢复各1题。此数量是教学建议，不代表统计可靠性。真实项目准入须能解释失败，而不仅展示一次成功。
