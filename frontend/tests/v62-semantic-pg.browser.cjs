// v6.2: six semantic scenarios, normal UI submission/confirmation, owned API/PG/Fake.
const {chromium} = require('playwright-core');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const scenarios = [
  {name:'travel',target:'我已经有一个旅行规划 Agent，希望系统补 Agent 基础，并强化网页信息获取、可恢复规划和知识检索。',key:'agent.application',carrier:'旅行规划 Agent',recipes:['browser','workflow','rag']},
  {name:'starter',target:'我没有项目想法，想系统学习 Agent 应用开发。',key:'agent.application',carrier:'研究与行动助手',recipes:[]},
  {name:'voice',target:'我想学语音 Agent。',key:'agent.application',carrier:'研究与行动助手',recipes:[]},
  {name:'commerce',target:'我已经有一个电商后台，想把它改造成带 AI 商品文案与客服能力的全栈应用。',key:'ai.fullstack',carrier:'电商后台',recipes:[]},
  {name:'node',target:'我已经有一个 Node.js API，想学习如何部署、监控、自动发布和恢复。',key:'cloud.services',carrier:'Node.js API',recipes:[]},
  {name:'knowledge',target:'我已经有一个自己的知识库项目，想学习 RAG 检索增强与证据回答 Agent。',key:'agent.application',carrier:'自己的知识库项目',recipes:['rag']},
];

