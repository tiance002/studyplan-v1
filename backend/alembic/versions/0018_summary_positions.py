"""Immutable position summary revisions, receipts and review bindings."""
from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        ALTER TABLE public.summary_attempts
            ADD COLUMN plan_id text,
            ADD COLUMN stage_id text,
            ADD COLUMN version integer NOT NULL DEFAULT 0 CHECK(version>=0),
            ADD COLUMN content_hash text,
            ADD COLUMN rubric_snapshot jsonb NOT NULL DEFAULT '{}'::jsonb,
            ADD CONSTRAINT summary_position_optional CHECK((plan_id IS NULL AND stage_id IS NULL AND version=0)
                OR (plan_id IS NOT NULL AND stage_id IS NOT NULL AND version>=1)),
            ADD CONSTRAINT summary_position_fk FOREIGN KEY(project_id,plan_id,stage_id,unit_id)
                REFERENCES public.plan_unit_links(project_id,plan_id,stage_id,unit_id),
            ADD CONSTRAINT summary_project_attempt UNIQUE(project_id,attempt_id),
            ADD CONSTRAINT summary_position_version UNIQUE(project_id,plan_id,stage_id,unit_id,version);
        CREATE TABLE public.summary_position_heads (
            project_id text NOT NULL,plan_id text NOT NULL,stage_id text NOT NULL,unit_id text NOT NULL,
            version integer NOT NULL CHECK(version>=1),
            PRIMARY KEY(project_id,plan_id,stage_id,unit_id),
            FOREIGN KEY(project_id,plan_id,stage_id,unit_id)
                REFERENCES public.plan_unit_links(project_id,plan_id,stage_id,unit_id)
        );
        CREATE TABLE public.summary_receipts (
            receipt_id text PRIMARY KEY,project_id text NOT NULL REFERENCES public.learning_projects(project_id),
            actor_id text NOT NULL,idempotency_key text NOT NULL CHECK(length(idempotency_key) BETWEEN 1 AND 128),
            action text NOT NULL CHECK(action IN('save','review','cancel')),
            input_hash text NOT NULL,response_snapshot jsonb NOT NULL,created_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE(project_id,actor_id,idempotency_key)
        );
        CREATE TABLE public.summary_review_bindings (
            project_id text NOT NULL,attempt_id text NOT NULL,run_id text NOT NULL REFERENCES public.ai_runs(run_id),
            actor_id text NOT NULL,manifest jsonb NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY(project_id,attempt_id),UNIQUE(run_id),
            FOREIGN KEY(project_id,attempt_id) REFERENCES public.summary_attempts(project_id,attempt_id)
        );
        CREATE INDEX summary_history_order ON public.summary_attempts(project_id,created_at DESC,attempt_id DESC);
        CREATE TRIGGER summary_attempt_immutable BEFORE UPDATE OR DELETE ON public.summary_attempts
            FOR EACH ROW EXECUTE FUNCTION public.refuse_exposure_history_mutation();
        CREATE TRIGGER summary_review_immutable BEFORE UPDATE OR DELETE ON public.summary_reviews
            FOR EACH ROW EXECUTE FUNCTION public.refuse_exposure_history_mutation();
        CREATE TRIGGER summary_receipt_immutable BEFORE UPDATE OR DELETE ON public.summary_receipts
            FOR EACH ROW EXECUTE FUNCTION public.refuse_exposure_history_mutation();
        CREATE TRIGGER summary_binding_immutable BEFORE UPDATE OR DELETE ON public.summary_review_bindings
            FOR EACH ROW EXECUTE FUNCTION public.refuse_exposure_history_mutation();
    """)
    for table in ("summary_attempts", "summary_reviews", "summary_position_heads", "summary_receipts", "summary_review_bindings"):
        if table in {"summary_attempts", "summary_reviews"}:
            op.execute(f"DROP POLICY {table}_project_scope ON public.{table}")
        actor_check = " AND actor_id=NULLIF(current_setting('app.actor_id',true),'')" if table in {"summary_receipts", "summary_review_bindings"} else ""
        op.execute(f"""ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY;
            ALTER TABLE public.{table} FORCE ROW LEVEL SECURITY;
            CREATE POLICY {table}_owner ON public.{table} USING(
                project_id=NULLIF(current_setting('app.project_id',true),'') AND EXISTS(
                SELECT 1 FROM public.learning_projects p WHERE p.project_id={table}.project_id
                AND p.owner_actor_id=NULLIF(current_setting('app.actor_id',true),'') AND p.archived_at IS NULL))
            WITH CHECK(project_id=NULLIF(current_setting('app.project_id',true),'') {actor_check} AND EXISTS(
                SELECT 1 FROM public.learning_projects p WHERE p.project_id={table}.project_id
                AND p.owner_actor_id=NULLIF(current_setting('app.actor_id',true),'') AND p.archived_at IS NULL));""")
    op.execute("""REVOKE UPDATE,DELETE ON public.summary_attempts,public.summary_reviews FROM studyplan_app;
        GRANT SELECT,INSERT ON public.summary_receipts,public.summary_review_bindings TO studyplan_app;
        GRANT SELECT,INSERT,UPDATE ON public.summary_position_heads TO studyplan_app;""")


def downgrade():
    op.execute("""DO $$ BEGIN
        IF EXISTS(SELECT 1 FROM public.summary_position_heads) OR EXISTS(SELECT 1 FROM public.summary_receipts)
           OR EXISTS(SELECT 1 FROM public.summary_review_bindings) OR EXISTS(SELECT 1 FROM public.summary_attempts WHERE plan_id IS NOT NULL)
        THEN RAISE EXCEPTION 'Summary history exists; refuse destructive downgrade'; END IF; END $$;
        DROP TABLE public.summary_review_bindings;
        DROP TABLE public.summary_receipts;
        DROP TABLE public.summary_position_heads;
        DROP TRIGGER summary_attempt_immutable ON public.summary_attempts;
        DROP TRIGGER summary_review_immutable ON public.summary_reviews;
        DROP INDEX public.summary_history_order;
        ALTER TABLE public.summary_attempts DROP CONSTRAINT summary_project_attempt,
            DROP CONSTRAINT summary_position_version,DROP CONSTRAINT summary_position_fk,
            DROP CONSTRAINT summary_position_optional,DROP COLUMN plan_id,DROP COLUMN stage_id,
            DROP COLUMN version,DROP COLUMN content_hash,DROP COLUMN rubric_snapshot;
    """)
    for table in ("summary_attempts", "summary_reviews"):
        op.execute(f"DROP POLICY {table}_owner ON public.{table}; CREATE POLICY {table}_project_scope "
                   f"ON public.{table} USING(project_id=current_setting('app.project_id',true)) "
                   f"WITH CHECK(project_id=current_setting('app.project_id',true));")
    op.execute("GRANT UPDATE,DELETE ON public.summary_attempts,public.summary_reviews TO studyplan_app")
