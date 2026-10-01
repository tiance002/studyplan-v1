import { useEffect, useRef, useState } from 'react';
import { api, ApiError } from '../../api/client';
import type { DTO } from '../../api/types';

type Target = Pick<DTO['ResourceSearchRequest'], 'plan_id' | 'stage_id' | 'unit_id'>;
type Search = DTO['ResourceSearchView'];
const provenanceLabels: Record<DTO['ResourceCandidateView']['provenance'], string> = {
  official: '官方来源候选', community: '社区来源', user_provided: '用户提供',
  curated_pool: '资料池', github_candidate: 'GitHub 候选',
  search_candidate: '搜索候选',
};

export function ResourcePicker({ projectId, target }: { projectId: string; target: Target }) {
  const alive = useRef(true);
  const [query, setQuery] = useState('');
  const [pending, setPending] = useState<DTO['ResourceSearchRequest'] | null>(null);
  const [search, setSearch] = useState<Search | null>(null);
  const [selected, setSelected] = useState<DTO['SelectedResourceView'][]>([]);
  const [title, setTitle] = useState(''), [url, setUrl] = useState('');
  const [error, setError] = useState(''), [busy, setBusy] = useState(false);
  const [notSubmitted, setNotSubmitted] = useState(false);
  useEffect(() => {
    alive.current = true;
    api.selectedResources(projectId, target).then(value => {
      if (alive.current) setSelected(value);
    }).catch(e => { if (alive.current) setError(e.message); });
    return () => { alive.current = false; };
  }, [projectId, target.plan_id, target.stage_id, target.unit_id]);

  async function act(work: () => Promise<void>) {
    setBusy(true); setError('');
    try { await work(); } catch (e) {
      if (alive.current) setError(e instanceof Error ? e.message : '操作失败，请重试。');
    } finally { if (alive.current) setBusy(false); }
  }
  async function reload() {
    const value = await api.selectedResources(projectId, target);
    if (alive.current) setSelected(value);
  }
  async function submit(body: DTO['ResourceSearchRequest']) {
    const value = await api.searchResources(projectId, body);
    if (alive.current) { setSearch(value); setNotSubmitted(false); }
  }
  function start() {
    const body = { ...target, query: query.trim(), idempotency_key: crypto.randomUUID() };
    setPending(body); setSearch(null); setNotSubmitted(false);
    void act(() => submit(body));
  }
  function recover() {
    if (!pending) return;
    void act(async () => {
      try {
        const value = search
          ? await api.resourceSearch(projectId, search.search_id, target)
          : await api.resourceSearchByKey(projectId, pending.idempotency_key, target);
        if (alive.current) { setSearch(value); setNotSubmitted(false); }
      } catch (e) {
        if (e instanceof ApiError && e.status === 404 && alive.current) {
          setNotSubmitted(true);
          throw new Error('尚未发现原查询的提交记录。可继续读取，或明确提交原查询。');
        }
        throw e;
      }
    });
  }
  return <section className="panel" aria-label="单元资料选取">
    <h3>补充本单元资料</h3>
    <p className="form-note">点击搜索会将搜索词发送给搜索服务。搜索结果与手动网址均为未核验候选，选取资料不代表完成学习。</p>
    <label>搜索词<input aria-label="搜索词" maxLength={500} value={query} onChange={e => setQuery(e.target.value)} /></label>
    <div className="chips">
      <button className="btn" disabled={busy || !query.trim()} onClick={start}>{pending ? '重新搜索' : '搜索资料'}</button>
      {pending && <button className="btn" disabled={busy} onClick={recover}>读取原查询</button>}
      {notSubmitted && pending && <button className="btn" disabled={busy} onClick={() => void act(() => submit(pending))}>提交原查询</button>}
    </div>
    {error && <p role="alert" className="form-note">{error}</p>}
    {search && <div aria-live="polite">
      <p>{search.status === 'succeeded' ? '查询完成' : search.status === 'failed' ? '查询失败，可手动接入资料' : search.status === 'reconciliation_required' ? '查询结果待核对，请读取原查询或手动接入资料' : '查询已提交，可能仍在处理或响应未知；读取原查询不会重复搜索，也可手动接入'}：{search.query}</p>
      {search.error && <p>{search.error}</p>}
      {search.status === 'succeeded' && !search.candidates.length && <p>没有找到候选，可修改搜索词或手动接入资料。</p>}
      {search.candidates.map(item => <div className="resource-row" key={item.resource_id}>
        <span><a href={item.url} target="_blank" rel="noreferrer">{item.title}</a><small>未核验 · {provenanceLabels[item.provenance]} · {item.source_note}</small></span>
        <button className="btn" disabled={busy} onClick={() => void act(async () => {
          await api.selectResource(projectId, { ...target, search_id: search.search_id, candidate_id: item.resource_id }); await reload();
        })}>选用此资料</button>
      </div>)}
    </div>}
    <h3>手动接入资料</h3>
    <p className="form-note">可粘贴文档、课程或 GitHub 网址，只保存为本单元的未核验资料。</p>
    <label>资料标题<input aria-label="资料标题" value={title} maxLength={300} onChange={e => setTitle(e.target.value)} /></label>
    <label>资料网址<input aria-label="资料网址" type="url" value={url} maxLength={4096} onChange={e => setUrl(e.target.value)} /></label>
    <button className="btn" disabled={busy || !title.trim() || !url.trim()} onClick={() => void act(async () => {
      await api.manualResource(projectId, { ...target, title: title.trim(), url: url.trim() });
      await reload(); if (alive.current) { setTitle(''); setUrl(''); }
    })}>保存手动资料</button>
    <h3>已选资料</h3>
    {!selected.length && <p>本单元还没有选取资料。</p>}
    {selected.map(item => <div className="resource-row" key={item.selection_id}>
      <span><a href={item.resource.url} target="_blank" rel="noreferrer">{item.resource.title}</a><small>未核验 · {provenanceLabels[item.resource.provenance]} · {item.resource.source_note}</small></span>
      <button className="btn" disabled={busy} onClick={() => void act(async () => {
        await api.removeResource(projectId, item.selection_id, target); await reload();
      })}>移除此资料</button>
    </div>)}
  </section>;
}
