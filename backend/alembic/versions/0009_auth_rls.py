"""Deny-by-default RLS for the global authentication boundary."""

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade():
    predicates = {
        "auth_users": "actor_id=NULLIF(current_setting('app.actor_id',true),'') OR username_key=NULLIF(current_setting('app.auth_username',true),'')",
        "auth_sessions": "actor_id=NULLIF(current_setting('app.actor_id',true),'') OR token_hash=NULLIF(current_setting('app.auth_token_hash',true),'')",
        "auth_throttle": "bucket=NULLIF(current_setting('app.auth_bucket',true),'')",
    }
    for table, predicate in predicates.items():
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY authentication_scope ON {table} USING ({predicate}) WITH CHECK ({predicate})"
        )


def downgrade():
    op.execute("""DO $$ BEGIN IF EXISTS(SELECT 1 FROM auth_users)
        THEN RAISE EXCEPTION 'User data prevents removal of authentication isolation'; END IF; END $$;""")
    for table in ("auth_users", "auth_sessions", "auth_throttle"):
        op.execute(f"DROP POLICY authentication_scope ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
