# Acceptance 06: parent-node unit coverage contract

## Observed evidence

Acceptance `b3f2-real-20260930-06` is consumed. Run
`run_bc41446c11754fccbc468bcc7170af9c` remains failed. All ten provider Attempts
succeeded with finish reason stop: one outline, seven structure, two repair.
The terminal local error is:

```text
结构批次知识节点未关联到学习单元：node.context（stage.context）
```

Checkpoint step 26 schedules record_failure; step 27 is terminal. Repair count is
two, current structure index six, practice index zero, generation errors empty,
and draft count zero. Final merge and draft persistence were not reached.

Read-only inspection of the saved response payloads shows:

| Batch | Original units | Successful retained repair |
| --- | --- | --- |
| tools | schema unit covers node.tools.1; result unit covers node.tools.2 | Both units also cover node.tools |
| rag | ingest unit covers node.rag.1; grounded unit covers node.rag.2 | A foundation unit covers node.rag |
| context | state unit covers node.context.1; budget unit covers node.context.2 | No third repair was dispatched |

All three original batches already contain their parent node with node_type skill
and correct contains edges from that parent to its children. Environment,
model_api, langgraph and mcp cover every emitted node in their units. The retained
tools/rag repairs preserve nodes and relations and restore unit coverage through
two valid unit organizations. The missing parent coverage, rather than provider
syntax or incorrect relations, consumed the bounded repair quota.

## Minimal change and limits

The application already requires complete node-unit coverage, but the generation
contract explicitly described parent relations without explicitly requiring
parent coverage in units. The recurring leaf-only associations demonstrate this
contract gap. They do not prove what reasoning the provider used internally.

The patch makes the existing invariant explicit at generation time:

- Structure context carries required_unit_node_keys copied from the frozen
  current stage inventory, including parents and excluding external prerequisites.
- The existing Structure contract requires every emitted node, including parent
  skill nodes, in at least one unit.node_keys. Contains edges do not count as unit
  coverage. Generation and schema-specific repair use the same rule.
- Suitable units remain authored by the provider. Runtime does not invent a unit,
  add an association, omit parents or normalize returned content to manufacture
  a successful validation result.

Only the local input and provider request contract change. Validator behavior,
global validation, merge, persistence, repair cap two, request cap 21 and protocol
b3f2-batch-v1 remain intact. Normal Agent requests remain 19. Prompt version changes
from b3f2-v5-practice-json to b3f2-v6-unit-coverage to identify the new contract.

The offline tests prove the requirement is present in actual HTTP messages and
that invalid saved output remains rejected. They do not establish real provider
compliance or complete real acceptance success. That requires a future separately
authorized acceptance with an unconsumed ID; Acceptance 06 must not be replayed.

## Verification

The business-only Run 06 fixture contains three original batches and the two
retained successful repairs. Tests cover both generation and repair HTTP messages,
frozen parent inventories, exclusion of external prerequisites, no silent output
modification, historical failures, both successful repair organizations and
generic stages without an invented inventory.

- Targeted pytest: PASS, 127 cases covering Run 06, provider, localization, Run 05,
  partial JSON content handling, batched planning and controlled-live safety.
- Two existing Windows directory symlink tests: NOT RUN due unavailable privileges.
  Junction/reparse coverage: PASS. No elevation requested.
- Normal Fake path, bounded two-repair behavior, relation contract, Practice
  JSON/shape, transport unknown, malformed JSON and length regression: PASS.
- Ruff and git diff --check: PASS.
- Complete large suite: NOT RUN; verification is scoped to the patch.
- New real provider requests during this patch: 0. New real Runs: 0.

No historical Run/Attempt, Acceptance journal/evidence, database data, credentials,
.workbuddy or design-preview is modified.
