const { chromium } = require("playwright-core");
const assert = require("node:assert/strict");

(async () => {
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  try {
    const page = await browser.newPage();
    page.setDefaultTimeout(4000);
    await page.route("**/api/v1/session", r => r.fulfill({ status: 401, json: { message: "未登录" } }));
    await page.route("**/healthz", r => r.fulfill({ json: { llm_provider: "fake" } }));
    const requests = [];
    let failure = { status: 401, body: { message: "用户名或密码错误" } };
    await page.route("**/api/v1/auth/*", async (route) => {
      requests.push({ url: route.request().url(), body: route.request().postDataJSON() });
      if (failure.status === 0) return route.abort("failed");
      await route.fulfill({
        status: failure.status,
        contentType: typeof failure.body === "string" ? "text/html" : "application/json",
        body: typeof failure.body === "string" ? failure.body : JSON.stringify(failure.body),
      });
    });
    await page.goto(process.env.STUDYPLAN_URL || "http://127.0.0.1:5175");
    await page.getByLabel("用户名", { exact: true }).fill("回归测试");
    await page.getByLabel("密码", { exact: true }).fill("123456");
    await page.getByRole("button", { name: "登录学习空间", exact: true }).click();
    await page.getByRole("alert").waitFor();
    await page.getByLabel("用户名", { exact: true }).fill("回归测试二");
    assert.equal(await page.getByRole("alert").count(), 0, "editing clears stale error");
    await page.getByRole("button", { name: "注册", exact: true }).click();
    await page.getByRole("heading", { name: "创建你的学习空间" }).waitFor();
    failure = { status: 409, body: { message: "用户名已存在" } };
    // Latest user rule replaces 15–128 for NEW registrations only.
    for (const password of ["123456", "123456789012", "😀".repeat(6), "😀".repeat(12), " 1234 "]) {
      await page.getByLabel("密码", { exact: true }).fill(password);
      const before = requests.length;
      await page.getByRole("button", { name: "注册并进入", exact: true }).click();
      await page.getByRole("alert").waitFor();
      assert.equal(requests.length, before + 1, "6–12 code-point registration requests reach API");
      assert.equal(requests.at(-1).body.password, password, "registration never strips or normalizes passwords");
      assert.ok(requests.at(-1).url.endsWith("/auth/register"));
      assert.match(await page.getByRole("alert").innerText(), /已被使用.*登录|已被使用.*更换/);
    }
    await page.getByLabel("密码", { exact: true }).fill("12345");
    const beforeValidation = requests.length;
    await page.getByRole("button", { name: "注册并进入", exact: true }).click();
    await page.getByRole("alert").waitFor();
    assert.match(await page.getByRole("alert").innerText(), /新密码须为 6–12/);
    assert.equal(requests.length, beforeValidation, "invalid input is rejected before sending");
    await page.getByLabel("密码", { exact: true }).fill("😀".repeat(13));
    await page.getByRole("button", { name: "注册并进入", exact: true }).click();
    assert.equal(await page.getByLabel("密码", { exact: true }).inputValue(), "😀".repeat(13), "password must not be silently truncated");
    assert.equal(requests.length, beforeValidation);
    await page.getByLabel("密码", { exact: true }).fill("😀".repeat(12));
    assert.equal(await page.getByRole("alert").count(), 0, "password editing clears error");
    failure = { status: 409, body: { message: "用户名已存在" } };
    await page.getByRole("button", { name: "注册并进入", exact: true }).click();
    await page.getByRole("alert").waitFor();
    assert.match(await page.getByRole("alert").innerText(), /已被使用.*登录|已被使用.*更换/);
    assert.ok(requests.at(-1).url.endsWith("/auth/register"));
    assert.match(await page.getByText(/6–12 个字符，支持粘贴/).innerText(), /无需混合/);
    assert.equal(await page.getByLabel("密码", { exact: true }).evaluate(node => node.dispatchEvent(new ClipboardEvent('paste', { bubbles: true, cancelable: true }))), true, "paste is not prevented");
    failure = { status: 422, body: { detail: [] } };
    await page.getByRole("button", { name: "注册并进入", exact: true }).click();
    await page.getByRole("alert").waitFor();
    assert.match(await page.getByRole("alert").innerText(), /新密码为 6–12/);
    await page.getByLabel("密码", { exact: true }).evaluate(node => {
      Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(node, String.fromCharCode(0xd800));
      node.dispatchEvent(new Event('input', { bubbles: true }));
    });
    const beforeInvalidUnicode = requests.length;
    await page.getByRole("button", { name: "注册并进入", exact: true }).click();
    await page.getByRole("alert").waitFor();
    assert.match(await page.getByRole("alert").innerText(), /非法字符/);
    assert.equal(requests.length, beforeInvalidUnicode);
    await page.getByRole("button", { name: "登录", exact: true }).click();
    assert.equal(await page.getByRole("alert").count(), 0);
    assert.equal(await page.getByLabel("用户名", { exact: true }).inputValue(), "回归测试二");
    failure = { status: 401, body: { message: "用户名或密码错误" } };
    await page.getByLabel("用户名", { exact: true }).fill("  Ａ旧账号  ");
    for (const password of ["x", "123456789012345", "😀".repeat(128)]) {
      await page.getByLabel("密码", { exact: true }).fill(password);
      const before = requests.length;
      await page.getByRole("button", { name: "登录学习空间", exact: true }).click();
      await page.getByRole("alert").waitFor();
      assert.equal(requests.length, before + 1, "legacy 1–128 password login requests remain permitted");
      assert.equal(requests.at(-1).body.password, password);
      assert.equal(requests.at(-1).body.username, "A旧账号", "Chinese username NFKC/trim is retained");
    }
    for (const password of ["", "😀".repeat(129)]) {
      await page.getByLabel("密码", { exact: true }).fill(password);
      const before = requests.length;
      await page.getByRole("button", { name: "登录学习空间", exact: true }).click();
      await page.getByRole("alert").waitFor();
      assert.equal(requests.length, before);
      assert.equal(await page.getByLabel("密码", { exact: true }).inputValue(), password);
    }
    await page.getByLabel("密码", { exact: true }).fill("旧密码依然由存储散列判定");
    for (const [status, body, expected] of [
      [401, { message: "用户名或密码错误" }, /尚未注册.*注册/],
      [422, { detail: [] }, /用户名.*2.*32.*密码.*128/],
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
    console.log("PASS: register 6–12 code points, raw/emoji/paste/invalid Unicode, legacy login 1–128, Chinese normalization, modes/errors/throttle/network");
  } finally {
    await browser.close();
  }
})().catch((error) => { console.error(error); process.exitCode = 1; });
