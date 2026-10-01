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

from app.application.container import AppContainer
from app.application.model_binding import SubmissionBinding
from app.application.model_settings import ModelSettingsService
from app.application.plan_service import PlanService
from app.application.sessions import InMemorySessionStore, SessionRecord
from app.core.config import Settings
from app.domain.workspace.models import AuthContext
from app.infrastructure.db import (
    PgPlanningCatalog,
    PgPlanRepository,
    PgPublicResourceCatalog,
    PgRunRepository,
)
from app.infrastructure.db.job_repository import PgPlanningJobRepository
from app.infrastructure.providers import SUPPORTED_PROVIDERS, build_llm
from app.infrastructure.worker.planning_worker import PlanningWorker

__all__ = ["build_container"]


def _fake_binding(scope: AuthContext, project_id: str) -> SubmissionBinding:
    """Freeze the deployment default budget for the Fake / in-process deployment."""
    from app.agent_workflows.planning_batches import DEFAULT_BUDGET

    return SubmissionBinding(model_ref="fake:planning-demo", budget_policy=DEFAULT_BUDGET)


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
    from app.infrastructure.db.browser_auth import PgBrowserAuth
    browser_auth = PgBrowserAuth(dsn, settings.session_ttl_seconds)
    from app.infrastructure.db.workspace import PgWorkspaceReader
    workspace_reader = PgWorkspaceReader(dsn)
    from app.application.learning_exposures import LearningExposureService
    from app.application.resource_preferences import ResourcePreferenceService
    from app.infrastructure.db.learning_exposures import PgLearningExposures
    from app.infrastructure.db.resource_preferences import PgResourcePreferences
    exposure_service = LearningExposureService(PgLearningExposures(dsn))
    preference_service = ResourcePreferenceService(PgResourcePreferences(dsn))
    from app.application.learning_resources import LearningResourceService
    from app.infrastructure.db.learning_resources import PgLearningResources
    from app.infrastructure.resources.tavily import TavilyResourceIndex
    if settings.search_provider not in ("", "tavily"):
        raise RuntimeError("Unsupported search provider")
    search_index = TavilyResourceIndex(settings.tavily_api_key) if settings.search_provider == "tavily" and settings.tavily_api_key else None
    resource_service = LearningResourceService(PgLearningResources(dsn), search_index, settings.search_request_limit,
                                               preference_resolver=preference_service.resolve)
    sessions = browser_auth
    if settings.llm_provider.strip().lower() not in SUPPORTED_PROVIDERS:
        build_llm(settings)

    from app.infrastructure.db.model_settings import PgModelSettings
    from app.infrastructure.providers.endpoint_policy import ModelEndpointPolicy
    model_repository = PgModelSettings(dsn,settings.model_settings_encryption_key)
    model_service = ModelSettingsService(model_repository,ModelEndpointPolicy(settings.llm_allowed_hosts).validate)
    if settings.use_fake_llm:
        from app.infrastructure.providers.planning_demo import build_planning_demo
        llm = build_planning_demo()
    else:
        from app.infrastructure.providers.runtime_factory import UnconfiguredLLM
        llm = UnconfiguredLLM()
    executor = None
    runtime_factory = None
    if not settings.use_fake_llm:
        from app.infrastructure.checkpointer.planning_executor import PgPlanningExecutor
        from app.infrastructure.db.plan_repository import to_psycopg_dsn
        from app.infrastructure.providers.runtime_factory import PersonalPlanningRuntimeFactory
        if not settings.checkpoint_database_url:
            raise RuntimeError("Real provider requires CHECKPOINT_DATABASE_URL")
        from urllib.parse import urlsplit
        app_url = urlsplit(to_psycopg_dsn(dsn))
        cp_url = urlsplit(to_psycopg_dsn(settings.checkpoint_database_url))
        if (app_url.hostname, app_url.port or 5432, app_url.path) == (cp_url.hostname, cp_url.port or 5432, cp_url.path):
            raise RuntimeError("Business and checkpoint databases must be separate")
        executor = PgPlanningExecutor(to_psycopg_dsn(settings.checkpoint_database_url),llm=llm)
        runtime_factory = PersonalPlanningRuntimeFactory(settings,model_repository)
    from app.agent_workflows.planning_batches import PROTOCOL_VERSION
    from app.infrastructure.db.domain_pack_catalog import PgDomainPackCatalog
    planning_jobs = PgPlanningJobRepository(
        dsn,
        actor_ids=settings.planning_worker_actor_ids,
        max_attempts=settings.worker_max_attempts,
        admission_mode=settings.planning_worker_admission_mode,
    )
    binding_resolver = runtime_factory.bind_submission if runtime_factory is not None else _fake_binding

    plan_service = PlanService(
        repository=PgPlanRepository(dsn),
        runs=PgRunRepository(dsn),
        catalog=PgPlanningCatalog(dsn),
        resources=PgPublicResourceCatalog(dsn),
        llm=llm,
        graph_version=settings.graph_version or PROTOCOL_VERSION,
        planning_executor=executor,domain_pack_selector=PgDomainPackCatalog(dsn).select,
        runtime_factory=runtime_factory,
        planning_jobs=planning_jobs,
        worker_actor_ids=settings.planning_worker_actor_ids,
        planning_worker_admission_mode=settings.planning_worker_admission_mode,
        binding_resolver=binding_resolver,
        preference_resolver=preference_service.project_default,
    )
    planning_worker = PlanningWorker(
        jobs=planning_jobs,
        execute=plan_service.execute_generation,
        actor_ids=settings.planning_worker_actor_ids,
        poll_interval_seconds=settings.worker_poll_interval_seconds,
        lease_seconds=settings.worker_lease_seconds,
        is_development=settings.is_development,
        admission_mode=settings.planning_worker_admission_mode,
    )
    return AppContainer(settings=settings, sessions=sessions, plan_service=plan_service,
                        model_settings_service=model_service, browser_auth=browser_auth,
                        workspace_reader=workspace_reader, planning_worker=planning_worker,
                        resource_service=resource_service, exposure_service=exposure_service,
                        preference_service=preference_service)
