import { test } from "node:test";
import assert from "node:assert/strict";
import {
  togglePanel,
  fitPanels,
  initialPanels,
} from "../src/components/panels.ts";
test("N+P opens A and closing restores prior layout", () => {
  const a = togglePanel(initialPanels, "assistant");
  assert.equal(a.nav, false);
  assert.equal(a.plan, true);
  assert.equal(a.assistant, true);
  const closed = togglePanel(a, "assistant");
  assert.equal(closed.nav, true);
});
test("P+A opening N collapses P; N+A opening P closes A", () => {
  const a = togglePanel(togglePanel(initialPanels, "assistant"), "nav");
  assert.equal(a.plan, false);
  const p = togglePanel(a, "plan");
  assert.equal(p.assistant, false);
  assert.equal(p.nav, true);
});
test("wide assistant preserves readable canvas at target widths", () => {
  for (const width of [1366, 1440, 1920]) {
    const s = fitPanels(
      { ...initialPanels, assistant: true, assistantWidth: 800 },
      width,
    );
    const consumed =
      (s.nav ? width * 0.11 : 62) +
      (s.plan ? width * 0.17 : 0) +
      (s.assistant ? s.assistantWidth : 0);
    assert.ok(width - consumed >= 600);
  }
});
test("manual reopening wins after assistant caused automatic collapse", () => {
  const auto = fitPanels(
    { ...initialPanels, assistant: true, assistantWidth: 800 },
    1366,
  );
  const reopened = fitPanels(togglePanel(auto, "nav", 1366), 1366);
  assert.equal(reopened.nav, true);
  assert.equal(reopened.plan, false);
  assert.ok(reopened.assistantWidth < 800);
});
