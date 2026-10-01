"""Position-bound immutable manual originals and human acceptance history."""

from alembic import op

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        ALTER TABLE public.practice_submissions
            ADD COLUMN plan_id text, ADD COLUMN stage_id text, ADD COLUMN actor_id text,
            ADD COLUMN submission_no integer NOT NULL DEFAULT 0 CHECK(submission_no>=0),
            ADD COLUMN version integer NOT NULL DEFAULT 0 CHECK(version>=0),
            ADD COLUMN content_hash text, ADD COLUMN task_snapshot jsonb NOT NULL DEFAULT '{}'::jsonb,
            ADD COLUMN evidence_details jsonb NOT NULL DEFAULT '[]'::jsonb CHECK(jsonb_typeof(evidence_details)='array'),
            ADD COLUMN artifact_kind text NOT NULL DEFAULT 'other' CHECK(artifact_kind IN
                ('project_description','evaluation','architecture','design_decision','failure_review','explanation','other')),
            ADD COLUMN parent_submission_id text,
            ADD CONSTRAINT submission_position_optional CHECK(
                (plan_id IS NULL AND stage_id IS NULL AND version=0 AND submission_no=0)
                OR (plan_id IS NOT NULL AND stage_id IS NOT NULL AND version>=1 AND submission_no>=1 AND actor_id IS NOT NULL)),
            ADD CONSTRAINT submission_new_grade CHECK(actor_id IS NULL OR
                (evidence_grade IN('reported','insufficient') AND verification IS NULL)),
            ADD CONSTRAINT submission_position_fk FOREIGN KEY(project_id,plan_id,stage_id,task_id)
                REFERENCES public.plan_task_links(project_id,plan_id,stage_id,task_id),
            ADD CONSTRAINT submission_parent_scope FOREIGN KEY(project_id,parent_submission_id)
                REFERENCES public.practice_submissions(project_id,submission_id),
            ADD CONSTRAINT submission_not_self_parent CHECK(parent_submission_id IS DISTINCT FROM submission_id),
            ADD CONSTRAINT submission_position_version UNIQUE(project_id,plan_id,stage_id,task_id,version);
        ALTER TABLE public.acceptance_reviews
            ADD COLUMN actor_id text, ADD COLUMN coverage jsonb NOT NULL DEFAULT '[]'::jsonb CHECK(jsonb_typeof(coverage)='array'),
            ADD COLUMN acknowledge_verification_limit boolean NOT NULL DEFAULT false,
            ADD COLUMN basis_snapshot jsonb NOT NULL DEFAULT '{}'::jsonb,
            ADD CONSTRAINT acceptance_new_user CHECK(actor_id IS NULL OR reviewer_kind='user');
        CREATE TABLE public.submission_position_heads (
            project_id text NOT NULL,plan_id text NOT NULL,stage_id text NOT NULL,task_id text NOT NULL,
            version integer NOT NULL CHECK(version>=1),PRIMARY KEY(project_id,plan_id,stage_id,task_id),
            FOREIGN KEY(project_id,plan_id,stage_id,task_id) REFERENCES public.plan_task_links(project_id,plan_id,stage_id,task_id));
        CREATE TABLE public.submission_receipts (
            receipt_id text PRIMARY KEY,project_id text NOT NULL REFERENCES public.learning_projects(project_id),
            actor_id text NOT NULL,idempotency_key text NOT NULL CHECK(length(idempotency_key) BETWEEN 1 AND 128),
            action text NOT NULL CHECK(action IN('save','decide')),input_hash text NOT NULL,response_snapshot jsonb NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),UNIQUE(project_id,actor_id,idempotency_key));
        CREATE INDEX submission_history_order ON public.practice_submissions(project_id,created_at DESC,submission_id DESC);
    """)
    for table in (
        "practice_submissions",
        "acceptance_reviews",
        "submission_position_heads",
        "submission_receipts",
    ):
        if table in {"practice_submissions", "acceptance_reviews"}:
            op.execute(f"DROP POLICY {table}_project_scope ON public.{table}")
        actor_check = (
            " AND actor_id=NULLIF(current_setting('app.actor_id',true),'')"
            if table != "submission_position_heads"
            else ""
        )
        op.execute(f"""
            ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY;
            ALTER TABLE public.{table} FORCE ROW LEVEL SECURITY;
            CREATE POLICY {table}_owner ON public.{table}
            USING(project_id=NULLIF(current_setting('app.project_id',true),'') AND EXISTS(
                SELECT 1 FROM public.learning_projects p WHERE p.project_id={table}.project_id
                AND p.owner_actor_id=NULLIF(current_setting('app.actor_id',true),'') AND p.archived_at IS NULL))
            WITH CHECK(project_id=NULLIF(current_setting('app.project_id',true),'') {actor_check} AND EXISTS(
                SELECT 1 FROM public.learning_projects p WHERE p.project_id={table}.project_id
                AND p.owner_actor_id=NULLIF(current_setting('app.actor_id',true),'') AND p.archived_at IS NULL));
        """)
        if table != "submission_position_heads":
            op.execute(f"""CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON public.{table}
                FOR EACH ROW EXECUTE FUNCTION public.refuse_exposure_history_mutation();""")
    op.execute("""
        REVOKE UPDATE,DELETE ON public.practice_submissions,public.acceptance_reviews,public.submission_receipts FROM studyplan_app;
        REVOKE DELETE ON public.submission_position_heads FROM studyplan_app;
        GRANT SELECT,INSERT ON public.submission_receipts TO studyplan_app;
        GRANT SELECT,INSERT,UPDATE ON public.submission_position_heads TO studyplan_app;
    """)


def downgrade():
    op.execute("""DO $$ BEGIN
        IF EXISTS(SELECT 1 FROM public.submission_receipts)
            OR EXISTS(SELECT 1 FROM public.practice_submissions WHERE plan_id IS NOT NULL OR actor_id IS NOT NULL)
            OR EXISTS(SELECT 1 FROM public.acceptance_reviews WHERE actor_id IS NOT NULL)
            OR EXISTS(SELECT 1 FROM public.submission_position_heads) THEN
            RAISE EXCEPTION 'Submission history exists; refuse destructive downgrade';
        END IF; END $$;
        DROP TABLE public.submission_receipts; DROP TABLE public.submission_position_heads;
        DROP INDEX public.submission_history_order;
        DROP TRIGGER practice_submissions_immutable ON public.practice_submissions;
        DROP TRIGGER acceptance_reviews_immutable ON public.acceptance_reviews;
        ALTER TABLE public.practice_submissions DROP CONSTRAINT submission_position_version,
            DROP CONSTRAINT submission_not_self_parent,DROP CONSTRAINT submission_parent_scope,
            DROP CONSTRAINT submission_position_fk,DROP CONSTRAINT submission_new_grade,DROP CONSTRAINT submission_position_optional,
            DROP COLUMN plan_id,DROP COLUMN stage_id,DROP COLUMN actor_id,DROP COLUMN submission_no,DROP COLUMN version,
            DROP COLUMN content_hash,DROP COLUMN task_snapshot,DROP COLUMN evidence_details,DROP COLUMN artifact_kind,
            DROP COLUMN parent_submission_id;
        ALTER TABLE public.acceptance_reviews DROP CONSTRAINT acceptance_new_user,DROP COLUMN actor_id,
            DROP COLUMN coverage,DROP COLUMN acknowledge_verification_limit,DROP COLUMN basis_snapshot;
    """)
    for table in ("practice_submissions", "acceptance_reviews"):
        op.execute(f"""DROP POLICY {table}_owner ON public.{table};
            CREATE POLICY {table}_project_scope ON public.{table}
            USING(project_id=NULLIF(current_setting('app.project_id',true),''))
            WITH CHECK(project_id=NULLIF(current_setting('app.project_id',true),''));""")
    op.execute(
        "GRANT UPDATE,DELETE ON public.practice_submissions,public.acceptance_reviews TO studyplan_app"
    )
