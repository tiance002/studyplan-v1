"""Actual app-role PG/API/standard queue and retained receipt coaching boundaries."""
from dataclasses import replace
from concurrent.futures import ThreadPoolExecutor
import psycopg
import pytest
from app.application.model_binding import SubmissionBinding
from app.application.planning_budget import BudgetPolicy
from app.domain.assistant import ASSISTANT_PROTOCOL, ASSISTANT_PURPOSE
from app.infrastructure.providers.attempt_ledger import PgAttemptLLM
from app.main import create_app
from app.ports.llm import LLMResult, LLMFailure
from fastapi.testclient import TestClient
from tests.e2e.test_b2v_http_end_to_end import migrated_db as migrated_db
from tests.integration.test_prompts_pg import prompt_scenario as prompt_scenario, resource_scenario as resource_scenario
from tests.integration.test_summary_http_pg import login

pytestmark=pytest.mark.postgres
BASE='/api/v1/assistant/conversations'

class Provider:
    model='synthetic-assistant'; prompt_version=ASSISTANT_PROTOCOL; base_url='https://fixture.invalid'
    configuration_ref='fixture:assistant'; domain_pack={}; budget_policy=BudgetPolicy(100,100,100,100,100,100)
    def __init__(self): self.calls=[]; self.outcome=None
    def request_options(self,purpose):
        assert purpose==ASSISTANT_PURPOSE
        return dict(model=self.model,max_tokens=100)
    def generate_structured(self,**kwargs):
        self.calls.append(kwargs)
        return self.outcome or LLMResult({'reply':'## 已保存本轮反馈\n请结合当前要求说明边界。'},self.model,'synthetic',input_tokens=2,output_tokens=3)

@pytest.fixture
def setup(prompt_scenario):
    db,scope,cmd,container,current=prompt_scenario
    provider=Provider(); service=container.assistant_service
    service.bind_submission=lambda *_: SubmissionBinding(provider.configuration_ref,provider.budget_policy)
    service.provider_resolver=lambda scope,project,run,ref,manifest: PgAttemptLLM(db.app_dsn,provider,manifest=manifest)
    return db,scope,cmd,container,current,provider

def start(client,query,headers,cmd,mode='summary',key='begin',force_new=False):
    body=dict(plan_id=cmd.plan_id,stage_id=cmd.stage_id,mode=mode,task_id=cmd.task_id if mode=='practice' else None,idempotency_key=key,force_new=force_new)
    r=client.post(BASE,params=query,headers=headers,json=body)
    assert r.status_code==200,r.text
    return r.json(),body

def send(client,query,headers,identifier,text,intent='work_draft',key='send'):
    body=dict(intent=intent,content=text,idempotency_key=key,consent_to_model=True)
    r=client.post(BASE+'/'+identifier+'/messages',params=query,headers=headers,json=body)
    assert r.status_code==202,r.text
    return r.json(),body

