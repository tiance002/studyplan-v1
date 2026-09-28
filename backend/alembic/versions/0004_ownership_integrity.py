"""B2-V §五：计划快照的**归属完整性**（跨计划错挂 / 孤儿分配 / 绑错单元）。

## 为什么需要本迁移

0003 已经给「父表加 ``UNIQUE (project_id, <id>)``、子表换复合 FK」打了基础，
但仍留下三类**数据库层无法拒绝**的错误（RLS 只过滤**行**，不保证 FK 两端
**归属一致**，更不保证 ``plan_id`` 与 ``stage_id`` 属于**同一版本**）：

1. **同项目内跨计划错挂**：``plan_unit_links`` / ``plan_task_links`` /
   ``stage_resource_assignments`` / ``knowledge_extensions`` 只有
   ``(project_id, stage_id)`` 级 FK，因此「plan A 的链接指向 plan B 的阶段」
   可以写进去（stage 确实属于本项目）。
   → 本迁移给 ``plan_stages`` 补 ``UNIQUE (project_id, plan_id, stage_id)``，
   并把上述子表的 stage FK 升级为 ``(project_id, plan_id, stage_id)`` 三元组。
2. **孤儿资源分配 / 扩展**：``stage_resource_assignments`` /
   ``knowledge_extensions`` 的 ``plan_id`` 默认 ``''`` 且**无** FK，
   于是可以留下不属于任何版本的快照行。
   → 补 ``(project_id, plan_id) → plan_revisions`` FK。
3. **扩展绑错单元**：``knowledge_extensions.unit_id`` 无任何约束。
   → 补 ``(project_id, plan_id, unit_id) → plan_unit_links`` FK
   （``plan_unit_links`` 先补 ``UNIQUE (project_id, plan_id, unit_id)``），
   即「扩展只能绑定到**本计划**已挂载的单元」。

另外新增 ``plan_task_knowledge_links`` 表：任务-知识关联属于**版本快照**
（B2-V §四要求它进结构指纹），必须有 ``(project_id, plan_id)`` 与
``(project_id, plan_id, task_id)`` 双重约束，防止「关联到别的计划的实践任务」。

公共资源引用（``source_ref``）补 ``FK → public_resource_sources(source_id)``：
无核验来源时**存 NULL**（不是空串），并保留 ``fallback_search_terms`` 表达
搜索建议——**绝不**编造已核验来源。``section_refs`` 是 jsonb 数组，数据库
无法约束，其「章节必须属于该来源」由领域层输出前校验（见
``app.domain.resources.curation``）。

## 已发布迁移不改写

0001/0002/0003 **不动**；本文件是纯增量迁移。

## downgrade

带数据保护：新表有行即拒绝降级；删约束/删列按依赖逆序还原。
"""

from __future__ import annotations

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

#: 需要把 ``(project_id, stage_id)`` 升级为 ``(project_id, plan_id, stage_id)`` 的子表。
_STAGE_SCOPED_CHILDREN = (
    "plan_unit_links",
    "plan_task_links",
    "stage_resource_assignments",
    "knowledge_extensions",
)

#: 本迁移新增的表（downgrade 数据保护 + 删表）。
_NEW_TABLES = ("plan_task_knowledge_links",)


def _plan_scoped_stage_fk() -> None:
    """1) ``plan_stages`` 补 ``UNIQUE (project_id, plan_id, stage_id)``；
    2) 子表 stage FK 升级为三元组（禁止跨计划错挂）。
    """
    op.execute(
        "ALTER TABLE public.plan_stages "
        "ADD CONSTRAINT plan_stages_project_plan_stage_unique "
        "UNIQUE (project_id, plan_id, stage_id)"
    )
    for child in _STAGE_SCOPED_CHILDREN:
        # 先去掉 0003 建立的二元组 FK，避免两套约束语义分叉。
        op.execute(
            f"ALTER TABLE public.{child} "
            f"DROP CONSTRAINT IF EXISTS {child}_stage_id_project_fkey"
        )
        op.execute(
            f"ALTER TABLE public.{child} "
            f"ADD CONSTRAINT {child}_plan_stage_fkey "
            f"FOREIGN KEY (project_id, plan_id, stage_id) "
            f"REFERENCES public.plan_stages (project_id, plan_id, stage_id)"
        )


