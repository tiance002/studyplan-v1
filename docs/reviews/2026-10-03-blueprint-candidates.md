三个候选可以用现有 DomainPack JSON 承载，但**目前只能作为内容候选，不能标为已审核正式 Blueprint**。最接近可用的是 Knowledge/RAG；Coding 和 Workflow 可以复用已有模型、工具、编排教材，但各自的代码修改安全、审批与副作用控制仍有教材证据缺口。

本次实际分支核对为 `feat/n1-resource-discovery`。仅做文件读取和 JSON 解析，没有修改文件、切换分支、提交、启动服务、操作数据库或联网。模型请求偏好记录为 `gpt-6.1-sol/high`；实际模型解析与 effort：`NOT OBSERVABLE`。

**1. 当前内容缺口及文件定位**

| 缺口 | 仓库证据与位置 | 对三个候选的影响 |
|---|---|---|
| 尚无三个独立的正式 Blueprint | `backend/app/infrastructure/content/` 只有 `agent-application-v1/v2/v3.json` 和 `python-engineering-v1.json`；[v3](D:/studyplan/backend/app/infrastructure/content/agent-application-v3.json:1) 仍是通用知识助手路线 | 不能把通用路线换三个标题就算完成，需要不同必修闭包和贯穿项目 |
| 必修依赖过宽 | [v3 的 `node.reliability`](D:/studyplan/backend/app/infrastructure/content/agent-application-v3.json:474) 同时依赖 LangGraph、RAG、MCP、Context | 原样复用会让 Coding、Workflow 也强制学习 RAG/MCP；应在新候选内容版本中收紧依赖，保留旧版本 |
| Python 章节顺序有明确问题 | [v3 Python 目录](D:/studyplan/backend/app/infrastructure/content/agent-application-v3.json:752) 将第 12 章 Virtual Environments 排在第 4 章 Control Flow 前 | 本地 `order_index` 合法不等于作者章节顺序正确；候选中分开安排，按第 4→7→8→12 章阅读 |
| Python 前置包不完整 | [python-engineering-v1.json](D:/studyplan/backend/app/infrastructure/content/python-engineering-v1.json:1) 没有 `knowledge_blueprints`，也没有显式学习指导；资料没有逐章节日期及审核说明 | 尚不足以覆盖三个方向所需的数据结构、JSON、路径边界、测试与状态记录 |
| 正式 Seed 没有预置学习关系与实践增量 | v3 的阶段没有 `learning_guidance`；[默认指导逻辑](D:/studyplan/backend/app/domain/planning/guidance.py:157) 明确回退为“模板未预置与先前教程的关系” | 需要把下面的关系、增量、验收写入已有字段 |
| 免费正文及来源版本证据不足 | v3 的 provenance 是“标题、主题适配、URL/index review”；v2/v3 lineage 明确没有新网页审核。[10月2日课程记录](D:/studyplan/docs/acceptance/test-account-curriculum-review-2026-10-02.md:1) 有页面审阅证据，但没有独立的免费正文审核记录 | 可复用历史记录，不能升级成“免费正文已审核”，也不能把 `source_version: 1` 当作官方版本号 |
| fixture 不是正式教材 | [Tool Calling fixture](D:/studyplan/docs/curriculum/tool-calling-vertical-fixture-2026-10-03.json:1) 是 `acceptance_only_not_published_seed`；源码为 `main`、`files: []`、`suggested` | Hello-Agents 的“已经见过”仅适用于该输入；源码切片继续可选待核对 |
| 新候选不自动成为运行时可选内容 | [现有目标路由](D:/studyplan/backend/app/infrastructure/domain_pack.py:37) 只返回 `agent.application` 或 `python.engineering` | 下面交付的是内容数据规格；主会话仍需核对选择与接入，不代表已经可生成 |

[10月4日交付要求](D:/studyplan/docs/implementation/STUDYPLAN_OCT6_FINAL_DELIVERY_GOAL_2026-10-03.md:736) 包括三个 Blueprint、Python 前置、免费正文审核记录和贯穿实践。下面分别提供这些内容的候选，资料不足处明确保留缺口。

