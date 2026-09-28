# Personal OpenAI-compatible Model Settings Implementation Plan

> Execute directly using superpowers:executing-plans. User explicitly forbids subagents.

**Goal:** Users save private Base URL/model/API Key; each run fixes the selected revision.
**Architecture:** Existing AuthContext selects actor, PG RLS stores metadata/encrypted revisions, application service validates CAS and public HTTPS endpoint, composition creates per-run provider/runtime without shared mutation.
**Tech Stack:** Existing FastAPI/PG/httpx/StateGraph/React; cryptography for authenticated secret encryption (no new framework).
**Spec:** docs/design-package/B3-user-model-settings-design.md (approved).

## Constraints and review focus

- Only OpenAI-compatible chat/completions; no protocol selector, silent Fake or automatic paid retry.
- API Key never returned/logged/localStorage; independently configured encryption master key, fail closed.
- actor from server session; settings and run configuration binding constrained by RLS and ownership.
- Version CAS, preserved historical run configuration, concurrent requests do not mutate shared provider.
- HTTPS approved hostname only, public DNS/IP checks, no redirects/proxy inheritance; production network egress must also deny private/metadata.
- Tests must cover no-key setup startup, cross-actor isolation, missing/wrong encryption key, stale save, unsafe endpoint, two simultaneous runtime selections, public DTO and browser handling.

## Tasks

1. [x] Write failing PG settings tests; add 0007 settings/current/history/run binding migration, model settings port/service and encrypted PG repository. Test secret persistence, actor RLS, immutable metadata revision and CAS.
2. [x] Add URL policy tests and endpoint guard; add Settings encryption key/allowed hosts, per-run factory at composition, optional llm/executor selection in PlanService. Test runtime selection and no shared mutation. Startup allows configuring a personal provider without deployment key, but never Fake fallback.
3. [x] Add authenticated model-settings GET/PUT/DELETE DTO/routes, container dependency; test redaction and forbidden identities. Export OpenAPI/TS.
4. [x] Implement model settings React component and typed API methods; save/clear, version handling, provider status, missing configuration generation guard; no browser persistent secret.
5. [x] Migrate dedicated local B3 database using installation role; generate a separate encryption master key in ignored .env without touching provider credentials. Configure approved OpenAI/DeepSeek hosts. Browser verify saving/redaction/reload/clear; verify configured per-run pipeline via real HTTP/PG and existing model protocol Mock only where labeled.
6. [x] Full pytest, Ruff, mypy, frontend build; actual provider closure through selected personal configuration, retained attempt evidence, direct review, acceptance docs and commit. Production auth/egress limitations documented.

Each task uses a failing targeted check before implementation and passes its checks before proceeding. User has authorized writing the plan and implementing it directly; no additional execution handoff or subagent review.
