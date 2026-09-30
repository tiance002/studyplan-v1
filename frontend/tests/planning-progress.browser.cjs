// Task 6 (B3-F2): per-stage generation progress on the Planning page.
//
// The page may only speak the *business* RunProgress DTO from Task 5. This Mock
// test drives the page with canned API responses and asserts that:
//
//  1. a running run shows the batch phase, current stage and frozen budget;
//  2. a failed run shows the business failure location (never a graph node name);
//  3. a run without progress renders no progress panel at all;
//  4. nothing that looks like a graph internal (thread id, checkpoint, node name,
//     prompt) ever reaches the DOM.
//
// No backend is required: every endpoint is fulfilled by page.route.
const { chromium } = require("playwright-core");
const assert = require("node:assert/strict");

const PROJECT = "project-test";
const BASE = process.env.STUDYPLAN_URL || "http://127.0.0.1:5173";
const FORBIDDEN = [
  "thread_id",
  "checkpoint",
  "graph_version",
  "generate_structure_batch",
  "generate_practice_batch",
  "await_approval",
  "merge_and_validate",
  "node_name",
  "prompt",
];

function baseProgress(overrides) {
  return {
    phase: "practice",
    current_stage_index: 1,
    current_stage_title: "核心实现",
    total_stages: 9,
    completed_structure_batches: 9,
    total_structure_batches: 9,
    completed_practice_batches: 1,
    total_practice_batches: 9,
    completed_batches: 10,
    request_count: 11,
    max_requests: 21,
    input_tokens: 1100,
    output_tokens: 2200,
    usage_complete: true,
    failure_phase: "",
    failure_stage: "",
    ...overrides,
  };
}

(async () => {
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  try {
    const page = await browser.newPage();
    let runView = null;
    let runReads = 0, generations = 0;
    await page.route("**/api/v1/session", (r) =>
      r.fulfill({
        json: { username: "进度测试", project_ids: [PROJECT], csrf_token: "test" },
      }),
    );
    await page.route("**/healthz", (r) =>
      r.fulfill({ json: { llm_provider: "fake" } }),
    );
    await page.route("**/api/v1/runs/run-test?**", (r) => {
      runReads++;
      return r.fulfill({ json: runView });
    });
    await page.route("**/api/v1/plans/generate?**", (r) => {
      generations++;
      return r.fulfill({ status: 202, json: { run_id: "run-test" } });
    });

    const open = async () => {
      await page.goto(`${BASE}/#planning`);
      await page.evaluate(
        (p) => localStorage.setItem(`studyplan-run:${p}`, "run-test"),
        PROJECT,
      );
      await page.reload();
    };

    // 1) Running run: business phase, stage position and frozen budget.
    runView = {
      run_id: "run-test",
      status: "running",
      next_action: "wait",
      version: 1,
      result_ref: null,
      error: null,
      progress: baseProgress(),
    };
    await open();
    await page.locator(".run-progress").waitFor();
    assert.equal(
      await page.locator(".run-progress-head strong").innerText(),
      "正在生成阶段实践任务",
    );
    assert.equal(
      await page.locator(".run-progress-head .pill").innerText(),
      "阶段 2 / 9 · 核心实现",
    );
    const running = await page.locator(".run-progress").innerText();
    assert.match(running, /已完成 10 \/ 18 个批次/);
    assert.match(running, /结构 9\/9 · 实践 1\/9/);
    assert.match(running, /模型请求 11 \/ 21/);
    assert.match(running, /输入 1100 · 输出 2200/);
    assert.equal(
      await page
        .locator('.progress-track[role="progressbar"]')
        .getAttribute("aria-valuenow"),
      "56",
    );

    // Both active statuses keep polling and reject even programmatic submits.
    for (const status of ["queued", "running"]) {
      runView = { ...runView, status, progress: baseProgress({
        input_tokens: null, output_tokens: null, usage_complete: false,
      }) };
      await open();
      await page.locator(".run-progress").waitFor();
      assert.equal(await page.locator("button.btn.primary").first().isDisabled(), true);
      assert.match(await page.locator(".run-progress").innerText(), /尚未完整上报/);
      assert.doesNotMatch(await page.locator(".run-progress").innerText(), /输入 0|输出 0|费用/);
      const readsBefore = runReads;
      const nextRead = page.waitForResponse(r => r.url().includes("/runs/run-test"));
      await page.locator("form").evaluate(form => {
        form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
        form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
      });
      await nextRead;
      assert.ok(runReads > readsBefore, `${status} stopped polling`);
      assert.equal(generations, 0, `${status} submitted a second Run`);
    }

    // 2) Failed run: business failure location, not a graph node name.
    runView = {
      run_id: "run-test",
      status: "failed",
      next_action: "retry",
      version: 2,
      result_ref: null,
      error: { code: "planning_failed", message: "计划生成未通过校验，可重新发起" },
      progress: baseProgress({
        phase: "structure",
        current_stage_index: 2,
        current_stage_title: "工具与编排",
        completed_structure_batches: 2,
        completed_practice_batches: 0,
        completed_batches: 2,
        request_count: 3,
        failure_phase: "structure",
        failure_stage: "stage.core",
      }),
    };
    await open();
    await page.locator(".run-progress").waitFor();
    assert.equal(
      await page.locator(".run-progress-head strong").innerText(),
      "正在生成阶段知识结构",
    );
    assert.match(await page.locator(".run-progress").innerText(), /失败位置：结构批次 stage\.core/);

    // 3) A run without progress (e.g. an older run) renders no panel.
    runView = {
      run_id: "run-test",
      status: "waiting_user",
      next_action: "review_draft",
      version: 3,
      result_ref: null,
      error: null,
      progress: null,
    };
    await open();
    await page.locator(".run-banner").waitFor();
    assert.equal(await page.locator(".run-progress").count(), 0);

    // 4) No graph internals anywhere in the visible text.
    const text = (await page.locator("body").innerText()).toLowerCase();
    for (const token of FORBIDDEN) {
      assert.equal(
        text.includes(token),
        false,
        `DOM leaked a graph internal: ${token}`,
      );
    }
    // Two submits in the same event turn create exactly one accepted Run.
    runView = { ...runView, status: "waiting_user" };
    await open();
    await page.locator(".run-banner").waitFor();
    assert.equal(await page.locator("button.btn.primary").first().isDisabled(), false);
    runView = { ...runView, status: "queued" };
    const submitted = page.waitForResponse(r => r.url().includes("/plans/generate"));
    await page.locator("form").evaluate(form => {
      form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
      form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    });
    await submitted;
    await page.getByText("等待生成", { exact: true }).waitFor();
    assert.equal(generations, 1);
    assert.equal(await page.locator("button.btn.primary").first().isDisabled(), true);
    console.log(
      "PASS: queued/running polling and duplicate-submit guards, NULL usage, business-only progress, failure location, no-progress fallback",
    );
  } finally {
    await browser.close();
  }
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
