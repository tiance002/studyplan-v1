"""业务库连接与仓储实现。B2 实现。

约束：应用角色 `studyplan_app` **无 DDL**（ADR-0003）。

- :class:`~app.infrastructure.db.plan_repository.PgPlanRepository`
  —— ``PlanRepositoryPort`` 的 PostgreSQL 实现（单事务原子发布 + DB 唯一约束幂等）。
- :class:`~app.infrastructure.db.run_repository.PgRunRepository`
  —— ``RunRepositoryPort`` 的 PostgreSQL 实现（对外运行状态投影 ``ai_runs``）。
- :class:`~app.infrastructure.db.planning_catalog.PgPlanningCatalog`
  —— ``PlanningCatalogPort`` 的 PostgreSQL 实现（幂等物化稳定实体）。
- :class:`~app.infrastructure.db.public_resource_catalog.PgPublicResourceCatalog`
  —— 公共资源来源/章节的只读目录（计划输出前的引用校验，B2-V §五）。
"""

from app.infrastructure.db.plan_repository import PgPlanRepository, to_psycopg_dsn
from app.infrastructure.db.planning_catalog import PgPlanningCatalog, stable_entity_id
from app.infrastructure.db.public_resource_catalog import PgPublicResourceCatalog
from app.infrastructure.db.run_repository import PgRunRepository

__all__ = [
    "PgPlanRepository",
    "PgPlanningCatalog",
    "PgPublicResourceCatalog",
    "PgRunRepository",
    "stable_entity_id",
    "to_psycopg_dsn",
]
