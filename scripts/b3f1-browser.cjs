// Run with STUDYPLAN_PLAYWRIGHT_MODULE pointing to a locally installed playwright(-core).
const { chromium } = require(
  process.env.STUDYPLAN_PLAYWRIGHT_MODULE ||
    "../frontend/node_modules/playwright-core",
);
const assert = require("node:assert/strict");
const fs = require("node:fs");
(async () => {
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1000 },
  });
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("http://127.0.0.1:5173");
  await page.waitForLoadState("networkidle");
  console.log("initial:", await page.locator("h2").allTextContents());
  await page.screenshot({path:'output/playwright/b3f1-login.png'});
  await page.getByRole("button", { name: "注册", exact: true }).click();
  await page
    .getByLabel("用户名", { exact: true })
    .fill("浏览验收" + Date.now().toString().slice(-8));
  await page.getByLabel("密码", { exact: true }).fill("123456");
  await page.getByRole("button", { name: "注册并进入", exact: true }).click();
  await page.getByRole("heading", { name: "今天，从这里继续。" }).waitFor();
  await page
    .getByRole("button", { name: "创建第一条计划 →", exact: true })
    .click();
  await page
    .getByRole("button", { name: "生成学习草案 →", exact: true })
    .click();
  await page
    .getByRole("button", { name: "确认并发布路线", exact: true })
    .waitFor();
  console.log("draft:", await page.locator(".draft-stage").count());
  // A second window changes the same persisted draft. The first window must
  // keep its unsaved edit on 409 until the user explicitly reloads.
  const session = await (
    await page.context().request.get("http://127.0.0.1:5173/api/v1/session")
  ).json();
  const project = session.project_ids[0];
  const runId = await page.evaluate(
    (p) => localStorage.getItem(`studyplan-run:${p}`),
    project,
  );
  const run = await (
    await page
      .context()
      .request.get(
        `http://127.0.0.1:5173/api/v1/runs/${runId}?project_id=${project}`,
      )
  ).json();
  const draftUrl = `http://127.0.0.1:5173/api/v1/plans/drafts/${run.result_ref}?project_id=${project}`;
  const draft = await (await page.context().request.get(draftUrl)).json();
  draft.stages[0].title = "另一个窗口的阶段标题";
  const edited = await page
    .context()
    .request.post(draftUrl.replace("?", "/decision?"), {
      headers: { "X-CSRF-Token": session.csrf_token },
      data: {
        decision: "edit",
        expected_version: 0,
        draft_hash: draft.draft_hash,
        edited_stages: draft.stages,
      },
    });
  assert.equal(edited.status(), 200);
  const firstTitle = page.getByRole("textbox", {
    name: "阶段 1 标题",
    exact: true,
  });
  await firstTitle.fill("当前窗口未保存的标题");
  await page.getByRole("button", { name: "保存修改", exact: true }).click();
  await page
    .getByRole("button", { name: "重新加载草案", exact: true })
    .waitFor();
  assert.equal(await firstTitle.inputValue(), "当前窗口未保存的标题");
  await page.screenshot({ path: "output/playwright/b3f1-conflict.png" });
  await page.getByRole("button", { name: "重新加载草案", exact: true }).click();
  await firstTitle.waitFor();
  await page.waitForFunction(
    () =>
      document.querySelector('[aria-label="阶段 1 标题"]').value ===
      "另一个窗口的阶段标题",
  );
  await page
    .getByRole("textbox", { name: "阶段 1 标题", exact: true })
    .fill("Agent 开发基础准备（已调整）");
  await page.getByRole("button", { name: "保存修改", exact: true }).click();
  await page
    .getByRole("button", { name: "确认并发布路线", exact: true })
    .click();
  await page
    .getByText("路线已发布，可以进入阶段学习。", { exact: true })
    .waitFor();
  await page.screenshot({ path: "output/playwright/b3f1-published.png" });
  await page.getByRole("button", { name: "学习路径", exact: true }).click();
  await page.getByRole('heading',{name:'你的学习路径',exact:true}).waitFor();
  await page.screenshot({path:'output/playwright/b3f1-path.png'});
  await page
    .getByRole("button", { name: "进入学习 →", exact: true })
    .first()
    .click();
  await page
    .getByRole("heading", { name: "Agent 开发基础准备（已调整）", exact: true })
    .waitFor();
  await page.reload();
  await page
    .getByRole("heading", { name: "Agent 开发基础准备（已调整）", exact: true })
    .waitFor();
  const results = [];
  for (const width of [1440, 1920, 1366]) {
    await page.setViewportSize({ width, height: 1000 });
    // Start from N+P; explicit toggles restore the expanded state after each case.
    await page.evaluate(() => {
      localStorage.setItem(
        "studyplan-panels",
        JSON.stringify({
          nav: true,
          plan: true,
          assistant: false,
          assistantWidth: 430,
        }),
      );
    });
    await page.reload();
    await page
      .getByRole("heading", {
        name: "Agent 开发基础准备（已调整）",
        exact: true,
      })
      .waitFor();
    const sizes = await page.evaluate(() => ({
      nav: document.querySelector(".global-nav").getBoundingClientRect().width,
      plan: document.querySelector(".plan-sidebar").getBoundingClientRect()
        .width,
      canvas: document.querySelector(".main-workspace").getBoundingClientRect()
        .width,
      overflow: document.documentElement.scrollWidth > innerWidth,
    }));
    assert.ok(Math.abs(sizes.nav - width * 0.11) < 2);
    assert.ok(Math.abs(sizes.plan - width * 0.17) < 2);
    assert.equal(sizes.overflow, false);
    await page.screenshot({
      path: `output/playwright/b3f1-workspace-${width}.png`,
    });
    await page.getByRole("button", { name: "✧ 学习助手", exact: true }).click();
    assert.equal(await page.locator(".global-nav.mini").count(), 1);
    assert.equal(await page.locator(".plan-sidebar").count(), 1);
    const divider = page.getByRole("separator", { name: "调整学习助手宽度" });
    const box = await divider.boundingBox();
    const before = await page
      .locator(".assistant-panel")
      .evaluate((e) => e.getBoundingClientRect().width);
    await page.mouse.move(box.x, 300);
    await page.mouse.move(box.x - 40, 300);
    assert.equal(
      await page
        .locator(".assistant-panel")
        .evaluate((e) => e.getBoundingClientRect().width),
      before,
    );
    await page.mouse.move(box.x, 300);
    await page.mouse.down();
    await page.mouse.move(box.x - 90, 300, { steps: 6 });
    await page.mouse.up();
    const after = await page
      .locator(".assistant-panel")
      .evaluate((e) => e.getBoundingClientRect().width);
    assert.ok(after > before + 70);
    assert.ok(
      (await page
        .locator(".main-workspace")
        .evaluate((e) => e.getBoundingClientRect().width)) >= 600,
    );
    await page.screenshot({
      path: `output/playwright/b3f1-assistant-${width}.png`,
    });
    const styles = await page.locator(".side-title").evaluateAll((nodes) =>
      nodes.map((n) => ({
        size: getComputedStyle(n).fontSize,
        weight: getComputedStyle(n).fontWeight,
        title: n.closest("button").title,
      })),
    );
    assert.ok(styles.every((s) => s.size === "13px" && s.weight === "600"));
    await page.getByRole("button", { name: "关闭学习助手" }).click();
    assert.equal(await page.locator(".global-nav.mini").count(), 0);
    results.push({
      width,
      ...sizes,
      assistantBefore: before,
      assistantAfter: after,
    });
  }
  for (const [name, heading] of [
    ["知识总结", "知识总结"],
    ["项目实践", "项目实践"],
    ["我的会话", "我的会话"],
    ["学习工作台", "今天，从这里继续。"],
  ]) {
    await page.getByRole("button", { name, exact: true }).first().click();
    await page.getByRole("heading", { name: heading, exact: true }).waitFor();
    await page.screenshot({ path: `output/playwright/b3f1-${name}.png` });
  }
  await page.getByRole('button',{name:/4\. 完成可验收的 Agent 应用/}).click();
  await page.getByRole('button',{name:'项目实践',exact:true}).first().click();
  await page.getByRole('heading',{name:'构建并验证知识助手',exact:true}).waitFor();
  await page.screenshot({path:'output/playwright/b3f1-项目实践.png'});
  // Exercise every panel transition through real controls, plus focus mode.
  await page.getByRole('button',{name:'✧ 学习助手',exact:true}).click();
  await page.getByRole('button',{name:'展开全局导航',exact:true}).click();
  assert.equal(await page.locator('.plan-sidebar').count(),0);
  await page.getByRole('button',{name:'展开计划',exact:true}).click();
  assert.equal(await page.locator('.assistant-panel').count(),0);
  assert.equal(await page.locator('.plan-sidebar').count(),1);
  await page.getByRole('button',{name:'专注阅读',exact:true}).click();
  assert.equal(await page.locator('.plan-sidebar').count(),0);
  assert.equal(await page.locator('.global-nav.mini').count(),1);
  await page.getByRole('button',{name:'展开全局导航',exact:true}).click();
  await page.getByRole('button',{name:'展开计划',exact:true}).click();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.reload();
  await page.waitForLoadState("networkidle");
  assert.equal(
    await page.evaluate(
      () => document.documentElement.scrollWidth > innerWidth,
    ),
    false,
  );
  await page.screenshot({ path: "output/playwright/b3f1-mobile.png" });
  assert.deepEqual(errors, []);
  fs.writeFileSync(
    "output/playwright/b3f1-browser-results.json",
    JSON.stringify(
      {
        results,
        errors,
        refresh: true,
        registration: true,
        edit: true,
        publication: true,
        mobile: true,
        conflictPreservesEdit: true,
      },
      null,
      2,
    ),
  );
  console.log(JSON.stringify(results));
  await browser.close();
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
