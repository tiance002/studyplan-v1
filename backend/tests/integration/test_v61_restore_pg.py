"""P8: native custom dump/restore between two owned test DBs, no global roles.

An already-running PG16 container supplies client executables only. They connect
to the verified host cluster, never to the helper container's own database.
"""
import hashlib
import json
import os
import shutil
import subprocess
from dataclasses import replace
from pathlib import Path
from urllib.parse import unquote, urlsplit

import psycopg
import pytest
from app.composition import build_container
from app.core.config import get_settings
from app.core.ids import new_id
from app.infrastructure.domain_pack import CURRENT_PACKS, load_pack
from app.main import create_app
from app.tools.seed_b3 import seed_reviewed_pack
from fastapi.testclient import TestClient
from psycopg import sql

from tests.e2e.test_b2v_http_end_to_end import _run_alembic
from tests.integration.test_current_learning_loop_pg import ok
from tests.pg_harness import (
    ADMIN_HOST,
    ADMIN_PASSWORD,
    ADMIN_PORT,
    ADMIN_USER,
    admin_connect,
    create_test_database,
    instance_is_dedicated,
    roles_created_by_harness,
)

pytestmark = pytest.mark.postgres
ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / 'var/current-learning-loop'
TOOL_CONTAINER = 'raglocalfirst0930-db-1'


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def database_snapshot(db):
    """All public rows + ACL/RLS/policies, independent of regenerated object OIDs."""
    with psycopg.connect(db.migrator_dsn) as conn:
        conn.execute("SET TIME ZONE 'UTC'")
        tables = conn.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename").fetchall()
        rows = {}
        for (table,) in tables:
            values = conn.execute(sql.SQL('SELECT to_jsonb(t)::text FROM public.{} AS t ORDER BY to_jsonb(t)::text').format(sql.Identifier(table))).fetchall()
            rows[table] = {'count': len(values), 'sha256': digest(values)}
        acl = conn.execute("""SELECT c.relname,r.rolname,c.relrowsecurity,c.relforcerowsecurity,
            ARRAY(SELECT a::text FROM unnest(c.relacl) a ORDER BY a::text)
            FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace JOIN pg_roles r ON r.oid=c.relowner
            WHERE n.nspname='public' AND c.relkind IN ('r','S','v','m') ORDER BY c.relname""").fetchall()
        policies = conn.execute("SELECT schemaname,tablename,policyname,permissive,roles::text,cmd,qual,with_check FROM pg_policies WHERE schemaname='public' ORDER BY tablename,policyname").fetchall()
        schema_acl = conn.execute("SELECT nspname,pg_get_userbyid(nspowner),ARRAY(SELECT a::text FROM unnest(nspacl) a ORDER BY a::text) FROM pg_namespace WHERE nspname='public'").fetchall()
        return {'tables': rows, 'acl_rls_sha256': digest(acl), 'policies_sha256': digest(policies), 'schema_acl_sha256': digest(schema_acl)}


def role_state():
    with admin_connect('postgres') as conn:
        return conn.execute("SELECT rolname,rolcanlogin,rolsuper,rolcreatedb,rolcreaterole,rolbypassrls FROM pg_roles WHERE rolname IN ('studyplan_app','studyplan_migrator') ORDER BY rolname").fetchall()