@pytest.mark.parametrize('mode',['summary','practice'])
def test_three_turns_exact_user_text_explicit_formal_save_and_restore(setup,mode):
    db,scope,cmd,container,current,provider=setup
    query=dict(project_id=cmd.project_id)
    with TestClient(create_app(container)) as c:
        headers=login(c,db,scope)
        v,body=start(c,query,headers,cmd,mode); identifier=v['conversation_id']
        assert c.post(BASE,params=query,headers=headers,json=body).json()['conversation_id']==identifier
        assert len(c.get(BASE,params=query).json()['items'])==1
        for i,(text,intent) in enumerate([(' \n原始工作稿🙂\t ','work_draft'),('解释当前遗漏','question'),(' \n修改后的完整原稿🙂\t ','work_draft')]):
            v,b=send(c,query,headers,identifier,text,intent,'turn'+str(i))
            assert c.post(BASE+'/'+identifier+'/messages',params=query,headers=headers,json=b).status_code==202
            assert v['formal_saves']==[] and v['formal_version']==0
            assert container.planning_worker.tick()
            v=c.get(BASE+'/'+identifier,params=query).json()
            assert len(v['messages'])==(i+1)*2 and v['messages'][-1]['run_status']=='succeeded'
            assert v['messages'][-2]['content']==text
        assert len(provider.calls)==3
        assert provider.calls[1]['payload']['work_draft']['content']==' \n原始工作稿🙂\t '
        assert provider.calls[1]['payload']['current_message']['intent']=='question'
        assert 'private.invalid' not in str(provider.calls)
        final=' \n用户明确最终保存的文本🙂\t '
        b=dict(content=final,draft_message_id=v['current_draft_message_id'],expected_version=0,idempotency_key='formal')
        saved=c.post(BASE+'/'+identifier+'/save',params=query,headers=headers,json=b)
        assert saved.status_code==200,saved.text
        v=saved.json(); assert v['formal_saves'][0]['content']==final and v['formal_version']==1
        assert c.post(BASE+'/'+identifier+'/save',params=query,headers=headers,json=b).json()['formal_saves']==v['formal_saves']
        assert len(provider.calls)==3
        assert c.post(BASE+'/'+identifier+'/save',params=query,headers=headers,json=dict(b,idempotency_key='stale')).status_code==409
        assert c.get(BASE+'/'+identifier,params=query).json()['messages']==v['messages']
        with psycopg.connect(db.app_dsn) as conn:
            assert conn.execute('SELECT count(*) FROM assistant_messages').fetchone()[0]==0
            conn.execute("SELECT set_config('app.actor_id',%s,true),set_config('app.project_id',%s,true)",(scope.actor_id,cmd.project_id))
            assert conn.execute('SELECT count(*) FROM assistant_messages').fetchone()[0]==6
            assert conn.execute("SELECT count(*) FROM ai_provider_attempts WHERE run_id IN(SELECT run_id FROM assistant_turns)").fetchone()[0]==3
            assert conn.execute("SELECT status FROM practice_tasks WHERE task_id=%s",(cmd.task_id,)).fetchone()[0]=='pending'
        if mode=='summary':
            formal=c.get('/api/v1/summaries',params={**query,'plan_id':cmd.plan_id,'stage_id':cmd.stage_id}).json()['attempts'][-1]
            assert formal['content']==final
        else:
            formal=c.get('/api/v1/prompts',params={**query,'plan_id':cmd.plan_id,'stage_id':cmd.stage_id,'task_id':cmd.task_id}).json()['revisions'][-1]
            assert formal['user_draft']==final

@pytest.mark.parametrize('outcome,expected',[(LLMFailure('provider_invalid_json','invalid'),'failed'),(LLMFailure('unknown','unknown',dispatch_unknown=True),'reconciliation_required'),(LLMResult({'reply':''},'synthetic','synthetic'),'failed')])
def test_known_invalid_unknown_strict_json_no_retry_no_repair(setup,outcome,expected):
    db,scope,cmd,container,current,provider=setup; provider.outcome=outcome
    q=dict(project_id=cmd.project_id)
    with TestClient(create_app(container)) as c:
        h=login(c,db,scope);v,_=start(c,q,h,cmd);identifier=v['conversation_id']
        v,b=send(c,q,h,identifier,'原稿')
        assert container.planning_worker.tick()
        v=c.get(BASE+'/'+identifier,params=q).json()
        assert len(v['messages'])==1 and v['messages'][0]['run_status']==expected
        assert not container.planning_worker.tick() and len(provider.calls)==1
        if expected=='reconciliation_required':
            other,_=start(c,q,h,cmd,key='another',force_new=True)
            assert c.post(BASE+'/'+other['conversation_id']+'/messages',params=q,headers=h,json=dict(b,idempotency_key='new-unknown')).status_code==409


