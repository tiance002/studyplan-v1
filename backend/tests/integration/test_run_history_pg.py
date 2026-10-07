"""Private, bounded server recovery; owned PostgreSQL and explicit Fake model."""

import psycopg
import pytest

from tests.e2e.test_b2v_http_end_to_end import migrated_db as migrated_db
from tests.integration.test_generated_plan_changes_pg import generated_route as generated_route

pytestmark = pytest.mark.postgres


def test_history_is_bounded_private_and_read_only(generated_route):
    db, container, client, params, _, _ = generated_route
    project = params['project_id']
    scope = container.browser_auth.resolve(client.cookies.get(container.settings.session_cookie_name))
    calls = len(container.plan_service._llm.calls)
    with psycopg.connect(db.migrator_dsn) as conn:
        before_jobs = conn.execute('SELECT count(*) FROM ai_jobs').fetchone()[0]
        for index in range(22):
            conn.execute("""INSERT INTO ai_runs(run_id,actor_id,project_id,kind,status,next_action,
                graph_name,graph_version,thread_id,created_at)
                VALUES (%s,%s,%s,'plan_generate','failed','retry','planning','b3f2-short-v2',
                'PRIVATE_MANIFEST_THREAD', '2090-01-01'::timestamptz + %s * interval '1 second')""",
                (f'history-{project}-{index:02}', scope.actor_id, project, index))
        for actor, kind, suffix in [("foreign-history-actor", 'plan_generate', 'foreign'),
                                    (scope.actor_id, 'prompt_review', 'prompt')]:
            conn.execute("""INSERT INTO ai_runs(run_id,actor_id,project_id,kind,status,next_action,
                graph_name,graph_version,created_at)
                VALUES (%s,%s,%s,%s,'failed','none','private','private', '2091-01-01')""",
                (f'history-{project}-{suffix}', actor, project, kind))
    result = client.get('/api/v1/runs', params={**params, 'limit': 3})
    assert result.status_code == 200, result.text
    assert [r['run_id'] for r in result.json()] == [f'history-{project}-{i:02}' for i in (21, 20, 19)]
    for row in result.json():
        assert row['progress'] is None
        assert set(row) == {'run_id', 'status', 'next_action', 'version', 'result_ref', 'error', 'progress'}
    assert 'PRIVATE_MANIFEST_THREAD' not in result.text
    assert len(client.get('/api/v1/runs', params=params).json()) == 10
    assert len(client.get('/api/v1/runs', params={**params, 'limit': 20}).json()) == 20
    for limit in (0, -1, 21, 1000000):
        assert client.get('/api/v1/runs', params={**params, 'limit': limit}).status_code == 422
    assert client.get('/api/v1/runs', params={'project_id': 'foreign-project'}).status_code == 403
    assert client.get(f'/api/v1/runs/history-{project}-foreign', params=params).status_code == 404
    assert len(container.plan_service._llm.calls) == calls
    with psycopg.connect(db.migrator_dsn) as conn:
        assert conn.execute('SELECT count(*) FROM ai_jobs').fetchone()[0] == before_jobs
    client.cookies.clear()
    assert client.get('/api/v1/runs', params=params).status_code == 401


def test_history_recovers_unknown_without_claim_or_replay(generated_route):
    db, container, client, params, _, _ = generated_route
    scope = container.browser_auth.resolve(client.cookies.get(container.settings.session_cookie_name))
    run_id = 'history-unknown-' + params['project_id']
    with psycopg.connect(db.migrator_dsn) as conn:
        conn.execute("""INSERT INTO ai_runs(run_id,actor_id,project_id,kind,status,next_action,
                graph_name,graph_version,error_class)
            VALUES (%s,%s,%s,'plan_generate','reconciliation_required','reconcile',
                'planning','b3f2-short-v2','provider_dispatch_unknown')""",
            (run_id, scope.actor_id, params['project_id']))
    calls = len(container.plan_service._llm.calls)
    rows = client.get('/api/v1/runs', params=params)
    assert rows.status_code == 200, rows.text
    recovered = next(r for r in rows.json() if r['run_id'] == run_id)
    assert recovered['status'] == 'reconciliation_required' and recovered['next_action'] == 'reconcile'
    assert client.get('/api/v1/runs/' + run_id, params=params).json()['status'] == recovered['status']
    assert not container.planning_worker.tick()
    assert len(container.plan_service._llm.calls) == calls
