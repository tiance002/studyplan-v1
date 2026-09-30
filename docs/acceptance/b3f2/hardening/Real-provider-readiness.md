# B3-F2.1 real-provider readiness

**Prepared; real DeepSeek = NOT RUN.** This Goal authorizes Fake/MockTransport/PG
hardening and preparation only. Real model quality, billed usage, endpoint
availability and invoice cost have not been validated.

Prepared files:

- `scripts/b3f2-controlled-live.ps1`: explicit paid gate, no default dispatch.
- `backend/app/tools/b3f2_controlled_live.py`: existing personal deepseek-flash,
  frozen budgets/thinking, exclusive one-submission journal, exact fenced Worker
  claim, first-failure dispatch stop, 21-request ceiling and final coverage check.
- `backend/app/tools/b3f2_inspect.py`: READ ONLY application-role RLS inspection,
  Attempt metadata and honest Run subtotals/completeness/coverage.
- `docs/acceptance/b3f2/real-provider/README.md`: prerequisites, authorization,
  limits, interruption recovery and review checklist.

Offline commands:

```powershell
./.venv/Scripts/python.exe -m pytest backend/tests/unit/test_controlled_live.py -o addopts= -q
pwsh -NoProfile -File scripts/b3f2-controlled-live.ps1
```

Unit checks: **PASS**, exit 0, 7 passed (0.44s). They validate gate before settings,
exact model/options without dispatch, first truncation/invalid-JSON/unknown
failure stops further attempts, ceiling/duplicate/run guards, and NULL usage.
The initial offline test run was **FAIL**, 1 failed / 6 passed: the test's success
stub omitted required LLMResult model/provider fields; corrected stub, no
production behavior change.

PowerShell default gate: **PASS** (expected refusal), child exit **2**, output
`NOT RUN: explicit -ConfirmPaidRun authorization is required.` A subprocess
assertion verified the child return code (wrapper exit 0). No ConfirmPaidRun
invocation occurred. The read-only inspector is additionally exercised against
the final socket test's disposable PG Run; no real business Run is inspected.

Unknown tokens/diagnostics stay NULL, and partial token/latency sums carry false
completeness flags. The script does not equate 19 requests with tokens/cost or
8192 with consumed tokens. No model settings, historical Attempts, checkpoint
data or published migrations were modified by this Goal.

Ready for **user review and separate authorization** of one live acceptance.
Merges, milestone tags and a paid Run remain outside this Goal.
