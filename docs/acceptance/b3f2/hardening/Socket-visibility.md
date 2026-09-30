# B3-F2.1 localhost Run visibility — PASS

## Proven harness defect and historical evidence limits

The original socket harness constructed `httpx.Client(...)` with default
`trust_env=True`. Installed HTTPX transport inspection in this environment
selected **HTTPProxy** even for a `http://127.0.0.1:...` URL. TestClient's ASGI
transport does not take that network/proxy path.

A controlled local proxy reproduces the recorded symptom deterministically:
forward POST to the actual app, drive its real PG/Fake Worker, then return
`{"detail":"Not Found"}` for GET from the proxy. The original harness fails at
`GET /api/v1/runs/{run_id}` with 404. The GET never reaches the intended API;
successful POST/committed waiting_user rows do not establish GET routing.

The fix is `trust_env=False` on the localhost socket test client. The new socket
helper follows the same rule. No application repository, RLS policy, migration,
database role, frontend 404 handling, or production query bypass was changed.
The real provider's own network client already uses `trust_env=False`.

Earlier M5/M7 documents inferred an RLS visibility race from row existence and
the presence of FORCE RLS. That inference is withdrawn. The original failures
did not retain request-origin/proxy traces, so this Goal cannot prove the origin
of **every historical** 404. It does prove the transport defect, an exact symptom
reproduction, and removal of that defect under a hostile proxy. No RLS defect
was reproduced. The standalone pre-change four tests also passed (28.79s),
consistent with an environment-dependent transport issue.

## Scope and transaction investigation

- API dependencies resolve the actor and project scope from the session cookie;
  requested project_id is checked against that scope. No secret was logged.
- Worker/application repositories share the intended database/container.
- `PgRunRepository._tx` opens a fresh connection/transaction per call and sets
  `app.project_id` transaction-locally before the query, on the same connection.
- The existing ai_runs RLS policy uses project_id; it does not require
  app.actor_id. Actor authentication and project authorization remain API duties.
- Actual missing runs produce the application's `{code,message,request_id,details}`
  error, distinct from generic router/proxy `{"detail":"Not Found"}`. The tests
  verify genuine missing-run 404 and unauthorized-project 403 too.

## Commands and evidence

```powershell
./.venv/Scripts/python.exe -m pytest backend/tests/e2e/test_b2v_socket_counterexamples.py -o addopts= -q
```

Pre-change: **PASS**, exit 0, 4 passed (28.79s). This alone did not prove a fix.

```powershell
./.venv/Scripts/python.exe -m pytest backend/tests/e2e/test_socket_proxy_isolation.py -o addopts= -q
```

Original transport: **FAIL**, exit 1, 1 failed (11.28s), exact generic GET 404
after successful POST/Worker. The retained regression additionally verifies the
waiting_user row through the same application-role repository before GET.

```powershell
./.venv/Scripts/python.exe -m pytest backend/tests/e2e/test_b2v_socket_counterexamples.py backend/tests/e2e/test_socket_proxy_isolation.py -o addopts= -q
```

After fix: **PASS**, exit 0, 5 passed (40.69s): original four plus proxy isolation.

```powershell
./.venv/Scripts/python.exe -m pytest backend/tests/e2e/test_b3f2_socket_visibility.py -o addopts= -q
```

**PASS**, exit 0, 1 test / **20 consecutive Runs** (124.92s): 20/20 waiting_user,
0 GET 404, all immediate queued and final GETs 200. Each Run uses the full
reviewed Agent pack, real localhost Uvicorn socket, PG, PG LangGraph checkpoint,
Fake LLM and Planning Worker: nine stages, 27/27 required nodes, 19 Fake calls.
Total 380 Fake dispatches. The application role is checked NOBYPASSRLS, and its
transaction project setting is asserted. Recorded row facts include actor,
project, Run ID, waiting_user status and version 3; no cookie/key/session secret.

There are no GET retries or post-generation sleeps. Only server startup has a
bounded readiness wait. Each assertion calls GET once; no frontend workaround.
The final suite repeats this test including added read-only inspector and
negative-scope assertions. All PG creation/seeding/drop is restricted by the
existing harness to disposable `studyplan_test_*` databases.

Raw evidence: `var/b3f2-hardening/socket-before.txt`, `socket-proxy-red.txt`,
`socket-green.txt`, `socket-twenty.txt`. Final no-exclusion result: `Regression.md`.
