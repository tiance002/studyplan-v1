import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';
import {build} from 'esbuild';
const root=path.resolve(new URL('..',import.meta.url).pathname.replace(/^\/([A-Za-z]:)/,'$1'));
const output=path.join(root,'var','planning-render-test.cjs');
fs.mkdirSync(path.dirname(output),{recursive:true});
await build({stdin:{contents:`import React from 'react';import {renderToStaticMarkup} from 'react-dom/server';import {Curriculum} from './src/features/planning/Curriculum';export function render(plan){return renderToStaticMarkup(React.createElement(Curriculum,{plan}));}`,resolveDir:root,loader:'tsx'},bundle:true,platform:'node',format:'cjs',outfile:output});
const {render}=createRequire(import.meta.url)(output);
const draft=JSON.parse(fs.readFileSync(new URL('./planning-public-draft.fixture.json',import.meta.url),'utf8'));
test('actual HTTP public teaching projection renders knowledge, materials and embedded guidance',()=>{const html=render(draft);assert.ok(html.includes(draft.v2_content.knowledge[0].title));assert.ok(html.includes(draft.v2_content.materials[0].reading_focus));assert.ok(html.includes(draft.v2_content.stages[0].guidance.practice_delta.increment[0]));assert.ok(html.includes('chapter.md#L1-L1'));assert.ok(html.includes('独立小练习'));assert.ok(html.includes('最终成果'));assert.ok(html.includes(draft.v2_content.capabilities.capabilities[0].learning_outcomes[0].text));assert.ok(html.includes('已有能力说明'));assert.ok(html.includes('所选材料的免费访问条件已核对'));assert.ok(html.includes('合成验收资料'));assert.ok(html.includes('Synthetic fixture'));assert.ok(!html.includes(draft.v2_content.materials[0].source_snapshot.title));assert.ok(!html.includes('policy:'));});
// Synthetic display fixture only: these added branches have no real review qualification.
// It reuses the actual public DTO shape and does not invoke Compiler, PG, Worker or Provider.
test('synthetic display branches preserve Supplement Reference and whole-core slice study facts',()=>{
 const display=structuredClone(draft),stage=display.v2_content.stages[0];
 for(const [index,role] of ['supplement','reference'].entries()){
  const material=structuredClone(display.v2_content.materials[0]);
  material.material_id=`synthetic_display_${role}`;material.role=role;material.order_index=index+1;
  material.reading_focus=`合成${role}阅读重点`;
  material.source_snapshot={...material.source_snapshot,material_id:material.material_id,title:`合成${role}资料`,source_version:`synthetic-${role}-v1`,section_refs:[`${role}.md#L2-L4`],limitations:[`合成${role}展示资料，无真实审核资格`],free_access:'unknown',qualification:'synthetic_display_fixture',usable:false,url:'https://example.invalid/display-only'};
  display.v2_content.materials.push(material);
 }
 for(const mode of ['whole_core','slices']){
  const requirement={requirement_id:`synthetic_study_${mode}`,problem:`合成${mode}源码问题`,mode,outcome_refs:stage.outcome_refs,avoid_scope:[`${mode}避读范围`],expected_outputs:[`${mode}学习产物`],normal_behavior:[`${mode}正常行为`],failure_behavior:[`${mode}失败行为`],inputs_outputs:[{input:`${mode}正常输入`,output:`${mode}正常输出`}],design_questions:[`${mode}设计取舍`],selected_case_ref:`synthetic_case_${mode}`};
  const source={case_id:requirement.selected_case_ref,repo_url:'https://example.invalid/synthetic-project',version:`synthetic-${mode}-v1`,mode,outcome_refs:stage.outcome_refs,evidence_refs:[],qualification:'synthetic_display_fixture',limitations:[`${mode}合成展示，无真实审核资格`]};
  stage.project_study_refs.push(requirement.requirement_id);display.v2_content.project_study.push({requirement,case:source});
 }
 const html=render(display),checks=[];
 const contains=(name,expected)=>{assert.ok(html.includes(expected),name);checks.push({name,status:'PASS'});};
 contains('supplement role','补充材料 · Supplement');contains('reference role','查阅资料 · Reference');
 for(const role of ['supplement','reference'])for(const suffix of ['阅读重点','展示资料，无真实审核资格'])contains(`${role} ${suffix}`,`合成${role}${suffix}`);
 for(const role of ['supplement','reference'])contains(`${role} sections`,`${role}.md#L2-L4`);
 contains('whole core mode','学习工程核心整体');contains('slice mode','学习相关工程切片');
 for(const mode of ['whole_core','slices'])for(const suffix of ['正常行为','失败行为','正常输入','正常输出','设计取舍','学习产物','避读范围'])contains(`${mode} ${suffix}`,`${mode}${suffix}`);
 for(const mode of ['whole_core','slices']){contains(`${mode} case version`,`synthetic-${mode}-v1`);contains(`${mode} case limitations`,`${mode}合成展示，无真实审核资格`);}
 contains('own project stays separate','继续使用你的项目');contains('case distinction','这是对别人项目的源码学习，与你自己的持续实践分别记录。');
 contains('carrier practice remains','项目阶段实践');
 assert.ok(!html.includes('synthetic_study_whole_core'),'internal requirement identity is not a user title');
 const directory=path.resolve(root,'..','var','planning-v2-item9-clarification-20261009');fs.mkdirSync(directory,{recursive:true});
 fs.writeFileSync(path.join(directory,'frontend-synthetic-display-branches.json'),JSON.stringify({status:'PASS',evidence_kind:'synthetic SSR display fixture only',qualification:'NOT real teaching review evidence',calls:{PG:0,Worker:0,Provider:0,browser:0},material_version_note:'material versions stay frozen in source_snapshot and are displayed by the existing native material dialog; this SSR case asserts material roles/reading/sections/limitations and case versions',checks,fixture:display},null,2)+'\n');
});
