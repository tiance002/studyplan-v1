"""Normal Cookie/CSRF HTTP + real owned PG/Worker; model is Fake."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest

from tests.integration.test_generated_plan_changes_pg import _run_owned_route_browser
from tests.integration.test_generated_plan_changes_pg import generated_route as generated_route
from tests.integration.test_generated_plan_changes_pg import migrated_db as migrated_db

pytestmark = pytest.mark.postgres


def submit(client, params, headers):
    response = client.post('/api/v1/plans/generate', params=params, headers=headers,
                           json={'goal': 'Agent 工具学习'})
    assert response.status_code == 202, response.text
    return response.json()


def test_queued_cancel_http_scope_csrf_cas_and_no_worker_dispatch(generated_route):
    _, container, client, params, headers, _ = generated_route
    queued = submit(client, params, headers)
    run = client.get(queued['status_url']).json()
    url = '/api/v1/runs/' + run['run_id'] + '/cancel'
    body = {'expected_version': run['version'], 'idempotency_key': 'http-cancel'}
    calls = len(container.plan_service._llm.calls)
    assert client.post(url, params=params, json=body).status_code == 403
    assert client.post(url, params={'project_id': 'foreign'}, headers=headers, json=body).status_code == 403
    assert client.post(url, params=params, headers=headers, json={**body, 'expected_version': 99}).status_code == 409
    assert client.post(url, params=params, headers=headers, json={**body, 'actor_id': 'forged'}).status_code == 422
    result = client.post(url, params=params, headers=headers, json=body)
    assert result.status_code == 200, result.text
    assert result.json()['status'] == 'cancelled' and result.json()['next_action'] == 'none'
    assert client.post(url, params=params, headers=headers, json=body).json() == result.json()
    assert not container.planning_worker.tick()
    assert len(container.plan_service._llm.calls) == calls
    assert client.get(queued['status_url']).json()['status'] == 'cancelled'
    new_run = submit(client, params, headers)
    assert new_run['run_id'] != queued['run_id']
    assert container.planning_worker.tick()
    assert client.get(new_run['status_url']).json()['status'] == 'succeeded'
    assert client.get(queued['status_url']).json()['status'] == 'cancelled'
    client.cookies.clear()
    assert client.post(url, params=params, headers=headers, json=body).status_code == 401


@pytest.mark.parametrize('winner', ['cancel', 'publish'])
def test_cancel_after_draft_save_fences_late_completion_and_publication(generated_route, monkeypatch, winner):
    _, container, client, params, headers, old = generated_route
    queued = submit(client, params, headers)
    saved, release = Event(), Event()
    draft_id = []
    original = container.plan_service._complete_generation

    def after_save(**kwargs):
        draft_id.append(kwargs['trace'].state['draft_ref'])
        saved.set()
        assert release.wait(20), 'test release timed out'
        return original(**kwargs)

    monkeypatch.setattr(container.plan_service, '_complete_generation', after_save)
    with ThreadPoolExecutor(max_workers=1) as pool:
        worker = pool.submit(container.planning_worker.tick)
        try:
            assert saved.wait(20), 'Worker did not save draft'
            draft = client.get('/api/v1/plans/drafts/' + draft_id[0], params=params).json()
            assert draft['status'] in {'pending', 'awaiting_approval'}
            run = client.get(queued['status_url']).json()
            decision = {'decision': 'approve', 'expected_version': old['version'],
                        'draft_hash': draft['draft_hash'], 'idempotency_key': 'late-approve'}
            if winner == 'publish':
                approved = client.post('/api/v1/plans/drafts/' + draft_id[0] + '/decision', params=params,
                                       headers=headers, json=decision)
                assert approved.status_code == 200, approved.text
            cancelled = client.post('/api/v1/runs/' + run['run_id'] + '/cancel', params=params, headers=headers,
                                   json={'expected_version': run['version'], 'idempotency_key': 'saved-cancel'})
            assert cancelled.status_code == (200 if winner == 'cancel' else 409), cancelled.text
            if winner == 'cancel':
                assert cancelled.json()['status'] == 'cancelled'
            reread = client.get('/api/v1/plans/drafts/' + draft_id[0], params=params).json()
            assert reread['status'] == ('cancelled' if winner == 'cancel' else 'approved')
            assert reread['draft_hash'] == draft['draft_hash']
            if winner == 'cancel':
                rejected = client.post('/api/v1/plans/drafts/' + draft_id[0] + '/decision', params=params,
                                       headers=headers, json=decision)
                assert rejected.status_code == 409, rejected.text
        finally:
            release.set()
        assert worker.result(timeout=20)
    assert client.get(queued['status_url']).json()['status'] == ('cancelled' if winner == 'cancel' else 'succeeded')
    current = client.get('/api/v1/plans/current', params=params).json()
    assert current['plan_id'] == (old['plan_id'] if winner == 'cancel' else approved.json()['plan']['plan_id'])


def test_real_browser_running_cancel_reload_and_relogin(generated_route, monkeypatch):
    import os
    if os.environ.get('STUDYPLAN_GENERATED_ROUTE_BROWSER') != '1':
        pytest.skip('real Chrome enabled only for owned browser acceptance')
    _, container, client, params, headers, _ = generated_route
    queued = submit(client, params, headers)
    run_id = queued['run_id']
    release = Event()
    started = Event()
    acknowledged = Event()
    original_execute = container.plan_service.execute_generation
    original_cancel = container.plan_service._planning_jobs.cancel_run
    calls = len(container.plan_service._llm.calls)

    def paused_execution(project_id, current_run_id, **kwargs):
        if current_run_id == run_id:
            started.set()
            assert release.wait(60), 'owned browser cancellation timed out'
            if not acknowledged.is_set():
                from app.ports.planning_jobs import PlanningLeaseLostError
                raise PlanningLeaseLostError('owned browser test ended before cancellation')
        return original_execute(project_id, current_run_id, **kwargs)

    def release_after_cancel(**kwargs):
        result = original_cancel(**kwargs)
        acknowledged.set()
        release.set()
        return result

    monkeypatch.setattr(container.plan_service, 'execute_generation', paused_execution)
    monkeypatch.setattr(container.plan_service._planning_jobs, 'cancel_run', release_after_cancel)
    monkeypatch.setenv('STUDYPLAN_CANCEL_RUN', run_id)
    try:
        _run_owned_route_browser(generated_route, 'frontend/tests/planning-cancel-pg.browser.cjs')
    finally:
        release.set()
    assert client.get(queued['status_url']).json()['status'] == 'cancelled'
    assert started.is_set() and acknowledged.is_set()
    assert len(container.plan_service._llm.calls) == calls
