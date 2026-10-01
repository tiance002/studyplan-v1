"""Explicit preview/confirm/cancel; no provider or Graph dependency."""
from app.core.errors import ValidationAppError
from app.ports.resource_changes import ResourceChangeRepository


class ResourceChangeService:
    def __init__(self, repository: ResourceChangeRepository):
        self.repository = repository

    def catalog(self, scope, project_id):
        scope.require_project(project_id)
        return self.repository.catalog(scope, project_id)

    def preview(self, scope, command):
        scope.require_project(command.project_id)
        return self.repository.preview(scope, command)

    def get(self, scope, project_id, proposal_id):
        scope.require_project(project_id)
        return self.repository.get(scope, project_id, proposal_id)

    def decide(self, scope, project_id, proposal_id, action, expected_version, preview_hash, idempotency_key,
               acknowledge_warnings=False):
        scope.require_project(project_id)
        if action not in {"confirm", "cancel"}:
            raise ValidationAppError("必须明确确认或取消预览")
        if type(expected_version) is not int or expected_version < 0 or not preview_hash or not idempotency_key:
            raise ValidationAppError("确认必须携带版本、预览hash及幂等键")
        return self.repository.decide(scope, project_id, proposal_id, action, expected_version, preview_hash,
                                      idempotency_key, acknowledge_warnings)
