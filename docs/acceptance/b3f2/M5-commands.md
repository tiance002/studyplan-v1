# Fresh verification commands

All commands ran from `D:/studyplan`, except npm commands from `D:/studyplan/frontend`.

```powershell
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
.venv/Scripts/python.exe -m pytest backend/tests -ra
.venv/Scripts/python.exe -m ruff check backend/app backend/alembic/versions/0010_resource_knowledge_links.py backend/tests/e2e/test_b3f2_learning_route.py backend/tests/unit/test_b3f2_planning.py
.venv/Scripts/python.exe -m mypy backend/app
npm run build
npm test
npm run test:auth
npm run test:workspace
node scripts/b3f2-browser.cjs
git diff --check
```

Raw pytest output and its exit code: `M5-backend-tests.txt`. Ruff/mypy: `M5-lint.txt`, `M5-types.txt`. npm commands and individual exit codes: `M5-frontend.txt`.

The real local browser command exited 0 and printed:

```json
{"stages":9,"nodes":27,"widths":[1366,1440,1920],"provider":"fake","errors":[]}
```

Detailed layout measurements and verified URLs: `browser/results.json`. This acceptance used no route interception or mock API: it registered against the local backend, generated and approved its draft and read the published plan/workspace back from PostgreSQL. The backend model provider was explicitly Fake, independently checked before generation. A first browser-script run encountered an ambiguous h1/h2 selector; the script was corrected to select the stage h1, then the entire workflow was rerun successfully.

The adapter test originally referenced a nonexistent DTO run_id in its final ledger assertion; this test assertion was corrected to query the actor's project run. The corrected test passes through actual PG StateGraph and MockTransport. UTF-8 mode avoids Windows subprocess output decoding warnings when migration fixture logs contain Unicode. No business implementation was changed to mask these harness issues.
