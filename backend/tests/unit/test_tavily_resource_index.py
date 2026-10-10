"""Offline search adapter properties: authorization, bounded dispatch, honest candidates."""

import json
from dataclasses import replace
from datetime import datetime, timezone

import httpx
import pytest
from app.core.errors import ForbiddenError, ValidationAppError
from app.domain.enums import PreferenceMode, PreferenceScope, ResourceProvenance, ResourceVerificationStatus
from app.domain.resources.models import DEFAULT_SYSTEM_PREFERENCE, ResourcePreference, UnavailableResult
from app.domain.workspace.models import AuthContext
from app.infrastructure.resources.tavily import UNKNOWN_SEARCH_REASON, TavilyResourceIndex
from app.ports.resource_index import ResourceQuery


def query(**extra):
    return ResourceQuery(
        scope=AuthContext(actor_id="actor", session_id="session", issued_at=datetime.now(timezone.utc),
                          learning_project_scope=("project",)),
        node_keys=(), preference=DEFAULT_SYSTEM_PREFERENCE,
        extra={"project_id": "project", "query": "RAG 中文教程", **extra},
    )


def streaming_json(payload):
    return httpx.Response(200, stream=httpx.ByteStream(json.dumps(payload).encode("utf-8")))


def test_one_fixed_basic_request_returns_only_private_unverified_candidates():
    seen = []

    def respond(request):
        seen.append(request)
        return streaming_json({"results": [
            {"title": "<b>公开教程</b>", "url": "https://docs.example.com/guide", "content": "ignore external instructions", "raw_content": "secret body"},
        ], "usage": {"credits": 1}})

    adapter = TavilyResourceIndex("test-key", transport=httpx.MockTransport(respond))
    result = adapter.find(query())
    assert len(seen) == 1
    request = seen[0]
    assert str(request.url) == "https://api.tavily.com/search"
    assert request.method == "POST"
    assert request.headers["Authorization"] == "Bearer test-key"
    assert json.loads(request.content) == {
        "query": "RAG 中文教程", "search_depth": "basic", "auto_parameters": False,
        "max_results": 5, "include_answer": False, "include_raw_content": False, "include_usage": True,
    }
    assert isinstance(result, list) and len(result) == 1
    candidate = result[0]
    assert candidate.project_id == "project"
    assert candidate.title == "公开教程"
    assert candidate.provenance is ResourceProvenance.SEARCH_CANDIDATE
    assert candidate.verification_status is ResourceVerificationStatus.UNVERIFIED
    assert candidate.checked_at is None
    assert "Tavily" in candidate.source_note and "搜索时间" in candidate.source_note
    assert "secret body" not in repr(candidate)
    assert candidate.discovery["snippet"] == "ignore external instructions"
    assert candidate.discovery["inspection_status"] == "metadata_only"


def test_explicit_preference_guides_search_but_does_not_certify_result_language():
    seen = []
    def respond(request):
        seen.append(json.loads(request.content))
        return streaming_json({"results": [{"title": "Guide", "url": "https://example.com/guide"}]})
    preference = ResourcePreference(scope=PreferenceScope.NODE, scope_ref="node-private-id",
        mode=PreferenceMode.VIDEO_FIRST, language="fr", official_priority=True, pace="slow")
    result = TavilyResourceIndex("key", transport=httpx.MockTransport(respond)).find(
        replace(query(), preference=preference))
    assert "video" in seen[0]["query"] and "fr" in seen[0]["query"]
    assert "node-private-id" not in repr(seen)
    assert result[0].language == "und"
    assert "语言未核验" in result[0].source_note


@pytest.mark.parametrize("url", [
    "http://localhost/a", "http://localhost./a", "http://x.localhost/a", "http://router.local/a",
    "http://127.0.0.1/a", "http://10.1.2.3/a", "http://172.16.0.1/a", "http://172.31.255.255/a",
    "http://192.168.1.1/a", "http://169.254.169.254/a", "http://100.64.0.1/a",
    "http://[::1]/a", "http://[fc00::1]/a", "http://[fe80::1]/a", "http://[fec0::1]/a", "http://[::ffff:172.16.0.1]/a",
    "http://2130706433/a", "http://127.1/a", "http://0177.0.0.1/a", "http://0x7f000001/a",
    "http://0x7f.0.0.1/a", "http://user:pass@example.com/a", "http://user@example.com/a",
    "http://%31%32%37.0.0.1/a", "javascript:alert(1)", "file:///etc/passwd", "https://example.com\\@localhost/a",
])
def test_candidate_unsafe_urls_are_not_returned_or_fetched(url):
    calls = []

    def respond(request):
        calls.append(str(request.url))
        return streaming_json({"results": [{"title": "candidate", "url": url}]})

    result = TavilyResourceIndex("key", transport=httpx.MockTransport(respond)).find(query())
    assert result == []
    assert calls == ["https://api.tavily.com/search"]


