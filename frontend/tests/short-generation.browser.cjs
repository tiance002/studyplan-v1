// Browser contract test with explicit mocked HTTP responses; no provider calls.
const { chromium } = require("playwright-core");
const assert = require("node:assert/strict");
const PROJECT = "short-generation-project";
const BASE = process.env.STUDYPLAN_URL || "http://127.0.0.1:5173";

(async () => {
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  try {
    const page = await browser.newPage();
    let reads = 0, decisions = 0;
    let draft = {
      draft_id: "opaque-candidate", project_id: PROJECT, revision: 1,
      status: "awaiting_approval", draft_hash: "hash-original", version: 1,
      stages: [{ stage_id: "s1", stable_key: "foundation", title: "基础阶段",
        section_kind: "foundation", order_index: 0, objective: "建立基础" }],
      stage_resources: [], validation_warnings: [],
    };
    await page.route("**/api/v1/session", r => r.fulfill({ json: {
      username: "短任务测试", project_ids: [PROJECT], csrf_token: "test",
    } }));
    await page.route("**/healthz", r => r.fulfill({ json: { llm_provider: "fake" } }));
    await page.route("**/api/v1/workspace?**", r => r.fulfill({ status: 404, json: {} }));
    await page.route("**/api/v1/plans/current?**", r => r.fulfill({ status: 404, json: {} }));
    await page.route("**/api/v1/runs/opaque-run?**", r => {
      reads++;
      return r.fulfill({ json: { run_id: "opaque-run", status: "succeeded",
        next_action: "none", result_ref: draft.draft_id, version: 3, error: null } });
    });
    await page.route("**/api/v1/plans/drafts/opaque-candidate?**", r => r.fulfill({ json: draft }));
    await page.route("**/api/v1/plans/drafts/opaque-candidate/decision?**", r => {
      decisions++;
      return r.fulfill({ status: 409, json: { message: "草案已变化" } });
    });
    await page.goto(`${BASE}/#planning`);
    await page.evaluate(p => localStorage.setItem(`studyplan-run:${p}`, "opaque-run"), PROJECT);
    await page.reload();
    await page.waitForLoadState("networkidle");
    await page.getByRole("button", { name: "确认并发布路线", exact: true }).waitFor({ timeout: 5000 });
    assert.match(await page.locator(".run-banner strong").innerText(), /草案已生成.*等待确认/);
    const terminalReads = reads;
    await page.waitForTimeout(1800);
    assert.equal(reads, terminalReads, "terminal run must stop polling");

    const title = page.getByLabel("阶段 1 标题", { exact: true });
    await title.fill("我的未保存编辑");
    assert.equal(await page.getByRole("button", { name: "确认并发布路线", exact: true }).isDisabled(), true);
    await page.getByRole("button", { name: "刷新运行状态", exact: true }).click();
    await page.waitForLoadState("networkidle");
    assert.equal(await title.inputValue(), "我的未保存编辑", "refresh must preserve unsaved input");
    await page.getByRole("button", { name: "保存修改", exact: true }).click();
    await page.getByRole("alert").waitFor();
    assert.equal(decisions, 1);
    assert.equal(await title.inputValue(), "我的未保存编辑", "409 must preserve input");
    assert.equal(await page.getByRole("button", { name: "保存修改", exact: true }).isDisabled(), true);
    draft = { ...draft, draft_hash: "hash-new", stages: [{ ...draft.stages[0], title: "另一窗口已保存" }] };
    await page.getByRole("button", { name: "重新加载草案", exact: true }).click();
    await page.waitForFunction(() => document.querySelector('input[aria-label="阶段 1 标题"]')?.value === "另一窗口已保存");
    assert.equal(await title.inputValue(), "另一窗口已保存");
    await page.reload();
    await page.waitForLoadState("networkidle");
    assert.equal(await title.inputValue(), "另一窗口已保存", "reload recovers persisted draft");
    console.log("PASS: completed generation retains editable draft; terminal polling stops; refresh/409 preserve edits; explicit reload restores draft");
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
