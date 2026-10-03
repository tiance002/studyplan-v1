# Blueprint 来源正文审核（2026-10-03）

## 审核范围与结论

本次按共享候选证据包，复核现有 `agent-application-v3.json` 中 Python Tutorial 与 LangChain/LangGraph 引用，并覆盖候选课程提出的 Python 教程第 4、5、6、7、8、12 章及 `json`、`pathlib`、`unittest` 标准库参考页。LangChain/LangGraph 审核 Models、Messages、Tools、Structured output、Agents、Test、Retrieval、Graph API、Persistence、Short-term memory 十页。

审核日期为本机 `2026-10-03`（Asia/Shanghai）。Web 工具返回各页 “Crawled: today”；没有单独可见的工具时钟，故工具抓取日记为 **NOT OBSERVABLE**。以下均由 Python Software Foundation 或 LangChain 官方文档域名提供；对于我本次打开的页面，工具显示的页面 URL 与请求 URL 一致，未观察到跳转。该观察仅限本次页面访问。无需登录，工具可直接读取英文正文和具体章节/小节，不仅是搜索摘要。此结论表示公开正文可读，不表示运行过示例、验证兼容性或审查整站。

现有 JSON 的 `source_version: 1` 是 StudyPlan 内部来源记录版本，不是官方产品版本。Python 页面标题显示 Python 3.14.8 文档；文档系列为 3.14。LangChain/LangGraph 页面是滚动更新的 OSS Python 文档，页面正文没有给出本次审核所对应的 LangChain 或 LangGraph 包版本；记为 **官方包版本：NOT OBSERVABLE**。正文个别说明出现 `langchain>=1.1` / `>=1.2`，不能据此断定整套教程或示例对应某个固定包版本。页面与内容以后可能变化。

## Python 官方文档

