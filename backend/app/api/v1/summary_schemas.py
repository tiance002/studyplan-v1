from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Identifier = Annotated[str, Field(min_length=1, max_length=512)]
Key = Annotated[str, Field(min_length=1, max_length=128)]


class SummaryReviewView(BaseModel):
    review_id: str
    attempt_id: str
    conclusion: Literal["satisfied", "needs_revision", "misconception"]
    covered: list[str]
    gaps: list[str]
    misconceptions: list[str]
    questions: list[str]
    rubric_version: int
    run_id: str
    created_at: datetime


class SummaryAttemptView(BaseModel):
    attempt_id: str
    project_id: str
    plan_id: str | None
    stage_id: str | None
    unit_id: str | None
    attempt_no: int
    version: int = Field(ge=0)
    content: str
    content_hash: str
    created_at: datetime
    rubric_snapshot: dict[str, object]
    review: SummaryReviewView | None
    run_id: str | None
    run_status: str | None
    legacy_review: dict[str, object] | None = None
    legacy_review_recorded_at: datetime | None = None


class SummaryThreadView(BaseModel):
    project_id: str
    plan_id: str
    stage_id: str
    unit_id: str | None
    version: int = Field(ge=0)
    questions: list[str] = Field(min_length=3, max_length=3)
    attempts: list[SummaryAttemptView]
    history_truncated: bool = False


class SummaryHistoryView(BaseModel):
    items: list[SummaryAttemptView]
    next_cursor: str | None


class SummarySaveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plan_id: Identifier
    stage_id: Identifier
    unit_id: Identifier | None = None
    content: str = Field(min_length=1, max_length=20000)
    expected_version: int = Field(ge=0, strict=True)
    idempotency_key: Key


class SummarySaveView(BaseModel):
    thread: SummaryThreadView
    attempt: SummaryAttemptView
    replayed: bool


class SummaryReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    idempotency_key: Key
    consent_to_model: Literal[True]

    @field_validator("consent_to_model", mode="before")
    @classmethod
    def require_explicit_boolean(cls, value):
        if value is not True:
            raise ValueError("需明确同意发送此修订至模型")
        return value


class SummaryCancelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_id: Identifier
    expected_version: int = Field(ge=1, strict=True)
    idempotency_key: Key


class SummaryReviewRunView(BaseModel):
    run_id: str
    attempt_id: str
    status_url: str
    status: str
    next_action: str
    version: int = Field(ge=1)
