"""M1.1: disposable PG/RLS, persistent sessions and original graph decisions.

Requires the existing pg_harness dedicated-instance opt-in. Synthetic data only.
No live acceptance IDs, real credentials or provider HTTP requests are used.
"""
from contextlib import contextmanager
from dataclasses import replace
from unittest.mock import patch

import httpx
import psycopg
import pytest
from app.application.browser_auth import HASHER, credentials, verify_password
from app.composition import build_container
from app.core.config import get_settings
from app.infrastructure.checkpointer.planning_executor import PgPlanningExecutor
from app.infrastructure.db.browser_auth import token_hash
from app.infrastructure.db.model_settings import PgModelSettings
from app.infrastructure.providers.runtime_factory import PersonalPlanningRuntimeFactory
from app.main import create_app
from app.tools.b3f2_controlled_live import validate_provider
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from langgraph.checkpoint.postgres import PostgresSaver

from tests.e2e.test_b2v_http_end_to_end import (
    ACTOR_A1,
    ACTOR_A2,
    GOAL_A,
    PROJECT_P1,
    PROJECT_P2,
    _approve_body,
    _fake_llm,
    _select_test_pack,
    migrated_db,
)
from tests.pg_harness import create_test_database, instance_is_dedicated

pytestmark = pytest.mark.postgres
SECOND_OWNED = 'm11-owned-second'
PASSWORD = 'M11Test123'
MODEL_SECRET = 'm11-fixture-secret-no-valid-provider-key'
ORIGIN = 'http://localhost:5173'


def local_container(db, checkpoint, key, **overrides):
    settings = replace(get_settings(), database_url=db.app_dsn,
                       checkpoint_database_url=checkpoint.migrator_dsn,
                       model_settings_encryption_key=key, llm_provider='fake',
                       local_entry_enabled=True, local_actor_id=ACTOR_A1,
                       local_project_id=PROJECT_P1, planning_worker_actor_ids=(ACTOR_A1,),
                       allow_origins=(ORIGIN,), app_host='127.0.0.1', app_port=8000,
                       graph_version='b3f2-batch-v1')
    settings = replace(settings, **overrides)
    container = build_container(settings)
    service = container.plan_service
    service._llm = _fake_llm()
    service._domain_pack_selector = _select_test_pack
    service._executor = PgPlanningExecutor(checkpoint.migrator_dsn, llm=service._llm)
    return container


def client_for(container):
    return TestClient(create_app(container), base_url='http://127.0.0.1:8000',
                      client=('127.0.0.1', 43210))


def enter(client):
    response = client.post('/api/v1/session/local', json={}, headers={'Origin': ORIGIN})
    assert response.status_code == 200, response.text
    return response.json()['csrf_token']


