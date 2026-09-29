// Local HTTP + browser acceptance. The backend must explicitly be in Fake mode.
const { chromium } = require('../frontend/node_modules/playwright-core');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const output = 'docs/acceptance/b3f2/browser';
(async () => {
  fs.mkdirSync(output, { recursive: true });
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    await page.goto('http://127.0.0.1:5173');
    await page.waitForLoadState('networkidle');
    assert.equal((await (await page.request.get('http://127.0.0.1:5173/healthz')).json()).llm_provider, 'fake');
    await page.getByRole('button', { name: '注册', exact: true }).click();
    await page.getByLabel('用户名', { exact: true }).fill('路线验收' + Date.now().toString().slice(-8));
    await page.getByLabel('密码', { exact: true }).fill('123456');
    await page.getByRole('button', { name: '注册并进入', exact: true }).click();
    await page.getByRole('heading', { name: '今天，从这里继续。', exact: true }).waitFor();
    await page.getByRole('button', { name: '创建第一条计划 →', exact: true }).click();
    await page.getByRole('button', { name: '生成学习草案 →', exact: true }).click();
    await page.getByRole('button', { name: '确认并发布路线', exact: true }).waitFor();
    const session = await (await page.request.get('http://127.0.0.1:5173/api/v1/session')).json();
    const project = session.project_ids[0];
    const runId = await page.evaluate(p => localStorage.getItem(`studyplan-run:${p}`), project);
    const get = async path => {
      const response = await page.request.get('http://127.0.0.1:5173/api/v1/' + path + '?project_id=' + project);
      assert.equal(response.status(), 200, await response.text());
      return response.json();
    };
    const run = await get('runs/' + runId);
    const draft = await get('plans/drafts/' + run.result_ref);
    assert.equal(draft.source_pack_key, 'agent.application');
    assert.equal(draft.source_pack_version, 1);
    assert.equal(draft.stages.length, 9);
    assert.ok(draft.stage_resources.every(r => r.verification_status === 'reviewed' && r.node_ids.length && r.ordered_sections.length));
    await page.screenshot({ path: `${output}/draft.png`, fullPage: true });
    await page.getByRole('button', { name: '确认并发布路线', exact: true }).click();
    await page.getByText('路线已发布，可以进入阶段学习。', { exact: true }).waitFor();
    const plan = await get('plans/current');
    const workspace = await get('workspace');
    assert.equal(plan.stages.length, 9);
    assert.equal(workspace.stages.reduce((n, s) => n + s.nodes.length, 0), 27);
    assert.deepEqual(plan.stage_resources.map(r => r.ordered_sections), draft.stage_resources.map(r => r.ordered_sections));
    await page.getByRole('button', { name: '学习路径', exact: true }).click();
    await page.getByRole('heading', { name: '你的学习路径', exact: true }).waitFor();
    await page.screenshot({ path: `${output}/learning-path.png`, fullPage: true });
    await page.getByRole('button', { name: '进入学习 →', exact: true }).first().click();
    const first = workspace.stages[0];
    await page.getByRole('heading', { name: first.stage.title, exact: true, level: 1 }).waitFor();
    const child = first.nodes.find(n => !n.child_ids.length);
    await page.locator('.node-tabs').getByRole('button', { name: child.title, exact: true }).click();
    assert.match(await page.locator('.learning-pin').innerText(), new RegExp(child.objectives[0]));
    await page.reload();
    await page.locator('.node-tabs .selected').waitFor();
    assert.equal(await page.locator('.node-tabs .selected').innerText(), child.title);
    assert.equal(await page.locator('.plan-sidebar').getByText('待学习', { exact: true }).count(), 0);
    const results = [];
    for (const width of [1366, 1440, 1920]) {
      await page.setViewportSize({ width, height: 1000 });
      await page.evaluate(() => localStorage.setItem('studyplan-panels', JSON.stringify({ nav: true, plan: true, assistant: false, assistantWidth: 430 })));
      await page.reload();
      await page.getByRole('heading', { name: first.stage.title, exact: true, level: 1 }).waitFor();
      const sizes = await page.evaluate(() => ({
        nav: document.querySelector('.global-nav').getBoundingClientRect().width,
        plan: document.querySelector('.plan-sidebar').getBoundingClientRect().width,
        canvas: document.querySelector('.main-workspace').getBoundingClientRect().width,
        overflow: document.documentElement.scrollWidth > innerWidth,
        headings: Array.from(document.querySelectorAll('.side-title')).map(n => ({ size: getComputedStyle(n).fontSize, weight: getComputedStyle(n).fontWeight })),
      }));
      assert.ok(Math.abs(sizes.nav - width * .11) < 2);
      assert.ok(Math.abs(sizes.plan - width * .17) < 2);
      assert.equal(sizes.overflow, false);
      assert.ok(sizes.headings.every(h => h.size === '13px' && h.weight === '600'));
      const hrefs = await page.locator('.resource-row').evaluateAll(nodes => nodes.map(n => n.getAttribute('href')));
      const valid = first.resources.filter(r => r.node_ids.includes(child.node_id)).flatMap(r => r.ordered_sections.map(s => s.url));
      assert.ok(hrefs.length && hrefs.every(h => valid.includes(h)));
      await page.screenshot({ path: `${output}/workspace-${width}.png` });
      await page.getByRole('button', { name: '✧ 学习助手', exact: true }).click();
      assert.equal(await page.locator('.global-nav.mini').count(), 1);
      const divider = page.getByRole('separator', { name: '调整学习助手宽度' });
      const box = await divider.boundingBox();
      await page.mouse.move(box.x, 300);
      await page.mouse.down();
      await page.mouse.move(box.x - 90, 300, { steps: 6 });
      await page.mouse.up();
      assert.ok(await page.locator('.main-workspace').evaluate(n => n.getBoundingClientRect().width) >= 600);
      await page.screenshot({ path: `${output}/assistant-${width}.png` });
      results.push({ width, ...sizes, chapterLinks: hrefs, assistantDrag: true });
    }
    assert.deepEqual(errors, []);
    fs.writeFileSync(`${output}/example-plan.json`, JSON.stringify({ provider: 'fake', cloudVerification: 'NOT RUN', run, draft, plan, workspace }, null, 2));
    fs.writeFileSync(`${output}/results.json`, JSON.stringify({ registration: true, publication: true, refresh: true, results, errors }, null, 2));
    console.log(JSON.stringify({ stages: plan.stages.length, nodes: 27, widths: results.map(r => r.width), provider: 'fake', errors }));
  } finally { await browser.close(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
