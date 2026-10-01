import pytest
from app.core.errors import ValidationAppError
from app.domain.practice.models import PromptExport, PromptRevision


def test_short_prompt_original_and_raw_export_preserve_whitespace():
    raw = " \n写\t🙂  "
    revision = PromptRevision.create(task_id="task", user_draft=raw, revision_no=1)
    assert revision.user_draft == raw
    export = PromptExport.create(task_id="task", revision=revision, export_text=raw)
    assert export.export_text == raw


def test_prompt_export_rejects_another_task():
    revision = PromptRevision.create(task_id="task", user_draft="x" * 50, revision_no=1)
    with pytest.raises(ValidationAppError):
        PromptExport.create(task_id="other", revision=revision, export_text=revision.user_draft)


@pytest.mark.parametrize(
    "raw",
    ["", " \n ", "x" * 40001, "x\x00y", "x\ud800y"],
    ids=["empty", "blank", "limit", "nul", "surrogate"],
)
def test_unpersistable_prompt_is_sanitized(raw):
    with pytest.raises(ValidationAppError) as error:
        PromptRevision.create(task_id="task", user_draft=raw, revision_no=1)
    assert raw not in str(error.value) if raw else True


def test_nested_review_projection_omits_local_secrets_and_identifiers():
    import json

    from app.domain.prompts import prompt_review_context

    snapshot = {
        "practice_project": {"idea": "private idea"},
        "source_snapshot": {"url": "private URL"},
        "task": {
            "title": "Task",
            "goal": "Goal",
            "knowledge_links": [
                {
                    "node_id": "private ID",
                    "stable_key": "node.key",
                    "title": "Knowledge",
                    "role": "core",
                    "content_version": 2,
                    "source_note": "nested private sentinel",
                    "url": "private URL",
                }
            ],
        },
    }
    result = prompt_review_context(snapshot)
    assert "private" not in json.dumps(result)
    assert result["knowledge_links"] == [
        {"stable_key": "node.key", "title": "Knowledge", "role": "core", "content_version": 2}
    ]
    assert snapshot["task"]["knowledge_links"][0]["source_note"] == "nested private sentinel"


def test_closed_prompt_feedback_and_bounded_manifest():
    from app.application.model_binding import SubmissionBinding
    from app.application.planning_budget import BudgetPolicy
    from app.domain.prompts import prompt_manifest, prompt_manifest_intact, validate_prompt_feedback

    manifest = prompt_manifest(SubmissionBinding("test:1", BudgetPolicy(20, 30, 40, 50, 15, 10)))
    assert (
        manifest["protocol"] == "prompt-review-v1"
        and manifest["max_requests"] == 1
        and manifest["output_cap"] == 10
    )
    assert prompt_manifest_intact(manifest)
    assert not prompt_manifest_intact(dict(manifest, max_requests=2))
    assert not validate_prompt_feedback({"strengths": ["clear"], "gaps": [], "suggestions": []})
    for bad in (
        {"strengths": [], "gaps": [], "suggestions": []},
        {"strengths": ["x"], "gaps": [], "suggestions": [], "task_id": "forged"},
        {"strengths": ["x"] * 21, "gaps": [], "suggestions": []},
        {"strengths": ["x\x00"], "gaps": [], "suggestions": []},
    ):
        assert validate_prompt_feedback(bad)


def test_prompt_provider_own_protocol_cap_and_no_claim_in_wire():
    import json

    import httpx
    from app.application.planning_budget import BudgetPolicy
    from app.infrastructure.providers.openai_compatible import OpenAICompatibleLLM
    from app.ports.llm import LLMFailure, LLMResult

    calls = []

    def reply(request):
        calls.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps({"strengths": ["clear"], "gaps": [], "suggestions": []})
                        },
                        "finish_reason": "stop",
                    }
                ]
            },
        )

    with httpx.Client(transport=httpx.MockTransport(reply)) as client:
        provider = OpenAICompatibleLLM(
            base_url="https://offline.invalid/v1",
            api_key="offline-only",
            model="offline",
            client=client,
            budget_policy=BudgetPolicy(100, 100, 100, 100, 80, 50),
        )
        kwargs = dict(
            purpose="prompt.review",
            payload={
                "user_draft": " raw ",
                "task_snapshot": {},
                "_prompt_claim": {"lease_token": "never-send"},
            },
            schema_name="PromptReviewV1",
            run_id="r",
            attempt_id="r:prompt_review:1",
        )
        assert isinstance(provider.generate_structured(**kwargs), LLMFailure) and not calls
        assert provider.prompt_version == "v2-g2-v8-resource-roles"
        provider.prompt_version = "prompt-review-v1"
        assert isinstance(provider.generate_structured(**kwargs), LLMResult)
    assert len(calls) == 1 and calls[0]["max_tokens"] == 50
    assert "never-send" not in json.dumps(calls)
    assert "Review the saved learner implementation Prompt" in calls[0]["messages"][0]["content"]
    # JSON mode requires an explicit JSON instruction even when the learner's
    # original and task contain no such word (DeepSeek returns HTTP 400).
    assert calls[0]["response_format"] == {"type": "json_object"}
    assert "json" in calls[0]["messages"][0]["content"].lower()


def test_implementation_export_over_cap_fails_instead_of_truncation():
    revision = PromptRevision.create(task_id="task", user_draft="原", revision_no=1)
    with pytest.raises(ValidationAppError):
        PromptExport.create(task_id="task", revision=revision, export_text="x" * 240001)
