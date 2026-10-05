"""Frozen coaching conversations, exact originals and one reply binding per turn."""
from alembic import op

revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None


def claim_function():
    # Load the previous immutable claim definition by path, not a DB introspection rewrite.
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location("prior_prompt_migration", Path(__file__).with_name("0020_prompt_positions.py"))
    prior = importlib.util.module_from_spec(spec); spec.loader.exec_module(prior)
    sql = prior._function(True)
    guard = """r.kind='assistant_reply' AND r.graph_version='assistant-coaching-v1' AND EXISTS(
        SELECT 1 FROM public.assistant_turns b WHERE b.run_id=r.run_id
        AND b.project_id=r.project_id AND b.actor_id=r.actor_id)"""
    sql = sql.replace("('plan_generate','summary_review','prompt_review')", "('plan_generate','summary_review','prompt_review','assistant_reply')")
    sql = sql.replace("AND (r.kind='plan_generate' OR", "AND (("+guard+") OR r.kind='plan_generate' OR")
    sql = sql.replace("WHERE ((r.kind='summary_review'", "WHERE (("+guard+" AND NOT EXISTS(SELECT 1 FROM public.assistant_messages m WHERE m.run_id=r.run_id AND m.role='assistant')) OR (r.kind='summary_review'")
    return sql


