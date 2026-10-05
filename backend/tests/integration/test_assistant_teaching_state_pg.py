"""Server issue ledger over ordinary API/Worker and retained owned PG receipts.

Synthetic providers only: no product model request or product database writes.
"""
from copy import deepcopy
from dataclasses import replace

import psycopg
from psycopg.types.json import Jsonb
import pytest
from fastapi.testclient import TestClient

from app.composition import build_container
from app.api.v1.assistant_schemas import AssistantConversationView
from app.core.config import get_settings
from app.core.ids import content_hash
from app.domain.assistant_teaching import TEACHING_CONTRACT, REEXPRESSION
from app.infrastructure.providers.attempt_ledger import PgAttemptLLM
from app.main import create_app
from app.ports.llm import LLMResult, LLMFailure
from tests.integration.test_assistant_http_pg import BASE, setup as setup, start
from tests.integration.test_prompts_pg import prompt_scenario as prompt_scenario, resource_scenario as resource_scenario
from tests.e2e.test_b2v_http_end_to_end import migrated_db as migrated_db
from tests.integration.test_summary_http_pg import login

pytestmark=pytest.mark.postgres

FIRST=dict(phase='question_round_1',reply='自由文本：提前解释并追问已解决点？',proposal=None,
           issues=[dict(topic=f'主题{n}',question=f'关键问题{n}？',issue_id='forged') for n in range(1,4)],
           conversation_id='forged',run_id='forged',message_id='forged')
SECOND=dict(phase='question_round_2',reply='请再回答已解决的关键问题1？',proposal=None,
            evaluation=[dict(issue_id=f'i{n}',state='resolved' if n==1 else 'unresolved',
                             followup_question=None if n==1 else f'仅剩问题{n}？') for n in range(1,4)])

def final_value(mode, ready=False):
    return dict(phase='ready_to_draft' if ready else 'teach',reply='过渡',
                evaluation=[dict(issue_id=f'i{n}',state='resolved' if ready or n==1 else 'unresolved') for n in range(1,4)],
                **({} if ready else {'teaching':[dict(issue_id=f'i{n}',explanation=f'解释剩余主题{n}。') for n in (2,3)]}),
                proposal='候选完整原文' if ready or mode=='practice' else None)

def send_natural(client,q,h,identifier,text,key):
    body=dict(content=text,idempotency_key=key,consent_to_model=True)
    result=client.post(BASE+'/'+identifier+'/messages',params=q,headers=h,json=body)
    assert result.status_code==202,result.text
    return result.json(),body

def run_turn(client,q,h,identifier,container,provider,outcome,index):
    provider.outcome=LLMResult(deepcopy(outcome),provider.model,'synthetic',input_tokens=2,output_tokens=3)
    sent,body=send_natural(client,q,h,identifier,f'精确保留第{index}轮🙂',f'turn-{index}')
    before=len(provider.calls)
    assert container.planning_worker.tick()
    view=client.get(BASE+'/'+identifier,params=q)
    assert view.status_code==200,view.text
    view=view.json()
    assert view['messages'][-1]['run_status']=='succeeded',view
    assert len(provider.calls)==before+1
    assert client.post(BASE+'/'+identifier+'/messages',params=q,headers=h,json=body).status_code==202
    assert not container.planning_worker.tick() and len(provider.calls)==before+1
    return view,sent['messages'][-1]['run_id']

