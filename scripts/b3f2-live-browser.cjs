// Explicitly authorized one-run cloud acceptance. Refuses a second dispatch.
const { chromium } = require('../frontend/node_modules/playwright-core');
const fs = require('node:fs');
const assert = require('node:assert/strict');
const tag = process.env.B3F2_LIVE_TAG || '';
assert.ok(!tag || /^[a-z0-9-]{1,32}$/.test(tag), 'Invalid evidence tag');
const output = 'docs/acceptance/b3f2/live' + (tag ? '/' + tag : '');
const journal = tag ? `.git/b3f2-live-${tag}-journal.json` : '.git/b3f2-live-journal.json';
const privateSession = tag ? `.git/b3f2-live-${tag}-browser-session.json` : '.git/b3f2-live-browser-session.json';
const goal = '学习 Agent 应用开发，具备基础 Python 经验，完成一个可验收的知识助手。覆盖 LLM API 与 Prompt、工具调用及结构化输出、LangGraph、RAG、MCP、上下文与记忆基础、评价和可靠性；保留开发环境与综合实践。';
(async () => {
  assert.equal(process.env.B3F2_AUTHORIZED_LIVE, '1', 'Explicit one-run authorization required');
  fs.mkdirSync(output, { recursive: true });
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  try {
    const resumed = fs.existsSync(journal);
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, ...(resumed ? { storageState: privateSession } : {}) });
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    const base = 'http://127.0.0.1:5173';
    const health = await (await page.request.get(base + '/healthz')).json();
    assert.equal(health.llm_provider, 'openai_compatible');
    await page.goto(base);
    await page.waitForLoadState('networkidle');
    if (!resumed) {
      await page.getByRole('button', { name: '注册', exact: true }).click();
      await page.getByLabel('用户名', { exact: true }).fill('云路线验收' + Date.now().toString().slice(-8));
      await page.getByLabel('密码', { exact: true }).fill('123456');
      await page.getByRole('button', { name: '注册并进入', exact: true }).click();
      await page.getByRole('heading', { name: '今天，从这里继续。', exact: true }).waitFor();
      await context.storageState({ path: privateSession });
      const session = await (await page.request.get(base + '/api/v1/session')).json();
      fs.writeFileSync(journal, JSON.stringify({ project: session.project_ids[0], dispatchIntent: true, goal, startedAt: new Date().toISOString() }));
      await page.getByRole('button', { name: '创建第一条计划 →', exact: true }).click();
      await page.getByRole('textbox', { name: '你想学会什么？', exact: true }).fill(goal);
      const generated = page.waitForResponse(r => r.url().includes('/api/v1/plans/generate?') && r.request().method() === 'POST', { timeout: 900000 });
      await page.getByRole('button', { name: '生成学习草案 →', exact: true }).click();
      console.log('One authorized generation dispatched; no redispatch on restart.');
      const response = await generated;
      assert.equal(response.status(), 202, await response.text());
      const data = await response.json();
      fs.writeFileSync(journal, JSON.stringify({ ...JSON.parse(fs.readFileSync(journal)), runId: data.run_id }));
    }
    const state = JSON.parse(fs.readFileSync(journal));
    assert.ok(state.runId, 'Dispatch outcome unknown: inspect retained server run; never generate again');
    const session = await (await page.request.get(base + '/api/v1/session')).json();
    assert.ok(session.project_ids.includes(state.project));
    const suffix = '?project_id=' + state.project;
    const get = async path => {
      const response = await page.request.get(base + '/api/v1/' + path + suffix);
      assert.equal(response.status(), 200, await response.text());
      return response.json();
    };
    const run = await get('runs/' + state.runId);
    fs.writeFileSync(`${output}/run.json`, JSON.stringify(run, null, 2));
    console.log(JSON.stringify({ runId: state.runId, status: run.status, nextAction: run.next_action }));
    if (run.status !== 'waiting_user' && run.status !== 'succeeded') {
      await page.screenshot({ path: `${output}/generation-result.png`, fullPage: true });
      throw new Error('Cloud run did not produce an approvable draft; inspect retained evidence, do not repeat calls');
    }
    const draft = await get('plans/drafts/' + run.result_ref);
    assert.equal(draft.source_pack_key, 'agent.application');
    assert.equal(draft.source_pack_version, 1);
    assert.ok(draft.stages.length > 2);
    assert.ok(draft.stage_resources.some(r => r.ordered_sections.length));
    await page.goto(base + '/#planning');
    await page.evaluate(({ project, runId }) => localStorage.setItem(`studyplan-run:${project}`, runId), state);
    await page.reload();
    await page.getByRole('textbox', { name: '阶段 1 标题', exact: true }).waitFor();
    await page.screenshot({ path: `${output}/draft.png`, fullPage: true });
    let plan;
    if (draft.status === 'awaiting_approval') {
      const response = await page.request.post(base + '/api/v1/plans/drafts/' + draft.draft_id + '/decision' + suffix, {
        headers: { 'X-CSRF-Token': session.csrf_token }, data: { decision: 'approve', expected_version: 0,
          draft_hash: draft.draft_hash, idempotency_key: 'b3f2-live-one-run' },
      });
      assert.equal(response.status(), 200, await response.text());
      plan = (await response.json()).plan;
    } else plan = await get('plans/current');
    assert.deepEqual(await get('plans/current'), plan);
    const workspace = await get('workspace');
    const required = JSON.parse(fs.readFileSync('backend/app/infrastructure/content/agent-application-v1.json')).required_node_keys;
    const keys = new Set(workspace.stages.flatMap(s => s.nodes.map(n => n.stable_key)));
    assert.ok(required.every(k => keys.has(k)));
    assert.ok(workspace.stages.every(s => s.units.length && s.tasks.length));
    assert.ok(workspace.stages.every(s => s.resources.every(r => r.node_ids.every(id => s.nodes.some(n => n.node_id === id)))));
    const first = workspace.stages[0];
    await page.evaluate(({ project, revision, stage, node, username }) => {
      localStorage.setItem(`studyplan-position:${username}:${project}:${revision}`, JSON.stringify({ stage, node }));
      localStorage.setItem('studyplan-panels', JSON.stringify({ nav: true, plan: true, assistant: false, assistantWidth: 430 }));
    }, { project: state.project, revision: plan.revision, stage: first.stage.stage_id, node: first.nodes[0].node_id, username: session.username });
    const widths = [];
    for (const width of [1366, 1440, 1920]) {
      await page.setViewportSize({ width, height: 1000 });
      await page.goto(base + '/#workspace');
      await page.reload();
      await page.getByRole('heading', { name: first.stage.title, exact: true, level: 1 }).waitFor();
      const sizes = await page.evaluate(() => ({ nav: document.querySelector('.global-nav').getBoundingClientRect().width,
        plan: document.querySelector('.plan-sidebar').getBoundingClientRect().width, overflow: document.documentElement.scrollWidth > innerWidth }));
      assert.ok(Math.abs(sizes.nav - width * .11) < 2 && Math.abs(sizes.plan - width * .17) < 2 && !sizes.overflow);
      assert.ok((await page.locator('.learning-pin').innerText()).includes(first.nodes[0].objectives[0]));
      await page.screenshot({ path: `${output}/workspace-${width}.png` });
      widths.push({ width, ...sizes });
    }
    const finalRun = await get('runs/' + state.runId);
    fs.writeFileSync(`${output}/example-plan.json`, JSON.stringify({ provider: 'openai_compatible', goal, run: finalRun, draft, plan, workspace }, null, 2));
    fs.writeFileSync(`${output}/browser-results.json`, JSON.stringify({ widths, errors, readback: true, requiredCoverage: true }, null, 2));
    console.log(JSON.stringify({ stageCount: plan.stages.length, nodeCount: keys.size, unitCount: plan.unit_links.length, taskCount: plan.task_links.length,
      reviewedAssignments: plan.stage_resources.filter(r => r.verification_status === 'reviewed').length, published: true, errors }));
  } finally { await browser.close(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
