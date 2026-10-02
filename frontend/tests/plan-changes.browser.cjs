// Explicit browser Fake: exercises real UI, with no provider/database/external calls.
const { chromium } = require('playwright-core');
const assert = require('node:assert/strict');
const BASE = process.env.STUDYPLAN_URL || 'http://127.0.0.1:5178';

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  try {
    const page = await browser.newPage();
    page.setDefaultTimeout(5000);
    let username = 'alice', project = 'project-a', conflict = true, delay = false, release, entered;
    const errors = [], previews = [], confirms = [], reads = [], proposals = new Map();
    let workspaceReads = 0;
    const stages = [
      { stage_id: 's0', stable_key: 'locked', title: '当前基础', order_index: 0, locked: true, inclusion: 'required' },
      { stage_id: 's1', stable_key: 'future-a', title: '未来实践', order_index: 1, locked: false, inclusion: 'required' },
      { stage_id: 's2', stable_key: 'future-b', title: '未来深化', order_index: 2, locked: false, inclusion: 'recommended' },
      { stage_id: 's3', stable_key: 'optional', title: '可选对照', order_index: 3, locked: false, inclusion: 'optional' },
      { stage_id: 's4', stable_key: 'capstone', title: '最终综合实践', order_index: 4, locked: true, inclusion: 'required' },
    ];
    page.on('pageerror', error => errors.push(error.message));
    await page.route('**/*', route => {
      if (!['127.0.0.1', 'localhost'].includes(new URL(route.request().url()).hostname)) return route.abort('blockedbyclient');
      return route.continue();
    });
    await page.route('**/api/v1/**', route => route.abort('blockedbyclient'));
    await page.route('**/api/v1/session', route => route.fulfill({ json: { username, project_ids: [project], csrf_token: 'fake' } }));
    await page.route('**/healthz', route => route.fulfill({ json: { llm_provider: 'fake' } }));
    await page.route('**/api/v1/workspace?**', route => { workspaceReads++; return route.fulfill({ status: 404, json: {} }); });
    await page.route('**/api/v1/auth/logout', route => route.fulfill({ json: { logged_out: true } }));
    await page.route('**/api/v1/auth/login', route => {
      username = route.request().postDataJSON().username;
      return route.fulfill({ json: { username, project_ids: [project], csrf_token: 'fake' } });
    });
    await page.route('**/api/v1/plan-changes**', async route => {
      const request = route.request(), url = new URL(request.url()), body = request.postDataJSON();
      const requestProject = url.searchParams.get('project_id');
      if (request.method() !== 'GET') assert.equal(requestProject, project);
      const id = url.pathname.split('/')[4];
      if (url.pathname.endsWith('/context')) return route.fulfill({ json: { plan_id: 'plan-' + requestProject, revision: 2, stages } });
      if (request.method() === 'GET') {
        reads.push({ username, project, id });
        const proposal = proposals.get(id);
        assert.equal(proposal.owner, username, 'never read another account proposal');
        assert.equal(proposal.project, requestProject, 'never read another project proposal');
        return route.fulfill({ json: proposal.value });
      }
      if (url.pathname.endsWith('/confirm')) {
        confirms.push(body);
        if (conflict) return route.fulfill({ status: 409, json: { message: '路线版本已变化，请核对原预览。' } });
        const proposal = proposals.get(id);
        proposal.value = { ...proposal.value, status: 'approved' };
        return route.fulfill({ json: { preview: proposal.value, plan_id: 'plan-new', revision: 3, created: true } });
      }
      if (url.pathname.endsWith('/cancel')) {
        const proposal = proposals.get(id);
        proposal.value = { ...proposal.value, status: 'cancelled' };
        return route.fulfill({ json: { preview: proposal.value, plan_id: null, revision: null, created: false } });
      }
      previews.push(body);
      const before = ['locked', 'future-a', 'future-b', 'optional', 'capstone'];
      const after = body.operation === 'remove_optional_topic' ? before.filter(key => key !== body.stage_key) : body.stage_keys;
      const proposal_id = 'proposal-' + previews.length;
      const value = { proposal_id, status: 'awaiting_approval', base_plan_id: body.plan_id, base_revision: 2,
        operation: body.operation, before_stage_keys: before, after_stage_keys: after, warnings: ['仅调整未来阶段'], preview_hash: 'hash-' + proposal_id,
        draft: { draft_id: 'draft-' + proposal_id, project_id: project, revision: 3, status: 'awaiting_approval', draft_hash: 'draft-hash', version: 1,
          stages: after.map((key, index) => ({ ...stages.find(stage => stage.stable_key === key), order_index: index, objective: '学习目标', section_kind: 'core' })),
          stage_resources: [], validation_warnings: [] },
      };
      proposals.set(proposal_id, { owner: username, project, value });
      if (delay) { entered(); await new Promise(resolve => { release = resolve; }); }
      return route.fulfill({ json: value });
    });
    await page.goto(BASE + '/#planning', { waitUntil: 'domcontentloaded', timeout: 30000 });
    const panel = page.getByRole('region', { name: '有限路线调整', exact: true });
    await panel.waitFor();
    await panel.locator('summary').click();
    const order = panel.getByRole('list', { name: '待预览阶段顺序', exact: true });
    await order.waitFor();
    assert.equal(await panel.getByRole('button', { name: '上移 当前基础', exact: true }).isDisabled(), true);
    assert.equal(await panel.getByRole('button', { name: '下移 当前基础', exact: true }).isDisabled(), true);
    assert.equal(await panel.getByRole('button', { name: '上移 最终综合实践', exact: true }).isDisabled(), true);
    assert.equal(await panel.getByRole('button', { name: '下移 最终综合实践', exact: true }).isDisabled(), true);
    assert.equal(await panel.getByRole('button', { name: '上移 未来实践', exact: true }).isDisabled(), true);
    assert.equal(await panel.getByRole('button', { name: '预览移除 未来实践', exact: true }).count(), 0);
    await panel.getByRole('button', { name: '上移 未来深化', exact: true }).click();
    assert.match(await order.innerText(), /当前基础[\s\S]*未来深化[\s\S]*未来实践[\s\S]*可选对照[\s\S]*最终综合实践/);
    await panel.getByRole('button', { name: '预览阶段顺序', exact: true }).evaluate(button => { button.click(); button.click(); });
    const preview = panel.getByRole('region', { name: '路线调整预览', exact: true });
    await preview.waitFor();
    assert.equal(previews.length, 1);
    assert.deepEqual(previews[0].stage_keys, ['locked', 'future-b', 'future-a', 'optional', 'capstone']);
    assert.equal(previews[0].operation, 'reorder_future_stage');
    assert.equal(previews[0].expected_version, 2);
    assert.ok(previews[0].idempotency_key);
    assert.equal(confirms.length, 0, 'preview never automatically publishes');
    assert.match(await preview.innerText(), /调整前[\s\S]*调整后/);
    assert.match(await preview.innerText(), /历史[\s\S]*保留/);
    assert.match(await preview.innerText(), /不自动继承/);
    const confirm = panel.getByRole('button', { name: '确认发布新路线', exact: true });
    assert.equal(await confirm.isDisabled(), true);
    await page.reload();
    await panel.locator('summary').click();
    await preview.waitFor();
    assert.equal(previews.length, 1, 'reload recovers proposal by GET, never POST');
    assert.equal(reads.length, 1);
    const cache = await page.evaluate(() => Object.entries(localStorage).filter(([key]) => key.startsWith('studyplan-plan-change:')));
    assert.equal(cache.length, 1);
    assert.equal(cache[0][1], 'proposal-1', 'cache stores only opaque proposal id');
    await panel.getByRole('checkbox', { name: '我已理解新版学习进度会重置', exact: true }).check();
    await confirm.evaluate(button => { button.click(); button.click(); });
    await panel.getByRole('alert').waitFor();
    assert.equal(confirms.length, 1, 'double click issues one confirm');
    assert.equal(confirms[0].acknowledge_reset, true);
    assert.equal(confirms[0].preview_hash, 'hash-proposal-1');
    assert.equal(await preview.count(), 1, '409 preserves preview');
    assert.equal(await confirm.isDisabled(), true);
    conflict = false;
    await panel.getByRole('button', { name: '读取调整预览', exact: true }).click();
    await panel.getByRole('checkbox', { name: '我已理解新版学习进度会重置', exact: true }).check();
    await confirm.click();
    await panel.getByText('新路线已发布。', { exact: true }).waitFor();
    assert.equal(confirms.length, 2);
    assert.deepEqual(confirms[0], confirms[1], 'same preview confirmation retries with original idempotency key');
    assert.ok(workspaceReads >= 3, 'publication refreshes workspace');

    // Another project under the same account must not recover the previous proposal.
    project = 'project-b';
    await page.reload();
    await panel.locator('summary').click();
    await order.waitFor();
    assert.equal(await preview.count(), 0);
    assert.equal(reads.length, 2);
    await panel.getByRole('button', { name: '预览移除 可选对照', exact: true }).click();
    await preview.waitFor();
    assert.equal(previews[1].operation, 'remove_optional_topic');
    assert.equal(previews[1].stage_key, 'optional');
    await panel.getByRole('button', { name: '取消路线调整', exact: true }).click();
    await panel.getByText('路线调整已取消。', { exact: true }).waitFor();

    // Fence a response that arrives after logout/new-account login.
    delay = true;
    const pending = new Promise(resolve => { entered = resolve; });
    await panel.getByRole('button', { name: '预览移除 可选对照', exact: true }).click();
    await pending;
    await page.getByRole('button', { name: '退出登录', exact: true }).click();
    await page.getByLabel('用户名', { exact: true }).fill('bob');
    await page.getByLabel('密码', { exact: true }).fill('password');
    await page.locator('.auth-card').getByRole('button', { name: '登录学习空间', exact: true }).click();
    await panel.waitFor();
    release();
    await panel.locator('summary').click();
    await order.waitFor();
    assert.equal(await preview.count(), 0, 'new account never sees late old-account preview');
    const afterLogout = await page.evaluate(() => Object.entries(localStorage).filter(([key]) => key.startsWith('studyplan-plan-change:')));
    assert.equal(afterLogout.some(([key]) => key.includes('bob')), false, 'late result cannot create new-account cache');
    assert.equal(afterLogout.some(([, value]) => value === 'proposal-3'), false, 'unmounted old scope cannot cache late result');
    assert.equal(reads.length, 2, 'new account does not read prior proposal');
    assert.deepEqual(errors, []);
    console.log('PASS: browser Fake locked/optional bounds, explicit preview/reset gate, GET reload, single/idempotent confirm, 409 retention, project/account isolation and logout late-response fence');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
