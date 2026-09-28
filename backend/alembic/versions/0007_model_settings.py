"""Actor-private encrypted model revisions and run selection binding."""
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE user_model_setting_versions (
        actor_id text NOT NULL, version integer NOT NULL CHECK(version>0),
        base_url text NOT NULL, model_id text NOT NULL, protocol text NOT NULL,
        encrypted_api_key text, created_at timestamptz NOT NULL DEFAULT now(),
        PRIMARY KEY(actor_id,version));
        CREATE TABLE user_model_settings (
        actor_id text PRIMARY KEY, version integer NOT NULL,
        FOREIGN KEY(actor_id,version) REFERENCES user_model_setting_versions(actor_id,version));
        CREATE TABLE ai_run_model_settings (
        run_id text PRIMARY KEY REFERENCES ai_runs(run_id),
        actor_id text NOT NULL, settings_version integer NOT NULL,
        FOREIGN KEY(actor_id,settings_version) REFERENCES user_model_setting_versions(actor_id,version));""")
    for table in ("user_model_setting_versions", "user_model_settings", "ai_run_model_settings"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        predicate = "actor_id = NULLIF(current_setting('app.actor_id',true),'')"
        if table == "ai_run_model_settings":
            predicate += " AND EXISTS (SELECT 1 FROM ai_runs r WHERE r.run_id=ai_run_model_settings.run_id AND r.actor_id=ai_run_model_settings.actor_id)"
        op.execute(f"CREATE POLICY actor_private ON {table} USING ({predicate}) WITH CHECK ({predicate})")
        op.execute(f"GRANT SELECT,INSERT,UPDATE,DELETE ON {table} TO studyplan_app")


def downgrade():
    op.execute("""DO $$ BEGIN IF EXISTS(SELECT 1 FROM user_model_setting_versions)
        THEN RAISE EXCEPTION 'Personal model history prevents downgrade'; END IF; END $$""")
    op.execute("DROP TABLE ai_run_model_settings, user_model_settings, user_model_setting_versions")
