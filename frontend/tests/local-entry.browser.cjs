// Only use user-provided disposable Fake services. Never start an app/DB here.
const { chromium } = require("playwright-core");
const path = require("node:path");
const fs = require("node:fs/promises");

function providedUrl(name) {
  const raw = process.env[name];
  if (!raw) throw new Error(`NOT RUN: ${name} requires a supplied disposable Fake service`);
  const url = new URL(raw);
  if (url.protocol !== "http:" || !["localhost", "127.0.0.1", "[::1]"].includes(url.hostname) || url.username || url.password || url.pathname !== "/" || url.search || url.hash)
    throw new Error("NOT RUN: only explicit loopback test origins allowed");
  return url.origin;
}

(async () => {
  if (process.env.M11_DISPOSABLE_FAKE_CONFIRMED !== "YES")
    throw new Error("NOT RUN: disposable service/DB isolation must be confirmed first");
  const base = providedUrl("M11_FAKE_UI_URL");
  const missing = providedUrl("M11_MISSING_BINDING_UI_URL");
  if (!process.env.M11_BROWSER_EXECUTABLE || !process.env.M11_EVIDENCE_DIR)
    throw new Error("NOT RUN: supply browser executable and new evidence directory");
  for (const origin of [base, missing]) {
    const health = await fetch(origin + "/healthz").then(r => r.json());
    const mode = await fetch(origin + "/api/v1/session/entry-mode").then(r => r.json());
    if (health.llm_provider !== "fake" || mode.local_entry_enabled !== true)
      throw new Error("NOT RUN: supplied service is not Fake local-entry mode");
  }
  const browser = await chromium.launch({ executablePath: process.env.M11_BROWSER_EXECUTABLE, headless: true });
  try {
    const page = await browser.newPage();
    // Browser traffic is confined to the two disposable test origins.
    await page.route("**/*", async route => {
      const origin = new URL(route.request().url()).origin;
      return [base, missing].includes(origin) ? route.continue() : route.abort();
    });
    // Block generation, decisions and model-setting mutations even if UI regresses.
    await page.route("**/api/v1/**", async route => {
      const req = route.request();
      if (req.method() !== "GET" && !req.url().endsWith("/session/local"))
        return route.abort();
      return route.continue();
    });
    await page.goto(base);
    await page.getByRole("navigation", { name: "全局导航" }).waitFor();
    const before = await page.evaluate(() => fetch("/api/v1/session").then(r => r.json()));
    if (!before.default_project_id || !before.project_ids.includes(before.default_project_id))
      throw new Error("FAIL: no explicit owned default Project");
    if (await page.getByRole("textbox", { name: /用户名|密码/ }).count())
      throw new Error("FAIL: local entry asks for credentials");
    const model = await page.evaluate(() => fetch("/api/v1/model-settings").then(r => r.json()));
    if (Object.hasOwn(model, "api_key") || Object.hasOwn(model, "encrypted_api_key"))
      throw new Error("FAIL: model metadata contains a credential field");
    const forbidden = process.env.M11_FORBIDDEN_SECRET;
    if (forbidden && (JSON.stringify(model).includes(forbidden) || (await page.content()).includes(forbidden)))
      throw new Error("FAIL: synthetic model credential exposed");
    const sessionCookies = (await page.context().cookies()).filter(c => c.name === "studyplan_session");
    if (sessionCookies.length !== 1 || !sessionCookies[0].httpOnly || sessionCookies[0].sameSite !== "Strict")
      throw new Error("FAIL: persistent session cookie lacks expected protections");
    await page.reload();
    await page.getByRole("navigation", { name: "全局导航" }).waitFor();
    const after = await page.evaluate(() => fetch("/api/v1/session").then(r => r.json()));
    if (JSON.stringify(before.project_ids) !== JSON.stringify(after.project_ids) || before.default_project_id !== after.default_project_id)
      throw new Error("FAIL: refresh changed ownership");
    if (before.csrf_token !== after.csrf_token)
      throw new Error("FAIL: refresh replaced the persistent session");
    await fs.mkdir(process.env.M11_EVIDENCE_DIR, { recursive: true });
    await page.screenshot({ path: path.join(process.env.M11_EVIDENCE_DIR, "local-entry.png") });
    await page.goto(missing);
    await page.getByRole("heading", { name: "本地学习空间尚未就绪" }).waitFor();
    if (await page.getByRole("textbox", { name: /用户名|密码/ }).count())
      throw new Error("FAIL: binding failure falls back to login/register");
    await page.screenshot({ path: path.join(process.env.M11_EVIDENCE_DIR, "missing-binding.png") });
    console.log("PASS | supplied Fake browser entry, refresh ownership/session, missing binding, model secret protection; no model/decision mutations");
  } finally { await browser.close(); }
})().catch(error => { console.error(error.message); process.exitCode = 1; });
