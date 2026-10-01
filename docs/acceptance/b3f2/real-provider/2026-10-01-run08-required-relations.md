# B3-F2 Run 08: required relations and local repair

## Real result: FAIL

- Acceptance ID: `b3f2-real-20261001-08`.
- Run: `run_0cabcf3fa19a40a89a4e14e7481bb85b`.
- Runtime baseline: `cd871e660e137b717e44470eeb60d402f83448e2`
  (confirmed on `origin/develop` by fetch before the fix).
- All 19 provider Attempts succeeded: 1 outline, 9 structure, 9 practice.
- All finish reasons were `stop`; no output truncation or transport failure.
- Repair count: 0. Final status: `failed`, error class: `planning_failed`.
- No Draft was saved; the failure happened at final merged validation.

The saved checkpoint and business outputs show exactly two missing required edges:

```text
node.environment -> node.model_api (prerequisite)
node.reliability -> node.capstone (prerequisite)
```

Both owning batches emitted their internal `contains` relations but omitted their
declared external prerequisite. The frozen input included these dependencies and
the provider prompt already required them. Local validation checked the type and
endpoints of supplied relations, but did not check required edge completeness.
Final route validation detected the omissions and routed directly to failure.

## Minimal fix

`validate_structure_batch` now checks required `contains` and `prerequisite`
relations for blueprint nodes owned by the frozen current batch. Direction and
type must match the final validator exactly. This catches missing, reversed and
wrong-type edges while the original batch can still enter the existing local
repair path.

There is no automatic edge insertion or provider retry. The provider prompt stays
`b3f2-v7-practice-repair`; graph protocol stays `b3f2-batch-v1`. The shared repair
cap remains 2 and the maximum request count remains 21 (19 normal requests).
Final global validation remains in place.

## Offline verification: PASS

The retained fixture contains only business outline/structure/practice outputs and
final validation errors, with no credentials, actor scope or model settings.

- Before the fix, the regression run had 10 expected failures: both omissions and
  missing/reversed/wrong-type relations were accepted locally; no repair ran.
- After the fix, Run 08 answers plus explicit corrected Fake repair answers reach
  `await_approval` through the actual StateGraph in 21 requests with 2 repairs.
- Persistently omitted edges stop after 2 repairs, 5 requests, no practice
  dispatch and no Draft callback.
- Correct initial answers reach `await_approval` in 19 requests with no repair.
- StateGraph and interpreter errors, stop outcomes and Attempt IDs match.
- External and internal prerequisites, parent containment, exact relation type
  and direction, payload immutability, and generic batches are covered.
- Targeted suite: **PASS**, 153 tests. Two Windows directory symlink cases are
  **NOT RUN** because creation requires elevation on this host. The junction and
  reparse-point tests are **PASS**.
- Ruff and `git diff --check`: **PASS**.
- Full large suite: **NOT RUN**, scoped verification was used.

Scope: Run 08, Run 07 repair routing, Run 06 unit coverage, Run 05 validation,
partial content repair, batched planning, provider, localization, controlled live.

## Next manual acceptance

Recommended ID: `b3f2-real-20261001-09`. Local preparation confirmed it is valid
and unconsumed, and journal/evidence hashes for acceptances 01–08 are unchanged.

The ignored `var/codex-goals/b3f2-free-preflight.py` was updated to this ID and
historical Run 08. Its existing read-only credential, ownership, queue, personal
model, endpoint, thinking, budgets, worker allowlist/lock, graph and checkpoint
checks remain in place. Full free preflight: **NOT RUN** in Codex; the user runs
the wrapper in the PowerShell process with configured private environment values.

Only after `REAL PROVIDER PREFLIGHT = PASS` and exit code 0 should the user issue
the separate command with `-ConfirmPaidRun`, Acceptance 09 and their Project ID.
This patch does not claim a new real-provider acceptance PASS.

During diagnosis, implementation and offline verification:

- New real provider requests: 0.
- New real Runs: 0.
- Historical Run/Attempt/journal/evidence mutations: 0.
- Database data writes: 0.
- Paid authorization consumed: NO.
