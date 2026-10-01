from typing import Annotated

from app.api.v1.deps import get_auth_context, get_container
from app.api.v1.prompt_schemas import (
    PromptCancelRequest,
    PromptExportRequest,
    PromptExportView,
    PromptHistoryView,
    PromptReviewRequest,
    PromptReviewRunView,
    PromptRevisionView,
    PromptSaveRequest,
    PromptSaveView,
    PromptThreadView,
)
from app.api.v1.routes import ProjectId
from app.application.container import AppContainer
from app.application.prompts import PromptService
from app.core.errors import DependencyUnavailableError
from app.domain.prompts import PromptSaveCommand
from app.domain.workspace.models import AuthContext
from fastapi import APIRouter, Depends, Query

router = APIRouter(prefix="/api/v1/prompts")


def get_prompt_service(container: AppContainer = Depends(get_container)) -> PromptService:
    service = getattr(container, "prompt_service", None)
    if service is None:
        raise DependencyUnavailableError("Prompt 服务尚未装配")
    return service


@router.get("", response_model=PromptThreadView, operation_id="get_prompt_thread")
def get_thread(
    plan_id: Annotated[str, Query(min_length=1, max_length=512)],
    stage_id: Annotated[str, Query(min_length=1, max_length=512)],
    task_id: Annotated[str, Query(min_length=1, max_length=512)],
    project_id: str = ProjectId,
    scope: AuthContext = Depends(get_auth_context),
    service: PromptService = Depends(get_prompt_service),
):
    return service.thread(scope, project_id, plan_id, stage_id, task_id)


@router.post("", response_model=PromptSaveView, operation_id="save_prompt_original")
def save_original(
    body: PromptSaveRequest,
    project_id: str = ProjectId,
    scope: AuthContext = Depends(get_auth_context),
    service: PromptService = Depends(get_prompt_service),
):
    return service.save(scope, PromptSaveCommand(project_id=project_id, **body.model_dump()))


@router.get("/history", response_model=PromptHistoryView, operation_id="get_prompt_history")
def get_history(
    cursor: Annotated[str | None, Query(max_length=1024)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    project_id: str = ProjectId,
    scope: AuthContext = Depends(get_auth_context),
    service: PromptService = Depends(get_prompt_service),
):
    return service.history(scope, project_id, cursor, limit)


@router.get("/revisions/{revision_id}", response_model=PromptRevisionView, operation_id="get_prompt_revision")
def get_revision(
    revision_id: str,
    project_id: str = ProjectId,
    scope: AuthContext = Depends(get_auth_context),
    service: PromptService = Depends(get_prompt_service),
):
    return service.revision(scope, project_id, revision_id)


@router.post(
    "/revisions/{revision_id}/review",
    response_model=PromptReviewRunView,
    status_code=202,
    operation_id="request_prompt_review",
)
def review_attempt(
    revision_id: str,
    body: PromptReviewRequest,
    project_id: str = ProjectId,
    scope: AuthContext = Depends(get_auth_context),
    service: PromptService = Depends(get_prompt_service),
):
    return service.request_review(scope, project_id, revision_id, body.idempotency_key, body.consent_to_model)


@router.post(
    "/revisions/{revision_id}/cancel-review",
    response_model=PromptReviewRunView,
    operation_id="cancel_prompt_review",
)
def cancel_review(
    revision_id: str,
    body: PromptCancelRequest,
    project_id: str = ProjectId,
    scope: AuthContext = Depends(get_auth_context),
    service: PromptService = Depends(get_prompt_service),
):
    return service.cancel_review(
        scope, project_id, revision_id, body.run_id, body.expected_version, body.idempotency_key
    )


@router.post(
    "/revisions/{revision_id}/exports", response_model=PromptExportView, operation_id="export_prompt_revision"
)
def export_revision(
    revision_id: str,
    body: PromptExportRequest,
    project_id: str = ProjectId,
    scope: AuthContext = Depends(get_auth_context),
    service: PromptService = Depends(get_prompt_service),
):
    return service.export(scope, project_id, revision_id, body.format, body.idempotency_key)


@router.get("/exports/{export_id}", response_model=PromptExportView, operation_id="get_prompt_export")
def get_export(
    export_id: str,
    project_id: str = ProjectId,
    scope: AuthContext = Depends(get_auth_context),
    service: PromptService = Depends(get_prompt_service),
):
    return service.get_export(scope, project_id, export_id)
