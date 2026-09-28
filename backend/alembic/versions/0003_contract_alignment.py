"""B2-C：契约收口迁移（复合 project FK + 字段对齐 + 公共资源/主线/扩展表）。

## 与 0001/0002 的关系

**不改写已发布的历史迁移**（0001 / 0002）。本迁移只做增量修正：

1. **复合 project FK**（P1-02）：给父表加 ``UNIQUE (project_id, <id>)``，
   把子表单列 FK 换成复合 FK ``(project_id, <id>)``。RLS 只过滤**行**，
   不保证 FK 两端**归属一致**；只有复合 FK 才能在数据库层禁止「本项目引用
   别的项目的实体」。同时删除旧单列 FK，避免两套约束语义分叉。
2. **领域/结构字段错位**（P1-03）：
   - ``learning_units`` 补 ``objectives``；``rubric`` 默认由 ``'[]'`` 改为 ``'{}'``
     （领域契约是 dict）。
   - ``plan_stages`` 补 ``section_kind`` / ``objective``（领域有、表里没有）。
   - ``practice_tasks`` 补 ``title``（领域有、表里没有）。
   - ``plan_revisions`` 补 ``source_pack_key`` / ``source_pack_version``。
   - ``plan_publications`` 补 ``idempotency_key`` / ``body_fingerprint`` /
     ``structure_fingerprint`` / ``revision``，并把幂等作用域统一为
     ``(project_id, idempotency_key)``（与 ``PublishRecord`` 字段语义一致）。
   - ``resource_records.project_id`` 保持 ``NOT NULL``（它是**项目私有**记录）；
     领域侧 ``ResourceRecord.project_id`` 已改为必填，公共资源另设新表。
3. **新表**（V1.2 §2.2）：``domain_packs`` / ``public_resource_sources`` /
   ``public_resource_sections``（公共只读）+ ``stage_resource_assignments`` /
   ``knowledge_extensions``（私人计划快照，项目 RLS）。

## 隔离与权限

- 私人新表（``stage_resource_assignments`` / ``knowledge_extensions``）：
  ``ENABLE`` + ``FORCE ROW LEVEL SECURITY`` + 项目归属策略（缺上下文默认拒绝）。
- 公共表（``domain_packs`` / ``public_resource_*``）：``FORCE RLS`` +
  仅 ``FOR SELECT USING (true)`` 策略；应用角色只被 ``GRANT SELECT``，
  写入由权限与策略双重拒绝（迁移角色持 ``BYPASSRLS`` 供种子导入）。
- 同 URL 可有多个章节：``public_resource_sections`` **不建** ``UNIQUE(url)``。

## downgrade

带数据保护：本迁移新增的表任一有行即拒绝降级；先撤授权再删表。
"""

from __future__ import annotations

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

#: 本迁移新增的表（供 downgrade 删表与数据保护）。
#: 注意：删除顺序必须**先子后父**（章节依赖来源），故按依赖逆序排列。
_NEW_TABLES = (
    "knowledge_extensions",
    "stage_resource_assignments",
    "public_resource_sections",
    "public_resource_sources",
    "domain_packs",
)

#: 项目作用域的私人新表（需要 RLS 项目归属策略）。
_PRIVATE_NEW_TABLES = (
    "knowledge_extensions",
    "stage_resource_assignments",
)

#: 公共只读新表（FORCE RLS + SELECT-all 策略，应用角色只读）。
_PUBLIC_NEW_TABLES = (
    "domain_packs",
    "public_resource_sources",
    "public_resource_sections",
)

#: 父表 -> 需要新增的 ``UNIQUE (project_id, <id_col>)``。
_PARENT_UNIQUES: dict[str, str] = {
    "knowledge_nodes": "node_id",
    "learning_units": "unit_id",
    "plan_revisions": "plan_id",
    "plan_stages": "stage_id",
    "practice_projects": "practice_project_id",
    "practice_tasks": "task_id",
    "practice_submissions": "submission_id",
    "prompt_revisions": "revision_id",
    "summary_attempts": "attempt_id",
    "resource_records": "resource_id",
}

