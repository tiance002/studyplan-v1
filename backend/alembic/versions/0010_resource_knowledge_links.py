"""Add reviewed-index metadata and private resource/knowledge binding; preserve old snapshots."""

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE domain_packs ADD COLUMN content_digest text NOT NULL DEFAULT ''")
    op.execute("ALTER TABLE public_resource_sources ADD COLUMN documentation_version text NOT NULL DEFAULT ''")
    for table in ("public_resource_sources", "public_resource_sections"):
        op.execute(f"ALTER TABLE {table} ADD COLUMN verification_status text NOT NULL DEFAULT 'legacy_index' CHECK (verification_status IN ('reviewed','legacy_index','unverified'))")
    op.execute("ALTER TABLE public_resource_sections ADD COLUMN review_note text NOT NULL DEFAULT ''")
    op.execute("ALTER TABLE stage_resource_assignments ADD COLUMN node_ids jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(node_ids)='array')")
    # Security-invoker checks run under existing project RLS. A reference must
    # belong to a unit of the same published stage, rather than merely exist.
    op.execute("""
        CREATE FUNCTION enforce_resource_node_scope() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE node_ref text;
        BEGIN
          FOR node_ref IN SELECT jsonb_array_elements_text(NEW.node_ids) LOOP
            IF NOT EXISTS (
              SELECT 1 FROM plan_unit_links p JOIN unit_node_links u
                ON u.project_id=p.project_id AND u.unit_id=p.unit_id
              WHERE p.project_id=NEW.project_id AND p.plan_id=NEW.plan_id
                AND p.stage_id=NEW.stage_id AND u.node_id=node_ref
            ) THEN
              RAISE EXCEPTION 'Resource node is outside published stage' USING ERRCODE='23514';
            END IF;
          END LOOP;
          RETURN NEW;
        END $$;
        CREATE TRIGGER resource_node_scope BEFORE INSERT OR UPDATE OF node_ids,project_id,plan_id,stage_id
          ON stage_resource_assignments FOR EACH ROW EXECUTE FUNCTION enforce_resource_node_scope();
    """)


def downgrade():
    op.execute("""DO $$ BEGIN
      IF EXISTS(SELECT 1 FROM stage_resource_assignments WHERE node_ids <> '[]'::jsonb)
        OR EXISTS(SELECT 1 FROM public_resource_sources WHERE verification_status <> 'legacy_index')
      THEN RAISE EXCEPTION 'Reviewed resource data prevents downgrade'; END IF;
    END $$;""")
    op.execute("DROP TRIGGER resource_node_scope ON stage_resource_assignments")
    op.execute("DROP FUNCTION enforce_resource_node_scope()")
    op.execute("ALTER TABLE stage_resource_assignments DROP COLUMN node_ids")
    op.execute("ALTER TABLE public_resource_sections DROP COLUMN review_note")
    for table in ("public_resource_sections", "public_resource_sources"):
        op.execute(f"ALTER TABLE {table} DROP COLUMN verification_status")
    op.execute("ALTER TABLE public_resource_sources DROP COLUMN documentation_version")
    op.execute("ALTER TABLE domain_packs DROP COLUMN content_digest")
