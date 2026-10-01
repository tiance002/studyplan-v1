import pytest
from app.core.errors import ValidationAppError
from app.domain.reflections.models import SummaryAttempt


def test_short_summary_keeps_exact_unicode_whitespace():
    raw = "  学\n\t🙂  "
    attempt = SummaryAttempt.create(unit_id="u", project_id="p", content=raw,
                                    attempt_no=1, rubric_version=1)
    assert attempt.content == raw


@pytest.mark.parametrize("raw", ["", " \n\t", "x" * 20001])
def test_blank_and_raw_over_limit_rejected(raw):
    with pytest.raises(ValidationAppError):
        SummaryAttempt.create(unit_id="u", project_id="p", content=raw,
                              attempt_no=1, rubric_version=1)


@pytest.mark.parametrize("raw", ["x\x00y", "x\ud800y"])
def test_unpersistable_private_text_rejected_without_echo(raw):
    from app.domain.summaries import SummarySaveCommand
    with pytest.raises(ValidationAppError) as error:
        SummarySaveCommand("p", "plan", "stage", "unit", raw, 0, "k")
    assert raw not in str(error.value)


def test_summary_manifest_and_feedback_have_closed_bounded_contract():
    from app.domain.summaries import validate_feedback
    assert validate_feedback({"conclusion": "satisfied", "covered": ["objective"],
                              "gaps": [], "misconceptions": [], "questions": []}) == []
    for wrong in ({"conclusion": "verified"},
                  {"conclusion": "satisfied", "covered": ["x"] * 21, "gaps": [], "misconceptions": [], "questions": []},
                  {"conclusion": "satisfied", "covered": ["x"], "gaps": [], "misconceptions": [], "questions": [], "attempt_id": "spoof"}):
        assert validate_feedback(wrong)


def test_summary_provider_protocol_has_own_prompt_capped_output_and_no_claim_in_wire():
    import json

    import httpx
    from app.application.planning_budget import BudgetPolicy
    from app.infrastructure.providers.openai_compatible import OpenAICompatibleLLM
    from app.ports.llm import LLMResult
    calls = []
    def reply(request):
        calls.append(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps({
            "conclusion": "needs_revision", "covered": ["x"], "gaps": ["y"], "misconceptions": [], "questions": []})}, "finish_reason": "stop"}]})
    with httpx.Client(transport=httpx.MockTransport(reply)) as client:
        provider = OpenAICompatibleLLM(base_url="https://offline.invalid/v1", api_key="offline-only", model="offline",
            client=client, budget_policy=BudgetPolicy(100, 100, 100, 100, 80, 50))
        assert provider.prompt_version == "v2-g2-v8-resource-roles"
        provider.prompt_version = "summary-review-v1"
        result = provider.generate_structured(purpose="summary.review", payload={"content": " raw ",
            "rubric_snapshot": {}, "_summary_claim": {"lease_token": "never-send"}}, schema_name="SummaryReviewV1", run_id="r", attempt_id="a")
    assert isinstance(result, LLMResult) and len(calls) == 1 and calls[0]["max_tokens"] == 50
    assert "never-send" not in json.dumps(calls)
    assert "Review a saved learner reflection" in calls[0]["messages"][0]["content"]
    assert set(provider.budget_policy.as_dict()) == {"outline", "structure", "practice", "repair", "deployment_cap", "model_cap"}
