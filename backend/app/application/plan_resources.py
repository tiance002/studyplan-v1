"""阶段资源的**输出与落库前**校验（B2-V §五）。

## 两个方向，一份规则

公共资源的 ``source_ref`` / ``section_refs`` 必须**真实存在**且「章节属于
对应来源」。这条规则在**两个时机**都要生效，且判定必须一致：

1. **落库前**（保存草案 / 发布）：把无法核验的引用**降级**为「无来源 + 搜索
   建议」，使 ``stage_resource_assignments.source_ref`` 的复合外键不会指向
   不存在的来源（§五），同时**不编造**已核验章节。
2. **输出前**（草案/正式路线视图）：把引用解析成可安全展示的章节，
   核验失败时**显式**给出搜索建议与降级说明。

两个方向都复用领域层的 :func:`~app.domain.resources.curation.resolve_assignment_output`，
因此不可能出现「落库认为有效、输出认为无效」的分叉。
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from app.domain.enums import StageResourceRole
from app.domain.resources.curation import (
    PublicResourceSection,
    PublicResourceSource,
    ResolvedSection,
    StageResourceAssignment,
    resolve_assignment_output,
)
from app.ports.public_resources import PublicResourceCatalogPort

__all__ = [
    "StageResourceView",
    "normalize_stage_resources",
    "resolve_stage_resources",
]

#: 降级且没有任何搜索建议时的兜底搜索词（**建议**，不是已核验来源）。
_DEFAULT_FALLBACK = "该阶段 学习资源"


def restrict_pack_resources(state: Mapping[str, Any], pack: Mapping[str, Any]) -> dict[str, Any]:
    """A real catalog row is insufficient: it must belong to this selected pack."""
    result = deepcopy(dict(state))
    sources = {s["source_id"]: s for s in pack.get("resources", [])}
    approved_urls = {section["url"] for source in sources.values() for section in source.get("sections", [])}
    approved_urls.update(source["canonical_url"] for source in sources.values())
    for stage in (result.get("outline") or {}).get("sections", []):
        stage_nodes = {n for u in result.get("units", []) if u.get("section_key") == stage["stable_key"]
                       for n in u.get("node_keys", [])}
        for item in stage.get("resources", []):
            source = sources.get(item.get("source_ref"))
            sections = {s["section_id"]: s for s in source.get("sections", [])} if source else {}
            refs = item.get("section_refs", [])
            root_case = bool(source and source.get("media_type") == "repo" and item.get("role") == "case_study"
                             and not refs and source.get("verification_status") == "legacy_index")
            valid = bool(source and (refs or root_case) and item.get("source_version") == source["source_version"]
                         and all(ref in sections for ref in refs))
            pending_scope = (pack.get("curriculum_review") or {}).get("review_status") == "selected_scope_pending"
            indexed_entry = bool(pending_scope and source and source.get("verification_status") == "legacy_index"
                                 and source.get("checked_at")
                                 and all(sections[ref].get("verification_status") == "legacy_index"
                                         and sections[ref].get("checked_at") for ref in refs))
            if valid and source is not None and pack.get("pack_key") == "agent.application" and not root_case and not indexed_entry:
                valid = source.get("verification_status") == "reviewed" and all(
                    sections[ref].get("verification_status") == "reviewed" for ref in refs)
                applicable = {k for ref in refs for k in sections[ref].get("applicable_node_keys", [])}
                linked = set(item.get("node_keys") or stage_nodes) & stage_nodes & applicable
                valid = valid and bool(linked)
                item["node_keys"] = sorted(linked)
            else:
                item["node_keys"] = sorted(set(item.get("node_keys") or stage_nodes) & stage_nodes)
            if not valid:
                item.update(source_ref="", section_refs=[], source_version=0)
                item["fallback_search_terms"] = item.get("fallback_search_terms") or [stage["title"] + " 官方文档 教程"]
        for extension in stage.get("extensions", []):
            links = extension.get("links", [])
            extension["links"] = [url for url in links if url in approved_urls]
            if len(extension["links"]) != len(links):
                extension["search_hints"] = extension.get("search_hints") or [extension.get("topic", stage["title"]) + " 官方文档"]
    return result


@dataclass(frozen=True, slots=True)
class StageResourceView:
    """阶段资源分配的可展示视图（已核验章节 + 显式降级说明）。"""

    assignment_id: str
    stage_id: str
    role: StageResourceRole
    creator: str
    source_ref: str
    source_version: int
    ordered_sections: tuple[ResolvedSection, ...]
    fallback_search_terms: tuple[str, ...]
    warnings: tuple[str, ...]
    node_ids: tuple[str, ...] = ()
    title: str = ""
    media_type: str = ""
    language: str = ""
    documentation_version: str = ""
    verification_status: str = "unverified"

    @property
    def degraded(self) -> bool:
        return bool(self.warnings)


def _load_catalog(
    assignments: Sequence[StageResourceAssignment],
    *,
    catalog: PublicResourceCatalogPort,
) -> tuple[dict[str, PublicResourceSource], dict[str, PublicResourceSection]]:
    """一次取回所有被引用的来源与章节（避免 N 次往返）。"""
    source_ids = sorted({a.source_ref for a in assignments if a.source_ref})
    return catalog.load_sources(source_ids=source_ids), catalog.load_source_sections(
        source_ids=source_ids
    )


def resolve_stage_resources(
    assignments: Sequence[StageResourceAssignment],
    *,
    catalog: PublicResourceCatalogPort,
    stage_titles: Mapping[str, str],
) -> tuple[StageResourceView, ...]:
    """把阶段资源分配解析为**可安全展示**的视图（B2-V §五）。

    核验失败时不编造章节，只给出搜索建议与一条显式说明。
    """
    sources, sections = _load_catalog(assignments, catalog=catalog)
    views: list[StageResourceView] = []
    for assignment in assignments:
        resolved = resolve_assignment_output(
            assignment,
            known_sources=sources,
            known_sections=sections,
            fallback_hint=stage_titles.get(assignment.stage_id, ""),
        )
        source = sources.get(resolved.source_ref) if resolved.source_ref else None
        views.append(
            StageResourceView(
                assignment_id=resolved.assignment_id,
                stage_id=resolved.stage_id,
                role=resolved.role,
                creator=source.creator if source is not None else "",
                source_ref=resolved.source_ref,
                source_version=resolved.source_version,
                ordered_sections=resolved.sections,
                fallback_search_terms=resolved.fallback_search_terms,
                warnings=resolved.warnings,
                node_ids=assignment.node_ids,
                title=source.title if source else "",
                media_type=source.media_type if source else "",
                language=source.language if source else "",
                documentation_version=source.documentation_version if source else "",
                verification_status=source.verification_status if source and not resolved.degraded else "unverified",
            )
        )
    return tuple(views)


def normalize_stage_resources(
    assignments: Sequence[StageResourceAssignment],
    *,
    catalog: PublicResourceCatalogPort,
    stage_titles: Mapping[str, str],
) -> tuple[StageResourceAssignment, ...]:
    """**落库前**把无法核验的引用降级（B2-V §五）。

    对每条分配执行与输出层**完全相同**的核验：

    - 来源存在且章节归属正确 → 原样保留（保留 ``source_ref`` 与有序章节）；
    - 否则 → 丢掉 ``source_ref``（存 NULL，不触发外键）与 ``section_refs``，
      改用搜索建议，**绝不**写入未核验的章节引用。

    这样 ``GET /drafts`` 展示的降级结果与数据库中的正式版本**完全一致**，
    用户的确认哈希也覆盖了这份降级后的内容。
    """
    sources, sections = _load_catalog(assignments, catalog=catalog)
    normalized: list[StageResourceAssignment] = []
    for assignment in assignments:
        resolved = resolve_assignment_output(
            assignment,
            known_sources=sources,
            known_sections=sections,
            fallback_hint=stage_titles.get(assignment.stage_id, ""),
        )
        if not resolved.degraded:
            normalized.append(assignment)
            continue
        fallback = tuple(resolved.fallback_search_terms) or (_DEFAULT_FALLBACK,)
        normalized.append(
            StageResourceAssignment.create(
                project_id=assignment.project_id,
                stage_id=assignment.stage_id,
                role=assignment.role,
                plan_id=assignment.plan_id,
                # 降级：不写未核验来源，只保留搜索建议。
                source_ref="",
                section_refs=(),
                order_index=assignment.order_index,
                source_version=0,
                fallback_search_terms=fallback,
                node_ids=assignment.node_ids,
            )
        )
    return tuple(normalized)
