"""Reuse narrow server-only queue claim for frozen single-call summary reviews."""
from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def _function(include_summary):
    kinds = "('plan_generate','summary_review')" if include_summary else "('plan_generate')"
    summary_guard = """AND (r.kind='plan_generate' OR (r.graph_version='summary-review-v1' AND EXISTS(
        SELECT 1 FROM public.summary_review_bindings b WHERE b.run_id=r.run_id
        AND b.project_id=r.project_id AND b.actor_id=r.actor_id)))""" if include_summary else ""
    reconcile = """
        FOR candidate IN
            SELECT j.job_id,r.run_id FROM public.ai_jobs j JOIN public.ai_runs r USING(run_id)
            JOIN public.learning_projects p ON p.project_id=r.project_id
            JOIN public.summary_review_bindings b ON b.run_id=r.run_id AND b.project_id=r.project_id AND b.actor_id=r.actor_id
            WHERE r.kind='summary_review' AND r.graph_version='summary-review-v1'
                AND r.status IN('queued','running') AND j.status='running' AND j.lease_expires_at<clock_timestamp()
                AND p.archived_at IS NULL AND p.owner_actor_id=r.actor_id
                AND EXISTS(SELECT 1 FROM public.ai_provider_attempts a WHERE a.run_id=r.run_id
                    AND a.status IN('dispatched','reconciliation_required'))
                AND NOT EXISTS(SELECT 1 FROM public.summary_reviews s WHERE s.run_id=r.run_id)
            ORDER BY j.created_at,j.job_id FOR UPDATE OF j,r,p SKIP LOCKED LIMIT 50
        LOOP
            UPDATE public.ai_runs r SET status='reconciliation_required',next_action='reconcile',
                error_class='attempt_dispatch_unknown',version=r.version+1,updated_at=clock_timestamp()
                WHERE r.run_id=candidate.run_id;
            UPDATE public.ai_jobs j SET status='reconciliation_required',lease_token=NULL,lease_expires_at=NULL
                WHERE j.job_id=candidate.job_id;
        END LOOP;
    """ if include_summary else ""
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


def upgrade():
    op.execute(_function(True))


def downgrade():
    # Do not strand new reviews behind an old worker protocol.
    op.execute("""DO $$ BEGIN IF EXISTS(SELECT 1 FROM public.summary_review_bindings) THEN
        RAISE EXCEPTION 'Summary review runs exist; refuse protocol downgrade'; END IF; END $$;""")
    op.execute(_function(False))
