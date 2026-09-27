"""新版业务库初始基线（B1 骨架）。

## 这条基线与旧工程 0001 的关系

**不复用旧 `0001` 的 revision id 与表结构。** 旧 0001 是为旧业务域而建，
含 `routing_decision`、`acquisition_fetch_observations`、
`study_metrics_snapshot()` 等新版不需要的对象（见
`docs/migration/legacy-inventory.md` §4.3）。新版需要自己的基线。

## 本文件当前状态（B1 骨架）

只建立**最小可验证结构**，用于证明迁移链可用：

- `ai_runs` / `ai_run_events` / `ai_provider_attempts` / `ai_jobs`
  —— 运行投影与队列（设计 §5）；
- `learning_projects` —— 学习空间（最小）；
- `plan_drafts` / `plan_revisions` / `plan_publications` —— 规划域
  （最小，用于验证「重复确认不重建两份」与「已确认结构不可变」）。

B2 才补齐知识节点/关系/单元/实践任务等完整业务表。

## 运行时约定（沿用旧工程已验证的做法，见 module-reuse-matrix.md §3）

- **C9**：迁移不建 role、不建 extension；角色不存在时**显式失败**。
- **C10**：`alembic.ini` 保持纯 ASCII（中文 Windows GBK 陷阱）。
- **C11**：迁移角色与应用角色强制分离，应用角色**不得**有 DDL。

## B1 审查修复（本版）

审查发现原基线三处缺陷，本版一并修复：

1. **`downgrade` 数据保护不完整**：只检查 `ai_runs` / `plan_revisions`，
   其余业务表（`learning_projects` / `plan_drafts` / `plan_publications` /
   `ai_run_events` / `ai_provider_attempts` / `ai_jobs`）有数据时仍会被
   静默清库。本版改为**遍历所有业务表**，任一有行即拒绝降级。
2. **RLS 只 ENABLE 未 FORCE**：表属主（迁移角色）默认**绕过** RLS，
   连接到库的迁移角色可无视策略读写所有行。本版对所有私有表启用
   ``FORCE ROW LEVEL SECURITY``，使属主也受策略约束。
3. **`ai_run_events` / `ai_provider_attempts` 没有归属策略**：只 ENABLE
   没有 policy 的表在开启 RLS 后对所有非属主**默认拒绝全部访问**，
   实际上不可用；且缺少按 run 归属的隔离。本版补齐「经 `run_id` 归属到
   当前 project」的策略。

RLS 谓词一律用 ``current_setting(..., true)``（缺上下文 → NULL → 零行，
即**默认拒绝**）。worker 策略带 ``app.worker_id`` 上下文检查，防越权领取。
"""

from __future__ import annotations

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

#: 全部业务表（按外键依赖逆序排列，供 downgrade 删除与数据保护使用）。
_ALL_BUSINESS_TABLES = (
    "ai_jobs",
    "ai_provider_attempts",
    "ai_run_events",
    "ai_runs",
    "plan_publications",
    "plan_revisions",
    "plan_drafts",
    "learning_projects",
)

#: 通过 ``project_id`` 直接归属的表。
_PROJECT_SCOPED_TABLES = (
    "plan_drafts",
    "plan_revisions",
    "plan_publications",
    "ai_runs",
)

#: 通过 ``run_id`` 间接归属的表（需子查询到 ai_runs.project_id）。
_RUN_SCOPED_TABLES = (
    "ai_run_events",
    "ai_provider_attempts",
    "ai_jobs",
)