**2. 共用 Python 前置与教材引用**

三个候选都面向“有基础编程认知、Agent 初学者”。仓库现有 Python Tutorial 不能直接宣称覆盖完全零编程基础教学。

建议共用以下前置内容；它们仍是普通 `stage_blueprints`、`knowledge_blueprints` 和 `practice_blueprints`。

| 前置阶段 | 学习目的及顺序 | 贯穿实践的起点 | 可检查验收 |
|---|---|---|---|
| P1 `stage.python_functions` | 控制流、函数、列表/字典与输入校验。Primary：现有第4章；解释器章节作 Reference。数据结构第5章仅有私人课程阅读安排，正式章节记录待补核 | 把输入转换为明确的成功结果或错误结果 | 正常、空输入、类型不符分别有固定预期；函数结果可断言 |
| P2 `stage.python_files`，依赖P1 | UTF-8 文件读写、异常、JSON记录与基础测试。Primary：现有第7→8章，保持顺序；JSON/测试教材覆盖待补核 | 读取本地样例，保存路径、正文和错误；输出可再读取的记录 | 正常、空文件、缺失文件可区分；JSON往返不丢关键字段；保存命令与结果 |
| P3 `stage.environment`，依赖P2 | 虚拟环境、解释器与依赖记录。Primary：现有第12章，单独安排 | 为前两阶段脚本建立可复现启动方式 | 新环境按README复现；记录解释器版本与依赖，不把环境差异混为业务失败 |

各方向另需：

- **Knowledge/RAG**：遍历文档、为文件和片段保留标识、列表/字典过滤与排序。无需先修数学、PyTorch或模型训练。
- **Coding**：路径处理、模块与导入、读取测试输出、基础版本差异认知。进入修改阶段前必须能解释目标文件、修改内容和测试结果；不要求任意 shell 执行。
- **Workflow**：显式状态、条件分支、JSON状态记录、异常分类、业务键去重。日期/CSV按所选工单数据需要补充；异步与并发不作默认前置。

下表使用教材简称，均指向仓库现有资源记录：

| 简称 | `source_ref` | `section_refs` |
|---|---|---|
| Models / Messages | `src_agent_langchain_v1` | `sec_agent_models_v1` / `sec_agent_messages_v1` |
| Tools / Structured | 同上 | `sec_agent_tools_v1` / `sec_agent_structured_v1` |
| Agents / Test | 同上 | `sec_agent_agents_v1` / `sec_agent_testing_v1` |
| Graph / Persistence | 同上 | `sec_agent_graph_v1` / `sec_agent_persistence_v1` |
| Retrieval / Memory | 同上 | `sec_agent_retrieval_v1` / `sec_agent_memory_v1` |
| Evaluation | `src_agent_evaluation_v1` | `sec_agent_evaluation_v1` |

这些记录目前的 `source_version` 都是 `1`。以下每阶段只指定一个 Primary，其他资料写为 Supplement 或 Comparison。尽量使用单章节 Primary，避免依靠拼接的 LangChain/LangGraph 本地目录冒充已核实的作者顺序。

表中的学习关系是**预置的阅读关系，不是掌握判定**：首次接触用 `unknown`；复用明确学过的机制时用 `deepen` 或 `review`。如果用户实际没有完成前阶段，应显示前置提示。

**候选 A：Knowledge / RAG Agent**

建议 `pack_key: "agent.knowledge_rag"`，新内容版本从 `1` 开始。

目标：构建一个小型本地知识问答 Agent，回答能追溯到真实文档片段；无依据、工具失败和上下文不足时有明确行为。贯穿项目：**三份无敏感样例文档的知识助手**。

阶段顺序：P1→P2→P3→K1→K2→K3→K4→K5→K6→K7。RAG机制不依赖 Workflow；本路线先学RAG，是目标优先级安排。

