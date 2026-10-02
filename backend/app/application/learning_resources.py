"""User-triggered search and explicit private selection; never publish a public Seed."""
import hashlib
import json
from dataclasses import asdict

from app.application.resource_discovery_contract import DiscoveryEvidence, SelectionMapping
from app.core.errors import (
    DependencyUnavailableError,
    IdempotencyConflictError,
    NotFoundError,
    ValidationAppError,
)
from app.core.ids import new_id
from app.domain.enums import MediaType, ResourceProvenance, ResourceVerificationStatus
from app.domain.resources.discovery import validate_private_mapping
from app.domain.resources.models import (
    DEFAULT_SYSTEM_PREFERENCE,
    ResourceRecord,
    UnavailableResult,
    rank_resources,
)
from app.ports.learning_resources import LearningResourcesPort
from app.ports.resource_index import ResourceIndexPort, ResourceInspectionQuery, ResourceQuery
from pydantic import ValidationError

UNKNOWN_SEARCH_REASON = "搜索响应未知，请核对后再显式发起新搜索"
UNKNOWN_INSPECTION_REASON = "教程检查响应未知，请核对回执；不会自动重新读取"


class LearningResourceService:
    def __init__(self, repository: LearningResourcesPort, search: ResourceIndexPort | None, request_limit: int,
                 *, preference_resolver=None, github=None, content_limit=3000, metadata_limit=2000):
        self.repository = repository
        self.index = search
        self.request_limit = max(0, min(1000, request_limit))
        self.preference_resolver = preference_resolver
        self.github = github
        self.content_limit = max(0, min(3000, content_limit))
        self.metadata_limit = max(0, min(2000, metadata_limit))

    @staticmethod
    def _target(scope, target):
        from app.application.resource_preferences import ResourcePreferenceService
        ResourcePreferenceService._target(scope, target)

    @staticmethod
    def _hash(payload):
        return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()

    @staticmethod
    def _key(key):
        if not isinstance(key, str) or not 1 <= len(key.strip()) <= 128:
            raise ValidationAppError("请求需要1–128字符幂等键")
        try:
            key.encode("utf-8")
        except UnicodeError as exc:
            raise ValidationAppError("幂等键含非法字符") from exc
        return key.strip()

    def search(self, scope, target, query, idempotency_key, *, source="web"):
        self._target(scope, target)
        if not isinstance(query, str) or not 1 <= len(query.strip()) <= 500:
            raise ValidationAppError("搜索词长度需在1–500字符之间")
        idempotency_key = self._key(idempotency_key)
        if source not in {"web", "github"}:
            raise ValidationAppError("资料来源只能是网页或GitHub")
        try:
            query.encode("utf-8")
            idempotency_key.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ValidationAppError("搜索词或幂等键含非法字符") from exc
        query = query.strip()
        input_hash = self._hash([target, query, source])
        # A durable same-key reply checks current authorization in the repository
        # but never re-resolves mutable preferences or requires a live provider.
        try:
            prior = self.repository.get_search_by_key(scope, target, idempotency_key)
        except NotFoundError:
            prior = None
        if prior is not None:
            old_hash = hashlib.sha256(json.dumps([target, query], sort_keys=True).encode()).hexdigest()
            legacy_match = (source == "web" and prior["source"] == "web" and not prior["context_snapshot"]
                            and prior["input_hash"] == old_hash)
            if prior["input_hash"] != input_hash and not legacy_match:
                raise IdempotencyConflictError()
            return prior
        index = self.index if source == "web" else self.github
        if index is None:
            # Check existing cross-position intent before a missing adapter can
            # obscure a same-key conflict. Repository scope checks remain final.
            conflict = getattr(self.repository, "check_search_intent", None)
            if conflict:
                conflict(scope, target, idempotency_key, input_hash)
            raise DependencyUnavailableError("所选搜索服务未配置；可以手动接入资料")
        # Validate the selected node and complete preference before reserving
        # quota; a wrong node or uninterpretable setting never dispatches.
        preference = (self.preference_resolver(scope, target) if self.preference_resolver
                      else DEFAULT_SYSTEM_PREFERENCE)
        context = {"preference": json.loads(json.dumps(asdict(preference), default=str)),
                   "node_id": target.get("node_id"), "module_keys": self.repository.allowed_module_keys(scope, target)}
        saved, fresh = self.repository.reserve(scope, target, query, idempotency_key, input_hash,
            self.request_limit, source=source, context_snapshot=context)
        if not fresh:
            return saved
        # Reservation is committed before any network dispatch. A process exit
        # leaves dispatched, which repeat-key reads never automatically replay.
        try:
            result = index.find(ResourceQuery(scope=scope, node_keys=(), preference=preference,
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
                "github_forbidden": "GitHub匿名接口暂不可用或限流，可以稍后显式查询",
                "github_rate_limited": "GitHub搜索暂时限流，可以稍后显式查询",
                "github_no_results": "没有找到GitHub候选；可以调整搜索词或手动接入",
                "github_redirect_rejected": "GitHub返回不允许的跳转",
                "github_http_error": "GitHub搜索请求失败",
                "github_destination_rejected": "GitHub DNS返回非公网地址，已在外发前拒绝；请检查代理的DNS/Fake-IP配置",
            }.get(result.reason, result.reason)
            return self.repository.finish(scope, target, saved["search_id"], status, [], message)
        try:
            candidates = [json.loads(json.dumps(asdict(item), default=str)) for item in result]
            for candidate in candidates:
                candidate["discovery"] = DiscoveryEvidence.model_validate(candidate.get("discovery", {})).model_dump(mode="json")
        except (ValidationError, ValueError, TypeError):
            return self.repository.finish(scope, target, saved["search_id"], "reconciliation_required", [], UNKNOWN_SEARCH_REASON)
        return self.repository.finish(scope, target, saved["search_id"], "succeeded", candidates, None)

    def inspect(self, scope, target, search_id, candidate_id, idempotency_key, *, paths=None):
        self._target(scope, target)
        key = self._key(idempotency_key)
        paths = [] if paths is None else paths
        if not isinstance(paths, list) or len(paths) > 2 or any(not isinstance(p, str) for p in paths):
            raise ValidationAppError("最多指定两个目录内文本章节")
        try:
            input_hash = self._hash([target, search_id, candidate_id, paths])
        except (UnicodeError, TypeError) as exc:
            raise ValidationAppError("教程检查参数含非法字符") from exc
        try:
            previous = self.repository.get_inspection_by_key(scope, target, key)
        except NotFoundError:
            previous = None
        if previous is not None:
            if previous["input_hash"] != input_hash:
                raise IdempotencyConflictError()
            return previous
        if self.github is None:
            raise DependencyUnavailableError("GitHub检查服务未配置")
        found = self.repository.get_search(scope, target, search_id)
        if found["status"] != "succeeded" or found["source"] != "github":
            raise ValidationAppError("只能检查已成功的GitHub搜索候选")
        if not any(candidate["resource_id"] == candidate_id for candidate in found["candidates"]):
            raise NotFoundError("候选不属于指定搜索和学习位置")
        saved, fresh = self.repository.reserve_inspection(scope, target, search_id, candidate_id,
            key, input_hash, paths, found["context_snapshot"], self.content_limit, self.metadata_limit)
        if not fresh:
            return saved
        try:
            # The original search preference is frozen, including its version.
            from app.domain.enums import PreferenceMode, PreferenceScope
            from app.domain.resources.models import ResourcePreference
            setting = saved["context_snapshot"].get("preference", {})
            preference = (ResourcePreference(**dict(setting, scope=PreferenceScope(setting["scope"]),
                mode=PreferenceMode(setting["mode"]))) if setting else DEFAULT_SYSTEM_PREFERENCE)
            result = self.github.inspect(ResourceInspectionQuery(scope=scope, candidate=saved["candidate"],
                query=found["query"], preference=preference, paths=tuple(paths)))
        except Exception:
            # A crash or unclassified upstream outcome never becomes a retry.
            return self.repository.finish_inspection(scope, target, saved["inspection_id"],
                "reconciliation_required", saved["candidate"], [], UNKNOWN_INSPECTION_REASON)
        return self.repository.finish_inspection(scope, target, saved["inspection_id"], result.status,
            result.candidate, result.receipts, result.error)

    def get_inspection(self, scope, target, inspection_id):
        return self.repository.get_inspection(scope, target, inspection_id)

    def get_inspection_by_key(self, scope, target, key):
        return self.repository.get_inspection_by_key(scope, target, key)

    def get_search(self, scope, target, search_id):
        return self.repository.get_search(scope, target, search_id)

    def get_search_by_key(self, scope, target, key):
        return self.repository.get_search_by_key(scope, target, key)

    def list_selected(self, scope, target):
        return self.repository.list_selected(scope, target)

    def select(self, scope, target, search_id, candidate_id, *, module_keys=None, chapter_paths=None, role="reference"):
        found = self.repository.get_search(scope, target, search_id)
        if found["status"] != "succeeded":
            raise ValidationAppError("搜索尚无可选择结果；可以手动接入")
        resource = next((c for c in found["candidates"] if c["resource_id"] == candidate_id), None)
        if resource is None:
            raise NotFoundError("该候选不属于此搜索和学习单元")
        inspection = self.repository.latest_inspection(scope, target, search_id, candidate_id)
        if inspection is not None:
            resource = inspection["candidate"]
        if module_keys or chapter_paths:
            if not module_keys or not chapter_paths or inspection is None:
                raise ValidationAppError("章节映射需要模块键、已读取章节和成功检查证据")
            try:
                evidence = DiscoveryEvidence.model_validate(resource["discovery"])
                evidence.selection_mapping = SelectionMapping(module_keys=module_keys, chapter_paths=chapter_paths, role=role)
            except ValidationError as exc:
                raise ValidationAppError("私人章节映射字段无效") from exc
            validate_private_mapping(evidence, self.repository.allowed_module_keys(scope, target))
            for chapter in evidence.chapters:
                if chapter.path in chapter_paths:
                    chapter.module_keys = list(module_keys)
            resource = dict(resource, discovery=evidence.model_dump(mode="json"))
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
        resource.discovery = DiscoveryEvidence(source="manual", limitations=["用户手动接入，尚未检查内容"]).model_dump(mode="json")
        return self.repository.select(scope, target, json.loads(json.dumps(asdict(resource), default=str)))

    def remove(self, scope, target, selection_id):
        return self.repository.remove(scope, target, selection_id)
