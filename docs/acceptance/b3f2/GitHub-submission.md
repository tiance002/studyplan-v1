# B3-F2 progress submission — 2026-09-29

This submission saves the current implementation on `codex/b3-f1`; it does not declare the entire B3-F2 goal accepted. It includes the master integration, per-run Agent/Python/unsupported selection, complete Agent demo blueprint, reviewed chapter index, resource/node persistence and workspace fixes. The earlier registration UX fix remains in commit `76643cf`.

Fresh pre-submission checks:

- `.venv/Scripts/python.exe -m pytest backend/tests -q -ra`: exit 0, completed through 100%, no failures or skips reported.
- `.venv/Scripts/python.exe -m ruff check backend/app backend/alembic/versions/0010_resource_knowledge_links.py backend/tests/e2e/test_b3f2_learning_route.py backend/tests/unit/test_b3f2_planning.py`: exit 0.
- `.venv/Scripts/python.exe -m mypy backend/app`: exit 0, 83 source files.
- `npm run build`: exit 0.
- `npm test`: exit 0, 4 layout tests passed.
- `npm run test:auth`: exit 0, auth browser regression passed.
- `npm run test:workspace`: exit 0, selected-node goal, chapter URL, neutral labels, refresh position and subknowledge passed with mocked API responses.
- `git diff --cached --check`: exit 0.

Cloud/paid model verification: **NOT RUN**. Full live-model example, live frontend screenshots at all requested widths and the final acceptance/delivery audit remain pending. Migration 0010 and reviewed-pack seeding were exercised by database tests; application to the existing development database is not asserted here.

Pre-existing `.workbuddy/` and `design-preview/` are excluded. No environment files, credentials or generated build output are included.