| 阶段与必需依赖 | 学习目的、前次关系 | Primary；其他资料 | 同一项目的实践增量与验收 |
|---|---|---|---|
| K1 `stage.model_api`；依赖环境 | 建立消息、请求/响应和依据边界。`unknown`：此前只有文件读取器，现在接入回答输入输出 | Models；Supplement：Messages | **基线**文档读取器→增加问答接口、答案/引用/无答案结构；保留读取行为。固定有答案与无答案问题；结构可校验，资料与指令分开。未调用模型时明确是样例验证 |
| K2 `stage.tools`；依赖K1 | 实现schema→请求→dispatch→result。`unknown`：本路线首次正式学工具；只有明确见过Tool概念时才采用fixture的`deepen` | Tools；Supplement：Structured | 增加`read_file`、`search_note`；保留普通问答。测试正常调用、未知工具、错误参数、工具抛错及越界路径；日志区分请求、执行和结果 |
| K3 `stage.agent_loop`；依赖K2 | 把工具接入有界循环，并建立Eval-Lite。`deepen node.tools`：从单次调用到多轮决策和停止 | Agents；Supplement：Test | 增加工具结果回传、动作上限、终止原因及10–20个固定案例。保留直接回答入口；每例保存trace、预期、实际结果与调用数，失败不伪装成成功 |
| K4 `stage.rag`；依赖K3，知识前置为模型/工具 | 学会索引、检索、回答分别检查。`deepen node.tools`：`search_note`从简单工具升级为片段检索 | Retrieval | 给每个片段绑定文档ID和位置；增加关键词检索或已有检索薄适配。保留按ID读取；保存相关片段标注，分别展示检索错误、依据错误和无答案。向量嵌入作为后续加深，不强制收费 |
| K5 `stage.langgraph`；依赖K3，实践接续K4 | 显式化检索→回答→失败的状态。`deepen node.agent_loop`：循环行为不变，新增状态与恢复位置 | Graph；Supplement：Persistence | 增加状态表、故障位置与有限恢复。保留K4检索及引用检查；注入读取超时、非法参数、动作上限，记录迁移原因，重复执行不重复新增结果 |
| K6 `stage.context`；依赖K5 | 区分原文、会话状态和摘要。`review`检查点、`deepen`上下文预算 | Memory；Supplement：Persistence。Comparison可复用Messages | 增加有限会话历史和摘要到原消息的引用。保留原文与来源；长会话包含用户更正，两个会话不串用。对比问题：裁剪和摘要分别遗漏了哪个约束？ |
| K7 `stage.capstone`；依赖K4、K5、K6和早期评价 | 用完整结果验收项目。`deepen node.eval_lite`：从格式/工具检查扩展到检索、引用、隔离与回归 | Test；Supplement：Evaluation | 合并已有案例为验收包，输出逐例结果、失败分类、启动说明和限制；保留此前trace。成功、无依据、工具失败、状态隔离都可检查，统计可复算 |

必修：Python、模型/消息、工具、有界循环/Eval-Lite、RAG、状态恢复、上下文、项目验收。

可选：MCP、真实Runtime源码切片、向量检索对比。**MCP不进入项目验收的必需闭包。**

**候选 B：Coding Agent**

建议 `pack_key: "agent.coding"`，新内容版本从 `1` 开始。

目标：围绕一个小型Python项目，读取相关文件、提出修改、展示差异，经明确确认后应用，并用受控测试检查。贯穿项目：**修复前置阶段文本统计CLI中的一个预设缺陷，再完成一个小功能**。

