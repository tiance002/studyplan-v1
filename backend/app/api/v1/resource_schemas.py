"""User-triggered resource search and private unit metadata contracts."""
from datetime import datetime
from typing import Literal

from app.domain.enums import MediaType, ResourceProvenance
from pydantic import BaseModel, ConfigDict, Field


class ResourceTargetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plan_id: str = Field(min_length=1, max_length=512)
    stage_id: str = Field(min_length=1, max_length=512)
    unit_id: str = Field(min_length=1, max_length=512)


class ResourceSearchRequest(ResourceTargetRequest):
    query: str = Field(min_length=1, max_length=500)
    idempotency_key: str = Field(min_length=1, max_length=128)


class ResourceSelectionRequest(ResourceTargetRequest):
    search_id: str = Field(min_length=1, max_length=64)
    candidate_id: str = Field(min_length=1, max_length=64)


class ManualResourceRequest(ResourceTargetRequest):
    url: str = Field(min_length=1, max_length=4096)
    title: str = Field(min_length=1, max_length=300)


class ResourceCandidateView(BaseModel):
    resource_id: str
    project_id: str
    url: str
    title: str
    media_type: MediaType
    language: str
    provenance: ResourceProvenance
    verification_status: Literal["unverified"] = "unverified"
    section_anchor: str | None = None
    checked_at: datetime | None = None
    source_note: str = ""


class ResourceSearchView(BaseModel):
    search_id: str
    status: Literal["dispatched", "succeeded", "failed", "reconciliation_required"]
    query: str
    candidates: list[ResourceCandidateView]
    error: str | None = None
    created_at: datetime


class SelectedResourceView(BaseModel):
    selection_id: str
    resource: ResourceCandidateView
    created_at: datetime


class ResourceRemovalView(BaseModel):
    removed: bool
