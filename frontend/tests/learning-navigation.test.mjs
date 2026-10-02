import {test} from 'node:test';
import assert from 'node:assert/strict';
import {toggleStage, stagePage} from '../src/components/learningNavigation.ts';
test('all stages start collapsed and expanding one closes the previous stage',()=>{let expanded=null; expanded=toggleStage(expanded,'a');assert.equal(expanded,'a');expanded=toggleStage(expanded,'b');assert.equal(expanded,'b');assert.equal(toggleStage(expanded,'b'),null);});
test('sidebar selection keeps practice and summary, external entry opens workspace',()=>{assert.equal(stagePage('practice'),'practice');assert.equal(stagePage('summary'),'summary');assert.equal(stagePage('dashboard'),'workspace');assert.equal(stagePage('practice',true),'workspace');});
import { taskSelectionForIntent } from '../src/components/learningNavigation.ts';
test('explicit task intent selects the clicked second task only once', () => {
  const intent={stageId:'s',taskId:'second',sequence:2};
  const tasks=[{task_id:'first'},{task_id:'second'}];
  assert.equal(taskSelectionForIntent('s',tasks,intent,1),'second');
  assert.equal(taskSelectionForIntent('s',tasks,intent,2),undefined,'an applied intent must not overwrite later dropdown choice');
});
test('task navigation refuses another stage or a task absent from the stage', () => {
  assert.equal(taskSelectionForIntent('other',[{task_id:'second'}],{stageId:'s',taskId:'second',sequence:1},0),undefined);
  assert.equal(taskSelectionForIntent('s',[{task_id:'first'}],{stageId:'s',taskId:'missing',sequence:1},0),undefined);
});
import { stageCompletionLabel, stageTotals } from '../src/components/learningNavigation.ts';
test('completion uses only server stage status and safely treats missing data as incomplete', () => {
  assert.equal(stageCompletionLabel({completion:{status:'completed'}}),'已完成');
  assert.equal(stageCompletionLabel({completion:{status:'incomplete',summary_completed:true,completed_practice_tasks:3,total_practice_tasks:3}}),'未完成');
  assert.equal(stageCompletionLabel({units:[{progress:'completed'}],tasks:[{status:'accepted'}]}),'未完成');
  assert.equal(stageCompletionLabel(undefined),'未完成');
});
test('stage totals never substitute the old unit completion counters', () => {
  assert.deepEqual(stageTotals({completed_stages:2,total_stages:4}),{completed:2,total:4});
  assert.deepEqual(stageTotals({completed_units:99,total_units:100}),{completed:0,total:0});
  assert.deepEqual(stageTotals({stages:[{},{}],completed_units:99}),{completed:0,total:2});
  assert.deepEqual(stageTotals({stages:[{},{}],total_stages:0}),{completed:0,total:0});
});
