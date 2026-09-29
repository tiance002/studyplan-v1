from app.api.v1.deps import get_auth_context, get_container, get_plan_service
from app.api.v1.routes import ProjectId
from app.api.v1.schemas import LearningWorkspaceView, StageWorkspaceView
from app.api.v1.views import plan_view
from app.application.container import AppContainer
from app.application.plan_service import PlanService
from app.core.errors import DependencyUnavailableError, NotFoundError
from app.domain.workspace.models import AuthContext
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/api/v1")


@router.get("/workspace", response_model=LearningWorkspaceView, operation_id="get_learning_workspace")
def workspace(
    project_id: str = ProjectId,
    scope: AuthContext = Depends(get_auth_context),
    service: PlanService = Depends(get_plan_service),
    container: AppContainer = Depends(get_container),
):
    scope.require_project(project_id)
    if container.workspace_reader is None:
        raise DependencyUnavailableError("工作区查询未装配")
    bundle = service.get_current(scope=scope, project_id=project_id)
    if bundle is None:
        raise NotFoundError("请先创建并确认学习计划")
    plan = plan_view(bundle)
    data = container.workspace_reader.read(
        scope, project_id, [u.unit_id for u in plan.unit_links], [t.task_id for t in plan.task_links]
    )
    stages = []
    for stage in plan.stages:
        ids = [u.unit_id for u in plan.unit_links if u.stage_id == stage.stage_id]
        tasks = [t.task_id for t in plan.task_links if t.stage_id == stage.stage_id]
        units = [u for u in data["units"] if u["unit_id"] in ids]
        node_ids = {n for u in units for n in u["node_ids"]}
        stages.append(
            StageWorkspaceView(
                stage=stage,
                units=units,
                nodes=[n for n in data["nodes"] if n["node_id"] in node_ids],
                resources=[r for r in plan.stage_resources if r.stage_id == stage.stage_id],
                tasks=[t for t in data["tasks"] if t["task_id"] in tasks],
            )
        )
    return LearningWorkspaceView(
        plan=plan,
        stages=stages,
        total_units=len(data["units"]),
        completed_units=sum(u["progress"] == "completed" for u in data["units"]),
    )
