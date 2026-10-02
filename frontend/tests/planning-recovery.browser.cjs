// Browser Fake for fail-closed recovery of planning runs. All API calls are
// fulfilled locally; this never invokes a provider or writes to a database.
const { chromium } = require('playwright-core');
const assert = require('node:assert/strict');
const BASE = process.env.STUDYPLAN_URL || 'http://127.0.0.1:5178';
const PROJECT = 'recovery-project';

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  try {
    const page = await browser.newPage();
    page.setDefaultTimeout(5000);
    let runView, runReads = 0, generations = 0, nextRunId = 0;
    await page.route('**/api/v1/session', route => route.fulfill({ json: {
      username: 'recovery-user', project_ids: [PROJECT], csrf_token: 'fake',
    } }));
    await page.route('**/healthz', route => route.fulfill({ json: { llm_provider: 'fake' } }));
    await page.route('**/api/v1/workspace?**', route => route.fulfill({ status: 404, json: {} }));
    await page.route('**/api/v1/plans/current?**', route => route.fulfill({ status: 404, json: {} }));
    await page.route('**/api/v1/runs/**', async route => {
      const id = new URL(route.request().url()).pathname.split('/').at(-1);
      runReads++;
      if (id.startsWith('new-run-')) runView = {
        run_id: id, status: 'queued', next_action: 'wait', version: 1,
        result_ref: null, error: null, progress: null,
      };
      return route.fulfill({ json: { ...runView, run_id: id } });
    });
    await page.route('**/api/v1/plans/generate?**', async route => {
      generations++;
      const id = `new-run-${++nextRunId}`;
      return route.fulfill({ status: 202, json: { run_id: id } });
    });

    const openWith = async (status, next_action) => {
      runView = { run_id: 'saved-run', status, next_action, version: 3,
        result_ref: null, error: null, progress: null };
      await page.goto(`${BASE}/#planning`);
      await page.evaluate(([project, id]) => localStorage.setItem(`studyplan-run:${project}`, id), [PROJECT, 'saved-run']);
      await page.reload();
      await page.getByRole('button', { name: '刷新运行状态', exact: true }).waitFor();
    };
    const submitGeneration = async () => {
      await page.locator('form').evaluate(form => form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })));
    };

    // A future status must remain recoverable by manual GET, without polling or POST.
    await openWith('paused_by_new_server', 'wait');
    const unknownStatusReads = runReads;
    assert.equal(await page.locator('button.btn.primary').first().isDisabled(), true);
    assert.match(await page.locator('.run-banner').innerText(), /需要核对/);
    assert.match(await page.locator('.run-banner').innerText(), /saved-run/);
    await page.waitForTimeout(1900);
    assert.equal(runReads, unknownStatusReads, 'unknown status must not poll forever');
    await page.getByRole('button', { name: '刷新运行状态', exact: true }).click();
    await page.waitForTimeout(100);
    assert.equal(runReads, unknownStatusReads + 1, 'manual read remains available');
    await submitGeneration();
    assert.equal(generations, 0, 'unknown status cannot start or replay a generation');

    // A known status with an unknown action also fails closed and stops polling.
    await openWith('running', 'resume_from_checkpoint_v9');
    const unknownActionReads = runReads;
    assert.equal(await page.locator('button.btn.primary').first().isDisabled(), true);
    assert.match(await page.locator('.run-banner').innerText(), /需要核对/);
    await page.waitForTimeout(1900);
    assert.equal(runReads, unknownActionReads, 'unknown next_action must not poll forever');
    await submitGeneration();
    assert.equal(generations, 0);

    // Failed and cancelled are safe terminals for a new generation; the POST
    // always creates a different Run ID and does not resume the stored run.
    for (const [status, action] of [['failed', 'retry'], ['cancelled', 'none']]) {
      await openWith(status, action);
      assert.equal(await page.locator('button.btn.primary').first().isDisabled(), false, `${status} should allow a new run`);
      await submitGeneration();
      await page.getByText('等待生成', { exact: true }).waitFor();
      assert.equal(generations, status === 'failed' ? 1 : 2);
      assert.equal(await page.evaluate(project => localStorage.getItem(`studyplan-run:${project}`), PROJECT), `new-run-${generations}`);
      assert.equal(runView.run_id, `new-run-${generations}`);
    }
    assert.equal(await page.locator('.run-banner').innerText().then(text => text.includes('不会恢复或重派')), false);
    console.log('PASS: unknown status/action fail closed, manual reread without polling/replay, failed/cancelled start distinct new runs');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