@pytest.mark.parametrize('mode',['summary','practice'])
def test_natural_issue_chain_formal_save_fresh_container_and_paged_history(setup,mode):
    db,scope,cmd,container,current,provider=setup;q=dict(project_id=cmd.project_id)
    with TestClient(create_app(container)) as client:
        h=login(client,db,scope);view,_=start(client,q,h,cmd,mode);identifier=view['conversation_id']
        view,r1=run_turn(client,q,h,identifier,container,provider,FIRST,1)
        assert '提前解释' not in view['messages'][-1]['content'] and 'forged' not in str(view)
        view,r2=run_turn(client,q,h,identifier,container,provider,SECOND,2)
        assert '关键问题1' not in view['messages'][-1]['content']
        assert all(f'仅剩问题{n}' in view['messages'][-1]['content'] for n in (2,3))
        view,r3=run_turn(client,q,h,identifier,container,provider,final_value(mode),3)
        assert (REEXPRESSION in view['messages'][-1]['content'])==(mode=='summary')
        if mode=='summary': view,_=run_turn(client,q,h,identifier,container,provider,final_value(mode,True),4)
        proposal=view['messages'][-1]
        assert proposal['status']=='ready_to_draft' and proposal['proposal']=='候选完整原文'
        assert view['formal_saves']==[] and view['formal_version']==0
        calls=len(provider.calls)
        saved=client.post(BASE+'/'+identifier+'/save',params=q,headers=h,json=dict(
            content=' 用户明确修改并保存🙂 ',proposal_message_id=proposal['message_id'],expected_version=0,idempotency_key='formal'))
        assert saved.status_code==200,saved.text
        assert saved.json()['formal_saves'][0]['content']==' 用户明确修改并保存🙂 ' and len(provider.calls)==calls
        older=client.get(BASE+'/'+identifier,params={**q,'before_sequence':5})
        assert older.status_code==200 and len(older.json()['messages'])==4
        assert '关键问题1' not in older.json()['messages'][-1]['content']
        with psycopg.connect(db.migrator_dsn) as conn:
            turns=conn.execute('SELECT payload FROM assistant_turns WHERE run_id=ANY(%s)',([r1,r2,r3],)).fetchall()
            assert all(t[0]['teaching_contract']==TEACHING_CONTRACT for t in turns)
            state=next(t[0]['teaching_state'] for t in turns if t[0]['teaching_state']['step']=='resolve')
            assert state['ledger_source']['run_id']==r1 and state['previous']['run_id']==r2
            assert state['issues'][0]['state']=='resolved'
            assert conn.execute('SELECT count(*) FROM ai_provider_attempts WHERE run_id IN (SELECT run_id FROM assistant_turns WHERE conversation_id=%s)',(identifier,)).fetchone()[0]==calls
            assert conn.execute('SELECT status FROM practice_tasks WHERE task_id=%s',(cmd.task_id,)).fetchone()[0]=='pending'
        # Rebuild the full composition, with no in-memory conversation cache.
        fresh=build_container(replace(get_settings(),database_url=db.app_dsn,llm_provider='fake',planning_worker_admission_mode='trusted_server',local_session_token=''))
        fresh_view=fresh.assistant_service.get(scope,cmd.project_id,identifier)
        assert AssistantConversationView.model_validate(fresh_view).model_dump(mode='json')['messages']==saved.json()['messages']
        with fresh.assistant_service.repository._tx(scope,cmd.project_id) as conn:
            row=fresh.assistant_service.repository._conversation(conn,cmd.project_id,identifier)
            recovered,_,modern=fresh.assistant_service.repository._teaching_history(conn,row)
        assert modern and recovered['step']=='ready' and recovered['ledger_source']['run_id']==r1

@pytest.mark.parametrize('tamper',['state','binding','turn_hash','event','receipt','message'])
def test_success_source_tampering_fails_closed_before_next_dispatch(setup,tamper):
    db,scope,cmd,container,current,provider=setup;q=dict(project_id=cmd.project_id)
    with TestClient(create_app(container)) as client:
        h=login(client,db,scope);view,_=start(client,q,h,cmd);identifier=view['conversation_id']
        view,run=run_turn(client,q,h,identifier,container,provider,FIRST,1)
        with psycopg.connect(db.migrator_dsn) as conn:
            # Fault injection in the harness-owned database only. Production
            # immutable triggers themselves already reject these mutations.
            assert db.name.startswith('studyplan_test_')
            conn.execute('ALTER TABLE assistant_turns DISABLE TRIGGER assistant_turns_immutable')
            conn.execute('ALTER TABLE assistant_messages DISABLE TRIGGER assistant_messages_immutable')
            if tamper in ('state','binding'):
                payload=conn.execute('SELECT payload FROM assistant_turns WHERE run_id=%s',(run,)).fetchone()[0]
                if tamper=='state':payload['teaching_state']['step']='ready'
                else:payload['teaching_state']['binding']['conversation_id']='foreign'
                digest=content_hash(payload)
                conn.execute('UPDATE assistant_turns SET payload=%s,payload_hash=%s WHERE run_id=%s',(Jsonb(payload),digest,run))
                conn.execute("UPDATE ai_run_events SET detail=jsonb_set(detail,'{payload_hash}',%s) WHERE run_id=%s AND status='submission'",(Jsonb(digest),run))
            elif tamper=='turn_hash':conn.execute("UPDATE assistant_turns SET payload_hash='corrupt' WHERE run_id=%s",(run,))
            elif tamper=='event':conn.execute("UPDATE ai_run_events SET detail=jsonb_set(detail,'{conversation_id}','\"foreign\"') WHERE run_id=%s AND status='submission'",(run,))
            elif tamper=='receipt':conn.execute("UPDATE ai_provider_attempts SET response_payload=jsonb_set(response_payload,'{payload,issues,0,question}','\"changed question\"') WHERE run_id=%s",(run,))
            else:conn.execute("UPDATE assistant_messages SET content='corrupt' WHERE run_id=%s AND role='assistant'",(run,))
            conn.execute('ALTER TABLE assistant_turns ENABLE TRIGGER assistant_turns_immutable')
            conn.execute('ALTER TABLE assistant_messages ENABLE TRIGGER assistant_messages_immutable')
        result=client.get(BASE+'/'+identifier,params=q)
        assert result.status_code==409,result.text
        assert client.post(BASE+'/'+identifier+'/messages',params=q,headers=h,json=dict(content='下一轮',consent_to_model=True,idempotency_key='after-corrupt')).status_code==409
        assert len(provider.calls)==1 and not container.planning_worker.tick()

