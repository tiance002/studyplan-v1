"""``/api/v1`` 业务接口 DTO —— **契约真相源**（ADR-0004）。

本模块只定义**模型**：具体路由由后续 B2-V 实现（Goal §5「可按后续 B2-V
实现具体路由」）。模型一旦进入 ``contracts/openapi.json`` 即成为对外契约，
改动必须同步 `contracts/examples/`、文档与 `frontend/src/api/generated/`。

硬约束（SOFTWARE_DESIGN.md §7 / FRONTEND_HANDOFF.md）：

- **``AuthContext`` 永不出现在任何可写请求体**——它由服务端会话派生。
- 时间一律 **UTC ISO8601**；``null`` 与 ``[]`` 语义分开（缺失用 ``null``，
  空集合用 ``[]``）。
- 业务状态枚举一律**复用** :mod:`app.domain.enums`，不在 DTO 或前端另立一套。
- 前端永不接触 Graph 内部节点名；只消费稳定 ``RunView.status/next_action``。
- 主线资源保留**原有章节顺序**（``ordered_sections``），扩展知识标为可选
  （``required`` 恒为 ``False`` 语义）；**不做**章节重叠率/覆盖率计算。
"""

from __future__ import annotations

from typing import Any, Literal

from app.domain.enums import (
    AiRunNextAction,
    AiRunStatus,
    DraftDecision,
    KnowledgeNodeType,
    OutlineSectionKind,
    PlanDraftStatus,
    PlanRevisionStatus,
    PracticeTaskStatus,
    PreferenceMode,
    PreferenceScope,
    StageResourceRole,
    UnitProgress,
)
from app.domain.planning.guidance import LearningGuidance
from pydantic import BaseModel, ConfigDict, Field

# --------------------------------------------------------------------- 通用信封


class ErrorBody(BaseModel):
    """统一错误视图：``code/message/request_id/details``，不回显敏感输入。

    ``code`` 是一个**稳定**标识：HTTP 响应里取 ``core.errors.ErrorCode``；
    出现在 ``RunView.error`` 里时表示**运行失败类别**（同样是稳定闭集，
    不含图内部节点名）。前端按 ``code`` 分支，**不解析** ``message``。
    """

    model_config = ConfigDict(extra="forbid")

    code: str = Field(..., max_length=64, description="稳定错误码（ErrorCode 或稳定 run error class）")
    message: str = Field(..., max_length=500, description="面向用户的可读信息")
    request_id: str = Field(..., max_length=64)
    details: dict[str, Any] = Field(default_factory=dict)


class PrefsSnapshot(BaseModel):
    """资源偏好快照（请求内联，非独立资源）。"""

    model_config = ConfigDict(extra="forbid")

    mode: PreferenceMode = PreferenceMode.MIXED
    language: str = Field(default="zh", max_length=16)
    official_priority: bool = True
    pace: Literal["slow", "normal", "fast"] = "normal"


# --------------------------------------------------------------------- 运行状态


class RunProgress(BaseModel):
    """一次运行的分批生成**业务进度**（唯一可授权给前端的进度视图）。

    只包含稳定业务字段：阶段、当前阶段位置、已完成批次数、冻结的请求上限、
    以及由付费账本汇总的计量。**不含** thread_id、图节点名、内部 checkpoint
    或模型提示词。

    计量缺失时 ``input_tokens`` / ``output_tokens`` 保持 ``null``，
    ``usage_complete`` 说明当前合计是否覆盖全部已记录请求 —— 绝不用 0 冒充未知。
    """

    model_config = ConfigDict(extra="forbid")

    phase: Literal["outline", "structure", "practice", "validation", "done"]
    current_stage_index: int | None = Field(default=None, ge=0)
    current_stage_title: str = Field(default="", max_length=200)
    total_stages: int = Field(default=0, ge=0)
    completed_structure_batches: int = Field(default=0, ge=0)
    total_structure_batches: int = Field(default=0, ge=0)
    completed_practice_batches: int = Field(default=0, ge=0)
    total_practice_batches: int = Field(default=0, ge=0)
    completed_batches: int = Field(default=0, ge=0)
    request_count: int = Field(default=0, ge=0)
    max_requests: int = Field(default=0, ge=0)
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    usage_complete: bool = False
    failure_phase: str = Field(default="", max_length=32)
    failure_stage: str = Field(default="", max_length=128)


