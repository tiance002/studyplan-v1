"""Existing Worker + ordinary auth + owned PG. Models are explicitly Fake."""
from dataclasses import replace

import psycopg
import pytest
from app.composition import build_container
from app.core.config import get_settings
from app.core.ids import new_id
from app.infrastructure.db.learning_resources import PgLearningResources
from app.infrastructure.domain_pack import load_pack
from app.main import create_app
from app.ports.llm import LLMDispatchUnknownError
from app.tools.seed_b3 import seed_reviewed_pack
from fastapi.testclient import TestClient

from tests.e2e.test_b2v_http_end_to_end import migrated_db as migrated_db
from tests.unit.test_learning_guidance import guided_pack, repeated_guided_pack

pytestmark = pytest.mark.postgres


@pytest.fixture
def generated_route(migrated_db, request):
    pack = repeated_guided_pack()
    optional = getattr(request, 'param', None) == 'optional'
    if optional:
        pack = guided_pack()
        next(s for s in pack['stage_blueprints'] if s['stable_key'] == 'stage.mcp')['inclusion'] = 'optional'
        pack['required_node_keys'] = [k for k in pack['required_node_keys'] if not k.startswith('node.mcp')]
        next(n for n in pack['knowledge_blueprints'] if n['stable_key'] == 'node.reliability')['prerequisite_keys'].remove('node.mcp')
    # Explicit immutable synthetic snapshots for lifecycle regression coverage.
    pack['version'] = 3 if optional else 4
    with psycopg.connect(migrated_db.migrator_dsn) as conn:
        seed_reviewed_pack(conn, pack)
    settings = replace(get_settings(), database_url=migrated_db.app_dsn, llm_provider='fake',
                       local_session_token='', planning_worker_admission_mode='trusted_server',
                       allow_origins=('http://127.0.0.1:5178',))
    container = build_container(settings)
    from tests.helpers.frozen_planning import install_frozen_generation
    install_frozen_generation(container.plan_service, pack)
    with TestClient(create_app(container)) as client:
        auth = client.post('/api/v1/auth/register', json={'username': '重规划' + new_id('usr')[-10:],
                                                        'password': 'Test-pass1!'})
        assert auth.status_code == 200, auth.text
        project = auth.json()['project_ids'][0]
        params = {'project_id': project}
        headers = {'X-CSRF-Token': auth.json()['csrf_token']}
        submit = client.post('/api/v1/plans/generate', params=params, headers=headers,
                             json={'goal': 'Agent工具复习', 'goal_spec': {'target': 'Agent', 'outcome_purpose': 'interview'}})
        assert submit.status_code == 202, submit.text
        assert container.planning_worker.tick()
        run = client.get(submit.json()['status_url']).json()
        assert run['status'] == 'succeeded', run
        draft = client.get('/api/v1/plans/drafts/' + run['result_ref'], params=params).json()
        approved = client.post('/api/v1/plans/drafts/' + draft['draft_id'] + '/decision', params=params,
                    headers=headers, json={'decision': 'approve', 'expected_version': 0,
                        'draft_hash': draft['draft_hash'], 'idempotency_key': 'initial'})
        assert approved.status_code == 200, approved.text
        yield migrated_db, container, client, params, headers, approved.json()['plan']


