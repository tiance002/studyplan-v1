"""planning 领域：草案、计划版本、阶段、局部改动与幂等发布。

核心不变量（SOFTWARE_DESIGN.md §3）：
1. 草案**永不**直接覆盖正式路线；只有用户确认的 ``PlanRevision`` 是当前路线。
2. 已确认结构**不可变**：任何改动产生新的 revision。
3. 同项目内 ``revision`` 序号唯一。
4. 「当前版本」由显式引用决定，**不得**取最大版本号（未确认草案可能版本更高）。
5. 发布必须校验草案 hash + expected_version + 幂等键，且重复确认不产生两份计划。
6. 局部重规划按 ``stable_key`` 精确映射，不依据相近标题自动合并历史。

## B2-V §三：唯一的「草案 → 版本快照」入口

``plan_stages.stage_id`` 是**全局主键**，因此每个新版本必须**重新生成** stage_id，
并按稳定语义把 ``unit_links`` / ``task_links`` / ``stage_resources`` /
``extensions`` / ``task_knowledge_links`` 重映射到新阶段。
本模块只提供**一个**转换入口 :func:`build_revision_snapshot`（草案版包装
:func:`revision_from_draft`），生产路径与测试**必须**共用它——
禁止各自实现一套版本构造逻辑，否则「同路由不同 ID」会产生不同的结构指纹。

## B2-V §四：指纹只依赖**稳定语义字段**，不依赖数据库 ID

``content_hash`` 与 ``structure_fingerprint`` 都把 ``stage_id`` 解析为
``stable_key`` 后再入哈希，因此「同一路由、不同 stage_id」得到同一指纹。
两者覆盖**全部发布结构**：阶段、单元/任务链接、任务-知识链接、主线资源
（含 ``fallback_search_terms``）、扩展知识（含 ``required``/``unit_id``）、
领域包版本。
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
    TaskKnowledgeRole,
)
from app.domain.resources.curation import (
    KnowledgeExtension,
    StageResourceAssignment,
    validate_extension_soft_limit,
    validate_extensions,
    validate_mainline_continuity,
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


@dataclass(frozen=True, slots=True)
class PlanTaskKnowledgeLink:
    """任务 -> 知识节点关联（B2-V §四）。

    ``role`` 只表达强度（core / supporting / extension），
    **不**表达掌握程度，也不会因为任务完成而自动给节点打掌握标签。
    与 :class:`PlanTaskLink` 一致，``task_id`` / ``node_id`` 都是既有实体的 ID。
    """

    task_id: str
    node_id: str
    role: TaskKnowledgeRole = TaskKnowledgeRole.CORE

    @staticmethod
    def create(
        *, task_id: str, node_id: str, role: TaskKnowledgeRole = TaskKnowledgeRole.CORE
    ) -> "PlanTaskKnowledgeLink":
        if not task_id or not node_id:
            raise ValidationAppError("任务知识关联的 task_id 与 node_id 均不能为空")
        return PlanTaskKnowledgeLink(task_id=task_id, node_id=node_id, role=role)


def _stage_key_index(stages: Sequence[PlanStage]) -> dict[str, str]:
    """``stage_id -> stable_key``。指纹据此**摆脱数据库 ID**（B2-V §三）。"""
    return {s.stage_id: s.stable_key for s in stages}


def _stages_payload(stages: Sequence[PlanStage]) -> list[dict[str, object]]:
    return [
        {
            "stable_key": s.stable_key,
            "title": s.title,
            "section_kind": str(s.section_kind),
            "order_index": s.order_index,
            "objective": s.objective,
        }
        for s in stages
    ]


def _structure_payload(
    *,
    stages: Sequence[PlanStage],
    unit_links: Sequence[PlanUnitLink],
    task_links: Sequence[PlanTaskLink],
    task_knowledge_links: Sequence[PlanTaskKnowledgeLink],
    stage_resources: Sequence[StageResourceAssignment],
    extensions: Sequence[KnowledgeExtension],
) -> dict[str, object]:
    """**共享**的发布结构语义快照（B2-V §四：两处指纹必须语义一致）。

    草案哈希与版本指纹都调用本函数，因此不可能出现「一个覆盖了某字段、
    另一个没有」的分叉。``stage_id`` 统一解析为 ``stable_key``。
    """
    key = _stage_key_index(stages)

    def _k(stage_id: str) -> str:
        return key.get(stage_id, stage_id)

    return {
        "unit_links": [
            {"stage": _k(x.stage_id), "unit_id": x.unit_id, "order_index": x.order_index}
            for x in unit_links
        ],
        "task_links": [
            {"stage": _k(x.stage_id), "task_id": x.task_id, "order_index": x.order_index}
            for x in task_links
        ],
        "task_knowledge_links": [
            {"task_id": x.task_id, "node_id": x.node_id, "role": str(x.role)}
            for x in task_knowledge_links
        ],
        "stage_resources": [
            {
                "stage": _k(a.stage_id),
                "role": str(a.role),
                "source_ref": a.source_ref,
                "section_refs": list(a.section_refs),
                "order_index": a.order_index,
                "source_version": a.source_version,
                # B2-V §四：搜索建议也是用户可见内容，必须进指纹。
                "fallback_search_terms": list(a.fallback_search_terms),
            }
            for a in stage_resources
        ],
        "extensions": [
            {
                "stage": _k(e.stage_id),
                "topic": e.topic,
                "concepts": list(e.concepts),
                "guidance": e.guidance,
                "links": list(e.links),
                "search_hints": list(e.search_hints),
                "thinking_prompts": list(e.thinking_prompts),
                # B2-V §四：required / unit_id 影响用户看到的结构，必须进指纹。
                "required": e.required,
                "unit_id": e.unit_id,
                "order_index": e.order_index,
            }
            for e in extensions
        ],
    }


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
    #: 任务 → 知识节点关联（B2-V §四：属于发布结构，必须进指纹）。
    task_knowledge_links: tuple[PlanTaskKnowledgeLink, ...] = ()
    #: 阶段主线/补充/对照资源快照（V1.2 §2.2）。
    stage_resources: tuple[StageResourceAssignment, ...] = ()
    #: 规划阶段预置的扩展知识与思考提示（V1.2 §2.1）。
    extensions: tuple[KnowledgeExtension, ...] = ()
    #: 来源领域包/模板版本（共享模板预留，V1 只记录）。
    source_pack_key: str = ""
    source_pack_version: int = 0
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
        task_knowledge_links: Sequence[PlanTaskKnowledgeLink] = (),
        stage_resources: Sequence[StageResourceAssignment] = (),
        extensions: Sequence[KnowledgeExtension] = (),
        source_pack_key: str = "",
        source_pack_version: int = 0,
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
            task_knowledge_links=tuple(task_knowledge_links),
            stage_resources=tuple(stage_resources),
            extensions=tuple(extensions),
            source_pack_key=source_pack_key.strip(),
            source_pack_version=source_pack_version,
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

    def validation_warnings(self) -> list[str]:
        """**软上限**警告（不阻断发布）：每阶段扩展主题条数（设计 §2.1）。

        与 :meth:`_validate_structure` 的硬错误分开：软上限只提示，
        不得因为「想好看」而删掉必要内容。
        """
        return validate_extension_soft_limit(self.extensions)

    def structure_fingerprint(self) -> str:
        """结构指纹：用于判断「同一草案重复确认」与「重规划是否实质变化」。

        **必须覆盖全部发布结构**（B2-C §3.1 / B2-V §三 §四）：阶段 + 单元/任务
        链接 + 任务-知识链接 + 阶段资源主线 + 扩展知识 + 领域包版本。
        否则「只改了单元/资源/扩展」的草案会被误判为「结构相同」而不新建版本。

        **只依赖稳定语义字段**：``stage_id`` 一律解析为 ``stable_key``，
        因此「同一路由、不同 stage_id」得到**同一**指纹（B2-V §三）。
        """
        return content_hash(
            {
                "project_id": self.project_id,
                "goal_snapshot": self.goal_snapshot,
                "stages": _stages_payload(self.stages),
                **_structure_payload(
                    stages=self.stages,
                    unit_links=self.unit_links,
                    task_links=self.task_links,
                    task_knowledge_links=self.task_knowledge_links,
                    stage_resources=self.stage_resources,
                    extensions=self.extensions,
                ),
                "source_pack_key": self.source_pack_key,
                "source_pack_version": self.source_pack_version,
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
        for assignment in self.stage_resources:
            if assignment.stage_id not in stage_ids:
                raise ValidationAppError("阶段资源分配指向不存在的阶段")
        for extension in self.extensions:
            if extension.stage_id not in stage_ids:
                raise ValidationAppError("扩展知识指向不存在的阶段")
        unit_pairs = [(link.stage_id, link.unit_id) for link in self.unit_links]
        if len(set(unit_pairs)) != len(unit_pairs):
            raise ValidationAppError("同一阶段内单元重复链接")
        if len({link.unit_id for link in self.unit_links}) != len(self.unit_links):
            raise ValidationAppError("单元在计划内不可重复挂载")
        task_pairs = [(link.stage_id, link.task_id) for link in self.task_links]
        if len(set(task_pairs)) != len(task_pairs):
            raise ValidationAppError("同一阶段内任务重复链接")
        if len({link.task_id for link in self.task_links}) != len(self.task_links):
            raise ValidationAppError("任务在计划内不可重复挂载")

        # 任务-知识链接：任务必须已被本计划挂载；同一 (task,node) 不可重复。
        planned_tasks = {link.task_id for link in self.task_links}
        seen_tk: set[tuple[str, str]] = set()
        for tk in self.task_knowledge_links:
            if tk.task_id not in planned_tasks:
                raise ValidationAppError("任务知识关联指向未挂载的任务")
            pair = (tk.task_id, tk.node_id)
            if pair in seen_tk:
                raise ValidationAppError("同一任务对同一知识节点重复关联")
            seen_tk.add(pair)

        # 扩展绑定的单元必须是**本计划**已挂载的单元（B2-V §五：禁止绑错单元）。
        planned_units = {link.unit_id for link in self.unit_links}
        for extension in self.extensions:
            if extension.unit_id and extension.unit_id not in planned_units:
                raise ValidationAppError("扩展知识绑定了本计划未挂载的学习单元")

        # V1.2 §2.1 确定性校验（硬错误，阻断发布）：
        # 主线数量 / 连续章节顺序 / 扩展结构安全。**不做**任何重复率计算。
        mainline_errors = validate_mainline_continuity(self.stage_resources)
        if mainline_errors:
            raise ValidationAppError("；".join(mainline_errors))
        extension_errors = validate_extensions(self.extensions)
        if extension_errors:
            raise ValidationAppError("；".join(extension_errors))


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
    #: 完整发布结构（B2-C §3.1）：阶段→单元/任务链接、资源主线、扩展知识。
    #: publish 必须把这些**全部**传入 PlanRevision，否则会丢失学习单元/实践关联。
    unit_links: tuple[PlanUnitLink, ...] = ()
    task_links: tuple[PlanTaskLink, ...] = ()
    #: 任务 → 知识节点关联（B2-V §四）。
    task_knowledge_links: tuple[PlanTaskKnowledgeLink, ...] = ()
    stage_resources: tuple[StageResourceAssignment, ...] = ()
    extensions: tuple[KnowledgeExtension, ...] = ()
    source_pack_key: str = ""
    source_pack_version: int = 0
    practice_project_idea: str = ""
    status: PlanDraftStatus = PlanDraftStatus.AWAITING_APPROVAL
    validation_warnings: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def content_hash(self) -> str:
        """内容指纹。忽略 run_id / 时间戳等易变字段。

        **覆盖全部发布结构**（B2-C §3.1 / B2-V §四）：阶段 + 单元/任务链接 +
        任务-知识链接 + 阶段资源主线（含搜索建议）+ 扩展知识（含 required /
        unit_id）+ 领域包版本。用户确认的 hash 因此代表「将要发布的完整路线」，
        而不是只有阶段标题。

        与 :meth:`PlanRevision.structure_fingerprint` 共用同一份结构载荷，
        保证两处语义**不会分叉**；``stage_id`` 一律解析为 ``stable_key``。
        """
        return content_hash_stable(
            {
                "project_id": self.project_id,
                "goal_snapshot": self.goal_snapshot,
                "revision_candidate": self.revision_candidate,
                "stages": _stages_payload(self.stages),
                "unit_refs": list(self.unit_refs),
                "task_refs": list(self.task_refs),
                "node_stable_keys": list(self.node_stable_keys),
                **_structure_payload(
                    stages=self.stages,
                    unit_links=self.unit_links,
                    task_links=self.task_links,
                    task_knowledge_links=self.task_knowledge_links,
                    stage_resources=self.stage_resources,
                    extensions=self.extensions,
                ),
                "source_pack_key": self.source_pack_key,
                "source_pack_version": self.source_pack_version,
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


# --------------------------------------------------------------------------- 版本构造
# B2-V §三：**唯一**的「草案/结构 → 版本快照」入口。生产路径与测试必须共用。


def build_revision_snapshot(
    *,
    project_id: str,
    revision: int,
    goal_snapshot: str,
    stages: Sequence[PlanStage],
    unit_links: Sequence[PlanUnitLink] = (),
    task_links: Sequence[PlanTaskLink] = (),
    task_knowledge_links: Sequence[PlanTaskKnowledgeLink] = (),
    stage_resources: Sequence[StageResourceAssignment] = (),
    extensions: Sequence[KnowledgeExtension] = (),
    source_pack_key: str = "",
    source_pack_version: int = 0,
    now: datetime | None = None,
) -> PlanRevision:
    """把「阶段 + 引用」构造为一个**独立**的新版本快照（B2-V §三）。

    ``plan_stages.stage_id`` 是**全局主键**，因此这里**总是重新生成** stage_id，
    并按「旧 stage_id → 新 stage_id」重映射所有引用该阶段的结构：

    - ``unit_links`` / ``task_links``（阶段 → 单元/任务）
    - ``stage_resources``（阶段主线/补充资源快照）
    - ``extensions``（阶段扩展知识）

    链接的**稳定语义**（unit_id / task_id / source_ref / section_refs /
    topic / fallback_search_terms ...）原样保留，因此：

    - 结构指纹不受 ID 变化影响（「同路由不同 ID」→ 同指纹）；
    - 连续两版不会因复用旧 stage_id 触发主键冲突。

    返回的版本**未冻结**；由调用方决定是否 :meth:`PlanRevision.freeze`。
    """
    new_stages = tuple(
        PlanStage.create(
            stable_key=s.stable_key,
            title=s.title,
            section_kind=s.section_kind,
            order_index=s.order_index,
            objective=s.objective,
        )
        for s in stages
    )
    remap = {old.stage_id: new.stage_id for old, new in zip(stages, new_stages, strict=True)}

    def _sid(stage_id: str) -> str:
        return remap.get(stage_id, stage_id)

    return PlanRevision.create(
        project_id=project_id,
        revision=revision,
        goal_snapshot=goal_snapshot,
        stages=new_stages,
        unit_links=tuple(
            PlanUnitLink(stage_id=_sid(x.stage_id), unit_id=x.unit_id, order_index=x.order_index)
            for x in unit_links
        ),
        task_links=tuple(
            PlanTaskLink(stage_id=_sid(x.stage_id), task_id=x.task_id, order_index=x.order_index)
            for x in task_links
        ),
        task_knowledge_links=tuple(
            PlanTaskKnowledgeLink(task_id=x.task_id, node_id=x.node_id, role=x.role)
            for x in task_knowledge_links
        ),
        stage_resources=tuple(
            StageResourceAssignment.create(
                project_id=project_id,
                stage_id=_sid(a.stage_id),
                role=a.role,
                source_ref=a.source_ref,
                section_refs=a.section_refs,
                order_index=a.order_index,
                source_version=a.source_version,
                fallback_search_terms=a.fallback_search_terms,
            )
            for a in stage_resources
        ),
        extensions=tuple(
            KnowledgeExtension.create(
                project_id=project_id,
                stage_id=_sid(e.stage_id),
                topic=e.topic,
                concepts=e.concepts,
                guidance=e.guidance,
                links=e.links,
                search_hints=e.search_hints,
                thinking_prompts=e.thinking_prompts,
                required=e.required,
                order_index=e.order_index,
                unit_id=e.unit_id,
            )
            for e in extensions
        ),
        source_pack_key=source_pack_key,
        source_pack_version=source_pack_version,
        now=now,
    )


def revision_from_draft(
    draft: PlanDraft, *, revision: int, now: datetime | None = None
) -> PlanRevision:
    """草案 → 版本快照的**唯一**入口（B2-V §三）。"""
    return build_revision_snapshot(
        project_id=draft.project_id,
        revision=revision,
        goal_snapshot=draft.goal_snapshot,
        stages=draft.stages,
        unit_links=draft.unit_links,
        task_links=draft.task_links,
        task_knowledge_links=draft.task_knowledge_links,
        stage_resources=draft.stage_resources,
        extensions=draft.extensions,
        source_pack_key=draft.source_pack_key,
        source_pack_version=draft.source_pack_version,
        now=now,
    )


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
        校验幂等键 / 草案 hash / expected_version
        -> 由**唯一入口** :func:`revision_from_draft` 构造候选版本
        -> 在**单一事务**内写入 revision + 关系 + 切换当前引用 + 更新草案状态
        + 写发布记录（由 ``PlanRepositoryPort.publish_revision`` 完成）。

        **B2-V §二**：草案状态的终态更新**属于发布事务**，本方法**不再**在
        发布成功后额外调用 ``save_draft``（那会产生「已发布但草案仍可发布」
        的窗口，且失败时留下半发布状态）。仓储在事务内从数据库**复核**草案
        最新状态，因此调用方持有的过期对象不会被信任。

        **B2-V §四**：即使结构与当前路线一致（复用、``created=False``），
        也**必须**落库幂等结果，否则同键重放会再次走到发布分支。
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

        # 2) 草案必须处于「可发布」状态：已取消/已失效/已处理的草案绝不能发布。
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

        # 5) 结构指纹去重：重规划若与当前路线结构一致，不新建版本。
        next_revision = (current.revision if current else 0) + 1
        candidate = revision_from_draft(draft, revision=next_revision, now=now)
        # 草案期的资源/扩展 plan_id 为空，发布时绑定到新版本。
        if candidate.stage_resources:
            candidate.stage_resources = tuple(
                a.bound_to_plan(candidate.plan_id) for a in candidate.stage_resources
            )
        if candidate.extensions:
            candidate.extensions = tuple(
                e.bound_to_plan(candidate.plan_id) for e in candidate.extensions
            )
        if (
            current is not None
            and current.structure_fingerprint() == candidate.structure_fingerprint()
        ):
            # 复用当前版本：**仍要**把幂等结果落库（B2-V §四），
            # 否则同键重放找不到记录会再次进入发布分支。
            draft.status = PlanDraftStatus.APPROVED
            self._repo.publish_revision(
                draft=draft,
                revision=current,
                superseded=None,
                idempotency_key=idempotency_key,
                body_fingerprint=body_fp,
                created=False,
            )
            return PublishResult(
                plan_id=current.plan_id,
                revision=current.revision,
                created=False,
                structure_fingerprint=current.structure_fingerprint(),
            )

        # 6) 冻结新版本，并在**单一事务内**写入 revision + 关系 + 切换当前引用 +
        #    更新草案状态 + 发布记录（由 ``publish_revision`` 完成）。
        candidate.freeze(now=now)
        draft.status = PlanDraftStatus.APPROVED
        self._repo.publish_revision(
            draft=draft,
            revision=candidate,
            superseded=current,
            idempotency_key=idempotency_key,
            body_fingerprint=body_fp,
            created=True,
        )
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

        **不在此处做统一的"草案已处理"前置检查**：每个分支都有自己的权威判定，
        且顺序至关重要——

        - ``approve`` 交给 :meth:`publish`，而 ``publish`` **最先**检查幂等键。
          若在此处先拦「草案已处理」，则「同一幂等键的重复确认」会被误判成
          409，而不是按 §四 返回**原始结果**（重放必须可复现）。
        - ``edit`` 由 :meth:`PlanDraft.apply_edit` 按状态拒绝。
        - ``cancel`` 由 ``cancel_draft`` 的**状态条件**更新拒绝。
        """
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
                # 取消走**状态条件**更新：若草案已被发布（approved），
                # 仓储会抛 ConflictError，**不会**把已发布版本对应的草案改坏。
                self._repo.cancel_draft(
                    project_id=draft.project_id, draft_id=draft.draft_id
                )
                draft.status = PlanDraftStatus.CANCELLED
                # 取消后的草案绝不可被 worker 稍后发布：保存与发布都按状态过滤。
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

    事务契约（Goal §6 / B1.2 §三）：

    - ``publish_revision`` 必须在**单一事务**内完成，且**草案状态更新也属于
      该事务**：草案状态检查 → 版本检查 → 新建 PlanRevision → 写入 unit/task
      关系 → 切换当前引用 → 更新被替代版本状态 → 更新草案状态 → 写发布记录。
      任何一步失败整体回滚，**不得留下半发布状态**，尤其**不得把被替代版本
      错误地留在 SUPERSEDED**（回滚必须恢复其原状态）。
    - 幂等靠 **DB 唯一约束**（``(project_id, idempotency_key)``），
      不得用「先查后写」伪造并发幂等。
    - ``PlanRevision`` 一旦 APPROVED/SUPERSEDED **不可变**；
      重规划**不得删除**历史 summary/outcome/learning_record。

    字段语义（三处必须一致，不得各说各话）：

    - **幂等键** ``idempotency_key``：调用方提供的操作键，与 ``project_id``
      组成唯一约束；同一键的重复请求返回**同一结果**。
    - **请求体指纹** ``body_fingerprint``：发布请求的语义指纹（草案内容）。
      同键同体 → 复用；同键异体 → 409 ``idempotency_conflict``。
    - **发布记录** :class:`PublishRecord`：落库的发布事实，含 ``plan_id`` /
      ``revision`` / ``idempotency_key`` / ``body_fingerprint`` /
      ``structure_fingerprint``。它是幂等复用与体比对的**唯一依据**。
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
        created: bool = True,
    ) -> None:
        """**单事务**落定一次发布（B2-V §二）。

        ``created=True``：新建版本（写 revision + 阶段/链接/资源/扩展 +
        切换当前引用 + 草案状态 + 发布记录）。
        ``created=False``：结构与当前路线一致而**复用**当前版本；此时
        ``revision`` 即当前版本、``superseded`` 必须为 ``None``，实现**只**
        更新草案状态并写发布记录（B2-V §四：复用也必须持久化幂等结果）。

        无论哪种情形，实现都**必须**在事务内：

        1. 从数据库**复核**草案最新状态（``SELECT ... FOR UPDATE``），
           不得信任调用方持有的旧对象；
        2. 用**状态条件**更新草案为 ``approved`` 并**检查受影响行数**，
           行数不为 1 即整体回滚；
        3. 被取消 / 已处理的草案一律拒绝。
        """
        ...

    def set_current(self, *, project_id: str, plan_id: str) -> None: ...

    def get_draft(self, *, project_id: str, draft_id: str) -> PlanDraft | None: ...

    def save_draft(self, draft: PlanDraft) -> None:
        """保存草案。实现**必须按状态条件**更新并**检查受影响行数**：

        - 已 ``cancelled`` 的草案不得被覆盖为可发布（设计 §3 C6）；
        - 已 ``approved`` 的草案不得被再次改写（否则会与已发布版本脱节）；
        - 行数为 0（被条件挡下）时**必须抛** :class:`ConflictError`，
          而不是静默忽略——调用方需要知道这次写入没有生效。
        """
        ...

    def cancel_draft(self, *, project_id: str, draft_id: str) -> None:
        """把草案置为 ``cancelled``（**状态条件**更新，行数为 0 即抛冲突）。

        与 :meth:`publish_revision` 并发时由行锁串行化：谁先拿到行谁生效，
        另一方必须失败，**不得**出现「已发布却被取消」或「已取消却被发布」。
        """
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
    "PlanTaskKnowledgeLink",
    "PlanTaskLink",
    "PlanUnitLink",
    "PublishRecord",
    "PublishResult",
    "build_revision_snapshot",
    "diff_revisions",
    "revision_from_draft",
    "validate_soft_limits",
]
