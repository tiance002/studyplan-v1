from app.api.v1.deps import get_auth_context, get_container
from app.api.v1.routes import ProjectId
from app.api.v1.submission_schemas import (
    PracticeOutcomeView,
    PracticeSubmissionDecisionRequest,
    PracticeSubmissionDecisionView,
    PracticeSubmissionHistoryView,
    PracticeSubmissionRequest,
    PracticeSubmissionSaveView,
    PracticeSubmissionThreadView,
    PracticeSubmissionView,
)
from app.application.container import AppContainer
from app.application.practice_submissions import PracticeSubmissionService
from app.core.errors import DependencyUnavailableError
from app.domain.practice_submissions import (
    CriterionCoverage,
    SubmissionDecisionCommand,
    SubmissionEvidence,
    SubmissionSaveCommand,
)
from app.domain.workspace.models import AuthContext
from fastapi import APIRouter, Depends, Query

router = APIRouter(prefix="/api/v1/submissions")
outcomes_router = APIRouter(prefix="/api/v1/outcomes")


def get_submission_service(container: AppContainer = Depends(get_container)) -> PracticeSubmissionService:
    service = getattr(container, "practice_submission_service", None)
    if service is None:
        raise DependencyUnavailableError("成果提交服务尚未装配")
    return service


@router.get("", response_model=PracticeSubmissionThreadView, operation_id="get_practice_submission_thread")
def thread(
    project_id: str = ProjectId,
    plan_id: str = Query(min_length=1, max_length=512),
    stage_id: str = Query(min_length=1, max_length=512),
    task_id: str = Query(min_length=1, max_length=512),
    scope: AuthContext = Depends(get_auth_context),
    service: PracticeSubmissionService = Depends(get_submission_service),
):
    return service.thread(scope, project_id, plan_id, stage_id, task_id)


@router.post("", response_model=PracticeSubmissionSaveView, operation_id="save_practice_submission")
def save(
    body: PracticeSubmissionRequest,
    project_id: str = ProjectId,
    scope: AuthContext = Depends(get_auth_context),
    service: PracticeSubmissionService = Depends(get_submission_service),
):
    values = body.model_dump()
    values["evidence"] = tuple(SubmissionEvidence(**item) for item in values["evidence"])
    return service.save(scope, SubmissionSaveCommand(project_id=project_id, **values))


@router.get(
    "/history", response_model=PracticeSubmissionHistoryView, operation_id="get_practice_submission_history"
)
def history(
    project_id: str = ProjectId,
    cursor: str | None = Query(default=None, max_length=1024),
    limit: int = Query(default=20, ge=1, le=100),
    scope: AuthContext = Depends(get_auth_context),
    service: PracticeSubmissionService = Depends(get_submission_service),
):
    return service.history(scope, project_id, cursor, limit)


@router.get("/{submission_id}", response_model=PracticeSubmissionView, operation_id="get_practice_submission")
def get_submission(
    submission_id: str,
    project_id: str = ProjectId,
    scope: AuthContext = Depends(get_auth_context),
    service: PracticeSubmissionService = Depends(get_submission_service),
):
    return service.get(scope, project_id, submission_id)


@router.post(
    "/{submission_id}/decision",
    response_model=PracticeSubmissionDecisionView,
    operation_id="decide_practice_submission",
)
def decide(
    submission_id: str,
    body: PracticeSubmissionDecisionRequest,
    project_id: str = ProjectId,
    scope: AuthContext = Depends(get_auth_context),
    service: PracticeSubmissionService = Depends(get_submission_service),
):
    values = body.model_dump()
    values["coverage"] = tuple(
        CriterionCoverage(item["criterion_index"], tuple(item["evidence_indices"]), item["observation"])
        for item in values["coverage"]
    )
    return service.decide(
        scope, SubmissionDecisionCommand(project_id=project_id, submission_id=submission_id, **values)
    )


@outcomes_router.get("", response_model=PracticeOutcomeView, operation_id="get_practice_outcomes")
def outcomes(
    project_id: str = ProjectId,
    cursor: str | None = Query(default=None, max_length=1024),
    limit: int = Query(default=20, ge=1, le=100),
    scope: AuthContext = Depends(get_auth_context),
    service: PracticeSubmissionService = Depends(get_submission_service),
):
    return service.outcomes(scope, project_id, cursor, limit)
