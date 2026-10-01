from __future__ import annotations

from typing import Any, Protocol

from app.domain.learning_exposures import ExposureCommand
from app.domain.workspace.models import AuthContext


class LearningExposureRepository(Protocol):
    def list(self, scope: AuthContext, project_id: str, plan_id: str,
             stage_id: str | None = None) -> list[dict[str, Any]]: ...
    def change(self, scope: AuthContext, command: ExposureCommand) -> dict[str, Any]: ...
    def history(self, scope: AuthContext, project_id: str, plan_id: str,
                stage_id: str, unit_id: str) -> list[dict[str, Any]]: ...
