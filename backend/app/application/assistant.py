"""Multi-turn coaching; official writes stay in their original services."""
from app.agent_workflows.graphs import run_review_graph
from app.core.errors import AppError, DependencyUnavailableError, ForbiddenError, ValidationAppError
from app.domain.assistant import ASSISTANT_PURPOSE, assistant_manifest, validate_message, validate_reply
from app.domain.prompts import PromptSaveCommand
from app.domain.summaries import SummarySaveCommand
from app.ports.llm import LLMDispatchUnknownError, LLMFailure
from app.ports.summaries import ReviewPersistenceInterrupted


class AssistantService:
    def __init__(self, repository, summary_service, prompt_service, *, bind_submission=None,
                 provider_resolver=None, admission_mode="allowlist", actor_ids=()):
        self.repository = repository
        self.summary_service = summary_service
        self.prompt_service = prompt_service
        self.bind_submission = bind_submission
        self.provider_resolver = provider_resolver
        self.admission_mode = admission_mode
        self.actor_ids = actor_ids

    def create(self, scope, project, body):
        return self.repository.create(scope, project, body)

    def get(self, scope, project, identifier, before_sequence=None):
        return self.repository.get(scope, project, identifier, before_sequence)

    def list(self, scope, project, cursor=None, limit=20):
        return self.repository.list(scope, project, cursor, limit)

    def send(self, scope, project, identifier, body):
        validate_message(body["intent"], body["content"])
        if body.get("consent_to_model") is not True:
            raise ValidationAppError("发送模型前需要明确同意")
        prior = self.repository.message_receipt(scope, project, identifier, body)
        if prior:
            return prior
        error = None
        manifest = None
        if self.admission_mode == "allowlist" and scope.actor_id not in self.actor_ids:
            error = "assistant_worker_unavailable"
        elif self.bind_submission is None:
            error = "assistant_binding_unavailable"
        else:
            try:
                manifest = assistant_manifest(self.bind_submission(scope, project))
            except AppError:
                error = "assistant_binding_unavailable"
        return self.repository.send(scope, project, identifier, body, manifest, error)

    def save(self, scope, project, identifier, body):
        # A durable reservation holds the exact save key/body. If the ordinary
        # save commits before association fails, replay uses that same original
        # service receipt; no second formal revision is created.
        validate_message("work_draft", body["content"])
        row, reserved = self.repository.reserve_save(scope, project, identifier, body)
        if reserved["status"] != "succeeded":
            original_key = "assistant-save:" + reserved["save_id"]
            common = dict(project_id=project, plan_id=row["plan_id"], stage_id=row["stage_id"],
                          expected_version=body["expected_version"], idempotency_key=original_key)
            try:
                if row["mode"] == "summary":
                    result = self.summary_service.save(scope, SummarySaveCommand(
                        **common, unit_id=None, content=body["content"]))
                    artifact = result["attempt"]
                else:
                    result = self.prompt_service.save(scope, PromptSaveCommand(
                        **common, task_id=row["task_id"], user_draft=body["content"]))
                    artifact = result["revision"]
            except AppError:
                self.repository.save_outcome(scope, project, reserved["save_id"])
                raise
            try:
                self.repository.save_outcome(scope, project, reserved["save_id"], artifact)
            except Exception as exc:
                raise DependencyUnavailableError("正式原文已保存，关联待核对；请保留原操作并用同一幂等键恢复",
                    artifact_id=artifact.get("attempt_id") or artifact.get("revision_id"), formal_version=artifact["version"]) from exc
        return self.get(scope, project, identifier)

    def cancel(self, scope, project, identifier, body):
        return self.repository.cancel(scope, project, identifier, body)

    def execute_reply(self, *, project_id, run_id, claim, guard=None):
        if claim is None or (claim.project_id, claim.run_id) != (project_id, run_id):
            raise ValidationAppError("助手执行需要精确 Worker claim")
        if guard:
            guard()
        try:
            turn = self.repository.turn(claim)
        except AppError:
            return self.repository.finish(claim, None, error="assistant_contract_invalid")
        if self.provider_resolver is None:
            return self.repository.finish(claim, turn, error="assistant_provider_unavailable")
        scope = self.repository._claim_scope(claim)
        try:
            provider = self.provider_resolver(scope, project_id, run_id, turn["manifest"]["model_ref"], turn["manifest"])
        except AppError:
            return self.repository.finish(claim, turn, error="assistant_binding_unavailable")

        def load(state):
            return {"snapshot": turn["payload"]}

        def review(state):
            if guard:
                guard()
            payload = dict(turn["payload"], _project_id=project_id, _assistant_claim=dict(
                job_id=claim.job_id, run_id=claim.run_id, project_id=project_id,
                actor_id=claim.actor_id, lease_token=claim.lease_token))
            result = provider.generate_structured(purpose=ASSISTANT_PURPOSE, payload=payload,
                schema_name="AssistantReplyV1", run_id=run_id, attempt_id=run_id + ":assistant_reply:1")
            if isinstance(result, LLMFailure):
                if result.dispatch_unknown:
                    raise LLMDispatchUnknownError("助手结果未知，禁止重发")
                raise _ReplyFailure(result.error_class)
            return {"review": result.payload}

        def validate(value):
            if validate_reply(value):
                raise _ReplyFailure("assistant_reply_invalid")
            return []

        def persist(state):
            if guard:
                guard()
            return self.repository.finish(claim, turn, state["review"])

        try:
            return run_review_graph(initial={"run_id": run_id, "project_id": project_id},
                load_snapshot=load, review_once=review, validate_review=validate, persist_review=persist)
        except _ReplyFailure as exc:
            return self.repository.finish(claim, turn, error=exc.error_class)
        except LLMDispatchUnknownError:
            return self.repository.finish(claim, turn, error="provider_dispatch_unknown", unknown=True)
        except Exception as exc:
            from app.ports.planning_jobs import PlanningLeaseLostError
            if isinstance(exc, PlanningLeaseLostError):
                raise
            raise ReviewPersistenceInterrupted("助手落库中断；保留原回执和队列以安全恢复") from exc


class _ReplyFailure(Exception):
    def __init__(self, error_class):
        self.error_class = error_class
