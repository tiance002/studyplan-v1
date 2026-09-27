"""ports：领域与外部世界之间的协议边界。

设计约束（SOFTWARE_DESIGN.md §2）：

- Ports 是 ``Protocol``，**不含实现**，也不 import 任何 SDK / ORM / 框架。
- 契约测试必须**同样作用于 Fake 与真实适配器**：Fake 通过 ≠ 真实适配器通过。
- **Failure DTO 不准静默转成空成功**：外部故障必须显式表达，
  不能"返回空列表"让上层误以为"查询成功但没有结果"。
- Fake **不允许部署为真实评审能力**。

依赖方向：``api -> application -> domain & ports <- infrastructure``。
infrastructure 实现 ports；domain 只依赖 ports，不依赖 infrastructure。
"""

from app.ports.graph_runner import GraphRunnerPort
from app.ports.llm import LLMPort, LLMResult
from app.ports.rag import Evidence, RAGPort
from app.ports.repository import RepositoryPort
from app.ports.resource_index import ResourceIndexPort

__all__ = [
    "Evidence",
    "GraphRunnerPort",
    "LLMPort",
    "LLMResult",
    "RAGPort",
    "RepositoryPort",
    "ResourceIndexPort",
]
