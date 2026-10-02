import { useEffect, useMemo, useSyncExternalStore } from 'react';
import { api, ApiError } from '../../api/client';
import type { DTO, ResourceCandidate, ResourceInspectionRequest, ResourceTarget } from '../../api/types';
import { resourceBuffer } from './resourceBuffer';

const provenanceLabels: Record<ResourceCandidate['provenance'], string> = {
  official:'官方来源候选', community:'社区来源', user_provided:'用户提供', curated_pool:'资料池', github_candidate:'GitHub 候选', search_candidate:'搜索候选',
};
const inspectionLabels = { metadata_only:'候选未读', readme_read:'README已读', chapter_or_index_checked:'章节/目录抽查', controlled_review:'受控内容审核' };
const roleLabels = { candidate:'候选', mainline_candidate:'主线候选（需另行预览与确认）', reference:'参考资料', unsuitable:'不适配' };
const chapterLabels = { listed:'仅目录列出，未读', read:'已读取', unsupported:'格式暂不支持，未读' };
const observed = (value: boolean | null | undefined) => value == null ? '未知' : value ? '已观察到' : '未观察到';
function publicUrl(value: string) {
  try { const url = new URL(value); return ['https:', 'http:'].includes(url.protocol) && !url.username && !url.password ? url.href : undefined; }
  catch { return undefined; }
}
function ResourceLink({ url, title }: {url:string; title:string}) {
  const href = publicUrl(url);
  return href ? <a href={href} target="_blank" rel="noreferrer">{title}</a> : <span>{title}（链接不可用）</span>;
}
function Evidence({ resource }: { resource: ResourceCandidate }) {
  const evidence = resource.discovery;
  if (!evidence) return <p className="form-note">候选未读 · 旧记录未保存读取证据 · 许可证未知</p>;
  return <div className="form-note resource-evidence" aria-label={resource.title+'的资料证据'}>
    <p><strong>{inspectionLabels[evidence.inspection_status]}</strong> · 未核验学习掌握 · {roleLabels[evidence.recommended_role]}</p>
    <p>原始排序：{evidence.provider_rank ?? '未知'} · 相关性分数：{evidence.provider_score ?? '服务未提供'}</p>
    {evidence.snippet && <p>{evidence.snippet}</p>}
    {evidence.repo && <p>仓库：{evidence.repo.owner}/{evidence.repo.name} · 分支：{evidence.repo.default_branch || '未知'} · {evidence.repo.license ? '许可证：'+evidence.repo.license : '许可证未知'} · Stars：{evidence.repo.stars ?? '未知'} · 更新时间：{evidence.repo.updated_at || '未知'}</p>}
    {!evidence.repo && <p>许可证未知</p>}
    <p>教学结构：{observed(evidence.signals?.teaching_structure)} · 先修说明：{observed(evidence.signals?.prerequisites)} · 练习：{observed(evidence.signals?.exercises)} · 难度：{evidence.signals?.difficulty || 'unknown'} · 语言：{evidence.signals?.language || 'unknown'} · 技术版本：{evidence.signals?.version || 'unknown'}</p>
    {!!evidence.reasons?.length && <ul aria-label="排序理由">{evidence.reasons.map((reason,index) => <li key={index}>{reason}</li>)}</ul>}
    {!!evidence.files?.length && <div><strong>实际读取证据</strong><ul>{evidence.files.map((file,index) => <li key={file.path+':'+index}>
      <ResourceLink url={file.url} title={file.path} /> · 行 {file.line_start}–{file.line_end} · {file.truncated ? '已截断' : '未截断'}<br />
      读取时间：{file.fetched_at} · Blob SHA：{file.blob_sha || '未知'} · 内容 Hash：{file.content_hash}
    </li>)}</ul></div>}
    {!!evidence.chapters?.length && <div><strong>章节与未检查部分（作者顺序）</strong><ol>{[...evidence.chapters].sort((a,b) => a.order-b.order).map((chapter,index) => <li key={chapter.path+':'+index}>
      {chapter.title} · {chapter.path} · {chapterLabels[chapter.status]}{chapter.module_keys?.length ? ' · 模块：'+chapter.module_keys.join('、') : ''}
    </li>)}</ol></div>}
    {!!evidence.limitations?.length && <ul aria-label="检查限制">{evidence.limitations.map((limitation,index) => <li key={index}>{limitation}</li>)}</ul>}
    {evidence.inspection_status !== 'metadata_only' && <p>抽查只覆盖上述文件和范围，不代表整门课程质量认证。</p>}
  </div>;
}

