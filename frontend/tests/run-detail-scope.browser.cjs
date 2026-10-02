// Keep one PlanningPage instance mounted while changing its actor/project props.
// All network responses are synthetic and intercepted in the browser.
const { chromium } = require('playwright-core');
const assert = require('node:assert/strict');
const BASE = process.env.STUDYPLAN_URL || 'http://127.0.0.1:5178';

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  try {
    const page = await browser.newPage();
    page.setDefaultTimeout(5000);
    let enteredOld, releaseOld, enteredNew, enteredDraftCurrent, releaseDraftCurrent;
    const oldStarted = new Promise(resolve => { enteredOld = resolve; });
    const newStarted = new Promise(resolve => { enteredNew = resolve; });
    let newerStarted;
    const newerRunStarted = new Promise(resolve => { newerStarted = resolve; });
    const draftCurrentStarted = new Promise(resolve => { enteredDraftCurrent = resolve; });
    let holdDraftCurrent = false;
    await page.route('**/api/v1/plans/current?**', async route => {
      const query = new URL(route.request().url()).searchParams;
      if (holdDraftCurrent && query.get('project_id') === 'project-a') {
        enteredDraftCurrent();
        await new Promise(resolve => { releaseDraftCurrent = resolve; });
        return route.fulfill({ json: { project_id: 'project-a', revision: 91, goal_snapshot: 'stale plan' } });
      }
      return route.fulfill({ status: 404, json: {} });
    });
    await page.route('**/api/v1/plan-changes/context?**', route => route.fulfill({ status: 404, json: {} }));
    await page.route('**/api/v1/runs/run-a?**', async route => {
      enteredOld();
      await new Promise(resolve => { releaseOld = resolve; });
      return route.fulfill({ json: { run_id: 'run-a', status: 'reconciliation_required', next_action: 'reconcile', version: 1, result_ref: null, error: null, progress: null } });
    });
    await page.route('**/api/v1/runs/run-b?**', route => { enteredNew(); return route.fulfill({ json: { run_id: 'run-b', status: 'succeeded', next_action: 'none', version: 2, result_ref: null, error: null, progress: null } }); });
    await page.route('**/api/v1/runs/run-a-newer?**', route => { newerStarted(); return route.fulfill({ json: { run_id: 'run-a-newer', status: 'failed', next_action: 'retry', version: 3, result_ref: null, error: { code: 'failed', message: 'newer result' }, progress: null } }); });
    await page.route('**/api/v1/runs/run-draft?**', route => route.fulfill({ json: { run_id: 'run-draft', status: 'succeeded', next_action: 'review_draft', version: 3, result_ref: 'draft-a', error: null, progress: null } }));
    await page.route('**/api/v1/plans/drafts/draft-a?**', route => route.fulfill({ json: { draft_id: 'draft-a', project_id: 'project-a', revision: 3, goal_snapshot: 'stale draft target', status: 'awaiting_approval', draft_hash: 'hash', version: 1, stages: [], source_pack_key: 'seed', source_pack_version: 1 } }));
    await page.addInitScript(() => {
      localStorage.setItem('studyplan-run:project-a', 'run-a');
      localStorage.setItem('studyplan-run:project-b', 'run-b');
    });
    await page.goto(`${BASE}/tests/run-detail-scope.html`);
    await oldStarted;
    await page.getByRole('button', { name: '切换测试作用域' }).click();
    await newStarted;
    await page.getByText('生成已完成', { exact: true }).waitFor();
    await page.evaluate(() => localStorage.setItem('studyplan-run:project-a', 'run-a-newer'));
    await page.getByRole('button', { name: '切换测试作用域' }).click();
    await newerRunStarted;
    await page.getByText('生成失败', { exact: true }).waitFor();
    releaseOld();
    await page.waitForTimeout(100);
    assert.equal(await page.getByText('运行需要核对，请勿重复调用', { exact: true }).count(), 0, 'old-scope run response must not render after props switch');
    assert.equal(await page.getByText('生成失败', { exact: true }).count(), 1, 'an older request must not overwrite a newer run after returning to the same scope');

    // A selected run with a result stays fenced until its draft has been read.
    const sameScopePage = await browser.newPage();
    sameScopePage.setDefaultTimeout(5000);
    let enteredStaleDraft, releaseStaleDraft;
    const staleDraftStarted = new Promise(resolve => { enteredStaleDraft = resolve; });
    let sameScopeGenerateCalls = 0, resultReads = 0;
    await sameScopePage.route('**/api/v1/plans/generate?**', route => { sameScopeGenerateCalls++; return route.fulfill({ status: 202, json: { run_id: 'unexpected', status_url: '/ignored' } }); });
    await sameScopePage.route('**/api/v1/plans/current?**', route => route.fulfill({ status: 404, json: {} }));
    await sameScopePage.route('**/api/v1/plan-changes/context?**', route => route.fulfill({ status: 404, json: {} }));
    await sameScopePage.route('**/api/v1/runs/run-late-draft?**', route => route.fulfill({ json: { run_id: 'run-late-draft', status: 'succeeded', next_action: 'none', version: 1, result_ref: 'draft-race', error: null, progress: null } }));
    await sameScopePage.route('**/api/v1/plans/drafts/draft-race?**', async route => {
      if (++resultReads === 1) return route.fulfill({ status: 503, json: { message: 'result unavailable' } });
      enteredStaleDraft();
      await new Promise(resolve => { releaseStaleDraft = resolve; });
      return route.fulfill({ json: { draft_id: 'draft-race', project_id: 'project-a', revision: 1, goal_snapshot: 'recovered result', status: 'approved', draft_hash: 'hash', version: 1, stages: [], source_pack_key: 'seed', source_pack_version: 1 } });
    });
    await sameScopePage.addInitScript(() => localStorage.setItem('studyplan-run:project-a', 'run-late-draft'));
    await sameScopePage.goto(`${BASE}/tests/run-detail-scope.html`);
    await sameScopePage.getByRole('alert').filter({ hasText: 'result unavailable' }).waitFor();
    assert.equal(await sameScopePage.getByRole('button', { name: '生成学习草案 →', exact: true }).isDisabled(), true,
      'result read failure must retain the lifecycle block');
    assert.equal(await sameScopePage.evaluate(() => localStorage.getItem('studyplan-run:project-a')), 'run-late-draft');
    await sameScopePage.locator('form').evaluate(form => form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })));
    assert.equal(sameScopeGenerateCalls, 0, 'failed result recovery must not generate or replay');
    await sameScopePage.getByRole('button', { name: '刷新运行状态', exact: true }).click();
    await staleDraftStarted;
    assert.equal(await sameScopePage.locator('form .btn.primary').isDisabled(), true, 'generation stays blocked while a selected run result is still loading');
    await sameScopePage.locator('form').evaluate(form => form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })));
    assert.equal(sameScopeGenerateCalls, 0, 'pending result recovery must not dispatch a new generation');
    releaseStaleDraft();
    await sameScopePage.getByText('已确认草案', { exact: true }).waitFor();
    assert.equal(await sameScopePage.getByRole('button', { name: '生成学习草案 →', exact: true }).isDisabled(), false, 'completed result verification releases the lifecycle block');
    await sameScopePage.close();

    // An old manual-read action must not restore its error/busy state after a
    // scope switch and a successful run read in the new scope.
    const actionPage = await browser.newPage();
    actionPage.setDefaultTimeout(5000);
    let actionRunReads = 0, enteredActionRead, releaseActionRead;
    const actionReadStarted = new Promise(resolve => { enteredActionRead = resolve; });
    await actionPage.route('**/api/v1/plans/current?**', route => route.fulfill({ status: 404, json: {} }));
    await actionPage.route('**/api/v1/plan-changes/context?**', route => route.fulfill({ status: 404, json: {} }));
    await actionPage.route('**/api/v1/runs/run-action-a?**', async route => {
      actionRunReads++;
      if (actionRunReads === 1) return route.fulfill({ json: { run_id: 'run-action-a', status: 'reconciliation_required', next_action: 'reconcile', version: 1, result_ref: null, error: null, progress: null } });
      enteredActionRead();
      await new Promise(resolve => { releaseActionRead = resolve; });
      return route.fulfill({ status: 503, json: { message: 'stale action error' } });
    });
    await actionPage.route('**/api/v1/runs/run-action-b?**', route => route.fulfill({ json: { run_id: 'run-action-b', status: 'succeeded', next_action: 'none', version: 2, result_ref: null, error: null, progress: null } }));
    await actionPage.addInitScript(() => {
      localStorage.setItem('studyplan-run:project-a', 'run-action-a');
      localStorage.setItem('studyplan-run:project-b', 'run-action-b');
    });
    await actionPage.goto(`${BASE}/tests/run-detail-scope.html`);
    await actionPage.getByRole('button', { name: '刷新运行状态', exact: true }).click();
    await actionReadStarted;
    await actionPage.getByRole('button', { name: '切换测试作用域' }).click();
    await actionPage.getByText('生成已完成', { exact: true }).waitFor();
    releaseActionRead();
    await actionPage.waitForTimeout(100);
    assert.equal(await actionPage.getByRole('alert').count(), 0, 'stale action error must not surface in the new scope');
    assert.equal(await actionPage.getByRole('button', { name: '生成学习草案 →', exact: true }).isDisabled(), false, 'stale action cannot leave the new scope busy');
    await actionPage.close();

    // Fence a draft's second awaited read too: its run and draft responses may
    // be valid when received, but the current-plan lookup can finish after scope changes.
    const draftPage = await browser.newPage();
    draftPage.setDefaultTimeout(5000);
    await draftPage.route('**/api/v1/plans/current?**', async route => {
      const query = new URL(route.request().url()).searchParams;
      if (holdDraftCurrent && query.get('project_id') === 'project-a') {
        enteredDraftCurrent();
        await new Promise(resolve => { releaseDraftCurrent = resolve; });
        return route.fulfill({ json: { project_id: 'project-a', revision: 91, goal_snapshot: 'stale plan' } });
      }
      return route.fulfill({ status: 404, json: {} });
    });
    await draftPage.route('**/api/v1/plan-changes/context?**', route => route.fulfill({ status: 404, json: {} }));
    await draftPage.route('**/api/v1/runs/run-draft?**', route => route.fulfill({ json: { run_id: 'run-draft', status: 'succeeded', next_action: 'review_draft', version: 3, result_ref: 'draft-a', error: null, progress: null } }));
    await draftPage.route('**/api/v1/runs/run-b?**', route => route.fulfill({ json: { run_id: 'run-b', status: 'succeeded', next_action: 'none', version: 2, result_ref: null, error: null, progress: null } }));
    await draftPage.route('**/api/v1/plans/drafts/draft-a?**', route => route.fulfill({ json: { draft_id: 'draft-a', project_id: 'project-a', revision: 3, goal_snapshot: 'stale draft target', status: 'awaiting_approval', draft_hash: 'hash', version: 1, stages: [], source_pack_key: 'seed', source_pack_version: 1 } }));
    holdDraftCurrent = true;
    await draftPage.addInitScript(() => {
      localStorage.setItem('studyplan-run:project-a', 'run-draft');
      localStorage.setItem('studyplan-run:project-b', 'run-b');
    });
    await draftPage.goto(`${BASE}/tests/run-detail-scope.html`);
    await Promise.race([draftCurrentStarted, new Promise((_, reject) => setTimeout(() => reject(new Error('draft current read was not reached')), 5000))]);
    await draftPage.getByRole('button', { name: '切换测试作用域' }).click();
    await draftPage.getByText('生成已完成', { exact: true }).waitFor();
    releaseDraftCurrent();
    await draftPage.waitForTimeout(100);
    assert.equal(await draftPage.getByText('检查与调整草案', { exact: true }).count(), 0, 'late current-plan lookup cannot apply a prior-scope draft');
    await draftPage.close();
    console.log('PASS: same mounted PlanningPage rejects a late detail response from a previous actor/project scope');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
