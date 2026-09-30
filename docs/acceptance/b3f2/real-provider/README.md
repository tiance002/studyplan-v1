# B3-F2 controlled real-provider acceptance

The B3-F2.1 readiness-hardening work used only Fake/MockTransport. The first
real acceptance subsequently ran and ended as `reconciliation_required`; its
record is [2026-09-30-live-result.md](2026-09-30-live-result.md). Fake and
MockTransport results do not verify real-model quality.

## Authorization and preflight

Each real Run requires a separate human authorization and a new, explicitly
supplied AcceptanceId. The prepared entry point is
`scripts/b3f2-controlled-live.ps1`. Without `-ConfirmPaidRun`, `-AcceptanceId`,
and `-ProjectId`, it exits before settings, database access, or model dispatch.
Do not run legacy `b3-verify-live.ps1`, `b3f2-inspect-live.py`, or browser live
scripts for this acceptance: their earlier workflow and request ceilings differ.

1. Use the existing local development deployment configuration in the process
   environment: application-role `DATABASE_URL`, separate
   `CHECKPOINT_DATABASE_URL`, encryption key, real provider mode, and existing
   `PLANNING_WORKER_ACTOR_IDS` allowlist. Do not use a migration role.
2. Use an existing dedicated acceptance learning project and account. Configure
   its personal model through the existing UI: official `api.deepseek.com`,
   `deepseek-flash`, OpenAI protocol, valid credential. The harness reads the
   existing personal revision; it does not replace model credentials/settings.
3. Privately set `B3F2_USERNAME` and `B3F2_PASSWORD` in the process environment.
   Do not put credentials in command arguments, evidence, Git, or screenshots.
4. Stop the external Planning Worker. The harness acquires its existing PG
   single-worker lock, rejects active/unresolved runs in the selected project,
   and processes only the exact new run's fenced claim, once.
5. Confirm no other actor/process is submitting to this acceptance project.
   A mismatched claim aborts before model execution. This is a local acceptance
   harness, not a replacement deployment scheduler.

Example for a future separately reviewed acceptance, **not executed here**:

```powershell
./scripts/b3f2-controlled-live.ps1 `
  -ConfirmPaidRun `
  -AcceptanceId "b3f2-real-20260930-02" `
  -ProjectId $env:B3F2_PROJECT_ID
```

The example AcceptanceId is not authorization by itself. The operator must
choose and provide a fresh ID for every separately authorized Run.

## Multiple explicitly authorized acceptances

- One AcceptanceId identifies at most one Run. The ID is supplied manually;
  tooling never generates a replacement ID or retries under a new ID.
- IDs must match `^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$`; path separators, `..`,
  control characters, empty IDs, and reserved legacy aliases (`legacy`, `1`,
  `first`, and the first acceptance's example ID) are rejected.
- Each new authorization writes under the fixed directory
  `.git/b3f2-controlled-live/`, for example
  `b3f2-real-20260930-02.json` and
  `b3f2-real-20260930-02-evidence.json`.
- The journal is created with exclusive-create and begins with
  `status=submission_intent` before the generation POST. Once created, the ID is
  consumed even if POST, the process, or the network fails. An existing journal
  or evidence file stops execution; deleting either file is never a retry method.
- Evidence is created exclusively for that ID and includes the AcceptanceId,
  RunId, ProjectId, final status, request count, and a safe Attempt summary. It
  excludes credentials, cookies, session tokens, Authorization headers, DSNs,
  and encryption keys.
- The fixed root files
  `.git/b3f2-controlled-live.json` and
  `.git/b3f2-controlled-live-evidence.json` are reserved as the legacy first
  acceptance. They are not migrated or modified.

Legacy first acceptance remains immutable:

- Run: `run_c4fbba87293144abaead9585f129ce39`
- Status: `reconciliation_required`
- Result: the fourth `planning.structure / stage.tools` request was
  `provider_transport_unknown`; the network change near the failure is an
  external factor, not a program-proven unique root cause.

Acceptance #2 is a new authorization, a new AcceptanceId, and a new Run. It is
not a retry of the legacy Run. Do not modify or replay its Run or Attempts.

Goal: 从零学习 Agent 应用开发，并完成一个可验收的知识库 Agent 项目.

## Frozen execution limits

| Purpose | max_tokens per request |
| --- | ---: |
| planning.outline | 4096 |
| planning.structure | 8192 |
| planning.practice | 4096 |
| planning.repair | 8192 |

The provider is checked before generation and again when resolving the frozen
runtime: exact official `deepseek-flash`, `thinking={"type":"disabled"}`, and
the budgets above. Existing budget validation still applies.

Normal flow is **1 + 9 + 9 = 19 requests**, maximum **21** including the existing
shared two-repair limit. **19 is a request count, not a Token count. 8192 is an
output ceiling for one request, not actual usage.** No cost is inferred from
request counts or token limits.

The first provider/model failure, truncation, dispatch exception or unknown
outcome stops dispatch. `reconciliation_required` ends acceptance. No new
attempt ID after failure, duplicate dispatch, second generation, Worker polling
loop, automatic publish, retry, or unlimited repair is authorized. Semantic
validation failures may use only the existing bounded repairs before a provider
failure. Inspect and retain failures; do not clean business/checkpoint/Attempt data.

## Evidence and interruption

An exclusively created `.git/b3f2-controlled-live/<AcceptanceId>.json` records
submission intent before that acceptance's sole POST. If the process is
interrupted or the POST result is ambiguous, the journal remains and blocks
another invocation with that ID. **Do not delete the journal or rerun to recover
an ID.** A new Run requires separate human authorization and a new ID. Journal
and evidence contain acceptance/actor/project/run metadata, never cookies or
keys. The two fixed root files are the immutable legacy first-acceptance record.

The full runtime uses the existing composition root, API routes, PostgreSQL,
LangGraph checkpointer and Planning Worker. Its local API requests use TestClient;
the independent socket acceptance is documented in `../hardening/Socket-visibility.md`.
After execution, `.git/b3f2-controlled-live/<AcceptanceId>-evidence.json`
contains metadata only and is exclusive-create; an existing evidence file stops
the operation without overwrite.

Read-only inspection, **not run against a real business Run in this Goal**:

```powershell
$env:PYTHONPATH = 'D:\studyplan\backend'
./.venv/Scripts/python.exe -m app.tools.b3f2_inspect `
  --actor-id '<actor>' --project-id '<project>' --run-id '<run>'
```

This uses application-role RLS in a READ ONLY transaction with actor/project
context; rejects superuser/BYPASSRLS roles; does not read checkpoint contents or
mutate historical attempts. Each Attempt reports ID, purpose, schema, stage,
status, model, max_tokens, thinking, finish_reason, input/output tokens, latency,
content/reasoning character counts and error class. Missing diagnostics/usage
remain NULL. No prompt, response text, secret, or invoice estimate is exported.

Run totals report request/terminal-success/terminal-failure/unresolved counts,
known input/output and latency subtotals with completeness flags, final status,
draft stages and frozen required-node coverage. A partial subtotal is explicitly
incomplete; all-unknown stays NULL. Inspect for exactly nine stages and 27/27
required nodes, and review the actual draft before any publish/milestone action.

## Evidence from the original readiness-hardening Goal

- Default PowerShell refusal: PASS, child exit 2 (intended refusal).
- Offline gate/options/failure/ceiling/NULL tests: PASS, 7 tests, exit 0.
- Actual paid invocation and real-model acceptance: **NOT RUN**.

See `../hardening/Real-provider-readiness.md` and `../hardening/Regression.md`.
