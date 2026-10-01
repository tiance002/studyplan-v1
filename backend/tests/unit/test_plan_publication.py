"""计划发布与事务一致性（Goal §6）。

覆盖：
- 同键同体 → 复用原结果，不重复发布
- 同键异体 → 409 idempotency_conflict
- 已取消 / 已失效草案 → 不发布
- hash 不匹配 → 不发布
- expected_version 不匹配 → 不覆盖
- 重复确认（不同 idempotency_key，同一草案）→ 结构指纹去重，不产生两份计划
- 发布必须在单一事务内完成（仓储端口契约）
- PlanRevision 冻结后不可变；重规划不得删除历史
"""

from __future__ import annotations

from dataclasses import replace

import pytest
from app.core.errors import (
    ConflictError,
    IdempotencyConflictError,
    ValidationAppError,
    VersionConflictError,
)
from app.domain.enums import (
    DraftDecision,
    OutlineSectionKind,
    PlanDraftStatus,
    PlanRevisionStatus,
    StageResourceRole,
    TaskKnowledgeRole,
)
from app.domain.planning.models import (
    PlanDraft,
    PlanPublicationService,
    PlanRepositoryPort,
    PlanRevision,
    PlanStage,
    PlanTaskKnowledgeLink,
    PlanTaskLink,
    PlanUnitLink,
    PublishRecord,
    revision_from_draft,
)
from app.domain.resources.curation import (
    KnowledgeExtension,
    StageResourceAssignment,
)

# --------------------------------------------------------------------------- fake repo


class FakePlanRepository(PlanRepositoryPort):
    """内存实现。以单事务语义模拟 ``publish_revision``（原子）。

    B2-V §二：模拟真实 PG 的**事务内草案状态复核**——
    发布前从 ``self.drafts`` 读**数据库里的**状态，而不是信任调用方对象。
    """

    def __init__(self) -> None:
        self.current: PlanRevision | None = None
        self.revisions: list[PlanRevision] = []
        self.drafts: dict[str, PlanDraft] = {}
        self.publish_records: dict[tuple[str, str], PublishRecord] = {}
        self.call_log: list[str] = []
        self.fail_on: str | None = None

    def get_current(self, *, project_id: str) -> PlanRevision | None:
        return self.current

    def get_revision(self, *, project_id: str, revision: int) -> PlanRevision | None:
        return next((r for r in self.revisions if r.revision == revision), None)

    def list_revisions(self, *, project_id: str) -> list[PlanRevision]:
        return list(self.revisions)

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
        """模拟**单一事务**：任何一步失败整体回滚，不留半发布状态。

        B1.2 §三 修复：回滚必须**同时恢复被替代版本的状态**。旧实现在
        ``publish_record`` 失败时已经调用过 ``mark_superseded()``，回滚却只删
        新版本，导致既有 v1 被**错误地**留在 ``SUPERSEDED``。这正是真实
        PG 实现必须避免的陷阱（发布与草案状态更新同属一个事务）。

        B2-V §二：事务内**复核数据库中的草案状态**（``self.drafts``）；
        B2-V §四：``created=False``（复用当前版本）也必须落库幂等记录。
        """
        record_key = (draft.project_id, idempotency_key)
        # 事务开始前快照全部受影响状态。
        snap_revisions = list(self.revisions)
        snap_current = self.current
        snap_record = self.publish_records.get(record_key)
        snap_superseded_status = superseded.status if superseded is not None else None
        # 真实流程中草案在发布前必然已落库；fake 对未登记的草案做等价隐式落库
        # （状态取「等待确认」，即服务发布前库里应有的状态），使单元测试聚焦领域
        # 规则（真实的「草案不存在」路径由 PG 测试覆盖）。
        seeded = False
        if draft.draft_id not in self.drafts:
            self.drafts[draft.draft_id] = replace(
                draft, status=PlanDraftStatus.AWAITING_APPROVAL
            )
            seeded = True
        stored = self.drafts[draft.draft_id]
        snap_draft_status = stored.status

        log: list[str] = ["begin"]
        try:
            # 0) 事务内复核草案最新状态（不信任调用方持有的旧对象）。
            if stored.status not in {
                PlanDraftStatus.AWAITING_APPROVAL,
                PlanDraftStatus.PENDING,
            }:
                log.append("check_draft(FAIL:not_publishable)")
                raise ConflictError(
                    "草案已被取消或已处理，不能再发布",
                    reason="draft_not_publishable",
                    status=str(stored.status),
                )
            log.append("check_draft")

            if created:
                if self.fail_on == "revision":
                    log.append("insert_revision(FAIL)")
                    raise RuntimeError("boom")
                log.append("insert_revision")
                self.revisions.append(revision)
                if superseded is not None:
                    log.append("mark_superseded")
                    superseded.mark_superseded()

            if self.fail_on == "publish_record":
                log.append("insert_record(FAIL)")
                raise RuntimeError("boom")
            log.append("insert_record")
            self.publish_records[record_key] = PublishRecord(
                plan_id=revision.plan_id,
                revision=revision.revision,
                idempotency_key=idempotency_key,
                body_fingerprint=body_fingerprint,
                structure_fingerprint=revision.structure_fingerprint(),
            )
            if self.fail_on == "draft_status":
                # 草案状态更新也在发布事务内（B1.2 §三）。
                log.append("update_draft_status(FAIL)")
                raise RuntimeError("boom")
            log.append("update_draft_status")
            stored.status = PlanDraftStatus.APPROVED
            if self.fail_on == "set_current":
                log.append("set_current(FAIL)")
                raise RuntimeError("boom")
            log.append("set_current")
            if created:
                self.current = revision
        except Exception:
            # 回滚：恢复**全部**状态，包括被替代版本的状态与当前引用。
            self.revisions = snap_revisions
            self.current = snap_current
            if snap_record is None:
                self.publish_records.pop(record_key, None)
            else:
                self.publish_records[record_key] = snap_record
            if superseded is not None and snap_superseded_status is not None:
                superseded.status = snap_superseded_status
            stored.status = snap_draft_status
            if seeded:
                self.drafts.pop(draft.draft_id, None)
            log.append("rollback")
            raise
        finally:
            self.call_log.append(",".join(log))

    def set_current(self, *, project_id: str, plan_id: str) -> None:
        pass

    def get_draft(self, *, project_id: str, draft_id: str) -> PlanDraft | None:
        return self.drafts.get(draft_id)

    def _require_version(self, expected_version: int | None) -> None:
        actual = self.current.version if self.current else 0
        if expected_version is not None and expected_version != actual:
            raise VersionConflictError("stale version", expected_version=expected_version, actual_version=actual)

    def save_draft(self, draft: PlanDraft, *, expected_hash: str | None = None,
                   expected_version: int | None = None, write_fence=None) -> None:
        self._require_version(expected_version)
        # 契约：终态（cancelled / approved）草案不得被改写（B2-V §二.4）。
        existing = self.drafts.get(draft.draft_id)
        if existing is not None and existing.status in {
            PlanDraftStatus.CANCELLED,
            PlanDraftStatus.APPROVED,
        }:
            raise ConflictError(
                "草案已终结（已取消或已发布），不能再修改",
                reason="draft_terminal",
            )
        self.drafts[draft.draft_id] = draft

    def cancel_draft(self, *, project_id: str, draft_id: str,
                     expected_hash: str | None = None, expected_version: int | None = None) -> None:
        self._require_version(expected_version)
        stored = self.drafts.get(draft_id)
        if stored is None or stored.status not in {
            PlanDraftStatus.AWAITING_APPROVAL,
            PlanDraftStatus.PENDING,
        }:
            raise ConflictError(
                "草案已处理（已取消或已发布），不能再取消",
                reason="draft_not_cancellable",
            )
        stored.status = PlanDraftStatus.CANCELLED

    def find_publish_by_idempotency_key(
        self, *, project_id: str, idempotency_key: str
    ) -> PublishRecord | None:
        return self.publish_records.get((project_id, idempotency_key))


