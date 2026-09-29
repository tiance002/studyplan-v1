"""Persistent browser credentials, opaque sessions and login throttling."""

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE auth_users (
        actor_id text PRIMARY KEY, username text NOT NULL, username_key text UNIQUE NOT NULL,
        password_hash text NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
        CREATE TABLE auth_sessions (
        token_hash text PRIMARY KEY, actor_id text NOT NULL REFERENCES auth_users(actor_id),
        session_id text NOT NULL UNIQUE, csrf_token text NOT NULL,
        issued_at timestamptz NOT NULL DEFAULT now(), expires_at timestamptz NOT NULL);
        CREATE INDEX auth_sessions_expiry ON auth_sessions(expires_at);
        CREATE TABLE auth_throttle (
        bucket text PRIMARY KEY, attempts integer NOT NULL, window_start timestamptz NOT NULL DEFAULT now());
        GRANT SELECT,INSERT,UPDATE,DELETE ON auth_users,auth_sessions,auth_throttle TO studyplan_app;
    """)


def downgrade():
    op.execute("""DO $$ BEGIN IF EXISTS(SELECT 1 FROM auth_users)
        THEN RAISE EXCEPTION 'User data prevents downgrade'; END IF; END $$;
        DROP TABLE auth_sessions,auth_users,auth_throttle;""")
