const { chromium } = require("playwright-core");
const assert = require("node:assert/strict");

(async () => {
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  try {
    const page = await browser.newPage();
    const requests = [];
    let failure = { status: 401, body: { message: "用户名或密码错误" } };
    await page.route("**/api/v1/auth/*", async (route) => {
      requests.push(route.request().url());
      if (failure.status === 0) return route.abort("failed");
      await route.fulfill({
        status: failure.status,
        contentType: typeof failure.body === "string" ? "text/html" : "application/json",
        body: typeof failure.body === "string" ? failure.body : JSON.stringify(failure.body),
      });
    });
    await page.goto(process.env.STUDYPLAN_URL || "http://127.0.0.1:5173");
    await page.getByLabel("用户名", { exact: true }).fill("回归测试");
    await page.getByLabel("密码", { exact: true }).fill("123456");
    await page.getByRole("button", { name: "登录学习空间", exact: true }).click();
    await page.getByRole("alert").waitFor();
    await page.getByLabel("用户名", { exact: true }).fill("回归测试二");
    assert.equal(await page.getByRole("alert").count(), 0, "editing clears stale error");
    await page.getByRole("button", { name: "注册", exact: true }).click();
    await page.getByRole("heading", { name: "创建你的学习空间" }).waitFor();
    await page.getByLabel("密码", { exact: true }).fill("123");
    const beforeValidation = requests.length;
    await page.getByRole("button", { name: "注册并进入", exact: true }).click();
    await page.getByRole("alert").waitFor();
    assert.match(await page.getByRole("alert").innerText(), /密码须为 6–12/);
    assert.equal(requests.length, beforeValidation, "invalid input is rejected before sending");
    await page.getByLabel("密码", { exact: true }).fill("1234567890123");
    await page.getByRole("button", { name: "注册并进入", exact: true }).click();
    assert.equal(await page.getByLabel("密码", { exact: true }).inputValue(), "1234567890123", "password must not be silently truncated");
    assert.equal(requests.length, beforeValidation);
    await page.getByLabel("密码", { exact: true }).fill("123456");
    assert.equal(await page.getByRole("alert").count(), 0, "password editing clears error");
    failure = { status: 409, body: { message: "用户名已存在" } };
    await page.getByRole("button", { name: "注册并进入", exact: true }).click();
    await page.getByRole("alert").waitFor();
    assert.match(await page.getByRole("alert").innerText(), /已被使用.*登录|已被使用.*更换/);
    assert.ok(requests.at(-1).endsWith("/auth/register"));
    await page.getByRole("button", { name: "登录", exact: true }).click();
    assert.equal(await page.getByRole("alert").count(), 0);
    assert.equal(await page.getByLabel("用户名", { exact: true }).inputValue(), "回归测试二");
    for (const [status, body, expected] of [
      [401, { message: "用户名或密码错误" }, /尚未注册.*注册/],
      [422, { detail: [] }, /用户名.*2.*32.*密码.*6.*12/],
      [429, { message: "尝试次数过多，请十分钟后再试" }, /十分钟/],
      [502, "Bad gateway", /服务暂时不可用/],
      [0, "", /无法连接/],
    ]) {
      failure = { status, body };
      await page.getByRole("button", { name: "登录学习空间", exact: true }).click();
      await page.getByRole("alert").waitFor();
      assert.match(await page.getByRole("alert").innerText(), expected);
      if (status === 401) await page.getByRole("button", { name: "立即注册", exact: true }).waitFor();
    }
    console.log("PASS: auth mode, stale errors, duplicate username, validation, throttle, unavailable service and network failure");
  } finally {
    await browser.close();
  }
})().catch((error) => { console.error(error); process.exitCode = 1; });