(async () => {
  const api = process.env.STUDYPLAN_V62_API;
  assert.equal(new URL(api).hostname,'127.0.0.1');
  const ui = process.env.STUDYPLAN_URL || 'http://127.0.0.1:5178';
  const dir = path.resolve(__dirname,'../../var/v62');
  fs.mkdirSync(dir,{recursive:true});
  const browser = await chromium.launch({channel:'chrome',headless:true});
  const evidence = [], errors = [], cleanup = [];
  let active = null, failed = null;
  try {
    for (const [index,scenario] of scenarios.entries()) {
      active = scenario.name;
      const context = await browser.newContext();
      const page = await context.newPage();
      page.setDefaultTimeout(20000);
      page.on('pageerror',e => errors.push({scenario:scenario.name,message:e.message}));
      const calls = [], navigationAborts = [];
      await context.route('**/*',async route => {
        const request = route.request(), url = new URL(request.url());
        if (!['127.0.0.1','localhost'].includes(url.hostname)) return route.abort('blockedbyclient');
        if (!url.pathname.startsWith('/api/v1/') && url.pathname !== '/healthz') return route.continue();
        try {
          const response = await route.fetch({url:api+url.pathname+url.search});
          calls.push({method:request.method(),path:url.pathname,status:response.status()});
          return await route.fulfill({response});
        } catch (error) {
          if (request.method()==='GET' && /Route is already handled|Request context disposed/.test(error.message)) {
            navigationAborts.push({path:url.pathname,reason:error.message.split('\n')[0]});
            return;
          }
          throw error;
        }
      });
      const username = '语义浏览器'+Date.now()+index, password = 'Test-pass1!';
      async function auth(register) {
        if (register) await page.getByRole('button',{name:'注册',exact:true}).click();
        await page.getByLabel('用户名',{exact:true}).fill(username);
        await page.getByLabel('密码',{exact:true}).fill(password);
        await page.getByRole('button',{name:register?'注册并进入':'登录学习空间',exact:true}).click();
        await page.getByRole('button',{name:'退出登录',exact:true}).waitFor();
      }
      const read = async endpoint => page.evaluate(async endpoint => {
        const sessionResponse = await fetch('/api/v1/session');
        if (!sessionResponse.ok) throw new Error('normal cookie session missing');
        const session = await sessionResponse.json();
        const response = await fetch(endpoint+'?project_id='+encodeURIComponent(session.project_ids[0]));
        if (!response.ok) throw new Error('read status '+response.status);
        return response.json();
      },endpoint);
      await page.goto(ui+'/#planning');
      await auth(true);
      await page.getByLabel('你想学会什么？').fill(scenario.target);
      await page.getByText('补充目标与起点（可选）',{exact:true}).click();
      await page.getByLabel('当前起点',{exact:true}).fill('有基础编程认知；初学者');
      const generated = page.waitForResponse(r => r.request().method()==='POST' && new URL(r.url()).pathname==='/api/v1/plans/generate');
      await page.getByRole('button',{name:'生成学习草案 →',exact:true}).click();
      assert.equal((await generated).status(),202);
      await page.getByLabel('阶段 1 标题',{exact:true}).waitFor();
      const body = await page.locator('body').innerText();
      assert.ok(body.includes(scenario.carrier),scenario.name+' visible carrier');
      const composition = page.getByRole('region',{name:'项目与可组合专项',exact:true});
      await composition.waitFor();
      const compositionText = await composition.innerText();
      for (const recipe of scenario.recipes) assert.ok(compositionText.includes(recipe),scenario.name+' recipe '+recipe);
      assert.ok(compositionText.includes('Evaluation') && compositionText.includes('可组合'));
      assert.ok(!compositionText.includes('agentic_rl'));
      if (scenario.name==='starter') assert.ok(compositionText.includes('默认项目候选（可替换）'));
      else if (!['voice'].includes(scenario.name)) assert.ok(compositionText.includes('用户项目：'));
      if (scenario.name==='voice') {
        const gap = page.getByRole('region',{name:'资料缺口',exact:true});
        await gap.waitFor();
        assert.ok((await gap.innerText()).includes('needs_research_or_review'));
        assert.ok((await gap.innerText()).includes('语音'));
      }
      await page.screenshot({path:path.join(dir,scenario.name+'-draft.png'),fullPage:true});
      const approval = page.waitForResponse(r => r.request().method()==='POST' && new URL(r.url()).pathname.endsWith('/decision') && r.request().postDataJSON().decision==='approve');
      await page.getByRole('button',{name:'确认并发布路线',exact:true}).click();
      const approved = await approval;
      assert.equal(approved.status(),200);
      const plan = (await approved.json()).plan;
      assert.equal(plan.goal_spec.target,scenario.target);
      assert.equal(plan.source_pack_key,scenario.key);
      assert.ok(plan.source_pack_version>{'agent.application':4,'ai.fullstack':1,'cloud.services':1}[scenario.key]);
      for (const stage of plan.stages) assert.ok(stage.learning_guidance.practice_delta.baseline.includes(scenario.carrier));
      const candidates = plan.extensions.filter(e => e.topic.startsWith('项目学习：'));
      assert.ok(candidates.every(e => !e.required && e.guidance.includes('可选') && e.guidance.includes('替换')));
      if (scenario.name==='node') assert.ok(!plan.stages.some(s => /FastAPI|Task Service/.test(s.title)));
      if (scenario.name==='knowledge') assert.ok(candidates.some(e => /RAGFlow|WeKnora/.test(e.topic)));
      await page.goto(ui+'/#workspace');
      await page.locator('.stage-trigger').first().waitFor();
      const workspace = await read('/api/v1/workspace');
      const tasks = workspace.stages.flatMap(s=>s.tasks);
      assert.ok(tasks.length && tasks.every(t=>t.goal.includes(scenario.carrier)),scenario.name+' task carrier');
      if (scenario.name==='knowledge') {
        const candidate = candidates.find(e=>/RAGFlow|WeKnora/.test(e.topic));
        const stage = plan.stages.find(s=>s.stage_id===candidate.stage_id);
        await page.locator('.stage-trigger').filter({hasText:stage.title}).click();
        const card = page.getByRole('region',{name:'项目源码学习',exact:true});
        await card.waitFor();
        const text = await card.innerText();
        assert.ok(text.includes('项目案例（可选）') && text.includes('替换'));
        const prompt = await card.getByLabel('源码学习 Prompt',{exact:true}).inputValue();
        assert.ok(prompt.includes(scenario.carrier));
        assert.ok(!/github\.com\/[^\s/]+\/[^\s/]+\/(?:blob|tree)\//.test(prompt));
        await card.screenshot({path:path.join(dir,'knowledge-optional-card.png')});
      }
      const before = calls.filter(c=>c.method==='POST' && c.path==='/api/v1/plans/generate').length;
      assert.equal(before,1);
      await page.reload();
      await page.getByRole('button',{name:'退出登录',exact:true}).waitFor();
      assert.deepEqual(await read('/api/v1/plans/current'),plan);
      await page.getByRole('button',{name:'退出登录',exact:true}).click();
      await auth(false);
      assert.deepEqual(await read('/api/v1/plans/current'),plan);
      assert.equal(calls.filter(c=>c.method==='POST' && c.path==='/api/v1/plans/generate').length,before);
      await page.screenshot({path:path.join(dir,scenario.name+'-relogin.png'),fullPage:true});
      evidence.push({status:'PASS',...scenario,plan_id:plan.plan_id,pack_version:plan.source_pack_version,stage_count:plan.stages.length,model:'Fake',database:'owned real PG',calls,navigationAborts});
      console.log('PASS semantic scenario:',scenario.name);
      await context.unrouteAll({behavior:'ignoreErrors'});
      await context.close();
      cleanup.push({scenario:scenario.name,status:'PASS'});
    }
    assert.deepEqual(errors,[]);
  } catch (error) {
    failed = {scenario:active,status:'FAIL',message:error.message,stack:error.stack};
    throw error;
  } finally {
    await Promise.all(browser.contexts().map(async context => {
      await context.unrouteAll({behavior:'ignoreErrors'});
      await context.close();
      cleanup.push({scenario:active,status:'PASS',kind:'final cleanup'});
    }));
    await browser.close();
    fs.writeFileSync(path.join(dir,'semantic-browser.json'),JSON.stringify({status:failed?'FAIL':'PASS',evidence,failed,errors,cleanup,not_run:scenarios.filter(s=>!evidence.some(e=>e.name===s.name)&&s.name!==active).map(s=>s.name)},null,2));
  }
})().catch(error=>{console.error(error);process.exitCode=1;});
