"""GitHub-only bounded temporary teaching text; no arbitrary URL fetching.

The application owns actor/project admission and closes the returned body after
the Reader call. Only an anonymous fixed GitHub endpoint is contacted here.
"""
import base64
import binascii
import hashlib
import json
import posixpath
import re
import time
from urllib.parse import quote, urlsplit

import httpx
from app.core.ids import content_hash
from app.domain.planning.research_reader import TransientBody
from app.domain.resources.models import ResourceRecord
from app.infrastructure.resources.github import (
    _COMPONENT,
    _TEXT_EXTENSIONS,
    GitHubFailure,
    GitHubResourceIndex,
)
from app.infrastructure.resources.github_transport import (
    GitHubNotDispatchedError,
    validate_content_path,
    validate_github_url,
)

_MAX_WIRE = 65536
_MAX_TEXT = 16384
_SHA = re.compile(r"[0-9a-f]{40}\Z")
_JSON_TYPES = {"application/json", "application/vnd.github+json"}
_ADMIN_FILES = {"contributing", "license", "licence", "changelog", "code_of_conduct", "security", "support"}
_SELECTION_STOPWORDS = {"the", "and", "for", "with", "from", "into", "using", "use", "build", "validate",
    "implement", "explain", "learn", "learning", "tutorial", "course", "guide", "docs", "chapter", "lesson"}


def _reject(reason="invalid_body_payload", *, unread=False):
    raise GitHubFailure(reason, unread=unread)


def _valid_ref(ref):
    return (isinstance(ref, str) and 1 <= len(ref) <= 255 and ref != "@"
        and not any(ord(char) <= 32 or ord(char) == 127 or char in "~^:?*[\\" for char in ref)
        and not any(part in ref for part in ("..", "@{", "//"))
        and not ref.startswith("/") and not ref.endswith(("/", "."))
        and all(not part.startswith(".") and not part.endswith(".lock") for part in ref.split("/")))


