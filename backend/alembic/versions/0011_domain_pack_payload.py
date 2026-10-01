"""Persist immutable complete published Seed; legacy rows require explicit import."""
from alembic import op

revision = '0011'
down_revision = '0010'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE public.domain_packs ADD COLUMN published_payload jsonb CHECK (published_payload IS NULL OR jsonb_typeof(published_payload) = 'object')")


def downgrade():
    op.execute("""DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM public.domain_packs WHERE published_payload IS NOT NULL) THEN
            RAISE EXCEPTION 'Published Seed payload exists; refuse data-losing downgrade';
        END IF;
    END $$""")
    op.execute('ALTER TABLE public.domain_packs DROP COLUMN published_payload')
