// Owned Chrome/HTTP/PG acceptance; one real Prompt review, no repeated dispatch.
const {chromium}=require('playwright-core');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..'),dir=path.join(root,'var/v2-g3');
const acceptance='v2-g3-20261001-03';
assert.equal(process.env.V2_CONFIRM_PROMPT_PAID_RUN,acceptance,'Fresh explicit owned acceptance required');
const readFile=name=>fs.existsSync(path.join(dir,name))?JSON.parse(fs.readFileSync(path.join(dir,name),'utf8')):null;
const write=(name,value)=>fs.writeFileSync(path.join(dir,name),JSON.stringify(value,null,2),{flag:'wx'});
assert.ok(!readFile('prompt-confirmed-real.json'),'Completed acceptance must not be replayed');
const credentials=JSON.parse(fs.readFileSync(path.join(root,'var/v2-g1/v2-g1-20261001-01-browser-private.json'),'utf8'));
const context=readFile('prompt-confirmed-real-context.json');assert.equal(context.acceptance_id,acceptance);
const quota=folder=>fs.readdirSync(path.join(root,'.git',folder)).filter(n=>/^request-\d+\.json$/.test(n)).length;
(async()=>{const browser=await chromium.launch({channel:'chrome',headless:true});try{
 const page=await browser.newPage({viewport:{width:1450,height:1100},permissions:['clipboard-read','clipboard-write']});
 const errors=[],forbidden=[];page.on('pageerror',()=>errors.push('pageerror'));page.on('dialog',d=>d.accept());
 await page.route('**/api/v1/**',route=>{const request=route.request(),url=new URL(request.url());
  if(request.method()==='POST'&&['/api/v1/plans/generate','/api/v1/resources/searches','/api/v1/resource-changes'].includes(url.pathname)){
   forbidden.push(url.pathname);return route.abort();}
  if(request.method()==='POST'&&url.pathname.startsWith('/api/v1/prompts/')&&url.pathname.endsWith('/review')){
   if(readFile('prompt-confirmed-real-review-intent.json'))return route.abort();
   write('prompt-confirmed-real-review-intent.json',{acceptance_id:acceptance,revision_id:url.pathname.split('/revisions/')[1].split('/')[0],body:request.postDataJSON()});}
  return route.continue();});
 await page.goto((process.env.STUDYPLAN_URL||'http://127.0.0.1:5175')+'/#practice');
 await page.getByLabel('用户名',{exact:true}).fill(credentials.username);
 await page.getByLabel('密码',{exact:true}).fill(credentials.password);
 await page.getByRole('button',{name:'登录学习空间',exact:true}).click();
 const editor=page.getByRole('textbox',{name:'方案与 Prompt 原文',exact:true});await editor.waitFor();
 const read=async url=>page.evaluate(async u=>{const r=await fetch(u,{credentials:'include'});if(!r.ok)throw new Error('Owned GET failed');return r.json();},url);
 const scope='?project_id='+encodeURIComponent(context.project_id);
 const workspace=await read('/api/v1/workspace'+scope);assert.equal(workspace.plan.revision,2);
 const stage=workspace.stages.find(s=>s.tasks.length);assert.ok(stage,'Owned published tasks required');
 const task=stage.tasks[0];await page.getByLabel('实践所属阶段').selectOption(stage.stage.stage_id);
 await page.getByLabel('实践任务',{exact:true}).selectOption(task.task_id);
 const threadUrl='/api/v1/prompts'+scope+'&'+new URLSearchParams({plan_id:workspace.plan.plan_id,stage_id:stage.stage.stage_id,task_id:task.task_id});
 const before=await read(threadUrl);assert.ok(before.practice_project.title);assert.equal(before.task.task_id,task.task_id);
 const exposures=await read('/api/v1/exposures'+scope+'&plan_id='+encodeURIComponent(workspace.plan.plan_id));
 let saved=readFile('prompt-confirmed-real-saved.json');
 if(!saved){assert.equal(quota('v2-paid-quota-20261001'),22);assert.equal(before.version,2);
  const raw='  实施方案：针对“'+task.title+'”，先明确一个可检查的交付物，再逐项核对任务要求。\nPrompt：请解释输入、输出、失败边界及验证命令；保留原始失败记录。没有实际执行的步骤标为待实施，不能声称测试已经通过。\n\t';
  await editor.fill(raw);const responsePromise=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/v1/prompts'&&r.request().method()==='POST');
  await page.getByRole('button',{name:'保存方案与 Prompt',exact:true}).click();const response=await responsePromise;assert.equal(response.status(),200);
  saved=(await response.json()).revision;assert.equal(saved.user_draft,raw);write('prompt-confirmed-real-saved.json',saved);}
 const revisionUrl='/api/v1/prompts/revisions/'+encodeURIComponent(saved.revision_id)+scope;
 let retained=await read(revisionUrl),receipt=readFile('prompt-confirmed-real-review-receipt.json');
 if(!receipt){if(retained.run_id){const run=await read('/api/v1/runs/'+encodeURIComponent(retained.run_id)+scope);
   receipt={run_id:run.run_id,revision_id:saved.revision_id,status_url:'/api/v1/runs/'+encodeURIComponent(run.run_id)+scope};write('prompt-confirmed-real-review-receipt.json',receipt);}
  else{assert.ok(!readFile('prompt-confirmed-real-review-intent.json'),'Unknown POST is retained; inspect without retry');
   await page.getByLabel('选择已保存版本').selectOption(saved.revision_id);await page.getByRole('checkbox').first().check();
   const responsePromise=page.waitForResponse(r=>new URL(r.url()).pathname.endsWith('/'+saved.revision_id+'/review'));
   await page.getByRole('button',{name:'请求这版原文反馈',exact:true}).click();const response=await responsePromise;assert.equal(response.status(),202);
   receipt=await response.json();write('prompt-confirmed-real-review-receipt.json',receipt);}}
 let newer=readFile('prompt-confirmed-real-second-saved.json');
 if(!newer){const raw='第二版方案：补充一个最小失败示例和预期验证命令。\n这些是待执行的设计；没有运行结果前，不将任务标为已验收。\n ';
  await editor.fill(raw);const responsePromise=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/v1/prompts'&&r.request().method()==='POST');
  await page.getByRole('button',{name:'保存方案与 Prompt',exact:true}).click();const response=await responsePromise;assert.equal(response.status(),200);
  newer=(await response.json()).revision;assert.equal(newer.user_draft,raw);write('prompt-confirmed-real-second-saved.json',newer);}
 const local='反馈和导出期间仍在编辑的第三版文字，保持未保存。';await editor.fill(local);
 await page.getByLabel('选择已保存版本').selectOption(saved.revision_id);
 if(!readFile('prompt-confirmed-real-editor-gate.json'))write('prompt-confirmed-real-editor-gate.json',{acceptance_id:acceptance,run_id:receipt.run_id,newer_revision_id:newer.revision_id});
 const original=page.getByRole('article',{name:'已保存方案第 '+saved.revision_no+' 版',exact:true});
 await original.getByRole('heading',{name:'优点',exact:true}).waitFor({timeout:180000});
 assert.equal(await editor.inputValue(),local);assert.equal((await read(receipt.status_url)).status,'succeeded');
 retained=await read(revisionUrl);assert.equal(retained.user_draft,saved.user_draft);assert.equal(retained.review.run_id,receipt.run_id);
 const latest=await read(threadUrl);assert.equal(latest.revisions.at(-1).revision_id,newer.revision_id);assert.equal(latest.revisions.at(-1).review,null);
 let rawExport=readFile('prompt-confirmed-real-raw-export.json');
 if(!rawExport){await original.getByLabel('导出内容').selectOption('raw');const responsePromise=page.waitForResponse(r=>new URL(r.url()).pathname.endsWith('/'+saved.revision_id+'/exports'));
  await original.getByRole('button',{name:'生成这版导出',exact:true}).click();const response=await responsePromise;assert.equal(response.status(),200);
  rawExport=await response.json();write('prompt-confirmed-real-raw-export.json',rawExport);}
 assert.equal(rawExport.revision_id,saved.revision_id);assert.equal(rawExport.export_text,saved.user_draft);
 // The retained raw export is read from the selected version, never from the editor.
 if(!(await original.getByRole('button',{name:'下载这版导出',exact:true}).isVisible()))throw new Error('Retained export needs explicit UI observation');
 await original.getByRole('button',{name:'复制这版导出',exact:true}).click();
 await original.getByRole('alert').filter({hasText:'已复制所选版本导出'}).waitFor();
 const clipboard=await page.evaluate(()=>navigator.clipboard.readText());assert.equal(process.platform==='win32'?clipboard.replace(/\r\n/g,'\n'):clipboard,saved.user_draft);
 const downloadPromise=page.waitForEvent('download');await original.getByRole('button',{name:'下载这版导出',exact:true}).click();const download=await downloadPromise;
 const downloaded=path.join(dir,'prompt-confirmed-real-downloaded.txt');await download.saveAs(downloaded);assert.equal(fs.readFileSync(downloaded,'utf8'),saved.user_draft);
 let implementation=readFile('prompt-confirmed-real-implementation-export.json');
 if(!implementation){await original.getByLabel('导出内容').selectOption('implementation');const responsePromise=page.waitForResponse(r=>new URL(r.url()).pathname.endsWith('/'+saved.revision_id+'/exports'));
  await original.getByRole('button',{name:'生成这版导出',exact:true}).click();const response=await responsePromise;assert.equal(response.status(),200);
  implementation=await response.json();write('prompt-confirmed-real-implementation-export.json',implementation);}
 assert.equal(implementation.revision_id,saved.revision_id);assert.ok(implementation.export_text.includes(saved.user_draft));assert.ok(implementation.export_text.includes(task.title));
 assert.equal(await editor.inputValue(),local);
 assert.deepEqual(await read('/api/v1/exposures'+scope+'&plan_id='+encodeURIComponent(workspace.plan.plan_id)),exposures);
 assert.equal((await read('/api/v1/workspace'+scope)).stages.find(s=>s.stage.stage_id===stage.stage.stage_id).tasks.find(t=>t.task_id===task.task_id).status,task.status);
 await page.reload();await editor.waitFor();await page.getByRole('article',{name:'已保存方案第 '+newer.revision_no+' 版',exact:true}).waitFor();assert.equal(await editor.inputValue(),newer.user_draft);
 await page.getByLabel('选择已保存版本').selectOption(saved.revision_id);await original.getByRole('heading',{name:'优点',exact:true}).waitFor();
 assert.equal((await read('/api/v1/prompts/exports/'+rawExport.export_id+scope)).export_text,saved.user_draft);
 assert.ok((await read('/api/v1/prompts/history'+scope)).items.some(r=>r.revision_id===saved.revision_id&&r.review?.run_id===receipt.run_id));
 assert.equal(quota('v2-paid-quota-20261001'),23);assert.equal(quota('v2-search-quota-20261001'),2);assert.deepEqual(errors,[]);assert.deepEqual(forbidden,[]);
 await page.evaluate(()=>window.scrollTo(0,0));await page.screenshot({path:path.join(dir,'prompt-confirmed-real.png'),fullPage:true});
 const result={status:'PASS',acceptance_id:acceptance,source:'Chrome + owned HTTP/PG + configured model + actual clipboard/download',
  run_id:receipt.run_id,project_id:context.project_id,original_revision_id:saved.revision_id,newer_revision_id:newer.revision_id,
  raw_export_id:rawExport.export_id,implementation_export_id:implementation.export_id,model_requests:23,search_requests:2,
  exact_raw:true,pinned_feedback:true,newer_and_editor_preserved:true,clipboard_exact:clipboard===saved.user_draft,clipboard_lf_equivalent:true,download_exact:true,
  selected_older_exports:true,progress_and_task_status_unchanged:true,reload_history:true};
 write('prompt-confirmed-real.json',result);console.log(JSON.stringify(result));
 }finally{await browser.close();}})().catch(()=>{console.error('FAIL: owned Prompt observation; preserve known revisions/Run/exports and inspect without repeating dispatch.');process.exitCode=1;});
