import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import ts from 'typescript';
const compile = path => ts.transpileModule(readFileSync(new URL(path,import.meta.url),'utf8'),{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}}).outputText;
const url = source => `data:text/javascript;base64,${Buffer.from(source).toString('base64')}`;
const react=url(`export const useState=(...args)=>globalThis.restoreHooks.useState(...args);export const useRef=(...args)=>globalThis.restoreHooks.useRef(...args);export const useEffect=(...args)=>globalThis.restoreHooks.useEffect(...args);`);
const api=url('export const assistantApi={list:(...args)=>globalThis.restoreApi.list(...args),read:(...args)=>globalThis.restoreApi.read(...args),save:(...args)=>globalThis.restoreApi.save(...args),create:(...args)=>globalThis.restoreApi.create(...args),send:(...args)=>globalThis.restoreApi.send(...args)};');
const client=url('export class ApiError extends Error{constructor(status,message){super(message);this.status=status;}};');
const {ApiError}=await import(client);
const state=url(compile('./assistantState.ts'));
const source=compile('./useAssistant.ts').replace("'react'",JSON.stringify(react)).replace("'../../api/client'",JSON.stringify(client)).replace("'../../api/assistantClient'",JSON.stringify(api)).replace("'./assistantState'",JSON.stringify(state));
const {useAssistant}=await import(url(source));
function harness() {
  const slots=[],effects=[];let index=0;
  globalThis.window={addEventListener(){},removeEventListener(){}};
  globalThis.restoreHooks={
    useState(initial){const i=index++;if(!slots[i])slots[i]={value:typeof initial==='function'?initial():initial};return [slots[i].value,value=>{slots[i].value=typeof value==='function'?value(slots[i].value):value;}];},
    useRef(value){const i=index++;if(!slots[i])slots[i]={current:value};return slots[i];},
    useEffect(effect,deps){const i=index++,old=slots[i];if(!old||deps.some((value,j)=>value!==old.deps[j])){slots[i]={deps,cleanup:old?.cleanup};effects.push(()=>{slots[i].cleanup?.();slots[i].cleanup=effect();});}},
  };
  return {render(project='project',actor='owner'){index=0;return useAssistant(project,actor,async()=>{},'plan');},effects(){while(effects.length)effects.shift()();}};
}
function deferred(){let resolve,reject;const promise=new Promise((yes,no)=>{resolve=yes;reject=no;});return {promise,resolve,reject};}
test('initial restored account waits for scope initialization then reads once and tracks loading',async()=>{
  const h=harness(),pending=deferred(),calls=[];globalThis.restoreApi={list:project=>{calls.push(project);return pending.promise;}};
  let a=h.render();assert.equal(a.listReady,false);await a.list();assert.equal(calls.length,0);
  h.effects();a=h.render();assert.equal(a.listReady,true);const request=a.list();void a.list();a=h.render();assert.equal(a.listLoading,true);assert.equal(a.listLoaded,false);assert.equal(calls.length,1);
  pending.resolve({items:[{conversation_id:'one'},{conversation_id:'two'}],next_cursor:null});await request;a=h.render();assert.equal(a.listLoading,false);assert.equal(a.listLoaded,true);assert.equal(a.items.length,2);
});
test('account change discards late old list and initializes a new single GET',async()=>{
  const h=harness(),old=deferred(),calls=[];globalThis.restoreApi={list:project=>{calls.push(project);return calls.length===1?old.promise:Promise.resolve({items:[{conversation_id:'new'}],next_cursor:null});}};
  h.render();h.effects();let a=h.render();const request=a.list();a=h.render('other','different');assert.equal(a.listReady,false);h.effects();a=h.render('other','different');assert.deepEqual(a.items,[]);await a.list();old.resolve({items:[{conversation_id:'private-old'}],next_cursor:null});await request;a=h.render('other','different');assert.deepEqual(a.items.map(c=>c.conversation_id),['new']);assert.deepEqual(calls,['project','other']);
});
test('failed first read is not an empty success and clear removes readiness/private cache',async()=>{
  const h=harness();let calls=0;globalThis.restoreApi={list:async()=>{calls++;throw new Error('offline');}};h.render();h.effects();let a=h.render();await a.list();a=h.render();assert.equal(a.listLoaded,false);assert.equal(a.listLoading,false);assert.equal(a.listError,'暂时无法加载会话，请重新加载。');h.effects();a=h.render();assert.equal(calls,1);a.clear();a=h.render();assert.equal(a.listReady,false);assert.equal(a.listLoaded,false);assert.deepEqual(a.items,[]);
});
test('formal CAS conflict preserves exact edited text and only explicit GET unlocks save',async()=>{
  const h=harness();const c={conversation_id:'c',plan_id:'plan',messages:[],formal_saves:[],formal_version:2,current_draft_message_id:null,read_only:false};globalThis.restoreApi={read:async()=>c,save:async()=>{throw new ApiError(409,'version conflict');}};
  h.render();h.effects();let a=h.render();await a.resume('c');a=h.render();a.update({formal:'  local\n',formalDirty:true});a=h.render();await a.save({content:'  local\n',draft_message_id:'draft',expected_version:1,idempotency_key:'save'});a=h.render();assert.equal(a.buffer.saveConflict,true);assert.equal(a.buffer.formal,'  local\n');await a.read('c',false);a=h.render();assert.equal(a.buffer.saveConflict,true);assert.equal(a.buffer.formal,'  local\n');await a.read('c');a=h.render();assert.equal(a.buffer.saveConflict,false);assert.equal(a.buffer.formal,'  local\n');assert.equal(a.conversation.formal_version,2);
});
test('normal start delegates recent restore while explicit new start sends force_new',async()=>{
 const h=harness(),bodies=[];const c={conversation_id:'c',plan_id:'plan',messages:[],formal_saves:[],formal_version:0,current_draft_message_id:null,read_only:false};globalThis.restoreApi={create:async(project,body)=>{bodies.push(body);return c;}};h.render();h.effects();let a=h.render();const target={plan_id:'plan',stage_id:'stage',mode:'summary',task_id:null};await a.start(target);a=h.render();assert.equal(a.conversation.conversation_id,'c');assert.equal(bodies[0].force_new,false);await a.start({...target,force_new:true});assert.equal(bodies[1].force_new,true);
});
test('unconfirmed create blocks fresh operation keys and uses the original key for explicit recovery',async()=>{
 const h=harness(),bodies=[];const c={conversation_id:'c',plan_id:'plan',messages:[],formal_saves:[],formal_version:0,current_draft_message_id:null,read_only:false};globalThis.restoreApi={create:async(project,body)=>{bodies.push(body);if(bodies.length===1)throw new Error('response lost');return c;}};h.render();h.effects();let a=h.render();const target={plan_id:'plan',stage_id:'stage',mode:'summary',task_id:null};await a.start(target);a=h.render();await a.start({...target,force_new:true});assert.equal(bodies.length,1);await a.start(a.startPending);assert.equal(bodies.length,2);assert.deepEqual(bodies[0],bodies[1]);a=h.render();assert.equal(a.startPending,null);
});


