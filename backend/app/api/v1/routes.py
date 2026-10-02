"""``/api/v1`` 业务路由（B2-V §六）：**最薄但真实**的业务 HTTP 链路。

    POST /api/v1/plans/generate                    发起规划（Fake LLM + 真实 PG）
    GET  /api/v1/runs/{run_id}                     运行状态投影
    GET  /api/v1/plans/drafts/{draft_id}           草案（含已核验资源）
    POST /api/v1/plans/drafts/{draft_id}/decision  approve / edit / cancel
    GET  /api/v1/plans/current                     当前正式路线

## 两条硬约束（Goal §六）

1. **授权来自服务端会话**：``AuthContext`` 由 :func:`get_auth_context` 从
   Cookie 令牌派生；请求体里没有、也不会被读取 ``actor_id`` / ``tenant_id`` /
   项目范围。
2. **先鉴权再访问仓储**：每个端点先 ``scope.require_project(project_id)``，
   只有项目属于会话范围才调用 :class:`PlanService`（进而访问 PG 仓储）。

``project_id`` 通过查询参数显式传入，并且**必须**落在会话的项目范围内，
否则 403 —— 传一个不属于自己的项目不会获得任何数据。
"""

from __future__ import annotations

from urllib.parse import quote, urlencode

from app.api.v1.deps import get_auth_context, get_plan_service
from app.api.v1.schemas import (
    DraftDecisionRequest,
    PlanDecisionResponse,
    PlanDraftView,
    PlanGenerateRequest,
    PlanGenerateResponse,
    PlanView,
    RunView,
)
from app.api.v1.views import (
    draft_view,
    plan_view,
    run_view,
    stage_from_dto,
)
from app.application.plan_service import DecisionCommand, DraftBundle, PlanBundle, PlanService
from app.core.errors import NotFoundError
from app.domain.planning.intent import goal_spec_from_payload
from app.domain.workspace.models import AuthContext
from fastapi import APIRouter, Depends, Query, status

__all__ = ["router"]

API_PREFIX = "/api/v1"

router = APIRouter(prefix=API_PREFIX)

#: 项目查询参数的统一声明（显式、受校验，不是"任意项目授权"）。
ProjectId = Query(
    ...,
    min_length=1,
    max_length=64,
    description="学习空间 ID；必须属于当前会话的项目范围，否则 403",
)


@router.post(
    "/plans/generate",
    response_model=PlanGenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    operation_id="generate_plan",
    summary="发起一次规划生成",
)
def generate_plan(
    payload: PlanGenerateRequest,
    project_id: str = ProjectId,
    scope: AuthContext = Depends(get_auth_context),
    service: PlanService = Depends(get_plan_service),
) -> PlanGenerateResponse:
    """发起规划。返回 ``run_id``；草案内容通过 ``GET /runs/{run_id}`` 与
    ``GET /plans/drafts/{draft_id}`` 获取（本响应**不**回显草案）。"""
    run_id = service.submit_generation(
        scope=scope,
        project_id=project_id,
        goal=payload.goal,
        goal_spec=goal_spec_from_payload(payload.goal_spec.model_dump(mode="json")) if payload.goal_spec else None,
        prefs_snapshot=(payload.prefs_snapshot.model_dump(mode="json")
                        if "prefs_snapshot" in payload.model_fields_set else None),
    )
    return PlanGenerateResponse(
        run_id=run_id,
        status_url=f"{API_PREFIX}/runs/{quote(run_id, safe='')}?{urlencode({'project_id': project_id})}",
    )


@router.get(
    "/runs",
    response_model=list[RunView],
    operation_id="list_planning_runs",
    summary="读取当前账户与学习空间最近的规划运行",
)
def list_runs(
    project_id: str = ProjectId,
    limit: int = Query(default=10, ge=1, le=20),
    scope: AuthContext = Depends(get_auth_context),
    service: PlanService = Depends(get_plan_service),
) -> list[RunView]:
    """只读列表；不会恢复图、领取任务或重派模型。进度通过所选运行单独读取。"""
    return [run_view(run) for run in service.list_runs(scope=scope, project_id=project_id, limit=limit)]


@router.get(
    "/runs/{run_id}",
    response_model=RunView,
    operation_id="get_run",
    summary="读取运行状态投影",
)
def get_run(
    run_id: str,
    project_id: str = ProjectId,
    scope: AuthContext = Depends(get_auth_context),
    service: PlanService = Depends(get_plan_service),
) -> RunView:
    """对外运行状态：``status`` / ``next_action`` / ``result_ref``（不透明）
    以及分批生成的业务进度 ``progress``（无图内部字段）。"""
    bundle = service.get_run(scope=scope, project_id=project_id, run_id=run_id)
    return run_view(bundle.run, bundle.progress)


@router.get(
    "/plans/drafts/{draft_id}",
    response_model=PlanDraftView,
    operation_id="get_plan_draft",
    summary="读取草案（含已核验资源）",
)
def get_plan_draft(
    draft_id: str,
    project_id: str = ProjectId,
    scope: AuthContext = Depends(get_auth_context),
    service: PlanService = Depends(get_plan_service),
) -> PlanDraftView:
    """草案完整结构 + ``draft_hash``（确认时原样回传）。

    资源引用会在此**实际输出前**校验：核验失败的条目只给搜索建议，
    **绝不**编造已核验章节（B2-V §五）。
    """
    bundle = service.get_draft(scope=scope, project_id=project_id, draft_id=draft_id)
    return draft_view(bundle)


@router.post(
    "/plans/drafts/{draft_id}/decision",
    response_model=PlanDecisionResponse,
    operation_id="decide_plan_draft",
    summary="确认 / 编辑 / 取消草案",
)
def decide_plan_draft(
    draft_id: str,
    payload: DraftDecisionRequest,
    project_id: str = ProjectId,
    scope: AuthContext = Depends(get_auth_context),
    service: PlanService = Depends(get_plan_service),
) -> PlanDecisionResponse:
    """处理用户在等待确认处的决定。

    - ``approve``：单事务发布（幂等；重复确认返回**同一结果**，不产生第二份计划）；
    - ``edit``：应用编辑并**重新校验**，保存新草案（不发布）；
    - ``cancel``：状态条件取消（已发布的草案不会被取消）。
    """
    command = DecisionCommand(
        decision=payload.decision,
        expected_version=payload.expected_version,
        draft_hash=payload.draft_hash,
        idempotency_key=payload.idempotency_key,
        edited_stages=(
            tuple(stage_from_dto(s) for s in payload.edited_stages)
            if payload.edited_stages is not None
            else None
        ),
    )
    outcome = service.decide(
        scope=scope, project_id=project_id, draft_id=draft_id, command=command
    )
    plan = (
        plan_view(PlanBundle(revision=outcome.plan, resources=outcome.plan_resources))
        if outcome.plan is not None
        else None
    )
    return PlanDecisionResponse(
        run_id=outcome.run_id,
        draft=draft_view(DraftBundle(draft=outcome.draft, resources=outcome.resources)),
        plan=plan,
    )


@router.get(
    "/plans/current",
    response_model=PlanView,
    operation_id="get_current_plan",
    summary="读取当前正式路线",
)
def get_current_plan(
    project_id: str = ProjectId,
    scope: AuthContext = Depends(get_auth_context),
    service: PlanService = Depends(get_plan_service),
) -> PlanView:
    """当前**已确认**的路线。没有正式路线时 404（而不是返回空计划）。"""
    bundle = service.get_current(scope=scope, project_id=project_id)
    if bundle is None:
        raise NotFoundError("当前没有已确认的路线")
    return plan_view(bundle)
