const { chromium } = require('playwright-core');
const assert = require('node:assert/strict');

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    const errors = [];
    const unexpected = [];
    page.on('pageerror', error => errors.push(error.message));
    page.setDefaultTimeout(7000);
    const makeStage = (id, index, title) => ({
      stage: { stage_id: id, stable_key: id, title, section_kind: 'core', order_index: index, objective: `理解 ${title}` },
      nodes: [{ node_id: `n-${id}`, stable_key: id, title: `${title}知识`, objectives: [], prerequisite_ids: [], child_ids: [], node_type: 'concept', source_status: 'reviewed' }],
      units: [], resources: [], tasks: [],
    });
    const stages = [makeStage('prior', 0, '工具调用'), makeStage('runtime', 1, '运行时学习'), makeStage('cloud', 2, '云服务学习')];
    stages[1].tasks = [{ task_id: 'restore', practice_project_id: 'own-project', stable_key: 'restore', title: '工作台失败恢复',
      goal: '检索失败可重试', acceptance: ['失败后状态可检查'], status: 'pending' }];
    for (const item of stages.slice(1)) item.resources = [{ assignment_id: `repo-${item.stage.stage_id}`, stage_id: item.stage.stage_id,
      role: 'case_study', media_type: 'repo', title: item.stage.title, ordered_sections: [], source_ref: 'reviewed', source_version: 1 }];
    const extension = (id, title, focus) => ({ extension_id: `e-${id}`, stage_id: id, topic: `项目学习：${title}`,
      concepts: [focus, '<img src=x onerror="window.injected=true">'], guidance: '为什么现在：先有自己的最小项目，再比较运行机制。\n学习深度：理解关键机制\n暂不涉及：训练系统',
      thinking_prompts: ['两种实现如何处理错误？', '可迁移哪一项机制？'], links: [`https://github.com/example/${id}`] });
    const workspace = { plan: { plan_id: 'study-plan', project_id: 'project', revision: 1, goal_snapshot: '构建资料工作台',
      goal_spec: { target: '工作台', scope: ['重点 RAG'], desired_depth: 'applied' }, source_pack_key: 'agent.application',
      stages: stages.map(item => item.stage), extensions: [extension('runtime', '运行时', '状态恢复'), extension('cloud', '云服务', '手工部署')] },
      stages, total_units: 0, completed_units: 0 };
    workspace.plan.extensions.push({ extension_id: 'comparison', stage_id: 'runtime', topic: '对比学习：Tool Calling', concepts: ['错误处理对照'],
      guidance: '已学：最小 Agent\n本次新增：恢复策略\n关系：COMPARE / DEEPEN', thinking_prompts: ['两种实现的重试边界在哪里？'] });
    await page.route('**/*', route => {
      const url = new URL(route.request().url());
      if (!['127.0.0.1', 'localhost'].includes(url.hostname)) { unexpected.push(url.href); return route.abort(); }
      return route.continue();
    });
    await page.route('**/api/v1/**', route => { unexpected.push(route.request().method() + ' ' + route.request().url()); return route.abort(); });
    await page.route('**/api/v1/session', route => route.fulfill({ json: { username: '项目学习', project_ids: ['project'], csrf_token: 'fixture' } }));
    await page.route('**/api/v1/workspace?**', route => route.fulfill({ json: workspace }));
    await page.route('**/api/v1/resource-changes/catalog?**', route => route.fulfill({ json: [] }));
    await page.route('**/healthz', route => route.fulfill({ json: { fake_llm: true } }));
    await page.goto((process.env.STUDYPLAN_URL || 'http://127.0.0.1:5173') + '/#path', { waitUntil: 'domcontentloaded', timeout: 30000 });
    assert.equal(await page.getByRole('button', { name: '课程改进建议', exact: true }).count(), 0);
    await page.locator('.timeline-stage').nth(1).getByRole('button', { name: '进入学习 →' }).click();
    const card = page.getByRole('region', { name: '项目源码学习' });
    await card.waitFor();
    assert.equal(await card.count(), 1);
    assert.equal(await card.locator('img').count(), 0);
    assert.equal(await card.getByRole('link').getAttribute('href'), 'https://github.com/example/runtime');
    const prompt = page.getByRole('textbox', { name: '源码学习 Prompt' });
    const initial = await prompt.inputValue();
    assert.ok(initial.includes('工具调用知识'));
    assert.ok(initial.includes('工作台失败恢复：检索失败可重试；验收：失败后状态可检查'));
    assert.ok(initial.includes('Agent 应用开发'));
    assert.ok(!initial.includes('云服务学习知识'), 'future stages are not prior knowledge');
    await page.getByRole('region', { name: '对比与思考提示' }).getByText('两种实现的重试边界在哪里？', { exact: true }).waitFor();
    // Exercise the real browser clipboard with granted local permission.
    await page.context().grantPermissions(['clipboard-read', 'clipboard-write']);
    await card.getByRole('button', { name: '复制给 AI', exact: true }).click();
    await card.getByText('已复制，可粘贴给外部 AI。', { exact: true }).waitFor();
    assert.equal((await page.evaluate(() => navigator.clipboard.readText())).replace(/\r\n/g, '\n'), initial);
    await page.evaluate(() => Object.defineProperty(navigator.clipboard, 'writeText', { configurable: true, value: () => Promise.reject(new Error('denied')) }));
    await card.getByRole('button', { name: '复制给 AI', exact: true }).click();
    await card.getByText('复制失败，已选中文本。请手动复制上方 Prompt。', { exact: true }).waitFor();
    assert.equal(await prompt.inputValue(), initial, 'fallback retains complete text');
    assert.equal(await prompt.evaluate(element => element.selectionEnd - element.selectionStart), initial.length);
    await page.setViewportSize({ width: 390, height: 844 });
    await card.scrollIntoViewIfNeeded();
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true, '390px page fits');
    await page.goto((process.env.STUDYPLAN_URL || 'http://127.0.0.1:5173') + '/#path', { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.locator('.timeline-stage').nth(2).getByRole('button', { name: '进入学习 →' }).click();
    await card.getByRole('heading', { name: '云服务', exact: true }).waitFor();
    assert.equal(await page.getByRole('region', { name: '对比与思考提示' }).count(), 0);
    assert.equal(await card.getByRole('status').innerText(), '', 'new stage clears clipboard feedback');
    assert.ok((await prompt.inputValue()).includes('手工部署'));
    assert.ok(!(await prompt.inputValue()).includes('本次学习重点：\n- 状态恢复'));
    workspace.plan.revision = 2;
    workspace.plan.extensions[1].concepts = ['新版部署范围'];
    await page.reload();
    await page.goto((process.env.STUDYPLAN_URL || 'http://127.0.0.1:5173') + '/#path', { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.locator('.timeline-stage').nth(2).getByRole('button', { name: '进入学习 →' }).click();
    await card.getByRole('heading', { name: '云服务', exact: true }).waitFor();
    assert.ok((await prompt.inputValue()).includes('新版部署范围'));
    assert.equal(await card.getByRole('status').innerText(), '');
    if (process.env.STUDYPLAN_PRODUCTION === '1') {
      await page.goto((process.env.STUDYPLAN_URL || 'http://127.0.0.1:5173') + '/?previewCurriculum=1#path', { waitUntil: 'domcontentloaded', timeout: 30000 });
      await page.getByRole('heading', { name: '你的学习路径', exact: true }).waitFor();
      assert.equal(await page.getByRole('button', { name: '课程改进建议', exact: true }).count(), 0, 'production hides explicit static preview query');
    }
    await page.goto((process.env.STUDYPLAN_URL || 'http://127.0.0.1:5173') + '/#path', { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.locator('.timeline-stage').first().getByRole('button', { name: '进入学习 →' }).click();
    await page.getByRole('heading', { name: '工具调用', exact: true }).waitFor();
    assert.equal(await card.count(), 0, 'ordinary stages do not create synthetic project cards');
    assert.deepEqual(errors, []);
    assert.deepEqual(unexpected, [], 'copy and learning do not send new APIs or external requests');
    console.log('PASS: project-study root/fields, escaped text, prior/future knowledge, real clipboard, denied fallback, stage/revision reset, 390px, production-route entry');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