@pytest.mark.parametrize('generated_route', ['optional'], indirect=True)
def test_add_topic_worker_closure_history_private_reload_and_idempotency(generated_route):
    db, container, client, params, headers, full = generated_route
    removed = client.post('/api/v1/plan-changes', params=params, headers=headers,
        json=dict(plan_id=full['plan_id'], expected_version=full['version'], operation='remove_optional_topic',
                  stage_key='stage.mcp', idempotency_key='remove-for-add'))
    assert removed.status_code == 200, removed.text
    rm = removed.json()
    assert client.post('/api/v1/plan-changes/' + rm['proposal_id'] + '/confirm', params=params, headers=headers,
        json=dict(expected_version=full['version'], preview_hash=rm['preview_hash'],
                  idempotency_key='confirm-remove', acknowledge_reset=True)).status_code == 200
    old = client.get('/api/v1/plans/current', params=params).json()
    first = old['stages'][0]
    unit = next(link['unit_id'] for link in old['unit_links'] if link['stage_id'] == first['stage_id'])
    pos = dict(plan_id=old['plan_id'], stage_id=first['stage_id'], unit_id=unit)
    assert client.put('/api/v1/exposures', params=params, headers=headers, json={**pos, 'status': 'in_progress',
        'expected_version': 0, 'idempotency_key': 'add-start'}).status_code == 200
    scope = container.browser_auth.resolve(client.cookies.get(container.settings.session_cookie_name))
    selected = PgLearningResources(db.app_dsn).select(scope, {**pos, **params}, dict(resource_id='add-private-' + params['project_id'],
        project_id=params['project_id'], url='https://example.com/add-private', title='PRIVATE_ADD_BODY', media_type='text',
        language='en', provenance='user_provided', verification_status='unverified', source_version=7))
    context = client.get('/api/v1/plan-changes/context', params=params).json()
    assert 'node.mcp.1' in {t['stable_key'] for t in context['add_topic_options']}
    body = dict(plan_id=old['plan_id'], expected_version=old['version'], operation='add_topic',
                topic_keys=['node.mcp.1'], idempotency_key='add-owned')
    queued = client.post('/api/v1/plan-changes/generate', params=params, headers=headers, json=body)
    assert queued.status_code == 202, queued.text
    assert client.post('/api/v1/plan-changes/generate', params=params, headers=headers, json=body).json() == queued.json()
    assert client.post('/api/v1/plan-changes/generate', params=params, headers=headers,
        json={**body, 'topic_keys': ['node.mcp.2']}).status_code == 409
    assert container.planning_worker.tick()
    run = client.get(queued.json()['status_url']).json()
    assert run['status'] == 'succeeded', run
    url = '/api/v1/plan-changes/' + run['result_ref']
    preview = client.get(url, params=params).json()
    assert preview['operation'] == 'add_topic'
    assert preview['added_stage_keys'] == ['stage.mcp']
    assert {'node.mcp', 'node.mcp.1'} <= set(preview['added_node_keys'])
    assert preview['topic_keys'] == ['node.mcp.1']
    assert preview['topic_titles']['node.mcp.1'] == next(t['title'] for t in context['add_topic_options'] if t['stable_key'] == 'node.mcp.1')
    before = [s['stable_key'] for s in old['stages']]
    after = preview['after_stage_keys']
    assert [k for k in after if k in before] == before and after[-1] == before[-1]
    assert preview['draft']['stages'][0] == first
    assert preview['retained_stage_keys'] == before
    for stage in old['stages']:
        assert next(s for s in preview['draft']['stages'] if s['stable_key'] == stage['stable_key'])['stage_id'] == stage['stage_id']
    assert client.get('/api/v1/plans/current', params=params).json()['plan_id'] == old['plan_id']
    decision = dict(expected_version=old['version'], preview_hash=preview['preview_hash'],
                    idempotency_key='add-confirm', acknowledge_reset=True)
    result = client.post(url + '/confirm', params=params, headers=headers, json=decision)
    assert result.status_code == 200, result.text
    assert client.post(url + '/confirm', params=params, headers=headers, json=decision).json() == result.json()
    newer = client.get('/api/v1/plans/current', params=params).json()
    assert newer['goal_snapshot'] == old['goal_snapshot'] and newer['goal_spec'] == old['goal_spec']
    assert client.get('/api/v1/plan-changes/context', params=params).json()['add_topic_options'] == []
    assert client.post('/api/v1/plan-changes/generate', params=params, headers=headers, json=body).json() == queued.json()
    assert not container.planning_worker.tick()
    with psycopg.connect(db.migrator_dsn) as conn:
        copied = conn.execute('SELECT resource_snapshot FROM learning_resource_selections WHERE project_id=%s AND plan_id=%s',
                             (params['project_id'], newer['plan_id'])).fetchone()[0]
        assert copied['selection_copy_lineage']['original_selection_id'] == selected['selection_id']
        assert conn.execute('SELECT count(*) FROM learning_exposures WHERE project_id=%s AND plan_id=%s',
                            (params['project_id'], old['plan_id'])).fetchone()[0] == 1
        assert conn.execute('SELECT count(*) FROM learning_exposures WHERE project_id=%s AND plan_id=%s',
                            (params['project_id'], newer['plan_id'])).fetchone()[0] == 0
    assert 'PRIVATE_ADD_BODY' not in str(container.plan_service._llm.calls)


