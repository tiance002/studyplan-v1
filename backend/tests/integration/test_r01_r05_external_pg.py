"""One new owned PG attempt proves known-invalid W5 receipt settlement."""
import json
from pathlib import Path

import httpx
import psycopg
import pytest
from app.core.errors import ValidationAppError

from backend.tests.integration import test_w5_owned_runner_pg as w5
from backend.tests.integration.test_w5_owned_runner_pg import loopback_only as loopback_only
from scripts import planning_v2_scenario_a as runner
from scripts.planning_v2_acceptance_external import ledger_snapshot

pytestmark = pytest.mark.postgres
EVIDENCE = Path(__file__).resolve().parents[3] / "var/r01-r05-fix/owned-pg"


@pytest.fixture(scope="module")
def db():
    old = w5.EVIDENCE
    w5.EVIDENCE = EVIDENCE
    generator = w5.db.__wrapped__()
    try:
        yield next(generator)
    finally:
        generator.close()
        w5.EVIDENCE = old


@pytest.fixture(scope="module")
def checkpoint_db():
    old = w5.EVIDENCE
    w5.EVIDENCE = EVIDENCE
    generator = w5.checkpoint_db.__wrapped__()
    try:
        yield next(generator)
    finally:
        generator.close()
        w5.EVIDENCE = old


def test_invalid_finish_settles_known_failure_and_never_redispatches(db, checkpoint_db, monkeypatch):
    real_mock = httpx.MockTransport

    def invalid_mock(handler):
        def respond(request):
            response = handler(request)
            if request.url.host == "api.deepseek.com" and request.method == "POST":
                envelope = response.json()
                envelope["choices"][0]["finish_reason"] = {"bad": "stop"}
                return httpx.Response(200, json=envelope)
            return response
        return real_mock(respond)

    monkeypatch.setattr(httpx, "MockTransport", invalid_mock)
    folder, packet, options, run, cold, requests = w5.make(db, checkpoint_db, monkeypatch)
    path = folder / "prepared.json"
    assert runner.worker_tick(path, external=cold(), **options)
    record, receipt = ledger_snapshot(folder / "mock-model-global")[0]
    with psycopg.connect(db.migrator_dsn) as conn:
        status, payload = conn.execute(
            "SELECT status,response_payload FROM ai_provider_attempts WHERE run_id=%s AND attempt_id=%s",
            (run, record["attempt_id"])).fetchone()
        assert status == receipt["status"] == "failed"
        assert payload["value"]["error_class"] == receipt["error_class"] == "finish_reason_invalid"
        assert payload["value"]["dispatch_unknown"] is receipt["unknown"] is False
        assert receipt["usage"]["total_tokens"] == 36
        assert payload["manifest_hash"] == packet["manifest"]["manifest_hash"]
        assert conn.execute("SELECT count(*) FROM plan_drafts WHERE run_id=%s", (run,)).fetchone()[0] == 0
    with pytest.raises(ValidationAppError):
        runner.worker_tick(path, external=cold(), **options)
    assert len(requests) == len(ledger_snapshot(folder / "mock-model-global")) == 1
    (folder / "r05-receipt-result.json").write_text(json.dumps({"run_id": run,
        "status": status, "unknown": False, "requests": 1, "redispatch": 0}), encoding="utf8")
