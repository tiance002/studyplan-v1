"""Plan-position progress and immutable operation/source history."""
from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE public.learning_exposures (
            exposure_id text PRIMARY KEY,
            project_id text NOT NULL,
            plan_id text NOT NULL,
            stage_id text NOT NULL,
            unit_id text NOT NULL,
            status text NOT NULL CHECK(status IN ('not_started','in_progress','completed','skipped')),
            version integer NOT NULL CHECK(version>=1),
            node_snapshot jsonb NOT NULL CHECK(jsonb_typeof(node_snapshot)='array'),
            source_snapshot jsonb NOT NULL CHECK(jsonb_typeof(source_snapshot)='object'),
            updated_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE(project_id,plan_id,stage_id,unit_id),
            FOREIGN KEY(project_id,plan_id,stage_id,unit_id)
                REFERENCES public.plan_unit_links(project_id,plan_id,stage_id,unit_id),
            UNIQUE(project_id,exposure_id)
        );
        CREATE TABLE public.learning_exposure_events (
            event_id text PRIMARY KEY,
            project_id text NOT NULL,
            exposure_id text NOT NULL,
            actor_id text NOT NULL,
            idempotency_key text NOT NULL CHECK(length(idempotency_key) BETWEEN 1 AND 128),
            input_hash text NOT NULL,
            from_status text NOT NULL CHECK(from_status IN ('not_started','in_progress','completed','skipped')),
            to_status text NOT NULL CHECK(to_status IN ('not_started','in_progress','completed','skipped')),
            expected_version integer NOT NULL CHECK(expected_version>=0),
            version integer NOT NULL CHECK(version=expected_version+1),
            node_snapshot jsonb NOT NULL CHECK(jsonb_typeof(node_snapshot)='array'),
            source_snapshot jsonb NOT NULL CHECK(jsonb_typeof(source_snapshot)='object'),
            response_snapshot jsonb NOT NULL CHECK(jsonb_typeof(response_snapshot)='object'),
            created_at timestamptz NOT NULL DEFAULT now(),
            FOREIGN KEY(project_id,exposure_id)
                REFERENCES public.learning_exposures(project_id,exposure_id),
            UNIQUE(project_id,actor_id,idempotency_key),
            UNIQUE(exposure_id,version)
        );
        CREATE FUNCTION public.refuse_exposure_history_mutation() RETURNS trigger
            LANGUAGE plpgsql SET search_path=pg_catalog AS $$ BEGIN
            RAISE EXCEPTION 'Learning exposure history is immutable';
        END $$;
        CREATE TRIGGER exposure_history_immutable BEFORE UPDATE OR DELETE ON public.learning_exposure_events
            FOR EACH ROW EXECUTE FUNCTION public.refuse_exposure_history_mutation();
        REVOKE ALL ON FUNCTION public.refuse_exposure_history_mutation() FROM PUBLIC;
    """)
    for table in ("learning_exposures", "learning_exposure_events"):
        op.execute(f"""
            ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY;
            ALTER TABLE public.{table} FORCE ROW LEVEL SECURITY;
            CREATE POLICY {table}_owner ON public.{table}
            USING(project_id=NULLIF(current_setting('app.project_id',true),'') AND EXISTS(
                SELECT 1 FROM public.learning_projects p WHERE p.project_id={table}.project_id
                AND p.owner_actor_id=NULLIF(current_setting('app.actor_id',true),'')
                AND p.archived_at IS NULL))
            WITH CHECK(project_id=NULLIF(current_setting('app.project_id',true),'') AND EXISTS(
                SELECT 1 FROM public.learning_projects p WHERE p.project_id={table}.project_id
                AND p.owner_actor_id=NULLIF(current_setting('app.actor_id',true),'')
                AND p.archived_at IS NULL));
        """)
    op.execute("GRANT SELECT,INSERT,UPDATE ON public.learning_exposures TO studyplan_app")
    op.execute("GRANT SELECT,INSERT ON public.learning_exposure_events TO studyplan_app")


def downgrade():
    op.execute("""DO $$ BEGIN
        IF EXISTS(SELECT 1 FROM public.learning_exposures)
            OR EXISTS(SELECT 1 FROM public.learning_exposure_events) THEN
            RAISE EXCEPTION 'Exposure history exists; refuse data-losing downgrade';
        END IF;
    END $$;
    DROP TABLE public.learning_exposure_events;
    DROP TABLE public.learning_exposures;
    DROP FUNCTION public.refuse_exposure_history_mutation();
    """)
