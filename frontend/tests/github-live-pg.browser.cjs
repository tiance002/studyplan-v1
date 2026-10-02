// Real public GitHub is called by the product API, with an append-only acceptance ledger.
const { chromium } = require('playwright-core');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

(async () => {
  const api = process.env.STUDYPLAN_GITHUB_OWNED_API;
  assert.ok(api && new URL(api).hostname === '127.0.0.1');
  const id = process.env.STUDYPLAN_GITHUB_ACCEPTANCE_ID;
  const directory = path.resolve(__dirname, '../../var/oct6-guidance');
  fs.mkdirSync(directory, { recursive: true });
  const evidence = { acceptance_id: id, status: 'NOT RUN', model: 'Fake fixture only', github: 'real public REST', events: [] };
  const save = () => fs.writeFileSync(path.join(directory, id + '-browser.json'), JSON.stringify(evidence, null, 2));
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const page = await browser.newPage();
  page.setDefaultTimeout(25000);
  const errors = [], posts = [];
  page.on('pageerror', error => errors.push(error.message));
  try {
    await page.route('**/*', async route => {
      const url = new URL(route.request().url());
      if (!['127.0.0.1', 'localhost'].includes(url.hostname)) return route.abort('blockedbyclient');
      if (url.pathname.startsWith('/api/v1/') || url.pathname === '/healthz') {
        if (route.request().method() === 'POST' && url.pathname.startsWith('/api/v1/resources/')) {
          posts.push({ path: url.pathname, body: route.request().postDataJSON() });
        }
        const response = await route.fetch({ url: api + url.pathname + url.search });
        evidence.events.push({ method: route.request().method(), path: url.pathname, status: response.status() });
        return route.fulfill({ response });
      }
      return route.continue();
    });
    const login = async () => {
      await page.getByLabel('用户名', { exact: true }).fill(process.env.STUDYPLAN_GITHUB_OWNED_USER);
      await page.getByLabel('密码', { exact: true }).fill('Test-pass1!');
      const response = page.waitForResponse(r => r.url().endsWith('/api/v1/auth/login'));
      await page.getByRole('button', { name: '登录学习空间', exact: true }).click();
      assert.equal((await response).status(), 200);
      await page.getByRole('button', { name: '补充本单元资料', exact: true }).waitFor();
    };
    await page.goto((process.env.STUDYPLAN_URL || 'http://127.0.0.1:5178') + '/#workspace');
    await login();
    const session = await (await page.request.get(api + '/api/v1/session')).json();
    const project = session.project_ids[0];
    const workspace = await (await page.request.get(api + '/api/v1/workspace?project_id=' + project)).json();
    const tools = workspace.stages.find(s => s.stage.stable_key === 'stage.tools');
    assert.ok(tools);
    await page.evaluate(([key, value]) => localStorage.setItem(key, JSON.stringify(value)),
      [`studyplan-position:${session.username}:${project}:${workspace.plan.revision}`,
       { stage: tools.stage.stage_id, node: tools.nodes[0].node_id }]);
    await page.reload();
    const dialog = page.getByRole('dialog', { name: '补充本单元资料', exact: true });
    const open = async () => { await page.getByRole('button', { name: '补充本单元资料', exact: true }).click(); await dialog.waitFor(); };
    await open();
    await dialog.getByLabel('搜索来源', { exact: true }).selectOption('github');
    await dialog.getByLabel('搜索词', { exact: true }).fill('learn-claude-code tool in:name,description,readme');
    const searching = page.waitForResponse(r => new URL(r.url()).pathname === '/api/v1/resources/searches');
    await dialog.getByRole('button', { name: '搜索资料', exact: true }).click();
    const searchResponse = await searching;
    assert.equal(searchResponse.status(), 200);
    evidence.search = await searchResponse.json(); save();
    assert.equal(evidence.search.status, 'succeeded', JSON.stringify(evidence.search));
    assert.ok(evidence.search.candidates.length >= 1 && evidence.search.candidates.length <= 5);
    const target = evidence.search.candidates.find(c => c.discovery.repo.owner === 'shareAI-lab' && c.discovery.repo.name === 'learn-claude-code');
    assert.ok(target, 'the named tutorial must be present; original search rank is not a quality verdict');
    const article = dialog.locator('article').filter({ has: page.getByRole('link', { name: target.title, exact: true }) });
    const inspecting = page.waitForResponse(r => new URL(r.url()).pathname === '/api/v1/resources/inspections');
    await article.getByRole('button', { name: '检查教程/章节', exact: true }).click();
    const checked = await inspecting;
    assert.equal(checked.status(), 200);
    evidence.inspection = await checked.json(); save();
    assert.equal(evidence.inspection.status, 'succeeded', JSON.stringify(evidence.inspection));
    const discovery = evidence.inspection.candidate.discovery;
    assert.ok(discovery.files.length >= 2 && discovery.files.length <= 3, 'README and at least one real chapter');
    const chapter = discovery.chapters.find(c => c.status === 'read');
    assert.ok(chapter, 'actual read chapter is required for private mapping');
    const key = evidence.search.context_snapshot.module_keys[0];
    assert.ok(key);
    await article.getByLabel('关联模块', { exact: true }).selectOption(key);
    await article.getByLabel('已读章节', { exact: true }).selectOption(chapter.path);
    await article.getByLabel('私人资料用途', { exact: true }).selectOption('supplement');
    const selecting = page.waitForResponse(r => new URL(r.url()).pathname === '/api/v1/resources/selections' && r.request().method() === 'POST');
    await article.getByRole('button', { name: '选用并映射已读章节', exact: true }).click();
    const selected = await selecting;
    assert.equal(selected.status(), 200);
    evidence.selection = await selected.json(); save();
    assert.deepEqual(evidence.selection.resource.discovery.selection_mapping.chapter_paths, [chapter.path]);
    await dialog.getByRole('button', { name: '移除此资料', exact: true }).waitFor();
    await page.reload(); await open();
    await dialog.getByRole('button', { name: '移除此资料', exact: true }).waitFor();
    for (const file of discovery.files) assert.ok((await dialog.innerText()).includes(file.content_hash));
    await page.keyboard.press('Escape');
    await page.getByRole('button', { name: '退出登录', exact: true }).click();
    await login(); await open();
    await dialog.getByRole('button', { name: '移除此资料', exact: true }).waitFor();
    assert.equal(posts.filter(p => p.path.endsWith('/searches')).length, 1);
    assert.equal(posts.filter(p => p.path.endsWith('/inspections')).length, 1);
    assert.equal(posts.filter(p => p.path.endsWith('/selections')).length, 1);
    assert.deepEqual(errors, []);
    evidence.status = 'PASS'; evidence.commands = posts; save();
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.screenshot({ path: path.join(directory, id + '-browser.png') });
    console.log('PASS: real public GitHub search/README/chapter, ordinary auth, real owned PG, private selection, refresh/relogin, no replay');
  } catch (error) {
    evidence.status = 'FAIL'; evidence.error = error.message; save();
    throw error;
  } finally {
    await page.unrouteAll({ behavior: 'wait' });
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
