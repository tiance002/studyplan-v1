const { chromium } = require('playwright-core');
const assert = require('node:assert/strict');
const BASE = process.env.STUDYPLAN_URL || 'http://127.0.0.1:5178';
const PROJECT = 'cancel-project';
(async () => {
 const browser = await chromium.launch({channel:'chrome',headless:true});
 try {
  const page = await browser.newPage(); page.setDefaultTimeout(5000);
  let view, posts=[], generations=0, fail=false, holdRead=false, held, conflict=false, reconcile=false, holdCancel=false, heldCancel;
  await page.route('**/api/v1/**', async route => {
   const req=route.request(), url=new URL(req.url()), path=url.pathname;
   const reply=(json,status=200)=>route.fulfill({json,status});
   if(path==='/api/v1/session') return reply({username:'cancel-user',project_ids:[PROJECT],csrf_token:'fake'});
   if(path.endsWith('/cancel')) {
    posts.push(req.postDataJSON());
    assert.equal(req.headers()['x-csrf-token'],'fake');
    if(conflict) return reply({message:'version conflict'},409);
    if(holdCancel) {holdCancel=false;heldCancel=()=>reply({...view,status:'cancelled',next_action:'none',version:view.version+1});return;}
    if(fail) return reply({message:'lost response'},503);
    view={...view,status:reconcile?'reconciliation_required':'cancelled',next_action:reconcile?'reconcile':'none',version:view.version+1};
    return reply(view);
   }
   if(path==='/api/v1/plans/generate') {generations++;view={...view,run_id:'new-run',status:'queued',next_action:'wait',version:1};return reply({run_id:'new-run'},202);}
   if(path.startsWith('/api/v1/runs/')) {
    const snapshot={...view};
    if(holdRead) {holdRead=false;held=()=>reply(snapshot);return;}
    return reply(snapshot);
   }
   return reply({},404);
  });
  await page.route('**/healthz',r=>r.fulfill({json:{llm_provider:'fake'}}));
  const open=async(status='queued',next_action='wait')=>{
   view={run_id:'saved-run',status,next_action,version:3,result_ref:null,error:null,progress:null};
   await page.goto(BASE+'/#planning');
   await page.evaluate(p=>{localStorage.clear();localStorage.setItem(`studyplan-run:${p}`,'saved-run');},PROJECT);
   await page.reload(); await page.getByRole('button',{name:'刷新运行状态',exact:true}).waitFor();
  };
  const cancel=()=>page.getByRole('button',{name:'取消生成',exact:true});
  const generate=()=>page.locator('button.btn.primary').first();
  await open(); await cancel().click(); await page.getByText('运行已取消',{exact:true}).waitFor();
  assert.equal(posts[0].expected_version,3); assert.ok(posts[0].idempotency_key);
  assert.equal(await generate().isDisabled(),false);
  await generate().click(); await page.getByText('等待生成',{exact:true}).waitFor();assert.equal(generations,1);assert.equal(view.run_id,'new-run');
  await open('running');fail=true;await cancel().click();
  await page.getByRole('button',{name:'重试同一次取消',exact:true}).waitFor();
  assert.equal(await generate().isDisabled(),true);const original=posts.at(-1);
  await page.reload();await page.getByRole('button',{name:'重试同一次取消',exact:true}).waitFor();
  assert.equal(posts.length,2,'restoration must not automatically POST');
  fail=false;await page.getByRole('button',{name:'重试同一次取消',exact:true}).click();
  await page.getByText('运行已取消',{exact:true}).waitFor();assert.deepEqual(posts.at(-1),original);
  await open('running');conflict=true;await cancel().click();
  await page.getByText('取消未确认，运行版本或状态可能已变化。请刷新运行状态后再决定。',{exact:true}).waitFor();
  assert.equal(await cancel().count(),0);assert.equal(await page.getByRole('button',{name:'重试同一次取消',exact:true}).count(),0);
  const conflictBody=posts.at(-1);view={...view,version:4};conflict=false;
  await page.getByRole('button',{name:'刷新运行状态',exact:true}).click();await cancel().waitFor();await cancel().click();
  await page.getByText('运行已取消',{exact:true}).waitFor();assert.equal(posts.at(-1).expected_version,4);assert.notEqual(posts.at(-1).idempotency_key,conflictBody.idempotency_key);
  await open('running');reconcile=true;await cancel().click();
  await page.getByText('运行需要核对，请勿重复调用',{exact:true}).waitFor();assert.equal(await generate().isDisabled(),true);assert.equal(await cancel().count(),0);reconcile=false;
  await open('running');fail=true;await cancel().click();await page.getByRole('button',{name:'重试同一次取消',exact:true}).waitFor();
  const verifyPosts=posts.length;view={...view,status:'cancelled',next_action:'none',version:4};fail=false;
  await page.getByRole('button',{name:'刷新运行状态',exact:true}).click();await page.getByText('运行已取消',{exact:true}).waitFor();
  assert.equal(posts.length,verifyPosts);assert.equal(await generate().isDisabled(),false);
  await open('running');holdCancel=true;heldCancel=null;await cancel().click({noWaitAfter:true});
  await page.waitForTimeout(100);assert.ok(heldCancel);await page.getByRole('button',{name:'学习工作台',exact:true}).click();
  await heldCancel();await page.waitForTimeout(100);assert.equal(await page.getByText('生成已取消。再次生成将创建一条新的运行。',{exact:true}).count(),0);
  await open('running');holdRead=true;held=null;
  await page.waitForFunction(()=>true); await page.waitForTimeout(1800);assert.ok(held,'poll request held');
  await cancel().click();await page.getByText('运行已取消',{exact:true}).waitFor();await held();await page.waitForTimeout(100);
  assert.equal(await page.getByText('运行已取消',{exact:true}).count(),1,'stale running poll cannot overwrite cancellation');
  await open('reconciliation_required','reconcile');const before=posts.length;
  assert.equal(await cancel().count(),0);assert.equal(await generate().isDisabled(),true);await page.waitForTimeout(1700);assert.equal(posts.length,before);
  for(const [status,action] of [['waiting_user','review_draft'],['future_status','wait'],['running','future_action']]){await open(status,action);assert.equal(await cancel().count(),0);}
  const scopePage=await browser.newPage();scopePage.setDefaultTimeout(5000);
  let scopeRelease, scopeEntered;
  const scopeStarted=new Promise(resolve=>{scopeEntered=resolve;});
  await scopePage.route('**/api/v1/**',async route=>{
   const path=new URL(route.request().url()).pathname;
   if(path.endsWith('/cancel')){
    scopeEntered();await new Promise(resolve=>{scopeRelease=resolve;});
    return route.fulfill({json:{run_id:'run-a',status:'cancelled',next_action:'none',version:4,result_ref:null,error:null,progress:null}});
   }
   if(path.startsWith('/api/v1/runs/')){
    const a=path.endsWith('/run-a');return route.fulfill({json:{run_id:a?'run-a':'run-b',status:a?'queued':'succeeded',next_action:a?'wait':'none',version:3,result_ref:null,error:null,progress:null}});
   }
   return route.fulfill({status:404,json:{}});
  });
  await scopePage.addInitScript(()=>{
   localStorage.setItem('studyplan-run:project-a','run-a');localStorage.setItem('studyplan-run:project-b','run-b');
  });
  await scopePage.goto(BASE+'/tests/run-detail-scope.html');await scopePage.getByRole('button',{name:'取消生成',exact:true}).click();await scopeStarted;
  const scopeStorageBefore=await scopePage.evaluate(()=>Object.fromEntries(Object.keys(localStorage).map(key=>[key,localStorage.getItem(key)])));
  await scopePage.getByRole('button',{name:'切换测试作用域',exact:true}).click();await scopePage.getByText('生成已完成',{exact:true}).waitFor();
  scopeRelease();await scopePage.waitForTimeout(100);
  assert.equal(await scopePage.getByText('生成已完成',{exact:true}).count(),1,'A cancellation ack cannot replace B run');
  assert.equal(await scopePage.getByRole('button',{name:'生成学习草案 →',exact:true}).isDisabled(),false,'A action cannot leave B busy');
  assert.equal(await scopePage.getByRole('alert').count(),0);assert.equal(await scopePage.getByText('运行已取消',{exact:true}).count(),0);
  const scopeStorageAfter=await scopePage.evaluate(()=>Object.fromEntries(Object.keys(localStorage).map(key=>[key,localStorage.getItem(key)])));
  assert.deepEqual(scopeStorageAfter,scopeStorageBefore,'late A ack cannot change B or erase A persisted request');
  await scopePage.close();
  console.log('PASS: queued cancellation, distinct generation, persisted 503 same-request retry/status verification, CAS409 fresh-version request, reconcile acknowledgement, unmount and same-mounted actor/project late acknowledgement, stale poll fence, reconciliation and unknown locks');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
