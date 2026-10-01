"""Immutable task-position originals, exports and bounded Prompt review claims."""

from alembic import op

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        ALTER TABLE public.plan_task_links ADD CONSTRAINT plan_task_exact_position UNIQUE(project_id,plan_id,stage_id,task_id);
        ALTER TABLE public.prompt_revisions
            ADD COLUMN plan_id text, ADD COLUMN stage_id text,
            ADD COLUMN version integer NOT NULL DEFAULT 0 CHECK(version>=0),
            ADD COLUMN content_hash text, ADD COLUMN task_snapshot jsonb NOT NULL DEFAULT '{}'::jsonb,
            ADD CONSTRAINT prompt_position_optional CHECK((plan_id IS NULL AND stage_id IS NULL AND version=0)
                OR (plan_id IS NOT NULL AND stage_id IS NOT NULL AND version>=1)),
            ADD CONSTRAINT prompt_position_fk FOREIGN KEY(project_id,plan_id,stage_id,task_id)
                REFERENCES public.plan_task_links(project_id,plan_id,stage_id,task_id),
            ADD CONSTRAINT prompt_project_revision UNIQUE(project_id,revision_id),
            ADD CONSTRAINT prompt_position_version UNIQUE(project_id,plan_id,stage_id,task_id,version);
        CREATE TABLE public.prompt_position_heads (
            project_id text NOT NULL,plan_id text NOT NULL,stage_id text NOT NULL,task_id text NOT NULL,
            version integer NOT NULL CHECK(version>=1), PRIMARY KEY(project_id,plan_id,stage_id,task_id),
            FOREIGN KEY(project_id,plan_id,stage_id,task_id) REFERENCES public.plan_task_links(project_id,plan_id,stage_id,task_id));
        CREATE TABLE public.prompt_receipts (
            receipt_id text PRIMARY KEY,project_id text NOT NULL REFERENCES public.learning_projects(project_id),
            actor_id text NOT NULL,idempotency_key text NOT NULL CHECK(length(idempotency_key) BETWEEN 1 AND 128),
            action text NOT NULL CHECK(action IN('save','review','cancel','export')),input_hash text NOT NULL,
            response_snapshot jsonb NOT NULL,created_at timestamptz NOT NULL DEFAULT now(),UNIQUE(project_id,actor_id,idempotency_key));
        CREATE TABLE public.prompt_review_bindings (
            project_id text NOT NULL,revision_id text NOT NULL,run_id text NOT NULL REFERENCES public.ai_runs(run_id),
            actor_id text NOT NULL,manifest jsonb NOT NULL,created_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY(project_id,revision_id),UNIQUE(run_id),
            FOREIGN KEY(project_id,revision_id) REFERENCES public.prompt_revisions(project_id,revision_id));
        CREATE TABLE public.prompt_exports (
            export_id text PRIMARY KEY,project_id text NOT NULL,task_id text NOT NULL,revision_id text NOT NULL,
            revision_no integer NOT NULL,format text NOT NULL CHECK(format IN('raw','implementation')),
            export_text text NOT NULL CHECK(length(export_text) BETWEEN 1 AND 240000),content_hash text NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),UNIQUE(project_id,revision_id,format),
            FOREIGN KEY(project_id,revision_id) REFERENCES public.prompt_revisions(project_id,revision_id),
            FOREIGN KEY(project_id,task_id) REFERENCES public.practice_tasks(project_id,task_id));
        CREATE INDEX prompt_history_order ON public.prompt_revisions(project_id,created_at DESC,revision_id DESC);
    """)
    for table in (
        "prompt_revisions",
        "prompt_reviews",
        "prompt_position_heads",
        "prompt_receipts",
        "prompt_review_bindings",
        "prompt_exports",
    ):
        if table in {"prompt_revisions", "prompt_reviews"}:
            op.execute(f"DROP POLICY {table}_project_scope ON public.{table}")
        actor = (
            " AND actor_id=NULLIF(current_setting('app.actor_id',true),'')"
            if table in {"prompt_receipts", "prompt_review_bindings"}
            else ""
        )
        op.execute(f"""ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY; ALTER TABLE public.{table} FORCE ROW LEVEL SECURITY;
            CREATE POLICY {table}_owner ON public.{table} USING(project_id=NULLIF(current_setting('app.project_id',true),'')
                AND EXISTS(SELECT 1 FROM public.learning_projects p WHERE p.project_id={table}.project_id
                    AND p.owner_actor_id=NULLIF(current_setting('app.actor_id',true),'') AND p.archived_at IS NULL))
            WITH CHECK(project_id=NULLIF(current_setting('app.project_id',true),'') {actor}
                AND EXISTS(SELECT 1 FROM public.learning_projects p WHERE p.project_id={table}.project_id
                    AND p.owner_actor_id=NULLIF(current_setting('app.actor_id',true),'') AND p.archived_at IS NULL));""")
        if table != "prompt_position_heads":
            op.execute(
                f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON public.{table} "
                "FOR EACH ROW EXECUTE FUNCTION public.refuse_exposure_history_mutation()"
            )
    op.execute("""REVOKE UPDATE,DELETE ON public.prompt_revisions,public.prompt_reviews FROM studyplan_app;
        GRANT SELECT,INSERT ON public.prompt_receipts,public.prompt_review_bindings,public.prompt_exports TO studyplan_app;
        GRANT SELECT,INSERT,UPDATE ON public.prompt_position_heads TO studyplan_app;""")
    op.execute(_function(True))


def downgrade():
    op.execute("""DO $$ BEGIN IF EXISTS(SELECT 1 FROM public.prompt_receipts)
        OR EXISTS(SELECT 1 FROM public.prompt_exports) OR EXISTS(SELECT 1 FROM public.prompt_review_bindings)
        OR EXISTS(SELECT 1 FROM public.prompt_revisions WHERE plan_id IS NOT NULL) THEN
        RAISE EXCEPTION 'Prompt history exists; refuse destructive downgrade'; END IF; END $$;""")
    op.execute(_function(False))
    op.execute("""DROP TABLE public.prompt_exports; DROP TABLE public.prompt_review_bindings;
        DROP TABLE public.prompt_receipts; DROP TABLE public.prompt_position_heads;
        DROP TRIGGER prompt_revisions_immutable ON public.prompt_revisions;
        DROP TRIGGER prompt_reviews_immutable ON public.prompt_reviews; DROP INDEX public.prompt_history_order;
        ALTER TABLE public.prompt_revisions DROP CONSTRAINT prompt_position_version,DROP CONSTRAINT prompt_project_revision,
            DROP CONSTRAINT prompt_position_fk,DROP CONSTRAINT prompt_position_optional,
            DROP COLUMN plan_id,DROP COLUMN stage_id,DROP COLUMN version,DROP COLUMN content_hash,DROP COLUMN task_snapshot;
        ALTER TABLE public.plan_task_links DROP CONSTRAINT plan_task_exact_position;""")
    for table in ("prompt_revisions", "prompt_reviews"):
        op.execute(
            f"DROP POLICY {table}_owner ON public.{table}; CREATE POLICY {table}_project_scope ON public.{table} "
            "USING(project_id=current_setting('app.project_id',true)) WITH CHECK(project_id=current_setting('app.project_id',true))"
        )
    op.execute("GRANT UPDATE,DELETE ON public.prompt_revisions,public.prompt_reviews TO studyplan_app")


def _function(include_prompt):
    kinds = (
        "('plan_generate','summary_review','prompt_review')"
        if include_prompt
        else "('plan_generate','summary_review')"
    )
    prompt_guard = (
        """ OR (r.kind='prompt_review' AND r.graph_version='prompt-review-v1' AND EXISTS(
        SELECT 1 FROM public.prompt_review_bindings b WHERE b.run_id=r.run_id
        AND b.project_id=r.project_id AND b.actor_id=r.actor_id))"""
        if include_prompt
        else ""
    )
    summary_guard = f"""AND (r.kind='plan_generate' OR (r.graph_version='summary-review-v1' AND EXISTS(
        SELECT 1 FROM public.summary_review_bindings b WHERE b.run_id=r.run_id
        AND b.project_id=r.project_id AND b.actor_id=r.actor_id)){prompt_guard})"""
    prompt_reconcile_guard = (
        """ OR (r.kind='prompt_review' AND r.graph_version='prompt-review-v1'
        AND EXISTS(SELECT 1 FROM public.prompt_review_bindings b WHERE b.run_id=r.run_id AND b.project_id=r.project_id AND b.actor_id=r.actor_id)
        AND NOT EXISTS(SELECT 1 FROM public.prompt_reviews s WHERE s.run_id=r.run_id))"""
        if include_prompt
        else ""
    )
    reconcile = f"""
        FOR candidate IN
            SELECT j.job_id,r.run_id FROM public.ai_jobs j JOIN public.ai_runs r USING(run_id)
            JOIN public.learning_projects p ON p.project_id=r.project_id
            WHERE ((r.kind='summary_review' AND r.graph_version='summary-review-v1'
                AND EXISTS(SELECT 1 FROM public.summary_review_bindings b WHERE b.run_id=r.run_id AND b.project_id=r.project_id AND b.actor_id=r.actor_id)
                AND NOT EXISTS(SELECT 1 FROM public.summary_reviews s WHERE s.run_id=r.run_id)){prompt_reconcile_guard})
                AND r.status IN('queued','running') AND j.status='running' AND j.lease_expires_at<clock_timestamp()
                AND p.archived_at IS NULL AND p.owner_actor_id=r.actor_id
                AND EXISTS(SELECT 1 FROM public.ai_provider_attempts a WHERE a.run_id=r.run_id
                    AND a.status IN('dispatched','reconciliation_required'))
            ORDER BY j.created_at,j.job_id FOR UPDATE OF j,r,p SKIP LOCKED LIMIT 50
        LOOP
            UPDATE public.ai_runs r SET status='reconciliation_required',next_action='reconcile',
                error_class='attempt_dispatch_unknown',version=r.version+1,updated_at=clock_timestamp()
                WHERE r.run_id=candidate.run_id;
            UPDATE public.ai_jobs j SET status='reconciliation_required',lease_token=NULL,lease_expires_at=NULL
                WHERE j.job_id=candidate.job_id;
        END LOOP;
    """
    return f"""
        CREATE OR REPLACE FUNCTION public.claim_next_planning_job(
            requested_worker text, requested_lease integer, requested_attempts integer
        ) RETURNS TABLE(job_id text, run_id text, project_id text, actor_id text, lease_token text)
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $function$
        DECLARE candidate record; token text;
        BEGIN
            IF requested_worker IS NULL OR length(requested_worker) NOT BETWEEN 1 AND 128 OR btrim(requested_worker)=''
                OR requested_lease IS NULL OR requested_lease NOT BETWEEN 1 AND 3600
                OR requested_attempts IS NULL OR requested_attempts NOT BETWEEN 1 AND 10 THEN
                RAISE EXCEPTION 'Invalid planning claim parameters' USING ERRCODE='22023';
            END IF;
            {reconcile}
            SELECT j.job_id,r.run_id,r.project_id,r.actor_id INTO candidate
            FROM public.ai_jobs j JOIN public.ai_runs r ON r.run_id=j.run_id
            JOIN public.learning_projects p ON p.project_id=r.project_id
            WHERE p.archived_at IS NULL AND p.owner_actor_id=r.actor_id
                AND r.kind IN {kinds} AND r.status IN('queued','running')
                {summary_guard}
                AND (j.status='pending' OR (j.status='running' AND j.lease_expires_at<now()))
                AND j.available_at<=now() AND j.attempts<requested_attempts
                AND NOT EXISTS(SELECT 1 FROM public.ai_provider_attempts a WHERE a.run_id=r.run_id
                    AND a.status IN('dispatched','reconciliation_required'))
            ORDER BY j.created_at,j.job_id FOR UPDATE OF j,r SKIP LOCKED LIMIT 1;
            IF NOT FOUND THEN RETURN; END IF;
            token := pg_catalog.gen_random_uuid()::text;
            UPDATE public.ai_jobs j SET status='running',lease_token=token,
                lease_expires_at=now()+(requested_lease * interval '1 second'),
                worker_id=requested_worker,attempts=j.attempts+1 WHERE j.job_id=candidate.job_id;
            UPDATE public.ai_runs r SET status='running',next_action='wait',version=r.version+1,updated_at=now()
                WHERE r.run_id=candidate.run_id;
            RETURN QUERY SELECT candidate.job_id::text,candidate.run_id::text,candidate.project_id::text,candidate.actor_id::text,token;
        END $function$;
        REVOKE ALL ON FUNCTION public.claim_next_planning_job(text,integer,integer) FROM PUBLIC;
        GRANT EXECUTE ON FUNCTION public.claim_next_planning_job(text,integer,integer) TO studyplan_app;
    """
