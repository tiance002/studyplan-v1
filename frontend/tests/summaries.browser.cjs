const {chromium}=require('playwright-core');
const assert=require('node:assert/strict');
const fs=require('node:fs'); const path=require('node:path');
(async()=>{const browser=await chromium.launch({channel:'chrome',headless:true});try{
 const page=await browser.newPage();page.setDefaultTimeout(4000);
 const stage={stage_id:'s',stable_key:'stage.test',title:'总结测试阶段',section_kind:'core',order_index:0,objective:'理解工具'};
 const units=['u1','u2'].map((unit_id,i)=>({unit_id,title:'总结单元'+(i+1),node_ids:[],objectives:['说明原理'],progress:'not_started'}));
 const workspace={plan:{plan_id:'p',project_id:'project',revision:1,goal_snapshot:'学习',stages:[stage],unit_links:[],task_links:[],stage_resources:[],extensions:[]},stages:[{stage,nodes:[],units,resources:[],tasks:[]}],total_units:2,completed_units:0};
 const threads={u1:{project_id:'project',plan_id:'p',stage_id:'s',unit_id:'u1',version:0,questions:['学到了什么？','如何运用？','工具有哪些边界？'],attempts:[]},u2:{project_id:'project',plan_id:'p',stage_id:'s',unit_id:'u2',version:0,questions:['一','二','三'],attempts:[]}};
 const attempts={};let saves=[],reviews=[],cancels=[],failSave=true,conflict=false,polls=0,finish=true,failCancel=true;
 let holdSave=false,releaseSave,signalSave,holdRead=false,releaseRead,signalRead;
 const legacy={attempt_id:'legacy',project_id:'project',plan_id:null,stage_id:null,unit_id:'oldunit',attempt_no:1,version:1,content:'历史原文\n 未改写',content_hash:'old',created_at:new Date().toISOString(),rubric_snapshot:{},review:null,run_id:null,run_status:null};
 legacy.legacy_review={feedback:'旧格式反馈原文'};legacy.legacy_review_recorded_at=new Date().toISOString();
 await page.route('**/api/v1/**',r=>r.abort('blockedbyclient'));
 await page.route('**/api/v1/session',r=>r.fulfill({json:{username:'总结用户',project_ids:['project'],csrf_token:'test'}}));
 await page.route('**/api/v1/workspace?**',r=>r.fulfill({json:workspace}));
 await page.route('**/healthz',r=>r.fulfill({json:{llm_provider:'fake'}}));
 await page.route('**/api/v1/runs/**',r=>{polls++;const id=r.request().url().split('/runs/')[1].split('?')[0];const a=Object.values(attempts).find(a=>a.run_id===id);if(finish){a.run_status='succeeded';a.review={review_id:'review'+a.attempt_id,attempt_id:a.attempt_id,conclusion:'needs_revision',covered:['原文已覆盖工具'],gaps:['补充边界'],misconceptions:[],questions:['如何核对？'],rubric_version:1,run_id:id,created_at:new Date().toISOString()};}return r.fulfill({json:{run_id:id,status:finish?'succeeded':'running',next_action:finish?'none':'wait',version:3}});});
 await page.route('**/api/v1/summaries**',async r=>{
  const req=r.request(),url=new URL(req.url()),body=req.postDataJSON();
  if(url.pathname.endsWith('/history'))return r.fulfill({json:{items:[legacy],next_cursor:null}});
  if(url.pathname.includes('/attempts/')){const id=url.pathname.split('/attempts/')[1].split('/')[0],a=attempts[id]||legacy;
   if(url.pathname.endsWith('/cancel-review')){cancels.push(body);a.run_status='cancelled';if(failCancel){failCancel=false;return r.abort('failed');}return r.fulfill({status:202,json:{run_id:a.run_id,attempt_id:id,status_url:'/api/v1/runs/'+a.run_id,status:'cancelled',next_action:'none',version:4}});}
   if(url.pathname.endsWith('/review')){reviews.push(body);a.run_id='run'+id;a.run_status='queued';return r.fulfill({status:202,json:{run_id:a.run_id,attempt_id:id,status_url:'/api/v1/runs/'+a.run_id,status:'queued',next_action:'wait',version:1}});}
   return r.fulfill({json:a});}
  if(req.method()==='GET'){const value=JSON.parse(JSON.stringify(threads[url.searchParams.get('unit_id')]));if(holdRead){holdRead=false;signalRead();await new Promise(resolve=>{releaseRead=resolve;});}return r.fulfill({json:value});}
  saves.push(body);const t=threads[body.unit_id];
  const prior=Object.values(attempts).find(a=>a.key===body.idempotency_key);
  if(prior)return r.fulfill({json:{thread:t,attempt:prior,replayed:true}});
  if(conflict){conflict=false;t.version++;return r.fulfill({status:409,json:{message:'保存版本已变化'}});}
  const a={...body,attempt_id:'a'+(Object.keys(attempts).length+1),project_id:'project',attempt_no:t.attempts.length+1,version:1,key:body.idempotency_key,content_hash:'hash',created_at:new Date().toISOString(),rubric_snapshot:{unit_title:'当时的单元',plan_revision:1,objectives:['说明工具边界']},review:null,run_id:null,run_status:null};attempts[a.attempt_id]=a;t.attempts.push(a);t.version++;
  if(failSave){failSave=false;return r.abort('failed');}if(holdSave){holdSave=false;signalSave();await new Promise(resolve=>{releaseSave=resolve;});}return r.fulfill({json:{thread:t,attempt:a,replayed:false}});
 });
 await page.goto((process.env.STUDYPLAN_URL||'http://127.0.0.1:5174')+'/#summary');
 const editor=page.getByRole('textbox',{name:'总结原文',exact:true});await editor.waitFor();await page.getByText('工具有哪些边界？',{exact:true}).waitFor();
 const raw='  短总结🙂\n\n';await editor.fill(raw);assert.equal(reviews.length,0);
 await page.getByRole('button',{name:'保存总结',exact:true}).click();await page.getByRole('button',{name:'重试原保存',exact:true}).waitFor();
 await editor.fill('较新的未保存编辑');await page.getByRole('button',{name:'重试原保存',exact:true}).click();await page.getByText('第 1 次保存的原文',{exact:true}).waitFor();
 assert.deepEqual(saves[0],saves[1]);assert.equal(saves[0].content,raw);assert.equal(await editor.inputValue(),'较新的未保存编辑');
 assert.equal(await page.locator('.summary-history .summary-original').first().textContent(),raw);
 await page.getByRole('checkbox').check();await page.getByRole('button',{name:'请求这次原文的反馈',exact:true}).click();await editor.fill('反馈期间继续写');
 await page.getByText('原文已覆盖工具',{exact:true}).waitFor();assert.equal(await editor.inputValue(),'反馈期间继续写');assert.equal(reviews.length,1);
 const terminalPolls=polls;await page.waitForTimeout(1700);assert.equal(polls,terminalPolls);
 conflict=true;await page.getByRole('button',{name:'保存总结',exact:true}).click();await page.getByText(/保存版本已变化/).waitFor();assert.equal(await editor.inputValue(),'反馈期间继续写');
 await page.getByRole('button',{name:'读取最新保存记录',exact:true}).click();await page.getByRole('button',{name:'保存总结',exact:true}).waitFor();
 holdRead=true;const readEntered=new Promise(resolve=>{signalRead=resolve;});await page.getByRole('button',{name:'读取最新保存记录',exact:true}).click();await readEntered;
 holdSave=true;const saveEntered=new Promise(resolve=>{signalSave=resolve;});await page.getByRole('button',{name:'保存总结',exact:true}).click();await saveEntered;await editor.fill('保存等待时更新的文字');releaseSave();await page.getByText('第 2 次保存的原文',{exact:true}).waitFor();releaseRead();
 await page.waitForTimeout(100);assert.equal(await editor.inputValue(),'保存等待时更新的文字');assert.equal(await page.getByLabel('查看保存版本').locator('option').count(),3);
 await editor.fill('单元一保留文字');await page.getByLabel('总结所属学习单元').selectOption('u2');await editor.fill('单元二保留文字');await page.getByLabel('总结所属学习单元').selectOption('u1');assert.equal(await editor.inputValue(),'单元一保留文字');
 await page.getByRole('button',{name:'读取项目总结历史',exact:true}).click();await page.getByRole('button',{name:/历史原文/}).click();assert.equal(await editor.inputValue(),'单元一保留文字');await page.getByText('历史原文\n 未改写',{exact:true}).waitFor();
 await page.getByRole('region',{name:'旧格式反馈',exact:true}).getByText('旧格式反馈原文',{exact:true}).waitFor();
 assert.equal(await page.evaluate(()=>JSON.stringify(localStorage).includes('单元一保留文字')),false);
 await page.reload();await editor.waitFor();await page.getByText('第 2 次保存的原文',{exact:true}).waitFor();assert.equal(await editor.inputValue(),'反馈期间继续写');
 finish=false;await page.getByRole('checkbox').first().check();await page.getByLabel('查看保存版本').selectOption('a1');await page.getByLabel('查看保存版本').selectOption('a2');assert.equal(await page.getByRole('checkbox').first().isChecked(),false);await page.getByRole('checkbox').first().check();await page.getByRole('button',{name:'请求这次原文的反馈',exact:true}).first().click();
 await page.getByRole('button',{name:'取消这次反馈',exact:true}).waitFor();await page.getByRole('button',{name:'取消这次反馈',exact:true}).click();await page.getByRole('button',{name:'重试原取消请求',exact:true}).click();await page.getByText(/本次反馈未完成/).waitFor();assert.equal(cancels.length,2);assert.deepEqual(cancels[0],cancels[1]);assert.equal(cancels[0].expected_version,3);
 fs.mkdirSync(path.resolve(__dirname,'../../var/v2-g3'),{recursive:true});await page.screenshot({path:path.resolve(__dirname,'../../var/v2-g3/summary-mock.png'),fullPage:true});
 console.log('PASS: exact raw short save, same-body retry, late feedback, conflict refresh, position buffers, history isolation, reload, terminal stop and cancel');
 }finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
