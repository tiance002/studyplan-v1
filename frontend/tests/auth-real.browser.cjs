const { chromium } = require("playwright-core");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

(async () => {
  // Explicit owned test server only; never register test users in the product DB.
  assert.equal(process.env.STUDYPLAN_AUTH_TEST_URL, "http://127.0.0.1:5176");
  const origin = process.env.STUDYPLAN_AUTH_TEST_URL;
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  try {
    const page = await browser.newPage();
    const results = [];
    const suffix = Date.now().toString(36);
    for (const [index, password] of ["123456", "😀".repeat(12)].entries()) {
      await page.goto(origin);
      await page.getByRole("button", { name: "注册", exact: true }).click();
      await page.getByLabel("用户名", { exact: true }).fill(`真实入口${suffix}${index}`);
      await page.getByLabel("密码", { exact: true }).fill(password);
      const registered = page.waitForResponse(r => r.url().endsWith("/api/v1/auth/register") && r.request().method() === "POST");
      await page.getByRole("button", { name: "注册并进入", exact: true }).click();
      assert.equal((await registered).status(), 200, "real registration reaches ordinary PG auth");
      await page.getByRole("button", { name: "退出登录", exact: true }).waitFor();
      const csrf = (await page.request.get(`${origin}/api/v1/session`)).json();
      assert.equal((await csrf).username, `真实入口${suffix}${index}`);
      await page.reload();
      await page.getByRole("button", { name: "退出登录", exact: true }).waitFor();
      const loggedOut = page.waitForResponse(r => r.url().endsWith("/api/v1/auth/logout"));
      await page.getByRole("button", { name: "退出登录", exact: true }).click();
      assert.equal((await loggedOut).status(), 200);
      await page.getByLabel("用户名", { exact: true }).fill(`真实入口${suffix}${index}`);
      await page.getByLabel("密码", { exact: true }).fill(password);
      const login = page.waitForResponse(r => r.url().endsWith("/api/v1/auth/login"));
      await page.getByRole("button", { name: "登录学习空间", exact: true }).click();
      assert.equal((await login).status(), 200);
      await page.getByRole("button", { name: "退出登录", exact: true }).waitFor();
      await page.getByRole("button", { name: "退出登录", exact: true }).click();
      await page.getByRole("button", { name: "注册", exact: true }).waitFor();
      results.push({ characters: Array.from(password).length, registration: 200, refresh: true, logout: 200, login: 200 });
    }
    await page.getByRole("button", { name: "注册", exact: true }).click();
    await page.locator("#password-hint").waitFor();
    assert.match(await page.locator("#password-hint").innerText(), /6–12/);
    const directory = path.resolve(__dirname, "../../var/auth-fix");
    fs.mkdirSync(directory, { recursive: true });
    await page.screenshot({ path: path.join(directory, "auth-real.png"), fullPage: true });
    fs.writeFileSync(path.join(directory, "auth-real.json"), JSON.stringify({ status: "PASS", scope: "owned isolated PG + actual HTTP/Vite/Chrome; no fake responses", results, provider_calls: 0 }, null, 2));
    console.log("PASS: actual Chrome registration at 6 and 12 code points, cookie persistence, refresh, logout and login");
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
