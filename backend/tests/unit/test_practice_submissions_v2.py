from dataclasses import replace

import pytest
from app.core.errors import ValidationAppError


def command(**changes):
    from app.domain.practice_submissions import SubmissionSaveCommand

    values = dict(
        project_id="p",
        plan_id="plan",
        stage_id="stage",
        task_id="task",
        note="  Raw🙂\n",
        repo_url=None,
        evidence=(),
        artifact_kind="other",
        parent_submission_id=None,
        expected_plan_version=1,
        expected_task_version=1,
        expected_version=0,
        idempotency_key="key",
    )
    values.update(changes)
    return SubmissionSaveCommand(**values)


def evidence(**changes):
    from app.domain.practice_submissions import SubmissionEvidence

    values = dict(
        kind="external_report",
        label="  CI report ",
        content="\ncommit / all tests passed🙂  ",
        source_url=None,
    )
    values.update(changes)
    return SubmissionEvidence(**values)


def test_raw_is_preserved_and_domain_grade_never_keyword_verified():
    saved = command(evidence=(evidence(),))
    assert saved.note == "  Raw🙂\n"
    assert saved.evidence[0].content.endswith("🙂  ")
    assert saved.grade.value == "reported"
    assert command().grade.value == "insufficient"
    assert replace(saved, note=" \t\n").grade.value == "reported"
    assert replace(saved, idempotency_key="another").input_hash() == saved.input_hash()


@pytest.mark.parametrize(
    "changes",
    [
        dict(note="\x00"),
        dict(note="\ud800"),
        dict(note="x" * 20001),
        dict(note=" \n"),
        dict(note="", repo_url="https://localhost/repo"),
        dict(expected_version=True),
        dict(expected_plan_version=0),
        dict(artifact_kind="verified"),
        dict(repo_url="https://secret:pw@localhost"),
    ],
)
def test_invalid_original_is_rejected_without_echo(changes):
    with pytest.raises(ValidationAppError):
        command(**changes)


def test_attribution_urls_and_total_bounds_are_validated():
    for changes in [
        dict(kind="verified"),
        dict(label=" "),
        dict(content=" "),
        dict(kind="source_reference"),
        dict(source_url="file:///private"),
        dict(source_url="https://host\nsecret"),
    ]:
        with pytest.raises(ValidationAppError):
            evidence(**changes)
    assert evidence(kind="source_reference", source_url="http://localhost/report").source_url
    with pytest.raises(ValidationAppError):
        command(evidence=tuple(evidence(content="x" * 10000) for _ in range(9)))


def test_manual_coverage_requires_real_saved_indices_and_acknowledgment():
    from app.domain.practice_submissions import CriterionCoverage, SubmissionDecisionCommand

    item = CriterionCoverage(0, (0,), "  observed exactly  ")
    cmd = SubmissionDecisionCommand("p", "s", "accepted", " rationale ", (item,), True, 1, 2, 1, "key")
    cmd.validate_basis(["criterion"], 1, "reported")
    assert cmd.rationale == " rationale " and item.observation == "  observed exactly  "
    for bad in [
        replace(cmd, acknowledge_verification_limit=False),
        replace(cmd, coverage=()),
        replace(cmd, coverage=(CriterionCoverage(0, (1,), "observed"),)),
        replace(cmd, coverage=(item, item)),
    ]:
        with pytest.raises(ValidationAppError):
            bad.validate_basis(["criterion"], 1, "reported")
    with pytest.raises(ValidationAppError):
        cmd.validate_basis(["criterion"], 1, "insufficient")


def test_public_requests_forbid_verified_actor_reviewer_and_coerced_versions():
    from app.api.v1.submission_schemas import PracticeSubmissionDecisionRequest, PracticeSubmissionRequest
    from pydantic import ValidationError

    body = dict(
        plan_id="plan",
        stage_id="stage",
        task_id="task",
        note="raw",
        repo_url=None,
        evidence=[],
        artifact_kind="other",
        parent_submission_id=None,
        expected_plan_version=1,
        expected_task_version=1,
        expected_version=0,
        idempotency_key="key",
    )
    for extra in [
        dict(actor_id="other"),
        dict(evidence_grade="verified"),
        dict(verification={"result": "pass"}),
        dict(expected_version=True),
    ]:
        with pytest.raises(ValidationError):
            PracticeSubmissionRequest.model_validate(body | extra)
    review = dict(
        conclusion="accepted",
        rationale="observed",
        coverage=[],
        acknowledge_verification_limit=True,
        expected_plan_version=1,
        expected_task_version=1,
        expected_version=1,
        idempotency_key="key",
    )
    for extra in [dict(reviewer_kind="system"), dict(acknowledge_verification_limit="true")]:
        with pytest.raises(ValidationError):
            PracticeSubmissionDecisionRequest.model_validate(review | extra)
