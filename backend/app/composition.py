"""组合根：把端口与实现装配成 :class:`AppContainer`。

**唯一**允许把基础设施实现接到应用服务上的地方（``SOFTWARE_DESIGN.md`` §2）。

## 装配规则

- 会话解析：骨架用进程内存储（``InMemorySessionStore``）。真实部署应替换为
  受签名保护的会话存储（B3 输入）。
- 计划服务：仅在配置了 ``DATABASE_URL`` 时装配。缺数据库时 ``plan_service``
  为 ``None``，业务端点返回 503 —— 而不是让整个进程起不来（开发骨架需要
  能在无 PG 时启动 ``/healthz`` 与 ``/docs``）。
- LLM：走 ``build_llm``，provider 未实现时**拒绝启动**（不静默退回 Fake）。

## 为什么业务服务不在这里 import FastAPI

本模块只产出**纯 Python 对象**；把它们挂到 ``app.state`` 是 ``main.py`` 的
职责。这样组合根可以被非 Web 场景（worker、脚本、测试）复用。
"""

from __future__ import annotations

from app.agent_workflows import GRAPH_VERSION
from app.application.container import AppContainer
from app.application.plan_service import PlanService
from app.application.sessions import InMemorySessionStore, SessionRecord
from app.core.config import Settings
from app.infrastructure.db import (
    PgPlanningCatalog,
    PgPlanRepository,
    PgPublicResourceCatalog,
    PgRunRepository,
)
from app.infrastructure.providers import build_llm

__all__ = ["build_container"]


def build_container(settings: Settings) -> AppContainer:
    """按配置装配容器。

    缺少 ``DATABASE_URL`` 时**不**装配计划服务：真实业务事实必须落 Postgres，
    内存实现只用于测试，不作为生产降级路径。
    """
    sessions = InMemorySessionStore()
    if settings.is_development and settings.local_session_token:
        sessions.add(SessionRecord(token=settings.local_session_token,
                     actor_id=settings.local_actor_id,session_id="local-session",
                     learning_project_scope=(settings.local_project_id,)))
    dsn = settings.database_url.strip()
    if not dsn:
        return AppContainer(settings=settings, sessions=sessions, plan_service=None)

    llm = build_llm(settings)
    executor = None
    pack_key, pack_version = "", 0
    if not settings.use_fake_llm:
        from app.infrastructure.checkpointer.planning_executor import PgPlanningExecutor
        from app.infrastructure.db.plan_repository import to_psycopg_dsn
        from app.infrastructure.providers.attempt_ledger import PgAttemptLLM
        if not settings.checkpoint_database_url:
            raise RuntimeError("Real provider requires CHECKPOINT_DATABASE_URL")
        from urllib.parse import urlsplit
        app_url = urlsplit(to_psycopg_dsn(dsn))
        cp_url = urlsplit(to_psycopg_dsn(settings.checkpoint_database_url))
        if (app_url.hostname, app_url.port or 5432, app_url.path) == (cp_url.hostname, cp_url.port or 5432, cp_url.path):
            raise RuntimeError("Business and checkpoint databases must be separate")
        llm = PgAttemptLLM(dsn,llm)
        executor = PgPlanningExecutor(to_psycopg_dsn(settings.checkpoint_database_url),llm=llm)
        pack_key, pack_version = "python.engineering", 1
    plan_service = PlanService(
        repository=PgPlanRepository(dsn),
        runs=PgRunRepository(dsn),
        catalog=PgPlanningCatalog(dsn),
        resources=PgPublicResourceCatalog(dsn),
        llm=llm,
        graph_version=settings.graph_version or GRAPH_VERSION,
        planning_executor=executor,source_pack_key=pack_key,source_pack_version=pack_version,
    )
    return AppContainer(settings=settings, sessions=sessions, plan_service=plan_service)
