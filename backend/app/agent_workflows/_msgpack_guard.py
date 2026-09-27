"""在 **import langgraph 之前**关闭 pickle fallback。

设计约束（SOFTWARE_DESIGN.md §5 / ADR-0002）：

    ``LANGGRAPH_STRICT_MSGPACK=true`` 必须在进程启动/导入 LangGraph
    **之前**设定，关闭不必要的 pickle fallback。

**为什么必须是独立模块**：Python 的导入顺序决定了"设环境变量"必须发生在
``langgraph`` 被任何模块 import 之前。如果把 ``os.environ.setdefault`` 写在
``agent_workflows/__init__.py`` 里，只要有任何模块先 import 了 langgraph，
这行就晚了。因此本模块**不 import 任何 langgraph 相关内容**，
只做一件事，并由 ``agent_workflows/__init__.py`` 在**第一行**导入。

安全性：pickle 反序列化可执行任意代码。Checkpoint 数据虽然来自本系统的
Checkpointer，但一旦数据库被写入恶意 payload，pickle fallback 会把
"读取断点"变成"任意代码执行"。关闭 fallback 是纵深防御的一环。
"""

from __future__ import annotations

import os

#: 期望值：关闭 pickle fallback。见 SOFTWARE_DESIGN.md §5。
STRICT_MSGPACK_ENV = "LANGGRAPH_STRICT_MSGPACK"


def enforce_strict_msgpack() -> str:
    """确保 ``LANGGRAPH_STRICT_MSGPACK`` 为真。

    用 ``setdefault`` 的语义而非硬覆盖：运维若显式设为 ``false``
    （例如排查兼容问题），本函数**不静默改回**，而是让显式配置生效 ——
    但会在返回值里如实告知当前值，便于启动日志记录。

    Returns:
        当前生效的值（``"true"`` / ``"false"`` / 其他原值）。
    """
    os.environ.setdefault(STRICT_MSGPACK_ENV, "true")
    return os.environ.get(STRICT_MSGPACK_ENV, "")


__all__ = ["STRICT_MSGPACK_ENV", "enforce_strict_msgpack"]
