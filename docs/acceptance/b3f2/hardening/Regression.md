# B3-F2.1 regression ledger — PASS

Branch: `fix/b3f2-1-hardening`; starting commit
`cf5d42ac04405f876ea5506816c812650f654b37`.
Execution date: 2026-09-30. Real DeepSeek / other paid model: **NOT RUN**.

## A. Payload — PASS

```powershell
./.venv/Scripts/python.exe -m pytest backend/tests/unit/test_payload_localization.py backend/tests/unit/test_batched_planning.py backend/tests/unit/test_b3_provider.py -o addopts= -q
```

Exit 0; 38 passed, 0.93s. New tests first failed as expected before the fix
(9 failed / 1 passed, exit 1). Details: `Payload-localization.md`.

## B. Socket — PASS

```powershell
./.venv/Scripts/python.exe -m pytest backend/tests/e2e/test_b2v_socket_counterexamples.py backend/tests/e2e/test_socket_proxy_isolation.py -o addopts= -q
./.venv/Scripts/python.exe -m pytest backend/tests/e2e/test_b3f2_socket_visibility.py -o addopts= -q
```

Exit 0: 5 passed, 40.69s (original 4/4 plus proxy regression).
Exit 0: 1 passed, 124.92s (20/20 full nine-stage Runs, zero 404).
No retries, test exclusions or reduced Agent coverage. Details: `Socket-visibility.md`.

## C. B3-F2 targeted regression — PASS

```powershell
./.venv/Scripts/python.exe -m pytest backend/tests/e2e/test_batched_agent_route.py backend/tests/integration/test_batched_recovery_pg.py backend/tests/e2e/test_async_generation.py backend/tests/integration/test_run_budget_pg.py backend/tests/e2e/test_b3f2_learning_route.py -o addopts= -q
```

First invocation used a wrong async test directory: no tests ran (command FAIL).
Correct paths initially produced 25 passed / 1 failed, exit 1, 108.08s: obsolete
MockTransport fixture assumed every request included a full domain_pack.
The adapter now honors explicit context and asserts only Outline has the pack.
Corrected targeted command: **PASS**, exit 0, 26 passed, 79.40s.

## D. Final complete regression — PASS

```powershell
./.venv/Scripts/python.exe -m pytest backend/tests
./.venv/Scripts/python.exe -m ruff check backend
./.venv/Scripts/python.exe -m mypy backend/app
npm --prefix frontend test
npm --prefix frontend run build
git diff --check
```

Executed after A/B/C passed, with no socket exclusion, pytest override or skip:
**backend PASS, exit 0, 523 passed, 441.47s (7m21s), 0 failed / 0 skipped**.
The full suite includes the original four socket counterexamples, hostile-proxy
regression and another complete 20-Run stability execution. The latter includes
read-only PG inspection and missing-run/unauthorized-project negative assertions.
ruff: PASS, exit 0 (`All checks passed!`).
mypy: PASS, exit 0 (`Success: no issues found in 92 source files`; existing
untyped-body notes are not errors).
Frontend tests: PASS, exit 0, 4 passed / 0 skipped, 172.3667ms.
Frontend build: PASS, exit 0; TypeScript + Vite, 43 modules, Vite build 977ms.
`git diff --check`: PASS, exit 0. Raw local evidence: `backend-full.txt`,
`ruff.txt`, `mypy.txt`, `frontend-tests.txt`, `frontend-build.txt` under
`var/b3f2-hardening/`.

## Additional offline/UI checks — PASS

```powershell
./.venv/Scripts/python.exe -m pytest backend/tests/unit/test_controlled_live.py -o addopts= -q
$env:STUDYPLAN_URL='http://127.0.0.1:5177'
npm --prefix frontend run test:progress
```

Exit 0; 7 offline tests. Exit 0; one Chrome Mock API browser scenario verifies
queued/running polling, disabled button, programmatic duplicate-submit guard,
same-event double submit producing exactly one POST, NULL token display,
request-count labels, progress/failure/no-progress states and no graph internals.
Vite was served locally on 127.0.0.1:5177; all API endpoints were mocked.
Final localization + readiness recheck: PASS, exit 0, 17 passed (0.92s):
`pytest backend/tests/unit/test_controlled_live.py backend/tests/unit/test_payload_localization.py -o addopts= -q`.
PowerShell default paid gate: expected child exit 2, verified via subprocess.

## Safety and Git

Only the Goal branch is changed. `.workbuddy/` and `design-preview/` remain
untracked and untouched. No migration edits, real business DB cleanup,
historical Attempt edits, checkpoint cleanup, real model calls, branch/tag
deletion, force push, published-history rewrite, or integration merges.
Test harnesses create/drop their explicitly disposable databases only.
Temporary execution logs stay ignored under `var/b3f2-hardening/`.

Protected untracked artifacts: **PASS**, 17/17 files compared against the
2026-09-30 external SHA256 manifest (relative path, byte length and SHA256).
Their directories retain exactly 17 files. Protected refs remain:

| Ref | Commit |
| --- | --- |
| master | a9c469eb140121bef78767045bb742b5781b0a7c |
| develop | 6e51dfb34da955604894731aece695acda248156 |
| checkpoint-b3f2-batched-fake-20260930 (peeled) | 6e51dfb34da955604894731aece695acda248156 |
| backup/local-master-pre-sync-20260930 | f30d194e66eebc401e2f4723fe1d2ac21933cf77 |
| backup/local-codex-b3f1-pre-sync-20260930 | 1683cbf2a1daa939c730777c1e029557b3384db7 |

## Changed file inventory

Product context/transport:

- `backend/app/agent_workflows/nodes.py`
- `backend/app/infrastructure/providers/openai_compatible.py`
- `frontend/src/features/planning/PlanningPage.tsx`

Offline/PG/socket/UI regression:

- `backend/tests/unit/test_payload_localization.py`
- `backend/tests/unit/test_controlled_live.py`
- `backend/tests/e2e/test_b2v_socket_counterexamples.py`
- `backend/tests/e2e/test_socket_proxy_isolation.py`
- `backend/tests/e2e/test_b3f2_socket_visibility.py`
- `backend/tests/e2e/test_b3f2_learning_route.py`
- `backend/tests/helpers/socket_app.py`
- `frontend/tests/planning-progress.browser.cjs`

Controlled-live preparation:

- `backend/app/tools/b3f2_controlled_live.py`
- `backend/app/tools/b3f2_inspect.py`
- `scripts/b3f2-controlled-live.ps1`
- `docs/acceptance/b3f2/real-provider/README.md`

Acceptance and correction of earlier unsupported RLS diagnosis:

- `docs/acceptance/b3f2/hardening/Payload-localization.md`
- `docs/acceptance/b3f2/hardening/Socket-visibility.md`
- `docs/acceptance/b3f2/hardening/Regression.md`
- `docs/acceptance/b3f2/hardening/Real-provider-readiness.md`
- `docs/acceptance/b3f2/batched/M5-service-tests.txt`
- `docs/acceptance/b3f2/batched/M7-e2e-tests.txt`
- `docs/acceptance/b3f2/batched/commands-and-status.md`
