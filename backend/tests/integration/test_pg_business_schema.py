"""B2 业务域迁移验收：0002 新表、FORCE RLS、跨项目隔离、降级数据保护。

沿用 §7 的独立临时库约束：所有操作限定在 ``studyplan_test_*``，结束即删库。
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

from tests.pg_harness import PgTestDatabase, create_test_database  # noqa: E402

#: 0002 新增的全部业务表（设计 §3）。
B2_TABLES = (
    "knowledge_nodes",
    "knowledge_relations",
    "learning_units",
    "unit_node_links",
    "plan_stages",
    "plan_unit_links",
    "plan_task_links",
    "unit_progress",
    "practice_projects",
    "practice_tasks",
    "task_knowledge_links",
    "practice_submissions",
    "acceptance_reviews",
    "prompt_revisions",
    "prompt_reviews",
    "summary_attempts",
    "summary_reviews",
    "preferences",
    "preference_overrides",
    "resource_records",
    "node_resource_links",
)


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


@pytest.fixture(scope="module")
def migrated_db() -> PgTestDatabase:
    db = create_test_database(prefix="studyplan_test_b2")
    assert _run_alembic(db, "upgrade", "head").returncode == 0, "迁移必须可干净执行"
    try:
        yield db
    finally:
        db.drop()


def _tables(db: PgTestDatabase) -> set[str]:
    with psycopg.connect(db.migrator_dsn) as conn:
        return {
            r[0]
            for r in conn.execute(
                "SELECT tablename FROM pg_tables WHERE schemaname='public'"
            ).fetchall()
        }


def test_b2_migration_creates_all_business_tables(migrated_db: PgTestDatabase) -> None:
    tables = _tables(migrated_db)
    missing = set(B2_TABLES) - tables
    assert not missing, f"缺少 B2 业务表：{missing}"
    # 0001 的骨架表仍在（不得被改写）
    assert {"plan_drafts", "plan_revisions", "plan_publications"} <= tables


def test_b2_tables_enable_and_force_rls(migrated_db: PgTestDatabase) -> None:
    with psycopg.connect(migrated_db.migrator_dsn) as conn:
        rows = conn.execute(
            """
            SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity
            FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname='public' AND c.relkind='r' AND c.relname = ANY(%s)
            """,
            (list(B2_TABLES),),
        ).fetchall()
    assert len(rows) == len(B2_TABLES), "部分 B2 表不存在"
    bad = [(n, e, f) for n, e, f in rows if not (e and f)]
    assert not bad, f"以下表未 ENABLE+FORCE RLS：{bad}"


def test_b2_tables_have_ownership_policy(migrated_db: PgTestDatabase) -> None:
    with psycopg.connect(migrated_db.migrator_dsn) as conn:
        policies = dict(
            conn.execute(
                "SELECT tablename, count(*) FROM pg_policies WHERE schemaname='public' "
                "GROUP BY tablename"
            ).fetchall()
        )
    missing = [t for t in B2_TABLES if policies.get(t, 0) < 1]
    assert not missing, f"以下 B2 表缺少归属策略：{missing}"


def test_b2_cross_project_isolation(migrated_db: PgTestDatabase) -> None:
    """以应用角色验证新表的跨项目隔离（缺上下文默认拒绝、跨项目读写拒绝）。"""
    with psycopg.connect(migrated_db.migrator_dsn, autocommit=True) as conn:
        conn.execute("TRUNCATE knowledge_nodes, learning_projects CASCADE")
        conn.execute(
            "INSERT INTO learning_projects(project_id,owner_actor_id,title,goal_statement,stable_key) "
            "VALUES ('p1','a1','t1','g1','sk-p1'), ('p2','a2','t2','g2','sk-p2')"
        )
        conn.execute(
            "INSERT INTO knowledge_nodes(node_id,project_id,stable_key,title,node_type,source_status) "
            "VALUES ('n1','p1','sk-n1','N1','concept','ai_draft'), "
            "('n2','p2','sk-n2','N2','concept','ai_draft')"
        )

    with psycopg.connect(migrated_db.app_dsn) as conn:
        # 缺上下文 → 默认拒绝
        assert conn.execute("SELECT count(*) FROM knowledge_nodes").fetchone()[0] == 0
        # p1 上下文只能看到 p1
        conn.execute("SET app.project_id = 'p1'")
        assert conn.execute("SELECT node_id FROM knowledge_nodes").fetchall() == [("n1",)]
        # 以 p1 上下文写 p2 的数据必须被拒绝
        with pytest.raises(Exception) as exc:  # noqa: B017 - 具体异常由 RLS 决定
            conn.execute(
                "INSERT INTO knowledge_nodes(node_id,project_id,stable_key,title,node_type,source_status) "
                "VALUES ('nx','p2','sk-nx','NX','concept','ai_draft')"
            )
        assert "row-level security" in str(exc.value).lower() or "权限" in str(exc.value)


def test_b2_downgrade_refused_when_data_exists() -> None:
    """0002 有数据时降级到 0001 必须被拒绝，且表结构保留。"""
    db = create_test_database(prefix="studyplan_test_b2down")
    try:
        assert _run_alembic(db, "upgrade", "head").returncode == 0
        with psycopg.connect(db.migrator_dsn, autocommit=True) as conn:
            conn.execute(
                "INSERT INTO learning_projects(project_id,owner_actor_id,title,goal_statement,stable_key) "
                "VALUES ('p1','a1','t','g','sk1')"
            )
            conn.execute(
                "INSERT INTO knowledge_nodes(node_id,project_id,stable_key,title,node_type,source_status) "
                "VALUES ('n1','p1','sk-n1','N','concept','ai_draft')"
            )
        result = _run_alembic(db, "downgrade", "0001")
        assert result.returncode != 0, "有数据时降级必须失败"
        assert "拒绝降级" in result.stderr
        assert "knowledge_nodes" in _tables(db), "拒绝降级后表结构必须保留"
    finally:
        db.drop()


def test_b2_downgrade_succeeds_on_empty() -> None:
    """空库允许 0002 → 0001 降级。"""
    db = create_test_database(prefix="studyplan_test_b2empty")
    try:
        assert _run_alembic(db, "upgrade", "head").returncode == 0
        result = _run_alembic(db, "downgrade", "0001")
        assert result.returncode == 0, f"空库降级应成功：{result.stderr[-400:]}"
        tables = _tables(db)
        assert "knowledge_nodes" not in tables, "降级后 0002 表应被删除"
        assert "plan_revisions" in tables, "0001 骨架表应保留"
    finally:
        db.drop()