#: 子表 -> [(本地列, 父表, 父表 id 列)]，需要换成复合 FK。
_CHILD_FKS: dict[str, list[tuple[str, str, str]]] = {
    "knowledge_relations": [
        ("from_node_id", "knowledge_nodes", "node_id"),
        ("to_node_id", "knowledge_nodes", "node_id"),
    ],
    "unit_node_links": [
        ("unit_id", "learning_units", "unit_id"),
        ("node_id", "knowledge_nodes", "node_id"),
    ],
    "plan_stages": [("plan_id", "plan_revisions", "plan_id")],
    "plan_unit_links": [
        ("plan_id", "plan_revisions", "plan_id"),
        ("stage_id", "plan_stages", "stage_id"),
        ("unit_id", "learning_units", "unit_id"),
    ],
    "plan_task_links": [
        ("plan_id", "plan_revisions", "plan_id"),
        ("stage_id", "plan_stages", "stage_id"),
        ("task_id", "practice_tasks", "task_id"),
    ],
    "unit_progress": [("unit_id", "learning_units", "unit_id")],
    "practice_tasks": [("practice_project_id", "practice_projects", "practice_project_id")],
    "task_knowledge_links": [
        ("task_id", "practice_tasks", "task_id"),
        ("node_id", "knowledge_nodes", "node_id"),
    ],
    "practice_submissions": [("task_id", "practice_tasks", "task_id")],
    "acceptance_reviews": [("submission_id", "practice_submissions", "submission_id")],
    "prompt_revisions": [("task_id", "practice_tasks", "task_id")],
    "prompt_reviews": [("revision_id", "prompt_revisions", "revision_id")],
    "summary_attempts": [("unit_id", "learning_units", "unit_id")],
    "summary_reviews": [("attempt_id", "summary_attempts", "attempt_id")],
    "node_resource_links": [
        ("node_id", "knowledge_nodes", "node_id"),
        ("resource_id", "resource_records", "resource_id"),
    ],
}


