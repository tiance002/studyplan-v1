"""Explicit user progress operations: no Graph, provider or mastery inference."""
from app.domain.learning_exposures import ExposureCommand
from app.ports.learning_exposures import LearningExposureRepository


class LearningExposureService:
    def __init__(self, repository: LearningExposureRepository):
        self.repository = repository

    def list(self, scope, project_id, plan_id, stage_id=None):
        scope.require_project(project_id)
        return self.repository.list(scope, project_id, plan_id, stage_id)

    def change(self, scope, command: ExposureCommand):
        scope.require_project(command.project_id)
        return self.repository.change(scope, command)

    def history(self, scope, project_id, plan_id, stage_id, unit_id):
        scope.require_project(project_id)
        return self.repository.history(scope, project_id, plan_id, stage_id, unit_id)