# --------------------------------------------------------------------------- helpers


def _make_stages(n: int = 2) -> tuple[PlanStage, ...]:
    return tuple(
        PlanStage.create(
            stable_key=f"stage-{i}",
            title=f"阶段 {i}",
            section_kind=OutlineSectionKind.FOUNDATION,
            order_index=i,
        )
        for i in range(n)
    )


def _make_draft(*, project_id: str = "prj_1", stages: tuple[PlanStage, ...] | None = None) -> PlanDraft:
    return PlanDraft(
        draft_id="drf_1",
        project_id=project_id,
        run_id="run_1",
        goal_snapshot="学会 Python 并做出一个小工具",
        revision_candidate=1,
        stages=stages if stages is not None else _make_stages(),
    )


def _service(repo: FakePlanRepository) -> PlanPublicationService:
    return PlanPublicationService(repo)


# --------------------------------------------------------------------------- tests


def test_approve_publishes_new_revision() -> None:
    repo = FakePlanRepository()
    draft = _make_draft()
    result = _service(repo).publish(
        draft=draft,
        presented_hash=draft.content_hash,
        expected_version=0,
        idempotency_key="key-1",
    )
    assert result.created is True
    assert result.revision == 1
    assert repo.current is not None
    assert repo.current.status is PlanRevisionStatus.APPROVED
    assert draft.status is PlanDraftStatus.APPROVED


