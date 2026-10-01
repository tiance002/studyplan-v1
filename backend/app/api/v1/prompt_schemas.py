from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Identifier = Annotated[str, Field(min_length=1, max_length=512)]
Key = Annotated[str, Field(min_length=1, max_length=128)]


class PromptKnowledgeView(BaseModel):
    node_id: str
    stable_key: str
    title: str
    role: str
    content_version: int


class PromptPracticeProjectView(BaseModel):
    practice_project_id: str
    title: str
    idea: str
    repo_url: str | None
    status: str
    version: int


class PromptTaskView(BaseModel):
    task_id: str
    title: str
    goal: str
    in_scope: list[str]
    out_scope: list[str]
    acceptance: list[str]
    status: str
    knowledge_links: list[PromptKnowledgeView]


class PromptReviewView(BaseModel):
    review_id: str
    revision_id: str
    task_id: str
    strengths: list[str]
    gaps: list[str]
    suggestions: list[str]
    run_id: str
    created_at: datetime


class PromptRevisionView(BaseModel):
    revision_id: str
    project_id: str
    plan_id: str | None
    stage_id: str | None
    task_id: str
    revision_no: int
    version: int = Field(ge=0)
    user_draft: str
    content_hash: str
    created_at: datetime
    task_snapshot: dict[str, object]
    review: PromptReviewView | None
    run_id: str | None
    run_status: str | None
    legacy_review: dict[str, object] | None = None
    legacy_review_recorded_at: datetime | None = None


class PromptThreadView(BaseModel):
    project_id: str
    plan_id: str
    stage_id: str
    task_id: str
    version: int = Field(ge=0)
    practice_project: PromptPracticeProjectView
    task: PromptTaskView
    revisions: list[PromptRevisionView]
    history_truncated: bool = False


class PromptSaveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plan_id: Identifier
    stage_id: Identifier
    task_id: Identifier
    user_draft: str = Field(min_length=1, max_length=40000)
    expected_version: int = Field(ge=0, strict=True)
    idempotency_key: Key


class PromptSaveView(BaseModel):
    thread: PromptThreadView
    revision: PromptRevisionView
    replayed: bool


class PromptHistoryView(BaseModel):
    items: list[PromptRevisionView]
    next_cursor: str | None


class PromptReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    consent_to_model: Literal[True]
    idempotency_key: Key

    @field_validator("consent_to_model", mode="before")
    @classmethod
    def explicit_boolean(cls, value):
        if value is not True:
            raise ValueError("需明确同意发送此修订及任务要求至模型")
        return value


class PromptReviewRunView(BaseModel):
    run_id: str
    revision_id: str
    status_url: str
    status: str
    next_action: str
    version: int = Field(ge=1)


class PromptCancelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_id: Identifier
    expected_version: int = Field(ge=1, strict=True)
    idempotency_key: Key


class PromptExportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    format: Literal["raw", "implementation"]
    idempotency_key: Key


class PromptExportView(BaseModel):
    export_id: str
    project_id: str
    task_id: str
    revision_id: str
    revision_no: int
    format: Literal["raw", "implementation"]
    export_text: str = Field(max_length=240000)
    content_hash: str
    created_at: datetime
