import { useEffect, useRef, useState } from 'react';
import { api, ApiError } from '../../api/client';
import type { DTO } from '../../api/types';

type Status = DTO['UnitProgress'];
type Target = Pick<DTO['ExposureChangeRequest'], 'plan_id' | 'stage_id' | 'unit_id'>;
export const progressLabels: Record<Status, string> = {
  not_started: '未开始', in_progress: '学习中', completed: '自述已完成', skipped: '已跳过',
};

export function ExposurePanel({projectId, target, onChange}: {
  projectId: string; target: Target; onChange: (value: DTO['ExposureView']) => void;
}) {
  const alive = useRef(true);
  const readSequence = useRef(0), editSequence = useRef(0);
  const [current, setCurrent] = useState<DTO['ExposureView'] | null>(null);
  const [history, setHistory] = useState<DTO['ExposureEventView'][]>([]);
  const [status, setStatus] = useState<Status>('not_started');
  const [pending, setPending] = useState<DTO['ExposureChangeRequest'] | null>(null);
  const [conflict, setConflict] = useState(false), [busy, setBusy] = useState(false), [error, setError] = useState('');
  async function read(initial = false) {
    const ticket = ++readSequence.current, editTicket = editSequence.current;
    let items: DTO['ExposureView'][], events: DTO['ExposureEventView'][];
    try {
      [items, events] = await Promise.all([
        api.listExposures(projectId, target.plan_id, target.stage_id), api.exposureHistory(projectId, target),
      ]);
    } catch (e) {
      if (alive.current && ticket === readSequence.current) throw e;
      return;
    }
    if (!alive.current || ticket !== readSequence.current) return;
    const value = items.find(e => e.unit_id === target.unit_id);
    if (!value) throw new Error('该学习位置暂不可用，请刷新。');
    setCurrent(value); setHistory(events); onChange(value);
    if (initial && editTicket === editSequence.current) setStatus(value.status);
    setPending(null); setConflict(false);
  }
  useEffect(() => {
    alive.current = true;
    read(true).catch(e => {if (alive.current) setError(e.message);});
    return () => {alive.current = false; ++readSequence.current;};
  }, []);
  async function act(work: () => Promise<void>) {
    setBusy(true); setError('');
    try {await work();} catch (e) {
      if (!alive.current) return;
      if (e instanceof ApiError && e.status === 409) setConflict(true);
      setError(e instanceof Error ? e.message : '操作失败，请读取最新进度。');
    } finally {if (alive.current) setBusy(false);}
  }
  async function submit(body: DTO['ExposureChangeRequest']) {
    ++readSequence.current;
    let result: DTO['ExposureChangeView'];
    try {result = await api.changeExposure(projectId, body);}
    finally {++readSequence.current;}
    if (!alive.current) return;
    setCurrent(result.exposure); onChange(result.exposure); setPending(null); setConflict(false);
    const events = await api.exposureHistory(projectId, target);
    if (alive.current) setHistory(events);
  }
  return <section className="panel" aria-label="出现位置学习进度">
    <h3>本次出现位置的学习进度</h3>
    <p className="form-note">这是本单元在当前计划阶段的自述进度，不代表知识掌握核验。跳过不会记为完成。</p>
    <p aria-live="polite">当前记录：{current ? progressLabels[current.status] : '读取中'}</p>
    <label>进度动作<select aria-label="进度动作" value={status} onChange={e => {++editSequence.current;setStatus(e.target.value as Status);}}>
      {Object.entries(progressLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
    </select></label>
    <div className="chips">
      <button className="btn" disabled={busy || !current || !!pending || status === current.status} onClick={() => {
        const body = {...target, status, expected_version: current!.version, idempotency_key: crypto.randomUUID()};
        setPending(body); void act(() => submit(body));
      }}>保存进度</button>
      {pending && !conflict && <button className="btn" disabled={busy} onClick={() => void act(() => submit(pending))}>重试原进度操作</button>}
      <button className="btn" disabled={busy} onClick={() => void act(() => read())}>读取最新进度</button>
    </div>
    {error && <p role="alert">{error}{conflict ? ' 请读取最新进度后核对；所选动作已保留。' : ' 结果不明时可重试原操作，保持同一请求。'}</p>}
    <h4>进度历史</h4>
    {!history.length && <p>尚无进度变更记录。</p>}
    {history.map(event => <div key={event.event_id} className="resource-row"><span>
      <strong>{progressLabels[event.from_status]} → {progressLabels[event.to_status]}</strong>
      <small>{new Date(event.created_at).toLocaleString()} · 当时知识：{event.node_snapshot.map(n => n.title).join('、') || '无'}
      · 当时安排的公开资料 {event.source_snapshot.public_assignments.length} 项，私有资料 {event.source_snapshot.private_selections.length} 项（不表示实际阅读）</small>
    </span></div>)}
  </section>;
}
