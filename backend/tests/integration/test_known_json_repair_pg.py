"""Known malformed JSON uses bounded repair; fresh owned PG and MockTransport only."""
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import httpx
import psycopg
from psycopg.rows import dict_row
import pytest

from app.agent_workflows.planning_batches import DEFAULT_BUDGET, SHORT_GENERATION_VERSION, attempt_purpose
from app.agent_workflows.runtime import PostgresSaver
from app.composition import build_container
from app.core.ids import new_id
from app.domain.runs.fencing import PlanningWriteFence
from app.infrastructure.checkpointer.planning_executor import PgPlanningExecutor, builder_for_version
from app.infrastructure.domain_pack import CURRENT_PACKS, load_pack
from app.infrastructure.providers.attempt_ledger import PgAttemptLLM
from app.infrastructure.providers.openai_compatible import OpenAICompatibleLLM
from app.infrastructure.providers.planning_demo import build_planning_demo
from app.main import create_app
from app.ports.llm import LLMDispatchUnknownError
from app.tools.seed_b3 import seed_reviewed_pack
from fastapi.testclient import TestClient
from tests.integration.test_v62_semantic_pg import settings_for
from tests.integration.test_v613_contract_pg import queued_authority, project_counts
from tests.pg_harness import create_test_database, instance_is_dedicated, roles_created_by_harness

pytestmark = pytest.mark.postgres
ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'var/known-json-repair-20261005/pg'
FIXTURE = ROOT / 'var/rc-user-20261005/private/responses/160.body'
FIXTURE_SHA = 'ffffffa319a2217bd889dca2f4c9416d21fc37d78903cbf4a090ccb3bf8d901c'


class OwnedDatabase:
    def __init__(self, db):
        self._db = db

    def __getattr__(self, name):
        return getattr(self._db, name)

    def __repr__(self):
        return 'OwnedDatabase(name=' + repr(self._db.name) + ')'


def evidence(name, **details):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / (name + '.json')).write_text(json.dumps(dict(status='PASS',
        requested_model='gpt-6.1-sol', requested_effort='medium', actual_resolution='NOT OBSERVABLE',
        real_product_model_requests=0, global_role_mutations=0, quota='160/200 unchanged',
        **details), ensure_ascii=False, indent=2), encoding='utf-8')


@pytest.fixture(scope='module')
def owned_dbs():
    assert not instance_is_dedicated() and roles_created_by_harness() == set()
    business = create_test_database('studyplan_test_known_json_business')
    checkpoint = create_test_database('studyplan_test_known_json_checkpoint')
    try:
        migration = subprocess.run([sys.executable, '-m', 'alembic', 'upgrade', 'head'],
            cwd=ROOT / 'backend', env=dict(os.environ, STUDYPLAN_MIGRATION_DSN=business.migrator_dsn),
            capture_output=True, text=True, encoding='utf-8', errors='replace')
        assert migration.returncode == 0, 'Owned migration failed'
        with psycopg.connect(business.migrator_dsn) as conn:
            seed_reviewed_pack(conn, load_pack(CURRENT_PACKS['agent.application']))
            conn.execute("INSERT INTO learning_projects(project_id,owner_actor_id,title,goal_statement,stable_key) VALUES ('jobs_p1','jobs_a1','owned','goal','known_json_1'),('jobs_p2','jobs_a2','owned two','goal','known_json_2')")
        with PostgresSaver.from_conn_string(checkpoint.migrator_dsn) as saver:
            saver.setup()
        assert roles_created_by_harness() == set()
        evidence('owned-databases', business_database=business.name, checkpoint_database=checkpoint.name,
                 migrations='PASS', roles_created=[], new_owned=True)
        yield OwnedDatabase(business), OwnedDatabase(checkpoint)
    finally:
        checkpoint.drop()
        business.drop()
        assert roles_created_by_harness() == set()


@pytest.fixture(autouse=True)
def clean_owned_runs(owned_dbs):
    with psycopg.connect(owned_dbs[0].migrator_dsn) as conn:
        conn.execute('TRUNCATE ai_provider_attempts, ai_jobs, ai_runs CASCADE')


def attempt_rows(db, run_id):
    with psycopg.connect(db.migrator_dsn, row_factory=dict_row) as conn:
        return conn.execute('SELECT attempt_id,status,schema_name,input_tokens,output_tokens,error_class,response_payload FROM ai_provider_attempts WHERE run_id=%s ORDER BY attempt_id', (run_id,)).fetchall()


