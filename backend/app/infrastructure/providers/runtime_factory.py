"""Create a fresh provider/ledger/runtime for each authenticated run.

A run freezes its model configuration **at enqueue time** (``bind_submission``)
and resolves that exact revision later (``for_bound_run``). The current settings
are never consulted at execution time, so editing or clearing model settings
after submission cannot silently swap the model under a queued run — a revoked
frozen revision fails loudly instead.
"""
import hashlib
import json
from copy import deepcopy
from dataclasses import replace
from typing import cast

from app.agent_workflows.planning_batches import manifest_is_intact
from app.application.model_binding import SubmissionBinding
from app.application.planning_budget import budget_policy_for_model
from app.core.errors import ValidationAppError
from app.infrastructure.checkpointer.planning_executor import PgPlanningExecutor
from app.infrastructure.providers import build_llm
from app.infrastructure.providers.attempt_ledger import PgAttemptLLM
from app.infrastructure.providers.endpoint_policy import ModelEndpointPolicy
from app.infrastructure.providers.openai_compatible import OpenAICompatibleLLM
from app.ports.graph_runner import PlanningRuntime
from app.ports.llm import LLMFailure

__all__ = ["PersonalPlanningRuntimeFactory", "UnconfiguredLLM", "parse_personal_ref"]

_PERSONAL_PREFIX = "personal:"


def parse_personal_ref(model_ref: str) -> tuple[str, int] | None:
    """Parse ``personal:<actor>:<version>``; ``None`` for any other descriptor."""
    if not model_ref.startswith(_PERSONAL_PREFIX):
        return None
    parts = model_ref.split(":")
    if len(parts) != 3 or not parts[2].isdigit():
        return None
    return parts[1], int(parts[2])


class UnconfiguredLLM:
    def generate_structured(self, **kwargs):
        return LLMFailure("model_not_configured", "Configure a model before generation")


class PersonalPlanningRuntimeFactory:
    def __init__(self, settings, repository):
        self.settings = settings
        self.repository = repository
        self.policy = ModelEndpointPolicy(settings.llm_allowed_hosts)

    def bind_submission(self, scope, project_id) -> SubmissionBinding:
        """Freeze the actor's current model revision and budget for a new run.

        Called before the run row exists, so this returns a *descriptor* rather
        than pinning a row; ``for_bound_run`` pins exactly that revision later.
        """
        scope.require_project(project_id)
        view = self.repository.get(scope.actor_id)
        if view is None or not view.has_api_key:
            return self._deployment_binding()
        policy = budget_policy_for_model(
            self.settings, model=view.model_id, base_url=view.base_url
        )
        return SubmissionBinding(
            model_ref=f"personal:{scope.actor_id}:{view.version}", budget_policy=policy
        )

    def _deployment_binding(self) -> SubmissionBinding:
        settings = self.settings
        if settings.use_fake_llm or not all((settings.llm_api_key, settings.llm_model_id, settings.llm_base_url)):
            raise ValidationAppError("请先配置个人模型或部署模型后再发起生成")
        base_url = self.policy.validate(settings.llm_base_url)
        policy = budget_policy_for_model(settings, model=settings.llm_model_id, base_url=base_url)
        # This opaque server descriptor detects rotation without storing a plaintext key.
        revision = hashlib.sha256(json.dumps(
            [base_url, settings.llm_model_id, settings.llm_api_key, policy.as_dict()],
            sort_keys=True, ensure_ascii=False,
        ).encode()).hexdigest()
        return SubmissionBinding(model_ref=f"deployment:{revision}", budget_policy=policy)

    def for_bound_run(self, scope, project_id, run_id, model_ref) -> "OpenAICompatibleLLM":
        """Resolve the revision a run froze; refuse silently swapping the model."""
        scope.require_project(project_id)
        if model_ref.startswith("deployment:"):
            if model_ref != self._deployment_binding().model_ref:
                raise ValidationAppError("该 Run 冻结的部署模型配置已变更；拒绝静默改用当前配置")
            provider = self._deployment_provider()
            provider.configuration_ref = model_ref
            return provider
        parsed = parse_personal_ref(model_ref)
        if parsed is None:
            raise ValidationAppError("该 Run 的模型配置引用不可识别，拒绝按当前设置执行")
        actor_id, version = parsed
        if actor_id != scope.actor_id:
            raise ValidationAppError("该 Run 的模型配置不属于当前账户")
        selected = self.repository.bind_version(actor_id, project_id, run_id, version)
        if selected is None:
            raise ValidationAppError(
                "该 Run 冻结的模型配置已被撤销或不可用；拒绝静默改用当前模型设置"
            )
        return self._personal_provider(actor_id, selected)

    def _personal_provider(self, actor_id: str, selected) -> OpenAICompatibleLLM:
        """Build a provider bound to one pinned settings revision."""
        if selected.protocol != "openai":
            raise ValidationAppError("Unsupported model API protocol")
        policy = budget_policy_for_model(
            self.settings, model=selected.model_id, base_url=selected.base_url
        )
        provider = OpenAICompatibleLLM(
            base_url=selected.base_url, api_key=selected.api_key, model=selected.model_id,
            timeout=self.settings.llm_timeout_seconds,
            max_tokens=self.settings.llm_max_output_tokens,
            endpoint_guard=self.policy.validate, budget_policy=policy)
        provider.configuration_ref = f"personal:{actor_id}:{selected.version}"
        return provider

    def _deployment_provider(self) -> OpenAICompatibleLLM:
        """Deployment-level credentials (no personal setting bound to this run)."""
        base_url = self.policy.validate(self.settings.llm_base_url)
        provider = cast(OpenAICompatibleLLM, build_llm(replace(self.settings, llm_provider="openai_compatible")))
        provider.base_url = base_url
        provider.endpoint_guard = self.policy.validate
        provider.configuration_ref = "deployment"
        return provider

    def __call__(self, scope, project_id, run_id, model_ref="", *, manifest=None) -> PlanningRuntime:
        scope.require_project(project_id)
        frozen_manifest = deepcopy(manifest)
        if frozen_manifest is not None and (
            not manifest_is_intact(frozen_manifest)
            or frozen_manifest.get("model_ref") != model_ref
        ):
            raise ValidationAppError("冻结规划清单或模型绑定不一致，拒绝派发")
        if model_ref:
            provider = self.for_bound_run(scope, project_id, run_id, model_ref)
        else:
            # No frozen reference (older callers): pin the current revision once.
            selected = self.repository.bind_run(scope.actor_id, project_id, run_id)
            if selected:
                provider = self._personal_provider(scope.actor_id, selected)
            else:
                # Do not select Fake when a personal setting is absent or revoked.
                if not self.settings.llm_api_key or not self.settings.llm_model_id:
                    raise ValidationAppError("Configure a personal model before generation")
                provider = self._deployment_provider()
        ledger = PgAttemptLLM(self.settings.database_url, provider, manifest=frozen_manifest)
        executor = PgPlanningExecutor(self.settings.checkpoint_database_url, llm=ledger)
        return PlanningRuntime(ledger, executor)
