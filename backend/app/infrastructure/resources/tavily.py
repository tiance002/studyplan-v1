"""One explicit Tavily lookup; durable dispatch admission belongs to the caller."""

from __future__ import annotations

import html
import ipaddress
import json
import re
import time
from datetime import datetime, timezone
from urllib.parse import urlsplit

import httpx
from app.core.errors import ForbiddenError, ValidationAppError
from app.core.ids import new_id
from app.domain.enums import MediaType, PreferenceScope, ResourceProvenance, ResourceVerificationStatus
from app.domain.resources.models import ResourceRecord, UnavailableResult
from app.domain.workspace.models import AuthContext
from app.ports.resource_index import ResourceQuery

_ENDPOINT = "https://api.tavily.com/search"
_MAX_BODY = 256 * 1024
UNKNOWN_SEARCH_REASON = "搜索响应未知，请核对后再显式发起新搜索"


def safe_candidate_url(value: object) -> str | None:
    """Validate display-only external URLs; this adapter never fetches them."""
    if not isinstance(value, str) or not value or len(value) > 4096:
        return None
    if any(ord(character) <= 32 or ord(character) == 127 for character in value) or "\\" in value:
        return None
    try:
        value.encode("utf-8")
        parsed = urlsplit(value)
        host = (parsed.hostname or "").lower().rstrip(".")
        port = parsed.port
        if (parsed.scheme.lower() not in {"http", "https"} or not host
                or parsed.username is not None or parsed.password is not None
                or "%" in parsed.netloc or port == 0):
            return None
        if host == "localhost" or host.endswith((".localhost", ".local", ".localdomain", ".internal")):
            return None
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            labels = host.encode("idna").decode("ascii").split(".")
            # Reject integer/octal/hex/shortened IPv4 spellings before treating
            # a numeric host as DNS. No resolver override or candidate request.
            if all(re.fullmatch(r"(?:[0-9]+|0x[0-9a-f]+)", label) for label in labels):
                return None
            if len(labels) < 2 or any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label) for label in labels):
                return None
        else:
            if not address.is_global or address.is_multicast:
                return None
            if isinstance(address, ipaddress.IPv6Address) and address.is_site_local:
                return None
            if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
                if not address.ipv4_mapped.is_global or address.ipv4_mapped.is_multicast:
                    return None
    except (ValueError, UnicodeError):
        return None
    return value


class TavilyResourceIndex:
    def __init__(self, api_key: str, *, transport: httpx.BaseTransport | None = None,
                 timeout_seconds: float = 15):
        if not 0 < timeout_seconds <= 15:
            raise ValidationAppError("检索超时需在 0–15 秒之间")
        self._key = api_key.strip()
        self._transport = transport
        self._timeout = timeout_seconds

    def find(self, query: ResourceQuery) -> list[ResourceRecord] | UnavailableResult:
        if not isinstance(query.scope, AuthContext):
            raise ForbiddenError("检索需要服务端授权范围")
        project_id = query.extra.get("project_id")
        if not isinstance(project_id, str):
            raise ValidationAppError("检索缺少学习空间范围")
        query.scope.require_project(project_id)
        words = query.extra.get("query")
        if not isinstance(words, str) or not words.strip() or not 1 <= len(words) <= 500:
            raise ValidationAppError("检索词需为 1–500 个字符")
        try:
            words.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ValidationAppError("检索词含非法字符") from exc
        if not isinstance(query.limit, int) or isinstance(query.limit, bool) or query.limit < 1:
            raise ValidationAppError("检索数量需为正整数")
        limit = min(query.limit, 5)
        if not self._key:
            return UnavailableResult("tavily_not_configured")
        search_words = words
        if query.preference.scope is not PreferenceScope.SYSTEM:
            search_words += (f"\nPreferred format: {query.preference.mode.value}; "
                             f"language: {query.preference.language}; "
                             f"official sources preferred: {query.preference.official_priority}")
        payload = {"query": search_words, "search_depth": "basic", "auto_parameters": False,
                   "max_results": limit, "include_answer": False,
                   "include_raw_content": False, "include_usage": True}
        started = time.monotonic()
        searched_at = datetime.now(timezone.utc).isoformat()
        try:
            with httpx.Client(transport=self._transport, timeout=self._timeout, trust_env=False,
                              follow_redirects=False, verify=True) as client:
                with client.stream("POST", _ENDPOINT, json=payload,
                                   headers={"Authorization": "Bearer " + self._key,
                                            "Accept-Encoding": "identity"}) as response:
                    if 300 <= response.status_code < 400:
                        return UnavailableResult("tavily_redirect_rejected")
                    if response.status_code == 401:
                        return UnavailableResult("tavily_unauthorized")
                    if response.status_code == 429:
                        return UnavailableResult("tavily_rate_limited")
                    if response.status_code != 200:
                        return UnavailableResult("tavily_http_error")
                    # Identity encoding avoids decoding unbounded compressed data.
                    if response.headers.get("Content-Encoding", "identity").lower() != "identity":
                        return UnavailableResult(UNKNOWN_SEARCH_REASON)
                    declared = response.headers.get("Content-Length", "")
                    if declared.isdecimal() and (len(declared) > 20 or int(declared) > _MAX_BODY):
                        return UnavailableResult(UNKNOWN_SEARCH_REASON)
                    body = bytearray()
                    for chunk in response.iter_raw():
                        if time.monotonic() - started > self._timeout:
                            return UnavailableResult(UNKNOWN_SEARCH_REASON)
                        if len(body) + len(chunk) > _MAX_BODY:
                            return UnavailableResult(UNKNOWN_SEARCH_REASON)
                        body.extend(chunk)
        except httpx.TimeoutException:
            return UnavailableResult(UNKNOWN_SEARCH_REASON)
        except httpx.HTTPError:
            return UnavailableResult(UNKNOWN_SEARCH_REASON)
        try:
            decoded = json.loads(body)
        except (ValueError, UnicodeError, RecursionError):
            return UnavailableResult(UNKNOWN_SEARCH_REASON)
        if not isinstance(decoded, dict) or not isinstance(decoded.get("results"), list):
            return UnavailableResult(UNKNOWN_SEARCH_REASON)
        candidates: list[ResourceRecord] = []
        seen: set[str] = set()
        for item in decoded["results"]:
            if not isinstance(item, dict):
                continue
            url = safe_candidate_url(item.get("url"))
            title = item.get("title")
            if url is None or url in seen or not isinstance(title, str):
                continue
            title = html.unescape(re.sub(r"<[^>]*>", "", title)).strip()
            if not title or len(title) > 300:
                continue
            try:
                title.encode("utf-8")
            except UnicodeEncodeError:
                continue
            seen.add(url)
            candidates.append(ResourceRecord(
                resource_id=new_id("res"), project_id=project_id, url=url, title=title,
                media_type=MediaType.TEXT, language="und",
                provenance=ResourceProvenance.SEARCH_CANDIDATE,
                verification_status=ResourceVerificationStatus.UNVERIFIED, checked_at=None,
                source_note=f"Tavily 搜索候选；搜索时间 {searched_at}；语言未核验；未检查链接、内容覆盖或教学质量。",
            ))
            if len(candidates) == limit:
                break
        return candidates if candidates else UnavailableResult("tavily_no_safe_results")
