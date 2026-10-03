"""B2-C 契约收口迁移（0003）验收：复合 project FK、字段对齐、新表与只读公共资源。

沿用 §7 的独立临时库约束：所有操作限定在 ``studyplan_test_*``，结束即删库。

本文件覆盖 Goal §「迁移 0003」的硬要求：

1. **复合 project FK 反例**：数据库层必须禁止「本项目引用别的项目的实体」——
   且该约束在**拥有 BYPASSRLS 的迁移角色**下依然生效（证明它来自 FK 而非 RLS）。
2. **domain/schema 字段对齐矩阵**：逐个领域实体验证「领域字段 → 表列」存在，
   防止后续再出现静默错位。
3. **新表 RLS 与只读公共资源**：私人表项目隔离；公共表应用角色只读。
4. **降级数据保护**：新表有数据即拒绝降级。
"""

from __future__ import annotations

import dataclasses
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

#: 0003 新增的表。
NEW_TABLES = (
    "domain_packs",
    "public_resource_sources",
    "public_resource_sections",
    "stage_resource_assignments",
    "knowledge_extensions",
)

#: 项目作用域私人新表。
PRIVATE_NEW_TABLES = ("knowledge_extensions", "stage_resource_assignments")

#: 公共只读新表。
PUBLIC_NEW_TABLES = ("domain_packs", "public_resource_sources", "public_resource_sections")


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
    db = create_test_database(prefix="studyplan_test_b2c")
    assert _run_alembic(db, "upgrade", "head").returncode == 0, "0003 迁移必须可干净执行"
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


def _columns(db: PgTestDatabase, table: str) -> set[str]:
    with psycopg.connect(db.migrator_dsn) as conn:
        return {
            r[0]
            for r in conn.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema='public' AND table_name=%s",
                (table,),
            ).fetchall()
        }


def _seed_two_projects(db: PgTestDatabase) -> None:
    """以迁移角色（BYPASSRLS）写入两个项目的对照数据。

    刻意用迁移角色：这样「跨项目引用被拒」只可能来自 FK，而非 RLS 过滤。
    """
    with psycopg.connect(db.migrator_dsn, autocommit=True) as conn:
        conn.execute("TRUNCATE learning_projects CASCADE")
        conn.execute(
            "INSERT INTO learning_projects(project_id,owner_actor_id,title,goal_statement,stable_key) "
            "VALUES ('p1','a1','t1','g1','sk-p1'), ('p2','a2','t2','g2','sk-p2')"
        )


# --------------------------------------------------------------------- 结构存在性


def test_0003_creates_new_tables(migrated_db: PgTestDatabase) -> None:
    tables = _tables(migrated_db)
    missing = set(NEW_TABLES) - tables
    assert not missing, f"缺少 0003 新表：{missing}"
    # 0001/0002 的表不得被改写
    assert {"plan_revisions", "plan_publications", "knowledge_nodes"} <= tables


def test_0003_aligns_domain_fields(migrated_db: PgTestDatabase) -> None:
    """领域有、0002 表里没有的字段必须在 0003 补齐。"""
    expected = {
        "learning_units": {"objectives"},
        "plan_stages": {"section_kind", "objective"},
        "practice_projects": {"title", "version"},
        "practice_tasks": {"title", "stage_index"},
        "resource_records": {"source_note"},
        "plan_revisions": {"source_pack_key", "source_pack_version"},
        "plan_publications": {
            "idempotency_key",
            "body_fingerprint",
            "structure_fingerprint",
            "revision",
        },
    }
    for table, cols in expected.items():
        missing = cols - _columns(migrated_db, table)
        assert not missing, f"{table} 缺少对齐列：{missing}"


def test_0003_relaxes_legacy_publication_columns(migrated_db: PgTestDatabase) -> None:
    """幂等作用域改为 (project_id, idempotency_key) 后，遗留 run_id/operation_key 放开 NOT NULL。"""
    with psycopg.connect(migrated_db.migrator_dsn) as conn:
        rows = dict(
            conn.execute(
                "SELECT column_name, is_nullable FROM information_schema.columns "
                "WHERE table_name='plan_publications' AND column_name IN ('run_id','operation_key')"
            ).fetchall()
        )
        idx = conn.execute(
            "SELECT indexdef FROM pg_indexes WHERE schemaname='public' "
            "AND indexname='plan_publications_project_idem_unique'"
        ).fetchone()
    assert rows == {"run_id": "YES", "operation_key": "YES"}, rows
    assert idx is not None, "缺少 (project_id, idempotency_key) 唯一索引"
    assert "idempotency_key" in idx[0]


# ----------------------------------------------------------------- 复合 FK 反例/正例


