"""FastAPI 应用入口（B2-V §六）。

本阶段注册五条业务路由（计划生成 / 运行状态 / 草案 / 决定 / 当前路线），
组合根把端口与实现装配为 :class:`~app.application.container.AppContainer`。

## 启动顺序的硬约束

`app.agent_workflows` 必须在**任何** langgraph 相关代码之前被 import：
它负责设置 `LANGGRAPH_STRICT_MSGPACK=true`（ADR-0002）。
本文件因此显式 import 该包，且注释提醒**不要调整顺序**。
"""

from __future__ import annotations

from typing import Any

# ⚠️ 必须在 import 任何 langgraph 相关模块之前。不要调整导入顺序。
from app import agent_workflows  # noqa: F401  (副作用：设置 LANGGRAPH_STRICT_MSGPACK)
from app.agent_workflows import GRAPH_VERSION
from app.api.v1.deps import CONTAINER_STATE_KEY
from app.api.v1.model_settings_routes import router as model_settings_router
from app.api.v1.routes import router as v1_router
from app.api.v1.schemas import V1_SCHEMAS
from app.api.v1.session_routes import router as session_router
from app.application.container import AppContainer
from app.composition import build_container
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.request_context import new_request_id, set_request_id
from app.core.startup_guard import validate_startup_security
from fastapi import FastAPI, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

API_PREFIX = "/api/v1"


def _install_contract_schemas(application: FastAPI) -> None:
    """把 ``/api/v1`` 业务 DTO 注册进 OpenAPI ``components.schemas``。

    路由已经自带这些模型，但显式注册保证**全部** DTO 都在契约里可见
    （包括尚未被任何路径引用的 DTO），前端才能生成完整类型。
    """
    base_openapi = application.openapi

    def custom_openapi() -> dict[str, Any]:
        if application.openapi_schema:
            return application.openapi_schema
        schema = base_openapi()
        components = schema.setdefault("components", {}).setdefault("schemas", {})
        for model in V1_SCHEMAS:
            model_schema = model.model_json_schema(
                ref_template="#/components/schemas/{model}"
            )
            # 嵌套模型（如 ErrorBody 被 RunView 引用）落在 $defs，平铺进 components。
            for name, definition in (model_schema.pop("$defs", None) or {}).items():
                components.setdefault(name, definition)
            components.setdefault(model.__name__, model_schema)
        application.openapi_schema = schema
        return schema

    application.openapi = custom_openapi  # type: ignore[method-assign]


def _install_error_handling(application: FastAPI) -> None:
    """统一错误视图：``code/message/request_id/details``（不回显敏感输入）。"""

    @application.exception_handler(RequestValidationError)
    async def _validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        if request.url.path == "/api/v1/model-settings":
            # FastAPI's default validation response includes raw input, including
            # malformed API Key objects. Never echo input/ctx on this secret route.
            return JSONResponse(status_code=422,content={"detail":[
                {"loc":error["loc"],"type":error["type"],"msg":"Invalid model setting value"}
                for error in exc.errors()]})
        return await request_validation_exception_handler(request,exc)

    @application.exception_handler(AppError)
    async def _app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        from app.core.request_context import get_request_id

        request_id = get_request_id() or new_request_id()
        return JSONResponse(
            status_code=exc.http_status,
            content=exc.to_view(request_id=request_id),
            headers={"X-Request-Id": request_id},
        )


def _install_request_id(application: FastAPI) -> None:
    """为每个请求绑定 ``request_id`` 并回传 ``X-Request-Id``。"""

    @application.middleware("http")
    async def _request_id_middleware(request: Request, call_next: Any) -> Any:
        request_id = request.headers.get("X-Request-Id") or new_request_id()
        token = set_request_id(request_id)
        try:
            response = await call_next(request)
        finally:
            from app.core.request_context import reset_request_id

            reset_request_id(token)
        response.headers.setdefault("X-Request-Id", request_id)
        return response


def create_app(container: AppContainer | None = None) -> FastAPI:
    """构建应用实例。

    拆成工厂函数以便测试用不同配置创建独立实例。

    启动期**强制**安全校验：生产环境的非法配置（Fake LLM、默认密钥、
    非法 DB、内存 Checkpointer、内存仓储后端、未实现的真实 Provider）
    会在此**显式抛错**，绝不静默降级（Goal §8）。

    Args:
        container: 可选的已装配容器。为 ``None`` 时按进程配置装配；
            测试可注入指向临时库、带 Fake LLM 与会话的容器。

    Raises:
        StartupSecurityError: 生产配置中存在任一安全违规。
    """
    settings = get_settings()
    # 组合根把"声明可用"与"实际可用"对齐：校验失败即拒绝启动。
    validate_startup_security(settings)
    application = FastAPI(
        title="studyplan API",
        version="1.1.0",
        description=(
            "学习规划助手 V1.1 —— LangGraph 编排 + FastAPI 接入 + PostgreSQL 业务事实源。\n\n"
            "**契约真相源是 Pydantic 模型**，本 OpenAPI 是其导出物（ADR-0004）。\n"
            "**AuthContext 永不出现在可写请求体**，由服务端会话派生。"
        ),
        openapi_url=f"{API_PREFIX}/openapi.json",
        docs_url="/docs",
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.allow_origins),
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Idempotency-Key", "X-Request-Id"],
    )

    # 容器：测试可注入；否则按配置装配（缺 DATABASE_URL 时业务端点返回 503）。
    setattr(application.state, CONTAINER_STATE_KEY, container or build_container(settings))

    _install_request_id(application)
    _install_error_handling(application)

    @application.get("/healthz", tags=["meta"])
    def healthz() -> dict[str, object]:
        """健康检查。**不暴露**图版本以外的内部信息。"""
        return {
            "status": "ok",
            "app": settings.app_name,
            "env": settings.app_env,
            "graph_version": GRAPH_VERSION,
            # 如实告知当前是否使用 fake，避免"以为在用云模型"（ADR-0005 C7）
            "llm_provider": settings.llm_provider,
            "repository_backend": settings.repository_backend,
        }

    application.include_router(v1_router)
    application.include_router(session_router)
    application.include_router(model_settings_router)
    # 契约模型注册必须在返回前完成（否则导出的 OpenAPI 缺业务 DTO）。
    _install_contract_schemas(application)
    return application


def __getattr__(name: str) -> FastAPI:
    """惰性构造 `app`，使 `app.main:app`（uvicorn 入口）仍可用。

    不在此处直接 `app = create_app()`：那会让 `import app.main` 本身
    在非法生产配置下抛错，导致测试无法在**受控断言**内验证失败行为。
    惰性访问保证：
    - `from app.main import create_app` 永远可导入（用于测试与组合）；
    - 一旦访问 `.app`（如 uvicorn 启动），非法配置**立即显式抛错**。
    """
    if name == "app":
        return create_app()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
