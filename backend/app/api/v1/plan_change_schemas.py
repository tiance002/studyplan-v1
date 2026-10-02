from typing import Annotated, Literal

from app.api.v1.schemas import GoalSpec, PlanDraftView, StageDetail
from pydantic import BaseModel, ConfigDict, Field

Key = Annotated[str, Field(min_length=1, max_length=200)]
Operation = Literal['reorder_future_stage', 'remove_optional_topic']
GeneratedOperation = Literal['change_goal', 'regenerate_future_plan']


class GeneratedPlanChangeRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    plan_id: Key
    expected_version: int = Field(ge=0, strict=True)
    idempotency_key: Key
    operation: GeneratedOperation
    goal: str = Field(default='', max_length=2000)
    goal_spec: GoalSpec | None = None


class PlanChangeRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    plan_id: Key
    expected_version: int = Field(ge=0, strict=True)
    idempotency_key: Key
    operation: Operation
    stage_keys: list[Key] = Field(default_factory=list, max_length=100)
    stage_key: str = Field(default='', max_length=200)


class PlanChangeDecisionRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_version: int = Field(ge=0, strict=True)
    preview_hash: str = Field(min_length=1, max_length=128)
    idempotency_key: Key
    acknowledge_reset: bool = Field(default=False, strict=True)


class PlanChangeStage(BaseModel):
    stage_id: str
    stable_key: str
    title: str
    order_index: int
    locked: bool
    inclusion: Literal['required', 'recommended', 'optional']


class PlanChangeContext(BaseModel):
    plan_id: str
    revision: int
    stages: list[PlanChangeStage]
    goal: str = ''
    goal_spec: GoalSpec | None = None
    regenerate_available: bool = False
    generation_max_requests: int = 0


class PlanChangePreviewView(BaseModel):
    proposal_id: str
    status: Literal['awaiting_approval', 'approved', 'cancelled']
    draft: PlanDraftView
    base_plan_id: str
    base_revision: int
    operation: Operation | GeneratedOperation
    before_stage_keys: list[str]
    after_stage_keys: list[str]
    warnings: list[str]
    preview_hash: str
    retained_stage_keys: list[str] = Field(default_factory=list)
    before_goal: str = ''
    after_goal: str = ''
    before_stages: list[StageDetail] = Field(default_factory=list)


class PlanChangeResult(BaseModel):
    preview: PlanChangePreviewView
    plan_id: str | None = None
    revision: int | None = None
    created: bool