def test_composite_fk_blocks_cross_project_knowledge_relation(
    migrated_db: PgTestDatabase,
) -> None:
    """反例：p1 的关系不得引用 p2 的知识节点（即使写入者拥有 BYPASSRLS）。"""
    _seed_two_projects(migrated_db)
    with psycopg.connect(migrated_db.migrator_dsn, autocommit=True) as conn:
        conn.execute(
            "INSERT INTO knowledge_nodes(node_id,project_id,stable_key,title,node_type,source_status) "
            "VALUES ('n1','p1','sk-n1','N1','concept','ai_draft'), "
            "('n1b','p1','sk-n1b','N1b','concept','ai_draft'), "
            "('n2','p2','sk-n2','N2','concept','ai_draft')"
        )
        # 正例：同项目关系允许
        conn.execute(
            "INSERT INTO knowledge_relations(relation_id,project_id,from_node_id,to_node_id,relation_type) "
            "VALUES ('r1','p1','n1','n1b','related')"
        )
        assert conn.execute(
            "SELECT count(*) FROM knowledge_relations WHERE project_id='p1'"
        ).fetchone()[0] == 1
        # 反例：跨项目引用必须被复合 FK 拒绝
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            conn.execute(
                "INSERT INTO knowledge_relations"
                "(relation_id,project_id,from_node_id,to_node_id,relation_type) "
                "VALUES ('r2','p1','n1','n2','related')"
            )


def test_composite_fk_blocks_cross_project_unit_node_link(
    migrated_db: PgTestDatabase,
) -> None:
    """反例：p1 的单元不得挂到 p2 的知识节点。"""
    _seed_two_projects(migrated_db)
    with psycopg.connect(migrated_db.migrator_dsn, autocommit=True) as conn:
        conn.execute(
            "INSERT INTO knowledge_nodes(node_id,project_id,stable_key,title,node_type,source_status) "
            "VALUES ('n1','p1','sk-n1','N1','concept','ai_draft'), "
            "('n2','p2','sk-n2','N2','concept','ai_draft')"
        )
        conn.execute(
            "INSERT INTO learning_units(unit_id,project_id,stable_key,title,objectives,rubric) "
            "VALUES ('u1','p1','sk-u1','U1','[]'::jsonb,'{}'::jsonb)"
        )
        # 正例：同项目链接允许
        conn.execute(
            "INSERT INTO unit_node_links(link_id,project_id,unit_id,node_id,order_index,role) "
            "VALUES ('l1','p1','u1','n1',0,'core')"
        )
        # 反例：跨项目节点必须被拒绝
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            conn.execute(
                "INSERT INTO unit_node_links(link_id,project_id,unit_id,node_id,order_index,role) "
                "VALUES ('l2','p1','u1','n2',1,'core')"
            )


def test_composite_fk_blocks_cross_project_practice_task(
    migrated_db: PgTestDatabase,
) -> None:
    """反例：p1 的任务不得挂到 p2 的实践项目。"""
    _seed_two_projects(migrated_db)
    with psycopg.connect(migrated_db.migrator_dsn, autocommit=True) as conn:
        conn.execute(
            "INSERT INTO practice_projects"
            "(practice_project_id,project_id,title,idea,status) "
            "VALUES ('pp1','p1','PP1','idea one','idea'), ('pp2','p2','PP2','idea two','idea')"
        )
        # 正例
        conn.execute(
            "INSERT INTO practice_tasks"
            "(task_id,project_id,practice_project_id,stable_key,title,goal,acceptance,status) "
            "VALUES ('tk1','p1','pp1','sk-tk1','T1','g1','[\"a\"]'::jsonb,'pending')"
        )
        # 反例
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            conn.execute(
                "INSERT INTO practice_tasks"
                "(task_id,project_id,practice_project_id,stable_key,title,goal,acceptance,status) "
                "VALUES ('tk2','p1','pp2','sk-tk2','T2','g2','[\"a\"]'::jsonb,'pending')"
            )


# ------------------------------------------------------------------ RLS 与只读公共


def test_0003_new_tables_force_rls(migrated_db: PgTestDatabase) -> None:
    with psycopg.connect(migrated_db.migrator_dsn) as conn:
        rows = conn.execute(
            """
            SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity
            FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname='public' AND c.relkind='r' AND c.relname = ANY(%s)
            """,
            (list(NEW_TABLES),),
        ).fetchall()
    assert len(rows) == len(NEW_TABLES), "部分新表不存在"
    bad = [(n, e, f) for n, e, f in rows if not (e and f)]
    assert not bad, f"以下新表未 ENABLE+FORCE RLS：{bad}"


