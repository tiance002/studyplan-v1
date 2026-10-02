// Normal login + real HTTP/owned PG. Existing Worker uses an explicitly Fake model.
const { chromium } = require('playwright-core');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

(async () => {
  const api = process.env.STUDYPLAN_GENERATED_ROUTE_API;
  const ui = process.env.STUDYPLAN_URL || 'http://127.0.0.1:5178';
  assert.equal(new URL(api).hostname, '127.0.0.1');
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const forwarded = [], errors = [];
  const pages = [];
  let generationPosts = 0;
  try {
    async function openFresh() {
      const context = await browser.newContext();
      const page = await context.newPage();
      pages.push(page);
      page.setDefaultTimeout(15000);
      page.on('pageerror', err => errors.push(err.message));
      await page.route('**/*', async route => {
        const url = new URL(route.request().url());
        if (!['127.0.0.1', 'localhost'].includes(url.hostname)) return route.abort('blockedbyclient');
        if (url.pathname.startsWith('/api/v1/') || url.pathname === '/healthz') {
          if (['/api/v1/plans/generate', '/api/v1/plan-changes/generate'].includes(url.pathname)) generationPosts++;
          const response = await route.fetch({ url: api + url.pathname + url.search });
          forwarded.push({ method: route.request().method(), path: url.pathname, status: response.status() });
          return route.fulfill({ response });
        }
        return route.continue();
      });
      await page.goto(ui + '/#planning');
      await page.getByLabel('用户名', { exact: true }).fill(process.env.STUDYPLAN_GENERATED_ROUTE_USER);
      await page.getByLabel('密码', { exact: true }).fill('Test-pass1!');
      const loginResponse = page.waitForResponse(r => r.url().endsWith('/api/v1/auth/login'));
      await page.getByRole('button', { name: '登录学习空间', exact: true }).click();
      assert.equal((await loginResponse).status(), 200);
      await page.getByRole('button', { name: '读取服务器上的运行', exact: true }).waitFor();
      assert.deepEqual(await page.evaluate(() => Object.keys(localStorage).filter(k => k.startsWith('studyplan-run:'))), []);
      return { context, page };
    }
    const unknown = await openFresh();
    assert.equal(forwarded.filter(r => r.path === '/api/v1/runs').length, 0, 'history is an explicit read');
    await unknown.page.getByRole('button', { name: '读取服务器上的运行', exact: true }).click();
    const history = unknown.page.getByRole('region', { name: '服务器上的运行', exact: true });
    const unknownRow = history.getByRole('listitem', { name: process.env.STUDYPLAN_HISTORY_UNKNOWN_RUN, exact: true });
    await unknownRow.getByRole('button', { name: '读取此运行', exact: true }).click();
    await unknown.page.getByText('运行需要核对，请勿重复调用', { exact: true }).waitFor();
    assert.equal(await unknown.page.getByRole('button', { name: '生成学习草案 →', exact: true }).isDisabled(), true);
    assert.equal(await history.getByRole('listitem', { name: process.env.STUDYPLAN_HISTORY_SUCCESS_RUN, exact: true })
      .getByRole('button', { name: '读取此运行', exact: true }).isDisabled(), true, 'active/unknown pointer cannot be bypassed');
    await unknown.page.reload();
    await unknown.page.getByText('运行需要核对，请勿重复调用', { exact: true }).waitFor();
    await unknown.page.setViewportSize({ width: 390, height: 844 });
    assert.equal(await unknown.page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    await unknown.page.unrouteAll({ behavior: 'wait' });
    await unknown.context.close();

    const successful = await openFresh();
    await successful.page.getByRole('button', { name: '读取服务器上的运行', exact: true }).click();
    const row = successful.page.getByRole('region', { name: '服务器上的运行', exact: true })
      .getByRole('listitem', { name: process.env.STUDYPLAN_HISTORY_SUCCESS_RUN, exact: true });
    await row.getByRole('button', { name: '读取此运行', exact: true }).click();
    await successful.page.getByRole('button', { name: '确认并发布路线', exact: true }).waitFor();
    assert.equal(await successful.page.getByRole('button', { name: '生成学习草案 →', exact: true }).isDisabled(), true);
    await successful.page.reload();
    await successful.page.getByRole('button', { name: '确认并发布路线', exact: true }).waitFor();
    assert.ok(forwarded.some(r => r.path === '/api/v1/plans/drafts/' + process.env.STUDYPLAN_HISTORY_DRAFT && r.status === 200));
    assert.equal(generationPosts, 0, 'all recoveries are reads; no new generation or replay');
    assert.deepEqual(errors, []);
    const directory = path.resolve(__dirname, '../../var/oct6-guidance');
    await successful.page.setViewportSize({ width: 1440, height: 1000 });
    await successful.page.getByRole('button', { name: '读取服务器上的运行', exact: true }).scrollIntoViewIfNeeded();
    await successful.page.screenshot({ path: path.join(directory, 'run-history-real-pg.png') });
    fs.writeFileSync(path.join(directory, 'run-history-browser-pg.json'), JSON.stringify({
      status: 'PASS', database: 'owned real PG', model: 'Fake', generationPosts, forwarded,
    }, null, 2));
    await successful.page.unrouteAll({ behavior: 'wait' });
    await successful.context.close();
    console.log('PASS: empty-cache private history, unknown fail closed, successful draft GET/reload, zero generation POST');
  } finally {
    for (const page of pages) if (!page.isClosed()) await page.unrouteAll({ behavior: 'wait' });
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
