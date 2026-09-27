"""RAG 端口：从**独立 RAG 项目**获取已授权证据。

设计约束（SOFTWARE_DESIGN.md §2 §6）：

- 主项目**不**自己实现索引/检索；索引引擎由独立项目维护。
- ``scope`` 是服务端生成的 ``AuthContext`` —— 检索**必须**带授权范围，
  不能只按 query 检索（否则会跨用户泄露）。
- RAG 超时/失败**只**使"相关补充资料不可用"，**不得**导致学习进度回滚，
  也**不得**让模型伪造证据。
- 返回的证据必须带**引用**（``citation``），使"这句话来自哪"可追溯。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class Citation:
    """一条证据的来源定位。

    ``locator`` 可为 URL、章节号或视频时间点。**不得伪造** ——
    无法给出来源时应返回 ``Evidence.grade = "unavailable"`` 而非臆造链接。
    """

    source_url: str | None = None
    section_anchor: str | None = None
    title: str = ""


@dataclass(frozen=True, slots=True)
class Evidence:
    """一条检索到的证据。"""

    evidence_id: str
    text: str
    citation: Citation
    score: float = 0.0
    #: ``verified`` 表示本平台可核验来源；``unavailable`` 表示取不到真实证据。
    grade: str = "unverified"


@dataclass(frozen=True, slots=True)
class RAGUnavailable:
    """RAG 不可用时的**显式**返回。

    调用方由此得知"补充资料不可用"，而不是把它当作"没有相关资料"。
    """

    reason: str
    suggestions: tuple[str, ...] = field(default_factory=tuple)


class RAGUnavailableError(RuntimeError):
    """RAG 服务故障。上层须降级为"补充资料不可用"，不得回滚学习进度。"""


@runtime_checkable
class RAGPort(Protocol):
    """已授权证据检索端口。"""

    def retrieve(
        self, *, scope: object, query: str, limit: int
    ) -> list[Evidence] | RAGUnavailable: ...


__all__ = [
    "Citation",
    "Evidence",
    "RAGPort",
    "RAGUnavailable",
    "RAGUnavailableError",
]
