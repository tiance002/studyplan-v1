// Ordinary browser registration/generation and real owned HTTP/PG. Generation model: Fake.
const { chromium } = require('playwright-core');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {createHash}=require('node:crypto');
const hash=value=>createHash('sha256').update(value,'utf8').digest('hex');

(async () => {
  const api = process.env.STUDYPLAN_CURRENT_LOOP_API;
  assert.equal(new URL(api).hostname, '127.0.0.1');
  const ui = process.env.STUDYPLAN_URL || 'http://127.0.0.1:5178';
  const browser = await chromium.launch({channel:'chrome', headless:true});
  const context = await browser.newContext();
  const forwarded = [], errors = [], originals = [], summaries = [], ownedWrites = [];
  let collectOwnedWrites=true;
  let failWorkspace = false, hideSummary = false, hiddenBody, hiddenResult;
  try {
    await context.route('**/*', async route => {
      const request = route.request(), url = new URL(request.url());
      if (!['127.0.0.1','localhost'].includes(url.hostname)) return route.abort('blockedbyclient');
      if (!url.pathname.startsWith('/api/v1/') && url.pathname !== '/healthz') return route.continue();
      if (failWorkspace && url.pathname === '/api/v1/workspace' && request.method() === 'GET') {
        failWorkspace = false;
        forwarded.push({method:'GET', path:url.pathname, status:503, injected:true});
        return route.fulfill({status:503, contentType:'application/json', body:JSON.stringify({detail:'controlled owned read failure'})});
      }
      const response = await route.fetch({url:api + url.pathname + url.search});
      forwarded.push({method:request.method(), path:url.pathname, status:response.status()});
      if(collectOwnedWrites && request.method()==='POST' && response.status()===200 &&
        (url.pathname.startsWith('/api/v1/plans/drafts/')||url.pathname.startsWith('/api/v1/summaries')||url.pathname.startsWith('/api/v1/submissions')))
        ownedWrites.push({path:url.pathname,body:request.postDataJSON()});
      if (hideSummary && url.pathname === '/api/v1/summaries' && request.method() === 'POST') {
        hideSummary = false; hiddenBody = request.postDataJSON(); hiddenResult = await response.json();
        assert.equal(response.status(), 200);
        return route.abort('failed'); // real save succeeded, caller response intentionally unavailable
      }
      return route.fulfill({response});
    });
    let page = await context.newPage();
    page.setDefaultTimeout(12000);
    page.on('pageerror', error => errors.push(error.message));
    page.on('dialog', dialog => dialog.accept());
    const username = '闭环' + Date.now(), password = 'Test-pass1!';
    async function authenticate(register=false, user=username) {
      if (register) await page.getByRole('button', {name:'注册',exact:true}).click();
      await page.getByLabel('用户名',{exact:true}).fill(user);
      await page.getByLabel('密码',{exact:true}).fill(password);
      const response = page.waitForResponse(r => new URL(r.url()).pathname === '/api/v1/auth/' + (register?'register':'login'));
      await page.getByRole('button',{name:register?'注册并进入':'登录学习空间',exact:true}).click();
      assert.equal((await response).status(),200);
      await page.getByRole('button',{name:'退出登录',exact:true}).waitFor();
    }
    const request = async (url, body) => page.evaluate(async ({url,body}) => {
      const session = await (await fetch('/api/v1/session')).json();
      const response = await fetch(url, {method:body?'POST':'GET', headers:body?{'Content-Type':'application/json','X-CSRF-Token':session.csrf_token}:{}, body:body?JSON.stringify(body):undefined});
      return {status:response.status, body:await response.json()};
    }, {url,body});
    await page.goto(ui+'/#planning');
    await authenticate(true);
    await page.getByRole('button',{name:'退出登录',exact:true}).click();
    await authenticate();
    await page.getByLabel('你想学会什么？').fill('Agent工具学习闭环');
    const generation = page.waitForResponse(r => new URL(r.url()).pathname === '/api/v1/plans/generate');
    await page.getByRole('button',{name:'生成学习草案 →',exact:true}).click();
    const queued = await generation; assert.equal(queued.status(),202);
    const receipt = await queued.json();
    await page.getByLabel('阶段 1 标题',{exact:true}).waitFor();
    await page.getByLabel('阶段 1 标题',{exact:true}).fill('闭环私有修改标题🙂');
    await page.getByRole('button',{name:'保存修改',exact:true}).click();
    const approval = page.waitForResponse(r => r.request().method()==='POST' && new URL(r.url()).pathname.endsWith('/decision') && r.request().postDataJSON().decision==='approve');
    await page.getByRole('button',{name:'确认并发布路线',exact:true}).click();
    const published = await approval; assert.equal(published.status(),200);
    const plan = (await published.json()).plan;
    assert.equal(plan.stages[0].title,'闭环私有修改标题🙂');
    const session = (await request('/api/v1/session')).body;
    const q = '?project_id='+session.project_ids[0];
    const run=(await request(receipt.status_url)).body; assert.equal(run.next_action,'none');
    const tool = plan.stages.find(s=>s.stable_key==='stage.tools');
    const position = {plan_id:plan.plan_id,stage_id:tool.stage_id};
    const completion = async () => (await request('/api/v1/workspace'+q)).body.stages.find(s=>s.stage.stage_id===tool.stage_id).completion;
    await page.goto(ui+'/#summary');
    await page.getByLabel('总结所属阶段').selectOption(tool.stage_id);
    const editor = page.getByLabel('总结原文',{exact:true});
    async function saveSummary(raw) {
      await editor.fill(raw);
      const response = page.waitForResponse(r=>new URL(r.url()).pathname==='/api/v1/summaries'&&r.request().method()==='POST');
      await page.getByRole('button',{name:'保存总结',exact:true}).click();
      const http = await response; assert.equal(http.status(),200);
      const result = await http.json(); assert.equal(result.attempt.content,raw); summaries.push(result.attempt);
      await page.getByRole('button',{name:'保存总结',exact:true}).waitFor({state:'visible'});
      return result;
    }
    await saveSummary('  第一版🙂\n段落二\t ');
    failWorkspace=true;
    await saveSummary('  第二版漢字🙂\n段落二\t ');
    await page.getByRole('alert').filter({hasText:'总结已保存，阶段状态暂未刷新'}).waitFor();
    assert.equal((await completion()).status,'incomplete');
    // Unknown save is reconciled with exactly the original body/key, one durable row.
    hideSummary=true;
    await editor.fill('  响应隐藏保存🙂\n\t ');
    await page.getByRole('button',{name:'保存总结',exact:true}).click();
    await page.getByRole('button',{name:'重试原保存',exact:true}).waitFor();
    const replay = page.waitForResponse(r=>new URL(r.url()).pathname==='/api/v1/summaries'&&r.request().method()==='POST');
    await page.getByRole('button',{name:'重试原保存',exact:true}).click();
    const replayHttp = await replay;
    assert.deepEqual(replayHttp.request().postDataJSON(),hiddenBody);
    const replayed=await replayHttp.json(); assert.equal(replayed.replayed,true);
    assert.deepEqual(replayed.attempt,hiddenResult.attempt);
    summaries.push(hiddenResult.attempt);
    // Another real page writes against the same baseline; 409 must preserve local text.
    const second = await context.newPage();
    await second.goto(ui+'/#summary');
    await second.getByLabel('总结所属阶段').selectOption(tool.stage_id);
    await second.getByRole('button',{name:'保存总结',exact:true}).waitFor();
    await second.getByLabel('总结原文',{exact:true}).fill('第二页面保存🙂\n ');
    const secondSave = second.waitForResponse(r=>new URL(r.url()).pathname==='/api/v1/summaries'&&r.request().method()==='POST');
    await second.getByRole('button',{name:'保存总结',exact:true}).click();
    assert.equal((await secondSave).status(),200);
    await editor.fill('本地冲突文字🙂\n须保留 ');
    const conflict = page.waitForResponse(r=>new URL(r.url()).pathname==='/api/v1/summaries'&&r.request().method()==='POST');
    await page.getByRole('button',{name:'保存总结',exact:true}).click();
    assert.equal((await conflict).status(),409);
    assert.equal(await editor.inputValue(),'本地冲突文字🙂\n须保留 ');
    await page.getByRole('button',{name:'读取最新保存记录',exact:true}).click();
    assert.equal(await editor.inputValue(),'本地冲突文字🙂\n须保留 ');
    await second.close();
    await page.goto(ui+'/#practice');
    await page.getByLabel('实践所属阶段').selectOption(tool.stage_id);
    const tasks = plan.task_links.filter(t=>t.stage_id===tool.stage_id);
    const panel = page.getByRole('region',{name:'成果提交与人工验收',exact:true});
    for (const [index,task] of tasks.entries()) {
      await page.getByLabel('实践任务',{exact:true}).selectOption(task.task_id);
      const note='  初次不足🙂\n\t '+index;
      await panel.getByLabel('成果说明原文',{exact:true}).fill(note);
      let response = page.waitForResponse(r=>new URL(r.url()).pathname==='/api/v1/submissions'&&r.request().method()==='POST');
      await panel.getByRole('button',{name:'保存成果与证据',exact:true}).click();
      let http=await response; assert.equal(http.status(),200); const first=await http.json();
      assert.equal(first.submission.note,note); assert.equal(first.submission.evidence_grade,'insufficient');
      let detail=panel.locator('.submission-detail:visible');
      await detail.getByLabel('人工决定',{exact:true}).selectOption('needs_more_evidence');
      await detail.getByLabel('人工决定理由').fill('请补实际观察🙂\n ');
      response=page.waitForResponse(r=>new URL(r.url()).pathname.endsWith('/decision')&&r.request().method()==='POST');
      await detail.getByRole('button',{name:'记录人工决定',exact:true}).click();
      const needsHttp=await response; assert.equal(needsHttp.status(),200); const needs=await needsHttp.json();
      await panel.getByLabel('成果说明原文',{exact:true}).fill('  补充🙂\n外部合成观察\t ');
      await panel.getByLabel('补充到已有成果').selectOption(first.submission.submission_id);
      await panel.getByRole('button',{name:'添加证据',exact:true}).click();
      const evidence=panel.getByRole('group',{name:'证据 1',exact:true});
      await evidence.getByLabel('证据类别').selectOption('external_report');
      await evidence.getByLabel('证据标题').fill('本机合成报告');
      await evidence.getByLabel('证据原文').fill('  成功/失败观察🙂\n非平台核验\t ');
      response=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/v1/submissions'&&r.request().method()==='POST');
      await panel.getByRole('button',{name:'保存成果与证据',exact:true}).click();
      http=await response; assert.equal(http.status(),200); const supplemented=await http.json();
      assert.equal(supplemented.submission.note,'  补充🙂\n外部合成观察\t ');
      assert.equal(supplemented.submission.evidence[0].content,'  成功/失败观察🙂\n非平台核验\t ');
      assert.equal(supplemented.submission.parent_submission_id,first.submission.submission_id);
      detail=panel.locator('.submission-detail:visible');
      await detail.getByLabel('人工决定',{exact:true}).selectOption('accepted');
      await detail.getByLabel('人工决定理由').fill('逐项人工检查🙂\n平台未执行 ');
      for (let i=0;i<supplemented.submission.task_snapshot.task.acceptance.length;i++) {
        const criterion=detail.getByRole('group',{name:'验收要求 '+(i+1),exact:true});
        await criterion.getByLabel('选择证据 1',{exact:true}).check();
        await criterion.getByLabel('实际观察',{exact:true}).fill('观察🙂\n边界'+i);
      }
      await detail.getByLabel('我理解这是人工确认，平台没有独立运行代码或核验来源').check();
      response=page.waitForResponse(r=>new URL(r.url()).pathname.endsWith('/decision')&&r.request().method()==='POST');
      await detail.getByRole('button',{name:'记录人工决定',exact:true}).click();
      http=await response; assert.equal(http.status(),200); const accepted=await http.json();
      assert.equal(accepted.task_status,'accepted');
      originals.push(needs.submission,accepted.submission);
      assert.equal((await completion()).status,index===tasks.length-1?'completed':'incomplete');
    }
    // Navigation proves the automatically refreshed in-memory projection, before reload.
    await page.evaluate(() => {location.hash='workspace';});
    await page.locator('.stage-completion').filter({hasText:'已完成'}).waitFor();
    const postsBefore=forwarded.filter(r=>r.method==='POST'&&!r.path.startsWith('/api/v1/auth/')).length;
    await page.reload();
    await page.getByRole('button',{name:'退出登录',exact:true}).click(); await authenticate();
    await page.waitForLoadState('networkidle'); await page.close(); page=await context.newPage(); await page.goto(ui+'/#workspace');
    for (const item of summaries) assert.equal((await request('/api/v1/summaries/attempts/'+item.attempt_id+q)).body.content,item.content);
    for (const item of originals) {
      const persisted=(await request('/api/v1/submissions/'+item.submission_id+q)).body;
      assert.equal(persisted.note,item.note); assert.deepEqual(persisted.task_snapshot,item.task_snapshot);
      assert.deepEqual(persisted.review,item.review);
    }
    assert.equal((await completion()).status,'completed');
    assert.equal(forwarded.filter(r=>r.method==='POST'&&!r.path.startsWith('/api/v1/auth/')).length,postsBefore);
    assert.equal(forwarded.filter(r=>r.path.endsWith('/review')&&r.method==='POST').length,0);
    // E5 uses B's ordinary browser cookie and B's valid CSRF, including A receipt replay.
    collectOwnedWrites=false;
    await page.getByRole('button',{name:'退出登录',exact:true}).click();
    const buser='隔离'+Date.now(); await authenticate(true,buser);
    const bsession=(await request('/api/v1/session')).body;
    const bq='?project_id='+bsession.project_ids[0];
    const privateReads=[receipt.status_url,'/api/v1/plans/drafts/'+run.result_ref+q,
      '/api/v1/workspace'+q,'/api/v1/summaries/history'+q,'/api/v1/submissions/history'+q,'/api/v1/outcomes'+q,
      ...summaries.map(s=>'/api/v1/summaries/attempts/'+s.attempt_id+q),
      ...originals.map(s=>'/api/v1/submissions/'+s.submission_id+q)];
    for(const url of privateReads) {
      const denied=await request(url); assert.equal(denied.status,403);
      assert.ok(!JSON.stringify(denied.body).includes('闭环私有修改标题')&&!JSON.stringify(denied.body).includes('第一版🙂'));
    }
    for(const item of summaries) assert.ok([403,404].includes((await request('/api/v1/summaries/attempts/'+item.attempt_id+bq)).status));
    for(const item of originals) assert.ok([403,404].includes((await request('/api/v1/submissions/'+item.submission_id+bq)).status));
    for(const scope of [q,bq]) assert.ok([403,404].includes((await request('/api/v1/summaries'+scope,hiddenBody)).status));
    for(const scope of [q,bq]) for(const original of ownedWrites) {
      const denied=await request(original.path+scope,original.body);
      assert.ok([403,404].includes(denied.status),JSON.stringify({path:original.path,status:denied.status}));
      assert.ok(!JSON.stringify(denied.body).includes('第一版🙂')&&!JSON.stringify(denied.body).includes('补充🙂'));
    }
    assert.ok(!(await page.locator('body').innerText()).includes('第一版🙂'));
    await page.getByRole('button',{name:'退出登录',exact:true}).click(); await authenticate();
    assert.equal((await completion()).status,'completed');
    await page.waitForLoadState('networkidle');
    assert.deepEqual(errors,[]);
    const directory=path.resolve(__dirname,'../../var/current-learning-loop'); fs.mkdirSync(directory,{recursive:true});
    await page.screenshot({path:path.join(directory,'current-loop.png')});
    fs.writeFileSync(path.join(directory,'browser-pg.json'),JSON.stringify({status:'PASS',model:'Fake',requested_agent_model:'gpt-6.1-sol/medium',actual_agent_model:'NOT OBSERVABLE',plan_id:plan.plan_id,plan_version:plan.version,run_id:receipt.run_id,
      summaries:summaries.map(s=>({attempt_id:s.attempt_id,content_sha256:hash(s.content),rubric_snapshot:s.rubric_snapshot})),
      submissions:originals.map(s=>({submission_id:s.submission_id,note_sha256:hash(s.note),evidence_sha256:s.evidence.map(e=>hash(e.content)),task_snapshot:s.task_snapshot,review:s.review})),forwarded},null,2));
    console.log('PASS: current ordinary browser loop E1/E3/E4/E5 with real writes and Fake generation; controlled E2 separately PG');
  } catch(error) {
    console.error('LAST_HTTP',JSON.stringify(forwarded.slice(-12)));
    for(const p of context.pages()) console.error('PAGE_BODY',await p.locator('body').innerText());
    throw error;
  } finally {await context.unrouteAll({behavior:'wait'});await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
