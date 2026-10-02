"""Read-only automatic stage completion on isolated PostgreSQL and real HTTP."""
from dataclasses import replace

import psycopg
import pytest
from app.core.errors import AppError
from app.domain.summaries import SummarySaveCommand
from app.infrastructure.db.summaries import PgSummaries
from app.infrastructure.db.workspace import PgWorkspaceReader
from app.main import create_app
from fastapi.testclient import TestClient

from tests.e2e.test_b2v_http_end_to_end import migrated_db as migrated_db  # noqa: F401
from tests.integration.test_practice_submissions_pg import decision, repository
from tests.integration.test_practice_submissions_pg import (
    submission_scenario as submission_scenario,  # noqa: F401
)
from tests.integration.test_prompts_pg import prompt_scenario as prompt_scenario  # noqa: F401
from tests.integration.test_prompts_pg import resource_scenario as resource_scenario  # noqa: F401
from tests.integration.test_summary_http_pg import login

pytestmark = pytest.mark.postgres


def read(db, scope, command, plan):
    return PgWorkspaceReader(db.app_dsn).read(scope, command.project_id,
        [u.unit_id for u in plan.unit_links], [t.task_id for t in plan.task_links], plan_id=command.plan_id)


def summary(db, scope, command, **changes):
    cmd = SummarySaveCommand(command.project_id, command.plan_id, command.stage_id, None, ' Stage summary ', 0, 'completion-summary')
    return PgSummaries(db.app_dsn).save(scope, replace(cmd, **changes))


def test_current_plan_position_completion_inputs_exclude_unit_summaries_and_saved_evidence(submission_scenario):
    db, scope, cmd, _, plan = submission_scenario
    data = read(db, scope, cmd, plan)
    assert data['summary_stage_ids'] == set()
    assert data['accepted_task_positions'] == set()
    summary(db, scope, cmd, unit_id=plan.unit_links[0].unit_id)
    assert read(db, scope, cmd, plan)['summary_stage_ids'] == set()
    saved = repository(db).save(scope, cmd)
    assert read(db, scope, cmd, plan)['accepted_task_positions'] == set()
    repository(db).decide(scope, decision(cmd, saved))
    data = read(db, scope, cmd, plan)
    assert data['accepted_task_positions'] == {(cmd.stage_id, cmd.task_id)}
    assert data['summary_stage_ids'] == set()
    summary(db, scope, cmd, idempotency_key='stage')
    assert read(db, scope, cmd, plan)['summary_stage_ids'] == {cmd.stage_id}


def test_http_summary_and_manual_acceptance_automatically_complete_stage(submission_scenario):
    from tests.integration.test_submission_http_pg import body
    db, scope, cmd, container, _ = submission_scenario
    query = dict(project_id=cmd.project_id)
    with TestClient(create_app(container)) as client:
        headers = login(client, db, scope)
        def completion():
            response = client.get('/api/v1/workspace', params=query)
            assert response.status_code == 200
            result = response.json()
            return result, result['stages'][0]['completion']
        result, stage = completion()
        assert result['total_stages'] == 1 and result['completed_stages'] == 0
        assert stage == dict(status='incomplete', summary_completed=False, completed_practice_tasks=0, total_practice_tasks=1)
        summary(db, scope, cmd)
        assert completion()[1]['summary_completed']
        assert completion()[1]['status'] == 'incomplete'
        saved = client.post('/api/v1/submissions', params=query, headers=headers, json=body(cmd))
        assert saved.status_code == 200
        assert completion()[1]['status'] == 'incomplete'
        manual = body(decision(cmd, saved.json()))
        manual.pop('submission_id')
        accepted = client.post('/api/v1/submissions/' + saved.json()['submission']['submission_id'] + '/decision',
            params=query, headers=headers, json=manual)
        assert accepted.status_code == 200
        result, stage = completion()
        assert result['completed_stages'] == 1
        assert stage == dict(status='completed', summary_completed=True, completed_practice_tasks=1, total_practice_tasks=1)
        assert result['completed_units'] == 0
    with psycopg.connect(db.migrator_dsn) as conn:
        for table in ('unit_progress', 'learning_exposures', 'ai_runs'):
            assert conn.execute(f'SELECT count(*) FROM {table} WHERE project_id=%s', (cmd.project_id,)).fetchone()[0] == 0


def test_owner_scope_denies_forged_completion_reads(submission_scenario):
    db, scope, cmd, _, plan = submission_scenario
    summary(db, scope, cmd)
    with pytest.raises(AppError) as error:
        read(db, replace(scope, actor_id='forged'), cmd, plan)
    assert error.value.http_status == 403
    other = replace(cmd, plan_id='foreign-plan')
    data = read(db, scope, other, plan)
    assert data['summary_stage_ids'] == set() and data['accepted_task_positions'] == set()


