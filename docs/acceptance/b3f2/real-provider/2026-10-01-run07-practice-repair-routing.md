# Acceptance 07: Practice repair routing and role contract

## Confirmed historical evidence

Acceptance `b3f2-real-20260930-07` is consumed. Historical Run
`run_6dca52ec3c324eafa82191f9f30ef353` remains failed with planning_failed.
The 14 retained provider requests succeeded: one outline, nine structure, two
practice and two repair. No Structure repair was needed in this acceptance.

The first model_api Practice batch has this deterministic error:

```text
实践批次第 2 条任务知识关联的 role 非法：'support'（stage.model_api）
```

The original and both repair outputs are identical parsed business objects. Each
keeps support on the task.model_api / node.model_api.2 link. Legitimate role values
are core, supporting and extension. Provider success does not establish business
validation success.

Checkpoint evidence independently identifies a graph wiring bug:

| Step | Saved state / next node |
| --- | --- |
| 34 | Practice role error; schedules repair_batch |
| 35 | repair_count 1, target kind practice; schedules validate_structure_batch |
| 36 | Error overwritten with 结构批次缺失; schedules another repair_batch |
| 37 | repair_count 2, target still practice; schedules validate_structure_batch |
| 38 | 结构批次缺失; schedules record_failure |
| 39 | Terminal failure |

All Structure batches were already complete (index nine). The inappropriate
Structure validation therefore accesses past the last batch. No final merge or
draft persistence was reached; the Run has no draft.

The interpreter already returns from Practice repair to Practice validation.
The real StateGraph instead had an unconditional repair_batch to
validate_structure_batch edge. Previous interpreter regression tests could not
prove this real graph edge was correct.

## Minimal repair

The StateGraph now routes completed repairs by repair_target.kind:

- structure to validate_structure_batch;
- practice to validate_practice_batch;
- provider generation failure or missing/unknown target to record_failure.

No third repair is introduced. Unknown transport dispatch still raises the
existing LLMDispatchUnknownError for application reconciliation, before any
additional provider call.

The Practice generation/repair contract now explicitly names the existing domain
enum for both knowledge_links and task_knowledge_links, rejects support, and asks
repair to correct invalid roles while preserving valid keys. There is no runtime
role mapping, silent normalization or validator relaxation. Prompt version is
b3f2-v7-practice-repair; Structure unit/relation contracts are preserved. Protocol
remains b3f2-batch-v1 and normal/max request counts remain 19/21 with two shared
repairs. Final global validators and persistence are unchanged.

## Offline verification

The business-only Run 07 fixture retains outline, Structure/Practice objects,
both repair answers and the relevant checkpoint tail. It contains no credentials,
headers, provider configuration or connection strings. Its source baseline is
d1540b43f2d8c56027aa57ff6dc3e56f080d0b2a.

Before implementation, real StateGraph tests reproduce the wrong-validator
behavior, including a correct Fake repair still leading to Structure validation.
After implementation, InMemorySaver tests run the actual StateGraph and prove:

- A corrected Fake Practice answer is revalidated as Practice, merges, saves a
  draft and reaches the real approval interrupt in 20 requests.
- Persistently invalid historical Practice answers retain the exact role error,
  stop after two repairs/14 requests, and never dispatch a third repair.
- Structure repair still returns to Structure validation.
- One Structure plus one Practice repair share the two-repair cap and reach the
  draft in 21 requests; the normal actual graph takes 19 requests.
- Actual StateGraph and interpreter use the same stable Attempt identities and
  produce matching validation outcomes for successful/persistent Practice repair.
- Repair JSON/length failures stop immediately; transport unknown preserves the
  dispatch-unknown exception. Unknown repair targets fail closed.

Results:

- Targeted pytest: PASS, 139 cases, including actual StateGraph repair, provider,
  localization, Run 06/05 fixtures, partial content, batched planning and
  controlled-live safety.
- Two existing privileged Windows symlink cases: NOT RUN; junction/reparse cases
  PASS. No elevation requested.
- Ruff and git diff --check: PASS.
- Full large suite and new paid validation: NOT RUN.

Historical Acceptance 01-07 journal/evidence hashes are unchanged. Read-only
diagnosis made no database data writes. New real provider requests: 0. New real
Runs: 0. Offline tests establish routing and request contract correctness, without
claiming a future model answer or complete real acceptance will pass.

## Next manual acceptance

The ignored local free-preflight script is prepared for the unconsumed identity
b3f2-real-20261001-08 and checks historical Run 07 remains terminal failed,
Acceptance 01-07 hashes, project queue, credentials/configuration, checkpoint and
Worker lock. The user runs it in their configured PowerShell. Paid acceptance is
a separate manual step after all free checks pass. IDs 01-07 must not be replayed.
