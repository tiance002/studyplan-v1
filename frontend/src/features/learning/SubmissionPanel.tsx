import { useEffect, useRef, useState } from 'react';
import { ApiError } from '../../api/client';
import { submissionApi } from '../../api/submissionClient';
import type {
  ArtifactKind, EvidenceKind, PracticeSubmissionCoverageRequest, PracticeSubmissionDecisionRequest,
  PracticeSubmissionEvidenceRequest, PracticeSubmissionRequest, PracticeSubmissionThreadView,
  PracticeSubmissionView, SubmissionTarget,
} from '../../api/submissionClient';

export const artifactLabels: Record<ArtifactKind, string> = {
  project_description: '项目说明', evaluation: '评估', architecture: '架构',
  design_decision: '设计决定', failure_review: '失败复盘', explanation: '说明', other: '其他资料',
};
const evidenceLabels: Record<EvidenceKind, string> = {
  user_statement: '本人陈述', external_report: '外部报告（平台未核验）', source_reference: '来源引用（未检查）',
};
const message = (e: unknown) => e instanceof Error ? e.message : '记录未能核对，请保留原文。';
const rejected = (e: unknown): e is ApiError => e instanceof ApiError && [400, 401, 403, 404, 409, 422].includes(e.status);
const positionKey = (t: SubmissionTarget) => `${t.plan_id}/${t.stage_id}/${t.task_id}`;
const copy = async (text: string) => navigator.clipboard.writeText(text);
type EvidenceEdit = PracticeSubmissionEvidenceRequest & { localId: string };
type Draft = { note: string; repo: string; evidence: EvidenceEdit[]; kind: ArtifactKind; parent: string | null };
type Buffer = Draft & {
  baseline: string; edit: number; initialized: boolean; thread?: PracticeSubmissionThreadView;
  pending?: PracticeSubmissionRequest; busy?: boolean; conflict?: boolean; error?: string;
  target?: SubmissionTarget; taskTitle?: string; planRevision?: number;
};
const fresh = (): Buffer => ({ note: '', repo: '', evidence: [], kind: 'other', parent: null, baseline: '', edit: 0, initialized: false });
const raw = (d: Draft) => JSON.stringify({
  note: d.note, repo_url: d.repo || null, evidence: d.evidence.map(({ localId: _id, ...e }) => e),
  artifact_kind: d.kind, parent_submission_id: d.parent,
});
const emptyRaw = raw(fresh());
const dirty = (b: Buffer) => raw(b) !== (b.baseline || emptyRaw);
export function retainSubmission(old: PracticeSubmissionView | undefined, next: PracticeSubmissionView) {
  return old?.review && !next.review ? { ...next, review: old.review } : next;
}

