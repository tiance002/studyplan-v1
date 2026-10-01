// Real owned HTTP/PG; supplied CLI report, explicit synthetic-account human decisions.
const { chromium } = require('playwright-core');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '../..');
const directory = path.join(root, 'var/v2-g4');
const acceptance = 'v2-g4-20261002-01';
assert.equal(process.env.V2_SUBMISSION_ACCEPTANCE, acceptance);
const readFile = (name, dir = directory) => JSON.parse(fs.readFileSync(path.join(dir, name), 'utf8'));
const exists = name => fs.existsSync(path.join(directory, name));
const write = (name, value) => fs.writeFileSync(path.join(directory, name), JSON.stringify(value, null, 2), { flag: 'wx' });
assert.ok(!exists('submission-real.json'), 'Completed acceptance must not be replayed');
assert.ok(!exists('submission-real-save-1-intent.json'), 'Read prior request intent and persisted result before continuing');
const credentials = readFile('v2-g1-20261001-01-browser-private.json', path.join(root, 'var/v2-g1'));
const context = readFile('submission-real-context.json');
assert.equal(context.acceptance_id, acceptance);
const toolReport = readFile('external-tool-report.json');
const priorPrompt = readFile('prompt-confirmed-real.json', path.join(root, 'var/v2-g3'));
const priorSummary = readFile('summary-real.json', path.join(root, 'var/v2-g3'));
const quota = folder => fs.readdirSync(path.join(root, '.git', folder)).filter(name => /^request-\d+\.json$/.test(name)).length;

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1450, height: 1050 }, permissions: ['clipboard-read', 'clipboard-write'] });
    const errors = [], forbidden = [];
    let saves = 0, decisions = 0;
    page.on('pageerror', () => errors.push('pageerror'));
    page.on('dialog', dialog => dialog.accept());
    await page.route('**/api/v1/**', route => {
      const request = route.request(), url = new URL(request.url());
      if (!['GET', 'HEAD', 'OPTIONS'].includes(request.method()) && !url.pathname.startsWith('/api/v1/auth/') && !url.pathname.startsWith('/api/v1/submissions')) {
        forbidden.push(url.pathname);
        return route.abort();
      }
      if (request.method() === 'POST' && url.pathname === '/api/v1/submissions') {
        saves++;
        write(`submission-real-save-${saves}-intent.json`, { acceptance_id: acceptance, body: request.postDataJSON() });
      }
      if (request.method() === 'POST' && url.pathname.endsWith('/decision')) {
        decisions++;
        write(`submission-real-decision-${decisions}-intent.json`, { acceptance_id: acceptance, submission_id: url.pathname.split('/')[4], body: request.postDataJSON() });
      }
      return route.continue();
    });
    await page.goto((process.env.STUDYPLAN_URL || 'http://127.0.0.1:5175') + '/#practice');
    await page.getByLabel('用户名', { exact: true }).fill(credentials.username);
    await page.getByLabel('密码', { exact: true }).fill(credentials.password);
    const loginResponse = page.waitForResponse(response => new URL(response.url()).pathname === '/api/v1/auth/login' && response.request().method() === 'POST');
    await page.getByRole('button', { name: '登录学习空间', exact: true }).click();
    assert.equal((await loginResponse).status(), 200);
    await page.getByRole('textbox', { name: '方案与 Prompt 原文', exact: true }).waitFor();
    const read = url => page.evaluate(async value => {
      const response = await fetch(value, { credentials: 'include' });
      if (!response.ok) throw new Error('Owned GET failed: ' + response.status);
      return response.json();
    }, url);
    const scope = '?project_id=' + encodeURIComponent(context.project_id);
    const workspace = await read('/api/v1/workspace' + scope);
    assert.equal(workspace.plan.revision, 3);
    const practice = await read('/api/v1/practice-changes/context' + scope);
    const task = practice.tasks.find(value => value.title === '自选交付：可检查的 Agent 调试记录');
    assert.ok(task && task.status === 'pending');
    const targetQuery = '&' + new URLSearchParams({ plan_id: practice.plan_id, stage_id: task.stage_id, task_id: task.task_id });
    const historyUrls = [
      ...[priorPrompt.original_revision_id, priorPrompt.newer_revision_id].map(id => '/api/v1/prompts/revisions/' + id + scope),
      ...[priorSummary.original_attempt_id, priorSummary.newer_attempt_id].map(id => '/api/v1/summaries/attempts/' + id + scope),
      ...[priorPrompt.raw_export_id, priorPrompt.implementation_export_id].map(id => '/api/v1/prompts/exports/' + id + scope),
      '/api/v1/exposures' + scope + '&plan_id=' + encodeURIComponent(practice.plan_id),
    ];
    const before = { workspace, task, history: await Promise.all(historyUrls.map(read)), thread: await read('/api/v1/submissions' + scope + targetQuery), outcomes: await read('/api/v1/outcomes' + scope) };
    assert.equal(before.thread.version, 0);
    write('submission-real-before.json', before);
    await page.getByLabel('实践所属阶段').selectOption(task.stage_id);
    await page.getByLabel('实践任务', { exact: true }).selectOption(task.task_id);
    const panel = page.getByRole('region', { name: '成果提交与人工验收', exact: true });
    const editor = panel.getByLabel('成果说明原文', { exact: true });
    const note1 = '  初次提交：我已设计一个最小工具调用，但尚未提供实际输入输出。\n先保存原文，等待补充证据。\n\t';
    await editor.fill(note1);
    await panel.getByLabel('成果资料分类').selectOption('project_description');
    const save1Response = page.waitForResponse(response => new URL(response.url()).pathname === '/api/v1/submissions' && response.request().method() === 'POST');
    await panel.getByRole('button', { name: '保存成果与证据', exact: true }).click();
    const save1Http = await save1Response;
    assert.equal(save1Http.status(), 200);
    const saved1 = await save1Http.json();
    write('submission-real-save-1.json', saved1);
    assert.equal(saved1.submission.note, note1);
    assert.equal(saved1.submission.evidence_grade, 'insufficient');
    assert.equal(saved1.thread.task.status, 'awaiting_evidence');
    assert.equal(saved1.thread.task_version, 2);
    let detail = panel.locator('.submission-detail:visible');
    await detail.getByText('证据不足，尚不能人工确认通过', { exact: true }).waitFor();
    await detail.getByLabel('人工决定', { exact: true }).selectOption('needs_more_evidence');
    await detail.getByLabel('人工决定理由').fill('当前只有设计自述，请补实际成功输入输出、失败结果和未执行范围。');
    const decision1Response = page.waitForResponse(response => new URL(response.url()).pathname.endsWith('/' + saved1.submission.submission_id + '/decision'));
    await detail.getByRole('button', { name: '记录人工决定', exact: true }).click();
    const decision1Http = await decision1Response;
    assert.equal(decision1Http.status(), 200);
    const decided1 = await decision1Http.json();
    write('submission-real-decision-1.json', decided1);
    assert.equal(decided1.task_status, 'awaiting_evidence');
    assert.equal(decided1.task_version, 2);
    await detail.getByText('人工决定：需要补充证据', { exact: true }).waitFor();
    const note2 = '  补充成果🙂：本机提供最小 sum 工具的成功与失败记录。\n这份报告由外部 CLI 提供，平台未执行代码。\nAgent 集成和公网部署仍待实施。\n\t';
    await editor.fill(note2);
    await panel.getByLabel('成果资料分类').selectOption('evaluation');
    await panel.getByLabel('补充到已有成果').selectOption(saved1.submission.submission_id);
    await panel.getByRole('button', { name: '添加证据', exact: true }).click();
    const evidence1 = panel.getByRole('group', { name: '证据 1', exact: true });
    await evidence1.getByLabel('证据类别').selectOption('external_report');
    await evidence1.getByLabel('证据标题').fill('  本机工具输入输出与失败报告  ');
    const reportText = '  ' + JSON.stringify(toolReport, null, 2) + '\n\t';
    await evidence1.getByLabel('证据原文').fill(reportText);
    await panel.getByRole('button', { name: '添加证据', exact: true }).click();
    const evidence2 = panel.getByRole('group', { name: '证据 2', exact: true });
    await evidence2.getByLabel('证据类别').selectOption('user_statement');
    await evidence2.getByLabel('证据标题').fill('未实施范围声明');
    await evidence2.getByLabel('证据原文').fill('Agent/model 集成、公开部署、外部仓库执行仍待实施。本次只有最小工具 CLI 观察。');
    const save2Response = page.waitForResponse(response => new URL(response.url()).pathname === '/api/v1/submissions' && response.request().method() === 'POST');
    await panel.getByRole('button', { name: '保存成果与证据', exact: true }).click();
    const save2Http = await save2Response;
    assert.equal(save2Http.status(), 200);
    const saved2 = await save2Http.json();
    write('submission-real-save-2.json', saved2);
    assert.equal(saved2.submission.note, note2);
    assert.equal(saved2.submission.evidence[0].content, reportText);
    assert.equal(saved2.submission.parent_submission_id, saved1.submission.submission_id);
    assert.equal(saved2.submission.evidence_grade, 'reported');
    assert.equal(saved2.thread.version, 2);
    assert.equal(saved2.thread.task_version, 2);
    assert.equal(saved2.submission.task_snapshot.plan_revision, 3);
    assert.deepEqual(saved2.submission.task_snapshot.task.acceptance, task.acceptance);
    detail = panel.locator('.submission-detail:visible');
    await detail.getByLabel('人工决定', { exact: true }).selectOption('accepted');
    await detail.getByLabel('人工决定理由').fill('测试账号逐项对照外部 CLI 报告和未实施声明，人工确认本任务的两条要求；不表示平台实测或完整 Agent 已完成。');
    const acceptButton = detail.getByRole('button', { name: '记录人工决定', exact: true });
    assert.equal(await acceptButton.isEnabled(), false);
    const observations = ['输入 [2,3] 输出5；输入 ["2",3] 返回 Every value must be an integer，记录了成功与失败。', 'Agent/model 集成、公开部署、外部仓库执行均明确标为待实施。'];
    for (let index = 0; index < task.acceptance.length; index++) {
      const criterion = detail.getByRole('group', { name: `验收要求 ${index + 1}`, exact: true });
      await criterion.getByLabel(`选择证据 ${index + 1}`).check();
      await criterion.getByLabel('实际观察').fill(observations[index]);
    }
    assert.equal(await acceptButton.isEnabled(), false);
    await detail.getByLabel('我理解这是人工确认，平台没有独立运行代码或核验来源').check();
    const decision2Response = page.waitForResponse(response => new URL(response.url()).pathname.endsWith('/' + saved2.submission.submission_id + '/decision'));
    await acceptButton.click();
    const local = '  人工决定后继续编辑的未保存成果说明。\n不要覆盖这段原文。\n\t';
    await editor.fill(local);
    const decision2Http = await decision2Response;
    assert.equal(decision2Http.status(), 200);
    const decided2 = await decision2Http.json();
    write('submission-real-decision-2.json', decided2);
    await detail.getByText('人工确认通过（未平台实测）', { exact: true }).waitFor();
    assert.equal(decided2.task_status, 'accepted');
    assert.equal(decided2.task_version, 3);
    assert.equal(decided2.submission.evidence_grade, 'reported');
    assert.equal(decided2.submission.review.reviewer_kind, 'user');
    assert.equal(decided2.submission.review.coverage.length, 2);
    assert.equal(await editor.inputValue(), local);
    await detail.getByRole('button', { name: '复制已保存成果原文', exact: true }).click();
    const clipboard = await page.evaluate(() => navigator.clipboard.readText());
    assert.equal(process.platform === 'win32' ? clipboard.replace(/\r\n/g, '\n') : clipboard, note2);
    assert.deepEqual(await Promise.all(historyUrls.map(read)), before.history);
    assert.deepEqual(await read('/api/v1/submissions/' + saved1.submission.submission_id + scope), decided1.submission);
    await page.getByRole('button', { name: '读取成果资料归档', exact: true }).click();
    const archive = page.getByRole('region', { name: '成果资料归档', exact: true });
    await archive.getByRole('heading', { name: '评估', exact: true }).waitFor();
    await archive.getByRole('button', { name: /人工确认通过，未平台实测/ }).click();
    await archive.getByRole('article', { name: '所选成果详情', exact: true }).getByText(note2, { exact: true }).waitFor();
    assert.equal(await archive.getByText('待补充', { exact: true }).count(), 5);
    assert.equal(await editor.inputValue(), local);
    await archive.scrollIntoViewIfNeeded();
    await page.screenshot({ path: path.join(directory, 'submission-real-archive.png'), fullPage: true });
    await panel.scrollIntoViewIfNeeded();
    await page.screenshot({ path: path.join(directory, 'submission-real.png'), fullPage: true });
    await page.reload();
    await page.getByLabel('实践所属阶段').selectOption(task.stage_id);
    await page.getByLabel('实践任务', { exact: true }).selectOption(task.task_id);
    await panel.getByLabel('选择已保存成果').selectOption(saved1.submission.submission_id);
    await panel.locator('.submission-detail:visible').getByText(note1, { exact: true }).waitFor();
    await panel.getByLabel('选择已保存成果').selectOption(saved2.submission.submission_id);
    await panel.locator('.submission-detail:visible').getByText('人工确认通过（未平台实测）', { exact: true }).waitFor();
    const after = { workspace: await read('/api/v1/workspace' + scope), thread: await read('/api/v1/submissions' + scope + targetQuery), outcomes: await read('/api/v1/outcomes' + scope) };
    write('submission-real-after.json', after);
    assert.equal(after.thread.task.status, 'accepted');
    assert.equal(after.thread.submissions.length, 2);
    assert.deepEqual(await Promise.all(historyUrls.map(read)), before.history);
    assert.equal(quota('v2-paid-quota-20261001'), 23);
    assert.equal(quota('v2-search-quota-20261001'), 2);
    assert.equal(saves, 2); assert.equal(decisions, 2);
    assert.deepEqual(errors, []); assert.deepEqual(forbidden, []);
    const result = { status: 'PASS', acceptance_id: acceptance,
      source: 'Chrome + real loopback HTTP + retained owned PG; supplied CLI report and explicit synthetic-account manual decisions',
      project_id: context.project_id, plan_id: practice.plan_id, task_id: task.task_id,
      initial_submission_id: saved1.submission.submission_id, supplemental_submission_id: saved2.submission.submission_id,
      note_only_insufficient: true, explicit_needs_more_evidence: true, immutable_supplement: true,
      frozen_criteria: true, actual_external_cli_report: true, platform_execution: false, source_checked: false,
      explicit_coverage_and_ack: true, manual_accepted_reported: true, task_version: after.thread.task_version,
      originals_and_learning_history_unchanged: true, local_edit_preserved: true,
      clipboard_exact: clipboard === note2, clipboard_lf_equivalent: true, outcome_groups: 7,
      empty_groups_waiting: 5, reload_historical_and_latest: true, owner_product_acceptance: 'NOT RUN',
      model_requests: 23, search_requests: 2, new_model_requests: 0, new_search_requests: 0 };
    write('submission-real.json', result);
    console.log(JSON.stringify(result));
  } finally { await browser.close(); }
})().catch(error => {
  if (!exists('submission-real-failure.json')) write('submission-real-failure.json', { status: 'FAIL', acceptance_id: acceptance, error: String(error) });
  console.error('FAIL: owned manual submission observation. Preserve intents; inspect exact saved receipt and task before any additional POST.');
  process.exitCode = 1;
});
