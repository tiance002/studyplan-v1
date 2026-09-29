# B3-F2 implementation brief

The user-provided B3-F2 goal is the binding specification. Extend the existing LangGraph planning and publication flow in place. Keep browser authentication, personal model settings, draft approval hashes, publication CAS/idempotency, history and the V6.3 layout.

## Design decisions

- Select a repository-reviewed domain pack once for the normalized goal, before generation. Agent/LLM/LangGraph/RAG/MCP application goals select `agent.application`; explicit Python engineering goals select `python.engineering`; other goals select no curated pack. Agent intent takes precedence over incidental Python prerequisites. Never use Python as the fallback for an unsupported direction.
- Carry the selected key/version and resource-support scope through graph input, provider context, draft projection and publication. Do not store goal-specific selection on a shared mutable provider.
- Keep outline → structure → practice → validation/repair → approval. Generate a complete skeleton without fixed stage/unit/task counts. The Agent pack covers environment, language/API/prompt foundations, tools/structured output, LangGraph, retrieval/RAG, MCP, memory/context, evaluation/reliability and a capstone. Ordering/grouping can vary; required coverage cannot disappear.
- Extend existing entities only where persistence requires it: subknowledge and resource-to-node links are immutable generation data. Add an additive migration after 0009 if needed; never rewrite 0004–0009. Older payloads and plans retain compatible defaults and hashes.
- Resource IDs are owned by this repository's catalog, not claimed as external publisher IDs. Mark a chapter reviewed only after reading its official content and checking title/topic/URL and suitability. Store review evidence/date, documented version and limits. Unreviewed or outside-selected-pack references become search suggestions.
- The workspace reads stable published entity IDs. Show selected-node objectives in the top goal, neutral node labels without recorded progress, real chapter links and subknowledge. Preserve percentages, panel rules and assistant behavior. Restore selection atomically per actor/project/revision.
- Fake generation follows the selected pack's complete skeleton and makes no cloud claims. MockTransport tests inspect actual provider requests and exercise output processing. No paid model calls are authorized; cloud validation remains NOT RUN unless explicitly authorized.

## Completion evidence

M0 integration report and regression log; supported-scope and reviewed-resource index; an example produced through the real existing HTTP/draft/publication/readback flow with its provider mode clearly labelled; frontend screenshots at 1366/1440/1920; raw test commands/output/exit codes; cloud-call report; deferred P2/P3 items; next-session API dependencies. A paid-generated example remains conditional on explicit authorization and cannot be labelled completed without it.