def _field_alignment() -> None:
    # ---- learning_units：objectives + rubric 默认对齐领域 dict ----
    op.execute(
        "ALTER TABLE public.learning_units "
        "ADD COLUMN IF NOT EXISTS objectives jsonb NOT NULL DEFAULT '[]'::jsonb"
    )
    op.execute(
        "ALTER TABLE public.learning_units ALTER COLUMN rubric SET DEFAULT '{}'::jsonb"
    )

    # ---- plan_stages：section_kind / objective ----
    op.execute(
        "ALTER TABLE public.plan_stages "
        "ADD COLUMN IF NOT EXISTS section_kind text NOT NULL DEFAULT 'core'"
    )
    op.execute(
        "ALTER TABLE public.plan_stages "
        "ADD COLUMN IF NOT EXISTS objective text NOT NULL DEFAULT ''"
    )

    # ---- practice_projects：title（领域必填）/ version（乐观并发）----
    op.execute(
        "ALTER TABLE public.practice_projects "
        "ADD COLUMN IF NOT EXISTS title text NOT NULL DEFAULT ''"
    )
    op.execute(
        "ALTER TABLE public.practice_projects "
        "ADD COLUMN IF NOT EXISTS version integer NOT NULL DEFAULT 1"
    )

    # ---- practice_tasks：title（领域必填）/ stage_index（阶段归属）----
    op.execute(
        "ALTER TABLE public.practice_tasks "
        "ADD COLUMN IF NOT EXISTS title text NOT NULL DEFAULT ''"
    )
    op.execute(
        "ALTER TABLE public.practice_tasks "
        "ADD COLUMN IF NOT EXISTS stage_index integer NOT NULL DEFAULT 0"
    )

    # ---- resource_records：source_note（领域有、表里没有）----
    op.execute(
        "ALTER TABLE public.resource_records "
        "ADD COLUMN IF NOT EXISTS source_note text NOT NULL DEFAULT ''"
    )

    # ---- plan_revisions：领域包来源版本 ----
    op.execute(
        "ALTER TABLE public.plan_revisions "
        "ADD COLUMN IF NOT EXISTS source_pack_key text NOT NULL DEFAULT ''"
    )
    op.execute(
        "ALTER TABLE public.plan_revisions "
        "ADD COLUMN IF NOT EXISTS source_pack_version integer NOT NULL DEFAULT 0"
    )

    # ---- plan_publications：与 PublishRecord 字段语义统一 ----
    # 端口契约以 (project_id, idempotency_key) 为幂等作用域，run_id/operation_key
    # 是 0001 遗留的「按 run 幂等」列。新契约下它们不再必填，故放开 NOT NULL，
    # 否则基础设施无法写入一条纯 PublishRecord 形态的记录（B2-D 的硬阻塞）。
    op.execute("ALTER TABLE public.plan_publications ALTER COLUMN run_id DROP NOT NULL")
    op.execute("ALTER TABLE public.plan_publications ALTER COLUMN operation_key DROP NOT NULL")
    op.execute(
        "ALTER TABLE public.plan_publications "
        "ADD COLUMN IF NOT EXISTS idempotency_key text"
    )
    op.execute(
        "ALTER TABLE public.plan_publications "
        "ADD COLUMN IF NOT EXISTS body_fingerprint text NOT NULL DEFAULT ''"
    )
    op.execute(
        "ALTER TABLE public.plan_publications "
        "ADD COLUMN IF NOT EXISTS structure_fingerprint text NOT NULL DEFAULT ''"
    )
    op.execute(
        "ALTER TABLE public.plan_publications "
        "ADD COLUMN IF NOT EXISTS revision integer"
    )
    # 幂等作用域统一为 (project_id, idempotency_key)（与端口契约一致）。
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS plan_publications_project_idem_unique "
        "ON public.plan_publications (project_id, idempotency_key) "
        "WHERE idempotency_key IS NOT NULL"
    )


def _composite_fks() -> None:
    # 1) 父表加 UNIQUE (project_id, <id>)。
    for table, id_col in _PARENT_UNIQUES.items():
        op.execute(
            f"ALTER TABLE public.{table} "
            f"ADD CONSTRAINT {table}_project_id_unique UNIQUE (project_id, {id_col})"
        )

    # 2) 子表：删除旧单列 FK，换复合 FK。
    for child, fks in _CHILD_FKS.items():
        for local_col, parent, parent_id in fks:
            # Postgres 自动命名规则：<table>_<column>_fkey。
            op.execute(
                f"ALTER TABLE public.{child} "
                f"DROP CONSTRAINT IF EXISTS {child}_{local_col}_fkey"
            )
            op.execute(
                f"ALTER TABLE public.{child} "
                f"ADD CONSTRAINT {child}_{local_col}_project_fkey "
                f"FOREIGN KEY (project_id, {local_col}) "
                f"REFERENCES public.{parent} (project_id, {parent_id})"
            )


