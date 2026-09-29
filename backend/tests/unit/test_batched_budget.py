from dataclasses import FrozenInstanceError
from types import SimpleNamespace

import pytest
from app.application.planning_budget import BudgetPolicy, budget_policy_for_model
from app.core.errors import ValidationAppError


@pytest.fixture
def policy() -> BudgetPolicy:
    return BudgetPolicy(
        outline=4096,
        structure=8192,
        practice=4096,
        repair=8192,
        deployment_cap=8192,
        model_cap=393216,
    )


def test_purpose_budgets_are_explicit_and_immutable(policy: BudgetPolicy):
    assert policy.for_purpose("planning.outline") == 4096
    assert policy.for_purpose("planning.structure") == 8192
    assert policy.for_purpose("planning.practice") == 4096
    assert policy.for_purpose("planning.repair") == 8192
    assert policy.as_dict() == {
        "outline": 4096,
        "structure": 8192,
        "practice": 4096,
        "repair": 8192,
        "deployment_cap": 8192,
        "model_cap": 393216,
    }
    with pytest.raises(FrozenInstanceError):
        policy.structure = 1000  # type: ignore[misc]


def test_deployment_hard_cap_conflict_is_reported_without_clamping():
    policy = BudgetPolicy(4096, 8192, 4096, 8192, 8000, 393216)
    with pytest.raises(ValidationAppError, match="structure"):
        policy.for_purpose("planning.structure")


@pytest.mark.parametrize("value", [0, -1, True, 1.5])
def test_invalid_budget_values_are_rejected(value):
    with pytest.raises(ValidationAppError):
        BudgetPolicy(value, 8192, 4096, 8192, 8192, 393216)


def test_unknown_purpose_is_rejected(policy: BudgetPolicy):
    with pytest.raises(ValidationAppError, match="planning.unknown"):
        policy.for_purpose("planning.unknown")


def test_only_the_confirmed_deepseek_host_and_model_get_its_published_cap():
    settings = SimpleNamespace(
        llm_outline_output_tokens=4096,
        llm_structure_output_tokens=8192,
        llm_practice_output_tokens=4096,
        llm_repair_output_tokens=8192,
        llm_max_output_tokens=8192,
        llm_model_max_output_tokens=16384,
    )
    flash = budget_policy_for_model(settings, model="deepseek-flash", base_url="https://api.deepseek.com/v1")
    assert flash.model_cap == 393216
    personal_model = budget_policy_for_model(settings, model="my-flash", base_url="https://api.deepseek.com")
    assert personal_model.model_cap == 16384
    alias_host = budget_policy_for_model(settings, model="deepseek-flash", base_url="https://proxy.example")
    assert alias_host.model_cap == 16384


def test_unconfirmed_compatible_model_requires_an_explicit_cap():
    settings = SimpleNamespace(
        llm_outline_output_tokens=4096,
        llm_structure_output_tokens=8192,
        llm_practice_output_tokens=4096,
        llm_repair_output_tokens=8192,
        llm_max_output_tokens=8192,
        llm_model_max_output_tokens=0,
    )
    with pytest.raises(ValidationAppError, match="model_cap"):
        budget_policy_for_model(settings, model="other", base_url="https://other.example")


def test_settings_defaults_cover_each_purpose_and_deployment_hard_cap(monkeypatch):
    from app.core.config import get_settings, reset_settings_cache

    for name in (
        "LLM_MAX_OUTPUT_TOKENS",
        "LLM_OUTLINE_OUTPUT_TOKENS",
        "LLM_STRUCTURE_OUTPUT_TOKENS",
        "LLM_PRACTICE_OUTPUT_TOKENS",
        "LLM_REPAIR_OUTPUT_TOKENS",
        "LLM_MODEL_MAX_OUTPUT_TOKENS",
    ):
        monkeypatch.delenv(name, raising=False)
    reset_settings_cache()
    settings = get_settings()
    try:
        assert (settings.llm_max_output_tokens, settings.llm_outline_output_tokens,
                settings.llm_structure_output_tokens, settings.llm_practice_output_tokens,
                settings.llm_repair_output_tokens) == (8192, 4096, 8192, 4096, 8192)
        assert settings.llm_model_max_output_tokens == 0
    finally:
        reset_settings_cache()
