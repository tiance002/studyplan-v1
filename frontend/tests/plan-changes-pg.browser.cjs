// Real normal auth + HTTP + owned PG. No model, search or external requests.
const {chromium} = require('playwright-core');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

(async () => {
  const api = process.env.STUDYPLAN_ROUTE_API;
  const ui = process.env.STUDYPLAN_URL || 'http://127.0.0.1:5178';
  assert.ok(api && new URL(api).hostname === '127.0.0.1', 'owned loopback API required');
  const browser = await chromium.launch({channel:'chrome', headless:true});
  try {
    const page = await browser.newPage();
    const errors = [], forwarded = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.route('**/*', async route => {
      const url = new URL(route.request().url());
      if (!['127.0.0.1', 'localhost'].includes(url.hostname)) return route.abort('blockedbyclient');
      if (url.pathname.startsWith('/api/v1/') || url.pathname === '/healthz') {
        const response = await route.fetch({url:api + url.pathname + url.search});
        forwarded.push({method:route.request().method(), path:url.pathname, status:response.status()});
        return route.fulfill({response});
      }
      return route.continue();
    });
    async function login() {
      await page.getByLabel('用户名', {exact:true}).fill(process.env.STUDYPLAN_ROUTE_USER);
      await page.getByLabel('密码', {exact:true}).fill('isolatepass1'); // Synthetic owned account.
      const response = page.waitForResponse(r => r.url().endsWith('/api/v1/auth/login'));
      await page.getByRole('button', {name:'登录学习空间', exact:true}).click();
      const result = await response;
      assert.equal(result.status(), 200, await result.text());
      await page.getByRole('region', {name:'有限路线调整', exact:true}).waitFor();
    }
    const region = page.getByRole('region', {name:'有限路线调整', exact:true});
    await page.goto(ui + '/#planning');
    await login();
    await region.locator('summary').click();
    await region.getByRole('button', {name:'读取当前路线', exact:true}).click();
    await region.getByRole('button', {name:'下移 b', exact:true}).waitFor();
    assert.equal(await region.getByRole('button', {name:'下移 a', exact:true}).isEnabled(), false);
    assert.equal(await region.getByRole('button', {name:'上移 final', exact:true}).isEnabled(), false);
    await region.getByRole('button', {name:'下移 b', exact:true}).click();
    await region.getByRole('button', {name:'预览阶段顺序', exact:true}).click();
    const preview = page.getByRole('region', {name:'路线调整预览', exact:true});
    await preview.waitFor();
    assert.equal(await preview.getByRole('button', {name:'确认发布新路线', exact:true}).isEnabled(), false);
    const session = await (await page.request.get(api + '/api/v1/session')).json();
    const project = session.project_ids[0];
    const params = '?project_id=' + encodeURIComponent(project);
    const before = await (await page.request.get(api + '/api/v1/plans/current' + params)).json();
    const cache = await page.evaluate(() => Object.entries(localStorage).filter(([k]) => k.startsWith('studyplan-plan-change:')));
    assert.equal(cache.length, 1);
    const proposalId = cache[0][1];
    assert.ok(proposalId.startsWith('rch_'));
    const persistedPreview = await (await page.request.get(api + '/api/v1/plan-changes/' + proposalId + params)).json();
    assert.deepEqual(persistedPreview.after_stage_keys, ['a','c','b','final']);
    await page.reload();
    await region.waitFor();
    await region.locator('summary').click();
    await preview.waitFor();
    await preview.getByRole('checkbox').check();
    const response = page.waitForResponse(r => r.url().includes('/plan-changes/') && r.url().endsWith('/confirm' + params));
    await preview.getByRole('button', {name:'确认发布新路线', exact:true}).click();
    const confirmation = await response;
    assert.equal(confirmation.status(), 200);
    const result = await confirmation.json();
    assert.equal(result.created, true);
    await region.getByRole('status').filter({hasText:'新路线已发布'}).waitFor();
    const after = await (await page.request.get(api + '/api/v1/plans/current' + params)).json();
    assert.equal(after.plan_id, result.plan_id);
    assert.equal(after.revision, before.revision + 1);
    assert.deepEqual(after.stages.map(s => s.stable_key), ['a','c','b','final']);
    const workspace = await (await page.request.get(api + '/api/v1/workspace' + params)).json();
    assert.equal(workspace.plan.plan_id, result.plan_id);
    await page.getByRole('button', {name:'退出登录', exact:true}).click();
    await login();
    await region.locator('summary').click();
    await region.getByRole('status').filter({hasText:'新路线已发布'}).waitFor();
    await page.setViewportSize({width:390,height:844});
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    assert.deepEqual(errors, []);
    const directory = path.resolve(__dirname, '../../var/oct6-guidance');
    fs.mkdirSync(directory, {recursive:true});
    await region.screenshot({path:path.join(directory,'route-change-real-pg.png')});
    fs.writeFileSync(path.join(directory,'route-change-browser-pg.json'), JSON.stringify({
      status:'PASS', model:'NOT RUN', database:'real owned isolated PG', before_plan:before.plan_id,
      after_plan:after.plan_id, proposal_id:proposalId, forwarded,
    }, null, 2));
    console.log('PASS: normal auth, real HTTP/PG finite change, preview reload, publish, logout/relogin, 390px');
  } finally {await browser.close();}
})().catch(error => {console.error(error);process.exitCode=1;});
