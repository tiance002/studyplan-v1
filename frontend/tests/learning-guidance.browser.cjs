const { chromium } = require('playwright-core');
const assert = require('node:assert/strict');

// Catches a missing/collapsed guide, unsafe source links, or a guide retained from another stage.
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    const pageErrors = [];
    page.on('pageerror', error => pageErrors.push(error.message));
    page.setDefaultTimeout(5000);
    const guidance = {
      why_now: '已有最小聊天 Agent，现在连接 Tool 请求与执行结果。',
      previous_relation: '已经见过 Tool 概念，本次聚焦 Loop / Dispatch / Result。',
      learning_focus: ['tool schema', 'model tool request', 'dispatch', 'observation/result', 'error handling', '<img src=x onerror="window.guideExecuted=true">'],
      comparison_focus: ['两份实现新增第三个 Tool 分别修改哪里？'],
      practice_delta: {
        baseline: '最小聊天 Agent', increment: ['增加 read_file 和 search_note'],
        preserved: ['普通聊天不受影响'], validation: ['正常调用', '未知 Tool', '错误参数', 'Tool 抛错'],
        reuse: ['Permission / RAG / MCP 可继续复用'],
      },
      source_slice: {
        repo_url: 'https://github.com/openai/openai-agents-python', ref: 'fixture-ref-123',
        files: ['src/agents/run.py', 'src/agents/' + 'long_path_'.repeat(35) + '.py'],
        call_chain: ['tool registration', 'dispatch', 'result', 'next model turn'],
        questions: ['工具结果如何进入下一轮模型调用？'], optional: true, verification_status: 'suggested',
      },
      exposure_relation: 'deepen', knowledge_keys: ['tool_calling'],
    };
    const makeStage = (id, index, extra = {}) => ({
      stage: { stage_id: id, stable_key: 'stage.' + id, title: '阶段 ' + id, section_kind: 'core', order_index: index, objective: '检查学习指导', ...extra },
      nodes: [], units: [], resources: [], tasks: [],
    });
    const stages = [
      makeStage('a', 0, { learning_guidance: guidance }),
      makeStage('b', 1, { learning_guidance: { ...guidance, why_now: '现在进入恢复行为学习。', comparison_focus: [], source_slice: null, exposure_relation: 'review' } }),
      makeStage('legacy', 2), makeStage('null', 3, { learning_guidance: null }),
    ];
    delete stages[1].stage.learning_guidance.exposure_relation;
    delete stages[1].stage.learning_guidance.knowledge_keys;
    delete stages[1].stage.learning_guidance.source_slice;
    const workspace = {
      plan: { plan_id: 'guide-plan', project_id: 'project', revision: 1, goal_snapshot: '理解 Tool Calling', stages: stages.map(s => s.stage), unit_links: [], task_links: [], stage_resources: [], extensions: [] },
      stages, total_units: 0, completed_units: 0,
    };
    const requests = [];
    await page.route('**/*', route => {
      const url = new URL(route.request().url());
      if (!['127.0.0.1', 'localhost'].includes(url.hostname)) return route.abort('blockedbyclient');
      return route.continue();
    });
    await page.route('**/api/v1/**', route => {
      requests.push({ method: route.request().method(), url: route.request().url() });
      return route.abort('blockedbyclient');
    });
    await page.route('**/api/v1/session', route => route.fulfill({ json: { username: '学习指导测试', project_ids: ['project'], csrf_token: 'test' } }));
    let workspaceReads = 0;
    await page.route('**/api/v1/workspace?**', route => {
      workspaceReads++;
      return route.fulfill({ json: workspace });
    });
    await page.route('**/healthz', route => route.fulfill({ json: { llm_provider: 'fake' } }));
    await page.goto((process.env.STUDYPLAN_URL || 'http://127.0.0.1:5178') + '/#workspace', { waitUntil: 'domcontentloaded', timeout: 30000 });
    const guide = page.getByRole('region', { name: '学习指导', exact: true });
    await guide.waitFor();
    const summary = guide.locator('summary');
    const details = guide.locator('details');
    assert.equal(await details.getAttribute('open'), null, 'guidance starts collapsed');
    assert.equal(await guide.getByText(guidance.why_now, { exact: true }).isVisible(), false);
    await summary.focus();
    await summary.press('Enter');
    await guide.getByText(guidance.why_now, { exact: true }).waitFor();
    const text = await guide.innerText();
    for (const expected of [guidance.previous_relation, ...guidance.learning_focus, ...guidance.comparison_focus,
      guidance.practice_delta.baseline, ...Object.values(guidance.practice_delta).filter(Array.isArray).flat(),
      ...guidance.source_slice.files, ...guidance.source_slice.call_chain, ...guidance.source_slice.questions,
      'fixture-ref-123', '可选', '未核验']) assert.ok(text.includes(expected), expected);
    assert.equal(await guide.locator('img').count(), 0, 'model strings render as text');
    assert.equal(await page.evaluate(() => window.guideExecuted), undefined);
    const sourceLink = guide.getByRole('link', { name: '打开 GitHub 仓库', exact: true });
    assert.equal(await sourceLink.getAttribute('href'), 'https://github.com/openai/openai-agents-python');
    assert.equal(await sourceLink.getAttribute('target'), '_blank');
    assert.match(await sourceLink.getAttribute('rel'), /noopener/);
    assert.match(await sourceLink.getAttribute('rel'), /noreferrer/);
    await summary.click();
    assert.equal(await guide.getByText(guidance.why_now, { exact: true }).isVisible(), false);

    await page.reload();
    await guide.waitFor();
    await summary.click();
    await guide.getByText(guidance.why_now, { exact: true }).waitFor();
    assert.equal(workspaceReads, 2, 'refresh reuses the workspace response without generating guidance');
    await page.locator('.stage-trigger').nth(1).click();
    assert.equal(await details.getAttribute('open'), null, 'stage switch resets expansion');
    await summary.click();
    await guide.getByText('现在进入恢复行为学习。', { exact: true }).waitFor();
    await guide.getByText('关系待明确', { exact: true }).waitFor();
    assert.equal(await guide.getByText(guidance.why_now, { exact: true }).count(), 0, 'no stale stage guide');
    assert.equal(await guide.getByRole('link').count(), 0);
    assert.equal(await guide.getByRole('heading', { name: '对比问题', exact: true }).count(), 0);
    await page.locator('.stage-trigger').nth(2).click();
    await page.getByRole('heading', { name: '阶段 legacy', exact: true }).waitFor();
    assert.equal(await guide.count(), 0, 'legacy stage without guidance is compatible');
    await page.locator('.stage-trigger').nth(3).click();
    await page.getByRole('heading', { name: '阶段 null', exact: true }).waitFor();
    assert.equal(await guide.count(), 0, 'null guidance is compatible');

    for (const unsafeUrl of ['javascript:alert(1)', 'https://github.com.evil.example/org/repo', 'https://user:secret@github.com/org/repo', 'https://github.com:444/org/repo', 'https://github.com/org/repo?token=secret', 'https://github.com/org/repo/tree/main', 'https://github.com/org/%2e%2e']) {
      stages[0].stage.learning_guidance = { ...guidance, source_slice: { ...guidance.source_slice, repo_url: unsafeUrl } };
      await page.reload();
      await page.locator('.stage-trigger').first().click();
      await guide.waitFor();
      await summary.click();
      assert.equal(await guide.getByRole('link').count(), 0, 'reject unsafe source URL: ' + unsafeUrl);
      await guide.getByText('源码地址暂不可用。', { exact: true }).waitFor();
    }
    stages[0].stage.learning_guidance = { ...guidance, source_slice: { ...guidance.source_slice, verification_status: 'reviewed' } };
    await page.reload();
    await page.locator('.stage-trigger').first().click();
    await guide.waitFor();
    await summary.click();
    await guide.getByText('已审核', { exact: true }).waitFor();
    await page.setViewportSize({ width: 390, height: 844 });
    await guide.scrollIntoViewIfNeeded();
    assert.equal(await guide.evaluate(element => element.scrollWidth <= element.clientWidth), true, 'long source path fits at 390px');
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true, 'page fits at 390px');
    assert.equal(requests.some(request => request.method !== 'GET'), false, 'guidance never triggers a command');
    assert.deepEqual(pageErrors, [], 'no browser runtime errors');
    if (process.env.STUDYPLAN_GUIDANCE_SCREENSHOT) await page.screenshot({ path: process.env.STUDYPLAN_GUIDANCE_SCREENSHOT, fullPage: true });
    console.log('PASS: guidance collapse/keyboard/content, escaped text, safe source entry/ref/status, refresh, stage isolation, legacy/null and 390px');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
