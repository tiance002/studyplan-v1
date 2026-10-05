import type { Conversation } from '../../api/assistantClient';
export const terminalAssistant = new Set(['succeeded','failed','cancelled','canceled','unknown','reconciliation_required']);
export const latestAssistantRun = (c?:Conversation) => c?.messages.filter(m=>m.run_id).at(-1);
export const assistantBlocked = (c?:Conversation) => !!c?.read_only || !!c?.messages.some(m => m.run_id && (!terminalAssistant.has(m.run_status || '') || ['unknown','reconciliation_required'].includes(m.run_status || '')));
export const currentAssistantDraft = (c:Conversation) => c.messages.find(m=>m.message_id===c.current_draft_message_id && m.role==='user')?.content || '';
export const summaryWelcome = {title:'把你对本阶段的总结发给我。',checks:['核心知识是否覆盖；','关键概念之间的关系是否讲清楚；','有没有明显误解或遗漏；','是否能用自己的话说明本阶段重点。']};
export const practiceWelcome = {title:'把你准备交给 AI / Codex 的 Prompt 发给我。',checks:['任务目标是否明确；','修改范围和约束是否清楚；','输入与输出要求是否完整；','验收标准是否能真正证明任务完成；','有没有容易让 AI 扩大范围或误解任务的地方。']};
export function assistantTargetTitle(c:Pick<Conversation,'mode'|'title'|'context'>):string {
  const direct=c.context[c.mode==='summary'?'stage_title':'task_title'];
  if(typeof direct==='string'&&direct.trim())return direct;
  const snapshot=c.context[c.mode==='summary'?'stage':'task'];
  if(snapshot&&typeof snapshot==='object'&&'title' in snapshot&&typeof snapshot.title==='string')return snapshot.title;
  return c.title.replace(/^(阶段总结|总结辅导|实践辅导|实践 Prompt|Prompt 辅导)\s*[·：:]\s*/,'');
}
export const assistantModeLabel = (mode:string) => mode==='summary'?'阶段总结':'实践辅导';
export function assistantListStatus(c:Pick<Conversation,'has_formal_save'> & Partial<Pick<Conversation,'messages'|'formal_saves'>>):string {
  if(c.has_formal_save||c.formal_saves?.length)return '已保存';
  if(!c.messages)return '未加载';
  return c.messages.some(m=>m.role==='assistant'&&m.status==='ready_to_draft'&&m.proposal)?'待确认':'未保存';
}
export const assistantPreview = (c:Partial<Pick<Conversation,'messages'>>) => c.messages?.at(-1)?.content || (c.messages?'还没有消息':'最近消息暂未加载');
export function assistantMatches(c:Pick<Conversation,'mode'|'title'|'context'> & Partial<Pick<Conversation,'messages'>>,mode:string,query:string):boolean {
  return (mode==='全部'||mode==='all'||c.mode===mode)&&`${assistantTargetTitle(c)} ${assistantPreview(c)} ${assistantModeLabel(c.mode)}`.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase());
}
export function assistantDateGroup(value:string,now=new Date()):string {
  const date=new Date(value);if(Number.isNaN(date.getTime()))return '更早';
  const day=new Date(now.getFullYear(),now.getMonth(),now.getDate()),previous=new Date(day);previous.setDate(previous.getDate()-1);
  const dateDay=new Date(date.getFullYear(),date.getMonth(),date.getDate());
  if(dateDay.getTime()===day.getTime())return '今天';if(dateDay.getTime()===previous.getTime())return '昨天';
  return `${date.getFullYear()===now.getFullYear()?'':`${date.getFullYear()}年`}${date.getMonth()+1}月${date.getDate()}日`;
}
export function finishProposalEdit(edits:Record<string,string>|undefined,id:string|undefined,saved:string):Record<string,string> {
  const result={...edits};if(id&&result[id]===saved)delete result[id];return result;
}
export function mergeConversation(old:Conversation|undefined,next:Conversation):Conversation {
  if (old && (old.messages.at(-1)?.sequence || 0) > (next.messages.at(-1)?.sequence || 0)) return old;
  const messages=[...next.messages,...(old?.messages.filter(m=>!next.messages.some(n=>n.message_id===m.message_id))||[])].sort((a,b)=>a.sequence-b.sequence).map(m=>{
    const known=old?.messages.find(value=>value.message_id===m.message_id);
    if(known&&known.run_id===m.run_id&&((known.run_version||0)>(m.run_version||0)||(terminalAssistant.has(known.run_status||'')&&!terminalAssistant.has(m.run_status||''))))return known;
    return m;
  });
  const pagination=old?.message_cursor!==null&&old?.message_cursor!==undefined&&next.message_cursor!==null&&next.message_cursor!==undefined&&old.message_cursor<next.message_cursor?{messages_truncated:old.messages_truncated,message_cursor:old.message_cursor}:old?.messages_truncated===false?{messages_truncated:false,message_cursor:null}:{};
  if (old && old.formal_version > next.formal_version) return {...next,...pagination,messages,formal_version:old.formal_version,formal_saves:old.formal_saves};
  return {...next,...pagination,messages};
}
export function mergeAssistantHistory(current:Conversation,page:Conversation):Conversation {
  if(current.conversation_id!==page.conversation_id)return current;
  const messages=[...current.messages,...page.messages.filter(m=>!current.messages.some(n=>n.message_id===m.message_id))].sort((a,b)=>a.sequence-b.sequence);
  return {...current,messages,messages_truncated:page.messages_truncated,message_cursor:page.message_cursor};
}