def upgrade():
    op.execute("""
    CREATE TABLE public.assistant_conversations (
        conversation_id text PRIMARY KEY, project_id text NOT NULL, actor_id text NOT NULL,
        plan_id text NOT NULL, plan_revision integer NOT NULL CHECK(plan_revision>0),
        stage_id text NOT NULL, task_id text, mode text NOT NULL CHECK(mode IN('summary','practice')),
        title text NOT NULL, context jsonb NOT NULL, context_hash text NOT NULL,
        current_draft_message_id text, created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
        UNIQUE(project_id,conversation_id),
        CHECK((mode='summary' AND task_id IS NULL) OR (mode='practice' AND task_id IS NOT NULL)),
        FOREIGN KEY(project_id,plan_id,stage_id) REFERENCES public.plan_stages(project_id,plan_id,stage_id),
        FOREIGN KEY(project_id,plan_id,stage_id,task_id) REFERENCES public.plan_task_links(project_id,plan_id,stage_id,task_id)
    );
    CREATE TABLE public.assistant_messages (
        message_id text PRIMARY KEY, project_id text NOT NULL, conversation_id text NOT NULL,
        sequence integer NOT NULL CHECK(sequence>0), role text NOT NULL CHECK(role IN('user','assistant')),
        intent text NOT NULL CHECK(intent IN('work_draft','question','reply')), content text NOT NULL CHECK(length(content)>0),
        run_id text REFERENCES public.ai_runs(run_id), draft_message_id text, trigger_message_id text, delivery_error text,
        created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
        UNIQUE(project_id,conversation_id,message_id), UNIQUE(conversation_id,sequence), UNIQUE(run_id,role),
        FOREIGN KEY(project_id,conversation_id) REFERENCES public.assistant_conversations(project_id,conversation_id),
        FOREIGN KEY(project_id,conversation_id,draft_message_id) REFERENCES public.assistant_messages(project_id,conversation_id,message_id),
        FOREIGN KEY(project_id,conversation_id,trigger_message_id) REFERENCES public.assistant_messages(project_id,conversation_id,message_id),
        CHECK((role='user' AND intent IN('work_draft','question') AND trigger_message_id IS NULL)
           OR (role='assistant' AND intent='reply' AND trigger_message_id IS NOT NULL))
    );
    ALTER TABLE public.assistant_conversations ADD CONSTRAINT assistant_current_draft_fk
        FOREIGN KEY(project_id,conversation_id,current_draft_message_id) REFERENCES public.assistant_messages(project_id,conversation_id,message_id);
    CREATE TABLE public.assistant_turns (
        run_id text PRIMARY KEY REFERENCES public.ai_runs(run_id), project_id text NOT NULL, actor_id text NOT NULL,
        conversation_id text NOT NULL, trigger_message_id text NOT NULL, draft_message_id text,
        context_hash text NOT NULL, manifest jsonb NOT NULL, payload jsonb NOT NULL, payload_hash text NOT NULL,
        FOREIGN KEY(project_id,conversation_id,trigger_message_id) REFERENCES public.assistant_messages(project_id,conversation_id,message_id),
        FOREIGN KEY(project_id,conversation_id,draft_message_id) REFERENCES public.assistant_messages(project_id,conversation_id,message_id)
    );
    CREATE TABLE public.assistant_receipts (
        receipt_id text PRIMARY KEY, project_id text NOT NULL REFERENCES public.learning_projects(project_id),
        actor_id text NOT NULL, idempotency_key text NOT NULL CHECK(length(idempotency_key) BETWEEN 1 AND 128),
        action text NOT NULL, input_hash text NOT NULL, response_snapshot jsonb NOT NULL,
        UNIQUE(project_id,actor_id,idempotency_key)
    );
    CREATE TABLE public.assistant_formal_saves (
        save_id text PRIMARY KEY, project_id text NOT NULL, actor_id text NOT NULL, conversation_id text NOT NULL,
        draft_message_id text NOT NULL, content text NOT NULL, expected_version integer NOT NULL CHECK(expected_version>=0),
        idempotency_key text NOT NULL, input_hash text NOT NULL, artifact_type text NOT NULL CHECK(artifact_type IN('summary','prompt')),
        artifact_id text, formal_version integer, status text NOT NULL CHECK(status IN('pending','succeeded','failed')),
        created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
        UNIQUE(project_id,actor_id,idempotency_key),
        FOREIGN KEY(project_id,conversation_id,draft_message_id) REFERENCES public.assistant_messages(project_id,conversation_id,message_id)
    );
    CREATE INDEX assistant_history_order ON public.assistant_conversations(project_id,actor_id,created_at DESC,conversation_id DESC);
    """)
    for table in ('assistant_conversations','assistant_messages','assistant_turns','assistant_receipts','assistant_formal_saves'):
        op.execute(f"""ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY;
            ALTER TABLE public.{table} FORCE ROW LEVEL SECURITY;
            CREATE POLICY {table}_owner ON public.{table}
            USING(project_id=NULLIF(current_setting('app.project_id',true),'') AND actor_owner_placeholder)
            WITH CHECK(project_id=NULLIF(current_setting('app.project_id',true),'') AND actor_owner_placeholder);
        """.replace('actor_owner_placeholder', f"EXISTS(SELECT 1 FROM public.learning_projects p WHERE p.project_id={table}.project_id AND p.owner_actor_id=NULLIF(current_setting('app.actor_id',true),'') AND p.archived_at IS NULL)"))
        if table != 'assistant_messages':
            op.execute(f"DROP POLICY {table}_owner ON public.{table}; CREATE POLICY {table}_owner ON public.{table} USING(project_id=NULLIF(current_setting('app.project_id',true),'') AND actor_id=NULLIF(current_setting('app.actor_id',true),'') AND EXISTS(SELECT 1 FROM public.learning_projects p WHERE p.project_id={table}.project_id AND p.owner_actor_id=NULLIF(current_setting('app.actor_id',true),'') AND p.archived_at IS NULL)) WITH CHECK(project_id=NULLIF(current_setting('app.project_id',true),'') AND actor_id=NULLIF(current_setting('app.actor_id',true),'') AND EXISTS(SELECT 1 FROM public.learning_projects p WHERE p.project_id={table}.project_id AND p.owner_actor_id=NULLIF(current_setting('app.actor_id',true),'') AND p.archived_at IS NULL))")
        op.execute(f"GRANT SELECT,INSERT ON public.{table} TO studyplan_app")
        if table in ('assistant_messages','assistant_turns','assistant_receipts'):
            op.execute(f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON public.{table} FOR EACH ROW EXECUTE FUNCTION public.refuse_exposure_history_mutation()")
    op.execute("GRANT UPDATE(current_draft_message_id) ON public.assistant_conversations TO studyplan_app; GRANT UPDATE(artifact_id,formal_version,status) ON public.assistant_formal_saves TO studyplan_app")
    op.execute(claim_function())


def downgrade():
    op.execute("""DO $$ BEGIN IF EXISTS(SELECT 1 FROM public.assistant_conversations) OR EXISTS(SELECT 1 FROM public.assistant_receipts) THEN RAISE EXCEPTION 'Assistant history exists; refuse destructive downgrade'; END IF; END $$;""")
    import importlib.util
    from pathlib import Path
    spec=importlib.util.spec_from_file_location('prior_prompt_migration',Path(__file__).with_name('0020_prompt_positions.py'))
    prior=importlib.util.module_from_spec(spec); spec.loader.exec_module(prior)
    op.execute(prior._function(True))
    op.execute("""ALTER TABLE public.assistant_conversations DROP CONSTRAINT assistant_current_draft_fk;
        DROP TABLE public.assistant_formal_saves,public.assistant_receipts,public.assistant_turns,public.assistant_messages,public.assistant_conversations;""")
