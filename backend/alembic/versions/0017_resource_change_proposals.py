"""Ordinary plan-resource proposals and immutable command receipts."""
from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE FUNCTION public.lock_reviewed_resource_index(request_source_id text) RETURNS boolean
            LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$ BEGIN
            IF request_source_id IS NULL OR length(request_source_id) NOT BETWEEN 1 AND 512 THEN RETURN false; END IF;
            PERFORM source_id FROM public.public_resource_sources WHERE source_id=request_source_id
                AND verification_status='reviewed' AND checked_at IS NOT NULL FOR UPDATE;
            IF NOT FOUND THEN RETURN false; END IF;
            PERFORM section_id FROM public.public_resource_sections WHERE source_id=request_source_id FOR SHARE;
            RETURN true;
        END $$;
        REVOKE ALL ON FUNCTION public.lock_reviewed_resource_index(text) FROM PUBLIC;
        GRANT EXECUTE ON FUNCTION public.lock_reviewed_resource_index(text) TO studyplan_app;
        ALTER TABLE public.plan_drafts ADD CONSTRAINT plan_drafts_project_draft_unique UNIQUE(project_id,draft_id);
        CREATE TABLE public.resource_change_proposals (
            proposal_id text PRIMARY KEY, project_id text NOT NULL,
            actor_id text NOT NULL, draft_id text NOT NULL,
            base_plan_id text NOT NULL, base_revision integer NOT NULL,
            status text NOT NULL CHECK(status IN('pending','confirmed','cancelled')),
            preview_hash text NOT NULL, catalog_digest text NOT NULL,
            payload jsonb NOT NULL CHECK(jsonb_typeof(payload)='object'),
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE(project_id,draft_id),
            UNIQUE(project_id,proposal_id),
            FOREIGN KEY(project_id,draft_id) REFERENCES public.plan_drafts(project_id,draft_id),
            FOREIGN KEY(project_id,base_plan_id) REFERENCES public.plan_revisions(project_id,plan_id)
        );
        ALTER TABLE public.plan_drafts ADD COLUMN resource_change_proposal_id text;
        ALTER TABLE public.plan_drafts ADD CONSTRAINT plan_drafts_resource_proposal_scope
            FOREIGN KEY(project_id,resource_change_proposal_id)
            REFERENCES public.resource_change_proposals(project_id,proposal_id);
        CREATE TABLE public.resource_change_receipts (
            receipt_id text PRIMARY KEY, project_id text NOT NULL, actor_id text NOT NULL,
            idempotency_key text NOT NULL CHECK(length(idempotency_key) BETWEEN 1 AND 128),
            action text NOT NULL CHECK(action IN('preview','confirm','cancel')),
            input_hash text NOT NULL, response_snapshot jsonb NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE(project_id,actor_id,idempotency_key)
        );
        CREATE TRIGGER resource_change_receipts_immutable BEFORE UPDATE OR DELETE
            ON public.resource_change_receipts FOR EACH ROW
            EXECUTE FUNCTION public.refuse_exposure_history_mutation();
    """)
    for table in ("resource_change_proposals", "resource_change_receipts"):
        op.execute(f"""
            ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY;
            ALTER TABLE public.{table} FORCE ROW LEVEL SECURITY;
            CREATE POLICY {table}_owner ON public.{table}
            USING(project_id=NULLIF(current_setting('app.project_id',true),'') AND EXISTS(
                SELECT 1 FROM public.learning_projects p WHERE p.project_id={table}.project_id
                AND p.owner_actor_id=NULLIF(current_setting('app.actor_id',true),'') AND p.archived_at IS NULL))
            WITH CHECK(project_id=NULLIF(current_setting('app.project_id',true),'')
                AND actor_id=NULLIF(current_setting('app.actor_id',true),'') AND EXISTS(
                SELECT 1 FROM public.learning_projects p WHERE p.project_id={table}.project_id
                AND p.owner_actor_id=NULLIF(current_setting('app.actor_id',true),'') AND p.archived_at IS NULL));
        """)
    op.execute("GRANT SELECT,INSERT,UPDATE ON public.resource_change_proposals TO studyplan_app")
    op.execute("GRANT SELECT,INSERT ON public.resource_change_receipts TO studyplan_app")


def downgrade():
    op.execute("""DO $$ BEGIN
        IF EXISTS(SELECT 1 FROM public.resource_change_proposals)
            OR EXISTS(SELECT 1 FROM public.resource_change_receipts) THEN
            RAISE EXCEPTION 'Resource proposal history exists; refuse destructive downgrade';
        END IF;
    END $$;
    DROP TABLE public.resource_change_receipts;
    ALTER TABLE public.plan_drafts DROP CONSTRAINT plan_drafts_resource_proposal_scope;
    ALTER TABLE public.plan_drafts DROP COLUMN resource_change_proposal_id;
    DROP TABLE public.resource_change_proposals;
    ALTER TABLE public.plan_drafts DROP CONSTRAINT plan_drafts_project_draft_unique;
    DROP FUNCTION public.lock_reviewed_resource_index(text);
    """)
