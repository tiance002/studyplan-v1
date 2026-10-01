"""Manual artifacts and human decisions never dispatch or alter learning progress."""

from app.domain.practice_submissions import raw_text
from app.ports.practice_submissions import PracticeSubmissionsPort


class PracticeSubmissionService:
    def __init__(self, repository: PracticeSubmissionsPort):
        self.repository = repository

    def thread(self, scope, project_id, plan_id, stage_id, task_id):
        scope.require_project(project_id)
        for value in (plan_id, stage_id, task_id):
            raw_text(value, 512)
        return self.repository.thread(scope, project_id, plan_id, stage_id, task_id)

    def save(self, scope, command):
        scope.require_project(command.project_id)
        return self.repository.save(scope, command)

    def get(self, scope, project_id, submission_id):
        scope.require_project(project_id)
        raw_text(submission_id, 512)
        return self.repository.get(scope, project_id, submission_id)

    def decide(self, scope, command):
        scope.require_project(command.project_id)
        return self.repository.decide(scope, command)

    def history(self, scope, project_id, cursor=None, limit=20):
        scope.require_project(project_id)
        return self.repository.history(scope, project_id, cursor, limit)

    def outcomes(self, scope, project_id, cursor=None, limit=20):
        scope.require_project(project_id)
        return self.repository.outcomes(scope, project_id, cursor, limit)
