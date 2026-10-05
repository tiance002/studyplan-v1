"""Practice final contract on owned PG, ordinary API/Worker, and durable receipts."""
import psycopg
from psycopg.types.json import Jsonb
import pytest
from fastapi.testclient import TestClient
from app.core.ids import content_hash
from app.main import create_app
from app.ports.llm import LLMResult, LLMFailure
from tests.integration.test_assistant_http_pg import BASE, setup as setup, start
from tests.integration.test_assistant_teaching_state_pg import FIRST, SECOND, run_turn, send_natural
from tests.integration.test_prompts_pg import prompt_scenario as prompt_scenario, resource_scenario as resource_scenario
from tests.e2e.test_b2v_http_end_to_end import migrated_db as migrated_db
from tests.integration.test_summary_http_pg import login

pytestmark = pytest.mark.postgres
KIND = 'practice_teach_with_proposal'


def final():
    return dict(reply='过渡',teaching=[dict(issue_id=f'i{n}',explanation=f'当前剩余主题{n}的正确解释。') for n in (2,3)],proposal='候选任务要求：校验输入并保留可检查的失败证据。')


def prepare(client, db, scope, cmd, container, provider):
    q=dict(project_id=cmd.project_id); h=login(client,db,scope)
    v,_=start(client,q,h,cmd,'practice'); identifier=v['conversation_id']
    run_turn(client,q,h,identifier,container,provider,FIRST,1)
    run_turn(client,q,h,identifier,container,provider,SECOND,2)
    return q,h,identifier


@pytest.mark.parametrize('wire',['omitted','explicit'])
def test_final_proposal_formal_adopt_custom_cas_idempotency_rls_scope(setup,wire):
    db,scope,cmd,container,current,provider=setup
    with TestClient(create_app(container)) as c:
        q,h,identifier=prepare(c,db,scope,cmd,container,provider)
        value=final()
        if wire=='explicit':
            value.update(phase='teach',status='ready_to_draft',evaluation=[dict(issue_id=f'i{n}',state='resolved' if n==1 else 'unresolved') for n in (1,2,3)])
        v,run=run_turn(c,q,h,identifier,container,provider,value,3)
        source=v['messages'][-1]
        assert source['status']=='ready_to_draft' and source['proposal']==value['proposal']
        assert '关键问题' not in source['content'] and v['formal_version']==0
        with psycopg.connect(db.migrator_dsn) as conn:
            payload=conn.execute('SELECT payload FROM assistant_turns WHERE run_id=%s',(run,)).fetchone()[0]
            event=conn.execute("SELECT detail FROM ai_run_events WHERE run_id=%s AND status='submission'",(run,)).fetchone()[0]
            assert payload['expected_response_kind']==event['expected_response_kind']==KIND
            assert [i['state'] for i in payload['teaching_state']['issues']]==['resolved','unresolved','unresolved']
        for version,text in enumerate((source['proposal'],' 用户明确修改的正式原文🙂 ')):
            body=dict(content=text,proposal_message_id=source['message_id'],expected_version=version,idempotency_key=f'formal-{version}')
            r=c.post(BASE+'/'+identifier+'/save',params=q,headers=h,json=body)
            assert r.status_code==200,r.text
            assert r.json()['formal_version']==version+1
            assert c.post(BASE+'/'+identifier+'/save',params=q,headers=h,json=body).json()['formal_version']==version+1
            assert c.post(BASE+'/'+identifier+'/save',params=q,headers=h,json=dict(body,idempotency_key=f'stale-{version}')).status_code==409
        assert len(provider.calls)==3
        formal=c.get('/api/v1/prompts',params={**q,'plan_id':cmd.plan_id,'stage_id':cmd.stage_id,'task_id':cmd.task_id}).json()['revisions'][-1]
        assert formal['user_draft']==' 用户明确修改的正式原文🙂 '
        with psycopg.connect(db.app_dsn) as conn:
            assert conn.execute('SELECT count(*) FROM assistant_messages').fetchone()[0]==0
            conn.execute("SELECT set_config('app.actor_id',%s,true),set_config('app.project_id',%s,true)",(scope.actor_id,cmd.project_id))
            assert conn.execute('SELECT count(*) FROM assistant_messages').fetchone()[0]==6
            assert conn.execute('SELECT status FROM practice_tasks WHERE task_id=%s',(cmd.task_id,)).fetchone()[0]=='pending'
        reg=c.post('/api/v1/auth/register',json=dict(username='CoreOther'+scope.actor_id[-10:],password='isolatepass1'))
        assert reg.status_code==200
        assert c.get(BASE+'/'+identifier,params=q).status_code==403
        assert c.post(BASE+'/'+identifier+'/save',params=q,headers={'X-CSRF-Token':reg.json()['csrf_token']},json=body).status_code==403


