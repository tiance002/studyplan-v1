"""Offline binding guards for configured deployment models; no HTTP requests."""
from dataclasses import replace
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from app.core.config import get_settings
from app.core.errors import ValidationAppError
from app.domain.workspace.models import AuthContext
from app.infrastructure.providers.runtime_factory import PersonalPlanningRuntimeFactory


def factory(view=None):
    settings = replace(get_settings(), llm_provider="openai_compatible",
                       llm_base_url="https://api.deepseek.com/v1", llm_api_key="private-test-key",
                       llm_model_id="deepseek-flash", llm_model_max_output_tokens=8192)
    repository = SimpleNamespace(get=lambda actor: view)
    runtime = PersonalPlanningRuntimeFactory(settings, repository)
    runtime.policy.validate = lambda value: value
    return runtime


SCOPE = AuthContext(actor_id="actor", session_id="session", learning_project_scope=("project",),
                    issued_at=datetime.now(UTC))


def test_deployment_config_is_frozen_for_registered_actor_without_personal_settings():
    runtime = factory()
    binding = runtime.bind_submission(SCOPE, "project")
    assert binding.model_ref.startswith("deployment:")
    assert "private-test-key" not in binding.model_ref
    provider = runtime.for_bound_run(SCOPE, "project", "run", binding.model_ref)
    assert provider.model == "deepseek-flash"
    assert provider.configuration_ref == binding.model_ref


def test_rotated_deployment_key_cannot_silently_replace_frozen_configuration():
    runtime = factory()
    binding = runtime.bind_submission(SCOPE, "project")
    runtime.settings = replace(runtime.settings, llm_api_key="rotated-private-key")
    with pytest.raises(ValidationAppError):
        runtime.for_bound_run(SCOPE, "project", "run", binding.model_ref)


def test_personal_model_still_takes_precedence_and_unconfigured_model_is_rejected():
    runtime = factory(SimpleNamespace(has_api_key=True, version=7, model_id="deepseek-flash",
                                     base_url="https://api.deepseek.com/v1"))
    assert runtime.bind_submission(SCOPE, "project").model_ref == "personal:actor:7"
    runtime = factory()
    runtime.settings = replace(runtime.settings, llm_api_key="")
    with pytest.raises(ValidationAppError):
        runtime.bind_submission(SCOPE, "project")
