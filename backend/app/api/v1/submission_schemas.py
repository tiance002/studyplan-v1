from datetime import datetime
from typing import Annotated, Literal

from app.api.v1.prompt_schemas import PromptPracticeProjectView, PromptTaskView
from pydantic import BaseModel, ConfigDict, Field

ArtifactKind = Literal[
    "project_description",
    "evaluation",
    "architecture",
    "design_decision",
    "failure_review",
    "explanation",
    "other",
]
EvidenceKind = Literal["user_statement", "external_report", "source_reference"]
EvidenceGrade = Literal["verified", "reported", "insufficient"]
AcceptanceConclusion = Literal["accepted", "needs_more_evidence", "not_passed"]
Identifier = Annotated[str, Field(min_length=1, max_length=512)]
Key = Annotated[str, Field(min_length=1, max_length=128)]
Index = Annotated[int, Field(ge=0, strict=True)]


class PracticeSubmissionEvidenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: EvidenceKind
    label: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=10000)
    source_url: str | None = Field(max_length=2000)


class PracticeSubmissionEvidenceView(BaseModel):
    kind: EvidenceKind
    label: str
    content: str
    source_url: str | None


class PracticeSubmissionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plan_id: Identifier
    stage_id: Identifier
    task_id: Identifier
    note: str = Field(max_length=20000)
    repo_url: str | None = Field(max_length=500)
    evidence: list[PracticeSubmissionEvidenceRequest] = Field(max_length=50)
    artifact_kind: ArtifactKind
    parent_submission_id: Identifier | None
    expected_plan_version: int = Field(ge=1, strict=True)
    expected_task_version: int = Field(ge=1, strict=True)
    expected_version: int = Field(ge=0, strict=True)
    idempotency_key: Key


class PracticeSubmissionTaskView(PromptTaskView):
    stable_key: str
    version: int = Field(ge=1)


class PracticeSubmissionSnapshotView(BaseModel):
    snapshot_status: Literal["frozen", "legacy_unfrozen"]
    plan_id: str | None
    plan_revision: int | None
    stage_id: str | None
    stage_title: str | None
    practice_project: PromptPracticeProjectView | None
    task: PracticeSubmissionTaskView | None
    warning: str | None


class PracticeSubmissionCoverageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    criterion_index: Index
    evidence_indices: list[Index] = Field(min_length=1, max_length=50)
    observation: str = Field(min_length=1, max_length=2000)


class PracticeSubmissionCoverageView(BaseModel):
    criterion_index: int
    evidence_indices: list[int]
    observation: str


class PracticeSubmissionDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    conclusion: AcceptanceConclusion
    rationale: str = Field(min_length=1, max_length=4000)
    coverage: list[PracticeSubmissionCoverageRequest] = Field(max_length=20)
    acknowledge_verification_limit: bool = Field(default=False, strict=True)
    expected_plan_version: int = Field(ge=1, strict=True)
    expected_task_version: int = Field(ge=1, strict=True)
    expected_version: int = Field(ge=1, strict=True)
    idempotency_key: Key


class PracticeSubmissionReviewView(BaseModel):
    review_id: str
    submission_id: str
    conclusion: AcceptanceConclusion
    reviewer_kind: Literal["user", "model", "system"]
    rationale: str
    coverage: list[PracticeSubmissionCoverageView]
    acknowledge_verification_limit: bool
    created_at: datetime
    manual_confirmation: bool


class PracticeSubmissionView(BaseModel):
    submission_id: str
    project_id: str
    plan_id: str | None
    stage_id: str | None
    task_id: str
    submission_no: int = Field(ge=0)
    version: int = Field(ge=0)
    note: str
    repo_url: str | None
    evidence: list[PracticeSubmissionEvidenceView]
    legacy_evidence: list[str]
    artifact_kind: ArtifactKind
    parent_submission_id: str | None
    content_hash: str
    task_snapshot: PracticeSubmissionSnapshotView
    evidence_grade: EvidenceGrade
    verification_available: bool
    source_check_available: bool
    review: PracticeSubmissionReviewView | None
    created_at: datetime


class PracticeSubmissionThreadView(BaseModel):
    project_id: str
    plan_id: str
    stage_id: str
    task_id: str
    plan_version: int
    version: int = Field(ge=0)
    task_version: int = Field(ge=1)
    practice_project: PromptPracticeProjectView
    task: PracticeSubmissionTaskView
    submissions: list[PracticeSubmissionView]
    history_truncated: bool
    platform_execution_available: bool
    source_check_available: bool


class PracticeSubmissionSaveView(BaseModel):
    thread: PracticeSubmissionThreadView
    submission: PracticeSubmissionView
    replayed: bool


class PracticeSubmissionDecisionView(BaseModel):
    submission: PracticeSubmissionView
    task_status: str
    task_version: int = Field(ge=1)
    created: bool
    manual_confirmation: bool


class PracticeSubmissionHistoryView(BaseModel):
    items: list[PracticeSubmissionView]
    next_cursor: str | None


class PracticeOutcomeItemView(BaseModel):
    submission_id: str
    artifact_kind: ArtifactKind
    plan_revision: int | None
    stage_title: str | None
    task_title: str | None
    project_title: str | None
    evidence_grade: EvidenceGrade
    conclusion: AcceptanceConclusion | None
    manual_confirmation: bool
    created_at: datetime


class PracticeOutcomeGroupView(BaseModel):
    kind: ArtifactKind
    title: str
    total_records: int = Field(ge=0)
    items: list[PracticeOutcomeItemView]


class PracticeOutcomeView(BaseModel):
    project_id: str
    groups: list[PracticeOutcomeGroupView]
    next_cursor: str | None
