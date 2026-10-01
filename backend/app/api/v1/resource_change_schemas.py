"""Explicit public-index replacement preview and ordinary plan confirmation."""
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ResourceChangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plan_id: str = Field(min_length=1, max_length=512)
    stage_id: str = Field(min_length=1, max_length=512)
    assignment_id: str = Field(min_length=1, max_length=512)
    source_ref: str = Field(min_length=1, max_length=512)
    source_version: int = Field(ge=1, strict=True)
    section_refs: list[str] = Field(min_length=1, max_length=300)
    expected_version: int = Field(ge=0, strict=True)
    copy_policy: Literal["copy_active", "keep_history_only"]
    idempotency_key: str = Field(min_length=1, max_length=128)


class ResourceChangeDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=0, strict=True)
    preview_hash: str = Field(min_length=1, max_length=128)
    idempotency_key: str = Field(min_length=1, max_length=128)
    acknowledge_warnings: bool = Field(default=False, strict=True)


class ResourceCatalogSourceView(BaseModel):
    source_id: str
    canonical_url: str
    title: str
    creator: str
    media_type: str
    language: str
    source_version: int
    verification_status: str
    documentation_version: str = ""
    provenance: str = ""
    checked_at: datetime | None = None


class ResourceCatalogSectionView(BaseModel):
    section_id: str
    source_id: str
    order_index: int
    title: str
    url: str
    anchor: str = ""
    verification_status: str
    checked_at: datetime | None = None
    review_note: str = ""


class ResourceCatalogView(BaseModel):
    source: ResourceCatalogSourceView
    sections: list[ResourceCatalogSectionView]
    index_truncated: bool = False


class ResourceBindingSnapshotView(BaseModel):
    assignment_id: str
    stage_id: str
    stage_key: str
    role: str
    order_index: int = 0
    source_ref: str
    source_version: int
    section_refs: list[str]
    snapshot_status: Literal["frozen", "unresolved_reference", "legacy_unfrozen"]
    snapshot_origin: str | None = None
    source: ResourceCatalogSourceView | None
    sections: list[ResourceCatalogSectionView]
    view: dict[str, Any] | None


class ResourceChangeNodeView(BaseModel):
    node_id: str
    stable_key: str
    title: str
    content_version: int


class ResourceChangePrerequisiteView(BaseModel):
    from_node_id: str
    to_node_id: str
    relation_type: str


class ResourceChangeCoverageView(BaseModel):
    mapping_status: Literal["available", "missing"]
    mapped_node_keys: list[str]
    unmatched_node_ids: list[str]
    required_extension_topics: list[str]


class ResourceChangeWorkloadView(BaseModel):
    before_section_count: int
    after_section_count: int
    delta_sections: int
    unit_count: int
    estimated_minutes: int | None


class ResourceChangeProgressObservation(BaseModel):
    unit_id: str
    status: Literal["not_started", "in_progress", "completed", "skipped"]
    version: int


class ResourceChangeProgressView(BaseModel):
    started_units: int
    completed_units: int
    skipped_units: int
    observations: list[ResourceChangeProgressObservation]


class ResourceChangeUnknownConstraintView(BaseModel):
    status: Literal["unknown"]


class ResourceChangePrivateBindingsView(BaseModel):
    policy: Literal["copy_active", "keep_history_only"]
    active_count: int
    copy_count: int
    history_retained: bool


class ResourceChangeImpactView(BaseModel):
    unit_ids: list[str]
    nodes: list[ResourceChangeNodeView]
    prerequisites: list[ResourceChangePrerequisiteView]
    prerequisite_status: Literal["recorded_relations_only", "unknown"]
    coverage: ResourceChangeCoverageView
    workload: ResourceChangeWorkloadView
    progress: ResourceChangeProgressView
    environment: ResourceChangeUnknownConstraintView
    pace: ResourceChangeUnknownConstraintView
    private_bindings: ResourceChangePrivateBindingsView
    warnings: list[str]


class ResourceChangePreviewView(BaseModel):
    proposal_id: str
    draft_id: str
    project_id: str
    actor_id: str
    base_plan_id: str
    base_revision: int
    status: Literal["pending", "confirmed", "cancelled"]
    preview_hash: str
    copy_policy: Literal["copy_active", "keep_history_only"]
    before: ResourceBindingSnapshotView
    after: ResourceBindingSnapshotView
    impact: ResourceChangeImpactView
    warnings: list[str]
    created_at: datetime
    draft_hash: str
    catalog_digest: str


class ResourceChangeResultView(BaseModel):
    proposal_id: str
    action: Literal["confirm", "cancel"]
    status: Literal["confirmed", "cancelled"]
    plan_id: str | None
    revision: int | None
    created: bool
    copied_selections: int
