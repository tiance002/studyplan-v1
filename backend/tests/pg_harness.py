"""PostgreSQL 测试基础设施：独立临时库 + 迁移角色/应用角色分离。

## 硬约束（来自 Goal §7 与 B1.2 §一）

- 只允许创建 ``studyplan_test_*`` 命名的**临时**数据库做测试；
- **禁止**连接、修改、迁移或清空旧工程数据库；
- 迁移角色与应用角色必须不同；
- 缺授权上下文时默认拒绝（RLS 谓词用 ``current_setting(..., true)``）。

## 角色安全（B1.2 修复）

`CREATE ROLE` / `ALTER ROLE` 作用于**集群级**对象，会影响同一实例上的所有
数据库。旧实现在共享实例上无条件 `ALTER ROLE ... PASSWORD / CREATEDB /
BYPASSRLS`，属于危险操作（B1.2 复审指出）。本模块改为：

1. **优先使用专用、可销毁的测试实例**：设置 ``STUDYPLAN_TEST_PG_DEDICATED=1``
   显式声明实例专用，才允许创建/修改全局角色。
2. **不能证明实例专用 → 安全拒绝**：若所需角色不存在或属性不符，且未声明
   专用，则抛 :class:`UnsafeSharedInstanceError`（由测试层转为 skip），
   **绝不**改动已有角色。
3. **已存在且属性已满足 → 完全不修改**（尤其**不重置密码**）。
4. **只清理自己创建的角色**：本进程创建的角色在 session 结束时删除；
   预先存在的角色一律不动，保证"测试结束不遗留意外角色权限变化"。

## 为什么仍需要 BYPASSRLS 的迁移角色

迁移角色是 schema 属主且负责降级前的数据保护检查。若受 RLS 约束，
``SELECT count(*)`` 会被策略过滤成 0 行，使"有数据就拒绝降级"形同虚设。
应用角色则**必须** NOBYPASSRLS —— 这正是两个角色分离的意义。
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

#: 显式声明"该实例是专用的、可销毁的测试实例"。只有此时才允许管理全局角色。
DEDICATED_ENV = "STUDYPLAN_TEST_PG_DEDICATED"

MIGRATOR_ROLE = "studyplan_migrator"
APP_ROLE = "studyplan_app"
APP_ROLE_PASSWORD = "studyplan_app_test_pw"
MIGRATOR_ROLE_PASSWORD = "studyplan_migrator_test_pw"


class UnsafeSharedInstanceError(RuntimeError):
    """在未证明专用的实例上，拒绝创建/修改全局角色。

    测试层捕获本异常并**跳过** postgres 组，而不是失败——
    安全属性优先于"跑满测试"。
    """


@dataclass(frozen=True)
class RoleSpec:
    """测试所需的角色属性。``password`` 仅在**新建**角色时使用。"""

    name: str
    password: str
    can_login: bool = True
    superuser: bool = False
    createdb: bool = False
    createrole: bool = False
    bypassrls: bool = False


ROLE_SPECS: dict[str, RoleSpec] = {
    MIGRATOR_ROLE: RoleSpec(
        name=MIGRATOR_ROLE,
        password=MIGRATOR_ROLE_PASSWORD,
        createdb=True,
        bypassrls=True,
    ),
    APP_ROLE: RoleSpec(
        name=APP_ROLE,
        password=APP_ROLE_PASSWORD,
        createdb=False,
        createrole=False,
        superuser=False,
        bypassrls=False,
    ),
}

#: 本进程创建的角色；只有这些才允许在收尾时删除。
_ROLES_CREATED: set[str] = set()


def instance_is_dedicated() -> bool:
    """是否已显式声明该 PostgreSQL 实例为专用、可销毁的测试实例。"""
    return os.environ.get(DEDICATED_ENV, "").strip().lower() in {"1", "true", "yes", "on"}


def roles_created_by_harness() -> set[str]:
    """返回本进程创建的角色名（供测试断言清理行为）。"""
    return set(_ROLES_CREATED)


def admin_dsn(dbname: str = "postgres") -> str:
    return (
        f"postgresql://{ADMIN_USER}:{quote(ADMIN_PASSWORD)}@"
        f"{ADMIN_HOST}:{ADMIN_PORT}/{dbname}"
    )


def role_dsn(role: str, password: str, dbname: str) -> str:
    return f"postgresql://{role}:{quote(password)}@{ADMIN_HOST}:{ADMIN_PORT}/{dbname}"


def role_password(role: str) -> str:
    """角色的连接口令：优先环境变量，其次模块默认值。

    对**预先存在**的角色，若口令与此不符，连接会失败 —— 此时我们**不会**
    去重置它（那正是被禁止的修改），而是安全拒绝。
    """
    env_key = f"STUDYPLAN_TEST_PG_{role.upper()}_PASSWORD"
    if env_key in os.environ:
        return os.environ[env_key]
    return ROLE_SPECS[role].password


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
    严格的单引号转义；输入全部来自本模块常量/环境变量，无外部来源。
    """
    return "'" + value.replace("'", "''") + "'"