@contextmanager
def session(owned_dbs, kind, *, unknown=False, invalid_repair=False):
    db, checkpoint = owned_dbs
    container = build_container(settings_for(db))
    with TestClient(create_app(container)) as client:
        _, params, _, run_id, actor, initial = queued_authority(db, container, client, 'knownjson')
    claim = container.plan_service._planning_jobs.claim_next('known-json-owned', 300)
    assert claim is not None and claim.run_id == run_id
    fence = PlanningWriteFence(**asdict(claim))
    fake = build_planning_demo()
    calls = []
    invalid_ids = []
    raw = FIXTURE.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == FIXTURE_SHA
    retained = json.loads(raw)
    # The private body is consumed only in memory and never included in evidence.
    assert retained['choices'][0]['finish_reason'] == 'stop'

    class Provider(OpenAICompatibleLLM):
        def generate_structured(self, **kwargs):
            self.current = kwargs
            return super().generate_structured(**kwargs)

    def transport(request):
        kwargs = provider.current
        calls.append((kwargs['purpose'], kwargs['attempt_id']))
        if kwargs['purpose'] == 'planning.' + kind and not invalid_ids:
            invalid_ids.append(kwargs['attempt_id'])
            if unknown:
                raise httpx.ReadTimeout('owned synthetic timeout', request=request)
            return httpx.Response(200, content=raw)
        if invalid_repair and kwargs['purpose'] == 'planning.repair':
            return httpx.Response(200, content=raw)
        content = fake._handlers[kwargs['purpose']](kwargs['purpose'], kwargs['payload'])
        return httpx.Response(200, json={'choices':[{'message':{'content':json.dumps(content, ensure_ascii=False)}, 'finish_reason':'stop'}], 'usage':{'prompt_tokens':11, 'completion_tokens':13}})

    with httpx.Client(transport=httpx.MockTransport(transport)) as http_client:
        provider = Provider(base_url='https://owned-mock.invalid/v1', api_key='synthetic-test-only',
            model='owned-mock', client=http_client, budget_policy=DEFAULT_BUDGET)
        requests = []
        class RecordingLedger(PgAttemptLLM):
            def generate_structured(self, **kwargs):
                requests.append(deepcopy(kwargs))
                return super().generate_structured(**kwargs)
        ledger = RecordingLedger(db.app_dsn, provider, manifest=initial['manifest'])
        def nodes_for(fresh=None):
            service = (fresh or container).plan_service
            return service._build_nodes(project_id=params['project_id'], run_id=run_id,
                goal=initial['goal'], selected_pack=initial['domain_pack'], frozen_input=initial,
                llm=ledger, write_fence=fence)
        yield dict(db=db, checkpoint=checkpoint, container=container, initial=initial, claim=claim,
            run_id=run_id, actor=actor, project_id=params['project_id'], ledger=ledger,
            nodes=nodes_for(), nodes_for=nodes_for, calls=calls, invalid_ids=invalid_ids,
            requests=requests, provider=provider)


def assert_receipts(ctx, *, repaired=True):
    rows = attempt_rows(ctx['db'], ctx['run_id'])
    normal = next(r for r in rows if r['attempt_id'] == ctx['invalid_ids'][0])
    assert normal['status'] == 'failed' and normal['error_class'] == 'provider_invalid_json'
    assert normal['response_payload']['error_class'] == 'provider_invalid_json'
    assert normal['input_tokens'] >= 0 and normal['output_tokens'] >= 0
    assert 'known_failed_attempt' not in normal['response_payload']['details']
    repairs = [r for r in rows if attempt_purpose(r['attempt_id']) == 'planning.repair']
    assert len(repairs) == 1 and repairs[0]['attempt_id'] != normal['attempt_id']
    assert repairs[0]['status'] == ('succeeded' if repaired else 'failed')
    if repaired:
        assert (repairs[0]['input_tokens'], repairs[0]['output_tokens']) == (11, 13)
    return rows


