# B3-F2 (batched) — commands and status

Branch: `codex/b3-f1`. All commands are run from the repo root with the project
venv (`.venv/Scripts/python.exe`). Raw outputs live under `var/`.

## Per-task commits

| Task | Commit | Subject |
|---|---|---|
| 1 | `7b7fbc7` | per-stage model output budgets and diagnostics |
| 2 | `38d042e` | enqueue planning runs and add a fenced local worker |
| 3 | `47cc67f` | add batched planning protocol with frozen budget and bounded repair |
| 4 | `2bd8445` | resume batched runs by graph version and finish real legacy checkpoints |
| 5 | `572b068` | single batched protocol, frozen submission and RunProgress |
| 6 | `32d837e` | per-stage generation progress on the planning page |
| 7 | (this change) | independent Fake E2E + real-graph progress consistency fix |

## Lint

    .venv/Scripts/python.exe -m ruff check backend/app backend/tests
    -> All checks passed!                          exit 0

## Types

    .venv/Scripts/python.exe -m mypy backend/app
    -> Success: no issues found in 90 source files exit 0

## Directed suites  (raw: var/b3f2-task7-directed.txt)

    .venv/Scripts/python.exe -m pytest \
        backend/tests/e2e/test_batched_agent_route.py \
        backend/tests/e2e/test_b3f2_learning_route.py \
        backend/tests/e2e/test_async_generation.py \
        backend/tests/integration/test_batched_recovery_pg.py \
        backend/tests/unit/test_batched_planning.py \
        backend/tests/contract -o addopts= -q
    -> 76 passed in 147.90s                        exit 0

## Full backend regression  (raw: var/b3f2-task7-nosock.txt)

    .venv/Scripts/python.exe -m pytest backend/tests \
        --ignore=backend/tests/e2e/test_b2v_socket_counterexamples.py \
        -o addopts= -q
    -> 500 passed in 398.49s                       exit 0

## Socket counterexamples — known flaky baseline (NOT green)

    .venv/Scripts/python.exe -m pytest \
        backend/tests/e2e/test_b2v_socket_counterexamples.py -o addopts= -q
    -> 4 failed in 22.86s                          exit 1

All four fail with `AssertionError: {"detail":"Not Found"}  assert 404 == 200` —
the pre-existing baseline (see `M5-service-tests.txt` §5). Not part of B3-F2 and
not counted as a pass.

## Environment caveats

- Tests that spawn a child process writing to PostgreSQL (the kill-recovery test)
  must run **outside the tool sandbox**.
- Use a **fresh** pytest `--basetemp` per run: a reused directory leaves a stale
  `blocked.json` sentinel and makes the kill-recovery test fail spuriously (now
  also hardened in the test itself — see `M7-e2e-tests.txt` §6b).

## Status

| Item | State |
|---|---|
| Task 1–6 | done, committed |
| Task 7 E2E | done, committed |
| ruff / mypy | green |
| Directed suites | 76/76 green |
| Full backend (no socket) | 500/500 green |
| Socket counterexamples | 4 pre-existing failures (baseline, recorded) |
| Frontend (Task 6) | green (see `M6-frontend-tests.txt`) |
| Real cloud run | NOT RUN (Fake/MockTransport only, per constraints) |
| Deploy / merge to main | NOT done (out of scope) |
