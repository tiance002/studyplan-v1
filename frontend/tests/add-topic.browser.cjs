// Browser Fake for controlled topic addition. API responses are fulfilled in
// Playwright; no database or provider is contacted.
const { chromium } = require('playwright-core');
const assert = require('node:assert/strict');
const BASE = process.env.STUDYPLAN_URL || 'http://127.0.0.1:5178';
const PROJECT = 'add-topic-project';

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  try {
    const page = await browser.newPage();
    page.setDefaultTimeout(6000);
    let requestBody = null, reads = 0;
    const oldStages = [
      { stage_id: 'prefix', stable_key: 'python-base', title: 'Python 基础', section_kind: 'foundation', order_index: 0, objective: '保留的前置', learning_guidance: null },
      { stage_id: 'capstone', stable_key: 'capstone', title: '综合实践', section_kind: 'practice', order_index: 1, objective: '最终项目', learning_guidance: null },
    ];
    const added = { stage_id: 'new-rag', stable_key: 'rag-prerequisite', title: 'RAG 检索基础', section_kind: 'core', order_index: 1, objective: '拆解检索与引用', learning_guidance: null };
    const proposal = { proposal_id: 'add-topic-proposal', status: 'awaiting_approval', base_plan_id: 'plan-topic', base_revision: 4,
      operation: 'add_topic', before_goal: 'Agent 学习', after_goal: 'Agent 学习', before_stages: oldStages,
      before_stage_keys: oldStages.map(s => s.stable_key), after_stage_keys: ['python-base','rag-prerequisite','capstone'],
       retained_stage_keys: ['python-base','capstone'], topic_keys: ['retrieval_augmented_generation'], added_node_keys: ['retrieval','citation'], added_stage_keys: ['rag-prerequisite'],
       topic_titles: { retrieval_augmented_generation: 'RAG 检索与引用', retrieval: '检索基础', citation: '回答引用' },
      warnings: ['系统将补入主题的前置依赖；前置阶段虽然保留，原学习指导可能不再适用。'], preview_hash: 'topic-preview-hash',
      draft: { draft_id: 'topic-draft', project_id: PROJECT, revision: 5, status: 'awaiting_approval', draft_hash: 'draft-hash', version: 1, change_preview_id: 'add-topic-proposal',
        goal_snapshot: 'Agent 学习', goal_spec: null, source_pack_key: 'agent', source_pack_version: 1,
        stages: [...oldStages.slice(0,1), added, oldStages[1]].map((s, i) => ({ ...s, order_index: i })), stage_resources: [], validation_warnings: [] },
    };
    await page.route('**/api/v1/session', route => route.fulfill({ json: { username: 'topic-owner', project_ids: [PROJECT], csrf_token: 'fake' } }));
    await page.route('**/healthz', route => route.fulfill({ json: { llm_provider: 'fake' } }));
    await page.route('**/api/v1/workspace?**', route => route.fulfill({ status: 404, json: {} }));
    await page.route('**/api/v1/plans/current?**', route => route.fulfill({ status: 404, json: {} }));
    await page.route('**/api/v1/plan-changes/context?**', route => route.fulfill({ json: {
      plan_id: 'plan-topic', revision: 4, goal: 'Agent 学习', regenerate_available: true, generation_max_requests: 10,
      stages: [...oldStages.map((s, i) => ({ ...s, locked: true, inclusion: 'required' })),],
      add_topic_options: [
        { stable_key: 'retrieval_augmented_generation', title: 'RAG 检索与引用', added_stage_keys: ['rag-prerequisite'] },
        { stable_key: 'tool_calling', title: 'Tool Calling', added_stage_keys: ['tool-practice'] },
      ],
    } }));
    await page.route('**/api/v1/plan-changes/generate?**', async route => {
      requestBody = route.request().postDataJSON();
      return route.fulfill({ status: 202, json: { run_id: 'topic-run', status_url: '/api/v1/runs/topic-run' } });
    });
    await page.route('**/api/v1/runs/topic-run?**', route => {
      reads++;
      return route.fulfill({ json: { run_id: 'topic-run', status: 'succeeded', next_action: 'none', version: 2, result_ref: 'topic-draft', error: null, progress: null } });
    });
    await page.route('**/api/v1/plans/drafts/topic-draft?**', route => route.fulfill({ json: proposal.draft }));
    await page.route('**/api/v1/plan-changes/add-topic-proposal?**', route => route.fulfill({ json: proposal }));
    await page.goto(`${BASE}/#planning`);
    const panel = page.getByRole('region', { name: '有限路线调整', exact: true });
    await panel.locator('summary').click();
    await panel.getByRole('checkbox', { name: 'RAG 检索与引用', exact: true }).check();
    await panel.getByRole('button', { name: '生成主题追加草案', exact: true }).click();
    await page.getByText('草案已生成 · 等待确认', { exact: true }).waitFor();
    assert.equal(requestBody.operation, 'add_topic');
    assert.deepEqual(requestBody.topic_keys, ['retrieval_augmented_generation']);
    assert.equal(requestBody.goal, '');
    assert.equal(requestBody.goal_spec, undefined);
    assert.ok(requestBody.idempotency_key);
    const preview = panel.getByRole('region', { name: '路线调整预览', exact: true });
    await preview.waitFor();
    assert.match(await preview.innerText(), /RAG 检索与引用/);
    assert.match(await preview.innerText(), /RAG 检索基础/);
    assert.match(await preview.innerText(), /拆解检索与引用/);
    assert.match(await preview.innerText(), /保留的旧阶段/);
    assert.match(await preview.innerText(), /可能不再适用/);
    assert.equal(await page.getByRole('button', { name: '确认并发布路线', exact: true }).count(), 0);
    assert.equal(reads, 1);
    const saved = await page.evaluate(() => Object.entries(localStorage).filter(([key]) => key.startsWith('studyplan-plan-change:')));
    assert.equal(saved.length, 1); assert.equal(saved[0][1], 'add-topic-proposal');

    await page.reload();
    const recovered = page.getByRole('region', { name: '有限路线调整', exact: true });
    await recovered.locator('summary').click();
    await recovered.getByRole('region', { name: '路线调整预览', exact: true }).waitFor();
    assert.equal(requestBody.topic_keys.length, 1, 'reload recovers by proposal GET, not generation POST');

    // Empty curated options are explained honestly; no arbitrary topic text.
    await page.unroute('**/api/v1/plan-changes/context?**');
    await page.route('**/api/v1/plan-changes/context?**', route => route.fulfill({ json: {
      plan_id: 'plan-topic', revision: 4, goal: 'Agent 学习', regenerate_available: true, generation_max_requests: 10, stages: oldStages.map(s => ({ ...s, locked: true, inclusion: 'required' })), add_topic_options: [],
    } }));
    await page.evaluate(() => localStorage.clear());
    await page.reload();
    const emptyPanel = page.getByRole('region', { name: '有限路线调整', exact: true });
    await emptyPanel.locator('summary').click();
    await emptyPanel.getByText('当前没有可追加的受控主题。', { exact: true }).waitFor();
    assert.equal(await emptyPanel.getByRole('button', { name: '生成主题追加草案', exact: true }).count(), 0);
    console.log('PASS: curated topic selection, parent-bound dependency copy, model request envelope, complete add-topic preview, ID-only recovery and empty catalog explanation');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