@contextmanager
def prepared_environment():
    """Owned disposable databases; ten in-process Fake calls create two old drafts."""
    assert instance_is_dedicated(), 'Explicit disposable-instance opt-in required'
    # Reuse the already reviewed PG migration/public-resource fixture; no new schema.
    generator = migrated_db.__wrapped__()
    db = next(generator)
    checkpoint = create_test_database(prefix='studyplan_test_m11_cp')
    try:
        with PostgresSaver.from_conn_string(checkpoint.migrator_dsn) as saver:
            saver.setup()
        key = Fernet.generate_key().decode()
        with psycopg.connect(db.migrator_dsn) as conn:
            for actor, username in ((ACTOR_A1, 'M11Original'), (ACTOR_A2, 'M11Other')):
                conn.execute('INSERT INTO auth_users(actor_id,username,username_key,password_hash) '
                             'VALUES (%s,%s,%s,%s)',
                             (actor, username, username.casefold(), HASHER.hash(PASSWORD)))
            conn.execute("INSERT INTO learning_projects(project_id,owner_actor_id,title,goal_statement,stable_key) "
                         "VALUES (%s,%s,'Synthetic second owned project','fixture','m11-second')",
                         (SECOND_OWNED, ACTOR_A1))
            conn.execute("INSERT INTO auth_sessions(token_hash,actor_id,session_id,csrf_token,expires_at) "
                         "VALUES (%s,%s,'m11-expired-original','synthetic-csrf',now()-interval '1 day')",
                         (token_hash('synthetic-expired'), ACTOR_A1))
        models = PgModelSettings(db.app_dsn, key)
        for actor, model in ((ACTOR_A1, 'deepseek-flash'), (ACTOR_A2, 'foreign-fixture-model')):
            models.save(actor, expected_version=0, base_url='https://api.deepseek.com',
                        model_id=model, protocol='openai', api_key=MODEL_SECRET)
        container = local_container(db, checkpoint, key)
        drafts = []
        with patch.object(httpx.HTTPTransport, 'handle_request', side_effect=AssertionError('NO PROVIDER HTTP')), \
                patch.object(httpx.AsyncHTTPTransport, 'handle_async_request', side_effect=AssertionError('NO PROVIDER HTTP')):
            with client_for(container) as client:
                csrf = enter(client)
                for _ in range(2):
                    submitted = client.post('/api/v1/plans/generate', params={'project_id': PROJECT_P1},
                                            json={'goal': GOAL_A}, headers={'X-CSRF-Token': csrf})
                    assert submitted.status_code == 202, submitted.text
                    assert container.planning_worker.tick()
                    run = client.get('/api/v1/runs/' + submitted.json()['run_id'],
                                     params={'project_id': PROJECT_P1}).json()
                    assert run['status'] == 'waiting_user', run
                    draft = client.get('/api/v1/plans/drafts/' + run['result_ref'],
                                       params={'project_id': PROJECT_P1}).json()
                    assert draft['status'] == 'awaiting_approval'
                    drafts.append((run, draft))
        assert len(container.plan_service._llm.calls) == 10
        yield dict(db=db, checkpoint=checkpoint, key=key, drafts=drafts)
    finally:
        checkpoint.drop()
        generator.close()


@pytest.fixture(scope='module')
def environment():
    with prepared_environment() as fixture:
        yield fixture


def test_pg_role_and_rls_fail_closed_without_context(environment):
    db = environment['db']
    with psycopg.connect(db.app_dsn) as conn:
        flags = conn.execute('SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole '
                             'FROM pg_roles WHERE rolname=current_user').fetchone()
        assert flags == (False, False, False, False)
        for table in ('auth_users', 'auth_sessions', 'learning_projects', 'user_model_settings', 'ai_runs', 'plan_drafts'):
            assert conn.execute('SELECT count(*) FROM ' + table).fetchone()[0] == 0
            assert conn.execute('SELECT relrowsecurity,relforcerowsecurity FROM pg_class WHERE relname=%s',
                                (table,)).fetchone() == (True, True)


def test_persistent_session_scope_models_and_no_identity_creation(environment):
    db, cp, key = environment['db'], environment['checkpoint'], environment['key']
    with psycopg.connect(db.migrator_dsn) as conn:
        before = conn.execute('SELECT actor_id,username,password_hash FROM auth_users ORDER BY actor_id').fetchall()
        models_before = conn.execute('SELECT * FROM user_model_setting_versions ORDER BY actor_id,version').fetchall()
    first = local_container(db, cp, key)
    with client_for(first) as client:
        enter(client)
        response = client.get('/api/v1/session')
        assert set(response.json()['project_ids']) == {PROJECT_P1, SECOND_OWNED}
        assert response.json()['default_project_id'] == PROJECT_P1
        cookies = dict(client.cookies)
        assert first.sessions.resolve(cookies[first.settings.session_cookie_name]).actor_id == ACTOR_A1
        model = client.get('/api/v1/model-settings')
        assert model.json()['model_id'] == 'deepseek-flash'
        assert MODEL_SECRET not in model.text and 'encrypted_api_key' not in model.text
    with client_for(local_container(db, cp, key)) as restarted:
        restarted.cookies.update(cookies)
        assert restarted.get('/api/v1/session').json() == response.json()
    with psycopg.connect(db.migrator_dsn) as conn:
        assert conn.execute('SELECT actor_id,username,password_hash FROM auth_users ORDER BY actor_id').fetchall() == before
        assert conn.execute('SELECT * FROM user_model_setting_versions ORDER BY actor_id,version').fetchall() == models_before
        assert conn.execute("SELECT count(*) FROM auth_sessions WHERE session_id='m11-expired-original'").fetchone()[0] == 1


