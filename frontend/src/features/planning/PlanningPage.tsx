import { useEffect, useRef, useState } from 'react';
import { api, ApiError, type GoalSpec, type PlanningDraft, type PlanningPlan, type PlanningRun, type RevisionContext } from '../../api/client';
import type { DTO } from '../../api/types';
import { Curriculum } from './Curriculum';
import { PlanningDialog } from './PlanningDialog';
import { progressLabel, fact, facts, serverGoal } from './facts';
import './planning.css';
const empty: GoalSpec = { target: '', starting_point: '', scope: [], desired_depth: 'unspecified', outcome_purpose: 'learn', constraints: [], project_context: '' };
const key = () => crypto.randomUUID();
export function PlanningPage({ project, actorKey, onPublished }: {
    project: string;
    actorKey: string;
    onPublished: () => Promise<void>;
}) {
    const [available, setAvailable] = useState<DTO['V2PlanningAvailability'] | null>(null), [goal, setGoal] = useState<GoalSpec>(empty), [current, setCurrent] = useState<PlanningPlan | null>(null), [draft, setDraft] = useState<PlanningDraft | null>(null), [run, setRun] = useState<PlanningRun | null>(null), [runs, setRuns] = useState<PlanningRun[]>([]), [error, setError] = useState(''), [busy, setBusy] = useState(false), [loading, setLoading] = useState(true), [supplement, setSupplement] = useState(false), [answers, setAnswers] = useState<Record<string, string>>({}), [confirmation, setConfirmation] = useState(false), [consent, setConsent] = useState(false), [replanning, setReplanning] = useState(false), [context, setContext] = useState<RevisionContext | null>(null), [editing, setEditing] = useState(false), [descriptions, setDescriptions] = useState<Record<string, string>>({}), [order, setOrder] = useState<string[]>([]), [preview, setPreview] = useState<PlanningDraft | null>(null), [history, setHistory] = useState<PlanningPlan | null>(null), [revision, setRevision] = useState(''), [pending, setPending] = useState(() => !!sessionStorage.getItem(`studyplan-v2:${JSON.stringify([actorKey, project])}:mutation`));
    const cache = `studyplan-v2:${JSON.stringify([actorKey, project])}`, alive = useRef(true), lock = useRef(false);
    useEffect(() => () => { alive.current = false; }, []);
    const failure = (err: unknown) => setError(err instanceof ApiError && err.status === 409 ? '计划或问题已变化，请手动刷新后核对当前状态。' : (err as Error).message);
    async function readRun(id: string) {
        let value = await api.run(project, id);
        const seen = new Set<string>();
        while (value.clarification?.continuation_run_id && !seen.has(value.run_id)) {
            seen.add(value.run_id);
            value = await api.run(project, value.clarification.continuation_run_id);
        }
        if (!alive.current)
            return;
        setRun(value);
        let previous = {};
        try {
            previous = JSON.parse(sessionStorage.getItem(cache) || '{}');
        }
        catch { }
        sessionStorage.setItem(cache, JSON.stringify({ ...previous, run: value.run_id }));
        if (value.result_ref && value.status === 'succeeded') {
            const result = await api.draft(project, value.result_ref);
            setDraft(result.status === 'awaiting_approval' ? result : null);
        }
    }
    async function refresh() {
        const [a, p, r] = await Promise.all([api.planningAvailability(project), api.current(project), api.runs(project, 20)]);
        if (!alive.current)
            return;
        setAvailable(a);
        setCurrent(p);
        setRuns(r);
        if (p)
            setGoal(serverGoal(p));
        let saved: {
            run?: string;
            preview?: string;
        } | null = null;
        try {
            saved = JSON.parse(sessionStorage.getItem(cache) || 'null');
        }
        catch { }
        const id = saved?.run || r[0]?.run_id;
        if (id)
            await readRun(id);
        if (saved?.preview) {
            const restored = await api.revisionPreview(project, saved.preview);
            if (restored.status === 'awaiting_approval') {
                setPreview(restored);
                setEditing(true);
                setOrder((restored.stages || []).map(next => p?.stages?.find(old => old.stable_key === next.stable_key)?.stage_id).filter((id): id is string => !!id));
                setDescriptions(Object.fromEntries((p?.stages || []).map(s => [s.stage_id, restored.stages?.find(next => next.stable_key === s.stable_key)?.objective ?? s.objective])));
            }
        }
        if (p?.v2_content && a.local_change)
            setContext(await api.revisionContext(project));
    }
    useEffect(() => { refresh().catch(failure).finally(() => setLoading(false)); }, [project, actorKey]);
    useEffect(() => {
        if (!run || !['queued', 'running'].includes(run.status))
            return;
        const timer = setTimeout(() => readRun(run.run_id).catch(failure), 1800);
        return () => clearTimeout(timer);
    }, [run]);
    async function mutate(action: () => Promise<void>) {
        if (lock.current || pending)
            return;
        lock.current = true;
        setBusy(true);
        setError('');
        try {
            await action();
            sessionStorage.removeItem(`${cache}:mutation`);
        }
        catch (e) {
            if (sessionStorage.getItem(cache + ":mutation") && e instanceof ApiError && (e.status === 0 || e.outcomeUnknown))
                setPending(true);
            else
                sessionStorage.removeItem(`${cache}:mutation`);
            failure(e);
        }
        finally {
            lock.current = false;
            setBusy(false);
        }
    }
    async function reconcile() {
        try {
            await refresh();
            // A generic GET cannot prove the identity of an ambiguous mutation.
            setError('');
        }
        catch (e) {
            failure(e);
        }
    }
    async function sent<T>(request: Promise<T>): Promise<T> { const response = await request; sessionStorage.removeItem(cache + ':mutation'); const data = fact(response); if (typeof data.run_id === 'string') {
        let prior = {};
        try {
            prior = JSON.parse(sessionStorage.getItem(cache) || '{}');
        }
        catch { }
        sessionStorage.setItem(cache, JSON.stringify({ ...prior, run: data.run_id }));
    } if (typeof data.draft_id === 'string')
        sessionStorage.setItem(cache, JSON.stringify({ run: run?.run_id, preview: data.draft_id })); return response; }
    function remember<T>(kind: string, body: T): T { sessionStorage.setItem(cache + ':mutation', JSON.stringify({ kind, body, parent_run_id: run?.run_id, draft_id: (preview || draft)?.draft_id, current_plan_id: current?.plan_id })); return body; }
    async function generate() { await mutate(async () => { const submitted = { ...goal, target: goal.target.trim(), scope: goal.scope?.map(v => v.trim()).filter(Boolean), constraints: goal.constraints?.map(v => v.trim()).filter(Boolean) }; const response = current && replanning ? await sent(api.replanOwned(project, remember("replanOwned", { current_plan_id: current.plan_id, expected_version: current.revision, idempotency_key: key(), goal_spec: submitted }))) : await sent(api.generateOwnedPlan(project, remember("generateOwnedPlan", { goal: submitted.target, goal_spec: submitted }))); setDraft(null); setAnswers({}); await readRun(response.run_id); }); }
    async function answer() {
        if (!run?.clarification)
            return;
        await mutate(async () => { const response = await sent(api.answerPlanningQuestions(project, remember("answerPlanningQuestions", { parent_run_id: run.run_id, clarification_version: run.clarification!.clarification_version, answers: run.clarification!.questions.map(q => ({ question_id: q.question_id, answer_text: answers[q.question_id]?.trim() || '' })), idempotency_key: key() }))); setAnswers({}); await readRun(response.run_id); });
    }
    async function confirm() {
        const chosen = preview || draft;
        if (!chosen)
            return;
        await mutate(async () => {
            const fresh = preview ? await api.revisionPreview(project, chosen.draft_id) : await api.draft(project, chosen.draft_id);
            if (fresh.draft_hash !== chosen.draft_hash || fresh.version !== chosen.version) {
                if (preview)
                    setPreview(fresh);
                else
                    setDraft(fresh);
                setConfirmation(false);
                throw new ApiError(409, '草案已变化');
            }
            const body = { expected_version: current?.revision || 0, draft_hash: fresh.draft_hash, idempotency_key: key() };
            if (preview || fresh.v2_revision)
                await sent(api.decideRevision(project, fresh.draft_id, 'confirm', remember("decideRevision", body)));
            else
                await sent(api.decide(project, fresh.draft_id, remember("decide", { ...body, decision: 'approve' })));
            setConfirmation(false);
            setDraft(null);
            setPreview(null);
            setEditing(false);
            setReplanning(false);
            sessionStorage.removeItem(cache);
            setRun(null);
            setCurrent(await api.current(project));
            await onPublished();
            await refresh();
        });
    }
    function startLocal() {
        if (!current || !context)
            return;
        setEditing(true);
        setPreview(null);
        setOrder(current.stages?.map(s => s.stage_id) || []);
        setDescriptions(Object.fromEntries((current.stages || []).map(s => [s.stage_id, s.objective])));
    }
    function invalidate() { setPreview(null); sessionStorage.setItem(cache, JSON.stringify({ run: run?.run_id })); }
    async function makePreview() {
        if (!current)
            return;
        await mutate(async () => { const edits = (current.stages || []).filter(s => descriptions[s.stage_id] !== undefined && descriptions[s.stage_id] !== s.objective).map(s => ({ stage_id: s.stage_id, what_to_learn: descriptions[s.stage_id] })); const p = await sent(api.previewLocalPlan(project, remember("previewLocalPlan", { current_plan_id: current.plan_id, expected_version: current.revision, idempotency_key: key(), stage_edits: edits, stage_order: order }))); setPreview(p); sessionStorage.setItem(cache, JSON.stringify({ run: run?.run_id, preview: p.draft_id })); });
    }
    const clar = run?.clarification, chosen = preview || draft, active = !!run && ['queued', 'running'].includes(run.status), blocked = busy || pending || [run, ...runs].some(item => item?.status === "reconciliation_required" || item?.error?.code === "provider_transport_unknown"), visible = history || chosen || current, canConfirm = chosen?.status === 'awaiting_approval' && !!chosen.v2_content;
    return <div className="content planning-v2"><header className="pv-heading"><h1>学习计划</h1><p className="pv-muted">从你的目标出发，安排知识、教材与项目实践。</p><button className="text-button" onClick={reconcile} disabled={busy}>刷新当前状态</button></header>{loading && <p role="status">正在读取学习计划…</p>}{error && <div className="pv-notice pv-warning" role="alert">{error}</div>}{pending && <p className="pv-notice pv-warning">提交结果尚未核对，请刷新当前状态。不会自动重复提交。</p>}{available && !available.initial_generation && <div className="pv-notice">{available.message}</div>}
 {((!current && !run && !chosen) || replanning) && <section className="pv-panel"><h2>{replanning ? '目标变了，重新规划' : '你想学什么，最后想完成什么？'}</h2><p className="pv-muted">用自己的话描述目标。已有基础、限制和项目都可以补充，也可以留空。</p><label htmlFor="planning-goal">学习目标</label><textarea id="planning-goal" rows={5} maxLength={2000} value={goal.target} onChange={e => setGoal({ ...goal, target: e.target.value })} placeholder="描述你希望学会的能力，或希望完成的项目"/><div className="pv-actions"><button onClick={() => setSupplement(true)}>补充信息（可选）</button><button className="primary" disabled={blocked || active || (!replanning && !!run) || !goal.target.trim() || !(replanning ? available?.semantic_replanning : available?.initial_generation)} onClick={generate}>{replanning ? '重新规划' : '生成学习计划'}</button>{replanning && <button onClick={() => setReplanning(false)}>返回当前计划</button>}</div>{goal.starting_point && <p className="pv-muted">已有基础：{goal.starting_point}</p>}</section>}
 {active && run && <section className="pv-panel" aria-live="polite"><h2>正在准备学习计划</h2><p>{run.progress ? progressLabel(run.progress.phase) : '正在准备学习计划，请稍候。'}</p>{run.progress?.current_stage_title && <p>{run.progress.current_stage_title}</p>}<button disabled={blocked} onClick={() => mutate(async () => { setRun(await sent(api.cancelRun(project, run.run_id, remember("cancelRun", { expected_version: run.version, idempotency_key: key() })))); })}>取消生成</button></section>}
 {clar && <section className="pv-panel"><h2>需要补充信息</h2><p>{clar.message}</p>{clar.questions.slice(0, 3).map(q => <label className="pv-field" key={q.question_id}>{q.question_text}<textarea rows={3} maxLength={2000} value={answers[q.question_id] || ''} disabled={!clar.can_submit_answers || !available?.clarification || blocked} onChange={e => setAnswers({ ...answers, [q.question_id]: e.target.value })}/></label>)}<button className="primary" onClick={answer} disabled={blocked || !available?.clarification || !clar.can_submit_answers || !!clar.continuation_run_id || clar.questions.length > 3 || clar.questions.some(q => !answers[q.question_id]?.trim())}>提交补充信息，继续规划</button></section>}
 {run && !active && !clar && run.status !== 'succeeded' && <section className="pv-notice pv-warning"><h2>{run.status === 'reconciliation_required' || run.error?.code === 'provider_transport_unknown' ? '需要核对执行结果' : run.status === 'cancelled' ? '已取消生成' : '计划尚未完成'}</h2><p>{run.error?.message || '当前没有可以确认的完整草案。请核对当前状态。'}</p>{run.planning_issues?.map((issue, i) => <p key={i}>{issue.message}</p>)}<button disabled>尚不能确认此草案</button></section>}
 {visible && <><div className="pv-section-head"><h2>{history ? `历史路线 · 版本 ${history.revision}` : chosen ? '课程草案，先看看是否适合你' : `当前路线 · 版本 ${current?.revision}`}</h2>{current && !history && <div className="pv-actions"><button disabled={!available?.local_change || !current.v2_content || blocked} onClick={startLocal}>调整计划</button><button disabled={!available?.semantic_replanning || blocked} onClick={() => { setReplanning(true); setGoal(serverGoal(current)); }}>目标变了，重新规划</button></div>}{history && <button onClick={() => setHistory(null)}>返回当前路线</button>}</div><Curriculum key={`${history ? 'history' : 'current'}:${visible.revision}:${'draft_hash' in visible ? visible.draft_hash : ''}`} plan={visible}/></>}
 {!history && draft && !preview && draft.status === 'awaiting_approval' && !draft.v2_revision && <DraftEdit draft={draft} disabled={blocked} onSave={stages => mutate(async () => { const result = await sent(api.decide(project, draft.draft_id, remember("decide", { decision: 'edit', draft_hash: draft.draft_hash, expected_version: current?.revision || 0, idempotency_key: '', edited_stages: stages }))); setDraft(result.draft); })}/>}
 {!history && editing && current && context && <section className="pv-panel"><h2>调整未来阶段</h2><p>只修改未来阶段说明与合法顺序。教材、任务、目标与成果要求保持原有事实。</p>{(order.length ? order : current.stages?.map(s => s.stage_id) || []).map((id, index) => {
                const stage = current.stages?.find(s => s.stage_id === id), state = context.stages.find(s => s.stage_id === id);
                if (!stage)
                    return null;
                return <div className="pv-field" key={id}><strong>{stage.title}</strong><p className="pv-muted">{state?.learning_status === 'completed' ? '已完成，原版本记录保留' : state?.learning_status === 'started' ? '已开始，原版本记录保留' : '尚未开始'}</p><textarea aria-label={`${stage.title}的学习说明`} value={descriptions[id] ?? stage.objective} disabled={blocked || state?.protected !== false} onChange={e => { setDescriptions({ ...descriptions, [id]: e.target.value }); invalidate(); }}/><button disabled={blocked || index === 0 || state?.protected !== false || context.stages.find(s => s.stage_id === order[index - 1])?.protected !== false} onClick={() => { const next = [...order]; [next[index - 1], next[index]] = [next[index], next[index - 1]]; setOrder(next); invalidate(); }}>向前调整</button></div>;
            })}<button disabled={blocked} onClick={makePreview}>预览修改</button>{preview && <><h3>修改前后差异</h3>{(preview.stages || []).map(s => <div className="pv-diff" key={s.stage_id}><p>原说明：{current.stages?.find(old => old.stable_key === s.stable_key)?.objective}</p><p>新说明：{s.objective}</p></div>)}<p>原顺序：{current.stages?.map(s => s.title).join(' → ')}</p><p>新顺序：{preview.stages?.map(s => s.title).join(' → ')}</p><button disabled={blocked} onClick={() => mutate(async () => { await sent(api.decideRevision(project, preview.draft_id, 'cancel', remember("decideRevision", { expected_version: current.revision, draft_hash: preview.draft_hash, idempotency_key: key() }))); setPreview(null); setEditing(false); invalidate(); })}>取消本次修改</button></>}</section>}
 {!history && chosen && <div className="pv-approval"><p>确认后采用这份安排。过去的学习记录继续保留原版本。</p><button className="primary" disabled={!canConfirm || blocked} onClick={() => { setConsent(false); setConfirmation(true); }}>{canConfirm ? '采用这份计划' : '尚不能确认此草案'}</button></div>}
 {current && <section className="pv-panel"><h2>版本历史</h2><p>{context?.history_policy || '历史版本保留当时的学习安排与来源。新版本不按阶段标题复制完成状态。'}</p><div className="pv-actions"><label>历史版本<input type="number" min={1} max={current.revision} value={revision} onChange={e => setRevision(e.target.value)}/></label><button onClick={() => {
                const n = Number(revision);
                if (Number.isInteger(n) && n >= 1 && n <= current.revision)
                    api.planRevision(project, n).then(setHistory).catch(failure);
            }} disabled={!revision || busy}>查看原路线</button></div>{facts(fact(current.v2_revision).lineage).map((line, i) => <p key={i}>来自版本 {Number(line.source_revision)} 的{line.learning_status === 'completed' ? '已完成' : line.learning_status === 'started' ? '已开始' : '未来'}阶段记录保留。</p>)}</section>}
 {runs.length > 1 && <details className="pv-panel"><summary>此前的规划记录</summary>{runs.map((r, i) => <button className="text-button" key={r.run_id} onClick={() => { setDraft(null); setHistory(null); readRun(r.run_id).catch(failure); }}>规划记录 {runs.length - i} · {{ queued: '准备中', running: '生成中', succeeded: '已完成', failed: r.clarification ? '需要补充信息' : '未完成', cancelled: '已取消', reconciliation_required: '待核对', waiting_user: '待确认' }[r.status]}</button>)}</details>}
 {supplement && <PlanningDialog title="补充信息（全部可选）" onClose={() => setSupplement(false)}><label className="pv-field">已有基础<textarea maxLength={1000} value={goal.starting_point} onChange={e => setGoal({ ...goal, starting_point: e.target.value })}/></label><label className="pv-field">学习范围（每行一项）<textarea value={goal.scope?.join('\n') || ''} onChange={e => setGoal({ ...goal, scope: e.target.value.split('\n') })}/></label><label className="pv-field">期望深度<select value={goal.desired_depth} onChange={e => setGoal({ ...goal, desired_depth: e.target.value as GoalSpec['desired_depth'] })}><option value="unspecified">暂不指定</option><option value="foundation">理解基础</option><option value="applied">能够应用</option><option value="deep">深入理解</option></select></label><label className="pv-field">用途<select value={goal.outcome_purpose} onChange={e => setGoal({ ...goal, outcome_purpose: e.target.value as GoalSpec['outcome_purpose'] })}><option value="learn">学习</option><option value="interview">面试</option><option value="portfolio">作品</option><option value="internship">实习</option><option value="production">实际项目</option></select></label><label className="pv-field">必须保留的限制（每行一项）<textarea value={goal.constraints?.join('\n') || ''} onChange={e => setGoal({ ...goal, constraints: e.target.value.split('\n') })}/></label><label className="pv-field">已有项目与背景<textarea maxLength={2000} value={goal.project_context || ''} onChange={e => setGoal({ ...goal, project_context: e.target.value })}/></label><button className="primary" onClick={() => setSupplement(false)}>保存补充信息</button></PlanningDialog>}
 {!history && confirmation && chosen && <PlanningDialog title="采用这份学习计划？" onClose={() => setConfirmation(false)}><p>请确认已阅读目标、教材范围、实践任务与成果要求。</p><label className="pv-check"><input type="checkbox" checked={consent} onChange={e => setConsent(e.target.checked)}/>我已阅读，确认采用当前草案。</label><button className="primary" disabled={!consent || blocked} onClick={confirm}>确认采用</button></PlanningDialog>}
 </div>;
}
function DraftEdit({ draft, disabled, onSave }: {
    draft: PlanningDraft;
    disabled: boolean;
    onSave: (stages: NonNullable<PlanningDraft['stages']>) => void;
}) { const [stages, setStages] = useState(draft.stages || []); useEffect(() => setStages(draft.stages || []), [draft.draft_hash]); return <details className="pv-panel"><summary>编辑阶段学习说明</summary><p>仅调整阶段说明，保留完整课程结构与教材实践事实。</p>{stages.map((stage, i) => <label className="pv-field" key={stage.stage_id}>{stage.title}<textarea value={stage.objective} disabled={disabled} onChange={e => setStages(stages.map((s, n) => n === i ? { ...s, objective: e.target.value } : s))}/></label>)}<button disabled={disabled} onClick={() => onSave(stages)}>保存草案说明</button></details>; }