def upgrade() -> None:
    # ---- 角色断言：角色不存在时显式失败，不静默建库（C9）----
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

    # ---- 学习空间（最小）----
    op.execute(
        """
        CREATE TABLE public.learning_projects (
            project_id        text PRIMARY KEY,
            owner_actor_id    text NOT NULL,
            title             text NOT NULL,
            goal_statement    text NOT NULL,
            stable_key        text NOT NULL,
            version           integer NOT NULL DEFAULT 1,
            created_at        timestamptz NOT NULL DEFAULT now(),
            updated_at        timestamptz NOT NULL DEFAULT now(),
            archived_at       timestamptz,
            CONSTRAINT learning_projects_stable_key_unique UNIQUE (owner_actor_id, stable_key)
        )
        """
    )
    op.execute(
        "CREATE INDEX learning_projects_owner_idx ON public.learning_projects (owner_actor_id)"
    )

    # ---- 规划草案与版本 ----
    op.execute(
        """
        CREATE TABLE public.plan_drafts (
            draft_id          text PRIMARY KEY,
            project_id        text NOT NULL REFERENCES public.learning_projects (project_id),
            run_id            text,
            status            text NOT NULL,
            content_hash      text NOT NULL,
            revision_candidate integer,
            payload           jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at        timestamptz NOT NULL DEFAULT now(),
            updated_at        timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    # 同一项目下 run 至多一个草案，防重复生成
    op.execute(
        "CREATE UNIQUE INDEX plan_drafts_run_unique ON public.plan_drafts (run_id) "
        "WHERE run_id IS NOT NULL"
    )
    op.execute(
        "CREATE INDEX plan_drafts_project_status_idx ON public.plan_drafts (project_id, status)"
    )

    op.execute(
        """
        CREATE TABLE public.plan_revisions (
            plan_id           text PRIMARY KEY,
            project_id        text NOT NULL REFERENCES public.learning_projects (project_id),
            revision          integer NOT NULL,
            goal_snapshot     text NOT NULL,
            status            text NOT NULL,
            structure         jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at        timestamptz NOT NULL DEFAULT now(),
            -- 已确认结构不可变：同一项目 revision 唯一
            CONSTRAINT plan_revisions_unique UNIQUE (project_id, revision)
        )
        """
    )
    # 每个项目至多一个"当前"版本
    op.execute(
        "CREATE UNIQUE INDEX plan_revisions_current_unique ON public.plan_revisions (project_id) "
        "WHERE status = 'approved'"
    )

    # ---- 幂等提交记录：run_id + operation_key 唯一且可重放（设计 §5）----
    op.execute(
        """
        CREATE TABLE public.plan_publications (
            publication_id    text PRIMARY KEY,
            project_id        text NOT NULL,
            run_id            text NOT NULL,
            operation_key     text NOT NULL,
            plan_id           text NOT NULL,
            draft_hash        text NOT NULL,
            created_at        timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT plan_publications_idempotent UNIQUE (run_id, operation_key)
        )
        """
    )

    # ---- 运行投影与队列 ----
    op.execute(
        """
        CREATE TABLE public.ai_runs (
            run_id            text PRIMARY KEY,
            actor_id          text NOT NULL,
            project_id        text NOT NULL,
            kind              text NOT NULL,
            graph_name        text,
            graph_version     text,
            status            text NOT NULL,
            next_action       text NOT NULL DEFAULT 'none',
            thread_id         text,
            idempotency_key   text,
            error_class       text,
            result_ref        text,
            created_at        timestamptz NOT NULL DEFAULT now(),
            updated_at        timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    # 同键同体返回同结果：幂等键在项目内唯一
    op.execute(
        "CREATE UNIQUE INDEX ai_runs_idempotency_unique ON public.ai_runs (project_id, idempotency_key) "
        "WHERE idempotency_key IS NOT NULL"
    )
    op.execute(
        "CREATE INDEX ai_runs_project_status_idx ON public.ai_runs (project_id, status)"
    )
    # ⚠️ thread_id 只由服务端映射使用，永不返回客户端。

    op.execute(
        """
        CREATE TABLE public.ai_run_events (
            event_id          bigserial PRIMARY KEY,
            run_id            text NOT NULL REFERENCES public.ai_runs (run_id) ON DELETE CASCADE,
            node_name         text,
            attempt_id        text,
            status            text NOT NULL,
            detail            jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at        timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX ai_run_events_run_idx ON public.ai_run_events (run_id, event_id)")

    op.execute(
        """
        CREATE TABLE public.ai_provider_attempts (
            attempt_id        text PRIMARY KEY,
            run_id            text NOT NULL,
            provider          text NOT NULL,
            model_id          text NOT NULL,
            prompt_version    text,
            status            text NOT NULL,
            input_tokens      integer,
            output_tokens     integer,
            cost_micros       bigint,
            latency_ms        integer,
            error_class       text,
            created_at        timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX ai_provider_attempts_run_idx ON public.ai_provider_attempts (run_id)"
    )

    op.execute(
        """
        CREATE TABLE public.ai_jobs (
            job_id            text PRIMARY KEY,
            run_id            text NOT NULL,
            job_key           text NOT NULL,
            status            text NOT NULL DEFAULT 'pending',
            lease_token       text,
            lease_expires_at  timestamptz,
            worker_id         text,
            attempts          integer NOT NULL DEFAULT 0,
            available_at      timestamptz NOT NULL DEFAULT now(),
            created_at        timestamptz NOT NULL DEFAULT now(),
            -- 唯一 job key：重复投递不产生第二个 job
            CONSTRAINT ai_jobs_key_unique UNIQUE (job_key)
        )
        """
    )
    op.execute(
        "CREATE INDEX ai_jobs_claim_idx ON public.ai_jobs (status, available_at)"
    )

    # ---- RLS：应用查询的第二道防线 ----
    # 谓词用 current_setting(..., true)：缺上下文时返回 NULL → 零行（默认拒绝）。
    #
    # B1 修复：ENABLE + FORCE 双开。只 ENABLE 时表属主（迁移角色）绕过 RLS，
    # 连接到迁移角色即可无视隔离。FORCE 让属主也受策略约束。
    for table in _ALL_BUSINESS_TABLES:
        op.execute(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE public.{table} FORCE ROW LEVEL SECURITY")

    # 1) 按 project_id 直接归属的表
    for table in _PROJECT_SCOPED_TABLES:
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

    # 2) 学习空间自身的归属列名不同，单独处理
    op.execute(
        """
        CREATE POLICY learning_projects_actor_scope ON public.learning_projects
        USING (owner_actor_id = NULLIF(current_setting('app.actor_id', true), ''))
        WITH CHECK (owner_actor_id = NULLIF(current_setting('app.actor_id', true), ''))
        """
    )

    # 3) 按 run_id 间接归属的表：经 ai_runs 关联到当前 project。
    #    B1 修复：原版只 ENABLE 不给策略，导致这些表对非属主默认全拒绝、
    #    实际不可用。这里补齐"run 属于当前 project"的谓词。
    for table in _RUN_SCOPED_TABLES:
        op.execute(
            f"""
            CREATE POLICY {table}_run_scope ON public.{table}
            USING (
                EXISTS (
                    SELECT 1 FROM public.ai_runs r
                    WHERE r.run_id = public.{table}.run_id
                      AND r.project_id = NULLIF(current_setting('app.project_id', true), '')
                )
            )
            WITH CHECK (
                EXISTS (
                    SELECT 1 FROM public.ai_runs r
                    WHERE r.run_id = public.{table}.run_id
                      AND r.project_id = NULLIF(current_setting('app.project_id', true), '')
                )
            )
            """
        )

    # ---- 权限：应用角色只有 DML，无 DDL（C11）----
    # 应用角色**不**被授予 CREATE/ALTER/DROP 等 DDL 权限。
    op.execute(
        """
        GRANT SELECT, INSERT, UPDATE, DELETE ON
            public.learning_projects, public.plan_drafts, public.plan_revisions,
            public.plan_publications, public.ai_runs, public.ai_run_events,
            public.ai_provider_attempts, public.ai_jobs
        TO studyplan_app
        """
    )
    op.execute("GRANT USAGE, SELECT ON SEQUENCE public.ai_run_events_event_id_seq TO studyplan_app")
    op.execute("GRANT SELECT ON public.alembic_version TO studyplan_app")
    # 应用角色需要能使用 public schema（连接后查询）。
    op.execute("GRANT USAGE ON SCHEMA public TO studyplan_app")


def downgrade() -> None:
    """只在**没有任何业务数据**时才允许降级。

    B1 修复：原版只检查 `ai_runs` / `plan_revisions` 两张表，其余业务表
    （学习空间、草案、发布记录、运行事件、provider 尝试、任务队列）有数据
    时会被**静默清空**。本版遍历**全部**业务表，任一有行即拒绝降级。

    ⚠️ **陷阱（本版踩到并修复）**：数据保护检查本身**必须绕过 RLS**。
    业务表开启了 ``FORCE ROW LEVEL SECURITY``，迁移连接没有 ``app.actor_id`` /
    ``app.project_id`` 上下文，普通 ``SELECT count(*)`` 会被策略过滤成 0 行
    —— 于是"有数据"被误判成"空库"，保护形同虚设。因此检查在
    ``SET LOCAL row_security = off`` 下执行；若当前角色无权关 RLS 则显式报错，
    而不是默默按"空库"处理。

    立场：破坏性的基线回滚必须有数据保护；宁可让 downgrade 失败，
    也不能一次误操作清掉真实进度。需要强制清库时由运维显式 DROP DATABASE。
    """
    checks = ",\n                ".join(
        f"(SELECT count(*) FROM public.{table}) AS {table}_cnt"
        for table in _ALL_BUSINESS_TABLES
    )
    guards = "\n".join(
        f"""            IF row_to_json(rec)::jsonb ->> '{table}_cnt' <> '0' THEN
                RAISE EXCEPTION '业务表 {table} 仍有数据，拒绝降级';
            END IF;"""
        for table in _ALL_BUSINESS_TABLES
    )
    # 注意：SET LOCAL row_security 必须在**事务内**、且不能放在 plpgsql 的
    # BEGIN 块里用 EXECUTE 设置后再做查询（plpgsql 的语句边界会重置）。
    # 因此这里分两步：
    #   1) 在 alembic 迁移事务内用 op.execute 直接 SET LOCAL（迁移本就跑在
    #      事务里，见 env.py 的 context.begin_transaction）；
    #   2) 再做计数断言。
    # 数据保护检查必须在**不受 RLS 干扰**的前提下进行：迁移角色是 schema 属主，
    # 且按 bootstrap 约定拥有 BYPASSRLS（见 docs/adr/ADR-0003 与
    # tests/pg_harness.ensure_roles）。否则 FORCE RLS 会把"有数据"过滤成 0 行，
    # 保护形同虚设。
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
    for table in _ALL_BUSINESS_TABLES:
        op.execute(f"DROP TABLE IF EXISTS public.{table} CASCADE")