def _fetch_role_state(conn, role: str) -> dict[str, bool] | None:
    """读取角色属性；不存在返回 ``None``。"""
    row = conn.execute(
        "SELECT rolcanlogin, rolsuper, rolcreatedb, rolcreaterole, rolbypassrls "
        "FROM pg_roles WHERE rolname = %s",
        (role,),
    ).fetchone()
    if row is None:
        return None
    return {
        "can_login": bool(row[0]),
        "superuser": bool(row[1]),
        "createdb": bool(row[2]),
        "createrole": bool(row[3]),
        "bypassrls": bool(row[4]),
    }


def fetch_role_state(role: str) -> dict[str, bool] | None:
    """公开只读访问器：读取角色属性（不存在返回 ``None``）。"""
    with admin_connect("postgres") as conn:
        return _fetch_role_state(conn, role)


def harness_skip_reason() -> str | None:
    """**只读**探测：返回需要跳过 postgres 组的原因，或 ``None`` 表示可安全运行。

    不产生任何写副作用（不建库、不建/改角色）。
    """
    if not postgres_reachable():
        return "本地 PostgreSQL 不可达"
    try:
        with admin_connect("postgres") as conn:
            for spec in ROLE_SPECS.values():
                state = _fetch_role_state(conn, spec.name)
                try:
                    plan_role_action(state, spec, dedicated=instance_is_dedicated())
                except UnsafeSharedInstanceError as exc:
                    return str(exc)
    except Exception as exc:  # noqa: BLE001
        return f"探测 PostgreSQL 失败：{exc}"
    return None


def role_satisfies(existing: dict[str, bool], spec: RoleSpec) -> bool:
    """既有角色属性是否**恰好**满足需求。"""
    return (
        existing.get("can_login", False) == spec.can_login
        and existing.get("superuser", False) == spec.superuser
        and existing.get("createdb", False) == spec.createdb
        and existing.get("createrole", False) == spec.createrole
        and existing.get("bypassrls", False) == spec.bypassrls
    )


def plan_role_action(
    existing: dict[str, bool] | None, spec: RoleSpec, *, dedicated: bool
) -> str:
    """**纯函数**：决定对某角色采取的动作，或在共享实例上安全拒绝。

    返回 ``"keep"`` / ``"create"`` / ``"alter"``。

    Raises:
        UnsafeSharedInstanceError: 需要创建或修改角色，但未声明实例专用。
    """
    if existing is None:
        if not dedicated:
            raise UnsafeSharedInstanceError(
                f"角色 {spec.name!r} 不存在，且未声明实例专用"
                f"（设置 {DEDICATED_ENV}=1 以允许在专用实例上创建）。"
                "拒绝在共享实例上创建全局角色。"
            )
        return "create"
    if role_satisfies(existing, spec):
        # 属性已满足：**不做任何修改**（尤其不重置密码）。
        return "keep"
    if not dedicated:
        raise UnsafeSharedInstanceError(
            f"角色 {spec.name!r} 属性不符合要求（期望 "
            f"login={spec.can_login}, createdb={spec.createdb}, "
            f"createrole={spec.createrole}, superuser={spec.superuser}, "
            f"bypassrls={spec.bypassrls}），且未声明实例专用。"
            "拒绝修改已有全局角色属性。"
        )
    return "alter"


def _role_flags(spec: RoleSpec) -> str:
    return " ".join(
        [
            "LOGIN" if spec.can_login else "NOLOGIN",
            "SUPERUSER" if spec.superuser else "NOSUPERUSER",
            "CREATEDB" if spec.createdb else "NOCREATEDB",
            "CREATEROLE" if spec.createrole else "NOCREATEROLE",
            "BYPASSRLS" if spec.bypassrls else "NOBYPASSRLS",
        ]
    )


