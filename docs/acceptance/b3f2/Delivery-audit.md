# B3-F2 delivery audit

## Current state

The active branch is `codex/b3-f1`. The master history was integrated in `6a187fc`; implementation through `ce81eaa` is already on GitHub. See [M0-integration.md](M0-integration.md) for exact parents, merge-base, migration hashes and eighteen conflict resolutions. No force push, migration rewrite or published-history deletion was used.

Local development migration 0010 and immutable Agent/Python resource seeding succeeded on 2026-09-29. The frontend remains at http://127.0.0.1:5173 and the backend at http://127.0.0.1:8000 in explicitly labelled **Fake mode**. No cloud request was made by this acceptance run.

Final backend regression: **428 passed in 235.59s, exit 0**, no skips or warnings reported. Frontend build, four layout tests, auth browser regression and workspace browser regression all exited 0. Ruff passed and mypy checked 83 source files successfully. Exact commands and raw logs are linked in [M5-commands.md](M5-commands.md).

## Requirement evidence

| Requirement | Evidence and scope |
|---|---|
| A/B: direction and immutable pack binding | `test_b3f2_planning.py::test_select_pack_by_actual_direction`; Agent+Python overlap chooses Agent; Python engineering retains its pack; draft/publication readback checks key and version. |
| C: unsupported directions | Unit and real HTTP tests for watercolor goals, search-only references, no Python source binding. |
| D: complete route | Fake HTTP example has 9 stages/27 nodes/9 units/9 tasks; MockTransport exercises the OpenAI-compatible adapter through the real PG LangGraph and ledger with exactly three requests. Actual cloud model counts remain NOT RUN. |
| E: chapter/node association | E2E verifies published stage resources belong to that stage's nodes and chapter URLs match the reviewed manifest; SQL trigger rejects an out-of-stage node. Browser checks selected-node chapter URLs. |
| F: history | Agent→Python replan retains old completed unit_progress and both published revisions. |
| G: approval safety | Existing B2-V stale-hash/CAS/idempotency tests; new full route repeated approval returns the same plan; MockTransport count remains three after repeated approval. |
| H: readback | Approval response equals GET current; published chapters and node IDs equal draft values; resources displayed from the published snapshot. |
| I: isolation | Other actor receives 403; same actor's second space gets 404 for first-space draft and disjoint unit IDs; existing RLS suite retained. |
| J: legacy reads | Existing publication/repository/B2-V tests retained; optional node_ids defaults empty and are omitted from legacy hash payloads. |
| K: regressions | Full backend suite covers browser auth, personal model settings, durable provider attempts and plan publication; frontend auth browser tests and build pass. |
| L: layout | `browser/results.json`: 1366/1440/1920 widths, 11% nav/17% plan, no horizontal overflow, 13px/600 headings, assistant drag/collapse and ≥600px canvas. PNGs inspected as part of acceptance. |

## Example and screenshots

`browser/example-plan.json` is an actual local HTTP generation/publication/readback snapshot using **Fake**, not a cloud-model result. The example has the same business DTOs and IDs as the current development database. No session cookies, passwords or API keys are included. Browser screenshots include draft, learning path, selected-node workspace and assistant at all three requested widths. Reproduce with `node scripts/b3f2-browser.cjs` while the backend is explicitly in Fake mode; the script refuses other provider modes before registration/generation.

The full reviewed chapter metadata and support list are in [Resource-index.md](Resource-index.md). Source URLs are official chapter pages. Local index IDs, curated order and review-day precision are explained there.

## Cloud verification

- Status: **NOT RUN — awaiting explicit authorization**.
- Configured deployment model: `deepseek-flash`; maximum output tokens per response: 8000.
- Requests/tokens charged by this acceptance run: 0/0; provider invoice cost: not available, no cloud calls made.
- A full normal route uses outline, structure and practice requests. Existing repair policy permits up to two additional content-repair requests. Approval/replay must not call the model again. Any authorized cloud run must report actual ledger counts and tokens; it cannot be described using the Fake/MockTransport example.

## P2/P3 deferrals

- P2: conservative keyword direction selection can misread negated or mixed goals; ambiguous goals should be clarified in a future UX iteration. No paid classifier is added.
- P2: living-document indexes require periodic human review and new immutable versions when content changes; chapter suitability is broad within its declared topic, without line-by-line syllabus extraction.
- P2: generic unsupported routes have search suggestions and no reviewed resource pool. Python retains the earlier engineering scope and legacy index labels.
- P3: translation/adaptive reading detail, accessibility refinement and additional subject packs. No ranking, community feedback, caching or high-concurrency work is required for this release.

## Next learning-session API dependencies

Existing inputs: `GET /api/v1/session`, `GET /api/v1/workspace?project_id=…`, `GET /api/v1/plans/current?project_id=…`. Session supplies server-authorized spaces and CSRF; workspace supplies revision/stage/node/unit/task/resource IDs, objectives, subknowledge and prerequisites. The learner position is currently localStorage scoped by username/project/revision, not a server-side session record.

Next batch must define session create/read/list and current-position APIs referencing these published IDs; optimistic version checks and actor/project ownership must apply. Unit/node progress writes need an explicit evidence/status contract: the current reader only presents recorded unit_progress and leaves node progress neutral. Outcomes and summaries must link to the originating session, revision and knowledge/unit IDs while preserving old revisions. None of these writes, chat streams, summary generation or practice execution is implemented in this goal.

For planning, keep current `POST /api/v1/plans/generate`, run polling, draft GET and decision POST. Confirmation must keep expected_version, draft_hash and idempotency_key. Model settings continue through the existing encrypted personal settings API; no browser key exposure or second planner is needed.