| 阶段与必需依赖 | 学习目的、前次关系 | Primary；其他资料 | 同一项目的实践增量与验收 |
|---|---|---|---|
| C1 `stage.model_api`；依赖环境及Python模块/测试基础 | 将问题描述、代码材料和修改建议分开。`unknown`：从CLI代码进入结构化分析 | Models；Supplement：Messages | 给CLI增加代码问题分析入口，输出目标文件、问题、建议与不确定项；保留CLI运行。用固定缺陷检查建议是否对应实际代码，缺材料时明确说明 |
| C2 `stage.tools`；依赖C1 | 只读代码工具的schema、路径范围与错误。`unknown`：首次工具实现 | Tools；Supplement：Structured | 增加`list_files`、`read_file`、`search_code`；保留普通分析。正常文件、缺失路径、越界路径、未知工具均有记录；尚不写文件 |
| C3 `stage.agent_loop`；依赖C2 | 完成观察→定位→修改提案的有界循环。`deepen node.tools` | Agents；Supplement：Test | 增加最大步数和“找到依据/需要补材料/失败”终态，准备固定缺陷集。保留只读边界；每项建议可定位到真实文件，未知内容不能伪造 |
| C4 `stage.coding_workspace`；依赖C3 | 将“建议修改”与“实际应用”分开。`deepen node.tools`：从读取能力扩展到受控修改 | Tools；Supplement：Structured。**文件修改安全教材待补核** | 增加目标文件白名单、差异预览、明确确认与基线检查。保留读工具；未确认零写入，基线变化拒绝旧提案，重复确认不重复应用，无关文件保持原样 |
| C5 `stage.langgraph`；依赖C3、C4 | 编排提案→确认→应用→测试→结束。`deepen node.agent_loop`：新增执行状态和失败分支 | Graph；Supplement：Persistence | 增加状态记录、固定测试入口与失败终态；保留C4确认边界。测试失败不报告成功，重启后能区分未应用/已应用/待核对；未知执行结果不盲目重跑 |
| C6 `stage.context`；依赖C5 | 保存需求、基线、已读文件和验证结果。`review`运行状态、`deepen`上下文组织 | Memory；Supplement：Messages | 增加任务摘要并保留原需求/差异/测试记录；用户更正能覆盖旧计划中的假设。对比问题：长代码上下文裁剪后，哪个验收条件容易丢失？ |
| C7 `stage.capstone`；依赖C4–C6和早期评价 | 检查实际环境结果。`deepen node.eval_lite`：从提案格式到代码和回归 | Test；Supplement：Evaluation | 完成一项缺陷修复与一项小功能，提交差异、确认记录、测试命令及原始输出。合法修改满足要求；越界、过期提案、测试失败、动作上限都有证据；原CLI回归通过 |

必修：Python文件/模块/测试、模型、只读代码工具、有界循环、修改边界、状态流程、上下文、验收。

RAG、MCP、RL均不默认必修。任意shell、自动安装依赖、自动运行外部仓库不进入本候选基础范围。

这一候选的**工具/循环/编排教材有仓库记录，完整Coding教材链尚未证实**，尤其不能把普通Tools页面标成已经覆盖文件修改安全与测试执行隔离。

**候选 C：Workflow / Automation Agent**

建议 `pack_key: "agent.workflow_automation"`，新内容版本从 `1` 开始。

目标：将输入解析、规则校验、动作提案、审批和结果记录组织成有限流程。贯穿项目：**本地工单分类→动作提案→人工批准→写入模拟动作记录**。基础阶段不发送真实邮件、不接真实业务账号。

