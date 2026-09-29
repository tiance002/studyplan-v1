# Authorized cloud verification — attempt 1

User explicitly authorized one Agent route generation, up to five provider requests (outline/structure/practice plus up to two structural repairs), at most 8000 output tokens per response, with no second automatic generation.

## Observed result

- Model: `deepseek-flash`, deployment configuration, official `api.deepseek.com` endpoint.
- Run: `run_54bd4bd11b6047709c581a3e530d43b6`.
- Request count: **3**. Outline, structure and practice all returned `finish_reason=length` and were rejected as `provider_output_truncated`.
- Result: **FAILED**; no approvable draft, no published plan, no stage/resource associations to claim as a cloud result. The previous nine-stage example is still explicitly Fake.
- No repair dispatch, no second generation and no repeated POST were made.
- Actual input/output tokens: **unavailable** in this attempt's legacy failure records. They are not zero. The v1 adapter returned the truncation failure before extracting response usage, so the ledger stored NULL. These records were not fabricated or edited after the fact.
- Invoice cost: unavailable; completion responses do not provide account invoice costs and the old failure records do not preserve usage. No cost estimate is claimed.
- Evidence: `usage.json`, `run.json`, `generation-result.png`. The browser driver exited 1 because no approvable draft existed. The authoritative run and all three failed attempt IDs remain in PostgreSQL.

## Investigation and offline repair

The request specified max_tokens=8000 and no thinking control. Current [official DeepSeek thinking-mode documentation](https://api-docs.deepseek.com/guides/thinking_mode/) says thinking is enabled by default at high effort, and supports `thinking.type=disabled` for Chat Completions. This establishes the request's default mode. Since the old adapter discarded the response before retaining reasoning/content lengths and usage, the precise division between reasoning and JSON tokens cannot be recovered from this ledger; reasoning exhausting the budget is a supported hypothesis, not a measured conclusion.

The v2 adapter explicitly disables thinking only for `deepseek-flash` on `api.deepseek.com`, preserving generic OpenAI-compatible endpoints and custom models. It retains available usage/latency on rejected JSON or truncation. Truncation diagnostics contain counts only, never reasoning text. The durable ledger stores and replays failure measurements without dispatching again. A changed prompt version prevents reuse under a different request identity.

MockTransport regression confirms the official-only request option, rejection of truncated content, failure token retention and one-dispatch replay. This is an **offline fix**, not proof that the next cloud generation succeeds.

Fresh offline verification: `.venv/Scripts/python.exe -m pytest backend/tests -ra` with `PYTHONUTF8=1`: **433 passed in 174.40s, exit 0**. Raw output: `Offline-regression.txt`. Ruff/mypy output: `Offline-lint.txt`, `Offline-types.txt`. Provider, graph, publication, auth and model-setting regressions are included. No cloud invocation occurred during these tests.

## Authorization remaining

Two requests from the original five-request ceiling were unused. The normal three-step generator requires a new generation, which the original authorization explicitly excluded. No further cloud call is authorized until the user approves a new bounded run. Existing failed run state and publication history remain intact.
