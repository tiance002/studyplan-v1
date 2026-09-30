# B3-F2 (batched generation) — final delivery

Branch `codex/b3-f1`. One generation protocol, one recovery semantic, frozen
submission, business-only progress, and an independent Fake E2E. No cloud model
was called; no migration was added; only disposable `studyplan_test_*` databases
were used; nothing was merged to `master` or deployed.

Due to earlier GitHub API replay, the remote SHA differs from the original local
SHA; the entries below use the actual GitHub SHAs.

## 1. What was delivered (Tasks 1–7)

| Task | Deliverable | Commit |
|---|---|---|
| 1 | Per-stage model output budgets + diagnostics | `7b7fbc7` |
| 2 | Durable enqueue + fenced local Worker | `38d042e` |
| 3 | `b3f2-batch-v1` batched planning graph + frozen manifest | `47cc67f` |
| 4 | Checkpoint recovery by graph version; real legacy checkpoints finished | `2bd8445` |
| 5 | Single protocol, frozen submission, business `RunProgress`, HTTP default switch | `3a769cd7f5d9bd66850de8f5f672e3cae45ec418` |
| 6 | Frontend per-stage progress on the business DTO only | `e0e272ff92bb261b999e4cb2d4e67041cef18e0b` |
| 7 | Independent disposable-PG Fake E2E + real-graph consistency fix | `880362eb460dbf702402e9746e34cd8f7e06f86f` |

Final evidence alignment commit: `6e51dfb34da955604894731aece695acda248156`.

## 2. The protocol

`b3f2-batch-v1` is the **only** official generation protocol. A run is:

    normalize -> generate_skeleton
              -> [generate_structure_batch -> validate -> advance] x9
              -> [generate_practice_batch  -> validate -> advance] x9
              -> merge_and_validate -> save_draft_projection
              -> await_approval [interrupt] -> apply_decision -> commit | cancel

- **One request per node**: 1 outline + 9 structure + 9 practice = 19 requests;
  the frozen cap is 21 (two bounded repairs).
- **Frozen submission**: protocol version, a non-secret model descriptor, the
  reviewed pack, the batch catalog and the request/output budget are frozen at
  enqueue (`freeze_manifest` -> `manifest_hash`; `SubmissionBinding`). A later
  settings change cannot alter a submitted run, and any tampering is detectable.
- **Local validation, deterministic merge**: each batch is validated against its
  own frozen slice; global relations are checked only after merge.
- **Only same-protocol recovery**: `builder_for_version` refuses every other
  version (incl. `"1"`, `"planning-legacy-v1"`, `""`) instead of silently
  converting. `PlanService` refuses a legacy configured `GRAPH_VERSION` at start.
- **Business-only progress**: `RunProgress` exposes phase, current stage
  index/title, completed/total batch counts, the frozen request cap and nullable
  usage. No thread id, node name, checkpoint or prompt ever leaves the backend.

## 3. Verification (raw logs under `var/`, index in `commands-and-status.md`)

- **ruff** — `backend/app` + `backend/tests`: all checks passed (exit 0).
- **mypy** — `backend/app`: 90 source files, no issues (exit 0).
- **Directed suites** — 76 passed, exit 0 (`var/b3f2-task7-directed.txt`).
- **Full backend regression** — 500 passed, exit 0 (`var/b3f2-task7-nosock.txt`).
- **Independent Fake E2E** (`backend/tests/e2e/test_batched_agent_route.py`) — 6
  tests over a disposable business DB + a separate disposable checkpoint DB, the
  real `StateGraph` and the real HTTP routes:
  full generation -> `waiting_user` -> approve -> publish with a complete business
  progress; frozen submission asserted from the persisted event; kill/resume that
  does **not** re-dispatch completed batches; `waiting_user` never auto-continued;
  cancel terminal + `409`; legacy/unknown versions refused.
- **Frontend** (Task 6) — `tsc -b`, `vite build`, node tests and the Playwright
  Mock progress test green (see `M6-frontend-tests.txt`).
- **Socket counterexamples** — 4 **pre-existing** failures, recorded separately as
  the known baseline and **never** reported as an unqualified pass
  (`M7-e2e-tests.txt` §7).

## 4. Defects found and fixed during acceptance

1. **`recursion_limit` under-count** (Task 5): the real `StateGraph` needed 3
   super-steps per batch, not 2; a full 9-stage run hit `GraphRecursionError` and
   was reported `planning_failed`. Fixed and verified (19 requests -> `waiting_user`).
2. **Real-graph off-by-one on the last batch of each phase** (Task 7): the real
   graph skipped `advance_*` on the last batch, so `current_structure_index`
   stopped at `count-1`; production progress showed `phase="structure"` and 8/9
   after all 9 had committed, and the real graph disagreed with the interpreter.
   Fixed by always advancing then routing by index; `recursion_limit()` updated
   to charge exactly 3 per batch. Verified: `phase=done`, 18/18.
3. **Stale-sentinel harness fragility** in the Task 4 kill-recovery test: a reused
   `--basetemp` left a `blocked.json` that killed the child instantly. Hardened
   the test to remove the sentinel before launch.

All three are documented in `M5-service-tests.txt` §6 and `M7-e2e-tests.txt` §6.

## 5. Design-revision conformance

- New Runs uniformly use `b3f2-batch-v1`; the service rejects any other configured
  version rather than converting it.
- Legacy checkpoint recovery / DTO compatibility / auto-migration are **not**
  implemented; legacy-only routing and its compatibility tests were removed (git
  history retains them).
- Unknown versions are explicitly refused, never guessed from the current default.
- Existing tests were **updated** to assert the new contract (request counts 3->19,
  `progress` in the run DTO) rather than deleted.
- Dev-env legacy checkpoints for the abandoned protocol were cleaned after
  recording scope (0 legacy business runs; 89/191/390 legacy checkpoint rows),
  touching nothing else — see `M5-legacy-data-audit.txt`.

## 6. Explicitly NOT done

- **No real cloud model run** — Fake / MockTransport only, as required.
- **No migration** and no touch of production/other business data.
- **No deploy, no merge to `master`.** The work stays on the dev branch.
- Real provider live counts remain **NOT RUN**; the ledger-backed `request_count`
  is exercised by `test_b3f2_learning_route.py` (MockTransport + `PgAttemptLLM`),
  while the in-process Fake path correctly reports `0`/`NULL` (never fabricated).
- The 4 socket counterexample failures remain the pre-existing baseline.

## 7. Next steps (not in this goal)

Push the branch to `origin/codex/b3-f1` for review. Real-cloud acceptance and any
`master` merge require explicit authorization and are out of scope here.
