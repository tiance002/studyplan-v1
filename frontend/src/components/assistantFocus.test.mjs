import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import ts from 'typescript';
const code=ts.transpileModule(readFileSync(new URL('./assistantFocus.ts',import.meta.url),'utf8'),{compilerOptions:{module:ts.ModuleKind.ESNext}}).outputText;
const {restoreAssistantFocus}=await import(`data:text/javascript;base64,${Buffer.from(code).toString('base64')}`);
const element=(label,attrs={})=>({tagName:'BUTTON',isConnected:true,hasAttribute:key=>key in attrs,getAttribute:key=>attrs[key]??null,focus(){focused.push(label);}});
let focused=[];
test('valid external launcher receives focus after closing assistant',()=>{focused=[];restoreAssistantFocus(element('launcher'),{contains:()=>false},element('entry'));assert.deepEqual(focused,['launcher']);});
test('async launch body, disabled, disconnected and internal focus return to stable entry',()=>{
 const variants=[null,{...element('body'),tagName:'BODY'},element('disabled',{disabled:''}),element('aria-disabled',{'aria-disabled':'true'}),{...element('removed'),isConnected:false},element('inside')];
 for(const previous of variants){focused=[];restoreAssistantFocus(previous,{contains:e=>e===variants.at(-1)},element('entry'));assert.deepEqual(focused,['entry']);}
});
test('missing or disabled fallback is not focused',()=>{focused=[];restoreAssistantFocus(null,null,null);restoreAssistantFocus(null,null,element('disabled',{disabled:''}));assert.deepEqual(focused,[]);});
