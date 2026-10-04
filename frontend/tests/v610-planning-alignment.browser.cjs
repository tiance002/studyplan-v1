// Actual owned HTTP/PG/Fake only: ordinary UI auth, generation and synthetic confirmation.
const { chromium } = require('playwright-core');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const scenarios = [
  { name: 'system', target: '零基础系统学习 Agent 应用开发，先做一个最小应用。', key: 'agent.application', startingPoint: '零基础，尚未实现 Agent。' },
  { name: 'mcp', target: '我只想学 MCP；已经会基础 Tool 调用。', key: 'agent.application', startingPoint: '已经会基础 Tool 调用。' },
  { name: 'node', target: '我已有一个 Node.js API，希望学习部署、监控、自动发布和恢复。', key: 'cloud.services', startingPoint: '已有 Node.js API，熟悉 JavaScript 与 HTTP。' },
];

(async () => {
  const api = process.env.STUDYPLAN_V610_API || 'http://127.0.0.1:8029';
  const ui = process.env.STUDYPLAN_URL || 'http://127.0.0.1:5189';
  // Pin both endpoints to the explicitly assigned owned servers.
  assert.equal(new URL(api).origin, 'http://127.0.0.1:8029');
  assert.equal(new URL(ui).origin, 'http://127.0.0.1:5189');
  const directory = path.resolve(__dirname, '../../var/v610');
  fs.mkdirSync(directory, { recursive: true });
  const evidence = [], errors = [], blockedExternal = [], navigationAborts = [];
  const started = Date.now();
  let browser, active = null, failed = null, currentPage;
  const log = message => {
    console.log(message);
    fs.appendFileSync(path.join(directory, 'alignment-browser.log'), new Date().toISOString() + ' ' + message + '\n');
  };
  fs.writeFileSync(path.join(directory, 'alignment-browser.log'), 'v6.10 owned PG / Fake / Edge; no mocked API responses\n');
  const deadline = setTimeout(() => {
    failed = { status: 'FAIL', scenario: active, message: '220-second suite limit approached (215-second deadline)' };
    browser?.close().catch(() => {});
  }, 215000);
  try {
    browser = await chromium.launch({ channel: 'msedge', headless: true });
    for (const [index, scenario] of scenarios.entries()) {
      active = scenario.name;
      const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
      const page = currentPage = await context.newPage();
      page.setDefaultTimeout(12000);
      page.setDefaultNavigationTimeout(20000);
      page.on('pageerror', error => errors.push({ scenario: active, message: error.message }));
      const calls = [];
      await context.route('**/*', async route => {
        const request = route.request(), url = new URL(request.url());
        if (!['127.0.0.1', 'localhost'].includes(url.hostname)) {
          blockedExternal.push({ scenario: active, origin: url.origin });
          return route.abort('blockedbyclient');
        }
        if (!url.pathname.startsWith('/api/v1/') && url.pathname !== '/healthz') return route.continue();
        try {
          // A real HTTP relay preserves the ordinary cookie and CSRF flow.
          const response = await route.fetch({ url: api + url.pathname + url.search, timeout: 35000, maxRetries: 0 });
          calls.push({ method: request.method(), path: url.pathname, status: response.status(),
            csrf_present: !!request.headers()['x-csrf-token'] });
          await route.fulfill({ response });
        } catch (error) {
          if (request.method() === 'GET' && /Route is already handled|Request context disposed|Target.*closed/.test(error.message)) {
            navigationAborts.push({ scenario: active, path: url.pathname });
            return;
          }
          errors.push({ scenario: active, message: 'HTTP relay: ' + error.message });
          await route.abort().catch(() => {});
        }
      });
      const username = '对齐验收' + Date.now().toString(36) + index, password = 'Test-pass1!';
      const authenticate = async register => {
        if (register) await page.getByRole('button', { name: '注册', exact: true }).click();
        await page.getByLabel('用户名', { exact: true }).fill(username);
        await page.getByLabel('密码', { exact: true }).fill(password);
        const response = page.waitForResponse(r => new URL(r.url()).pathname === '/api/v1/auth/' + (register ? 'register' : 'login'));
        await page.getByRole('button', { name: register ? '注册并进入' : '登录学习空间', exact: true }).click();
        assert.equal((await response).status(), 200);
        await page.getByRole('button', { name: '退出登录', exact: true }).waitFor();
      };
      const read = endpoint => page.evaluate(async endpoint => {
        const response = await fetch('/api/v1/session', { credentials: 'include' });
        if (!response.ok) throw new Error('ordinary session missing: ' + response.status);
        const session = await response.json();
        if (!session.project_ids?.[0]) throw new Error('session has no project');
        const data = await fetch(endpoint + '?project_id=' + encodeURIComponent(session.project_ids[0]), { credentials: 'include' });
        if (!data.ok) throw new Error('owned read failed: ' + data.status);
        return data.json();
      }, endpoint);

      await page.goto(ui + '/#planning');
      await authenticate(true);
      const health = await page.evaluate(async () => (await fetch('/healthz')).json());
      assert.equal(health.llm_provider, 'fake', 'owned server must use Fake before generation');
      assert.equal(health.repository_backend, 'postgres');
      // The wrapped label contains the textarea's initial text in Edge's
      // accessible label. Use the stable question prefix as older real harnesses do.
      await page.getByLabel('你想学会什么？').fill(scenario.target);
      await page.getByText('补充目标与起点（可选）', { exact: true }).click();
      await page.getByLabel('当前起点', { exact: true }).fill(scenario.startingPoint);
      const generation = page.waitForResponse(r => r.request().method() === 'POST' && new URL(r.url()).pathname === '/api/v1/plans/generate', { timeout: 40000 });
      await page.getByRole('button', { name: '生成学习草案 →', exact: true }).click();
      const generated = await generation;
      assert.equal(generated.status(), 202);
      const generationBody = await generated.json();
      await page.getByLabel('阶段 1 标题', { exact: true }).waitFor({ timeout: 35000 });
      assert.ok((await page.getByRole('region', { name: '草案目标快照', exact: true }).innerText()).includes(scenario.target));
      if (scenario.name === 'mcp') assert.equal(await page.locator('.draft-stage').count(), 4);
      if (scenario.name === 'node') {
        assert.ok((await page.locator('body').innerText()).includes('Node.js API'));
        const draftGap = page.getByRole('region', { name: '资料缺口', exact: true });
        await draftGap.first().waitFor();
        const gapText = (await draftGap.allInnerTexts()).join('\n');
        assert.ok(gapText.includes('通用本地演练与待选范围') && gapText.includes('needs_research_or_review'));
      }
      await page.screenshot({ path: path.join(directory, scenario.name + '-draft-edge.png'), fullPage: true });
      const decision = page.waitForResponse(r => r.request().method() === 'POST' && new URL(r.url()).pathname.endsWith('/decision') && r.request().postDataJSON()?.decision === 'approve');
      await page.getByRole('button', { name: '确认并发布路线', exact: true }).click();
      const approved = await decision;
      assert.equal(approved.status(), 200);
      const plan = (await approved.json()).plan;
      assert.equal(plan.goal_spec.target, scenario.target);
      assert.equal(plan.source_pack_key, scenario.key);
      assert.equal(plan.source_pack_version, scenario.name === 'node' ? 3 : 6);
      await page.goto(ui + '/#workspace');
      await page.locator('.stage-trigger').first().waitFor();
      const workspace = await read('/api/v1/workspace');
      assert.equal(workspace.plan.plan_id, plan.plan_id);
      const tasks = workspace.stages.flatMap(stage => stage.tasks);
      assert.ok(tasks.length > 0 && tasks.every(task => task.acceptance.length > 0));
      const checks = {};
      if (scenario.name === 'system') {
        const reference = workspace.stages.find(stage => /\.a8$/.test(stage.stage.stable_key));
        assert.ok(reference, 'full Agent route retains real engineering study stage A8');
        assert.ok(reference.nodes.length > 0, 'A8 contains consumable knowledge');
        assert.ok(plan.stages.length > 6, 'full route does not stop at old six-stage representative');
        await page.locator('.stage-trigger').filter({ hasText: reference.stage.title }).click();
        const card = page.getByRole('region', { name: '项目源码学习', exact: true }).filter({ hasText: 'Pi 轻量 Runtime' });
        await card.waitFor();
        const prompt = await card.getByLabel('源码学习 Prompt', { exact: true }).inputValue();
        assert.ok(prompt.includes('whole_core') && prompt.includes('预期产物') && prompt.includes('迁移候选'));
        assert.ok(prompt.includes('不代表已掌握'));
        assert.ok((await card.getByRole('link').getAttribute('href')).startsWith('https://github.com/'));
        await card.screenshot({ path: path.join(directory, 'system-pi-card-edge.png') });
        checks.reference_stage = reference.stage.stable_key;
        checks.reference_knowledge_count = reference.nodes.length;
        checks.study_mode = 'whole_core';
        await context.grantPermissions(['clipboard-read', 'clipboard-write']);
        await card.getByRole('button', { name: '复制给 AI', exact: true }).click();
        await card.getByText('已复制，可粘贴给外部 AI。', { exact: true }).waitFor();
        assert.equal((await page.evaluate(() => navigator.clipboard.readText())).replace(/\r\n/g, '\n'), prompt);
        checks.clipboard = 'PASS';
      } else if (scenario.name === 'mcp') {
        assert.deepEqual(plan.stages.map(stage => stage.stable_key.split('.').at(-1)).sort(), ['a0', 'a1', 'a2', 'a6']);
        assert.ok(!plan.extensions.some(item => item.topic.includes('Pi')));
        assert.ok(!plan.stages.some(stage => /\.a8$/.test(stage.stable_key)));
        checks.narrow_scope = 'A0/A1/A2/A6 only';
      } else {
        assert.ok(!plan.stages.some(stage => /\.sm1$/.test(stage.stable_key)));
        const carrierTasks = tasks.filter(task => task.goal.includes('Node.js API'));
        const microTasks = tasks.filter(task => task.goal.includes('独立 Micro Exercise'));
        assert.ok(carrierTasks.length > 0 && microTasks.length > 0, 'actual task goals identify carrier and independent experiments');
        assert.ok(tasks.every(task => task.goal.includes('Node.js API') || task.goal.includes('独立 Micro Exercise')));
        assert.ok(tasks.every(task => !task.goal.includes('Task Service')));
        const gap = plan.extensions.find(item => item.topic.includes('通用本地演练与待选范围')
          && item.guidance.includes('needs_research_or_review'));
        assert.ok(gap, 'cloud research gap remains explicit');
        const stage = workspace.stages.find(item => item.stage.stage_id === gap.stage_id);
        assert.ok(stage);
        await page.locator('.stage-trigger').filter({ hasText: stage.stage.title }).click();
        const gapContent = page.getByRole('region', { name: '对比与思考提示', exact: true }).filter({ hasText: gap.topic });
        await gapContent.waitFor();
        assert.ok((await gapContent.innerText()).includes('needs_research_or_review'));
        checks.carrier_task_count = carrierTasks.length;
        checks.micro_exercise_count = microTasks.length;
        checks.research_gap = gap.topic;
      }
      await page.screenshot({ path: path.join(directory, scenario.name + '-workspace-edge.png'), fullPage: true });
      const generationCount = calls.filter(call => call.method === 'POST' && call.path === '/api/v1/plans/generate').length;
      assert.equal(generationCount, 1);
      await page.reload();
      await page.getByRole('button', { name: '退出登录', exact: true }).waitFor();
      assert.deepEqual(await read('/api/v1/plans/current'), plan);
      assert.deepEqual(await read('/api/v1/workspace'), workspace);
      await page.getByRole('button', { name: '退出登录', exact: true }).click();
      await authenticate(false);
      assert.deepEqual(await read('/api/v1/plans/current'), plan);
      assert.deepEqual(await read('/api/v1/workspace'), workspace);
      assert.equal(calls.filter(call => call.method === 'POST' && call.path === '/api/v1/plans/generate').length, generationCount);
      for (const call of calls.filter(call => call.method === 'POST' && /plans\/generate|\/decision$|auth\/logout/.test(call.path))) {
        assert.ok(call.csrf_present, call.path + ' ordinary UI CSRF header');
        assert.ok(call.status < 400, call.path + ' success');
      }
      await page.screenshot({ path: path.join(directory, scenario.name + '-relogin-edge.png'), fullPage: true });
      evidence.push({ status: 'PASS', scenario: scenario.name, target: scenario.target, plan_id: plan.plan_id,
        generation: generationBody, stage_count: plan.stages.length, task_count: tasks.length,
        pack_version: plan.source_pack_version, checks, calls, provider: 'Fake', database: 'owned PostgreSQL',
        refresh: 'PASS', relogin: 'PASS', extra_generation_requests: 0 });
      fs.writeFileSync(path.join(directory, scenario.name + '-browser-plan.json'), JSON.stringify({ plan, workspace }, null, 2));
      log('PASS Edge ordinary UI scenario: ' + scenario.name);
      await context.unrouteAll({ behavior: 'ignoreErrors' });
      await context.close();
    }
    assert.deepEqual(errors, []);
    assert.deepEqual(blockedExternal, [], 'UI must not attempt external network during consumption');
    log('PASS v6.10 Edge system Agent / narrow MCP / Node API ordinary UI acceptance');
  } catch (error) {
    failed = failed || { status: 'FAIL', scenario: active, message: error.message, stack: error.stack };
    if (currentPage && !currentPage.isClosed()) await currentPage.screenshot({ path: path.join(directory, 'failure-edge.png'), fullPage: true }).catch(() => {});
    log('FAIL ' + active + ': ' + error.message);
    throw error;
  } finally {
    clearTimeout(deadline);
    if (browser) {
      await Promise.all(browser.contexts().map(context => context.unrouteAll({ behavior: 'ignoreErrors' }).catch(() => {})));
      await browser.close().catch(() => {});
    }
    fs.writeFileSync(path.join(directory, 'alignment-browser.json'), JSON.stringify({ status: failed ? 'FAIL' : 'PASS',
      evidence, failed, errors, blockedExternal, navigationAborts, elapsed_ms: Date.now() - started,
      scope: 'owned PostgreSQL + Fake + actual HTTP + Edge; no API mocks',
      not_run: scenarios.filter(scenario => !evidence.some(item => item.scenario === scenario.name)).map(scenario => scenario.name) }, null, 2));
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
