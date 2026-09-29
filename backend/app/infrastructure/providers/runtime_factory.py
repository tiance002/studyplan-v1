"""Create a fresh provider/ledger/runtime for each authenticated run."""
from dataclasses import replace

from app.application.planning_budget import budget_policy_for_model
from app.core.errors import ValidationAppError
from app.infrastructure.checkpointer.planning_executor import PgPlanningExecutor
from app.infrastructure.providers import build_llm
from app.infrastructure.providers.attempt_ledger import PgAttemptLLM
from app.infrastructure.providers.endpoint_policy import ModelEndpointPolicy
from app.infrastructure.providers.openai_compatible import OpenAICompatibleLLM
from app.ports.graph_runner import PlanningRuntime
from app.ports.llm import LLMFailure


class UnconfiguredLLM:
    def generate_structured(self, **kwargs):
        return LLMFailure("model_not_configured","Configure a model before generation")


class PersonalPlanningRuntimeFactory:
    def __init__(self, settings, repository):
        self.settings = settings
        self.repository = repository
        self.policy = ModelEndpointPolicy(settings.llm_allowed_hosts)

    def __call__(self, scope, project_id, run_id):
        scope.require_project(project_id)
        selected = self.repository.bind_run(scope.actor_id,project_id,run_id)
        if selected:
            if selected.protocol != "openai":
                raise ValidationAppError("Unsupported model API protocol")
            policy = budget_policy_for_model(self.settings, model=selected.model_id, base_url=selected.base_url)
            provider = OpenAICompatibleLLM(base_url=selected.base_url,api_key=selected.api_key,model=selected.model_id,
                timeout=self.settings.llm_timeout_seconds,max_tokens=self.settings.llm_max_output_tokens,
                endpoint_guard=self.policy.validate, budget_policy=policy)
            provider.configuration_ref = f"personal:{scope.actor_id}:{selected.version}"
        else:
            # Do not select Fake when a personal setting is absent or revoked.
            if not self.settings.llm_api_key or not self.settings.llm_model_id:
                raise ValidationAppError("Configure a personal model before generation")
            base_url = self.policy.validate(self.settings.llm_base_url)
            provider = build_llm(replace(self.settings,llm_provider="openai_compatible"))
            provider.base_url = base_url
            provider.endpoint_guard = self.policy.validate
            provider.configuration_ref = "deployment"
        ledger = PgAttemptLLM(self.settings.database_url,provider)
        executor = PgPlanningExecutor(self.settings.checkpoint_database_url,llm=ledger)
        return PlanningRuntime(ledger,executor)
