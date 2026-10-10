"""Offline security matrix for the minimal teaching-body seam."""
import base64
import hashlib
import json
import socket
from types import SimpleNamespace

import httpx
import pytest
from app.core.ids import content_hash
from app.domain.enums import MediaType, ResourceProvenance, ResourceVerificationStatus
from app.domain.resources.models import ResourceRecord


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("Real DNS/socket forbidden in teaching-body tests")
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)


def candidate(*, source="github", url="https://github.com/author/course", ref="main"):
    return ResourceRecord(resource_id="old-private-id", project_id="project", url=url,
        title="Course", media_type=MediaType.REPO, language="und",
        provenance=ResourceProvenance.SEARCH_CANDIDATE,
        verification_status=ResourceVerificationStatus.UNVERIFIED,
        discovery={"source": source, "repo": {"owner": "author", "name": "course", "default_branch": ref}})


def file_payload(path, raw, **changes):
    result = {"type": "file", "path": path, "encoding": "base64", "sha": "a" * 40,
        "size": len(raw), "content": base64.b64encode(raw).decode()}
    result.update(changes)
    return result


def reply(data, *, mime="application/json", status=200, headers=None):
    response_headers = {} if mime is None else {"Content-Type": mime}
    response_headers.update(headers or {})
    raw = data if isinstance(data, bytes) else json.dumps(data).encode()
    return httpx.Response(status, headers=response_headers, stream=httpx.ByteStream(raw))


def make_adapter(respond, **kwargs):
    from app.infrastructure.resources.teaching_body import GitHubTeachingBody
    return GitHubTeachingBody(transport=httpx.MockTransport(respond), **kwargs)


def standard_response(request, *, text=b"# Lesson\nEvidence\n", readme=None):
    if request.url.path.endswith("/readme"):
        return reply(file_payload("README.md", readme or b"# Index\n[Lesson](chapters/lesson.md)"))
    assert request.url.path == "/repos/author/course/contents/chapters/lesson.md"
    return reply(file_payload("chapters/lesson.md", text))


def test_success_actual_chapter_identity_preserves_bom_and_clearable_body():
    seen = []
    text = "\ufeff# Lesson\n中文 evidence\n"
    def respond(request):
        seen.append(request)
        assert "authorization" not in request.headers
        assert request.headers["accept-encoding"] == "identity"
        assert dict(request.url.params) == {"ref": "main"}
        return standard_response(request, text=text.encode())
    body = make_adapter(respond).read(candidate())
    assert body.status == "succeeded" and body.requests == len(seen) == 2
    assert body.bytes_read > len(text.encode()) and body.reason == ""
    assert body.url == "https://github.com/author/course/blob/main/chapters/lesson.md"
    assert body.resource_id == "resource_" + content_hash({"url": body.url})
    assert body.version == "git-blob:" + "a" * 40
    chunk, = body.chunks
    assert set(chunk) == {"chunk_id", "resource_id", "version", "content_hash", "location", "text"}
    assert chunk["text"] == text and chunk["location"] == "chapters/lesson.md#L1-L2"
    assert chunk["content_hash"] == hashlib.sha256(text.encode()).hexdigest()
    assert chunk["resource_id"] == body.resource_id and chunk["version"] == body.version
    assert chunk["chunk_id"] == "chunk_" + content_hash({k: v for k, v in chunk.items() if k not in {"text", "chunk_id"}})
    assert "中文 evidence" not in repr(body)
    repeated = make_adapter(respond).read(candidate())
    assert repeated.chunks == body.chunks
    body.close()
    repeated.close()
    assert body.chunks == repeated.chunks == []


@pytest.mark.parametrize("source", ["web", "manual", "unknown"])
def test_unsupported_source_never_dispatches(source):
    body = make_adapter(lambda _: pytest.fail("Unsupported source dispatched")).read(candidate(source=source))
    assert body.status == "unread" and body.reason == "unsupported_body_source"
    assert body.requests == 0 and body.bytes_read == 0 and body.chunks == []


