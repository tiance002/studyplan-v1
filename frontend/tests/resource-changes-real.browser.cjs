// Actual owned loopback HTTP/PG and browser, no model/search dispatch.
const {chromium}=require('playwright-core');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..'),acceptance='v2-g2-20261001-03';
if(process.env.V2_CONFIRM_RESOURCE_CHANGE_RUN!==acceptance)throw new Error('Explicit owned replacement acceptance required');
const reportPath=path.join(root,'var/v2-g2/resource-change-real.json');
assert.ok(!fs.existsSync(reportPath),'Do not replay completed acceptance');
const phasePath=path.join(root,'var/v2-g2/resource-change-real-preview.json');
const privateContext=JSON.parse(fs.readFileSync(path.join(root,'var/v2-g1/v2-g1-20261001-01-browser-private.json')));
const quota=folder=>fs.readdirSync(path.join(root,'.git',folder)).filter(n=>/^request-\d+\.json$/.test(n)).length;
const base=process.env.STUDYPLAN_URL||'http://127.0.0.1:5175';
assert.equal(quota('v2-paid-quota-20261001'),20);assert.equal(quota('v2-search-quota-20261001'),2);
(async()=>{const browser=await chromium.launch({channel:'chrome',headless:true});try{
  const page=await browser.newPage({viewport:{width:1400,height:1000}}),errors=[],forbidden=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/api/v1/**',route=>{const req=route.request(),url=new URL(req.url());
    if(req.method()==='POST'&&['/api/v1/plans/generate','/api/v1/resources/searches'].includes(url.pathname)){forbidden.push(url.pathname);return route.abort();}
    return route.continue();});
  await page.goto(base+'/#workspace');
  await page.getByLabel('用户名',{exact:true}).fill(privateContext.username);
  await page.getByLabel('密码',{exact:true}).fill(privateContext.password);
  await page.getByRole('button',{name:'登录学习空间',exact:true}).click();
  await page.getByRole('region',{name:'主线资料替换'}).waitFor();
  async function read(url){return page.evaluate(async u=>{const r=await fetch(u,{credentials:'include'});if(!r.ok)throw new Error('Owned GET failed '+r.status);return r.json();},url);}
  const session=await read('/api/v1/session'),project=session.project_ids[0],scope='?project_id='+encodeURIComponent(project);
  let phase=fs.existsSync(phasePath)?JSON.parse(fs.readFileSync(phasePath)):null;
  if(!phase){
    const workspace=await read('/api/v1/workspace'+scope);assert.equal(workspace.plan.revision,1);
    const stage=workspace.stages[0],primary=stage.resources.find(r=>r.role==='primary');assert.ok(primary);
    const catalog=await read('/api/v1/resource-changes/catalog'+scope);
    let source=catalog.find(row=>row.source.source_id===primary.source_ref&&row.sections.length>1)||catalog.find(row=>row.sections.length>1);assert.ok(source);
    const oldRefs=primary.ordered_sections.map(s=>s.section_id);
    const sections=source.sections.slice(0,source.source.source_id===primary.source_ref&&oldRefs.length===1&&oldRefs[0]===source.sections[0].section_id?2:1);
    assert.ok(source.source.source_id!==primary.source_ref||JSON.stringify(oldRefs)!==JSON.stringify(sections.map(s=>s.section_id)));
    const oldExposures=await read('/api/v1/exposures'+scope+'&plan_id='+encodeURIComponent(workspace.plan.plan_id));
    const panel=page.getByRole('region',{name:'主线资料替换'});
    await panel.getByLabel('公开资料目录').selectOption(source.source.source_id);
    await panel.getByLabel('起始章节').selectOption(sections[0].section_id);
    await panel.getByLabel('结束章节').selectOption(sections.at(-1).section_id);
    await panel.getByLabel('私人资料沿用策略').selectOption('copy_active');
    const responsePromise=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/v1/resource-changes'&&r.request().method()==='POST');
    await panel.getByRole('button',{name:'查看主线替换差异'}).click();
    const response=await responsePromise;assert.equal(response.status(),200);const preview=await response.json();
    assert.equal(preview.status,'pending');assert.deepEqual(preview.after.section_refs,sections.map(s=>s.section_id));
    assert.equal((await read('/api/v1/workspace'+scope)).plan.plan_id,workspace.plan.plan_id);
    phase={acceptance_id:acceptance,project,old_plan_id:workspace.plan.plan_id,old_revision:1,old_exposures:oldExposures,preview};
    fs.writeFileSync(phasePath,JSON.stringify(phase,null,2),{flag:'wx'});
  }
  // A failed observation resumes this same retained proposal; never create another.
  let retained=await read('/api/v1/resource-changes/'+encodeURIComponent(phase.preview.proposal_id)+scope);
  if(retained.status==='pending'){
    const key=`studyplan:resource-change:${project}:${phase.old_plan_id}:${phase.preview.before.stage_id}`;
    await page.evaluate(({key,id})=>localStorage.setItem(key,id),{key,id:phase.preview.proposal_id});
    await page.reload();const panel=page.getByRole('region',{name:'主线资料替换'});
    await panel.getByText('预览状态：待确认',{exact:true}).waitFor();
    assert.equal(await panel.getByRole('button',{name:'确认发布新路线'}).isDisabled(),true);
    await panel.getByRole('checkbox').check();
    const responsePromise=page.waitForResponse(r=>new URL(r.url()).pathname.endsWith('/'+phase.preview.proposal_id+'/confirm'));
    await panel.getByRole('button',{name:'确认发布新路线'}).click();
    const response=await responsePromise;assert.equal(response.status(),200);const receipt=await response.json();
    assert.equal(receipt.revision,2);assert.equal(receipt.copied_selections,phase.preview.impact.private_bindings.copy_count);
    fs.writeFileSync(path.join(root,'var/v2-g2/resource-change-real-receipt.json'),JSON.stringify(receipt,null,2),{flag:'wx'});
    retained=await read('/api/v1/resource-changes/'+encodeURIComponent(phase.preview.proposal_id)+scope);
  }
  assert.equal(retained.status,'confirmed');
  const current=await read('/api/v1/workspace'+scope);assert.equal(current.plan.revision,2);assert.notEqual(current.plan.plan_id,phase.old_plan_id);
  assert.notEqual(current.stages[0].stage.stage_id,phase.preview.before.stage_id);
  const newExposure=await read('/api/v1/exposures'+scope+'&plan_id='+encodeURIComponent(current.plan.plan_id));
  assert.ok(newExposure.length&&newExposure.every(e=>e.version===0&&e.status==='not_started'&&!e.recorded));
  assert.deepEqual(await read('/api/v1/exposures'+scope+'&plan_id='+encodeURIComponent(phase.old_plan_id)),phase.old_exposures);
  const primary=current.stages[0].resources.find(r=>r.role==='primary');assert.deepEqual(primary.ordered_sections.map(s=>s.section_id),phase.preview.after.section_refs);
  let copiedCount=0;
  for(const stage of current.stages)for(const unit of stage.units){const selections=await read('/api/v1/resources/selections'+scope+'&'+new URLSearchParams({plan_id:current.plan.plan_id,stage_id:stage.stage.stage_id,unit_id:unit.unit_id}));copiedCount+=selections.length;for(const selected of selections)assert.ok(selected.resource.source_note?.includes('原选择记录'));}
  assert.equal(copiedCount,phase.preview.impact.private_bindings.copy_count);
  await page.reload();await page.getByRole('region',{name:'出现位置学习进度'}).getByText('当前记录：未开始',{exact:true}).waitFor();
  await page.getByRole('region',{name:'主线资料替换'}).scrollIntoViewIfNeeded();
  await page.screenshot({path:path.join(root,'var/v2-g2/resource-change-real.png'),fullPage:true});
  assert.deepEqual(errors,[]);assert.deepEqual(forbidden,[]);assert.equal(quota('v2-paid-quota-20261001'),20);assert.equal(quota('v2-search-quota-20261001'),2);
  const report={status:'PASS',acceptance_id:acceptance,source:'Chrome + real owned loopback HTTP + retained PG',preview_then_explicit_confirm:true,revision:2,old_progress_preserved:true,new_exposures_unstarted:true,private_copy_count:phase.preview.impact.private_bindings.copy_count,source_snapshot_preserved:true,reload:true,model_requests:20,search_requests:2};
  fs.writeFileSync(reportPath,JSON.stringify(report,null,2),{flag:'wx'});console.log(JSON.stringify(report));
}finally{await browser.close();}})().catch(()=>{console.error('Real owned replacement FAIL; inspect retained owned evidence without printing credentials.');process.exitCode=1;});
