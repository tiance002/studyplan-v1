import { test } from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import ts from "../node_modules/typescript/lib/typescript.js";

const source = await readFile(new URL("../src/api/client.ts", import.meta.url), "utf8");
const js = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ES2022 } }).outputText;
const client = await import(`data:text/javascript;base64,${Buffer.from(js).toString("base64")}`);

test("client exposes local bootstrap without client identity or fixed secret", () => {
  assert.equal(typeof client.restoreSession, "function");
});

test("local 401 bootstraps once with empty payload and retains server-selected project", async () => {
  const calls = [];
  const original = globalThis.fetch;
  globalThis.fetch = async (url, options) => {
    calls.push([url, options]);
    if (url.endsWith("entry-mode")) return Response.json({ local_entry_enabled: true });
    if (url.endsWith("/local")) return Response.json({ project_ids: ["p-a", "p-b"], default_project_id: "p-b", csrf_token: "fixture-csrf" });
    return Response.json({ message: "expired" }, { status: 401 });
  };
  try {
    let mode;
    const result = await client.restoreSession((value) => { mode = value; });
    assert.equal(mode, true);
    assert.equal(result.default_project_id, "p-b");
    assert.deepEqual(calls.map(([url]) => url), ["/api/v1/session/entry-mode", "/api/v1/session", "/api/v1/session/local"]);
    assert.equal(calls[2][1].body, "{}");
    assert.equal(calls[2][1].credentials, "include");
    assert.equal(calls[2][1].headers.Authorization, undefined);
  } finally { globalThis.fetch = original; }
});

test("disabled local mode retains legacy 401 and never creates a session", async () => {
  const calls = [];
  const original = globalThis.fetch;
  globalThis.fetch = async (url) => {
    calls.push(url);
    return url.endsWith("entry-mode") ? Response.json({ local_entry_enabled: false }) : Response.json({}, { status: 401 });
  };
  try {
    await assert.rejects(client.restoreSession(() => {}), (e) => e.status === 401);
    assert.equal(calls.length, 2);
  } finally { globalThis.fetch = original; }
});

test("binding failure stays in local mode and never registers or retries", async () => {
  const calls = [];
  const original = globalThis.fetch;
  globalThis.fetch = async (url) => {
    calls.push(url);
    if (url.endsWith("entry-mode")) return Response.json({ local_entry_enabled: true });
    return Response.json({ message: "local configuration unavailable" }, { status: url.endsWith("/local") ? 503 : 401 });
  };
  try {
    let mode;
    await assert.rejects(client.restoreSession(v => { mode = v; }), (e) => e.status === 503);
    assert.equal(mode, true);
    assert.equal(calls.length, 3);
  } finally { globalThis.fetch = original; }
});

test("refresh reuses session; non-401 errors never bootstrap", async () => {
  const original = globalThis.fetch;
  try {
    for (const status of [200, 403, 503]) {
      const calls = [];
      globalThis.fetch = async (url) => {
        calls.push(url);
        return url.endsWith("entry-mode") ? Response.json({ local_entry_enabled: true }) : Response.json({ project_ids: ["p-b"] }, { status });
      };
      if (status === 200) assert.deepEqual((await client.restoreSession(() => {})).project_ids, ["p-b"]);
      else await assert.rejects(client.restoreSession(() => {}), (e) => e.status === status);
      assert.equal(calls.length, 2);
    }
  } finally { globalThis.fetch = original; }
});
