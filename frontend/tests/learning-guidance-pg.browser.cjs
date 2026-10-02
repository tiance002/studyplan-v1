// Real HTTP/PG acceptance. The owning Python test supplies a live isolated API.
const {chromium} = require('playwright-core');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

(async () => {
  const api = process.env.STUDYPLAN_GUIDANCE_API;
  const ui = process.env.STUDYPLAN_URL || 'http://127.0.0.1:5178';
  assert.ok(api && new URL(api).hostname === '127.0.0.1', 'requires owned loopback API');
  const browser = await chromium.launch({channel:'chrome', headless:true});
  try {
    const page = await browser.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    const forwarded = [];
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
      await page.getByLabel('用户名', {exact:true}).fill('指导验收');
      await page.getByLabel('密码', {exact:true}).fill('Test-pass1!'); // Synthetic test account only.
      await page.getByRole('button', {name:'登录学习空间', exact:true}).click();
      await page.locator('.stage-trigger').first().waitFor();
    }
    await page.goto(ui + '/#workspace');
    await login();
    const workspaceResponse = await page.request.get(api + '/api/v1/session');
    // Browser owns a normal persisted session, not a development token.
    assert.equal(workspaceResponse.status(), 200);
    const project = (await workspaceResponse.json()).project_ids[0];
    const realWorkspace = await page.request.get(api + '/api/v1/workspace?project_id=' + encodeURIComponent(project));
    assert.equal(realWorkspace.status(), 200);
    const workspace = await realWorkspace.json();
    const tools = workspace.stages.find(s => s.stage.stable_key === 'stage.tools');
    assert.ok(tools && tools.stage.learning_guidance);
    await page.locator('.stage-trigger').filter({hasText:tools.stage.title}).click();
    const guide = page.getByRole('region', {name:'学习指导', exact:true});
    await guide.locator('summary').click();
    for (const expected of ['已有最小聊天 Agent', 'read_file', 'search_note', '未知 Tool', '错误参数', 'Tool 抛错', '第三个 Tool']) {
      assert.ok((await guide.innerText()).includes(expected), expected);
    }
    await page.reload();
    await guide.waitFor();
    await guide.locator('summary').click();
    assert.ok((await guide.innerText()).includes('read_file'));
    await page.getByRole('button', {name:'退出登录', exact:true}).click();
    await login();
    await page.locator('.stage-trigger').filter({hasText:tools.stage.title}).click();
    await guide.locator('summary').click();
    assert.ok((await guide.innerText()).includes('未知 Tool'));
    await page.setViewportSize({width:390,height:844});
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    assert.deepEqual(errors, []);
    assert.ok(forwarded.some(r => r.path === '/api/v1/auth/login' && r.status === 200));
    assert.ok(forwarded.some(r => r.path === '/api/v1/workspace' && r.status === 200));
    const dir = path.resolve(__dirname, '../../var/oct6-guidance');
    fs.mkdirSync(dir, {recursive:true});
    await page.screenshot({path:path.join(dir,'learning-guidance-real-pg.png'),fullPage:true});
    fs.writeFileSync(path.join(dir,'browser-pg.json'), JSON.stringify({status:'PASS',model:'Fake',database:'real isolated PG',forwarded},null,2));
    console.log('PASS: real auth/HTTP/PG guidance, refresh, logout/relogin and narrow viewport; model explicitly Fake');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode=1; });
