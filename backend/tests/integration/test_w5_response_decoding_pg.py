"""Narrow new owned PG receipts over real Provider and encoded Mock HTTP."""
import json
from pathlib import Path

import httpx
import psycopg
import pytest
import zstandard
from app.core.errors import ValidationAppError

from backend.tests.integration import test_w5_owned_runner_pg as w5
from backend.tests.integration.test_w5_owned_runner_pg import loopback_only as loopback_only
from scripts import planning_v2_scenario_a as runner
from scripts.planning_v2_acceptance_external import ledger_snapshot

pytestmark = pytest.mark.postgres
EVIDENCE = Path(__file__).resolve().parents[3] / "var/codex-goals/w5-response-decoding-20261010/owned-final"


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
    generator = w5.checkpoint_db.__wrapped__()
    try:
        yield next(generator)
    finally:
        generator.close()


@pytest.mark.parametrize("bad", [False, True])
def test_encoded_model_global_and_native_pg_receipts_agree(db, checkpoint_db, monkeypatch, bad):
    real_mock = httpx.MockTransport

    def encoded_mock(handler):
        def respond(request):
            response = handler(request)
            if request.url.host == "api.deepseek.com" and request.method == "POST":
                raw = b"malformed compressed response" if bad else zstandard.ZstdCompressor().compress(response.content)
                return httpx.Response(200, headers={"content-encoding": "zstd"}, stream=httpx.ByteStream(raw))
            return response
        return real_mock(respond)

    monkeypatch.setattr(httpx, "MockTransport", encoded_mock)
    folder, packet, options, run, cold, requests = w5.make(db, checkpoint_db, monkeypatch)
    path = folder / "prepared.json"
    assert runner.worker_tick(path, external=cold(), **options)
    record, global_result = ledger_snapshot(folder / "mock-model-global")[0]
    with psycopg.connect(db.migrator_dsn) as conn:
        status, payload, output = conn.execute(
            "SELECT status,response_payload,output_tokens FROM ai_provider_attempts WHERE run_id=%s AND attempt_id=%s",
            (run, record["attempt_id"])).fetchone()
        assert payload["manifest_hash"] == packet["manifest"]["manifest_hash"]
        assert status == global_result["status"] == ("failed" if bad else "succeeded")
        if bad:
            assert payload["value"]["error_class"] == global_result["error_class"] == "model_response_decoding_failed"
            assert payload["value"]["dispatch_unknown"] is global_result["unknown"] is False
            assert global_result["usage"] is output is None
            assert conn.execute("SELECT status FROM ai_runs WHERE run_id=%s", (run,)).fetchone()[0] == "failed"
        else:
            assert payload["value"]["input_tokens"] == global_result["usage"]["prompt_tokens"] == 20
            assert payload["value"]["output_tokens"] == output == global_result["usage"]["completion_tokens"] == 16
            assert payload["value"]["finish_reason"] == global_result["finish_reason"] == "stop"
        assert conn.execute("SELECT count(*) FROM plan_drafts WHERE run_id=%s", (run,)).fetchone()[0] == 0
    if bad:
        with pytest.raises(ValidationAppError):
            runner.worker_tick(path, external=cold(), **options)
    else:
        frozen = runner.read_review(path, external=cold(), **options)
        assert frozen["review"]["stage"] == "goal_analysis"
        assert not runner.worker_tick(path, external=cold(), **options)
    assert len(requests) == 1
    (folder / "encoding-result.json").write_text(json.dumps({"bad": bad, "status": status,
        "run_id": run, "global_count": 1, "owned_draft_count": 0}), encoding="utf-8")
