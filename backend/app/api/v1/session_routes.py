"""Browser password sessions; server-derived identity and project scope."""

import secrets
from urllib.parse import urlsplit

from app.api.v1.deps import get_auth_context, get_container
from app.application.container import AppContainer
from app.application.sessions import validate_local_binding
from app.core.errors import DependencyUnavailableError, ForbiddenError, UnauthenticatedError
from app.core.startup_guard import is_loopback
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
    default_project_id: str = ""


class SessionEntryMode(BaseModel):
    local_entry_enabled: bool


class LocalSessionEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")


def check_local_request(request, container, *, require_origin=False):
    if not container.settings.local_entry_enabled:
        return
    settings = container.settings
    if not request.client or not is_loopback(request.client.host):
        raise ForbiddenError("本地入口仅允许 loopback 访问")
    if any(h.lower() == "forwarded" or h.lower().startswith("x-forwarded-") for h in request.headers):
        raise ForbiddenError("本地入口不接受代理转发身份")
    origins = set(settings.allow_origins)
    for host in ("127.0.0.1", "localhost", "[::1]"):
        origins.add(f"http://{host}:{settings.app_port}")
        origins.add(f"https://{host}:{settings.app_port}")
    authorities = {urlsplit(o).netloc.lower() for o in origins}
    if request.headers.get("host", "").lower() not in authorities:
        raise ForbiddenError("本地入口 Host 不受信任")
    origin = request.headers.get("origin")
    if (require_origin and not origin) or (origin is not None and origin not in origins):
        raise ForbiddenError("本地入口 Origin 不受信任")
    if request.headers.get("sec-fetch-site", "").lower() == "cross-site":
        raise ForbiddenError("本地入口拒绝跨站请求")


@router.get("/session/entry-mode", response_model=SessionEntryMode, operation_id="get_session_entry_mode")
def entry_mode(container: AppContainer = Depends(get_container)):
    return SessionEntryMode(local_entry_enabled=container.settings.local_entry_enabled)


@router.post("/session/local", response_model=SessionView, operation_id="enter_local_session")
def enter_local_session(payload: LocalSessionEntry, request: Request, response: Response,
                        container: AppContainer = Depends(get_container)):
    if not container.settings.local_entry_enabled:
        raise ForbiddenError("本地入口未启用")
    check_local_request(request, container, require_origin=True)
    validate_local_binding(container.settings)
    service = auth_service(container)
    token = service.issue_local(container.settings.local_actor_id, container.settings.local_project_id)
    return session_response(token, response, container)


class SessionEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(min_length=1, max_length=512)


@router.post("/session", response_model=SessionView, operation_id="enter_development_session")
def enter_development_session(
    payload: SessionEntry, response: Response, container: AppContainer = Depends(get_container)
):
    # Compatibility for explicitly injected legacy test sessions only. Normal PG
    # composition never exposes this path as an authentication alternative.
    if container.settings.local_entry_enabled or container.browser_auth is not None or not container.settings.is_development:
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
    if container.settings.local_entry_enabled:
        check_local_request(request, container)
        return
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
    if settings.local_entry_enabled:
        validate_local_binding(settings)
        if row["actor_id"] != settings.local_actor_id:
            auth_service(container).logout(token)
            raise ForbiddenError("会话不属于本地绑定 actor")
        projects = auth_service(container).local_binding(settings.local_actor_id, settings.local_project_id)
    return SessionView(project_ids=projects, username=row["username"], csrf_token=row["csrf_token"],
                       default_project_id=settings.local_project_id if settings.local_entry_enabled else "")


def authenticate(payload, request, response, container, registration):
    if container.settings.local_entry_enabled:
        if registration:
            raise ForbiddenError("本地入口不创建新身份")
        validate_local_binding(container.settings)
        auth_service(container).local_binding(container.settings.local_actor_id, container.settings.local_project_id)
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
    return SessionView(project_ids=list(scope.learning_project_scope), username=row["username"], csrf_token=row["csrf_token"],
                       default_project_id=container.settings.local_project_id if container.settings.local_entry_enabled else "")


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
    if container.settings.local_entry_enabled:
        check_local_request(request, container)
        if container.browser_auth is None:
            raise DependencyUnavailableError("本地入口需要持久会话 adapter")
    if request.method in {"GET", "HEAD", "OPTIONS"} or container.browser_auth is None:
        return
    check_origin(request, container)
    row, _ = container.browser_auth.detail(request.cookies.get(container.settings.session_cookie_name, ""))
    if not secrets.compare_digest(request.headers.get("X-CSRF-Token", ""), row["csrf_token"]):
        raise ForbiddenError("安全校验失败，请刷新页面后重试")
