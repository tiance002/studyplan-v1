"""``/api/v1`` 依赖注入：容器访问、**服务端派生**的授权上下文、计划服务。

## 硬约束（ADR-0004 第 4 条 / Goal §六）

``AuthContext`` **只能**从服务端会话派生：

    Cookie(不透明令牌) -> SessionResolverPort.resolve() -> AuthContext

请求体、查询串、请求头里的 ``actor_id`` / ``tenant_id`` / 项目范围一律
**不被读取**。客户端无法自报身份，也无法自报项目授权。
"""

from __future__ import annotations

from dataclasses import replace

from app.application.container import AppContainer
from app.application.plan_service import PlanService
from app.application.sessions import validate_local_binding
from app.core.errors import DependencyUnavailableError, ForbiddenError, UnauthenticatedError
from app.domain.workspace.models import AuthContext
from fastapi import Depends, Request

__all__ = [
    "get_auth_context",
    "get_container",
    "get_plan_service",
    "require_project_scope",
]

#: 容器挂在 ``app.state`` 上的属性名（唯一约定）。
CONTAINER_STATE_KEY = "container"


def get_container(request: Request) -> AppContainer:
    """取出已装配的应用容器。"""
    container = getattr(request.app.state, CONTAINER_STATE_KEY, None)
    if not isinstance(container, AppContainer):
        raise DependencyUnavailableError("应用容器未装配")
    return container


def get_auth_context(
    request: Request,
    container: AppContainer = Depends(get_container),
) -> AuthContext:
    """从**服务端会话**派生授权上下文。

    只读取 Cookie 里的不透明令牌；解析失败即 401（**不**退化为匿名上下文）。
    """
    token = request.cookies.get(container.settings.session_cookie_name, "")
    context = container.sessions.resolve(token) if token else None
    if context is None:
        raise UnauthenticatedError()
    if container.settings.local_entry_enabled:
        validate_local_binding(container.settings)
        if container.browser_auth is None:
            raise DependencyUnavailableError("本地入口需要持久会话 adapter")
        if context.actor_id != container.settings.local_actor_id:
            raise ForbiddenError("会话不属于本地绑定 actor")
        projects = container.browser_auth.local_binding(context.actor_id, container.settings.local_project_id)
        context = replace(context, learning_project_scope=tuple(projects))
    from app.api.v1.session_routes import check_csrf
    check_csrf(request, container)
    return context


def get_plan_service(container: AppContainer = Depends(get_container)) -> PlanService:
    """取出计划服务；未装配（缺 ``DATABASE_URL``）时明确 503。"""
    if container.plan_service is None:
        raise DependencyUnavailableError(
            "计划服务未装配：缺少 DATABASE_URL，业务事实必须落 PostgreSQL"
        )
    return container.plan_service


def require_project_scope(scope: AuthContext, project_id: str) -> str:
    """校验项目归属后再返回 ``project_id``（**先鉴权再访问仓储**）。

    不属于会话范围时统一 403，不区分「不存在」与「无权限」，避免枚举探测。
    """
    scope.require_project(project_id)
    return project_id
