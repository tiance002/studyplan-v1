import {useEffect,useRef,useState} from 'react';
import type {AssistantController} from '../features/learning/useAssistant';
import {assistantTargetTitle,practiceWelcome,summaryWelcome} from '../features/learning/assistantState';
import {restoreAssistantFocus} from './assistantFocus';
const failureReasons:Record<string,string>={assistant_binding_unavailable:'请先核对模型设置。',assistant_worker_unavailable:'辅导服务暂不可用。',assistant_input_too_large:'请缩短本次输入后再发送。'};
export function LearningAssistantPanel({close,controller:a}:{close:()=>void;controller:AssistantController}) {
  const input=useRef<HTMLTextAreaElement>(null),panel=useRef<HTMLElement>(null),bottom=useRef<HTMLDivElement>(null);
  const [menu,setMenu]=useState(false);
  useEffect(()=>{const previous=document.activeElement as HTMLElement|null,currentPanel=panel.current;input.current?.focus();return()=>restoreAssistantFocus(previous,currentPanel,document.querySelector<HTMLElement>('[data-assistant-entry]'));},[]);
  const c=a.conversation,b=a.buffer,welcome=c?.mode==='practice'?practiceWelcome:summaryWelcome;
  useEffect(()=>{if(c)input.current?.focus();},[c?.conversation_id]);
  useEffect(()=>{bottom.current?.scrollIntoView({block:'nearest'});},[c?.conversation_id,c?.messages.at(-1)?.sequence]);
  const saveProposal=(messageId:string,content:string)=>void a.save({content,proposal_message_id:messageId,expected_version:c!.formal_version,idempotency_key:crypto.randomUUID()});
  const saveDisabled=!c||c.read_only||b.busy||!!b.save||!!b.saveConflict;
  return <aside ref={panel} className="assistant-panel assistant-chat" aria-label="学习助手" onKeyDown={e=>{if(e.key==='Escape'){e.stopPropagation();if(menu)setMenu(false);else close();}if(e.key==='Tab'&&window.innerWidth<960){const elements=panel.current?.querySelectorAll<HTMLElement>('button:not(:disabled),textarea:not(:disabled),[tabindex="0"]');if(elements?.length){const first=elements[0],last=elements[elements.length-1];if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}}}}}>
    <header className="assistant-top"><div><strong>学习助手</strong>{c&&<small>{c.mode==='summary'?'阶段总结':'实践辅导'} · {assistantTargetTitle(c)}</small>}</div><button className="icon-button assistant-menu-toggle" aria-label="会话菜单" aria-expanded={menu} onClick={()=>setMenu(!menu)}>…</button><button className="icon-button" aria-label="关闭学习助手" onClick={close}>×</button></header>
    {menu&&<div className="assistant-menu" aria-label="会话操作">{c&&<><button className="text-button" disabled={c.read_only||a.starting||!!a.startPending} onClick={()=>{setMenu(false);void a.start({plan_id:c.plan_id,stage_id:c.stage_id,task_id:c.task_id,mode:c.mode,force_new:true});}}>新建会话</button><button className="text-button" onClick={()=>{setMenu(false);void a.read();}}>重新读取状态</button>{a.run?.run_id&&['queued','running'].includes(a.run.run_status||'')&&<button className="text-button" disabled={b.busy||a.run.run_version===null||!!b.cancel} onClick={()=>{setMenu(false);void a.cancel({run_id:a.run!.run_id!,expected_version:a.run!.run_version!,idempotency_key:crypto.randomUUID()});}}>取消回复</button>}</>}</div>}
    <div className="assistant-scroll" role="log" aria-live="polite">
      {a.listError&&<p className="assistant-inline-state" role="alert">{a.listError}</p>}{a.startPending&&<button className="text-button" disabled={a.starting} onClick={()=>void a.start(a.startPending!)}>重新读取状态</button>}
      {c?<>{c.read_only&&<p className="assistant-inline-state" role="status">这是旧路线的会话，当前只能查看。</p>}
      <article className="assistant-message assistant assistant-welcome"><strong>{welcome.title}</strong><p>我会重点检查：</p><ul>{welcome.checks.map(v=><li key={v}>{v}</li>)}</ul></article>
      {c.messages_truncated&&c.message_cursor!==null&&<button className="text-button" disabled={b.historyBusy} onClick={()=>void a.earlier()}>{b.historyBusy?'正在读取…':'读取较早消息'}</button>}
      {c.messages.map(m=>{const editing=b.proposalEdits?.[m.message_id]!==undefined;const saved=c.formal_saves.filter(s=>s.proposal_message_id===m.message_id);return <article className={`assistant-message ${m.role}`} key={m.message_id}>
        <span className="assistant-speaker">{m.role==='assistant'?'学习助手':'你'}</span><div className="assistant-message-text">{m.content}</div>
        {m.role==='user'&&['queued','running'].includes(m.run_status||'')&&<p className="assistant-inline-state" role="status">正在思考…</p>}
        {m.role==='user'&&m.run_status==='failed'&&<p className="assistant-inline-state" role="status">⚠ 这次回复生成失败，你的消息已经保存。{m.error_class?failureReasons[m.error_class]||'':''}</p>}
        {m.role==='user'&&['unknown','reconciliation_required'].includes(m.run_status||'')&&<p className="assistant-inline-state" role="status">⚠ 这次回复状态正在核对，暂时不能重新发送。</p>}
        {m.role==='user'&&['cancelled','canceled'].includes(m.run_status||'')&&<p className="assistant-inline-state" role="status">回复已取消。</p>}
        {m.role==='assistant'&&m.status==='ready_to_draft'&&m.proposal&&<section className="assistant-proposal" aria-label={c.mode==='summary'?'建议阶段总结':'建议最终 Prompt'}><h3>{c.mode==='summary'?'建议阶段总结':'建议最终 Prompt'}</h3><div className="assistant-message-text">{m.proposal}</div><div className="chips"><button className="btn primary" disabled={saveDisabled} onClick={()=>saveProposal(m.message_id,m.proposal!)}>采用并保存</button><button className="btn quiet" disabled={c.read_only||b.busy} onClick={()=>a.update({proposalEdits:{...b.proposalEdits,[m.message_id]:b.proposalEdits?.[m.message_id]??m.proposal!}})}>修改后保存</button></div>
          {editing&&<div className="assistant-proposal-editor"><textarea aria-label="我的候选版本" rows={7} value={b.proposalEdits![m.message_id]} onChange={e=>a.update({proposalEdits:{...b.proposalEdits,[m.message_id]:e.target.value}})}/><button className="btn primary" disabled={saveDisabled||!b.proposalEdits![m.message_id].trim()||Array.from(b.proposalEdits![m.message_id]).length>20000} onClick={()=>saveProposal(m.message_id,b.proposalEdits![m.message_id])}>保存我的版本</button></div>}
          {saved.length>0&&<p className="assistant-inline-state" role="status">已保存{c.mode==='summary'?'阶段总结':'任务 Prompt'}。</p>}
        </section>}
      </article>;})}
      {b.error&&<p className="assistant-inline-state" role="alert">{b.error}</p>}{b.saveConflict&&<div className="assistant-inline-state"><p>正式内容已在其他位置更新。你的版本仍保留，请核对后再保存。</p><button className="text-button" onClick={()=>void a.read()}>重新读取状态</button></div>}{b.save&&<button className="text-button" disabled={b.busy||c.read_only} onClick={()=>void a.save(b.save!)}>核对保存结果</button>}{b.send&&<button className="text-button" disabled={b.busy||a.blocked} onClick={()=>void a.send(b.send!)}>核对发送结果</button>}{b.cancel&&<button className="text-button" disabled={b.busy} onClick={()=>void a.cancel(b.cancel!)}>核对取消结果</button>}
      </>:<p className="muted">从阶段的「开始总结」或具体任务的「开始实践」进入，也可打开已有会话。</p>}
      <div ref={bottom}/>
    </div>
    {c&&<form className="assistant-compose" onSubmit={e=>{e.preventDefault();if(!b.busy&&!a.blocked&&!b.send&&b.text.trim())void a.send({content:b.text,idempotency_key:crypto.randomUUID()});}}><textarea ref={input} aria-label="助手输入框" rows={3} value={b.text} onChange={e=>a.update({text:e.target.value})} placeholder={c.read_only?'此会话只读':'发消息…'} disabled={c.read_only}/><button className="btn primary" type="submit" disabled={b.busy||a.blocked||!!b.send||!b.text.trim()} aria-label="发送">{b.busy?'发送中…':'发送'}</button></form>}
  </aside>;
}
