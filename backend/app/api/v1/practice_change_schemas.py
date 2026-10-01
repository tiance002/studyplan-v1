from datetime import datetime
from typing import Annotated, Literal

from app.api.v1.prompt_schemas import PromptKnowledgeView, PromptPracticeProjectView, PromptTaskView
from pydantic import BaseModel, ConfigDict, Field

Identifier = Annotated[str, Field(min_length=1, max_length=512)]
ShortText = Annotated[str, Field(min_length=1, max_length=2000)]


class PracticeChangeProjectView(PromptPracticeProjectView):
    pass


class PracticeChangeKnowledgeView(BaseModel):
    node_id: str
    stable_key: str
    title: str
    content_version: int


class PracticeChangeKnowledgeLink(BaseModel):
    model_config = ConfigDict(extra="forbid")
    node_id: Identifier
    role: Literal["core", "supporting", "extension"]


class PracticeChangeTaskKnowledgeView(PromptKnowledgeView):
    role: Literal["core", "supporting", "extension"]


class PracticeChangeTaskView(PromptTaskView):
    knowledge_links: list[PracticeChangeTaskKnowledgeView]
    practice_project_id: str
    stable_key: str
    version: int
    stage_id: str
    stage_key: str
    order_index: int


class PracticeChangeStageView(BaseModel):
    stage_id: str
    stable_key: str
    title: str
    order_index: int


class PracticeChangeContextView(BaseModel):
    project_id: str
    plan_id: str
    revision: int
    version: int
    practice_projects: list[PracticeChangeProjectView]
    stages: list[PracticeChangeStageView]
    tasks: list[PracticeChangeTaskView]
    knowledge_options: list[PracticeChangeKnowledgeView]


class PracticeChangeTaskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation: Literal["update", "add"]
    client_key: str = Field(min_length=1, max_length=128)
    task_id: Identifier | None
    stage_id: Identifier
    title: str = Field(min_length=1, max_length=200)
    goal: ShortText
    in_scope: list[ShortText] = Field(min_length=1, max_length=20)
    out_scope: list[ShortText] = Field(min_length=1, max_length=20)
    acceptance: list[ShortText] = Field(min_length=1, max_length=20)
    knowledge_links: list[PracticeChangeKnowledgeLink] = Field(min_length=1, max_length=30)


class PracticeChangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plan_id: Identifier
    practice_project_id: Identifier
    title: str = Field(min_length=1, max_length=200)
    idea: str = Field(min_length=10, max_length=4000)
    repo_url: str | None = Field(max_length=500)
    task_changes: list[PracticeChangeTaskRequest] = Field(max_length=30)
    expected_version: int = Field(ge=1, strict=True)
    copy_policy: Literal["copy_active", "keep_history_only"]
    idempotency_key: str = Field(min_length=1, max_length=128)


class PracticeChangeDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1, strict=True)
    preview_hash: str = Field(min_length=1, max_length=128)
    idempotency_key: str = Field(min_length=1, max_length=128)
    acknowledge_warnings: bool = Field(default=False, strict=True)


class PracticeChangeTaskDeltaView(BaseModel):
    operation: Literal["update", "add", "rebind"]
    before: PracticeChangeTaskView | None
    after: PracticeChangeTaskView


class PracticeChangeImpactView(BaseModel):
    changed_task_ids: list[str]
    added_task_ids: list[str]
    cloned_task_count: int
    started_task_count: int
    prompt_revision_count: int
    summary_count: int
    exposure_count: int
    private_binding_count: int
    new_exposures_reset: bool
    preserve_history: bool


class PracticeChangePreviewView(BaseModel):
    proposal_id: str
    draft_id: str
    project_id: str
    base_plan_id: str
    base_revision: int
    base_version: int
    status: Literal["pending", "confirmed", "cancelled"]
    preview_hash: str
    draft_hash: str
    copy_policy: Literal["copy_active", "keep_history_only"]
    before: PracticeChangeProjectView
    after: PracticeChangeProjectView
    task_changes: list[PracticeChangeTaskDeltaView]
    impact: PracticeChangeImpactView
    warnings: list[str]
    created_at: datetime


class PracticeChangeResultView(BaseModel):
    proposal_id: str
    action: Literal["confirm", "cancel"]
    status: Literal["confirmed", "cancelled"]
    plan_id: str | None
    revision: int | None
    created: bool
    copied_selections: int
