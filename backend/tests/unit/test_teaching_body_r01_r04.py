"""R01/R04 real GitHub adapter regressions with no external calls."""
import socket

import httpx
import pytest
from app.domain.enums import ResourceVerificationStatus

from tests.unit.test_teaching_body import candidate, file_payload, make_adapter, reply


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("Real DNS/socket forbidden in chapter regression tests")
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)


@pytest.mark.parametrize("outcome,title,path", [
    ("定义模型结构化输出合同", "结构化输出", "04-结构化输出.md"),
    ("按工具输入合同校验调用参数", "工具调用", "05-工具调用.md"),
    ("定义模型结构化输出合同", "Structured Output", "structured-output.md"),
])
def test_short_chinese_and_english_headings_select_only_allowlisted_chapter(outcome, title, path):
    source = candidate()
    calls = []
    def respond(request):
        calls.append(request.url.path)
        if request.url.path.endswith("/readme"):
            readme = f"[{title}](CONTRIBUTING.md)\n[Python](python.md)\n[{title}]({path})\n[{title}](https://evil.example/hidden.md)"
            return reply(file_payload("README.md", readme.encode()))
        assert request.url.path.endswith("/contents/" + path)
        return reply(file_payload(path, b"# Candidate text, no reviewed coverage"))
    body = make_adapter(respond).read(source, must_teach=(outcome,))
    assert body.status == "succeeded" and body.requests == len(calls) == 2
    assert source.verification_status == ResourceVerificationStatus.UNVERIFIED
    assert body.chunks[0]["location"].startswith(path + "#")
    body.close()


@pytest.mark.parametrize("readme,reason", [
    ("[Python](python.md)", "no_matching_teaching_chapter"),
    ("[工具调用](CONTRIBUTING.md)", "no_supported_teaching_chapter"),
    ("[工具调用](one.md)\n[工具调用](two.md)", "ambiguous_teaching_chapter"),
])
def test_chinese_alias_does_not_promote_unrelated_admin_or_ambiguous_candidates(readme, reason):
    body = make_adapter(lambda _: reply(file_payload("README.md", readme.encode()))).read(
        candidate(), must_teach=("按工具输入合同校验调用参数",))
    assert body.status == "unread" and body.reason == reason and body.requests == 1
    assert not body.chunks


def test_valid_oversized_declaration_is_known_unread_without_consuming_body():
    consumed, closed, responses = [], [], []
    class Body(httpx.SyncByteStream):
        def __iter__(self):
            consumed.append(True)
            yield b"secret"
        def close(self):
            closed.append(True)
    def respond(_):
        response = httpx.Response(200, headers={"Content-Type": "application/json", "Content-Length": "70000"}, stream=Body())
        responses.append(response)
        return response
    body = make_adapter(respond).read(candidate())
    assert body.status == "unread" and body.reason == "body_size_exceeded"
    assert body.requests == 1 and body.bytes_read == 0 and consumed == [] and closed == [True]
    assert responses[0].extensions["studyplan_body_termination"] == "declared_capacity_rejected"


@pytest.mark.parametrize("headers", [
    {"Content-Length": "-1"}, {"Content-Length": "1.2"}, {"Content-Length": "9" * 21},
    {"Content-Length": "70000", "Content-Encoding": "gzip"},
    {"Content-Length": "70000", "Content-Type": "text/html"},
])
def test_invalid_declaration_or_security_headers_never_signal_capacity_unread(headers):
    response = httpx.Response(200, headers={"Content-Type": "application/json", **headers}, stream=httpx.ByteStream(b"secret"))
    body = make_adapter(lambda _: response).read(candidate())
    assert body.status == "failed" and body.requests == 1 and body.bytes_read == 0
    assert response.extensions["studyplan_body_termination"] == "body_validation_rejected"


def test_chapter_exclusion_progresses_only_through_real_toc_siblings():
    calls = []
    def respond(request):
        calls.append(request.url.path)
        if request.url.path.endswith("/readme"):
            return reply(file_payload("README.md", b"[Tool Calling](first.md)\n[Tool Calling](second.md)"))
        assert request.url.path.endswith("/contents/second.md")
        return reply(file_payload("second.md", b"# Tool Calling"))
    body = make_adapter(respond).read(candidate(), must_teach=("按工具输入合同校验调用参数",),
        exclude_paths=("first.md", "absent.md"))
    assert body.status == "succeeded" and body.requests == len(calls) == 2
    assert body.chunks[0]["location"].startswith("second.md#")
    body.close()


@pytest.mark.parametrize("excluded", [("../evil.md",), ("first.py",), ("a.md", "a.md"), "a.md", ("a.md",) * 101])
def test_invalid_chapter_exclusions_fail_before_dispatch(excluded):
    body = make_adapter(lambda _: pytest.fail("Invalid exclusion dispatched")).read(candidate(), exclude_paths=excluded)
    assert body.status == "failed" and body.requests == 0


def test_excluded_explicit_selection_is_rejected_without_fetching_body():
    body = make_adapter(lambda _: reply(file_payload("README.md", b"[Tool Calling](first.md)"))).read(
        candidate(), paths=("first.md",), exclude_paths=("first.md",))
    assert body.status == "failed" and body.requests == 0


def test_all_relevant_chapters_excluded_is_known_unread():
    body = make_adapter(lambda _: reply(file_payload("README.md", b"[Tool Calling](first.md)\n[Python](python.md)"))).read(
        candidate(), must_teach=("按工具输入合同校验调用参数",), exclude_paths=("first.md",))
    assert body.status == "unread" and body.reason == "no_matching_teaching_chapter"
    assert body.requests == 1
