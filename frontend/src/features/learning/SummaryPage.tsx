import { useEffect, useRef, useState } from 'react';
import {formalRefreshPolicy} from './artifactRefresh';
import { api, ApiError } from '../../api/client';
import type { SummaryAttempt, SummaryCancelBody, SummaryReviewBody, SummarySaveBody, SummaryTarget, SummaryThread } from '../../api/client';
import type { DTO } from '../../api/types';

type Buffer = {text: string; baseline: string; edit: number; initialized: boolean; thread?: SummaryThread;
  selected?: string; pending?: SummarySaveBody; busy?: boolean; error?: string; conflict?: boolean; consent?: boolean;
  reviewPending?: {id: string; body: SummaryReviewBody}; reviewing?: boolean;
  runVersion?: {id: string; version: number}; cancelPending?: {id: string; body: SummaryCancelBody}; cancelling?: boolean};
const fresh = (): Buffer => ({text: '', baseline: '', edit: 0, initialized: false});
const terminal = new Set(['succeeded','failed','cancelled','canceled','unknown','reconciliation_required']);
const targetKey = (t: SummaryTarget) => `${t.plan_id}/${t.stage_id}/${t.unit_id || '@stage'}`;
const message = (e: unknown) => e instanceof Error ? e.message : '操作未完成，请保留本地文字后再核对。';
function mergeThread(old: SummaryThread|undefined, next: SummaryThread): SummaryThread {
  if (old && old.version > next.version) return old;
  return {...next, attempts: next.attempts.map(a => {
    const known = old?.attempts.find(o => o.attempt_id === a.attempt_id);
    return known?.review && !a.review ? {...a, review: known.review, run_id: known.run_id, run_status: known.run_status} : a;
  })};
}

function Snapshot({value}: {value: Record<string,unknown>}) {
  const unit = typeof value.unit_snapshot === 'object' && value.unit_snapshot ? value.unit_snapshot as Record<string,unknown> : {};
  const title = value.stage_title || value.unit_title || unit.title;
  const objectives = value.objectives || unit.objectives;
  const notes = Array.isArray(objectives) ? objectives.filter((v): v is string => typeof v === 'string') : [];
  const nodes = Array.isArray(value.node_snapshot) ? value.node_snapshot : [];
  const source = value.source_snapshot && typeof value.source_snapshot === 'object' ? value.source_snapshot as Record<string,unknown> : {};
  const bindings = [...(Array.isArray(source.public_assignments) ? source.public_assignments : []),
    ...(Array.isArray(source.published_resource_snapshots) ? source.published_resource_snapshots : []),
    ...(Array.isArray(source.private_selections) ? source.private_selections : [])];
  const labels = (items: unknown[]) => items.map(v => {
    if (!v || typeof v !== 'object') return '';
    const item = v as Record<string,unknown>, resource = item.resource_snapshot as Record<string,unknown>|undefined;
    const published = item.source as Record<string,unknown>|undefined;
    return typeof item.title === 'string' ? item.title : typeof resource?.title === 'string' ? resource.title
      : typeof published?.title === 'string' ? published.title : '';
  }).filter(Boolean);
  return <div className="summary-snapshot">
    {typeof title === 'string' && <p>{value.stage_title && !value.unit_title ? '当时阶段' : '当时单元'}：{title}</p>}
    {typeof value.plan_revision === 'number' && <p>当时路线：第 {value.plan_revision} 版</p>}
    {notes.length > 0 && <><h4>当时学习目标</h4><ul>{notes.map((v,i) => <li key={i}>{v}</li>)}</ul></>}
    {labels(nodes).length > 0 && <p>关联知识：{labels(nodes).join('、')}</p>}
    {labels(bindings).length > 0 && <p>安排的资料：{labels(bindings).join('、')}</p>}
    {!title && !notes.length && !nodes.length && !bindings.length && <p>这条历史记录没有可核对的当时要求快照；不会用当前要求补写历史。</p>}
    <p className="form-note">资料安排只记录来源绑定，不代表实际阅读或掌握。</p>
  </div>;
}