@pytest.mark.parametrize('kind', ['structure', 'practice'])
def test_known_json_full_validated_draft_owned_pg(owned_dbs, kind):
    with session(owned_dbs, kind) as ctx:
        executor = PgPlanningExecutor(ctx['checkpoint'].migrator_dsn, llm=ctx['ledger'])
        trace = executor.execute_or_resume(ctx['nodes'], ctx['initial'], new_id('checkpoint'), SHORT_GENERATION_VERSION, lambda: None)
        assert trace.state['repair_count'] == 1 and trace.state['draft_ref']
        assert not trace.state.get('generation_errors') and not trace.state.get('structure_errors')
        rows = assert_receipts(ctx)
        counts = project_counts(ctx['db'], ctx['project_id'])
        assert counts['plan_drafts'] == 1 and counts['plan_revisions'] == 0
        assert len(ctx['calls']) == 2 + len(ctx['initial']['manifest']['structure_batches']) + len(ctx['initial']['manifest']['stages'])
        authority = ctx['container'].plan_service._planning_jobs.read_generation_authority(ctx['actor'], ctx['project_id'], ctx['run_id'])
        failed = [r for r in authority['receipts'] if r.get('failure')]
        assert len(failed) == 1 and 'payload' not in failed[0]
        evidence('full-' + kind, database=ctx['db'].name, checkpoint_database=ctx['checkpoint'].name,
            run_id=ctx['run_id'], attempts=[{k:r[k] for k in ('attempt_id','status','schema_name','input_tokens','output_tokens','error_class')} for r in rows],
            mock_http_requests=len(ctx['calls']), fixture_sha=FIXTURE_SHA, business_counts=counts,
            validated_draft=True, normal_failed_preserved=True, independent_failure_authority=True)


@pytest.mark.parametrize('crash_after', ['normal', 'repair'])
def test_receipt_before_checkpoint_replay_no_new_charge(owned_dbs, monkeypatch, crash_after):
    with session(owned_dbs, 'structure') as ctx:
        config = {'configurable':{'thread_id':new_id('checkpoint')}, 'recursion_limit':1000}
        with PostgresSaver.from_conn_string(ctx['checkpoint'].migrator_dsn) as saver:
            graph = builder_for_version(SHORT_GENERATION_VERSION)(ctx['nodes'], checkpointer=saver)
            graph.invoke(ctx['initial'], config, interrupt_before=['generate_structure_batch'])
            before = graph.get_state(config)
            delta = ctx['nodes'].generate_structure_batch(deepcopy(before.values))
            assert len(ctx['calls']) == 2 and not delta.get('generation_errors')
            assert graph.get_state(config).values == before.values
            if crash_after == 'repair':
                graph.invoke(None, config, interrupt_before=['repair_batch'])
                before = graph.get_state(config)
                assert before.next == ('repair_batch',) and before.values['repair_count'] == 0
                delta = ctx['nodes'].repair_batch(deepcopy(before.values))
                assert delta['repair_count'] == 1 and len(ctx['calls']) == 3
                assert graph.get_state(config).values == before.values
        fresh = build_container(settings_for(ctx['db']))
        authority = fresh.plan_service._planning_jobs.read_generation_authority(ctx['actor'], ctx['project_id'], ctx['run_id'])
        nodes = ctx['nodes_for'](fresh)
        executor = PgPlanningExecutor(ctx['checkpoint'].migrator_dsn, llm=ctx['ledger'])
        stop = 'generate_structure_batch' if crash_after == 'normal' else 'repair_batch'
        monkeypatch.setattr(executor, '_stream', lambda g,p,c,progress:g.invoke(p,c,interrupt_after=[stop]))
        calls_before = len(ctx['calls'])
        trace = executor.execute_or_resume(nodes, authority['initial'], config['configurable']['thread_id'], SHORT_GENERATION_VERSION, lambda:None)
        assert len(ctx['calls']) == calls_before
        if crash_after == 'repair':
            assert trace.state['repair_count'] == 1
            assert_receipts(ctx)
        else:
            assert len(attempt_rows(ctx['db'], ctx['run_id'])) == 2
        assert project_counts(ctx['db'], ctx['project_id'])['plan_drafts'] == 0
        evidence('replay-' + crash_after, database=ctx['db'].name, checkpoint_database=ctx['checkpoint'].name,
            run_id=ctx['run_id'], crash_boundary=crash_after + '_receipt_committed_checkpoint_uncommitted',
            mock_http_before_recovery=calls_before, mock_http_during_recovery=0, draft_count=0)


