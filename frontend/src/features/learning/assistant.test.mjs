import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import ts from 'typescript';
const compile = path => ts.transpileModule(readFileSync(new URL(path,import.meta.url),'utf8'),{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}}).outputText;
const moduleUrl = code => `data:text/javascript;base64,${Buffer.from(code).toString('base64')}`;
const state = await import(moduleUrl(compile('./assistantState.ts')));
const {formalRefreshPolicy}=await import(moduleUrl(compile('./artifactRefresh.ts')));
const React=await import('react');
const {renderToStaticMarkup}=await import('react-dom/server');
const panelSource=ts.transpileModule(readFileSync(new URL('../../components/LearningAssistantPanel.tsx',import.meta.url),'utf8'),{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.React}}).outputText;
const panelModules=panelSource.replace("from 'react'","from 'react'").replace("'../features/learning/assistantState'",JSON.stringify(moduleUrl(compile('./assistantState.ts')))).replace("'./assistantFocus'",JSON.stringify(moduleUrl(compile('../../components/assistantFocus.ts')))).replace("'./assistantProposalScroll'",JSON.stringify(moduleUrl(compile('../../components/assistantProposalScroll.ts'))));
// Bare React imports resolve through an explicit file URL from this workspace.
const {createRequire}=await import('node:module');const {pathToFileURL}=await import('node:url');const require=createRequire(import.meta.url);
const reactUrl=pathToFileURL(require.resolve('react')).href;
const {LearningAssistantPanel}=await import(moduleUrl(`import React from ${JSON.stringify(reactUrl)};\n${panelModules.replace("'react'",JSON.stringify(reactUrl))}`));
const clientUrl=moduleUrl(compile('../../api/client.ts'));
const {setCsrfToken}=await import(clientUrl);
const {assistantApi}=await import(moduleUrl(compile('../../api/assistantClient.ts').replace("'./client'",JSON.stringify(clientUrl))));
const message = (id,sequence,role='user',intent='work_draft',content='  draft\n') => ({message_id:id,sequence,role,intent,content,run_id:null,run_status:null});
const base = () => ({conversation_id:'c',plan_id:'p',read_only:false,formal_version:0,formal_saves:[],current_draft_message_id:'draft',messages:[message('draft',1),message('question',2,'user','question','why?'),message('answer',3,'assistant','question','advice')]});
test('question and assistant reply never become the current user draft',()=>assert.equal(state.currentAssistantDraft(base()),'  draft\n'));
test('forged assistant draft pointer cannot become user original',()=>assert.equal(state.currentAssistantDraft({...base(),current_draft_message_id:'answer'}),''));
for(const status of ['queued','running','unknown','reconciliation_required'])test(`${status} prevents a new dispatch`,()=>assert.equal(state.assistantBlocked({...base(),messages:[{...message('draft',1),run_id:'r',run_status:status}]}),true));
for(const status of ['succeeded','failed','cancelled'])test(`${status} releases a known terminal turn`,()=>assert.equal(state.assistantBlocked({...base(),messages:[{...message('draft',1),run_id:'r',run_status:status}]}),false));
test('old Plan conversation blocks new model dispatch',()=>assert.equal(state.assistantBlocked({...base(),read_only:true}),true));
test('late older snapshot preserves newer messages',()=>{const c=base();assert.equal(state.mergeConversation(c,{...c,messages:[message('draft',1)]}),c);});
test('late snapshot cannot remove a confirmed formal save',()=>{const old={...base(),formal_version:2,formal_saves:[{save_id:'s'}]};assert.deepEqual(state.mergeConversation(old,base()).formal_saves,old.formal_saves);});
test('late queued snapshot cannot regress a terminal run',()=>{const old={...base(),messages:[{...message('draft',1),run_id:'r',run_status:'succeeded',run_version:3}]};const next={...old,messages:[{...old.messages[0],run_status:'queued',run_version:1}]};assert.equal(state.mergeConversation(old,next).messages[0].run_status,'succeeded');});
test('null-run known admission failure preserves user draft and permits formal saving',()=>{const c={...base(),messages:[{...message('draft',1),run_status:'failed',error_class:'assistant_binding_unavailable'}]};assert.equal(state.currentAssistantDraft(c),'  draft\n');assert.equal(state.assistantBlocked(c),false);});
test('older message page preserves current scope, draft and confirmed saves',()=>{const current={...base(),messages:[message('draft',100),message('question',121)],message_cursor:100,messages_truncated:true,formal_version:2,formal_saves:[{save_id:'s'}]};const page={...current,current_draft_message_id:'old',formal_version:0,formal_saves:[],messages:[message('old',1),message('draft',100)],message_cursor:null,messages_truncated:false};const merged=state.mergeAssistantHistory(current,page);assert.equal(merged.current_draft_message_id,'draft');assert.equal(merged.formal_version,2);assert.equal(merged.formal_saves[0].save_id,'s');assert.deepEqual(merged.messages.map(m=>m.sequence),[1,100,121]);assert.equal(merged.message_cursor,null);});
test('normal refresh retains already loaded history and exhausted cursor',()=>{const old={...base(),messages:[message('old',1),message('draft',100)],messages_truncated:false,message_cursor:null};const next={...old,messages:[message('draft',100),message('new',122)],messages_truncated:true,message_cursor:100};const merged=state.mergeConversation(old,next);assert.deepEqual(merged.messages.map(m=>m.sequence),[1,100,122]);assert.equal(merged.messages_truncated,false);assert.equal(merged.message_cursor,null);});
test('history from another conversation cannot contaminate current conversation',()=>{const current=base();assert.equal(state.mergeAssistantHistory(current,{...current,conversation_id:'other'}),current);});
test('artifact refresh preserves dirty draft/CAS and requires explicit read before a new version',()=>{const dirty={text:'  unsaved\n',baseline:'old',edit:2,initialized:true,thread:{version:1},conflict:true};const automatic=formalRefreshPolicy(dirty,2,2,false,true);assert.deepEqual(automatic,{version:1,adoptText:false,clearConflict:false});const explicit=formalRefreshPolicy(dirty,2,2,false,false);assert.deepEqual(explicit,{version:2,adoptText:false,clearConflict:true});assert.equal(dirty.text,'  unsaved\n');});
test('clean artifact refresh adopts newest text only if no edits happened during GET',()=>{const clean={text:'old',baseline:'old',edit:1,initialized:true,thread:{version:1}};assert.deepEqual(formalRefreshPolicy(clean,2,1,false,true),{version:2,adoptText:true,clearConflict:false});assert.equal(formalRefreshPolicy({...clean,edit:2},2,1,false,true).adoptText,false);assert.equal(formalRefreshPolicy({...clean,pending:{key:'save'}},2,1,false,true).version,1);});
test('fixed welcome uses exact mode copy and target title strips legacy UI prefix',()=>{assert.equal(state.summaryWelcome.title,'把你对本阶段的总结发给我。');assert.equal(state.summaryWelcome.checks.length,4);assert.equal(state.practiceWelcome.title,'把你准备交给 AI / Codex 的 Prompt 发给我。');assert.equal(state.practiceWelcome.checks.length,5);assert.equal(state.assistantTargetTitle({mode:'practice',title:'实践 Prompt · 真实任务',context:{}}),'真实任务');});
test('saving a proposal clears only its confirmed edit and preserves late edits/other proposals',()=>{assert.deepEqual(state.finishProposalEdit({one:'exact',two:'other'},'one','exact'),{two:'other'});assert.deepEqual(state.finishProposalEdit({one:'late edit'},'one','sent'),{one:'late edit'});});
test('chat render has fixed welcome, natural composer and safe proposal without technical IDs',()=>{const conversation={...base(),mode:'summary',title:'阶段总结 · 核心概念',context:{},stage_id:'PRIVATE_STAGE_ID',conversation_id:'PRIVATE_CONVERSATION_ID',read_only:false,messages:[{...message('PRIVATE_MESSAGE_ID',1,'assistant','reply','hello <script>'),status:'ready_to_draft',proposal:'proposal <img onerror=bad>'}]};const html=renderToStaticMarkup(React.createElement(LearningAssistantPanel,{close(){},controller:{conversation,buffer:{text:'',proposalEdits:{},busy:false},blocked:false,update(){},send(){},save(){}}}));assert.match(html,/阶段总结 · 核心概念/);assert.match(html,/采用并保存/);assert.match(html,/修改后保存/);assert.match(html,/把你对本阶段的总结发给我/);assert.doesNotMatch(html,/PRIVATE_|checkbox|<select|消息意图|同意将|所评稿|路线第/);assert.match(html,/&lt;script&gt;/);assert.doesNotMatch(html,/<script>|<img onerror/);});
test('both mode custom proposal saves enforce the API 20000 character boundary',()=>{
 for(const mode of ['summary','practice'])for(const count of [20000,20001]){const conversation={...base(),mode,title:'目标',context:{},read_only:false,messages:[{...message('proposal-message',1,'assistant','reply','ready'),status:'ready_to_draft',proposal:'candidate'}]};const html=renderToStaticMarkup(React.createElement(LearningAssistantPanel,{close(){},controller:{conversation,buffer:{text:'',proposalEdits:{'proposal-message':'x'.repeat(count)},busy:false},blocked:false,update(){},send(){},save(){}}}));const button=html.match(/<button[^>]*>保存我的版本<\/button>/)?.[0];assert.ok(button);assert.equal(button.includes('disabled=""'),count>20000,`${mode}/${count}`);}
});
test('GET refresh/list only read; POST body preserves exact content and same idempotency key',async()=>{
 const original=globalThis.fetch,calls=[];setCsrfToken('csrf');
 globalThis.fetch=async(url,options)=>{calls.push({url,options});return {ok:true,status:200,json:async()=>base()};};
 try{await assistantApi.read('project space','c/x');await assistantApi.list('project space','next/x');const body={content:' \n my draft\n ',intent:'work_draft',idempotency_key:'same',consent_to_model:true};await assistantApi.send('project space','c/x',body);await assistantApi.send('project space','c/x',body);await assistantApi.save('project space','c/x',{content:'final',draft_message_id:'draft',expected_version:2,idempotency_key:'save'});await assistantApi.read('project space','c/x',100);
 assert.equal(calls[0].options.method,'GET');assert.equal(calls[1].options.method,'GET');assert.match(calls[0].url,/c%2Fx\?project_id=project%20space/);assert.match(calls[1].url,/limit=20&cursor=next%2Fx/);assert.deepEqual(JSON.parse(calls[2].options.body),body);assert.equal(calls[2].options.body,calls[3].options.body);assert.equal(calls[2].options.headers['X-CSRF-Token'],'csrf');assert.match(calls[4].url,/\/save\?/);assert.equal(calls[5].options.method,'GET');assert.match(calls[5].url,/before_sequence=100/);
 }finally{globalThis.fetch=original;setCsrfToken('');}
});
test('V1.1 natural send and proposal save transport only user content and frozen operation fields',async()=>{
 const original=globalThis.fetch,calls=[];globalThis.fetch=async(url,options)=>{calls.push({url,body:options.body?JSON.parse(options.body):null});return {ok:true,status:200,json:async()=>base()};};
 try{await assistantApi.send('p','c',{content:'  natural question\n',idempotency_key:'turn'});await assistantApi.save('p','c',{content:'custom proposal',proposal_message_id:'server-assistant-message',expected_version:2,idempotency_key:'formal'});await assistantApi.create('p',{plan_id:'plan',stage_id:'stage',task_id:null,mode:'summary',force_new:true,idempotency_key:'new'});assert.deepEqual(calls[0].body,{content:'  natural question\n',idempotency_key:'turn'});assert.equal(calls[1].body.proposal_message_id,'server-assistant-message');assert.equal('draft_message_id' in calls[1].body,false);assert.equal('intent' in calls[0].body,false);assert.equal('consent_to_model' in calls[0].body,false);assert.equal(calls[2].body.force_new,true);}finally{globalThis.fetch=original;}
});

