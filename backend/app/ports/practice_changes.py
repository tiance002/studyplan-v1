from typing import Protocol

from app.domain.practice_changes import PracticeChangeCommand
from app.domain.workspace.models import AuthContext


class PracticeChangeRepository(Protocol):
    def context(self, scope: AuthContext, project_id: str) -> dict: ...
    def preview(self, scope: AuthContext, command: PracticeChangeCommand) -> dict: ...
    def get(self, scope: AuthContext, project_id: str, proposal_id: str) -> dict: ...
    def decide(
        self,
        scope: AuthContext,
        project_id: str,
        proposal_id: str,
        action: str,
        expected_version: int,
        preview_hash: str,
        idempotency_key: str,
        acknowledge_warnings: bool = False,
    ) -> dict: ...