export function SubmissionPanel({ project, target, currentPlanId, active, onChanged }: {
  project: string; target: SubmissionTarget | null; currentPlanId: string; active: boolean;
  onChanged?: () => Promise<void> | void;
}) {
  const [buffers, setBuffers] = useState<Record<string, Buffer>>({});
  const [records, setRecords] = useState<Record<string, PracticeSubmissionView>>({});
  const [selected, setSelected] = useState('');
  const alive = useRef(true), tickets = useRef<Record<string, number>>({});
  const selectionTicket = useRef(0), bufferRef = useRef(buffers);
  bufferRef.current = buffers;
  const key = target ? positionKey(target) : '';
  const currentKey = useRef(key); currentKey.current = key;
  const b = buffers[key] || fresh();

  useEffect(() => { alive.current = true; return () => { alive.current = false; }; }, []);
  function update(k: string, fn: (old: Buffer) => Buffer) {
    if (!alive.current) return;
    setBuffers(old => { const next = { ...old, [k]: fn(old[k] || fresh()) }; bufferRef.current = next; return next; });
  }
  function put(values: PracticeSubmissionView[]) {
    if (alive.current) setRecords(old => {
      const next = { ...old };
      for (const value of values) next[value.submission_id] = retainSubmission(old[value.submission_id], value);
      return next;
    });
  }
  function select(id: string) { selectionTicket.current++; setSelected(id); }
  function edit(fn: (old: Buffer) => Buffer) {
    if (target) update(key, old => ({ ...fn(old), edit: old.edit + 1, target, taskTitle: old.thread?.task.title, planRevision: old.thread?.plan_version }));
  }
  async function read(k: string, t: SubmissionTarget, initial = false) {
    const ticket = tickets.current[k] = (tickets.current[k] || 0) + 1;
    const editNo = bufferRef.current[k]?.edit || 0, selectionNo = selectionTicket.current;
    try {
      const thread = await submissionApi.thread(project, t);
      if (!alive.current || tickets.current[k] !== ticket) return;
      const old = bufferRef.current[k];
      if (old?.thread && (old.thread.version > thread.version || old.thread.task_version > thread.task_version)) return;
      put(thread.submissions);
      update(k, prev => {
        const last = thread.submissions.at(-1);
        const saved: Draft = { note: last?.note || '', repo: last?.repo_url || '', kind: last?.artifact_kind || 'other', parent: null,
          evidence: (last?.evidence || []).map(e => ({ ...e, localId: crypto.randomUUID() })) };
        return { ...prev, thread, target: t, taskTitle: thread.task.title, planRevision: thread.plan_version,
          initialized: true, conflict: false, error: '', ...(prev.conflict ? { pending: undefined } : {}),
          ...(initial && !prev.initialized && prev.edit === editNo ? { ...saved, baseline: raw(saved) } : {}) };
      });
      if (initial && currentKey.current === k && selectionTicket.current === selectionNo) select(thread.submissions.at(-1)?.submission_id || '');
    } catch (e) { if (tickets.current[k] === ticket) update(k, old => ({ ...old, error: message(e) })); }
  }
  useEffect(() => { select(bufferRef.current[key]?.thread?.submissions.at(-1)?.submission_id || ''); }, [key]);
  useEffect(() => {
    if (key && target && active && !bufferRef.current[key]?.initialized) void read(key, target, true);
  }, [key, active]);
  const hasDirty = Object.values(buffers).some(dirty);
  useEffect(() => {
    const warn = (e: BeforeUnloadEvent) => { if (hasDirty) { e.preventDefault(); e.returnValue = ''; } };
    window.addEventListener('beforeunload', warn); return () => window.removeEventListener('beforeunload', warn);
  }, [hasDirty]);

  async function save(k: string, body: PracticeSubmissionRequest) {
    tickets.current[k] = (tickets.current[k] || 0) + 1;
    const selectionNo = selectionTicket.current;
    update(k, old => ({ ...old, pending: body, busy: true, error: '', conflict: false }));
    try {
      const result = await submissionApi.save(project, body);
      if (!alive.current) return;
      put([...result.thread.submissions, result.submission]);
      update(k, old => ({ ...old, initialized: true, pending: undefined, conflict: false,
        thread: old.thread && (old.thread.version > result.thread.version || old.thread.task_version > result.thread.task_version) ? old.thread : result.thread,
        baseline: JSON.stringify({ note: body.note, repo_url: body.repo_url, evidence: body.evidence, artifact_kind: body.artifact_kind, parent_submission_id: body.parent_submission_id }) }));
      if (currentKey.current === k && selectionTicket.current === selectionNo) select(result.submission.submission_id);
      try { await onChanged?.(); } catch (e) { update(k, old => ({ ...old, error: `成果已经保存，工作区刷新未完成：${message(e)} 请读取记录，不必重复提交。` })); }
    } catch (e) {
      update(k, old => ({ ...old, error: message(e), conflict: e instanceof ApiError && e.status === 409,
        ...(rejected(e) && (e.status !== 409 || body.plan_id !== currentPlanId) ? { pending: undefined } : {}) }));
    } finally {
      tickets.current[k] = (tickets.current[k] || 0) + 1;
      update(k, old => ({ ...old, busy: false }));
    }
  }
  function submit() {
    if (!target || !b.thread) return;
    const evidence = b.evidence.map(({ localId: _id, ...e }) => e);
    const total = [b.note, b.repo, ...evidence.flatMap(e => [e.label, e.content, e.source_url || ''])].reduce((n, s) => n + Array.from(s).length, 0);
    if ((!b.note.trim() && !evidence.length) || Array.from(b.note).length > 20000 || total > 80000 || evidence.some(e =>
      !e.label.trim() || !e.content.trim() || Array.from(e.label).length > 200 || Array.from(e.content).length > 10000 || (e.kind === 'source_reference' && !e.source_url))) {
      update(key, old => ({ ...old, error: '请填写成果说明或完整证据；来源引用需要地址。说明最多 20000 字符，全部内容最多 80000 字符。' })); return;
    }
    void save(key, { ...target, note: b.note, repo_url: b.repo || null, evidence, artifact_kind: b.kind,
      parent_submission_id: b.parent, expected_plan_version: b.thread.plan_version, expected_task_version: b.thread.task_version,
      expected_version: b.thread.version, idempotency_key: crypto.randomUUID() });
  }
  const oldBuffers = Object.entries(buffers).filter(([, value]) => value.target && value.target.plan_id !== currentPlanId && (dirty(value) || value.pending));
  const samePosition = (s: PracticeSubmissionView) => !!target && s.plan_id === target.plan_id && s.stage_id === target.stage_id && s.task_id === target.task_id;
  const historicalRecords = Object.values(records).filter(s => !samePosition(s));
  return <section className="panel submission-panel" aria-label="成果提交与人工验收">
    <h2>成果提交与人工验收</h2>
    <p>提交实际完成的工作与证据。平台当前不会运行代码或独立核验来源；人工确认不会把知识标记为已验证，也不会自动完成学习位置。</p>
    {oldBuffers.length > 0 && <section aria-label="旧路线未保存的成果">
      <h3>旧路线未保存的成果</h3><p>这些本地说明和证据仍属于旧任务，只能复制保管，不会自动转入新任务。</p>
      {oldBuffers.map(([oldKey, value]) => <article key={oldKey}>
        <h4>路线第 {value.planRevision || '?'} 版 · {value.taskTitle || '旧任务'}</h4>
        <textarea aria-label={`旧成果说明与证据：${value.taskTitle || '旧任务'}`} readOnly rows={6} value={localCopy(value)} />
        <button className="btn" onClick={() => void copy(localCopy(value)).then(() => update(oldKey, old => ({ ...old, error: '旧成果已复制，请在本机保管。' }))).catch(() => update(oldKey, old => ({ ...old, error: '复制未完成，请选中文字手动复制。' })))}>复制旧成果与证据</button>
        {value.pending && <><p>原保存结果尚未确认。这里只核对原内容与原请求标识，不能发起新的旧路线保存。</p>
          <button className="btn" disabled={value.busy} onClick={() => void save(oldKey, value.pending!)}>核对旧请求（原内容与原请求标识）</button></>}
        {value.error && <p role="status">{value.error}</p>}
      </article>)}
    </section>}
    {!target ? <p>请选择当前路线中的实践任务。项目归档仍可读取历史成果。</p> : <>
      <div className="submission-editor">
        <label>成果说明原文<textarea aria-label="成果说明原文" rows={5} value={b.note} onChange={e => edit(old => ({ ...old, note: e.target.value }))} /></label>
        <label>成果仓库地址（可选）<input aria-label="成果仓库地址（可选）" value={b.repo} onChange={e => edit(old => ({ ...old, repo: e.target.value }))} /></label>
        <label>成果资料分类<select aria-label="成果资料分类" value={b.kind} onChange={e => edit(old => ({ ...old, kind: e.target.value as ArtifactKind }))}>
          {Object.entries(artifactLabels).map(([v, label]) => <option value={v} key={v}>{label}</option>)}
        </select></label>
        <label>补充到已有成果<select aria-label="补充到已有成果" value={b.parent || ''} onChange={e => edit(old => ({ ...old, parent: e.target.value || null }))}>
          <option value="">独立成果</option>{b.thread?.submissions.map(s => <option key={s.submission_id} value={s.submission_id}>补充第 {s.submission_no} 次成果</option>)}
        </select></label>
        <p>补充会创建新记录，原记录和人工决定保持不变。地址仅是未检查的元数据，不会访问仓库或网页。</p>
        {b.evidence.map((e, i) => <fieldset key={e.localId} aria-label={`证据 ${i + 1}`}>
          <legend>证据 {i + 1}</legend>
          <label>证据类别<select aria-label="证据类别" value={e.kind} onChange={event => edit(old => ({ ...old, evidence: old.evidence.map(v => v.localId === e.localId ? { ...v, kind: event.target.value as EvidenceKind } : v) }))}>
            {Object.entries(evidenceLabels).map(([v, label]) => <option key={v} value={v}>{label}</option>)}
          </select></label>
          <label>证据标题<input aria-label="证据标题" value={e.label} onChange={event => edit(old => ({ ...old, evidence: old.evidence.map(v => v.localId === e.localId ? { ...v, label: event.target.value } : v) }))} /></label>
          <label>证据原文<textarea aria-label="证据原文" rows={4} value={e.content} onChange={event => edit(old => ({ ...old, evidence: old.evidence.map(v => v.localId === e.localId ? { ...v, content: event.target.value } : v) }))} /></label>
          <label>证据来源地址<input aria-label="证据来源地址" value={e.source_url || ''} onChange={event => edit(old => ({ ...old, evidence: old.evidence.map(v => v.localId === e.localId ? { ...v, source_url: event.target.value || null } : v) }))} /></label>
          <button className="text-button" onClick={() => edit(old => ({ ...old, evidence: old.evidence.filter(v => v.localId !== e.localId) }))}>移除这项本地证据</button>
        </fieldset>)}
        <button className="btn" disabled={b.evidence.length >= 50} onClick={() => edit(old => ({ ...old, evidence: [...old.evidence, { localId: crypto.randomUUID(), kind: 'user_statement', label: '', content: '', source_url: null }] }))}>添加证据</button>
        <p aria-live="polite">{dirty(b) ? '有未保存成果或证据，刷新和退出前请保存或复制。' : '本地输入与读取的记录同步。'} 本地内容仅保留在本次页面。</p>
        <div className="chips">
          <button className="btn primary" disabled={!b.thread || b.busy || !!b.pending} onClick={submit}>保存成果与证据</button>
          {b.pending && !b.conflict && <button className="btn" disabled={b.busy} onClick={() => void save(key, b.pending!)}>重试原成果保存</button>}
          <button className="btn" disabled={b.busy} onClick={() => void read(key, target)}>读取当前成果记录</button>
          <button className="btn" onClick={() => void copy(localCopy(b)).then(() => update(key, old => ({ ...old, error: '本地成果已复制。' }))).catch(() => update(key, old => ({ ...old, error: '复制未完成，请手动复制。' })))}>复制本地成果与证据</button>
        </div>
        {b.error && <p role="alert">{b.error} {b.conflict ? '请读取当前成果记录；本地文字不会被覆盖。' : b.pending ? '结果未知，请重试原保存，不会自动重新提交。' : ''}</p>}
      </div>
      <label>选择已保存成果<select aria-label="选择已保存成果" value={selected} onChange={e => select(e.target.value)}>
        <option value="">选择记录</option>{b.thread?.submissions.map(s => <option key={s.submission_id} value={s.submission_id}>第 {s.submission_no} 次 · {artifactLabels[s.artifact_kind]}</option>)}
      </select></label>
      {b.thread?.history_truncated && <p>这里只显示最近 20 次提交；更早记录可从成果资料归档读取。</p>}
    </>}
    {historicalRecords.length > 0 && <section aria-label="本次页面中的历史成果">
      <h3>本次页面中的历史成果</h3><p>旧成果只供查看；若原人工决定结果未知，可核对完全相同的旧请求，不能创建新的旧任务决定。</p>
      {historicalRecords.map(s => <button className="resource-row" key={s.submission_id} onClick={() => select(s.submission_id)}>
        {s.task_snapshot.task?.title || '旧任务'} · 第 {s.submission_no} 次成果
      </button>)}
    </section>}
    {Object.values(records).map(s => <div key={s.submission_id} hidden={selected !== s.submission_id}>
      <SubmissionDetail project={project} submission={s}
        thread={samePosition(s) ? b.thread : undefined}
        canDecide={samePosition(s) && b.thread?.submissions.at(-1)?.submission_id === s.submission_id}
        onUpdated={(value, taskVersion) => {
          put([value]);
          if (samePosition(value) && taskVersion) update(key, old => ({ ...old, thread: old.thread ? { ...old.thread, task_version: Math.max(old.thread.task_version, taskVersion) } : undefined }));
        }} onChanged={onChanged} oldPosition={!samePosition(s)} onReadCurrent={samePosition(s) && target ? () => read(key, target) : undefined} />
    </div>)}
  </section>;
}

