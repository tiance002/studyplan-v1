"""图产物 → ``PlanDraft`` 的**唯一**投影（应用层）。

## 为什么单独一层

图 State 是 JSON 可序列化的「生成中间产物」（``outline`` / ``nodes`` /
``units`` / ``relations`` / ``practice_proposal``），**不是**业务实体。
业务实体（``PlanDraft`` / ``PlanRevision``）的构造规则属于领域，
但「把哪段 state 映射到哪个字段」属于**应用编排**，因此放在 application 层。

本模块只做**确定性映射**，不做任何业务校验（校验在
``PlanRevision._validate_structure`` 与 ``validate_plan_structure`` 里，
只有一份）。它也不碰数据库：实体 ID 由 :class:`CatalogIds` 注入。

## 约定（与 Fake LLM / 真实模型输出一致的字段名）

``outline.sections[]``
    ``stable_key`` / ``title`` / ``section_kind`` / ``objective`` /
    ``resources[]`` / ``extensions[]``

``units[]``
    ``stable_key`` / ``title`` / ``section_key`` / ``order_index`` / ``node_keys[]``

``practice_proposal.tasks[]``
    ``stable_key`` / ``title`` / ``goal`` / ``section_key`` / ``order_index`` /
    ``acceptance[]`` / ``knowledge_links[]``（``node_stable_key`` / ``role``）
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from app.core.ids import new_id
from app.domain.enums import OutlineSectionKind, StageResourceRole, TaskKnowledgeRole
from app.domain.planning.guidance import guidance_from_payload
from app.domain.planning.intent import goal_spec_from_payload
from app.domain.planning.models import (
    PlanDraft,
    PlanStage,
    PlanTaskKnowledgeLink,
    PlanTaskLink,
    PlanUnitLink,
)
from app.domain.resources.curation import KnowledgeExtension, StageResourceAssignment
from app.ports.runs import CatalogIds

__all__ = ["project_draft"]


def _text(value: object, default: str = "") -> str:
    return str(value).strip() if value is not None else default


def _dicts(raw: object) -> list[dict[str, object]]:
    if not isinstance(raw, (list, tuple)):
        return []
    return [dict(x) for x in raw if isinstance(x, dict)]


def _as_int(value: object, default: int) -> int:
    """严格取整数：非整数（含 ``bool`` / 浮点 / 数字字符串）一律退回默认值。

    图产物是 JSON 可序列化结构，模型可能给出 ``"3"`` 或 ``3.7``。
    这里不做静默截断——校验层会另行拒绝非法 ``order_index``，
    投影层只需保证自己不会崩。
    """
    if isinstance(value, bool) or not isinstance(value, int):
        return default
    return value


def _str_list(value: object) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    return [str(v).strip() for v in value if str(v).strip()]


def _section_kind(raw: object) -> OutlineSectionKind:
    try:
        return OutlineSectionKind(_text(raw, "core"))
    except ValueError:
        # 未知分节类型退化为 core，而不是让整份草案失败。
        return OutlineSectionKind.CORE


def _role(raw: object) -> StageResourceRole:
    try:
        return StageResourceRole(_text(raw, "primary"))
    except ValueError:
        return StageResourceRole.SUPPLEMENT


def _knowledge_role(raw: object) -> TaskKnowledgeRole:
    try:
        return TaskKnowledgeRole(_text(raw, "core"))
    except ValueError:
        return TaskKnowledgeRole.CORE


def project_draft(
    *,
    project_id: str,
    run_id: str,
    goal_snapshot: str,
    revision_candidate: int,
    state: Mapping[str, Any],
    catalog: CatalogIds,
    draft_id: str | None = None,
    source_pack_key: str = "",
    source_pack_version: int = 0,
) -> PlanDraft:
    """把一次图运行的状态投影为可确认的 ``PlanDraft``。"""
    outline = state.get("outline") or {}
    if not isinstance(outline, Mapping):
        outline = {}
    sections = _dicts(outline.get("sections"))

    stages: list[PlanStage] = []
    stage_by_key: dict[str, PlanStage] = {}
    for order, section in enumerate(sections):
        key = _text(section.get("stable_key")) or f"section_{order}"
        stage = PlanStage.create(
            stable_key=key,
            title=_text(section.get("title"), key),
            section_kind=_section_kind(section.get("section_kind")),
            order_index=order,
            objective=_text(section.get("objective")),
            learning_guidance=guidance_from_payload(section.get("learning_guidance")),
        )
        stages.append(stage)
        stage_by_key[key] = stage

    def _stage_for(section_key: object, fallback_index: int) -> PlanStage | None:
        stage = stage_by_key.get(_text(section_key))
        if stage is not None:
            return stage
        if 0 <= fallback_index < len(stages):
            return stages[fallback_index]
        return None

    unit_links: list[PlanUnitLink] = []
    seen_units: set[str] = set()
    for index, unit in enumerate(_dicts(state.get("units"))):
        unit_key = _text(unit.get("stable_key"))
        unit_id = catalog.unit_ids.get(unit_key)
        if not unit_id or unit_id in seen_units:
            continue
        stage = _stage_for(unit.get("section_key"), index)
        if stage is None:
            continue
        seen_units.add(unit_id)
        unit_links.append(
            PlanUnitLink(
                stage_id=stage.stage_id,
                unit_id=unit_id,
                order_index=_as_int(unit.get("order_index"), len(unit_links)),
            )
        )

    practice = state.get("practice_proposal") or {}
    if not isinstance(practice, Mapping):
        practice = {}
    task_links: list[PlanTaskLink] = []
    task_knowledge: list[PlanTaskKnowledgeLink] = []
    seen_tasks: set[str] = set()
    for index, task in enumerate(_dicts(practice.get("tasks"))):
        task_key = _text(task.get("stable_key"))
        task_id = catalog.task_ids.get(task_key)
        if not task_id or task_id in seen_tasks:
            continue
        stage = _stage_for(task.get("section_key"), len(stages) - 1)
        if stage is None:
            continue
        seen_tasks.add(task_id)
        task_links.append(
            PlanTaskLink(
                stage_id=stage.stage_id,
                task_id=task_id,
                order_index=_as_int(task.get("order_index"), index),
            )
        )
        for link in _dicts(task.get("knowledge_links")):
            node_id = catalog.node_ids.get(_text(link.get("node_stable_key")))
            if not node_id:
                continue
            task_knowledge.append(
                PlanTaskKnowledgeLink(
                    task_id=task_id, node_id=node_id, role=_knowledge_role(link.get("role"))
                )
            )

    stage_resources: list[StageResourceAssignment] = []
    extensions: list[KnowledgeExtension] = []
    for section in sections:
        stage_key = _text(section.get("stable_key"))
        stage = stage_by_key.get(stage_key)
        if stage is None:
            continue
        for order, resource in enumerate(_dicts(section.get("resources"))):
            stage_resources.append(
                StageResourceAssignment.create(
                    project_id=project_id,
                    plan_id="",
                    stage_id=stage.stage_id,
                    role=_role(resource.get("role")),
                    source_ref=_text(resource.get("source_ref")),
                    section_refs=tuple(_str_list(resource.get("section_refs"))),
                    order_index=_as_int(resource.get("order_index"), order),
                    source_version=_as_int(resource.get("source_version"), 0),
                    node_ids=tuple(catalog.node_ids[k] for k in _str_list(resource.get("node_keys")) if k in catalog.node_ids),
                    fallback_search_terms=tuple(
                        _str_list(resource.get("fallback_search_terms"))
                    ),
                )
            )
        for order, extension in enumerate(_dicts(section.get("extensions"))):
            unit_ref = _text(extension.get("unit_ref"))
            unit_id = catalog.unit_ids.get(unit_ref) if unit_ref else None
            extensions.append(
                KnowledgeExtension.create(
                    project_id=project_id,
                    plan_id="",
                    stage_id=stage.stage_id,
                    topic=_text(extension.get("topic")),
                    concepts=tuple(_str_list(extension.get("concepts"))),
                    guidance=_text(extension.get("guidance")),
                    links=tuple(_str_list(extension.get("links"))),
                    search_hints=tuple(_str_list(extension.get("search_hints"))),
                    thinking_prompts=tuple(_str_list(extension.get("thinking_prompts"))),
                    required=bool(extension.get("required", False)),
                    order_index=_as_int(extension.get("order_index"), order),
                    unit_id=unit_id,
                )
            )

    return PlanDraft(
        draft_id=draft_id or new_id("drf"),
        project_id=project_id,
        run_id=run_id,
        goal_snapshot=goal_snapshot,
        goal_spec=goal_spec_from_payload((state.get("manifest") or {}).get("goal_spec")),
        revision_candidate=revision_candidate,
        stages=tuple(stages),
        unit_refs=tuple(unit_ids_sorted(unit_links, catalog)),
        task_refs=tuple(
            sorted(key for key, tid in catalog.task_ids.items() if tid in seen_tasks)
        ),
        node_stable_keys=tuple(sorted(catalog.node_ids)),
        unit_links=tuple(unit_links),
        task_links=tuple(task_links),
        task_knowledge_links=tuple(task_knowledge),
        stage_resources=tuple(stage_resources),
        extensions=tuple(extensions),
        source_pack_key=source_pack_key,
        source_pack_version=source_pack_version,
        practice_project_idea=_text(practice.get("idea")),
    )


def unit_ids_sorted(
    unit_links: Sequence[PlanUnitLink], catalog: CatalogIds
) -> list[str]:
    """按 ``unit_links`` 顺序返回**稳定键**（供审计与局部重规划映射）。"""
    by_id = {v: k for k, v in catalog.unit_ids.items()}
    return [by_id.get(link.unit_id, link.unit_id) for link in unit_links]