class RunView(BaseModel):
    """对外运行状态投影（**唯一**可授权给前端的运行视图）。

    ``status`` 成功 **不自动等于** 知识已学会/任务已验收。
    ``result_ref`` 是不透明引用；前端不得解析其内部结构。
    """

    run_id: str = Field(..., max_length=64)
    status: AiRunStatus
    next_action: AiRunNextAction
    version: int = Field(..., ge=1, description="乐观并发版本号")
    result_ref: str | None = Field(default=None, max_length=128)
    error: ErrorBody | None = None
    progress: RunProgress | None = Field(
        default=None, description="分批生成业务进度；未发布过进度的运行（如旧版）为 null"
    )


class PlanGenerateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    goal: str = Field(..., min_length=1, max_length=2000)
    prefs_snapshot: PrefsSnapshot = Field(default_factory=PrefsSnapshot)


class PlanGenerateResponse(BaseModel):
    """202 响应：只返回运行句柄，不返回草案内容。"""

    run_id: str = Field(..., max_length=64)
    status_url: str = Field(..., max_length=200)


# ------------------------------------------------------------------- 计划结构


class StageDetail(BaseModel):
    """阶段详情（前端「阶段导航」直接消费）。"""

    stage_id: str = Field(..., max_length=64)
    stable_key: str = Field(..., max_length=128)
    title: str = Field(..., max_length=200)
    section_kind: OutlineSectionKind
    order_index: int = Field(..., ge=0)
    objective: str = Field(default="", max_length=1000)
    learning_guidance: LearningGuidance | None = None


class OrderedSection(BaseModel):
    """主线资源的**有序章节**（保留作者原有章节顺序）。"""

    section_id: str = Field(..., max_length=64)
    order_index: int = Field(..., ge=0)
    title: str = Field(..., max_length=300)
    url: str = Field(..., max_length=2000)
    anchor: str = Field(default="", max_length=200)


class StageResourceAssignmentView(BaseModel):
    """阶段 → 资源分配。``role=primary`` 表示该阶段主线。

    ``ordered_sections`` 保持原始顺序；无核验链接时用
    ``fallback_search_terms`` 给出搜索建议，**绝不编造 URL**。
    """

    assignment_id: str = Field(..., max_length=64)
    stage_id: str = Field(..., max_length=64)
    role: StageResourceRole
    creator: str = Field(default="", max_length=200, description="主线作者/机构")
    source_ref: str = Field(default="", max_length=64, description="公共资源来源 source_id")
    source_version: int = Field(default=0, ge=0)
    ordered_sections: list[OrderedSection] = Field(default_factory=list)
    fallback_search_terms: list[str] = Field(default_factory=list)
    node_ids: list[str] = Field(default_factory=list)
    title: str = ""
    media_type: str = ""
    language: str = ""
    documentation_version: str = ""
    verification_status: str = "unverified"
    warnings: list[str] = Field(default_factory=list)


class KnowledgeExtensionView(BaseModel):
    """阶段预置扩展知识（默认 1–2 项，**可选**，不强制完成）。"""

    extension_id: str = Field(..., max_length=64)
    stage_id: str = Field(..., max_length=64)
    topic: str = Field(..., max_length=200)
    concepts: list[str] = Field(default_factory=list)
    guidance: str = Field(default="", max_length=1000)
    links: list[str] = Field(default_factory=list, description="已核验链接（可能为空）")
    search_hints: list[str] = Field(default_factory=list, description="无核验链接时的搜索建议")
    thinking_prompts: list[str] = Field(default_factory=list, description="工程思考提示")
    required: bool = Field(default=False, description="V1 恒为可选语义")
    order_index: int = Field(default=0, ge=0)


class UnitLinkView(BaseModel):
    stage_id: str = Field(..., max_length=64)
    unit_id: str = Field(...)
    order_index: int = Field(..., ge=0)