@pytest.mark.parametrize('proposal',[None,'','   '])
def test_missing_final_proposal_failed_run_success_receipt_no_repair(setup,proposal):
    db,scope,cmd,container,current,provider=setup
    with TestClient(create_app(container)) as c:
        q,h,identifier=prepare(c,db,scope,cmd,container,provider)
        value=final();value['proposal']=proposal
        provider.outcome=LLMResult(value,provider.model,'synthetic',input_tokens=2,output_tokens=3)
        v,_=send_natural(c,q,h,identifier,'我仍然不理解','final-invalid');run=v['messages'][-1]['run_id']
        assert container.planning_worker.tick()
        v=c.get(BASE+'/'+identifier,params=q).json()
        assert len(v['messages'])==5 and v['messages'][-1]['run_status']=='failed'
        assert v['messages'][-1]['error_class']=='missing_required_practice_proposal'
        assert v['formal_version']==0 and not container.planning_worker.tick() and len(provider.calls)==3
        with psycopg.connect(db.migrator_dsn) as conn:
            receipt=conn.execute('SELECT status,response_payload FROM ai_provider_attempts WHERE run_id=%s',(run,)).fetchone()
            assert receipt[0]=='succeeded' and receipt[1]['payload']['proposal']==proposal


@pytest.mark.parametrize('tamper',['kind','event','missing_kind','missing_event'])
def test_expected_response_kind_tamper_fails_before_dispatch(setup,tamper):
    db,scope,cmd,container,current,provider=setup
    with TestClient(create_app(container)) as c:
        q,h,identifier=prepare(c,db,scope,cmd,container,provider)
        v,_=send_natural(c,q,h,identifier,'继续','tamper');run=v['messages'][-1]['run_id']
        with psycopg.connect(db.migrator_dsn) as conn:
            assert db.name.startswith('studyplan_test_')
            if tamper in ('kind','missing_kind'):
                conn.execute('ALTER TABLE assistant_turns DISABLE TRIGGER assistant_turns_immutable')
                payload=conn.execute('SELECT payload FROM assistant_turns WHERE run_id=%s',(run,)).fetchone()[0]
                if tamper=='kind':payload['expected_response_kind']='practice_issue_ledger'
                else:payload.pop('expected_response_kind')
                digest=content_hash(payload)
                conn.execute('UPDATE assistant_turns SET payload=%s,payload_hash=%s WHERE run_id=%s',(Jsonb(payload),digest,run))
                conn.execute("UPDATE ai_run_events SET detail=jsonb_set(detail,'{payload_hash}',%s) WHERE run_id=%s AND status='submission'",(Jsonb(digest),run))
                conn.execute('ALTER TABLE assistant_turns ENABLE TRIGGER assistant_turns_immutable')
            elif tamper=='event':
                conn.execute("UPDATE ai_run_events SET detail=jsonb_set(detail,'{expected_response_kind}','\"practice_issue_ledger\"') WHERE run_id=%s AND status='submission'",(run,))
            else:
                conn.execute("UPDATE ai_run_events SET detail=detail-'expected_response_kind' WHERE run_id=%s AND status='submission'",(run,))
        assert container.planning_worker.tick()
        assert c.get(BASE+'/'+identifier,params=q).status_code==409 and len(provider.calls)==2
        with psycopg.connect(db.migrator_dsn) as conn:
            assert conn.execute('SELECT status FROM ai_runs WHERE run_id=%s',(run,)).fetchone()[0]=='failed'