def test_same_task_global_accepted_does_not_complete_new_plan_position(submission_scenario):
    from app.core.ids import new_id
    from app.domain.planning.models import PlanDraft, PlanPublicationService
    from app.infrastructure.db.plan_repository import PgPlanRepository
    db, scope, cmd, container, old = submission_scenario
    repo = repository(db)
    saved = repo.save(scope, cmd)
    repo.decide(scope, decision(cmd, saved))
    summary(db, scope, cmd)
    plans = PgPlanRepository(db.app_dsn)
    draft = PlanDraft(new_id('drf'), cmd.project_id, '', 'New position', 1, stages=old.stages,
        unit_links=old.unit_links, task_links=old.task_links, task_knowledge_links=old.task_knowledge_links,
        stage_resources=old.stage_resources, resource_snapshots=old.resource_snapshots)
    plans.save_draft(draft, expected_version=old.version)
    PlanPublicationService(plans).publish(draft=draft, presented_hash=draft.content_hash,
        expected_version=old.version, idempotency_key='completion-new-plan')
    newer = plans.get_current(project_id=cmd.project_id)
    new_cmd = replace(cmd, plan_id=newer.plan_id, stage_id=newer.stages[0].stage_id)
    data = read(db, scope, new_cmd, newer)
    assert data['summary_stage_ids'] == set() and data['accepted_task_positions'] == set()
    assert data['tasks'][0]['status'] == 'accepted'
    summary(db, scope, new_cmd, idempotency_key='new-plan-summary')
    with TestClient(create_app(container)) as client:
        login(client, db, scope)
        response = client.get('/api/v1/workspace', params=dict(project_id=cmd.project_id))
        assert response.status_code == 200
        current = response.json()['stages'][0]['completion']
        assert current == dict(status='incomplete', summary_completed=True, completed_practice_tasks=0, total_practice_tasks=1)
    old_data = read(db, scope, cmd, old)
    assert old_data['summary_stage_ids'] == {cmd.stage_id}
    assert old_data['accepted_task_positions'] == {(cmd.stage_id, cmd.task_id)}


def test_summary_only_stage_completes_http(resource_scenario):
    db, scope, cmd, container, _ = resource_scenario
    with TestClient(create_app(container)) as client:
        login(client, db, scope)
        query = dict(project_id=cmd.project_id)
        assert client.get('/api/v1/workspace', params=query).json()['completed_stages'] == 0
        summary(db, scope, cmd)
        result = client.get('/api/v1/workspace', params=query).json()
        assert result['completed_stages'] == result['total_stages'] == 1
        assert result['stages'][0]['completion'] == dict(status='completed', summary_completed=True,
            completed_practice_tasks=0, total_practice_tasks=0)


def test_legacy_blank_unicode_stage_content_does_not_count(submission_scenario):
    db, scope, cmd, _, plan = submission_scenario
    with psycopg.connect(db.migrator_dsn) as conn:
        conn.execute("""INSERT INTO summary_attempts(attempt_id,project_id,unit_id,content,attempt_no,rubric_version,
            plan_id,stage_id,version) VALUES(%s,%s,NULL,%s,1,1,%s,%s,1)""",
            ('blank-' + cmd.project_id, cmd.project_id, ' \n\t\u3000 ', cmd.plan_id, cmd.stage_id))
        conn.execute('INSERT INTO summary_stage_heads(project_id,plan_id,stage_id,version) VALUES(%s,%s,%s,1)',
            cmd.position[:3])
    assert read(db, scope, cmd, plan)['summary_stage_ids'] == set()


def test_workspace_reads_one_summary_per_stage_after_many_revisions(submission_scenario, monkeypatch):
    db, scope, cmd, _, plan = submission_scenario
    for version in range(4):
        summary(db, scope, cmd, content=' summary ' + str(version), expected_version=version,
            idempotency_key='summary-version-' + str(version))
    saved = repository(db).save(scope, cmd)
    repository(db).decide(scope, decision(cmd, saved))
    original_connect = psycopg.connect
    fetched = []
    class Connection:
        def __init__(self, *args, **kwargs):
            self.conn = original_connect(*args, **kwargs)
        def __enter__(self):
            self.conn.__enter__()
            return self
        def __exit__(self, *args):
            return self.conn.__exit__(*args)
        def execute(self, sql, args=()):
            cursor = self.conn.execute(sql, args)
            if 'UNION ALL' in sql:
                rows = cursor.fetchall()
                fetched.extend(rows)
                class Result:
                    def fetchall(self):
                        return rows
                return Result()
            return cursor
    monkeypatch.setattr(psycopg, 'connect', Connection)
    data = read(db, scope, cmd, plan)
    assert data['summary_stage_ids'] == {cmd.stage_id}
    assert data['accepted_task_positions'] == {(cmd.stage_id, cmd.task_id)}
    assert len(fetched) == 2