def test_repeated_publish_same_key_same_body_reuses_result() -> None:
    repo = FakePlanRepository()
    svc = _service(repo)
    draft = _make_draft()
    r1 = svc.publish(
        draft=draft, presented_hash=draft.content_hash, expected_version=0, idempotency_key="key-1"
    )
    # 第二次：草案已是 APPROVED，但同键同体应命中幂等记录并复用。
    repo.drafts[draft.draft_id] = draft
    r2 = svc.publish(
        draft=draft,
        presented_hash=draft.content_hash,
        expected_version=1,
        idempotency_key="key-1",
    )
    assert r2.created is False
    assert (r2.plan_id, r2.revision) == (r1.plan_id, r1.revision)
    assert len(repo.revisions) == 1
    assert len(repo.publish_records) == 1


def test_repeated_publish_same_key_different_body_is_409() -> None:
    repo = FakePlanRepository()
    svc = _service(repo)
    draft = _make_draft()
    svc.publish(
        draft=draft, presented_hash=draft.content_hash, expected_version=0, idempotency_key="key-1"
    )
    # 同一幂等键，但草案内容不同（改了 goal_snapshot）。
    mutated = _make_draft()
    mutated.goal_snapshot = "完全不同的目标"
    repo.drafts[mutated.draft_id] = mutated
    with pytest.raises(IdempotencyConflictError):
        svc.publish(
            draft=mutated,
            presented_hash=mutated.content_hash,
            expected_version=1,
            idempotency_key="key-1",
        )


def test_cancelled_draft_cannot_publish() -> None:
    repo = FakePlanRepository()
    draft = _make_draft()
    draft.status = PlanDraftStatus.CANCELLED
    repo.drafts[draft.draft_id] = draft
    with pytest.raises(ConflictError) as exc:
        _service(repo).publish(
            draft=draft,
            presented_hash=draft.content_hash,
            expected_version=0,
            idempotency_key="key-1",
        )
    assert exc.value.details.get("reason") == "draft_not_publishable"


def test_hash_mismatch_refuses_publish() -> None:
    repo = FakePlanRepository()
    draft = _make_draft()
    with pytest.raises(ConflictError) as exc:
        _service(repo).publish(
            draft=draft, presented_hash="deadbeef", expected_version=0, idempotency_key="key-1"
        )
    assert exc.value.details.get("reason") == "draft_hash_mismatch"
    assert repo.revisions == []


def test_expected_version_mismatch_does_not_overwrite() -> None:
    repo = FakePlanRepository()
    # 先发布 v1
    d1 = _make_draft()
    _service(repo).publish(
        draft=d1, presented_hash=d1.content_hash, expected_version=0, idempotency_key="k1"
    )
    # 用过期 expected_version 发布新草案
    d2 = _make_draft(stages=_make_stages(3))
    with pytest.raises(VersionConflictError):
        _service(repo).publish(
            draft=d2, presented_hash=d2.content_hash, expected_version=0, idempotency_key="k2"
        )
    assert len(repo.revisions) == 1


def test_reconfirm_same_structure_does_not_create_second_plan() -> None:
    repo = FakePlanRepository()
    svc = _service(repo)
    d1 = _make_draft()
    r1 = svc.publish(
        draft=d1, presented_hash=d1.content_hash, expected_version=0, idempotency_key="k1"
    )
    # 另一个草案，但结构完全相同 → 结构指纹去重
    d2 = _make_draft()
    d2.draft_id = "drf_2"
    r2 = svc.publish(
        draft=d2, presented_hash=d2.content_hash, expected_version=r1.revision, idempotency_key="k2"
    )
    assert r2.created is False
    assert r2.revision == r1.revision
    assert len(repo.revisions) == 1


def test_missing_idempotency_key_fails() -> None:
    repo = FakePlanRepository()
    draft = _make_draft()
    with pytest.raises(ValidationAppError):
        _service(repo).publish(
            draft=draft, presented_hash=draft.content_hash, expected_version=0, idempotency_key=""
        )


def test_publish_is_single_transaction() -> None:
    """发布副作用必须在一次原子调用内完成（含草案状态复核与更新）。"""
    repo = FakePlanRepository()
    draft = _make_draft()
    _service(repo).publish(
        draft=draft, presented_hash=draft.content_hash, expected_version=0, idempotency_key="k1"
    )
    assert repo.call_log == [
        "begin,check_draft,insert_revision,insert_record,update_draft_status,set_current"
    ]


@pytest.mark.parametrize(
    "stage", ["revision", "publish_record", "draft_status", "set_current"]
)
def test_publish_failure_rolls_back(stage: str) -> None:
    """首次发布（无 v1）中途失败 -> 全或无，不留半发布状态。"""
    repo = FakePlanRepository()
    repo.fail_on = stage
    draft = _make_draft()
    with pytest.raises(RuntimeError):
        _service(repo).publish(
            draft=draft, presented_hash=draft.content_hash, expected_version=0, idempotency_key="k1"
        )
    # 全或无：不得留下半发布状态
    assert repo.revisions == []
    assert repo.publish_records == {}
    assert repo.current is None
    assert repo.call_log[-1].endswith("rollback")