def test_pg_missing_binding_spoof_and_cross_project_rejection(environment):
    db, cp, key = environment['db'], environment['checkpoint'], environment['key']
    with psycopg.connect(db.migrator_dsn) as conn:
        count = conn.execute('SELECT count(*) FROM auth_sessions').fetchone()[0]
    for overrides in ({'local_actor_id': ''}, {'local_actor_id': 'local_actor'},
                      {'local_actor_id': 'missing', 'planning_worker_actor_ids': ('missing',)},
                      {'local_actor_id': 'a,b'}, {'planning_worker_actor_ids': ()},
                      {'local_project_id': PROJECT_P2}):
        with client_for(local_container(db, cp, key, **overrides)) as client:
            assert client.post('/api/v1/session/local', json={}, headers={'Origin': ORIGIN}).status_code in (403, 503)
    with psycopg.connect(db.migrator_dsn) as conn:
        assert conn.execute('SELECT count(*) FROM auth_sessions').fetchone()[0] == count
    container = local_container(db, cp, key)
    with client_for(container) as client:
        assert client.post('/api/v1/session/local', json={'actor_id': ACTOR_A2}, headers={'Origin': ORIGIN}).status_code == 422
        response = client.post('/api/v1/session/local', json={}, headers={'Origin': ORIGIN, 'X-Actor-Id': ACTOR_A2})
        assert response.status_code == 200
        assert container.sessions.resolve(client.cookies.get(container.settings.session_cookie_name)).actor_id == ACTOR_A1
        csrf = response.json()['csrf_token']
        run, draft = environment['drafts'][0]
        for project in (PROJECT_P2, 'missing-project'):
            for path in ('/runs/' + run['run_id'], '/plans/drafts/' + draft['draft_id'], '/workspace', '/plans/current'):
                assert client.get('/api/v1' + path, params={'project_id': project}).status_code == 403
            assert client.post('/api/v1/plans/drafts/' + draft['draft_id'] + '/decision',
                               params={'project_id': project}, json={'decision': 'cancel', 'expected_version': 0},
                               headers={'X-CSRF-Token': csrf}).status_code == 403
        client.cookies.clear()
        foreign = container.browser_auth.issue(ACTOR_A2)
        client.cookies.set(container.settings.session_cookie_name, foreign)
        assert client.get('/api/v1/session').status_code == 403
        assert client.get('/api/v1/model-settings').status_code == 403
    assert len(container.plan_service._llm.calls) == 0


def test_cli_login_and_readonly_preflight_compatibility(environment):
    db, cp, key = environment['db'], environment['checkpoint'], environment['key']
    container = local_container(db, cp, key)
    with client_for(container) as client:
        # Existing controlled CLI sends no Origin; it still requires cookie + CSRF for writes.
        login = client.post('/api/v1/auth/login', json={'username': 'M11Original', 'password': PASSWORD})
        assert login.status_code == 200, login.text
        assert client.get('/api/v1/model-settings').json()['model_id'] == 'deepseek-flash'
        assert client.post('/api/v1/auth/logout', json={}).status_code == 403
        assert client.post('/api/v1/auth/logout', json={}, headers={'X-CSRF-Token': login.json()['csrf_token']}).status_code == 200
    with psycopg.connect(db.app_dsn) as conn:
        conn.execute('SET TRANSACTION READ ONLY')
        _, username = credentials('M11Original', PASSWORD)
        conn.execute("SELECT set_config('app.auth_username',%s,true)", (username,))
        actor, password_hash = conn.execute('SELECT actor_id,password_hash FROM auth_users WHERE username_key=%s', (username,)).fetchone()
        verify_password(PASSWORD, password_hash)
        assert actor == ACTOR_A1
    repository = PgModelSettings(db.app_dsn, key)
    selected = repository.resolve(actor)
    with patch.object(httpx.HTTPTransport, 'handle_request', side_effect=AssertionError('NO PROVIDER HTTP')) as guard:
        # Actual controlled-live free validator and provider factory; construction/options only.
        factory = PersonalPlanningRuntimeFactory(container.settings, repository)
        validate_provider(factory._personal_provider(actor, selected))
        assert guard.call_count == 0
    assert container.plan_service._graph_version == 'b3f2-batch-v1'
    jobs = container.plan_service._planning_jobs
    assert jobs.acquire_worker_lock()
    jobs.release_worker_lock()
    assert len(container.plan_service._llm.calls) == 0


