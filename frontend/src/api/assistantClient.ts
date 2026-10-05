import { requestApi } from './client';
export type AssistantMode = 'summary' | 'practice';
export type AssistantIntent = 'work_draft' | 'question';
export type AssistantMessage = {message_id:string;sequence:number;role:'user'|'assistant';intent:string;content:string;created_at:string;run_id:string|null;run_status:string|null;run_version:number|null;draft_message_id:string|null;trigger_message_id:string|null;error_class:string|null;status:'continue'|'ready_to_draft'|null;proposal:string|null};
export type Conversation = {conversation_id:string;project_id:string;plan_id:string;plan_revision:number;stage_id:string;task_id:string|null;mode:AssistantMode;title:string;context:Record<string,unknown>;context_hash:string;created_at:string;read_only:boolean;current_draft_message_id:string|null;messages:AssistantMessage[];formal_saves:{save_id:string;proposal_message_id?:string|null;draft_message_id:string;content:string;artifact_id:string;artifact_type:string;formal_version:number;created_at:string}[];formal_version:number;messages_truncated:boolean;message_cursor:number|null;last_activity_at:string;has_formal_save:boolean};
export type ConversationSummary = Omit<Conversation,'messages'|'formal_saves'|'messages_truncated'|'message_cursor'>;
export type AssistantStart = {plan_id:string;stage_id:string;mode:AssistantMode;task_id:string|null;idempotency_key:string;force_new?:boolean};
export type AssistantSend = {content:string;idempotency_key:string;intent?:AssistantIntent;consent_to_model?:true};
export type AssistantSave = {content:string;proposal_message_id?:string;draft_message_id?:string;expected_version:number;idempotency_key:string};
export type AssistantCancel = {run_id:string;expected_version:number;idempotency_key:string};
const path = (id?:string) => `/assistant/conversations${id ? `/${encodeURIComponent(id)}` : ''}`;
const scope = (project:string) => `?project_id=${encodeURIComponent(project)}`;
export const assistantApi = {
  create:(project:string,body:AssistantStart) => requestApi<Conversation>(`${path()}${scope(project)}`,body),
  list:(project:string,cursor?:string) => requestApi<{items:ConversationSummary[];next_cursor:string|null}>(`${path()}${scope(project)}&limit=20${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ''}`),
  read:(project:string,id:string,beforeSequence?:number) => requestApi<Conversation>(`${path(id)}${scope(project)}${beforeSequence===undefined?'':`&before_sequence=${beforeSequence}`}`),
  send:(project:string,id:string,body:AssistantSend) => requestApi<Conversation>(`${path(id)}/messages${scope(project)}`,body),
  save:(project:string,id:string,body:AssistantSave) => requestApi<Conversation>(`${path(id)}/save${scope(project)}`,body),
  cancel:(project:string,id:string,body:AssistantCancel) => requestApi<Conversation>(`${path(id)}/cancel${scope(project)}`,body),
};
