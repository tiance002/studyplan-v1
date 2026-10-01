import { useEffect, useRef, useState } from 'react';
import { api, ApiError } from '../../api/client';
import { promptApi } from '../../api/promptClient';
import type { PromptCancelBody, PromptExport, PromptExportBody, PromptReviewBody, PromptRevision, PromptSaveBody, PromptTarget, PromptTask, PromptThread } from '../../api/promptClient';
import type { DTO } from '../../api/types';

const terminal = new Set(['succeeded','failed','cancelled','canceled','unknown','reconciliation_required']);
const errorText = (e: unknown) => e instanceof Error ? e.message : '操作未完成，请核对保存记录。';
const targetKey = (t: PromptTarget) => `${t.plan_id}/${t.stage_id}/${t.task_id}`;
type Buffer = {text: string; baseline: string; edit: number; initialized: boolean; thread?: PromptThread; pending?: PromptSaveBody; busy?: boolean; conflict?: boolean; error?: string};
const fresh = (): Buffer => ({text:'',baseline:'',edit:0,initialized:false});
function keepRevision(old: PromptRevision|undefined, next: PromptRevision): PromptRevision {
  if (!old) return next;
  if (old.review && !next.review) return {...next, review:old.review,run_id:old.run_id,run_status:old.run_status};
  if (old.run_id === next.run_id && terminal.has(old.run_status || '') && !terminal.has(next.run_status || '')) return {...next,run_status:old.run_status};
  return next;
}
function Requirements({task}: {task: PromptTask}) {
  return <div className="prompt-requirements"><h3>{task.title}</h3><p>{task.goal}</p>
    {([['实施范围',task.in_scope],['范围之外',task.out_scope],['验收要求',task.acceptance]] as const).map(([label,items]) => <div key={label}><h4>{label}</h4>{items.length ? <ul>{items.map((v,i) => <li key={i}>{v}</li>)}</ul> : <p>没有补充条目。</p>}</div>)}
    <h4>关联知识</h4>{task.knowledge_links.length ? <ul>{task.knowledge_links.map(n => <li key={n.node_id}>{n.title}（{({core:'核心',supporting:'支撑',extension:'延伸'} as Record<string,string>)[n.role] || '关联知识'}）</li>)}</ul> : <p>没有可核对的关联知识记录。</p>}
  </div>;
}
function Snapshot({value}: {value: Record<string,unknown>}) {
  const task = (value.task || value.task_snapshot) as Partial<PromptTask>|undefined;
  const project = (value.practice_project || value.practice_project_snapshot) as {title?:string;idea?:string}|undefined;
  const title = value.task_title || task?.title;
  const list = (v: unknown) => Array.isArray(v) ? v.filter((x):x is string => typeof x === 'string') : [];
  const links = (value.knowledge_links || task?.knowledge_links) as PromptTask['knowledge_links']|undefined;
  return <div className="prompt-snapshot">
    {project?.title && <p>当时主项目：{project.title}</p>}{project?.idea && <p>{project.idea}</p>}
    {typeof value.plan_revision === 'number' && <p>当时路线：第 {value.plan_revision} 版</p>}
    {typeof title === 'string' ? <h4>{title}</h4> : <p>旧记录未保存可核对的当时任务要求；不会用当前任务补写历史。</p>}
    {typeof (value.goal || task?.goal) === 'string' && <p>{String(value.goal || task?.goal)}</p>}
    {(['in_scope','out_scope','acceptance'] as const).map(k => <div key={k}><h4>{{in_scope:'当时实施范围',out_scope:'当时范围之外',acceptance:'当时验收要求'}[k]}</h4>{list(value[k] || task?.[k]).length ? <ul>{list(value[k] || task?.[k]).map((v,i) => <li key={i}>{v}</li>)}</ul> : <p>没有可核对的条目。</p>}</div>)}
    {Array.isArray(links) && <p>当时关联知识：{links.map(n => n.title).filter(Boolean).join('、') || '无记录'}</p>}
    <p className="form-note">任务与知识关联来自保存时的要求，不代表已经实现、测试或验收。</p>
  </div>;
}
function LegacyReview({revision}: {revision: PromptRevision}) {
  if (!revision.legacy_review) return null;
  const collect = (v: unknown, depth=0): string[] => depth>4 ? [] : typeof v === 'string' ? [v] : Array.isArray(v) ? v.slice(0,20).flatMap(x=>collect(x,depth+1)) : v && typeof v==='object' ? Object.entries(v).slice(0,20).filter(([k])=>!k.endsWith('_id')).flatMap(([,x])=>collect(x,depth+1)) : [];
  return <section><h4>历史反馈原文</h4><p>以下按旧格式保留，没有补写新的结论。</p>{[...new Set(collect(revision.legacy_review))].map((v,i)=><p className="prompt-original" key={i}>{v}</p>)}</section>;
}