@pytest.mark.parametrize('mode', ['unknown', 'failed_repair'])
def test_unknown_or_failed_run_never_reclaimed_or_drafted(owned_dbs, mode):
    with session(owned_dbs, 'practice', unknown=mode=='unknown', invalid_repair=mode=='failed_repair') as ctx:
        executor = PgPlanningExecutor(ctx['checkpoint'].migrator_dsn, llm=ctx['ledger'])
        if mode == 'unknown':
            with pytest.raises(LLMDispatchUnknownError):
                executor.execute_or_resume(ctx['nodes'], ctx['initial'], new_id('checkpoint'), SHORT_GENERATION_VERSION, lambda:None)
            rows = attempt_rows(ctx['db'], ctx['run_id'])
            assert any(r['status']=='reconciliation_required' for r in rows)
            assert all(attempt_purpose(r['attempt_id'])!='planning.repair' for r in rows)
        else:
            trace = executor.execute_or_resume(ctx['nodes'], ctx['initial'], new_id('checkpoint'), SHORT_GENERATION_VERSION, lambda:None)
            assert trace.state.get('generation_errors') and not trace.state.get('draft_ref')
            rows = assert_receipts(ctx, repaired=False)
            with psycopg.connect(ctx['db'].migrator_dsn) as conn:
                conn.execute("UPDATE ai_runs SET status='failed',next_action='none' WHERE run_id=%s", (ctx['run_id'],))
        with psycopg.connect(ctx['db'].migrator_dsn) as conn:
            conn.execute("UPDATE ai_jobs SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE run_id=%s", (ctx['run_id'],))
        calls_before = len(ctx['calls'])
        assert ctx['container'].plan_service._planning_jobs.claim_next('restart-owned',300) is None
        assert not ctx['container'].planning_worker.tick()
        assert len(ctx['calls']) == calls_before
        assert project_counts(ctx['db'],ctx['project_id'])['plan_drafts'] == 0
        evidence(mode, database=ctx['db'].name, run_id=ctx['run_id'], attempt_statuses=[r['status'] for r in rows],
            repair_requests=sum(p=='planning.repair' for p,_ in ctx['calls']), claim=None, draft_count=0,
            mock_http_after_terminal=0)


@pytest.mark.parametrize('boundary', ['request', 'output', 'repair2'])
def test_existing_pg_budget_guards_survive_restart(owned_dbs, monkeypatch, boundary):
    from tests.integration.test_rc_runtime_budget_pg import (
        test_nth_request_allowed_then_n_plus_one_rejected_after_runtime_restart,
        test_output_budget_rejected_before_provider_with_request_count_below_cap,
        test_repair_total_two_across_batches_survives_runtime_restart,
    )
    checks = dict(request=test_nth_request_allowed_then_n_plus_one_rejected_after_runtime_restart,
        output=test_output_budget_rejected_before_provider_with_request_count_below_cap,
        repair2=test_repair_total_two_across_batches_survives_runtime_restart)
    checks[boundary](owned_dbs[0], monkeypatch)
    evidence('budget-' + boundary, database=owned_dbs[0].name, boundary=boundary,
        pre_dispatch_refusal=True, retained_attempts_counted_once=True, runtime_restart=True)


