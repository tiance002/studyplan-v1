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

import pytest
from app.core.errors import (
    ConflictError,
    IdempotencyConflictError,
    ValidationAppError,
    VersionConflictError,
)
from app.domain.enums import DraftDecision, OutlineSectionKind, PlanDraftStatus, PlanRevisionStatus
from app.domain.planning.models import (
    PlanDraft,
    PlanPublicationService,
    PlanRepositoryPort,
    PlanRevision,
    PlanStage,
    PublishRecord,
)

# --------------------------------------------------------------------------- fake repo


class FakePlanRepository(PlanRepositoryPort):
    """内存实现。以单事务语义模拟 publish_revision（原子）。"""

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
    ) -> None:
        # 模拟单一事务：任何一步失败整体回滚（不产生副作用）。
        log: list[str] = ["begin"]
        try:
            if self.fail_on == "revision":
                log.append("insert_revision(FAIL)")
                raise RuntimeError("boom")
            log.append("insert_revision")
            if superseded is not None:
                log.append("mark_superseded")
            self.revisions.append(revision)
            if superseded is not None:
                superseded.mark_superseded()
            if self.fail_on == "publish_record":
                log.append("insert_record(FAIL)")
                raise RuntimeError("boom")
            log.append("insert_record")
            self.publish_records[(draft.project_id, idempotency_key)] = PublishRecord(
                plan_id=revision.plan_id,
                revision=revision.revision,
                idempotency_key=idempotency_key,
                body_fingerprint=body_fingerprint,
                structure_fingerprint=revision.structure_fingerprint(),
            )
            if self.fail_on == "set_current":
                log.append("set_current(FAIL)")
                raise RuntimeError("boom")
            log.append("set_current")
            self.current = revision
        except Exception:
            # 回滚
            self.revisions = [
                r for r in self.revisions if r.plan_id != revision.plan_id
            ]
            self.publish_records.pop((draft.project_id, idempotency_key), None)
            log.append("rollback")
            raise
        finally:
            self.call_log.append(",".join(log))

    def set_current(self, *, project_id: str, plan_id: str) -> None:
        pass

    def get_draft(self, *, project_id: str, draft_id: str) -> PlanDraft | None:
        return self.drafts.get(draft_id)

    def save_draft(self, draft: PlanDraft) -> None:
        # 契约：已取消的草案不得被覆盖为可发布
        existing = self.drafts.get(draft.draft_id)
        if existing is not None and existing.status is PlanDraftStatus.CANCELLED:
            if draft.status is not PlanDraftStatus.CANCELLED:
                raise ConflictError("已取消的草案不可再发布", reason="draft_cancelled")
        self.drafts[draft.draft_id] = draft

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
    """发布副作用必须在一次原子调用内完成。"""
    repo = FakePlanRepository()
    draft = _make_draft()
    _service(repo).publish(
        draft=draft, presented_hash=draft.content_hash, expected_version=0, idempotency_key="k1"
    )
    assert repo.call_log == ["begin,insert_revision,insert_record,set_current"]


@pytest.mark.parametrize("stage", ["revision", "publish_record", "set_current"])
def test_publish_failure_rolls_back( stage: str) -> None:
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
        edited_stages=_make_stages(4),
    )
    assert result is None
    assert len(draft.stages) == 4
    assert draft.status is PlanDraftStatus.PENDING
    assert repo.revisions == []
