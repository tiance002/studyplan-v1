from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.api.v1.summary_schemas import Identifier, Key


class AssistantCreateRequest(BaseModel):
    model_config=ConfigDict(extra="forbid")
    plan_id: Identifier
    stage_id: Identifier
    mode: Literal['summary','practice']
    task_id: Identifier | None = None
    idempotency_key: Key


class AssistantMessageRequest(BaseModel):
    model_config=ConfigDict(extra="forbid")
    intent: Literal['work_draft','question']
    content: str = Field(min_length=1,max_length=20000)
    idempotency_key: Key
    consent_to_model: bool = False


class AssistantSaveRequest(BaseModel):
    model_config=ConfigDict(extra="forbid")
    content: str = Field(min_length=1,max_length=20000)
    draft_message_id: Identifier
    expected_version: int = Field(ge=0,strict=True)
    idempotency_key: Key


class AssistantCancelRequest(BaseModel):
    model_config=ConfigDict(extra="forbid")
    run_id: Identifier
    expected_version: int = Field(ge=1,strict=True)
    idempotency_key: Key


class AssistantMessageView(BaseModel):
    message_id: str
    sequence: int
    role: Literal['user','assistant']
    intent: Literal['work_draft','question','reply']
    content: str
    created_at: datetime
    run_id: str | None
    run_status: str | None
    run_version: int | None
    draft_message_id: str | None
    trigger_message_id: str | None
    error_class: str | None


class AssistantFormalSaveView(BaseModel):
    save_id: str
    draft_message_id: str
    content: str
    artifact_id: str
    artifact_type: Literal['summary','prompt']
    formal_version: int
    created_at: datetime


class AssistantConversationSummary(BaseModel):
    conversation_id: str
    project_id: str
    plan_id: str
    plan_revision: int
    stage_id: str
    task_id: str | None
    mode: Literal['summary','practice']
    title: str
    context: dict[str,object]
    context_hash: str
    created_at: datetime
    read_only: bool
    current_draft_message_id: str | None
    formal_version: int


class AssistantConversationView(AssistantConversationSummary):
    messages_truncated: bool
    message_cursor: int | None
    messages: list[AssistantMessageView]
    formal_saves: list[AssistantFormalSaveView]


class AssistantHistoryView(BaseModel):
    items: list[AssistantConversationSummary]
    next_cursor: str | None