def ensure_roles() -> None:
    """确保测试角色存在且属性正确 —— **最小侵入**。

    - 已存在且属性满足：**不做任何修改**（不重置密码、不改属性）。
    - 不存在或属性不符：
        - 实例已声明专用 → 创建 / 修正；
        - 否则 → 抛 :class:`UnsafeSharedInstanceError`（安全拒绝）。

    Raises:
        UnsafeSharedInstanceError: 需要创建/修改角色但未声明实例专用。
    """
    dedicated = instance_is_dedicated()
    with admin_connect("postgres") as conn:
        for spec in ROLE_SPECS.values():
            existing = _fetch_role_state(conn, spec.name)
            action = plan_role_action(existing, spec, dedicated=dedicated)
            if action == "keep":
                continue
            if action == "create":
                # 角色名/口令来自本模块常量，经转义后拼接安全。
                conn.execute(
                    f'CREATE ROLE "{spec.name}" {_role_flags(spec)} '
                    f"PASSWORD {_quote_literal(spec.password)}"
                )
                _ROLES_CREATED.add(spec.name)
            elif action == "alter":
                conn.execute(f'ALTER ROLE "{spec.name}" {_role_flags(spec)}')


def drop_roles_created_by_harness() -> list[str]:
    """删除**本进程创建**的角色，返回成功删除的名字。

    预先存在的角色一律不动。若角色仍被对象依赖而无法删除，记录在返回值之外
    并由调用方决定是否告警 —— 不会静默吞掉异常。
    """
    dropped: list[str] = []
    if not _ROLES_CREATED:
        return dropped
    with admin_connect("postgres") as conn:
        for role in sorted(_ROLES_CREATED):
            try:
                conn.execute(f'DROP ROLE IF EXISTS "{role}"')
            except psycopg.Error:
                # 仍有依赖对象（如未清理的临时库）：保留角色，交由人工处理。
                continue
            _ROLES_CREATED.discard(role)
            dropped.append(role)
    return dropped


def _verify_role_connectivity(db: PgTestDatabase) -> None:
    """确认能以两个测试角色连接。

    若认证失败（例如角色预先存在且口令未知），**不重置密码**，
    而是安全拒绝并给出可操作提示。
    """
    for role, dsn in (
        (MIGRATOR_ROLE, db.migrator_dsn),
        (APP_ROLE, db.app_dsn),
    ):
        try:
            with psycopg.connect(dsn, connect_timeout=10):
                continue
        except psycopg.OperationalError as exc:
            raise UnsafeSharedInstanceError(
                f"无法以角色 {role!r} 连接测试库：{exc}。"
                "该角色可能预先存在且口令未知；拒绝重置已有角色口令。"
                f"请设置 STUDYPLAN_TEST_PG_{role.upper()}_PASSWORD，"
                f"或在专用实例上设置 {DEDICATED_ENV}=1。"
            ) from exc


def create_test_database(prefix: str = "studyplan_test") -> PgTestDatabase:
    """创建带随机后缀的临时库，并把 schema 权限授予两个角色。

    库名形如 ``studyplan_test_<8位随机>``，符合 Goal 的命名约束。
    角色安全由 :func:`ensure_roles` 保证（共享实例上只读使用既有角色）。
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
    db = PgTestDatabase(
        name=name,
        admin_dsn=admin_dsn(name),
        migrator_dsn=role_dsn(MIGRATOR_ROLE, role_password(MIGRATOR_ROLE), name),
        app_dsn=role_dsn(APP_ROLE, role_password(APP_ROLE), name),
    )
    _verify_role_connectivity(db)
    return db


def postgres_reachable() -> bool:
    try:
        with admin_connect("postgres"):
            return True
    except Exception:  # noqa: BLE001
        return False


__all__ = [
    "APP_ROLE",
    "DEDICATED_ENV",
    "MIGRATOR_ROLE",
    "ROLE_SPECS",
    "PgTestDatabase",
    "RoleSpec",
    "UnsafeSharedInstanceError",
    "admin_connect",
    "admin_dsn",
    "create_test_database",
    "drop_roles_created_by_harness",
    "ensure_roles",
    "fetch_role_state",
    "harness_skip_reason",
    "instance_is_dedicated",
    "plan_role_action",
    "postgres_reachable",
    "role_dsn",
    "role_password",
    "role_satisfies",
    "roles_created_by_harness",
]
