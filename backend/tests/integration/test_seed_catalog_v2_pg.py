import os
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import psycopg
import pytest
from app.infrastructure.db.domain_pack_catalog import DomainPackUnavailableError, PgDomainPackCatalog
from app.infrastructure.domain_pack import load_pack
from app.tools.seed_b3 import seed_reviewed_pack

from tests.pg_harness import create_test_database

pytestmark = pytest.mark.postgres


@pytest.fixture(scope='module')
def db():
    # Force shared-instance safety; no global role creation/change is authorized.
    os.environ.pop('STUDYPLAN_TEST_PG_DEDICATED', None)
    database = create_test_database(prefix='studyplan_test_v2seed')
    try:
        result = subprocess.run([sys.executable, '-m', 'alembic', 'upgrade', 'head'],
                                cwd=Path(__file__).resolve().parents[2],
                                env=dict(os.environ, STUDYPLAN_MIGRATION_DSN=database.migrator_dsn),
                                capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        yield database
    finally:
        database.drop()


def test_catalog_missing_and_unknown_scope(db):
    catalog = PgDomainPackCatalog(db.app_dsn)
    with pytest.raises(DomainPackUnavailableError):
        catalog.select('Agent development')
    assert catalog.select('botany')['resource_support'] == 'search_only'


def test_publication_idempotency_conflict_atomic_and_version_snapshot(db):
    pack = load_pack('agent-application-v2.json')
    with psycopg.connect(db.migrator_dsn) as conn:
        seed_reviewed_pack(conn, pack)
        seed_reviewed_pack(conn, pack)
        before = conn.execute('SELECT count(*) FROM public_resource_sources').fetchone()[0]
        conflicting = deepcopy(pack)
        conflicting['title'] = 'Changed same version'
        with pytest.raises(ValueError):
            seed_reviewed_pack(conn, conflicting)
        newer = deepcopy(pack)
        newer['version'] = 3
        # A new pack row inserted before resource conflict must also roll back.
        newer['resources'][-1]['title'] = 'Changed same source'
        with pytest.raises(ValueError):
            seed_reviewed_pack(conn, newer)
        assert conn.execute('SELECT count(*) FROM domain_packs').fetchone()[0] == 1
        assert conn.execute('SELECT count(*) FROM public_resource_sources').fetchone()[0] == before
    catalog = PgDomainPackCatalog(db.app_dsn)
    assert catalog.select('Agent') == pack
    newer = deepcopy(pack)
    newer['version'] = 3
    newer['title'] = 'New immutable version'
    with psycopg.connect(db.migrator_dsn) as conn:
        seed_reviewed_pack(conn, newer)
        assert conn.execute('SELECT published_payload FROM domain_packs WHERE version=2').fetchone()[0] == pack
    assert catalog.select('Agent') == newer


def test_app_cannot_write_seed(db):
    with psycopg.connect(db.app_dsn) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("UPDATE domain_packs SET published_payload='{}'")


def test_controlled_cli_has_no_project_or_checkpoint_side_effect(db):
    backend = Path(__file__).resolve().parents[2]
    result = subprocess.run([sys.executable, '-m', 'app.tools.import_seed', '--file',
                             str(backend / 'app/infrastructure/content/python-engineering-v1.json')],
                            cwd=backend, env=dict(os.environ, STUDYPLAN_MIGRATION_DSN=db.migrator_dsn),
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    with psycopg.connect(db.migrator_dsn) as conn:
        assert conn.execute('SELECT count(*) FROM learning_projects').fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM information_schema.tables WHERE table_name='checkpoints'").fetchone()[0] == 0
    assert PgDomainPackCatalog(db.app_dsn).select('Python')['pack_key'] == 'python.engineering'


def test_legacy_row_requires_explicit_import_and_payload_is_not_file_fallback(db):
    with psycopg.connect(db.migrator_dsn) as conn:
        conn.execute("UPDATE domain_packs SET published_payload=NULL WHERE pack_key='python.engineering'")
    with pytest.raises(DomainPackUnavailableError):
        PgDomainPackCatalog(db.app_dsn).select('Python')
    with psycopg.connect(db.migrator_dsn) as conn:
        seed_reviewed_pack(conn, load_pack('python-engineering-v1.json'))
    assert PgDomainPackCatalog(db.app_dsn).select('Python')['version'] == 1


def test_invalid_payload_is_rejected_before_any_sql():
    class NoDatabase:
        def transaction(self):
            pytest.fail('Validation must precede DB transaction')
    invalid = load_pack('agent-application-v2.json')
    invalid['resources'][-1]['sections'][-1]['url'] = 'http://localhost/internal'
    with pytest.raises(ValueError):
        seed_reviewed_pack(NoDatabase(), invalid)
