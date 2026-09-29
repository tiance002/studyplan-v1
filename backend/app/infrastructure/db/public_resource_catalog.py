"""``PublicResourceCatalogPort`` 的 PostgreSQL 实现（B2-V §五）。

公共表（``public_resource_sources`` / ``public_resource_sections``）对应用角色
只有 ``SELECT`` 权限，策略是 ``FOR SELECT USING (true)``，因此读取不需要项目
上下文；这里仍走同一个 ``set_config`` 事务封装，保持连接使用方式一致。
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from typing import Any

import psycopg
from app.domain.resources.curation import PublicResourceSection, PublicResourceSource
from app.domain.resources.models import require_safe_url
from app.infrastructure.db.plan_repository import to_psycopg_dsn
from psycopg.rows import dict_row

__all__ = ["PgPublicResourceCatalog"]


def _source_from(row: dict[str, Any]) -> PublicResourceSource:
    url = str(row["canonical_url"])
    require_safe_url(url)
    return PublicResourceSource(
        source_id=str(row["source_id"]),
        canonical_url=url,
        title=str(row["title"]),
        creator=str(row.get("creator") or ""),
        media_type=str(row.get("media_type") or "course"),
        language=str(row.get("language") or "zh"),
        source_version=int(row.get("source_version") or 1),
        provenance=str(row.get("provenance") or ""),
        checked_at=row.get("checked_at"),  # type: ignore[arg-type]
        created_at=row.get("created_at"),  # type: ignore[arg-type]
        documentation_version=str(row.get("documentation_version") or ""),
        verification_status=str(row.get("verification_status") or "legacy_index"),
    )


def _section_from(row: dict[str, Any]) -> PublicResourceSection:
    url = str(row["url"])
    require_safe_url(url)
    return PublicResourceSection(
        section_id=str(row["section_id"]),
        source_id=str(row["source_id"]),
        order_index=int(row["order_index"]),  # type: ignore[arg-type]
        title=str(row["title"]),
        url=url,
        anchor=str(row.get("anchor") or ""),
        checked_at=row.get("checked_at"),  # type: ignore[arg-type]
        verification_status=str(row.get("verification_status") or "legacy_index"),
        review_note=str(row.get("review_note") or ""),
    )


class PgPublicResourceCatalog:
    """只读目录实现。空入参直接返回空字典，不产生 SQL 往返。"""

    def __init__(self, dsn: str) -> None:
        self._dsn = to_psycopg_dsn(dsn)

    @contextmanager
    def _conn(self) -> Iterator[psycopg.Connection[dict[str, Any]]]:
        with psycopg.connect(
            self._dsn, row_factory=dict_row
        ) as conn:  # type: psycopg.Connection[dict[str, Any]]
            yield conn

    def load_sources(self, *, source_ids: Sequence[str]) -> dict[str, PublicResourceSource]:
        wanted = [s for s in source_ids if s]
        if not wanted:
            return {}
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM public.public_resource_sources WHERE source_id = ANY(%s)",
                (wanted,),
            ).fetchall()
        return {str(r["source_id"]): _source_from(r) for r in rows}

    def load_sections(
        self, *, section_ids: Sequence[str]
    ) -> dict[str, PublicResourceSection]:
        wanted = [s for s in section_ids if s]
        if not wanted:
            return {}
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM public.public_resource_sections WHERE section_id = ANY(%s)",
                (wanted,),
            ).fetchall()
        return {str(r["section_id"]): _section_from(r) for r in rows}
