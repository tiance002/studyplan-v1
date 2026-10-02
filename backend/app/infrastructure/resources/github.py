"""Anonymous, bounded GitHub repository discovery and separate text inspection.

Only the fixed REST API is read. Markdown links are data, never instructions;
local text paths from the inspected README form the chapter allowlist.
"""
import base64
import binascii
import hashlib
import html
import json
import posixpath
import re
import time
from copy import deepcopy
from datetime import datetime, timezone
from urllib.parse import quote, unquote, urlsplit

import httpx
from app.application.resource_discovery_contract import (
    ChapterEvidence,
    ContentEvidence,
    DiscoveryEvidence,
    DiscoverySignals,
    GitHubRepository,
)
from app.core.errors import ForbiddenError, ValidationAppError
from app.core.ids import new_id
from app.domain.enums import MediaType, ResourceProvenance, ResourceVerificationStatus
from app.domain.resources.models import ResourceRecord, UnavailableResult
from app.domain.workspace.models import AuthContext
from app.infrastructure.resources.github_transport import (
    GitHubNotDispatchedError,
    PinnedPublicTransport,
    validate_content_path,
    validate_github_url,
)
from app.ports.resource_index import ResourceInspectionResult
from pydantic import ValidationError

UNKNOWN_SEARCH_REASON = "搜索响应未知，请核对后再显式发起新搜索"
UNKNOWN_INSPECTION_REASON = "教程检查响应未知，请核对回执；不会自动重新读取"
_MAX_BODY = 256 * 1024
_TEXT_EXTENSIONS = {".md", ".markdown", ".txt", ".rst"}
_COMPONENT = re.compile(r"[A-Za-z0-9_.-]{1,100}\Z")


def _clean(value, limit):
    if not isinstance(value, str):
        return ""
    return html.unescape(re.sub(r"<[^>]*>", "", value)).encode("utf-8", errors="replace").decode().strip()[:limit]


def topic_terms(words):
    """Conservative lexical overlap; no fabricated semantic/provider score."""
    ignored = {"tutorial", "course", "learn", "guide", "教程", "中文", "学习", "english", "chinese"}
    return set(word.lower() for word in re.findall(r"[A-Za-z][A-Za-z0-9_+-]*|[\u4e00-\u9fff]{2,}", words)
               if word.lower() not in ignored)


def topic_overlap(words, text):
    lowered = text.lower()
    return sum(term in lowered for term in topic_terms(words))


class GitHubFailure(Exception):
    def __init__(self, reason, *, unknown=False):
        self.reason, self.unknown = reason, unknown


