# Acceptance 04: partial JSON content diagnosis and offline repair verification

## Read-only historical evidence

- Acceptance: `b3f2-real-20260930-04` (consumed; no replay).
- Run: `run_df66789755be4c2aa4a38a110a82760e`, terminal `failed`, 6 requests.
- Failed Attempt: `planning.structure`, `stage.rag`, `KnowledgeStructureV1`.
- Persisted error: `provider_invalid_shape`.
- Exact persisted `details.missing_top_level_fields`: `["nodes", "relations", "units"]`.
- Recorded finish reason: `stop`; input/output tokens: 928 / 1125; content characters: 3671.

The scoped database inspection used a read-only transaction and made zero data
writes. The diagnostics are present in `ai_provider_attempts.response_payload`.
That column contains the serialized `LLMFailure` DTO, including `details`, rather
than the parsed business payload. `json.loads` succeeded, but the provider returned
a failure at its top-level field gate and discarded the parsed object. The
historical raw object cannot be reconstructed from that DTO; no assumptions are
made about its remaining keys or nesting.

## Root cause and minimal boundary change

`OpenAICompatibleLLM` previously classified missing business fields as a provider
failure. `PlanningNodes.generate_structure_batch` then emitted generation errors,
stopping the graph before `validate_structure_batch` and `repair_batch`. The same
gate affected `PracticeProposalV1`. Even after that gate, generation nodes rejected
missing/empty nodes, units or tasks, and normalized missing relations to an empty
array. These are batch schema boundary problems, not evidence of a rag-only prompt
problem.

For structure/practice generation and schema-specific repair, a valid JSON object
now returns `LLMResult` with its original parsed payload and safe missing-field
diagnostics. The existing Attempt ledger serializes that result, preserving the
partial object. A succeeded provider Attempt means the request produced parseable
object content; it does not imply business validation or Run success.

Generation and repair nodes retain field absence and value types. Deterministic
validators explicitly require all three structure fields and all five practice
fields; arrays must be arrays and practice identity/title/idea must be nonempty
strings. They emit field-specific errors, and the existing graph routes those
local errors to `planning.repair` with the partial batch, errors, frozen stage
context and schema-specific HTTP field contract. No automatic unwrapping or
business-field defaults manufacture valid content.

Malformed JSON, non-object JSON, invalid envelopes, output truncation and other
provider failures still fail fast. Unknown dispatch retains reconciliation
semantics. Repair still uses distinct stable Attempt identities and the existing
shared maximum of two repairs; no third repair or blind retry is introduced.

Prompt text/version remains `b3f2-v5-practice-json`; graph protocol remains
`b3f2-batch-v1`. Normal Agent request count remains 19, maximum 21.

## Offline verification scope

Mock HTTP and deterministic Fake tests cover all eight missing top-level fields,
partial-object preservation, local context/schema contract, successful repair,
persistent failures stopping after exactly two repairs, and a rag object missing
all three fields. Existing tests cover complete content with zero repairs,
relation type/direction correction, fixed budgets and transport reconciliation.
Malformed JSON, length and non-object fail-fast are exercised through the graph.

No historical Run/Attempt or Acceptance 01–04 journal/evidence is modified.
Real provider requests during this Goal: 0. New real Runs: 0.

Verification results:

- Targeted pytest (`test_partial_content_repair`, `test_batched_planning`,
  `test_b3_provider`, `test_payload_localization`, `test_controlled_live`):
  PASS, 100 cases. Two existing Windows symlink cases: NOT RUN because creating
  directory symlinks requires unavailable privileges; junction/reparse coverage
  runs without elevation. No elevation requested.
- Ruff for modified Python files and the local free-preflight script: PASS.
- `git diff --check`: PASS.
- Full regression suite: NOT RUN; verification is scoped to the changed boundary.

Acceptance 05 is a separate, unconsumed identity. Its credential-dependent free
preflight must run in the user's already configured PowerShell. No paid run is
authorized by this patch or its offline verification.
