"""B2：知识与计划业务域表（设计 §3）。

## 与 0001 的关系

**不改写 0001**（历史迁移不可改写）。本迁移只**新增**业务域表，并把 0001 已建立的
规划骨架（`plan_drafts` / `plan_revisions` / `plan_publications`）与新的知识/单元/实践域
用外键串起来。

## 本迁移新增的表（设计 §3「最小表/重要字段」）

- 知识域：`knowledge_nodes` / `knowledge_relations`
- 单元域：`learning_units` / `unit_node_links`
- 计划域：`plan_stages` / `plan_unit_links` / `plan_task_links`
- 进度域：`unit_progress`
- 实践域：`practice_projects` / `practice_tasks` / `task_knowledge_links` /
  `practice_submissions` / `acceptance_reviews`
- Prompt 工作台：`prompt_revisions` / `prompt_reviews`
- 总结闭环：`summary_attempts` / `summary_reviews`
- 偏好与资源：`preferences` / `preference_overrides` / `resource_records` /
  `node_resource_links`

## 归属与隔离（设计 §3「权限策略」）

**每张新私有表都带 `project_id` 列并直接以它做 RLS 谓词**。这样做的理由：
子表（如 `unit_node_links`）若靠「EXISTS 关联链」做策略，一旦父表在**同一事务**内
尚不可见或 JOIN 结果为空，策略会静默放行/拒绝到不可预期；把归属列**冗余**到每张表、
并用 FK 保证一致性，是更稳的双防线做法（应用查询 + 数据库 RLS）。

- 全部私有表 `ENABLE` + `FORCE ROW LEVEL SECURITY`（属主也受约束）。
- 谓词一律 `project_id = NULLIF(current_setting('app.project_id', true), '')`
  → 缺上下文为 NULL → 零行（**默认拒绝**）。
- 应用角色只有 DML、无 DDL；`GRANT` 覆盖全部新表。

## downgrade

带数据保护：遍历**全部**本迁移新增的表，任一有行即 `RAISE EXCEPTION` 拒绝降级；
在 `row_security = off` 语义下计数（迁移角色持 `BYPASSRLS`，见 ADR-0003）。
"""

from __future__ import annotations

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

#: 本迁移新增的全部业务表（供 downgrade 删表与数据保护）。
_NEW_TABLES = (
    "node_resource_links",
    "resource_records",
    "preference_overrides",
    "preferences",
    "acceptance_reviews",
    "practice_submissions",
    "prompt_reviews",
    "prompt_revisions",
    "task_knowledge_links",
    "practice_tasks",
    "practice_projects",
    "summary_reviews",
    "summary_attempts",
    "unit_progress",
    "plan_task_links",
    "plan_unit_links",
    "plan_stages",
    "unit_node_links",
    "learning_units",
    "knowledge_relations",
    "knowledge_nodes",
)

#: 全部新表都带 project_id，统一策略。
_PROJECT_SCOPED = _NEW_TABLES