@pytest.mark.parametrize("changes", [
    {"url": "http://github.com/author/course"}, {"url": "https://user@github.com/author/course"},
    {"url": "https://github.com:444/author/course"}, {"url": "https://github.com/other/course"},
    {"url": "https://github.com/author/course?token=secret"}, {"url": "https://github.com/author/course#x"},
    {"ref": ""}, {"ref": "../bad"}, {"ref": "main\nsecret"}, {"ref": "main.lock"},
])
def test_invalid_identity_or_ref_never_dispatches(changes):
    body = make_adapter(lambda _: pytest.fail("Invalid identity dispatched")).read(candidate(**changes))
    assert body.status == "failed" and body.requests == 0 and not body.chunks
    assert "secret" not in body.reason


@pytest.mark.parametrize("paths", [("a.md", "b.md"), ("../a.md",), ("a%2fb.md",), ("/a.md",), ("a.py",), "a.md"])
def test_invalid_or_unbounded_selection_fails_before_dispatch(paths):
    body = make_adapter(lambda _: pytest.fail("Invalid selection dispatched")).read(candidate(), paths=paths)
    assert body.status == "failed" and body.requests == 0 and body.chunks == []


def test_requested_path_requires_real_readme_allowlist():
    calls = []
    def respond(request):
        calls.append(request.url.path)
        return standard_response(request)
    body = make_adapter(respond).read(candidate(), paths=("hidden.md",))
    assert body.status == "failed" and body.requests == 1 and len(calls) == 1 and body.chunks == []


def test_readme_is_index_only_and_unsupported_links_do_not_become_body():
    readme = b"# Outcome-looking body\nEvidence\n[External](https://evil.example/a.md)\n[Notebook](a.ipynb)\n[Code](main.py)"
    body = make_adapter(lambda req: standard_response(req, readme=readme)).read(candidate())
    assert body.status == "unread" and body.requests == 1 and body.chunks == []


def test_default_uses_first_supported_index_path_without_keyword_inference():
    seen = []
    def respond(request):
        seen.append(request.url.path)
        if request.url.path.endswith("/readme"):
            return reply(file_payload("README.md", b"[Notebook](a.ipynb)\n[First](first.txt)\n[Outcome](second.md)"))
        assert request.url.path.endswith("/contents/first.txt")
        return reply(file_payload("first.txt", b"First text"))
    body = make_adapter(respond).read(candidate())
    assert body.status == "succeeded" and len(seen) == 2 and body.chunks[0]["text"] == "First text"
    body.close()


@pytest.mark.parametrize("mime", [None, "text/html", "application/octet-stream", "application/evil+json"])
@pytest.mark.parametrize("on_chapter", [False, True])
def test_json_mime_required_on_each_success_response_before_body_consumption(mime, on_chapter):
    consumed = []
    class ForbiddenBody(httpx.SyncByteStream):
        def __iter__(self):
            consumed.append(True)
            yield b"untrusted raw body secret"
    def respond(request):
        if on_chapter and request.url.path.endswith("/readme"):
            return standard_response(request)
        return httpx.Response(200, headers={} if mime is None else {"Content-Type": mime}, stream=ForbiddenBody())
    body = make_adapter(respond).read(candidate())
    assert body.status == "failed" and body.requests == (2 if on_chapter else 1)
    assert consumed == [] and not body.chunks and "secret" not in repr(body)


@pytest.mark.parametrize("mime", ["application/json; charset=utf-8", "application/vnd.github+json", "Application/JSON"])
def test_supported_json_media_types(mime):
    def respond(request):
        response = standard_response(request)
        response.headers["Content-Type"] = mime
        return response
    body = make_adapter(respond).read(candidate())
    assert body.status == "succeeded"
    body.close()


@pytest.mark.parametrize("status", [301, 302, 307, 308, 401, 403, 404, 429, 500])
def test_http_failure_known_fixed_reason_without_redirect_or_retry(status):
    calls = []
    body = make_adapter(lambda request: calls.append(request) or reply(b"credential body secret", status=status,
        headers={"Location": "https://127.0.0.1/secret"})).read(candidate())
    assert body.status == "failed" and body.requests == len(calls) == 1
    assert body.chunks == [] and "secret" not in repr(body)


