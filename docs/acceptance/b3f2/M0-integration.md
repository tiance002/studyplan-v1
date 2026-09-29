# M0 branch integration evidence

- Branch: `codex/b3-f1`
- Pre-integration HEAD: `76643cfc5f655b763a2e8f8954966669496fbe0e`
- Fetched remote master: `a9c469eb140121bef78767045bb742b5781b0a7c`
- Original merge-base: `b9e9cb0716a01084efdcbeb68fc00f7387790c5c`
- Integration commit: `6a187fce7ff22805f87f14bc0c60b8788d854529`

## Duplicate history and conflicts

The pairs 7da6ce1/932c434, f36e538/668f3bf and d299e87/a9c469e have identical Git trees. `git diff --quiet d299e87 origin/master` exited 0. Ordinary three-way merge reported 18 conflicts because the shared merge-base precedes both copies of B2-V. Every conflicting remote blob was checked byte-for-byte against the equivalent local B2-V blob before carrying forward the newer local version. No strategy option ours/theirs was used. `git diff --cached --quiet HEAD` exited 0 before the merge commit: integration introduced no file content changes, so all B3-F1 code/API/types and later repairs remain intact.

The retained later repairs include draft edit hash CAS, versioned catalog IDs, readback of the actual approved revision, preservation of learning history, run CAS/checkpoint reconciliation, browser auth/RLS/CSRF and personal encrypted model settings. There were no unknown transaction or migration semantics requiring approval.

Resolved paths:

- `backend/app/api/v1/deps.py`
- `backend/app/api/v1/routes.py`
- `backend/app/api/v1/schemas.py`
- `backend/app/api/v1/views.py`
- `backend/app/application/container.py`
- `backend/app/application/plan_service.py`
- `backend/app/composition.py`
- `backend/app/domain/planning/models.py`
- `backend/app/infrastructure/db/plan_repository.py`
- `backend/app/infrastructure/db/planning_catalog.py`
- `backend/app/infrastructure/db/run_repository.py`
- `backend/app/main.py`
- `backend/app/ports/runs.py`
- `backend/tests/e2e/test_b2v_http_end_to_end.py`
- `backend/tests/integration/test_pg_plan_repository.py`
- `backend/tests/unit/test_plan_publication.py`
- `contracts/openapi.json`
- `frontend/src/api/generated/schema.d.ts`

## Migrations

0004 is byte-identical to origin/master. 0005–0009 are absent from origin/master and were preserved; none was rewritten. SHA256 at integration:

- `0004_ownership_integrity.py`: `465d4bd7723969c294339ac783e4977a26503f0017c68f3efd7cccfbf52e0cdf`
- `0005_catalog_versions.py`: `ee46ba846ef0c382e182d982aa6853f4924457bc8d173c21c593d1912763ad5d`
- `0006_provider_results.py`: `71f4e462f98dc54c1701b91ae51704fb13ede90058ddffb8546af59a931f885b`
- `0007_model_settings.py`: `4c0072e8a39f6b0373187a50468d96c4676eb00173614de3844b07f7ce95f7b5`
- `0008_browser_auth.py`: `c0ab6a764345da287ff3cc9216bd57b0ee99ba75993d620bf9f5b207d8ec5c6b`
- `0009_auth_rls.py`: `41870710357c34c74bada74c10366711f93e304cf45df8017a1ba2ab0a827f30`

## Working tree and regression

No tracked uncommitted edits existed initially. Existing untracked `.workbuddy/` and `design-preview/` were left in place; their file SHA256 manifest is retained locally under `.git/b3f2-safety.json` and checked unchanged after merge. This private manifest is not committed.

Command: `.venv/Scripts/python.exe -m pytest backend/tests/e2e/test_b2v_http_end_to_end.py backend/tests/e2e/test_b3f1_access.py backend/tests/integration/test_pg_plan_repository.py backend/tests/unit/test_plan_publication.py -q -ra`

Raw output/exit code: [M0-tests.txt](M0-tests.txt). The final report must state actual passed/skipped totals.