def test_add_topic_refusals_never_queue_or_dispatch(generated_route):
    _, container, client, params, headers, old = generated_route
    calls = len(container.plan_service._llm.calls)
    body = dict(plan_id=old['plan_id'], expected_version=old['version'], operation='add_topic',
                topic_keys=['node.tools'], idempotency_key='add-reject')
    for changes, status in [({}, 400), ({'topic_keys': ['foreign.node']}, 400),
            ({'topic_keys': []}, 400), ({'topic_keys': ['node.tools', 'node.tools']}, 400),
            ({'goal': 'new goal'}, 400), ({'expected_version': old['version'] - 1}, 409),
            ({'actor_id': 'spoof'}, 422), ({'topic_keys': ['foreign.node'] * 21}, 422)]:
        response = client.post('/api/v1/plan-changes/generate', params=params, headers=headers,
                               json={**body, **changes})
        assert response.status_code == status, response.text
    assert client.post('/api/v1/plan-changes/generate', params=params, json=body).status_code == 403
    assert client.post('/api/v1/plan-changes/generate', params={'project_id': 'foreign-project'},
                       headers=headers, json=body).status_code == 403
    assert not container.planning_worker.tick()
    assert len(container.plan_service._llm.calls) == calls


@pytest.mark.parametrize('generated_route', ['optional'], indirect=True)
def test_add_topic_learning_after_enqueue_fences_dispatch_and_protects_completed_route(generated_route):
    _, container, client, params, headers, full = generated_route
    removed = client.post('/api/v1/plan-changes', params=params, headers=headers,
        json=dict(plan_id=full['plan_id'], expected_version=full['version'], operation='remove_optional_topic',
                  stage_key='stage.mcp', idempotency_key='late-remove'))
    assert removed.status_code == 200
    preview = removed.json()
    assert client.post('/api/v1/plan-changes/' + preview['proposal_id'] + '/confirm', params=params, headers=headers,
        json=dict(expected_version=full['version'], preview_hash=preview['preview_hash'],
                  idempotency_key='late-remove-confirm', acknowledge_reset=True)).status_code == 200
    old = client.get('/api/v1/plans/current', params=params).json()
    body = dict(plan_id=old['plan_id'], expected_version=old['version'], operation='add_topic',
                topic_keys=['node.mcp.1'], idempotency_key='late-add')
    queued = client.post('/api/v1/plan-changes/generate', params=params, headers=headers, json=body)
    assert queued.status_code == 202
    calls = len(container.plan_service._llm.calls)
    final = old['stages'][-1]
    unit = next(link['unit_id'] for link in old['unit_links'] if link['stage_id'] == final['stage_id'])
    assert client.put('/api/v1/exposures', params=params, headers=headers, json=dict(plan_id=old['plan_id'],
        stage_id=final['stage_id'], unit_id=unit, status='in_progress', expected_version=0,
        idempotency_key='late-final-start')).status_code == 200
    assert container.planning_worker.tick()
    assert client.get(queued.json()['status_url']).json()['status'] == 'failed'
    assert len(container.plan_service._llm.calls) == calls
    assert client.get('/api/v1/plan-changes/context', params=params).json()['add_topic_options'] == []
    assert client.post('/api/v1/plan-changes/generate', params=params, headers=headers,
                       json={**body, 'idempotency_key': 'after-start'}).status_code == 400
    assert not container.planning_worker.tick()



