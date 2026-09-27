"""成果证据等级的可信度验证（Goal §5）。

核心反例：用户**不得**通过关键词、URL 形态、文件名或 AI 自述，
把「自报成果」伪装成「系统已核验」。

规则：
- 用户文字 / 仓库 URL / 粘贴日志 / 未核验哈希 → reported
- 无有效证据 → insufficient
- 仅平台真实核验并落库的 ``VerificationRecord``（且通过）→ verified
"""

from __future__ import annotations

import pytest
from app.core.errors import ValidationAppError
from app.domain.enums import AcceptanceConclusion, EvidenceGrade, ReviewerKind
from app.domain.practice.models import (
    AcceptanceReview,
    PracticeSubmission,
    VerificationRecord,
)

# ---------------------------------------------------------------- insufficient


def test_submission_without_evidence_is_insufficient() -> None:
    sub = PracticeSubmission.create(task_id="ptk_1", note="我做完了")
    assert sub.evidence_grade is EvidenceGrade.INSUFFICIENT


def test_empty_submission_is_rejected() -> None:
    with pytest.raises(ValidationAppError):
        PracticeSubmission.create(task_id="ptk_1")


# ---------------------------------------------------------------- reported


@pytest.mark.parametrize(
    "evidence",
    [
        ["我完成了全部功能"],
        ["已经在本地跑通了"],
        ["commit abc1234"],
        ["sha: deadbeef"],
        ["CI 通过了 run: 12345"],
        ["日志: tests passed"],
        ["https://github.com/foo/bar"],
        ["见附件截图.png"],
        ["AI 评审说没问题"],
        ["已经 verified 了"],
    ],
)
def test_user_text_is_always_reported(evidence: list[str]) -> None:
    """明文/关键词/URL/自述——无论写得多像，都只能是 reported。"""
    sub = PracticeSubmission.create(task_id="ptk_1", evidence=evidence)
    assert sub.evidence_grade is EvidenceGrade.REPORTED


def test_repo_url_alone_is_only_reported() -> None:
    """仅给仓库地址**不等于**已核验（平台未 clone 也未执行）。"""
    sub = PracticeSubmission.create(
        task_id="ptk_1",
        note="代码已提交到仓库",
        repo_url="https://github.com/foo/bar",
    )
    assert sub.evidence_grade is EvidenceGrade.REPORTED


def test_unverified_commit_hash_is_only_reported() -> None:
    sub = PracticeSubmission.create(
        task_id="ptk_1",
        evidence=["commit 9f2c1a0"],
        repo_url="https://github.com/foo/bar",
    )
    assert sub.evidence_grade is EvidenceGrade.REPORTED


# ---------------------------------------------------------------- verified


def test_platform_verification_upgrades_to_verified() -> None:
    record = VerificationRecord.create(
        verification_method="git_clone",
        result="ok",
        evidence_ref="commit:9f2c1a0",
    )
    sub = PracticeSubmission.create(
        task_id="ptk_1",
        evidence=["提交见仓库"],
        repo_url="https://github.com/foo/bar",
        verification=record,
    )
    assert sub.evidence_grade is EvidenceGrade.VERIFIED
    assert sub.verification is record


def test_failed_verification_does_not_upgrade() -> None:
    record = VerificationRecord.create(
        verification_method="ci_run", result="failed", evidence_ref="run:12345"
    )
    sub = PracticeSubmission.create(
        task_id="ptk_1", evidence=["CI 跑过了"], verification=record
    )
    assert sub.evidence_grade is EvidenceGrade.REPORTED


def test_verification_record_requires_all_four_fields() -> None:
    for kwargs in (
        {"verification_method": "", "result": "ok", "evidence_ref": "x"},
        {"verification_method": "git_clone", "result": "", "evidence_ref": "x"},
        {"verification_method": "git_clone", "result": "ok", "evidence_ref": ""},
    ):
        with pytest.raises(ValidationAppError):
            VerificationRecord.create(**kwargs)


def test_verification_record_without_evidence_is_still_unverified_grade() -> None:
    """有核验记录但无任何证据条目/仓库 → 按规则仍有证据（核验通过）。"""
    record = VerificationRecord.create(
        verification_method="artifact_fetch", result="pass", evidence_ref="s3://x"
    )
    sub = PracticeSubmission.create(task_id="ptk_1", evidence=["产物已上传"], verification=record)
    assert sub.evidence_grade is EvidenceGrade.VERIFIED


# ------------------------------------------------------- 评审链互相独立


def test_prompt_review_pass_is_not_acceptance() -> None:
    """AI 评审「通过」不得直接等价于验收通过。"""
    with pytest.raises(ValidationAppError):
        AcceptanceReview.create(
            submission_id="psb_1",
            task_id="ptk_1",
            conclusion=AcceptanceConclusion.ACCEPTED,
            rationale="模型认为可以",
            reviewer_kind=ReviewerKind.MODEL,
        )


def test_user_can_accept() -> None:
    review = AcceptanceReview.create(
        submission_id="psb_1",
        task_id="ptk_1",
        conclusion=AcceptanceConclusion.ACCEPTED,
        rationale="我确认真实完成",
        reviewer_kind=ReviewerKind.USER,
    )
    assert review.conclusion is AcceptanceConclusion.ACCEPTED
