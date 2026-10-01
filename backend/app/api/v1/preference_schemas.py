"""Complete preference layers plus retained versions for inherited positions."""

from typing import Literal

from app.api.v1.resource_schemas import ResourceTargetRequest
from app.api.v1.schemas import PreferenceView
from app.domain.enums import PreferenceMode
from pydantic import BaseModel, Field


class PreferencePositionRequest(ResourceTargetRequest):
    node_id: str | None = Field(default=None, min_length=1, max_length=512)


class PreferencePutRequest(PreferencePositionRequest):
    scope: Literal["project", "unit", "node"]
    mode: PreferenceMode
    language: str = Field(default="zh", min_length=1, max_length=16)
    official_priority: bool = True
    pace: Literal["slow", "normal", "fast"] = "normal"
    expected_version: int = Field(ge=0)


class PreferenceDeleteRequest(PreferencePositionRequest):
    scope: Literal["project", "unit", "node"]
    expected_version: int = Field(ge=0)


class PreferenceVersions(BaseModel):
    project: int = Field(ge=0)
    unit: int = Field(ge=0)
    node: int = Field(ge=0)


class PreferenceContextView(BaseModel):
    project: PreferenceView | None
    unit: PreferenceView | None
    node: PreferenceView | None
    effective: PreferenceView | None
    invalid_scopes: list[Literal["project", "unit", "node"]] = Field(default_factory=list)
    inherited: bool
    versions: PreferenceVersions
