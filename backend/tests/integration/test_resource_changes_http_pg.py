"""Actual HTTP/CSRF/PG contract with an isolated synthetic catalog, no provider."""
from dataclasses import asdict

import pytest
from app.main import create_app
from fastapi.testclient import TestClient

from tests.integration.test_resource_changes_pg import migrated_db as migrated_db
from tests.integration.test_resource_changes_pg import scenario as scenario

pytestmark = pytest.mark.postgres


def test_http_preview_confirmation_receipt_and_server_identity(scenario):
    _, scope, command, container, current = scenario
    params = {'project_id': command.project_id}
    body = asdict(command)
    body.pop('project_id')
    with TestClient(create_app(container)) as client:
        client.cookies.set(container.settings.session_cookie_name, container.browser_auth.issue(scope.actor_id))
        headers = {'X-CSRF-Token': client.get('/api/v1/session').json()['csrf_token']}
        base = '/api/v1/resource-changes'
        assert client.get(base + '/catalog', params=params).status_code == 200
        assert client.post(base, params=params, json=body).status_code == 403
        assert client.post(base, params=params, headers=headers, json={**body, 'actor_id': 'client-spoof'}).status_code == 422
        response = client.post(base, params=params, headers=headers, json=body)
        assert response.status_code == 200, response.text
        preview = response.json()
        assert preview['actor_id'] == scope.actor_id and preview['base_plan_id'] == current.plan_id
        assert preview['before']['source']['title'] != preview['after']['source']['title']
        assert client.post(base, params=params, headers=headers, json=body).json() == preview
        url = base + '/' + preview['proposal_id']
        assert client.get(url, params=params).json() == preview
        decision = {'expected_version': command.expected_version, 'preview_hash': preview['preview_hash'],
                    'idempotency_key': 'http-confirm'}
        blocked = client.post(url + '/confirm', params=params, headers=headers, json=decision)
        assert blocked.status_code == 400 and blocked.json()['code'] == 'validation_error', blocked.text
        decision['acknowledge_warnings'] = True
        confirmed = client.post(url + '/confirm', params=params, headers=headers, json=decision)
        assert confirmed.status_code == 200, confirmed.text
        receipt = confirmed.json()
        assert receipt['status'] == 'confirmed' and receipt['revision'] == 2
        assert client.post(url + '/confirm', params=params, headers=headers, json=decision).json() == receipt
        assert client.get(url, params=params).json()['status'] == 'confirmed'
        assert client.get('/api/v1/plans/current', params=params).json()['plan_id'] == receipt['plan_id']
    with TestClient(create_app(container)) as anonymous:
        assert anonymous.get(url, params=params).status_code == 401
