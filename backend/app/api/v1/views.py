"""领域对象 → ``/api/v1`` DTO 的映射（**唯一**一处）。

放在 API 层是刻意的：领域模型不认识传输格式，DTO 是**对外契约**
（ADR-0004）。把映射集中在这里，可以保证「草案视图」与「正式路线视图」
使用同一套字段规则，不会出现两个端点对同一结构各说各话。
"""

from __future__ import annotations

from typing import Any, Mapping

from app.api.v1.schemas import (
    ErrorBody,
    GoalSpec,
    KnowledgeExtensionView,
    OrderedSection,
    PlanDraftView,
    PlanView,
    RunProgress,
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
    "progress_view",
    "resource_view",
    "run_view",
    "stage_detail",
    "stage_from_dto",
]

#: 运行失败类别 → 面向用户的稳定说明（不回显模型原文，不泄露图内部节点名）。
_RUN_ERROR_MESSAGES: dict[str, str] = {
    "planning_failed": "计划生成未通过校验，可重新发起",
    "provider_dispatch_unknown": "模型调用结果未知，需要核对结果；不会自动再次调用模型",
    "checkpoint_finalize_failed": "业务结果已提交，但断点收尾未确认，需要核对",
    "model_not_configured": "尚未配置可用模型，无法开始生成",
    "run_budget_exhausted": "本次运行已达到冻结的请求/输出预算上限，已停止派发",
    "run_manifest_violation": "执行清单与冻结提交不一致，已拒绝派发",
    "goal_clarification_required": "需要补充信息，请回答本轮问题后明确提交",
    "v2_curriculum_incomplete": "教学安排尚未完整，需处理教材或约束限制后再确认目标",
}

#: 进度阶段闭集；未知值一律回落到 ``outline``，不猜测、不回显原始值。
_PROGRESS_PHASES = frozenset({"outline", "structure", "practice", "validation", "done"})


def progress_view(raw: Mapping[str, Any] | None) -> RunProgress | None:
    """业务进度字典 → ``RunProgress``（仅稳定业务字段）。

    未知阶段回落为 ``outline``，缺失计量保持 ``None``。
    """
    if not raw:
        return None
    phase = str(raw.get("phase") or "")
    index = raw.get("current_stage_index")
    return RunProgress(
        phase=phase if phase in _PROGRESS_PHASES else "outline",  # type: ignore[arg-type]
        current_stage_index=int(index) if index is not None else None,
        current_stage_title=str(raw.get("current_stage_title") or ""),
        total_stages=int(raw.get("total_stages") or 0),
        completed_structure_batches=int(raw.get("completed_structure_batches") or 0),
        total_structure_batches=int(raw.get("total_structure_batches") or 0),
        completed_practice_batches=int(raw.get("completed_practice_batches") or 0),
        total_practice_batches=int(raw.get("total_practice_batches") or 0),
        completed_batches=int(raw.get("completed_batches") or 0),
        request_count=int(raw.get("request_count") or 0),
        max_requests=int(raw.get("max_requests") or 0),
        input_tokens=_optional_int(raw.get("input_tokens")),
        output_tokens=_optional_int(raw.get("output_tokens")),
        usage_complete=bool(raw.get("usage_complete")),
        failure_phase=str(raw.get("failure_phase") or ""),
        failure_stage=str(raw.get("failure_stage") or ""),
    )


def _optional_int(value: Any) -> int | None:
    """缺失保持 ``None``；只有真实数值才转换（绝不用 0 冒充未知）。"""
    return None if value is None else int(value)


def run_view(run: RunRecord, progress: Mapping[str, Any] | None = None, clarification=None, planning_issues=()) -> RunView:
    """运行投影 + 业务进度 → ``RunView``。``result_ref`` 保持不透明。"""
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
        progress=progress_view(progress),
        clarification=clarification,
        planning_issues=list(planning_issues),
    )


def stage_detail(stage: PlanStage) -> StageDetail:
    return StageDetail(
        stage_id=stage.stage_id,
        stable_key=stage.stable_key,
        title=stage.title,
        section_kind=stage.section_kind,
        order_index=stage.order_index,
        objective=stage.objective,
        learning_guidance=stage.learning_guidance,
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
        learning_guidance=dto.learning_guidance,
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
        canonical_url=view.canonical_url,
        node_ids=list(view.node_ids),
        title=view.title,
        media_type=view.media_type,
        language=view.language,
        documentation_version=view.documentation_version,
        verification_status=view.verification_status,
        warnings=list(view.warnings),
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
        goal_spec=GoalSpec.model_validate(draft.goal_spec) if draft.goal_spec else None,
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
        change_preview_id=draft.draft_id if draft.route_change else None,
        v2_content=draft.v2_execution.user_content() if draft.v2_execution else None,
        v2_revision=draft.v2_revision.user_content(execution=draft.v2_execution) if draft.v2_revision else None,
    )


def plan_view(bundle: PlanBundle) -> PlanView:
    """正式版本 + 已核验资源 → ``PlanView``。"""
    revision = bundle.revision
    return PlanView(
        plan_id=revision.plan_id,
        project_id=revision.project_id,
        revision=revision.revision,
        goal_snapshot=revision.goal_snapshot,
        goal_spec=GoalSpec.model_validate(revision.goal_spec) if revision.goal_spec else None,
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
        v2_content=revision.v2_execution.user_content() if revision.v2_execution else None,
        v2_revision=revision.v2_revision.user_content(execution=revision.v2_execution) if revision.v2_revision else None,
    )
