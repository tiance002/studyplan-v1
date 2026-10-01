from app.api.v1.deps import get_auth_context, get_container
from app.api.v1.resource_change_schemas import (
    ResourceCatalogView,
    ResourceChangeDecisionRequest,
    ResourceChangePreviewView,
    ResourceChangeRequest,
    ResourceChangeResultView,
)
from app.api.v1.routes import ProjectId
from app.application.container import AppContainer
from app.application.resource_changes import ResourceChangeService
from app.core.errors import DependencyUnavailableError
from app.domain.resource_changes import ResourceChangeCommand
from app.domain.workspace.models import AuthContext
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/api/v1/resource-changes")


def get_resource_change_service(container: AppContainer = Depends(get_container)) -> ResourceChangeService:
    service = getattr(container, "resource_change_service", None)
    if service is None:
        raise DependencyUnavailableError("受控主线变更服务未装配")
    return service


@router.get("/catalog", response_model=list[ResourceCatalogView], operation_id="list_reviewed_resource_indexes")
def catalog(project_id: str = ProjectId, scope: AuthContext = Depends(get_auth_context),
            service: ResourceChangeService = Depends(get_resource_change_service)):
    return service.catalog(scope, project_id)


@router.post("", response_model=ResourceChangePreviewView, operation_id="preview_resource_change")
def preview(body: ResourceChangeRequest, project_id: str = ProjectId,
            scope: AuthContext = Depends(get_auth_context), service: ResourceChangeService = Depends(get_resource_change_service)):
    values = body.model_dump()
    values["section_refs"] = tuple(values["section_refs"])
    return service.preview(scope, ResourceChangeCommand(project_id=project_id, **values))


@router.get("/{proposal_id}", response_model=ResourceChangePreviewView, operation_id="get_resource_change_preview")
def get_preview(proposal_id: str, project_id: str = ProjectId, scope: AuthContext = Depends(get_auth_context),
                service: ResourceChangeService = Depends(get_resource_change_service)):
    return service.get(scope, project_id, proposal_id)


@router.post("/{proposal_id}/confirm", response_model=ResourceChangeResultView, operation_id="confirm_resource_change")
def confirm(proposal_id: str, body: ResourceChangeDecisionRequest, project_id: str = ProjectId,
            scope: AuthContext = Depends(get_auth_context), service: ResourceChangeService = Depends(get_resource_change_service)):
    return service.decide(scope, project_id, proposal_id, "confirm", **body.model_dump())


@router.post("/{proposal_id}/cancel", response_model=ResourceChangeResultView, operation_id="cancel_resource_change")
def cancel(proposal_id: str, body: ResourceChangeDecisionRequest, project_id: str = ProjectId,
           scope: AuthContext = Depends(get_auth_context), service: ResourceChangeService = Depends(get_resource_change_service)):
    return service.decide(scope, project_id, proposal_id, "cancel", **body.model_dump())