@pytest.mark.parametrize(
    "stage", ["revision", "publish_record", "draft_status", "set_current"]
)
def test_publish_v2_failure_keeps_v1_current_and_not_superseded(stage: str) -> None:
    """B1.2 §三：**已有 v1、发布 v2 中途失败**必须整体回滚。

    关键断言：v1 仍是**当前**版本且**不得被错误地标记为 SUPERSEDED**。
    （旧实现在 ``publish_record`` 失败前已 ``mark_superseded``，回滚却只删新版本，
    导致 v1 被留在错误的 SUPERSEDED 状态 —— 这是本测试要钉死的缺陷。）
    """
    repo = FakePlanRepository()
    svc = _service(repo)
    d1 = _make_draft()
    r1 = svc.publish(
        draft=d1, presented_hash=d1.content_hash, expected_version=0, idempotency_key="k1"
    )
    assert repo.current is not None and repo.current.revision == 1

    # 发布 v2 时在指定阶段失败
    repo.fail_on = stage
    d2 = _make_draft(stages=_make_stages(3))
    d2.draft_id = "drf_2"
    with pytest.raises(RuntimeError):
        svc.publish(
            draft=d2,
            presented_hash=d2.content_hash,
            expected_version=r1.revision,
            idempotency_key="k2",
        )

    # v2 未产生；v1 仍是当前，且状态未被错误改写
    assert len(repo.revisions) == 1, "失败的 v2 不得留下任何版本"
    v1 = repo.revisions[0]
    assert v1.revision == 1
    assert v1.status is PlanRevisionStatus.APPROVED, "v1 不得被错误标记为 SUPERSEDED"
    assert repo.current is v1, "当前引用必须仍是 v1"
    assert repo.publish_records.get(("prj_1", "k2")) is None, "失败的发布不得留下幂等记录"
    # 失败后 v1 仍可被幂等复用
    again = svc.publish(
        draft=d1, presented_hash=d1.content_hash, expected_version=0, idempotency_key="k1"
    )
    assert again.created is False and again.revision == 1


def test_publish_record_fields_are_consistent_with_revision() -> None:
    """统一字段语义：幂等键 / 请求体指纹 / 发布记录必须与已发布版本一致。"""
    repo = FakePlanRepository()
    draft = _make_draft()
    result = _service(repo).publish(
        draft=draft, presented_hash=draft.content_hash, expected_version=0, idempotency_key="k-1"
    )
    record = repo.publish_records[("prj_1", "k-1")]
    assert record.idempotency_key == "k-1"
    assert record.plan_id == result.plan_id
    assert record.revision == result.revision
    assert record.structure_fingerprint == result.structure_fingerprint
    assert record.body_fingerprint, "发布记录必须保存请求体指纹（同键异体判定依据）"


def test_frozen_revision_is_immutable() -> None:
    revision = PlanRevision.create(
        project_id="prj_1", revision=1, goal_snapshot="目标", stages=_make_stages()
    )
    revision.freeze()
    assert revision.is_frozen is True
    # 冻结后 status 为 APPROVED，且没有可变更结构的公开入口
    assert revision.status is PlanRevisionStatus.APPROVED


def test_replanning_keeps_previous_revision_history() -> None:
    """重规划不得删除历史版本。"""
    repo = FakePlanRepository()
    svc = _service(repo)
    d1 = _make_draft()
    svc.publish(draft=d1, presented_hash=d1.content_hash, expected_version=0, idempotency_key="k1")
    d2 = _make_draft(stages=_make_stages(3))
    d2.draft_id = "drf_2"
    svc.publish(draft=d2, presented_hash=d2.content_hash, expected_version=1, idempotency_key="k2")
    assert len(repo.revisions) == 2
    assert repo.revisions[0].status is PlanRevisionStatus.SUPERSEDED
    assert repo.revisions[1].status is PlanRevisionStatus.APPROVED
    assert repo.current is repo.revisions[1]


def test_decide_approve_requires_idempotency_key() -> None:
    repo = FakePlanRepository()
    draft = _make_draft()
    with pytest.raises(ValidationAppError):
        _service(repo).decide_draft(
            draft=draft, decision=DraftDecision.APPROVE, expected_version=0, idempotency_key=""
        )


def test_decide_edit_requires_stages() -> None:
    repo = FakePlanRepository()
    draft = _make_draft()
    with pytest.raises(ValidationAppError):
        _service(repo).decide_draft(
            draft=draft, decision=DraftDecision.EDIT, expected_version=0
        )


