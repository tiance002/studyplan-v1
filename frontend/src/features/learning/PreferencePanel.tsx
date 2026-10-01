import { useEffect, useRef, useState } from 'react';
import { api, ApiError } from '../../api/client';
import type { DTO } from '../../api/types';

type Put = DTO['PreferencePutRequest'];
type Target = Pick<Put, 'plan_id' | 'stage_id' | 'unit_id' | 'node_id'>;
type Scope = Put['scope'];
const labels: Record<Scope, string> = {project: '项目默认', unit: '本学习单元', node: '本知识节点'};
type Values = Pick<Put, 'mode' | 'language' | 'official_priority' | 'pace'>;
export function PreferencePanel({projectId, target}: {projectId: string; target: Target}) {
  const alive = useRef(true);
  const readSequence = useRef(0), editSequence = useRef(0);
  const [context, setContext] = useState<DTO['PreferenceContextView'] | null>(null);
  const [scope, setScope] = useState<Scope>('unit');
  const [values, setValues] = useState<Values>({mode:'mixed', language:'zh', official_priority:true, pace:'normal'});
  const [pending, setPending] = useState<{kind: 'put'; body: Put} | {kind: 'delete'; body: DTO['PreferenceDeleteRequest']} | null>(null);
  const [busy, setBusy] = useState(false), [error, setError] = useState(''), [conflict, setConflict] = useState(false);
  function fill(value: DTO['PreferenceView'] | null) {
    setValues(value ? {mode: value.mode, language: value.language, official_priority:value.official_priority, pace:value.pace as Put['pace']}
      : {mode:'mixed',language:'zh',official_priority:true,pace:'normal'});
  }
  async function read(initial = false) {
    const ticket = ++readSequence.current, editTicket = editSequence.current;
    let value: DTO['PreferenceContextView'];
    try {value = await api.resourcePreferences(projectId, target);}
    catch (e) {
      if (alive.current && ticket === readSequence.current) throw e;
      return;
    }
    if (!alive.current || ticket !== readSequence.current) return;
    setContext(value); setPending(null); setConflict(false);
    if (initial && editTicket === editSequence.current) fill(value.unit || value.effective);
  }
  useEffect(() => {
    alive.current = true;
    read(true).catch(e => {if (alive.current) setError(e.message);});
    return () => {alive.current=false;++readSequence.current;};
  }, []);
  async function act(work: () => Promise<void>) {
    setBusy(true);setError('');
    try {await work();} catch(e) {
      if (!alive.current) return;
      if (e instanceof ApiError && (e.status === 409 || e.status === 403)) setConflict(true);
      setError(e instanceof Error ? e.message : '操作失败，请读取最新偏好。');
    } finally {if (alive.current) setBusy(false);}
  }
  async function submit(command: NonNullable<typeof pending>) {
    ++readSequence.current;
    let result: DTO['PreferenceContextView'];
    try {
      result = command.kind === 'put'
        ? await api.saveResourcePreference(projectId, command.body)
        : await api.restoreResourcePreference(projectId, command.body);
    } finally {++readSequence.current;}
    if (alive.current) {setContext(result);setPending(null);setConflict(false);}
  }
  const modeLabels: Record<Put['mode'], string> = {mixed:'混合', both:'文字与视频', text_first:'文字优先', video_first:'视频优先'};
  return <section className="panel" aria-label="资料偏好设置">
    <h3>资料偏好</h3>
    <p className="form-note">节点覆盖优先于单元，单元优先于项目默认。保存整组偏好；局部调整只影响所选范围。</p>
    {context?.invalid_scopes?.length ? <p role="status">旧设置待修复：{context.invalid_scopes.map(s=>labels[s as Scope] || s).join('、')}。请逐项保存完整设置或恢复上级偏好。</p> : null}
    {context?.effective ? <p>当前生效：{modeLabels[context.effective.mode]} · {context.effective.language} · {context.effective.scope === 'system' ? '系统默认' : labels[context.effective.scope as Scope]}</p>
      : context && <p>当前没有可用的生效偏好。表单提供可编辑假设（混合、中文、正常节奏），保存后才生效。</p>}
    <label>偏好范围<select aria-label="偏好范围" value={scope} onChange={e => {
      ++editSequence.current;
      const next = e.target.value as Scope;setScope(next);
      if(context) fill(context[next] || context.effective);
    }}>
      <option value="project">项目默认</option><option value="unit">本学习单元</option>
      {target.node_id && <option value="node">本知识节点</option>}
    </select></label>
    <label>资料形式<select aria-label="资料形式" value={values.mode} onChange={e => {++editSequence.current;setValues({...values,mode:e.target.value as Put['mode']});}}>
      {Object.entries(modeLabels).map(([v,l])=><option key={v} value={v}>{l}</option>)}
    </select></label>
    <label>资料语言<input aria-label="资料语言" value={values.language} maxLength={16} onChange={e=>{++editSequence.current;setValues({...values,language:e.target.value});}} /></label>
    <label>学习节奏<select aria-label="学习节奏" value={values.pace} onChange={e=>{++editSequence.current;setValues({...values,pace:e.target.value as Put['pace']});}}>
      <option value="slow">慢速</option><option value="normal">正常</option><option value="fast">快速</option>
    </select></label>
    <label className="chips"><input type="checkbox" style={{width:'auto',margin:0}} checked={values.official_priority} onChange={e=>{++editSequence.current;setValues({...values,official_priority:e.target.checked});}} />官方资料优先</label>
    <div className="chips">
      <button className="btn" disabled={busy || !context || !!pending || !values.language.trim()} onClick={()=>{
        const command = {kind:'put' as const,body:{...target,...values,scope,expected_version:context!.versions[scope]}};
        setPending(command);void act(()=>submit(command));
      }}>保存资料偏好</button>
      <button className="btn" disabled={busy || !context || !!pending || (!context[scope] && !context.invalid_scopes?.includes(scope))} onClick={()=>{
        const command = {kind:'delete' as const,body:{...target,scope,expected_version:context!.versions[scope]}};
        setPending(command);void act(()=>submit(command));
      }}>恢复上级偏好</button>
      {pending && !conflict && <button className="btn" disabled={busy} onClick={()=>void act(()=>submit(pending))}>重试原偏好操作</button>}
      <button className="btn" disabled={busy} onClick={()=>void act(()=>read())}>读取最新偏好</button>
    </div>
    {error && <p role="alert">{error} 请读取最新偏好后核对；输入已保留。</p>}
  </section>;
}
