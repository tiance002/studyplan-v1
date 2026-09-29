const { chromium } = require("playwright-core");
const assert = require("node:assert/strict");

(async () => {
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  try {
    const page = await browser.newPage();
    const stage = { stage_id: "stage-test", stable_key: "stage.tools", title: "工具调用", section_kind: "core", order_index: 0, objective: "阶段目标" };
    const nodes = [
      { node_id: "parent-test", stable_key: "node.tools", title: "工具基础", objectives: ["工具基础目标"], child_ids: ["child-test"] },
      { node_id: "child-test", stable_key: "node.tools.schema", title: "工具 schema", objectives: ["校验工具参数并拒绝非法输入"], child_ids: [] },
    ].map(n => ({ ...n, node_type: "concept", source_status: "ai_draft", prerequisite_ids: [], progress: null }));
    const resource = { assignment_id: "resource-test", stage_id: stage.stage_id, role: "primary", node_ids: ["child-test"], creator: "LangChain", source_ref: "source-test", source_version: 1,
      title: "Tools", documentation_version: "v1", language: "en", media_type: "documentation", verification_status: "reviewed", warnings: [], fallback_search_terms: [],
      ordered_sections: [{ section_id: "chapter-test", title: "Tools", order_index: 0, url: "https://docs.langchain.com/oss/python/langchain/tools", anchor: "" }] };
    const workspace = { plan: { plan_id: "plan-test", project_id: "project-test", revision: 1, goal_snapshot: "整条计划的总目标", stages: [stage], unit_links: [], task_links: [], stage_resources: [resource], extensions: [] },
      stages: [{ stage, nodes, units: [], resources: [resource], tasks: [] }], total_units: 0, completed_units: 0 };
    await page.route("**/api/v1/session", r => r.fulfill({ json: { username: "位置测试", project_ids: ["project-test"], csrf_token: "test" } }));
    await page.route("**/api/v1/workspace?**", r => r.fulfill({ json: workspace }));
    await page.route("**/healthz", r => r.fulfill({ json: { llm_provider: "fake" } }));
    await page.goto((process.env.STUDYPLAN_URL || "http://127.0.0.1:5173") + "/#workspace");
    await page.locator(".node-tabs").getByRole("button", { name: "工具 schema", exact: true }).click();
    assert.equal(await page.locator(".learning-pin").innerText(), "当前目标\n校验工具参数并拒绝非法输入");
    assert.equal(await page.locator(".plan-sidebar").getByText("待学习", { exact: true }).count(), 0);
    assert.equal(await page.locator(".resource-row").getAttribute("href"), resource.ordered_sections[0].url);
    await page.reload();
    await page.locator(".node-tabs .selected").waitFor();
    assert.equal(await page.locator(".node-tabs .selected").innerText(), "工具 schema");
    assert.match(await page.locator(".learning-pin").innerText(), /校验工具参数/);
    await page.locator(".node-tabs").getByRole("button", { name: "工具基础", exact: true }).click();
    await page.getByRole("heading", { name: "子知识", exact: true }).waitFor();
    assert.equal(await page.locator(".node-detail").getByRole("button", { name: "工具 schema", exact: true }).count(), 1);
    console.log("PASS: selected-node goal, neutral labels, exact chapter URL, refresh position and subknowledge");
  } finally { await browser.close(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
