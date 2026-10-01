"""Original-first save and one bounded model review of an immutable attempt."""
from datetime import UTC, datetime

from app.agent_workflows.graphs import run_review_graph
from app.core.errors import DependencyUnavailableError, ForbiddenError, ValidationAppError
from app.domain.summaries import (
    SUMMARY_PROTOCOL,
    SUMMARY_PURPOSE,
    review_rubric_context,
    summary_manifest,
    validate_feedback,
)
from app.domain.workspace.models import AuthContext
from app.ports.llm import LLMDispatchUnknownError, LLMFailure
from app.ports.planning_jobs import PlanningLeaseLostError
from app.ports.summaries import ReviewPersistenceInterrupted, SummariesPort


class SummaryService:
    def __init__(self, repository: SummariesPort, *, bind_submission=None, provider_resolver=None,
                 admission_mode="allowlist", actor_ids=()):
        if admission_mode not in {"allowlist", "trusted_server"}:
            raise ValidationAppError("总结反馈 Worker admission 无效")
        self.repository = repository
        self.bind_submission = bind_submission
        self.provider_resolver = provider_resolver
        self.admission_mode = admission_mode
        self.actor_ids = tuple(actor_ids)

    def thread(self, scope, project_id, plan_id, stage_id, unit_id):
        scope.require_project(project_id)
        return self.repository.thread(scope, project_id, plan_id, stage_id, unit_id)

    def save(self, scope, command):
        scope.require_project(command.project_id)
        return self.repository.save(scope, command)

    def attempt(self, scope, project_id, attempt_id):
        scope.require_project(project_id)
        return self.repository.attempt(scope, project_id, attempt_id)

    def history(self, scope, project_id, cursor=None, limit=20):
        scope.require_project(project_id)
        return self.repository.history(scope, project_id, cursor, limit)

    @staticmethod
    def _key(key):
        if (not isinstance(key, str) or not key.strip() or len(key) > 128 or "\x00" in key
                or any(0xD800 <= ord(char) <= 0xDFFF for char in key)):
            raise ValidationAppError("幂等键无效")

    def request_review(self, scope, project_id, attempt_id, idempotency_key, consent_to_model):
        scope.require_project(project_id)
        self._key(idempotency_key)
        if consent_to_model is not True:
            raise ValidationAppError("请明确同意把本次保存的总结和评分依据发送至所选模型")
        prior = self.repository.review_receipt(scope, project_id, attempt_id, idempotency_key)
        if prior:
            return prior
        if self.repository.has_review_binding(scope, project_id, attempt_id):
            return self.repository.enqueue_review(scope, project_id, attempt_id, idempotency_key, None)
        if self.admission_mode == "allowlist" and scope.actor_id not in self.actor_ids:
            raise ForbiddenError("后台 Worker 尚未配置服务当前账户")
        if self.bind_submission is None:
            raise DependencyUnavailableError("总结反馈模型尚未装配；原文已保存")
        binding = self.bind_submission(scope, project_id)
        return self.repository.enqueue_review(scope, project_id, attempt_id, idempotency_key, summary_manifest(binding))

    def cancel_review(self, scope, project_id, attempt_id, run_id, expected_version, idempotency_key):
        self._key(idempotency_key)
        if type(expected_version) is not int or expected_version < 1:
            raise ValidationAppError("反馈任务版本无效")
        return self.repository.cancel_review(scope, project_id, attempt_id, run_id, expected_version, idempotency_key)

    def execute_review(self, project_id, run_id, *, guard, claim):
        if claim is None or claim.project_id != project_id or claim.run_id != run_id:
            raise PlanningLeaseLostError("总结反馈需要准确的 Worker 领取凭证")
        guard()
        submission = self.repository.review_submission(claim)
        attempt, manifest = submission["attempt"], submission["manifest"]
        scope = AuthContext(claim.actor_id, "summary-worker", datetime.now(UTC), (project_id,))
        try:
            if self.provider_resolver is None:
                raise DependencyUnavailableError("总结反馈模型尚未装配")
            llm = self.provider_resolver(scope, project_id, run_id, manifest["model_ref"], manifest)
            def review_once(state):
                guard()
                result = llm.generate_structured(purpose=SUMMARY_PURPOSE,
                    payload={"_project_id": project_id, "content": attempt["content"],
                             "rubric_snapshot": state["rubric_snapshot"],
                             "_summary_claim": {"job_id": claim.job_id, "run_id": claim.run_id,
                                 "project_id": claim.project_id, "actor_id": claim.actor_id, "lease_token": claim.lease_token}},
                    schema_name="SummaryReviewV1", run_id=run_id, attempt_id=run_id + ":summary_review:1")
                if isinstance(result, LLMFailure):
                    if result.dispatch_unknown:
                        raise LLMDispatchUnknownError("总结反馈结果需要核对")
                    raise _ReviewFailure(result.error_class)
                return {"review": result.payload}

            def persist(state):
                guard()
                return self.repository.finish_review(claim, attempt["attempt_id"], state["review"])

            trace = run_review_graph(initial={"run_id": run_id, "project_id": project_id,
                "graph_version": SUMMARY_PROTOCOL, "subject_id": attempt["attempt_id"]},
                load_snapshot=lambda state: {"rubric_snapshot": review_rubric_context(attempt["rubric_snapshot"])},
                review_once=review_once, validate_review=validate_feedback, persist_review=persist)
            if trace.failed_errors:
                self.repository.finish_review(claim, attempt["attempt_id"], error_class="summary_review_invalid")
        except PlanningLeaseLostError:
            raise
        except LLMDispatchUnknownError:
            self.repository.finish_review(claim, attempt["attempt_id"], error_class="attempt_dispatch_unknown", unknown=True)
        except _ReviewFailure as error:
            self.repository.finish_review(claim, attempt["attempt_id"], error_class=error.error_class)
        except (ValidationAppError, DependencyUnavailableError):
            self.repository.finish_review(claim, attempt["attempt_id"], error_class="model_configuration_unavailable")
        except Exception as error:
            raise ReviewPersistenceInterrupted("总结反馈事务未完成；保留队列供安全恢复") from error
        # Unexpected persistence/crash exceptions deliberately propagate. Retained
        # provider results can be replayed; dispatched unknowns are never retried.


class _ReviewFailure(Exception):
    def __init__(self, error_class):
        self.error_class = error_class
