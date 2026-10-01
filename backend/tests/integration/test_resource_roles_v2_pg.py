"""Six-role CHECK and complete public catalogs on a harness-owned database."""
import psycopg
import pytest
from app.infrastructure.db.public_resource_catalog import PgPublicResourceCatalog
from app.infrastructure.domain_pack import load_pack
from app.tools.seed_b3 import seed_reviewed_pack

from tests.integration.test_seed_catalog_v2_pg import db as db

pytestmark = pytest.mark.postgres


def test_six_roles_are_persistable_and_unknown_role_rejected(db):
    with psycopg.connect(db.migrator_dsn) as conn:
        # LIKE copies the real CHECK while leaving foreign keys out of this
        # temporary probe; no project or original assignment is changed.
        conn.execute("CREATE TEMP TABLE role_probe (LIKE public.stage_resource_assignments INCLUDING CONSTRAINTS INCLUDING DEFAULTS)")
        for role in ("primary", "supplement", "comparison", "reference", "case_study", "practice"):
            conn.execute("INSERT INTO role_probe (assignment_id,project_id,stage_id,role) VALUES (%s,'p','s',%s)",
                (role, role))
        assert conn.execute("SELECT count(*) FROM role_probe").fetchone()[0] == 6
        with pytest.raises(psycopg.errors.CheckViolation):
            with conn.transaction():
                conn.execute("INSERT INTO role_probe (assignment_id,project_id,stage_id,role) VALUES ('bad','p','s','invented')")


def test_full_source_catalog_includes_unselected_chapters_read_only(db):
    pack = load_pack("python-engineering-v1.json")
    with psycopg.connect(db.migrator_dsn) as conn:
        seed_reviewed_pack(conn, pack)
    source = max(pack["resources"], key=lambda row: len(row["sections"]))
    assert len(source["sections"]) >= 3
    catalog = PgPublicResourceCatalog(db.app_dsn)
    selected = catalog.load_sections(section_ids=[source["sections"][0]["section_id"]])
    complete = catalog.load_source_sections(source_ids=[source["source_id"]])
    assert len(selected) == 1
    assert set(complete) == {section["section_id"] for section in source["sections"]}
    assert catalog.load_source_sections(source_ids=[]) == {}
    assert catalog.load_source_sections(source_ids=["missing"]) == {}
