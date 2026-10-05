import {useEffect,useState} from 'react';
import {assistantTargetTitle,assistantDateGroup,assistantMatches,assistantModeLabel,assistantListStatus,assistantPreview} from './assistantState';
import type {AssistantController} from './useAssistant';
export function ConversationList({controller:a}:{controller:AssistantController}) {
  const [query,setQuery]=useState(''),[filter,setFilter]=useState('all');
  useEffect(()=>{if(a.listReady)void a.list();},[a.listReady,a.listScope]);
  useEffect(()=>{setQuery('');setFilter('all');},[a.listScope]);
  const rows=a.items.map(item=>a.listDetails?.[item.conversation_id]||item).filter(c=>assistantMatches(c,filter,query));
  const groups=[...new Set(rows.map(c=>assistantDateGroup(c.last_activity_at||c.created_at)))];
  return <div className="content conversation-library"><h1>我的会话</h1><p className="lede">回看阶段总结与实践辅导，接着上次的讨论继续。</p>
    <label className="conversation-search"><span aria-hidden="true">⌕</span><input aria-label="搜索会话" placeholder="搜索标题、最近消息或类型" value={query} onChange={e=>setQuery(e.target.value)}/></label>
    <div className="conversation-filters">{[['all','全部'],['summary','阶段总结'],['practice','实践辅导']].map(([key,label])=><button className="text-button" key={key} aria-pressed={filter===key} onClick={()=>setFilter(key)}>{label}</button>)}<span>{rows.length} 个会话</span></div>
    {a.listError&&<div className="assistant-inline-state" role="alert"><p>暂时无法加载会话。</p><button className="text-button" disabled={a.listLoading} onClick={()=>void a.list()}>重新加载</button></div>}
    {a.startPending&&<div className="assistant-inline-state"><p>会话创建结果尚待核对。</p><button className="text-button" disabled={a.starting} onClick={()=>void a.start(a.startPending!)}>核对创建结果</button></div>}
    {(!a.listReady||a.listLoading)&&<p role="status">正在读取会话…</p>}
    {a.listLoaded&&!a.listLoading&&!rows.length&&<div className="conversation-empty"><strong>{a.items.length?'没有找到这个会话':'暂无会话'}</strong><p>{a.items.length?'试试阶段名称或任务标题。':'从阶段的「开始总结」或任务的「开始实践」进入。'}</p></div>}
    {groups.map(group=><section className="conversation-group" key={group} aria-label={`${group}的会话`}><h2>{group}</h2><ul>{rows.filter(c=>assistantDateGroup(c.last_activity_at||c.created_at)===group).map(c=>{const status=assistantListStatus(c),active=a.open&&a.conversation?.conversation_id===c.conversation_id;return <li key={c.conversation_id}><button className={`conversation-row${active?' selected':''}`} aria-pressed={active} onClick={()=>void a.resume(c.conversation_id)}><span className={`conversation-type-icon ${c.mode}`} aria-hidden="true">{c.mode==='summary'?'▤':'⌘'}</span><span className="conversation-row-content"><span className="conversation-row-top"><strong title={assistantTargetTitle(c)}>{assistantTargetTitle(c)}</strong><span className={`conversation-row-status ${status==='已保存'?'saved':status==='待确认'?'proposal':''}`}>• {status}</span></span><span className="conversation-row-preview">{assistantPreview(c)}</span><span className="conversation-row-meta"><span>{assistantModeLabel(c.mode)}</span>{c.read_only&&<span className="conversation-readonly">历史路线只读</span>}<time dateTime={c.last_activity_at||c.created_at}>{new Date(c.last_activity_at||c.created_at).toLocaleTimeString('zh-CN',{hour:'2-digit',minute:'2-digit'})}</time></span></span></button></li>;})}</ul></section>)}
    {a.cursor&&<button className="text-button" disabled={a.listLoading} onClick={()=>void a.list(true)}>读取更早会话</button>}
  </div>;
}
export { SummaryPage as SummaryDetail } from './SummaryPage';
export { PromptPage as PracticeDetail } from './PromptPage';