@pytest.mark.parametrize('mode', ['success', 'failed', 'unknown'])
def test_standard_owned_worker_projects_final_run(owned_dbs, mode):
    with session(owned_dbs, 'practice', unknown=mode=='unknown', invalid_repair=mode=='failed') as ctx:
        service = ctx['container'].plan_service
        service._runtime_factory = None
        service._llm = ctx['ledger']
        service._executor = PgPlanningExecutor(ctx['checkpoint'].migrator_dsn, llm=ctx['ledger'])
        ctx['container'].planning_worker._process(ctx['claim'])
        with psycopg.connect(ctx['db'].migrator_dsn) as conn:
            run_status, next_action, result_ref = conn.execute('SELECT status,next_action,result_ref FROM ai_runs WHERE run_id=%s', (ctx['run_id'],)).fetchone()
            job_status = conn.execute('SELECT status FROM ai_jobs WHERE run_id=%s', (ctx['run_id'],)).fetchone()[0]
        expected = dict(success='succeeded', failed='failed', unknown='reconciliation_required')[mode]
        assert run_status == expected
        counts = project_counts(ctx['db'], ctx['project_id'])
        assert counts['plan_drafts'] == (1 if mode=='success' else 0)
        assert counts['plan_revisions'] == 0
        if mode=='success':
            assert next_action == 'none' and result_ref and job_status == 'completed'
            rows = assert_receipts(ctx)
        elif mode=='failed':
            assert not result_ref and next_action=='retry' and job_status=='completed'
            rows = assert_receipts(ctx, repaired=False)
        else:
            assert next_action=='reconcile' and not result_ref and job_status=='running'
            rows = attempt_rows(ctx['db'], ctx['run_id'])
            assert any(r['status']=='reconciliation_required' for r in rows)
            assert all(attempt_purpose(r['attempt_id'])!='planning.repair' for r in rows)
            request = next(k for k in ctx['requests'] if k['attempt_id']==ctx['invalid_ids'][0])
            fresh = PgAttemptLLM(ctx['db'].app_dsn, ctx['provider'], manifest=ctx['initial']['manifest'])
            before_replay = len(ctx['calls'])
            retained = fresh.generate_structured(**request)
            assert retained.dispatch_unknown and retained.error_class=='attempt_dispatch_unknown'
            assert len(ctx['calls'])==before_replay
        calls_before = len(ctx['calls'])
        assert service._planning_jobs.claim_next('after-terminal-owned',300) is None
        assert not ctx['container'].planning_worker.tick()
        assert len(ctx['calls']) == calls_before
        evidence('worker-' + mode, database=ctx['db'].name, checkpoint_database=ctx['checkpoint'].name,
            run_id=ctx['run_id'], run_status=run_status, job_status=job_status, next_action=next_action,
            business_counts=counts, repair_requests=sum(p=='planning.repair' for p,_ in ctx['calls']),
            mock_http_requests=calls_before, mock_http_after_terminal=0, standard_worker_process=True,
            run_projection_sql_injected=False, unknown_fresh_ledger_replay='PASS' if mode=='unknown' else 'NOT RUN')


@pytest.mark.parametrize('mismatch', ['status', 'error', 'input_usage', 'output_usage'])
def test_durable_failed_receipt_mismatch_refuses_attestation_owned_pg(owned_dbs, mismatch):
    with session(owned_dbs, 'structure') as ctx:
        config = {'configurable':{'thread_id':new_id('checkpoint')}, 'recursion_limit':1000}
        with PostgresSaver.from_conn_string(ctx['checkpoint'].migrator_dsn) as saver:
            graph = builder_for_version(SHORT_GENERATION_VERSION)(ctx['nodes'], checkpointer=saver)
            graph.invoke(ctx['initial'], config, interrupt_before=['generate_structure_batch'])
            delta = ctx['nodes'].generate_structure_batch(deepcopy(graph.get_state(config).values))
            assert not delta.get('generation_errors')
        request = next(k for k in ctx['requests'] if k['attempt_id']==ctx['invalid_ids'][0])
        statements = {
            'status': "UPDATE ai_provider_attempts SET status='cancelled' WHERE attempt_id=%s",
            'error': "UPDATE ai_provider_attempts SET error_class='synthetic_mismatch' WHERE attempt_id=%s",
            'input_usage': 'UPDATE ai_provider_attempts SET input_tokens=input_tokens+1 WHERE attempt_id=%s',
            'output_usage': 'UPDATE ai_provider_attempts SET output_tokens=output_tokens+1 WHERE attempt_id=%s',
        }
        with psycopg.connect(ctx['db'].migrator_dsn) as conn:
            conn.execute(statements[mismatch], (ctx['invalid_ids'][0],))
        before = len(ctx['calls'])
        fresh = PgAttemptLLM(ctx['db'].app_dsn, ctx['provider'], manifest=ctx['initial']['manifest'])
        rejected = fresh.generate_structured(**request)
        assert rejected.error_class=='attempt_receipt_conflict' and not rejected.dispatch_unknown
        assert 'known_failed_attempt' not in rejected.details
        assert len(ctx['calls'])==before
        assert project_counts(ctx['db'],ctx['project_id'])['plan_drafts']==0
        evidence('receipt-mismatch-' + mismatch, database=ctx['db'].name,
            run_id=ctx['run_id'], mismatch=mismatch, error_class=rejected.error_class,
            attestation=False, mock_http_before_replay=before, mock_http_during_replay=0,
            draft_count=0, mutated_receipt_database='new owned only')
