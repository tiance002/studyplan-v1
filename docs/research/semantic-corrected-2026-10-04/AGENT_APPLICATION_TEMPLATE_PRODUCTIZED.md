# Agent应用开发：统一基础主线与可选强化编排

> 产品语义：方向描述目标能力，不绑定职业、单个项目、单个框架或单个 Recipe。章节与阶段是可裁剪的默认教学骨架；按目标和起点选取，并尊重实际前置。
>
> Continuous Outcome Carrier 优先使用用户合适项目；范围过大时裁成可维护纵切面。没有项目才推荐 Default Starter Project。能力暂不适合迁入项目时，先做独立 Micro Exercise，再按需要迁回；允许重构/替换实现，保留问题、测试、数据、接口、设计决策与验证证据。下面项目名称及增量列均为默认候选示例，不要求把每项能力装进同一代码仓库。
>
> 项目案例都是可替换候选，审读深度以标准目录为准。阶段验收由用户提交并确认的证据支持，不自动判定 mastery、不自动打分。完整规则见 [PLANNING_SEMANTICS_STANDARD.md](PLANNING_SEMANTICS_STANDARD.md)。

Default Starter Project / 默认贯穿项目候选是“研究与行动助手”，仅在用户没有合适项目时推荐。下面用它示范能力增量：读取用户授权的资料，回答带来源的问题；需要动作时生成计划，经策略或必要审批后在练习环境执行，并留下可复核证据。先资料问答，再受控行动，不从第一阶段就接生产账号、任意shell和多agent。它可自然覆盖RAG、上下文、workflow、browser、eval；Coding是可选工作区adapter，Agentic RL另设训练分支，不把所有专项硬塞进产品。

本轮不安排日期，不修改StudyPlan代码，不发布Seed。免费教程优先；API与云计算属于实践可能费用，阅读免费不意味着实践零成本。阶段实践为本轮设计，尚未执行。参考资源审读范围以RESEARCH_LOG与catalog为准。

## 路径

先诊断最小前置→Hello-Agents连续基础→Eval-Lite贯穿→记忆与简单RAG→上下文与协议按需→一个最小真实成果→选择专项→系统评价与迁移。应用者不以训练数学为前置；做RL者先具备轨迹、reward与held-out评价，才进入参数训练。

## 最小前置诊断

用一个独立脚本：读JSON文件，将输入交给函数，返回字典，错误输入捕获异常，保存输出，正常/错误各一断言。能完成就跳过Python补课；不会只补函数、dict/list、JSON、异常、文件和测试对应小节。Hello-Agents默认有Python与LLM API基础，因此不能把“环境配置完成”当成前置完成。API概念：request、response、messages、tool schema、环境变量；离线固定响应可先理解循环，不要求先调用付费模型。

## 基础章节的教学编排

