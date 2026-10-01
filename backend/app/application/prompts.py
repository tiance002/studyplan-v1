from app.application.summaries import SummaryService
from app.domain.prompts import (
    PROMPT_PROTOCOL,
    PROMPT_PURPOSE,
    prompt_manifest,
    prompt_review_context,
    validate_prompt_feedback,
)


class PromptService(SummaryService):
    subject_label = "Prompt"
    basis_label = "任务与知识要求"
    protocol = PROMPT_PROTOCOL
    purpose = PROMPT_PURPOSE
    subject_column = "revision_id"
    snapshot_column = "task_snapshot"
    raw_column = "user_draft"
    claim_column = "_prompt_claim"
    schema_name = "PromptReviewV1"
    attempt_suffix = ":prompt_review:1"
    invalid_error_class = "prompt_review_invalid"
    build_manifest = staticmethod(prompt_manifest)
    feedback_valid = staticmethod(validate_prompt_feedback)
    review_context = staticmethod(prompt_review_context)

    def thread(self, scope, project_id, plan_id, stage_id, task_id):
        scope.require_project(project_id)
        return self.repository.thread(scope, project_id, plan_id, stage_id, task_id)

    def revision(self, scope, project_id, revision_id):
        scope.require_project(project_id)
        return self.repository.attempt(scope, project_id, revision_id)

    def export(self, scope, project_id, revision_id, format, idempotency_key):
        scope.require_project(project_id)
        self._key(idempotency_key)
        return self.repository.export(scope, project_id, revision_id, format, idempotency_key)

    def get_export(self, scope, project_id, export_id):
        scope.require_project(project_id)
        return self.repository.get_export(scope, project_id, export_id)