export function PromptPage({project,workspace,initialStage,active=true}: {project:string;workspace:DTO['LearningWorkspaceView']|null;initialStage:string;active?:boolean}) {
  const [stageChoice,setStageChoice]=useState(initialStage), [taskChoice,setTaskChoice]=useState('');
  const stage=workspace?.stages.find(s=>s.stage.stage_id===stageChoice)||workspace?.stages[0];
  const task=stage?.tasks.find(t=>t.task_id===taskChoice)||stage?.tasks[0];
  const target=workspace && stage && task ? {plan_id:workspace.plan.plan_id,stage_id:stage.stage.stage_id,task_id:task.task_id} : null;
  const key=target ? targetKey(target) : '';
  const currentKey=useRef(key);currentKey.current=key;
  const selectionSequence=useRef(0);
  const [buffers,setBuffers]=useState<Record<string,Buffer>>({}), [revisions,setRevisions]=useState<Record<string,PromptRevision>>({});
  const buffersRef=useRef(buffers);buffersRef.current=buffers;
  const sequence=useRef<Record<string,number>>({}), alive=useRef(true);
  const [selected,setSelected]=useState(''), [history,setHistory]=useState<string[]>([]), [cursor,setCursor]=useState<string|null>(null), [historyBusy,setHistoryBusy]=useState(false), [historyError,setHistoryError]=useState('');
  function choose(id:string){selectionSequence.current++;setSelected(id);}
  const b=buffers[key]||fresh();
  function update(k:string, fn:(old:Buffer)=>Buffer) {if(alive.current)setBuffers(old=>{const next={...old,[k]:fn(old[k]||fresh())};buffersRef.current=next;return next;});}
  function put(values:PromptRevision[]) {if(alive.current)setRevisions(old=>{const next={...old};for(const v of values)next[v.revision_id]=keepRevision(old[v.revision_id],v);return next;});}
  useEffect(()=>{alive.current=true;return()=>{alive.current=false;};},[]);
  async function read(k:string,t:PromptTarget,initial=false) {
    const ticket=sequence.current[k]=(sequence.current[k]||0)+1, edit=buffersRef.current[k]?.edit||0, selectionTicket=selectionSequence.current;
    try {const thread=await promptApi.thread(project,t);if(!alive.current||sequence.current[k]!==ticket)return;
      const old=buffersRef.current[k];if(old?.thread && old.thread.version>thread.version)return;
      put(thread.revisions);update(k,prev=>({...prev,thread,initialized:true,error:'',conflict:false,
        ...(initial && !prev.initialized && prev.edit===edit ? {text:thread.revisions.at(-1)?.user_draft||'',baseline:thread.revisions.at(-1)?.user_draft||''}:{}),
        ...(prev.conflict ? {pending:undefined}: {})}));
      if(initial && thread.revisions.length && currentKey.current===k && selectionSequence.current===selectionTicket)choose(thread.revisions.at(-1)!.revision_id);
    } catch(e){if(sequence.current[k]===ticket)update(k,old=>({...old,error:errorText(e)}));}
  }
  useEffect(()=>{if(key)choose(buffersRef.current[key]?.thread?.revisions.at(-1)?.revision_id||'');},[key]);
  useEffect(()=>{if(key&&target&&active&&!buffersRef.current[key]?.initialized)void read(key,target,true);},[key,active]);
  const dirty=Object.values(buffers).some(v=>v.text!==v.baseline);
  useEffect(()=>{const warn=(e:BeforeUnloadEvent)=>{if(dirty){e.preventDefault();e.returnValue='';}};window.addEventListener('beforeunload',warn);return()=>window.removeEventListener('beforeunload',warn);},[dirty]);
  async function save(k:string,body:PromptSaveBody) {
    const selectionTicket=selectionSequence.current;
    sequence.current[k]=(sequence.current[k]||0)+1;update(k,old=>({...old,pending:body,busy:true,error:''}));
    try {const result=await promptApi.save(project,body);if(!alive.current)return;put(result.thread.revisions);put([result.revision]);
      update(k,old=>({...old,thread:old.thread && old.thread.version>result.thread.version ? old.thread:result.thread,baseline:body.user_draft,pending:undefined,conflict:false,initialized:true}));
      // Keep completion tied to this position even if navigation occurs mid-save.
      if(currentKey.current===k && selectionSequence.current===selectionTicket)choose(result.revision.revision_id);
    }catch(e){update(k,old=>({...old,error:errorText(e),conflict:e instanceof ApiError&&e.status===409}));}
    finally{sequence.current[k]=(sequence.current[k]||0)+1;update(k,old=>({...old,busy:false}));}
  }
  async function readHistory(more=false) {
    setHistoryBusy(true);setHistoryError('');try{const result=await promptApi.history(project,more?cursor||undefined:undefined);if(!alive.current)return;put(result.items);setHistory(old=>more?[...new Set([...old,...result.items.map(r=>r.revision_id)])]:result.items.map(r=>r.revision_id));setCursor(result.next_cursor);}
    catch(e){if(alive.current)setHistoryError(errorText(e));}finally{if(alive.current)setHistoryBusy(false);}
  }
  if(!workspace)return <div className="content"><h1>项目实践</h1><p>先确认学习路线，再查看其中的主项目和实践任务。</p></div>;
  const chars=Array.from(b.text).length;
  return <div className="content prompt-page"><h1>项目实践与 Prompt</h1><p className="lede">结合路线中的任务，把实现方案与 Prompt 一起保存。反馈与导出都使用你明确选择的已保存版本。</p><p aria-label="当前实践路线">路线第 {workspace.plan.revision} 版：{workspace.plan.goal_snapshot}</p>
    <div className="prompt-targets"><label>实践所属阶段<select aria-label="实践所属阶段" value={stage?.stage.stage_id||''} onChange={e=>{setStageChoice(e.target.value);setTaskChoice('');}}>{workspace.stages.map(s=><option key={s.stage.stage_id} value={s.stage.stage_id}>{s.stage.title}</option>)}</select></label>
      <label>实践任务<select aria-label="实践任务" value={task?.task_id||''} onChange={e=>setTaskChoice(e.target.value)}>{stage?.tasks.map(t=><option key={t.task_id} value={t.task_id}>{t.title}</option>)}</select></label></div>
    {!target||!task ? <p>当前阶段没有正式计划关联的实践任务。请选择其他阶段。</p> : <>
      <section className="panel prompt-context" aria-label="当前实践要求"><h2>路线中的主项目</h2>{b.thread ? <><h3>{b.thread.practice_project.title}</h3><p>{b.thread.practice_project.idea}</p><Requirements task={b.thread.task}/></> : <><h3>{task.title}</h3><p>{task.goal}</p><p>正在读取主项目与完整任务要求。</p></>}
        <p className="form-note">这些要求来自当前批准路线。保存与模型建议不会改变任务、学习进度或验收结果。</p></section>
      <section className="panel prompt-editor" aria-label="方案编辑"><h2>我的方案与 Prompt</h2><label>方案与 Prompt 原文<textarea aria-label="方案与 Prompt 原文" rows={12} value={b.text} onChange={e=>update(key,old=>({...old,text:e.target.value,edit:old.edit+1}))}/></label>
        <p className="form-note">{chars} / 40000 字符。保留空白行与原格式；短方案也能保存。</p><p aria-live="polite">{b.text!==b.baseline?'有未保存文字，请保存或复制后再刷新。':'编辑文字与保存记录同步。'} 未保存文字仅保留在本次打开的页面，切换阶段、任务和栏目仍会保留；刷新或退出后不会恢复。</p>
        <div className="chips"><button className="btn primary" disabled={!b.thread||b.busy||!!b.pending||!b.text.trim()||chars>40000} onClick={()=>void save(key,{...target,user_draft:b.text,expected_version:b.thread!.version,idempotency_key:crypto.randomUUID()})}>保存方案与 Prompt</button>
          {b.pending&&!b.conflict&&<button className="btn" disabled={b.busy} onClick={()=>void save(key,b.pending!)}>重试原保存</button>}
          <button className="btn" disabled={b.busy} onClick={()=>void read(key,target)}>读取最新保存版本</button>
          <button className="btn" onClick={()=>void navigator.clipboard.writeText(b.text).then(()=>update(key,old=>({...old,error:'已复制本地原文。'}))).catch(()=>update(key,old=>({...old,error:'复制未完成，请选中原文手动复制。'})))}>复制本地原文</button></div>
        {b.error&&<p role="alert">{b.error} {b.conflict?'请读取最新保存版本；编辑文字会保留。':b.pending?'结果尚未确认，请用原保存重试。':''}</p>}
      </section>
    </>}
      <section className="panel prompt-saved"><h2>已保存版本、反馈与导出</h2>{b.thread?.history_truncated&&<p>这里显示最近 20 次保存；更早的版本可在项目历史中读取。</p>}
        <label>选择已保存版本<select aria-label="选择已保存版本" value={selected} onChange={e=>choose(e.target.value)}><option value="">选择版本</option>{b.thread?.revisions.map(r=><option key={r.revision_id} value={r.revision_id}>第 {r.revision_no} 版 · {new Date(r.created_at).toLocaleString()}</option>)}
          {selected&&!b.thread?.revisions.some(r=>r.revision_id===selected)&&revisions[selected]&&<option value={selected}>历史第 {revisions[selected].revision_no} 版</option>}</select></label>
        {!selected&&<p>先保存原文，再选择反馈或导出。保存不会调用模型。</p>}
        {Object.values(revisions).map(r=><div key={r.revision_id} hidden={selected!==r.revision_id}><RevisionPanel project={project} revision={r} active={active&&selected===r.revision_id} onChange={v=>put([v])}/></div>)}
      </section>
    <section className="panel prompt-project-history" aria-label="项目方案历史"><h2>项目方案历史</h2><p>旧路线、旧任务的原文和当时要求独立保留。查看、反馈和导出历史版本不会覆盖编辑文字。</p>
      <button className="btn" disabled={historyBusy} onClick={()=>void readHistory()}>读取项目方案历史</button>
      {history.map(id=>{const r=revisions[id],savedTask=r.task_snapshot.task as Partial<PromptTask>|undefined;return <button className="resource-row" key={id} onClick={()=>choose(id)}>{savedTask?.title || (typeof r.task_snapshot.task_title==='string'?r.task_snapshot.task_title:'历史方案')} · 第 {r.revision_no} 版 · {new Date(r.created_at).toLocaleString()}</button>;})}
      {cursor&&<button className="btn" disabled={historyBusy} onClick={()=>void readHistory(true)}>读取更早的方案</button>}{historyError&&<p role="alert">{historyError}</p>}
    </section>
  </div>;
}