def test_native_custom_restore_preserves_extensions_originals_acl_and_no_dispatch():
    if os.environ.get('STUDYPLAN_V61_RESTORE_NATIVE') != '1':
        pytest.skip('owned native restore acceptance enabled explicitly')
    # Refuse harness modes that could create/alter global roles.
    assert not instance_is_dedicated()
    assert not roles_created_by_harness()
    assert len(role_state()) == 2
    assert ADMIN_HOST == '127.0.0.1' and ADMIN_PORT == 5432
    assert shutil.which('docker'), 'NOT RUN: no native clients or callable docker tool helper'
    before_roles = role_state()
    inspected = subprocess.run(['docker', 'inspect', TOOL_CONTAINER, '--format', '{{json .State.Running}}|{{.Id}}|{{.Config.Image}}|{{json .NetworkSettings.Ports}}'], capture_output=True, text=True, timeout=15)
    assert inspected.returncode == 0, 'NOT RUN: verified running PG client container unavailable'
    running, container_id, image, ports_json = inspected.stdout.strip().split('|', 3)
    assert running == 'true' and image == 'pgvector/pgvector:pg16'
    ports = json.loads(ports_json)
    assert {'HostIp': '127.0.0.1', 'HostPort': '25438'} in ports['5432/tcp']
    # A different mapped port is deliberate: this helper supplies binaries only.
    native_prefix = ['docker', 'exec', '-e', 'PGPASSWORD', container_id]
    with admin_connect('postgres') as conn:
        cluster_id = conn.execute('SELECT system_identifier::text FROM pg_control_system()').fetchone()[0]
        server_version = conn.execute('SHOW server_version').fetchone()[0]
    fingerprint = subprocess.run([*native_prefix, 'psql', '-X', '-A', '-t', '--host', 'host.docker.internal', '--port', str(ADMIN_PORT),
        '--username', ADMIN_USER, '--dbname', 'postgres', '--command', 'SELECT system_identifier::text FROM pg_control_system()'],
        env=dict(os.environ, PGPASSWORD=ADMIN_PASSWORD), capture_output=True, text=True, timeout=15)
    assert fingerprint.returncode == 0 and fingerprint.stdout.strip() == cluster_id
    versions = {}
    for tool in ('pg_dump', 'pg_restore'):
        result = subprocess.run(['docker', 'exec', container_id, tool, '--version'], capture_output=True, text=True, timeout=15)
        assert result.returncode == 0
        versions[tool] = result.stdout.strip()
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    owned = []
    report = {'status': 'FAIL', 'model': 'Fake', 'requested_agent_model': 'gpt-6.1-sol/medium', 'actual_agent_model': 'NOT OBSERVABLE',
        'server_version': server_version, 'cluster_id': cluster_id, 'client_versions': versions,
        'tool_container': {'id': container_id, 'image': image, 'ports': ports}, 'commands': [], 'cleanup': {}}
    report_path = None
    try:
        source = create_test_database(prefix='studyplan_test_v61_restore_source')
        owned.append(source)
        target = create_test_database(prefix='studyplan_test_v61_restore_target')
        owned.append(target)
        assert source.name.startswith('studyplan_test_') and target.name.startswith('studyplan_test_')
        assert source.name != target.name
        report.update(source_database=source.name, target_database=target.name)
        report_path = EVIDENCE / f'v61-restore-{source.name[-8:]}.json'
        migration = _run_alembic(source, 'upgrade', 'head')
        assert migration.returncode == 0, migration.stderr
        with psycopg.connect(source.migrator_dsn) as conn:
            for filename in CURRENT_PACKS.values():
                seed_reviewed_pack(conn, load_pack(filename))
        settings = replace(get_settings(), database_url=source.app_dsn, llm_provider='fake', local_session_token='', planning_worker_admission_mode='trusted_server')
        container = build_container(settings)
        username = '恢复'+new_id('usr')[-10:]
        with TestClient(create_app(container)) as client:
            auth = ok(client.post('/api/v1/auth/register', json=dict(username=username, password='Test-pass1!')))
            query, headers = dict(project_id=auth['project_ids'][0]), {'X-CSRF-Token': auth['csrf_token']}
            queued = ok(client.post('/api/v1/plans/generate', params=query, headers=headers,
                json={'goal': '零基础系统学 Agent，后面重点 RAG。', 'goal_spec': {'target': '零基础系统学 Agent，后面重点 RAG。'}}), 202)
            assert container.planning_worker.tick()
            run = ok(client.get(queued['status_url']))
            assert (run['status'], run['next_action']) == ('succeeded', 'none')
            draft_url = '/api/v1/plans/drafts/'+run['result_ref']
            draft = ok(client.get(draft_url, params=query))
            plan = ok(client.post(draft_url+'/decision', params=query, headers=headers,
                json=dict(decision='approve', expected_version=0, draft_hash=draft['draft_hash'], idempotency_key='restore-publish')))['plan']
            assert plan['extensions'], 'restore must verify nonempty Plan.extensions'
            stage = plan['stages'][0]
            summary = ok(client.post('/api/v1/summaries', params=query, headers=headers,
                json=dict(plan_id=plan['plan_id'], stage_id=stage['stage_id'], content='  恢复原文🙂\n第二行\t ', expected_version=0, idempotency_key='restore-summary')))['attempt']
            task = next(t for t in plan['task_links'] if t['stage_id'] == stage['stage_id'])
            position = dict(plan_id=plan['plan_id'], stage_id=stage['stage_id'], task_id=task['task_id'])
            thread = ok(client.get('/api/v1/submissions', params={**query, **position}))
            saved = ok(client.post('/api/v1/submissions', params=query, headers=headers, json={**position,
                'note': '  合成恢复成果🙂\n原格式\t ', 'repo_url': None, 'artifact_kind': 'evaluation', 'parent_submission_id': None,
                'evidence': [dict(kind='external_report', label='合成报告', content='  人工观察🙂\n非平台执行\t ', source_url=None)],
                'expected_plan_version': thread['plan_version'], 'expected_task_version': thread['task_version'], 'expected_version': thread['version'], 'idempotency_key': 'restore-save'}))
            submission_id = saved['submission']['submission_id']
            accepted = ok(client.post('/api/v1/submissions/'+submission_id+'/decision', params=query, headers=headers,
                json=dict(conclusion='accepted', rationale='合成人工检查🙂\n未平台核验 ', acknowledge_verification_limit=True,
                    coverage=[dict(criterion_index=i, evidence_indices=[0], observation='合成观察🙂\n'+str(i)) for i in range(len(saved['submission']['task_snapshot']['task']['acceptance']))],
                    expected_plan_version=thread['plan_version'], expected_task_version=saved['thread']['task_version'], expected_version=saved['thread']['version'], idempotency_key='restore-accept')))['submission']
            outcomes = ok(client.get('/api/v1/outcomes', params=query))
            workspace = ok(client.get('/api/v1/workspace', params=query))
        before = database_snapshot(source)
        archive = EVIDENCE / f'v61-restore-{source.name[-8:]}.dump'
        parsed = urlsplit(source.migrator_dsn)
        assert parsed.path[1:] == source.name and urlsplit(target.migrator_dsn).path[1:] == target.name
        assert source.name in {d.name for d in owned} and target.name in {d.name for d in owned}
        env = dict(os.environ, PGPASSWORD=unquote(parsed.password or ''))
        dump_command = [*native_prefix, 'pg_dump', '--format=custom', '--host', 'host.docker.internal', '--port', str(ADMIN_PORT), '--username', parsed.username, '--dbname', source.name]
        with archive.open('xb') as output:
            dumped = subprocess.run(dump_command, env=env, stdout=output, stderr=subprocess.PIPE, timeout=60)
        report['commands'].append({'argv': dump_command, 'exit_code': dumped.returncode})
        assert dumped.returncode == 0, dumped.stderr.decode(errors='replace')
        assert archive.stat().st_size > 0
        listed = subprocess.run(['docker', 'exec', '-i', container_id, 'pg_restore', '--list'], input=archive.read_bytes(), capture_output=True, timeout=30)
        report['commands'].append({'argv': ['docker', 'exec', '-i', container_id, 'pg_restore', '--list'], 'exit_code': listed.returncode})
        assert listed.returncode == 0
        assert source.name != target.name and target.name.startswith('studyplan_test_') and target in owned
        restore_command = ['docker', 'exec', '-i', '-e', 'PGPASSWORD', container_id, 'pg_restore', '--exit-on-error', '--single-transaction', '--clean', '--if-exists',
            '--host', 'host.docker.internal', '--port', str(ADMIN_PORT), '--username', parsed.username, '--dbname', target.name]
        with archive.open('rb') as source_dump:
            restored = subprocess.run(restore_command, env=env, stdin=source_dump, capture_output=True, timeout=60)
        report['commands'].append({'argv': restore_command, 'exit_code': restored.returncode})
        assert restored.returncode == 0, restored.stderr.decode(errors='replace')
        after = database_snapshot(target)
        assert after == before
        fresh = build_container(replace(settings, database_url=target.app_dsn))
        with TestClient(create_app(fresh)) as client:
            ok(client.post('/api/v1/auth/login', json=dict(username=username, password='Test-pass1!')))
            assert ok(client.get('/api/v1/plans/current', params=query)) == plan
            assert ok(client.get('/api/v1/workspace', params=query)) == workspace
            assert ok(client.get('/api/v1/summaries/attempts/'+summary['attempt_id'], params=query)) == summary
            assert ok(client.get('/api/v1/submissions/'+submission_id, params=query)) == accepted
            assert ok(client.get('/api/v1/outcomes', params=query)) == outcomes
            assert not fresh.planning_worker.tick()
            assert not fresh.plan_service._llm.calls
        assert role_state() == before_roles and not roles_created_by_harness()
        report.update(status='PASS', archive_path=str(archive), archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
            source_snapshot=before, restored_snapshot=after, snapshot_digest=digest(before),
            originals={'plan_id': plan['plan_id'], 'extensions': plan['extensions'], 'summary_id': summary['attempt_id'],
                'summary_content_sha256': hashlib.sha256(summary['content'].encode()).hexdigest(), 'summary_rubric_snapshot': summary['rubric_snapshot'],
                'submission_id': submission_id, 'note_sha256': hashlib.sha256(accepted['note'].encode()).hexdigest(),
                'task_snapshot': accepted['task_snapshot'], 'review': accepted['review']}, restored_model_calls=0)
    finally:
        for db in reversed(owned):
            assert db.name.startswith('studyplan_test_')
            db.drop()
            report['cleanup'][db.name] = 'PASS'
        assert role_state() == before_roles and not roles_created_by_harness()
        if report_path:
            report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