def test_decide_cancel_marks_draft_cancelled_and_cannot_publish() -> None:
    repo = FakePlanRepository()
    draft = _make_draft()
    repo.drafts[draft.draft_id] = draft
    result = _service(repo).decide_draft(
        draft=draft, decision=DraftDecision.CANCEL, expected_version=0
    )
    assert result is None
    assert draft.status is PlanDraftStatus.CANCELLED
    # 取消后 worker 再尝试发布 → 失败
    with pytest.raises(ConflictError):
        _service(repo).publish(
            draft=draft,
            presented_hash=draft.content_hash,
            expected_version=0,
            idempotency_key="k9",
        )


def test_decide_edit_applies_and_saves_without_publishing() -> None:
    repo = FakePlanRepository()
    draft = _make_draft()
    repo.drafts[draft.draft_id] = draft
    result = _service(repo).decide_draft(
        draft=draft,
        decision=DraftDecision.EDIT,
        expected_version=0,
        presented_hash=draft.content_hash,
        edited_stages=_make_stages(4),
    )
    assert result is None
    assert len(draft.stages) == 4
    assert draft.status is PlanDraftStatus.PENDING
    assert repo.revisions == []


# ---------------------------------------------------------------------------
# B2-C P1-01：发布必须携带**完整结构**（单元/任务/资源/扩展）
# ---------------------------------------------------------------------------


def _linked_draft(
    *, project_id: str = "prj_1", stages: tuple[PlanStage, ...] | None = None
) -> PlanDraft:
    """构造带完整发布结构的草案（单元/任务链接 + 阶段资源主线 + 扩展知识）。"""
    stgs = stages if stages is not None else _make_stages(2)
    s0, s1 = stgs[0], stgs[1]
    return PlanDraft(
        draft_id="drf_linked",
        project_id=project_id,
        run_id="run_1",
        goal_snapshot="学会 Python 并做出一个小工具",
        revision_candidate=1,
        stages=stgs,
        unit_refs=("u_basic", "u_rag"),
        task_refs=("t_pdf",),
        node_stable_keys=("n_python", "n_rag"),
        unit_links=(
            PlanUnitLink(stage_id=s0.stage_id, unit_id="unt_basic", order_index=0),
            PlanUnitLink(stage_id=s1.stage_id, unit_id="unt_rag", order_index=0),
        ),
        task_links=(PlanTaskLink(stage_id=s1.stage_id, task_id="ptk_pdf", order_index=0),),
        stage_resources=(
            StageResourceAssignment.create(
                project_id=project_id,
                plan_id="",
                stage_id=s0.stage_id,
                role=StageResourceRole.PRIMARY,
                source_ref="src_1",
                section_refs=("sec_1", "sec_2"),
            ),
        ),
        extensions=(
            KnowledgeExtension.create(
                project_id=project_id,
                plan_id="",
                stage_id=s1.stage_id,
                topic="SQLite/PostgreSQL/MySQL 认识与对比",
                concepts=("基本特点", "典型适用场景"),
                guidance="了解基本特点及典型适用场景",
                search_hints=("关系型数据库对比 入门",),
                thinking_prompts=("多人同时写入？", "是否需要独立服务？"),
            ),
        ),
        source_pack_key="agent_app_dev",
        source_pack_version=1,
    )


def test_publish_carries_unit_and_task_links_and_snapshot() -> None:
    """P1-01 RED：发布的 PlanRevision 必须包含单元/任务链接、资源与扩展快照。"""
    repo = FakePlanRepository()
    draft = _linked_draft()
    _service(repo).publish(
        draft=draft,
        presented_hash=draft.content_hash,
        expected_version=0,
        idempotency_key="k1",
    )
    rev = repo.current
    assert rev is not None
    assert len(rev.unit_links) == 2, "发布丢失了学习单元链接"
    assert len(rev.task_links) == 1, "发布丢失了实践任务链接"
    assert len(rev.stage_resources) == 1, "发布丢失了阶段资源主线快照"
    assert len(rev.extensions) == 1, "发布丢失了扩展知识快照"
    assert rev.source_pack_key == "agent_app_dev"


def test_structure_fingerprint_covers_full_route() -> None:
    """P1-01 RED：结构指纹必须覆盖完整路线（仅改单元链接也应判为不同结构）。"""
    repo = FakePlanRepository()
    svc = _service(repo)
    d1 = _linked_draft()
    r1 = svc.publish(
        draft=d1, presented_hash=d1.content_hash, expected_version=0, idempotency_key="k1"
    )
    # 复用同一批阶段（同一 stage_id），仅改动单元链接目标。
    d2 = _linked_draft(stages=d1.stages)
    d2.draft_id = "drf_linked2"
    d2.unit_links = (
        PlanUnitLink(stage_id=d1.stages[0].stage_id, unit_id="unt_other", order_index=0),
        d1.unit_links[1],
    )
    r2 = svc.publish(
        draft=d2,
        presented_hash=d2.content_hash,
        expected_version=r1.revision,
        idempotency_key="k2",
    )
    assert r2.created is True, "仅单元链接变化也必须新建版本（指纹必须覆盖完整路线）"
    assert r2.revision == 2


