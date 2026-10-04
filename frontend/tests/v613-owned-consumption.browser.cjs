// Actual API + owned PG + Edge; input Plans are Fake-generated/confirmed, never mocked here.
const { chromium } = require('playwright-core');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

(async () => {
  assert.equal(process.env.STUDYPLAN_V613_EDGE_READY, '1', 'Fresh F1-F4 and PG execution gate required');
  const directory = path.resolve(__dirname, '../../var/v613');
  const evidence = path.join(directory, 'edge');
  fs.mkdirSync(evidence, { recursive: true });
  const scenarios = ['rag', 'system', 'mcp', 'node', 'long'];
  const inputs = scenarios.map(scenario => ({ scenario,
    credentials: JSON.parse(fs.readFileSync(path.join(directory, `private/fake-${scenario}.json`), 'utf8')),
    plan: JSON.parse(fs.readFileSync(path.join(directory, `pg/plan-${scenario}.json`), 'utf8')),
    workspace: JSON.parse(fs.readFileSync(path.join(directory, `pg/workspace-${scenario}.json`), 'utf8')),
  }));
  const secrets = inputs.flatMap(input => [input.credentials.username, input.credentials.password]);
  const redact = value => secrets.reduce((safe, secret) => safe.split(secret).join('[synthetic account redacted]'), String(value));
  const api = 'http://127.0.0.1:8031', ui = 'http://127.0.0.1:5191';
  const calls = [], external = [], forbiddenMutations = [], errors = [], checks = {};
  const started = Date.now();
  let browser, activePage, failed = null;
  const log = message => {
    const safe = redact(message);
    console.log(safe);
    fs.appendFileSync(path.join(evidence, 'browser.log'), new Date().toISOString() + ' ' + safe + '\n');
  };
  const markerFor = (workspace, code) => workspace.stages.find(item => item.stage.stable_key.endsWith('.' + code));
  try {
    browser = await chromium.launch({ channel: 'msedge', headless: true });
    for (const { scenario, credentials, plan, workspace } of inputs) {
      assert.deepEqual(workspace.plan, plan);
      assert.equal(plan.project_id, credentials.project_id);
      const scenarioChecks = checks[scenario] = {};
      const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
      const page = activePage = await context.newPage();
      page.setDefaultTimeout(12000);
      page.setDefaultNavigationTimeout(20000);
      page.on('pageerror', error => errors.push(redact(error.message)));
      await context.route('**/*', async route => {
        const request = route.request(), url = new URL(request.url());
        if (!['127.0.0.1', 'localhost'].includes(url.hostname)) { external.push(url.origin); return route.abort('blockedbyclient'); }
        if (!url.pathname.startsWith('/api/v1/') && url.pathname !== '/healthz') return route.continue();
        if (!['GET', 'HEAD'].includes(request.method()) && !(request.method() === 'POST' && ['/api/v1/auth/login', '/api/v1/auth/logout'].includes(url.pathname))) {
          forbiddenMutations.push({ scenario, method: request.method(), path: url.pathname });
          return route.abort('blockedbyclient');
        }
        try {
          const response = await route.fetch({ url: api + url.pathname + url.search, timeout: 20000, maxRetries: 0 });
          calls.push({ scenario, method: request.method(), path: url.pathname, status: response.status(), csrf_present: !!request.headers()['x-csrf-token'] });
          await route.fulfill({ response });
        } catch (error) {
          if (request.method() === 'GET' && /Route is already handled|Request context disposed|Target.*closed/.test(error.message)) return;
          errors.push(redact('HTTP relay: ' + error.message));
          await route.abort().catch(() => {});
        }
      });
      async function login() {
        await page.getByLabel('用户名', { exact: true }).fill(credentials.username);
        await page.getByLabel('密码', { exact: true }).fill(credentials.password);
        const response = page.waitForResponse(response => new URL(response.url()).pathname === '/api/v1/auth/login');
        await page.getByRole('button', { name: '登录学习空间', exact: true }).click();
        assert.equal((await response).status(), 200);
        await page.getByRole('button', { name: '退出登录', exact: true }).waitFor();
      }
      async function exactRead() {
        const actual = await page.evaluate(async projectId => {
          const session = await fetch('/api/v1/session', { credentials: 'include' });
          if (!session.ok || !(await session.json()).project_ids.includes(projectId)) throw new Error('ordinary session/project unavailable');
          const read = async endpoint => {
            const response = await fetch(endpoint + '?project_id=' + encodeURIComponent(projectId), { credentials: 'include' });
            if (!response.ok) throw new Error('ordinary exact read failed ' + response.status);
            return response.json();
          };
          return { plan: await read('/api/v1/plans/current'), workspace: await read('/api/v1/workspace') };
        }, credentials.project_id);
        assert.deepEqual(actual.plan, plan);
        assert.deepEqual(actual.workspace, workspace);
      }
      async function enter(stage) {
        await page.locator('.stage-trigger').filter({ hasText: stage.stage.title }).click();
        await page.locator('.page-title-line h1').filter({ hasText: stage.stage.title }).waitFor();
      }
      async function cardsFor(stage, mode, minimum, requireLongContinuation = false) {
        await enter(stage);
        const cards = page.getByRole('region', { name: '项目源码学习', exact: true });
        assert.ok(await cards.count() >= minimum);
        if (minimum === 2) assert.equal(await cards.count(), 2, 'two actual alternative mature cards');
        const extensions = plan.extensions.filter(extension => extension.stage_id === stage.stage.stage_id && extension.topic.startsWith('项目学习：'));
        for (let index = 0; index < await cards.count(); index++) {
          const card = cards.nth(index), title = await card.getByRole('heading', { level: 2 }).innerText();
          const fragments = extensions.filter(extension => extension.topic.slice('项目学习：'.length).replace(/[（(]续\d+(?:\/\d+)?[）)]\s*$/, '').trim() === title).sort((a, b) => a.order_index - b.order_index);
          assert.ok(fragments.length > 0);
          const guidance = fragments.map(fragment => fragment.guidance).join('');
          const prompt = await card.getByLabel('源码学习 Prompt', { exact: true }).inputValue();
          assert.ok((await card.innerText()).includes(guidance), 'all ordered guidance fragments visible');
          assert.ok(prompt.includes(guidance), 'full guidance retained in prompt');
          if (mode) assert.ok(prompt.includes(mode));
          assert.ok(prompt.includes('不代表已掌握') && prompt.includes('不要覆盖现有本地修改'));
          assert.ok(prompt.includes('当前仓库的源码'));
          if (!requireLongContinuation) assert.ok(prompt.includes('正常') && prompt.includes('失败'));
          assert.ok(prompt.includes('暂不涉及') && prompt.includes('迁移'));
          if (requireLongContinuation && fragments.length > 1) {
            assert.ok(guidance.length > 850, 'independent P01 fixture has actual long ordered continuation');
            scenarioChecks.long_continuation_fragment_count = fragments.length;
            scenarioChecks.long_continuation_characters = guidance.length;
          }
          await context.grantPermissions(['clipboard-read', 'clipboard-write']);
          await card.getByRole('button', { name: '复制给 AI', exact: true }).click();
          await card.getByText('已复制，可粘贴给外部 AI。', { exact: true }).waitFor();
          assert.equal((await page.evaluate(() => navigator.clipboard.readText())).replace(/\r\n/g, '\n'), prompt);
        }
        if (requireLongContinuation) assert.ok(scenarioChecks.long_continuation_fragment_count > 1, 'P01 has a persisted continuation, not only short guidance');
        await page.screenshot({ path: path.join(evidence, `${scenario}-${mode || 'continuation'}.png`), fullPage: true });
        return await cards.count();
      }
      await page.goto(ui + '/#workspace');
      await login();
      await exactRead();
      await page.goto(ui + '/#workspace');
      await page.locator('.stage-trigger').first().waitFor();
      const sidebar = await page.locator('.stage-trigger').allTextContents();
      assert.equal(sidebar.length, workspace.stages.length);
      workspace.stages.forEach((stage, index) => assert.ok(sidebar[index].includes(stage.stage.title), 'saved stage order rendered'));
      scenarioChecks.exact_initial_get = 'PASS';
      const a2 = markerFor(workspace, 'a2');
      if (a2 && scenario !== 'long') {
        assert.ok(a2.units.length >= 3 && a2.nodes.length === 1 && a2.tasks.length === 1);
        assert.ok(a2.units.every(unit => unit.node_ids.length === 1 && unit.node_ids[0] === a2.nodes[0].node_id));
        await enter(a2);
        const unitsRegion = page.getByRole('region', { name: '本阶段学习单元', exact: true });
        assert.deepEqual(await unitsRegion.locator('.learning-unit > h3').allTextContents(), a2.units.map(unit => unit.title));
        for (const unit of a2.units) for (const objective of unit.objectives) await unitsRegion.getByText(objective, { exact: true }).waitFor();
        assert.equal(await unitsRegion.getByRole('button', { name: a2.nodes[0].title, exact: true }).count(), a2.units.length);
        assert.equal(await page.locator('.practice-preview article').count(), 1);
        assert.equal(await unitsRegion.getByRole('button', { name: /完成|掌握|总结/ }).count(), 0);
        await page.screenshot({ path: path.join(evidence, `${scenario}-a2-units.png`), fullPage: true });
        scenarioChecks.a2_multiunit_one_canonical_one_task = 'PASS';
      }
      if (['rag', 'system'].includes(scenario)) {
        for (const code of ['a5', 'a6', 'a8']) { const stage = markerFor(workspace, code); assert.ok(stage); await enter(stage); }
        scenarioChecks.a5_a6_a8 = 'PASS';
        scenarioChecks.small_core_cards = await cardsFor(markerFor(workspace, 'a8'), 'whole_core', 1);
      }
      if (scenario === 'rag') {
        for (const code of ['g0','g1','g2','g3','g4','g5','g6','gr','gt']) { const stage = markerFor(workspace, code); assert.ok(stage); await enter(stage); }
        scenarioChecks.specialty_mature_transfer = 'PASS';
        const mature = markerFor(workspace, 'gr');
        assert.equal(mature.tasks.length, 1, 'alternative repositories do not create two required tasks');
        scenarioChecks.mature_alternative_cards = await cardsFor(mature, 'targeted_deep_dive', 2);
      }
      if (scenario === 'mcp') {
        assert.ok(markerFor(workspace, 'a6'));
        for (const code of ['a5','a8','g0','gr','gt']) assert.equal(markerFor(workspace, code), undefined);
        await enter(markerFor(workspace, 'a6'));
        scenarioChecks.narrow_mcp_closure = 'PASS';
      }
      if (scenario === 'node') {
        const tasks = workspace.stages.flatMap(stage => stage.tasks);
        assert.ok(tasks.every(task => /Node\.js API/.test(task.goal)));
        assert.ok(tasks.every(task => !/FastAPI|TaskService/.test(task.goal)));
        for (const stage of workspace.stages) { await enter(stage); for (const task of stage.tasks) await page.locator('.practice-preview').getByText(task.goal, { exact: true }).waitFor(); }
        scenarioChecks.continuous_node_project = 'PASS';
        await page.screenshot({ path: path.join(evidence, 'node-continuous-project.png'), fullPage: true });
      }
      if (scenario === 'long') {
        const continuation = plan.extensions.find(extension => extension.topic.startsWith('项目学习：') && /[（(]续\d+(?:\/\d+)?[）)]\s*$/.test(extension.topic));
        assert.ok(continuation, 'independent owned P01 fixture contains actual saved continuation');
        const continuationStage = workspace.stages.find(stage => stage.stage.stage_id === continuation.stage_id);
        assert.ok(continuationStage);
        scenarioChecks.p01_owned_long_guidance_cards = await cardsFor(continuationStage, null, 1, true);
        scenarioChecks.p01_long_guidance_complete_consumption = 'PASS';
      }
      await page.reload();
      await page.getByRole('button', { name: '退出登录', exact: true }).waitFor();
      await exactRead(); scenarioChecks.refresh_exact_get = 'PASS';
      const logout = page.waitForResponse(response => new URL(response.url()).pathname === '/api/v1/auth/logout');
      await page.getByRole('button', { name: '退出登录', exact: true }).click();
      assert.equal((await logout).status(), 200);
      await login(); await exactRead(); scenarioChecks.relogin_exact_get = 'PASS';
      await page.screenshot({ path: path.join(evidence, `${scenario}-relogin.png`), fullPage: true });
      await context.close();
      log(`PASS ${scenario}: actual owned API/PG Plan, ordinary Edge, exact initial/refresh/relogin reads`);
    }
    assert.deepEqual(forbiddenMutations, []); assert.deepEqual(external, []); assert.deepEqual(errors, []);
    assert.ok(calls.filter(call => call.path === '/api/v1/auth/logout').every(call => call.csrf_present));
    const forbidden = path.join(evidence, 'forbidden-dispatch.jsonl');
    assert.ok(!fs.existsSync(forbidden) || fs.readFileSync(forbidden, 'utf8').trim() === '', 'model/Worker forbidden guard never attempted');
  } catch (error) {
    failed = { status: 'FAIL', message: redact(error.message), stack: redact(error.stack || '') };
    if (activePage && !activePage.isClosed()) await activePage.screenshot({ path: path.join(evidence, 'failure.png'), fullPage: true }).catch(() => {});
    log('FAIL ' + error.message); process.exitCode = 1;
  } finally {
    if (browser) {
      await browser.close().catch(() => {});
    }
    fs.writeFileSync(path.join(evidence, 'checks.json'), JSON.stringify({ status: failed ? 'FAIL' : 'PASS',
      source: 'Fake-generated confirmed Plans; actual owned PG + HTTP API + Edge renderer; auth POST only',
      checks, calls, failed, errors, forbiddenMutations, external,
      generation_requests: calls.filter(call => /generate|confirm/.test(call.path)).length,
      model_dispatch_attempts: fs.existsSync(path.join(evidence, 'forbidden-dispatch.jsonl')) ? fs.readFileSync(path.join(evidence, 'forbidden-dispatch.jsonl'), 'utf8').trim().split('\n').filter(Boolean).length : 0,
      elapsed_ms: Date.now() - started }, null, 2));
  }
})().catch(() => { console.error('v6.13 read-only browser setup failed; no secret input printed'); process.exitCode = 1; });