def _link_unique_parents() -> None:
    """``plan_unit_links`` / ``plan_task_links`` 补可作 FK 父键的唯一约束。"""
    op.execute(
        "ALTER TABLE public.plan_unit_links "
        "ADD CONSTRAINT plan_unit_links_project_plan_unit_unique "
        "UNIQUE (project_id, plan_id, unit_id)"
    )
    op.execute(
        "ALTER TABLE public.plan_task_links "
        "ADD CONSTRAINT plan_task_links_project_plan_task_unique "
        "UNIQUE (project_id, plan_id, task_id)"
    )


def _guard_no_orphan_snapshots() -> None:
    """升级前自检：``plan_id`` 为空的历史快照行无法满足新 FK，必须显式报错。

    迁移**不静默修补**业务数据——宁可拒绝执行，也不伪造归属。
    """
    op.execute(
        """
        DO $$
        DECLARE
            bad_asg bigint;
            bad_ext bigint;
        BEGIN
            SELECT count(*) INTO bad_asg
            FROM public.stage_resource_assignments WHERE plan_id = '';
            SELECT count(*) INTO bad_ext
            FROM public.knowledge_extensions WHERE plan_id = '';
            IF bad_asg > 0 OR bad_ext > 0 THEN
                RAISE EXCEPTION
                    '存在 plan_id 为空的资源分配(%)/扩展(%)，无法建立归属 FK；请先修复数据',
                    bad_asg, bad_ext;
            END IF;
        END
        $$;
        """
    )


def _snapshot_ownership_fks() -> None:
    """资源分配 / 扩展：补「必须属于某个已发布版本」的 FK。"""
    for table in ("stage_resource_assignments", "knowledge_extensions"):
        op.execute(
            f"ALTER TABLE public.{table} "
            f"ADD CONSTRAINT {table}_plan_fkey "
            f"FOREIGN KEY (project_id, plan_id) "
            f"REFERENCES public.plan_revisions (project_id, plan_id)"
        )

    # 扩展只能绑定到**本计划**已挂载的单元（unit_id 可空 = 未绑定具体单元）。
    op.execute(
        "ALTER TABLE public.knowledge_extensions "
        "ADD CONSTRAINT knowledge_extensions_plan_unit_fkey "
        "FOREIGN KEY (project_id, plan_id, unit_id) "
        "REFERENCES public.plan_unit_links (project_id, plan_id, unit_id)"
    )

    # 公共资源引用：空串统一转为 NULL，再建 FK（无核验来源 = NULL，不编造）。
    op.execute(
        "UPDATE public.stage_resource_assignments SET source_ref = NULL "
        "WHERE source_ref = ''"
    )
    op.execute(
        "ALTER TABLE public.stage_resource_assignments "
        "ALTER COLUMN source_ref DROP NOT NULL"
    )
    op.execute(
        "ALTER TABLE public.stage_resource_assignments "
        "ADD CONSTRAINT stage_resource_assignments_source_fkey "
        "FOREIGN KEY (source_ref) "
        "REFERENCES public.public_resource_sources (source_id)"
    )


def _run_projection_version() -> None:
    """``ai_runs.version``：对外 RunView 的乐观并发版本号（B2-V §六）。

    ``ai_runs`` 是**对外运行状态投影**，前端据此做乐观并发；
    没有版本号就无法区分「我拿到的状态已经旧了」。
    """
    op.execute(
        "ALTER TABLE public.ai_runs "
        "ADD COLUMN IF NOT EXISTS version integer NOT NULL DEFAULT 1"
    )


