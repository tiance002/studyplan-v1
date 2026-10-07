from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace

import psycopg
import pytest
from app.core.errors import AppError
from app.core.ids import new_id
from app.domain.enums import OutlineSectionKind, UnitProgress
from app.domain.learning_exposures import ExposureCommand
from app.domain.plan_changes import PlanChangeCommand
from app.domain.planning.models import PlanDraft, PlanPublicationService, PlanStage, PlanUnitLink
from app.infrastructure.db.learning_exposures import PgLearningExposures
from app.infrastructure.db.learning_resources import PgLearningResources
from app.infrastructure.db.plan_changes import PgPlanChanges
from app.infrastructure.db.plan_repository import PgPlanRepository
from app.main import create_app
from app.tools.seed_b3 import seed_reviewed_pack
from fastapi.testclient import TestClient

from tests.integration.test_resource_changes_pg import migrated_db as migrated_db
from tests.integration.test_resource_changes_pg import scenario as scenario

pytestmark = pytest.mark.postgres


@pytest.fixture
def route_scenario(scenario):
    db, scope, resource, container, old = scenario
    keys = ('a', 'b', 'c', 'final')
    stages = tuple(PlanStage.create(stable_key=k, title=k, section_kind=OutlineSectionKind.CORE,
                                   order_index=i) for i, k in enumerate(keys))
    pack = dict(pack_key='route.fixture', version=1, status='published', title='Isolated route fixture',
                supported_scope='Owned PG acceptance only', provenance='Synthetic test, not public evidence',
                stage_blueprints=[dict(stable_key=k, title=k, section_kind='core', objective='Validate route changes',
                                       inclusion='optional' if k == 'b' else 'required') for k in keys],
                knowledge_blueprints=[], required_node_keys=[], practice_blueprints=[], resources=[], resource_refs=[])
    links = [PlanUnitLink(stages[0].stage_id, old.unit_links[0].unit_id, 0)]
    with psycopg.connect(db.migrator_dsn) as conn:
        seed_reviewed_pack(conn, pack)
        for s in stages[1:]:
            unit = new_id('unt')
            conn.execute("INSERT INTO learning_units(unit_id,project_id,stable_key,title) VALUES(%s,%s,%s,%s)",
                         (unit, resource.project_id, 'unit.' + s.stable_key, s.title))
            links.append(PlanUnitLink(s.stage_id, unit, 0))
    draft = PlanDraft(new_id('drf'), resource.project_id, '', 'Finite route fixture', 2, stages=stages,
                      unit_links=tuple(links), source_pack_key=pack['pack_key'], source_pack_version=1)
    repo = PgPlanRepository(db.app_dsn)
    repo.save_draft(draft, expected_version=old.version)
    PlanPublicationService(repo).publish(draft=draft, presented_hash=draft.content_hash,
                                        expected_version=old.version, idempotency_key='route-initial')
    current = repo.get_current(project_id=resource.project_id)
    cmd = PlanChangeCommand(resource.project_id, current.plan_id, current.version, 'preview',
                            'reorder_future_stage', ('a', 'c', 'b', 'final'))
    return db, scope, cmd, container, current


def confirm(repo, scope, cmd, preview, key='confirm', **changes):
    return repo.decide(scope, cmd.project_id, preview['proposal_id'], 'confirm', cmd.expected_version,
                       preview['preview_hash'], key, **{'acknowledge_reset': True, **changes})


