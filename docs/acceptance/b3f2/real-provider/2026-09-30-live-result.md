# B3-F2 first controlled real-provider run — 2026-09-30

## Outcome

**INCOMPLETE — `reconciliation_required`.** This is the only real Run recorded
for this acceptance:

- Run ID: `run_c4fbba87293144abaead9585f129ce39`
- Final status: `reconciliation_required`
- Three provider requests returned successfully. The fourth request,
  `planning.structure` / `stage.tools`, ended as `provider_transport_unknown`.

The expected complete flow contains 19 requests. This Run stopped at an
unknown transport outcome, so the acceptance **cannot be declared a complete
19-request PASS**. No further real Run or real-provider request was made to
resolve it.

## Recorded request results

| Request | Input tokens | Output tokens | Result |
| --- | ---: | ---: | --- |
| Outline | 8803 | 1352 | Success |
| Structure / `environment` | 801 | 460 | Success |
| Structure / `model_api` | 817 | 496 | Success |
| Structure / `stage.tools` | Unknown | Unknown | `provider_transport_unknown` |

No `finish_reason=length` or `provider_output_truncated` was recorded. The
transport-unknown request has no confirmed provider response or finish reason.

## External context and interpretation

The operator confirms that the network was manually changed near the
`stage.tools` failure. This is an important external factor to retain with the
acceptance record. The available evidence does **not** prove that this was the
only root cause.

The transport result does not establish whether the provider received or
completed that request. Preserve `reconciliation_required`; do not infer a
successful response or dispatch another request under a new Attempt.

## Transport diagnostics patch

`OpenAICompatibleLLM` now adds `transport_exception_type` (for example,
`ReadError` or `RemoteProtocolError`) to diagnostics when an HTTPX timeout or
transport exception is caught. It records only the exception class name, not
the exception text, API key, or Authorization header. The behavior remains:

- `dispatch_unknown=True`
- no automatic retry
- reconcile before any further dispatch

The historical Attempt and its evidence were not modified or backfilled. Its
specific transport exception class is therefore not inferred retroactively.

## Offline verification

- `test_transport_failure_records_exception_type_without_leaking_or_retrying`:
  PASS — MockTransport records the exception type, leaks neither the API key
  nor Authorization text, and receives one request.
- `test_b3_paid_ledger_replay_and_unknown`: PASS — MockTransport confirms the
  unresolved Attempt is not dispatched again; exactly one Attempt row remains
  in `reconciliation_required`.
- Real DeepSeek calls during this diagnostics patch: **NOT RUN**.
