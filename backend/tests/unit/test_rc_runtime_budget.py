"""Ordinary runtime budget binding; no provider HTTP or database writes."""

from copy import deepcopy
from types import SimpleNamespace

import pytest

from app.agent_workflows.planning_batches import (
    DEFAULT_BUDGET, STRUCTURE_PURPOSE, attempt_key, freeze_manifest,
)
from app.core.errors import ValidationAppError
from app.infrastructure.providers.attempt_ledger import PgAttemptLLM
from app.infrastructure.providers.runtime_factory import PersonalPlanningRuntimeFactory


def frozen_manifest():
    return freeze_manifest({"resource_support": "search_only", "stage_blueprints": []},
                           DEFAULT_BUDGET, "deployment:frozen", generic_stage_count=3)


def ordinary_factory(monkeypatch, provider):
    import app.infrastructure.providers.runtime_factory as module

    settings = SimpleNamespace(
        llm_allowed_hosts=(), database_url="postgresql://unused:unused@127.0.0.1/unused",
        checkpoint_database_url="postgresql://unused:unused@127.0.0.1/unused",
    )
    factory = PersonalPlanningRuntimeFactory(settings, SimpleNamespace())
    monkeypatch.setattr(factory, "for_bound_run", lambda *args: provider)
    monkeypatch.setattr(module, "PgPlanningExecutor",
                        lambda dsn, *, llm: SimpleNamespace(llm=llm))
    return factory


def test_ordinary_runtime_factory_binds_independent_frozen_manifest(monkeypatch):
    provider = SimpleNamespace()
    calls = []
    scope = SimpleNamespace(require_project=lambda project: calls.append(project))
    factory = ordinary_factory(monkeypatch, provider)
    manifest = frozen_manifest()
    expected = deepcopy(manifest)
    runtime = factory(scope, "owned-project", "owned-run", "deployment:frozen", manifest=manifest)
    assert runtime.llm.manifest == expected
    assert runtime.llm.manifest is not manifest
    assert runtime.executor.llm is runtime.llm
    manifest["max_requests"] = 400
    assert runtime.llm.manifest == expected
    assert calls == ["owned-project"]


@pytest.mark.parametrize("mutation", ["tampered", "model_ref"])
def test_factory_rejects_invalid_frozen_authority_before_provider_resolution(monkeypatch, mutation):
    factory = ordinary_factory(monkeypatch, SimpleNamespace())
    resolved = []
    monkeypatch.setattr(factory, "for_bound_run", lambda *args: resolved.append(args))
    manifest = frozen_manifest()
    model_ref = "deployment:frozen"
    if mutation == "tampered":
        manifest["max_requests"] += 1
    else:
        model_ref = "deployment:different"
    with pytest.raises(ValidationAppError):
        factory(SimpleNamespace(require_project=lambda _: None), "owned", "run", model_ref,
                manifest=manifest)
    assert not resolved


class BudgetReadConnection:
    def __init__(self, keys=()):
        self.keys = keys

    def execute(self, query, args=()):
        return SimpleNamespace(fetchone=lambda: None,
                               fetchall=lambda: [{"attempt_id": key} for key in self.keys])


@pytest.mark.parametrize("actual_cap", [8193, 0, -1, True, "8192", None])
def test_actual_provider_cap_must_be_positive_integer_within_frozen_purpose(actual_cap):
    manifest = frozen_manifest()
    ledger = PgAttemptLLM("postgresql://unused:unused@127.0.0.1/unused",
        SimpleNamespace(request_options=lambda _: {"max_tokens": actual_cap}), manifest=manifest)
    key = attempt_key("unit-owned", STRUCTURE_PURPOSE, "stage.general.0", 0, 0)
    assert ledger._budget_rejection(BudgetReadConnection(), run_id="unit-owned",
        attempt_id=key, purpose=STRUCTURE_PURPOSE) == "run_budget_exhausted"


def test_purpose_cannot_differ_from_registered_attempt_key():
    manifest = frozen_manifest()
    ledger = PgAttemptLLM("postgresql://unused:unused@127.0.0.1/unused",
        SimpleNamespace(request_options=lambda _: {"max_tokens": 4096}), manifest=manifest)
    key = attempt_key("unit-owned", STRUCTURE_PURPOSE, "stage.general.0", 0, 0)
    assert ledger._budget_rejection(BudgetReadConnection(), run_id="unit-owned",
        attempt_id=key, purpose="planning.practice") == "run_manifest_violation"
