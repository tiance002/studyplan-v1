from app.api.v1.deps import get_auth_context, get_container
from app.api.v1.practice_change_schemas import (
    PracticeChangeContextView,
    PracticeChangeDecisionRequest,
    PracticeChangePreviewView,
    PracticeChangeRequest,
    PracticeChangeResultView,
)
from app.api.v1.routes import ProjectId
from app.application.container import AppContainer
from app.application.practice_changes import PracticeChangeService
from app.core.errors import DependencyUnavailableError
from app.domain.practice_changes import KnowledgeChoice, PracticeChangeCommand, TaskChange
from app.domain.workspace.models import AuthContext
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/api/v1/practice-changes")


def get_practice_change_service(container: AppContainer = Depends(get_container)) -> PracticeChangeService:
    service = getattr(container, "practice_change_service", None)
    if service is None:
        raise DependencyUnavailableError("受控实践变更服务尚未装配")
    return service


@router.get("/context", response_model=PracticeChangeContextView, operation_id="get_practice_change_context")
def context(
    project_id: str = ProjectId,
    scope: AuthContext = Depends(get_auth_context),
    service: PracticeChangeService = Depends(get_practice_change_service),
):
    return service.context(scope, project_id)


@router.post("", response_model=PracticeChangePreviewView, operation_id="preview_practice_change")
def preview(
    body: PracticeChangeRequest,
    project_id: str = ProjectId,
    scope: AuthContext = Depends(get_auth_context),
    service: PracticeChangeService = Depends(get_practice_change_service),
):
    values = body.model_dump()
    tasks = []
    for data in values.pop("task_changes"):
        data["knowledge_links"] = tuple(KnowledgeChoice(**item) for item in data["knowledge_links"])
        for key in ("in_scope", "out_scope", "acceptance"):
            data[key] = tuple(data[key])
        tasks.append(TaskChange(**data))
    return service.preview(
        scope, PracticeChangeCommand(project_id=project_id, task_changes=tuple(tasks), **values)
    )


@router.get(
    "/{proposal_id}", response_model=PracticeChangePreviewView, operation_id="get_practice_change_preview"
)
def get_preview(
    proposal_id: str,
    project_id: str = ProjectId,
    scope: AuthContext = Depends(get_auth_context),
    service: PracticeChangeService = Depends(get_practice_change_service),
):
    return service.get(scope, project_id, proposal_id)


@router.post(
    "/{proposal_id}/confirm", response_model=PracticeChangeResultView, operation_id="confirm_practice_change"
)
def confirm(
    proposal_id: str,
    body: PracticeChangeDecisionRequest,
    project_id: str = ProjectId,
    scope: AuthContext = Depends(get_auth_context),
    service: PracticeChangeService = Depends(get_practice_change_service),
):
    return service.decide(scope, project_id, proposal_id, "confirm", **body.model_dump())


@router.post(
    "/{proposal_id}/cancel", response_model=PracticeChangeResultView, operation_id="cancel_practice_change"
)
def cancel(
    proposal_id: str,
    body: PracticeChangeDecisionRequest,
    project_id: str = ProjectId,
    scope: AuthContext = Depends(get_auth_context),
    service: PracticeChangeService = Depends(get_practice_change_service),
):
    return service.decide(scope, project_id, proposal_id, "cancel", **body.model_dump())
