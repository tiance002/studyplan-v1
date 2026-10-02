"""Private discovery evidence and separately metered durable inspections."""
from alembic import op

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        ALTER TABLE public.resource_search_requests
            ADD COLUMN source text NOT NULL DEFAULT 'web' CHECK(source IN ('web','github')),
            ADD COLUMN context_snapshot jsonb NOT NULL DEFAULT '{}' CHECK(jsonb_typeof(context_snapshot)='object'),
            ADD COLUMN node_id text,
            ADD CONSTRAINT resource_search_project_id_unique UNIQUE(project_id,search_id);
        CREATE TABLE public.resource_read_usage_counter (
            singleton boolean PRIMARY KEY DEFAULT true CHECK(singleton),
            content_reserved integer NOT NULL DEFAULT 0 CHECK(content_reserved>=0),
            metadata_reserved integer NOT NULL DEFAULT 0 CHECK(metadata_reserved>=0)
        );
        INSERT INTO public.resource_read_usage_counter(singleton) VALUES(true);
        GRANT SELECT,UPDATE ON public.resource_read_usage_counter TO studyplan_app;
        CREATE FUNCTION public.guard_resource_read_counter() RETURNS trigger
            LANGUAGE plpgsql SET search_path=pg_catalog AS $$
        BEGIN
            IF NEW.content_reserved <> OLD.content_reserved+3
                OR NEW.metadata_reserved <> OLD.metadata_reserved+2 THEN
                RAISE EXCEPTION 'Inspection reservation must debit three content and two metadata slots';
            END IF;
            RETURN NEW;
        END $$;
        CREATE TRIGGER resource_read_counter_monotonic BEFORE UPDATE ON public.resource_read_usage_counter
            FOR EACH ROW EXECUTE FUNCTION public.guard_resource_read_counter();
        REVOKE ALL ON FUNCTION public.guard_resource_read_counter() FROM PUBLIC;
        CREATE TABLE public.resource_inspection_requests (
            inspection_id text PRIMARY KEY,
            project_id text NOT NULL,
            actor_id text NOT NULL,
            plan_id text NOT NULL,
            stage_id text NOT NULL,
            unit_id text NOT NULL,
            search_id text NOT NULL,
            candidate_id text NOT NULL,
            idempotency_key text NOT NULL CHECK(length(idempotency_key) BETWEEN 1 AND 128),
            input_hash text NOT NULL,
            status text NOT NULL CHECK(status IN ('dispatched','succeeded','failed','reconciliation_required')),
            paths jsonb NOT NULL DEFAULT '[]' CHECK(jsonb_typeof(paths)='array'),
            context_snapshot jsonb NOT NULL DEFAULT '{}' CHECK(jsonb_typeof(context_snapshot)='object'),
            candidate_snapshot jsonb NOT NULL DEFAULT '{}' CHECK(jsonb_typeof(candidate_snapshot)='object'),
            receipts jsonb NOT NULL DEFAULT '[]' CHECK(jsonb_typeof(receipts)='array'),
            error text,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE(project_id,actor_id,idempotency_key),
            FOREIGN KEY(project_id,plan_id,stage_id,unit_id)
                REFERENCES public.plan_unit_links(project_id,plan_id,stage_id,unit_id),
            FOREIGN KEY(project_id,search_id)
                REFERENCES public.resource_search_requests(project_id,search_id)
        );
        ALTER TABLE public.resource_inspection_requests ENABLE ROW LEVEL SECURITY;
        ALTER TABLE public.resource_inspection_requests FORCE ROW LEVEL SECURITY;
        CREATE POLICY resource_inspection_requests_owner ON public.resource_inspection_requests
        USING (project_id=NULLIF(current_setting('app.project_id',true),'') AND EXISTS(
            SELECT 1 FROM public.learning_projects p WHERE p.project_id=resource_inspection_requests.project_id
            AND p.owner_actor_id=NULLIF(current_setting('app.actor_id',true),'') AND p.archived_at IS NULL))
        WITH CHECK (project_id=NULLIF(current_setting('app.project_id',true),'') AND EXISTS(
            SELECT 1 FROM public.learning_projects p WHERE p.project_id=resource_inspection_requests.project_id
            AND p.owner_actor_id=NULLIF(current_setting('app.actor_id',true),'') AND p.archived_at IS NULL));
        GRANT SELECT,INSERT,UPDATE ON public.resource_inspection_requests TO studyplan_app;
    """)


def downgrade():
    op.execute("""DO $$ BEGIN
        IF EXISTS(SELECT 1 FROM public.resource_inspection_requests)
            OR EXISTS(SELECT 1 FROM public.resource_read_usage_counter WHERE content_reserved>0 OR metadata_reserved>0)
            OR EXISTS(SELECT 1 FROM public.resource_search_requests WHERE source='github' OR context_snapshot<>'{}') THEN
            RAISE EXCEPTION 'Discovery history exists; refuse data-losing downgrade';
        END IF;
    END $$;
    DROP TABLE public.resource_inspection_requests;
    DROP TABLE public.resource_read_usage_counter;
    DROP FUNCTION public.guard_resource_read_counter();
    ALTER TABLE public.resource_search_requests DROP CONSTRAINT resource_search_project_id_unique,
        DROP COLUMN source, DROP COLUMN context_snapshot, DROP COLUMN node_id;
    """)