class GitHubTeachingBody(GitHubResourceIndex):
    supports_outcome_selection = True

    @staticmethod
    def _selection_terms(must_teach):
        """Exact approved labels aid discovery, never establish coverage.

        Chinese public outcome text can name an English technical capability.
        Only the existing policy's exact text binding supplies that alias.
        """
        from app.domain.planning.capability_policy import CAPABILITY_POLICY
        aliases = {outcome.text: definition.title + " " + definition.capability_id
            for definition in CAPABILITY_POLICY.definitions for outcome in definition.learning_outcomes}
        terms = set()
        for text in must_teach:
            words = text + " " + aliases.get(text, "")
            terms.update(word.lower() for word in re.findall(r"[A-Za-z][A-Za-z0-9]*|[\u4e00-\u9fff]{2,}", words)
                if word.lower() not in _SELECTION_STOPWORDS)
        return terms

    @staticmethod
    def _select_chapter(chapters, must_teach):
        if not chapters:
            return None, "no_supported_teaching_chapter"
        if not must_teach:
            return chapters[0].path, ""
        terms = GitHubTeachingBody._selection_terms(must_teach)
        scored = []
        for chapter in chapters:
            label = chapter.title + " " + posixpath.splitext(chapter.path)[0]
            words = {w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9]*|[\u4e00-\u9fff]{2,}", label)}
            # English tokens match whole words; Chinese phrases may appear
            # inside a heading. No arbitrary path can enter this ranking.
            score = sum(term in words if term.isascii() else term in label for term in terms)
            scored.append((score, chapter))
        best = max(score for score, _ in scored)
        if best == 0:
            return None, "no_matching_teaching_chapter"
        winners = [chapter for score, chapter in scored if score == best]
        if len(winners) != 1:
            return None, "ambiguous_teaching_chapter"
        return winners[0].path, ""

    def _json(self, client, path, *, params, deadline, kind, receipts, budget):
        """Reuse the fixed transport; distinguish invalid data from lost replies.

        This small local streaming boundary is necessary because the legacy
        inspection parser classifies invalid JSON as unknown. Its code stays
        unchanged. The same aggregate wire budget and absolute deadline apply.
        """
        url = httpx.URL("https://api.github.com" + path, params=params)
        validate_github_url(str(url))
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise GitHubFailure("body_read_unknown", unknown=True)
        receipt = {"status": "dispatched", "bytes": 0}
        receipts.append(receipt)
        body = bytearray()
        try:
            with client.stream("GET", url, timeout=remaining,
                extensions={"n1_deadline": deadline, "n1_kind": kind},
                headers={"Accept": "application/vnd.github+json", "Accept-Encoding": "identity",
                    "X-GitHub-Api-Version": "2026-03-10", "User-Agent": "StudyPlan-resource-research"}) as response:
                if response.status_code != 200:
                    if response.status_code == 404 and "/contents/" in path:
                        _reject("teaching_chapter_not_found", unread=True)
                    _reject("body_http_rejected")
                if response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() not in _JSON_TYPES:
                    _reject("unsupported_body_response_type")
                if response.headers.get("Content-Encoding", "identity").strip().lower() != "identity":
                    _reject("unsupported_body_encoding")
                length = response.headers.get("Content-Length")
                if length is not None and (not length.isdecimal() or len(length) > 20 or int(length) > budget[0]):
                    _reject("body_size_exceeded")
                for chunk in response.iter_raw():
                    receipt["bytes"] += len(chunk)
                    if time.monotonic() >= deadline:
                        raise GitHubFailure("body_read_unknown", unknown=True)
                    if len(chunk) > budget[0]:
                        _reject("body_size_exceeded")
                    budget[0] -= len(chunk)
                    body.extend(chunk)
            if time.monotonic() >= deadline:
                raise GitHubFailure("body_read_unknown", unknown=True)
            try:
                data = json.loads(body.decode("utf-8"))
            except (ValueError, UnicodeError, RecursionError):
                _reject()
            if not isinstance(data, dict):
                _reject()
            receipt["status"] = "succeeded"
            return data
        except GitHubNotDispatchedError:
            receipt["status"] = "not_dispatched"
            raise GitHubFailure("body_destination_rejected") from None
        except GitHubFailure as exc:
            receipt["status"] = "unknown" if exc.unknown else "failed"
            raise
        except (httpx.HTTPError, OSError):
            receipt["status"] = "unknown"
            raise GitHubFailure("body_read_unknown", unknown=True) from None
        finally:
            body.clear()

    @staticmethod
    def _decode_file(data, *, expected_path=None):
        raw = text = None
        try:
            path = validate_content_path(data.get("path"))
            sha = data.get("sha")
            if (data.get("type") != "file" or data.get("encoding") != "base64"
                or posixpath.splitext(path)[1].lower() not in _TEXT_EXTENSIONS
                or (expected_path is not None and path != expected_path)
                or not isinstance(sha, str) or not _SHA.fullmatch(sha)
                or not isinstance(data.get("content"), str)):
                _reject()
            raw = base64.b64decode(data["content"].replace("\n", "").replace("\r", ""), validate=True)
            size = data.get("size")
            if (not isinstance(size, int) or isinstance(size, bool) or size != len(raw)
                or len(raw) == 0):
                _reject()
            if len(raw) > _MAX_TEXT:
                _reject("body_size_exceeded", unread=True)
            text = raw.decode("utf-8")
            if "\x00" in text:
                _reject()
            return path, sha, text
        except (ValueError, UnicodeError, binascii.Error, TypeError):
            _reject()
        finally:
            data.clear()
            raw = text = None

    def read(self, candidate: ResourceRecord, *, paths=(), must_teach=(), max_bytes=65536,
             timeout_seconds=15) -> TransientBody:
        receipts, payloads = [], []
        readme = chapter_text = None

        def result(status, reason="", **metadata):
            return TransientBody(status, reason=reason,
                requests=sum(receipt["status"] != "not_dispatched" for receipt in receipts),
                bytes_read=sum(receipt["bytes"] for receipt in receipts), **metadata)

        try:
            if not isinstance(candidate, ResourceRecord) or not isinstance(candidate.discovery, dict):
                _reject("invalid_body_candidate")
            if candidate.discovery.get("source") != "github":
                return result("unread", "unsupported_body_source")
            if (not isinstance(max_bytes, int) or isinstance(max_bytes, bool) or not 0 < max_bytes <= _MAX_WIRE
                or not isinstance(timeout_seconds, (int, float)) or isinstance(timeout_seconds, bool)
                or not 0 < timeout_seconds <= 15):
                _reject("invalid_body_limits")
            repo = candidate.discovery.get("repo")
            if not isinstance(repo, dict):
                _reject("invalid_body_candidate")
            owner, name, ref = repo.get("owner"), repo.get("name"), repo.get("default_branch")
            if not all(isinstance(part, str) and _COMPONENT.fullmatch(part) and part not in {".", ".."} for part in (owner, name)):
                _reject("invalid_body_candidate")
            if not _valid_ref(ref):
                _reject("invalid_body_ref")
            url = urlsplit(candidate.url)
            if (url.scheme != "https" or url.netloc not in {"github.com", "github.com:443"}
                or url.path != f"/{owner}/{name}" or url.query or url.fragment
                or any(ord(char) <= 32 or ord(char) == 127 or char == "\\" for char in candidate.url)):
                _reject("invalid_body_candidate")
            if not isinstance(paths, (tuple, list)) or len(paths) > 1:
                _reject("invalid_body_selection")
            for path in paths:
                validate_content_path(path)
                if posixpath.splitext(path)[1].lower() not in _TEXT_EXTENSIONS:
                    _reject("invalid_body_selection")
            if (not isinstance(must_teach, (tuple, list)) or len(must_teach) > 6
                or any(not isinstance(text, str) or not text.strip() or len(text) > 2000 for text in must_teach)):
                _reject("invalid_body_outcomes")
            for text in must_teach:
                text.encode("utf-8")
            prefix, params = f"/repos/{owner}/{name}", {"ref": ref}
            deadline = time.monotonic() + min(timeout_seconds, self._timeout)
            budget = [max_bytes]
            with self._client() as client:
                data = self._json(client, prefix + "/readme", params=params, deadline=deadline,
                    kind="content", receipts=receipts, budget=budget)
                payloads.append(data)
                readme_path, _, readme = self._decode_file(data)
                indexed = [entry for entry in self._chapters(readme, readme_path) if entry.status != "unsupported"]
                if paths and paths[0] not in {entry.path for entry in indexed}:
                    _reject("body_path_not_in_index")
                chapters = [entry for entry in indexed if posixpath.splitext(posixpath.basename(entry.path))[0].lower().split(".")[0]
                    not in _ADMIN_FILES]
                if paths:
                    selected = paths[0]
                else:
                    selected, reason = self._select_chapter(chapters, must_teach)
                    if selected is None:
                        return result("unread", reason)
                data = self._json(client, prefix + "/contents/" + quote(selected, safe="/"), params=params,
                    deadline=deadline, kind="content", receipts=receipts, budget=budget)
                payloads.append(data)
                path, sha, chapter_text = self._decode_file(data, expected_path=selected)
            chapter_url = f"https://github.com/{owner}/{name}/blob/{quote(ref, safe='')}/{quote(path, safe='/')}"
            resource_id, version = "resource_" + content_hash({"url": chapter_url}), "git-blob:" + sha
            chunk = {"resource_id": resource_id, "version": version,
                "content_hash": hashlib.sha256(chapter_text.encode("utf-8")).hexdigest(),
                "location": f"{path}#L1-L{max(1, len(chapter_text.splitlines()))}"}
            chunk["chunk_id"] = "chunk_" + content_hash(chunk)
            chunk["text"] = chapter_text
            return result("succeeded", resource_id=resource_id, url=chapter_url, version=version, chunks=[chunk])
        except GitHubFailure as exc:
            return result("unknown" if exc.unknown else "unread" if exc.unread else "failed",
                "body_read_unknown" if exc.unknown else exc.reason)
        except (ValueError, UnicodeError, TypeError, AttributeError, binascii.Error):
            return result("failed", "invalid_body_payload")
        except (httpx.HTTPError, OSError):
            return result("unknown", "body_read_unknown")
        finally:
            for payload in payloads:
                payload.clear()
            payloads.clear()
            readme = chapter_text = None
