// Browser Fake for generated finite route changes. All endpoints are local
// Playwright fulfillments: no database, external search or model provider.
const { chromium } = require('playwright-core');
const assert = require('node:assert/strict');
const BASE = process.env.STUDYPLAN_URL || 'http://127.0.0.1:5178';
const PROJECT = 'generated-route-project';

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  try {
    const page = await browser.newPage();
    page.setDefaultTimeout(6000);
    let generationCalls = [], routeCalls = [], confirmCalls = [], cancelCalls = [];
    let contextRevision = 5, unknownOnManualRead = false, plainReads = 0;
    const runReads = new Map(), proposals = new Map(), runDraft = new Map(), draftStates = new Map();
    const stages = [
      { stage_id: 'prefix', stable_key: 'prefix', title: '已完成基础', objective: '保留前置成果', order_index: 0, locked: true, inclusion: 'required' },
      { stage_id: 'future-old', stable_key: 'future-old', title: '旧未来阶段', objective: '旧目标内容', order_index: 1, locked: false, inclusion: 'required' },
      { stage_id: 'capstone', stable_key: 'capstone', title: '最终综合实践', objective: '最终验收', order_index: 2, locked: true, inclusion: 'required' },
    ];
    const makeDraft = (id, goal, title, objective, status = 'awaiting_approval', proposalId = null) => ({
      draft_id: id, project_id: PROJECT, revision: 6, status, draft_hash: `draft-hash-${id}`, version: 1,
      goal_snapshot: goal, goal_spec: null, source_pack_key: 'agent', source_pack_version: 1,
      change_preview_id: proposalId,
      stages: [stages[0], { stage_id: `${id}-future`, stable_key: 'new-future', title, objective, order_index: 1, locked: false, inclusion: 'required' }, stages[2]],
      stage_resources: [], validation_warnings: [],
    });
    const makePreview = (proposalId, operation, status, draft) => ({
      proposal_id: proposalId, status, draft, base_plan_id: 'plan-a', base_revision: contextRevision,
      operation, before_goal: '旧学习目标', after_goal: draft.goal_snapshot,
      before_stages: stages, before_stage_keys: stages.map(s => s.stable_key),
      after_stage_keys: draft.stages.map(s => s.stable_key), retained_stage_keys: ['prefix', 'capstone'],
      warnings: ['原路线与历史会保留'], preview_hash: `hash-${proposalId}`,
    });
    await page.route('**/api/v1/session', route => route.fulfill({ json: { username: 'owner-a', project_ids: [PROJECT], csrf_token: 'fake' } }));
    await page.route('**/healthz', route => route.fulfill({ json: { llm_provider: 'fake' } }));
    await page.route('**/api/v1/workspace?**', route => route.fulfill({ status: 404, json: {} }));
    await page.route('**/api/v1/plans/current?**', route => route.fulfill({ status: 404, json: {} }));
    await page.route('**/api/v1/plan-changes/context?**', route => route.fulfill({ json: {
      plan_id: 'plan-a', revision: contextRevision, goal: '旧学习目标', goal_spec: { target: '旧学习目标', scope: ['旧范围'] },
      regenerate_available: true, generation_max_requests: 13, stages,
    } }));
    await page.route('**/api/v1/plan-changes/generate?**', async route => {
      const body = route.request().postDataJSON();
      routeCalls.push(body);
      assert.equal(body.plan_id, 'plan-a');
      assert.equal(body.expected_version, contextRevision);
      assert.ok(body.idempotency_key);
      assert.equal(body.goal_spec, undefined, 'do not carry stale goal profile implicitly');
      if (body.operation === 'regenerate_future_plan') assert.equal(body.goal, '', 'regeneration retains the stored goal');
      if (body.operation === 'change_goal') assert.ok(body.goal, 'goal change requires an explicit new target');
      const id = `change-run-${routeCalls.length}`;
      runDraft.set(id, `change-draft-${routeCalls.length}`);
      draftStates.set(`change-draft-${routeCalls.length}`, 'awaiting_approval');
      runReads.set(id, 0);
      return route.fulfill({ status: 202, json: { run_id: id, status_url: `/api/v1/runs/${id}` } });
    });
    await page.route('**/api/v1/plans/generate?**', async route => {
      generationCalls.push(route.request().postDataJSON());
      return route.fulfill({ status: 202, json: { run_id: `plain-run-${generationCalls.length}` } });
    });
    await page.route('**/api/v1/runs/**', async route => {
      const id = new URL(route.request().url()).pathname.split('/').at(-1);
      if (id.startsWith('plain-run-')) {
        plainReads++;
        if (plainReads === 1) return route.fulfill({ status: 503, json: { message: 'temporary read failure' } });
        return route.fulfill({ json: { run_id: id, status: 'cancelled', next_action: 'none', version: 2, result_ref: null, error: null, progress: null } });
      }
      if (unknownOnManualRead && id === 'change-run-2' && (runReads.get(id) || 0) > 0) return route.fulfill({ json: {
        run_id: id, status: 'future_status', next_action: 'wait', version: 9, result_ref: null, error: null, progress: null,
      } });
      const reads = (runReads.get(id) || 0) + 1;
      runReads.set(id, reads);
      const draftId = runDraft.get(id);
      const body = id === 'change-run-1'
        ? { run_id: id, status: reads === 1 ? 'queued' : 'succeeded', next_action: reads === 1 ? 'wait' : 'none', version: reads, result_ref: reads === 1 ? null : draftId, error: null, progress: null }
        : { run_id: id, status: 'succeeded', next_action: 'none', version: reads, result_ref: draftId, error: null, progress: null };
      return route.fulfill({ json: body });
    });
    await page.route('**/api/v1/plans/drafts/**', route => {
      const id = new URL(route.request().url()).pathname.split('/').at(-1);
      const index = id.endsWith('1') ? 1 : 2;
      return route.fulfill({ json: makeDraft(id, index === 1 ? '旧学习目标' : '新目标 C', index === 1 ? '未来新结构' : '目标调整后的结构', index === 1 ? '新建结构内容' : '按新目标调整内容', draftStates.get(id) || 'awaiting_approval', `proposal-${index}`) });
    });
    await page.route('**/api/v1/plan-changes/proposal-**?**', route => {
      const id = new URL(route.request().url()).pathname.split('/').at(-1);
      return route.fulfill({ json: proposals.get(id) });
    });
    await page.route('**/api/v1/plan-changes/proposal-1/confirm?**', async route => {
      const body = route.request().postDataJSON(); confirmCalls.push(body);
      const previous = proposals.get('proposal-1');
      const draft = { ...previous.draft, status: 'approved' };
      draftStates.set(draft.draft_id, 'approved');
      const value = makePreview('proposal-1', previous.operation, 'approved', draft);
      proposals.set('proposal-1', value); contextRevision++;
      return route.fulfill({ json: { preview: value, plan_id: 'plan-next', revision: contextRevision, created: true } });
    });
    await page.route('**/api/v1/plan-changes/proposal-2/cancel?**', async route => {
      const body = route.request().postDataJSON(); cancelCalls.push(body);
      const previous = proposals.get('proposal-2');
      draftStates.set(previous.draft.draft_id, 'cancelled');
      const value = makePreview('proposal-2', previous.operation, 'cancelled', { ...previous.draft, status: 'cancelled' });
      proposals.set('proposal-2', value);
      return route.fulfill({ json: { preview: value, plan_id: null, revision: null, created: false } });
    });
    // Provide proposal records when generation returns a route draft.
    page.on('requestfinished', async request => {
      if (!request.url().includes('/api/v1/plan-changes/generate')) return;
      const body = request.postDataJSON(), index = routeCalls.length;
      const draft = makeDraft(`change-draft-${index}`, body.operation === 'change_goal' ? body.goal : '旧学习目标', index === 1 ? '未来新结构' : '目标调整后的结构', index === 1 ? '新建结构内容' : '按新目标调整内容', 'awaiting_approval', `proposal-${index}`);
      proposals.set(`proposal-${index}`, makePreview(`proposal-${index}`, body.operation, 'awaiting_approval', draft));
    });

    await page.goto(`${BASE}/#planning`);
    const panel = page.getByRole('region', { name: '有限路线调整', exact: true });
    await panel.locator('summary').click();
    await panel.getByRole('button', { name: '重新生成未来阶段', exact: true }).click();
    await page.getByText('草案已生成 · 等待确认', { exact: true }).waitFor();
    assert.equal(routeCalls.length, 1);
    assert.equal(routeCalls[0].operation, 'regenerate_future_plan');
    assert.equal(runReads.get('change-run-1'), 2, '202 run uses PlanningPage queued → succeeded polling');
    assert.equal(await page.evaluate(project => localStorage.getItem(`studyplan-run:${project}`), PROJECT), 'change-run-1');
    const preview = panel.getByRole('region', { name: '路线调整预览', exact: true });
    await preview.waitFor();
    assert.match(await preview.innerText(), /旧目标内容|新建结构内容/);
    assert.match(await preview.innerText(), /保留前置成果/);
    assert.match(await preview.innerText(), /新建结构内容/);
    assert.equal(await page.getByRole('button', { name: '确认并发布路线', exact: true }).count(), 0, 'protected route draft bypasses ordinary DraftDecision');
    const saved = await page.evaluate(() => Object.entries(localStorage).filter(([key]) => key.startsWith('studyplan-plan-change:')));
    assert.equal(saved.length, 1); assert.equal(saved[0][1], 'proposal-1');

    await page.reload();
    const recovered = page.getByRole('region', { name: '有限路线调整', exact: true });
    await recovered.locator('summary').click();
    const recoveredPreview = recovered.getByRole('region', { name: '路线调整预览', exact: true });
    await recoveredPreview.waitFor();
    assert.equal(routeCalls.length, 1, 'reload never repeats generated route POST');
    assert.match(await recoveredPreview.innerText(), /调整前|旧目标内容/);
    await recovered.getByRole('checkbox', { name: '我已理解新版学习进度会重置', exact: true }).check();
    await recovered.getByRole('button', { name: '确认发布新路线', exact: true }).click();
    await page.getByText('新路线已发布。', { exact: true }).waitFor();
    assert.equal(confirmCalls.length, 1);
    assert.equal(confirmCalls[0].acknowledge_reset, true);
    assert.equal(confirmCalls[0].preview_hash, 'hash-proposal-1');
    await page.waitForFunction(() => {
      const button = [...document.querySelectorAll('button')].find(item => item.textContent.trim() === '生成学习草案 →');
      return button && !button.disabled;
    });

    // A 202 whose first status GET fails remains recoverable by ID and never
    // triggers another generation POST during manual status recovery.
    await page.locator('form').evaluate(form => form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })));
    await page.getByText('已提交，待读回', { exact: true }).waitFor();
    assert.equal(generationCalls.length, 1);
    assert.equal(await page.evaluate(project => localStorage.getItem(`studyplan-run:${project}`), PROJECT), 'plain-run-1');
    await page.getByRole('button', { name: '手动读取运行状态', exact: true }).click();
    await page.getByText('运行已取消', { exact: true }).waitFor();
    assert.equal(generationCalls.length, 1, 'manual status recovery never repeats the POST');

    // Goal changes use the new target and do not silently send the old GoalSpec.
    await recovered.getByRole('textbox', { name: '新的学习目标', exact: true }).fill('新目标 C');
    await recovered.getByRole('button', { name: '生成目标调整草案', exact: true }).click();
    await page.getByText('草案已生成 · 等待确认', { exact: true }).waitFor();
    assert.equal(routeCalls.length, 2);
    assert.equal(routeCalls[1].operation, 'change_goal'); assert.equal(routeCalls[1].goal, '新目标 C');
    const preview2 = recovered.getByRole('region', { name: '路线调整预览', exact: true });
    await preview2.waitFor();
    assert.match(await preview2.innerText(), /旧学习目标/);
    assert.match(await preview2.innerText(), /新目标 C/);
    await recovered.getByRole('button', { name: '取消路线调整', exact: true }).click();
    await page.getByText('路线调整已取消。', { exact: true }).waitFor();
    assert.equal(cancelCalls.length, 1);
    await page.waitForFunction(() => {
      const button = [...document.querySelectorAll('button')].find(item => item.textContent.trim() === '生成学习草案 →');
      return button && !button.disabled;
    });

    unknownOnManualRead = true;
    await page.getByRole('button', { name: '刷新运行状态', exact: true }).click();
    await page.getByText('运行状态需要核对', { exact: true }).waitFor();
    assert.equal(await page.getByRole('button', { name: '生成学习草案 →', exact: true }).isDisabled(), true);
    const generationsBeforeUnknownSubmit = generationCalls.length;
    await page.locator('form').evaluate(form => form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })));
    assert.equal(generationCalls.length, generationsBeforeUnknownSubmit, 'unknown status blocks normal generation too');
    console.log('PASS: generated route 202 recovery, protected before/after draft diff, single publisher confirmation/cancel, goal operation, ID-only cache and unknown-run generation block');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
