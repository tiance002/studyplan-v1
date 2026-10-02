// Browser Fake for explicitly reading and selecting server-side runs. Every
// endpoint is intercepted locally; no generation, database, or provider call.
const { chromium } = require('playwright-core');
const assert = require('node:assert/strict');
const BASE = process.env.STUDYPLAN_URL || 'http://127.0.0.1:5178';

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  try {
    const page = await browser.newPage();
    page.setDefaultTimeout(6000);
    let username = 'user-a', project = 'project-a', listCalls = 0, runCalls = [], generateCalls = 0, failFirstDetail = true;
    let failNextList = false, delayList = false, releaseList, enteredList;
    const history = [
      { run_id: 'run-reconcile', status: 'reconciliation_required', next_action: 'reconcile', version: 4, result_ref: null, error: { code: 'unknown', message: '需要核对' }, progress: null },
      { run_id: 'run-old-success', status: 'succeeded', next_action: 'none', version: 2, result_ref: null, error: null, progress: null },
    ];
    await page.route('**/api/v1/session', route => route.fulfill({ json: { username, project_ids: [project], csrf_token: 'fake' } }));
    await page.route('**/healthz', route => route.fulfill({ json: { llm_provider: 'fake' } }));
    await page.route('**/api/v1/workspace?**', route => route.fulfill({ status: 404, json: {} }));
    await page.route('**/api/v1/plans/current?**', route => route.fulfill({ status: 404, json: {} }));
    await page.route('**/api/v1/runs?**', async route => {
      listCalls++;
      const url = new URL(route.request().url());
      assert.equal(url.searchParams.get('project_id'), project);
      assert.ok(Number(url.searchParams.get('limit')) <= 20);
      if (failNextList) { failNextList = false; return route.fulfill({ status: 503, json: { message: 'temporary' } }); }
      if (delayList) { enteredList(); await new Promise(resolve => { releaseList = resolve; }); }
      return route.fulfill({ json: history });
    });
    await page.route('**/api/v1/runs/**', async route => {
      const id = new URL(route.request().url()).pathname.split('/').at(-1);
      runCalls.push({ username, project, id });
      if (id === 'run-reconcile') {
        if (failFirstDetail) { failFirstDetail = false; return route.fulfill({ status: 503, json: { message: 'temporary detail failure' } }); }
        return route.fulfill({ json: history[0] });
      }
      return route.fulfill({ json: history[1] });
    });
    await page.route('**/api/v1/plans/generate?**', route => { generateCalls++; return route.fulfill({ status: 202, json: { run_id: 'unexpected' } }); });
    await page.route('**/api/v1/plan-changes/context?**', route => route.fulfill({ status: 404, json: {} }));
    await page.route('**/api/v1/auth/logout', route => route.fulfill({ json: { logged_out: true } }));
    await page.route('**/api/v1/auth/login', route => {
      username = route.request().postDataJSON().username;
      project = 'project-b';
      return route.fulfill({ json: { username, project_ids: [project], csrf_token: 'fake-b' } });
    });

    await page.goto(`${BASE}/#planning`);
    assert.equal(listCalls, 0, 'mount must not read server run history automatically');
    await page.getByRole('button', { name: '读取服务器上的运行', exact: true }).click();
    await page.getByRole('region', { name: '服务器上的运行', exact: true }).waitFor();
    assert.equal(listCalls, 1);
    assert.equal(await page.getByText('run-reconcile', { exact: true }).count(), 1);
    const reconcileRow = page.getByRole('listitem', { name: 'run-reconcile', exact: true });
    assert.equal(await reconcileRow.getByRole('button', { name: '读取此运行', exact: true }).isDisabled(), false);
    await reconcileRow.getByRole('button', { name: '读取此运行', exact: true }).click();
    await page.getByText('运行编号已保存，待读回', { exact: true }).waitFor();
    assert.equal(await page.getByText('run-reconcile', { exact: true }).count(), 1, 'failed detail read retains selected run id');
    await page.getByRole('button', { name: '手动读取运行状态', exact: true }).click();
    await page.getByText('运行需要核对，请勿重复调用', { exact: true }).waitFor();
    assert.deepEqual(runCalls.at(-1), { username: 'user-a', project: 'project-a', id: 'run-reconcile' });
    assert.equal(await page.getByRole('button', { name: '生成学习草案 →', exact: true }).isDisabled(), true);
    await page.locator('form').evaluate(form => form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })));
    assert.equal(generateCalls, 0);
    const oldSuccessRow = page.getByRole('listitem', { name: 'run-old-success', exact: true });
    assert.equal(await oldSuccessRow.getByRole('button', { name: '读取此运行', exact: true }).isDisabled(), true, 'active/unsafe current run permits only same-run selection');

    // Read error is retryable; a failed list never creates a generation.
    failNextList = true;
    await page.getByRole('button', { name: '读取服务器上的运行', exact: true }).click();
    await page.getByRole('alert').filter({ hasText: 'temporary' }).waitFor();
    assert.equal(generateCalls, 0);
    await page.getByRole('button', { name: '重新读取运行列表', exact: true }).click();
    await page.getByRole('region', { name: '服务器上的运行', exact: true }).waitFor();

    // A list response begun under account A must not replace account B's list.
    delayList = true;
    const entered = new Promise(resolve => { enteredList = resolve; });
    const countBeforeLate = listCalls;
    const clickRead = page.getByRole('button', { name: '读取服务器上的运行', exact: true }).click();
    await entered;
    await page.getByRole('button', { name: '退出登录', exact: true }).click();
    await page.getByLabel('用户名', { exact: true }).fill('user-b');
    await page.getByLabel('密码', { exact: true }).fill('password');
    await page.getByRole('button', { name: '登录学习空间', exact: true }).click();
    await page.getByRole('button', { name: '读取服务器上的运行', exact: true }).waitFor();
    releaseList();
    await page.waitForTimeout(100);
    assert.ok(listCalls > countBeforeLate);
    assert.equal(runCalls.some(item => item.username === 'user-b' && item.id === 'run-reconcile'), false, 'late list cannot auto-select/recover under new scope');
    assert.equal(generateCalls, 0);
    console.log('PASS: manual-only list read, selected-run recovery, reconciliation fail-closed, list retry and cross-account late-response fence');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