function RevisionPanel({project,revision:r,active,onChange}: {project:string;revision:PromptRevision;active:boolean;onChange:(v:PromptRevision)=>void}) {
  const [consent,setConsent]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState('');
  const [reviewPending,setReviewPending]=useState<PromptReviewBody|null>(null),[cancelPending,setCancelPending]=useState<PromptCancelBody|null>(null),[runVersion,setRunVersion]=useState<number|null>(null);
  const [format,setFormat]=useState<'raw'|'implementation'>('raw'),[exportPending,setExportPending]=useState<PromptExportBody|null>(null),[exported,setExported]=useState<PromptExport|null>(null);
  const alive=useRef(true),readTicket=useRef(0);
  useEffect(()=>{alive.current=true;return()=>{alive.current=false;readTicket.current++;};},[]);
  async function read() {const ticket=++readTicket.current;try{const value=await promptApi.revision(project,r.revision_id);if(alive.current&&ticket===readTicket.current){onChange(value);if(value.run_id&&['queued','running'].includes(value.run_status||'')){const run=await api.run(project,value.run_id);if(alive.current&&ticket===readTicket.current)setRunVersion(run.version);}}}catch(e){if(alive.current)setError(errorText(e));}}
  useEffect(()=>{setConsent(false);if(active)void read();},[active]);
  useEffect(()=>{
    if(!active||!r.run_id||terminal.has(r.run_status||'')||r.review)return;
    let stopped=false,count=0,timer:ReturnType<typeof setTimeout>;
    async function poll(){try{const run=await api.run(project,r.run_id!);if(stopped)return;setRunVersion(run.version);
      if(terminal.has(run.status)||run.next_action==='reconcile') {try{const value=await promptApi.revision(project,r.revision_id);if(!stopped)onChange({...value,run_status:run.next_action==='reconcile'?'unknown':run.status});}catch(e){if(!stopped)onChange({...r,run_status:run.next_action==='reconcile'?'unknown':run.status});throw e;}}
      else{count++;timer=setTimeout(poll,document.hidden?30000:Math.min(10000,1500*1.5**count));}
    }catch(e){if(!stopped)setError(`反馈状态未能核对：${errorText(e)} 原文保留，不会自动重新请求反馈。`);}}
    timer=setTimeout(poll,300);return()=>{stopped=true;clearTimeout(timer);};
  },[active,r.run_id,r.run_status]);
  async function work<T>(call:()=>Promise<T>, success:(result:T)=>void, failure?:(error:unknown)=>void){setBusy(true);setError('');try{const value=await call();if(alive.current)success(value);}catch(e){if(alive.current){setError(errorText(e));failure?.(e);}}finally{if(alive.current)setBusy(false);}}
  function review(body:PromptReviewBody){setReviewPending(body);void work(()=>promptApi.review(project,r.revision_id,body),run=>{readTicket.current++;onChange({...r,run_id:run.run_id,run_status:run.status});setRunVersion(run.version);setReviewPending(null);setConsent(false);});}
  function cancel(body:PromptCancelBody){setCancelPending(body);void work(()=>promptApi.cancel(project,r.revision_id,body),run=>{readTicket.current++;onChange({...r,run_status:run.status});setCancelPending(null);setRunVersion(run.version);},e=>{if(e instanceof ApiError&&e.status===409){setCancelPending(null);setRunVersion(null);void read();}});}
  function exportRevision(body:PromptExportBody){setExportPending(body);void work(()=>promptApi.export(project,r.revision_id,body),value=>{if(value.revision_id!==r.revision_id||value.format!==body.format)throw new Error('导出版本未能核对，请保留原文并重新读取。');setExported(value);setExportPending(null);});}
  function download(){if(!exported)return;const url=URL.createObjectURL(new Blob([exported.export_text],{type:'text/plain;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download=`studyplan-prompt-v${exported.revision_no}-${exported.format}.txt`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
  return <article aria-label={`已保存方案第 ${r.revision_no} 版`}><h3>第 {r.revision_no} 版原文</h3><pre className="prompt-original">{r.user_draft}</pre><details><summary>保存时的主项目与任务要求</summary><Snapshot value={r.task_snapshot}/></details>
    <h3>这版原文的反馈</h3>{r.review?<div>{([['优点',r.review.strengths],['待补充',r.review.gaps],['建议',r.review.suggestions]] as const).map(([label,items])=><div key={label}><h4>{label}</h4>{items.length?<ul>{items.map((v,i)=><li key={i}>{v}</li>)}</ul>:<p>没有额外条目。</p>}</div>)}</div>
    : r.run_id?<p role="status">{terminal.has(r.run_status||'')?(['unknown','reconciliation_required'].includes(r.run_status||'')?'反馈结果未知，请先核对，不会自动重新发起。':'本次反馈已结束；原文保留。'):'正在为这版已保存原文生成反馈，你可以继续编辑。'}</p>:<p>尚未请求反馈。</p>}
    <LegacyReview revision={r}/>
    {!r.review&&!r.run_id&&<><label className="prompt-consent"><input type="checkbox" checked={consent} onChange={e=>setConsent(e.target.checked)}/>同意将这版已保存的方案 / Prompt 原文和对应任务、知识要求发送给已配置模型</label><button className="btn" disabled={!consent||busy||!!reviewPending} onClick={()=>review({consent_to_model:true,idempotency_key:crypto.randomUUID()})}>请求这版原文反馈</button></>}
    {reviewPending&&<button className="btn" disabled={busy} onClick={()=>review(reviewPending)}>重试原反馈请求</button>}
    {r.run_id&&['queued','running'].includes(r.run_status||'')&&<button className="btn" disabled={busy||runVersion===null||!!cancelPending} onClick={()=>cancel({run_id:r.run_id!,expected_version:runVersion!,idempotency_key:crypto.randomUUID()})}>取消这版反馈</button>}
    {cancelPending&&<button className="btn" disabled={busy} onClick={()=>cancel(cancelPending)}>重试原取消请求</button>}
    <button className="text-button" onClick={()=>void read()}>核对这版反馈</button>
    <h3>导出所选保存版本</h3><p>导出不调用模型，也不包含编辑框中尚未保存的文字。</p><label>导出内容<select aria-label="导出内容" value={format} onChange={e=>setFormat(e.target.value as typeof format)}><option value="raw">原文</option><option value="implementation">实施 Prompt（含当时要求）</option></select></label>
    <button className="btn" disabled={busy||!!exportPending} onClick={()=>exportRevision({format,idempotency_key:crypto.randomUUID()})}>生成这版导出</button>
    {exportPending&&<button className="btn" disabled={busy} onClick={()=>exportRevision(exportPending)}>重试原导出请求</button>}
    {exported&&<section aria-label="所选保存版本导出"><p>已生成第 {exported.revision_no} 版{exported.format==='raw'?'原文':'实施 Prompt'}导出。</p><pre className="prompt-original">{exported.export_text}</pre><div className="chips"><button className="btn" onClick={()=>void navigator.clipboard.writeText(exported.export_text).then(()=>setError('已复制所选版本导出。')).catch(()=>setError('复制失败，请选择导出文字手动复制。'))}>复制这版导出</button><button className="btn" onClick={download}>下载这版导出</button><button className="btn" disabled={busy} onClick={()=>void work(()=>promptApi.savedExport(project,exported.export_id),value=>{if(value.revision_id===r.revision_id)setExported(value);})}>读取已保存导出</button></div></section>}
    {error&&<p role="alert">{error} 原文保留；结果不明时使用原请求重试，不会自动重派。</p>}
  </article>;
}
