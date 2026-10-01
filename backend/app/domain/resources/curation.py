"""resources 领域（V1.2）：公共资源目录、章节、阶段主线分配与扩展知识。

设计定位（V1.2 §2.2 §二.4）：

- ``PublicResourceSource`` / ``PublicResourceSection`` 是**公共受审核、只读**的
  资源来源与章节，可被多用户读；**用户不可直接写**。
- ``StageResourceAssignment`` / ``KnowledgeExtension`` 属于**私人已发布计划快照**，
  公共资源更新**不**静默修改个人已确认路线。
- 同 URL 可有多个章节：``PublicResourceSection`` 有独立 ``anchor`` / ``order_index``，
  因此**不能**用 ``UNIQUE(url)`` 登记章节。

硬约束（V1.2 §2.2 §3）：

- ``checked_at`` 只表示「链接/章节索引曾确认」，**不代表教学质量**。
- 无核验链接时保存**搜索词**而非编造 URL（``require_safe_url`` 拒绝私网/非法 scheme）。
- **不做**章节重叠率 / 覆盖率 / 作者选型分析 —— 本模块不提供任何此类计算。
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Mapping

from app.core.errors import ValidationAppError
from app.core.ids import new_id
from app.domain.enums import (
    ResourceSourceVisibility,
    StageResourceRole,
)
from app.domain.resources.models import require_safe_url

#: 每阶段主线条数上限：一阶段一条主线（设计 §2.1）。
MAINLINE_PRIMARY_MAX = 1

#: 每阶段扩展主题**软上限**：默认 1–2 项，超出只警告、不阻断（设计 §2.1 §3）。
EXTENSION_SOFT_LIMIT = 2


# --------------------------------------------------------------------------- 公共资源


@dataclass(frozen=True, slots=True)
class PublicResourceSource:
    """公共受审核资源来源（一门课 / 一条连续项目教程 / 一份资料）。

    ``source_version`` 与 ``checked_at`` 记录来源版本与索引确认时间，
    供私人计划在实例化时快照，避免公共更新静默改动个人路线。
    """

    source_id: str
    canonical_url: str
    title: str
    creator: str
    media_type: str
    language: str
    source_version: int = 1
    visibility: ResourceSourceVisibility = ResourceSourceVisibility.CURATED
    provenance: str = ""
    checked_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    documentation_version: str = ""
    verification_status: str = "legacy_index"

    @staticmethod
    def create(
        *,
        canonical_url: str,
        title: str,
        creator: str = "",
        media_type: str = "course",
        language: str = "zh",
        source_version: int = 1,
        provenance: str = "",
        now: datetime | None = None,
    ) -> "PublicResourceSource":
        require_safe_url(canonical_url)
        _require_text(title, "资源来源标题", max_len=300)
        if source_version < 1:
            raise ValidationAppError("资源来源版本必须从 1 开始")
        return PublicResourceSource(
            source_id=new_id("src"),
            canonical_url=canonical_url.strip(),
            title=title.strip(),
            creator=creator.strip(),
            media_type=media_type.strip() or "course",
            language=language.strip() or "zh",
            source_version=source_version,
            provenance=provenance.strip(),
            checked_at=now or datetime.now(timezone.utc),
        )


@dataclass(frozen=True, slots=True)
class PublicResourceSection:
    """公共资源来源下的一个章节（有序）。

    同一 ``url`` 可被多个章节复用（不同 anchor），因此**无** ``UNIQUE(url)``。
    """

    section_id: str
    source_id: str
    order_index: int
    title: str
    url: str
    anchor: str = ""
    checked_at: datetime | None = None
    verification_status: str = "legacy_index"
    review_note: str = ""

    @staticmethod
    def create(
        *,
        source_id: str,
        order_index: int,
        title: str,
        url: str,
        anchor: str = "",
        now: datetime | None = None,
    ) -> "PublicResourceSection":
        if not source_id:
            raise ValidationAppError("章节必须归属一个资源来源")
        if order_index < 0:
            raise ValidationAppError("章节顺序索引不能为负")
        _require_text(title, "章节标题", max_len=300)
        require_safe_url(url)
        return PublicResourceSection(
            section_id=new_id("sec"),
            source_id=source_id,
            order_index=order_index,
            title=title.strip(),
            url=url.strip(),
            anchor=anchor.strip(),
            checked_at=now or datetime.now(timezone.utc),
        )


# --------------------------------------------------------------------------- 私人计划快照


@dataclass(frozen=True, slots=True)
class StageResourceAssignment:
    """阶段 → 资源分配（私人已发布计划快照的一部分）。

    ``role=PRIMARY`` 表示阶段主线；一个阶段**至多一条** ``PRIMARY``。
    主线章节 ``section_refs`` 必须按原始顺序排列（顺序校验见 ``validate_mainline``）。
    无核验链接时用 ``fallback_search_terms`` 表达搜索建议，**不编造 URL**。

    ``plan_id`` 在**草案阶段为空**（plan 尚未生成），发布时用
    :meth:`bound_to_plan` 绑定到新版本。因此 ``create`` 不要求 plan_id 非空。
    """

    assignment_id: str
    project_id: str
    plan_id: str
    stage_id: str
    role: StageResourceRole
    source_ref: str = ""
    section_refs: tuple[str, ...] = ()
    order_index: int = 0
    source_version: int = 0
    fallback_search_terms: tuple[str, ...] = ()
    snapshot_at: datetime | None = None
    node_ids: tuple[str, ...] = ()

    @staticmethod
    def create(
        *,
        project_id: str,
        stage_id: str,
        role: StageResourceRole,
        plan_id: str = "",
        source_ref: str = "",
        section_refs: tuple[str, ...] = (),
        order_index: int = 0,
        source_version: int = 0,
        fallback_search_terms: tuple[str, ...] = (),
        now: datetime | None = None,
        node_ids: tuple[str, ...] = (),
    ) -> "StageResourceAssignment":
        for name, value in (("project_id", project_id), ("stage_id", stage_id)):
            if not value:
                raise ValidationAppError(f"阶段资源分配缺少 {name}")
        if order_index < 0:
            raise ValidationAppError("阶段资源分配顺序索引不能为负")
        sections = tuple(section_refs)
        if any(not isinstance(s, str) or not s for s in sections):
            raise ValidationAppError("阶段资源分配存在空的章节引用")
        fallback = tuple(t.strip() for t in fallback_search_terms if t and t.strip())
        if role is StageResourceRole.PRIMARY and not sections and not fallback:
            # 主线必须至少给出有序章节，或（索引不可用时）明确的搜索建议。
            raise ValidationAppError("阶段主线必须至少给出有序章节或明确的搜索建议")
        return StageResourceAssignment(
            assignment_id=new_id("asg"),
            project_id=project_id,
            plan_id=plan_id.strip(),
            stage_id=stage_id,
            role=role,
            source_ref=source_ref.strip(),
            section_refs=sections,
            order_index=order_index,
            source_version=source_version,
            fallback_search_terms=fallback,
            snapshot_at=now or datetime.now(timezone.utc),
            node_ids=tuple(node_ids),
        )

    def bound_to_plan(self, plan_id: str) -> "StageResourceAssignment":
        """发布时把草案期的分配绑定到具体 plan 版本。"""
        return replace(self, plan_id=plan_id)


@dataclass(frozen=True, slots=True)
class KnowledgeExtension:
    """阶段预置扩展知识（规划时生成，只作扩展；用户按需外学）。

    设计 §2.1：通用选型视野在**规划时**直接提供 1–2 个扩展主题，
    含学习范围（``concepts``/``guidance``）、已核验链接（``links``）或
    搜索建议（``search_hints``）与工程思考提示（``thinking_prompts``）。

    **不做**覆盖率 / 重复度 / 作者选型分析；``required`` 恒为可选语义。
    """

    extension_id: str
    project_id: str
    plan_id: str
    stage_id: str
    topic: str
    concepts: tuple[str, ...] = ()
    guidance: str = ""
    links: tuple[str, ...] = ()
    search_hints: tuple[str, ...] = ()
    thinking_prompts: tuple[str, ...] = ()
    required: bool = False
    order_index: int = 0
    unit_id: str | None = None

    @staticmethod
    def create(
        *,
        project_id: str,
        stage_id: str,
        topic: str,
        plan_id: str = "",
        concepts: tuple[str, ...] = (),
        guidance: str = "",
        links: tuple[str, ...] = (),
        search_hints: tuple[str, ...] = (),
        thinking_prompts: tuple[str, ...] = (),
        required: bool = False,
        order_index: int = 0,
        unit_id: str | None = None,
    ) -> "KnowledgeExtension":
        for name, value in (("project_id", project_id), ("stage_id", stage_id)):
            if not value:
                raise ValidationAppError(f"扩展知识缺少 {name}")
        _require_text(topic, "扩展主题", max_len=200)
        if order_index < 0:
            raise ValidationAppError("扩展主题顺序索引不能为负")
        # 已核验链接必须通过 URL 安全校验（防 SSRF / 假链接）。
        for link in links:
            require_safe_url(link)
        return KnowledgeExtension(
            extension_id=new_id("ext"),
            project_id=project_id,
            plan_id=plan_id.strip(),
            stage_id=stage_id,
            topic=topic.strip(),
            concepts=tuple(c.strip() for c in concepts if c and c.strip()),
            guidance=guidance.strip(),
            links=tuple(link.strip() for link in links if link and link.strip()),
            search_hints=tuple(h.strip() for h in search_hints if h and h.strip()),
            thinking_prompts=tuple(
                p.strip() for p in thinking_prompts if p and p.strip()
            ),
            required=bool(required),
            order_index=order_index,
            unit_id=unit_id,
        )

    def bound_to_plan(self, plan_id: str) -> "KnowledgeExtension":
        """发布时把草案期的扩展绑定到具体 plan 版本。"""
        return replace(self, plan_id=plan_id)


# --------------------------------------------------------------------------- 确定性校验


def validate_section_selection(
    *,
    source_ref: str,
    section_refs: tuple[str, ...],
    role: StageResourceRole,
    catalog_order: Mapping[str, tuple[str, int]],
) -> list[str]:
    """Validate against the complete author catalog; never reorder selected IDs.

    Author indices may be sparse. PRIMARY is an increasing contiguous interval
    in catalog rank. Other roles retain the user's order and may skip chapters.
    Role alone does not imply required knowledge coverage.
    """
    errors: list[str] = []
    if any(not ref for ref in section_refs):
        errors.append("存在空的章节引用")
    if len(set(section_refs)) != len(section_refs):
        errors.append("章节存在重复引用")
    own = [(key, index) for key, (source, index) in catalog_order.items() if source == source_ref]
    indices = [index for _, index in own]
    if any(type(i) is not int or i < 0 for i in indices) or len(set(indices)) != len(indices):
        errors.append("来源目录章节顺序索引非法或重复")
        return errors
    rank = {key: i for i, (key, _) in enumerate(sorted(own, key=lambda row: row[1]))}
    for ref in section_refs:
        if ref not in catalog_order:
            errors.append(f"章节引用不存在：{ref}")
        elif catalog_order[ref][0] != source_ref:
            errors.append(f"章节 {ref} 不属于来源 {source_ref}")
    if errors:
        return errors
    if role is StageResourceRole.PRIMARY and section_refs:
        selected = [rank[ref] for ref in section_refs]
        if any(right != left + 1 for left, right in zip(selected, selected[1:], strict=False)):
            errors.append("主线章节必须按作者目录顺序连续选择 (source order)")
    return errors


def validate_mainline_continuity(
    assignments: "list[StageResourceAssignment] | tuple[StageResourceAssignment, ...]",
    *,
    known_sections: Mapping[str, PublicResourceSection] | None = None,
) -> list[str]:
    """校验**连续章节顺序**（确定性，不做重复度计算）。

    规则：

    1. 一个阶段**至多一条** ``PRIMARY`` 主线（``MAINLINE_PRIMARY_MAX``）。
    2. 主线 ``section_refs`` 不得为空引用、不得重复。
    3. 同一阶段的补充/对照分配 ``order_index`` 不得重复。

    返回错误列表（空列表表示通过）。
    """
    errors: list[str] = []
    by_stage: dict[str, list[StageResourceAssignment]] = {}
    for assignment in assignments:
        if known_sections is not None and assignment.source_ref:
            errors.extend(validate_section_selection(
                source_ref=assignment.source_ref, section_refs=assignment.section_refs,
                role=assignment.role,
                catalog_order={key: (s.source_id, s.order_index) for key, s in known_sections.items()},
            ))
        by_stage.setdefault(assignment.stage_id, []).append(assignment)

    for stage_id, items in by_stage.items():
        primaries = [a for a in items if a.role is StageResourceRole.PRIMARY]
        if len(primaries) > MAINLINE_PRIMARY_MAX:
            errors.append(
                f"阶段 {stage_id} 存在 {len(primaries)} 条主线，"
                f"每阶段至多 {MAINLINE_PRIMARY_MAX} 条"
            )
        for primary in primaries:
            refs = list(primary.section_refs)
            if any(not ref for ref in refs):
                errors.append(f"阶段 {stage_id} 的主线存在空的章节引用")
            if len(set(refs)) != len(refs):
                errors.append(f"阶段 {stage_id} 的主线章节存在重复引用")
        orders = [a.order_index for a in items]
        if len(set(orders)) != len(orders):
            errors.append(f"阶段 {stage_id} 的资源分配顺序索引重复")
    return errors


def validate_extension_soft_limit(
    extensions: "list[KnowledgeExtension] | tuple[KnowledgeExtension, ...]",
) -> list[str]:
    """每阶段扩展条数**软上限**：超出只警告、不阻断（设计 §2.1）。"""
    warnings: list[str] = []
    by_stage: dict[str, int] = {}
    for extension in extensions:
        by_stage[extension.stage_id] = by_stage.get(extension.stage_id, 0) + 1
    for stage_id, count in by_stage.items():
        if count > EXTENSION_SOFT_LIMIT:
            warnings.append(
                f"阶段 {stage_id} 扩展主题 {count} 项超过建议上限 "
                f"{EXTENSION_SOFT_LIMIT}，建议精简（不阻断发布）"
            )
    return warnings


def validate_extensions(extensions: "list[KnowledgeExtension] | tuple[KnowledgeExtension, ...]") -> list[str]:
    """扩展结构合法性：主题非空、顺序非负、已核验链接安全。"""
    errors: list[str] = []
    seen_orders: dict[str, set[int]] = {}
    for extension in extensions:
        if not extension.topic.strip():
            errors.append("扩展主题不能为空")
        if extension.order_index < 0:
            errors.append(f"扩展 {extension.topic} 的顺序索引不能为负")
        orders = seen_orders.setdefault(extension.stage_id, set())
        if extension.order_index in orders:
            errors.append(
                f"阶段 {extension.stage_id} 的扩展顺序索引重复：{extension.order_index}"
            )
        orders.add(extension.order_index)
        for link in extension.links:
            try:
                require_safe_url(link)
            except ValidationAppError as exc:
                errors.append(f"扩展 {extension.topic} 的链接不安全：{exc.message}")
    return errors


def _require_text(value: str, field: str, *, max_len: int) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValidationAppError(f"{field}不能为空")
    if len(value) > max_len:
        raise ValidationAppError(f"{field}长度不得超过 {max_len} 字符")


# --------------------------------------------------------------------------- 输出前校验
# B2-V §五：公共资源的 ``source_ref`` / ``section_refs`` 在**实际输出前**必须
# 校验「引用存在」且「章节属于对应来源」；没有可用来源时**显式**给出搜索建议，
# **绝不**把未核验的章节当成已核验章节输出。


@dataclass(frozen=True, slots=True)
class ResolvedSection:
    """已确认存在且归属正确的公共资源章节（按作者原有顺序输出）。"""

    section_id: str
    order_index: int
    title: str
    url: str
    anchor: str = ""


@dataclass(frozen=True, slots=True)
class ResolvedAssignment:
    """阶段资源分配的**输出视图**（校验后的结果 + 显式降级说明）。"""

    assignment_id: str
    stage_id: str
    role: StageResourceRole
    source_ref: str
    source_version: int
    sections: tuple[ResolvedSection, ...]
    fallback_search_terms: tuple[str, ...]
    warnings: tuple[str, ...]

    @property
    def degraded(self) -> bool:
        """``True`` 表示无法给出已核验章节，只提供搜索建议。"""
        return bool(self.warnings)


def resolve_assignment_output(
    assignment: StageResourceAssignment,
    *,
    known_sources: Mapping[str, PublicResourceSource],
    known_sections: Mapping[str, PublicResourceSection],
    fallback_hint: str = "",
) -> ResolvedAssignment:
    """把一条阶段资源分配解析为**可安全输出**的视图（B2-V §五）。

    规则（确定性、可单测）：

    1. 无 ``source_ref`` → 不给章节，仅给搜索建议（并记一条显式说明）。
    2. ``source_ref`` 不在公共来源里 → 同上，**不编造**章节。
    3. 章节不存在 → 丢弃并记明；章节存在但属于**别的来源** → 丢弃并记明。
    4. 仅当来源存在且章节归属正确时才输出 ``sections``，且保持原顺序。

    ``fallback_hint``（通常是阶段标题）仅用于在**没有任何搜索建议**时生成
    一条确定性的搜索词——这是「建议」，不是「已核验来源」。
    """
    warnings: list[str] = []
    sections: list[ResolvedSection] = []
    source_ref = assignment.source_ref
    source = known_sources.get(source_ref) if source_ref else None

    if not source_ref:
        warnings.append("未指定已核验资源来源，仅提供搜索建议")
    elif source is None:
        warnings.append(f"引用的资源来源不存在：{source_ref}；已降级为搜索建议")
    elif source.verification_status == "unverified" or (source.verification_status == "reviewed" and source.checked_at is None):
        warnings.append("资源来源未完成内容与索引核对；已降级为搜索建议")
    elif assignment.source_version and assignment.source_version != source.source_version:
        warnings.append("资源版本与已确认索引不一致；已降级为搜索建议")
    else:
        if assignment.role is StageResourceRole.PRIMARY:
            warnings.extend(validate_section_selection(
                source_ref=source_ref, section_refs=assignment.section_refs, role=assignment.role,
                catalog_order={key: (s.source_id, s.order_index) for key, s in known_sections.items()},
            ))
        for ref in assignment.section_refs:
            section = known_sections.get(ref)
            if section is None:
                warnings.append(f"引用的章节不存在：{ref}")
                continue
            if section.source_id != source_ref:
                warnings.append(f"章节 {ref} 不属于来源 {source_ref}")
                continue
            if section.verification_status == "unverified" or (section.verification_status == "reviewed" and section.checked_at is None):
                warnings.append(f"章节未完成内容与索引核对：{ref}")
                continue
            sections.append(
                ResolvedSection(
                    section_id=section.section_id,
                    order_index=section.order_index,
                    title=section.title,
                    url=section.url,
                    anchor=section.anchor,
                )
            )

    fallback = list(assignment.fallback_search_terms)
    if warnings and not fallback and fallback_hint.strip():
        fallback = [f"{fallback_hint.strip()} 入门教程"]
    if warnings and not fallback:
        warnings.append("缺少可用搜索建议，请人工确认资源")

    # A truncated PRIMARY would fabricate a different author interval. Keep
    # honest fallback warnings instead of silently repairing the selected IDs.
    if assignment.role is StageResourceRole.PRIMARY and warnings:
        sections.clear()
    return ResolvedAssignment(
        assignment_id=assignment.assignment_id,
        stage_id=assignment.stage_id,
        role=assignment.role,
        source_ref=source_ref,
        source_version=assignment.source_version,
        sections=tuple(sections),
        fallback_search_terms=tuple(fallback),
        warnings=tuple(warnings),
    )


__all__ = [
    "EXTENSION_SOFT_LIMIT",
    "MAINLINE_PRIMARY_MAX",
    "KnowledgeExtension",
    "PublicResourceSection",
    "PublicResourceSource",
    "ResolvedAssignment",
    "ResolvedSection",
    "StageResourceAssignment",
    "resolve_assignment_output",
    "validate_extension_soft_limit",
    "validate_extensions",
    "validate_mainline_continuity",
    "validate_section_selection",
]