function localCopy(value: Draft) {
  return [value.note, value.repo ? `\n仓库地址（未检查）：${value.repo}` : '', ...value.evidence.map((e, i) =>
    `\n证据 ${i + 1} · ${evidenceLabels[e.kind]}\n${e.label}\n${e.content}${e.source_url ? `\n来源地址（未检查）：${e.source_url}` : ''}`)].join('');
}
export function SubmissionDetail({ project, submission: s, thread, canDecide = false, oldPosition = false, onUpdated, onChanged, onReadCurrent }: {
  project: string; submission: PracticeSubmissionView; thread?: PracticeSubmissionThreadView; canDecide?: boolean;
  onUpdated?: (value: PracticeSubmissionView, taskVersion?: number) => void;
  onChanged?: () => Promise<void> | void; onReadCurrent?: () => Promise<void> | void;
  oldPosition?: boolean;
}) {
  const [conclusion, setConclusion] = useState<PracticeSubmissionDecisionRequest['conclusion']>('needs_more_evidence');
  const [rationale, setRationale] = useState(''), [ack, setAck] = useState(false);
  const [coverage, setCoverage] = useState<Record<number, { evidence_indices: number[]; observation: string }>>({});
  const [pending, setPending] = useState<PracticeSubmissionDecisionRequest | null>(null);
  const [busy, setBusy] = useState(false), [error, setError] = useState('');
  const alive = useRef(true), readTicket = useRef(0);
  useEffect(() => { alive.current = true; return () => { alive.current = false; readTicket.current++; }; }, []);
  const criteria = s.task_snapshot.task?.acceptance || [];
  const coverageBody: PracticeSubmissionCoverageRequest[] = Object.entries(coverage).filter(([, value]) => value.evidence_indices.length || value.observation.trim())
    .map(([index, value]) => ({ criterion_index: Number(index), ...value }));
  const complete = criteria.length > 0 && criteria.every((_, i) => coverage[i]?.evidence_indices.length && coverage[i]?.observation.trim());
  const validPartial = coverageBody.every(c => c.evidence_indices.length > 0 && c.observation.trim() && Array.from(c.observation).length <= 2000);
  const allowed = !!thread && canDecide && !s.review && s.task_snapshot.snapshot_status === 'frozen';
  async function read() {
    const ticket = ++readTicket.current;
    try { const value = await submissionApi.get(project, s.submission_id); if (alive.current && ticket === readTicket.current) onUpdated?.(retainSubmission(s, value)); }
    catch (e) { if (alive.current) setError(message(e)); }
  }
  async function decide(body: PracticeSubmissionDecisionRequest) {
    readTicket.current++; setPending(body); setBusy(true); setError('');
    try {
      const result = await submissionApi.decide(project, s.submission_id, body);
      if (!alive.current) return;
      onUpdated?.(result.submission, result.task_version); setPending(null); setAck(false);
      try { await onChanged?.(); } catch (e) { if (alive.current) setError(`人工决定已记录，工作区刷新未完成：${message(e)} 请读取记录，不要重复决定。`); }
    } catch (e) {
      if (alive.current) { setError(message(e)); if (rejected(e)) { setPending(null); setAck(false); } }
    } finally { if (alive.current) setBusy(false); }
  }
  const review = s.review;
  return <article className="submission-detail" aria-label="所选成果详情">
    <h3>第 {s.submission_no || '?'} 次成果 · {artifactLabels[s.artifact_kind]}</h3>
    <p>保存时间：{new Date(s.created_at).toLocaleString()}</p>
    <p>{s.evidence_grade === 'insufficient' ? '证据不足，尚不能人工确认通过' : s.evidence_grade === 'reported' ? '已报告，未由平台核验' : '旧记录保留的已核验等级，本批未重新实测'}</p>
    <pre className="submission-raw">{s.note}</pre>
    <button className="btn" onClick={() => void copy(s.note).then(() => setError('已复制所选成果说明原文。')).catch(() => setError('复制未完成，请选中原文手动复制。'))}>复制已保存成果原文</button>
    {s.repo_url && <p>仓库地址（未检查）：{s.repo_url}</p>}
    {s.parent_submission_id && <p>这是原成果的补充记录；原成果标识：{s.parent_submission_id}</p>}
    <h4>已保存证据</h4>{s.evidence.map((e, i) => <section key={i}>
      <h5>证据 {i + 1} · {evidenceLabels[e.kind]} · {e.label}</h5><pre className="submission-raw">{e.content}</pre>
      {e.source_url && <p>来源地址（未检查）：{e.source_url}</p>}
    </section>)}
    {s.legacy_evidence.map((e, i) => <pre className="submission-raw" key={i}>{e}</pre>)}
    <details><summary>保存时的任务要求和版本</summary>
      {s.task_snapshot.snapshot_status === 'legacy_unfrozen' ? <p>{s.task_snapshot.warning || '旧成果没有冻结的当时要求，不会补写当前任务。'}</p> : <>
        <p>路线第 {s.task_snapshot.plan_revision} 版 · {s.task_snapshot.stage_title}</p>
        <h4>{s.task_snapshot.practice_project?.title}</h4><p>{s.task_snapshot.practice_project?.idea}</p>
        <h4>{s.task_snapshot.task?.title} · 任务第 {s.task_snapshot.task?.version} 版</h4><p>{s.task_snapshot.task?.goal}</p>
        {(['in_scope', 'out_scope', 'acceptance'] as const).map(k => <div key={k}><h5>{{ in_scope: '实施范围', out_scope: '范围之外', acceptance: '验收要求' }[k]}</h5><ul>{s.task_snapshot.task?.[k].map((v, i) => <li key={i}>{v}</li>)}</ul></div>)}
        <p>关联知识：{s.task_snapshot.task?.knowledge_links.map(n => `${n.title}（${({ core: '核心', supporting: '支撑', extension: '延伸' } as Record<string, string>)[n.role] || '关联角色未记录'}，内容第 ${n.content_version} 版）`).join('、')}</p>
      </>}
    </details>
    <p className="form-note">平台执行与来源核验当前不可用。外部报告、网址和人工决定都不代表平台实测或知识已验证。</p>
    {review && <section aria-label="已保存人工决定">
      <h4>{review.manual_confirmation && review.reviewer_kind === 'user' ? (review.conclusion === 'accepted' ? '人工确认通过（未平台实测）' : review.conclusion === 'needs_more_evidence' ? '人工决定：需要补充证据' : '人工决定：未通过') : '保留的历史评审记录'}</h4>
      <pre className="submission-raw">{review.rationale}</pre>{review.coverage.map(c => <div key={c.criterion_index}><p>要求 {c.criterion_index + 1}：{criteria[c.criterion_index] || '当时要求未记录'}</p><p>引用证据：{c.evidence_indices.map(i => i + 1).join('、')}</p><pre className="submission-raw">{c.observation}</pre></div>)}
    </section>}
    {allowed && <div className="submission-decision">
      <h4>对这条已保存成果作人工决定</h4>
      <label>人工决定<select aria-label="人工决定" value={conclusion} onChange={e => setConclusion(e.target.value as typeof conclusion)}>
        <option value="needs_more_evidence">需要补充证据</option><option value="not_passed">未通过</option><option value="accepted">人工确认通过</option>
      </select></label>
      <label>人工决定理由<textarea aria-label="人工决定理由" rows={3} value={rationale} onChange={e => setRationale(e.target.value)} /></label>
      {criteria.map((criterion, i) => <fieldset key={i} aria-label={`验收要求 ${i + 1}`}><legend>验收要求 {i + 1}</legend><p>{criterion}</p>
        {s.evidence.map((e, index) => <label className="submission-check" key={index}><input type="checkbox" aria-label={`选择证据 ${index + 1}`} checked={coverage[i]?.evidence_indices.includes(index) || false} onChange={event => setCoverage(old => {
          const value = old[i] || { evidence_indices: [], observation: '' };
          return { ...old, [i]: { ...value, evidence_indices: event.target.checked ? [...value.evidence_indices, index].sort((a, b) => a - b) : value.evidence_indices.filter(v => v !== index) } };
        })} />证据 {index + 1}：{e.label}</label>)}
        <label>实际观察<textarea aria-label="实际观察" rows={2} value={coverage[i]?.observation || ''} onChange={e => setCoverage(old => ({ ...old, [i]: { evidence_indices: old[i]?.evidence_indices || [], observation: e.target.value } }))} /></label>
      </fieldset>)}
      <label className="submission-check"><input type="checkbox" aria-label="我理解这是人工确认，平台没有独立运行代码或核验来源" checked={ack} onChange={e => setAck(e.target.checked)} />我理解这是人工确认，平台没有独立运行代码或核验来源</label>
      <button className="btn primary" disabled={busy || !!pending || !rationale.trim() || Array.from(rationale).length > 4000 || !validPartial || (conclusion === 'accepted' && (!ack || !complete || s.evidence_grade === 'insufficient'))} onClick={() => void decide({ conclusion, rationale, coverage: coverageBody, acknowledge_verification_limit: ack,
        expected_plan_version: thread!.plan_version, expected_task_version: thread!.task_version, expected_version: thread!.version, idempotency_key: crypto.randomUUID() })}>记录人工决定</button>
    </div>}
    {!review && !allowed && <p>历史或非最新成果仅供查看；只有当前任务的最新保存记录可以作新的人工决定。</p>}
    {pending && <button className="btn" disabled={busy} onClick={() => void decide(pending)}>{oldPosition ? '核对旧决定请求（原内容与原请求标识）' : '重试原人工决定'}</button>}
    <button className="btn" disabled={busy} onClick={() => void read()}>读取所选成果详情</button>
    {onReadCurrent && <button className="btn" disabled={busy} onClick={() => void onReadCurrent()}>核对当前任务版本</button>}
    {error && <p role="alert">{error} {pending ? '结果未知，请用原决定重试，不会自动重新作决定。' : ''}</p>}
  </article>;
}
