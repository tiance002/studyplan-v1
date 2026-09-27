"""reflections 领域：单元总结、评审与修订历史。

核心约束：
- 用户**先**写，模型随后依据单元目标提出缺口与引导问题。
- 原文与反馈**不可变**：每次修订产生新的 attempt + review，不覆盖历史。
- 评审结论只说明「本次提交与 rubric 的符合情况」，
  **不**自动改变单元进度，**不**自动标记任务通过。
- 每次修订是独立的 run，图不会挂起数月。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.core.errors import ConflictError, ValidationAppError
from app.core.ids import content_hash, new_id
from app.domain.enums import ReviewerKind, SummaryReviewConclusion

MIN_SUMMARY_CHARS = 50
MAX_SUMMARY_CHARS = 20_000


@dataclass(frozen=True, slots=True)
class RubricSnapshot:
    """评审依据的快照：必须连同 rubric_version 一起保存。

    这样「新 rubric 改动后旧总结仍保留」是可解释的：
    旧结论只对旧版本负责，不宣称已满足新目标。
    """

    unit_id: str
    unit_stable_key: str
    rubric_version: int
    objectives: tuple[str, ...]
    rubric: dict[str, object]

    @staticmethod
    def from_unit_snapshot(snapshot: dict[str, object]) -> "RubricSnapshot":
        return RubricSnapshot(
            unit_id=str(snapshot["unit_id"]),
            unit_stable_key=str(snapshot["stable_key"]),
            rubric_version=int(snapshot["rubric_version"]),  # type: ignore[arg-type]
            objectives=tuple(str(o) for o in snapshot.get("objectives", ())),  # type: ignore[arg-type]
            rubric=dict(snapshot.get("rubric", {})),  # type: ignore[arg-type]
        )


@dataclass(slots=True)
class SummaryAttempt:
    """用户提交的一次总结原文（不可变内容 + 追加序号）。"""

    attempt_id: str
    unit_id: str
    project_id: str
    content: str
    attempt_no: int
    rubric_version: int
    run_id: str | None
    created_at: datetime
    content_hash: str = ""

    @staticmethod
    def create(
        *,
        unit_id: str,
        project_id: str,
        content: str,
        attempt_no: int,
        rubric_version: int,
        run_id: str | None = None,
        now: datetime | None = None,
    ) -> "SummaryAttempt":
        normalized = _normalize_summary(content)
        return SummaryAttempt(
            attempt_id=new_id("sum"),
            unit_id=unit_id,
            project_id=project_id,
            content=normalized,
            attempt_no=attempt_no,
            rubric_version=rubric_version,
            run_id=run_id,
            created_at=now or datetime.now(timezone.utc),
            content_hash=content_hash({"content": normalized}),
        )


@dataclass(frozen=True, slots=True)
class SummaryReview:
    """对一次 attempt 的评审结果（不可变）。"""

    review_id: str
    attempt_id: str
    unit_id: str
    conclusion: SummaryReviewConclusion
    covered: tuple[str, ...]
    gaps: tuple[str, ...]
    misconceptions: tuple[str, ...]
    questions: tuple[str, ...]
    rubric_version: int
    reviewer_kind: ReviewerKind
    run_id: str
    created_at: datetime

    @staticmethod
    def create(
        *,
        attempt_id: str,
        unit_id: str,
        conclusion: SummaryReviewConclusion,
        covered: list[str] | tuple[str, ...] = (),
        gaps: list[str] | tuple[str, ...] = (),
        misconceptions: list[str] | tuple[str, ...] = (),
        questions: list[str] | tuple[str, ...] = (),
        rubric_version: int,
        reviewer_kind: ReviewerKind = ReviewerKind.MODEL,
        run_id: str = "",
        now: datetime | None = None,
    ) -> "SummaryReview":
        return SummaryReview(
            review_id=new_id("srv"),
            attempt_id=attempt_id,
            unit_id=unit_id,
            conclusion=conclusion,
            covered=_clean(covered),
            gaps=_clean(gaps),
            misconceptions=_clean(misconceptions),
            questions=_clean(questions),
            rubric_version=rubric_version,
            reviewer_kind=reviewer_kind,
            run_id=run_id,
            created_at=now or datetime.now(timezone.utc),
        )

    @property
    def is_satisfied(self) -> bool:
        return self.conclusion is SummaryReviewConclusion.SATISFIED


@dataclass(slots=True)
class SummaryThread:
    """一个单元下的全部尝试与评审。

    ``next_attempt_no`` 由已有尝试数决定，防止「重试多写」——
    序号单调递增，重复提交走幂等键而非新序号。
    """

    unit_id: str
    project_id: str
    attempts: list[SummaryAttempt] = field(default_factory=list)
    reviews_by_attempt: dict[str, list[SummaryReview]] = field(default_factory=dict)

    @property
    def attempt_count(self) -> int:
        return len(self.attempts)

    def next_attempt_no(self) -> int:
        return self.attempt_count + 1

    def add_attempt(self, attempt: SummaryAttempt) -> None:
        expected = self.next_attempt_no()
        if attempt.attempt_no != expected:
            raise ConflictError(
                "总结序号不连续，可能有并发提交",
                expected=expected,
                actual=attempt.attempt_no,
            )
        if any(a.content_hash == attempt.content_hash for a in self.attempts):
            raise ConflictError("相同内容的总结已提交过，请修改后再提交")
        self.attempts.append(attempt)

    def attach_review(self, review: SummaryReview) -> None:
        if not any(a.attempt_id == review.attempt_id for a in self.attempts):
            raise ValidationAppError("评审指向不存在的总结尝试")
        bucket = self.reviews_by_attempt.setdefault(review.attempt_id, [])
        if any(r.review_id == review.review_id for r in bucket):
            return
        bucket.append(review)

    def latest_review(self) -> SummaryReview | None:
        if not self.attempts:
            return None
        latest = max(self.attempts, key=lambda a: a.attempt_no)
        reviews = self.reviews_by_attempt.get(latest.attempt_id, [])
        return reviews[-1] if reviews else None


def evaluate_review_completeness(review: SummaryReview) -> list[str]:
    """校验评审输出是否完整。

    模型返回空 gaps/questions 时不应直接判为 satisfied——
    至少要求给出 covered 与其中一类引导内容，否则视为无效评审。
    """
    problems: list[str] = []
    if not review.covered and not review.gaps:
        problems.append("评审既未说明覆盖内容，也未指出缺口")
    if review.conclusion is SummaryReviewConclusion.MISCONCEPTION and not review.misconceptions:
        problems.append("结论为 misconception 但未列出具体误解")
    if review.conclusion is SummaryReviewConclusion.NEEDS_REVISION and not (review.gaps or review.questions):
        problems.append("结论为 needs_revision 但未给出缺口或引导问题")
    return problems


def _normalize_summary(content: str) -> str:
    if not isinstance(content, str):
        raise ValidationAppError("总结内容必须是文本")
    stripped = content.strip()
    if len(stripped) < MIN_SUMMARY_CHARS:
        raise ValidationAppError(f"总结至少需要 {MIN_SUMMARY_CHARS} 个字符")
    if len(stripped) > MAX_SUMMARY_CHARS:
        raise ValidationAppError(f"总结不得超过 {MAX_SUMMARY_CHARS} 个字符")
    return stripped


def _clean(items: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    result: list[str] = []
    for item in items:
        text = str(item).strip()
        if text and text not in result:
            result.append(text)
    return tuple(result)


__all__ = [
    "MAX_SUMMARY_CHARS",
    "MIN_SUMMARY_CHARS",
    "RubricSnapshot",
    "SummaryAttempt",
    "SummaryReview",
    "SummaryThread",
    "evaluate_review_completeness",
]
