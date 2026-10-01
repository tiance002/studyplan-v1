from app.core.errors import ValidationAppError
from app.domain.practice_changes import text
from app.ports.practice_changes import PracticeChangeRepository


class PracticeChangeService:
    def __init__(self, repository: PracticeChangeRepository):
        self.repository = repository

    def context(self, scope, project_id):
        scope.require_project(project_id)
        return self.repository.context(scope, project_id)

    def preview(self, scope, command):
        scope.require_project(command.project_id)
        return self.repository.preview(scope, command)

    def get(self, scope, project_id, proposal_id):
        scope.require_project(project_id)
        text(proposal_id, 512)
        return self.repository.get(scope, project_id, proposal_id)

    def decide(
        self,
        scope,
        project_id,
        proposal_id,
        action,
        expected_version,
        preview_hash,
        idempotency_key,
        acknowledge_warnings=False,
    ):
        scope.require_project(project_id)
        text(proposal_id, 512)
        text(preview_hash, 128)
        text(idempotency_key, 128)
        if (
            action not in {"confirm", "cancel"}
            or type(expected_version) is not int
            or expected_version < 1
            or type(acknowledge_warnings) is not bool
        ):
            raise ValidationAppError("决定必须携带原版本、hash、幂等键和明确操作")
        return self.repository.decide(
            scope,
            project_id,
            proposal_id,
            action,
            expected_version,
            preview_hash,
            idempotency_key,
            acknowledge_warnings,
        )
