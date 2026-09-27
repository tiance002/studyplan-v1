"""resources 领域：资源记录、偏好与覆盖。

核心约束：
- ``URL 可达 ≠ 内容质量``。三件事严格分离：可达性、内容覆盖、教学质量。
- 找不到真实资源时返回 ``unavailable`` + 检索建议；**绝不伪造 URL 或视频时间戳**。
- 偏好优先级：节点 > 单元 > 学习空间默认 > 系统默认。
  临时切换只写 override，**不写全局**。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable
from urllib.parse import urlparse

from app.core.errors import ValidationAppError
from app.core.ids import new_id
from app.domain.enums import (
    PREFERENCE_SCOPE_RANK,
    MediaType,
    PreferenceMode,
    PreferenceScope,
    ResourceProvenance,
    ResourceVerificationStatus,
)

SAFE_URL_SCHEMES: frozenset[str] = frozenset({"http", "https"})

#: 私网 / 环回 / 链路本地前缀：禁止把内网地址当作外部资源（防 SSRF）。
_PRIVATE_HOST_PREFIXES: tuple[str, ...] = (
    "127.",
    "10.",
    "192.168.",
    "169.254.",
    "0.",
    "::1",
    "fc",
    "fd",
)


@dataclass(slots=True)
class ResourceRecord:
    """一条资源记录。``section_anchor`` 可为章节编号或视频时间点。"""

    resource_id: str
    url: str
    title: str
    media_type: MediaType
    language: str
    provenance: ResourceProvenance
    verification_status: ResourceVerificationStatus
    section_anchor: str | None = None
    checked_at: datetime | None = None
    source_note: str = ""
    project_id: str | None = None

    @staticmethod
    def create(
        *,
        url: str,
        title: str,
        media_type: MediaType,
        language: str = "zh",
        provenance: ResourceProvenance = ResourceProvenance.CURATED_POOL,
        verification_status: ResourceVerificationStatus = ResourceVerificationStatus.UNVERIFIED,
        section_anchor: str | None = None,
        project_id: str | None = None,
        now: datetime | None = None,
    ) -> "ResourceRecord":
        require_safe_url(url)
        _require_text(title, "资源标题", max_len=300)
        return ResourceRecord(
            resource_id=new_id("res"),
            url=url.strip(),
            title=title.strip(),
            media_type=media_type,
            language=language.strip() or "zh",
            provenance=provenance,
            verification_status=verification_status,
            section_anchor=section_anchor.strip() if section_anchor else None,
            checked_at=now or datetime.now(timezone.utc),
            project_id=project_id,
        )

    def mark_verified(self, *, now: datetime | None = None) -> None:
        self.verification_status = ResourceVerificationStatus.VERIFIED_CANDIDATE
        self.checked_at = now or datetime.now(timezone.utc)

    def mark_unavailable(self, *, now: datetime | None = None) -> None:
        """探测失败如实标记。**不删除记录**，保留历史与出处。"""
        self.verification_status = ResourceVerificationStatus.UNAVAILABLE
        self.checked_at = now or datetime.now(timezone.utc)


def require_safe_url(url: str) -> str:
    """URL 安全校验：限制 scheme，拒绝私网地址与凭据内嵌。

    这是防 SSRF 的第一道关；实际抓取前还须校验重定向后的最终地址。
    """
    if not isinstance(url, str) or not url.strip():
        raise ValidationAppError("资源 URL 不能为空")
    parsed = urlparse(url.strip())
    if parsed.scheme.lower() not in SAFE_URL_SCHEMES:
        raise ValidationAppError(f"不支持的 URL 协议：{parsed.scheme or '(空)'}")
    if not parsed.hostname:
        raise ValidationAppError("URL 缺少主机名")
    if parsed.username or parsed.password:
        raise ValidationAppError("URL 不允许内嵌凭据")
    host = parsed.hostname.lower()
    if host == "localhost" or host.endswith(".local"):
        raise ValidationAppError("不允许使用本机地址作为外部资源")
    if any(host.startswith(prefix) for prefix in _PRIVATE_HOST_PREFIXES):
        raise ValidationAppError("不允许使用私有网段地址作为外部资源")
    return url.strip()


@dataclass(frozen=True, slots=True)
class ResourcePreference:
    """一个作用域上的资源偏好。``version`` 支持乐观并发。"""

    scope: PreferenceScope
    scope_ref: str            # SYSTEM 用 "system"；其余用 project/unit/node id
    mode: PreferenceMode = PreferenceMode.MIXED
    language: str = "zh"
    official_priority: bool = True
    pace: str = "normal"      # slow / normal / fast
    version: int = 1


@dataclass(frozen=True, slots=True)
class PreferenceOverride:
    """临时偏好覆盖。可整条删除，删除后回落到上一层。"""

    override_id: str
    scope: PreferenceScope
    scope_ref: str
    mode: PreferenceMode
    language: str
    created_at: datetime

    @staticmethod
    def create(
        *,
        scope: PreferenceScope,
        scope_ref: str,
        mode: PreferenceMode,
        language: str = "zh",
        now: datetime | None = None,
    ) -> "PreferenceOverride":
        if scope is PreferenceScope.SYSTEM:
            raise ValidationAppError("系统默认层不可被临时覆盖")
        return PreferenceOverride(
            override_id=new_id("ovr"),
            scope=scope,
            scope_ref=scope_ref,
            mode=mode,
            language=language,
            created_at=now or datetime.now(timezone.utc),
        )


DEFAULT_SYSTEM_PREFERENCE = ResourcePreference(
    scope=PreferenceScope.SYSTEM,
    scope_ref="system",
    mode=PreferenceMode.MIXED,
    language="zh",
    official_priority=True,
    pace="normal",
    version=1,
)


def resolve_preference(
    *,
    system: ResourcePreference = DEFAULT_SYSTEM_PREFERENCE,
    project: ResourcePreference | None = None,
    unit: ResourcePreference | None = None,
    node: ResourcePreference | None = None,
) -> ResourcePreference:
    """按优先级回落到最具体的一层。

    实现刻意保持「取最具体者整体生效」而不是按字段部分合并：
    部分合并会产生难以解释的组合（例如节点的语言 + 项目的媒体形态），
    用户无法从 UI 上预测结果。
    """
    candidates: list[ResourcePreference] = [system]
    for item in (project, unit, node):
        if item is not None:
            candidates.append(item)
    return max(candidates, key=lambda p: PREFERENCE_SCOPE_RANK[p.scope])


def rank_resources(
    resources: Iterable[ResourceRecord],
    *,
    preference: ResourcePreference,
) -> list[ResourceRecord]:
    """按偏好排序资源。

    排序键（依次）：
    1. ``unavailable`` 沉底（不可用不应占据首屏）
    2. 媒体形态匹配（both/mixed 时 text 优先，除非 video_first）
    3. 语言匹配
    4. 出处为官方
    5. 标题稳定排序，保证结果可复现
    """
    mode = preference.mode
    language = preference.language

    def media_rank(resource: ResourceRecord) -> int:
        if mode is PreferenceMode.BOTH or mode is PreferenceMode.MIXED:
            order = {MediaType.TEXT: 0, MediaType.INTERACTIVE: 1, MediaType.VIDEO: 2}
        elif mode is PreferenceMode.TEXT_FIRST:
            order = {MediaType.TEXT: 0, MediaType.INTERACTIVE: 1, MediaType.VIDEO: 2}
        else:  # video_first
            order = {MediaType.VIDEO: 0, MediaType.INTERACTIVE: 1, MediaType.TEXT: 2}
        return order.get(resource.media_type, 9)

    def sort_key(resource: ResourceRecord) -> tuple[int, int, int, int, str]:
        unavailable = 1 if resource.verification_status is ResourceVerificationStatus.UNAVAILABLE else 0
        language_miss = 0 if resource.language == language else 1
        official_miss = 0 if (
            preference.official_priority
            and resource.provenance is ResourceProvenance.OFFICIAL
        ) else 1
        return (unavailable, media_rank(resource), language_miss, official_miss, resource.title)

    return sorted(resources, key=sort_key)


@dataclass(frozen=True, slots=True)
class UnavailableResult:
    """找不到真实资源时的诚实返回。"""

    reason: str
    suggestions: tuple[str, ...] = ()

    @staticmethod
    def create(reason: str, suggestions: Iterable[str] = ()) -> "UnavailableResult":
        return UnavailableResult(
            reason=reason,
            suggestions=tuple(s for s in suggestions if s),
        )


def _require_text(value: str, field: str, *, max_len: int) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValidationAppError(f"{field}不能为空")
    if len(value) > max_len:
        raise ValidationAppError(f"{field}长度不得超过 {max_len} 字符")


__all__ = [
    "DEFAULT_SYSTEM_PREFERENCE",
    "SAFE_URL_SCHEMES",
    "PreferenceOverride",
    "ResourcePreference",
    "ResourceRecord",
    "UnavailableResult",
    "rank_resources",
    "require_safe_url",
    "resolve_preference",
]
