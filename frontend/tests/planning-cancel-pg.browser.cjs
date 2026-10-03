// Normal login + owned real HTTP/PG/Worker. Model is explicitly Fake.
const { chromium } = require('playwright-core');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
(async () => {
  const api = process.env.STUDYPLAN_GENERATED_ROUTE_API;
  const ui = process.env.STUDYPLAN_URL || 'http://127.0.0.1:5178';
  assert.equal(new URL(api).hostname, '127.0.0.1');
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const page = await browser.newPage();
  const errors = [], requests = [];
  page.setDefaultTimeout(15000);
  page.on('pageerror', error => errors.push(error.message));
  try {
    await page.route('**/*', async route => {
      const request = route.request(), url = new URL(request.url());
      if (!['127.0.0.1', 'localhost'].includes(url.hostname)) return route.abort('blockedbyclient');
      if (url.pathname.startsWith('/api/v1/') || url.pathname === '/healthz') {
        const response = await route.fetch({ url: api + url.pathname + url.search });
        requests.push({ path: url.pathname, method: request.method(), status: response.status() });
        return route.fulfill({ response });
      }
      return route.continue();
    });
    async function login() {
      await page.getByLabel('用户名', { exact: true }).fill(process.env.STUDYPLAN_GENERATED_ROUTE_USER);
      await page.getByLabel('密码', { exact: true }).fill('Test-pass1!');
      const response = page.waitForResponse(r => r.url().endsWith('/api/v1/auth/login'));
      await page.getByRole('button', { name: '登录学习空间', exact: true }).click();
      assert.equal((await response).status(), 200);
      await page.getByRole('button', { name: '读取服务器上的运行', exact: true }).waitFor();
    }
    await page.goto(ui + '/#planning');
    await login();
    await page.getByRole('button', { name: '读取服务器上的运行', exact: true }).click();
    await page.getByRole('listitem', { name: process.env.STUDYPLAN_CANCEL_RUN, exact: true })
      .getByRole('button', { name: '读取此运行', exact: true }).click();
    await page.getByRole('button', { name: '取消生成', exact: true }).waitFor();
    await page.getByRole('status').getByText('正在生成', { exact: true }).waitFor();
    const acknowledgement = page.waitForResponse(r => r.url().includes('/runs/' + process.env.STUDYPLAN_CANCEL_RUN + '/cancel'));
    await page.getByRole('button', { name: '取消生成', exact: true }).click();
    assert.equal((await acknowledgement).status(), 200);
    await page.getByRole('status').getByText('运行已取消', { exact: true }).waitFor();
    await page.reload();
    await page.getByRole('status').getByText('运行已取消', { exact: true }).waitFor();
    await page.getByRole('button', { name: '退出登录', exact: true }).click();
    await login();
    await page.getByRole('status').getByText('运行已取消', { exact: true }).waitFor();
    assert.equal(requests.filter(r => r.path.endsWith('/cancel') && r.method === 'POST').length, 1);
    assert.equal(requests.filter(r => ['/api/v1/plans/generate', '/api/v1/plan-changes/generate'].includes(r.path)).length, 0);
    assert.equal(await page.getByRole('button', { name: '取消生成', exact: true }).count(), 0);
    await page.setViewportSize({ width: 390, height: 844 });
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    const directory = path.resolve(__dirname, '../../var/oct6-guidance');
    await page.screenshot({ path: path.join(directory, 'planning-cancel-real-pg.png') });
    fs.writeFileSync(path.join(directory, 'planning-cancel-real-pg.json'), JSON.stringify({
      status: 'PASS', database: 'owned real PG', worker: 'real', model: 'Fake', requests,
    }, null, 2));
    assert.deepEqual(errors, []);
    console.log('PASS: normal login, real running Worker cancellation, refresh/relogin, one cancel POST and zero redispatch');
  } finally {
    await page.unrouteAll({ behavior: 'wait' });
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
