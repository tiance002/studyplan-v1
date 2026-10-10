"""Focused W5 response classification through actual adapters; HTTP is mocked."""
import json

import httpx
import pytest
from app.ports.llm import LLMFailure

from backend.tests.unit.test_w5_acceptance_external import (
    candidate,
    file_response,
    invoke,
    model_response,
    ready,
)
from backend.tests.unit.test_w5_acceptance_external import no_network as no_network
from backend.tests.unit.test_w5_acceptance_external import owned as owned
from scripts import planning_v2_acceptance_external as ext


@pytest.mark.parametrize("finish", [{"invalid": "stop"}, ["stop"], 1, True, None])
def test_complete_invalid_finish_is_known_failure(owned, finish):
    settings, options, _ = owned
    external, _calls = ready(owned)
    envelope = model_response().json()
    envelope["choices"][0]["finish_reason"] = finish
    result = invoke(external, settings, lambda _r: httpx.Response(200, json=envelope))
    assert isinstance(result, LLMFailure) and not result.dispatch_unknown
    assert result.error_class == "finish_reason_invalid"
    receipt = ext.ledger_snapshot(options["model_ledger"])[0][1]
    assert receipt["status"] == "failed" and receipt["unknown"] is False
    assert receipt["usage"]["total_tokens"] == 46
    assert receipt["finish_reason"] is None
    assert json.loads((options["evidence_dir"] / "STOP.json").read_bytes())["unknown"] is False
    external.close()


@pytest.mark.parametrize("lost", [False, True])
def test_corrupt_body_and_real_transport_loss_keep_distinct_receipts(owned, lost):
    settings, options, _ = owned
    external, _calls = ready(owned)
    class Broken(httpx.SyncByteStream):
        def __iter__(self):
            yield b"{"
            if lost:
                raise httpx.ReadError("synthetic interrupted reply")
    ports = external.resource_ports(settings, github_transport=httpx.MockTransport(lambda _r:
        httpx.Response(200, headers={"content-type": "application/json"}, stream=Broken())))
    result = ports.body_reader.read(candidate(), max_bytes=65536)
    assert result.status == ("unknown" if lost else "failed")
    operation = ext.ledger_snapshot(options["evidence_dir"] / "external-body-operations")[0][1]
    wire = ext.ledger_snapshot(options["evidence_dir"] / "external-body-http")[0][1]
    assert operation["unknown"] is wire["unknown"] is lost
    assert wire["status"] == ("reconciliation_required" if lost else "succeeded")
    assert operation["status"] == ("unknown" if lost else "failed")
    external.close()


def test_declared_body_capacity_rejection_is_consumed_known_unread(owned):
    settings, options, _ = owned
    external, _calls = ready(owned)
    sent = []

    def respond(request):
        sent.append(request)
        if request.url.path.endswith("/readme"):
            return file_response("README.md", "[Lesson](lesson.md)")
        return httpx.Response(200, headers={"content-type": "application/json", "content-length": "70000"},
                              stream=httpx.ByteStream(b"not consumed"))

    ports = external.resource_ports(settings, github_transport=httpx.MockTransport(respond))
    result = ports.body_reader.read(candidate(), paths=("lesson.md",), max_bytes=65536)
    assert result.status == "unread" and len(sent) == 2
    assert not (options["evidence_dir"] / "STOP.json").exists()
    receipt = ext.ledger_snapshot(options["evidence_dir"] / "external-body-http")[-1][1]
    assert receipt["status"] == "unread" and not receipt["unknown"]
    assert receipt["response_bytes"] == 0
    assert receipt["error_class"] == "declared_capacity_rejected"
    external.check()
    external.close()


@pytest.mark.parametrize("case", ["stream-overrun", "wire-overrun", "bad-encoding", "bad-length", "bad-mime"])
def test_known_body_rejection_blocks_without_network_unknown(owned, case):
    settings, options, _ = owned
    external, _calls = ready(owned)
    def respond(_request):
        headers = {"content-type": "application/json"}
        body = b"x" * (262145 if case == "wire-overrun" else 65537) if case.endswith("overrun") else b"x"
        headers.update({"content-encoding": "gzip"} if case == "bad-encoding" else
                       {"content-length": "-1"} if case == "bad-length" else
                       {"content-type": "text/html"} if case == "bad-mime" else {})
        return httpx.Response(200, headers=headers, stream=httpx.ByteStream(body))
    ports = external.resource_ports(settings, github_transport=httpx.MockTransport(respond))
    result = ports.body_reader.read(candidate(), max_bytes=65536)
    assert result.status == "failed"
    receipt = ext.ledger_snapshot(options["evidence_dir"] / "external-body-http")[0][1]
    assert receipt["status"] == "failed" and not receipt["unknown"]
    operation = ext.ledger_snapshot(options["evidence_dir"] / "external-body-operations")[0][1]
    assert operation["status"] == "failed" and not operation["unknown"]
    if case.endswith("overrun"):
        assert result.bytes_read == receipt["response_bytes"] == (262145 if case == "wire-overrun" else 65537)
    assert json.loads((options["evidence_dir"] / "STOP.json").read_bytes())["unknown"] is False
    external.close()
