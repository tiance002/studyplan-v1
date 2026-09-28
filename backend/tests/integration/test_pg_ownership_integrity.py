"""B2-V §五：计划快照的**归属完整性**数据库反例（真实 PostgreSQL）。

## 为什么必须用**迁移角色**（BYPASSRLS）来写这些反例

RLS 只过滤**行**；若用应用角色插入跨项目数据，失败可能来自 RLS 而不是约束，
就无法证明「约束真的在起作用」。因此本文件一律用**迁移角色**（``BYPASSRLS``，
schema 属主）直连写入，任何被拒绝都只能归因于 **FK / UNIQUE 约束本身**。

覆盖四类必须被数据库拒绝的错误：

1. **同项目内跨计划错挂**：链接的 ``plan_id`` 与 ``stage_id`` 不属于同一版本；
2. **指向不存在的阶段**；
3. **孤儿资源分配 / 扩展**：``plan_id`` 不对应任何版本；
4. **扩展绑错单元**、**任务-知识关联指向别的计划的实践任务**、
   **资源来源不存在**。

所有操作限定在 ``studyplan_test_*`` 临时库，结束即删库。
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

PROJECT = "p1"
OTHER_PROJECT = "p2"


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
def db() -> PgTestDatabase:
    """建库 + 迁移 + 最小可用种子（两个项目，各自一个已发布版本）。"""
    database = create_test_database(prefix="studyplan_test_b2v_own")
    assert _run_alembic(database, "upgrade", "head").returncode == 0
    _seed(database)
    try:
        yield database
    finally:
        database.drop()


def _seed(database: PgTestDatabase) -> None:
    with psycopg.connect(database.migrator_dsn, autocommit=True) as conn:
        conn.execute(
            "INSERT INTO learning_projects(project_id,owner_actor_id,title,goal_statement,stable_key) "
            "VALUES ('p1','a1','t1','g1','sk-p1'), ('p2','a2','t2','g2','sk-p2')"
        )
        for project in (PROJECT, OTHER_PROJECT):
            conn.execute(
                "INSERT INTO learning_units(unit_id,project_id,stable_key,title) "
                "VALUES (%s,%s,%s,'单元')",
                (f"unt_{project}", project, f"sk-unt-{project}"),
            )
            # 一个**未挂载**的备用单元：用于「跨计划错挂」反例（避免撞 UNIQUE）。
            conn.execute(
                "INSERT INTO learning_units(unit_id,project_id,stable_key,title) "
                "VALUES (%s,%s,%s,'备用单元')",
                (f"unt_{project}_alt", project, f"sk-unt-{project}-alt"),
            )
            conn.execute(
                "INSERT INTO knowledge_nodes(node_id,project_id,stable_key,title,node_type,source_status) "
                "VALUES (%s,%s,%s,'节点','concept','ai_draft')",
                (f"nod_{project}", project, f"sk-nod-{project}"),
            )
            conn.execute(
                "INSERT INTO practice_projects(practice_project_id,project_id,title,idea,status) "
                "VALUES (%s,%s,'实践项目','做一个工具','idea')",
                (f"ppj_{project}", project),
            )
            conn.execute(
                "INSERT INTO practice_tasks"
                "(task_id,project_id,practice_project_id,stable_key,title,goal,acceptance,status) "
                "VALUES (%s,%s,%s,%s,'任务','目标','[\"可验收\"]'::jsonb,'pending')",
                (f"ptk_{project}", project, f"ppj_{project}", f"sk-ptk-{project}"),
            )
            # 一个**未被任何计划挂载**的任务：用于「关联到本计划未挂载任务」反例。
            conn.execute(
                "INSERT INTO practice_tasks"
                "(task_id,project_id,practice_project_id,stable_key,title,goal,acceptance,status) "
                "VALUES (%s,%s,%s,%s,'未挂载任务','目标','[\"可验收\"]'::jsonb,'pending')",
                (
                    f"ptk_{project}_extra",
                    project,
                    f"ppj_{project}",
                    f"sk-ptk-{project}-extra",
                ),
            )
            # 两个版本：v1 与 v2（用于「跨计划/跨版本错挂」反例）。
            for rev in (1, 2):
                plan_id = f"pln_{project}_v{rev}"
                conn.execute(
                    "INSERT INTO plan_revisions"
                    "(plan_id,project_id,revision,goal_snapshot,status,structure) "
                    "VALUES (%s,%s,%s,'目标','superseded','{}'::jsonb)",
                    (plan_id, project, rev),
                )
                conn.execute(
                    "INSERT INTO plan_stages"
                    "(stage_id,project_id,plan_id,stable_key,title,section_kind,objective,order_index) "
                    "VALUES (%s,%s,%s,%s,'阶段','core','',0)",
                    (f"stg_{project}_v{rev}", project, plan_id, f"sk-stg-{rev}"),
                )
                conn.execute(
                    "INSERT INTO plan_unit_links"
                    "(link_id,project_id,plan_id,stage_id,unit_id,order_index) "
                    "VALUES (%s,%s,%s,%s,%s,0)",
                    (f"lnk_{project}_v{rev}", project, plan_id, f"stg_{project}_v{rev}", f"unt_{project}"),
                )
                conn.execute(
                    "INSERT INTO plan_task_links"
                    "(link_id,project_id,plan_id,stage_id,task_id,order_index) "
                    "VALUES (%s,%s,%s,%s,%s,0)",
                    (f"tlk_{project}_v{rev}", project, plan_id, f"stg_{project}_v{rev}", f"ptk_{project}"),
                )
        # 公共资源来源与章节（source_ref FK 的合法目标）。
        conn.execute(
            "INSERT INTO public_resource_sources"
            "(source_id,canonical_url,title) VALUES ('src_ok','https://example.com/a','示例')"
        )
        conn.execute(
            "INSERT INTO public_resource_sections"
            "(section_id,source_id,order_index,title,url) "
            "VALUES ('sec_ok','src_ok',0,'第一章','https://example.com/a#1')"
        )


def _insert(database: PgTestDatabase, sql: str, params: tuple[object, ...]) -> None:
    with psycopg.connect(database.migrator_dsn, autocommit=True) as conn:
        conn.execute(sql, params)


# --------------------------------------------------------------------- 1) 跨计划错挂


def test_unit_link_cannot_mix_plan_and_stage(db: PgTestDatabase) -> None:
    """p1 的 v1 链接指向 **v2** 的阶段 → 复合 FK 拒绝（同项目内跨计划错挂）。"""
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        _insert(
            db,
            "INSERT INTO plan_unit_links"
            "(link_id,project_id,plan_id,stage_id,unit_id,order_index) "
            "VALUES ('lnk_bad1','p1','pln_p1_v1','stg_p1_v2','unt_p1_alt',0)",
            (),
        )


def test_task_link_cannot_mix_plan_and_stage(db: PgTestDatabase) -> None:
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        _insert(
            db,
            "INSERT INTO plan_task_links"
            "(link_id,project_id,plan_id,stage_id,task_id,order_index) "
            "VALUES ('tlk_bad1','p1','pln_p1_v1','stg_p1_v2','ptk_p1_extra',0)",
            (),
        )


def test_resource_assignment_cannot_mix_plan_and_stage(db: PgTestDatabase) -> None:
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        _insert(
            db,
            "INSERT INTO stage_resource_assignments"
            "(assignment_id,project_id,plan_id,stage_id,role,source_ref,section_refs,order_index) "
            "VALUES ('asg_bad1','p1','pln_p1_v1','stg_p1_v2','primary','src_ok','[]'::jsonb,0)",
            (),
        )


def test_extension_cannot_mix_plan_and_stage(db: PgTestDatabase) -> None:
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        _insert(
            db,
            "INSERT INTO knowledge_extensions"
            "(extension_id,project_id,plan_id,stage_id,topic) "
            "VALUES ('ext_bad1','p1','pln_p1_v1','stg_p1_v2','主题')",
            (),
        )


def test_cross_project_stage_reference_is_rejected(db: PgTestDatabase) -> None:
    """p1 的计划引用 **p2** 的阶段（stage_id 全局主键但项目不同）→ 拒绝。"""
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        _insert(
            db,
            "INSERT INTO plan_unit_links"
            "(link_id,project_id,plan_id,stage_id,unit_id,order_index) "
            "VALUES ('lnk_bad2','p1','pln_p1_v1','stg_p2_v1','unt_p1_alt',0)",
            (),
        )


# --------------------------------------------------------------------- 2) 不存在的阶段


def test_link_to_unknown_stage_is_rejected(db: PgTestDatabase) -> None:
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        _insert(
            db,
            "INSERT INTO plan_unit_links"
            "(link_id,project_id,plan_id,stage_id,unit_id,order_index) "
            "VALUES ('lnk_bad3','p1','pln_p1_v1','stg_does_not_exist','unt_p1_alt',0)",
            (),
        )


def test_stage_of_unknown_plan_is_rejected(db: PgTestDatabase) -> None:
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        _insert(
            db,
            "INSERT INTO plan_stages"
            "(stage_id,project_id,plan_id,stable_key,title,section_kind,objective,order_index) "
            "VALUES ('stg_orphan','p1','pln_missing','sk','阶段','core','',0)",
            (),
        )


# --------------------------------------------------------------------- 3) 孤儿快照


def test_orphan_resource_assignment_is_rejected(db: PgTestDatabase) -> None:
    """``plan_id`` 不对应任何版本 → 孤儿资源分配被拒绝。"""
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        _insert(
            db,
            "INSERT INTO stage_resource_assignments"
            "(assignment_id,project_id,plan_id,stage_id,role,source_ref,section_refs,order_index) "
            "VALUES ('asg_orphan','p1','pln_missing','stg_p1_v1','primary','src_ok','[]'::jsonb,0)",
            (),
        )


def test_orphan_extension_is_rejected(db: PgTestDatabase) -> None:
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        _insert(
            db,
            "INSERT INTO knowledge_extensions"
            "(extension_id,project_id,plan_id,stage_id,topic) "
            "VALUES ('ext_orphan','p1','pln_missing','stg_p1_v1','主题')",
            (),
        )


# --------------------------------------------------------------------- 4) 绑错实体


def test_extension_bound_to_foreign_unit_is_rejected(db: PgTestDatabase) -> None:
    """扩展绑定的单元必须是**本计划已挂载**的单元（v1 只挂了 unt_p1）。"""
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        _insert(
            db,
            "INSERT INTO knowledge_extensions"
            "(extension_id,project_id,plan_id,stage_id,unit_id,topic) "
            "VALUES ('ext_badunit','p1','pln_p1_v1','stg_p1_v1','unt_p2','主题')",
            (),
        )


def test_task_knowledge_link_requires_task_in_same_plan(db: PgTestDatabase) -> None:
    """任务-知识关联的任务必须是**本计划已挂载**的实践任务。

    ``ptk_p1_extra`` 属于本项目但**未**被 ``pln_p1_v1`` 挂载 → 必须被拒绝。
    """
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        _insert(
            db,
            "INSERT INTO plan_task_knowledge_links"
            "(link_id,project_id,plan_id,task_id,node_id,role,order_index) "
            "VALUES ('tkl_bad','p1','pln_p1_v1','ptk_p1_extra','nod_p1','core',0)",
            (),
        )


def test_task_knowledge_link_rejects_foreign_node(db: PgTestDatabase) -> None:
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        _insert(
            db,
            "INSERT INTO plan_task_knowledge_links"
            "(link_id,project_id,plan_id,task_id,node_id,role,order_index) "
            "VALUES ('tkl_bad2','p1','pln_p1_v1','ptk_p1','nod_p2','core',0)",
            (),
        )


def test_resource_source_ref_must_exist(db: PgTestDatabase) -> None:
    """``source_ref`` 必须指向真实存在的公共来源（不存在的来源被拒绝）。"""
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        _insert(
            db,
            "INSERT INTO stage_resource_assignments"
            "(assignment_id,project_id,plan_id,stage_id,role,source_ref,section_refs,order_index) "
            "VALUES ('asg_badsrc','p1','pln_p1_v1','stg_p1_v1','primary','src_missing','[]'::jsonb,0)",
            (),
        )


# --------------------------------------------------------------------- 合法路径不误伤


def test_valid_rows_are_accepted(db: PgTestDatabase) -> None:
    """合法归属必须能写入（约束不能把正常数据也挡掉）。"""
    _insert(
        db,
        "INSERT INTO stage_resource_assignments"
        "(assignment_id,project_id,plan_id,stage_id,role,source_ref,section_refs,order_index) "
        "VALUES ('asg_ok','p1','pln_p1_v1','stg_p1_v1','primary','src_ok','[\"sec_ok\"]'::jsonb,0)",
        (),
    )
    # 无核验来源 = NULL（不是空串）
    _insert(
        db,
        "INSERT INTO stage_resource_assignments"
        "(assignment_id,project_id,plan_id,stage_id,role,source_ref,section_refs,"
        "fallback_search_terms,order_index) "
        "VALUES ('asg_ok_null','p1','pln_p1_v1','stg_p1_v1','primary',NULL,'[]'::jsonb,"
        "'[\"搜索建议\"]'::jsonb,1)",
        (),
    )
    _insert(
        db,
        "INSERT INTO knowledge_extensions"
        "(extension_id,project_id,plan_id,stage_id,unit_id,topic) "
        "VALUES ('ext_ok','p1','pln_p1_v1','stg_p1_v1','unt_p1','主题')",
        (),
    )
    _insert(
        db,
        "INSERT INTO plan_task_knowledge_links"
        "(link_id,project_id,plan_id,task_id,node_id,role,order_index) "
        "VALUES ('tkl_ok','p1','pln_p1_v1','ptk_p1','nod_p1','core',0)",
        (),
    )
    with psycopg.connect(db.migrator_dsn) as conn:
        assert conn.execute(
            "SELECT count(*) FROM stage_resource_assignments WHERE project_id='p1'"
        ).fetchone()[0] == 2
        assert conn.execute(
            "SELECT count(*) FROM plan_task_knowledge_links WHERE project_id='p1'"
        ).fetchone()[0] == 1


def test_downgrade_0004_is_blocked_when_new_table_has_rows(db: PgTestDatabase) -> None:
    """新表有行时必须拒绝降级（数据保护）。"""
    _insert(
        db,
        "INSERT INTO plan_task_knowledge_links"
        "(link_id,project_id,plan_id,task_id,node_id,role,order_index) "
        "VALUES ('tkl_downgrade','p1','pln_p1_v1','ptk_p1','nod_p1','core',0) "
        "ON CONFLICT DO NOTHING",
        (),
    )
    result = _run_alembic(db, "downgrade", "0003")
    assert result.returncode != 0, "有数据的 0004 表不得被静默降级"
    assert "plan_task_knowledge_links" in (result.stderr + result.stdout)