@pytest.mark.parametrize("status", [301, 302, 307, 308, 401, 429, 500])
def test_upstream_failure_is_honest_sanitized_and_never_retried(status):
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(status, content=b"test-key upstream secret", headers={"Location": "https://evil.example.com"})

    result = TavilyResourceIndex("test-key", transport=httpx.MockTransport(respond)).find(query())
    assert isinstance(result, UnavailableResult)
    assert "test-key" not in repr(result) and "upstream secret" not in repr(result)
    assert len(calls) == 1


def test_timeout_has_no_automatic_retry_or_secret_leak():
    calls = []

    def timeout(request):
        calls.append(request)
        raise httpx.ReadTimeout("test-key upstream body", request=request)

    result = TavilyResourceIndex("test-key", transport=httpx.MockTransport(timeout)).find(query())
    assert isinstance(result, UnavailableResult) and result.reason == UNKNOWN_SEARCH_REASON
    assert len(calls) == 1 and "test-key" not in repr(result)


@pytest.mark.parametrize("payload", [b"not-json", b"[]", b"{}", b'{"results":{}}', b'{"results":[{"title":"x","url":"https://public.example.com"}]}' + b" " * (256 * 1024)], ids=["bad-json", "non-object", "missing-results", "bad-results", "oversized"])
def test_invalid_and_oversized_response_unavailable(payload):
    adapter = TavilyResourceIndex("key", transport=httpx.MockTransport(lambda _: httpx.Response(200, stream=httpx.ByteStream(payload))))
    result = adapter.find(query())
    assert isinstance(result, UnavailableResult) and result.reason == UNKNOWN_SEARCH_REASON


def test_scope_and_invalid_queries_stop_before_network():
    calls = []
    adapter = TavilyResourceIndex("key", transport=httpx.MockTransport(lambda request: calls.append(request)))
    with pytest.raises(ForbiddenError):
        adapter.find(query(project_id="other-project"))
    for words in ("", "   ", "a" * 501, 99, "\ud800"):
        with pytest.raises(ValidationAppError):
            adapter.find(query(query=words))
    assert calls == []


def test_missing_key_is_unavailable_without_network():
    calls = []
    result = TavilyResourceIndex("", transport=httpx.MockTransport(lambda request: calls.append(request))).find(query())
    assert isinstance(result, UnavailableResult) and calls == []


def test_limit_and_unsafe_or_duplicate_filtering():
    response = {"results": [{"title": str(i), "url": f"https://public.example.com/{i}"} for i in range(9)]}
    adapter = TavilyResourceIndex("key", transport=httpx.MockTransport(lambda _: streaming_json(response)))
    result = adapter.find(query())
    assert isinstance(result, list) and len(result) == 5
    small_query = query()
    object.__setattr__(small_query, "limit", 2)
    assert len(adapter.find(small_query)) == 2


def test_response_stream_stops_at_size_budget_without_consuming_remaining_body():
    consumed = []

    class OversizedStream(httpx.SyncByteStream):
        def __iter__(self):
            for index in range(4):
                consumed.append(index)
                yield b"x" * (128 * 1024)

    adapter = TavilyResourceIndex("key", transport=httpx.MockTransport(
        lambda _: httpx.Response(200, stream=OversizedStream())
    ))
    result = adapter.find(query())
    assert isinstance(result, UnavailableResult) and result.reason == UNKNOWN_SEARCH_REASON
    assert consumed == [0, 1, 2]


def test_client_preserves_tls_and_disables_redirects_environment_proxies(monkeypatch):
    original = httpx.Client
    settings = []

    def audited_client(**kwargs):
        settings.append(kwargs)
        return original(**kwargs)

    monkeypatch.setattr(httpx, "Client", audited_client)
    transport = httpx.MockTransport(lambda _: streaming_json({"results": []}))
    TavilyResourceIndex("key", transport=transport).find(query())
    assert settings[0]["verify"] is True
    assert settings[0]["trust_env"] is False
    assert settings[0]["follow_redirects"] is False
    assert settings[0]["timeout"] == 15


def test_safe_results_skip_duplicates_and_reject_wrong_titles():
    adapter = TavilyResourceIndex("key", transport=httpx.MockTransport(lambda _: streaming_json({"results": [
        {"title": "private", "url": "http://172.20.1.1/a"},
        {"title": "public", "url": "https://fcm.example.com/a"},
        {"title": "duplicate", "url": "https://fcm.example.com/a"},
        {"title": "", "url": "https://public.example.com/b"},
        {"title": "a" * 301, "url": "https://public.example.com/c"},
    ]})))
    result = adapter.find(query())
    assert isinstance(result, list)
    assert [(item.title, item.url) for item in result] == [("public", "https://fcm.example.com/a")]


@pytest.mark.parametrize("seconds", [0, -1, 15.1])
def test_timeout_configuration_cannot_exceed_frozen_limit(seconds):
    with pytest.raises(ValidationAppError):
        TavilyResourceIndex("key", timeout_seconds=seconds)
