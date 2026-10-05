import type { Conversation } from '../../api/assistantClient';
export const terminalAssistant = new Set(['succeeded','failed','cancelled','canceled','unknown','reconciliation_required']);
export const latestAssistantRun = (c?:Conversation) => c?.messages.filter(m=>m.run_id).at(-1);
export const assistantBlocked = (c?:Conversation) => !!c?.read_only || !!c?.messages.some(m => m.run_id && (!terminalAssistant.has(m.run_status || '') || ['unknown','reconciliation_required'].includes(m.run_status || '')));
export const currentAssistantDraft = (c:Conversation) => c.messages.find(m=>m.message_id===c.current_draft_message_id && m.role==='user')?.content || '';
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
