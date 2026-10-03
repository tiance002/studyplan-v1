// Three concrete goals through the normal UI and an owned real HTTP/PG server.
const {chromium} = require('playwright-core');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

(async () => {
  const api = process.env.STUDYPLAN_DIRECTION_API;
  assert.equal(new URL(api).hostname, '127.0.0.1');
  const ui = process.env.STUDYPLAN_URL || 'http://127.0.0.1:5178';
  const browser = await chromium.launch({channel:'chrome',headless:true});
  const evidence = [], errors = [];
  try {
    for (const [index,target,special,fragment] of [
      [0,'Knowledge / RAG Agent','stage.rag','片段'],
      [1,'Coding Agent','stage.coding_workspace','白名单'],
      [2,'Workflow / Automation Agent','stage.workflow_effects','业务键'],
    ]) {
      const context = await browser.newContext();
      const page = await context.newPage();
      page.setDefaultTimeout(15000);
      page.on('pageerror', e => errors.push(e.message));
      const calls = [];
      await context.route('**/*', async route => {
        const request = route.request(), url = new URL(request.url());
        if (!['127.0.0.1','localhost'].includes(url.hostname)) return route.abort('blockedbyclient');
        if (!url.pathname.startsWith('/api/v1/') && url.pathname !== '/healthz') return route.continue();
        const response = await route.fetch({url:api+url.pathname+url.search});
        calls.push({method:request.method(),path:url.pathname,status:response.status()});
        return route.fulfill({response});
      });
      const username = '方向浏览器' + Date.now() + index, password = 'Test-pass1!';
      async function auth(register) {
        if (register) await page.getByRole('button',{name:'注册',exact:true}).click();
        await page.getByLabel('用户名',{exact:true}).fill(username);
        await page.getByLabel('密码',{exact:true}).fill(password);
        await page.getByRole('button',{name:register?'注册并进入':'登录学习空间',exact:true}).click();
        await page.getByRole('button',{name:'退出登录',exact:true}).waitFor();
      }
      const read = async endpoint => page.evaluate(async endpoint => {
        const sessionResponse = await fetch('/api/v1/session');
        if (!sessionResponse.ok) throw new Error('normal session missing');
        const session = await sessionResponse.json();
        const response = await fetch(endpoint+'?project_id='+encodeURIComponent(session.project_ids[0]));
        if (!response.ok) throw new Error('read status '+response.status);
        return response.json();
      },endpoint);
      await page.goto(ui+'/#planning');
      await auth(true);
      await page.getByLabel('你想学会什么？').fill(target);
      await page.getByText('补充目标与起点（可选）',{exact:true}).click();
      await page.getByLabel('当前起点',{exact:true}).fill('有基础编程认知；Agent 初学者');
      const generated = page.waitForResponse(r => r.request().method()==='POST' && new URL(r.url()).pathname==='/api/v1/plans/generate');
      await page.getByRole('button',{name:'生成学习草案 →',exact:true}).click();
      assert.equal((await generated).status(),202);
      await page.getByLabel('阶段 1 标题',{exact:true}).waitFor();
      const snapshot = page.getByRole('region',{name:'草案目标快照',exact:true});
      assert.ok((await snapshot.innerText()).includes(target));
      const approval = page.waitForResponse(r => r.request().method()==='POST' && new URL(r.url()).pathname.endsWith('/decision') && r.request().postDataJSON().decision==='approve');
      await page.getByRole('button',{name:'确认并发布路线',exact:true}).click();
      const approved = await approval;
      assert.equal(approved.status(),200);
      const plan = (await approved.json()).plan;
      assert.equal(plan.stages.length,10);
      assert.equal(plan.goal_spec.target,target);
      assert.ok(plan.stages.some(s=>s.stable_key===special));
      assert.equal(plan.stages.some(s=>s.stable_key==='stage.rag'), index===0);
      assert.ok(!plan.stages.some(s=>s.stable_key==='stage.mcp'));
      await page.goto(ui+'/#workspace');
      await page.locator('.stage-trigger').first().waitFor();
      const stage = plan.stages.find(s=>s.stable_key===special);
      await page.locator('.stage-trigger').filter({hasText:stage.title}).click();
      const guide = page.getByRole('region',{name:'学习指导',exact:true});
      await guide.locator('summary').click();
      assert.ok((await guide.innerText()).includes(fragment));
      const before = calls.filter(c=>c.method==='POST' && c.path==='/api/v1/plans/generate').length;
      assert.equal(before,1);
      await page.reload();
      await page.getByRole('button',{name:'退出登录',exact:true}).waitFor();
      assert.equal((await read('/api/v1/plans/current')).plan_id,plan.plan_id);
      await page.getByRole('button',{name:'退出登录',exact:true}).click();
      await auth(false);
      assert.equal((await read('/api/v1/plans/current')).plan_id,plan.plan_id);
      assert.equal(calls.filter(c=>c.method==='POST' && c.path==='/api/v1/plans/generate').length,before);
      await page.goto(ui+'/#workspace');
      await page.locator('.stage-trigger').first().waitFor();
      await page.setViewportSize({width:390,height:844});
      await page.locator('.stage-trigger').filter({hasText:stage.title}).click();
      await guide.locator('summary').click();
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
      const dir = path.resolve(__dirname,'../../var/oct6-guidance');
      fs.mkdirSync(dir,{recursive:true});
      await page.screenshot({path:path.join(dir,'direction-'+index+'-real-pg.png'),fullPage:true});
      evidence.push({target,special,plan_id:plan.plan_id,model:'Fake',database:'real owned PG',calls});
      await context.close();
    }
    assert.deepEqual(errors,[]);
    fs.writeFileSync(path.resolve(__dirname,'../../var/oct6-guidance/direction-browser.json'),JSON.stringify({status:'PASS',evidence},null,2));
    console.log('PASS: three concrete goals, normal registration/generation/approval, scoped guidance, refresh/relogin, mobile; model Fake');
  } finally { await browser.close(); }
})().catch(error=>{console.error(error);process.exitCode=1;});
