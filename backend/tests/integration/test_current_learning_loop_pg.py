"""Current learning loop: ordinary cookie auth, real owned PG/HTTP, Fake generation.

No real provider, legacy acceptance replay, production DB, or global role mutation.
"""
from dataclasses import replace

import psycopg
import pytest
from app.composition import build_container
from app.core.config import get_settings
from app.core.ids import new_id
from app.main import create_app
from app.tools.seed_b3 import seed_reviewed_pack
from fastapi.testclient import TestClient

from tests.integration.test_generated_plan_changes_pg import generated_route as generated_route
from tests.integration.test_generated_plan_changes_pg import migrated_db as migrated_db
from tests.unit.test_learning_guidance import guided_pack

pytestmark = pytest.mark.postgres


@pytest.fixture
def loop_container(migrated_db):
    pack = guided_pack()
    pack['version'] = 2  # controlled legacy acceptance, distinct from versions 3/4
    with psycopg.connect(migrated_db.migrator_dsn) as conn:
        seed_reviewed_pack(conn, pack)
    settings = replace(get_settings(), database_url=migrated_db.app_dsn, llm_provider='fake',
        local_session_token='', planning_worker_admission_mode='trusted_server',
        allow_origins=('http://127.0.0.1:5178',))
    container = build_container(settings)
    select = container.plan_service._domain_pack_selector
    container.plan_service._domain_pack_selector = lambda goal: pack if select(goal).get('pack_key') == pack['pack_key'] else select(goal)
    return container


def ok(response, status=200):
    assert response.status_code == status, response.text
    return response.json()


def generate(client, container, query, headers, key):
    current = client.get('/api/v1/plans/current', params=query)
    base = current.json()['version'] if current.status_code == 200 else 0
    queued = ok(client.post('/api/v1/plans/generate', params=query, headers=headers,
        json={'goal': 'Agent学习闭环' + key, 'goal_spec': {'target': 'Agent'}}), 202)
    assert container.planning_worker.tick()
    run = ok(client.get(queued['status_url']))
    assert (run['status'], run['next_action']) == ('succeeded', 'none')
    draft = ok(client.get('/api/v1/plans/drafts/' + run['result_ref'], params=query))
    plan = ok(client.post('/api/v1/plans/drafts/' + draft['draft_id'] + '/decision', params=query,
        headers=headers, json=dict(decision='approve', expected_version=base,
            draft_hash=draft['draft_hash'], idempotency_key=key)))['plan']
    return plan


def publish_e2_route(container, project):
    # E2 controlled Domain publication; browser E1 generates an unmodified route.
    from app.domain.planning.models import PlanDraft, PlanPublicationService
    from app.infrastructure.db.plan_repository import PgPlanRepository
    repo = PgPlanRepository(container.settings.database_url)
    old = repo.get_current(project_id=project)
    tool_id = next(s.stage_id for s in old.stages if s.stable_key == 'stage.tools')
    empty_id = next(s.stage_id for s in old.stages if s.stable_key == 'stage.environment')
    extra = next(t for t in old.task_links if t.stage_id == empty_id)
    links = tuple(replace(t, stage_id=tool_id) if t == extra else t for t in old.task_links)
    draft = PlanDraft(new_id('drf'), project, '', 'Controlled E2 boundary', old.revision+1,
        stages=old.stages, unit_links=old.unit_links, task_links=links,
        task_knowledge_links=old.task_knowledge_links, stage_resources=old.stage_resources,
        resource_snapshots=old.resource_snapshots)
    repo.save_draft(draft, expected_version=old.version)
    PlanPublicationService(repo).publish(draft=draft, presented_hash=draft.content_hash,
        expected_version=old.version, idempotency_key='e2-controlled-route')


