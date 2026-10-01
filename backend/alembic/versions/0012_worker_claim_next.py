"""Narrow trusted-server queue admission without per-user worker configuration."""

from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade():
    # Created/owned by the migration connection role. The existing application
    # role gets only EXECUTE; no database-role attributes are changed.
    op.execute("""
        CREATE FUNCTION public.claim_next_planning_job(
            requested_worker text, requested_lease integer, requested_attempts integer
        ) RETURNS TABLE(job_id text, run_id text, project_id text, actor_id text, lease_token text)
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog
        AS $function$
        DECLARE
            candidate record;
            token text;
        BEGIN
            IF requested_worker IS NULL OR length(requested_worker) NOT BETWEEN 1 AND 128 OR btrim(requested_worker)=''
                OR requested_lease IS NULL OR requested_lease NOT BETWEEN 1 AND 3600
                OR requested_attempts IS NULL OR requested_attempts NOT BETWEEN 1 AND 10 THEN
                RAISE EXCEPTION 'Invalid planning claim parameters' USING ERRCODE = '22023';
            END IF;
            SELECT j.job_id, r.run_id, r.project_id, r.actor_id INTO candidate
            FROM public.ai_jobs j JOIN public.ai_runs r ON r.run_id=j.run_id
            JOIN public.learning_projects p ON p.project_id=r.project_id
            WHERE p.archived_at IS NULL AND p.owner_actor_id=r.actor_id
                AND r.kind='plan_generate' AND r.status IN ('queued','running')
                AND (j.status='pending' OR (j.status='running' AND j.lease_expires_at < now()))
                AND j.available_at <= now() AND j.attempts < requested_attempts
                AND NOT EXISTS (SELECT 1 FROM public.ai_provider_attempts a
                    WHERE a.run_id=r.run_id AND a.status IN ('dispatched','reconciliation_required'))
            ORDER BY j.created_at,j.job_id
            FOR UPDATE OF j,r SKIP LOCKED LIMIT 1;
            IF NOT FOUND THEN RETURN; END IF;
            token := pg_catalog.gen_random_uuid()::text;
            UPDATE public.ai_jobs j SET status='running',lease_token=token,
                lease_expires_at=now()+(requested_lease * interval '1 second'),
                worker_id=requested_worker,attempts=j.attempts+1
            WHERE j.job_id=candidate.job_id;
            UPDATE public.ai_runs r SET status='running',next_action='wait',
                version=r.version+1,updated_at=now()
            WHERE r.run_id=candidate.run_id;
            RETURN QUERY SELECT candidate.job_id::text,candidate.run_id::text,
                candidate.project_id::text,candidate.actor_id::text,token;
        END
        $function$;
        REVOKE ALL ON FUNCTION public.claim_next_planning_job(text,integer,integer) FROM PUBLIC;
        GRANT EXECUTE ON FUNCTION public.claim_next_planning_job(text,integer,integer) TO studyplan_app;
    """)


def downgrade():
    op.execute("DROP FUNCTION public.claim_next_planning_job(text,integer,integer)")
