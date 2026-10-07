// Local browser fixture only: no backend, database, provider or external network.
const { chromium } = require('playwright-core');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const BASE = process.env.STUDYPLAN_URL || 'http://127.0.0.1:5178';
const MESSAGE = '新的学习规划流程正在重构，当前暂不可创建新路线。';

(async () => {
  assert.ok(['127.0.0.1', 'localhost'].includes(new URL(BASE).hostname));
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const evidence = [];
  try {
    for (const status of ['none', 'queued', 'running', 'waiting_user', 'succeeded', 'failed', 'cancelled', 'reconciliation_required']) {
      const context = await browser.newContext();
      const page = await context.newPage();
      const requests = [], errors = [];
      page.on('pageerror', error => errors.push(error.message));
      await context.route('**/*', route => {
        const request = route.request(), url = new URL(request.url());
        if (!['127.0.0.1', 'localhost'].includes(url.hostname)) return route.abort('blockedbyclient');
        if (url.pathname === '/api/v1/session') return route.fulfill({ json: { username: 'placeholder-owner', project_ids: ['placeholder-project'], csrf_token: 'local-fixture' } });
        if (url.pathname === '/healthz') return route.fulfill({ json: { llm_provider: 'unavailable' } });
        if (url.pathname === '/api/v1/workspace') return route.fulfill({ status: 404, json: {} });
        if (url.pathname.startsWith('/api/v1/')) {
          requests.push({ method: request.method(), path: url.pathname });
          return route.abort('blockedbyclient');
        }
        return route.continue();
      });
      // Old opaque identifiers must never cause automatic recovery or replay.
      await context.addInitScript(({ status }) => {
        if (status === 'none') return;
        localStorage.setItem('studyplan-run:placeholder-project', 'retained-' + status);
        localStorage.setItem('studyplan-run:["placeholder-owner","placeholder-project"]', 'retained-' + status);
        localStorage.setItem('studyplan-plan-change:["placeholder-owner","placeholder-project"]', 'retained-proposal');
      }, { status });
      await page.goto(BASE + '/#planning');
      await page.waitForLoadState('networkidle');
      const heading = page.getByRole('heading', { name: '学习计划', exact: true });
      await heading.waitFor();
      const content = heading.locator('..');
      assert.equal((await content.innerText()).trim(), '学习计划\n\n' + MESSAGE);
      assert.equal(await content.locator('button,input,textarea,select,form,details').count(), 0);
      assert.doesNotMatch(await content.innerText(), /Seed|Run|RAG|Coding|Workflow|Browser|A[0-8]|专项|草案|方向/);
      await page.reload();
      await page.waitForLoadState('networkidle');
      assert.equal((await content.innerText()).trim(), '学习计划\n\n' + MESSAGE);
      assert.deepEqual(requests, [], 'no generation, draft, publication, run recovery or history requests');
      assert.deepEqual(errors, []);
      evidence.push({ retained_status: status, unexpected_api_requests: requests, page_errors: errors, rendered: await content.innerText() });
      if (status === 'none' && process.env.STUDYPLAN_PLACEHOLDER_EVIDENCE_DIR) {
        const directory = path.resolve(process.env.STUDYPLAN_PLACEHOLDER_EVIDENCE_DIR);
        fs.mkdirSync(directory, { recursive: true });
        await page.screenshot({ path: path.join(directory, 'planning-placeholder-edge.png'), fullPage: true });
      }
      await context.close();
    }
    if (process.env.STUDYPLAN_PLACEHOLDER_EVIDENCE_DIR) {
      fs.writeFileSync(path.join(path.resolve(process.env.STUDYPLAN_PLACEHOLDER_EVIDENCE_DIR), 'planning-placeholder-browser.json'), JSON.stringify({ status: 'PASS', browser: 'Edge', fixture: 'local intercepted HTTP; no backend/DB/provider', cases: evidence }, null, 2));
    }
    console.log('PASS: Edge planning route placeholder, 8 retained-cache states and reload; 0 planning/Run/Draft/decision calls');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