def _create_tables() -> None:
    # ---------------------------------------------------------------- 知识域
    op.execute(
        """
        CREATE TABLE public.knowledge_nodes (
            node_id           text PRIMARY KEY,
            project_id        text NOT NULL REFERENCES public.learning_projects (project_id),
            stable_key        text NOT NULL,
            title             text NOT NULL,
            node_type         text NOT NULL,
            objectives        jsonb NOT NULL DEFAULT '[]'::jsonb,
            content_version   integer NOT NULL DEFAULT 1,
            source_status     text NOT NULL,
            supersedes_id     text,
            created_at        timestamptz NOT NULL DEFAULT now(),
            updated_at        timestamptz NOT NULL DEFAULT now(),
            -- 稳定键在项目内唯一；稳定键不等于标题
            CONSTRAINT knowledge_nodes_stable_key_unique UNIQUE (project_id, stable_key)
        )
        """
    )
    op.execute(
        "CREATE INDEX knowledge_nodes_project_idx ON public.knowledge_nodes (project_id)"
    )

    op.execute(
        """
        CREATE TABLE public.knowledge_relations (
            relation_id       text PRIMARY KEY,
            project_id        text NOT NULL REFERENCES public.learning_projects (project_id),
            from_node_id      text NOT NULL REFERENCES public.knowledge_nodes (node_id),
            to_node_id        text NOT NULL REFERENCES public.knowledge_nodes (node_id),
            relation_type     text NOT NULL,
            created_at        timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT knowledge_relations_unique
                UNIQUE (project_id, from_node_id, to_node_id, relation_type),
            CONSTRAINT knowledge_relations_no_self CHECK (from_node_id <> to_node_id)
        )
        """
    )
    op.execute(
        "CREATE INDEX knowledge_relations_project_idx ON public.knowledge_relations (project_id)"
    )

    # ---------------------------------------------------------------- 单元域
    op.execute(
        """
        CREATE TABLE public.learning_units (
            unit_id           text PRIMARY KEY,
            project_id        text NOT NULL REFERENCES public.learning_projects (project_id),
            stable_key        text NOT NULL,
            title             text NOT NULL,
            rubric            jsonb NOT NULL DEFAULT '[]'::jsonb,
            rubric_version    integer NOT NULL DEFAULT 1,
            created_at        timestamptz NOT NULL DEFAULT now(),
            updated_at        timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT learning_units_stable_key_unique UNIQUE (project_id, stable_key)
        )
        """
    )
    op.execute(
        "CREATE INDEX learning_units_project_idx ON public.learning_units (project_id)"
    )

    op.execute(
        """
        CREATE TABLE public.unit_node_links (
            link_id           text PRIMARY KEY,
            project_id        text NOT NULL REFERENCES public.learning_projects (project_id),
            unit_id           text NOT NULL REFERENCES public.learning_units (unit_id),
            node_id           text NOT NULL REFERENCES public.knowledge_nodes (node_id),
            order_index       integer NOT NULL,
            role              text NOT NULL,
            CONSTRAINT unit_node_links_unique UNIQUE (unit_id, node_id)
        )
        """
    )
    op.execute(
        "CREATE INDEX unit_node_links_unit_order_idx ON public.unit_node_links (unit_id, order_index)"
    )

    # ---------------------------------------------------------------- 实践域（须先于 plan_task_links）
    op.execute(
        """
        CREATE TABLE public.practice_projects (
            practice_project_id text PRIMARY KEY,
            project_id          text NOT NULL REFERENCES public.learning_projects (project_id),
            idea                text NOT NULL,
            repo_url            text,
            status              text NOT NULL,
            created_at          timestamptz NOT NULL DEFAULT now(),
            updated_at          timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX practice_projects_project_idx ON public.practice_projects (project_id)"
    )

    op.execute(
        """
        CREATE TABLE public.practice_tasks (
            task_id             text PRIMARY KEY,
            project_id          text NOT NULL REFERENCES public.learning_projects (project_id),
            practice_project_id text NOT NULL REFERENCES public.practice_projects (practice_project_id),
            stable_key          text NOT NULL,
            goal                text NOT NULL,
            in_scope            jsonb NOT NULL DEFAULT '[]'::jsonb,
            out_scope           jsonb NOT NULL DEFAULT '[]'::jsonb,
            acceptance          jsonb NOT NULL DEFAULT '[]'::jsonb,
            status              text NOT NULL,
            version             integer NOT NULL DEFAULT 1,
            created_at          timestamptz NOT NULL DEFAULT now(),
            updated_at          timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT practice_tasks_stable_key_unique UNIQUE (practice_project_id, stable_key)
        )
        """
    )
    op.execute(
        "CREATE INDEX practice_tasks_project_idx ON public.practice_tasks (project_id)"
    )

    # ---------------------------------------------------------------- 计划域
    op.execute(
        """
        CREATE TABLE public.plan_stages (
            stage_id          text PRIMARY KEY,
            project_id        text NOT NULL REFERENCES public.learning_projects (project_id),
            plan_id           text NOT NULL REFERENCES public.plan_revisions (plan_id),
            stable_key        text NOT NULL,
            title             text NOT NULL,
            order_index       integer NOT NULL,
            CONSTRAINT plan_stages_stable_key_unique UNIQUE (plan_id, stable_key),
            CONSTRAINT plan_stages_order_unique UNIQUE (plan_id, order_index)
        )
        """
    )
    op.execute(
        "CREATE INDEX plan_stages_plan_idx ON public.plan_stages (plan_id, order_index)"
    )

    op.execute(
        """
        CREATE TABLE public.plan_unit_links (
            link_id           text PRIMARY KEY,
            project_id        text NOT NULL REFERENCES public.learning_projects (project_id),
            plan_id           text NOT NULL REFERENCES public.plan_revisions (plan_id),
            stage_id          text NOT NULL REFERENCES public.plan_stages (stage_id),
            unit_id           text NOT NULL REFERENCES public.learning_units (unit_id),
            order_index       integer NOT NULL,
            CONSTRAINT plan_unit_links_unique UNIQUE (plan_id, unit_id)
        )
        """
    )
    op.execute(
        "CREATE INDEX plan_unit_links_stage_idx ON public.plan_unit_links (stage_id, order_index)"
    )

    op.execute(
        """
        CREATE TABLE public.plan_task_links (
            link_id           text PRIMARY KEY,
            project_id        text NOT NULL REFERENCES public.learning_projects (project_id),
            plan_id           text NOT NULL REFERENCES public.plan_revisions (plan_id),
            stage_id          text NOT NULL REFERENCES public.plan_stages (stage_id),
            task_id           text NOT NULL REFERENCES public.practice_tasks (task_id),
            order_index       integer NOT NULL,
            CONSTRAINT plan_task_links_unique UNIQUE (plan_id, task_id)
        )
        """
    )
    op.execute(
        "CREATE INDEX plan_task_links_stage_idx ON public.plan_task_links (stage_id, order_index)"
    )

    # ---------------------------------------------------------------- 进度域
    op.execute(
        """
        CREATE TABLE public.unit_progress (
            project_id        text NOT NULL REFERENCES public.learning_projects (project_id),
            unit_id           text NOT NULL REFERENCES public.learning_units (unit_id),
            status            text NOT NULL,
            version           integer NOT NULL DEFAULT 1,
            updated_at        timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (project_id, unit_id)
        )
        """
    )

    # ---------------------------------------------------------------- 实践域（续）
    op.execute(
        """
        CREATE TABLE public.task_knowledge_links (
            link_id           text PRIMARY KEY,
            project_id        text NOT NULL REFERENCES public.learning_projects (project_id),
            task_id           text NOT NULL REFERENCES public.practice_tasks (task_id),
            node_id           text NOT NULL REFERENCES public.knowledge_nodes (node_id),
            role              text NOT NULL,
            CONSTRAINT task_knowledge_links_unique UNIQUE (task_id, node_id)
        )
        """
    )

    op.execute(
        """
        CREATE TABLE public.practice_submissions (
            submission_id     text PRIMARY KEY,
            project_id        text NOT NULL REFERENCES public.learning_projects (project_id),
            task_id           text NOT NULL REFERENCES public.practice_tasks (task_id),
            note              text,
            repo_url          text,
            evidence          jsonb NOT NULL DEFAULT '[]'::jsonb,
            evidence_grade    text NOT NULL,
            verification      jsonb,
            created_at        timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX practice_submissions_task_idx ON public.practice_submissions (task_id)"
    )

    op.execute(
        """
        CREATE TABLE public.acceptance_reviews (
            review_id         text PRIMARY KEY,
            project_id        text NOT NULL REFERENCES public.learning_projects (project_id),
            submission_id     text NOT NULL REFERENCES public.practice_submissions (submission_id),
            conclusion        text NOT NULL,
            reviewer_kind     text NOT NULL,
            rationale         text,
            created_at        timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT acceptance_reviews_one_per_submission UNIQUE (submission_id)
        )
        """
    )

    # ---------------------------------------------------------------- Prompt 工作台
    op.execute(
        """
        CREATE TABLE public.prompt_revisions (
            revision_id       text PRIMARY KEY,
            project_id        text NOT NULL REFERENCES public.learning_projects (project_id),
            task_id           text NOT NULL REFERENCES public.practice_tasks (task_id),
            revision          integer NOT NULL,
            user_draft        text NOT NULL,
            export_text       text,
            created_at        timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT prompt_revisions_unique UNIQUE (task_id, revision)
        )
        """
    )

    op.execute(
        """
        CREATE TABLE public.prompt_reviews (
            review_id         text PRIMARY KEY,
            project_id        text NOT NULL REFERENCES public.learning_projects (project_id),
            revision_id       text NOT NULL REFERENCES public.prompt_revisions (revision_id),
            review            jsonb NOT NULL DEFAULT '{}'::jsonb,
            run_id            text,
            created_at        timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT prompt_reviews_one_per_revision UNIQUE (revision_id)
        )
        """
    )

    # ---------------------------------------------------------------- 总结闭环
    op.execute(
        """
        CREATE TABLE public.summary_attempts (
            attempt_id        text PRIMARY KEY,
            project_id        text NOT NULL REFERENCES public.learning_projects (project_id),
            unit_id           text NOT NULL REFERENCES public.learning_units (unit_id),
            content           text NOT NULL,
            attempt_no        integer NOT NULL,
            rubric_version    integer NOT NULL,
            run_id            text,
            created_at        timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT summary_attempts_unique UNIQUE (unit_id, attempt_no)
        )
        """
    )

    op.execute(
        """
        CREATE TABLE public.summary_reviews (
            review_id         text PRIMARY KEY,
            project_id        text NOT NULL REFERENCES public.learning_projects (project_id),
            attempt_id        text NOT NULL REFERENCES public.summary_attempts (attempt_id),
            review            jsonb NOT NULL DEFAULT '{}'::jsonb,
            run_id            text,
            created_at        timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT summary_reviews_one_per_attempt UNIQUE (attempt_id)
        )
        """
    )

    # ---------------------------------------------------------------- 偏好与资源
    op.execute(
        """
        CREATE TABLE public.preferences (
            preference_id     text PRIMARY KEY,
            project_id        text NOT NULL REFERENCES public.learning_projects (project_id),
            scope             text NOT NULL,
            scope_ref         text,
            media_type        text,
            language          text,
            official_priority boolean NOT NULL DEFAULT false,
            pace              text,
            version           integer NOT NULL DEFAULT 1,
            updated_at        timestamptz NOT NULL DEFAULT now(),
            -- 同一 project 内 (scope, scope_ref) 唯一（project 级 scope_ref 用空串占位）
            CONSTRAINT preferences_unique UNIQUE (project_id, scope, scope_ref)
        )
        """
    )

    op.execute(
        """
        CREATE TABLE public.preference_overrides (
            override_id       text PRIMARY KEY,
            project_id        text NOT NULL REFERENCES public.learning_projects (project_id),
            scope             text NOT NULL,
            scope_ref         text,
            media_type        text,
            language          text,
            official_priority boolean NOT NULL DEFAULT false,
            pace              text,
            expires_at        timestamptz,
            created_at        timestamptz NOT NULL DEFAULT now()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE public.resource_records (
            resource_id       text PRIMARY KEY,
            project_id        text NOT NULL REFERENCES public.learning_projects (project_id),
            url               text NOT NULL,
            title             text,
            media_type        text,
            language          text,
            section_anchor    text,
            checked_at        timestamptz,
            verification_status text NOT NULL,
            provenance        text,
            created_at        timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT resource_records_url_unique UNIQUE (project_id, url)
        )
        """
    )

    op.execute(
        """
        CREATE TABLE public.node_resource_links (
            link_id           text PRIMARY KEY,
            project_id        text NOT NULL REFERENCES public.learning_projects (project_id),
            node_id           text NOT NULL REFERENCES public.knowledge_nodes (node_id),
            resource_id       text NOT NULL REFERENCES public.resource_records (resource_id),
            order_index       integer NOT NULL,
            CONSTRAINT node_resource_links_unique UNIQUE (node_id, resource_id)
        )
        """
    )


def _apply_rls_and_grants() -> None:
    # ---- RLS：ENABLE + FORCE，属主也受约束（设计 §3 双防线）----
    for table in _PROJECT_SCOPED:
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

    # ---- 权限：应用角色只有 DML，无 DDL（C11）----
    table_list = ", ".join(f"public.{t}" for t in _NEW_TABLES)
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table_list} TO studyplan_app")


def upgrade() -> None:
    # 角色断言：迁移不建 role（C9）。
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
    _create_tables()
    _apply_rls_and_grants()


def downgrade() -> None:
    """只在**本迁移新增的表全部为空**时才允许降级（数据保护）。"""
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
    # 先撤授权再删表，避免残留特权。
    table_list = ", ".join(f"public.{t}" for t in _NEW_TABLES)
    op.execute(f"REVOKE ALL ON {table_list} FROM studyplan_app")
    # 按依赖逆序删除。
    for table in _NEW_TABLES:
        op.execute(f"DROP TABLE IF EXISTS public.{table} CASCADE")
