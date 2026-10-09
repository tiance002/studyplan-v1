// Intercepted HTTP boundary; owned PG/Worker acceptance is separate.
const {chromium}=require('playwright-core'),assert=require('node:assert/strict');
const BASE=process.env.STUDYPLAN_URL||'http://127.0.0.1:5178';
(async()=>{
 assert.ok(['localhost','127.0.0.1'].includes(new URL(BASE).hostname));const browser=await chromium.launch({channel:'msedge',headless:true});
 try {for(const scenario of ['none','failed','reconciliation_required','cancelled','network_unknown','server_unknown','unreadable_success','conflict']){
  const unknown=scenario.endsWith('unknown')||scenario==='unreadable_success',canGenerate=unknown||scenario==='conflict';
  const context=await browser.newContext(),page=await context.newPage(),mutations=[],errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await context.route('**/*',route=>{
   const request=route.request(),url=new URL(request.url());if(!['localhost','127.0.0.1'].includes(url.hostname))return route.abort();
   if(url.pathname==='/api/v1/session')return route.fulfill({json:{username:'boundary-owner',project_ids:['boundary-project'],csrf_token:'fixture-csrf'}});
   if(url.pathname==='/healthz')return route.fulfill({json:{llm_provider:'unavailable'}});
   if(url.pathname==='/api/v1/workspace'||url.pathname==='/api/v1/plans/current')return route.fulfill({status:404,json:{}});
   if(url.pathname==='/api/v1/plans/v2/availability')return route.fulfill({json:{initial_generation:canGenerate,clarification:false,semantic_replanning:false,local_change:false,message:canGenerate?'受控学习规划可用':'学习计划生成正在升级，当前暂不可创建新路线。'}});
   const retained={run_id:'retained',status:scenario,next_action:'none',version:1,error:{code:scenario,message:'需要核对当前状态'}};
   if(url.pathname==='/api/v1/runs')return route.fulfill({json:scenario==='none'||canGenerate?[]:[retained]});
   if(url.pathname==='/api/v1/runs/retained')return route.fulfill({json:retained});
   if(url.pathname==='/api/v1/plans/v2/owned/generate'&&request.method()==='POST'){
    mutations.push({path:url.pathname,body:request.postDataJSON()});
    if(scenario==='conflict')return route.fulfill({status:409,json:{code:'conflict',message:'服务端版本已变化'}});
    if(scenario==='network_unknown')return route.abort();
    if(scenario==='server_unknown')return route.fulfill({status:500,json:{message:'需要核对提交结果'}});
    return route.fulfill({status:202,body:'not-json',contentType:'application/json'});
   }
   if(url.pathname.startsWith('/api/v1/')){if(request.method()!=='GET')mutations.push({path:url.pathname});return route.abort();}return route.continue();
  });
  await page.goto(BASE+'/#planning');await page.getByRole('heading',{name:'学习计划',exact:true}).waitFor();
  const generate=page.getByRole('button',{name:'生成学习计划',exact:true});
  if(canGenerate){
   await page.getByLabel('学习目标',{exact:true}).fill('学习目标');await generate.click();
   if(scenario==='conflict'){
    await page.getByRole('alert').filter({hasText:'计划或问题已变化，请手动刷新后核对当前状态。'}).waitFor();
    assert.equal(await page.evaluate(()=>sessionStorage.getItem('studyplan-v2:["boundary-owner","boundary-project"]:mutation')),null);
   }else{
    await page.getByText('提交结果尚未核对，请刷新当前状态。不会自动重复提交。').waitFor();
    const frozen=await page.evaluate(()=>sessionStorage.getItem('studyplan-v2:["boundary-owner","boundary-project"]:mutation'));
    assert.ok(frozen.includes('generateOwnedPlan'));assert.ok(!frozen.includes('fixture-csrf'));
   }
  }else{
   await page.getByText('学习计划生成正在升级，当前暂不可创建新路线。').waitFor();
   if(scenario==='none')assert.equal(await generate.isDisabled(),true);
   else {await page.getByRole('heading',{name:scenario==='reconciliation_required'?'需要核对执行结果':scenario==='cancelled'?'已取消生成':'计划尚未完成',exact:true}).waitFor();assert.equal(await generate.count(),0);assert.equal(await page.getByLabel('学习目标',{exact:true}).count(),0);}
  }
  if(scenario==='none'||canGenerate){await page.getByRole('button',{name:'补充信息（可选）'}).click();await page.getByRole('dialog').waitFor();await page.keyboard.press('Escape');assert.equal(await page.getByRole('dialog').count(),0);}
  await page.reload();await page.getByRole('heading',{name:'学习计划',exact:true}).waitFor();
  if(unknown){await page.getByText('提交结果尚未核对，请刷新当前状态。不会自动重复提交。').waitFor();await page.getByRole('button',{name:'刷新当前状态',exact:true}).click();assert.equal(await generate.isDisabled(),true);assert.equal(mutations.length,1);}
  else if(scenario==='conflict'){await page.getByRole('button',{name:'刷新当前状态',exact:true}).click();assert.equal(mutations.length,1);}
  else assert.deepEqual(mutations,[]);
  assert.deepEqual(errors,[]);await context.close();
 }
 console.log('PASS: 8 intercepted scenarios; disabled initial generation, retained Run hides empty form, dialog Escape, unknown identity survives reload/manual GET, 409 safe conflict, no automatic mutations');
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
