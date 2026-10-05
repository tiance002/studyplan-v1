import {useEffect} from 'react';
import {assistantTargetTitle} from './assistantState';
import type {AssistantController} from './useAssistant';
export function ConversationList({controller:a}:{controller:AssistantController}) {
  useEffect(()=>{if(a.listReady)void a.list();},[a.listReady,a.listScope]);
  return <div className="content"><p className="eyebrow">CONVERSATIONS</p><h1>我的会话</h1><p className="lede">恢复总结与实践辅导。打开历史只读取会话，不请求模型。</p><button className="btn" disabled={!a.listReady||a.listLoading} onClick={()=>void a.list()}>刷新会话列表</button>{a.listError&&<p role="alert">{a.listError}</p>}{a.startPending&&<button className="btn" disabled={a.starting} onClick={()=>void a.start(a.startPending!)}>重新读取状态</button>}{(!a.listReady||a.listLoading)&&<p role="status">正在恢复会话列表…</p>}{a.listLoaded&&!a.listLoading&&!a.items.length&&<p>暂无会话。请从已确认路线的阶段或具体实践任务开始。</p>}{a.items.map(c=><button className="resource-row" key={c.conversation_id} onClick={()=>void a.resume(c.conversation_id)}><strong>{assistantTargetTitle(c)}</strong><span>{c.mode==='summary'?'阶段总结':'实践辅导'} · {new Date(c.last_activity_at||c.created_at).toLocaleString()} · {c.has_formal_save?'已保存正式成果':'尚未保存'}</span></button>)}{a.cursor&&<button className="btn" disabled={a.listLoading} onClick={()=>void a.list(true)}>读取更早会话</button>}</div>;
}
export { SummaryPage as SummaryDetail } from './SummaryPage';
export { PromptPage as PracticeDetail } from './PromptPage';
