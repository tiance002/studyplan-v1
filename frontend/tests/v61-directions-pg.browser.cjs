// Three concrete goals through the normal UI and an owned real HTTP/PG server.
const {chromium} = require('playwright-core');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

(async () => {
  const api = process.env.STUDYPLAN_V61_API;
  assert.equal(new URL(api).hostname, '127.0.0.1');
  const ui = process.env.STUDYPLAN_URL || 'http://127.0.0.1:5178';
  const browser = await chromium.launch({channel:'chrome',headless:true});
  const evidence = [], errors = [];
  try {
    for (const [index,target,special,fragment] of [
      [0,'零基础系统学 Agent，后面重点 RAG。','stage.runtime_repo','LangGraph'],
      [1,'做 AI 资料工作台。','stage.repo','FastAPI'],
      [2,'学习云服务，能开发、部署和运维 API。','stage.repo','Azure'],
    ]) {
      const context = await browser.newContext({permissions:['clipboard-read','clipboard-write']});
      const page = await context.newPage();
      page.setDefaultTimeout(15000);
      page.on('pageerror', e => errors.push(e.message));
      const calls = [];
      const navigationAborts = [];
      await context.route('**/*', async route => {
        const request = route.request(), url = new URL(request.url());
        if (!['127.0.0.1','localhost'].includes(url.hostname)) return route.abort('blockedbyclient');
        if (!url.pathname.startsWith('/api/v1/') && url.pathname !== '/healthz') return route.continue();
        try {
          const response = await route.fetch({url:api+url.pathname+url.search});
          calls.push({method:request.method(),path:url.pathname,status:response.status()});
          return await route.fulfill({response});
        } catch (error) {
          // Navigation can cancel ancillary GETs after their real response.
          // Never suppress a mutation or an HTTP/business error.
          if (request.method()==='GET' && /Route is already handled|Request context disposed/.test(error.message)) {
            navigationAborts.push({method:'GET',path:url.pathname,reason:error.message.split('\n')[0]});
            return;
          }
          throw error;
        }
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
      console.log('CHECK generated',index);
      const snapshot = page.getByRole('region',{name:'草案目标快照',exact:true});
      assert.ok((await snapshot.innerText()).includes(target));
      assert.equal(await page.getByRole('region',{name:'学习指导',exact:true}).count(),[5,4,8][index]);
      assert.equal(await page.getByLabel('项目学习安排',{exact:true}).count(),1);
      const approval = page.waitForResponse(r => r.request().method()==='POST' && new URL(r.url()).pathname.endsWith('/decision') && r.request().postDataJSON().decision==='approve');
      await page.getByRole('button',{name:'确认并发布路线',exact:true}).click();
      const approved = await approval;
      assert.equal(approved.status(),200);
      const plan = (await approved.json()).plan;
      assert.equal(plan.stages.length,[5,4,8][index]);
      assert.equal(plan.goal_spec.target,target);
      assert.ok(plan.stages.some(s=>s.stable_key===special));
      assert.equal(plan.source_pack_key,['agent.application','ai.fullstack','cloud.services'][index]);
      assert.ok(!plan.stages.some(s=>s.stable_key==='stage.mcp'));
      await page.goto(ui+'/#workspace');
      await page.locator('.stage-trigger').first().waitFor();
      const stage = plan.stages.find(s=>s.stable_key===special);
      await page.locator('.stage-trigger').filter({hasText:stage.title}).click();
      const card = page.getByRole('region',{name:'项目源码学习',exact:true});
      await card.waitFor();
      console.log('CHECK card',index);
      assert.ok((await card.innerText()).includes(fragment));
      const prompt = await card.getByLabel('源码学习 Prompt',{exact:true}).inputValue();
      assert.ok(prompt.includes('clone') && prompt.includes('3–8') && prompt.includes('1–2'));
      for (const label of ['REVIEW','COMPARE','DEEPEN','VERSION_CONTEXT','NEW','源码事实','工程解释','未核实推断']) assert.ok(prompt.includes(label));
      assert.ok(!/github\.com\/[^\s/]+\/[^\s/]+\/(?:blob|tree)\//.test(prompt));
      assert.equal(await card.getByRole('link').count(),1);
      await card.getByRole('button',{name:'复制给 AI',exact:true}).click();
      await card.getByRole('status').filter({hasText:'已复制'}).waitFor();
      // Windows clipboard normalizes LF to CRLF; preserve all other characters.
      const copied = await page.evaluate(()=>navigator.clipboard.readText());
      assert.equal(copied.replace(/\r\n/g,'\n'),prompt);
      console.log('CHECK copied',index);
      const before = calls.filter(c=>c.method==='POST' && c.path==='/api/v1/plans/generate').length;
      assert.equal(before,1);
      await page.reload();
      await page.getByRole('button',{name:'退出登录',exact:true}).waitFor();
      assert.equal((await read('/api/v1/plans/current')).plan_id,plan.plan_id);
      await page.getByRole('button',{name:'退出登录',exact:true}).click();
      await auth(false);
      assert.equal((await read('/api/v1/plans/current')).plan_id,plan.plan_id);
      assert.equal(calls.filter(c=>c.method==='POST' && c.path==='/api/v1/plans/generate').length,before);
      await page.setViewportSize({width:390,height:844});
      await page.goto(ui+'/#path');
      await page.locator('.timeline-stage').nth(stage.order_index).getByRole('button',{name:'进入学习 →',exact:true}).click();
      await card.waitFor();
      assert.equal(await card.getByLabel('源码学习 Prompt',{exact:true}).inputValue(),prompt);
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
      console.log('CHECK restored/mobile',index);
      const dir = path.resolve(__dirname,'../../var/oct6-guidance');
      fs.mkdirSync(dir,{recursive:true});
      await card.screenshot({path:path.join(dir,'v61-direction-'+index+'-real-pg.png')});
      evidence.push({target,special,plan_id:plan.plan_id,model:'Fake',database:'real owned PG',calls,navigationAborts});
      await context.unrouteAll({behavior:'ignoreErrors'});
      await context.close();
    }
    assert.deepEqual(errors,[]);
    fs.writeFileSync(path.resolve(__dirname,'../../var/oct6-guidance/v61-direction-browser.json'),JSON.stringify({status:'PASS',evidence},null,2));
    console.log('PASS: v6.1 three representative goals, normal registration/generation/approval, scoped guidance, refresh/relogin, mobile; model Fake');
  } catch (error) {
    console.error('FAILED CHECK:',error.message);
    throw error;
  } finally {
    await Promise.all(browser.contexts().map(context=>context.unrouteAll({behavior:'ignoreErrors'})));
    await browser.close();
  }
})().catch(error=>{console.error(error);process.exitCode=1;});