def _new_tables() -> None:
    op.execute(
        """
        CREATE TABLE public.plan_task_knowledge_links (            link_id         text PRIMARY KEY,
            project_id      text NOT NULL REFERENCES public.learning_projects (project_id),
            plan_id         text NOT NULL,
            task_id         text NOT NULL,
            node_id         text NOT NULL,
            role            text NOT NULL DEFAULT 'core',
            order_index     integer NOT NULL DEFAULT 0,
            -- 同一版本内同一 (task, node) 只允许一条关联。
            CONSTRAINT plan_task_knowledge_links_unique
                UNIQUE (project_id, plan_id, task_id, node_id),
            -- 关联必须落在**同一版本**（禁止跨计划错挂）。
            CONSTRAINT plan_task_knowledge_links_plan_fkey
                FOREIGN KEY (project_id, plan_id)
                REFERENCES public.plan_revisions (project_id, plan_id),
            -- 任务必须是**本计划已挂载**的实践任务。
            CONSTRAINT plan_task_knowledge_links_task_fkey
                FOREIGN KEY (project_id, plan_id, task_id)
                REFERENCES public.plan_task_links (project_id, plan_id, task_id),
            -- 知识节点必须属于同一项目。
            CONSTRAINT plan_task_knowledge_links_node_fkey
                FOREIGN KEY (project_id, node_id)
                REFERENCES public.knowledge_nodes (project_id, node_id)
        )
        """
    )
    op.execute(
        "CREATE INDEX plan_task_knowledge_links_plan_idx "
        "ON public.plan_task_knowledge_links (project_id, plan_id, order_index)"
    )
    op.execute("ALTER TABLE public.plan_task_knowledge_links ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.plan_task_knowledge_links FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY plan_task_knowledge_links_project_scope
        ON public.plan_task_knowledge_links
        USING (project_id = NULLIF(current_setting('app.project_id', true), ''))
        WITH CHECK (project_id = NULLIF(current_setting('app.project_id', true), ''))
        """
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE "
        "ON public.plan_task_knowledge_links TO studyplan_app"
    )


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'studyplan_app') THEN
                RAISE EXCEPTION 'role studyplan_app 不存在；请先由 bootstrap 脚本创建角色（迁移不建 role）';
            END IF;
        END
        $$;
        """
    )
    _guard_no_orphan_snapshots()
    _plan_scoped_stage_fk()
    _link_unique_parents()
    _snapshot_ownership_fks()
    _run_projection_version()
    _new_tables()


def downgrade() -> None:
    """带数据保护：新表任一有行即拒绝降级。"""
    checks = ",\n                ".join(
        f"(SELECT count(*) FROM public.{t}) AS {t}_cnt" for t in _NEW_TABLES
    )
    guards = "\n".join(
        f"""            IF row_to_json(rec)::jsonb ->> '{t}_cnt' <> '0' THEN
                RAISE EXCEPTION '业务表 {t} 仍有数据，拒绝降级';
            END IF;"""
        for t in _NEW_TABLES
    )
    op.execute(
        f"""
        DO $$
        DECLARE
            rec record;
        BEGIN
            SELECT {checks}
            INTO rec;
{guards}
        END
        $$;
        """
    )

    op.execute("REVOKE ALL ON public.plan_task_knowledge_links FROM studyplan_app")
    for table in _NEW_TABLES:
        op.execute(f"DROP TABLE IF EXISTS public.{table} CASCADE")

    op.execute("ALTER TABLE public.ai_runs DROP COLUMN IF EXISTS version")

    op.execute(
        "ALTER TABLE public.stage_resource_assignments "
        "DROP CONSTRAINT IF EXISTS stage_resource_assignments_source_fkey"
    )
    op.execute(
        "ALTER TABLE public.stage_resource_assignments "
        "ALTER COLUMN source_ref SET NOT NULL"
    )
    op.execute(
        "ALTER TABLE public.knowledge_extensions "
        "DROP CONSTRAINT IF EXISTS knowledge_extensions_plan_unit_fkey"
    )
    for table in ("stage_resource_assignments", "knowledge_extensions"):
        op.execute(f"ALTER TABLE public.{table} DROP CONSTRAINT IF EXISTS {table}_plan_fkey")

    op.execute(
        "ALTER TABLE public.plan_unit_links "
        "DROP CONSTRAINT IF EXISTS plan_unit_links_project_plan_unit_unique"
    )
    op.execute(
        "ALTER TABLE public.plan_task_links "
        "DROP CONSTRAINT IF EXISTS plan_task_links_project_plan_task_unique"
    )

    # 还原二元组 stage FK。
    for child in _STAGE_SCOPED_CHILDREN:
        op.execute(
            f"ALTER TABLE public.{child} "
            f"DROP CONSTRAINT IF EXISTS {child}_plan_stage_fkey"
        )
        op.execute(
            f"ALTER TABLE public.{child} "
            f"ADD CONSTRAINT {child}_stage_id_project_fkey "
            f"FOREIGN KEY (project_id, stage_id) "
            f"REFERENCES public.plan_stages (project_id, stage_id)"
        )
    op.execute(
        "ALTER TABLE public.plan_stages "
        "DROP CONSTRAINT IF EXISTS plan_stages_project_plan_stage_unique"
    )