class GitHubResourceIndex:
    def __init__(self, *, transport=None, timeout_seconds=15):
        if not 0 < timeout_seconds <= 15:
            raise ValidationAppError("GitHub检查超时需在0–15秒之间")
        self._transport = transport
        self._timeout = timeout_seconds

    @staticmethod
    def _scope(scope, project_id):
        if not isinstance(scope, AuthContext):
            raise ForbiddenError("GitHub读取需要服务端授权范围")
        scope.require_project(project_id)

    def _client(self):
        return httpx.Client(transport=self._transport or PinnedPublicTransport(),
            timeout=self._timeout, trust_env=False, follow_redirects=False, verify=True)

    def _json(self, client, path, *, params, deadline, kind, receipts, budget):
        url = httpx.URL("https://api.github.com" + path, params=params)
        validate_github_url(str(url))
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise GitHubFailure(UNKNOWN_INSPECTION_REASON, unknown=True)
        receipt = {"kind": kind, "path": path, "status": "dispatched", "bytes": 0,
                   "dispatched_at": datetime.now(timezone.utc).isoformat()}
        receipts.append(receipt)
        try:
            with client.stream("GET", url, timeout=remaining,
                    extensions={"n1_deadline": deadline, "n1_kind": kind},
                    headers={"Accept": "application/vnd.github+json", "Accept-Encoding": "identity",
                             "X-GitHub-Api-Version": "2026-03-10", "User-Agent": "StudyPlan-resource-discovery"}) as response:
                receipt["http_status"] = response.status_code
                if response.status_code != 200:
                    receipt["status"] = "failed"
                    reason = ("github_redirect_rejected" if 300 <= response.status_code < 400
                              else "github_rate_limited" if response.status_code == 429
                              else "github_forbidden" if response.status_code in {401, 403}
                              else "github_not_found" if response.status_code == 404 else "github_http_error")
                    raise GitHubFailure(reason)
                if response.headers.get("Content-Encoding", "identity").lower() != "identity":
                    raise GitHubFailure(UNKNOWN_INSPECTION_REASON, unknown=True)
                length = response.headers.get("Content-Length", "")
                if length.isdecimal() and (len(length) > 20 or int(length) > budget[0]):
                    raise GitHubFailure(UNKNOWN_INSPECTION_REASON, unknown=True)
                body = bytearray()
                for chunk in response.iter_raw():
                    if time.monotonic() >= deadline or len(chunk) > budget[0]:
                        raise GitHubFailure(UNKNOWN_INSPECTION_REASON, unknown=True)
                    budget[0] -= len(chunk)
                    receipt["bytes"] += len(chunk)
                    body.extend(chunk)
            if time.monotonic() >= deadline:
                raise GitHubFailure(UNKNOWN_INSPECTION_REASON, unknown=True)
            data = json.loads(body)
            if not isinstance(data, dict):
                raise GitHubFailure(UNKNOWN_INSPECTION_REASON, unknown=True)
            receipt["status"] = "succeeded"
            return data
        except GitHubNotDispatchedError:
            receipt["status"] = "not_dispatched"
            raise GitHubFailure("github_destination_rejected") from None
        except GitHubFailure as exc:
            if exc.unknown:
                receipt["status"] = "reconciliation_required"
            raise
        except (httpx.HTTPError, ValueError, UnicodeError, RecursionError, OSError):
            receipt["status"] = "reconciliation_required"
            raise GitHubFailure(UNKNOWN_INSPECTION_REASON, unknown=True) from None

    def find(self, query):
        project_id = query.extra.get("project_id")
        if not isinstance(project_id, str):
            raise ValidationAppError("GitHub检索缺少学习空间范围")
        self._scope(query.scope, project_id)
        words = query.extra.get("query")
        if not isinstance(words, str) or not 1 <= len(words.strip()) <= 500:
            raise ValidationAppError("检索词需为1–500字符")
        try:
            words.encode("utf-8")
        except UnicodeError as exc:
            raise ValidationAppError("检索词含非法字符") from exc
        if not isinstance(query.limit, int) or isinstance(query.limit, bool) or query.limit < 1:
            raise ValidationAppError("检索数量需为正整数")
        limit = min(5, query.limit)
        try:
            with self._client() as client:
                data = self._json(client, "/search/repositories", params={"q": words.strip(), "per_page": limit},
                    deadline=time.monotonic() + self._timeout, kind="search", receipts=[], budget=[_MAX_BODY])
        except GitHubFailure as exc:
            return UnavailableResult(UNKNOWN_SEARCH_REASON if exc.unknown else exc.reason)
        items = data.get("items")
        if not isinstance(items, list):
            return UnavailableResult(UNKNOWN_SEARCH_REASON)
        candidates, seen = [], set()
        for rank, item in enumerate(items[:5], 1):
            if not isinstance(item, dict):
                continue
            owner = item.get("owner", {}).get("login") if isinstance(item.get("owner"), dict) else None
            name = item.get("name")
            if not all(isinstance(part, str) and _COMPONENT.fullmatch(part) and part not in {".", ".."}
                       for part in (owner, name)):
                continue
            url = f"https://github.com/{owner}/{name}"
            if url in seen:
                continue
            try:
                license_info = item.get("license")
                repository = GitHubRepository(owner=owner, name=name,
                    default_branch=item.get("default_branch") or "",
                    license=license_info.get("spdx_id") if isinstance(license_info, dict) else None,
                    updated_at=item.get("updated_at"), stars=item.get("stargazers_count"))
                snippet = _clean(item.get("description"), 2000)
                evidence = DiscoveryEvidence(source="github", provider_rank=rank, snippet=snippet, repo=repository,
                    signals={"topic_overlap": topic_overlap(words, name + " " + snippet)},
                    reasons=["保留GitHub仓库搜索顺序；仅根据名称与描述记录主题词重合"],
                    limitations=["尚未读取README、章节、先修要求或核验教学质量；Star仅为元数据"])
            except (ValidationError, UnicodeError, TypeError):
                continue
            seen.add(url)
            candidates.append(ResourceRecord(resource_id=new_id("res"), project_id=project_id, url=url,
                title=f"{owner}/{name}", media_type=MediaType.REPO, language="und",
                provenance=ResourceProvenance.SEARCH_CANDIDATE,
                verification_status=ResourceVerificationStatus.UNVERIFIED,
                discovery=evidence.model_dump(mode="json"), source_note="GitHub搜索候选；尚未检查教程"))
            if len(candidates) >= limit:
                break
        return candidates or UnavailableResult("github_no_results")

    @staticmethod
    def _chapters(text, readme_path):
        chapters, seen = [], set()
        for title, href in re.findall(r"\[([^\]\n]+)\]\(([^\s)]+)(?:\s+[^)]*)?\)", text):
            try:
                parsed = urlsplit(href)
                if parsed.scheme or parsed.netloc or not parsed.path or href.startswith(('/', '\\', '#')):
                    continue
                local = unquote(parsed.path, errors="strict")
                path = posixpath.normpath(posixpath.join(posixpath.dirname(readme_path), local))
                validate_content_path(path)
            except (ValueError, UnicodeError):
                continue
            suffix = posixpath.splitext(path)[1].lower()
            if path in seen or path == readme_path or suffix not in _TEXT_EXTENSIONS | {".ipynb"}:
                continue
            seen.add(path)
            chapters.append(ChapterEvidence(path=path, title=_clean(title, 300), order=len(chapters),
                status="unsupported" if suffix == ".ipynb" else "listed"))
            if len(chapters) >= 100:
                break
        return chapters

    def inspect(self, query):
        candidate = deepcopy(query.candidate)
        self._scope(query.scope, candidate.get("project_id"))
        evidence = DiscoveryEvidence.model_validate(candidate.get("discovery", {}))
        repo = evidence.repo
        if evidence.source != "github" or repo is None:
            raise ValidationAppError("只能检查GitHub搜索候选")
        if not all(_COMPONENT.fullmatch(part) and part not in {".", ".."} for part in (repo.owner, repo.name)):
            raise ValidationAppError("仓库标识无效")
        if len(query.paths) > 2 or len(set(query.paths)) != len(query.paths):
            raise ValidationAppError("最多检查两个不重复的目录内文本章节")
        for path in query.paths:
            try:
                validate_content_path(path)
            except (ValueError, UnicodeError) as exc:
                raise ValidationAppError("检查路径无效") from exc
        evidence.files, evidence.chapters = [], []
        evidence.inspection_status = "metadata_only"
        evidence.signals = DiscoverySignals(topic_overlap=topic_overlap(query.query, candidate.get("title", "") + " " + evidence.snippet))
        evidence.recommended_role = "candidate"
        evidence.selection_mapping = None
        evidence.reasons = ["本次检查尚未取得文本证据"]
        evidence.limitations = ["仅保留当前检查实际读取的文件；失败或未知结果不继承上一轮核验标记"]
        receipts, budget = [], [_MAX_BODY]
        prefix = f"/repos/{repo.owner}/{repo.name}"
        ref = {"ref": repo.default_branch} if repo.default_branch else {}
        deadline = time.monotonic() + self._timeout
        texts = []

        def content(client, path, expected_path=None):
            data = self._json(client, path, params=ref, deadline=deadline, kind="content", receipts=receipts, budget=budget)
            local_path = data.get("path")
            try:
                validate_content_path(local_path)
            except (ValueError, UnicodeError):
                raise GitHubFailure("github_unsupported_file") from None
            if (data.get("type") != "file" or data.get("encoding") != "base64"
                    or posixpath.splitext(local_path)[1].lower() not in _TEXT_EXTENSIONS
                    or (expected_path and expected_path != local_path)):
                raise GitHubFailure("github_unsupported_file")
            encoded = data.get("content")
            if not isinstance(encoded, str):
                raise GitHubFailure("github_unsupported_file")
            try:
                raw = base64.b64decode(re.sub(r"\s", "", encoded), validate=True)
                text = raw.decode("utf-8")
            except (ValueError, UnicodeError, binascii.Error):
                raise GitHubFailure("github_unsupported_file") from None
            if sum(len(t.encode("utf-8")) for t in texts) + len(raw) > _MAX_BODY or "\x00" in text:
                raise GitHubFailure("github_unsupported_file")
            texts.append(text)
            evidence.files.append(ContentEvidence(path=local_path,
                url=f"https://github.com/{repo.owner}/{repo.name}/blob/{quote(repo.default_branch or 'HEAD', safe='')}/{quote(local_path, safe='/')}",
                blob_sha=data.get("sha"), content_hash=hashlib.sha256(raw).hexdigest(),
                fetched_at=datetime.now(timezone.utc).isoformat(), line_end=max(1, len(text.splitlines()))))
            return local_path, text

        try:
            with self._client() as client:
                readme_path, readme = content(client, prefix + "/readme")
                evidence.inspection_status = "readme_read"
                evidence.chapters = self._chapters(readme, readme_path)
                available = {chapter.path: chapter for chapter in evidence.chapters if chapter.status != "unsupported"}
                if query.paths:
                    if any(path not in available for path in query.paths):
                        raise GitHubFailure("github_path_not_in_inspected_index")
                    selected = sorted(query.paths, key=lambda path: available[path].order)
                else:
                    ranked = sorted(available.values(), key=lambda chapter: (
                        -topic_overlap(query.query, chapter.title + " " + chapter.path), chapter.order))
                    selected = [ranked[0].path] if ranked and topic_overlap(query.query, ranked[0].title + " " + ranked[0].path) else []
                for path in selected:
                    content(client, prefix + "/contents/" + quote(path, safe="/"), expected_path=path)
                    available[path].status = "read"
                if evidence.chapters or selected:
                    evidence.inspection_status = "chapter_or_index_checked"
            combined = "\n".join(texts)
            evidence.signals.topic_overlap = topic_overlap(query.query, combined)
            evidence.signals.prerequisites = bool(re.search(r"(?i)prerequisit|先修|前置知识|基础要求", combined))
            evidence.signals.exercises = bool(re.search(r"(?i)\bexercise\b|\bexercises\b|练习|实践任务|作业", combined))
            objectives = bool(re.search(r"(?i)learning objectives|you will learn|学习目标|本章目标", combined))
            evidence.signals.teaching_structure = (len(evidence.chapters) >= 2
                and (evidence.signals.exercises or objectives))
            evidence.recommended_role = ("mainline_candidate" if evidence.signals.topic_overlap and
                evidence.signals.teaching_structure and selected else "reference" if evidence.signals.topic_overlap else "unsuitable")
            evidence.reasons = ["主题词重合依据实际读取文本", "章节顺序来自README本地链接索引"]
            evidence.limitations = ["仅有限读取，未逐章审阅或执行代码；阅读不能证明知识掌握或课程受控审核",
                "语言、难度和技术版本尚未核验；未读取章节仅保留目录记录；Notebook仅提供链接"]
            candidate["discovery"] = evidence.model_dump(mode="json")
            return ResourceInspectionResult("succeeded", candidate, receipts)
        except GitHubFailure as exc:
            candidate["discovery"] = evidence.model_dump(mode="json")
            return ResourceInspectionResult("reconciliation_required" if exc.unknown else "failed", candidate, receipts,
                UNKNOWN_INSPECTION_REASON if exc.unknown else exc.reason)
        except (ValidationError, ValueError, UnicodeError, TypeError, httpx.HTTPError, OSError):
            candidate["discovery"] = evidence.model_dump(mode="json")
            return ResourceInspectionResult("reconciliation_required", candidate, receipts, UNKNOWN_INSPECTION_REASON)
