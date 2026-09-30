"""Offline readiness checks. No real database or provider is contacted."""

import pytest
from app.infrastructure.providers.openai_compatible import OpenAICompatibleLLM
from app.ports.llm import LLMFailure, LLMResult
from app.tools.b3f2_controlled_live import StopAfterFailure, main, validate_provider
from app.tools.b3f2_inspect import summarize


def test_default_gate_refuses_before_reading_settings(monkeypatch):
    def forbidden_settings():
        raise AssertionError("Default gate must not read deployment settings")

    monkeypatch.setattr("app.core.config.get_settings", forbidden_settings)
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    with pytest.raises(SystemExit, match="NOT RUN"):
        main([])


def test_exact_deepseek_options_are_checked_without_dispatch():
    provider = OpenAICompatibleLLM(base_url="https://api.deepseek.com", api_key="offline", model="deepseek-flash")
    validate_provider(provider)
    provider.model = "some-other-model"
    with pytest.raises(RuntimeError, match="deepseek-flash"):
        validate_provider(provider)


@pytest.mark.parametrize("failure", ["provider_output_truncated", "provider_invalid_json", "provider_transport_unknown"])
def test_first_failure_prevents_next_attempt(failure):
    class Provider:
        calls = 0

        def generate_structured(self, **kwargs):
            self.calls += 1
            return LLMFailure(failure, "offline", dispatch_unknown=failure.endswith("unknown"))

    provider = Provider()
    guarded = StopAfterFailure(provider, "run")
    guarded.generate_structured(run_id="run", attempt_id="one")
    with pytest.raises(RuntimeError, match="stopped"):
        guarded.generate_structured(run_id="run", attempt_id="two")
    assert provider.calls == 1


def test_request_ceiling_duplicate_and_run_identity():
    class Provider:
        calls = 0

        def generate_structured(self, **kwargs):
            self.calls += 1
            return LLMResult(payload={}, model_id="offline", provider="fake")

    provider = Provider()
    guarded = StopAfterFailure(provider, "run")
    for index in range(21):
        guarded.generate_structured(run_id="run", attempt_id=str(index))
    for run, attempt in (("run", "21"), ("run", "0"), ("other", "x")):
        with pytest.raises(RuntimeError, match="stopped"):
            guarded.generate_structured(run_id=run, attempt_id=attempt)
    assert provider.calls == 21


def test_inspection_keeps_unknown_usage_null_and_partial_subtotals_honest():
    row = {"attempt_id": "run:b3f2-batch-v1:planning.structure:stage.one:0:0",
           "status": "failed", "input_tokens": None, "output_tokens": None}
    report = summarize({"status": "failed"}, [row], None, ["node.one"])
    assert report["attempts"][0]["purpose"] == "planning.structure"
    assert report["attempts"][0]["stage_key"] == "stage.one"
    assert report["input_token_subtotal"] is None and report["output_token_subtotal"] is None
    assert report["usage_complete"] is False
    assert report["draft_stage_count"] is None
    report = summarize({"status": "failed"}, [row, {**row, "input_tokens": 7, "output_tokens": 9}], None, [])
    assert report["input_token_subtotal"] == 7 and report["usage_complete"] is False