test('conversation list presentation derives saved/proposal/draft and local search/date groups',()=>{
 const c={...base(),mode:'summary',title:'阶段总结 · 核心概念',context:{},created_at:'2026-10-05T09:00:00+08:00',last_activity_at:'2026-10-05T09:00:00+08:00',has_formal_save:false,messages:[{...message('a',1,'assistant','reply','最近消息'),proposal:'候选',status:'ready_to_draft'}]};
 assert.equal(state.assistantListStatus(c),'待确认');assert.equal(state.assistantListStatus({...c,has_formal_save:true}),'已保存');assert.equal(state.assistantListStatus({...c,messages:[]}),'未保存');
 assert.equal(state.assistantMatches(c,'全部','最近消息'),true);assert.equal(state.assistantMatches(c,'practice',''),false);assert.equal(state.assistantMatches(c,'summary','阶段总结'),true);
 assert.equal(state.assistantDateGroup(c.last_activity_at,new Date('2026-10-05T12:00:00+08:00')),'今天');assert.equal(state.assistantDateGroup('2026-10-04T09:00:00+08:00',new Date('2026-10-05T12:00:00+08:00')),'昨天');assert.equal(state.assistantDateGroup('2026-10-02T09:00:00+08:00',new Date('2026-10-05T12:00:00+08:00')),'10月2日');
});
for(const length of [50,2000,19960])test(`proposal ${length} characters renders collapsed six-line body and expansion control`,()=>{
 const conversation={...base(),mode:'practice',title:'任务',context:{},messages:[{...message('p',1,'assistant','reply','说明'),status:'ready_to_draft',proposal:'字'.repeat(length)}]};
 const html=renderToStaticMarkup(React.createElement(LearningAssistantPanel,{close(){},controller:{conversation,buffer:{text:'',busy:false},blocked:false,update(){},send(){},save(){}}}));assert.match(html,/assistant-proposal-body clamped/);assert.match(html,/aria-expanded="false"/);assert.match(html,/展开全文/);assert.doesNotMatch(html,/重新读取状态/);
});