主教材：[Hello-Agents](https://github.com/datawhalechina/hello-agents)，在线阅读由仓库README提供。[LCC](https://github.com/shareAI-lab/learn-claude-code)作为少量COMPARE/DEEPEN材料；不用把两门教程各自完整重跑。

| 阶段 / why now | 必要前置 | primary chapters / supplement | exposure relation | 小实践 | 持续项目增量 | exit criteria |
|---|---|---|---|---|---|---|
| A0 先知道程序在替模型做什么 | 最小Python诊断 | Hello ch1概念§1.1/1.2/1.4主读，§1.3长案例快读；ch2历史概览选读；ch3 §3.2.1–3.2.4与§3.3.2应用基础主读，底层/本地训练选读 | NEW；已会API者REVIEW | 手工给固定模型响应接一个查资料工具，区分模型决定与程序执行 | 项目问题、输入输出、禁止动作清单 | 能解释“模型返回命令≠命令已执行”；历史名词不要求全背 |
| A1 最小Agent loop | A0、循环/JSON/异常 | ch4 ReAct→Plan-and-Solve→Reflection，保持作者概念到实现链；LCC s01/02只COMPARE | NEW + COMPARE | 一个两步资料查询；工具名错、参数错、循环不停三反例 | 可查本地合成资料、记录轨迹与轮数上限 | 工具选择/参数/最终结果可验证；不用所有范式一起上线 |
| A2 组件化与受控行动 | A1；类不会才补最小接口 | ch7 Agent/LLM/Tool相关连续段；LCC s03权限/s04 hooks必要DEEPEN | REVIEW loop；NEW职责分离 | 用同一工具替换固定响应与API adapter；拒绝写入练习外目录 | 工具注册、统一错误、超时、审计与行动策略 | 能解释Tool/registry/LLM各职责；审批拒绝不会仍执行 |
| A3 简单知识问答 | A2；来源元数据 | ch8 Memory→RAG→文档问答助手；具体语料索引使用All-in-RAG ch1四步 | REVIEW RAG定义；DEEPEN pipeline | 五份合成短文，手工标相关文档；找不到答案时返回不足证据 | 资料导入、基础dense检索、来源ID | 检索结果可查看；答案带对应证据，能区别Memory和知识库 |
| A4 长会话和上下文预算 | A3；token与文件 | ch9 9.1/9.2→9.3 ContextBuilder→9.4 NoteTool→9.5 TerminalTool；LCC s08/09COMPARE | DEEPEN | 大结果/旧事实/临时限制：哪些召回，哪些裁剪，怎样重读 | 研究笔记、选择上下文、引用不可被摘要伪造 | 保存/召回/截断/摘要有独立证据；字符预算不是token精确值 |
| A5 框架只在复杂度出现时引入 | A1–A4中最小任务已成功；需要分支/恢复 | ch6目标相关框架实例主读，其它框架快读；Workflow专项LangGraph连续教程 | ch4/7 REVIEW；框架COMPARE；持久性DEEPEN | 研究→证据检查→人工审批→行动的分支，注入失败后恢复 | 图状态、checkpoint、interrupt、幂等行动 | 能说为何图有必要；简单RAG已会再引入，不以“学过框架”替代恢复演练 |
| A6 接外部能力 | A2/A5；远程时HTTP/异步 | ch10 10.1协议角色→10.2 MCP→10.5自建server按目标；A2A/ANP选读；LCC s14比较 | Tool REVIEW；transport NEW；mock COMPARE | 列工具、调只读计算/文档工具，未知工具/坏参数/断连 | 可选MCP adapter，宿主仍校验权限 | 解释server/client/transport与LLM工具调用差别；没有需求不学三个协议全部实现 |
| A7 系统评价 | A1起Eval-Lite已贯穿；有任务集和失败轨迹 | ch12 12.1→12.2工具调用→12.3任务成功→12.4judge；配合Evaluation专项 | Lite REVIEW；held-out/专项 DEEPEN | 将10条正常/失败任务分开发与held-out，比较基线及一次改动 | 回归报告、耗时/token、失败分类 | 分母与未跑项清楚；judge不是唯一证据；基准成绩不等于产品质量 |
| A8 可控真实项目 | A3/A4/A7，选一个专项门槛通过 | 小项目先整体；Pi/RAGFlow/WeKnora/browser-use等按PROJECT卡 | DEEPEN + COMPARE | 当前源码一条正常与失败链，复述，再迁移1–2项 | 目标相关能力，不复制全系统 | 有调用地图/边界/迁移验证；不能只展示clone或部署 |

## Hello-Agents 1–12的保留/缩短决策

ch1概念主读、长案例快读；ch2历史概览选读（不作为实现门槛）；ch3主读应用相关、模型训练数学选读；ch4主读；ch5非低代码目标快读，目标就是Dify等平台时转为Primary；ch6目标框架主读，其它COMPARE快读；ch7主读组件职责和选定实现；ch8主读；ch9主读；ch10 MCP相关主读、A2A/ANP目标深化；ch11应用者读轨迹/reward/训练概览，真正训练者转RL专项；ch12系统评估主读，并把Eval-Lite提前到ch4实践开始。

这属于教学编排判断，不声称每个选定章节都已完整深审。逐章证据、课程自身教授与遗漏详见DEEP_REVIEW。

## 开放组合的专项入口（首批，非闭集）

| 目标 | 入口证据 | Recipe/能力路径 | 可替换项目案例 |
|---|---|---|---|
| Knowledge / RAG Agent | 简单RAG+bad-case日志 | AGENT_SPECIALIZATION_RAG | RAGFlow/WeKnora是可替换已审核候选；也可用用户项目。模型路由仅按用户成本/质量目标选修，检索router不等于模型router |
| 软件任务自动化 | 受控文件工具+测试+diff | AGENT_SPECIALIZATION_CODING | Pi先局部工程；隔离/服务化再OpenHands |
| 可恢复业务自动化 | 状态/副作用/分支有需求 | AGENT_SPECIALIZATION_WORKFLOW | LangGraph；多agent目标需要再AgentScope |
| 网页研究/操作 | 本地表单固定脚本可验证 | AGENT_SPECIALIZATION_BROWSER | Playwright先基础，再browser-use观测/行动 |
| 提升可靠性 | 至少一种可执行任务 | AGENT_EVALUATION_PATH | 框架/基准只服务测量问题 |
| 模型参数训练 | 有环境/轨迹/可靠reward/held-out | AGENTIC_RL_PATH | 先小实验，GPU训练另作可选 |

首批 Recipe 是开放的冷启动骨架，可选择/组合0..N个。一个阶段优先强化一个主要能力问题以降低认知负荷；用户总体目标可同时组合多个专项并按前置顺序学习。这是节奏建议，不是产品归属或路由限制。评估与失败诊断贯穿，每增加工具/检索/恢复能力就增加对应grader。只要应用开发目标不需要训练，RL介绍后可停止，不阻塞后续工程评价。

## 每次教学单元

问题：当前项目出现什么具体困难？
概念：用通俗语言解释本次一个主题。
真实例子：材料当前代码的输入、输出、分支、调用与失败路径。
小实践：给合成输入、可观察结果和失败反例，不一次公布全部答案。
项目增量：只升级一个契约，写明验证方式。
复述：让用户解释正常/失败各一条；纠正后保存通过证据。
下一阶段：按exit而非日期或阅读时长。

## 核心理解证据与 Optional Career Overlay：面试 / 项目展示

能讲一条请求从输入校验→上下文→工具/检索→生成→证据校验→状态/结果的链；能解释至少三个真实失败与诊断；能比较纯dense与hybrid、普通loop与workflow、本地执行与隔离执行；能把设计愿望、当前实现和实际测试分开。没有验证的数据不得编成“提升百分比”。

## Python诊断失败时的精确补课入口

免费中文官方[Python Tutorial](https://docs.python.org/zh-cn/3/tutorial/)用于即时补课，不要求全书先修。已核查下列正文与示例，未运行。

| 诊断失败 | 阅读 | 学后立即做 | 暂跳过 |
|---|---|---|---|
| 函数/返回不清楚 | [控制流4.1/4.2/4.8](https://docs.python.org/zh-cn/3/tutorial/controlflow.html) | 写查询函数返回结果，循环调用两次 | match高级模式、复杂参数形式 |
| 不会dict/list | [数据结构5.1/5.5](https://docs.python.org/zh-cn/3/tutorial/datastructures.html) | 使用工具名→函数/资料ID→文本映射 | 矩阵嵌套推导式 |
| 文件与JSON不会 | [输入输出7.2/7.2.2](https://docs.python.org/zh-cn/3/tutorial/inputoutput.html) | with打开合成JSON并保存结果，检查重读 | 格式化输出全部历史方法 |
| 错误只会看红字 | [异常8.2/8.3](https://docs.python.org/zh-cn/3/tutorial/errors.html) | 无效数字/缺文件各一例，返回可辨认错误 | ExceptionGroup等高级内容 |

最小测试先用两个assert验证自己的函数契约，再在持续项目有多项行为时引入测试框架；不把测试工具安装成功当作行为通过。官方教程默认会基本编程，因此真正零基础者需教师逐行带做上述诊断。版本按用户已有兼容环境选择，核心小节不强制升级解释器。


## Common Core 与深度边界

A0–A8保留原章节级编排，但不是每人同深度全走完：A0应用心智模型；A1loop与Eval-Lite；A2结构化工具、权限和错误边界；A3简单知识检索的位置；A4基础上下文；A5框架/workflow位置；A6协议/MCP位置；A7系统评估入口。A5恢复、A6MCP实现、A8源码切片按目标加深或跳过。RAG流水线优化、Coding shell/任务工程、Workflow持久运行、Browser观测行动不因位于Common Core附近就自动全展开。已学内容诊断跳过，教材会教的前置留在主线。

示例（planner输出语义，不是新增数据库字段）：

```yaml
primary_focus: rag
supporting_capabilities: [workflow, browser]
reviewed_recipe_refs: [rag, workflow, browser]
continuous_outcome_carrier: user_project
```

旅行规划可组合Workflow+Browser+RAG+Tool/API；研究目标可组合RAG+Browser+Evaluation；企业知识目标可组合RAG+Workflow+Auth/permission+Evaluation。Tool/API和Auth是能力，不要求先有同名Recipe。未命中现成Recipe时从capability/prerequisite/resource pool组合；公共池资料不足则明确needs_research_or_review，不编造。

核心理解仍要求能解释调用链、失败与设计取舍。只有career_goal=interview或project_showcase时，才增加面试问答、项目叙述或展示打磨；不把这些作为普通学习的必修出口。
