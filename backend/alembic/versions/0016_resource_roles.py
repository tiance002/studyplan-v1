"""Constrain stage resource roles to the six explicit product semantics."""
from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""ALTER TABLE public.stage_resource_assignments
        ADD CONSTRAINT stage_resource_assignments_role_check
        CHECK (role IN ('primary', 'supplement', 'comparison', 'reference', 'case_study', 'practice'))""")


def downgrade():
    # 0015 had an unconstrained text column. Removing this check preserves all
    # stored role values, including the three additional roles.
    op.execute("ALTER TABLE public.stage_resource_assignments DROP CONSTRAINT stage_resource_assignments_role_check")
