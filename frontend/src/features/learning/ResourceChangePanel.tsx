import { useEffect, useRef, useState } from 'react';
import { api, ApiError } from '../../api/client';
import type { DTO } from '../../api/types';

type Preview = DTO['ResourceChangePreviewView'];
type Command = { kind: 'preview'; body: DTO['ResourceChangeRequest'] }
  | { kind: 'decision'; id: string; action: 'confirm' | 'cancel'; body: DTO['ResourceChangeDecisionRequest'] };
const obj = (value: unknown): Record<string, unknown> => value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {};
const words = (value: unknown, fallback = '未提供') => typeof value === 'string' && value ? value : fallback;
const rows = (value: unknown): Record<string, unknown>[] => Array.isArray(value) ? value.map(obj) : [];
const count = (value: unknown) => typeof value === 'number' ? String(value) : '未知';

function SourceSnapshot({ value, label }: { value: unknown; label: string }) {
  const snapshot = obj(value), source = obj(snapshot.source);
  return <section><h4>{label}</h4>
    <p>{words(source.title, '历史记录未保存当时来源标题')} · 版本 {count(snapshot.source_version)}</p>
    <p className="form-note">{words(source.creator)} · {words(source.language)} · {words(source.documentation_version)}</p>
    {typeof source.canonical_url === 'string' && <p>{source.canonical_url}</p>}
    {rows(snapshot.sections).length ? <ol>{rows(snapshot.sections).map(section => <li key={words(section.section_id)}>{words(section.title)}<small> {words(section.url)}</small></li>)}</ol>
      : <p className="muted">未保存可核对的历史章节元数据。</p>}
  </section>;
}

