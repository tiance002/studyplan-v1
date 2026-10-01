"""Scoped complete preference settings and explicit restore-inheritance."""

from app.api.v1.deps import get_auth_context, get_container
from app.api.v1.preference_schemas import (
    PreferenceContextView,
    PreferenceDeleteRequest,
    PreferencePositionRequest,
    PreferencePutRequest,
)
from app.api.v1.routes import ProjectId
from app.application.container import AppContainer
from app.application.resource_preferences import ResourcePreferenceService
from app.core.errors import DependencyUnavailableError
from app.domain.workspace.models import AuthContext
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/api/v1/preferences")


def get_preference_service(container: AppContainer = Depends(get_container)) -> ResourcePreferenceService:
    service = getattr(container, "preference_service", None)
    if service is None:
        raise DependencyUnavailableError("资料偏好服务未装配")
    return service


def target(project_id, body):
    return {"project_id": project_id, **body.model_dump(include={"plan_id", "stage_id", "unit_id", "node_id"})}


@router.get("", response_model=PreferenceContextView, operation_id="get_resource_preferences")
def get_preferences(position: PreferencePositionRequest = Depends(), project_id: str = ProjectId,
                    scope: AuthContext = Depends(get_auth_context),
                    service: ResourcePreferenceService = Depends(get_preference_service)):
    return service.get_context(scope, target(project_id, position))


@router.put("", response_model=PreferenceContextView, operation_id="put_resource_preference")
def put_preference(body: PreferencePutRequest, project_id: str = ProjectId,
                   scope: AuthContext = Depends(get_auth_context),
                   service: ResourcePreferenceService = Depends(get_preference_service)):
    return service.put(scope, target(project_id, body), scope_name=body.scope, mode=body.mode,
                       language=body.language, official_priority=body.official_priority,
                       pace=body.pace, expected_version=body.expected_version)


@router.delete("", response_model=PreferenceContextView, operation_id="restore_resource_preference")
def restore_preference(body: PreferenceDeleteRequest, project_id: str = ProjectId,
                       scope: AuthContext = Depends(get_auth_context),
                       service: ResourcePreferenceService = Depends(get_preference_service)):
    return service.restore(scope, target(project_id, body), scope_name=body.scope,
                           expected_version=body.expected_version)
