"""Nullable unit position permits immutable stage summaries beside legacy units."""
from alembic import op

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        ALTER TABLE public.summary_attempts ALTER COLUMN unit_id DROP NOT NULL,
            ADD CONSTRAINT summary_stage_fk FOREIGN KEY(project_id,plan_id,stage_id)
                REFERENCES public.plan_stages(project_id,plan_id,stage_id),
            ADD CONSTRAINT summary_stage_required CHECK(unit_id IS NOT NULL OR
                (plan_id IS NOT NULL AND stage_id IS NOT NULL));
        CREATE UNIQUE INDEX summary_stage_version ON public.summary_attempts(project_id,plan_id,stage_id,version)
            WHERE unit_id IS NULL;
        CREATE TABLE public.summary_stage_heads (
            project_id text NOT NULL,plan_id text NOT NULL,stage_id text NOT NULL,
            version integer NOT NULL CHECK(version>=1),
            PRIMARY KEY(project_id,plan_id,stage_id),
            FOREIGN KEY(project_id,plan_id,stage_id) REFERENCES public.plan_stages(project_id,plan_id,stage_id)
        );
        ALTER TABLE public.summary_stage_heads ENABLE ROW LEVEL SECURITY;
        ALTER TABLE public.summary_stage_heads FORCE ROW LEVEL SECURITY;
        CREATE POLICY summary_stage_heads_owner ON public.summary_stage_heads USING(
            project_id=NULLIF(current_setting('app.project_id',true),'') AND EXISTS(
                SELECT 1 FROM public.learning_projects p WHERE p.project_id=summary_stage_heads.project_id
                AND p.owner_actor_id=NULLIF(current_setting('app.actor_id',true),'') AND p.archived_at IS NULL))
            WITH CHECK(project_id=NULLIF(current_setting('app.project_id',true),'') AND EXISTS(
                SELECT 1 FROM public.learning_projects p WHERE p.project_id=summary_stage_heads.project_id
                AND p.owner_actor_id=NULLIF(current_setting('app.actor_id',true),'') AND p.archived_at IS NULL));
        GRANT SELECT,INSERT,UPDATE ON public.summary_stage_heads TO studyplan_app;
    """)


def downgrade():
    op.execute("""DO $$ BEGIN
        IF EXISTS(SELECT 1 FROM public.summary_stage_heads) OR
           EXISTS(SELECT 1 FROM public.summary_attempts WHERE unit_id IS NULL)
        THEN RAISE EXCEPTION 'Stage summary history exists; refuse destructive downgrade'; END IF; END $$;
        DROP TABLE public.summary_stage_heads;
        DROP INDEX public.summary_stage_version;
        ALTER TABLE public.summary_attempts DROP CONSTRAINT summary_stage_fk,
            DROP CONSTRAINT summary_stage_required, ALTER COLUMN unit_id SET NOT NULL;
    """)
