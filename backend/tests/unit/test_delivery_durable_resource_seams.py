"""Actual adapters and durable encoders; only storage and HTTP are offline doubles."""
import json
import socket
from types import SimpleNamespace

import httpx
import pytest
from app.core.ids import content_hash
from app.infrastructure.checkpointer.v2_planning_runtime import DurableBody, DurableIndex
from app.infrastructure.providers.v2_attempts import V2RecoveryBlocked, wire
from app.infrastructure.resources.github import GitHubResourceIndex
from app.infrastructure.resources.tavily import TavilyResourceIndex
from app.infrastructure.resources.teaching_body import GitHubTeachingBody

from tests.unit.test_deep_audit_resource_adapters import body_adapter
from tests.unit.test_tavily_resource_index import query, streaming_json
from tests.unit.test_teaching_body import candidate


class ReceiptStore:
    """Storage-only double: executes the real encode function and JSON roundtrip."""
    def __init__(self):
        self.scope, self.project_id = query().scope, "project"
        self.manifest = {"budget": {"search_cost_micros": 100}, "product_semantics": "planning-v2-product-v2"}
        self.current_review_scope = [{"outcome_id": "tool.calling.input_validation", "text": "Tool Calling"}]
        self.current_review_candidate_hash = "synthetic_frozen_candidate"
        self.rows, self.usage = {}, []

    def call(self, *, step, payload, invoke, encode, **_):
        key = content_hash({"step": step, "payload": payload})
        if key not in self.rows:
            value, usage = encode(invoke(key))
            self.rows[key] = json.loads(json.dumps(wire(value)))
            self.usage.append(usage)
        return self.rows[key]


@pytest.fixture(autouse=True)
def no_real_network(monkeypatch):
    def reject(*_, **__):
        raise AssertionError("No DNS/socket in offline resource bridge tests")
    monkeypatch.setattr(socket, "socket", reject)
    monkeypatch.setattr(socket, "getaddrinfo", reject)


@pytest.mark.parametrize("adapter", ["github", "web"])
def test_empty_response_through_durable_adapter_is_known_success_and_replays(adapter):
    requests = []
    index = (GitHubResourceIndex(transport=httpx.MockTransport(lambda r: requests.append(r)
        or streaming_json({"items": []}))) if adapter == "github" else
        TavilyResourceIndex("synthetic", transport=httpx.MockTransport(lambda r: requests.append(r)
        or streaming_json({"results": []}))))
    ledger = ReceiptStore()
    durable = DurableIndex(ledger, index, adapter)
    assert durable.find(query()) == durable.find(query()) == []
    assert len(requests) == 1 and ledger.usage == [{"searches": 1, "total_requests": 1}]
    assert next(iter(ledger.rows.values()))["kind"] == "search"


@pytest.mark.parametrize("adapter", ["github", "web"])
@pytest.mark.parametrize("status,stop", [(404, False), (500, False), (403, True), (429, True)])
def test_known_search_http_status_is_retained_and_never_unknown(adapter, status, stop):
    transport = httpx.MockTransport(lambda _: httpx.Response(status))
    index = GitHubResourceIndex(transport=transport) if adapter == "github" else TavilyResourceIndex("synthetic", transport=transport)
    ledger = ReceiptStore()
    value = DurableIndex(ledger, index, adapter).find(query())
    assert value.status == "failed" and value.stop_required is stop
    assert value.requests == 1 and value.receipts[0]["http_status"] == status
    assert next(iter(ledger.rows.values()))["kind"] == "search_status"


def test_real_transport_lost_response_remains_unknown():
    def lost(request):
        raise httpx.ReadTimeout("synthetic timeout", request=request)
    ledger = ReceiptStore()
    DurableIndex(ledger, GitHubResourceIndex(transport=httpx.MockTransport(lost)), "github").find(query())
    row = next(iter(ledger.rows.values()))
    assert row["kind"] == "failure" and row["value"]["dispatch_unknown"] is True


def test_known_unread_body_replays_metering_without_read_or_reader_dispatch():
    index, calls = body_adapter("[Contributing](CONTRIBUTING.md)", {})
    ledger = ReceiptStore()
    durable = DurableBody(ledger, index)
    assert durable.supports_outcome_selection
    options = {"must_teach": ("Tool Calling",)}
    first = durable.read(candidate(), **options)
    restored = durable.read(candidate(), **options)
    assert first.status == restored.status == "unread"
    assert first.reason == restored.reason == "no_supported_teaching_chapter"
    assert first.requests == restored.requests == len(calls) == 1
    assert first.bytes_read == restored.bytes_read > 0
    assert ledger.usage == [{"total_requests": 1, "body_bytes": first.bytes_read}]
    assert "Contributing" not in json.dumps(ledger.rows)