def test_0003_policies_match_visibility(migrated_db: PgTestDatabase) -> None:
    with psycopg.connect(migrated_db.migrator_dsn) as conn:
        policies = dict(
            conn.execute(
                "SELECT tablename, policyname FROM pg_policies WHERE schemaname='public' "
                "AND tablename = ANY(%s)",
                (list(NEW_TABLES),),
            ).fetchall()
        )
    for table in PRIVATE_NEW_TABLES:
        assert policies.get(table) == f"{table}_project_scope", policies.get(table)
    for table in PUBLIC_NEW_TABLES:
        assert policies.get(table) == f"{table}_public_read", policies.get(table)


def test_0003_public_tables_read_only_for_app_role(migrated_db: PgTestDatabase) -> None:
    """公共表：应用角色可读，但写入被权限拒绝（无 INSERT 授权）。"""
    # autocommit：失败语句不应中断后续独立断言（否则事务进入 aborted 状态）。
    with psycopg.connect(migrated_db.app_dsn, autocommit=True) as conn:
        # 可读（策略 FOR SELECT USING (true)）
        assert conn.execute("SELECT count(*) FROM domain_packs").fetchone()[0] == 0
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute(
                "INSERT INTO domain_packs"
                "(pack_key,version,status,supported_scope,title) "
                "VALUES ('pk',1,'draft','scope','T')"
            )
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("DELETE FROM public_resource_sources")


def test_0003_private_tables_cross_project_isolation(migrated_db: PgTestDatabase) -> None:
    """私人新表：缺上下文默认拒绝；跨项目读写拒绝。

    0004 给 ``knowledge_extensions`` 加了归属 FK（必须属于某个已发布版本的
    某个阶段），因此这里先植入最小父行（项目 → 版本 → 阶段）。
    """
    with psycopg.connect(migrated_db.migrator_dsn, autocommit=True) as conn:
        conn.execute(
            "INSERT INTO learning_projects(project_id,owner_actor_id,title,goal_statement,stable_key) "
            "VALUES ('p1','a1','t1','g1','sk-p1'), ('p2','a2','t2','g2','sk-p2') "
            "ON CONFLICT DO NOTHING"
        )
        for project, stage in (("p1", "stg1"), ("p2", "stg2")):
            plan = f"pln_{project}"
            conn.execute(
                "INSERT INTO plan_revisions"
                "(plan_id,project_id,revision,goal_snapshot,status,structure) "
                "VALUES (%s,%s,1,'目标','approved','{}'::jsonb) ON CONFLICT DO NOTHING",
                (plan, project),
            )
            conn.execute(
                "INSERT INTO plan_stages"
                "(stage_id,project_id,plan_id,stable_key,title,section_kind,objective,order_index) "
                "VALUES (%s,%s,%s,%s,'阶段','core','',0) ON CONFLICT DO NOTHING",
                (stage, project, plan, f"sk-{stage}"),
            )
        conn.execute(
            "INSERT INTO knowledge_extensions"
            "(extension_id,project_id,plan_id,stage_id,topic) "
            "VALUES ('e1','p1','pln_p1','stg1','topic one'), "
            "('e2','p2','pln_p2','stg2','topic two') "
            "ON CONFLICT DO NOTHING"
        )

    with psycopg.connect(migrated_db.app_dsn) as conn:
        # 缺上下文 → 默认拒绝
        assert conn.execute("SELECT count(*) FROM knowledge_extensions").fetchone()[0] == 0
        conn.execute("SET app.project_id = 'p1'")
        assert conn.execute(
            "SELECT extension_id FROM knowledge_extensions"
        ).fetchall() == [("e1",)]
        # 以 p1 上下文写 p2 必须被拒
        with pytest.raises(Exception) as exc:  # noqa: B017 - 具体异常由 RLS 决定
            conn.execute(
                "INSERT INTO knowledge_extensions"
                "(extension_id,project_id,plan_id,stage_id,topic) "
                "VALUES ('ex','p2','pln_p2','stg2','topic x')"
            )
        assert "row-level security" in str(exc.value).lower() or "权限" in str(exc.value)


# ------------------------------------------------------------------- 降级数据保护


def test_0003_downgrade_refused_when_new_table_has_data() -> None:
    db = create_test_database(prefix="studyplan_test_b2cdown")
    try:
        assert _run_alembic(db, "upgrade", "head").returncode == 0
        with psycopg.connect(db.migrator_dsn, autocommit=True) as conn:
            conn.execute(
                "INSERT INTO public_resource_sources"
                "(source_id,canonical_url,title) "
                "VALUES ('s1','https://example.com/course','Course')"
            )
        result = _run_alembic(db, "downgrade", "0002")
        assert result.returncode != 0, "新表有数据时降级必须失败"
        assert "拒绝降级" in result.stderr
        assert "public_resource_sources" in _tables(db), "拒绝降级后表结构必须保留"
    finally:
        db.drop()


