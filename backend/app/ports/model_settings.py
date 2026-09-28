"""Private model configuration metadata and server-only secret resolution."""
from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class ModelSettingsView:
    version: int
    base_url: str
    model_id: str
    protocol: str
    has_api_key: bool


@dataclass(frozen=True)
class ModelConfiguration:
    version: int
    base_url: str
    model_id: str
    protocol: str
    api_key: str = field(repr=False)


class ModelSettingsRepository(Protocol):
    def get(self, actor_id: str) -> ModelSettingsView | None: ...
    def save(self, actor_id: str, *, expected_version: int, base_url: str, model_id: str, protocol: str, api_key: str) -> ModelSettingsView: ...
    def clear(self, actor_id: str, *, expected_version: int) -> ModelSettingsView: ...
    def resolve(self, actor_id: str) -> ModelConfiguration | None: ...
    def bind_run(self, actor_id: str, project_id: str, run_id: str) -> ModelConfiguration | None: ...
