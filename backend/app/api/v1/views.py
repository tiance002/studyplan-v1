"""领域对象 → ``/api/v1`` DTO 的映射（**唯一**一处）。

放在 API 层是刻意的：领域模型不认识传输格式，DTO 是**对外契约**
（ADR-0004）。把映射集中在这里，可以保证「草案视图」与「正式路线视图」
使用同一套字段规则，不会出现两个端点对同一结构各说各话。
"""

from __future__ import annotations

from app.api.v1.schemas import (
    ErrorBody,
    KnowledgeExtensionView,
    OrderedSection,
    PlanDraftView,
    PlanView,
    RunView,
    StageDetail,
    StageResourceAssignmentView,
    TaskLinkView,
    UnitLinkView,
)
from app.application.plan_resources import StageResourceView
from app.application.plan_service import DraftBundle, PlanBundle
from app.core.request_context import get_request_id
from app.domain.planning.models import PlanStage
from app.domain.resources.curation import KnowledgeExtension
from app.domain.runs.models import RunRecord

__all__ = [
    "draft_view",
    "extension_view",
    "plan_view",
    "resource_view",
    "run_view",
    "stage_detail",
    "stage_from_dto",
]

#: 运行失败类别 → 面向用户的稳定说明（不回显模型原文，不泄露图内部节点名）。
_RUN_ERROR_MESSAGES: dict[str, str] = {
    "planning_failed": "计划生成未通过校验，可重新发起",
    "run_interrupted": "生成运行已中断或超时，需要核对结果；不会自动再次调用模型",
}


def run_view(run: RunRecord) -> RunView:
    """运行投影 → ``RunView``。``result_ref`` 保持不透明。"""
    error: ErrorBody | None = None
    if run.error_class:
        error = ErrorBody(
            code=run.error_class,
            message=_RUN_ERROR_MESSAGES.get(run.error_class, "运行未成功完成，可重试"),
            request_id=get_request_id(),
            details={},
        )
    return RunView(
        run_id=run.run_id,
        status=run.status,
        next_action=run.next_action,
        version=run.version,
        result_ref=run.result_ref,
        error=error,
    )


def stage_detail(stage: PlanStage) -> StageDetail:
    return StageDetail(
        stage_id=stage.stage_id,
        stable_key=stage.stable_key,
        title=stage.title,
        section_kind=stage.section_kind,
        order_index=stage.order_index,
        objective=stage.objective,
    )


def stage_from_dto(dto: StageDetail) -> PlanStage:
    """把编辑请求里的阶段还原为领域对象（``stable_key`` 由草案决定，见路由）。"""
    return PlanStage(
        stage_id=dto.stage_id,
        stable_key=dto.stable_key,
        title=dto.title,
        section_kind=dto.section_kind,
        order_index=dto.order_index,
        objective=dto.objective,
    )


def resource_view(view: StageResourceView) -> StageResourceAssignmentView:
    """已核验资源视图 → DTO。无核验章节时**只**给搜索建议。"""
    return StageResourceAssignmentView(
        assignment_id=view.assignment_id,
        stage_id=view.stage_id,
        role=view.role,
        creator=view.creator,
        source_ref=view.source_ref,
        source_version=view.source_version,
        ordered_sections=[
            OrderedSection(
                section_id=s.section_id,
                order_index=s.order_index,
                title=s.title,
                url=s.url,
                anchor=s.anchor,
            )
            for s in view.ordered_sections
        ],
        fallback_search_terms=list(view.fallback_search_terms),
    )


def extension_view(extension: KnowledgeExtension) -> KnowledgeExtensionView:
    return KnowledgeExtensionView(
        extension_id=extension.extension_id,
        stage_id=extension.stage_id,
        topic=extension.topic,
        concepts=list(extension.concepts),
        guidance=extension.guidance,
        links=list(extension.links),
        search_hints=list(extension.search_hints),
        thinking_prompts=list(extension.thinking_prompts),
        required=extension.required,
        order_index=extension.order_index,
    )


def draft_view(bundle: DraftBundle) -> PlanDraftView:
    """草案 + 已核验资源 → ``PlanDraftView``。"""
    draft = bundle.draft
    return PlanDraftView(
        draft_id=draft.draft_id,
        project_id=draft.project_id,
        revision=draft.revision_candidate,
        goal_snapshot=draft.goal_snapshot,
        stages=[stage_detail(s) for s in draft.stages],
        unit_links=[
            UnitLinkView(
                stage_id=link.stage_id, unit_id=link.unit_id, order_index=link.order_index
            )
            for link in draft.unit_links
        ],
        task_links=[
            TaskLinkView(
                stage_id=link.stage_id, task_id=link.task_id, order_index=link.order_index
            )
            for link in draft.task_links
        ],
        stage_resources=[resource_view(r) for r in bundle.resources],
        extensions=[extension_view(e) for e in draft.extensions],
        source_pack_key=draft.source_pack_key,
        source_pack_version=draft.source_pack_version,
        status=draft.status,
        draft_hash=draft.content_hash,
        version=draft.revision_candidate,
        validation_warnings=list(draft.validation_warnings),
    )


def plan_view(bundle: PlanBundle) -> PlanView:
    """正式版本 + 已核验资源 → ``PlanView``。"""
    revision = bundle.revision
    return PlanView(
        plan_id=revision.plan_id,
        project_id=revision.project_id,
        revision=revision.revision,
        goal_snapshot=revision.goal_snapshot,
        stages=[stage_detail(s) for s in revision.stages],
        unit_links=[
            UnitLinkView(
                stage_id=link.stage_id, unit_id=link.unit_id, order_index=link.order_index
            )
            for link in revision.unit_links
        ],
        task_links=[
            TaskLinkView(
                stage_id=link.stage_id, task_id=link.task_id, order_index=link.order_index
            )
            for link in revision.task_links
        ],
        stage_resources=[resource_view(r) for r in bundle.resources],
        extensions=[extension_view(e) for e in revision.extensions],
        source_pack_key=revision.source_pack_key,
        source_pack_version=revision.source_pack_version,
        status=revision.status,
        version=revision.version,
        approved_at=revision.approved_at.isoformat() if revision.approved_at else None,
    )
