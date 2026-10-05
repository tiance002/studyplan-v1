import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import ts from 'typescript';
const path=new URL('./assistantProposalScroll.ts',import.meta.url);
const code=ts.transpileModule(readFileSync(path,'utf8'),{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}}).outputText;
const {restoreProposalAnchor}=await import(`data:text/javascript;base64,${Buffer.from(code).toString('base64')}`);
for(const [before,after] of [[590,906],[590,410]])test(`proposal ${after>before?'expand':'collapse'} preserves bottom without smooth-scroll delay`,()=>{
 const scroll={scrollTop:100,style:{scrollBehavior:'smooth'}};
 Object.defineProperty(scroll,'scrollTop',{get(){return this.top??100;},set(value){assert.equal(this.style.scrollBehavior,'auto');this.top=value;},configurable:true});
 const card={isConnected:true,getBoundingClientRect:()=>({bottom:after})};restoreProposalAnchor(scroll,card,before);assert.equal(scroll.scrollTop,100+after-before);assert.equal(scroll.style.scrollBehavior,'smooth');
});
test('detached proposal cannot change the newly selected conversation scroll',()=>{const scroll={scrollTop:100,style:{scrollBehavior:'smooth'}};restoreProposalAnchor(scroll,{isConnected:false,getBoundingClientRect:()=>({bottom:900})},400);assert.equal(scroll.scrollTop,100);});
test('composer reserve remains actual measured height plus 24px',()=>{const css=readFileSync(new URL('../style.css',import.meta.url),'utf8'),panel=readFileSync(new URL('./LearningAssistantPanel.tsx',import.meta.url),'utf8');assert.match(css,/padding-bottom:calc\(var\(--composer-height,124px\) \+ 24px\)/);assert.match(panel,/composer\.getBoundingClientRect\(\)\.height/);assert.match(panel,/new ResizeObserver\(measure\)/);});
test('collapse resets only that candidate body to its first six lines and keeps bottom anchor',()=>{
 const scroll={scrollTop:300,style:{scrollBehavior:'smooth'}},body={scrollTop:450},other={scrollTop:600};
 restoreProposalAnchor(scroll,{isConnected:true,getBoundingClientRect:()=>({bottom:450})},600,body);
 assert.equal(body.scrollTop,0);assert.equal(other.scrollTop,600);assert.equal(scroll.scrollTop,150);
});
test('expanding does not reset an unrelated candidate body',()=>{const scroll={scrollTop:100,style:{scrollBehavior:'smooth'}},body={scrollTop:450};restoreProposalAnchor(scroll,{isConnected:true,getBoundingClientRect:()=>({bottom:800})},600);assert.equal(body.scrollTop,450);assert.equal(scroll.scrollTop,300);});
