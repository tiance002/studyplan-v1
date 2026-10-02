"""Offline GitHub protocol fixtures exercise bounded reads and truthful evidence."""
import base64
import importlib
import json
from dataclasses import asdict

import httpx
import pytest
from app.domain.resources.models import UnavailableResult

from tests.unit.test_tavily_resource_index import query, streaming_json


def adapter(respond):
    module = importlib.import_module("app.infrastructure.resources.github")
    return module.GitHubResourceIndex(transport=httpx.MockTransport(respond))


def repositories(items):
    return {"items": [{"name": name, "owner": {"login": "author"}, "full_name": f"author/{name}",
        "html_url": f"https://github.com/author/{name}", "default_branch": "main",
        "description": description, "stargazers_count": 20, "updated_at": "2026-01-01T00:00:00Z",
        "license": {"spdx_id": "MIT"}} for name, description in items]}


def contents(path, text):
    return {"type": "file", "path": path, "sha": "a" * 40,
        "encoding": "base64", "size": len(text.encode()),
        "content": base64.b64encode(text.encode()).decode()}


def test_github_single_search_preserves_rank_and_does_not_infer_teaching_from_name():
    seen = []
    def respond(request):
        seen.append(request)
        return streaming_json(repositories([("learn-agent", "RAG installer"), ("rag-course", "RAG exercises")]))
    found = adapter(respond).find(query())
    assert len(found) == 2 and len(seen) == 1
    assert seen[0].url.host == "api.github.com" and seen[0].url.path == "/search/repositories"
    assert dict(seen[0].url.params) == {"q": "RAG 中文教程", "per_page": "5"}
    evidence = asdict(found[0])["discovery"]
    assert evidence["provider_rank"] == 1 and evidence["provider_score"] is None
    assert evidence["signals"]["teaching_structure"] is None
    assert evidence["recommended_role"] == "candidate"
    assert evidence["repo"]["license"] == "MIT"


def test_default_inspection_reads_only_readme_and_one_local_matching_chapter():
    module = importlib.import_module("app.ports.resource_index")
    seen = []
    readme = "# RAG course\n## Prerequisites\nPython\n## Chapters\n[Setup](chapters/setup.md)\n[RAG exercises](chapters/rag.md)\n[Remote](https://evil.example/a.md)\n[Notebook](notebook.ipynb)"
    def respond(request):
        seen.append(request.url.path)
        if request.url.path == "/search/repositories":
            return streaming_json(repositories([("course", "RAG course")]))
        if request.url.path.endswith("/readme"):
            return streaming_json(contents("README.md", readme))
        if request.url.path.endswith("/contents/chapters/rag.md"):
            return streaming_json(contents("chapters/rag.md", "# RAG\n## Exercise\nBuild a retriever"))
        raise AssertionError("unexpected external or metadata request")
    index = adapter(respond)
    candidate = json.loads(json.dumps(asdict(index.find(query())[0]), default=str))
    result = index.inspect(module.ResourceInspectionQuery(scope=query().scope, candidate=candidate,
        query="RAG", preference=query().preference))
    assert result.status == "succeeded"
    evidence = result.candidate["discovery"]
    assert seen == ["/search/repositories", "/repos/author/course/readme", "/repos/author/course/contents/chapters/rag.md"]
    assert evidence["inspection_status"] == "chapter_or_index_checked"
    assert [file["path"] for file in evidence["files"]] == ["README.md", "chapters/rag.md"]
    assert [(c["path"], c["status"]) for c in evidence["chapters"]] == [
        ("chapters/setup.md", "listed"), ("chapters/rag.md", "read"), ("notebook.ipynb", "unsupported")]
    assert evidence["signals"]["teaching_structure"] is True
    assert result.candidate["verification_status"] == "unverified"
    assert all(file["blob_sha"] and file["content_hash"] and file["fetched_at"] for file in evidence["files"])
    assert "Build a retriever" not in json.dumps(evidence)


@pytest.mark.parametrize("status", [302, 401, 403, 429, 500])
def test_search_errors_sanitized_without_retry(status):
    calls = []
    index = adapter(lambda request: calls.append(request) or httpx.Response(status,
        content=b"private-token upstream-private", headers={"Location": "https://evil.example"}))
    result = index.find(query())
    assert isinstance(result, UnavailableResult) and len(calls) == 1
    assert "private" not in result.reason


