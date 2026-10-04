// Read one already confirmed paid plan. Only auth POSTs are permitted.
const { chromium } = require('playwright-core');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

(async () => {
  const directory = process.env.STUDYPLAN_PAID_EVIDENCE_DIR
    ? path.resolve(process.env.STUDYPLAN_PAID_EVIDENCE_DIR)
    : path.resolve(__dirname, '../../var/v610');
  assert.equal(JSON.parse(fs.readFileSync(path.join(directory, 'paid-and-pg.json'), 'utf8')).status, 'PASS', 'Confirmed real Plan is required before read-only Edge acceptance');
  const credentials = JSON.parse(fs.readFileSync(path.join(directory, 'private/browser.json'), 'utf8'));
  const expectedPlan = JSON.parse(fs.readFileSync(path.join(directory, 'plan.json'), 'utf8'));
  const expectedWorkspace = JSON.parse(fs.readFileSync(path.join(directory, 'workspace.json'), 'utf8'));
  assert.ok(typeof credentials.username === 'string' && typeof credentials.password === 'string');
  const api = process.env.STUDYPLAN_V610_PAID_API || 'http://127.0.0.1:8030';
  const ui = process.env.STUDYPLAN_V610_PAID_URL || 'http://127.0.0.1:5190';
  assert.equal(new URL(api).origin, 'http://127.0.0.1:8030');
  assert.equal(new URL(ui).origin, 'http://127.0.0.1:5190');
  const redact = value => String(value).split(credentials.password).join('[redacted]').split(credentials.username).join('[synthetic account]');
  const calls = [], forbiddenMutations = [], external = [], errors = [], checks = {};
  const started = Date.now();
  let browser, page, failed = null;
  const log = message => {
    const safe = redact(message);
    console.log(safe);
    fs.appendFileSync(path.join(directory, 'paid-consumption-browser.log'), new Date().toISOString() + ' ' + safe + '\n');
  };
  fs.writeFileSync(path.join(directory, 'paid-consumption-browser.log'), 'v6.10 Edge read-only paid Plan consumption; auth POSTs only\n');
  const deadline = setTimeout(() => {
    failed = { status: 'FAIL', message: '115-second read-only browser deadline' };
    browser?.close().catch(() => {});
  }, 115000);
  try {
    assert.equal(expectedWorkspace.plan.plan_id, expectedPlan.plan_id);
    browser = await chromium.launch({ channel: 'msedge', headless: true });
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
    page = await context.newPage();
    page.setDefaultTimeout(12000);
    page.setDefaultNavigationTimeout(20000);
    page.on('pageerror', error => errors.push(redact(error.message)));
    await context.route('**/*', async route => {
      const request = route.request(), url = new URL(request.url());
      if (!['127.0.0.1', 'localhost'].includes(url.hostname)) {
        external.push(url.origin);
        return route.abort('blockedbyclient');
      }
      if (!url.pathname.startsWith('/api/v1/') && url.pathname !== '/healthz') return route.continue();
      if (!['GET', 'HEAD'].includes(request.method())
        && !(request.method() === 'POST' && ['/api/v1/auth/login', '/api/v1/auth/logout'].includes(url.pathname))) {
        forbiddenMutations.push({ method: request.method(), path: url.pathname });
        return route.abort('blockedbyclient');
      }
      try {
        const response = await route.fetch({ url: api + url.pathname + url.search, timeout: 20000, maxRetries: 0 });
        calls.push({ method: request.method(), path: url.pathname, status: response.status(),
          csrf_present: !!request.headers()['x-csrf-token'] });
        await route.fulfill({ response });
      } catch (error) {
        if (request.method() === 'GET' && /Route is already handled|Request context disposed|Target.*closed/.test(error.message)) return;
        errors.push(redact('HTTP relay: ' + error.message));
        await route.abort().catch(() => {});
      }
    });
    const login = async () => {
      await page.getByLabel('用户名', { exact: true }).fill(credentials.username);
      await page.getByLabel('密码', { exact: true }).fill(credentials.password);
      const response = page.waitForResponse(r => new URL(r.url()).pathname === '/api/v1/auth/login');
      await page.getByRole('button', { name: '登录学习空间', exact: true }).click();
      assert.equal((await response).status(), 200, 'ordinary login succeeds');
      await page.getByRole('button', { name: '退出登录', exact: true }).waitFor();
    };
    const read = endpoint => page.evaluate(async endpoint => {
      const sessionResponse = await fetch('/api/v1/session', { credentials: 'include' });
      if (!sessionResponse.ok) throw new Error('ordinary session absent');
      const session = await sessionResponse.json();
      const response = await fetch(endpoint + '?project_id=' + encodeURIComponent(session.project_ids[0]), { credentials: 'include' });
      if (!response.ok) throw new Error('read failed: ' + response.status);
      return response.json();
    }, endpoint);
    const exactRead = async () => {
      assert.deepEqual(await read('/api/v1/plans/current'), expectedPlan);
      assert.deepEqual(await read('/api/v1/workspace'), expectedWorkspace);
    };
    await page.goto(ui + '/#workspace');
    await login();
    await exactRead();
    await page.goto(ui + '/#workspace');
    await page.locator('.stage-trigger').first().waitFor();
    const reference = expectedWorkspace.stages.find(stage => /\.a8$/.test(stage.stage.stable_key));
    assert.ok(reference && reference.nodes.length > 0 && reference.tasks.length > 0, 'A8 knowledge and tasks exist');
    const tasks = expectedWorkspace.stages.flatMap(stage => stage.tasks);
    assert.ok(tasks.length > 0 && tasks.every(task => task.acceptance.length > 0));
    await page.locator('.stage-trigger').filter({ hasText: reference.stage.title }).click();
    const card = page.getByRole('region', { name: '项目源码学习', exact: true }).filter({ hasText: 'Pi 轻量 Runtime' });
    await card.waitFor();
    const prompt = await card.getByLabel('源码学习 Prompt', { exact: true }).inputValue();
    assert.ok(prompt.includes('whole_core') && prompt.includes('预期产物') && prompt.includes('迁移候选'));
    assert.ok(prompt.includes('不代表已掌握') && prompt.includes('允许检查的本地目录'));
    assert.ok((await card.getByRole('link').getAttribute('href')).startsWith('https://github.com/'));
    assert.ok((await page.locator('.practice-preview').innerText()).includes(reference.tasks[0].title));
    await context.grantPermissions(['clipboard-read', 'clipboard-write']);
    await card.getByRole('button', { name: '复制给 AI', exact: true }).click();
    await card.getByText('已复制，可粘贴给外部 AI。', { exact: true }).waitFor();
    assert.equal((await page.evaluate(() => navigator.clipboard.readText())).replace(/\r\n/g, '\n'), prompt);
    checks.pi_card = 'PASS'; checks.study_mode = 'whole_core'; checks.clipboard = 'PASS';
    checks.reference_knowledge_count = reference.nodes.length; checks.reference_task_count = reference.tasks.length;
    await page.screenshot({ path: path.join(directory, 'paid-pi-workspace-edge.png'), fullPage: true });

    const later = expectedPlan.extensions.find(extension => extension.topic === '本次范围与后续学习路径');
    assert.ok(later && later.guidance.includes('3–8') && later.guidance.includes('未选专项没有自动生成或完成'));
    const laterStage = expectedPlan.stages.find(stage => stage.stage_id === later.stage_id);
    assert.ok(laterStage);
    await page.locator('.stage-trigger').filter({ hasText: laterStage.title }).click();
    const map = page.getByRole('region', { name: '对比与思考提示', exact: true }).filter({ hasText: later.topic });
    await map.waitFor();
    const mapText = await map.innerText();
    assert.ok(mapText.includes('3–8') && mapText.includes('当前首步') && mapText.includes('后续专项'));
    checks.current_and_later_map = 'PASS';
    await page.screenshot({ path: path.join(directory, 'paid-current-later-map-edge.png'), fullPage: true });
    await page.reload();
    await page.getByRole('button', { name: '退出登录', exact: true }).waitFor();
    await exactRead(); checks.refresh = 'PASS';
    const logout = page.waitForResponse(r => new URL(r.url()).pathname === '/api/v1/auth/logout');
    await page.getByRole('button', { name: '退出登录', exact: true }).click();
    assert.equal((await logout).status(), 200);
    await login();
    await exactRead(); checks.relogin = 'PASS';
    await page.screenshot({ path: path.join(directory, 'paid-relogin-edge.png'), fullPage: true });
    assert.deepEqual(forbiddenMutations, [], 'no generation, confirmation or business write attempted');
    assert.deepEqual(external, []); assert.deepEqual(errors, []);
    assert.equal(calls.filter(call => call.path === '/api/v1/plans/generate').length, 0);
    assert.ok(calls.filter(call => call.path === '/api/v1/auth/logout').every(call => call.csrf_present));
    log('PASS Edge paid Plan consumption: exact workspace, Pi whole_core knowledge/tasks, current/later 3–8 map, copy, refresh/relogin, no generation or external requests');
  } catch (error) {
    failed = failed || { status: 'FAIL', message: redact(error.message), stack: redact(error.stack || '') };
    if (page && !page.isClosed()) await page.screenshot({ path: path.join(directory, 'paid-consumption-failure-edge.png'), fullPage: true }).catch(() => {});
    log('FAIL paid consumption: ' + error.message);
    process.exitCode = 1;
  } finally {
    clearTimeout(deadline);
    if (browser) {
      await Promise.all(browser.contexts().map(context => context.unrouteAll({ behavior: 'ignoreErrors' }).catch(() => {})));
      await browser.close().catch(() => {});
    }
    fs.writeFileSync(path.join(directory, 'paid-consumption-browser.json'), JSON.stringify({ status: failed ? 'FAIL' : 'PASS',
      plan_id: expectedPlan.plan_id, stage_count: expectedPlan.stages.length, checks, calls,
      failed, errors, forbiddenMutations, external, generation_requests: 0,
      elapsed_ms: Date.now() - started, scope: 'already confirmed paid Plan; actual owned HTTP/PG; Edge; login/logout only writes' }, null, 2));
  }
})().catch(error => { console.error(error.name + ': read-only browser input/setup failed'); process.exitCode = 1; });
