from app.api.v1.deps import get_auth_context, get_container
from app.api.v1.plan_change_schemas import (
    PlanChangeContext,
    PlanChangeDecisionRequest,
    PlanChangePreviewView,
    PlanChangeRequest,
    PlanChangeResult,
)
from app.api.v1.routes import ProjectId
from app.api.v1.views import draft_view
from app.application.container import AppContainer
from app.application.plan_service import DraftBundle
from app.core.errors import DependencyUnavailableError
from app.domain.plan_changes import PlanChangeCommand
from app.domain.workspace.models import AuthContext
from fastapi import APIRouter, Depends

router = APIRouter(prefix='/api/v1/plan-changes')


def _service(container):
    if container.plan_change_service is None:
        raise DependencyUnavailableError('有限路线变更服务尚未装配')
    return container.plan_change_service


def _view(raw, container, scope, project):
    if container.plan_service is None:
        raise DependencyUnavailableError('草案读取服务尚未装配')
    bundle = container.plan_service.get_draft(scope=scope, project_id=project, draft_id=raw['proposal_id'])
    return {**raw, 'draft': draft_view(DraftBundle(draft=raw['draft'], resources=bundle.resources))}


@router.get('/context', response_model=PlanChangeContext, operation_id='get_plan_change_context')
def context(project_id: str = ProjectId, scope: AuthContext = Depends(get_auth_context),
            container: AppContainer = Depends(get_container)):
    return _service(container).context(scope, project_id)


@router.post('', response_model=PlanChangePreviewView, operation_id='preview_plan_change')
def preview(body: PlanChangeRequest, project_id: str = ProjectId, scope: AuthContext = Depends(get_auth_context),
            container: AppContainer = Depends(get_container)):
    raw = _service(container).preview(scope, PlanChangeCommand(project_id=project_id, **body.model_dump()))
    return _view(raw, container, scope, project_id)


@router.get('/{proposal_id}', response_model=PlanChangePreviewView, operation_id='get_plan_change_preview')
def get_preview(proposal_id: str, project_id: str = ProjectId, scope: AuthContext = Depends(get_auth_context),
                container: AppContainer = Depends(get_container)):
    return _view(_service(container).get(scope, project_id, proposal_id), container, scope, project_id)


def _decide(container, scope, project, proposal, action, body):
    result = _service(container).decide(scope, project, proposal, action, **body.model_dump())
    return {**result, 'preview': _view(result['preview'], container, scope, project)}


@router.post('/{proposal_id}/confirm', response_model=PlanChangeResult, operation_id='confirm_plan_change')
def confirm(proposal_id: str, body: PlanChangeDecisionRequest, project_id: str = ProjectId,
            scope: AuthContext = Depends(get_auth_context), container: AppContainer = Depends(get_container)):
    return _decide(container, scope, project_id, proposal_id, 'confirm', body)


@router.post('/{proposal_id}/cancel', response_model=PlanChangeResult, operation_id='cancel_plan_change')
def cancel(proposal_id: str, body: PlanChangeDecisionRequest, project_id: str = ProjectId,
           scope: AuthContext = Depends(get_auth_context), container: AppContainer = Depends(get_container)):
    return _decide(container, scope, project_id, proposal_id, 'cancel', body)
