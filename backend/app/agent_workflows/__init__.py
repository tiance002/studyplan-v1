"""agent_workflows：LangGraph 三张小 StateGraph 的构建与节点实现。

**唯一业务编排层**（ADR-0005）。设计约束：

- 只通过应用服务 / Ports 读写业务实体，**不得**自行 SQL 或创造第二份业务规则。
- Graph State 只存**有限 JSON 可序列化**字段；不写密钥、无限历史、
  完整检索文本、二进制附件（SOFTWARE_DESIGN.md §4）。
- ``interrupt()`` **只**位于独立等待节点；其前只做无副作用快照读取。

⚠️ 本包的第一行导入必须是 ``_msgpack_guard``：它必须在 langgraph
被 import **之前**执行。**不要调整导入顺序。**
"""

from __future__ import annotations

from app.agent_workflows._msgpack_guard import STRICT_MSGPACK_ENV, enforce_strict_msgpack

#: 进程内记录一次实际生效值，供启动日志与测试断言。
STRICT_MSGPACK_VALUE = enforce_strict_msgpack()

GRAPH_VERSION = "1"

__all__ = [
    "GRAPH_VERSION",
    "STRICT_MSGPACK_ENV",
    "STRICT_MSGPACK_VALUE",
    "enforce_strict_msgpack",
]
