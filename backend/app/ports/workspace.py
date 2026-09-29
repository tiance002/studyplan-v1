from typing import Any, Protocol

from app.domain.workspace.models import AuthContext


class WorkspaceReaderPort(Protocol):
    def read(
        self, scope: AuthContext, project_id: str, unit_ids: list[str], task_ids: list[str]
    ) -> dict[str, Any]: ...
