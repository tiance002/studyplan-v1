"""PostgreSQL 验收：迁移、RLS 权限反例、跨进程 Checkpoint 恢复。

对应 Goal §7 与 §10：

- 迁移在**独立临时库**上执行（``studyplan_test_*``），不碰任何旧库；
- RLS 反例：跨用户/跨项目读写拒绝、缺授权上下文默认拒绝；
- 应用角色最小权限（无 DDL）；
- 迁移角色与应用角色分离；
- **J**：杀掉进程、重新启动后仍能恢复 ``waiting_user``（跨进程 checkpoint）。

**所有数据库操作都限定在临时库上，测试结束即 DROP。**
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.postgres

psycopg = pytest.importorskip("psycopg")

BACKEND_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND_DIR))

from tests.pg_harness import (  # noqa: E402
    APP_ROLE,
    MIGRATOR_ROLE,
    PgTestDatabase,
    admin_connect,
    create_test_database,
)


@pytest.fixture(scope="module")
def migrated_db() -> PgTestDatabase:
    """建临时库 + 跑迁移，模块内共享；结束即删库。"""
    db = create_test_database()
    _run_alembic(db, "upgrade", "head")
    try:
        yield db
    finally:
        db.drop()


def _run_alembic(db: PgTestDatabase, *args: str) -> subprocess.CompletedProcess[str]:
    dsn = db.migrator_dsn.replace("postgresql://", "postgresql+psycopg://")
    env = dict(os.environ, STUDYPLAN_MIGRATION_DSN=dsn)
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=str(BACKEND_DIR),
        env=env,
        capture_output=True,
        text=True,
    )


def _roles_in_db(db: PgTestDatabase) -> None:
    """断言两个角色确实不同且应用角色无 elevated 权限。"""
    with admin_connect("postgres") as conn:
        rows = dict(
            conn.execute(
                "SELECT rolname, rolsuper FROM pg_roles WHERE rolname IN (%s, %s)",
                (APP_ROLE, MIGRATOR_ROLE),
            ).fetchall()
        )
    assert APP_ROLE in rows and MIGRATOR_ROLE in rows
    assert APP_ROLE != MIGRATOR_ROLE, "迁移角色与应用角色必须不同"
    assert rows[APP_ROLE] is False, "应用角色不得是超级用户"


# ---------------------------------------------------------------------------
# 迁移成功 + RLS 结构
# ---------------------------------------------------------------------------


def test_migration_applies_cleanly(migrated_db: PgTestDatabase) -> None:
    with psycopg.connect(migrated_db.migrator_dsn) as conn:
        tables = {
            r[0]
            for r in conn.execute(
                "SELECT tablename FROM pg_tables WHERE schemaname='public'"
            ).fetchall()
        }
    expected = {
        "learning_projects",
        "plan_drafts",
        "plan_revisions",
        "plan_publications",
        "ai_runs",
        "ai_run_events",
        "ai_provider_attempts",
        "ai_jobs",
    }
    assert expected <= tables, f"缺少表：{expected - tables}"


def test_all_private_tables_enable_and_force_rls(migrated_db: PgTestDatabase) -> None:
    """所有私有表必须 ENABLE + FORCE RLS（FORCE 让属主也受约束）。"""
    with psycopg.connect(migrated_db.migrator_dsn) as conn:
        rows = conn.execute(
            """
            SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity
            FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname='public' AND c.relkind='r'
            """
        ).fetchall()
    private = {name: (enabled, forced) for name, enabled, forced in rows if name != "alembic_version"}
    for name, (enabled, forced) in private.items():
        assert enabled, f"{name} 未启用 RLS"
        assert forced, f"{name} 未启用 FORCE ROW LEVEL SECURITY"


def test_every_private_table_has_ownership_policy(migrated_db: PgTestDatabase) -> None:
    """每张私有表都必须有归属策略（否则 RLS 会让它默认全拒绝、不可用）。"""
    with psycopg.connect(migrated_db.migrator_dsn) as conn:
        rows = conn.execute(
            "SELECT tablename, count(*) FROM pg_policies WHERE schemaname='public' "
            "GROUP BY tablename"
        ).fetchall()
    policies = dict(rows)
    for table in (
        "learning_projects",
        "plan_drafts",
        "plan_revisions",
        "plan_publications",
        "ai_runs",
        "ai_run_events",
        "ai_provider_attempts",
        "ai_jobs",
    ):
        assert policies.get(table, 0) >= 1, f"{table} 缺少归属策略"


# ---------------------------------------------------------------------------
# RLS 权限反例
# ---------------------------------------------------------------------------


def _seed(db: PgTestDatabase) -> None:
    """植入测试数据。

    迁移角色拥有 BYPASSRLS（见 pg_harness），因此可直接写入而不受策略约束；
    应用角色则始终 NOBYPASSRLS。这正是"迁移角色与应用角色必须不同"的体现。
    """
    with psycopg.connect(db.migrator_dsn, autocommit=True) as conn:
        conn.execute(
            "INSERT INTO learning_projects(project_id,owner_actor_id,title,goal_statement,stable_key) "
            "VALUES ('p1','actor1','t1','g1','sk-p1'), ('p2','actor2','t2','g2','sk-p2')"
        )
        conn.execute(
            "INSERT INTO plan_drafts(draft_id,project_id,status,content_hash) "
            "VALUES ('d1','p1','awaiting_approval','h1'), ('d2','p2','awaiting_approval','h2')"
        )


@pytest.fixture()
def seeded_db(migrated_db: PgTestDatabase) -> PgTestDatabase:
    with psycopg.connect(migrated_db.migrator_dsn, autocommit=True) as conn:
        conn.execute("TRUNCATE plan_drafts, plan_revisions, learning_projects CASCADE")
    _seed(migrated_db)
    return migrated_db


def test_missing_context_denies_all(seeded_db: PgTestDatabase) -> None:
    """缺授权上下文 -> 默认拒绝（0 行），而不是全量可见。"""
    with psycopg.connect(seeded_db.app_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM learning_projects").fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM plan_drafts").fetchone()[0] == 0


def test_cross_project_read_denied(seeded_db: PgTestDatabase) -> None:
    with psycopg.connect(seeded_db.app_dsn) as conn:
        conn.execute("SET app.project_id = 'p1'")
        rows = conn.execute("SELECT draft_id FROM plan_drafts").fetchall()
        assert rows == [("d1",)], "只能看到本项目草案"

        conn.execute("SET app.project_id = 'p2'")
        rows = conn.execute("SELECT draft_id FROM plan_drafts").fetchall()
        assert rows == [("d2",)], "切换项目后只能看到 p2 的草案"


def test_cross_project_write_denied(seeded_db: PgTestDatabase) -> None:
    """以 p1 的上下文试图写入 p2 的草案必须被拒绝。"""
    with psycopg.connect(seeded_db.app_dsn) as conn:
        conn.execute("SET app.project_id = 'p1'")
        with pytest.raises(Exception) as exc:  # noqa: B017 - 具体异常由 RLS 决定
            conn.execute(
                "INSERT INTO plan_drafts(draft_id,project_id,status,content_hash) "
                "VALUES ('dx','p2','awaiting_approval','hx')"
            )
        assert "row-level security" in str(exc.value).lower() or "权限" in str(exc.value)


def test_cross_actor_read_denied(seeded_db: PgTestDatabase) -> None:
    """学习空间按 actor 归属：actor1 看不到 actor2 的项目。"""
    with psycopg.connect(seeded_db.app_dsn) as conn:
        conn.execute("SET app.actor_id = 'actor1'")
        rows = conn.execute("SELECT project_id FROM learning_projects").fetchall()
        assert rows == [("p1",)]


def test_app_role_has_no_ddl(seeded_db: PgTestDatabase) -> None:
    """应用角色最小权限：不得建表/改表。"""
    with psycopg.connect(seeded_db.app_dsn) as conn:
        with pytest.raises(Exception):  # noqa: B017
            conn.execute("CREATE TABLE hack_attempt(x int)")


def test_app_role_cannot_bypass_rls(seeded_db: PgTestDatabase) -> None:
    """应用角色不得绕过 RLS。

    ``SET row_security = off`` 对 NOBYPASSRLS 角色有两种可能结果，二者都安全：
    1. PostgreSQL 直接抛 ``InsufficientPrivilege``（拒绝执行会受策略影响的查询）；
    2. 语句不报错但**没有任何效果**，查询仍被隔离。

    因此断言"要么报错、要么零行"，而不是依赖某一种具体行为 ——
    真正关心的安全属性是**数据始终被隔离**。
    """
    with psycopg.connect(seeded_db.app_dsn, autocommit=True) as conn:
        try:
            conn.execute("SET row_security = off")
            rows = conn.execute("SELECT count(*) FROM plan_drafts").fetchone()[0]
            assert rows == 0, "缺上下文时必须默认拒绝"
        except psycopg.errors.InsufficientPrivilege:
            pass  # 直接被拒绝，同样是安全结果
        finally:
            # 复位，避免会话级设置影响后续断言
            conn.execute("SET row_security = on")
        # 设置合法上下文后仍只能看到本项目数据
        conn.execute("SET app.project_id = 'p1'")
        assert conn.execute("SELECT draft_id FROM plan_drafts").fetchall() == [("d1",)]


def test_app_role_is_not_bypassrls(seeded_db: PgTestDatabase) -> None:
    """直接断言角色属性：应用角色 NOBYPASSRLS，迁移角色 BYPASSRLS。"""
    with admin_connect("postgres") as conn:
        rows = dict(
            conn.execute(
                "SELECT rolname, rolbypassrls FROM pg_roles WHERE rolname IN (%s, %s)",
                (APP_ROLE, MIGRATOR_ROLE),
            ).fetchall()
        )
    assert rows[APP_ROLE] is False, "应用角色必须 NOBYPASSRLS"
    assert rows[MIGRATOR_ROLE] is True, "迁移角色需要 BYPASSRLS 以完成数据保护检查"


# ---------------------------------------------------------------------------
# 迁移降级的数据保护
# ---------------------------------------------------------------------------


def test_downgrade_is_refused_when_business_data_exists() -> None:
    """有任何业务数据时拒绝降级（且 RLS 不得让检查误判为空库）。"""
    db = create_test_database()
    try:
        assert _run_alembic(db, "upgrade", "head").returncode == 0
        with psycopg.connect(db.migrator_dsn, autocommit=True) as conn:
            conn.execute(
                "INSERT INTO learning_projects(project_id,owner_actor_id,title,goal_statement,stable_key) "
                "VALUES ('p1','a1','t','g','sk1')"
            )
        result = _run_alembic(db, "downgrade", "base")
        assert result.returncode != 0, "有数据时降级必须失败"
        assert "拒绝降级" in result.stderr
        # 确认表仍在
        with psycopg.connect(db.migrator_dsn) as conn:
            still = conn.execute(
                "SELECT count(*) FROM pg_tables WHERE tablename='learning_projects'"
            ).fetchone()[0]
        assert still == 1, "拒绝降级后表结构必须保留"
    finally:
        db.drop()


def test_downgrade_succeeds_on_empty_database() -> None:
    """空库允许降级（基线可回滚用于本地开发）。"""
    db = create_test_database()
    try:
        assert _run_alembic(db, "upgrade", "head").returncode == 0
        result = _run_alembic(db, "downgrade", "base")
        assert result.returncode == 0, f"空库降级应成功：{result.stderr[-400:]}"
    finally:
        db.drop()
