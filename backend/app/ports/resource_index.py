"""资源索引端口：把知识节点映射到真实资源。

设计约束（SOFTWARE_DESIGN.md §2 §6）：

- **URL 可达 ≠ 内容质量**。返回结果必须分别携带可达性、覆盖与出处，
  平台不对教学质量下断言。
- 找不到真实资源时返回 ``unavailable`` + 检索建议，
  **绝不伪造 URL 或视频时间戳**。
- 偏好按 节点 > 单元 > 项目默认 > 系统默认 生效；
  **临时切换不写全局**。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from app.domain.resources.models import (
    ResourcePreference,
    ResourceRecord,
    UnavailableResult,
)


@dataclass(frozen=True, slots=True)
class ResourceQuery:
    """一次资源查询的输入。

    ``scope`` 必须是服务端生成的授权上下文；``preference`` 是**已解析**
    的最终偏好（调用方负责按优先级回落），端口不再自行解释层级。
    """

    scope: object
    node_keys: tuple[str, ...]
    preference: ResourcePreference
    limit: int = 10
    extra: dict[str, object] = field(default_factory=dict)


class ResourceIndexUnavailableError(RuntimeError):
    """资源索引不可用。上层应降级为 ``unavailable``，不阻断结构生成。"""


@dataclass(frozen=True, slots=True)
class ResourceInspectionQuery:
    scope: object
    candidate: dict
    query: str
    preference: ResourcePreference
    paths: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ResourceInspectionResult:
    status: str
    candidate: dict | None
    receipts: list[dict]
    error: str | None = None


@runtime_checkable
class ResourceIndexPort(Protocol):
    """资源检索端口。真实实现由独立资源服务或已校验资源池提供。"""

    def find(
        self, query: ResourceQuery
    ) -> list[ResourceRecord] | UnavailableResult: ...


__all__ = [
    "ResourceIndexPort",
    "ResourceIndexUnavailableError",
    "ResourceQuery",
]
