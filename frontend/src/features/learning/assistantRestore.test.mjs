import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import ts from 'typescript';
const compile = path => ts.transpileModule(readFileSync(new URL(path,import.meta.url),'utf8'),{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}}).outputText;
const url = source => `data:text/javascript;base64,${Buffer.from(source).toString('base64')}`;
const react=url(`export const useState=(...args)=>globalThis.restoreHooks.useState(...args);export const useRef=(...args)=>globalThis.restoreHooks.useRef(...args);export const useEffect=(...args)=>globalThis.restoreHooks.useEffect(...args);`);
const api=url('export const assistantApi={list:(...args)=>globalThis.restoreApi.list(...args),read:(...args)=>globalThis.restoreApi.read(...args),save:(...args)=>globalThis.restoreApi.save(...args)};');
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
  const h=harness();let calls=0;globalThis.restoreApi={list:async()=>{calls++;throw new Error('offline');}};h.render();h.effects();let a=h.render();await a.list();a=h.render();assert.equal(a.listLoaded,false);assert.equal(a.listLoading,false);assert.equal(a.listError,'offline');h.effects();a=h.render();assert.equal(calls,1);a.clear();a=h.render();assert.equal(a.listReady,false);assert.equal(a.listLoaded,false);assert.deepEqual(a.items,[]);
});
test('formal CAS conflict preserves exact edited text and only explicit GET unlocks save',async()=>{
  const h=harness();const c={conversation_id:'c',plan_id:'plan',messages:[],formal_saves:[],formal_version:2,current_draft_message_id:null,read_only:false};globalThis.restoreApi={read:async()=>c,save:async()=>{throw new ApiError(409,'version conflict');}};
  h.render();h.effects();let a=h.render();await a.resume('c');a=h.render();a.update({formal:'  local\n',formalDirty:true});a=h.render();await a.save({content:'  local\n',draft_message_id:'draft',expected_version:1,idempotency_key:'save'});a=h.render();assert.equal(a.buffer.saveConflict,true);assert.equal(a.buffer.formal,'  local\n');await a.read('c',false);a=h.render();assert.equal(a.buffer.saveConflict,true);assert.equal(a.buffer.formal,'  local\n');await a.read('c');a=h.render();assert.equal(a.buffer.saveConflict,false);assert.equal(a.buffer.formal,'  local\n');assert.equal(a.conversation.formal_version,2);
});