class TaskLinkView(BaseModel):
    stage_id: str = Field(..., max_length=64)
    task_id: str = Field(...)
    order_index: int = Field(..., ge=0)


class PlanSnapshot(BaseModel):
    """**完整版本快照**：阶段 + 单元/任务链接 + 主线资源 + 扩展知识。

    草案视图（``PlanDraftView``）与已发布视图（``PlanView``）共用本结构，
    保证「用户确认的结构」与「发布的结构」字段一致。
    """

    project_id: str = Field(..., max_length=64)
    revision: int = Field(..., ge=1)
    goal_snapshot: str = Field(..., max_length=2000)
    stages: list[StageDetail] = Field(default_factory=list)
    unit_links: list[UnitLinkView] = Field(default_factory=list)
    task_links: list[TaskLinkView] = Field(default_factory=list)
    stage_resources: list[StageResourceAssignmentView] = Field(default_factory=list)
    extensions: list[KnowledgeExtensionView] = Field(default_factory=list)
    source_pack_key: str = Field(default="", max_length=128)
    source_pack_version: int = Field(default=0, ge=0)


class PlanDraftView(PlanSnapshot):
    """草案视图。``draft_hash`` 必须原样回传用于确认校验。"""

    draft_id: str = Field(..., max_length=64)
    status: PlanDraftStatus
    draft_hash: str = Field(..., max_length=128, description="确认时原样回传，防确认期间被改写")
    version: int = Field(..., ge=0)
    validation_warnings: list[str] = Field(default_factory=list)


class PlanView(PlanSnapshot):
    """已确认路线视图（当前版本或历史版本）。"""

    plan_id: str = Field(..., max_length=64)
    status: PlanRevisionStatus
    version: int = Field(..., ge=1)
    approved_at: str | None = Field(default=None, description="UTC ISO8601")


class DraftDecisionRequest(BaseModel):
    """approve / edit / cancel。**非法或缺失决定一律失败，绝不默认 approve。**"""

    model_config = ConfigDict(extra="forbid")

    decision: DraftDecision
    expected_version: int = Field(
        ...,
        ge=0,
        description=(
            "**当前正式路线**的版本号（尚无正式路线时为 0）。"
            "用于乐观并发：期间若已有其它发布，本次确认返回 409。"
        ),
    )
    draft_hash: str = Field(
        default="", max_length=128, description="approve / edit 时必填：原样回传加载到的草案哈希"
    )
    idempotency_key: str = Field(
        default="", max_length=200, description="approve 时必填：重复确认返回同一结果"
    )
    edited_stages: list[StageDetail] | None = Field(
        default=None, description="decision=edit 时必填（完整结构，不允许只回 draft_ref）"
    )


class PlanDecisionResponse(BaseModel):
    """一次决定的处理结果：更新后的草案 + （确认时）发布出的正式路线。

    三种决定的形状一致，便于前端用同一段代码更新界面：

    - ``approve``：``draft.status=approved``，``plan`` 为当前正式路线；
    - ``edit``：``draft.status=awaiting_approval``（已重新校验），``plan`` 为 ``null``；
    - ``cancel``：``draft.status=cancelled``，``plan`` 为 ``null``。
    """

    run_id: str = Field(..., max_length=64)
    draft: PlanDraftView
    plan: PlanView | None = None


# ------------------------------------------------------------------ 知识与单元


class NodeView(BaseModel):
    """知识卡片。``source_status`` 如实区分 AI 草稿与已验证来源。"""

    node_id: str = Field(...)
    stable_key: str = Field(..., max_length=128)
    title: str = Field(..., max_length=200)
    node_type: KnowledgeNodeType
    objectives: list[str] = Field(default_factory=list)
    source_status: str = Field(..., max_length=32)


class UnitView(BaseModel):
    unit_id: str = Field(...)
    stable_key: str = Field(..., max_length=128)
    title: str = Field(..., max_length=200)
    objectives: list[str] = Field(default_factory=list)
    rubric_version: int = Field(..., ge=1)
    progress: UnitProgress = UnitProgress.NOT_STARTED


class ProgressPatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: UnitProgress
    expected_version: int = Field(..., ge=1)


class WorkspaceNodeView(NodeView):
    prerequisite_ids: list[str] = Field(default_factory=list)
    child_ids: list[str] = Field(default_factory=list)
    progress: UnitProgress | None = None


class WorkspaceUnitView(UnitView):
    node_ids: list[str] = Field(default_factory=list)
    progress_recorded: bool = False
    exposure_id: str | None = None
    exposure_version: int = Field(default=0, ge=0)
    legacy_progress: UnitProgress | None = None


class PreferenceView(BaseModel):
    scope: PreferenceScope
    scope_ref: str = Field(...)
    mode: PreferenceMode
    language: str = Field(..., max_length=16)
    official_priority: bool
    pace: str = Field(..., max_length=16)
    version: int = Field(..., ge=1)


class PreferenceUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scope: PreferenceScope
    scope_ref: str = Field(...)
    mode: PreferenceMode
    language: str = Field(default="zh", max_length=16)
    official_priority: bool = True
    pace: Literal["slow", "normal", "fast"] = "normal"
    expected_version: int = Field(default=0, ge=0)


# --------------------------------------------------------------------- 实践工作台


class PracticeTaskView(BaseModel):
    """实践任务。``thinking_prompts`` 在实践工作台重点展示。

    ``acceptance`` 必填：没有「怎样算完成」的任务无法验收。
    """

    task_id: str = Field(...)
    practice_project_id: str = Field(...)
    stable_key: str = Field(..., max_length=128)
    title: str = Field(..., max_length=200)
    goal: str = Field(..., max_length=2000)
    in_scope: list[str] = Field(default_factory=list)
    out_scope: list[str] = Field(default_factory=list)
    acceptance: list[str] = Field(..., min_length=1)
    status: PracticeTaskStatus
    thinking_prompts: list[str] = Field(default_factory=list)


class StageCompletionView(BaseModel):
    status: Literal["completed", "incomplete"] = "incomplete"
    summary_completed: bool = False
    completed_practice_tasks: int = Field(default=0, ge=0)
    total_practice_tasks: int = Field(default=0, ge=0)


class StageWorkspaceView(BaseModel):
    stage: StageDetail
    units: list[WorkspaceUnitView]
    nodes: list[WorkspaceNodeView]
    resources: list[StageResourceAssignmentView]
    tasks: list[PracticeTaskView]
    completion: StageCompletionView = Field(default_factory=StageCompletionView)


class LearningWorkspaceView(BaseModel):
    plan: PlanView
    stages: list[StageWorkspaceView]
    completed_units: int
    total_units: int
    completed_stages: int = Field(default=0, ge=0)
    total_stages: int = Field(default=0, ge=0)


class SummaryCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(..., min_length=1, max_length=40000)
    idempotency_key: str = Field(..., min_length=1, max_length=200)


class PromptRevisionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_draft: str = Field(..., min_length=1, max_length=40000)
    idempotency_key: str = Field(..., min_length=1, max_length=200)


#: 注册进 OpenAPI ``components.schemas`` 的 DTO 闭集。
#: 顺序不影响结果；新增 DTO 必须加入此元组，否则不会出现在导出契约里。
V1_SCHEMAS: tuple[type[BaseModel], ...] = (
    ErrorBody,
    PrefsSnapshot,
    RunProgress,
    RunView,
    PlanGenerateRequest,
    PlanGenerateResponse,
    StageDetail,
    OrderedSection,
    StageResourceAssignmentView,
    KnowledgeExtensionView,
    UnitLinkView,
    TaskLinkView,
    PlanSnapshot,
    PlanDraftView,
    PlanView,
    DraftDecisionRequest,
    PlanDecisionResponse,
    NodeView,
    UnitView,
    ProgressPatchRequest,
    PreferenceView,
    PreferenceUpdateRequest,
    PracticeTaskView,
    StageCompletionView,
    SummaryCreateRequest,
    PromptRevisionCreateRequest,
)

__all__ = [cls.__name__ for cls in V1_SCHEMAS] + ["V1_SCHEMAS"]
