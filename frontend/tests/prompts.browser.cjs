const {chromium}=require('playwright-core');
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
(async()=>{const browser=await chromium.launch({channel:'chrome',headless:true});try{
 const page=await browser.newPage();page.setDefaultTimeout(3000);
 const stage={stage_id:'s',stable_key:'stage.practice',title:'实践阶段',section_kind:'core',order_index:0,objective:'实践'};
 const task={task_id:'t',title:'做一个工具助手',goal:'说明并实现工具调用',in_scope:['工具协议'],out_scope:['公网部署'],acceptance:['能说明失败处理'],status:'planned',knowledge_links:[{node_id:'n',stable_key:'node.tools',title:'工具调用',role:'core',content_version:1}]};
 const workspace={plan:{plan_id:'p',project_id:'project',revision:1,goal_snapshot:'实践目标',stages:[stage],unit_links:[],task_links:[],stage_resources:[],extensions:[]},stages:[{stage,nodes:[],units:[],resources:[],tasks:[task,{...task,task_id:'t2',title:'验证助手'}]}],total_units:0,completed_units:0};
 await page.route('**/api/v1/**',r=>r.abort('blockedbyclient'));
 await page.route('**/api/v1/session',r=>r.fulfill({json:{username:'实践用户',project_ids:['project'],csrf_token:'test-csrf'}}));
 await page.route('**/api/v1/workspace?**',r=>r.fulfill({json:workspace}));
 await page.route('**/healthz',r=>r.fulfill({json:{llm_provider:'fake'}}));
 await page.addInitScript(()=>{navigator.clipboard.writeText=async value=>{window.promptCopied=value;};});
 const practice={practice_project_id:'practice',title:'我的工具助手主项目',idea:'围绕工具协议逐步实现助手',repo_url:null,status:'planned',version:1};
 const tasks={t:task,t2:{...task,task_id:'t2',title:'验证助手'}};
 const threads=Object.fromEntries(Object.entries(tasks).map(([id,value])=>[id,{project_id:'project',plan_id:'p',stage_id:'s',task_id:id,version:0,practice_project:practice,task:value,revisions:[],history_truncated:false}]));
 const revisions={},exports={};let saves=[],reviewCalls=[],cancelCalls=[],exportCalls=[],polls=0;
 let failSave=true,failReview=true,failExport=true,failCancel=true,conflict=false,finish=true,holdRead=false,releaseRead,signalRead,holdSave=false,releaseSave,signalSave;
 const legacy={revision_id:'old',project_id:'project',plan_id:null,stage_id:null,task_id:'oldtask',revision_no:7,version:0,user_draft:' 历史方案原文\n',content_hash:'oldhash',created_at:new Date().toISOString(),task_snapshot:{},review:null,run_id:null,run_status:null,legacy_review:{feedback:'旧反馈原文'}};
 revisions.old=legacy;
 await page.route('**/api/v1/runs/**',r=>{polls++;const rid=r.request().url().split('/runs/')[1].split('?')[0],rev=Object.values(revisions).find(v=>v.run_id===rid);if(finish){rev.run_status='succeeded';rev.review={review_id:'review-'+rev.revision_id,revision_id:rev.revision_id,task_id:rev.task_id,strengths:['这版原文说明了工具调用'],gaps:['补充失败处理'],suggestions:['说明验证方法'],run_id:rid,created_at:new Date().toISOString()};}return r.fulfill({json:{run_id:rid,status:finish?'succeeded':'running',next_action:finish?'none':'wait',version:3}});});
 await page.route('**/api/v1/prompts**',async r=>{
  const req=r.request(),url=new URL(req.url()),body=req.postDataJSON();
  if(req.method()!=='GET')assert.equal(req.headers()['x-csrf-token'],'test-csrf');
  if(url.pathname.endsWith('/history'))return r.fulfill({json:{items:[legacy],next_cursor:null}});
  if(url.pathname.includes('/exports/'))return r.fulfill({json:Object.values(exports).find(v=>v.export_id===url.pathname.split('/exports/')[1])});
  if(url.pathname.includes('/revisions/')){
   const id=url.pathname.split('/revisions/')[1].split('/')[0],rev=revisions[id];
   if(url.pathname.endsWith('/review')){reviewCalls.push({id,body});rev.run_id='run-'+id;rev.run_status='queued';if(failReview){failReview=false;return r.abort('failed');}return r.fulfill({status:202,json:{run_id:rev.run_id,revision_id:id,status_url:'/api/v1/runs/'+rev.run_id,status:rev.run_status,next_action:'wait',version:1}});}
   if(url.pathname.endsWith('/cancel-review')){cancelCalls.push({id,body});rev.run_status='cancelled';if(failCancel){failCancel=false;return r.abort('failed');}return r.fulfill({json:{run_id:rev.run_id,revision_id:id,status_url:'/api/v1/runs/'+rev.run_id,status:'cancelled',next_action:'none',version:4}});}
   if(url.pathname.endsWith('/exports')){exportCalls.push({id,body});const key=id+'/'+body.format;exports[key]||={export_id:'export-'+Object.keys(exports).length,project_id:'project',task_id:rev.task_id,revision_id:id,revision_no:rev.revision_no,format:body.format,export_text:body.format==='raw'?rev.user_draft:'主项目：'+rev.task_snapshot.practice_project?.title+'\n任务：'+rev.task_snapshot.task?.title+'\n验收：能说明失败处理\n原文：\n'+rev.user_draft,content_hash:'exporthash',created_at:new Date().toISOString()};if(failExport){failExport=false;return r.abort('failed');}return r.fulfill({json:exports[key]});}
   return r.fulfill({json:rev});
  }
  if(req.method()==='GET'){const value=JSON.parse(JSON.stringify(threads[url.searchParams.get('task_id')]));if(holdRead){holdRead=false;signalRead();await new Promise(resolve=>{releaseRead=resolve;});}return r.fulfill({json:value});}
  saves.push(body);const t=threads[body.task_id],prior=Object.values(revisions).find(v=>v.key===body.idempotency_key);
  if(prior)return r.fulfill({json:{thread:t,revision:prior,replayed:true}});
  if(conflict){conflict=false;t.version++;return r.fulfill({status:409,json:{message:'方案版本已变化'}});}
  const rev={revision_id:'r'+saves.length,project_id:'project',plan_id:'p',stage_id:'s',task_id:body.task_id,revision_no:t.revisions.length+1,version:t.version+1,user_draft:body.user_draft,content_hash:'rawhash',created_at:new Date().toISOString(),task_snapshot:{snapshot_status:'frozen',plan_revision:1,task:tasks[body.task_id],practice_project:practice,knowledge_links:task.knowledge_links},review:null,run_id:null,run_status:null,key:body.idempotency_key};revisions[rev.revision_id]=rev;t.revisions.push(rev);t.version++;
  if(failSave){failSave=false;return r.abort('failed');}if(holdSave){holdSave=false;signalSave();await new Promise(resolve=>{releaseSave=resolve;});}return r.fulfill({json:{thread:t,revision:rev,replayed:false}});
 });
 await page.goto((process.env.STUDYPLAN_URL||'http://127.0.0.1:5174')+'/#practice');
 const editor=page.getByRole('textbox',{name:'方案与 Prompt 原文',exact:true});await editor.waitFor();await page.getByRole('heading',{name:practice.title,exact:true}).waitFor();
 await page.getByText('能说明失败处理',{exact:true}).waitFor();await page.getByText('工具调用（核心）',{exact:true}).waitFor();
 const raw='  方案🙂\n\n请使用工具。  ';await editor.fill(raw);await page.getByRole('button',{name:'保存方案与 Prompt',exact:true}).click();await page.getByRole('button',{name:'重试原保存',exact:true}).waitFor();
 await editor.fill('更新的未保存方案');await page.getByRole('button',{name:'重试原保存',exact:true}).click();await page.getByRole('heading',{name:'第 1 版原文',exact:true}).waitFor();
 assert.deepEqual(saves[0],saves[1]);assert.equal(saves[0].user_draft,raw);assert.equal(await editor.inputValue(),'更新的未保存方案');assert.equal(reviewCalls.length,0);
 const visible=()=>page.locator('.prompt-saved article:visible');
 await visible().getByRole('checkbox').check();await visible().getByRole('button',{name:'请求这版原文反馈',exact:true}).click();await visible().getByRole('button',{name:'重试原反馈请求',exact:true}).waitFor();
 await page.getByLabel('实践任务',{exact:true}).selectOption('t2');await editor.fill('另一个任务的未保存方案');await page.getByLabel('实践任务',{exact:true}).selectOption('t');assert.equal(await editor.inputValue(),'更新的未保存方案');
 await visible().getByRole('button',{name:'重试原反馈请求',exact:true}).click();await editor.fill('反馈期间继续编辑');await page.getByText('这版原文说明了工具调用',{exact:true}).waitFor();assert.equal(await editor.inputValue(),'反馈期间继续编辑');assert.deepEqual(reviewCalls[0],reviewCalls[1]);
 const terminalPolls=polls;await page.waitForTimeout(1700);assert.equal(polls,terminalPolls);
 await visible().getByRole('button',{name:'生成这版导出',exact:true}).click();await visible().getByRole('button',{name:'重试原导出请求',exact:true}).waitFor();await visible().getByLabel('导出内容').selectOption('implementation');await visible().getByRole('button',{name:'重试原导出请求',exact:true}).click();
 await visible().getByRole('button',{name:'复制这版导出',exact:true}).click();assert.equal(await page.evaluate(()=>window.promptCopied),raw);assert.deepEqual(exportCalls[0],exportCalls[1]);
 let downloaded=page.waitForEvent('download');await visible().getByRole('button',{name:'下载这版导出',exact:true}).click();let file=await downloaded;assert.equal(fs.readFileSync(await file.path(),'utf8'),raw);assert.equal(file.suggestedFilename(),'studyplan-prompt-v1-raw.txt');
 await visible().getByRole('button',{name:'生成这版导出',exact:true}).click();await visible().getByText(/已生成第 1 版实施 Prompt导出/).waitFor();await visible().getByRole('button',{name:'复制这版导出',exact:true}).click();const implementation=await page.evaluate(()=>window.promptCopied);assert.ok(implementation.includes(practice.title)&&implementation.includes(task.title)&&implementation.endsWith(raw));assert.equal(implementation.includes('反馈期间继续编辑'),false);
 downloaded=page.waitForEvent('download');await visible().getByRole('button',{name:'下载这版导出',exact:true}).click();file=await downloaded;assert.equal(fs.readFileSync(await file.path(),'utf8'),implementation);
 conflict=true;await page.getByRole('button',{name:'保存方案与 Prompt',exact:true}).click();await page.getByText(/方案版本已变化/).waitFor();assert.equal(await editor.inputValue(),'反馈期间继续编辑');await page.getByRole('button',{name:'读取最新保存版本',exact:true}).click();
 holdRead=true;const readEntered=new Promise(resolve=>{signalRead=resolve;});await page.getByRole('button',{name:'读取最新保存版本',exact:true}).click();await readEntered;
 holdSave=true;const saveEntered=new Promise(resolve=>{signalSave=resolve;});await page.getByRole('button',{name:'保存方案与 Prompt',exact:true}).click();await saveEntered;await editor.fill('保存等待时继续编辑');releaseSave();await page.getByRole('heading',{name:'第 2 版原文',exact:true}).waitFor();releaseRead();await page.waitForTimeout(100);assert.equal(await editor.inputValue(),'保存等待时继续编辑');
 await visible().getByRole('checkbox').check();await page.getByLabel('选择已保存版本').selectOption('r1');await visible().getByLabel('导出内容').selectOption('raw');await visible().getByRole('button',{name:'生成这版导出',exact:true}).click();await visible().getByRole('button',{name:'复制这版导出',exact:true}).click();assert.equal(await page.evaluate(()=>window.promptCopied),raw);assert.equal(exportCalls.at(-1).id,'r1');await page.getByLabel('选择已保存版本').selectOption('r4');assert.equal(await visible().getByRole('checkbox').isChecked(),false);
 finish=false;await visible().getByRole('checkbox').check();await visible().getByRole('button',{name:'请求这版原文反馈',exact:true}).click();await visible().getByRole('button',{name:'取消这版反馈',exact:true}).click();await visible().getByRole('button',{name:'重试原取消请求',exact:true}).click();await visible().getByText(/本次反馈已结束/).waitFor();assert.deepEqual(cancelCalls[0],cancelCalls[1]);
 await page.getByRole('button',{name:'读取项目方案历史',exact:true}).click();await page.getByRole('button',{name:/历史方案 · 第 7 版/}).click();await page.getByText('旧反馈原文',{exact:true}).waitFor();assert.equal(await editor.inputValue(),'保存等待时继续编辑');await visible().getByRole('button',{name:'生成这版导出',exact:true}).click();await visible().getByRole('button',{name:'复制这版导出',exact:true}).click();assert.equal(await page.evaluate(()=>window.promptCopied),legacy.user_draft);
 assert.equal(await page.evaluate(()=>JSON.stringify(localStorage).includes('保存等待时继续编辑')),false);
 await page.reload();await editor.waitFor();await page.getByRole('heading',{name:'第 2 版原文',exact:true}).waitFor();assert.equal(await editor.inputValue(),'反馈期间继续编辑');
 fs.mkdirSync(path.resolve(__dirname,'../../var/v2-g3'),{recursive:true});await page.screenshot({path:path.resolve(__dirname,'../../var/v2-g3/prompt-mock.png'),fullPage:true});
 console.log('PASS: exact raw/context/CSRF, save/review/cancel/export samebody retries, late edits/head protection, selected-version copy/download, history and reload');
 }finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
