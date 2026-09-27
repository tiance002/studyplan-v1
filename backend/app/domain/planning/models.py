"""planning 领域：草案、计划版本、阶段、局部改动与幂等发布。

核心不变量（SOFTWARE_DESIGN.md §3）：
1. 草案**永不**直接覆盖正式路线；只有用户确认的 ``PlanRevision`` 是当前路线。
2. 已确认结构**不可变**：任何改动产生新的 revision。
3. 同项目内 ``revision`` 序号唯一。
4. 「当前版本」由显式引用决定，**不得**取最大版本号（未确认草案可能版本更高）。
5. 发布必须校验草案 hash + expected_version + 幂等键，且重复确认不产生两份计划。
6. 局部重规划按 ``stable_key`` 精确映射，不依据相近标题自动合并历史。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol, Sequence

from app.core.errors import (
    ConflictError,
    IdempotencyConflictError,
    NotFoundError,
    ValidationAppError,
    VersionConflictError,
)
from app.core.ids import content_hash, content_hash_stable, new_id
from app.domain.enums import (
    DraftDecision,
    OutlineSectionKind,
    PlanDraftStatus,
    PlanRevisionStatus,
)

#: 软上限：超过时给出警告但不阻断（避免为了「美观」而删掉必要内容）。
SOFT_LIMIT_UNITS = 40
SOFT_LIMIT_NODES = 200
SOFT_LIMIT_TASKS = 24


@dataclass(frozen=True, slots=True)
class PlanStage:
    """计划阶段。``order_index`` 决定展示顺序，必须连续递增。"""

    stage_id: str
    stable_key: str
    title: str
    section_kind: OutlineSectionKind
    order_index: int
    objective: str = ""

    @staticmethod
    def create(
        *,
        stable_key: str,
        title: str,
        section_kind: OutlineSectionKind,
        order_index: int,
        objective: str = "",
    ) -> "PlanStage":
        return PlanStage(
            stage_id=new_id("stg"),
            stable_key=stable_key,
            title=title.strip(),
            section_kind=section_kind,
            order_index=order_index,
            objective=objective.strip(),
        )


@dataclass(frozen=True, slots=True)
class PlanUnitLink:
    """阶段 -> 单元（引用已存在的稳定单元 ID）。"""

    stage_id: str
    unit_id: str
    order_index: int


@dataclass(frozen=True, slots=True)
class PlanTaskLink:
    """阶段 -> 实践任务。"""

    stage_id: str
    task_id: str
    order_index: int


@dataclass(slots=True)
class PlanRevision:
    """路径结构快照。

    一旦 ``status`` 变为 APPROVED 或 SUPERSEDED，**结构不可变**：
    ``freeze()`` 后任何 ``replace_*`` 调用都会抛错。
    """

    plan_id: str
    project_id: str
    revision: int
    goal_snapshot: str
    stages: tuple[PlanStage, ...] = ()
    unit_links: tuple[PlanUnitLink, ...] = ()
    task_links: tuple[PlanTaskLink, ...] = ()
    status: PlanRevisionStatus = PlanRevisionStatus.DRAFT
    approved_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @staticmethod
    def create(
        *,
        project_id: str,
        revision: int,
        goal_snapshot: str,
        stages: Sequence[PlanStage] = (),
        unit_links: Sequence[PlanUnitLink] = (),
        task_links: Sequence[PlanTaskLink] = (),
        now: datetime | None = None,
    ) -> "PlanRevision":
        if revision < 1:
            raise ValidationAppError("revision 必须从 1 开始")
        plan = PlanRevision(
            plan_id=new_id("pln"),
            project_id=project_id,
            revision=revision,
            goal_snapshot=goal_snapshot.strip(),
            stages=tuple(stages),
            unit_links=tuple(unit_links),
            task_links=tuple(task_links),
            created_at=now or datetime.now(timezone.utc),
        )
        plan._validate_structure()
        return plan

    @property
    def is_frozen(self) -> bool:
        return self.status in {PlanRevisionStatus.APPROVED, PlanRevisionStatus.SUPERSEDED}

    @property
    def version(self) -> int:
        """当前引用的乐观并发版本号 = revision 序号。

        未发布的草案不会成为 ``current``，因此这里直接复用 ``revision``，
        与「不得取最大版本号」的规则一致（见模块 docstring §4）。
        """
        return self.revision

    def freeze(self, *, now: datetime | None = None) -> None:
        """发布：一旦冻结便不可再改结构。"""
        self.status = PlanRevisionStatus.APPROVED
        self.approved_at = now or datetime.now(timezone.utc)

    def mark_superseded(self) -> None:
        self.status = PlanRevisionStatus.SUPERSEDED

    def structure_fingerprint(self) -> str:
        """结构指纹：用于判断「同一草案重复确认」与「重规划是否实质变化」。"""
        return content_hash(
            {
                "project_id": self.project_id,
                "goal_snapshot": self.goal_snapshot,
                "stages": [
                    {
                        "stable_key": s.stable_key,
                        "title": s.title,
                        "section_kind": str(s.section_kind),
                        "order_index": s.order_index,
                        "objective": s.objective,
                    }
                    for s in self.stages
                ],
                "unit_links": [
                    {"unit_id": link.unit_id, "order_index": link.order_index}
                    for link in self.unit_links
                ],
                "task_links": [
                    {"task_id": link.task_id, "order_index": link.order_index}
                    for link in self.task_links
                ],
            }
        )

    def stable_unit_keys(self) -> list[str]:
        """按顺序返回阶段引用的 stable_key（用于局部重规划精确映射）。"""
        return [s.stable_key for s in sorted(self.stages, key=lambda s: s.order_index)]

    def _validate_structure(self) -> None:
        if not self.stages:
            raise ValidationAppError("计划必须至少包含一个阶段")
        orders = [s.order_index for s in self.stages]
        if len(set(orders)) != len(orders):
            raise ValidationAppError("阶段顺序索引不可重复")
        if sorted(orders) != list(range(len(orders))):
            raise ValidationAppError("阶段顺序索引必须从 0 开始连续递增")
        keys = [s.stable_key for s in self.stages]
        if len(set(keys)) != len(keys):
            raise ValidationAppError("阶段稳定键不可重复")

        stage_ids = {s.stage_id for s in self.stages}
        for unit_link in self.unit_links:
            if unit_link.stage_id not in stage_ids:
                raise ValidationAppError("单元链接指向不存在的阶段")
        for task_link in self.task_links:
            if task_link.stage_id not in stage_ids:
                raise ValidationAppError("任务链接指向不存在的阶段")
        unit_pairs = [(link.stage_id, link.unit_id) for link in self.unit_links]
        if len(set(unit_pairs)) != len(unit_pairs):
            raise ValidationAppError("同一阶段内单元重复链接")
        if len({link.unit_id for link in self.unit_links}) != len(self.unit_links):
            raise ValidationAppError("单元在计划内不可重复挂载")


@dataclass(slots=True)
class PlanDraft:
    """规划草案：Graph 产物，等待用户确认。

    ``content_hash`` 用于确认时校验「用户看到的就是要发布的」，
    避免确认期间草案被后台改写。
    """

    draft_id: str
    project_id: str
    run_id: str
    goal_snapshot: str
    revision_candidate: int
    stages: tuple[PlanStage, ...] = ()
    unit_refs: tuple[str, ...] = ()          # 有序的 unit stable_key
    task_refs: tuple[str, ...] = ()          # 有序的 task stable_key
    node_stable_keys: tuple[str, ...] = ()
    practice_project_idea: str = ""
    status: PlanDraftStatus = PlanDraftStatus.AWAITING_APPROVAL
    validation_warnings: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def content_hash(self) -> str:
        """内容指纹。忽略 run_id / 时间戳等易变字段。"""
        return content_hash_stable(
            {
                "project_id": self.project_id,
                "goal_snapshot": self.goal_snapshot,
                "revision_candidate": self.revision_candidate,
                "stages": [
                    {
                        "stable_key": s.stable_key,
                        "title": s.title,
                        "section_kind": str(s.section_kind),
                        "order_index": s.order_index,
                        "objective": s.objective,
                    }
                    for s in self.stages
                ],
                "unit_refs": list(self.unit_refs),
                "task_refs": list(self.task_refs),
                "node_stable_keys": list(self.node_stable_keys),
                "practice_project_idea": self.practice_project_idea,
            }
        )

    def verify_hash(self, presented_hash: str) -> None:
        if not presented_hash or presented_hash != self.content_hash:
            raise ConflictError(
                "草案内容已变化，请重新加载后再确认",
                reason="draft_hash_mismatch",
            )

    def apply_edit(
        self,
        *,
        goal_snapshot: str | None = None,
        stages: Sequence[PlanStage] | None = None,
    ) -> None:
        """用户编辑草案。编辑后必须重新走一遍校验。"""
        if self.status not in {PlanDraftStatus.AWAITING_APPROVAL, PlanDraftStatus.PENDING}:
            raise ConflictError("当前草案状态不允许编辑")
        if goal_snapshot is not None:
            self.goal_snapshot = goal_snapshot.strip()
        if stages is not None:
            self.stages = tuple(stages)
        self.status = PlanDraftStatus.PENDING


@dataclass(frozen=True, slots=True)
class PublishResult:
    """幂等发布结果。``created=False`` 表示命中已有结果（未重复创建）。"""

    plan_id: str
    revision: int
    created: bool
    structure_fingerprint: str


def _publish_body_fingerprint(draft: PlanDraft) -> str:
    """发布请求的**语义体指纹**。

    同键（idempotency_key）同体 → 复用；同键异体 → 409。
    体 = 草案内容 + 目标项目，不含易变字段（时间、run_id）。
    """
    return content_hash_stable(
        {"project_id": draft.project_id, "draft_hash": draft.content_hash}
    )


class PlanPublicationService:
    """计划的纯逻辑发布协调器。

    本类**不做 I/O**：仓储由 application 层注入实现。
    这样领域规则可以被完整单测，而不需要数据库。

    发布必须**在单一数据库事务内**完成，由应用层包裹
    ``PlanRepositoryPort.publish_revision`` 调用（见 Goal §6）：
    草案状态检查 → 版本检查 → 新建 revision → 关系写入 →
    切换当前引用 → 写发布记录。
    """

    def __init__(self, repository: "PlanRepositoryPort") -> None:  # noqa: F821
        self._repo = repository

    def publish(
        self,
        *,
        draft: PlanDraft,
        presented_hash: str,
        expected_version: int,
        idempotency_key: str,
        now: datetime | None = None,
    ) -> PublishResult:
        """发布草案为正式的当前路线。

        顺序严格按设计文档：
        校验草案 hash + expected_version + 幂等键
        -> 新增 plan revision / links
        -> 设置当前引用（应用层在同一事务内完成）。
        """
        if not idempotency_key:
            raise ValidationAppError("发布必须携带幂等键")

        # 1) 先查幂等键：重复点击/重复投递。
        #    同键同体 → 复用既有结果（重放返回原结果，即使草案已 APPROVED）；
        #    同键异体 → 409。
        body_fp = _publish_body_fingerprint(draft)
        existing = self._repo.find_publish_by_idempotency_key(
            project_id=draft.project_id, idempotency_key=idempotency_key
        )
        if existing is not None:
            if existing.body_fingerprint != body_fp:
                raise IdempotencyConflictError(
                    "同一 Idempotency-Key 已用于不同的发布请求体"
                )
            return PublishResult(
                plan_id=existing.plan_id,
                revision=existing.revision,
                created=False,
                structure_fingerprint=existing.structure_fingerprint,
            )

        # 2) 草案必须处于「可发布」状态：已取消/已失效的草案绝不能发布。
        if draft.status not in {
            PlanDraftStatus.AWAITING_APPROVAL,
            PlanDraftStatus.PENDING,
        }:
            raise ConflictError(
                "当前草案状态不允许发布",
                reason="draft_not_publishable",
                status=str(draft.status),
            )

        # 3) 草案内容必须与用户看到的一致。
        draft.verify_hash(presented_hash)

        # 4) 乐观并发：当前引用版本必须匹配。
        current = self._repo.get_current(project_id=draft.project_id)
        current_version = current.version if current else 0
        if expected_version != current_version:
            raise VersionConflictError(
                "计划已被其他操作修改，请刷新后重试",
                expected_version=expected_version,
                actual_version=current_version,
            )

        # 4) 结构指纹去重：重规划若与当前路线结构一致，不新建版本。
        next_revision = (current.revision if current else 0) + 1
        candidate = PlanRevision.create(
            project_id=draft.project_id,
            revision=next_revision,
            goal_snapshot=draft.goal_snapshot,
            stages=draft.stages,
            now=now,
        )
        if (
            current is not None
            and current.structure_fingerprint() == candidate.structure_fingerprint()
        ):
            draft.status = PlanDraftStatus.APPROVED
            self._repo.save_draft(draft)
            return PublishResult(
                plan_id=current.plan_id,
                revision=current.revision,
                created=False,
                structure_fingerprint=current.structure_fingerprint(),
            )

        # 5) 冻结新版本，并在**单一事务内**写入 revision + 关系 + 切换当前引用 +
        #    发布记录（由应用层包裹 publish_revision 调用）。
        candidate.freeze(now=now)
        self._repo.publish_revision(
            draft=draft,
            revision=candidate,
            superseded=current,
            idempotency_key=idempotency_key,
            body_fingerprint=body_fp,
        )
        draft.status = PlanDraftStatus.APPROVED
        self._repo.save_draft(draft)
        return PublishResult(
            plan_id=candidate.plan_id,
            revision=candidate.revision,
            created=True,
            structure_fingerprint=candidate.structure_fingerprint(),
        )

    def decide_draft(
        self,
        *,
        draft: PlanDraft,
        decision: DraftDecision,
        expected_version: int,
        presented_hash: str = "",
        idempotency_key: str = "",
        edited_stages: Sequence[PlanStage] | None = None,
        now: datetime | None = None,
    ) -> PublishResult | None:
        """处理等待用户时的三种决定：approve / edit / cancel。

        **非法/缺失决定一律失败，绝不默认 approve**（Goal §3）。
        """
        if draft.status not in {PlanDraftStatus.AWAITING_APPROVAL, PlanDraftStatus.PENDING}:
            raise ConflictError("草案已处理，不能重复决定")

        match decision:
            case DraftDecision.APPROVE:
                if not idempotency_key:
                    raise ValidationAppError("approve 必须携带幂等键")
                return self.publish(
                    draft=draft,
                    presented_hash=presented_hash,
                    expected_version=expected_version,
                    idempotency_key=idempotency_key,
                    now=now,
                )
            case DraftDecision.EDIT:
                if edited_stages is None:
                    raise ValidationAppError("edit 必须携带修改后的阶段列表")
                draft.apply_edit(stages=edited_stages)
                self._repo.save_draft(draft)
                # 编辑后必须重新校验：调用方（应用层）随后重新入队 validate。
                return None
            case DraftDecision.CANCEL:
                draft.status = PlanDraftStatus.CANCELLED
                self._repo.save_draft(draft)
                # 取消后的草案绝不可被 worker 稍后发布：保存须按状态过滤。
                return None
            case _:  # pragma: no cover - 枚举已封闭
                raise ValidationAppError(f"未知决定：{decision}")


@dataclass(frozen=True, slots=True)
class PublishRecord:
    """已落库的发布记录（幂等复用 + 体指纹比对）。"""

    plan_id: str
    revision: int
    idempotency_key: str
    body_fingerprint: str
    structure_fingerprint: str


class PlanRepositoryPort(Protocol):
    """规划仓储端口。实现见 infrastructure；契约测试同时覆盖内存与 PG。

    事务契约（Goal §6）：

    - ``publish_revision`` 必须在**单一事务**内完成：
      草案状态检查 → 版本检查 → 新建 PlanRevision → 写入 unit/task 关系 →
      切换当前引用 → 更新被替代版本状态 → 写发布记录。
      任何一步失败整体回滚，不得留下半发布状态。
    - 幂等靠 **DB 唯一约束**（``(project_id, idempotency_key)``），
      不得用「先查后写」伪造并发幂等。
    - ``PlanRevision`` 一旦 APPROVED/SUPERSEDED **不可变**；
      重规划**不得删除**历史 summary/outcome/learning_record。
    """

    def get_current(self, *, project_id: str) -> PlanRevision | None: ...

    def get_revision(self, *, project_id: str, revision: int) -> PlanRevision | None: ...

    def list_revisions(self, *, project_id: str) -> list[PlanRevision]: ...

    def publish_revision(
        self,
        *,
        draft: PlanDraft,
        revision: PlanRevision,
        superseded: PlanRevision | None,
        idempotency_key: str,
        body_fingerprint: str,
    ) -> None: ...

    def set_current(self, *, project_id: str, plan_id: str) -> None: ...

    def get_draft(self, *, project_id: str, draft_id: str) -> PlanDraft | None: ...

    def save_draft(self, draft: PlanDraft) -> None:
        """保存草案。实现**必须按状态过滤**：已 CANCELLED 的草案不得被覆盖为可发布。"""
        ...

    def find_publish_by_idempotency_key(
        self, *, project_id: str, idempotency_key: str
    ) -> PublishRecord | None: ...


def diff_revisions(previous: PlanRevision, current: PlanRevision) -> dict[str, object]:
    """对比两个版本，输出面向 UI 的结构化差异。

    局部重规划后用于回答「哪些阶段/单元被保留」。完全按 ``stable_key`` 匹配，
    不按标题模糊匹配——这是设计文档的硬要求。
    """
    prev_keys = {s.stable_key for s in previous.stages}
    curr_keys = {s.stable_key for s in current.stages}
    prev_units = {link.unit_id for link in previous.unit_links}
    curr_units = {link.unit_id for link in current.unit_links}
    return {
        "from_revision": previous.revision,
        "to_revision": current.revision,
        "stages_added": sorted(curr_keys - prev_keys),
        "stages_removed": sorted(prev_keys - curr_keys),
        "stages_kept": sorted(curr_keys & prev_keys),
        "units_kept": sorted(curr_units & prev_units),
        "units_added": sorted(curr_units - prev_units),
        "units_removed": sorted(prev_units - curr_units),
        "goal_changed": previous.goal_snapshot != current.goal_snapshot,
    }


def validate_soft_limits(
    *,
    unit_count: int,
    node_count: int,
    task_count: int,
) -> list[str]:
    """数量软上限：超限返回警告，不阻断发布。"""
    warnings: list[str] = []
    if unit_count > SOFT_LIMIT_UNITS:
        warnings.append(f"单元数量 {unit_count} 超过建议上限 {SOFT_LIMIT_UNITS}，建议合并或延后")
    if node_count > SOFT_LIMIT_NODES:
        warnings.append(f"知识节点数量 {node_count} 超过建议上限 {SOFT_LIMIT_NODES}")
    if task_count > SOFT_LIMIT_TASKS:
        warnings.append(f"实践任务数量 {task_count} 超过建议上限 {SOFT_LIMIT_TASKS}")
    return warnings


def require_found(value: object | None, message: str) -> None:
    if value is None:
        raise NotFoundError(message)


__all__ = [
    "SOFT_LIMIT_NODES",
    "SOFT_LIMIT_TASKS",
    "SOFT_LIMIT_UNITS",
    "PlanDraft",
    "PlanPublicationService",
    "PlanRepositoryPort",
    "PlanRevision",
    "PlanStage",
    "PlanTaskLink",
    "PlanUnitLink",
    "PublishRecord",
    "PublishResult",
    "diff_revisions",
    "validate_soft_limits",
]
