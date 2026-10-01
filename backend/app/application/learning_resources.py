"""User-triggered search and explicit private selection; never publish a public Seed."""
import hashlib
import json
from dataclasses import asdict

from app.core.errors import DependencyUnavailableError, NotFoundError, ValidationAppError
from app.core.ids import new_id
from app.domain.enums import MediaType, ResourceProvenance, ResourceVerificationStatus
from app.domain.resources.models import (
    DEFAULT_SYSTEM_PREFERENCE,
    ResourceRecord,
    UnavailableResult,
    rank_resources,
)
from app.ports.learning_resources import LearningResourcesPort
from app.ports.resource_index import ResourceIndexPort, ResourceQuery

UNKNOWN_SEARCH_REASON = "搜索响应未知，请核对后再显式发起新搜索"


class LearningResourceService:
    def __init__(self, repository: LearningResourcesPort, search: ResourceIndexPort | None, request_limit: int,
                 *, preference_resolver=None):
        self.repository = repository
        self.index = search
        self.request_limit = max(0, min(1000, request_limit))
        self.preference_resolver = preference_resolver

    def search(self, scope, target, query, idempotency_key):
        scope.require_project(target["project_id"])
        if not isinstance(query, str) or not 1 <= len(query.strip()) <= 500:
            raise ValidationAppError("搜索词长度需在1–500字符之间")
        if not isinstance(idempotency_key, str) or not 1 <= len(idempotency_key.strip()) <= 128:
            raise ValidationAppError("搜索请求需要1–128字符幂等键")
        try:
            query.encode("utf-8")
            idempotency_key.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ValidationAppError("搜索词或幂等键含非法字符") from exc
        if self.index is None:
            raise DependencyUnavailableError("搜索服务未配置；可以手动接入资料")
        query = query.strip()
        # Validate the selected node and complete preference before reserving
        # quota; a wrong node or uninterpretable setting never dispatches.
        preference = (self.preference_resolver(scope, target) if self.preference_resolver
                      else DEFAULT_SYSTEM_PREFERENCE)
        input_hash = hashlib.sha256(json.dumps([target, query], sort_keys=True).encode()).hexdigest()
        saved, fresh = self.repository.reserve(scope, target, query, idempotency_key, input_hash, self.request_limit)
        if not fresh:
            return saved
        # Reservation is committed before any network dispatch. A process exit
        # leaves dispatched, which repeat-key reads never automatically replay.
        try:
            result = self.index.find(ResourceQuery(scope=scope, node_keys=(), preference=preference,
                limit=5, extra={"project_id": target["project_id"], "query": query}))
            if not isinstance(result, UnavailableResult):
                result = rank_resources(result, preference=preference)
        except Exception:
            # Never expose a transport/config exception (possibly containing
            # secrets), or assume a failed local response implies zero charges.
            result = UnavailableResult(UNKNOWN_SEARCH_REASON)
        if isinstance(result, UnavailableResult):
            status = "reconciliation_required" if result.reason == UNKNOWN_SEARCH_REASON else "failed"
            message = {
                "tavily_not_configured": "搜索服务未配置，可以手动接入资料",
                "tavily_unauthorized": "搜索服务授权失败，请检查本机服务密钥或手动接入",
                "tavily_rate_limited": "搜索服务暂时限流，可以稍后显式查询或手动接入",
                "tavily_redirect_rejected": "搜索服务返回了不允许的跳转，可以手动接入",
                "tavily_http_error": "搜索服务请求失败，可以手动接入",
                "tavily_no_safe_results": "没有可用的安全候选，可以修改搜索词或手动接入",
            }.get(result.reason, result.reason)
            return self.repository.finish(scope, target, saved["search_id"], status, [], message)
        candidates = [json.loads(json.dumps(asdict(item), default=str)) for item in result]
        return self.repository.finish(scope, target, saved["search_id"], "succeeded", candidates, None)

    def get_search(self, scope, target, search_id):
        return self.repository.get_search(scope, target, search_id)

    def get_search_by_key(self, scope, target, key):
        return self.repository.get_search_by_key(scope, target, key)

    def list_selected(self, scope, target):
        return self.repository.list_selected(scope, target)

    def select(self, scope, target, search_id, candidate_id):
        found = self.repository.get_search(scope, target, search_id)
        if found["status"] != "succeeded":
            raise ValidationAppError("搜索尚无可选择结果；可以手动接入")
        resource = next((c for c in found["candidates"] if c["resource_id"] == candidate_id), None)
        if resource is None:
            raise NotFoundError("该候选不属于此搜索和学习单元")
        return self.repository.select(scope, target, resource)

    def add_manual(self, scope, target, url, title):
        # URL safety is also enforced by the storage boundary; this operation
        # saves metadata only and never fetches or executes a repository.
        scope.require_project(target["project_id"])
        if not isinstance(title, str) or not 1 <= len(title.strip()) <= 300:
            raise ValidationAppError("资料标题长度需在1–300字符之间")
        if not isinstance(url, str) or not 1 <= len(url.strip()) <= 4096:
            raise ValidationAppError("资料网址长度需在1–4096字符之间")
        try:
            title.encode("utf-8")
            url.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ValidationAppError("资料标题或网址含非法字符") from exc
        resource = ResourceRecord(resource_id=new_id("res"), url=url.strip(), title=title.strip(),
            project_id=target["project_id"], language="zh",
            media_type=MediaType.REPO if url.startswith("https://github.com/") else MediaType.TEXT,
            provenance=ResourceProvenance.USER_PROVIDED, verification_status=ResourceVerificationStatus.UNVERIFIED)
        resource.checked_at = None
        resource.source_note = "用户手动接入，内容与章节尚未核验"
        return self.repository.select(scope, target, json.loads(json.dumps(asdict(resource), default=str)))

    def remove(self, scope, target, selection_id):
        return self.repository.remove(scope, target, selection_id)