@pytest.mark.parametrize('decision,index', [('approve', 0), ('cancel', 1)])
def test_old_waiting_user_checkpoint_decision_restart_and_replay(environment, decision, index):
    db, cp, key = environment['db'], environment['checkpoint'], environment['key']
    run, draft = environment['drafts'][index]
    container = local_container(db, cp, key)  # Fresh runtime has made zero Fake calls.
    original = container.plan_service._runs.get_run(project_id=PROJECT_P1, run_id=run['run_id'])
    with PostgresSaver.from_conn_string(cp.migrator_dsn) as saver:
        saved = saver.get_tuple({'configurable': {'thread_id': original.thread_id}})
        assert saved is not None
        assert saved.checkpoint['channel_values']['graph_version'] == 'b3f2-batch-v1'
    url = '/api/v1/plans/drafts/' + draft['draft_id'] + '/decision'
    body = _approve_body(draft, 0, 'm11-' + decision) if decision == 'approve' else {'decision': 'cancel', 'expected_version': 0}
    with patch.object(httpx.HTTPTransport, 'handle_request', side_effect=AssertionError('NO PROVIDER HTTP')) as guard:
        with client_for(container) as client:
            csrf = enter(client)
            invalid = ({**body, 'expected_version': 77}, {**body, 'draft_hash': 'stale'}) if decision == 'approve' else ()
            for bad in invalid:
                assert client.post(url, params={'project_id': PROJECT_P1}, json=bad, headers={'X-CSRF-Token': csrf}).status_code == 409
            assert client.post(url, params={'project_id': PROJECT_P1}, json=body).status_code == 403
            response = client.post(url, params={'project_id': PROJECT_P1}, json=body, headers={'X-CSRF-Token': csrf})
            assert response.status_code == 200, response.text
            cookies = dict(client.cookies)
        restarted = local_container(db, cp, key)
        with client_for(restarted) as client:
            client.cookies.update(cookies)
            repeated = client.post(url, params={'project_id': PROJECT_P1}, json=body, headers={'X-CSRF-Token': csrf})
            if decision == 'approve':
                assert repeated.status_code == 200, repeated.text
                assert repeated.json() == response.json()
            else:
                # Existing cancellation is state guarded: a second cancel is 409,
                # and must not mutate or dispatch. Only approval has an idem key.
                assert repeated.status_code == 409, repeated.text
            read = client.get('/api/v1/runs/' + run['run_id'], params={'project_id': PROJECT_P1}).json()
            assert read['status'] == ('succeeded' if decision == 'approve' else 'cancelled')
            assert read['run_id'] == run['run_id']
            reread = client.get('/api/v1/plans/drafts/' + draft['draft_id'], params={'project_id': PROJECT_P1}).json()
            assert reread['draft_hash'] == draft['draft_hash']
            assert reread['stages'] == draft['stages']
            if decision == 'approve':
                assert client.get('/api/v1/plans/current', params={'project_id': PROJECT_P1}).json() == response.json()['plan']
        assert guard.call_count == 0
    with PostgresSaver.from_conn_string(cp.migrator_dsn) as saver:
        saved = saver.get_tuple({'configurable': {'thread_id': original.thread_id}})
        assert saved.checkpoint['channel_values']['decision'] == decision
    with psycopg.connect(db.migrator_dsn) as conn:
        assert conn.execute('SELECT count(*) FROM ai_runs').fetchone()[0] == 2
        assert conn.execute('SELECT count(*) FROM ai_provider_attempts').fetchone()[0] == 0
    assert len(container.plan_service._llm.calls) + len(restarted.plan_service._llm.calls) == 0
