from typing import Annotated

from app.api.v1.deps import get_auth_context, get_container
from app.api.v1.routes import ProjectId
from app.api.v1.summary_schemas import (
    SummaryAttemptView,
    SummaryCancelRequest,
    SummaryHistoryView,
    SummaryReviewRequest,
    SummaryReviewRunView,
    SummarySaveRequest,
    SummarySaveView,
    SummaryThreadView,
)
from app.application.container import AppContainer
from app.application.summaries import SummaryService
from app.core.errors import DependencyUnavailableError
from app.domain.summaries import SummarySaveCommand
from app.domain.workspace.models import AuthContext
from fastapi import APIRouter, Depends, Query

router = APIRouter(prefix="/api/v1/summaries")


def get_summary_service(container: AppContainer = Depends(get_container)) -> SummaryService:
    service = getattr(container, "summary_service", None)
    if service is None:
        raise DependencyUnavailableError("总结服务尚未装配")
    return service


@router.get("", response_model=SummaryThreadView, operation_id="get_summary_thread")
def get_thread(plan_id: Annotated[str, Query(min_length=1, max_length=512)],
               stage_id: Annotated[str, Query(min_length=1, max_length=512)],
               unit_id: Annotated[str, Query(min_length=1, max_length=512)], project_id: str = ProjectId,
               scope: AuthContext = Depends(get_auth_context), service: SummaryService = Depends(get_summary_service)):
    return service.thread(scope, project_id, plan_id, stage_id, unit_id)


@router.post("", response_model=SummarySaveView, operation_id="save_summary_original")
def save_original(body: SummarySaveRequest, project_id: str = ProjectId,
                  scope: AuthContext = Depends(get_auth_context), service: SummaryService = Depends(get_summary_service)):
    return service.save(scope, SummarySaveCommand(project_id=project_id, **body.model_dump()))


@router.get("/history", response_model=SummaryHistoryView, operation_id="get_summary_history")
def get_history(cursor: Annotated[str | None, Query(max_length=1024)] = None,
                limit: Annotated[int, Query(ge=1, le=100)] = 20, project_id: str = ProjectId,
                scope: AuthContext = Depends(get_auth_context), service: SummaryService = Depends(get_summary_service)):
    return service.history(scope, project_id, cursor, limit)


@router.get("/attempts/{attempt_id}", response_model=SummaryAttemptView, operation_id="get_summary_attempt")
def get_attempt(attempt_id: str, project_id: str = ProjectId, scope: AuthContext = Depends(get_auth_context),
                service: SummaryService = Depends(get_summary_service)):
    return service.attempt(scope, project_id, attempt_id)


@router.post("/attempts/{attempt_id}/review", response_model=SummaryReviewRunView, status_code=202,
             operation_id="request_summary_review")
def review_attempt(attempt_id: str, body: SummaryReviewRequest, project_id: str = ProjectId,
                   scope: AuthContext = Depends(get_auth_context), service: SummaryService = Depends(get_summary_service)):
    return service.request_review(scope, project_id, attempt_id, body.idempotency_key, body.consent_to_model)


@router.post("/attempts/{attempt_id}/cancel-review", response_model=SummaryReviewRunView,
             operation_id="cancel_summary_review")
def cancel_review(attempt_id: str, body: SummaryCancelRequest, project_id: str = ProjectId,
                  scope: AuthContext = Depends(get_auth_context), service: SummaryService = Depends(get_summary_service)):
    return service.cancel_review(scope, project_id, attempt_id, body.run_id, body.expected_version, body.idempotency_key)