export function ResourceChangePanel({ projectId, planId, revision, stageId, primary, onPublished }: {
  projectId: string; planId: string; revision: number; stageId: string;
  primary: DTO['StageResourceAssignmentView'] | undefined; onPublished: () => Promise<void>;
}) {
  const alive = useRef(true), sequence = useRef(0);
  const storageKey = `studyplan:resource-change:${projectId}:${planId}:${stageId}`;
  const [catalog, setCatalog] = useState<DTO['ResourceCatalogView'][]>([]);
  const [sourceId, setSourceId] = useState(''), [start, setStart] = useState(''), [end, setEnd] = useState('');
  const [policy, setPolicy] = useState<'' | 'copy_active' | 'keep_history_only'>('');
  const [preview, setPreview] = useState<Preview | null>(null), [pending, setPending] = useState<Command | null>(null);
  const [ack, setAck] = useState(false), [busy, setBusy] = useState(false), [error, setError] = useState('');
  const source = catalog.find(item => obj(item.source).source_id === sourceId);
  const chapters = rows(source?.sections), startIndex = chapters.findIndex(s => s.section_id === start), endIndex = chapters.findIndex(s => s.section_id === end);
  const valid = !!primary && !!source && startIndex >= 0 && endIndex >= startIndex && policy !== '';
  function remember(id: string | null) { try { if (id) localStorage.setItem(storageKey, id); else localStorage.removeItem(storageKey); } catch { /* Storage is optional; the server retains the preview. */ } }
  useEffect(() => {
    alive.current = true;
    const read = ++sequence.current;
    api.resourceChangeCatalog(projectId).then(value => { if (alive.current && sequence.current === read) setCatalog(value); }).catch(e => { if (alive.current && sequence.current === read) setError(e.message); });
    let id: string | null = null; try { id = localStorage.getItem(storageKey); } catch { /* Optional storage. */ }
    if (id) api.resourceChange(projectId, id).then(value => { if (alive.current && sequence.current === read) setPreview(value); }).catch(e => { if (alive.current && sequence.current === read) setError(e.message); });
    return () => { alive.current = false; sequence.current++; };
  }, [projectId, storageKey]);
  async function submit(command: Command) {
    const read = ++sequence.current; setBusy(true); setError('');
    try {
      if (command.kind === 'preview') {
        const value = await api.previewResourceChange(projectId, command.body);
        if (!alive.current || read !== sequence.current) return;
        setPreview(value); setAck(false); remember(value.proposal_id); setPending(null);
      } else {
        const value = await api.decideResourceChange(projectId, command.id, command.action, command.body);
        if (!alive.current || read !== sequence.current) return;
        setPreview(old => old ? { ...old, status: value.status } : old); setPending(null); remember(null);
        if (value.status === 'confirmed') await onPublished();
      }
    } catch (e) {
      if (!alive.current || read !== sequence.current) return;
      setError(e instanceof Error ? e.message : '操作未完成，请读取或重试原操作。');
      // Network/5xx/malformed success leaves an exact command for uncertain-result recovery.
      if (e instanceof ApiError && e.status >= 400 && e.status < 500) setPending(null);
    } finally { if (alive.current && read === sequence.current) setBusy(false); }
  }
  function createPreview() {
    if (!valid || !primary || !source) return;
    const command: Command = { kind: 'preview', body: { plan_id: planId, stage_id: stageId, assignment_id: primary.assignment_id,
      source_ref: sourceId, source_version: Number(obj(source.source).source_version),
      section_refs: chapters.slice(startIndex, endIndex + 1).map(s => words(s.section_id, '')),
      expected_version: revision, copy_policy: policy, idempotency_key: crypto.randomUUID() } };
    setPending(command); void submit(command);
  }
  function decide(action: 'confirm' | 'cancel') {
    if (!preview || (action === 'confirm' && !ack)) return;
    const command: Command = { kind: 'decision', id: preview.proposal_id, action, body: {
      expected_version: preview.base_revision, preview_hash: preview.preview_hash,
      idempotency_key: crypto.randomUUID(), acknowledge_warnings: action === 'confirm' && ack } };
    setPending(command); void submit(command);
  }
  async function reread() {
    if (!preview) return;
    const read = ++sequence.current; setBusy(true); setError('');
    try { const value = await api.resourceChange(projectId, preview.proposal_id); if (alive.current && read === sequence.current) {
      setPreview(value); setAck(false);
      if (value.status !== 'pending') { setPending(null); remember(null); }
      if (value.status === 'confirmed') await onPublished();
    } }
    catch (e) { if (alive.current && read === sequence.current) setError(e instanceof Error ? e.message : '读取失败'); }
    finally { if (alive.current && read === sequence.current) setBusy(false); }
  }
  const impact = obj(preview?.impact), coverage = obj(impact.coverage), workload = obj(impact.workload), progress = obj(impact.progress), bindings = obj(impact.private_bindings);
  return <section className="panel" aria-label="主线资料替换"><h3>替换本阶段主线</h3>
    <p className="form-note">先查看差异，再明确确认新路线。旧学习记录和资料历史保留；新路线的学习位置从未开始起步。</p>
    {!primary ? <p>本阶段没有可替换的主线分配。</p> : <>
      <fieldset disabled={busy || !!pending}><legend>选择新主线</legend>
        <label>公开资料目录<select aria-label="公开资料目录" value={sourceId} onChange={e => { setSourceId(e.target.value); setStart(''); setEnd(''); }}><option value="">请选择已审核来源</option>{catalog.map(item => <option key={words(item.source.source_id)} value={words(item.source.source_id, '')}>{words(item.source.title)} · v{count(item.source.source_version)}</option>)}</select></label>
        <label>起始章节<select aria-label="起始章节" value={start} onChange={e => { setStart(e.target.value); setEnd(e.target.value); }}><option value="">请选择</option>{chapters.map(s => <option key={words(s.section_id)} value={words(s.section_id, '')}>{words(s.title)}</option>)}</select></label>
        <label>结束章节<select aria-label="结束章节" value={end} onChange={e => setEnd(e.target.value)}><option value="">请选择</option>{chapters.map((s, index) => <option disabled={index < startIndex} key={words(s.section_id)} value={words(s.section_id, '')}>{words(s.title)}</option>)}</select></label>
        <label>私人资料沿用策略<select aria-label="私人资料沿用策略" value={policy} onChange={e => setPolicy(e.target.value as typeof policy)}><option value="">请明确选择</option><option value="copy_active">将当前有效私人资料绑定沿用到新路线</option><option value="keep_history_only">保留旧版资料历史，不沿用到新路线</option></select></label>
        {source?.index_truncated && <p className="form-note">此目录仅展示前300章。只可选择当前展示的区间，其余章节需要补齐目录后使用。</p>}
        <button className="btn" disabled={!valid || preview?.status === 'pending'} onClick={createPreview}>查看主线替换差异</button>
      </fieldset>
      {pending && <button className="btn" disabled={busy} onClick={() => void submit(pending)}>重试原主线操作</button>}
      {preview && <div><p>预览状态：{preview.status === 'pending' ? '待确认' : preview.status === 'confirmed' ? '已确认' : '已取消'}</p>
        <SourceSnapshot value={preview.before} label="原主线" /><SourceSnapshot value={preview.after} label="新主线" />
        <p>影响 {Array.isArray(impact.unit_ids) ? impact.unit_ids.length : '未知'} 个学习单元；旧版已开始 {count(progress.started_units)}，已完成 {count(progress.completed_units)}。</p>
        <p>章节数 {count(workload.before_section_count)} → {count(workload.after_section_count)}；预计时长、环境与节奏：未提供可核对信息。</p>
        <p>知识覆盖：{coverage.mapping_status === 'available' ? '已有目录映射' : '映射不足，无法证明完整覆盖'}；先修：{impact.prerequisite_status === 'recorded_relations_only' ? '保留已记录的前置关系，仍需核对适用性' : '缺少明确检查结果'}。</p>
        {rows(impact.nodes).length > 0 && <p>相关知识：{rows(impact.nodes).map(n => words(n.title)).join('、')}</p>}
        {Array.isArray(coverage.required_extension_topics) && coverage.required_extension_topics.length > 0 && <p>必需补缺：{coverage.required_extension_topics.map(topic => words(topic)).join('、')}</p>}
        <p>私人资料：保留历史，{preview.copy_policy === 'copy_active' ? `沿用 ${count(bindings.copy_count)} 份有效绑定` : '不沿用绑定'}。</p>
        <ul>{preview.warnings.map(w => <li key={w}>{w}</li>)}</ul>
        <button className="btn" disabled={busy} onClick={() => void reread()}>读取原主线预览</button>
        {preview.status === 'pending' && <><label><input type="checkbox" checked={ack} disabled={busy || !!pending} onChange={e => setAck(e.target.checked)} />我已查看差异和缺少信息的提示，确认按此预览继续</label>
          <button className="btn primary" disabled={busy || !!pending || !ack} onClick={() => decide('confirm')}>确认发布新路线</button>
          <button className="btn" disabled={busy || !!pending} onClick={() => decide('cancel')}>取消主线预览</button></>}
      </div>}
    </>}
    {error && <><p role="alert" className="error">{error}</p><button className="btn" disabled={busy} onClick={() => void onPublished().catch(e => setError(e.message))}>读取当前路线</button></>}
  </section>;
}