export function ResourcePicker({ actorKey, projectId, target, nodeId, moduleTitles = {}, topic = '' }: {
  actorKey:string; projectId:string; target:ResourceTarget; nodeId?:string; moduleTitles?:Record<string,string>; topic?:string;
}) {
  const buffer = useMemo(() => resourceBuffer(actorKey, projectId, target, nodeId), [actorKey, projectId, target.plan_id, target.stage_id, target.unit_id, nodeId]);
  const state = useSyncExternalStore(buffer.subscribe, buffer.snapshot);
  const { query, source, pending, search, selected, title, url, error, busy, notSubmitted, inspections } = state;
  // Async closures write to their original position. Logout invalidates the buffer lease.
  async function reload() {
    const ticket = ++buffer.readSequence;
    const value = await api.selectedResources(projectId, target);
    if (ticket === buffer.readSequence) buffer.update({selected:value});
  }
  useEffect(() => {
    reload().catch(e => buffer.update({error:e instanceof Error ? e.message : '无法读取已选资料。'}));
  }, [buffer]);
  async function act(work: () => Promise<void>) {
    if (buffer.snapshot().busy || !buffer.active) return;
    buffer.update({busy:true,error:''});
    try { await work(); } catch(e) { buffer.update({error:e instanceof Error ? e.message : '操作失败，请读取原记录。'}); }
    finally { buffer.update({busy:false}); }
  }
  async function submit(body: DTO['ResourceSearchRequest']) {
    const value = await api.searchResources(projectId, body);
    buffer.update({search:value,notSubmitted:false});
  }
  function start() {
    if (buffer.snapshot().busy || !buffer.active) return;
    const body: DTO['ResourceSearchRequest'] = { ...target, ...(nodeId ? {node_id:nodeId} : {}), source, query:query.trim(), idempotency_key:crypto.randomUUID() };
    buffer.update({pending:body,search:null,inspections:{},mappings:{},notSubmitted:false});
    void act(() => submit(body));
  }
  function recover() {
    if (!pending) return;
    void act(async () => {
      try {
        const value = search ? await api.resourceSearch(projectId,search.search_id,target) : await api.resourceSearchByKey(projectId,pending.idempotency_key,target);
        buffer.update({search:value,notSubmitted:false});
      } catch(e) {
        if (e instanceof ApiError && e.status === 404) { buffer.update({notSubmitted:true}); throw new Error('尚未发现原查询的提交记录。可继续读取，或明确提交原查询。'); }
        throw e;
      }
    });
  }
  function beginInspection(candidate: ResourceCandidate) {
    if (!search || buffer.snapshot().busy || !buffer.active) return;
    const body: ResourceInspectionRequest = {...target,search_id:search.search_id,candidate_id:candidate.resource_id,idempotency_key:crypto.randomUUID()};
    buffer.update({inspections:{...buffer.snapshot().inspections,[candidate.resource_id]:{pending:body,view:null}}});
    void act(async () => {
      const view = await api.inspectResource(projectId,body);
      buffer.update({inspections:{...buffer.snapshot().inspections,[candidate.resource_id]:{pending:body,view}}});
    });
  }
  function recoverInspection(candidateId: string) {
    const original = buffer.snapshot().inspections[candidateId];
    if (!original) return;
    void act(async () => {
      const view = original.view ? await api.resourceInspection(projectId,original.view.inspection_id,target) : await api.resourceInspectionByKey(projectId,original.pending.idempotency_key,target);
      buffer.update({inspections:{...buffer.snapshot().inspections,[candidateId]:{...original,view}}});
    });
  }
  return <section className="panel" aria-label="单元资料选取">
    <h3>补充本单元资料</h3>
    <p className="form-note">仅在点击后向所选来源发送搜索词与当前资料偏好。请使用必要主题词，避免粘贴个人目标、总结或 Prompt。搜索与检查独立触发，选取资料不代表完成学习。</p>
    <label>搜索来源<select aria-label="搜索来源" value={source} onChange={event => buffer.update({source:event.target.value as 'web'|'github'})}><option value="web">网页</option><option value="github">GitHub</option></select></label>
    <label>搜索词<input aria-label="搜索词" maxLength={500} value={query} onChange={event => buffer.update({query:event.target.value})} /></label>
    {topic && <button className="btn quiet" disabled={busy} onClick={() => buffer.update({query:topic.slice(0,160)+' tutorial'})}>填入模块主题词</button>}
    <div className="chips">
      <button className="btn" disabled={busy || !query.trim()} onClick={start}>{pending ? '重新搜索' : '搜索资料'}</button>
      {pending && <button className="btn" disabled={busy} onClick={recover}>读取原查询</button>}
      {notSubmitted && pending && <button className="btn" disabled={busy} onClick={() => void act(() => submit(pending))}>提交原查询</button>}
    </div>
    {pending && !search && <p className="form-note">原查询：{pending.source === 'github' ? 'GitHub' : '网页'} · {pending.query} · {busy ? '正在读取响应' : '响应未知，请读取原查询核对；不会自动重复搜索'}</p>}
    {error && <p role="alert" className="form-note">{error}</p>}
    {search && <div aria-live="polite">
      <p>{search.status === 'succeeded' ? '查询完成' : search.status === 'failed' ? '查询失败，可手动接入资料' : search.status === 'reconciliation_required' ? '查询结果待核对，请读取原查询或手动接入资料' : '查询已提交，可能仍在处理或响应未知；读取原查询不会重复搜索'}：{search.query}</p>
      <p className="form-note">原查询来源：{(search.source || pending?.source) === 'github' ? 'GitHub' : '网页'} · 结果尚未自动接入主线。</p>
      {search.error && <p>{search.error}</p>}
      {search.status === 'succeeded' && !search.candidates.length && <p>没有找到候选，尚无适配主线。可修改搜索词、切换来源或手动接入资料。</p>}
      {search.candidates.map(item => {
        const inspection = inspections[item.resource_id];
        const displayed = inspection?.view?.candidate || item;
        const unresolved = inspection && (!inspection.view || !['succeeded','failed'].includes(inspection.view.status));
        const moduleKeys = Array.isArray(search.context_snapshot?.module_keys)
          ? search.context_snapshot.module_keys.filter((key):key is string => typeof key === 'string') : [];
        const readChapters = (displayed.discovery?.chapters || []).filter(chapter => chapter.status === 'read'
          && displayed.discovery?.files?.some(file => file.path === chapter.path));
        const mapping = state.mappings[item.resource_id] || {moduleKey:'',chapterPath:'',role:'reference' as const};
        const selectionTarget = 'context_snapshot' in search ? target
          : {plan_id:target.plan_id,stage_id:target.stage_id,unit_id:target.unit_id};
        const updateMapping = (patch:Partial<typeof mapping>) => buffer.update({mappings:{...buffer.snapshot().mappings,[item.resource_id]:{...mapping,...patch}}});
        return <article key={item.resource_id}>
          <div className="resource-row"><span><ResourceLink url={displayed.url} title={displayed.title} /><small>未核验 · {provenanceLabels[displayed.provenance]} · {displayed.source_note}</small></span>
            <button className="btn" disabled={busy} onClick={() => void act(async () => { await api.selectResource(projectId,{...selectionTarget,search_id:search.search_id,candidate_id:item.resource_id,role:'reference'}); await reload(); })}>选用此资料</button>
          </div>
          <Evidence resource={displayed} />
          {inspection?.view?.status === 'succeeded' && !!moduleKeys.length && !!readChapters.length && <fieldset>
            <legend>将已读章节关联到本单元模块</legend>
            <label>关联模块<select aria-label="关联模块" value={mapping.moduleKey} onChange={event => updateMapping({moduleKey:event.target.value})}>
              <option value="">请选择本单元模块</option>{moduleKeys.map(key => <option key={key} value={key}>{moduleTitles[key] || key}</option>)}
            </select></label>
            <label>已读章节<select aria-label="已读章节" value={mapping.chapterPath} onChange={event => updateMapping({chapterPath:event.target.value})}>
              <option value="">请选择实际读过的章节</option>{readChapters.map(chapter => <option key={chapter.path} value={chapter.path}>{chapter.title}</option>)}
            </select></label>
            <label>私人资料用途<select aria-label="私人资料用途" value={mapping.role} onChange={event => updateMapping({role:event.target.value as typeof mapping.role})}>
              <option value="reference">参考</option><option value="supplement">补充</option><option value="comparison">对照</option>
              <option value="case_study">案例</option><option value="practice">实践</option><option value="primary">主线候选（需另行预览确认）</option>
            </select></label>
            <button className="btn" disabled={busy || !mapping.moduleKey || !mapping.chapterPath} onClick={() => void act(async () => {
              await api.selectResource(projectId,{...target,search_id:search.search_id,candidate_id:item.resource_id,
                module_keys:[mapping.moduleKey],chapter_paths:[mapping.chapterPath],role:mapping.role}); await reload();
            })}>选用并映射已读章节</button>
            <p className="form-note">关联保存在私人资料中；主线替换仍需差异预览和明确确认。</p>
          </fieldset>}
          {(search.source || pending?.source || item.discovery?.source) === 'github' && <div className="chips">
            <button className="btn" disabled={busy || Boolean(unresolved) || search.status !== 'succeeded'} onClick={() => beginInspection(item)}>检查教程/章节</button>
            {inspection && <button className="btn" disabled={busy} onClick={() => recoverInspection(item.resource_id)}>读取原检查</button>}
          </div>}
          {inspection && <p className="form-note">检查状态：{inspection.view?.status === 'succeeded' ? '检查完成' : inspection.view?.status === 'failed' ? '检查失败' : '已提交或响应未知；仅回读原检查，不重复外发'}{inspection.view?.error ? ' · '+inspection.view.error : ''}{inspection.view ? ' · 外发回执：'+(inspection.view.receipts?.length ?? 0) : ''}</p>}
        </article>;
      })}
    </div>}
    <h3>手动接入资料</h3>
    <p className="form-note">可粘贴文档、课程或 GitHub 网址，只保存为本单元的私人未核验资料。主线替换需另行差异预览和明确确认。</p>
    <label>资料标题<input aria-label="资料标题" value={title} maxLength={300} onChange={event => buffer.update({title:event.target.value})} /></label>
    <label>资料网址<input aria-label="资料网址" type="url" value={url} maxLength={4096} onChange={event => buffer.update({url:event.target.value})} /></label>
    <button className="btn" disabled={busy || !title.trim() || !url.trim()} onClick={() => void act(async () => { await api.manualResource(projectId,{...target,title:title.trim(),url:url.trim()}); await reload(); buffer.update({title:'',url:''}); })}>保存手动资料</button>
    <h3>已选资料</h3>
    {!selected.length && <p>本单元还没有选取资料。</p>}
    {selected.map(item => <article key={item.selection_id}><div className="resource-row">
      <span><ResourceLink url={item.resource.url} title={item.resource.title} /><small>私人资料 · 未核验 · {provenanceLabels[item.resource.provenance]} · {item.resource.source_note}</small></span>
      <button className="btn" disabled={busy} onClick={() => void act(async () => {await api.removeResource(projectId,item.selection_id,target);await reload();})}>移除此资料</button>
    </div><Evidence resource={item.resource} /></article>)}
  </section>;
}
