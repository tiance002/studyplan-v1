// Ordinary auth + existing Worker + real HTTP/owned PG. Model is Fake.
const { chromium } = require('playwright-core');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

(async () => {
  const api = process.env.STUDYPLAN_GENERATED_ROUTE_API;
  assert.ok(api && new URL(api).hostname === '127.0.0.1');
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const page = await browser.newPage();
  page.setDefaultTimeout(20000);
  const errors = [], commands = [];
  page.on('pageerror', error => errors.push(error.message));
  try {
    await page.route('**/*', async route => {
      const url = new URL(route.request().url());
      if (!['127.0.0.1', 'localhost'].includes(url.hostname)) return route.abort('blockedbyclient');
      if (url.pathname.startsWith('/api/v1/') || url.pathname === '/healthz') {
        if (url.pathname === '/api/v1/plan-changes/generate') commands.push(route.request().postDataJSON());
        const response = await route.fetch({ url: api + url.pathname + url.search });
        return route.fulfill({ response });
      }
      return route.continue();
    });
    const region = page.getByRole('region', { name: '有限路线调整', exact: true });
    const preview = page.getByRole('region', { name: '路线调整预览', exact: true });
    await page.goto((process.env.STUDYPLAN_URL || 'http://127.0.0.1:5178') + '/#planning');
    async function login() {
      await page.getByLabel('用户名', { exact: true }).fill(process.env.STUDYPLAN_GENERATED_ROUTE_USER);
      await page.getByLabel('密码', { exact: true }).fill('Test-pass1!');
      await page.getByRole('button', { name: '登录学习空间', exact: true }).click();
      await region.waitFor();
    }
    await login();
    await region.locator('summary').first().click();
    await region.getByRole('button', { name: '读取当前路线', exact: true }).click();
    const session = await (await page.request.get(api + '/api/v1/session')).json();
    const project = session.project_ids[0];
    const params = '?project_id=' + project;
    const before = await (await page.request.get(api + '/api/v1/plans/current' + params)).json();
    const context = await (await page.request.get(api + '/api/v1/plan-changes/context' + params)).json();
    const topic = context.add_topic_options.find(t => t.stable_key === 'node.mcp.1');
    assert.ok(topic);
    await region.getByRole('checkbox', { name: topic.title, exact: true }).check();
    const queuedResponse = page.waitForResponse(r => new URL(r.url()).pathname === '/api/v1/plan-changes/generate');
    await region.getByRole('button', { name: '生成主题追加草案', exact: true }).click();
    const accepted = await queuedResponse;
    assert.equal(accepted.status(), 202, await accepted.text());
    const run = await accepted.json();
    await page.waitForFunction(([p, id]) => localStorage.getItem(`studyplan-run:${p}`) === id, [project, run.run_id]);
    await page.reload();
    await region.waitFor();
    if (await region.locator('details').first().getAttribute('open') === null) await region.locator('summary').first().click();
    await preview.waitFor();
    await preview.getByRole('heading', { name: '追加的受控主题', exact: true }).waitFor();
    assert.match(await preview.innerText(), /新增阶段|保留的旧阶段/);
    assert.equal(await page.getByRole('button', { name: '保存修改', exact: true }).count(), 0);
    const id = await page.evaluate(() => Object.entries(localStorage).find(([k]) => k.startsWith('studyplan-plan-change:'))?.[1]);
    assert.ok(id);
    const frozen = await (await page.request.get(api + '/api/v1/plan-changes/' + id + params)).json();
    assert.deepEqual(frozen.added_stage_keys, ['stage.mcp']);
    assert.ok(frozen.added_node_keys.includes('node.mcp.2'), 'entire controlled stage is disclosed');
    assert.ok(frozen.topic_titles['node.mcp.1']);
    assert.ok(!(await preview.innerText()).includes('node.mcp'), 'internal knowledge keys do not substitute learning titles');
    const tool = before.stages.find(s => s.stable_key === 'stage.tools');
    assert.deepEqual(frozen.draft.stages.find(s => s.stable_key === tool.stable_key), tool);
    assert.equal((await (await page.request.get(api + '/api/v1/plans/current' + params)).json()).plan_id, before.plan_id);
    assert.equal(await preview.getByRole('button', { name: '确认发布新路线', exact: true }).isEnabled(), false);
    await page.setViewportSize({ width: 1440, height: 1000 });
    await preview.getByRole('heading', { name: '追加的受控主题', exact: true }).scrollIntoViewIfNeeded();
    const directory = path.resolve(__dirname, '../../var/oct6-guidance');
    fs.mkdirSync(directory, { recursive: true });
    await page.screenshot({ path: path.join(directory, 'add-topic-real-pg.png') });
    await preview.getByRole('checkbox').check();
    const confirmed = page.waitForResponse(r => r.url().includes('/confirm?'));
    await preview.getByRole('button', { name: '确认发布新路线', exact: true }).click();
    assert.equal((await confirmed).status(), 200);
    await region.getByRole('status').filter({ hasText: '新路线已发布' }).waitFor();
    await region.getByText('当前没有可追加的受控主题。', { exact: true }).waitFor();
    const after = await (await page.request.get(api + '/api/v1/plans/current' + params)).json();
    assert.notEqual(after.plan_id, before.plan_id);
    assert.equal(after.stages.length, before.stages.length + 1);
    assert.equal(after.stages.at(-1).stable_key, before.stages.at(-1).stable_key);
    const progress = await (await page.request.get(api + '/api/v1/exposures' + params + '&plan_id=' + after.plan_id)).json();
    assert.ok(progress.every(item => !item.recorded));
    await page.getByRole('button', { name: '退出登录', exact: true }).click(); await login();
    if (await region.locator('details').first().getAttribute('open') === null) await region.locator('summary').first().click();
    await region.getByRole('status').filter({ hasText: '新路线已发布' }).waitFor();
    assert.equal(commands.length, 1);
    assert.deepEqual(commands[0].topic_keys, ['node.mcp.1']);
    assert.deepEqual(errors, []);
    fs.writeFileSync(path.join(directory, 'add-topic-browser-pg.json'), JSON.stringify({ status: 'PASS',
      model: 'Fake', database: 'real owned isolated PG', before: before.plan_id, after: after.plan_id, proposal: id, commands }, null, 2));
    console.log('PASS: add_topic ordinary login, real owned PG/Worker/HTTP, refresh/diff, protected stages, explicit confirm, relogin, no replay');
  } finally {
    await page.unrouteAll({ behavior: 'wait' });
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
