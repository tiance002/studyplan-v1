"""Raw manual work and explicit human assertions; no platform verification."""

from dataclasses import asdict, dataclass
from urllib.parse import urlsplit

from app.core.errors import ValidationAppError
from app.core.ids import content_hash
from app.domain.enums import AcceptanceConclusion, EvidenceGrade
from app.domain.practice.models import PracticeSubmission

ARTIFACT_KINDS = (
    "project_description",
    "evaluation",
    "architecture",
    "design_decision",
    "failure_review",
    "explanation",
    "other",
)
EVIDENCE_KINDS = ("user_statement", "external_report", "source_reference")
OUTCOME_TITLES = ("项目描述", "评估记录", "架构", "设计决定", "失败复盘", "解释说明", "其他成果")


def raw_text(value, maximum, *, nonblank=True):
    if (
        not isinstance(value, str)
        or len(value) > maximum
        or (nonblank and not value.strip())
        or "\x00" in value
        or any(0xD800 <= ord(char) <= 0xDFFF for char in value)
    ):
        raise ValidationAppError("文本为空、超出大小限制或含无法保存的字符")
    return value


def integer(value, minimum):
    if type(value) is not int or value < minimum:
        raise ValidationAppError("版本或索引无效")


def metadata_url(value, maximum):
    if value is None:
        return
    raw_text(value, maximum)
    try:
        parsed = urlsplit(value)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in value)
        ):
            raise ValueError()
        _ = parsed.port
    except ValueError:
        raise ValidationAppError("来源地址必须为无嵌入凭证的HTTP或HTTPS元数据") from None


@dataclass(frozen=True)
class SubmissionEvidence:
    kind: str
    label: str
    content: str
    source_url: str | None

    def __post_init__(self):
        if self.kind not in EVIDENCE_KINDS:
            raise ValidationAppError("证据来源类别无效")
        raw_text(self.label, 200)
        raw_text(self.content, 10000)
        metadata_url(self.source_url, 2000)
        if self.kind == "source_reference" and self.source_url is None:
            raise ValidationAppError("来源引用需要提供地址；平台不会访问或核验此地址")


@dataclass(frozen=True)
class SubmissionSaveCommand:
    project_id: str
    plan_id: str
    stage_id: str
    task_id: str
    note: str
    repo_url: str | None
    evidence: tuple[SubmissionEvidence, ...]
    artifact_kind: str
    parent_submission_id: str | None
    expected_plan_version: int
    expected_task_version: int
    expected_version: int
    idempotency_key: str

    def __post_init__(self):
        for value in self.position:
            raw_text(value, 512)
        raw_text(self.note, 20000, nonblank=False)
        metadata_url(self.repo_url, 500)
        if self.artifact_kind not in ARTIFACT_KINDS or len(self.evidence) > 50:
            raise ValidationAppError("成果类别或证据条目数量无效")
        if any(not isinstance(item, SubmissionEvidence) for item in self.evidence):
            raise ValidationAppError("证据条目无效")
        if not self.note.strip() and not self.evidence:
            raise ValidationAppError("提交必须包含说明或证据；仅仓库地址不足以提交")
        total = len(self.note) + sum(
            len(e.label) + len(e.content) + len(e.source_url or "") for e in self.evidence
        )
        if total > 80000:
            raise ValidationAppError("提交原文与证据总长度不得超过80000个字符")
        if self.parent_submission_id is not None:
            raw_text(self.parent_submission_id, 512)
        integer(self.expected_plan_version, 1)
        integer(self.expected_task_version, 1)
        integer(self.expected_version, 0)
        raw_text(self.idempotency_key, 128)

    @property
    def position(self):
        return self.project_id, self.plan_id, self.stage_id, self.task_id

    @property
    def grade(self) -> EvidenceGrade:
        # Only reuse the authoritative grade; its normalized strings never replace raw input.
        return PracticeSubmission.create(
            task_id=self.task_id,
            note=self.note,
            repo_url=self.repo_url,
            evidence=[item.content for item in self.evidence],
        ).evidence_grade

    def input_hash(self):
        return content_hash({key: value for key, value in asdict(self).items() if key != "idempotency_key"})

    def original_hash(self):
        return content_hash(
            {
                key: asdict(self)[key]
                for key in ("note", "repo_url", "evidence", "artifact_kind", "parent_submission_id")
            }
        )


@dataclass(frozen=True)
class CriterionCoverage:
    criterion_index: int
    evidence_indices: tuple[int, ...]
    observation: str

    def __post_init__(self):
        integer(self.criterion_index, 0)
        if not 1 <= len(self.evidence_indices) <= 50 or len(set(self.evidence_indices)) != len(
            self.evidence_indices
        ):
            raise ValidationAppError("每条标准需要不重复的证据索引")
        for value in self.evidence_indices:
            integer(value, 0)
        raw_text(self.observation, 2000)


@dataclass(frozen=True)
class SubmissionDecisionCommand:
    project_id: str
    submission_id: str
    conclusion: str
    rationale: str
    coverage: tuple[CriterionCoverage, ...]
    acknowledge_verification_limit: bool
    expected_plan_version: int
    expected_task_version: int
    expected_version: int
    idempotency_key: str

    def __post_init__(self):
        raw_text(self.project_id, 512)
        raw_text(self.submission_id, 512)
        raw_text(self.rationale, 4000)
        raw_text(self.idempotency_key, 128)
        if self.conclusion not in {value.value for value in AcceptanceConclusion} or len(self.coverage) > 20:
            raise ValidationAppError("人工结论或标准覆盖条数无效")
        if type(self.acknowledge_verification_limit) is not bool:
            raise ValidationAppError("需明确确认核验限制")
        for value in (self.expected_plan_version, self.expected_task_version, self.expected_version):
            integer(value, 1)

    def validate_basis(self, criteria, evidence_count, grade):
        indices = [item.criterion_index for item in self.coverage]
        if len(set(indices)) != len(indices) or any(index >= len(criteria) for index in indices):
            raise ValidationAppError("标准索引重复或不属于此保存版本")
        if any(index >= evidence_count for item in self.coverage for index in item.evidence_indices):
            raise ValidationAppError("证据索引不属于此保存版本")
        if self.conclusion == "accepted" and (
            grade == "insufficient"
            or not self.acknowledge_verification_limit
            or not criteria
            or set(indices) != set(range(len(criteria)))
        ):
            raise ValidationAppError("人工确认通过需充分证据、全部标准的实际观察以及明确确认平台未独立核验")

    def input_hash(self):
        return content_hash({key: value for key, value in asdict(self).items() if key != "idempotency_key"})
