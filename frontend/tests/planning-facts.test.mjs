import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import ts from 'typescript';
const source=fs.readFileSync(new URL('../src/features/planning/facts.ts',import.meta.url),'utf8');
const code=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.ESNext}}).outputText;
const adapter=await import(`data:text/javascript;base64,${Buffer.from(code).toString('base64')}`);
test('opaque material identity uses a readable fallback',()=>{assert.equal(adapter.resourceTitle('resource_'+'a'.repeat(64)),'指定学习教材');assert.equal(adapter.resourceTitle('真实教材'),'真实教材');assert.equal(adapter.resourceTitle(undefined),'指定学习教材');});
test('opaque bare hashes are hidden while reviewed repository titles stay readable',()=>{assert.equal(adapter.resourceTitle('A'.repeat(64)),'指定学习教材');assert.equal(adapter.resourceTitle('material_'+'b'.repeat(32)),'指定学习教材');assert.equal(adapter.resourceTitle('owner/repo · docs/chapter.md'),'owner/repo · docs/chapter.md');});
test('opaque material titles use the frozen GitHub source address without changing source hashes',()=>{
 assert.equal(adapter.resourceTitle('resource_'+'a'.repeat(64),'https://github.com/owner/repo/blob/main/docs/chapter.md'),'owner/repo · docs/chapter.md');
 assert.equal(adapter.resourceTitle('真实教材','https://github.com/owner/repo'),'真实教材');
 assert.equal(adapter.resourceTitle('a'.repeat(64),'https://evil.example/owner/repo'),'指定学习教材');
});
test('planning evidence never grants runtime verification',()=>{
 assert.equal(adapter.constraintStatus({status:'satisfied',planning_status:'arranged',runtime_status:'unverified'}),'学习要求已安排；实际运行尚未验证');
 assert.equal(adapter.constraintStatus({planning_status:'pending',runtime_status:'unverified'}),'学习要求仍待安排；实际运行尚未验证');
 assert.equal(adapter.constraintStatus({status:'satisfied'}),'已有符合限制的依据');
 assert.equal(adapter.constraintStatus({runtime_status:'unexpected'}),'学习安排以保存的状态为准；实际运行以保存的验证状态为准');
});
test('unresolved outcomes use frozen readable outcomes without exposing unknown identities',()=>{
 assert.deepEqual(adapter.unresolvedOutcomes({capabilities:{capabilities:[{learning_outcomes:[{outcome_id:'optional.branch',text:'理解可选分支'}]}]},unresolved:[{outcome_ref:'optional.branch',reason:'source_unavailable'},{outcome_ref:'internal_unknown',reason:'仍需补审'}]}),[{title:'理解可选分支',reason:'学习资料尚未齐全'},{title:'待补齐学习目标',reason:'仍需补审'}]);
 assert.deepEqual(adapter.unresolvedOutcomes({}),[]);
});
test('material links accept only HTTP and HTTPS',()=>{assert.equal(adapter.safeUrl('javascript:alert(1)'),undefined);assert.equal(adapter.safeUrl('file:///secrets'),undefined);assert.equal(adapter.safeUrl('https://example.org/chapter'),'https://example.org/chapter');});
test('rubric renders text without internal references',()=>{assert.deepEqual(adapter.lines([{text:'检查正常与失败路径',outcome_refs:['internal']},'固定事实']),['检查正常与失败路径','固定事实']);assert.deepEqual(adapter.lines([{hash:'internal'}]),[]);});
test('absent progress does not invent phase completion',()=>{assert.equal(adapter.progressLabel('unknown'),'正在准备学习计划');assert.equal(adapter.progressLabel('practice'),'正在准备实践与成果要求');});
test('public null GoalSpec restores all frozen supplement facts from the server profile',()=>{
 const draft=JSON.parse(fs.readFileSync(new URL('./planning-public-draft.fixture.json',import.meta.url),'utf8'));
 assert.equal(draft.goal_spec,null);
 const goal=adapter.serverGoal(draft);
 assert.equal(goal.target,draft.goal_snapshot);
 assert.equal(goal.starting_point,'我已经会Python');
 assert.deepEqual(goal.constraints,['教材必须免费']);
 assert.equal(goal.project_context,'已有本地 JSON 待办 CLI，保留现有接口和数据，不重建演示项目');
 assert.deepEqual(goal.scope,[]);
 assert.equal(goal.desired_depth,'applied');
 assert.equal(goal.outcome_purpose,'learn');
 const explicit={...goal,starting_point:'当前显式起点'};
 assert.deepEqual(adapter.serverGoal({...draft,goal_spec:explicit}),{...explicit,starting_point:'当前显式起点\n我已经会Python'});
});
test('target-only frozen claims and constraints survive changing target with explicit empty supplement',()=>{
 const explicit={target:'会Python，免费教材学Agent',starting_point:'',scope:['保留范围'],constraints:[],desired_depth:'deep',outcome_purpose:'portfolio',project_context:'现有项目'};
 const plan={goal_snapshot:explicit.target,goal_spec:explicit,v2_content:{profile:{starting_point:'',scope:['不同范围'],desired_depth:'foundation',outcome_purpose:'learn',project_context:'不同项目',learner_claims:[{text:'会Python',source_refs:['goal.target']},{text:'会Python',source_refs:['goal.target']}],hard_constraints:[{text:'教材免费',source_refs:['goal.target']},{text:'教材免费',source_refs:['goal.target']}]}}};
 const restored=adapter.serverGoal(plan),changed={...restored,target:'改为学习受控工具调用'};
 assert.equal(changed.starting_point,'会Python');assert.deepEqual(changed.constraints,['教材免费']);
 assert.deepEqual(changed.scope,['保留范围']);assert.equal(changed.desired_depth,'deep');assert.equal(changed.outcome_purpose,'portfolio');assert.equal(changed.project_context,'现有项目');
});