test('one list page hydrates details with at most four GETs and no mutation',async()=>{
 const h=harness(),pending=[],reads=[];globalThis.restoreApi={list:async()=>({items:Array.from({length:9},(_,i)=>({conversation_id:`c${i}`})),next_cursor:'next'}),read:(project,id)=>{reads.push([project,id]);const d=deferred();pending.push(d);return d.promise;},send(){assert.fail('list must not send');},create(){assert.fail('list must not create');}};
 h.render();h.effects();let a=h.render();const request=a.list();await Promise.resolve();assert.equal(reads.length,4);
 const detail=id=>({conversation_id:id,plan_id:'plan',messages:[],formal_saves:[],formal_version:0});
 pending[0].resolve(detail('c0'));await Promise.resolve();await Promise.resolve();assert.equal(reads.length,5);
 for(let i=1;i<9;i++){while(!pending[i])await Promise.resolve();pending[i].resolve(detail(`c${i}`));}
 await request;a=h.render();assert.equal(Object.keys(a.listDetails).length,9);assert.equal(a.listLoading,false);assert.equal(a.cursor,'next');assert.equal(reads.length,9);
});
test('failed detail remains unloaded while other summaries/details are usable',async()=>{
 const h=harness();globalThis.restoreApi={list:async()=>({items:[{conversation_id:'loaded'},{conversation_id:'failed'}],next_cursor:null}),read:async(project,id)=>{if(id==='failed')throw Error('PRIVATE_PROVIDER_TRACE');return {conversation_id:id,plan_id:'plan',messages:[],formal_saves:[],formal_version:0};}};
 h.render();h.effects();let a=h.render();await a.list();a=h.render();assert.equal(a.items.length,2);assert.ok(a.listDetails.loaded);assert.equal(a.listDetails.failed,undefined);assert.equal(a.listError,'');assert.equal(a.listLoaded,true);
});
test('account switch during detail hydration discards private result and stops remaining GETs',async()=>{
 const h=harness(),pending=deferred(),reads=[];globalThis.restoreApi={list:async()=>({items:Array.from({length:8},(_,i)=>({conversation_id:`private${i}`})),next_cursor:null}),read:(project,id)=>{reads.push(id);return pending.promise;}};
 h.render();h.effects();let a=h.render();const request=a.list();await Promise.resolve();assert.equal(reads.length,4);
 h.render('new-project','new-owner');h.effects();pending.resolve({conversation_id:'private0',plan_id:'plan',messages:[],formal_saves:[],formal_version:0});await request;a=h.render('new-project','new-owner');assert.deepEqual(a.listDetails,{});assert.deepEqual(a.items,[]);assert.equal(reads.length,4);
});

