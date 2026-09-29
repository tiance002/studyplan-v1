# Agent 应用开发资源索引 v1

领域包：`agent.application` / `1`。9 个主题、27 个知识及子知识节点，14 个官方章节。

章节 ID 是本仓库的目录标识，不是出版方提供的编号；order_index 是本路线的推荐阅读顺序，不是原书章节编号。核对日期是 2026-09-29，时间字段按审核日记录。living docs 后续可能变化，内容变更必须发布新包版本。此索引保存标题、URL 与概述，不复制正文。

## The Python Tutorial

机构：Python Software Foundation；类型：documentation；语言：en；文档版本：Python 3.14；目录版本：1；状态：reviewed。

| 推荐顺序 | 章节与官方 URL | 本地章节 ID | 适用知识键 | 内容核对摘要 |
|---|---|---|---|---|
| 1 | [12. Virtual Environments and Packages](https://docs.python.org/3.14/tutorial/venv.html) | `sec_agent_venv_v1` | node.environment, node.environment.1, node.environment.2 | 已核对虚拟环境创建、激活及包管理；适用于独立实验环境。 |
| 2 | [4. More Control Flow Tools](https://docs.python.org/3.14/tutorial/controlflow.html) | `sec_agent_functions_v1` | node.environment, node.environment.1, node.environment.2 | 已核对函数定义与控制流；适用于工具函数和基本输入处理。 |

## LangChain / LangGraph Python documentation

机构：LangChain；类型：documentation；语言：en；文档版本：v1 living documentation; reviewed 2026-09-29；目录版本：1；状态：reviewed。

| 推荐顺序 | 章节与官方 URL | 本地章节 ID | 适用知识键 | 内容核对摘要 |
|---|---|---|---|---|
| 1 | [Models](https://docs.langchain.com/oss/python/langchain/models) | `sec_agent_models_v1` | node.model_api, node.model_api.1, node.model_api.2 | 已核对模型初始化、调用、参数和工具调用入口。 |
| 2 | [Messages](https://docs.langchain.com/oss/python/langchain/messages) | `sec_agent_messages_v1` | node.model_api, node.model_api.1, node.model_api.2 | 已核对 system/user/tool 消息、文本提示及上下文角色。 |
| 3 | [Tools](https://docs.langchain.com/oss/python/langchain/tools) | `sec_agent_tools_v1` | node.tools, node.tools.1, node.tools.2 | 已核对工具定义、schema、返回值和错误处理；与结构化工具节点匹配。 |
| 4 | [Structured output](https://docs.langchain.com/oss/python/langchain/structured-output) | `sec_agent_structured_v1` | node.tools, node.tools.1, node.tools.2 | 已核对 JSON/Pydantic schema 与工具/供应商策略；适用于可校验输出。 |
| 5 | [Graph API overview](https://docs.langchain.com/oss/python/langgraph/graph-api) | `sec_agent_graph_v1` | node.langgraph, node.langgraph.1, node.langgraph.2 | 已核对 StateGraph、state/reducer、nodes、edges 和条件路由目录与说明。 |
| 6 | [Persistence](https://docs.langchain.com/oss/python/langgraph/persistence) | `sec_agent_persistence_v1` | node.langgraph, node.langgraph.1, node.langgraph.2, node.context, node.context.1, node.context.2 | 已核对 checkpointer/store 区别与 thread_id；仅学习基本持久化边界。 |
| 7 | [Retrieval](https://docs.langchain.com/oss/python/deepagents/retrieval) | `sec_agent_retrieval_v1` | node.rag, node.rag.1, node.rag.2 | 已核对 loaders、splitters、embeddings、vector stores 及 2-step/agentic RAG；只用检索基础部分。 |
| 8 | [Short-term memory](https://docs.langchain.com/oss/python/langchain/short-term-memory) | `sec_agent_memory_v1` | node.context, node.context.1, node.context.2 | 已核对会话状态、上下文窗口及 trim/summarize 基础；不扩展长期记忆实现。 |
| 9 | [Test](https://docs.langchain.com/oss/python/langchain/test) | `sec_agent_testing_v1` | node.capstone, node.capstone.1, node.capstone.2 | 已核对 unit/integration/trajectory evaluation 区分；与失败分支验证匹配。 |
| 10 | [Agents](https://docs.langchain.com/oss/python/langchain/agents) | `sec_agent_agents_v1` | node.capstone, node.capstone.1, node.capstone.2 | 已核对模型与工具循环及 harness 构成；作为综合知识助手参考。 |

## Model Context Protocol documentation

机构：Model Context Protocol maintainers；类型：documentation；语言：en；文档版本：Protocol 2026-07-28；目录版本：1；状态：reviewed。

| 推荐顺序 | 章节与官方 URL | 本地章节 ID | 适用知识键 | 内容核对摘要 |
|---|---|---|---|---|
| 1 | [Architecture overview](https://modelcontextprotocol.io/docs/2026-07-28/learn/architecture) | `sec_agent_mcp_v1` | node.mcp, node.mcp.1, node.mcp.2 | 已核对 host/client/server、tools/resources/prompts 和 stdio/Streamable HTTP；页面标明 2026-07-28 协议。 |

## LangSmith Evaluation documentation

机构：LangChain；类型：documentation；语言：en；文档版本：living documentation; reviewed 2026-09-29；目录版本：1；状态：reviewed。

| 推荐顺序 | 章节与官方 URL | 本地章节 ID | 适用知识键 | 内容核对摘要 |
|---|---|---|---|---|
| 1 | [LangSmith Evaluation](https://docs.langchain.com/langsmith/evaluation) | `sec_agent_evaluation_v1` | node.reliability, node.reliability.1, node.reliability.2 | 已核对数据集、评价标准及 offline/online evaluation；首版只学习离线验证思想，不要求云账号。 |

## 支持范围与限制

- Agent 应用开发：环境、API/Prompt、工具/结构化输出、LangGraph、RAG、MCP、上下文/记忆、评价/可靠性与综合实践。
- Python 工程入门：保留 `python.engineering` v1 旧目录；旧目录索引不会被改称为新审核资源。
- 其他方向：通用知识结构与搜索建议，不绑定 Python 包，也不提供虚构已核验资源。
- 此轮仅提供学习路线和资料；没有实现 RAG/MCP 运行服务、聊天、长期记忆或评分平台。英语官方资料可能需要一定阅读基础；使用其中的云模型示例可能产生服务商费用。
- 已审核表示核对了章节内容、主题与 URL，不表示保证所有示例代码在所有依赖版本上可运行。