def test_current_gate_raw_history_position_and_account_isolation(loop_container):
    container = loop_container
    with TestClient(create_app(container)) as client:
        auth = ok(client.post('/api/v1/auth/register', json=dict(username='闭环' + new_id('u')[-10:], password='Test-pass1!')))
        query, headers = dict(project_id=auth['project_ids'][0]), {'X-CSRF-Token': auth['csrf_token']}
        generate(client, container, query, headers, 'first')
        publish_e2_route(container, query['project_id'])
        plan = ok(client.get('/api/v1/plans/current', params=query))
        calls = len(container.plan_service._llm.calls)
        tools = next(s for s in plan['stages'] if s['stable_key'] == 'stage.tools')
        empty = next(s for s in plan['stages'] if s['stable_key'] == 'stage.environment')
        target = dict(plan_id=plan['plan_id'], stage_id=tools['stage_id'])
        def completion(stage_id):
            return next(s['completion'] for s in ok(client.get('/api/v1/workspace', params=query))['stages'] if s['stage']['stage_id'] == stage_id)
        assert completion(tools['stage_id'])['total_practice_tasks'] == 2
        unit = next(u['unit_id'] for u in plan['unit_links'] if u['stage_id'] == tools['stage_id'])
        ok(client.post('/api/v1/summaries', params=query, headers=headers, json={**target, 'unit_id': unit,
            'content': '旧单元总结不计阶段', 'expected_version': 0, 'idempotency_key': 'unit'}))
        assert not completion(tools['stage_id'])['summary_completed']
        blank = client.post('/api/v1/summaries', params=query, headers=headers,
            json={**target, 'content': ' \n\t　', 'expected_version': 0, 'idempotency_key': 'blank'})
        assert blank.status_code == 400
        tasks = [t for t in plan['task_links'] if t['stage_id'] == tools['stage_id']]
        originals = []
        for index, task in enumerate(tasks):
            position = {**target, 'task_id': task['task_id']}
            thread = ok(client.get('/api/v1/submissions', params={**query, **position}))
            body = {**position, 'note': '  成果🙂\n\t原文 ' + str(index), 'repo_url': None,
                'evidence': [dict(kind='external_report', label='观察', content='\n本机合成观察🙂\t ', source_url=None)],
                'artifact_kind': 'evaluation', 'parent_submission_id': None, 'expected_plan_version': thread['plan_version'],
                'expected_task_version': thread['task_version'], 'expected_version': thread['version'], 'idempotency_key': 'save-' + str(index)}
            saved = ok(client.post('/api/v1/submissions', params=query, headers=headers, json=body))
            item = saved['submission']
            manual = dict(conclusion='accepted', rationale='人工观察，平台未执行🙂',
                coverage=[dict(criterion_index=i, evidence_indices=[0], observation=' 实际观察\n🙂 ')
                    for i in range(len(item['task_snapshot']['task']['acceptance']))], acknowledge_verification_limit=True,
                expected_plan_version=thread['plan_version'], expected_task_version=saved['thread']['task_version'],
                expected_version=saved['thread']['version'], idempotency_key='accept-' + str(index))
            accepted = ok(client.post('/api/v1/submissions/' + item['submission_id'] + '/decision', params=query, headers=headers, json=manual))
            assert accepted['task_status'] == 'accepted'
            originals.append((body, item, manual))
            assert completion(tools['stage_id'])['status'] == 'incomplete'  # all tasks without stage summary
        versions = []
        for version, raw in enumerate(('  第一版🙂\n\t ', '  第二版漢字🙂\n行二\t ')):
            body = {**target, 'content': raw, 'expected_version': version, 'idempotency_key': 'summary-' + str(version)}
            result = ok(client.post('/api/v1/summaries', params=query, headers=headers, json=body))
            assert result['attempt']['content'] == raw
            replay = ok(client.post('/api/v1/summaries', params=query, headers=headers, json=body))
            assert replay['replayed'] and replay['attempt'] == result['attempt']
            versions.append((body, result['attempt']))
        assert completion(tools['stage_id'])['status'] == 'completed'
        ok(client.post('/api/v1/summaries', params=query, headers=headers, json=dict(plan_id=plan['plan_id'],
            stage_id=empty['stage_id'], content='无实践总结🙂\n ', expected_version=0, idempotency_key='empty')))
        assert completion(empty['stage_id']) == dict(status='completed', summary_completed=True, completed_practice_tasks=0, total_practice_tasks=0)
        other = ok(client.post('/api/v1/auth/register', json=dict(username='隔离' + new_id('u')[-10:], password='Test-pass1!')))
        bh = {'X-CSRF-Token': other['csrf_token']}
        for scope in (query, dict(project_id=other['project_ids'][0])):
            for path in ('/api/v1/summaries/attempts/' + versions[0][1]['attempt_id'], '/api/v1/submissions/' + originals[0][1]['submission_id']):
                denied = client.get(path, params=scope)
                assert denied.status_code in (403, 404)
                assert '第一版' not in denied.text and '成果🙂' not in denied.text
            assert client.post('/api/v1/summaries', params=scope, headers=bh, json=versions[0][0]).status_code in (403, 404)
            assert client.post('/api/v1/submissions', params=scope, headers=bh, json=originals[0][0]).status_code in (403, 404)
        login = ok(client.post('/api/v1/auth/login', json=dict(username=auth['username'], password='Test-pass1!')))
        headers = {'X-CSRF-Token': login['csrf_token']}
        for body, original in versions:
            assert ok(client.get('/api/v1/summaries/attempts/' + original['attempt_id'], params=query))['content'] == body['content']
        for body, original, _ in originals:
            detail = ok(client.get('/api/v1/submissions/' + original['submission_id'], params=query))
            assert detail['note'] == body['note'] and detail['task_snapshot'] == original['task_snapshot']
        assert len(container.plan_service._llm.calls) == calls
        newer = generate(client, container, query, headers, 'second')
        assert newer['plan_id'] != plan['plan_id']
        assert all(s['completion']['status'] == 'incomplete' for s in ok(client.get('/api/v1/workspace', params=query))['stages'])
        assert len(ok(client.get('/api/v1/summaries/history', params=query))['items']) >= 4