def test_summary_second_correction_rejects_next_send_without_model_and_still_saves(setup):
    db,scope,cmd,container,current,provider=setup;q=dict(project_id=cmd.project_id)
    with TestClient(create_app(container)) as client:
        h=login(client,db,scope);v,_=start(client,q,h,cmd);identifier=v['conversation_id']
        for n,result in enumerate((FIRST,SECOND,final_value('summary'),final_value('summary')),1):
            v,_=run_turn(client,q,h,identifier,container,provider,result,n)
        assert len(provider.calls)==4
        result=client.post(BASE+'/'+identifier+'/messages',params=q,headers=h,json=dict(content='仍错误',consent_to_model=True,idempotency_key='blocked'))
        assert result.status_code==409 and len(provider.calls)==4 and not container.planning_worker.tick()
        result=client.post(BASE+'/'+identifier+'/save',params=q,headers=h,json=dict(content='本人正式原文',draft_message_id=v['current_draft_message_id'],expected_version=0,idempotency_key='manual-save'))
        assert result.status_code==200,result.text
        assert len(provider.calls)==4

def test_natural_unknown_blocks_new_conversation_and_no_retry(setup):
    db,scope,cmd,container,current,provider=setup;q=dict(project_id=cmd.project_id)
    with TestClient(create_app(container)) as client:
        h=login(client,db,scope);v,_=start(client,q,h,cmd);identifier=v['conversation_id']
        provider.outcome=LLMFailure('unknown','unknown',dispatch_unknown=True)
        send_natural(client,q,h,identifier,'原文','unknown')
        assert container.planning_worker.tick() and len(provider.calls)==1
        v=client.get(BASE+'/'+identifier,params=q).json()
        assert v['messages'][0]['run_status']=='reconciliation_required'
        other,_=start(client,q,h,cmd,key='new',force_new=True)
        assert client.post(BASE+'/'+other['conversation_id']+'/messages',params=q,headers=h,json=dict(content='原文',consent_to_model=True,idempotency_key='retry')).status_code==409
        assert not container.planning_worker.tick() and len(provider.calls)==1

def test_legacy_natural_frozen_payload_remains_legacy_without_backfill(setup):
    db,scope,cmd,container,current,provider=setup;q=dict(project_id=cmd.project_id)
    with TestClient(create_app(container)) as client:
        h=login(client,db,scope);v,_=start(client,q,h,cmd);identifier=v['conversation_id']
        # Explicit legacy intent establishes the pre-marker contract; natural followup must preserve it.
        body=dict(intent='work_draft',content='历史工作稿',consent_to_model=True,idempotency_key='legacy')
        assert client.post(BASE+'/'+identifier+'/messages',params=q,headers=h,json=body).status_code==202
        assert container.planning_worker.tick()
        send_natural(client,q,h,identifier,'自然续接','legacy-natural')
        assert container.planning_worker.tick()
        with psycopg.connect(db.migrator_dsn) as conn:
            payloads=conn.execute('SELECT payload FROM assistant_turns WHERE conversation_id=%s',(identifier,)).fetchall()
        assert len(payloads)==2 and all('teaching_contract' not in t[0] and 'teaching_state' not in t[0] for t in payloads)
        assert len(provider.calls)==2
