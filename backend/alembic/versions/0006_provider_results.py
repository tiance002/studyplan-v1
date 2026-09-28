"""Retain structured paid results for safe replay (no redispatch on unknown)."""
from alembic import op

revision = "0006"
down_revision = "0005_catalog_versions"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE ai_provider_attempts ADD COLUMN request_fingerprint text NOT NULL DEFAULT '', ADD COLUMN schema_name text NOT NULL DEFAULT '', ADD COLUMN response_payload jsonb")


def downgrade():
    op.execute("DO $$ BEGIN IF EXISTS (SELECT 1 FROM ai_provider_attempts WHERE request_fingerprint <> '') THEN RAISE EXCEPTION 'Retained paid attempts prevent downgrade'; END IF; END $$")
    op.execute("ALTER TABLE ai_provider_attempts DROP COLUMN response_payload, DROP COLUMN schema_name, DROP COLUMN request_fingerprint")
