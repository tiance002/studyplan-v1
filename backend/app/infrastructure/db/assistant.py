"""Owner-scoped immutable conversation turns over the existing queue/fence."""
import base64
from datetime import datetime
from types import SimpleNamespace

from app.core.errors import ConflictError, IdempotencyConflictError, NotFoundError, ValidationAppError, VersionConflictError
from app.core.ids import content_hash, new_id
from app.domain.assistant import ASSISTANT_PROTOCOL, build_input, manifest_intact, validate_message, validate_reply
from app.domain.prompts import prompt_review_context
from app.domain.summaries import review_rubric_context
from app.infrastructure.db.learning_exposures import PgLearningExposures, _json
from app.infrastructure.db.planning_fence import lock_plan_version, lock_planning_write
from app.infrastructure.db.prompts import PgPrompts
from app.infrastructure.db.summaries import PgSummaries
from psycopg.types.json import Jsonb


class PgAssistant(PgSummaries):
    receipt_table = "assistant_receipts"

    @staticmethod
    def _conversation(conn, project, identifier):
        row = conn.execute("SELECT * FROM assistant_conversations WHERE project_id=%s AND conversation_id=%s", (project,identifier)).fetchone()
        if not row: raise NotFoundError("学习会话不存在")
        if content_hash(row["context"]) != row["context_hash"]: raise ConflictError("冻结会话依据不一致")
        return row

    @staticmethod
    def _current(conn, row):
        plan = PgLearningExposures._plan(conn,row["project_id"],row["plan_id"],current=True)
        if plan["revision"] != row["plan_revision"]: raise ConflictError("会话路线版本已改变，只能阅读旧会话")

    def _view(self, conn, row, before_sequence=None, *, include_messages=True):
        project, identifier = row["project_id"],row["conversation_id"]
        result={k:row[k] for k in ('conversation_id','project_id','plan_id','plan_revision','stage_id','task_id','mode','title','context','context_hash','created_at','current_draft_message_id')}
        try: self._current(conn,row); result['read_only']=False
        except (ConflictError, NotFoundError, ValidationAppError, VersionConflictError): result['read_only']=True
        messages=conn.execute("""SELECT m.*,coalesce(r.status,CASE WHEN m.delivery_error IS NOT NULL THEN 'failed' END) AS run_status,r.version AS run_version,coalesce(r.error_class,m.delivery_error) AS error_class
            FROM assistant_messages m LEFT JOIN ai_runs r USING(run_id)
            WHERE m.project_id=%s AND m.conversation_id=%s AND (%s::integer IS NULL OR m.sequence<%s)
            ORDER BY m.sequence DESC LIMIT 121""",(project,identifier,before_sequence,before_sequence)).fetchall() if include_messages else []
        result['messages_truncated']=len(messages)>120
        result['message_cursor']=messages[119]['sequence'] if len(messages)>120 else None
        result['messages']=list(reversed(messages[:120]))
        if include_messages and before_sequence is None and row['current_draft_message_id'] and not any(m['message_id']==row['current_draft_message_id'] for m in result['messages']):
            draft=conn.execute("""SELECT m.*,r.status AS run_status,r.version AS run_version,r.error_class FROM assistant_messages m LEFT JOIN ai_runs r USING(run_id)
                WHERE m.message_id=%s AND m.conversation_id=%s""",(row['current_draft_message_id'],identifier)).fetchone()
            if draft: result['messages'].insert(0,draft)
        result['formal_saves']=conn.execute("SELECT * FROM assistant_formal_saves WHERE project_id=%s AND conversation_id=%s AND status='succeeded' ORDER BY created_at DESC,save_id DESC LIMIT 20",(project,identifier)).fetchall() if include_messages else []
        if row['mode']=='summary':
            result['formal_version']=self._stage_thread(conn,(project,row['plan_id'],row['stage_id'],None))['version']
        else:
            head=conn.execute("SELECT version FROM prompt_position_heads WHERE project_id=%s AND plan_id=%s AND stage_id=%s AND task_id=%s",(project,row['plan_id'],row['stage_id'],row['task_id'])).fetchone()
            result['formal_version']=head['version'] if head else 0
        return _json(result)

    def get(self,scope,project,identifier,before_sequence=None):
        with self._tx(scope,project) as conn: return self._view(conn,self._conversation(conn,project,identifier),before_sequence)

    def list(self,scope,project,cursor=None,limit=20):
        if not 1<=limit<=100: raise ValidationAppError('会话分页范围无效')
        params=[project,scope.actor_id]; condition=''
        if cursor:
            try:
                stamp,identifier=base64.urlsafe_b64decode(cursor.encode()).decode().split('|',1)
                datetime.fromisoformat(stamp)
            except Exception: raise ValidationAppError('会话分页游标无效') from None
            condition=' AND (created_at,conversation_id)<(%s,%s)'; params.extend((stamp,identifier))
        with self._tx(scope,project) as conn:
            rows=conn.execute('SELECT * FROM assistant_conversations WHERE project_id=%s AND actor_id=%s'+condition+' ORDER BY created_at DESC,conversation_id DESC LIMIT %s',(*params,limit+1)).fetchall()
            items=[]
            for row in rows[:limit]:
                view=self._view(conn,row,include_messages=False); view.pop('messages'); view.pop('formal_saves'); items.append(view)
            next_cursor=base64.urlsafe_b64encode((rows[limit-1]['created_at'].isoformat()+'|'+rows[limit-1]['conversation_id']).encode()).decode() if len(rows)>limit else None
            return dict(items=items,next_cursor=next_cursor)

    def create(self,scope,project,body):
        fingerprint=content_hash(body); key=body['idempotency_key']
        with self._tx(scope,project,write=True) as conn:
            prior=self._receipt(conn,scope,project,key,'create',fingerprint)
            if prior: return self._view(conn,self._conversation(conn,project,prior['conversation_id']))
            plan=PgLearningExposures._plan(conn,project,body['plan_id'],current=True)
            command=SimpleNamespace(position=(project,body['plan_id'],body['stage_id'],None),project_id=project,plan_id=body['plan_id'],stage_id=body['stage_id'])
            stage=self._stage(conn,command.position)
            if body['mode']=='summary' and body.get('task_id') is None:
                context=review_rubric_context(self._stage_snapshot(conn,command,plan,stage))
                title='阶段总结 · '+stage['title']
            elif body['mode']=='practice' and body.get('task_id'):
                _,task=PgPrompts._context(conn,(project,body['plan_id'],body['stage_id'],body['task_id']))
                context=prompt_review_context(dict(task=task)); title='实践 Prompt · '+task['title']
            else: raise ValidationAppError('总结必须绑定阶段；实践必须绑定明确任务')
            identifier=new_id('aconv')
            conn.execute("""INSERT INTO assistant_conversations(conversation_id,project_id,actor_id,plan_id,plan_revision,stage_id,task_id,mode,title,context,context_hash)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",(identifier,project,scope.actor_id,body['plan_id'],plan['revision'],body['stage_id'],body.get('task_id'),body['mode'],title,Jsonb(context),content_hash(context)))
            self._record(conn,scope,project,key,'create',fingerprint,{'conversation_id':identifier})
            return self._view(conn,self._conversation(conn,project,identifier))

    def message_receipt(self,scope,project,identifier,body):
        with self._tx(scope,project) as conn:
            self._conversation(conn,project,identifier)
            prior=self._receipt(conn,scope,project,body['idempotency_key'],'message',content_hash(dict(conversation_id=identifier,**body)))
            return self._view(conn,self._conversation(conn,project,identifier)) if prior else None

    def send(self,scope,project,identifier,body,manifest,error=None):
        validate_message(body['intent'],body['content'])
        fingerprint=content_hash(dict(conversation_id=identifier,**body)); key=body['idempotency_key']
        with self._tx(scope,project,write=True) as conn:
            row=self._conversation(conn,project,identifier)
            prior=self._receipt(conn,scope,project,key,'message',fingerprint)
            if prior: return self._view(conn,row)
            self._current(conn,row)
            if body.get('consent_to_model') is not True: raise ValidationAppError('发送需要明确模型许可')
            if error is None and not manifest_intact(manifest): raise ValidationAppError('发送需要完整预算协议')
            # Scope-level unknown blocks even a newly created conversation/key.
            active=conn.execute("""SELECT r.status,b.conversation_id FROM assistant_turns b JOIN ai_runs r USING(run_id)
                JOIN assistant_conversations c ON c.conversation_id=b.conversation_id
                WHERE b.project_id=%s AND b.actor_id=%s AND r.status IN('queued','running','reconciliation_required')
                AND (b.conversation_id=%s OR (
                    c.plan_id=%s AND c.stage_id=%s AND c.mode=%s AND c.task_id IS NOT DISTINCT FROM %s
                    AND (r.status='reconciliation_required' OR (
                        EXISTS(SELECT 1 FROM ai_jobs j WHERE j.run_id=r.run_id AND j.status='running' AND j.lease_expires_at<=clock_timestamp())
                        AND EXISTS(SELECT 1 FROM ai_provider_attempts a WHERE a.run_id=r.run_id AND a.status IN('dispatched','reconciliation_required'))
                    ))
                ))""",(project,scope.actor_id,identifier,row['plan_id'],row['stage_id'],row['mode'],row['task_id'])).fetchone()
            if active: raise ConflictError('此会话已有活动回复，或相同位置有未知请求需要核对')
            count=conn.execute("SELECT count(*) AS n FROM ai_runs WHERE project_id=%s AND actor_id=%s AND kind IN('summary_review','prompt_review','assistant_reply') AND status IN('queued','running','reconciliation_required')",(project,scope.actor_id)).fetchone()['n']
            if count>=3: raise ConflictError('当前学习空间已有三个待处理反馈任务')
            messages=conn.execute('SELECT * FROM assistant_messages WHERE project_id=%s AND conversation_id=%s ORDER BY sequence',(project,identifier)).fetchall()
            draft=next((m for m in messages if m['message_id']==row['current_draft_message_id']),None)
            if body['intent']=='question' and draft is None: raise ValidationAppError('追问需要先提交本会话工作稿')
            message_id=new_id('amsg'); run_id=new_id('run')
            trigger=dict(message_id=message_id,intent=body['intent'],content=body['content'])
            if body['intent']=='work_draft': draft=trigger
            pairs=[]
            for reply in [m for m in messages if m['role']=='assistant'][-6:]:
                original=next(m for m in messages if m['message_id']==reply['trigger_message_id'])
                pairs.extend((original,reply))
            projected_draft={k:draft[k] for k in ('message_id','content')} if draft else None
            try: payload=build_input(row['mode'],row['context'],projected_draft,trigger,pairs)
            except ValidationAppError:
                error='assistant_input_too_large'; payload=None
            seq=max((m['sequence'] for m in messages),default=0)+1
            if error:
                conn.execute("""INSERT INTO assistant_messages(message_id,project_id,conversation_id,sequence,role,intent,content,draft_message_id,delivery_error)
                    VALUES(%s,%s,%s,%s,'user',%s,%s,%s,%s)""",(message_id,project,identifier,seq,body['intent'],body['content'],draft['message_id'] if draft else None,error))
                if body['intent']=='work_draft': conn.execute('UPDATE assistant_conversations SET current_draft_message_id=%s WHERE conversation_id=%s',(message_id,identifier))
                self._record(conn,scope,project,key,'message',fingerprint,dict(run_id=None,message_id=message_id))
                return self._view(conn,self._conversation(conn,project,identifier))
            conn.execute("INSERT INTO ai_runs(run_id,actor_id,project_id,kind,graph_name,graph_version,status,next_action,thread_id) VALUES(%s,%s,%s,'assistant_reply','assistant_coaching_graph',%s,'queued','wait',%s)",(run_id,scope.actor_id,project,ASSISTANT_PROTOCOL,run_id+'::'+ASSISTANT_PROTOCOL))
            conn.execute("""INSERT INTO assistant_messages(message_id,project_id,conversation_id,sequence,role,intent,content,run_id,draft_message_id)
                VALUES(%s,%s,%s,%s,'user',%s,%s,%s,%s)""",(message_id,project,identifier,seq,body['intent'],body['content'],run_id,draft['message_id'] if draft else None))
            conn.execute("INSERT INTO assistant_turns(run_id,project_id,actor_id,conversation_id,trigger_message_id,draft_message_id,context_hash,manifest,payload,payload_hash) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (run_id,project,scope.actor_id,identifier,message_id,draft['message_id'] if draft else None,row['context_hash'],Jsonb(manifest),Jsonb(payload),content_hash(payload)))
            if body['intent']=='work_draft': conn.execute('UPDATE assistant_conversations SET current_draft_message_id=%s WHERE conversation_id=%s',(message_id,identifier))
            submission=dict(kind='assistant_reply_submission',actor_id=scope.actor_id,project_id=project,conversation_id=identifier,trigger_message_id=message_id,manifest=manifest,payload_hash=content_hash(payload))
            conn.execute("INSERT INTO ai_run_events(run_id,status,detail) VALUES(%s,'submission',%s)",(run_id,Jsonb(submission)))
            conn.execute("INSERT INTO ai_jobs(job_id,run_id,job_key,status) VALUES(%s,%s,%s,'pending')",(new_id('job'),run_id,'assistant:'+run_id))
            self._record(conn,scope,project,key,'message',fingerprint,dict(run_id=run_id,message_id=message_id))
            return self._view(conn,self._conversation(conn,project,identifier))

    def turn(self,claim):
        with self._tx(self._claim_scope(claim),claim.project_id,write=True,fenced=True) as conn:
            lock_planning_write(conn,project_id=claim.project_id,run_id=claim.run_id,fence=self._fence(claim))
            row=conn.execute("SELECT b.* FROM assistant_turns b JOIN ai_runs r USING(run_id) WHERE b.run_id=%s AND b.project_id=%s AND b.actor_id=%s AND r.kind='assistant_reply' AND r.graph_version=%s",(claim.run_id,claim.project_id,claim.actor_id,ASSISTANT_PROTOCOL)).fetchone()
            if not row or not manifest_intact(row['manifest']) or content_hash(row['payload'])!=row['payload_hash']: raise ValidationAppError('助手冻结合同缺失或不一致')
            events=conn.execute("SELECT detail FROM ai_run_events WHERE run_id=%s AND status='submission'",(claim.run_id,)).fetchall()
            expected=dict(kind='assistant_reply_submission',actor_id=claim.actor_id,project_id=claim.project_id,
                conversation_id=row['conversation_id'],trigger_message_id=row['trigger_message_id'],manifest=row['manifest'],payload_hash=row['payload_hash'])
            if len(events)!=1 or events[0]['detail']!=expected: raise ValidationAppError('助手独立冻结提交不一致')
            trigger=conn.execute("SELECT * FROM assistant_messages WHERE message_id=%s AND conversation_id=%s AND project_id=%s AND role='user'",(row['trigger_message_id'],row['conversation_id'],claim.project_id)).fetchone()
            if not trigger or row['payload']['current_message']!={k:trigger[k] for k in ('message_id','intent','content')} or trigger['draft_message_id']!=row['draft_message_id']: raise ValidationAppError('助手触发原文不一致')
            if row['draft_message_id']:
                draft=conn.execute("SELECT message_id,content FROM assistant_messages WHERE message_id=%s AND conversation_id=%s AND project_id=%s AND role='user' AND intent='work_draft'",(row['draft_message_id'],row['conversation_id'],claim.project_id)).fetchone()
                if not draft or row['payload']['work_draft']!=draft: raise ValidationAppError('助手工作稿绑定不一致')
            elif row['payload']['work_draft'] is not None: raise ValidationAppError('助手工作稿绑定不一致')
            convo=self._conversation(conn,claim.project_id,row['conversation_id'])
            if row['context_hash']!=convo['context_hash'] or row['payload']['context']!=convo['context']: raise ValidationAppError('助手冻结上下文不一致')
            return row

    def finish(self,claim,turn,reply=None,error=None,unknown=False):
        with self._tx(self._claim_scope(claim),claim.project_id,write=True,fenced=True) as conn:
            lock_planning_write(conn,project_id=claim.project_id,run_id=claim.run_id,fence=self._fence(claim))
            run=conn.execute("SELECT kind,graph_version FROM ai_runs WHERE run_id=%s",(claim.run_id,)).fetchone()
            if run['kind']!='assistant_reply' or run['graph_version']!=ASSISTANT_PROTOCOL:
                raise ValidationAppError('助手终态协议不一致')
            if turn is not None:
                self._conversation(conn,claim.project_id,turn['conversation_id'])
            identifier=None
            if reply is not None:
                if validate_reply(reply): raise ValidationAppError('助手回复格式无效')
                identifier=new_id('amsg')
                seq=conn.execute('SELECT coalesce(max(sequence),0)+1 AS n FROM assistant_messages WHERE conversation_id=%s',(turn['conversation_id'],)).fetchone()['n']
                conn.execute("""INSERT INTO assistant_messages(message_id,project_id,conversation_id,sequence,role,intent,content,run_id,draft_message_id,trigger_message_id)
                    VALUES(%s,%s,%s,%s,'assistant','reply',%s,%s,%s,%s)""",(identifier,claim.project_id,turn['conversation_id'],seq,reply['reply'],claim.run_id,turn['draft_message_id'],turn['trigger_message_id']))
            status='succeeded' if identifier else ('reconciliation_required' if unknown else 'failed')
            conn.execute("UPDATE ai_runs SET status=%s,next_action=%s,result_ref=%s,error_class=%s,version=version+1,updated_at=clock_timestamp() WHERE run_id=%s",(status,'reconcile' if unknown else 'none',identifier,error,claim.run_id))
            conn.execute('UPDATE ai_jobs SET status=%s,lease_token=NULL,lease_expires_at=NULL WHERE job_id=%s',('completed' if identifier else ('reconciliation_required' if unknown else 'failed'),claim.job_id))
            return identifier or ''

    def reserve_save(self,scope,project,identifier,body):
        fingerprint=content_hash(dict(conversation_id=identifier,**body))
        with self._tx(scope,project,write=True) as conn:
            row=self._conversation(conn,project,identifier)
            prior=conn.execute('SELECT * FROM assistant_formal_saves WHERE project_id=%s AND actor_id=%s AND idempotency_key=%s',(project,scope.actor_id,body['idempotency_key'])).fetchone()
            if prior:
                if prior['input_hash']!=fingerprint: raise IdempotencyConflictError()
                if prior['status']=='failed': raise ConflictError('此正式保存已拒绝；请读取当前版本后明确重新保存')
                return row,prior
            self._current(conn,row)
            draft=conn.execute("SELECT * FROM assistant_messages WHERE project_id=%s AND conversation_id=%s AND message_id=%s AND role='user' AND intent='work_draft'",(project,identifier,body['draft_message_id'])).fetchone()
            if not draft: raise ValidationAppError('正式保存必须选择本会话的用户工作稿')
            pending=conn.execute("SELECT 1 FROM assistant_formal_saves WHERE project_id=%s AND conversation_id=%s AND status='pending'",(project,identifier)).fetchone()
            if pending: raise ConflictError('已有正式保存回执待恢复；请用原幂等键读取结果')
            save_id=new_id('asave')
            conn.execute("""INSERT INTO assistant_formal_saves(save_id,project_id,actor_id,conversation_id,draft_message_id,content,expected_version,idempotency_key,input_hash,artifact_type,status)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'pending')""",(save_id,project,scope.actor_id,identifier,body['draft_message_id'],body['content'],body['expected_version'],body['idempotency_key'],fingerprint,'summary' if row['mode']=='summary' else 'prompt'))
            return row,dict(save_id=save_id,status='pending')

    def save_outcome(self,scope,project,save_id,artifact=None):
        with self._tx(scope,project,write=True) as conn:
            if artifact:
                identifier=artifact.get('attempt_id') or artifact['revision_id']
                conn.execute("UPDATE assistant_formal_saves SET artifact_id=%s,formal_version=%s,status='succeeded' WHERE project_id=%s AND save_id=%s AND status='pending'",(identifier,artifact['version'],project,save_id))
            else: conn.execute("UPDATE assistant_formal_saves SET status='failed' WHERE project_id=%s AND save_id=%s AND status='pending'",(project,save_id))

    def cancel(self,scope,project,identifier,body):
        fingerprint=content_hash(dict(conversation_id=identifier,**body))
        with self._tx(scope,project,fenced=True) as conn:
            conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',('studyplan:plan-budget:'+body['run_id'],))
            lock_plan_version(conn,project,None)
            self._conversation(conn,project,identifier)
            prior=self._receipt(conn,scope,project,body['idempotency_key'],'cancel',fingerprint)
            if not prior:
                run=conn.execute("SELECT r.* FROM ai_runs r JOIN ai_jobs j USING(run_id) JOIN assistant_turns t USING(run_id) WHERE r.project_id=%s AND r.actor_id=%s AND t.conversation_id=%s AND r.run_id=%s FOR UPDATE OF j,r",(project,scope.actor_id,identifier,body['run_id'])).fetchone()
                if not run: raise NotFoundError('助手运行不存在')
                if run['version']!=body['expected_version']: raise VersionConflictError(expected_version=body['expected_version'],actual_version=run['version'])
                if run['status'] not in ('queued','running'): raise ConflictError('助手运行已经结束或需要核对')
                possible=conn.execute("SELECT 1 FROM ai_provider_attempts WHERE run_id=%s AND status IN('dispatched','reconciliation_required')",(body['run_id'],)).fetchone()
                status='reconciliation_required' if possible else 'cancelled'
                conn.execute("UPDATE ai_runs SET status=%s,next_action=%s,error_class=%s,version=version+1,updated_at=clock_timestamp() WHERE run_id=%s",(status,'reconcile' if possible else 'none','provider_dispatch_unknown' if possible else None,body['run_id']))
                conn.execute('UPDATE ai_jobs SET status=%s,lease_token=NULL,lease_expires_at=NULL WHERE run_id=%s',(status,body['run_id']))
                self._record(conn,scope,project,body['idempotency_key'],'cancel',fingerprint,dict(run_id=body['run_id']))
            return self._view(conn,self._conversation(conn,project,identifier))
