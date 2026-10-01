import { useEffect, useRef, useState } from 'react';
import { submissionApi } from '../../api/submissionClient';
import type { PracticeOutcomeView, PracticeSubmissionView } from '../../api/submissionClient';
import { artifactLabels, retainSubmission, SubmissionDetail } from './SubmissionPanel';

export function OutcomeArchive({ project }: { project: string }) {
  const [archive, setArchive] = useState<PracticeOutcomeView | null>(null);
  const [selected, setSelected] = useState<PracticeSubmissionView | null>(null);
  const [busy, setBusy] = useState(false), [error, setError] = useState('');
  const alive = useRef(true), ticket = useRef(0), detailTicket = useRef(0);
  useEffect(() => { alive.current = true; return () => { alive.current = false; ticket.current++; detailTicket.current++; }; }, []);
  async function read(more = false) {
    const id = ++ticket.current; setBusy(true); setError('');
    try {
      const value = await submissionApi.outcomes(project, more ? archive?.next_cursor || undefined : undefined);
      if (!alive.current || id !== ticket.current) return;
      setArchive(old => more && old ? { ...value, groups: value.groups.map(group => ({ ...group,
        items: [...(old.groups.find(v => v.kind === group.kind)?.items || []), ...group.items].filter((item, i, all) => all.findIndex(v => v.submission_id === item.submission_id) === i) })) } : value);
    } catch (e) { if (alive.current && id === ticket.current) setError(e instanceof Error ? e.message : '归档读取未完成。'); }
    finally { if (alive.current && id === ticket.current) setBusy(false); }
  }
  async function open(id: string) {
    const readNo = ++detailTicket.current; setError('');
    try { const value = await submissionApi.get(project, id); if (alive.current && readNo === detailTicket.current) setSelected(value); }
    catch (e) { if (alive.current && readNo === detailTicket.current) setError(e instanceof Error ? e.message : '成果详情读取未完成。'); }
  }
  return <section className="panel outcome-archive" aria-label="成果资料归档">
    <h2>成果资料归档</h2><p>按真实保存记录整理项目说明、评估、架构、设计决定、失败复盘和说明。空白分类等待补充，不生成测量、通过结果或虚构成果。</p>
    <button className="btn" disabled={busy} onClick={() => void read()}>读取成果资料归档</button>
    {archive && <div className="outcome-groups">{archive.groups.map(group => <section key={group.kind}>
      <h3>{artifactLabels[group.kind]}</h3><p>归档记录共 {group.total_records} 条</p>
      {!group.total_records ? <p>待补充</p> : !group.items.length ? <p>本页没有此类记录，可继续读取。</p> : group.items.map(item => <button className="resource-row" key={item.submission_id} onClick={() => void open(item.submission_id)}>
        {item.task_title || '旧成果（当时任务未记录）'} · {item.plan_revision ? `路线第 ${item.plan_revision} 版` : '旧路线版本未记录'} · {item.manual_confirmation && item.conclusion === 'accepted' ? '人工确认通过，未平台实测' : '查看实际记录'}
      </button>)}
    </section>)}</div>}
    {archive?.next_cursor && <button className="btn" disabled={busy} onClick={() => void read(true)}>读取更早的成果资料</button>}
    {selected && <SubmissionDetail key={selected.submission_id} project={project} submission={selected} onUpdated={value => setSelected(old => retainSubmission(old || undefined, value))} />}
    {error && <p role="alert">{error}</p>}
  </section>;
}
