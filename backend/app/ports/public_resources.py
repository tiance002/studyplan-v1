"""公共资源目录端口（B2-V §五）。

用途：计划**输出前**必须校验 ``stage_resource_assignments.source_ref`` /
``section_refs`` 指向的公共资源**真实存在**且「章节属于对应来源」。
没有可用来源时，输出层只能给出**搜索建议**，绝不编造已核验章节。

本端口**只读**：公共资源由受审核流程写入（应用角色只有 ``SELECT``）。
"""

from __future__ import annotations

from typing import Protocol, Sequence, runtime_checkable

from app.domain.resources.curation import PublicResourceSection, PublicResourceSource


@runtime_checkable
class PublicResourceCatalogPort(Protocol):
    """公共资源来源 / 章节的只读目录。"""

    def load_sources(self, *, source_ids: Sequence[str]) -> dict[str, PublicResourceSource]: ...

    def load_sections(
        self, *, section_ids: Sequence[str]
    ) -> dict[str, PublicResourceSection]: ...

    def load_source_sections(
        self, *, source_ids: Sequence[str]
    ) -> dict[str, PublicResourceSection]:
        """Read complete author catalogs for these sources, not selected IDs."""
        ...


__all__ = ["PublicResourceCatalogPort"]
