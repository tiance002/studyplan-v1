"""PostgreSQL 测试基础设施：独立临时库 + 迁移角色/应用角色分离。

## 硬约束（来自 Goal §7）

- 只允许创建 ``studyplan_test_*`` 命名的**临时**数据库做测试；
- **禁止**连接、修改、迁移或清空旧工程数据库；
- 迁移角色与应用角色必须不同；
- 缺授权上下文时默认拒绝（RLS 谓词用 ``current_setting(..., true)``）。

## 角色模型

| 角色 | 用途 | 权限 |
|---|---|---|
| ``studyplan_migrator`` | 执行 alembic 迁移 | DDL（建表/建索引/建策略） |
| ``studyplan_app``      | 应用运行时 | 只有 DML，**无 DDL** |

角色是**集群级**对象（CREATE ROLE 是全局的）。本模块在需要时创建它们，
测试库则在每个 session 里按需重建，名字带随机后缀避免并发碰撞。

## 为什么用超级用户建角色

创建角色需要超级用户或 CREATEROLE 权限。本机开发环境用 ``postgres``
超级用户完成 bootstrap；生产由运维脚本完成（迁移本身**不建角色**，见 C9）。
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from urllib.parse import quote

import psycopg

#: 管理员连接（仅用于建库/建角色；不用于执行业务查询）。
ADMIN_HOST = os.environ.get("STUDYPLAN_TEST_PG_HOST", "127.0.0.1")
ADMIN_PORT = int(os.environ.get("STUDYPLAN_TEST_PG_PORT", "5432"))
ADMIN_USER = os.environ.get("STUDYPLAN_TEST_PG_USER", "postgres")
ADMIN_PASSWORD = os.environ.get("STUDYPLAN_TEST_PG_PASSWORD", "postgres")

MIGRATOR_ROLE = "studyplan_migrator"
APP_ROLE = "studyplan_app"
APP_ROLE_PASSWORD = "studyplan_app_test_pw"
MIGRATOR_ROLE_PASSWORD = "studyplan_migrator_test_pw"


def admin_dsn(dbname: str = "postgres") -> str:
    return (
        f"postgresql://{ADMIN_USER}:{quote(ADMIN_PASSWORD)}@"
        f"{ADMIN_HOST}:{ADMIN_PORT}/{dbname}"
    )


def role_dsn(role: str, password: str, dbname: str) -> str:
    return f"postgresql://{role}:{quote(password)}@{ADMIN_HOST}:{ADMIN_PORT}/{dbname}"


def admin_connect(dbname: str = "postgres"):
    return psycopg.connect(admin_dsn(dbname), autocommit=True, connect_timeout=10)


@dataclass(frozen=True)
class PgTestDatabase:
    """一个隔离的临时测试库及其两个角色的 DSN。"""

    name: str
    admin_dsn: str
    migrator_dsn: str
    app_dsn: str

    def drop(self) -> None:
        with admin_connect("postgres") as conn:
            conn.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = %s AND pid <> pg_backend_pid()",
                (self.name,),
            )
            conn.execute(f'DROP DATABASE IF EXISTS "{self.name}"')


def _quote_literal(value: str) -> str:
    """把字符串转成 SQL 字面量（用于 CREATE ROLE 这类不支持占位符的语句）。

    ``CREATE ROLE ... PASSWORD`` 不接受参数占位符，因此必须拼接。这里做
    严格的单引号转义；输入全部来自本模块常量，无外部来源。
    """
    return "'" + value.replace("'", "''") + "'"


def ensure_roles() -> None:
    """创建迁移角色与应用角色（幂等）。

    **迁移角色与应用角色必须不同**（Goal §7）。应用角色**不带** CREATEDB/
    CREATEROLE/SUPERUSER，也不自动拥有 DDL 权限。
    """
    with admin_connect("postgres") as conn:
        for role, password in (
            (MIGRATOR_ROLE, MIGRATOR_ROLE_PASSWORD),
            (APP_ROLE, APP_ROLE_PASSWORD),
        ):
            exists = conn.execute(
                "SELECT 1 FROM pg_roles WHERE rolname = %s", (role,)
            ).fetchone()
            if not exists:
                # 角色名由本模块固定常量给出，口令经 _quote_literal 转义，拼接安全。
                conn.execute(
                    f'CREATE ROLE "{role}" LOGIN PASSWORD {_quote_literal(password)}'
                )
            else:
                conn.execute(
                    f'ALTER ROLE "{role}" LOGIN PASSWORD {_quote_literal(password)}'
                )
            # 应用角色**不得**有 elevated 权限。
            conn.execute(f'ALTER ROLE "{role}" NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS')
        # 迁移角色需要能建库对象。
        conn.execute(f'ALTER ROLE "{MIGRATOR_ROLE}" CREATEDB')
        # 迁移角色需要 BYPASSRLS：它是 schema 属主且负责数据保护检查，
        # 若受 RLS 约束，`SELECT count(*)` 会被策略过滤成 0 行，
        # 使"有数据就拒绝降级"的保护形同虚设（B1 审查实测到的陷阱）。
        # 应用角色**必须** NOBYPASSRLS —— 这正是两个角色分离的意义。
        conn.execute(f'ALTER ROLE "{MIGRATOR_ROLE}" BYPASSRLS')
        conn.execute(f'ALTER ROLE "{APP_ROLE}" NOBYPASSRLS')


def create_test_database(prefix: str = "studyplan_test") -> PgTestDatabase:
    """创建带随机后缀的临时库，并把 schema 权限授予两个角色。

    库名形如 ``studyplan_test_<8位随机>``，符合 Goal 的命名约束。
    """
    ensure_roles()
    name = f"{prefix}_{uuid.uuid4().hex[:8]}"
    with admin_connect("postgres") as conn:
        # 库名由本模块生成（无用户输入），拼接安全。
        conn.execute(f'CREATE DATABASE "{name}"')
        conn.execute(f'GRANT CREATE ON DATABASE "{name}" TO "{MIGRATOR_ROLE}"')
    # 在**目标库内**执行 schema 授权：PG15+ 起 public schema 默认不再对所有
    # 角色开放 CREATE，必须显式授予，否则迁移角色无法建表。
    with admin_connect(name) as conn:
        conn.execute(f'ALTER SCHEMA public OWNER TO "{MIGRATOR_ROLE}"')
        conn.execute(f'GRANT USAGE, CREATE ON SCHEMA public TO "{MIGRATOR_ROLE}"')
        # 应用角色只拿到连接与 schema 使用（DML 权限由迁移脚本精确授予）。
        conn.execute(f'GRANT USAGE ON SCHEMA public TO "{APP_ROLE}"')
    return PgTestDatabase(
        name=name,
        admin_dsn=admin_dsn(name),
        migrator_dsn=role_dsn(MIGRATOR_ROLE, MIGRATOR_ROLE_PASSWORD, name),
        app_dsn=role_dsn(APP_ROLE, APP_ROLE_PASSWORD, name),
    )


def postgres_reachable() -> bool:
    try:
        with admin_connect("postgres"):
            return True
    except Exception:  # noqa: BLE001
        return False


__all__ = [
    "APP_ROLE",
    "MIGRATOR_ROLE",
    "PgTestDatabase",
    "admin_connect",
    "admin_dsn",
    "create_test_database",
    "ensure_roles",
    "postgres_reachable",
    "role_dsn",
]
