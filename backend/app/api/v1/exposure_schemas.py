"""Explicit self-reported progress, separated from knowledge verification."""
from datetime import datetime
from typing import Any, Literal

from app.domain.enums import UnitProgress
from pydantic import BaseModel, ConfigDict, Field


class ExposurePositionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plan_id: str = Field(min_length=1, max_length=512)
    stage_id: str = Field(min_length=1, max_length=512)
    unit_id: str = Field(min_length=1, max_length=512)


class ExposureChangeRequest(ExposurePositionRequest):
    status: UnitProgress
    expected_version: int = Field(ge=0, strict=True)
    idempotency_key: str = Field(min_length=1, max_length=128)


class ExposureNodeSnapshot(BaseModel):
    node_id: str
    stable_key: str
    title: str
    node_type: str
    objectives: list[str]
    content_version: int
    source_status: str
    role: str
    order_index: int
    source_pack_key: str | None
    source_pack_version: int | None


class ExposureSourceSnapshot(BaseModel):
    kind: Literal["assigned_source_bindings"]
    public_assignments: list[dict[str, Any]]
    private_selections: list[dict[str, Any]]
    v2_content: dict[str, Any] | None = None


class ExposureView(BaseModel):
    exposure_id: str
    project_id: str
    plan_id: str
    stage_id: str
    unit_id: str
    status: UnitProgress
    version: int
    recorded: bool
    node_snapshot: list[ExposureNodeSnapshot]
    source_snapshot: ExposureSourceSnapshot
    updated_at: datetime | None


class ExposureEventView(BaseModel):
    event_id: str
    exposure_id: str
    project_id: str
    plan_id: str
    stage_id: str
    unit_id: str
    actor_id: str
    from_status: UnitProgress
    to_status: UnitProgress
    expected_version: int
    version: int
    node_snapshot: list[ExposureNodeSnapshot]
    source_snapshot: ExposureSourceSnapshot
    created_at: datetime


class ExposureChangeView(BaseModel):
    exposure: ExposureView
    event: ExposureEventView
    replayed: bool
