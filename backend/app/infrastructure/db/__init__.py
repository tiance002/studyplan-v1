"""业务库连接与仓储实现。B2 实现。

约束：应用角色 `studyplan_app` **无 DDL**（ADR-0003）。

- :class:`~app.infrastructure.db.plan_repository.PgPlanRepository`
  —— ``PlanRepositoryPort`` 的 PostgreSQL 实现（单事务原子发布 + DB 唯一约束幂等）。
"""

from app.infrastructure.db.plan_repository import PgPlanRepository, to_psycopg_dsn

__all__ = ["PgPlanRepository", "to_psycopg_dsn"]