| 阶段与必需依赖 | 学习目的、前次关系 | Primary；其他资料 | 同一项目的实践增量与验收 |
|---|---|---|---|
| W1 `stage.model_api`；依赖环境及Python状态/JSON基础 | 从工单文本生成结构化分类与理由。`unknown`：此前只有文件处理脚本 | Models；Supplement：Structured | 增加固定分类结果schema；保留原文。正常、缺字段、歧义输入有预期；歧义进入补充信息分支，不强行给动作 |
| W2 `stage.tools`；依赖W1 | 将规则查询和动作预览做成受控工具。`unknown`：首次工具实现 | Tools；Supplement：Messages | 增加`read_rule`、`preview_action`；保留分类。正常、未知规则、错误参数、工具异常可检查；预览阶段不产生动作记录 |
| W3 `stage.agent_loop`；依赖W2 | 用有界循环准备可检查提案与早期评价。`deepen node.tools` | Agents；Supplement：Test | 增加提案、需要补材料、失败、动作上限终态及固定工单集；保留零副作用预览。每个提案注明依据和计划动作，保存trace |
| W4 `stage.langgraph`；依赖W3 | 用确定性节点和路由组织流程。`deepen node.agent_loop`：分支由规则控制 | Graph；Supplement：Persistence。私人课程的Workflows and agents可作待转录Supplement | 增加分类→规则校验→待批准/拒绝/结束状态表；保留工具错误。歧义、规则不匹配和工具失败走明确分支，能从记录解释每次迁移 |
| W5 `stage.workflow_effects`；依赖W4 | 区分批准、执行、已知失败与未知结果。`deepen`状态恢复与工具边界 | Persistence；Supplement：Tools。**审批/幂等教材待补核** | 增加人工批准、业务键去重、模拟执行器及结果记录。未批准不执行；重复批准只产生一条动作；批准后输入变化使旧提案失效；未知结果暂停核对 |
| W6 `stage.context`；依赖W4，实践接续W5 | 保存多轮补充信息与规则版本。`review`已存状态、`deepen`上下文保留 | Memory；Supplement：Messages | 增加工单摘要、用户更正与原文引用；保留动作记录。两张工单不串用；历史说明绑定当时输入与规则，不能用新规则改写旧结果 |
| W7 `stage.capstone`；依赖W5、W6和早期评价 | 用流程状态与实际动作记录验收。`deepen node.eval_lite` | Test；Supplement：Evaluation | 输出固定案例、逐步trace与动作清单。覆盖成功、补材料、拒绝、工具失败、重复批准、重启和未知结果；结果可复算，恢复行为可复现 |

必修：Python状态/JSON、模型结构化输出、工具、有界循环、状态路由、批准与副作用边界、上下文、验收。

RAG仅在“必须查询知识库作决策”时加入；MCP仅在目标需要协议接入时加入。Persistence记录证明的是检查点教材存在，**不能据此声称审批和幂等教程已完整审核**。

**三个候选落成 JSON 时的具体约束**

上述阶段可以直接映射现有字段：

| 候选内容 | 现有字段 |
|---|---|
| 阶段顺序、目的、必修/选修 | `stage_blueprints[]`：`stable_key`、`section_kind`、`objective`、`inclusion` |
| 正式知识依赖 | `knowledge_blueprints[]`：`prerequisite_keys`、`parent_key`；根集合放`required_node_keys` |
| 为什么现在学、前次关系、重点 | `learning_guidance`：`why_now`、`previous_relation`、`exposure_relation`、`knowledge_keys`、`learning_focus` |
| 教材与实践前置 | `reading_prerequisites`、`practice_prerequisites` |
| 同一项目的连续增量 | `practice_delta`：`baseline`、`increment`、`preserved`、`validation`、`reuse` |
| 实际任务与验收 | `practice_blueprints[]`：`section_key`、`goal`、`acceptance`、`node_keys`、`in_scope`、`out_scope` |
| 教材安排 | `resources[]`：一个Primary，按需Supplement/Comparison |

可以新增候选知识键 `node.agent_loop`、`node.eval_lite`、`node.coding_workspace`、`node.workflow_effects`；它们只是现有知识蓝图中的记录，不需要新实体。

依赖建议明确为：

```text
environment → model_api → tools → agent_loop → eval_lite
tools → rag
agent_loop → langgraph → context
agent_loop → coding_workspace
langgraph → workflow_effects
eval_lite → reliability

RAG capstone:
  reliability + rag + langgraph + context

Coding capstone:
  reliability + coding_workspace + langgraph + context

Workflow capstone:
  reliability + workflow_effects + context
```