def test_summary_plus_one_of_two_tasks_and_foreign_stage_is_incomplete(generated_route):
    _, container, client, query, headers, _ = generated_route
    publish_e2_route(container, query['project_id'])
    plan = ok(client.get('/api/v1/plans/current', params=query))
    tools = next(s for s in plan['stages'] if s['stable_key'] == 'stage.tools')
    target = dict(plan_id=plan['plan_id'], stage_id=tools['stage_id'])
    ok(client.post('/api/v1/summaries', params=query, headers=headers,
        json={**target, 'content': '只有阶段总结🙂\n ', 'expected_version': 0, 'idempotency_key': 'only-summary'}))
    def gate():
        return next(s['completion'] for s in ok(client.get('/api/v1/workspace', params=query))['stages'] if s['stage']['stage_id'] == tools['stage_id'])
    assert gate() == dict(status='incomplete', summary_completed=True, completed_practice_tasks=0, total_practice_tasks=2)
    # Accepted evidence from a different current stage does not count here.
    foreign = next(t for t in plan['task_links'] if t['stage_id'] != tools['stage_id'])
    owned = [t for t in plan['task_links'] if t['stage_id'] == tools['stage_id']]
    for index, task in enumerate([foreign, *owned]):
        pos = dict(plan_id=plan['plan_id'], stage_id=task['stage_id'], task_id=task['task_id'])
        thread = ok(client.get('/api/v1/submissions', params={**query, **pos}))
        saved = ok(client.post('/api/v1/submissions', params=query, headers=headers,
            json={**pos, 'note': '人工边界观察', 'repo_url': None, 'evidence': [dict(kind='external_report', label='报告', content='合成观察', source_url=None)],
                'artifact_kind': 'evaluation', 'parent_submission_id': None, 'expected_plan_version': thread['plan_version'],
                'expected_task_version': thread['task_version'], 'expected_version': thread['version'], 'idempotency_key': 'gate-save-'+str(index)}))
        ok(client.post('/api/v1/submissions/'+saved['submission']['submission_id']+'/decision', params=query, headers=headers,
            json=dict(conclusion='accepted', rationale='人工检查，平台未执行',
                coverage=[dict(criterion_index=i, evidence_indices=[0], observation='观察') for i in range(len(saved['submission']['task_snapshot']['task']['acceptance']))],
                acknowledge_verification_limit=True, expected_plan_version=thread['plan_version'], expected_task_version=saved['thread']['task_version'],
                expected_version=saved['thread']['version'], idempotency_key='gate-accept-'+str(index))))
        assert gate()['completed_practice_tasks'] == max(0, index)
        assert gate()['status'] == ('completed' if index == 2 else 'incomplete')


def test_current_learning_loop_browser(loop_container):
    run_owned_browser(loop_container)


def test_controlled_two_task_and_no_task_browser(loop_container):
    import json
    with TestClient(create_app(loop_container)) as client:
        auth = ok(client.post('/api/v1/auth/register', json=dict(username='边界'+new_id('u')[-10:], password='Test-pass1!')))
        query, headers = dict(project_id=auth['project_ids'][0]), {'X-CSRF-Token': auth['csrf_token']}
        generate(client, loop_container, query, headers, 'e2-browser')
        publish_e2_route(loop_container, query['project_id'])
        plan = ok(client.get('/api/v1/plans/current', params=query))
    run_owned_browser(loop_container, dict(STUDYPLAN_CURRENT_LOOP_MODE='e2',
        STUDYPLAN_CURRENT_LOOP_USER=auth['username'], STUDYPLAN_CURRENT_LOOP_PLAN=json.dumps(plan)))


def run_owned_browser(loop_container, extra_env=None):
    import os
    import socket
    import subprocess
    import threading
    import time
    from pathlib import Path

    import uvicorn
    if os.environ.get('STUDYPLAN_CURRENT_LOOP_BROWSER') != '1':
        pytest.skip('owned Chrome acceptance enabled explicitly')
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    server = uvicorn.Server(uvicorn.Config(create_app(loop_container), log_level='error'))
    thread = threading.Thread(target=server.run, kwargs={'sockets': [sock]}, daemon=True)
    stop, errors = threading.Event(), []
    def work():
        while not stop.is_set():
            try:
                loop_container.planning_worker.tick()
            except Exception as exc:
                errors.append(repr(exc))
                return
            stop.wait(.1)
    worker = threading.Thread(target=work, daemon=True)
    thread.start()
    worker.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started and time.monotonic() < deadline:
            time.sleep(.05)
        assert server.started
        env = dict(os.environ, STUDYPLAN_CURRENT_LOOP_API=f'http://127.0.0.1:{sock.getsockname()[1]}', **(extra_env or {}))
        result = subprocess.run(['node', 'frontend/tests/current-learning-loop-pg.browser.cjs'],
            cwd=Path(__file__).resolve().parents[3], env=env, capture_output=True, text=True, encoding='utf-8', timeout=180)
        assert result.returncode == 0, result.stdout + result.stderr
        assert not errors
        assert len({run for run, _, _ in loop_container.plan_service._llm.calls}) == 1
    finally:
        stop.set()
        worker.join(10)
        server.should_exit = True
        thread.join(10)
        sock.close()