function LegacyFeedback({attempt}: {attempt: SummaryAttempt}) {
  if (!attempt.legacy_review) return null;
  function text(value: unknown, depth = 0): string[] {
    if (depth > 4) return [];
    if (typeof value === 'string') return value.trim() ? [value] : [];
    if (Array.isArray(value)) return value.slice(0, 20).flatMap(v => text(v, depth + 1));
    if (value && typeof value === 'object') return Object.entries(value).slice(0, 20)
      .filter(([key]) => !key.endsWith('_id') && !['created_at', 'rubric_version'].includes(key))
      .flatMap(([, v]) => text(v, depth + 1));
    return [];
  }
  const entries = [...new Set(text(attempt.legacy_review))].slice(0, 40);
  return <section aria-label="旧格式反馈">
    <h4>历史反馈原文</h4>
    <p className="form-note">这条反馈按旧格式保留，以下展示原有文字，不补写新的评审结论。</p>
    {attempt.legacy_review_recorded_at && <p>{new Date(attempt.legacy_review_recorded_at).toLocaleString()}</p>}
    {entries.length ? entries.map((value, i) => <p className="summary-original" key={i}>{value}</p>)
      : <p>旧反馈记录已保留，没有可展示的文字条目。</p>}
  </section>;
}

export function SummaryPage({project, workspace, initialStage, active = true, onStageChange, onSaved, onStart, assistantBusy, artifactRefreshVersion=0}: {
  artifactRefreshVersion?:number; onStart?:(stageId:string)=>void; assistantBusy?:boolean; project: string; workspace: DTO['LearningWorkspaceView']|null; initialStage: string; active?: boolean; onStageChange?:(id:string)=>void; onSaved?:()=>Promise<void>|void;
}) {
  const [stageChoice, setStageChoice] = useState(initialStage);
  const stage = workspace?.stages.find(s => s.stage.stage_id === (onStageChange ? initialStage : stageChoice)) || workspace?.stages[0];
  const currentTarget = workspace && stage ? {plan_id: workspace.plan.plan_id, stage_id: stage.stage.stage_id} : null;
  const [historicKey, setHistoricKey] = useState('');
  useEffect(() => {if (onStageChange) setHistoricKey('');}, [initialStage, onStageChange ? true : false]);
  const [history, setHistory] = useState<SummaryAttempt[]>([]), [historyCursor, setHistoryCursor] = useState<string|null>(null);
  const [historySelected, setHistorySelected] = useState<SummaryAttempt|null>(null), [historyError, setHistoryError] = useState('');
  const [historyBusy, setHistoryBusy] = useState(false);
  const [targets, setTargets] = useState<Record<string,{target: SummaryTarget; label: string}>>({});
  const target = historicKey ? targets[historicKey]?.target : currentTarget;
  const key = target ? targetKey(target) : '';
  const [buffers, setBuffers] = useState<Record<string,Buffer>>({});
  const buffersRef = useRef(buffers); buffersRef.current = buffers;
  const sequence = useRef<Record<string,number>>({}), alive = useRef(true);
  const b = buffers[key] || fresh();
  function update(k: string, fn: (old: Buffer) => Buffer) {
    if (!alive.current) return;
    setBuffers(old => {const next = {...old, [k]: fn(old[k] || fresh())}; buffersRef.current = next; return next;});
  }
  function updateAttempt(k: string, value: SummaryAttempt) {
    update(k, old => ({...old, thread: old.thread ? {...old.thread,
      attempts: old.thread.attempts.map(a => a.attempt_id === value.attempt_id ? value : a)} : old.thread}));
  }
  useEffect(() => {alive.current = true; return () => {alive.current = false;};}, []);
  useEffect(() => {
    if (!currentTarget || !stage) return;
    const k = targetKey(currentTarget);
    setTargets(old => old[k] ? old : {...old, [k]: {target: currentTarget,
      label: `路线 ${workspace!.plan.revision} · ${stage.stage.title} · 阶段总结`}});
  }, [currentTarget?.plan_id, currentTarget?.stage_id]);
  async function read(k: string, t: SummaryTarget, initial = false, artifactRefresh=false) {
    const ticket = sequence.current[k] = (sequence.current[k] || 0) + 1;
    const edit = buffersRef.current[k]?.edit || 0;
    try {
      const thread = await api.summaryThread(project, t);
      if (!alive.current || sequence.current[k] !== ticket) return;
      update(k, old => {
        const last = thread.attempts.at(-1);
        const merged=mergeThread(old.thread,thread);
        const policy=formalRefreshPolicy(old,merged.version,edit,initial,artifactRefresh);
        const latestSelection=artifactRefresh&&(!old.selected||old.selected===old.thread?.attempts.at(-1)?.attempt_id);
        return {...old, thread:{...merged,version:policy.version}, initialized: true, selected: latestSelection?last?.attempt_id:old.selected || last?.attempt_id,
          ...(policy.adoptText ? {text: last?.content || '', baseline: last?.content || ''} : {}),
          ...(policy.clearConflict?{conflict:false,error:'',...(old.conflict?{pending:undefined}:{})}:{})};
      });
    } catch(e) {if (sequence.current[k] === ticket) update(k, old => ({...old, error: message(e)}));}
  }
  useEffect(() => {
    if (key && target && active && !buffersRef.current[key]?.initialized) void read(key, target, true);
  }, [key, active]);
  const artifactReads=useRef<Record<string,number>>({});
  useEffect(()=>{if(!artifactRefreshVersion||!key||!target||!active||b.busy||b.pending||(artifactReads.current[key]||0)>=artifactRefreshVersion)return;artifactReads.current[key]=artifactRefreshVersion;void read(key,target,false,true);},[artifactRefreshVersion,key,active,b.busy,b.pending]);
  const dirty = Object.values(buffers).some(value => value.text !== value.baseline);
  useEffect(() => {
    const warn = (e: BeforeUnloadEvent) => {if (dirty) {e.preventDefault(); e.returnValue = '';}};
    window.addEventListener('beforeunload', warn); return () => window.removeEventListener('beforeunload', warn);
  }, [dirty]);
  async function save(k: string, body: SummarySaveBody) {
    sequence.current[k] = (sequence.current[k] || 0) + 1;
    update(k, old => ({...old, pending: body, busy: true, error: ''}));
    let saved = false;
    try {
      const result = await api.saveSummary(project, body);
      update(k, old => ({...old, thread: mergeThread(old.thread, result.thread), baseline: body.content,
        selected: result.attempt.attempt_id, consent: false, pending: undefined, conflict: false, initialized: true}));
      saved = true;
    } catch(e) {
      update(k, old => ({...old, error: message(e), conflict: e instanceof ApiError && e.status === 409}));
    } finally {sequence.current[k] = (sequence.current[k] || 0) + 1; update(k, old => ({...old, busy: false}));}
    if (saved && onSaved) {
      try { await onSaved(); }
      catch { update(k, old => ({...old, error: '总结已保存，阶段状态暂未刷新。可稍后重新加载学习空间。'})); }
    }
  }
  const selected = b.thread?.attempts.find(a => a.attempt_id === b.selected);
  async function review(k: string, attempt: SummaryAttempt, body: SummaryReviewBody) {
    update(k, old => ({...old, reviewing: true, error: '', reviewPending: {id: attempt.attempt_id, body}}));
    try {
      const run = await api.reviewSummary(project, attempt.attempt_id, body);
      updateAttempt(k, {...attempt, run_id: run.run_id, run_status: run.status});
      update(k, old => ({...old, reviewPending: undefined, consent: false}));
    } catch(e) {update(k, old => ({...old, error: message(e)}));}
    finally {update(k, old => ({...old, reviewing: false}));}
  }
  async function cancel(k: string, attempt: SummaryAttempt, body: SummaryCancelBody) {
    update(k, old => ({...old, cancelling: true, cancelPending: {id: attempt.attempt_id, body}, error: ''}));
    try {
      const result = await api.cancelSummaryReview(project, attempt.attempt_id, body);
      updateAttempt(k, {...attempt, run_status: result.status});
      update(k, old => ({...old, cancelPending: undefined}));
    } catch(e) {update(k, old => ({...old, error: message(e),
      ...(e instanceof ApiError && e.status === 409 ? {cancelPending: undefined} : {})}));}
    finally {update(k, old => ({...old, cancelling: false}));}
  }
  async function readHistory(more = false) {
    setHistoryBusy(true); setHistoryError('');
    try {
      const value = await api.summaryHistory(project, more ? historyCursor || undefined : undefined);
      if (!alive.current) return;
      setHistory(old => more ? [...old, ...value.items.filter(a => !old.some(o => o.attempt_id === a.attempt_id))] : value.items);
      setHistoryCursor(value.next_cursor);
    } catch(e) {if (alive.current) setHistoryError(message(e));}
    finally {if (alive.current) setHistoryBusy(false);}
  }
  useEffect(() => {
    if (!active || !selected?.run_id || !selected.run_status || terminal.has(selected.run_status) || selected.review) return;
    let stopped = false, timer: ReturnType<typeof setTimeout>, count = 0;
    const attempt = selected, k = key;
    const poll = async () => {
      try {
        const run = await api.run(project, attempt.run_id!);
        if (stopped) return;
        update(k, old => ({...old, runVersion: {id: attempt.attempt_id, version: run.version}}));
        if (terminal.has(run.status) || run.next_action === 'reconcile') {
          try {
            const value = await api.summaryAttempt(project, attempt.attempt_id);
            if (!stopped) updateAttempt(k, {...value, run_status: run.next_action === 'reconcile' ? 'unknown' : run.status});
          } catch(e) {
            if (!stopped) updateAttempt(k, {...attempt, run_status: run.next_action === 'reconcile' ? 'unknown' : run.status});
            throw e;
          }
          return;
        }
        count++;
        timer = setTimeout(poll, document.hidden ? 30000 : Math.min(10000, 1500 * 1.5 ** count));
      } catch(e) {if (!stopped) update(k, old => ({...old, error: `反馈状态读取失败：${message(e)} 原文已保存，可稍后核对。`}));}
    };
    timer = setTimeout(poll, 300);
    return () => {stopped = true; clearTimeout(timer);};
  }, [active, key, selected?.attempt_id, selected?.run_id, selected?.run_status]);
  if (!workspace || !target) return <div className="content"><h1>阶段总结</h1><p>先确认一条学习路线，再整理阶段总结。</p></div>;
  const isHistory = target.plan_id !== workspace.plan.plan_id;
  const chars = Array.from(b.text).length;
  return <div className="content summary-page">
    <h1>阶段总结</h1><p className="lede">围绕整个阶段整理概念、实践证据与尚未验证的问题，再选择是否请求反馈。保存总结不会自动完成学习单元。</p>
    <div className="summary-targets">
      <label>总结所属阶段<select value={stage?.stage.stage_id} onChange={e => {setStageChoice(e.target.value); onStageChange?.(e.target.value); setHistoricKey('');}}>
        {workspace.stages.map(s => <option key={s.stage.stage_id} value={s.stage.stage_id}>{s.stage.title}</option>)}</select></label>
      <label>已访问的总结位置<select value={historicKey} onChange={e => setHistoricKey(e.target.value)}>
        <option value="">当前所选位置</option>{Object.entries(targets).map(([id,t]) => <option key={id} value={id}>{t.label}</option>)}</select></label>
    </div>
    {isHistory && <p className="note-callout">正在查看旧路线位置；原文和当时要求保留在旧版本，不会移到当前路线。</p>}
    {onStart&&stage&&<button className="btn primary" disabled={assistantBusy||isHistory} onClick={()=>onStart(stage.stage.stage_id)}>开始总结</button>}
    <div className="summary-layout">
      <details className="panel summary-editor" aria-label="总结编辑"><summary>直接编辑正式总结（不请求 AI）</summary>
        <h2>{historicKey ? targets[historicKey]?.label : `${stage?.stage.title} · 我的阶段总结`}</h2>
        {historicKey ? <><p className="form-note">正在编辑已访问位置的文字。学习要求来自该位置保存时的快照。</p>{(selected || b.thread?.attempts.at(-1)) && <Snapshot value={(selected || b.thread!.attempts.at(-1))!.rubric_snapshot}/>}</>
          : <p className="muted">本阶段知识：{stage?.nodes.map(n => n.title).join("、") || "暂无关联知识"}</p>}
        <ol className="summary-questions">{(b.thread?.questions || []).map((q,i) => <li key={i}>{q}</li>)}</ol>
        <label>总结原文<textarea aria-label="总结原文" value={b.text} rows={14} onChange={e => update(key, old => ({...old, text: e.target.value, edit: old.edit+1}))}/></label>
        <p className="form-note">{chars} / 20000 字符。短总结也能保存，空白行和原有格式会保留。</p>
        <p aria-live="polite">{b.text !== b.baseline ? '有未保存文字：离开或刷新前请保存，或复制本地文字。' : '当前编辑文字已与保存记录同步。'} 本地文字仅留在本次打开的页面，刷新后不会恢复未保存内容。</p>
        <div className="chips">
          <button className="btn primary" disabled={!b.thread || b.busy || !!b.pending || !b.text.trim() || chars>20000 || isHistory} onClick={() => void save(key, {...target, content: b.text, expected_version: b.thread!.version, idempotency_key: crypto.randomUUID()})}>保存总结</button>
          {b.pending && !b.conflict && <button className="btn" disabled={b.busy} onClick={() => void save(key, b.pending!)}>重试原保存</button>}
          <button className="btn" disabled={b.busy} onClick={() => void read(key, target)}>读取最新保存记录</button>
          <button className="btn" onClick={() => void navigator.clipboard.writeText(b.text).then(() => update(key, old => ({...old, error: '已复制本地文字。'}))).catch(() => update(key, old => ({...old, error: '复制未完成，请选中编辑框文字手动复制。'})))}>复制本地文字</button>
        </div>
        {b.error && <p role="alert">{b.error} {b.conflict ? '请读取最新保存记录；编辑文字会保留，核对后再保存。' : b.pending ? '保存结果尚未确认，请使用原保存重试，避免重复新增。' : ''}</p>}
      </details>
      <aside className="summary-history panel" aria-label="总结历史与反馈">
        <h2>保存记录</h2>
        {b.thread?.history_truncated && <p>这里显示最近 20 次保存。更早的版本可在项目总结历史中查看。</p>}
        {!b.thread?.attempts.length && <p>还没有保存记录。先写下理解，保存后可选择请求反馈。</p>}
        <label>查看保存版本<select aria-label="查看保存版本" value={b.selected || ''} onChange={e => update(key, old => ({...old, selected: e.target.value, consent: false}))}>
          <option value="">选择版本</option>{b.thread?.attempts.map(a => <option value={a.attempt_id} key={a.attempt_id}>第 {a.attempt_no} 次 · {new Date(a.created_at).toLocaleString()}</option>)}</select></label>
        {selected && <>
          <h3>第 {selected.attempt_no} 次保存的原文</h3><pre className="summary-original">{selected.content}</pre>
          <LegacyFeedback attempt={selected}/>
          <details><summary>当时的学习要求与资料安排</summary><Snapshot value={selected.rubric_snapshot}/></details>
          <details><summary>查看历史反馈</summary><h3>这次原文的反馈</h3>
          {selected.review ? <div aria-label="已保存反馈"><strong>{{satisfied:'达到当时要求', needs_revision:'建议修订', misconception:'存在需要澄清的理解'}[selected.review.conclusion]}</strong>
            {([['已覆盖', selected.review.covered], ['待补充', selected.review.gaps], ['需要澄清', selected.review.misconceptions], ['继续思考', selected.review.questions]] as const).map(([title, items]) => <div key={title}><h4>{title}</h4>{items.length ? <ul>{items.map((v,i) => <li key={i}>{v}</li>)}</ul> : <p>没有额外条目。</p>}</div>)}</div>
          : selected.run_status && !terminal.has(selected.run_status) ? <p role="status">正在为第 {selected.attempt_no} 次原文生成反馈。你可以继续编辑。</p>
          : selected.run_status && selected.run_status !== 'succeeded' ? <p role="status">{['unknown','reconciliation_required'].includes(selected.run_status) ? '反馈结果未知，请先核对；不会自动重新发起。' : '本次反馈未完成。'} 原文已保存。</p>
          : <p>尚无反馈。</p>}
          {!selected.review && !selected.run_id && <>
            <label className="summary-consent"><input type="checkbox" checked={!!b.consent} onChange={e => update(key, old => ({...old, consent: e.target.checked}))}/>同意将所选已保存原文及当时学习要求发送给已配置模型，以请求反馈</label>
            <button className="btn" disabled={!b.consent || b.reviewing || !!b.reviewPending || isHistory} onClick={() => void review(key, selected, {idempotency_key: crypto.randomUUID(), consent_to_model: true})}>请求这次原文的反馈</button>
          </>}
          {b.reviewPending?.id === selected.attempt_id && <button className="btn" disabled={b.reviewing} onClick={() => void review(key, selected, b.reviewPending!.body)}>重试原反馈请求</button>}
          {selected.run_id && ['queued','running'].includes(selected.run_status || '') && <button className="btn" disabled={b.cancelling || !!b.cancelPending || b.runVersion?.id !== selected.attempt_id} onClick={() => void cancel(key, selected,
            {run_id: selected.run_id!, expected_version: b.runVersion!.version, idempotency_key: crypto.randomUUID()})}>取消这次反馈</button>}
          {b.cancelPending?.id === selected.attempt_id && <button className="btn" disabled={b.cancelling} onClick={() => void cancel(key, selected, b.cancelPending!.body)}>重试原取消请求</button>}
          <button className="text-button" onClick={() => void api.summaryAttempt(project, selected.attempt_id).then(value => updateAttempt(key, value)).catch(e => update(key, old => ({...old, error: message(e)})))}>核对这次反馈</button>
          </details>
        </>}
      </aside>
    </div>
    <section className="panel summary-project-history" aria-label="项目总结历史">
      <h2>项目总结历史</h2><p>查看旧路线与旧位置的原文，不会替换上面的编辑文字。</p>
      <button className="btn" disabled={historyBusy} onClick={() => void readHistory()}>读取项目总结历史</button>
      {history.map(a => <button className="resource-row" key={a.attempt_id} onClick={() => setHistorySelected(a)}>
        {typeof a.rubric_snapshot.stage_title === 'string' && !a.unit_id ? `${a.rubric_snapshot.stage_title} · 阶段总结` : typeof a.rubric_snapshot.unit_title === 'string' ? `${a.rubric_snapshot.unit_title} · 历史单元总结` : '历史原文'} · 第 {a.attempt_no} 次 · {new Date(a.created_at).toLocaleString()}</button>)}
      {historyCursor && <button className="btn" disabled={historyBusy} onClick={() => void readHistory(true)}>读取更早的总结</button>}
      {historyError && <p role="alert">{historyError}</p>}
      {historySelected && <HistoricalAttempt key={historySelected.attempt_id} project={project} initial={historySelected} active={active}/>}
    </section>
  </div>;
}