const listSource=ts.transpileModule(readFileSync(new URL('./SupportingPages.tsx',import.meta.url),'utf8'),{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.React}}).outputText.replace(/export \{.*?\} from .*?;/g,'').replace("'react'",JSON.stringify(reactUrl)).replace("'./assistantState'",JSON.stringify(moduleUrl(compile('./assistantState.ts'))));
const {ConversationList}=await import(moduleUrl(`import React from ${JSON.stringify(reactUrl)};\n${listSource}`));
test('formal conversation list renders local search/filters, detail previews and honest unloaded states',()=>{
 const date=new Date().toISOString(),items=['saved','proposal','draft','missing'].map(id=>({conversation_id:id,mode:'summary',title:'阶段总结 · '+id,context:{},has_formal_save:id==='saved',created_at:date,last_activity_at:date}));
 const listDetails=Object.fromEntries(items.slice(0,3).map(item=>[item.conversation_id,{...item,messages:[{...message(item.conversation_id,1,'assistant','reply','最近消息 '+item.conversation_id),status:item.conversation_id==='proposal'?'ready_to_draft':'continue',proposal:item.conversation_id==='proposal'?'候选':null}]}]));
 const html=renderToStaticMarkup(React.createElement(ConversationList,{controller:{items,listDetails,listReady:true,listScope:'scope',listLoaded:true,listLoading:false,list(){},resume(){},open:true,conversation:listDetails.proposal}}));
 for(const copy of ['搜索标题、最近消息或类型','全部','阶段总结','实践辅导','今天','最近消息 saved','待确认','已保存','未保存','未加载','最近消息暂未加载'])assert.ok(html.includes(copy),copy);
 assert.match(html,/conversation-row selected/);assert.doesNotMatch(html,/刷新会话列表|重新读取状态|打开历史只读取|不请求模型|CONVERSATIONS/);
});
test('unknown turn renders readonly reconciliation and does not expose technical error classes',()=>{
 const conversation={...base(),mode:'practice',title:'任务',context:{},messages:[{...message('u',1),run_id:'r',run_status:'unknown',error_class:'PRIVATE_TRACE'}]};
 const html=renderToStaticMarkup(React.createElement(LearningAssistantPanel,{close(){},controller:{conversation,buffer:{text:'保留输入',busy:false,send:{content:'保留输入',idempotency_key:'x'}},blocked:true,update(){},read(){},send(){},save(){}}}));
 assert.match(html,/状态正在核对，暂时不能重新发送/);assert.match(html,/<button class="text-button">核对发送结果<\/button>/);assert.doesNotMatch(html,/PRIVATE_TRACE|再次发送|重试/);assert.match(html,/disabled="" aria-label="发送"/);
});

test('assistant header shows saved/proposal/unsaved state and inline read recovery is available',()=>{
 for(const [status,patch] of [['已保存',{has_formal_save:true}],['待确认',{}],['未保存',{messages:[]}]]){
 const conversation={...base(),mode:'summary',title:'目标',context:{},messages:[{...message('p',1,'assistant'),status:'ready_to_draft',proposal:'候选'}],...patch};
 const html=renderToStaticMarkup(React.createElement(LearningAssistantPanel,{close(){},controller:{conversation,buffer:{text:'local',busy:false,error:'暂时无法读取会话，你的输入仍保留。'},blocked:false,update(){},read(){},send(){},save(){}}}));
 assert.match(html,new RegExp(`assistant-header-status[^>]*>• ${status}`));assert.match(html,/<button class="text-button">重新连接<\/button>/);
 }
});