def test_preview_reload_atomic_publish_history_private_lineage_and_receipt(route_scenario):
    db, scope, cmd, _, current = route_scenario
    repo = PgPlanChanges(db.app_dsn)
    pos = dict(project_id=cmd.project_id, plan_id=cmd.plan_id, stage_id=current.stages[0].stage_id,
               unit_id=current.unit_links[0].unit_id)
    PgLearningExposures(db.app_dsn).change(scope, ExposureCommand(**pos, status=UnitProgress.IN_PROGRESS,
                                         expected_version=0, idempotency_key='start'))
    selected = PgLearningResources(db.app_dsn).select(scope, pos, dict(resource_id='private-' + cmd.project_id,
               project_id=cmd.project_id, url='https://docs.python.org/3/', title='Private fixture',
               media_type='text', language='en', provenance='user_provided', verification_status='unverified', source_version=9))
    preview = repo.preview(scope, cmd)
    assert repo.preview(scope, cmd) == preview
    assert PgPlanChanges(db.app_dsn).get(scope, cmd.project_id, preview['proposal_id']) == preview
    assert PgPlanRepository(db.app_dsn).get_current(project_id=cmd.project_id).plan_id == cmd.plan_id
    with pytest.raises(AppError) as missing_ack:
        confirm(repo, scope, cmd, preview, acknowledge_reset=False)
    assert missing_ack.value.http_status == 400
    result = confirm(repo, scope, cmd, preview)
    assert result['created'] and result['revision'] == current.revision + 1
    assert confirm(PgPlanChanges(db.app_dsn), scope, cmd, preview) == result
    assert repo.preview(scope, cmd) == result['preview']
    with pytest.raises(AppError) as heterogeneous:
        confirm(repo, scope, cmd, preview, acknowledge_reset=False)
    assert heterogeneous.value.http_status == 409
    newer = PgPlanRepository(db.app_dsn).get_current(project_id=cmd.project_id)
    assert [s.stable_key for s in newer.stages] == ['a', 'c', 'b', 'final']
    assert all(not x['recorded'] for x in PgLearningExposures(db.app_dsn).list(scope, cmd.project_id, newer.plan_id))
    assert len(PgLearningExposures(db.app_dsn).history(scope, **pos)) == 1
    with psycopg.connect(db.migrator_dsn) as conn:
        copied = conn.execute('SELECT resource_snapshot FROM learning_resource_selections WHERE project_id=%s AND plan_id=%s',
                              (cmd.project_id, newer.plan_id)).fetchone()[0]
        assert copied['selection_copy_lineage']['original_selection_id'] == selected['selection_id']
        assert copied['selection_copy_lineage']['original_source_version'] == 9
        assert conn.execute('SELECT count(*) FROM ai_runs WHERE project_id=%s', (cmd.project_id,)).fetchone()[0] == 0
        assert conn.execute('SELECT count(*) FROM plan_revisions WHERE project_id=%s', (cmd.project_id,)).fetchone()[0] == 3


def test_learning_change_after_preview_fences_confirm_and_started_prefix(route_scenario):
    db, scope, cmd, _, current = route_scenario
    repo = PgPlanChanges(db.app_dsn)
    preview = repo.preview(scope, cmd)
    stage = current.stages[1]
    unit = next(link.unit_id for link in current.unit_links if link.stage_id == stage.stage_id)
    PgLearningExposures(db.app_dsn).change(scope, ExposureCommand(cmd.project_id, cmd.plan_id, stage.stage_id,
         unit, UnitProgress.IN_PROGRESS, 0, 'start-future'))
    with pytest.raises(AppError) as changed:
        confirm(repo, scope, cmd, preview)
    assert changed.value.http_status == 409
    context = repo.context(scope, cmd.project_id)
    assert [s['locked'] for s in context['stages']] == [True, True, False, True]
    with pytest.raises(AppError):
        repo.preview(scope, replace(cmd, idempotency_key='new-preview'))
    assert PgPlanRepository(db.app_dsn).get_current(project_id=cmd.project_id).plan_id == cmd.plan_id
    cancelled = repo.decide(scope, cmd.project_id, preview['proposal_id'], 'cancel', cmd.expected_version,
                            preview['preview_hash'], 'cancel')
    assert cancelled['preview']['status'] == 'cancelled'
    assert repo.decide(scope, cmd.project_id, preview['proposal_id'], 'cancel', cmd.expected_version,
                       preview['preview_hash'], 'cancel') == cancelled


def test_generic_draft_writes_cannot_bypass_route_preview(route_scenario):
    db, scope, cmd, _, _ = route_scenario
    preview = PgPlanChanges(db.app_dsn).preview(scope, cmd)
    repo = PgPlanRepository(db.app_dsn)
    draft = preview['draft']
    for write in (lambda: repo.save_draft(draft, expected_hash=draft.content_hash),
                  lambda: repo.cancel_draft(project_id=cmd.project_id, draft_id=draft.draft_id),
                  lambda: PlanPublicationService(repo).publish(draft=draft, presented_hash=draft.content_hash,
                               expected_version=cmd.expected_version, idempotency_key='bypass')):
        with pytest.raises(AppError) as denied:
            write()
        assert denied.value.http_status == 409