def test_final_receipt_resume_does_not_repeat_dispatch(setup,monkeypatch):
    db,scope,cmd,container,current,provider=setup
    with TestClient(create_app(container)) as c:
        q,h,identifier=prepare(c,db,scope,cmd,container,provider)
        provider.outcome=LLMResult(final(),provider.model,'synthetic',input_tokens=2,output_tokens=3)
        v,_=send_natural(c,q,h,identifier,'仍不理解','resume');run=v['messages'][-1]['run_id']
        repo=container.assistant_service.repository; original=repo.finish
        monkeypatch.setattr(repo,'finish',lambda *a,**k: (_ for _ in ()).throw(RuntimeError('owned interruption')))
        assert container.planning_worker.tick() and len(provider.calls)==3
        monkeypatch.setattr(repo,'finish',original)
        with psycopg.connect(db.migrator_dsn) as conn:
            conn.execute("UPDATE ai_jobs SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE run_id=%s",(run,))
        assert container.planning_worker.tick()
        v=c.get(BASE+'/'+identifier,params=q).json()
        assert v['messages'][-1]['status']=='ready_to_draft' and len(provider.calls)==3
        assert not container.planning_worker.tick()


def test_final_unknown_blocks_new_dispatch(setup):
    db,scope,cmd,container,current,provider=setup
    with TestClient(create_app(container)) as c:
        q,h,identifier=prepare(c,db,scope,cmd,container,provider)
        provider.outcome=LLMFailure('unknown','unknown',dispatch_unknown=True)
        v,_=send_natural(c,q,h,identifier,'仍不理解','unknown')
        assert container.planning_worker.tick() and len(provider.calls)==3
        v=c.get(BASE+'/'+identifier,params=q).json()
        assert v['messages'][-1]['run_status']=='reconciliation_required'
        other,_=start(c,q,h,cmd,'practice',key='another',force_new=True)
        assert c.post(BASE+'/'+other['conversation_id']+'/messages',params=q,headers=h,json=dict(content='重试',consent_to_model=True,idempotency_key='blocked')).status_code==409
        assert not container.planning_worker.tick() and len(provider.calls)==3


def test_final_cancel_before_dispatch_has_no_proposal(setup):
    db,scope,cmd,container,current,provider=setup
    with TestClient(create_app(container)) as c:
        q,h,identifier=prepare(c,db,scope,cmd,container,provider)
        v,_=send_natural(c,q,h,identifier,'仍不理解','cancel');run=v['messages'][-1]
        r=c.post(BASE+'/'+identifier+'/cancel',params=q,headers=h,json=dict(run_id=run['run_id'],expected_version=run['run_version'],idempotency_key='cancel-final'))
        assert r.status_code==200 and r.json()['messages'][-1]['run_status']=='cancelled'
        assert not container.planning_worker.tick() and len(provider.calls)==2
        assert r.json()['formal_version']==0


def test_final_dispatched_cancel_fences_success_receipt_and_late_proposal(setup,monkeypatch):
    db,scope,cmd,container,current,provider=setup
    with TestClient(create_app(container)) as c:
        q,h,identifier=prepare(c,db,scope,cmd,container,provider)
        provider.outcome=LLMResult(final(),provider.model,'synthetic',input_tokens=2,output_tokens=3)
        v,_=send_natural(c,q,h,identifier,'仍不理解','late');run=v['messages'][-1]['run_id']
        original=provider.generate_structured
        def cancelled_reply(**kwargs):
            current=c.get(BASE+'/'+identifier,params=q).json()['messages'][-1]
            body=dict(run_id=run,expected_version=current['run_version'],idempotency_key='cancel-dispatched')
            r=c.post(BASE+'/'+identifier+'/cancel',params=q,headers=h,json=body)
            assert r.status_code==200,r.text
            assert r.json()['messages'][-1]['run_status']=='reconciliation_required'
            return original(**kwargs)
        monkeypatch.setattr(provider,'generate_structured',cancelled_reply)
        assert container.planning_worker.tick()
        v=c.get(BASE+'/'+identifier,params=q).json()
        assert len(v['messages'])==5 and v['messages'][-1]['run_status']=='reconciliation_required'
        assert v['formal_version']==0 and not container.planning_worker.tick() and len(provider.calls)==3
        with psycopg.connect(db.migrator_dsn) as conn:
            assert conn.execute('SELECT status FROM ai_provider_attempts WHERE run_id=%s',(run,)).fetchone()[0]=='succeeded'
            assert conn.execute("SELECT count(*) FROM assistant_messages WHERE run_id=%s AND role='assistant'",(run,)).fetchone()[0]==0
