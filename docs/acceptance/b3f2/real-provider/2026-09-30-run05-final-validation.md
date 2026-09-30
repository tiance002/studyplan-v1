# Acceptance 05: exact final validation failure and local contract repair

## Read-only durable diagnosis

Acceptance `b3f2-real-20260930-05` is consumed. Its historical Run
`run_6b0e8ab85431460788b6754397d4e06d` remains `failed`, with
`error_class=planning_failed`, `next_action=retry` and no `result_ref`. No replay
or change to this Run is authorized.

Scoped database reads and checkpoint reads used READ ONLY transactions. Evidence:

- 19 retained provider Attempts: 1 outline, 9 structure, 9 practice, all succeeded.
- Latest checkpoint: step 58, no pending writes, both completed indices 9,
  `repair_count=0`, `generation_errors=[]`, no draft reference/hash.
- Step 54 holds the final capstone Practice batch with no local validation errors
  and schedules its advance; step 55 advances; step 56 schedules merge; step 57
  has 15 validation errors and schedules `record_failure`; step 58 is terminal.
- The recorded business progress ends in validation with 18 completed batches.
- Worker job: completed, attempts 1, no outstanding lease. `plan_drafts` count for
  this Run is 0.

Re-evaluating only pure deterministic functions over the stored batches produces
exactly the persisted errors. The baseline local validators pass all nine
Structure and all nine Practice batches, including the final capstone batch.
`merge_batches` returns no errors. `validate_plan_structure` returns these exact
12 errors (indices are zero-based positions in the merged link array):

```text
第 10 条任务知识关联的 role 非法：'support'
第 14 条任务知识关联的 role 非法：'support'
第 15 条任务知识关联的 role 非法：'support'
第 21 条任务知识关联的 role 非法：'support'
第 23 条任务知识关联的 role 非法：'support'
第 27 条任务知识关联的 role 非法：'support'
第 32 条任务知识关联的 role 非法：'support'
第 33 条任务知识关联的 role 非法：'support'
第 39 条任务知识关联的 role 非法：'support'
第 40 条任务知识关联的 role 非法：'support'
第 46 条任务知识关联的 role 非法：'support'
第 47 条任务知识关联的 role 非法：'support'
```

`validate_route_structure` returns these exact three errors:

```text
知识节点未关联到学习单元
资源知识关联不属于当前阶段：stage.rag
资源知识关联不属于当前阶段：stage.context
```

The concatenated result equals persisted `structure_errors` and
`validation_errors`. This is a deterministic content failure at
`merge_and_validate`, followed by `record_failure`. The completed failure branch
does not enter `save_draft_projection`. There is no draft persistence exception
to repair here. `PlanService.execute_generation` maps the graph's failed outcome
to Run `failed` / `planning_failed`; the Worker completes the handled job.

## Actual contract gaps and classification

| Actual error | Classification | Local evidence / correction boundary |
| --- | --- | --- |
| All 12 illegal `'support'` roles | B: Practice-local omission | The affected batches are model_api, tools, rag, mcp, context, reliability and capstone. Local validation checked reference existence but omitted the domain role enum. |
| Node not attached to a learning unit | A: Structure-local omission | `node.rag` and `node.context` exist in their own Structure batches but occur in no unit's node_keys. Local validation checked each unit's references, not the reverse coverage. |
| rag resource stage mismatch | A: same Structure-local omission | The resource requires `node.rag`, which belongs to rag but is absent from rag unit coverage. |
| context resource stage mismatch | A: same Structure-local omission | The resource requires `node.context`, which belongs to context but is absent from context unit coverage. |

The resource errors do not demonstrate invented cross-stage resource keys: the
two keys are present in the correct batches. Restoring their unit coverage fixes
both coverage and resource validation without changing resources or the outline.
No actual error indicates duplicate stable keys, relation cycles, missing
contains/prerequisite edges, missing required nodes, order-index failure, a merge
bug or conflicting validation rules. Truly global checks remain at final merge.

## Minimal production change

Only `planning_batches.py` changes production behavior:

- Structure-local validation checks every batch node is covered by a unit and
  reports the exact omitted key/stage.
- Practice-local validation checks top-level task knowledge link roles using the
  same `TaskKnowledgeRole` enum and missing-role default as the final validator:
  `core`, `supporting`, `extension`. `support` remains invalid.

These errors now enter the existing local `planning.repair` branch with the
invalid batch and frozen stage context. There is no automatic field/role
normalization, new provider retry, full-run retry, extra repair budget or change
to merge/persistence. Final global validators remain unchanged as defense in
depth. Prompt version remains `b3f2-v5-practice-json`; protocol remains
`b3f2-batch-v1`; normal/max requests remain 19/21.

The unchanged historical content has problems in more than two batches. A Fake
graph using all that content stops after two successful Structure repairs when
the next invalid Practice batch needs a third repair. This is intentional: the
patch improves detection and bounded handling, without claiming the historical
Run can be made successful within two repairs.

## Offline fixture and verification

`backend/tests/fixtures/b3f2_run05_validation.json` contains checkpoint business
objects only (outline, structure and practice batches), exact final errors and
the local baseline results captured before the patch. It excludes actor/project
credentials, provider configuration, headers, sessions and DB connection data.
The source baseline is `b8136781f78d4688d20543d042661c3fd94cf550`; tests verify the
frozen pack hash against the repository pack.

The new regression tests reproduce all 15 final errors, locate all actual local
errors, and verify explicitly constructed offline repair responses pass local
and final validation. Fake graph variants exercise zero/one/two repairs reaching
the draft (19/20/21 requests), both kinds of persistent failure stopping after
two repairs, and unchanged historical content stopping early without retrying
the whole Run. Correcting fixture answers is test-only; production content is
never silently corrected.

- Targeted pytest: PASS, 143 cases. The scope includes the Run 05 regression,
  batched planning, plan validators, partial-content handling, provider,
  localization and controlled-live tests.
- Two existing privileged Windows symlink cases: NOT RUN; no elevation requested.
  Junction/reparse coverage: PASS.
- Relation type/direction, Practice JSON/shape, malformed JSON, length and
  transport reconciliation regression: PASS in that targeted scope.
- Ruff and `git diff --check`: PASS.
- Full large regression suite: NOT RUN; verification is scoped to this change.

Historical Run/Attempt and Acceptance 01–05 journal/evidence remain unchanged.
Real provider requests during this Goal: 0. New real Runs: 0. Acceptance 06 free
preflight and a separate explicit paid authorization gate precede any future
real call.
