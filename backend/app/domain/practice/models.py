"""practice 领域：实践项目、阶段任务、实现思路修订与成果验收。

核心不变量（见 SOFTWARE_DESIGN.md §3 §8）：

1. ``PracticeProject``（用户拟开发的实际软件）与 ``LearningProject``
   （学习空间）**不是同一概念**，不得互相替代。
2. 一项任务对应**一项可验收交付物**；任务与知识节点多对多，
   但**不自动推断掌握**（``core``/``supporting``/``extension`` 只表达强度）。
3. ``PromptReviewConclusion`` 通过 **不等于** 真实功能验收通过；
   二者是独立的评审链。
4. 证据等级严格区分 ``verified`` / ``reported`` / ``insufficient``；
   **不得**因为"报告写得漂亮"就标 ``verified``。
5. 导出绑定**指定版本**，不覆盖用户初稿。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.core.errors import ConflictError, ValidationAppError
from app.core.ids import content_hash, new_id, require_stable_key, slugify_stable_key
from app.domain.enums import (
    AcceptanceConclusion,
    EvidenceGrade,
    PracticeProjectStatus,
    PracticeTaskStatus,
    ReviewerKind,
    TaskKnowledgeRole,
)

MIN_IDEA_CHARS = 10
MAX_IDEA_CHARS = 4_000
MIN_PROMPT_CHARS = 50
MAX_PROMPT_CHARS = 40_000
MAX_EVIDENCE_ITEMS = 50


@dataclass(slots=True)
class PracticeProject:
    """用户拟开发的实际软件项目。

    与 ``LearningProject`` 的区别：本对象描述"要做的软件"，
    后者描述"在平台上的学习空间"。一个学习空间可以有多个实践项目。
    """

    practice_project_id: str
    project_id: str
    title: str
    idea: str
    status: PracticeProjectStatus = PracticeProjectStatus.IDEA
    repo_url: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 1

    @staticmethod
    def create(
        *,
        project_id: str,
        title: str,
        idea: str,
        repo_url: str | None = None,
        now: datetime | None = None,
    ) -> "PracticeProject":
        _require_text(title, "实践项目标题", max_len=200)
        _require_text(idea, "项目想法", max_len=MAX_IDEA_CHARS, min_len=MIN_IDEA_CHARS)
        moment = now or datetime.now(timezone.utc)
        return PracticeProject(
            practice_project_id=new_id("ppj"),
            project_id=project_id,
            title=title.strip(),
            idea=idea.strip(),
            repo_url=repo_url.strip() if repo_url else None,
            created_at=moment,
            updated_at=moment,
        )

    def attach_repo(self, *, repo_url: str, now: datetime | None = None) -> None:
        """绑定仓库地址。

        注意：这是**用户提供/外部候选**的元数据，
        平台**不会** clone 或执行其中代码（设计 §6 硬约束）。
        """
        _require_text(repo_url, "仓库地址", max_len=500)
        self.repo_url = repo_url.strip()
        self.updated_at = now or datetime.now(timezone.utc)
        self.version += 1

    def transition_to(
        self, target: PracticeProjectStatus, *, now: datetime | None = None
    ) -> None:
        if self.status is PracticeProjectStatus.ARCHIVED:
            raise ConflictError("已归档的实践项目不可再变更状态")
        if target is self.status:
            return
        self.status = target
        self.updated_at = now or datetime.now(timezone.utc)
        self.version += 1


@dataclass(slots=True)
class PracticeTask:
    """一个可验证的实践任务。

    ``in_scope`` / ``out_scope`` / ``acceptance`` 三者缺一不可：
    没有明确"不做什么"和"怎样算完成"的任务无法验收。
    """

    task_id: str
    practice_project_id: str
    project_id: str
    stable_key: str
    title: str
    goal: str
    in_scope: list[str] = field(default_factory=list)
    out_scope: list[str] = field(default_factory=list)
    acceptance: list[str] = field(default_factory=list)
    status: PracticeTaskStatus = PracticeTaskStatus.PENDING
    stage_index: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 1

    @staticmethod
    def create(
        *,
        practice_project_id: str,
        project_id: str,
        title: str,
        goal: str,
        in_scope: list[str] | None = None,
        out_scope: list[str] | None = None,
        acceptance: list[str] | None = None,
        stable_key: str | None = None,
        stage_index: int = 0,
        now: datetime | None = None,
    ) -> "PracticeTask":
        _require_text(title, "任务标题", max_len=200)
        _require_text(goal, "任务目标", max_len=2_000)
        accepted = _clean(acceptance or [])
        if not accepted:
            # 设计 §4 明确把「必填验收标准」列为规划校验项。
            raise ValidationAppError("实践任务必须给出至少一条验收标准")
        return PracticeTask(
            task_id=new_id("ptk"),
            practice_project_id=practice_project_id,
            project_id=project_id,
            stable_key=require_stable_key(
                stable_key or slugify_stable_key(title, fallback_prefix="task")
            ),
            title=title.strip(),
            goal=goal.strip(),
            in_scope=_clean(in_scope or []),
            out_scope=_clean(out_scope or []),
            acceptance=accepted,
            stage_index=stage_index,
            created_at=now or datetime.now(timezone.utc),
        )

    @property
    def can_change_status(self) -> bool:
        return self.status is not PracticeTaskStatus.ACCEPTED

    def transition_to(
        self, target: PracticeTaskStatus, *, source: ReviewerKind = ReviewerKind.SYSTEM
    ) -> None:
        """状态迁移。

        ``ACCEPTED`` **只能**由 ``ReviewerKind.USER`` 或 ``SYSTEM``
        （基于已核验证据）触发，**模型评审不能**直接把任务标为已验收。
        """
        if target is PracticeTaskStatus.ACCEPTED and source is ReviewerKind.MODEL:
            raise ValidationAppError(
                "AI 评审结论不能直接把任务标为已验收；必须由用户确认或系统核验证据"
            )
        if target is self.status:
            return
        self.status = target
        self.version += 1


@dataclass(frozen=True, slots=True)
class TaskKnowledgeLink:
    """任务与知识节点的关系。

    ``role`` 表达**强度**（core/supporting/extension），
    **不**表达掌握程度，也不会因为任务完成而自动给节点打掌握标签。
    """

    task_id: str
    node_id: str
    role: TaskKnowledgeRole = TaskKnowledgeRole.CORE

    @staticmethod
    def create(*, task_id: str, node_id: str, role: TaskKnowledgeRole) -> "TaskKnowledgeLink":
        if not task_id or not node_id:
            raise ValidationAppError("任务知识关联的 task_id 与 node_id 均不能为空")
        return TaskKnowledgeLink(task_id=task_id, node_id=node_id, role=role)


@dataclass(frozen=True, slots=True)
class PromptRevision:
    """用户自己的实现思路修订。原文不可变，每次修订是新记录。"""

    revision_id: str
    task_id: str
    revision_no: int
    user_draft: str
    content_hash: str
    created_at: datetime

    @staticmethod
    def create(
        *,
        task_id: str,
        user_draft: str,
        revision_no: int,
        now: datetime | None = None,
    ) -> "PromptRevision":
        normalized = _normalize_prompt(user_draft)
        return PromptRevision(
            revision_id=new_id("prv"),
            task_id=task_id,
            revision_no=revision_no,
            user_draft=normalized,
            content_hash=content_hash({"draft": normalized}),
            created_at=now or datetime.now(timezone.utc),
        )


@dataclass(frozen=True, slots=True)
class PromptReview:
    """对某次 Prompt 修订的 AI 评审。"""

    review_id: str
    revision_id: str
    task_id: str
    strengths: tuple[str, ...]
    gaps: tuple[str, ...]
    suggestions: tuple[str, ...]
    reviewer_kind: ReviewerKind
    run_id: str
    created_at: datetime

    @staticmethod
    def create(
        *,
        revision_id: str,
        task_id: str,
        strengths: list[str] | None = None,
        gaps: list[str] | None = None,
        suggestions: list[str] | None = None,
        reviewer_kind: ReviewerKind = ReviewerKind.MODEL,
        run_id: str = "",
        now: datetime | None = None,
    ) -> "PromptReview":
        return PromptReview(
            review_id=new_id("prw"),
            revision_id=revision_id,
            task_id=task_id,
            strengths=tuple(_clean(strengths or [])),
            gaps=tuple(_clean(gaps or [])),
            suggestions=tuple(_clean(suggestions or [])),
            reviewer_kind=reviewer_kind,
            run_id=run_id,
            created_at=now or datetime.now(timezone.utc),
        )


@dataclass(frozen=True, slots=True)
class PromptExport:
    """导出的 Prompt。

    ``revision_id`` 指向**确定版本**——导出不影响任何已有修订。
    """

    export_id: str
    task_id: str
    revision_id: str
    export_text: str
    created_at: datetime

    @staticmethod
    def create(
        *,
        task_id: str,
        revision: PromptRevision,
        export_text: str,
        now: datetime | None = None,
    ) -> "PromptExport":
        _require_text(export_text, "导出内容", max_len=MAX_PROMPT_CHARS)
        return PromptExport(
            export_id=new_id("pex"),
            task_id=task_id,
            revision_id=revision.revision_id,
            export_text=export_text.strip(),
            created_at=now or datetime.now(timezone.utc),
        )


@dataclass(frozen=True, slots=True)
class VerificationRecord:
    """**平台真实核验**记录。

    设计 §8 硬约束：只有当平台**亲自执行**了核验（拉取仓库、运行 CI、
    访问可复现产物）并把结果落库后，才能把证据升级为 ``verified``。

    因此本记录**必须**由执行核验的基础设施填写；用户文本、粘贴日志、
    未核验的 commit 哈希、仓库 URL 一律**不能**构造出本记录，也就不能
    冒充 ``verified``。四个字段缺一不可：

    - ``verification_method``: 核验方式（如 ``git_clone``/``ci_run``/``artifact_fetch``）
    - ``verified_at``: 核验发生时间（服务端时钟）
    - ``result``: 核验结果（如 ``ok``/``failed``/``mismatch``）
    - ``evidence_ref``: 指向被核验对象的稳定引用（如 commit sha / 产物 URL）
    """

    verification_method: str
    verified_at: datetime
    result: str
    evidence_ref: str

    @staticmethod
    def create(
        *,
        verification_method: str,
        result: str,
        evidence_ref: str,
        now: datetime | None = None,
    ) -> "VerificationRecord":
        _require_text(verification_method, "核验方式", max_len=100)
        _require_text(result, "核验结果", max_len=100)
        _require_text(evidence_ref, "核验引用", max_len=1_000)
        return VerificationRecord(
            verification_method=verification_method.strip(),
            verified_at=now or datetime.now(timezone.utc),
            result=result.strip(),
            evidence_ref=evidence_ref.strip(),
        )

    @property
    def is_passing(self) -> bool:
        return self.result.strip().lower() in {"ok", "pass", "passed", "success"}


@dataclass(frozen=True, slots=True)
class PracticeSubmission:
    """用户提交的成果证据。"""

    submission_id: str
    task_id: str
    evidence_grade: EvidenceGrade
    evidence: tuple[str, ...]
    note: str
    repo_url: str | None
    created_at: datetime
    verification: VerificationRecord | None = None

    @staticmethod
    def create(
        *,
        task_id: str,
        evidence: list[str] | None = None,
        note: str = "",
        repo_url: str | None = None,
        verification: VerificationRecord | None = None,
        now: datetime | None = None,
    ) -> "PracticeSubmission":
        items = _clean(evidence or [])
        if len(items) > MAX_EVIDENCE_ITEMS:
            raise ValidationAppError(f"证据条目不得超过 {MAX_EVIDENCE_ITEMS} 条")
        if not items and not note.strip():
            raise ValidationAppError("提交必须包含证据或说明")
        # 证据等级由**服务端**判定：**不接受客户端自报**，也不接受
        # 用户文本 / 仓库 URL / 粘贴日志 / 未核验哈希冒充已核验。
        grade = _infer_evidence_grade(items, repo_url, verification)
        return PracticeSubmission(
            submission_id=new_id("psb"),
            task_id=task_id,
            evidence_grade=grade,
            evidence=tuple(items),
            note=note.strip(),
            repo_url=repo_url.strip() if repo_url else None,
            created_at=now or datetime.now(timezone.utc),
            verification=verification,
        )


@dataclass(frozen=True, slots=True)
class AcceptanceReview:
    """对一次提交的验收结论。必须基于证据说明。"""

    review_id: str
    submission_id: str
    task_id: str
    conclusion: AcceptanceConclusion
    rationale: str
    reviewer_kind: ReviewerKind
    created_at: datetime

    @staticmethod
    def create(
        *,
        submission_id: str,
        task_id: str,
        conclusion: AcceptanceConclusion,
        rationale: str,
        reviewer_kind: ReviewerKind,
        now: datetime | None = None,
    ) -> "AcceptanceReview":
        _require_text(rationale, "验收说明", max_len=4_000)
        if (
            conclusion is AcceptanceConclusion.ACCEPTED
            and reviewer_kind is ReviewerKind.MODEL
        ):
            raise ValidationAppError(
                "AI 不能独立作出「验收通过」结论；须由用户确认或系统核验证据"
            )
        return AcceptanceReview(
            review_id=new_id("arv"),
            submission_id=submission_id,
            task_id=task_id,
            conclusion=conclusion,
            rationale=rationale.strip(),
            reviewer_kind=reviewer_kind,
            created_at=now or datetime.now(timezone.utc),
        )


def _infer_evidence_grade(
    items: list[str],
    repo_url: str | None,
    verification: VerificationRecord | None = None,
) -> EvidenceGrade:
    """按**证据来源**推断等级。刻意保守。

    设计 §8 硬约束（B1 评审指出旧实现严重错误）：

    - 用户文字叙述、粘贴的日志、仓库 URL、未核验的 commit/sha —— 一律
      ``reported``。**不得**因为字符串里出现 ``commit``/``ci``/
      ``http(s)://`` 或提供了 ``repo_url`` 就升级为 ``verified``。
    - 完全没有证据（既无条目也无 repo）—— ``insufficient``。
    - 只有**平台亲自核验并落库**的 ``VerificationRecord`` 且核验通过，
      才给 ``verified``。

    判定**只依赖** ``verification`` 是否存在且通过，**绝不**依赖关键词、
    URL 形态、文件名或 AI 自述。
    """
    has_any_evidence = bool(items) or bool(repo_url)
    if verification is not None and verification.is_passing:
        return EvidenceGrade.VERIFIED
    if has_any_evidence:
        return EvidenceGrade.REPORTED
    return EvidenceGrade.INSUFFICIENT


def _normalize_prompt(text: str) -> str:
    if not isinstance(text, str):
        raise ValidationAppError("实现思路必须是文本")
    stripped = text.strip()
    if len(stripped) < MIN_PROMPT_CHARS:
        raise ValidationAppError(f"实现思路至少需要 {MIN_PROMPT_CHARS} 个字符")
    if len(stripped) > MAX_PROMPT_CHARS:
        raise ValidationAppError(f"实现思路不得超过 {MAX_PROMPT_CHARS} 个字符")
    return stripped


def _clean(items: list[str]) -> list[str]:
    result: list[str] = []
    for item in items:
        text = str(item).strip()
        if text and text not in result:
            result.append(text)
    return result


def _require_text(
    value: str, field: str, *, max_len: int, min_len: int = 1
) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValidationAppError(f"{field}不能为空")
    length = len(value.strip())
    if length < min_len:
        raise ValidationAppError(f"{field}至少需要 {min_len} 个字符")
    if length > max_len:
        raise ValidationAppError(f"{field}长度不得超过 {max_len} 字符")


__all__ = [
    "MAX_EVIDENCE_ITEMS",
    "MAX_IDEA_CHARS",
    "MAX_PROMPT_CHARS",
    "MIN_IDEA_CHARS",
    "MIN_PROMPT_CHARS",
    "AcceptanceReview",
    "PracticeProject",
    "PracticeSubmission",
    "PracticeTask",
    "PromptExport",
    "PromptReview",
    "PromptRevision",
    "TaskKnowledgeLink",
    "VerificationRecord",
]
