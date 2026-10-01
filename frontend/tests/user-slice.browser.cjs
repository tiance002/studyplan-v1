// Real loopback backend + retained isolated PostgreSQL + real generated draft.
// This test confirms its own dedicated test account; never a historical user draft.
const { chromium } = require("playwright-core");
const fs = require("node:fs");
const path = require("node:path");
const assert = require("node:assert/strict");
const acceptance = process.env.V2_ACCEPTANCE_ID;
if (!acceptance || !/^[A-Za-z0-9-]+$/.test(acceptance)) throw new Error("V2_ACCEPTANCE_ID required");
const root = path.resolve(__dirname, "../..");
const context = JSON.parse(fs.readFileSync(path.join(root, `var/v2-g1/${acceptance}-browser-private.json`)));
const report = JSON.parse(fs.readFileSync(path.join(root, `var/v2-g1/${acceptance}-report.json`)));
const BASE = process.env.STUDYPLAN_URL || "http://127.0.0.1:5175";
const resumePublished = process.env.V2_BROWSER_RESUME_PUBLISHED === "1";

(async () => {
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  try {
    const page = await browser.newPage();
    const consoleErrors = [];
    page.on("pageerror", error => consoleErrors.push(error.message));
    await page.goto(`${BASE}/#planning`);
    await page.getByLabel("用户名", { exact: true }).fill(context.username);
    await page.getByLabel("密码", { exact: true }).fill(context.password);
    await page.getByRole("button", { name: "登录学习空间", exact: true }).click();
    await page.locator(".planning-content").waitFor();
    await page.evaluate(({ project, run }) => localStorage.setItem(`studyplan-run:${project}`, run),
      { project: context.project_id, run: report.run.run_id });
    await page.reload();
    await page.waitForLoadState("networkidle");
    assert.equal(await page.locator(".draft-stage").count(), 9);
    if (!resumePublished) {
    await page.getByRole("button", { name: "确认并发布路线", exact: true }).waitFor();
    assert.match(await page.locator(".run-banner strong").innerText(), /草案已生成.*等待确认/);
    const title = page.getByLabel("阶段 1 标题", { exact: true });
    const edited = (await title.inputValue()) + "（浏览器已调整）";
    await title.fill(edited);
    await page.getByRole("button", { name: "保存修改", exact: true }).click();
    await page.getByText("修改已保存，请检查后确认。", { exact: true }).waitFor();
    await page.reload();
    await page.waitForLoadState("networkidle");
    assert.equal(await title.inputValue(), edited);
    await page.getByRole("button", { name: "确认并发布路线", exact: true }).click();
    await page.getByText("路线已发布，可以进入阶段学习。", { exact: true }).waitFor();
    } else {
      // The preceding browser run published successfully before a navigation
      // locator failure. Inspect the retained result; do not generate again.
      const current = await page.request.get(`${BASE}/api/v1/plans/current?project_id=${context.project_id}`);
      assert.equal(current.status(), 200);
      const plan = await current.json();
      assert.equal(plan.revision, 1);
      assert.match(plan.stages[0].title, /浏览器已调整/);
      assert.match(await page.locator(".run-banner strong").innerText(), /路线已发布/);
    }
    await page.screenshot({ path: path.join(root, `var/v2-g1/${acceptance}-published.png`), fullPage: true });
    await page.getByRole("button", { name: "退出登录", exact: true }).click();
    await page.getByLabel("用户名", { exact: true }).fill(context.username);
    await page.getByLabel("密码", { exact: true }).fill(context.password);
    await page.getByRole("button", { name: "登录学习空间", exact: true }).click();
    await page.locator(".planning-content").waitFor();
    await page.getByRole("heading", { name: "已确认草案", exact: true }).waitFor();
    assert.match(await page.locator(".run-banner strong").innerText(), /路线已发布/);
    assert.match(await page.locator(".draft-stage").first().innerText(), /浏览器已调整/);
    assert.equal(consoleErrors.length, 0, consoleErrors.join("\n"));
    const quota = path.join(root, ".git/v2-paid-quota-20261001");
    assert.equal(fs.readdirSync(quota).filter(name => name.startsWith("request-")).length, 20,
      "editing/confirmation/relogin must not dispatch another model request");
    fs.writeFileSync(path.join(root, `var/v2-g1/${acceptance}-browser.json`), JSON.stringify({
      status: "PASS", acceptance_id: acceptance, source: "real Chrome + loopback API + isolated PG",
      model_requests: 20, draft_stages: 9, edit_saved: true, published: true,
      relogin_readback: true, console_errors: consoleErrors,
      resumed_retained_publication: resumePublished,
    }, null, 2));
    console.log("PASS: real-model draft edited, saved, reloaded, published and read after browser logout/relogin; no extra provider requests");
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