def test_generated_future_worker_diff_confirm_restart_history_and_canonical_reuse(generated_route):
    db, container, client, params, headers, old = generated_route
    first = next(s for s in old['stages'] if s['stable_key'] == 'stage.tools')
    unit = next(x['unit_id'] for x in old['unit_links'] if x['stage_id'] == first['stage_id'])
    pos = dict(plan_id=old['plan_id'], stage_id=first['stage_id'], unit_id=unit)
    started = client.put('/api/v1/exposures', params=params, headers=headers, json={**pos,
            'status': 'in_progress', 'expected_version': 0, 'idempotency_key': 'start'})
    assert started.status_code == 200, started.text
    calls_before = len(container.plan_service._llm.calls)
    body = dict(plan_id=old['plan_id'], expected_version=old['version'], operation='regenerate_future_plan',
                idempotency_key='future')
    url = '/api/v1/plan-changes/generate'
    queued = client.post(url, params=params, headers=headers, json=body)
    assert queued.status_code == 202, queued.text
    assert len(container.plan_service._llm.calls) == calls_before
    assert client.post(url, params=params, headers=headers, json=body).json() == queued.json()
    assert container.planning_worker.tick()
    run = client.get(queued.json()['status_url']).json()
    assert run['status'] == 'succeeded' and run['next_action'] == 'none', run
    preview_url = '/api/v1/plan-changes/' + run['result_ref']
    preview = client.get(preview_url, params=params)
    assert preview.status_code == 200, preview.text
    preview = preview.json()
    assert preview['operation'] == 'regenerate_future_plan'
    assert preview['before_stage_keys'] == preview['after_stage_keys']
    assert next(s for s in preview['draft']['stages'] if s['stable_key'] == first['stable_key']) == first
    assert next(x for x in preview['draft']['unit_links'] if x['stage_id'] == first['stage_id'])['unit_id'] == unit
    assert preview['draft']['change_preview_id'] == run['result_ref']
    assert client.get('/api/v1/plans/current', params=params).json()['plan_id'] == old['plan_id']
    bypass = client.post('/api/v1/plans/drafts/' + run['result_ref'] + '/decision', params=params,
                        headers=headers, json={'decision': 'approve', 'expected_version': old['version'],
                            'draft_hash': preview['preview_hash'], 'idempotency_key': 'bypass'})
    assert bypass.status_code == 409
    decision = dict(expected_version=old['version'], preview_hash=preview['preview_hash'],
                    idempotency_key='confirm-generated', acknowledge_reset=True)
    result = client.post(preview_url + '/confirm', params=params, headers=headers, json=decision)
    assert result.status_code == 200, result.text
    assert client.post(preview_url + '/confirm', params=params, headers=headers, json=decision).json() == result.json()
    newer = client.get('/api/v1/plans/current', params=params).json()
    assert newer['plan_id'] != old['plan_id'] and newer['goal_spec'] == old['goal_spec']
    assert not container.planning_worker.tick()
    assert client.post(url, params=params, headers=headers, json=body).json() == queued.json()
    # A different command with the same key must not queue or dispatch again.
    assert client.post(url, params=params, headers=headers, json={**body, 'operation': 'change_goal',
                        'goal': 'Agent新目标'}).status_code == 409
    project = params['project_id']
    with psycopg.connect(db.migrator_dsn) as conn:
        nodes = conn.execute('''SELECT DISTINCT n.node_id FROM plan_unit_links p
            JOIN unit_node_links u USING(project_id,unit_id) JOIN knowledge_nodes n USING(project_id,node_id)
            WHERE p.plan_id=%s AND n.stable_key='node.tools' ''', (newer['plan_id'],)).fetchall()
        assert len(nodes) == 1
        assert conn.execute('SELECT count(*) FROM learning_exposures WHERE project_id=%s AND plan_id=%s',
                            (project, newer['plan_id'])).fetchone()[0] == 0
        assert conn.execute('SELECT count(*) FROM learning_exposures WHERE project_id=%s AND plan_id=%s',
                            (project, old['plan_id'])).fetchone()[0] == 1
        submission = conn.execute("SELECT detail FROM ai_run_events WHERE run_id=%s AND status='submission'",
                                  (run['run_id'],)).fetchone()[0]
        assert submission['initial']['route_change']['base_plan_id'] == old['plan_id']
        assert 'route_change_hash' in submission['manifest']
    fresh = build_container(container.settings)
    token = client.cookies.get(container.settings.session_cookie_name)
    with TestClient(create_app(fresh)) as restored:
        restored.cookies.set(fresh.settings.session_cookie_name, token)
        assert restored.get(preview_url, params=params).json()['status'] == 'approved'