@pytest.mark.parametrize("kind", ["timeout", "connect", "lost_read"])
@pytest.mark.parametrize("on_chapter", [False, True])
def test_transport_unknown_no_retry_no_partial_body(kind, on_chapter):
    seen = []
    def respond(request):
        seen.append(request)
        if on_chapter and request.url.path.endswith("/readme"):
            return standard_response(request)
        exc = {"timeout": httpx.ReadTimeout, "connect": httpx.ConnectError, "lost_read": httpx.ReadError}[kind]
        raise exc("credential upstream body secret", request=request)
    body = make_adapter(respond).read(candidate())
    assert body.status == "unknown" and body.requests == len(seen) == (2 if on_chapter else 1)
    assert body.chunks == [] and "secret" not in repr(body)


@pytest.mark.parametrize("raw", [b"not JSON", b"[]", b"null"])
def test_invalid_json_known_failure(raw):
    body = make_adapter(lambda _: reply(raw)).read(candidate())
    assert body.status == "failed" and body.requests == 1 and not body.chunks


@pytest.mark.parametrize("changes", [
    {"type": "symlink"}, {"encoding": "none"}, {"content": "%%secret"}, {"path": "wrong.md"},
    {"sha": "not-a-sha-secret"}, {"sha": None}, {"size": True}, {"size": 9999},
])
def test_invalid_chapter_payload_is_known_failure_and_never_leaks_body(changes):
    def respond(request):
        if request.url.path.endswith("/readme"):
            return standard_response(request)
        return reply(file_payload("chapters/lesson.md", b"body secret", **changes))
    body = make_adapter(respond).read(candidate())
    assert body.status == "failed" and body.requests == 2 and body.chunks == []
    assert "secret" not in repr(body)


@pytest.mark.parametrize("raw", [b"\xffsecret", b"nul\x00secret", b"x" * 16385, b""], ids=["invalid-utf8", "nul", "oversized", "empty"])
def test_invalid_utf8_nul_empty_or_oversized_text_known_failure(raw):
    body = make_adapter(lambda req: standard_response(req, text=raw)).read(candidate())
    assert body.status == ("unread" if len(raw) > 16384 else "failed") and body.requests == 2 and body.chunks == []
    assert "secret" not in repr(body)


def test_aggregate_wire_budget_includes_readme_and_chapter():
    readme = file_payload("README.md", b"[Lesson](chapters/lesson.md)")
    chapter = file_payload("chapters/lesson.md", b"actual body")
    budget = len(json.dumps(readme).encode()) + 5
    calls = []
    def respond(request):
        calls.append(request)
        return reply(readme if request.url.path.endswith("/readme") else chapter)
    body = make_adapter(respond).read(candidate(), max_bytes=budget)
    assert body.status == "failed" and body.requests == len(calls) == 2 and body.chunks == []


@pytest.mark.parametrize("headers", [{"Content-Encoding": "gzip"}, {"Content-Length": "99999999999999999999999999"}])
def test_declared_size_and_compression_rejected_before_body(headers):
    consumed = []
    class Body(httpx.SyncByteStream):
        def __iter__(self):
            consumed.append(True)
            yield b"secret"
    body = make_adapter(lambda _: httpx.Response(200, headers={"Content-Type": "application/json", **headers}, stream=Body())).read(candidate())
    assert body.status == "failed" and body.requests == 1 and body.chunks == [] and consumed == []


def test_total_deadline_not_reset_between_readme_and_chapter(monkeypatch):
    import app.infrastructure.resources.teaching_body as module
    clock = [0.0]
    monkeypatch.setattr(module, "time", SimpleNamespace(monotonic=lambda: clock[0]))
    calls = []
    def respond(request):
        calls.append(request)
        clock[0] = 2.0
        return standard_response(request)
    body = make_adapter(respond).read(candidate(), timeout_seconds=1)
    assert body.status == "unknown" and body.requests == len(calls) == 1 and body.chunks == []