def test_cold_body_receipt_without_old_usage_does_not_invent_zero_or_redispatch():
    ledger = ReceiptStore()
    ledger.call = lambda **_: {"kind": "body_metadata", "value": {"status": "failed"}}
    body = SimpleNamespace(read=lambda *_args, **_kwargs: pytest.fail("No redispatch"))
    with pytest.raises(V2RecoveryBlocked, match="trustworthy usage"):
        DurableBody(ledger, body).read(candidate())


def test_product_v2_selection_retains_historical_body_only_identity_and_cannot_redispatch():
    index, requests = body_adapter("[Tool Calling](docs/tool.md)", {"docs/tool.md": "# Tool Calling\nSynthetic text"})
    ledger = ReceiptStore()
    options = {"max_bytes": 65536, "timeout_seconds": 15}
    first = DurableBody(ledger, index).read(candidate(), **options)
    first.close()
    with pytest.raises(V2RecoveryBlocked, match="Body-only"):
        DurableBody(ledger, index).read(candidate(), must_teach=("Tool Calling",), **options)
    assert len(requests) == 2 and len(ledger.rows) == 1
    with pytest.raises(V2RecoveryBlocked, match="frozen review scope"):
        DurableBody(ledger, index).read(candidate(), must_teach=("Unapproved scope",), **options)
    assert len(ledger.rows) == 1


def test_legacy_durable_body_does_not_enable_new_selection_or_change_options():
    ledger = ReceiptStore()
    del ledger.manifest["product_semantics"]
    durable = DurableBody(ledger, SimpleNamespace(supports_outcome_selection=True))
    assert not durable.supports_outcome_selection


def test_outcome_scope_reaches_actual_body_chapter_and_receipt_contains_no_text():
    index, calls = body_adapter("[Contributing](CONTRIBUTING.md)\n[Tool Calling](docs/tool.md)",
                                {"docs/tool.md": "# Tool Calling\nActual synthetic explanation"})
    ledger = ReceiptStore()
    body = DurableBody(ledger, index).read(candidate(), must_teach=("Tool Calling",))
    assert body.status == "succeeded" and calls[-1].endswith("/contents/docs/tool.md")
    assert body.requests == len(calls) == 2
    assert "Actual synthetic explanation" not in json.dumps(ledger.rows)
    body.close()


def test_search_caption_survives_real_adapter_durable_serialization():
    index = TavilyResourceIndex("synthetic", transport=httpx.MockTransport(lambda _: streaming_json(
        {"results": [{"url": "https://github.com/owner/tutorial", "title": "Readable tutorial"}]})))
    ledger = ReceiptStore()
    result = DurableIndex(ledger, index, "web").find(query())
    assert result[0].title == "Readable tutorial" and result[0].source_note == ""


def test_web_body_not_supported_is_known_unread_without_any_http():
    from dataclasses import replace
    ledger = ReceiptStore()
    body = DurableBody(ledger, GitHubTeachingBody()).read(replace(candidate(), url="https://docs.example.com/tutorial",
                                                               discovery={"source": "web"}))
    assert body.status == "unread" and body.requests == 0
    assert ledger.usage == [{"total_requests": 0, "body_bytes": 0}]


def test_empty_github_reaches_real_web_adapter_but_unsupported_web_body_is_not_fake_reviewed():
    from app.application.teaching_resource_research import ResourceResearcher
    from app.domain.planning.resource_research import ResearchSession, research_input_hash

    from backend.tests.unit import test_resource_research as f
    p, plan, coverage, gaps = f.inputs()
    budget = f.ResearchBudget()
    ledger, requests = ReceiptStore(), []
    github = GitHubResourceIndex(transport=httpx.MockTransport(lambda r: requests.append(r)
        or streaming_json({"items": []})))
    web = TavilyResourceIndex("synthetic", transport=httpx.MockTransport(lambda r: requests.append(r)
        or streaming_json({"results": [{"url": "https://docs.example.com/tutorial", "title": "Public candidate"}]})))
    class NoReader:
        def generate_structured(self, **_):
            pytest.fail("Unsupported Web body must never enter Reader")
    researcher = ResourceResearcher(github=DurableIndex(ledger, github, "github"),
        web=DurableIndex(ledger, web, "web"), body_reader=DurableBody(ledger, GitHubTeachingBody()), llm=NoReader())
    # Legacy here deliberately keeps the old body identity; v2 algorithm has
    # a separate partial/fairness test, not synthetic Web reading support.
    session = ResearchSession("offline", research_input_hash(gaps, plan, coverage, p, budget,
        project_id="project", checked_at=f.STAMP, actor_id="actor"), budget)
    result = researcher.research(gaps, plan=plan, coverage=coverage, profile=p, session=session,
                                scope=f.SCOPE, project_id="project", checked_at=f.STAMP)
    assert len(requests) == 2 and not session.blocked and session.snapshot().pending_count == 0
    assert result.entries[0].status == "unresolved" and "body_unread" in result.entries[0].reason_codes
    assert session.usage["total_requests"] == 2 and session.usage["reader_requests"] == 0