def test_no_consent_no_scope_spoof_cross_account_and_exact_task(setup):
    db,scope,cmd,container,current,provider=setup;q=dict(project_id=cmd.project_id)
    with TestClient(create_app(container)) as c:
        h=login(c,db,scope);v,b=start(c,q,h,cmd,'practice');identifier=v['conversation_id']
        assert c.post(BASE,params=q,headers=h,json=dict(b,actor_id='spoof')).status_code==422
        assert c.post(BASE,params=q,headers=h,json=dict(b,task_id='wrong',idempotency_key='wrong')).status_code==404
        msg=dict(intent='work_draft',content='private',idempotency_key='nc',consent_to_model=False)
        assert c.post(BASE+'/'+identifier+'/messages',params=q,headers=h,json=msg).status_code==400
        assert c.post(BASE+'/'+identifier+'/messages',params=q,json=dict(msg,consent_to_model=True)).status_code==403
        reg=c.post('/api/v1/auth/register',json=dict(username='AssistantOther'+scope.actor_id[-10:],password='isolatepass1'))
        other={'X-CSRF-Token':reg.json()['csrf_token']}
        assert c.get(BASE+'/'+identifier,params=q).status_code==403
        assert c.get(BASE,params=q).status_code==403
        assert c.post(BASE+'/'+identifier+'/messages',params=q,headers=other,json=dict(msg,consent_to_model=True)).status_code==403
        assert provider.calls==[]


def test_save_receipt_survives_association_failure_without_second_revision(setup,monkeypatch):
    db,scope,cmd,container,current,provider=setup;q=dict(project_id=cmd.project_id)
    with TestClient(create_app(container),raise_server_exceptions=False) as c:
        h=login(c,db,scope);v,_=start(c,q,h,cmd);identifier=v['conversation_id']
        v,_=send(c,q,h,identifier,'原稿'); assert container.planning_worker.tick()
        b=dict(content='独立正式文本',draft_message_id=v['current_draft_message_id'],expected_version=0,idempotency_key='save')
        repo=container.assistant_service.repository;original=repo.save_outcome
        monkeypatch.setattr(repo,'save_outcome',lambda *a,**k: (_ for _ in ()).throw(RuntimeError('association interruption')))
        interrupted=c.post(BASE+'/'+identifier+'/save',params=q,headers=h,json=b)
        assert interrupted.status_code==503 and '关联待核对' in interrupted.json()['message']
        monkeypatch.setattr(repo,'save_outcome',original)
        result=c.post(BASE+'/'+identifier+'/save',params=q,headers=h,json=b)
        assert result.status_code==200 and result.json()['formal_version']==1
        with psycopg.connect(db.migrator_dsn) as conn:
            assert conn.execute('SELECT count(*) FROM summary_attempts WHERE project_id=%s',(cmd.project_id,)).fetchone()[0]==1


def test_provider_receipt_replay_after_reply_persistence_crash(setup,monkeypatch):
    db,scope,cmd,container,current,provider=setup;q=dict(project_id=cmd.project_id)
    with TestClient(create_app(container)) as c:
        h=login(c,db,scope);v,_=start(c,q,h,cmd);identifier=v['conversation_id']
        v,_=send(c,q,h,identifier,'原稿')
        repo=container.assistant_service.repository;original=repo.finish
        monkeypatch.setattr(repo,'finish',lambda *a,**k: (_ for _ in ()).throw(RuntimeError('reply interruption')))
        assert container.planning_worker.tick();assert len(provider.calls)==1
        monkeypatch.setattr(repo,'finish',original)
        with psycopg.connect(db.migrator_dsn) as conn:
            conn.execute("UPDATE ai_jobs SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE run_id=%s",(v['messages'][0]['run_id'],))
        assert container.planning_worker.tick()
        got=c.get(BASE+'/'+identifier,params=q).json()
        assert len(got['messages'])==2 and got['messages'][-1]['run_status']=='succeeded' and len(provider.calls)==1


