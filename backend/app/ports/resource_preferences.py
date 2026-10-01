"""One persistent preference source, with retained versions for inherited slots."""

from dataclasses import dataclass, field
from typing import Protocol

from app.domain.resources.models import ResourcePreference
from app.domain.workspace.models import AuthContext


@dataclass(frozen=True, slots=True)
class PreferenceLayers:
    project: ResourcePreference | None = None
    unit: ResourcePreference | None = None
    node: ResourcePreference | None = None
    versions: dict[str, int] = field(default_factory=lambda: {"project": 0, "unit": 0, "node": 0})
    invalid_scopes: tuple[str, ...] = ()


class ResourcePreferencesPort(Protocol):
    def get_context(self, scope: AuthContext, target: dict) -> PreferenceLayers: ...
    def put(self, scope: AuthContext, target: dict, preference: ResourcePreference,
            expected_version: int) -> PreferenceLayers: ...
    def restore(self, scope: AuthContext, target: dict, scope_name: str,
                expected_version: int) -> PreferenceLayers: ...
    def project_default(self, scope: AuthContext, project_id: str) -> ResourcePreference: ...