def _new_tables() -> None:
    # ------------------------------------------------------------- 公共策划/资源
    op.execute(
        """
        CREATE TABLE public.domain_packs (
            pack_key            text NOT NULL,
            version             integer NOT NULL,
            status              text NOT NULL,
            supported_scope     text NOT NULL,
            title               text NOT NULL,
            stage_blueprints    jsonb NOT NULL DEFAULT '[]'::jsonb,
            resource_refs       jsonb NOT NULL DEFAULT '[]'::jsonb,
            extension_blueprints jsonb NOT NULL DEFAULT '[]'::jsonb,
            practice_blueprints jsonb NOT NULL DEFAULT '[]'::jsonb,
            provenance          text NOT NULL DEFAULT '',
            created_at          timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (pack_key, version)
        )
        """
    )

    op.execute(
        """
        CREATE TABLE public.public_resource_sources (
            source_id       text PRIMARY KEY,
            canonical_url   text NOT NULL,
            title           text NOT NULL,
            creator         text NOT NULL DEFAULT '',
            media_type      text NOT NULL DEFAULT 'course',
            language        text NOT NULL DEFAULT 'zh',
            source_version  integer NOT NULL DEFAULT 1,
            visibility      text NOT NULL DEFAULT 'curated',
            provenance      text NOT NULL DEFAULT '',
            checked_at      timestamptz,
            created_at      timestamptz NOT NULL DEFAULT now()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE public.public_resource_sections (
            section_id      text PRIMARY KEY,
            source_id       text NOT NULL REFERENCES public.public_resource_sources (source_id),
            order_index     integer NOT NULL,
            title           text NOT NULL,
            url             text NOT NULL,
            anchor          text NOT NULL DEFAULT '',
            checked_at      timestamptz,
            -- 同 URL 可有多个章节（不同 anchor）：**不建** UNIQUE(url)。
            CONSTRAINT public_resource_sections_order_unique UNIQUE (source_id, order_index)
        )
        """
    )
    op.execute(
        "CREATE INDEX public_resource_sections_source_idx "
        "ON public.public_resource_sections (source_id, order_index)"
    )

    # ------------------------------------------------------------- 私人计划快照
    op.execute(
        """
        CREATE TABLE public.stage_resource_assignments (
            assignment_id       text PRIMARY KEY,
            project_id          text NOT NULL REFERENCES public.learning_projects (project_id),
            plan_id             text NOT NULL DEFAULT '',
            stage_id            text NOT NULL,
            role                text NOT NULL,
            source_ref          text NOT NULL DEFAULT '',
            section_refs        jsonb NOT NULL DEFAULT '[]'::jsonb,
            order_index         integer NOT NULL DEFAULT 0,
            source_version      integer NOT NULL DEFAULT 0,
            fallback_search_terms jsonb NOT NULL DEFAULT '[]'::jsonb,
            snapshot_at         timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX stage_resource_assignments_stage_idx "
        "ON public.stage_resource_assignments (project_id, stage_id)"
    )

    op.execute(
        """
        CREATE TABLE public.knowledge_extensions (
            extension_id     text PRIMARY KEY,
            project_id       text NOT NULL REFERENCES public.learning_projects (project_id),
            plan_id          text NOT NULL DEFAULT '',
            stage_id         text NOT NULL,
            unit_id          text,
            topic            text NOT NULL,
            concepts         jsonb NOT NULL DEFAULT '[]'::jsonb,
            guidance         text NOT NULL DEFAULT '',
            links            jsonb NOT NULL DEFAULT '[]'::jsonb,
            search_hints     jsonb NOT NULL DEFAULT '[]'::jsonb,
            thinking_prompts jsonb NOT NULL DEFAULT '[]'::jsonb,
            required         boolean NOT NULL DEFAULT false,
            order_index      integer NOT NULL DEFAULT 0
        )
        """
    )
    op.execute(
        "CREATE INDEX knowledge_extensions_stage_idx "
        "ON public.knowledge_extensions (project_id, stage_id)"
    )


def _rls_and_grants() -> None:
    # 私人新表：项目归属策略。
    for table in _PRIVATE_NEW_TABLES:
        op.execute(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE public.{table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY {table}_project_scope ON public.{table}
            USING (
                project_id = NULLIF(current_setting('app.project_id', true), '')
            )
            WITH CHECK (
                project_id = NULLIF(current_setting('app.project_id', true), '')
            )
            """
        )

    # 公共新表：FORCE RLS + 只读（SELECT-all）策略；写入无策略 => 拒绝。
    for table in _PUBLIC_NEW_TABLES:
        op.execute(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE public.{table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY {table}_public_read ON public.{table}
            FOR SELECT USING (true)
            """
        )

    # 权限：私人表 DML；公共表只读。
    private_list = ", ".join(f"public.{t}" for t in _PRIVATE_NEW_TABLES)
    public_list = ", ".join(f"public.{t}" for t in _PUBLIC_NEW_TABLES)
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {private_list} TO studyplan_app")
    op.execute(f"GRANT SELECT ON {public_list} TO studyplan_app")


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
    _field_alignment()
    _composite_fks()
    _new_tables()
    _rls_and_grants()


def downgrade() -> None:
    """带数据保护：本迁移新增的表任一有行即拒绝降级。"""
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
    # 撤授权 + 删新表（按依赖逆序）。
    private_list = ", ".join(f"public.{t}" for t in _PRIVATE_NEW_TABLES)
    public_list = ", ".join(f"public.{t}" for t in _PUBLIC_NEW_TABLES)
    op.execute(f"REVOKE ALL ON {private_list} FROM studyplan_app")
    op.execute(f"REVOKE ALL ON {public_list} FROM studyplan_app")
    for table in _NEW_TABLES:
        op.execute(f"DROP TABLE IF EXISTS public.{table} CASCADE")

    # 还原子表 FK（复合 -> 单列）与父表唯一约束。
    for child, fks in _CHILD_FKS.items():
        for local_col, parent, parent_id in fks:
            op.execute(
                f"ALTER TABLE public.{child} "
                f"DROP CONSTRAINT IF EXISTS {child}_{local_col}_project_fkey"
            )
            op.execute(
                f"ALTER TABLE public.{child} "
                f"ADD CONSTRAINT {child}_{local_col}_fkey "
                f"FOREIGN KEY ({local_col}) REFERENCES public.{parent} ({parent_id})"
            )
    for table in _PARENT_UNIQUES:
        op.execute(
            f"ALTER TABLE public.{table} "
            f"DROP CONSTRAINT IF EXISTS {table}_project_id_unique"
        )

    # 还原字段对齐（删列 / 复位默认值 / 复位 NOT NULL）。
    op.execute("DROP INDEX IF EXISTS public.plan_publications_project_idem_unique")
    for col in ("idempotency_key", "body_fingerprint", "structure_fingerprint", "revision"):
        op.execute(f"ALTER TABLE public.plan_publications DROP COLUMN IF EXISTS {col}")
    # 复位遗留列的 NOT NULL（回填占位值以恢复约束）。
    op.execute("UPDATE public.plan_publications SET run_id = '' WHERE run_id IS NULL")
    op.execute("UPDATE public.plan_publications SET operation_key = '' WHERE operation_key IS NULL")
    op.execute("ALTER TABLE public.plan_publications ALTER COLUMN run_id SET NOT NULL")
    op.execute("ALTER TABLE public.plan_publications ALTER COLUMN operation_key SET NOT NULL")
    for col in ("source_pack_key", "source_pack_version"):
        op.execute(f"ALTER TABLE public.plan_revisions DROP COLUMN IF EXISTS {col}")
    op.execute("ALTER TABLE public.resource_records DROP COLUMN IF EXISTS source_note")
    for col in ("title", "stage_index"):
        op.execute(f"ALTER TABLE public.practice_tasks DROP COLUMN IF EXISTS {col}")
    for col in ("title", "version"):
        op.execute(f"ALTER TABLE public.practice_projects DROP COLUMN IF EXISTS {col}")
    for col in ("section_kind", "objective"):
        op.execute(f"ALTER TABLE public.plan_stages DROP COLUMN IF EXISTS {col}")
    op.execute("ALTER TABLE public.learning_units DROP COLUMN IF EXISTS objectives")
    op.execute(
        "ALTER TABLE public.learning_units ALTER COLUMN rubric SET DEFAULT '[]'::jsonb"
    )
