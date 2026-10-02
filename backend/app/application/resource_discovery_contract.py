"""Boundary validation for versioned discovery evidence and private snapshots.

Pydantic belongs at application/API boundaries. Domain rules consume the
validated dictionary or structural evidence objects without framework imports.
"""
from datetime import datetime
from typing import Literal

from app.domain.enums import MediaType, ResourceProvenance, StageResourceRole
from pydantic import BaseModel, ConfigDict, Field


class EvidenceModel(BaseModel):
    model_config = ConfigDict(extra="ignore", validate_assignment=True, allow_inf_nan=False)


class GitHubRepository(EvidenceModel):
    owner: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=100)
    default_branch: str = Field(default="", max_length=255)
    license: str | None = Field(default=None, max_length=100)
    updated_at: str | None = Field(default=None, max_length=100)
    stars: int | None = Field(default=None, ge=0)


class ContentEvidence(EvidenceModel):
    path: str = Field(max_length=1024)
    url: str = Field(max_length=4096)
    blob_sha: str | None = Field(default=None, max_length=100)
    content_hash: str = Field(max_length=100)
    fetched_at: str = Field(max_length=100)
    line_start: int = Field(default=1, ge=1)
    line_end: int = Field(default=1, ge=1)
    truncated: bool = False


class ChapterEvidence(EvidenceModel):
    path: str = Field(max_length=1024)
    title: str = Field(max_length=300)
    order: int = Field(ge=0)
    status: Literal["listed", "read", "unsupported"] = "listed"
    module_keys: list[str] = Field(default_factory=list, max_length=100)


class DiscoverySignals(EvidenceModel):
    topic_overlap: int = Field(default=0, ge=0, le=500)
    teaching_structure: bool | None = None
    prerequisites: bool | None = None
    exercises: bool | None = None
    difficulty: str = Field(default="unknown", max_length=100)
    language: str = Field(default="unknown", max_length=100)
    version: str = Field(default="unknown", max_length=100)


class SelectionMapping(EvidenceModel):
    module_keys: list[str] = Field(min_length=1, max_length=100)
    chapter_paths: list[str] = Field(min_length=1, max_length=100)
    role: StageResourceRole = StageResourceRole.REFERENCE
    basis: Literal["user_selected_read_chapters"] = "user_selected_read_chapters"


class DiscoveryEvidence(EvidenceModel):
    schema_version: Literal[1] = 1
    source: Literal["web", "github", "manual", "unknown"] = "unknown"
    provider_rank: int | None = Field(default=None, ge=1)
    provider_score: float | None = None
    snippet: str = Field(default="", max_length=2000)
    repo: GitHubRepository | None = None
    inspection_status: Literal["metadata_only", "readme_read", "chapter_or_index_checked", "controlled_review"] = "metadata_only"
    files: list[ContentEvidence] = Field(default_factory=list, max_length=3)
    chapters: list[ChapterEvidence] = Field(default_factory=list, max_length=100)
    signals: DiscoverySignals = Field(default_factory=DiscoverySignals)
    recommended_role: Literal["candidate", "mainline_candidate", "reference", "unsuitable"] = "candidate"
    reasons: list[str] = Field(default_factory=list, max_length=100)
    limitations: list[str] = Field(default_factory=list, max_length=100)
    selection_mapping: SelectionMapping | None = None


class ResourceCandidateSnapshot(EvidenceModel):
    resource_id: str = Field(min_length=1, max_length=512)
    project_id: str = Field(min_length=1, max_length=512)
    url: str = Field(min_length=1, max_length=4096)
    title: str = Field(min_length=1, max_length=300)
    media_type: MediaType
    language: str = Field(min_length=1, max_length=100)
    provenance: ResourceProvenance
    verification_status: Literal["unverified"] = "unverified"
    section_anchor: str | None = Field(default=None, max_length=1024)
    checked_at: datetime | None = None
    source_note: str = Field(default="", max_length=4096)
    # Existing private snapshots may carry a source version used by copy lineage.
    source_version: int | str | None = None
    discovery: DiscoveryEvidence = Field(default_factory=DiscoveryEvidence)
