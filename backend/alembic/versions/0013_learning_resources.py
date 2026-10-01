"""Private unit resource selections and durable bounded search reservations."""
from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        ALTER TABLE public.plan_unit_links ADD CONSTRAINT plan_unit_position_unique
            UNIQUE(project_id,plan_id,stage_id,unit_id);
        CREATE TABLE public.search_usage_counter (
            singleton boolean PRIMARY KEY DEFAULT true CHECK(singleton),
            request_count integer NOT NULL DEFAULT 0 CHECK(request_count BETWEEN 0 AND 1000)
        );
        INSERT INTO public.search_usage_counter(singleton) VALUES(true);
        GRANT SELECT,UPDATE ON public.search_usage_counter TO studyplan_app;
        CREATE FUNCTION public.guard_search_counter() RETURNS trigger
            LANGUAGE plpgsql SET search_path=pg_catalog AS $$
        BEGIN
            IF NEW.request_count <> OLD.request_count + 1 THEN
                RAISE EXCEPTION 'Search reservations must increment monotonically by one';
            END IF;
            RETURN NEW;
        END $$;
        CREATE TRIGGER search_counter_monotonic BEFORE UPDATE ON public.search_usage_counter
            FOR EACH ROW EXECUTE FUNCTION public.guard_search_counter();
        REVOKE ALL ON FUNCTION public.guard_search_counter() FROM PUBLIC;
        CREATE TABLE public.resource_search_requests (
            search_id text PRIMARY KEY,
            project_id text NOT NULL,
            actor_id text NOT NULL,
            plan_id text NOT NULL,
            stage_id text NOT NULL,
            unit_id text NOT NULL,
            idempotency_key text NOT NULL CHECK(length(idempotency_key) BETWEEN 1 AND 128),
            input_hash text NOT NULL,
            query text NOT NULL CHECK(length(query) BETWEEN 1 AND 500),
            status text NOT NULL CHECK(status IN ('dispatched','succeeded','failed','reconciliation_required')),
            candidates jsonb NOT NULL DEFAULT '[]' CHECK(jsonb_typeof(candidates)='array'),
            error text,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE(project_id,actor_id,idempotency_key),
            FOREIGN KEY(project_id,plan_id,stage_id,unit_id)
                REFERENCES public.plan_unit_links(project_id,plan_id,stage_id,unit_id)
        );
        CREATE TABLE public.learning_resource_selections (
            selection_id text PRIMARY KEY,
            project_id text NOT NULL,
            plan_id text NOT NULL,
            stage_id text NOT NULL,
            unit_id text NOT NULL,
            resource_id text NOT NULL,
            resource_snapshot jsonb NOT NULL CHECK(jsonb_typeof(resource_snapshot)='object'),
            created_at timestamptz NOT NULL DEFAULT now(),
            removed_at timestamptz,
            FOREIGN KEY(project_id,plan_id,stage_id,unit_id)
                REFERENCES public.plan_unit_links(project_id,plan_id,stage_id,unit_id),
            FOREIGN KEY(project_id,resource_id) REFERENCES public.resource_records(project_id,resource_id)
        );
        CREATE UNIQUE INDEX selected_resource_active_unique ON public.learning_resource_selections
            (project_id,plan_id,unit_id,resource_id) WHERE removed_at IS NULL;
    """)
    for table in ("resource_search_requests", "learning_resource_selections"):
        op.execute(f"""
            ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY;
            ALTER TABLE public.{table} FORCE ROW LEVEL SECURITY;
            CREATE POLICY {table}_owner ON public.{table}
            USING (project_id=NULLIF(current_setting('app.project_id',true),'') AND EXISTS(
                SELECT 1 FROM public.learning_projects p WHERE p.project_id={table}.project_id
                AND p.owner_actor_id=NULLIF(current_setting('app.actor_id',true),'')
                AND p.archived_at IS NULL))
            WITH CHECK (project_id=NULLIF(current_setting('app.project_id',true),'') AND EXISTS(
                SELECT 1 FROM public.learning_projects p WHERE p.project_id={table}.project_id
                AND p.owner_actor_id=NULLIF(current_setting('app.actor_id',true),'')
                AND p.archived_at IS NULL));
            GRANT SELECT,INSERT,UPDATE ON public.{table} TO studyplan_app;
        """)


def downgrade():
    op.execute("""DO $$ BEGIN
        IF EXISTS(SELECT 1 FROM public.resource_search_requests)
            OR EXISTS(SELECT 1 FROM public.learning_resource_selections)
            OR EXISTS(SELECT 1 FROM public.search_usage_counter WHERE request_count>0) THEN
            RAISE EXCEPTION 'Resource/search history exists; refuse data-losing downgrade';
        END IF;
    END $$""")
    op.execute("""
        DROP TABLE public.learning_resource_selections;
        DROP TABLE public.resource_search_requests;
        DROP TABLE public.search_usage_counter;
        DROP FUNCTION public.guard_search_counter();
        ALTER TABLE public.plan_unit_links DROP CONSTRAINT plan_unit_position_unique;
    """)