def test_optional_removal_and_confirm_cancel_race(route_scenario):
    db, scope, cmd, _, current = route_scenario
    repo = PgPlanChanges(db.app_dsn)
    cmd = replace(cmd, operation='remove_optional_topic', stage_keys=(), stage_key='b')
    preview = repo.preview(scope, cmd)
    assert preview['after_stage_keys'] == ['a', 'c', 'final']
    def attempt(action):
        try:
            return repo.decide(scope, cmd.project_id, preview['proposal_id'], action, cmd.expected_version,
                               preview['preview_hash'], action, True)
        except AppError as exc:
            return exc
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, ['confirm', 'cancel']))
    assert sum(isinstance(r, dict) for r in results) == 1
    assert sum(isinstance(r, AppError) and r.http_status == 409 for r in results) == 1
    current_after = PgPlanRepository(db.app_dsn).get_current(project_id=cmd.project_id)
    if next(r for r in results if isinstance(r, dict))['created']:
        assert len(current_after.stages) == 3
    else:
        assert current_after.plan_id == current.plan_id


def test_failure_after_publication_rolls_back_entire_change(route_scenario, monkeypatch):
    from app.infrastructure.db import plan_changes
    db, scope, cmd, _, _ = route_scenario
    repo = PgPlanChanges(db.app_dsn)
    preview = repo.preview(scope, cmd)
    def fail(*_):
        raise RuntimeError('owned failure injection after publication')
    monkeypatch.setattr(plan_changes, 'copy_private_selections', fail)
    with pytest.raises(RuntimeError):
        confirm(repo, scope, cmd, preview)
    assert PgPlanRepository(db.app_dsn).get_current(project_id=cmd.project_id).plan_id == cmd.plan_id
    assert repo.get(scope, cmd.project_id, preview['proposal_id'])['status'] == 'awaiting_approval'
    with psycopg.connect(db.migrator_dsn) as conn:
        assert conn.execute('SELECT count(*) FROM plan_revisions WHERE project_id=%s', (cmd.project_id,)).fetchone()[0] == 2


def test_private_change_after_preview_is_not_silently_copied(route_scenario):
    db, scope, cmd, _, current = route_scenario
    repo = PgPlanChanges(db.app_dsn)
    preview = repo.preview(scope, cmd)
    pos = dict(project_id=cmd.project_id, plan_id=cmd.plan_id, stage_id=current.stages[0].stage_id,
               unit_id=current.unit_links[0].unit_id)
    PgLearningResources(db.app_dsn).select(scope, pos, dict(resource_id='private-' + cmd.project_id,
               project_id=cmd.project_id, url='https://docs.python.org/3/', title='Later selection',
               media_type='text', language='en', provenance='user_provided', verification_status='unverified'))
    with pytest.raises(AppError) as changed:
        confirm(repo, scope, cmd, preview)
    assert changed.value.http_status == 409


def test_real_http_csrf_auth_contract_restart_and_scope(route_scenario):
    db, scope, cmd, container, _ = route_scenario
    body = asdict(cmd)
    body.pop('project_id')
    params = {'project_id': cmd.project_id}
    base = '/api/v1/plan-changes'
    with TestClient(create_app(container)) as client:
        client.cookies.set(container.settings.session_cookie_name, container.browser_auth.issue(scope.actor_id))
        headers = {'X-CSRF-Token': client.get('/api/v1/session').json()['csrf_token']}
        assert client.get(base + '/context', params=params).status_code == 200
        assert client.post(base, params=params, json=body).status_code == 403
        assert client.post(base, params=params, headers=headers, json={**body, 'actor_id': 'spoof'}).status_code == 422
        response = client.post(base, params=params, headers=headers, json=body)
        assert response.status_code == 200, response.text
        preview = response.json()
        assert preview['draft']['draft_hash'] == preview['preview_hash']
        url = base + '/' + preview['proposal_id']
        assert client.get(url, params=params).json() == preview
        decision = dict(expected_version=cmd.expected_version, preview_hash=preview['preview_hash'],
                        idempotency_key='http-confirm', acknowledge_reset=True)
        response = client.post(url + '/confirm', params=params, headers=headers, json=decision)
        assert response.status_code == 200, response.text
        result = response.json()
        assert client.post(url + '/confirm', params=params, headers=headers, json=decision).json() == result
        assert client.get('/api/v1/plans/current', params=params).json()['plan_id'] == result['plan_id']
    from app.composition import build_container
    fresh = build_container(container.settings)
    with TestClient(create_app(fresh)) as client:
        client.cookies.set(fresh.settings.session_cookie_name, fresh.browser_auth.issue(scope.actor_id))
        assert client.get(url, params=params).json()['status'] == 'approved'
        assert client.get(url, params={'project_id': 'another'}).status_code == 403
    with TestClient(create_app(fresh)) as anonymous:
        assert anonymous.get(url, params=params).status_code == 401
