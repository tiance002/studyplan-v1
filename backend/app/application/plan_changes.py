from app.core.errors import ValidationAppError
from app.ports.plan_changes import PlanChangeRepository


class PlanChangeService:
    def __init__(self, repository: PlanChangeRepository):
        self.repository = repository

    def context(self, scope, project_id):
        scope.require_project(project_id)
        return self.repository.context(scope, project_id)

    def preview(self, scope, command):
        scope.require_project(command.project_id)
        return self.repository.preview(scope, command)

    def get(self, scope, project_id, proposal_id):
        scope.require_project(project_id)
        return self.repository.get(scope, project_id, proposal_id)

    def decide(self, scope, project_id, proposal_id, action, expected_version, preview_hash,
               idempotency_key, acknowledge_reset=False):
        scope.require_project(project_id)
        if action not in {'confirm', 'cancel'} or type(expected_version) is not int or expected_version < 0:
            raise ValidationAppError('必须明确确认或取消，并提供正确版本')
        if (not isinstance(preview_hash, str) or not preview_hash or len(preview_hash) > 128
                or not isinstance(idempotency_key, str) or not idempotency_key or len(idempotency_key) > 200
                or type(acknowledge_reset) is not bool):
            raise ValidationAppError('预览确认参数不合法')
        return self.repository.decide(scope, project_id, proposal_id, action, expected_version,
                                      preview_hash, idempotency_key, acknowledge_reset)
