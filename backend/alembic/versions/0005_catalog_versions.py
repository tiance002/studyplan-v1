"""Immutable catalog content versions; preserve every existing ID and FK."""
from alembic import op

revision = "0005_catalog_versions"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE knowledge_nodes DROP CONSTRAINT knowledge_nodes_stable_key_unique")
    op.execute("ALTER TABLE learning_units DROP CONSTRAINT learning_units_stable_key_unique")
    op.execute("CREATE INDEX knowledge_nodes_key_versions ON knowledge_nodes(project_id, stable_key)")
    op.execute("CREATE INDEX learning_units_key_versions ON learning_units(project_id, stable_key)")


def downgrade():
    # Duplicate logical keys mean versioned data exists; adding UNIQUE safely refuses.
    op.execute("ALTER TABLE knowledge_nodes ADD CONSTRAINT knowledge_nodes_stable_key_unique UNIQUE(project_id, stable_key)")
    op.execute("ALTER TABLE learning_units ADD CONSTRAINT learning_units_stable_key_unique UNIQUE(project_id, stable_key)")
    op.execute("DROP INDEX knowledge_nodes_key_versions")
    op.execute("DROP INDEX learning_units_key_versions")

