"""Canonical project source references; fixtures do not prove model semantics."""
import json

import httpx
import pytest
from app.application.goal_requirement_analysis import GoalRequirementAnalyzer
from app.core.errors import ValidationAppError
from app.domain.planning.goal_requirements import GoalRequirementProfileValidator
from app.domain.planning.intent import GoalSpec
from app.infrastructure.providers.openai_compatible import OpenAICompatibleLLM

PROJECT = "已经有旅行规划 Agent，希望继续基于它实践，现有项目只读"


def output(field="required_requirements", ref="project_context"):
    raw = {"schema_version": 1, "target_summary": "基于已有项目继续学习 Agent",
           "required_requirements": [{"text": "继续学习 Agent 开发", "origin": "explicit",
                                      "source_refs": ["goal.target"], "rationale": ""}],
           "hard_constraints": [], "learner_claims": [], "clarification_questions": [], "status": "ready"}
    if field == "required_requirements":
        raw[field][0].update(text="基于已有旅行规划 Agent 继续实践", source_refs=[ref])
    else:
        raw[field] = [{"text": "现有项目只读", "source_refs": [ref]}]
    return raw


def test_project_ref_instruction_and_example_reach_actual_transport_system():
    goal = GoalSpec("继续学习 Agent 开发", project_context=PROJECT)
    requests = []

    def respond(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(output())},
                                                    "finish_reason": "stop"}]})

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        provider = OpenAICompatibleLLM(base_url="https://provider.example/v1", api_key="mock-only",
                                        model="mock", client=client)
        profile = GoalRequirementAnalyzer(provider).analyze(goal, run_id="project-ref-test", attempt_id="one")
    assert len(requests) == 1
    system = requests[0]["messages"][0]["content"]
    assert "合法source_ref是project_context" in system
    assert "goal.project_context是非法source_ref" in system
    # The small example teaches the canonical ref without echoing input-path ambiguity.
    assert '{"text":"基于已有项目继续实践","source_refs":["project_context"],"origin":"explicit","rationale":""}' in system
    context = json.loads(requests[0]["messages"][1]["content"])["context"]["goal"]
    assert context["project_context"] == PROJECT
    assert profile.project_context == PROJECT


@pytest.mark.parametrize("field", ["required_requirements", "hard_constraints"])
def test_prefixed_project_ref_remains_invalid(field):
    goal = GoalSpec("继续学习 Agent 开发", project_context=PROJECT)
    with pytest.raises(ValidationAppError):
        GoalRequirementProfileValidator().validate(output(field, "goal.project_context"), goal=goal)


@pytest.mark.parametrize("field", ["required_requirements", "hard_constraints"])
def test_canonical_project_ref_passes_and_preserves_original_project(field):
    goal = GoalSpec("继续学习 Agent 开发", project_context=PROJECT)
    validator = GoalRequirementProfileValidator()
    profile = validator.validate(output(field), goal=goal)
    fact = getattr(profile, field)[0]
    assert fact.source_refs == ("project_context",)
    assert profile.project_context == PROJECT
    assert profile.profile_hash == validator.validate(output(field), goal=goal).profile_hash