def test_malformed_readme_link_is_skipped_and_installation_is_reference_only():
    module = importlib.import_module("app.ports.resource_index")
    def respond(request):
        if request.url.path == "/search/repositories":
            return streaming_json(repositories([("learn-agent", "Agent install")]))
        if request.url.path.endswith("/readme"):
            return streaming_json(contents("README.md", "# Agent setup\n[Bad](https://[)\n[Agent install](docs/agent-install.md)"))
        return streaming_json(contents("docs/agent-install.md", "# Agent install\npip install agent\nSet API_KEY"))
    index = adapter(respond)
    candidate = json.loads(json.dumps(asdict(index.find(query())[0]), default=str))
    result = index.inspect(module.ResourceInspectionQuery(scope=query().scope, candidate=candidate,
        query="Agent", preference=query().preference))
    assert result.status == "succeeded"
    assert result.candidate["discovery"]["recommended_role"] == "reference"
    assert result.candidate["discovery"]["signals"]["teaching_structure"] is False


@pytest.mark.parametrize("failure", ["timeout", "gzip", "oversized", "bad-json"])
def test_inspection_unknown_keeps_dispatch_receipt_without_retry(failure):
    module = importlib.import_module("app.ports.resource_index")
    calls = []
    def respond(request):
        calls.append(request.url.path)
        if request.url.path == "/search/repositories":
            return streaming_json(repositories([("course", "RAG")]))
        if failure == "timeout":
            raise httpx.ReadTimeout("private upstream content", request=request)
        if failure == "gzip":
            return httpx.Response(200, headers={"Content-Encoding": "gzip"}, stream=httpx.ByteStream(b"bad gzip"))
        return httpx.Response(200, stream=httpx.ByteStream(b"x" * (256 * 1024 + 1) if failure == "oversized" else b"not json"))
    index = adapter(respond)
    candidate = json.loads(json.dumps(asdict(index.find(query())[0]), default=str))
    candidate["discovery"]["inspection_status"] = "chapter_or_index_checked"
    candidate["discovery"]["signals"]["teaching_structure"] = True
    candidate["discovery"]["recommended_role"] = "mainline_candidate"
    result = index.inspect(module.ResourceInspectionQuery(scope=query().scope, candidate=candidate,
        query="RAG", preference=query().preference))
    assert result.status == "reconciliation_required" and len(result.receipts) == 1
    assert result.receipts[0]["status"] == "reconciliation_required"
    assert calls == ["/search/repositories", "/repos/author/course/readme"]
    assert "private" not in json.dumps(asdict(result))
    assert result.candidate["discovery"]["inspection_status"] == "metadata_only"
    assert result.candidate["discovery"]["signals"]["teaching_structure"] is None
    assert result.candidate["discovery"]["recommended_role"] == "candidate"


def test_requested_reading_orders_two_indexed_paths_and_rejects_arbitrary_path():
    module = importlib.import_module("app.ports.resource_index")
    calls = []
    def respond(request):
        calls.append(request.url.path)
        if request.url.path == "/search/repositories":
            return streaming_json(repositories([("course", "RAG")]))
        if request.url.path.endswith("/readme"):
            return streaming_json(contents("README.md", "# Lessons\n[First](first.md)\n[Second](second.md)"))
        return streaming_json(contents(request.url.path.rsplit("/", 1)[1], "# Lesson\nLearning objectives\nRAG"))
    index = adapter(respond)
    candidate = json.loads(json.dumps(asdict(index.find(query())[0]), default=str))
    inspected = index.inspect(module.ResourceInspectionQuery(scope=query().scope, candidate=candidate,
        query="RAG", preference=query().preference, paths=("second.md", "first.md")))
    assert inspected.status == "succeeded"
    assert [file["path"] for file in inspected.candidate["discovery"]["files"]] == ["README.md", "first.md", "second.md"]
    assert len(inspected.receipts) == 3
    unknown_path = index.inspect(module.ResourceInspectionQuery(scope=query().scope, candidate=candidate,
        query="RAG", preference=query().preference, paths=("hidden.md",)))
    assert unknown_path.status == "failed" and len(unknown_path.receipts) == 1
    assert not any(path.endswith("hidden.md") for path in calls)