@pytest.mark.parametrize("kwargs", [{"max_bytes": 0}, {"max_bytes": 65537}, {"max_bytes": True}, {"timeout_seconds": 0}, {"timeout_seconds": 15.1}, {"timeout_seconds": float("nan")}])
def test_invalid_limits_zero_dispatch(kwargs):
    body = make_adapter(lambda _: pytest.fail("Invalid limit dispatched")).read(candidate(), **kwargs)
    assert body.status == "failed" and body.requests == 0 and body.chunks == []


def test_client_preserves_existing_fixed_endpoint_security_settings(monkeypatch):
    settings = []
    original = httpx.Client
    def client(**kwargs):
        settings.append(kwargs)
        return original(**kwargs)
    monkeypatch.setattr(httpx, "Client", client)
    body = make_adapter(standard_response).read(candidate())
    assert body.status == "succeeded"
    assert settings[0]["verify"] is True and settings[0]["trust_env"] is False
    assert settings[0]["follow_redirects"] is False
    body.close()


def test_stream_size_early_stop_closes_response_without_consuming_remainder():
    consumed, closed = [], []
    class Oversized(httpx.SyncByteStream):
        def __iter__(self):
            for index in range(4):
                consumed.append(index)
                yield b"x" * 512
        def close(self):
            closed.append(True)
    body = make_adapter(lambda _: httpx.Response(200, headers={"Content-Type": "application/json"}, stream=Oversized())).read(candidate(), max_bytes=1024)
    assert body.status == "failed" and body.requests == 1 and body.chunks == []
    assert consumed == [0, 1, 2] and closed == [True] and body.bytes_read == 1536


def test_partial_stream_transport_error_stays_unknown_and_clears_response():
    closed = []
    class Broken(httpx.SyncByteStream):
        def __iter__(self):
            yield b'{"private":"body secret'
            raise httpx.ReadError("body secret")
        def close(self):
            closed.append(True)
    body = make_adapter(lambda _: httpx.Response(200, headers={"Content-Type": "application/json"}, stream=Broken())).read(candidate())
    assert body.status == "unknown" and body.requests == 1 and body.bytes_read > 0
    assert body.chunks == [] and closed == [True] and "secret" not in repr(body)


@pytest.mark.parametrize("answers", [
    [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.1", 443))],
    [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("140.82.112.5", 443)),
     (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))],
    [(socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("::ffff:8.8.8.8", 443, 0, 0))],
])
def test_inherited_pinned_transport_private_or_mixed_dns_proven_not_dispatched(answers):
    from app.infrastructure.resources.github_transport import PinnedPublicTransport
    from app.infrastructure.resources.teaching_body import GitHubTeachingBody
    body = GitHubTeachingBody(transport=PinnedPublicTransport(resolver=lambda *_: answers)).read(candidate())
    assert body.status == "failed" and body.reason == "body_destination_rejected"
    assert body.requests == 0 and body.bytes_read == 0 and body.chunks == []


def test_inherited_deadline_stream_requires_actual_github_tls_hostname():
    import httpcore
    from app.infrastructure.resources.github_transport import DeadlineStream
    fake_stream = SimpleNamespace(start_tls=lambda *_args, **_kwargs: pytest.fail("Wrong TLS hostname dispatched"))
    with pytest.raises(httpcore.ConnectError):
        DeadlineStream(fake_stream, None).start_tls(None, server_hostname="evil.example")


def test_exact_text_limit_and_explicit_index_path_succeed():
    text = b"x" * 16384
    body = make_adapter(lambda req: standard_response(req, text=text)).read(candidate(), paths=("chapters/lesson.md",))
    assert body.status == "succeeded" and body.requests == 2 and body.chunks[0]["text"].encode() == text
    body.close()


def test_requested_missing_path_fails_even_when_readme_has_no_supported_chapters():
    body = make_adapter(lambda req: standard_response(req, readme=b"# Index only")).read(candidate(), paths=("hidden.md",))
    assert body.status == "failed" and body.requests == 1 and body.chunks == []