def test_0003_downgrade_succeeds_on_empty() -> None:
    db = create_test_database(prefix="studyplan_test_b2cempty")
    try:
        assert _run_alembic(db, "upgrade", "head").returncode == 0
        result = _run_alembic(db, "downgrade", "0002")
        assert result.returncode == 0, f"空库降级应成功：{result.stderr[-400:]}"
        tables = _tables(db)
        for table in NEW_TABLES:
            assert table not in tables, f"降级后 {table} 应被删除"
        # 0002 表与字段对齐前的列应保留/复原
        assert "knowledge_nodes" in tables
        assert "objectives" not in _columns(db, "learning_units")
        assert "section_kind" not in _columns(db, "plan_stages")
        assert "idempotency_key" not in _columns(db, "plan_publications")
    finally:
        db.drop()


# ----------------------------------------------------------- domain/schema 对齐矩阵


def _entity_table_pairs() -> list[tuple[type, str]]:
    """领域实体类 -> 表名（仅含**标量字段落列**的实体）。"""
    from app.domain.catalog.models import KnowledgeNode, LearningUnit
    from app.domain.domain_packs.models import DomainPack
    from app.domain.planning.models import PlanStage, PublishRecord
    from app.domain.practice.models import PracticeProject, PracticeTask
    from app.domain.resources.curation import (
        KnowledgeExtension,
        PublicResourceSection,
        PublicResourceSource,
        StageResourceAssignment,
    )
    from app.domain.resources.models import ResourceRecord

    return [
        (KnowledgeNode, "knowledge_nodes"),
        (LearningUnit, "learning_units"),
        (PlanStage, "plan_stages"),
        (PracticeProject, "practice_projects"),
        (PracticeTask, "practice_tasks"),
        (ResourceRecord, "resource_records"),
        (PublicResourceSource, "public_resource_sources"),
        (PublicResourceSection, "public_resource_sections"),
        (StageResourceAssignment, "stage_resource_assignments"),
        (KnowledgeExtension, "knowledge_extensions"),
        (DomainPack, "domain_packs"),
        (PublishRecord, "plan_publications"),
    ]


#: 不落成同名列的领域字段：复合结构存于 jsonb（`structure`/`payload`），
#: 或为纯派生/时间字段。其 jsonb 载体列在 `test_composite_structure_carrier_columns_exist` 断言。
_JSONB_FIELD_CARRIERS = {
    "PlanStage": {"learning_guidance": ("plan_revisions", "structure")},
    "ResourceRecord": {"discovery": ("learning_resource_selections", "resource_snapshot")},
}
_NON_COLUMN_FIELDS: dict[str, set[str]] = {
    entity: set(fields) for entity, fields in _JSONB_FIELD_CARRIERS.items()
}


@pytest.mark.parametrize(
    "entity_cls,table",
    _entity_table_pairs(),
    ids=[c.__name__ for c, _ in _entity_table_pairs()],
)
def test_domain_entity_fields_have_columns(
    migrated_db: PgTestDatabase, entity_cls: type, table: str
) -> None:
    """domain/schema 对齐矩阵：标量字段落列，复合字段须有明确 JSONB 载体。

    新增字段而忘了迁移时，本测试会失败——这是防止再次出现 P1-03 的护栏。
    """
    columns = _columns(migrated_db, table)
    skip = _NON_COLUMN_FIELDS.get(entity_cls.__name__, set())
    missing = [
        f.name
        for f in dataclasses.fields(entity_cls)
        if f.name not in skip and f.name not in columns
    ]
    assert not missing, (
        f"{entity_cls.__name__} 的字段 {missing} 在表 {table} 无对应列（domain/schema 错位）"
    )


def test_composite_structure_carrier_columns_exist(migrated_db: PgTestDatabase) -> None:
    """``PlanRevision``/``PlanDraft`` 的复合结构存于 jsonb，载体列必须存在。"""
    assert "structure" in _columns(migrated_db, "plan_revisions")
    assert "payload" in _columns(migrated_db, "plan_drafts")
    # Optional nested values use existing snapshots, rather than new scalar
    # columns. Check their actual JSONB carriers instead of silently skipping.
    with psycopg.connect(migrated_db.migrator_dsn) as conn:
        for fields in _JSONB_FIELD_CARRIERS.values():
            for table, column in fields.values():
                row = conn.execute(
                    "SELECT data_type FROM information_schema.columns "
                    "WHERE table_schema='public' AND table_name=%s AND column_name=%s",
                    (table, column),
                ).fetchone()
                assert row == ("jsonb",), f"{table}.{column} must carry the nested snapshot"
