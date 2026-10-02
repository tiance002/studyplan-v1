// Normal login + existing Worker + real HTTP and owned PG; model is explicitly Fake.
const { chromium } = require('playwright-core');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

(async () => {
  const api = process.env.STUDYPLAN_GENERATED_ROUTE_API;
  const ui = process.env.STUDYPLAN_URL || 'http://127.0.0.1:5178';
  assert.ok(api && new URL(api).hostname === '127.0.0.1', 'owned loopback API required');
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  let page;
  try {
    page = await browser.newPage();
    page.setDefaultTimeout(15000);
    const errors = [], forwarded = [], submissions = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.route('**/*', async route => {
      const url = new URL(route.request().url());
      if (!['127.0.0.1', 'localhost'].includes(url.hostname)) return route.abort('blockedbyclient');
      if (url.pathname.startsWith('/api/v1/') || url.pathname === '/healthz') {
        if (url.pathname === '/api/v1/plan-changes/generate') submissions.push(route.request().postDataJSON());
        const response = await route.fetch({ url: api + url.pathname + url.search });
        forwarded.push({ method: route.request().method(), path: url.pathname, status: response.status() });
        return route.fulfill({ response });
      }
      return route.continue();
    });
    const region = page.getByRole('region', { name: '有限路线调整', exact: true });
    const preview = page.getByRole('region', { name: '路线调整预览', exact: true });
    async function login() {
      await page.getByLabel('用户名', { exact: true }).fill(process.env.STUDYPLAN_GENERATED_ROUTE_USER);
      await page.getByLabel('密码', { exact: true }).fill('Test-pass1!'); // Owned synthetic account.
      const response = page.waitForResponse(r => r.url().endsWith('/api/v1/auth/login'));
      await page.getByRole('button', { name: '登录学习空间', exact: true }).click();
      assert.equal((await response).status(), 200);
      await region.waitFor();
    }
    await page.goto(ui + '/#planning');
    await login();
    await region.locator('summary').first().click();
    await region.getByRole('button', { name: '读取当前路线', exact: true }).click();
    await region.getByRole('button', { name: '重新生成未来阶段', exact: true }).waitFor();
    const session = await (await page.request.get(api + '/api/v1/session')).json();
    const project = session.project_ids[0];
    const params = '?project_id=' + encodeURIComponent(project);
    const before = await (await page.request.get(api + '/api/v1/plans/current' + params)).json();
    const futureResponse = page.waitForResponse(r => r.url().includes('/plan-changes/generate'));
    await region.getByRole('button', { name: '重新生成未来阶段', exact: true }).click();
    const accepted = await futureResponse;
    assert.equal(accepted.status(), 202, await accepted.text());
    const submitted = await accepted.json();
    await page.waitForFunction(([project, id]) => localStorage.getItem(`studyplan-run:${project}`) === id,
                              [project, submitted.run_id]);
    // Reload uses a real durable run GET; it must never submit another command.
    await page.reload();
    await region.waitFor();
    if (await region.locator('details').first().getAttribute('open') === null) await region.locator('summary').first().click();
    await preview.waitFor();
    const normalActions = page.getByRole('button', { name: '保存修改', exact: true });
    assert.equal(await normalActions.count(), 0, 'protected generated draft has no generic edit bypass');
    assert.equal(await page.getByRole('button', { name: '确认并发布路线', exact: true }).count(), 0);
    assert.equal(await page.getByRole('button', { name: '生成学习草案 →', exact: true }).isEnabled(), false);
    assert.equal(await preview.getByRole('button', { name: '确认发布新路线', exact: true }).isEnabled(), false);
    assert.match(await preview.innerText(), /保留|保持/);
    const cache = await page.evaluate(() => Object.entries(localStorage).filter(([k]) => k.startsWith('studyplan-plan-change:')));
    assert.equal(cache.length, 1);
    const previewId = cache[0][1];
    const persisted = await (await page.request.get(api + '/api/v1/plan-changes/' + previewId + params)).json();
    assert.equal(persisted.operation, 'regenerate_future_plan');
    assert.deepEqual(persisted.before_stage_keys, persisted.after_stage_keys);
    const tool = before.stages.find(s => s.stable_key === 'stage.tools');
    assert.deepEqual(persisted.draft.stages.find(s => s.stable_key === tool.stable_key), tool);
    assert.equal((await (await page.request.get(api + '/api/v1/plans/current' + params)).json()).plan_id, before.plan_id);
    await preview.getByRole('checkbox').check();
    const confirmation = page.waitForResponse(r => r.url().includes('/plan-changes/') && r.url().includes('/confirm?'));
    await preview.getByRole('button', { name: '确认发布新路线', exact: true }).click();
    const confirmed = await confirmation;
    assert.equal(confirmed.status(), 200, await confirmed.text());
    const result = await confirmed.json();
    await region.getByRole('status').filter({ hasText: '新路线已发布' }).waitFor();
    const after = await (await page.request.get(api + '/api/v1/plans/current' + params)).json();
    assert.equal(after.plan_id, result.plan_id);
    assert.equal(after.revision, before.revision + 1);
    assert.equal(submissions.length, 1);
    const history = await (await page.request.get(api + '/api/v1/exposures/history' + params
      + '&plan_id=' + encodeURIComponent(before.plan_id) + '&stage_id=' + encodeURIComponent(tool.stage_id)
      + '&unit_id=' + encodeURIComponent(before.unit_links.find(l => l.stage_id === tool.stage_id).unit_id))).json();
    assert.equal(history.length, 1);
    const progress = await (await page.request.get(api + '/api/v1/exposures' + params + '&plan_id=' + after.plan_id)).json();
    assert.ok(progress.every(position => !position.recorded));
    await page.getByRole('button', { name: '退出登录', exact: true }).click();
    await login();
    if (await region.locator('details').first().getAttribute('open') === null) await region.locator('summary').first().click();
    await region.getByRole('status').filter({ hasText: '新路线已发布' }).waitFor();
    // A second controlled goal change uses the same Worker/diff path, then explicit cancel.
    await region.getByLabel('新的学习目标', { exact: true }).fill('Agent作品集新方向');
    const nextResponse = page.waitForResponse(r => r.url().includes('/plan-changes/generate'));
    await region.getByRole('button', { name: '生成目标调整草案', exact: true }).click();
    const goalAccepted = await nextResponse;
    assert.equal(goalAccepted.status(), 202, await goalAccepted.text());
    await preview.getByRole('button', { name: '取消路线调整', exact: true }).waitFor();
    assert.match(await preview.innerText(), /Agent作品集新方向/);
    const cancellation = page.waitForResponse(r => r.url().includes('/plan-changes/') && r.url().includes('/cancel?'));
    await preview.getByRole('button', { name: '取消路线调整', exact: true }).click();
    assert.equal((await cancellation).status(), 200);
    await region.getByRole('status').filter({ hasText: '路线调整已取消' }).waitFor();
    assert.equal((await (await page.request.get(api + '/api/v1/plans/current' + params)).json()).plan_id, after.plan_id);
    assert.equal(submissions.length, 2);
    await page.setViewportSize({ width: 390, height: 844 });
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    assert.deepEqual(errors, []);
    const directory = path.resolve(__dirname, '../../var/oct6-guidance');
    fs.mkdirSync(directory, { recursive: true });
    // Capture a readable viewport; a tall element inside the scroll canvas is
    // clipped by its parent and is unsuitable as visual acceptance evidence.
    await page.setViewportSize({ width: 1440, height: 1000 });
    await preview.getByRole('heading', { name: '目标调整', exact: true }).scrollIntoViewIfNeeded();
    await page.screenshot({ path: path.join(directory, 'generated-route-real-pg.png') });
    fs.writeFileSync(path.join(directory, 'generated-route-browser-pg.json'), JSON.stringify({
      status: 'PASS', model: 'Fake', database: 'real owned isolated PG', before_plan: before.plan_id,
      after_plan: after.plan_id, proposal_id: previewId, submissions: submissions.map(s => s.operation), forwarded,
    }, null, 2));
    console.log('PASS: normal auth, existing Worker/Fake model, real HTTP/PG, protected prefix, refresh/diff, confirm, relogin, goal-change cancel');
  } finally {
    if (page) await page.unrouteAll({ behavior: 'wait' });
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
