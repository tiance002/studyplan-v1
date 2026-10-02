from app.api.v1.deps import get_auth_context, get_container
from app.api.v1.resource_schemas import (
    ManualResourceRequest,
    ResourceInspectionRequest,
    ResourceInspectionView,
    ResourceRemovalView,
    ResourceSearchRequest,
    ResourceSearchView,
    ResourceSelectionRequest,
    ResourceTargetRequest,
    SelectedResourceView,
)
from app.api.v1.routes import ProjectId
from app.application.container import AppContainer
from app.application.learning_resources import LearningResourceService
from app.core.errors import DependencyUnavailableError
from app.domain.workspace.models import AuthContext
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/api/v1/resources")


def get_resource_service(container: AppContainer = Depends(get_container)) -> LearningResourceService:
    if container.resource_service is None:
        raise DependencyUnavailableError("资料服务未装配")
    return container.resource_service


def target(project_id, body):
    return {"project_id": project_id, **body.model_dump(
        include={"plan_id", "stage_id", "unit_id", "node_id"}, exclude_none=True)}


@router.post("/searches", response_model=ResourceSearchView, operation_id="search_learning_resources")
def search_resources(body: ResourceSearchRequest, project_id: str = ProjectId,
                     scope: AuthContext = Depends(get_auth_context),
                     service: LearningResourceService = Depends(get_resource_service)):
    position = target(project_id, body)
    if body.node_id is not None:
        position["node_id"] = body.node_id
    return service.search(scope, position, body.query, body.idempotency_key, source=body.source)


@router.post("/inspections", response_model=ResourceInspectionView, operation_id="inspect_learning_resource")
def inspect_resource(body: ResourceInspectionRequest, project_id: str = ProjectId,
                     scope: AuthContext = Depends(get_auth_context),
                     service: LearningResourceService = Depends(get_resource_service)):
    return service.inspect(scope, target(project_id, body), body.search_id, body.candidate_id,
                           body.idempotency_key, paths=body.paths)


@router.get("/inspections/{inspection_id}", response_model=ResourceInspectionView,
            operation_id="get_resource_inspection")
def get_inspection(inspection_id: str, position: ResourceTargetRequest = Depends(), project_id: str = ProjectId,
                   scope: AuthContext = Depends(get_auth_context),
                   service: LearningResourceService = Depends(get_resource_service)):
    return service.get_inspection(scope, target(project_id, position), inspection_id)


@router.get("/inspections/by-key/{key}", response_model=ResourceInspectionView,
            operation_id="get_resource_inspection_by_key")
def get_inspection_by_key(key: str, position: ResourceTargetRequest = Depends(), project_id: str = ProjectId,
                         scope: AuthContext = Depends(get_auth_context),
                         service: LearningResourceService = Depends(get_resource_service)):
    return service.get_inspection_by_key(scope, target(project_id, position), key)


@router.get("/searches/{search_id}", response_model=ResourceSearchView, operation_id="get_resource_search")
def get_search(search_id: str, position: ResourceTargetRequest = Depends(), project_id: str = ProjectId,
               scope: AuthContext = Depends(get_auth_context),
               service: LearningResourceService = Depends(get_resource_service)):
    return service.get_search(scope, target(project_id, position), search_id)


@router.get("/searches/by-key/{key}", response_model=ResourceSearchView, operation_id="get_resource_search_by_key")
def get_search_by_key(key: str, position: ResourceTargetRequest = Depends(), project_id: str = ProjectId,
                      scope: AuthContext = Depends(get_auth_context),
                      service: LearningResourceService = Depends(get_resource_service)):
    return service.get_search_by_key(scope, target(project_id, position), key)


@router.get("/selections", response_model=list[SelectedResourceView], operation_id="list_selected_resources")
def list_selected(position: ResourceTargetRequest = Depends(), project_id: str = ProjectId,
                  scope: AuthContext = Depends(get_auth_context),
                  service: LearningResourceService = Depends(get_resource_service)):
    return service.list_selected(scope, target(project_id, position))


@router.post("/selections", response_model=SelectedResourceView, operation_id="select_learning_resource")
def select_resource(body: ResourceSelectionRequest, project_id: str = ProjectId,
                    scope: AuthContext = Depends(get_auth_context),
                    service: LearningResourceService = Depends(get_resource_service)):
    return service.select(scope, target(project_id, body), body.search_id, body.candidate_id,
                          module_keys=body.module_keys, chapter_paths=body.chapter_paths, role=body.role)


@router.post("/manual", response_model=SelectedResourceView, operation_id="add_manual_learning_resource")
def manual_resource(body: ManualResourceRequest, project_id: str = ProjectId,
                    scope: AuthContext = Depends(get_auth_context),
                    service: LearningResourceService = Depends(get_resource_service)):
    return service.add_manual(scope, target(project_id, body), body.url, body.title)


@router.delete("/selections/{selection_id}", response_model=ResourceRemovalView, operation_id="remove_learning_resource")
def remove_resource(selection_id: str, position: ResourceTargetRequest = Depends(), project_id: str = ProjectId,
                    scope: AuthContext = Depends(get_auth_context),
                    service: LearningResourceService = Depends(get_resource_service)):
    return {"removed": service.remove(scope, target(project_id, position), selection_id)}