def test_active_limit_same_conversation_cancel_before_dispatch_and_old_plan_read_only(setup):
    db,scope,cmd,container,current,provider=setup;q=dict(project_id=cmd.project_id)
    with TestClient(create_app(container)) as c:
        h=login(c,db,scope);v,_=start(c,q,h,cmd);identifier=v['conversation_id']
        v,b=send(c,q,h,identifier,'原稿')
        assert c.post(BASE+'/'+identifier+'/messages',params=q,headers=h,json=dict(b,idempotency_key='second')).status_code==409
        run=v['messages'][0]
        cancel=dict(run_id=run['run_id'],expected_version=run['run_version'],idempotency_key='cancel')
        r=c.post(BASE+'/'+identifier+'/cancel',params=q,headers=h,json=cancel)
        assert r.status_code==200 and r.json()['messages'][0]['run_status']=='cancelled'
        assert not container.planning_worker.tick() and provider.calls==[]
        with psycopg.connect(db.migrator_dsn) as conn:
            conn.execute("UPDATE plan_revisions SET status='superseded' WHERE plan_id=%s",(cmd.plan_id,))
        got=c.get(BASE+'/'+identifier,params=q)
        assert got.status_code==200 and got.json()['read_only']
        assert c.post(BASE+'/'+identifier+'/messages',params=q,headers=h,json=dict(b,idempotency_key='old')).status_code==409
        assert c.post(BASE+'/'+identifier+'/save',params=q,headers=h,json=dict(content='old',draft_message_id=v['current_draft_message_id'],expected_version=0,idempotency_key='old-save')).status_code==409


def test_independent_submission_tamper_rejected_without_provider(setup):
    db,scope,cmd,container,current,provider=setup;q=dict(project_id=cmd.project_id)
    with TestClient(create_app(container)) as c:
        h=login(c,db,scope);v,_=start(c,q,h,cmd);identifier=v['conversation_id'];v,_=send(c,q,h,identifier,'原稿')
        with psycopg.connect(db.migrator_dsn) as conn:
            conn.execute("UPDATE ai_run_events SET detail=jsonb_set(detail,'{payload_hash}','\"corrupt\"') WHERE run_id=%s AND status='submission'",(v['messages'][0]['run_id'],))
        assert container.planning_worker.tick()
        got=c.get(BASE+'/'+identifier,params=q).json()
        assert got['messages'][0]['run_status']=='failed' and got['messages'][0]['error_class']=='assistant_contract_invalid' and provider.calls==[]


def test_concurrent_duplicate_create_and_send_one_identity(setup):
    db,scope,cmd,container,current,provider=setup
    service=container.assistant_service
    body=dict(plan_id=cmd.plan_id,stage_id=cmd.stage_id,task_id=None,mode='summary',idempotency_key='parallel-start')
    with ThreadPoolExecutor(max_workers=2) as pool: values=list(pool.map(lambda _:service.create(scope,cmd.project_id,body),range(2)))
    assert values[0]['conversation_id']==values[1]['conversation_id']
    identifier=values[0]['conversation_id'];msg=dict(content='原稿',intent='work_draft',consent_to_model=True,idempotency_key='parallel-send')
    with ThreadPoolExecutor(max_workers=2) as pool: sent=list(pool.map(lambda _:service.send(scope,cmd.project_id,identifier,msg),range(2)))
    assert sent[0]['messages'][0]['message_id']==sent[1]['messages'][0]['message_id']
    assert container.planning_worker.tick() and len(provider.calls)==1


def test_unconfigured_model_preserves_exact_original_and_can_formally_save(setup):
    db,scope,cmd,container,current,provider=setup; container.assistant_service.bind_submission=None
    q=dict(project_id=cmd.project_id)
    with TestClient(create_app(container)) as c:
        h=login(c,db,scope);v,_=start(c,q,h,cmd);identifier=v['conversation_id']
        text=' \n保留我未获反馈的原文🙂\t '
        v,_=send(c,q,h,identifier,text)
        assert v['messages'][0]['content']==text and v['messages'][0]['run_status']=='failed'
        assert v['messages'][0]['run_id'] is None
        assert not container.planning_worker.tick() and provider.calls==[]
        b=dict(content=text,draft_message_id=v['current_draft_message_id'],expected_version=0,idempotency_key='no-model-save')
        r=c.post(BASE+'/'+identifier+'/save',params=q,headers=h,json=b)
        assert r.status_code==200 and r.json()['formal_saves'][0]['content']==text
