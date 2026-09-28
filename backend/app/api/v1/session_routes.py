"""Local session entry: opaque token is resolved by server, never client identity."""
from app.api.v1.deps import get_auth_context, get_container
from app.application.container import AppContainer
from app.core.errors import UnauthenticatedError
from app.domain.workspace.models import AuthContext
from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, ConfigDict, Field

router = APIRouter(prefix="/api/v1")


class SessionEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(min_length=1,max_length=512)


class SessionView(BaseModel):
    project_ids: list[str]


@router.post("/session",response_model=SessionView,operation_id="enter_session")
def enter_session(payload: SessionEntry, response: Response, container: AppContainer = Depends(get_container)):
    scope = container.sessions.resolve(payload.token)
    if scope is None:
        raise UnauthenticatedError()
    settings = container.settings
    response.set_cookie(settings.session_cookie_name,payload.token,httponly=True,
                        secure=settings.session_cookie_secure,samesite="strict",max_age=settings.session_ttl_seconds)
    return SessionView(project_ids=list(scope.learning_project_scope))


@router.get("/session",response_model=SessionView,operation_id="get_session")
def get_session(scope: AuthContext = Depends(get_auth_context)):
    return SessionView(project_ids=list(scope.learning_project_scope))
