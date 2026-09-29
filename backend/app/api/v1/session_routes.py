"""Browser password sessions; server-derived identity and project scope."""

import secrets

from app.api.v1.deps import get_auth_context, get_container
from app.application.container import AppContainer
from app.core.errors import DependencyUnavailableError, ForbiddenError, UnauthenticatedError
from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field

router = APIRouter(prefix="/api/v1")


class CredentialsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=2, max_length=32)
    password: str = Field(min_length=6, max_length=12)


class SessionView(BaseModel):
    project_ids: list[str]
    username: str = ""
    csrf_token: str = ""


class SessionEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(min_length=1, max_length=512)


@router.post("/session", response_model=SessionView, operation_id="enter_development_session")
def enter_development_session(
    payload: SessionEntry, response: Response, container: AppContainer = Depends(get_container)
):
    # Compatibility for explicitly injected legacy test sessions only. Normal PG
    # composition never exposes this path as an authentication alternative.
    if container.browser_auth is not None or not container.settings.is_development:
        raise ForbiddenError("请使用用户名和密码登录")
    scope = container.sessions.resolve(payload.token)
    if scope is None:
        raise UnauthenticatedError()
    response.set_cookie(
        container.settings.session_cookie_name,
        payload.token,
        httponly=True,
        secure=container.settings.session_cookie_secure,
        samesite="strict",
    )
    return SessionView(project_ids=list(scope.learning_project_scope))


def auth_service(container):
    if container.browser_auth is None:
        raise DependencyUnavailableError("持久认证需要 PostgreSQL")
    return container.browser_auth


def check_origin(request, container):
    origin = request.headers.get("origin")
    if (
        origin
        and origin not in container.settings.allow_origins
        and origin != str(request.base_url).rstrip("/")
    ):
        raise ForbiddenError("请求来源不受信任")


def session_response(token, response, container):
    settings = container.settings
    response.set_cookie(
        settings.session_cookie_name,
        token,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="strict",
        max_age=settings.session_ttl_seconds,
        path="/",
    )
    row, projects = auth_service(container).detail(token)
    return SessionView(project_ids=projects, username=row["username"], csrf_token=row["csrf_token"])


def authenticate(payload, request, response, container, registration):
    check_origin(request, container)
    service = auth_service(container)
    method = service.register if registration else service.login
    token = method(payload.username, payload.password, request.client.host if request.client else "unknown")
    old_token = request.cookies.get(container.settings.session_cookie_name)
    if old_token:
        service.logout(old_token)
    return session_response(token, response, container)


@router.post("/auth/register", response_model=SessionView, operation_id="register_user")
def register(
    payload: CredentialsRequest,
    request: Request,
    response: Response,
    container: AppContainer = Depends(get_container),
):
    return authenticate(payload, request, response, container, True)


@router.post("/auth/login", response_model=SessionView, operation_id="login_user")
def login(
    payload: CredentialsRequest,
    request: Request,
    response: Response,
    container: AppContainer = Depends(get_container),
):
    return authenticate(payload, request, response, container, False)


@router.get("/session", response_model=SessionView, operation_id="get_session")
def get_session(
    request: Request, container: AppContainer = Depends(get_container), scope=Depends(get_auth_context)
):
    if container.browser_auth is None:
        return SessionView(project_ids=list(scope.learning_project_scope))
    row, projects = container.browser_auth.detail(
        request.cookies.get(container.settings.session_cookie_name, "")
    )
    return SessionView(project_ids=projects, username=row["username"], csrf_token=row["csrf_token"])


@router.post("/auth/logout", operation_id="logout_user")
def logout(
    request: Request,
    response: Response,
    container: AppContainer = Depends(get_container),
    scope=Depends(get_auth_context),
):
    auth_service(container).logout(request.cookies.get(container.settings.session_cookie_name, ""))
    response.delete_cookie(
        container.settings.session_cookie_name,
        path="/",
        httponly=True,
        secure=container.settings.session_cookie_secure,
        samesite="strict",
    )
    return {"logged_out": True}


def check_csrf(request, container):
    if request.method in {"GET", "HEAD", "OPTIONS"} or container.browser_auth is None:
        return
    check_origin(request, container)
    row, _ = container.browser_auth.detail(request.cookies.get(container.settings.session_cookie_name, ""))
    if not secrets.compare_digest(request.headers.get("X-CSRF-Token", ""), row["csrf_token"]):
        raise ForbiddenError("安全校验失败，请刷新页面后重试")
