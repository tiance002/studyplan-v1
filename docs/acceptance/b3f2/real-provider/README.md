# B3-F2.1 controlled real-provider acceptance

Status: **NOT RUN**. No real DeepSeek or other paid provider was called during
hardening. Fake and MockTransport results do not verify real-model quality.

## Authorization and preflight

After reviewing this Goal, the user may authorize exactly one paid Run separately.
The prepared entry point is `scripts/b3f2-controlled-live.ps1`. Without
`-ConfirmPaidRun` it exits 2 before settings, database access, or model dispatch.
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

Authorized command, **not executed in this Goal**:

```powershell
./scripts/b3f2-controlled-live.ps1 -ConfirmPaidRun -ProjectId '<existing-project-id>'
```

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

An exclusively created `.git/b3f2-controlled-live.json` records submission intent
before the sole POST. If the process is interrupted or the POST result is
ambiguous, that intent remains and blocks another invocation. **Do not delete
the journal or rerun to recover an ID.** A new authorization must be reviewed
separately. Recover the submitted ID through the existing project/run history.
Journal/evidence contain actor/project/run identifiers, never cookies or keys.

The full runtime uses the existing composition root, API routes, PostgreSQL,
LangGraph checkpointer and Planning Worker. Its local API requests use TestClient;
the independent socket acceptance is documented in `../hardening/Socket-visibility.md`.
After execution, `.git/b3f2-controlled-live-evidence.json` contains metadata only.

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

## This Goal's evidence

- Default PowerShell refusal: PASS, child exit 2 (intended refusal).
- Offline gate/options/failure/ceiling/NULL tests: PASS, 7 tests, exit 0.
- Actual paid invocation and real-model acceptance: **NOT RUN**.

See `../hardening/Real-provider-readiness.md` and `../hardening/Regression.md`.