def test_changed_basis_before_dispatch_fails_without_model_or_automatic_retry(generated_route):
    _, container, client, params, headers, old = generated_route
    calls = len(container.plan_service._llm.calls)
    queued = client.post('/api/v1/plan-changes/generate', params=params, headers=headers,
                json=dict(plan_id=old['plan_id'], expected_version=old['version'],
                          operation='regenerate_future_plan', idempotency_key='stale'))
    assert queued.status_code == 202, queued.text
    stage = old['stages'][0]
    unit = next(x['unit_id'] for x in old['unit_links'] if x['stage_id'] == stage['stage_id'])
    started = client.put('/api/v1/exposures', params=params, headers=headers, json=dict(plan_id=old['plan_id'],
               stage_id=stage['stage_id'], unit_id=unit, status='in_progress', expected_version=0, idempotency_key='later'))
    assert started.status_code == 200, started.text
    assert container.planning_worker.tick()
    run = client.get(queued.json()['status_url']).json()
    assert run['status'] == 'failed'
    assert len(container.plan_service._llm.calls) == calls
    assert not container.planning_worker.tick()
    assert client.get('/api/v1/plans/current', params=params).json()['plan_id'] == old['plan_id']


def test_change_goal_freezes_pack_and_context_without_exporting_private_body(generated_route):
    import json
    from copy import deepcopy

    db, container, client, params, headers, old = generated_route
    project = params['project_id']
    same_goal = client.post('/api/v1/plan-changes/generate', params=params, headers=headers,
        json=dict(plan_id=old['plan_id'], expected_version=old['version'], operation='change_goal',
                  idempotency_key='no-change', goal=old['goal_snapshot'], goal_spec=old['goal_spec']))
    assert same_goal.status_code == 400, same_goal.text
    unsupported = client.post('/api/v1/plan-changes/generate', params=params, headers=headers,
        json=dict(plan_id=old['plan_id'], expected_version=old['version'], operation='change_goal',
                  idempotency_key='unknown-template', goal='gardening and tomatoes'))
    assert unsupported.status_code == 409, unsupported.text
    scope = container.browser_auth.resolve(client.cookies.get(container.settings.session_cookie_name))
    stage = old['stages'][0]
    unit = next(x['unit_id'] for x in old['unit_links'] if x['stage_id'] == stage['stage_id'])
    PgLearningResources(db.app_dsn).select(scope, dict(project_id=project, plan_id=old['plan_id'],
                stage_id=stage['stage_id'], unit_id=unit), dict(resource_id='private-' + project, project_id=project,
                url='https://example.com/private-route-fixture', title='PRIVATE_BODY_NEVER_SEND', media_type='text',
                language='en', provenance='user_provided', verification_status='unverified', source_version=9))
    captured = []
    for purpose, handler in list(container.plan_service._llm._handlers.items()):
        def spy(p, payload, handler=handler):
            captured.append(deepcopy(payload))
            return handler(p, payload)
        container.plan_service._llm.register(purpose, spy)
    body = dict(plan_id=old['plan_id'], expected_version=old['version'], operation='change_goal',
                idempotency_key='new-goal', goal='Agent作品集',
                goal_spec={'target': 'Agent', 'outcome_purpose': 'portfolio'})
    queued = client.post('/api/v1/plan-changes/generate', params=params, headers=headers, json=body)
    assert queued.status_code == 202, queued.text
    assert client.post('/api/v1/plan-changes/generate', params=params, json=body).status_code == 403
    assert client.post('/api/v1/plan-changes/generate', params=params, headers=headers,
                       json={**body, 'actor_id': 'spoof'}).status_code == 422
    assert client.post('/api/v1/plan-changes/generate', params={'project_id': 'other'}, headers=headers,
                       json=body).status_code == 403
    # A later published version does not change the queued model contract or route.
    pack = load_pack('agent-application-v5.json')
    with psycopg.connect(db.migrator_dsn) as conn:
        seed_reviewed_pack(conn, pack)
    assert container.planning_worker.tick()
    run = client.get(queued.json()['status_url']).json()
    assert run['status'] == 'succeeded', run
    url = '/api/v1/plan-changes/' + run['result_ref']
    preview = client.get(url, params=params).json()
    assert preview['draft']['goal_snapshot'] == body['goal']
    assert preview['before_goal'] == old['goal_snapshot'] and preview['after_goal'] == body['goal']
    assert preview['retained_stage_keys'] == [] and preview['draft']['source_pack_version'] == 4
    outgoing = json.dumps(captured, ensure_ascii=False)
    assert 'PRIVATE_BODY_NEVER_SEND' not in outgoing and 'private-route-fixture' not in outgoing
    assert old['plan_id'] not in outgoing
    assert 'node_reuse' not in outgoing and 'before_stages' not in outgoing
    decision = dict(expected_version=old['version'], preview_hash=preview['preview_hash'],
                    idempotency_key='portfolio-confirm', acknowledge_reset=True)
    result = client.post(url + '/confirm', params=params, headers=headers, json=decision)
    assert result.status_code == 200, result.text
    newer = client.get('/api/v1/plans/current', params=params).json()
    assert newer['goal_snapshot'] == body['goal'] and newer['goal_spec']['outcome_purpose'] == 'portfolio'
    with psycopg.connect(db.migrator_dsn) as conn:
        assert conn.execute('SELECT count(*) FROM learning_resource_selections WHERE project_id=%s AND plan_id=%s',
                             (project, newer['plan_id'])).fetchone()[0] == 0
        assert conn.execute('SELECT count(*) FROM learning_resource_selections WHERE project_id=%s AND plan_id=%s',
                             (project, old['plan_id'])).fetchone()[0] == 1


def test_unknown_generated_run_is_never_replayed_and_new_request_is_blocked(generated_route):
    _, container, client, params, headers, old = generated_route
    invocations = []
    def unknown(**kwargs):
        invocations.append(kwargs['run_id'])
        raise LLMDispatchUnknownError('owned Fake unknown, no real dispatch')
    container.plan_service._llm.generate_structured = unknown
    body = dict(plan_id=old['plan_id'], expected_version=old['version'], operation='regenerate_future_plan',
                idempotency_key='unknown-fixture')
    url = '/api/v1/plan-changes/generate'
    queued = client.post(url, params=params, headers=headers, json=body)
    assert queued.status_code == 202
    assert container.planning_worker.tick()
    run = client.get(queued.json()['status_url']).json()
    assert run['status'] == 'reconciliation_required' and run['next_action'] == 'reconcile'
    assert client.post(url, params=params, headers=headers, json=body).json() == queued.json()
    assert not container.planning_worker.tick()
    assert client.post(url, params=params, headers=headers, json={**body, 'idempotency_key': 'new'}).status_code == 409
    assert len(invocations) == 1