| 官方页面与本次实际读取范围 | 正文证据 | 建议用途与覆盖边界 |
|---|---|---|
| [第4章 More Control Flow Tools](https://docs.python.org/3.14/tutorial/controlflow.html)；第4.1–4.9节 | 正文含 `if`、`for`、`range`、`break`/`continue`、`match`、函数定义、参数与返回值示例。 | Python 前置 P1：控制流、函数、基本输入处理。覆盖到工具函数基础；不是完整初学编程课程，也不讲 Agent 工具派发。 |
| [第5章 Data Structures](https://docs.python.org/3.14/tutorial/datastructures.html)；列表、列表推导、集合、字典等章节 | 正文示范列表的增删查、推导式、集合运算；字典小节说明键与映射。 | Python 前置 P1/P2：列表与字典是记录、过滤和检索样例的基础。只涵盖内置数据结构，不是知识库/RAG 教程。 |
| [第6章 Modules](https://docs.python.org/3.14/tutorial/modules.html)；模块、导入及包章节 | 正文把模块定义为含 Python 定义与语句的 `.py` 文件，并展示 import、命名空间与包引用。 | Python 前置补充；Coding 的模块组织基础。不能证明能安全检查、修改或执行任意项目代码。 |
| [第7章 Input and Output](https://docs.python.org/3.14/tutorial/inputoutput.html)；特别是 7.2、7.2.2 | 正文说明 `open(filename, mode, encoding=None)`、读写模式与 UTF-8 示例；7.2.2 介绍用 `json` 序列化嵌套列表和字典。 | Python 前置 P2：文件读写与 JSON 文件化的入门主材料。教程示例没有定义安全路径边界或文件修改授权。 |
| [第8章 Errors and Exceptions](https://docs.python.org/3.14/tutorial/errors.html)；8.1–8.6 中的异常处理部分 | 正文展示 traceback、捕获指定异常、`try`/`except`/`else`/`finally` 等说明。 | Python 前置 P2：将缺文件、格式错误和运行错误分开处理。不是分布式失败、重试或未知外部执行结果规范。 |
| [第12章 Virtual Environments and Packages](https://docs.python.org/3.14/tutorial/venv.html)；12.1–12.3 | 正文标题确认仅有 12.1 Introduction、12.2 Creating Virtual Environments、12.3 Managing Packages with pip；说明依赖版本冲突、`venv` 创建与激活、pip 包管理及 `requirements.txt`。 | Python 前置 P3：建立可复现本地环境。页面文本和安装命令是文档说明；本次没有执行命令或安装依赖。 |
| [标准库 json](https://docs.python.org/3.14/library/json.html)；Basic Usage、编码/解码与对象转换说明 | 正文列出 `dump`/`dumps`/`load`/`loads` 及转换规则；明确 JSON 不是 framed protocol，连续对同一文件重复 dump 会形成无效 JSON。 | Python 前置 P2：序列化/反序列化结构化记录。需由课程另行设计版本、追加记录和损坏文件处理策略。 |
| [标准库 pathlib](https://docs.python.org/3.14/library/pathlib.html)；Pure/Concrete paths、文件读写、目录遍历及路径操作 | 正文展示 `Path`、`read_text`/`write_text`、`Path.walk`、路径重命名/移动等 API，并描述部分替换语义。 | Python 前置 P2；Knowledge/RAG 文件样例可作路径 API 参考，Coding 可作路径操作参考。该 API 参考本身不构成目录沙箱、越界阻止、符号链接安全或授权规则教程。 |
| [标准库 unittest](https://docs.python.org/3.14/library/unittest.html)；Basic example、断言、发现与运行概述 | 正文提供 `TestCase`、`assertEqual`/`assertRaises`、`unittest.main()` 示例；发现章节说明发现会导入测试模块并给出包路径注意事项。 | Python 前置 P2；三个候选均可用于本地确定性测试基础。它不是 LangChain 集成测试凭证，也不覆盖隔离外部代码执行。 |

Python 页面各自公开正文可读。内部现有 JSON 只登记了第4和第12章；第5、6、7、8章以及标准库页面属于本次新增核对证据，不能倒称为原 Seed 已经登记或预置。

## LangChain / LangGraph 官方文档

下表按候选路线建议节点归属：Knowledge/RAG（K）、Coding（C）、Workflow（W）。章节正文均可直接公开读取；网址按现有 v3 JSON 中 section URL 核对。所有这些引用记录内部仍是 `source_version: 1`。

| 官方页面与本次实际读取范围 | 正文证据 | 建议用途及边界 |
|---|---|---|
| [Models](https://docs.langchain.com/oss/python/langchain/models)；模型调用、工具调用、结构化输出和 stream/batch 相关段落 | 有 model 初始化与调用内容；正文明确模型单独调用时由应用执行工具请求并将结果回传，Agent 会处理工具循环；另有结构化输出方式说明。 | K1/C1/W1 的模型输入输出；可作 K2/C2/W2 工具流转补充。是 framework 教材，不证明示例与本仓库运行时或固定包版本兼容。 |
| [Messages](https://docs.langchain.com/oss/python/langchain/messages)；Message types 及 System/Human/AI/Tool 说明 | 正文列出四类消息并说明 AI 消息可含工具调用、Tool 消息保存工具结果。 | K1/C1/W1 的消息角色，K6/C6/W6 的消息上下文补充。不等于对不可信输入的安全处理教程。 |
| [Tools](https://docs.langchain.com/oss/python/langchain/tools)；工具定义、参数 schema、返回类型、状态访问、执行及 Error handling | 目录与正文覆盖类型提示/schema、工具名和描述、Pydantic/JSON schema、Command 返回、ToolMessage 与异常处理中间件示例。 | K2/C2/W2 的工具定义和错误路径，K3/C3/W3 工具循环补充。没有提供 Coding Agent 文件写入白名单/差异确认/过期基线控制的完整安全流程，也没有 Workflow 业务幂等保证。 |
| [Structured output](https://docs.langchain.com/oss/python/langchain/structured-output)；response format、ProviderStrategy、ToolStrategy、schema 类型 | 正文解释 schema 捕获/校验并写入 `structured_response`，比较 provider 原生与工具策略，列出 Pydantic、dataclass、TypedDict、JSON Schema。 | K1/C1/W1 的结构化输入输出。输出 schema 验证不能替代业务规则、安全许可或副作用授权。 |
| [Agents](https://docs.langchain.com/oss/python/langchain/agents)；Agent loop 与 harness 简介，以及带 checkpointer 的线程续接示例 | 正文定义 Agent 为模型循环调用工具至任务完成，并将 harness 说明为 prompt、tools 与 middleware；示例重用 `thread_id` 续接消息。 | K3/C3/W3 的有限工具循环概念；K5/C5/W4 可补充。此处说明通用 agent loop，不代表有限步数约束、审批或项目隔离已经预置完成。 |
| [Test](https://docs.langchain.com/oss/python/langchain/test)；整页（正文共 66 行） | 页面公开介绍 unit tests、integration tests、trajectory evaluations；写明 unit test 可用 in-memory fakes、integration tests 调真实 LLM API、eval 可评估轨迹。页面主要是策略概览和下游链接，没有在该页提供完整单元测试教程或样例实现。 | K3/K7、C3/C7、W3/W7 的测试类别和验收对照。需要独立设计固定案例和测试实现；不能用本页宣称 Coding 安全、发布测试门禁已覆盖。 |
| [Retrieval](https://docs.langchain.com/oss/python/deepagents/retrieval)；Retrieval、Building a knowledge base、From retrieval to RAG | 正文说明有限上下文/静态知识、查询时检索、知识库、loaders/vector stores、2-step 与 agentic RAG，并链接 semantic search 教程。 | K4 RAG；内容是 Deep Agents 文档下的检索概念。不能推断为只依赖纯标准库、无向量/embedding 成本，也不覆盖本地具体索引实现。 |
| [Graph API overview](https://docs.langchain.com/oss/python/langgraph/graph-api)；页面目录与 StateGraph、state、reducers、节点、conditional edges、Command 等段落 | 正文展示图节点和边、条件路由、状态更新/路由命令；示例包括编译图和线程配置。 | K5/C5/W4 流程状态与路由。说明的是 LangGraph 图构造；不是业务事务、一致性、外部副作用回滚教材。 |
| [Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)；页面全文（正文 145 行） | 正文区分 checkpointer 的 thread-scoped graph checkpoints 与 store 的跨 thread key-value 数据，并说明续谈、恢复、故障容错用途。 | K5/K6、C5/C6、W4/W5/W6 的状态持久化概念。它解释机制和范围，不覆盖审批授权、旧提案失效、业务键去重或 exactly-once 幂等。 |
| [Short-term memory](https://docs.langchain.com/oss/python/langchain/short-term-memory)；消息历史、trim/delete/summarize 与 context-window 相关章节 | 正文讲短期记忆、状态消息、摘要和裁剪历史的常见策略及 token 限制。 | K6/C6/W6 的上下文维护；比较裁剪与摘要的学习问题有来源支撑。摘要本身不等于权威历史存档或用户隔离机制。 |

## 对候选 Blueprint 的影响

- **Python 前置可以有真实来源支撑**：第4、5章支持控制流、函数、列表/字典；第7、8章和 `json`、`pathlib`、`unittest` 支持文件、结构化记录、异常分类、路径 API 和测试入门；第12章支持环境准备。第6章可作为 Coding 的模块阅读补充。Tutorial 不是完整零基础编程课程，需按目标受众保留已有前置假设。
- **Knowledge/RAG 教材链可支撑核心概念**：模型/消息、工具、Agent 循环、Retrieval、Graph、Persistence、short-term memory 和测试策略均有相应公开内容。仍要由 Blueprint 把文档标识、引用证据、无答案行为、检索失败分类和本地实践写清楚。
- **Coding 路线存在明确教材缺口**：官方 Tools 页支撑定义/schema/返回/工具错误，Python 官方文档支撑模块/路径 API/单元测试基础；本次没有找到被审页面对文件写入白名单、差异预览后批准、基线变化拒绝过期提案、执行任意仓库代码隔离的成套说明。应在候选审计中继续标记缺口，不能把这些安全要求标成教材已教。
- **Workflow 路线存在明确教材缺口**：Graph API 和 Persistence 能支撑状态路由、检查点/恢复概念；被审页面未覆盖业务审批策略、重复批准的幂等键、提案与输入/规则版本绑定、执行结果未知时的人工核对。保持模拟副作用项目并单独教授/实现上述规则。
- `Test` 正文说明了 unit/integration/eval 的差别，但目前打开的是概览页，不是 LangChain 的 unit testing 下游页面正文。因此来源引用可用于指出测试类别，若 Blueprint 需要 MockChatModel、in-memory persistence、trajectory evaluator 的实际 API 指导，应再核对相应具体教程页。
- Python `pathlib` 提供路径操作接口，不是路径沙箱安全标准；LangChain 工具页提供 schema/dispatch/异常处理示例，也不是权限系统。任何这些页面均不能据此证明路径限制、跨用户授权、事务/副作用保护或生产安全。

## 不在本次证据范围内

本审核没有执行任何文档代码、安装包、调用模型/API、执行搜索服务、打开 GitHub/API/Tavily、接触凭证/私有数据、访问产品数据库或服务。没有验证第三方 provider、私有仓库或模型费用。没有把文档示例描述成与仓库当前代码、某个固定依赖锁文件或生产环境兼容。审阅也没有评价页面许可、完整性或未来稳定性；这些超出此页源码正文核对任务。

## 执行记录

- 文件：`docs/curriculum/blueprint-source-audit-2026-10-03.md`（本次新增）。
- 指定官方来源正文：已公开访问并核对标题、可读范围、内容证据及最终显示 URL。
- 外部代码/示例运行：**NOT RUN**。
- 实际模型 / effort：父任务请求 `gpt-6-luna` / `high`；本执行环境没有暴露可核实的解析模型与 effort，实际值 **NOT OBSERVABLE**。
