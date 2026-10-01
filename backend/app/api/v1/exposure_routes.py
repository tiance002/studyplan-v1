from typing import Annotated

from app.api.v1.deps import get_auth_context, get_container
from app.api.v1.exposure_schemas import (
    ExposureChangeRequest,
    ExposureChangeView,
    ExposureEventView,
    ExposurePositionRequest,
    ExposureView,
)
from app.api.v1.routes import ProjectId
from app.application.container import AppContainer
from app.application.learning_exposures import LearningExposureService
from app.core.errors import DependencyUnavailableError
from app.domain.learning_exposures import ExposureCommand
from app.domain.workspace.models import AuthContext
from fastapi import APIRouter, Depends, Query

router = APIRouter(prefix="/api/v1/exposures")


def get_exposure_service(container: AppContainer = Depends(get_container)) -> LearningExposureService:
    service = getattr(container, "exposure_service", None)
    if service is None:
        raise DependencyUnavailableError("出现位置进度服务未装配")
    return service


@router.get("", response_model=list[ExposureView], operation_id="list_learning_exposures")
def list_exposures(plan_id: Annotated[str, Query(min_length=1, max_length=512)],
                   stage_id: Annotated[str | None, Query(min_length=1, max_length=512)] = None,
                   project_id: str = ProjectId, scope: AuthContext = Depends(get_auth_context),
                   service: LearningExposureService = Depends(get_exposure_service)):
    return service.list(scope, project_id, plan_id, stage_id)


@router.put("", response_model=ExposureChangeView, operation_id="change_learning_exposure")
def change_exposure(body: ExposureChangeRequest, project_id: str = ProjectId,
                    scope: AuthContext = Depends(get_auth_context),
                    service: LearningExposureService = Depends(get_exposure_service)):
    return service.change(scope, ExposureCommand(project_id=project_id, **body.model_dump()))


@router.get("/history", response_model=list[ExposureEventView], operation_id="get_learning_exposure_history")
def exposure_history(position: ExposurePositionRequest = Depends(), project_id: str = ProjectId,
                     scope: AuthContext = Depends(get_auth_context),
                     service: LearningExposureService = Depends(get_exposure_service)):
    return service.history(scope, project_id, position.plan_id, position.stage_id, position.unit_id)
