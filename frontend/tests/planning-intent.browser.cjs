// Explicit browser Fake contract test: no backend, provider, or external network.
const { chromium } = require('playwright-core');
const assert = require('node:assert/strict');
const BASE = process.env.STUDYPLAN_URL || 'http://127.0.0.1:5178';
const PROJECT = 'planning-intent-fake';

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  try {
    async function openFixture(goalSpec) {
      const page = await browser.newPage();
      page.setDefaultTimeout(5000);
      const posts = [], commands = [], errors = [];
      page.on('pageerror', error => errors.push(error.message));
      const draft = {
        draft_id: 'intent-draft', project_id: PROJECT, revision: 1, version: 1,
        status: 'awaiting_approval', draft_hash: 'intent-hash', goal_spec: goalSpec,
        stages: [{ stage_id: 's1', stable_key: 'tool.foundation', title: 'Tool 实现', section_kind: 'core', order_index: 0, objective: '连接请求与执行结果' }],
        stage_resources: [], validation_warnings: [],
      };
      await page.route('**/*', route => {
        if (!['127.0.0.1', 'localhost'].includes(new URL(route.request().url()).hostname)) return route.abort('blockedbyclient');
        return route.continue();
      });
      await page.route('**/api/v1/**', route => {
        if (route.request().method() !== 'GET') commands.push(route.request().url());
        return route.abort('blockedbyclient');
      });
      await page.route('**/api/v1/session', route => route.fulfill({ json: { username: '规划意图 Fake', project_ids: [PROJECT], csrf_token: 'fake-csrf' } }));
      await page.route('**/healthz', route => route.fulfill({ json: { llm_provider: 'fake' } }));
      await page.route('**/api/v1/workspace?**', route => route.fulfill({ status: 404, json: {} }));
      await page.route('**/api/v1/plans/current?**', route => route.fulfill({ status: 404, json: {} }));
      await page.route('**/api/v1/plans/generate?**', route => {
        assert.equal(route.request().method(), 'POST');
        assert.equal(new URL(route.request().url()).searchParams.get('project_id'), PROJECT);
        posts.push(route.request().postDataJSON());
        return route.fulfill({ status: 202, json: { run_id: 'intent-run' } });
      });
      await page.route('**/api/v1/runs/intent-run?**', route => route.fulfill({ json: {
        run_id: 'intent-run', status: 'succeeded', next_action: 'none', result_ref: 'intent-draft', version: 1, error: null,
      } }));
      await page.route('**/api/v1/plans/drafts/intent-draft?**', route => route.fulfill({ json: draft }));
      await page.goto(BASE + '/#planning', { waitUntil: 'domcontentloaded', timeout: 30000 });
      await page.getByRole('button', { name: '生成学习草案 →', exact: true }).waitFor();
      return { page, posts, commands, errors };
    }

    // Omitting all supplementary inputs preserves the existing request shape.
    const legacy = await openFixture(null);
    const details = legacy.page.locator('details').filter({ has: legacy.page.locator('summary', { hasText: '补充目标与起点' }) });
    await details.waitFor();
    assert.equal(await details.getAttribute('open'), null);
    await legacy.page.getByRole('textbox', { name: '你想学会什么？', exact: true }).fill('学习 Tool Calling');
    await legacy.page.getByRole('button', { name: '生成学习草案 →', exact: true }).click();
    await legacy.page.getByRole('heading', { name: '检查与调整草案', exact: true }).waitFor();
    assert.deepEqual(legacy.posts, [{ goal: '学习 Tool Calling' }]);
    assert.equal(await legacy.page.getByRole('region', { name: '草案目标快照', exact: true }).count(), 0);
    assert.deepEqual(legacy.commands, []);
    assert.deepEqual(legacy.errors, []);
    await legacy.page.close();

    const serverSnapshot = {
      target: '学习 Tool Calling', scope: ['服务端冻结范围：Loop / Dispatch / Result'],
      desired_depth: 'deep', starting_point: '服务端冻结起点：已经见过 Tool 概念，尚未实现 dispatch。',
      outcome_purpose: 'portfolio', constraints: ['服务端冻结限制：教程正文免费'],
    };
    const { page, posts, commands, errors } = await openFixture(serverSnapshot);
    await page.locator('summary', { hasText: '补充目标与起点' }).click();
    await page.getByRole('textbox', { name: '你想学会什么？', exact: true }).fill('学习 Tool Calling');
    await page.getByRole('combobox', { name: '期望深度', exact: true }).selectOption('applied');
    await page.getByRole('combobox', { name: '成果用途', exact: true }).selectOption('interview');
    await page.getByRole('textbox', { name: '当前起点', exact: true }).fill('我看过 Tool 概念，还没有实现 dispatch。');
    await page.getByRole('textbox', { name: '学习范围（每行一项）', exact: true }).fill('  Tool schema  \n\nDispatch\n Result ');
    await page.getByRole('textbox', { name: '限制条件（每行一项）', exact: true }).fill('免费教程\n 每周三小时 ');
    await page.locator('form').evaluate(form => {
      form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
      form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    });
    await page.getByRole('heading', { name: '检查与调整草案', exact: true }).waitFor();
    assert.deepEqual(posts, [{ goal: '学习 Tool Calling', goal_spec: {
      target: '学习 Tool Calling', scope: ['Tool schema', 'Dispatch', 'Result'], desired_depth: 'applied',
      starting_point: '我看过 Tool 概念，还没有实现 dispatch。', outcome_purpose: 'interview', constraints: ['免费教程', '每周三小时'],
    } }], 'one explicit POST with the bounded DTO; no inferred knowledge/mastery');
    const snapshot = page.getByRole('region', { name: '草案目标快照', exact: true });
    await snapshot.waitFor();
    assert.match(await snapshot.innerText(), /服务端冻结起点/);
    assert.match(await snapshot.innerText(), /作品集/);
    assert.match(await snapshot.innerText(), /深入/);
    assert.match(await snapshot.innerText(), /服务端冻结范围/);
    assert.match(await snapshot.innerText(), /服务端冻结限制/);
    assert.doesNotMatch(await snapshot.innerText(), /已掌握|已完成|VERIFIED|掌握度/);
    await page.getByRole('textbox', { name: '当前起点', exact: true }).fill('表单中未保存的新起点');
    assert.doesNotMatch(await snapshot.innerText(), /表单中未保存/);
    await page.reload();
    await snapshot.waitFor();
    assert.match(await snapshot.innerText(), /服务端冻结起点/);
    assert.equal(posts.length, 1, 'reload only reads persisted run/draft');
    assert.deepEqual(commands, [], 'no progress or knowledge commands');
    assert.deepEqual(errors, []);
    await page.close();

    const invalid = await openFixture(null);
    await invalid.page.locator('summary', { hasText: '补充目标与起点' }).click();
    await invalid.page.getByRole('textbox', { name: '学习范围（每行一项）', exact: true }).fill(Array.from({ length: 21 }, (_, index) => '范围 ' + index).join('\n'));
    await invalid.page.getByRole('button', { name: '生成学习草案 →', exact: true }).click();
    await invalid.page.getByRole('alert').waitFor();
    assert.equal(invalid.posts.length, 0, 'reject too many scope items before dispatch');
    await invalid.page.getByRole('textbox', { name: '学习范围（每行一项）', exact: true }).fill('合法范围');
    await invalid.page.getByRole('textbox', { name: '限制条件（每行一项）', exact: true }).fill('限'.repeat(301));
    await invalid.page.getByRole('button', { name: '生成学习草案 →', exact: true }).click();
    await invalid.page.getByRole('alert').waitFor();
    assert.equal(invalid.posts.length, 0, 'reject oversized constraint item before dispatch');
    await invalid.page.close();
    console.log('PASS: browser Fake optional goal intent/default omission, single bounded POST, input limits, no mastery mutation, server draft snapshot and reload');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