test('created conversation appears immediately in empty library with its selected cached detail',async()=>{
 const h=harness();const c={conversation_id:'created',plan_id:'plan',mode:'summary',title:'新会话',context:{},messages:[],formal_saves:[],formal_version:0,current_draft_message_id:null,read_only:false};globalThis.restoreApi={create:async()=>c,list:async()=>({items:[],next_cursor:null})};h.render();h.effects();let a=h.render();await a.list();a=h.render();assert.deepEqual(a.items,[]);await a.start({plan_id:'plan',stage_id:'stage',mode:'summary',task_id:null,force_new:true});a=h.render();assert.equal(a.items[0].conversation_id,'created');assert.equal(a.conversation.conversation_id,'created');assert.ok(a.listDetails.created);assert.equal(a.open,true);
});
test('new conversation pin is bounded, preserves list cursor, and deduplicates later list results',async()=>{
 const h=harness();let number=0,listCount=0;const c=id=>({conversation_id:id,plan_id:'plan',mode:'practice',title:id,context:{},messages:[],formal_saves:[],formal_version:0,current_draft_message_id:null,read_only:false});globalThis.restoreApi={create:async()=>c(`new${++number}`),list:async()=>({items:listCount++===0?Array.from({length:20},(_,i)=>c(`old${i}`)):[c('new2'),c('later')],next_cursor:'original-cursor'}),read:async(project,id)=>c(id)};
 h.render();h.effects();let a=h.render();await a.list();a=h.render();const target={plan_id:'plan',stage_id:'stage',mode:'practice',task_id:'task',force_new:true};await a.start(target);a=h.render();assert.equal(a.items.length,21);assert.equal(a.items[0].conversation_id,'new1');await a.start(target);a=h.render();assert.equal(a.items.length,21);assert.equal(a.items[0].conversation_id,'new2');assert.equal(a.cursor,'original-cursor');assert.ok(a.items.some(i=>i.conversation_id==='old19'));await a.list(true);a=h.render();assert.equal(a.items.filter(i=>i.conversation_id==='new2').length,1);assert.equal(a.cursor,'original-cursor');
});