def test_draft_hash_covers_resources_and_extensions() -> None:
    """P1-01 RED：草案哈希必须覆盖资源主线与扩展知识。"""
    d1 = _linked_draft()
    d2 = _linked_draft(stages=d1.stages)
    d2.extensions = ()
    assert d1.content_hash != d2.content_hash, "草案哈希必须覆盖扩展知识"
    d3 = _linked_draft(stages=d1.stages)
    d3.stage_resources = ()
    assert d1.content_hash != d3.content_hash, "草案哈希必须覆盖阶段资源主线"


# ---------------------------------------------------------------------------
# B2-V §二：发布原子性 —— 事务内复核草案状态、状态条件更新、复用也落幂等
# ---------------------------------------------------------------------------


def test_stale_object_publish_after_cancel_is_rejected() -> None:
    """B2-V §二.2/.3：调用方持有的**旧对象**不得让已取消的草案被发布。

    调用方对象仍是 AWAITING_APPROVAL，但数据库里已是 CANCELLED；
    仓储必须在事务内复核数据库状态并拒绝，且**不产生任何版本**。
    """
    repo = FakePlanRepository()
    draft = _make_draft()
    # 模拟「另一个请求已取消该草案」：库里是 CANCELLED，调用方对象是陈旧的。
    cancelled = _make_draft()
    cancelled.status = PlanDraftStatus.CANCELLED
    repo.drafts[draft.draft_id] = cancelled
    assert draft.status is PlanDraftStatus.AWAITING_APPROVAL, "调用方对象必须仍是陈旧状态"

    with pytest.raises(ConflictError) as exc:
        _service(repo).publish(
            draft=draft,
            presented_hash=draft.content_hash,
            expected_version=0,
            idempotency_key="k-stale",
        )
    assert exc.value.details.get("reason") == "draft_not_publishable"
    assert repo.revisions == [], "被取消的草案绝不可产生版本"
    assert repo.publish_records == {}, "被拒绝的发布不得留下幂等记录"


def test_publish_rechecks_draft_from_store_not_caller_object() -> None:
    """事务内出现 check_draft 步骤（不信任调用方持有的旧对象）。"""
    repo = FakePlanRepository()
    draft = _make_draft()
    _service(repo).publish(
        draft=draft, presented_hash=draft.content_hash, expected_version=0, idempotency_key="k1"
    )
    assert "check_draft" in repo.call_log[0].split(",")
    # 发布后库里的草案必须是 APPROVED（终态更新属于发布事务）。
    stored = repo.drafts[draft.draft_id]
    assert stored.status is PlanDraftStatus.APPROVED


def test_reuse_path_persists_idempotency_record() -> None:
    """B2-V §四：结构与当前路线一致而**复用**时，幂等结果仍须落库。"""
    repo = FakePlanRepository()
    svc = _service(repo)
    d1 = _make_draft()
    svc.publish(draft=d1, presented_hash=d1.content_hash, expected_version=0, idempotency_key="k1")

    d2 = _make_draft()  # 结构完全相同
    d2.draft_id = "drf_2"
    r2 = svc.publish(
        draft=d2, presented_hash=d2.content_hash, expected_version=1, idempotency_key="k2"
    )
    assert r2.created is False and r2.revision == 1
    assert len(repo.revisions) == 1, "复用不得新建版本"
    assert ("prj_1", "k2") in repo.publish_records, "复用也必须持久化幂等结果"
    assert repo.publish_records[("prj_1", "k2")].revision == 1


def test_reuse_then_replay_returns_original_without_republishing() -> None:
    """复用落库后，同键重放必须直接命中记录（不再进入发布分支）。"""
    repo = FakePlanRepository()
    svc = _service(repo)
    d1 = _make_draft()
    r1 = svc.publish(
        draft=d1, presented_hash=d1.content_hash, expected_version=0, idempotency_key="k1"
    )
    d2 = _make_draft()
    d2.draft_id = "drf_2"
    r2 = svc.publish(
        draft=d2, presented_hash=d2.content_hash, expected_version=1, idempotency_key="k2"
    )
    calls_after_first = len(repo.call_log)
    r3 = svc.publish(
        draft=d2, presented_hash=d2.content_hash, expected_version=1, idempotency_key="k2"
    )
    assert (r3.plan_id, r3.revision, r3.created) == (r1.plan_id, r1.revision, False)
    assert (r2.plan_id, r2.revision) == (r1.plan_id, r1.revision)
    assert len(repo.call_log) == calls_after_first, "重放不得再次进入发布事务"


