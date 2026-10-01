// Chrome + owned HTTP/PG + exactly one configured real model dispatch.
const {chromium}=require('playwright-core');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..'),acceptance='v2-g3-20261001-01';
if(process.env.V2_CONFIRM_SUMMARY_PAID_RUN!==acceptance)throw new Error('Explicit new owned summary acceptance required');
const dir=path.join(root,'var/v2-g3'),report=path.join(dir,'summary-real.json');
assert.ok(!fs.existsSync(report),'Completed acceptance must not be replayed');
const credentials=JSON.parse(fs.readFileSync(path.join(root,'var/v2-g1/v2-g1-20261001-01-browser-private.json'),'utf8'));
const context=JSON.parse(fs.readFileSync(path.join(dir,'summary-real-context.json'),'utf8'));
const quota=folder=>fs.readdirSync(path.join(root,'.git',folder)).filter(n=>/^request-\d+\.json$/.test(n)).length;
const readFile=name=>fs.existsSync(path.join(dir,name))?JSON.parse(fs.readFileSync(path.join(dir,name),'utf8')):null;
const write=(name,value)=>fs.writeFileSync(path.join(dir,name),JSON.stringify(value,null,2),{flag:'wx'});
(async()=>{const browser=await chromium.launch({channel:'chrome',headless:true});try{
 const page=await browser.newPage({viewport:{width:1450,height:1100}}),errors=[],forbidden=[];
 page.on('pageerror',()=>errors.push('pageerror'));page.on('dialog',dialog=>dialog.accept());
 await page.route('**/api/v1/**',route=>{
  const req=route.request(),url=new URL(req.url());
  if(req.method()==='POST'&&['/api/v1/plans/generate','/api/v1/resources/searches','/api/v1/resource-changes'].includes(url.pathname)){
   forbidden.push(url.pathname);return route.abort();}
  if(req.method()==='POST'&&url.pathname.endsWith('/review')&&url.pathname.startsWith('/api/v1/summaries/')){
   const intent=path.join(dir,'summary-real-review-intent.json');
   if(fs.existsSync(intent))return route.abort();
   write('summary-real-review-intent.json',{acceptance_id:acceptance,attempt_id:url.pathname.split('/attempts/')[1].split('/')[0],body:req.postDataJSON()});
  }
  return route.continue();
 });
 await page.goto((process.env.STUDYPLAN_URL||'http://127.0.0.1:5175')+'/#summary');
 await page.getByLabel('用户名',{exact:true}).fill(credentials.username);
 await page.getByLabel('密码',{exact:true}).fill(credentials.password);
 await page.getByRole('button',{name:'登录学习空间',exact:true}).click();
 const editor=page.getByRole('textbox',{name:'总结原文',exact:true});await editor.waitFor();
 const read=async url=>page.evaluate(async u=>{const r=await fetch(u,{credentials:'include'});if(!r.ok)throw new Error('Owned GET failed');return r.json();},url);
 const scope='?project_id='+encodeURIComponent(context.project_id);
 const workspace=await read('/api/v1/workspace'+scope);assert.equal(workspace.plan.revision,2);
 const stage=workspace.stages[0],unit=stage.units[0];
 await page.getByLabel('总结所属阶段').selectOption(stage.stage.stage_id);
 await page.getByLabel('总结所属学习单元').selectOption(unit.unit_id);
 const threadUrl='/api/v1/summaries'+scope+'&'+new URLSearchParams({plan_id:workspace.plan.plan_id,stage_id:stage.stage.stage_id,unit_id:unit.unit_id});
 const exposuresBefore=await read('/api/v1/exposures'+scope+'&plan_id='+encodeURIComponent(workspace.plan.plan_id));
 let saved=readFile('summary-real-saved.json');
 if(!saved){
  assert.equal(quota('v2-paid-quota-20261001'),20);
  await page.getByRole('button',{name:'保存总结',exact:true}).waitFor();
  const raw='  本次我学习了'+unit.title+'。我先明确输入、输出和工具边界，再用简单例子解释流程。\n我还需要核对失败时如何保留记录，以及怎样用实际结果证明理解；目前这些是我的学习体会，不是已执行实验的证据。\n\t';
  await editor.fill(raw);
  const responsePromise=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/v1/summaries'&&r.request().method()==='POST');
  await page.getByRole('button',{name:'保存总结',exact:true}).click();const response=await responsePromise;assert.equal(response.status(),200);
  saved=(await response.json()).attempt;assert.equal(saved.content,raw);write('summary-real-saved.json',saved);
 }
 const attemptUrl='/api/v1/summaries/attempts/'+encodeURIComponent(saved.attempt_id)+scope;
 let retained=await read(attemptUrl),receipt=readFile('summary-real-review-receipt.json');
 if(!receipt){
  if(retained.run_id){const run=await read('/api/v1/runs/'+encodeURIComponent(retained.run_id)+scope);receipt={run_id:run.run_id,attempt_id:saved.attempt_id,status_url:'/api/v1/runs/'+encodeURIComponent(run.run_id)+scope};write('summary-real-review-receipt.json',receipt);}
  else{
   assert.ok(!readFile('summary-real-review-intent.json'),'Unknown submission is retained; inspect, never repeat POST');
   await page.getByLabel('查看保存版本').selectOption(saved.attempt_id);
   await page.getByRole('checkbox').first().check();
   const responsePromise=page.waitForResponse(r=>new URL(r.url()).pathname.endsWith('/'+saved.attempt_id+'/review'));
   await page.getByRole('button',{name:'请求这次原文的反馈',exact:true}).click();const response=await responsePromise;assert.equal(response.status(),202);
   receipt=await response.json();write('summary-real-review-receipt.json',receipt);
  }
 }
 let newer=readFile('summary-real-second-saved.json');
 if(!newer){
  const newerText='这是反馈排队期间新保存的第二次总结。\n我补充了下一步核对失败边界的计划，尚未实施，不把它写成已验证结果。\n ';
  await editor.fill(newerText);
  const responsePromise=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/v1/summaries'&&r.request().method()==='POST');
  await page.getByRole('button',{name:'保存总结',exact:true}).click();const response=await responsePromise;assert.equal(response.status(),200);
  newer=(await response.json()).attempt;assert.equal(newer.content,newerText);write('summary-real-second-saved.json',newer);
 }
 const localText='反馈返回前仍在编辑的本地文字，保持未保存。';await editor.fill(localText);
 await page.getByLabel('查看保存版本').selectOption(saved.attempt_id);
 if(!readFile('summary-real-editor-gate.json'))write('summary-real-editor-gate.json',{acceptance_id:acceptance,run_id:receipt.run_id,newer_attempt_id:newer.attempt_id});
 await page.locator('[aria-label="已保存反馈"]').waitFor({timeout:180000});
 assert.equal(await editor.inputValue(),localText);
 const run=await read(receipt.status_url);assert.equal(run.status,'succeeded');
 retained=await read(attemptUrl);assert.equal(retained.content,saved.content);assert.equal(retained.review.run_id,receipt.run_id);
 const latest=await read(threadUrl);assert.equal(latest.attempts.at(-1).attempt_id,newer.attempt_id);assert.equal(latest.attempts.at(-1).review,null);
 assert.deepEqual(await read('/api/v1/exposures'+scope+'&plan_id='+encodeURIComponent(workspace.plan.plan_id)),exposuresBefore);
 await page.reload();await editor.waitFor();await page.getByRole('heading',{name:'第 '+newer.attempt_no+' 次保存的原文',exact:true}).waitFor();
 assert.equal(await editor.inputValue(),newer.content);
 await page.getByLabel('查看保存版本').selectOption(saved.attempt_id);await page.locator('[aria-label="已保存反馈"]').waitFor();
 await page.getByRole('button',{name:'读取项目总结历史',exact:true}).click();
 assert.ok((await read('/api/v1/summaries/history'+scope)).items.some(a=>a.attempt_id===saved.attempt_id&&a.review?.run_id===receipt.run_id));
 assert.equal(quota('v2-paid-quota-20261001'),21);assert.equal(quota('v2-search-quota-20261001'),2);
 assert.deepEqual(errors,[]);assert.deepEqual(forbidden,[]);
 await page.screenshot({path:path.join(dir,'summary-real.png'),fullPage:true});
 const result={status:'PASS',acceptance_id:acceptance,source:'Chrome + real loopback HTTP + owned PostgreSQL + configured model',
  run_id:receipt.run_id,project_id:context.project_id,original_attempt_id:saved.attempt_id,newer_attempt_id:newer.attempt_id,
  model_requests:21,search_requests:2,original_saved_before_feedback:true,raw_preserved:true,pinned_feedback:true,
  newer_saved_and_local_editor_preserved:true,progress_unchanged:true,reload_saved_history:true};
 write('summary-real.json',result);console.log(JSON.stringify(result));
 }finally{await browser.close();}})().catch(()=>{console.error('FAIL: owned summary observation; preserve known attempts/run/receipts and inspect without repeating dispatch.');process.exitCode=1;});