这些是**新候选内容版本的依赖**，不覆盖已发布v1/v2/v3。各包内必须包含所有引用节点；不要直接写一个跨包Python知识键却缺少对应记录。RAG与LangGraph没有相互知识先修；表中的先后还包含实践基线接续。

两项现有校验边界尤其需要保留：

- [Primary校验](D:/studyplan/backend/app/domain/resources/curation.py:289) 要求在来源目录rank中递增连续；单纯递增还不够。不能通过重排或删掉目录章节绕过真实作者顺序。
- [Seed校验](D:/studyplan/backend/app/domain/domain_packs/validation.py:71) 校验引用、版本、DAG和审核字段，但不会审阅网页。`reviewed`需要日期，章节还需要`review_note`；格式通过不能替代免费正文与教材内容证据。

**3. 最少需要补核的资料清单**

| 最小补核项 | 具体范围 | 完成后可解除的缺口 |
|---|---|---|
| Python前置正文与版本 | 第4、5、7、8、12章；另核实JSON、基础测试、模块和路径处理的实际阅读段落；统一`/3/`与`/3.14/`来源记录 | 三个方向的Python入口；修正第12→4章倒序 |
| 共用Agent教材正文 | Models、Messages、Tools、Structured output、Agents、Test；核实无需付费即可阅读、实际标题/段落、页面版本或检查日期 | 三个候选的共用主线；API使用成本单独提示 |
| RAG与上下文资料 | Retrieval实际落地地址、索引/检索/生成阅读范围；Graph、Persistence、Memory的适用版本 | Knowledge/RAG主线及共用恢复/上下文阶段 |
| Coding专属资料 | 工作区路径边界、差异预览与应用、过期基线、固定测试入口及失败处理；仓库未发现完整审核链 | C4–C5的教材缺口，不能只靠通用Tools/Graph链接补齐声明 |
| Workflow专属资料 | 审批与执行分离、业务键去重、已知失败/未知结果、恢复及动作日志 | W5教材缺口，避免把checkpoint等同于副作用安全 |
| 来源审核记录整理 | 日期、实际URL、版本线索、阅读范围、免费正文结论、适用节点及限制 | 将历史index review与私人课程审阅转成可追溯的正式教材记录 |

源码切片可以暂缓，不阻塞基础闭环。若保留fixture中的 `learn-claude-code`，至少补固定commit、真实文件、调用链与阅读问题；补核前保持 `optional: true`、`verification_status: "suggested"`。Hello-Agents对比同样需要确切章节，不能只给两个链接就标成Comparison。

**4. 已证实与尚未证实**

已证实的是仓库事实：

- 现有JSON、模型与校验规则能够承载阶段、依赖、教材角色、学习关系和贯穿实践增量。
- 公共内容文件有通用Agent及Python包，没有三个独立正式Blueprint。
- [10月2日私人课程](D:/studyplan/docs/curriculum/test-account-agent-plan-2026-10-02.json) 已有可复用的具体任务：最小Agent/Eval-Lite、RAG与Workflow独立分支、MCP选修，以及trace、来源、错误和成果验收要求。
- 对应验收文档记录了19个官方页面的历史审阅；本次读取到的`reviewed-urls.json`是URL清单，不能单独证明免费正文或冻结页面内容。
- Tool Calling fixture明确未发布，源码未核对；v2/v3修正的是本地章节选择，没有新增网页审核。

尚未证实的是：

- 三个候选已完成完整JSON、DomainPack校验、导入、发布、目标匹配或普通用户生成。
- 所有教材免费正文、真实作者顺序、当前来源版本与示例兼容性已完成审核。
- Coding与Workflow专属教材链完整，或各阶段学生实践已经执行。
- fixture的源码路径、固定commit和跨教程关系已经审核。
- 10月4日正式内容交付门禁已经满足。

本次文件JSON解析：`PASS`。候选完整Seed校验、业务测试、真实PG、浏览器、外部资料核验与模型API调用：`NOT RUN`。这些候选可供主会话落成现有JSON；正式审核与运行验收状态仍需分别记录。