def test_historical_idempotency_replayable_after_later_publish() -> None:
    """B2-V §四：后续版本发布后，历史幂等结果仍可重放。"""
    repo = FakePlanRepository()
    svc = _service(repo)
    d1 = _linked_draft()
    r1 = svc.publish(
        draft=d1, presented_hash=d1.content_hash, expected_version=0, idempotency_key="k1"
    )
    d2 = _linked_draft(stages=_make_stages(3))
    d2.draft_id = "drf_2"
    r2 = svc.publish(
        draft=d2, presented_hash=d2.content_hash, expected_version=1, idempotency_key="k2"
    )
    assert r2.revision == 2

    replay = svc.publish(
        draft=d1, presented_hash=d1.content_hash, expected_version=1, idempotency_key="k1"
    )
    assert (replay.plan_id, replay.revision, replay.created) == (
        r1.plan_id,
        r1.revision,
        False,
    ), "历史幂等结果必须仍可重放"


# ---------------------------------------------------------------------------
# B2-V §三：唯一的版本构造入口 + 指纹摆脱数据库 ID
# ---------------------------------------------------------------------------


def test_same_route_with_different_stage_ids_has_same_fingerprint() -> None:
    """同一路由、不同 stage_id → **同一**结构指纹（指纹不得依赖 DB ID）。"""
    d1 = _linked_draft()
    d2 = _linked_draft(stages=_make_stages(2))  # 全新 stage_id，语义相同
    assert {s.stage_id for s in d1.stages}.isdisjoint({s.stage_id for s in d2.stages})
    r1 = revision_from_draft(d1, revision=1)
    r2 = revision_from_draft(d2, revision=2)
    assert r1.structure_fingerprint() == r2.structure_fingerprint()
    assert d1.content_hash == d2.content_hash, "草案哈希同样不得依赖 DB ID"


def test_build_revision_snapshot_remaps_all_references() -> None:
    """唯一的转换入口必须把链接/资源/扩展全部重映射到新 stage_id。"""
    draft = _linked_draft()
    rev = revision_from_draft(draft, revision=1)
    old_ids = {s.stage_id for s in draft.stages}
    new_ids = {s.stage_id for s in rev.stages}
    assert old_ids.isdisjoint(new_ids), "新版本必须生成独立 stage_id"
    assert {x.stage_id for x in rev.unit_links} <= new_ids
    assert {x.stage_id for x in rev.task_links} <= new_ids
    assert {a.stage_id for a in rev.stage_resources} <= new_ids
    assert {e.stage_id for e in rev.extensions} <= new_ids
    # 稳定语义原样保留
    assert [x.unit_id for x in rev.unit_links] == [x.unit_id for x in draft.unit_links]
    assert [x.task_id for x in rev.task_links] == [x.task_id for x in draft.task_links]


def test_consecutive_versions_have_distinct_stage_ids() -> None:
    """连续两版不得复用 stage_id（``plan_stages.stage_id`` 是全局主键）。"""
    draft = _linked_draft()
    v1 = revision_from_draft(draft, revision=1)
    v2 = revision_from_draft(draft, revision=2)
    assert {s.stage_id for s in v1.stages}.isdisjoint({s.stage_id for s in v2.stages})
    assert v1.structure_fingerprint() == v2.structure_fingerprint(), (
        "两版结构相同 → 指纹相同（stage_id 不参与指纹）"
    )


def test_production_publish_uses_single_conversion_entry() -> None:
    """生产发布路径必须经由 ``revision_from_draft``：发布版本的 stage_id 全新。"""
    repo = FakePlanRepository()
    draft = _linked_draft()
    _service(repo).publish(
        draft=draft, presented_hash=draft.content_hash, expected_version=0, idempotency_key="k1"
    )
    published = repo.current
    assert published is not None
    assert {s.stage_id for s in published.stages}.isdisjoint({s.stage_id for s in draft.stages})


def test_only_mainline_resource_change_creates_new_version() -> None:
    """仅主线资源变化 → 必须新建版本（指纹覆盖资源主线）。"""
    repo = FakePlanRepository()
    svc = _service(repo)
    d1 = _linked_draft()
    r1 = svc.publish(
        draft=d1, presented_hash=d1.content_hash, expected_version=0, idempotency_key="k1"
    )
    d2 = _linked_draft(stages=d1.stages)
    d2.draft_id = "drf_r2"
    d2.stage_resources = (
        StageResourceAssignment.create(
            project_id=d2.project_id,
            stage_id=d1.stages[0].stage_id,
            role=StageResourceRole.PRIMARY,
            source_ref="src_other",
            section_refs=("sec_9",),
        ),
    )
    r2 = svc.publish(
        draft=d2, presented_hash=d2.content_hash, expected_version=r1.revision, idempotency_key="k2"
    )
    assert r2.created is True and r2.revision == 2


