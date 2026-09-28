"""domain_packs 领域：策划领域内容包（有限领域的主线/扩展/实践模板）。

设计定位（V1.2 §二.3）：``DomainPack`` 是**策划配置输入**，
不是新 Agent、不是微服务、也不是第二套业务规则。
首版从仓库内审核过的 JSON/YAML 加载，配一个小型只读索引。

硬约束：

- 发布版（``PUBLISHED``）**只读**：任何改动产生新的 ``version``。
- 不实现公共投稿系统；模板实例化接口可预留 ``template_ref/version``。
- 公共素材只能被**引用/复制为私有计划**，不把他人的私有进度作为模板。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.core.errors import ValidationAppError
from app.core.ids import require_stable_key
from app.domain.enums import DomainPackStatus


@dataclass(frozen=True, slots=True)
class DomainPack:
    """一个版本化的领域内容包。

    字段（V1.2 §二.3）：
    ``pack_key/version/status/stage_blueprints/resource_refs/
    extension_blueprints/practice_blueprints`` + ``supported_scope/provenance``。
    """

    pack_key: str
    version: int
    status: DomainPackStatus
    supported_scope: str
    title: str
    #: 阶段蓝图：每个元素形如 ``{"stable_key", "title", "section_kind", "objective"}``。
    stage_blueprints: tuple[dict[str, object], ...] = ()
    #: 引用的公共资源来源 ``source_id``（只引用，不内嵌全文）。
    resource_refs: tuple[str, ...] = ()
    #: 扩展蓝图：``{"topic", "concepts", "guidance", "search_hints", "thinking_prompts"}``。
    extension_blueprints: tuple[dict[str, object], ...] = ()
    #: 实践蓝图：``{"stable_key", "title", "goal", "acceptance"}``。
    practice_blueprints: tuple[dict[str, object], ...] = ()
    provenance: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @staticmethod
    def create(
        *,
        pack_key: str,
        version: int,
        supported_scope: str,
        title: str,
        status: DomainPackStatus = DomainPackStatus.DRAFT,
        stage_blueprints: tuple[dict[str, object], ...] = (),
        resource_refs: tuple[str, ...] = (),
        extension_blueprints: tuple[dict[str, object], ...] = (),
        practice_blueprints: tuple[dict[str, object], ...] = (),
        provenance: str = "",
        now: datetime | None = None,
    ) -> "DomainPack":
        if version < 1:
            raise ValidationAppError("领域包版本必须从 1 开始")
        _require_text(title, "领域包标题", max_len=200)
        _require_text(supported_scope, "覆盖范围", max_len=200)
        return DomainPack(
            pack_key=require_stable_key(pack_key),
            version=version,
            status=status,
            supported_scope=supported_scope.strip(),
            title=title.strip(),
            stage_blueprints=tuple(stage_blueprints),
            resource_refs=tuple(resource_refs),
            extension_blueprints=tuple(extension_blueprints),
            practice_blueprints=tuple(practice_blueprints),
            provenance=provenance.strip(),
            created_at=now or datetime.now(timezone.utc),
        )

    @property
    def is_published(self) -> bool:
        return self.status is DomainPackStatus.PUBLISHED

    def require_published(self) -> None:
        """只有发布版领域包可以被用于正式规划。"""
        if not self.is_published:
            raise ValidationAppError("未发布的领域包不可用于规划")


def _require_text(value: str, field: str, *, max_len: int) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValidationAppError(f"{field}不能为空")
    if len(value) > max_len:
        raise ValidationAppError(f"{field}长度不得超过 {max_len} 字符")


__all__ = ["DomainPack"]
