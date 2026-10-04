const { chromium } = require('playwright-core');
const assert = require('node:assert/strict');

// Fake workspace fixture only. Real persisted PG/Edge acceptance is a separate evidence layer.
(async () => {
  const browser = await chromium.launch({ channel: process.env.STUDYPLAN_BROWSER_CHANNEL || 'msedge', headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    const errors = [], unexpected = [];
    page.on('pageerror', error => errors.push(error.message));
    page.setDefaultTimeout(7000);
    const stage = { stage_id: 'a2', stable_key: 'stage.v612.a2', title: 'A2 工具职责与边界',
      section_kind: 'core', order_index: 0, objective: '按受控工具范围学习，不增加正式任务' };
    const canonical = { node_id: 'canonical-a2', stable_key: 'node.v62.agent.application.a2', title: '工具调用与执行边界',
      objectives: ['保留受控范围和原有验收'], prerequisite_ids: [], child_ids: [], node_type: 'concept', source_status: 'reviewed' };
    const units = [
      { unit_id: 'unit-z', title: '工具职责与注册', objectives: ['说明何时由程序执行工具'], node_ids: [canonical.node_id] },
      { unit_id: 'unit-a', title: '参数与权限边界', objectives: ['区分合法参数与未授权动作'], node_ids: [canonical.node_id] },
      { unit_id: 'unit-m', title: '错误、超时与执行证据', objectives: ['区分失败、未执行和已完成', '<img src=x onerror="window.injected=true">'], node_ids: [canonical.node_id] },
    ];
    const stageWorkspaces = [{ stage, nodes: [canonical], units, tasks: [{ task_id: 'task-a2', title: '原有受控工具实践', goal: '检查正常与失败路径', acceptance: ['保留原有正式验收'], status: 'pending' }], resources: [] }];
    for (const [id, title] of [
      ['whole', '小型 Agent 源码核心学习'],
      ['tutorial', 'RAG 专项教程：数据入库'],
      ['mature', '成熟工程：检索与引用切片'],
    ]) stageWorkspaces.push({ stage: { ...stage, stage_id: id, stable_key: `stage.${id}`, title, order_index: stageWorkspaces.length }, nodes: [], units: [], resources: [], tasks: [] });
    const workspace = { plan: { plan_id: 'plan-v612-fixture', project_id: 'project', revision: 1, goal_snapshot: 'Fake 完整 Agent + RAG 教学样本',
      source_pack_key: 'agent.application', stages: stageWorkspaces.map(item => item.stage), extensions: [
        { extension_id: 'whole-mode', stage_id: 'whole', topic: '项目学习：待选核心', concepts: [], thinking_prompts: [], links: [], guidance: '学习方式：whole_core', required: false, order_index: 0 },
      ] },
      stages: stageWorkspaces, total_units: 3, completed_units: 0 };
    await page.route('**/*', route => {
      const url = new URL(route.request().url());
      if (!['127.0.0.1', 'localhost'].includes(url.hostname)) { unexpected.push(url.href); return route.abort(); }
      return route.continue();
    });
    await page.route('**/api/v1/**', route => { unexpected.push(route.request().method() + ' ' + route.request().url()); return route.abort(); });
    await page.route('**/api/v1/session', route => route.fulfill({ json: { username: 'v612 Fixture', project_ids: ['project'], csrf_token: 'fixture' } }));
    await page.route('**/api/v1/workspace?**', route => route.fulfill({ json: workspace }));
    await page.route('**/api/v1/resource-changes/catalog?**', route => route.fulfill({ json: [] }));
    await page.route('**/api/v1/resources/selections?**', route => route.fulfill({ json: [] }));
    await page.route('**/api/v1/preferences?**', route => route.fulfill({ json: {
      project: null, unit: null, node: null, effective: null, invalid_scopes: [],
      scope_versions: { project: 0, unit: 0, node: 0 },
    } }));
    await page.route('**/healthz', route => route.fulfill({ json: { fake_llm: true } }));
    const url = (process.env.STUDYPLAN_URL || 'http://127.0.0.1:5173') + '/#path';
    async function enter(index) {
      await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
      await page.locator('.timeline-stage').nth(index).getByRole('button', { name: '进入学习 →', exact: true }).click();
    }
    await enter(0);
    const region = page.getByRole('region', { name: '本阶段学习单元', exact: true });
    await region.waitFor();
    assert.deepEqual(await region.locator('.learning-unit > h3').allTextContents(), units.map(unit => unit.title), 'persisted order, not IDs or alphabetical title order');
    assert.equal(await region.getByRole('button', { name: canonical.title, exact: true }).count(), 3, 'three units visibly reuse one canonical');
    for (const unit of units) for (const objective of unit.objectives) await region.getByText(objective, { exact: true }).waitFor();
    assert.equal(await region.locator('img').count(), 0, 'teaching text remains escaped');
    await region.getByRole('button', { name: canonical.title, exact: true }).nth(1).click();
    await page.locator('.node-detail').getByRole('heading', { name: canonical.title, exact: true }).waitFor();
    await page.getByRole('button', { name: '资料偏好', exact: true }).click();
    const dialog = page.getByRole('dialog', { name: '资料偏好', exact: true });
    assert.equal(await dialog.getByLabel('资料所属学习单元').inputValue(), 'unit-a', 'associated knowledge picks the correct unit context');
    await dialog.getByRole('button', { name: '关闭资料偏好', exact: true }).click();
    assert.equal(await page.locator('.practice-preview article').count(), 1, 'unit count creates no extra formal task');
    assert.equal(await region.getByRole('checkbox').count(), 0);
    assert.equal(await region.getByRole('button', { name: /完成|掌握|总结/ }).count(), 0, 'no unit completion/mastery/daily summary controls');
    const snapshot = await region.innerText();
    await page.reload();
    await region.waitFor();
    assert.equal(await region.innerText(), snapshot, 'refresh preserves teaching presentation');
    await page.setViewportSize({ width: 390, height: 844 });
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true, '390px fits');
    if (process.env.STUDYPLAN_SCREENSHOT) await page.screenshot({ path: process.env.STUDYPLAN_SCREENSHOT, fullPage: true });
    for (const [index, label] of [[1, '小型源码 · 核心整体学习'], [2, '专项教程'], [3, '成熟工程 · 目标切片']]) {
      await enter(index);
      assert.equal(await page.getByLabel('阶段学习类型', { exact: true }).innerText(), label);
      await region.getByText('本阶段尚无学习单元。', { exact: true }).waitFor();
    }
    assert.equal(workspace.stages[0].nodes.length, 1);
    assert.deepEqual(errors, []);
    assert.deepEqual(unexpected, [], 'ordinary reads emit no mutation, generation or external request');
    console.log('PASS Fake Edge: ordered A2 three units/one canonical, objectives, escaped text, linked knowledge navigation, original task count, no extra gates, refresh, 390px, distinct route roles');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