function HistoricalAttempt({project, initial, active}: {project: string; initial: SummaryAttempt; active: boolean}) {
  const [attempt, setAttempt] = useState(initial), [consent, setConsent] = useState(false), [error, setError] = useState('');
  const [pending, setPending] = useState<SummaryReviewBody|null>(null), [busy, setBusy] = useState(false);
  const [runVersion, setRunVersion] = useState<number|null>(null), [cancelPending, setCancelPending] = useState<SummaryCancelBody|null>(null);
  async function read() {try {setAttempt(await api.summaryAttempt(project, attempt.attempt_id));} catch(e) {setError(message(e));}}
  async function requestReview(body: SummaryReviewBody) {
    setBusy(true); setPending(body); setError('');
    try {const result = await api.reviewSummary(project, attempt.attempt_id, body); setAttempt(old => ({...old, run_id: result.run_id, run_status: result.status})); setPending(null); setConsent(false);}
    catch(e) {setError(message(e));} finally {setBusy(false);}
  }
  async function cancel(body: SummaryCancelBody) {
    setBusy(true); setCancelPending(body); setError('');
    try {const result = await api.cancelSummaryReview(project, attempt.attempt_id, body); setAttempt(old => ({...old, run_status: result.status})); setCancelPending(null);}
    catch(e) {setError(message(e));} finally {setBusy(false);}
  }
  useEffect(() => {
    if (!active || !attempt.run_id || terminal.has(attempt.run_status || '') || attempt.review) return;
    let stopped = false, timer: ReturnType<typeof setTimeout>, count = 0;
    async function poll() {
      try {
        const run = await api.run(project, attempt.run_id!);
        if (stopped) return; setRunVersion(run.version);
        if (terminal.has(run.status) || run.next_action === 'reconcile') {
          const value = await api.summaryAttempt(project, attempt.attempt_id);
          if (!stopped) setAttempt({...value, run_status: run.next_action === 'reconcile' ? 'unknown' : run.status});
        } else {count++; timer = setTimeout(poll, document.hidden ? 30000 : Math.min(10000, 1500 * 1.5 ** count));}
      } catch(e) {if (!stopped) setError(message(e));}
    }
    timer = setTimeout(poll, 300); return () => {stopped = true; clearTimeout(timer);};
  }, [active, attempt.run_id, attempt.run_status]);
  return <article aria-label="历史总结原文"><h3>历史原文</h3><pre className="summary-original">{attempt.content}</pre><Snapshot value={attempt.rubric_snapshot}/><LegacyFeedback attempt={attempt}/>
    {attempt.review ? <><h4>当时反馈</h4><p>{{satisfied:'达到当时要求',needs_revision:'建议修订',misconception:'需要澄清理解'}[attempt.review.conclusion]}</p>
      <ul>{[...attempt.review.covered,...attempt.review.gaps,...attempt.review.misconceptions,...attempt.review.questions].map((v,i) => <li key={i}>{v}</li>)}</ul></>
    : attempt.run_id ? <p>{terminal.has(attempt.run_status || '') ? '反馈已结束；原文保留。结果未知时请先核对。' : '正在为这条历史原文生成反馈。'}</p>
    : <><label className="summary-consent"><input type="checkbox" checked={consent} onChange={e => setConsent(e.target.checked)}/>同意将这条历史原文及其当时要求发送给已配置模型</label>
      <button className="btn" disabled={!consent || busy || !!pending} onClick={() => void requestReview({idempotency_key: crypto.randomUUID(), consent_to_model: true})}>请求历史原文反馈</button></>}
    {pending && <button className="btn" disabled={busy} onClick={() => void requestReview(pending)}>重试原历史反馈请求</button>}
    {attempt.run_id && ['queued','running'].includes(attempt.run_status || '') && <button className="btn" disabled={busy || runVersion===null || !!cancelPending} onClick={() => void cancel({run_id: attempt.run_id!, expected_version: runVersion!, idempotency_key: crypto.randomUUID()})}>取消历史原文反馈</button>}
    {cancelPending && <button className="btn" disabled={busy} onClick={() => void cancel(cancelPending)}>重试原历史取消请求</button>}
    <button className="text-button" onClick={() => void read()}>核对历史反馈</button>{error && <p role="alert">{error} 原文保留，不会自动重新请求反馈。</p>}
  </article>;
}
