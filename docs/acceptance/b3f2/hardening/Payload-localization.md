# B3-F2.1 final LLM context localization — PASS

Branch: `fix/b3f2-1-hardening`. Baseline:
`cf5d42ac04405f876ea5506816c812650f654b37`. No paid model was called.

| Final request | Before | After |
| --- | --- | --- |
| Outline | Full pack + frozen manifest | Explicit full pack + manifest; nine stages and 27 required nodes preserved |
| Structure | Local helper payload + full pack added by node/provider | Current stage, owned node blueprints/resources, declared external prerequisite keys and resource support |
| Practice | Local helper payload + full pack added by node/provider | Current stage's verified nodes/units and practice blueprint |
| Repair | Global manifest + full pack, missing failed response | Failed batch, errors, target, local context and protocol/hash/repair-limit manifest fields |

`OpenAICompatibleLLM` serializes only caller-supplied context. Constructor
`domain_pack` remains available for historical ledger identity compatibility but
is never an implicit message fallback. Outline supplies its pack explicitly.
Transport-private `_...` fields stay out of HTTP messages. Declared external
prerequisite **keys** may cross stage boundaries; other stages' full blueprints,
resources and practice context do not.

The provider's batched repair shape/parser now follows `KnowledgeStructureV1`
or `PracticeProposalV1`, instead of requiring the old combined full-route shape.
The current protocol does not fall back to the legacy repair graph.
`prompt_version=b3f2-v3-local` identifies the changed wire contract. No historical
Attempt was edited, and no existing dispatch is automatically replayed with a
new identity.

## Verification

`backend/tests/unit/test_payload_localization.py` captures actual
`PlanningNodes.llm.generate_structured` calls for every structure/practice batch
and deterministic semantic-failure repairs. It also drives the full graph
through the real provider into HTTP MockTransport and inspects the serialized
user message. Assertions cover all nine stages, foreign-stage absence, exact
resource/node ownership, explicit outline pack, and both repair schemas. Scope
assertions avoid brittle fixed character lengths and tokenizer dependencies.

RED command:

```powershell
./.venv/Scripts/python.exe -m pytest backend/tests/unit/test_payload_localization.py -o addopts= -q
```

Before implementation: **FAIL**, exit 1, 9 failed / 1 passed (1.27s), confirming
node/provider pack injection and repair scope/shape defects.

GREEN command:

```powershell
./.venv/Scripts/python.exe -m pytest backend/tests/unit/test_payload_localization.py backend/tests/unit/test_batched_planning.py backend/tests/unit/test_b3_provider.py -o addopts= -q
```

**PASS**, exit 0, 38 passed (0.93s).

The existing HTTP+PG+ledger Mock test was updated to accept explicit pack only
on Outline and assert absence on all 18 subsequent messages. Its old adapter
indexed `prompt['domain_pack']` unconditionally; the first regression run exposed
that obsolete fixture assumption (25 passed / 1 failed). This test was corrected
to the new wire contract without reducing stages or coverage.

Raw local evidence: `var/b3f2-hardening/payload-red.txt`, `payload-green.txt`.
These ignored execution logs are not temporary debug files committed to Git.
Complete final suite evidence is in `Regression.md`.
