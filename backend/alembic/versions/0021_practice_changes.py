"""Controlled practice candidates and immutable preview/decision receipts."""

from alembic import op

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE public.practice_change_proposals (
            proposal_id text PRIMARY KEY,project_id text NOT NULL,actor_id text NOT NULL,draft_id text NOT NULL,
            base_plan_id text NOT NULL,base_revision integer NOT NULL,base_version integer NOT NULL,
            status text NOT NULL CHECK(status IN('pending','confirmed','cancelled')),preview_hash text NOT NULL,
            payload jsonb NOT NULL CHECK(jsonb_typeof(payload)='object'),created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),UNIQUE(project_id,draft_id),UNIQUE(project_id,proposal_id),
            UNIQUE(project_id,draft_id,proposal_id),
            FOREIGN KEY(project_id,draft_id) REFERENCES public.plan_drafts(project_id,draft_id),
            FOREIGN KEY(project_id,base_plan_id) REFERENCES public.plan_revisions(project_id,plan_id));
        ALTER TABLE public.plan_drafts ADD COLUMN practice_change_proposal_id text,
            ADD CONSTRAINT plan_drafts_practice_proposal_scope FOREIGN KEY(project_id,draft_id,practice_change_proposal_id)
                REFERENCES public.practice_change_proposals(project_id,draft_id,proposal_id),
            ADD CONSTRAINT plan_drafts_one_proposal CHECK(resource_change_proposal_id IS NULL OR practice_change_proposal_id IS NULL);
        CREATE TABLE public.practice_change_receipts (
            receipt_id text PRIMARY KEY,project_id text NOT NULL REFERENCES public.learning_projects(project_id),actor_id text NOT NULL,
            idempotency_key text NOT NULL CHECK(length(idempotency_key) BETWEEN 1 AND 128),
            action text NOT NULL CHECK(action IN('preview','confirm','cancel')),input_hash text NOT NULL,response_snapshot jsonb NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),UNIQUE(project_id,actor_id,idempotency_key));
        CREATE FUNCTION public.protect_practice_proposal() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$ BEGIN
            IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Practice proposal history is immutable'; END IF;
            IF OLD.status<>'pending' OR NEW.status NOT IN('confirmed','cancelled')
                OR (to_jsonb(NEW)-'status'-'updated_at') IS DISTINCT FROM (to_jsonb(OLD)-'status'-'updated_at') THEN
                RAISE EXCEPTION 'Practice proposal payload is immutable'; END IF;
            RETURN NEW; END $$;
        CREATE TRIGGER practice_proposal_immutable BEFORE UPDATE OR DELETE ON public.practice_change_proposals
            FOR EACH ROW EXECUTE FUNCTION public.protect_practice_proposal();
        CREATE TRIGGER practice_receipt_immutable BEFORE UPDATE OR DELETE ON public.practice_change_receipts
            FOR EACH ROW EXECUTE FUNCTION public.refuse_exposure_history_mutation();
    """)
    for table in ("practice_change_proposals", "practice_change_receipts"):
        op.execute(f"""ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY; ALTER TABLE public.{table} FORCE ROW LEVEL SECURITY;
            CREATE POLICY {table}_owner ON public.{table} USING(project_id=NULLIF(current_setting('app.project_id',true),'')
                AND EXISTS(SELECT 1 FROM public.learning_projects p WHERE p.project_id={table}.project_id
                    AND p.owner_actor_id=NULLIF(current_setting('app.actor_id',true),'') AND p.archived_at IS NULL))
            WITH CHECK(project_id=NULLIF(current_setting('app.project_id',true),'') AND actor_id=NULLIF(current_setting('app.actor_id',true),'')
                AND EXISTS(SELECT 1 FROM public.learning_projects p WHERE p.project_id={table}.project_id
                    AND p.owner_actor_id=NULLIF(current_setting('app.actor_id',true),'') AND p.archived_at IS NULL));""")
    op.execute(
        "GRANT SELECT,INSERT,UPDATE ON public.practice_change_proposals TO studyplan_app; GRANT SELECT,INSERT ON public.practice_change_receipts TO studyplan_app"
    )


def downgrade():
    op.execute("""DO $$ BEGIN IF EXISTS(SELECT 1 FROM public.practice_change_proposals) OR EXISTS(SELECT 1 FROM public.practice_change_receipts)
        THEN RAISE EXCEPTION 'Practice history exists; refuse destructive downgrade'; END IF; END $$;
        DROP TABLE public.practice_change_receipts;
        ALTER TABLE public.plan_drafts DROP CONSTRAINT plan_drafts_one_proposal,DROP CONSTRAINT plan_drafts_practice_proposal_scope,
            DROP COLUMN practice_change_proposal_id;
        DROP TABLE public.practice_change_proposals; DROP FUNCTION public.protect_practice_proposal();""")