def test_only_extension_change_creates_new_version() -> None:
    """仅扩展知识变化 → 必须新建版本（指纹覆盖扩展）。"""
    repo = FakePlanRepository()
    svc = _service(repo)
    d1 = _linked_draft()
    r1 = svc.publish(
        draft=d1, presented_hash=d1.content_hash, expected_version=0, idempotency_key="k1"
    )
    d2 = _linked_draft(stages=d1.stages)
    d2.draft_id = "drf_e2"
    d2.extensions = (
        KnowledgeExtension.create(
            project_id=d2.project_id,
            stage_id=d1.stages[1].stage_id,
            topic="完全不同的扩展主题",
            guidance="换一个方向",
        ),
    )
    r2 = svc.publish(
        draft=d2, presented_hash=d2.content_hash, expected_version=r1.revision, idempotency_key="k2"
    )
    assert r2.created is True and r2.revision == 2


# ---------------------------------------------------------------------------
# B2-V §四：哈希覆盖全部用户可见字段
# ---------------------------------------------------------------------------


def _base_kwargs(**overrides: object) -> dict[str, object]:
    draft = _linked_draft()
    return {
        "draft_id": "drf_h",
        "project_id": draft.project_id,
        "run_id": "run_1",
        "goal_snapshot": draft.goal_snapshot,
        "revision_candidate": 1,
        "stages": draft.stages,
        "unit_links": draft.unit_links,
        "task_links": draft.task_links,
        "task_knowledge_links": draft.task_knowledge_links,
        "stage_resources": draft.stage_resources,
        "extensions": draft.extensions,
        "source_pack_key": draft.source_pack_key,
        "source_pack_version": draft.source_pack_version,
        **overrides,
    }


def test_hash_covers_fallback_search_terms() -> None:
    """无核验链接时的搜索建议也是用户可见内容，必须进哈希。"""
    stage_id = _linked_draft().stages[0].stage_id
    base = PlanDraft(**_base_kwargs())  # type: ignore[arg-type]
    with_terms = PlanDraft(
        **_base_kwargs(
            stage_resources=(
                StageResourceAssignment.create(
                    project_id="prj_1",
                    stage_id=stage_id,
                    role=StageResourceRole.PRIMARY,
                    fallback_search_terms=("关系型数据库 入门",),
                ),
            )
        )  # type: ignore[arg-type]
    )
    assert base.content_hash != with_terms.content_hash


def test_hash_covers_extension_required_and_unit_id() -> None:
    stage_id = _linked_draft().stages[1].stage_id
    plain = PlanDraft(**_base_kwargs())  # type: ignore[arg-type]
    flagged = PlanDraft(
        **_base_kwargs(
            extensions=(
                KnowledgeExtension.create(
                    project_id="prj_1",
                    stage_id=stage_id,
                    topic="SQLite/PostgreSQL/MySQL 认识与对比",
                    concepts=("基本特点", "典型适用场景"),
                    guidance="了解基本特点及典型适用场景",
                    required=True,
                    unit_id="unt_rag",
                ),
            )
        )  # type: ignore[arg-type]
    )
    assert plain.content_hash != flagged.content_hash


def test_hash_covers_task_knowledge_links() -> None:
    base = PlanDraft(**_base_kwargs())  # type: ignore[arg-type]
    linked = PlanDraft(
        **_base_kwargs(
            task_knowledge_links=(
                PlanTaskKnowledgeLink.create(
                    task_id="ptk_pdf", node_id="n_rag", role=TaskKnowledgeRole.SUPPORTING
                ),
            )
        )  # type: ignore[arg-type]
    )
    assert base.content_hash != linked.content_hash


def test_hash_covers_mainline_section_order() -> None:
    """主线章节**顺序**变化必须改变哈希（顺序是用户可见语义）。"""
    stage_id = _linked_draft().stages[0].stage_id

    def _res(refs: tuple[str, ...]) -> StageResourceAssignment:
        return StageResourceAssignment.create(
            project_id="prj_1",
            stage_id=stage_id,
            role=StageResourceRole.PRIMARY,
            source_ref="src_1",
            section_refs=refs,
        )

    a = PlanDraft(**_base_kwargs(stage_resources=(_res(("sec_1", "sec_2")),)))  # type: ignore[arg-type]
    b = PlanDraft(**_base_kwargs(stage_resources=(_res(("sec_2", "sec_1")),)))  # type: ignore[arg-type]
    assert a.content_hash != b.content_hash


def test_structure_fingerprint_and_draft_hash_share_semantics() -> None:
    """结构指纹与草案哈希必须覆盖同一组结构字段（不会一个有一个没有）。"""
    draft = _linked_draft()
    rev = revision_from_draft(draft, revision=1)

    def _mutate(d: PlanDraft) -> PlanDraft:
        d.extensions = ()
        return d

    assert _mutate(_linked_draft(stages=draft.stages)).content_hash != draft.content_hash
    assert (
        revision_from_draft(_mutate(_linked_draft(stages=draft.stages)), revision=1)
        .structure_fingerprint()
        != rev.structure_fingerprint()
    )
