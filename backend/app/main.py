"""FastAPI 应用入口（B1 骨架）。

本阶段**不注册业务路由**（属 B2）。启动后 `/docs` 可查看 OpenAPI，
用于验证契约基建（ADR-0004）。

## 启动顺序的硬约束

`app.agent_workflows` 必须在**任何** langgraph 相关代码之前被 import：
它负责设置 `LANGGRAPH_STRICT_MSGPACK=true`（ADR-0002）。
本文件因此显式 import 该包，且注释提醒**不要调整顺序**。
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ⚠️ 必须在 import 任何 langgraph 相关模块之前。不要调整导入顺序。
from app import agent_workflows  # noqa: F401  (副作用：设置 LANGGRAPH_STRICT_MSGPACK)
from app.agent_workflows import GRAPH_VERSION
from app.core.config import get_settings

API_PREFIX = "/api/v1"


def create_app() -> FastAPI:
    """构建应用实例。

    拆成工厂函数以便测试用不同配置创建独立实例。
    """
    settings = get_settings()
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
        allow_headers=["Content-Type", "Idempotency-Key"],
    )

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

    return application


app = create_app()
