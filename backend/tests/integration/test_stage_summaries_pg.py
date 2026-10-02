"""Stage summaries against the existing isolated PostgreSQL harness, no external calls."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import psycopg
import pytest
from app.api.v1.summary_schemas import SummarySaveView
from app.core.errors import AppError
from app.domain.summaries import SummarySaveCommand
from app.infrastructure.db.summaries import PgSummaries

from tests.e2e.test_b2v_http_end_to_end import migrated_db as migrated_db
from tests.integration.test_resource_changes_pg import scenario as scenario

pytestmark = pytest.mark.postgres


def command(scenario, **changes):
    _, _, target, _, _ = scenario
    return replace(SummarySaveCommand(target.project_id, target.plan_id, target.stage_id, None,
        ' \n阶段原文🙂\t ', 0, 'stage-save'), **changes)


def test_stage_exact_save_scope_snapshot_cas_receipt_and_no_progress(scenario):
    db, scope, _, _, current = scenario
    repo = PgSummaries(db.app_dsn)
    cmd = command(scenario)
    assert repo.thread(scope, *cmd.position)['version'] == 0
    result = repo.save(scope, cmd)
    SummarySaveView.model_validate(result)
    assert result['attempt']['content'] == cmd.content
    assert result['attempt']['unit_id'] is None
    snapshot = result['attempt']['rubric_snapshot']
    assert snapshot['summary_scope'] == 'stage'
    assert snapshot['stage_title'] == current.stages[0].title
    assert [u['unit_id'] for u in snapshot['unit_snapshots']] == [current.unit_links[0].unit_id]
    assert len(snapshot['node_snapshot']) == 1
    assert snapshot['source_snapshot']['public_assignments']
    assert len(result['thread']['questions']) == 3
    assert '阶段' in result['thread']['questions'][2]
    assert repo.save(scope, cmd) == dict(result, replayed=True)
    for changed in (dict(content='different'), dict(idempotency_key='stale')):
        with pytest.raises(AppError) as error:
            repo.save(scope, replace(cmd, **changed))
        assert error.value.http_status == 409
    with psycopg.connect(db.migrator_dsn) as conn:
        for table in ('ai_runs', 'learning_exposures', 'unit_progress'):
            assert conn.execute(f'SELECT count(*) FROM {table} WHERE project_id=%s', (cmd.project_id,)).fetchone()[0] == 0


def test_stage_concurrent_saves_one_winner(scenario):
    db, scope, *_ = scenario
    repo = PgSummaries(db.app_dsn)
    def save(key):
        try:
            return repo.save(scope, command(scenario, idempotency_key=key))['thread']['version']
        except AppError as error:
            return error.http_status
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(save, ['race-a', 'race-b'])) == [1, 409]


def test_stage_and_unit_history_coexist_and_owner_or_foreign_stage_denied(scenario):
    db, scope, _, _, current = scenario
    repo = PgSummaries(db.app_dsn)
    cmd = command(scenario)
    stage = repo.save(scope, cmd)['attempt']
    unit = repo.save(scope, replace(cmd, unit_id=current.unit_links[0].unit_id, idempotency_key='unit'))['attempt']
    assert {a['attempt_id'] for a in repo.history(scope, cmd.project_id)['items']} == {stage['attempt_id'], unit['attempt_id']}
    assert repo.thread(scope, *cmd.position)['attempts'] == [stage]
    assert repo.thread(scope, *replace(cmd, unit_id=unit['unit_id']).position)['attempts'] == [unit]
    for call in (lambda: repo.thread(scope, cmd.project_id, cmd.plan_id, 'foreign-stage'),
                 lambda: repo.save(scope, replace(cmd, stage_id='foreign-stage', idempotency_key='foreign'))):
        with pytest.raises(AppError) as error:
            call()
        assert error.value.http_status == 404
    forged = replace(scope, actor_id='forged')
    with pytest.raises(AppError) as error:
        repo.thread(forged, *cmd.position)
    assert error.value.http_status == 403
    with psycopg.connect(db.app_dsn) as conn:
        conn.execute("SELECT set_config('app.actor_id','forged',true),set_config('app.project_id',%s,true)", (cmd.project_id,))
        assert conn.execute('SELECT * FROM summary_stage_heads WHERE project_id=%s', (cmd.project_id,)).fetchall() == []
    with psycopg.connect(db.migrator_dsn) as conn:
        conn.execute("UPDATE learning_units SET title='later unit' WHERE unit_id=%s", (unit['unit_id'],))
    assert repo.attempt(scope, cmd.project_id, stage['attempt_id'])['rubric_snapshot'] == stage['rubric_snapshot']
    with pytest.raises(psycopg.errors.RaiseException):
        with psycopg.connect(db.migrator_dsn) as conn:
            conn.execute("UPDATE summary_attempts SET content='rewritten' WHERE attempt_id=%s", (stage['attempt_id'],))


def publish_next(scenario, *, empty=False):
    from app.core.ids import new_id
    from app.domain.planning.models import PlanDraft, PlanPublicationService
    from app.infrastructure.db.plan_repository import PgPlanRepository
    db, _, target, _, current = scenario
    draft = PlanDraft(new_id('drf'), target.project_id, '', 'Next plan', 1, stages=current.stages,
        unit_links=() if empty else current.unit_links,
        stage_resources=() if empty else current.stage_resources,
        resource_snapshots=() if empty else current.resource_snapshots)
    plans = PgPlanRepository(db.app_dsn)
    plans.save_draft(draft, expected_version=1)
    PlanPublicationService(plans).publish(draft=draft, presented_hash=draft.content_hash, expected_version=1,
        idempotency_key='next-stage-plan')
    return plans.get_current(project_id=target.project_id)


def test_empty_stage_valid_new_plan_preserves_old_history_and_cas(scenario):
    db, scope, *_ = scenario
    repo = PgSummaries(db.app_dsn)
    old = command(scenario)
    original = repo.save(scope, old)['attempt']
    newer = publish_next(scenario, empty=True)
    new = replace(old, plan_id=newer.plan_id, stage_id=newer.stages[0].stage_id, idempotency_key='empty')
    assert repo.thread(scope, *new.position)['version'] == 0
    saved = repo.save(scope, new)['attempt']
    assert saved['rubric_snapshot']['unit_snapshots'] == []
    assert saved['rubric_snapshot']['node_snapshot'] == []
    assert saved['rubric_snapshot']['source_snapshot']['public_assignments'] == []
    assert repo.thread(scope, *old.position)['attempts'] == [original]
    assert repo.save(scope, old)['replayed']
    with pytest.raises(AppError) as error:
        repo.save(scope, replace(old, expected_version=1, idempotency_key='old-new-save'))
    assert error.value.http_status == 409


def test_multi_unit_stage_snapshots_order_and_deduplicate_requirements(scenario):
    from psycopg.types.json import Jsonb
    db, scope, _, _, current = scenario
    cmd = command(scenario)
    first_unit = current.unit_links[0].unit_id
    second_unit = 'second-' + cmd.project_id
    with psycopg.connect(db.migrator_dsn) as conn:
        conn.execute('UPDATE learning_units SET objectives=%s,rubric=%s WHERE unit_id=%s',
            (Jsonb(['shared', 'first']), Jsonb({'criterion': 'shared'}), first_unit))
        conn.execute("INSERT INTO learning_units(unit_id,project_id,stable_key,title,objectives,rubric) VALUES(%s,%s,'second','Second',%s,%s)",
            (second_unit, cmd.project_id, Jsonb(['shared', 'second']), Jsonb({'criterion': 'shared'})))
        node = conn.execute('SELECT node_id FROM unit_node_links WHERE unit_id=%s', (first_unit,)).fetchone()[0]
        conn.execute("INSERT INTO unit_node_links(link_id,project_id,unit_id,node_id,order_index,role) VALUES(%s,%s,%s,%s,0,'primary')",
            ('second-link-' + cmd.project_id, cmd.project_id, second_unit, node))
        conn.execute('INSERT INTO plan_unit_links(link_id,project_id,plan_id,stage_id,unit_id,order_index) VALUES(%s,%s,%s,%s,%s,1)',
            ('second-plan-link-' + cmd.project_id, *cmd.position[:3], second_unit))
    snapshot = PgSummaries(db.app_dsn).save(scope, cmd)['attempt']['rubric_snapshot']
    assert [u['unit_id'] for u in snapshot['unit_snapshots']] == [first_unit, second_unit]
    assert snapshot['objectives'] == ['shared', 'first', 'second']
    assert snapshot['rubric'] == [{'criterion': 'shared'}]
    assert len(snapshot['node_snapshot']) == 1


@pytest.mark.parametrize('stage_scope', [True, False])
def test_stage_and_unit_feedback_use_existing_pipeline_offline_only(scenario, stage_scope):
    from app.application.model_binding import SubmissionBinding
    from app.application.planning_budget import BudgetPolicy
    from app.application.summaries import SummaryService
    from app.domain.summaries import summary_manifest
    from app.infrastructure.db.job_repository import PgPlanningJobRepository

    from tests.integration.test_summaries_pg import OfflineProvider, resolver
    db, scope, _, _, current = scenario
    repo = PgSummaries(db.app_dsn)
    cmd = command(scenario, unit_id=None if stage_scope else current.unit_links[0].unit_id)
    attempt = repo.save(scope, cmd)['attempt']
    binding = SubmissionBinding('test:1', BudgetPolicy(20, 20, 20, 20, 20, 20))
    handle = repo.enqueue_review(scope, cmd.project_id, attempt['attempt_id'], 'review', summary_manifest(binding))
    claim = PgPlanningJobRepository(db.app_dsn, admission_mode='trusted_server').claim_next('stage-test', 30)
    assert claim.run_id == handle['run_id']
    provider = OfflineProvider()
    SummaryService(repo, provider_resolver=resolver(db, provider)).execute_review(claim.project_id, claim.run_id,
        guard=lambda: None, claim=claim)
    reviewed = repo.attempt(scope, cmd.project_id, attempt['attempt_id'])
    assert reviewed['review']['conclusion'] == 'needs_revision'
    assert reviewed['content'] == cmd.content
    assert provider.calls == 1
    if stage_scope:
        assert provider.payloads[0]['rubric_snapshot']['summary_scope'] == 'stage'
    assert 'source_snapshot' not in provider.payloads[0]['rubric_snapshot']
    with psycopg.connect(db.migrator_dsn) as conn:
        assert conn.execute('SELECT count(*) FROM learning_exposures WHERE project_id=%s', (cmd.project_id,)).fetchone()[0] == 0


def test_stage_http_omitted_unit_is_stage_scope(scenario):
    from app.main import create_app
    from fastapi.testclient import TestClient

    from tests.integration.test_summary_http_pg import login
    db, scope, target, container, _ = scenario
    query = dict(project_id=target.project_id, plan_id=target.plan_id, stage_id=target.stage_id)
    with TestClient(create_app(container)) as client:
        headers = login(client, db, scope)
        assert client.get('/api/v1/summaries', params=query).json()['unit_id'] is None
        body = dict(plan_id=target.plan_id, stage_id=target.stage_id, content=' stage raw ', expected_version=0, idempotency_key='http-stage')
        result = client.post('/api/v1/summaries', params=dict(project_id=target.project_id), json=body, headers=headers)
        assert result.status_code == 200
        assert result.json()['attempt']['unit_id'] is None
        assert result.json()['attempt']['content'] == body['content']


def test_stage_schema_guards_unique_scope_rls_and_downgrade(scenario):
    from tests.e2e.test_b2v_http_end_to_end import _run_alembic
    db, scope, *_ = scenario
    cmd = command(scenario)
    repo = PgSummaries(db.app_dsn)
    repo.save(scope, cmd)
    with psycopg.connect(db.migrator_dsn) as conn:
        assert conn.execute("SELECT relrowsecurity,relforcerowsecurity FROM pg_class WHERE relname='summary_stage_heads'").fetchone() == (True, True)
    with pytest.raises(psycopg.errors.UniqueViolation):
        with psycopg.connect(db.migrator_dsn) as conn:
            conn.execute("""INSERT INTO summary_attempts(attempt_id,project_id,unit_id,content,attempt_no,rubric_version,plan_id,stage_id,version)
                VALUES(%s,%s,NULL,'duplicate',99,1,%s,%s,1)""", ('duplicate-' + cmd.project_id, *cmd.position[:3]))
    with pytest.raises(psycopg.errors.CheckViolation):
        with psycopg.connect(db.migrator_dsn) as conn:
            conn.execute("INSERT INTO summary_attempts(attempt_id,project_id,unit_id,content,attempt_no,rubric_version) VALUES(%s,%s,NULL,'no stage',1,1)",
                ('invalid-' + cmd.project_id, cmd.project_id))
    result = _run_alembic(db, 'downgrade', '0022')
    assert result.returncode != 0
    assert 'Stage summary history exists; refuse destructive downgrade' in result.stderr
    assert repo.thread(scope, *cmd.position)['version'] == 1
