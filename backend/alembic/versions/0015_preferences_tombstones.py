"""Retain deleted preference slots and their monotonic versions for safe CAS."""

from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE public.preferences ADD COLUMN deleted_at timestamptz")


def downgrade():
    # A restored active slot can have deleted_at=NULL but a higher retained
    # version. Conservatively refuse removal when that history could exist.
    op.execute("""DO $$ BEGIN
        IF EXISTS(SELECT 1 FROM public.preferences WHERE deleted_at IS NOT NULL OR version>1) THEN
            RAISE EXCEPTION 'Preference tombstone/version history prevents downgrade';
        END IF;
    END $$""")
    op.execute("ALTER TABLE public.preferences DROP COLUMN deleted_at")
