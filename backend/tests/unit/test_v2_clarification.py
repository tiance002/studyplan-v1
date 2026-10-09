"""Bounded Item1 user facts; source membership and prior facts stay authoritative."""

import pytest
from app.application.goal_requirement_analysis import GoalRequirementAnalyzer
from app.core.errors import ValidationAppError
from app.domain.planning.goal_requirements import GoalRequirementProfileValidator
from app.domain.planning.intent import GoalSpec
from app.ports.llm import LLMResult

from backend.tests.unit.test_goal_requirement_analysis import output


def test_answers_enter_item1_with_original_goal_and_real_source_refs():
    goal = GoalSpec("学习MCP", starting_point="会Python", constraints=("免费",), project_context="已有项目")
    previous = GoalRequirementProfileValidator().validate(
        output(
            hard_constraints=[{"text": "免费", "source_refs": ["goal.constraints[0]"]}],
            learner_claims=[{"text": "会Python", "source_refs": ["goal.starting_point"]}],
            status="needs_clarification",
            clarification_questions=["目标产物是什么？"],
        ),
        goal=goal,
    )
    clarification = {
        "answers": [
            {
                "question_id": "question_test",
                "question_text": "目标产物是什么？",
                "answer_text": "本地工具",
                "clarification_version": 1,
                "source_ref": "clarification.answers[0]",
            }
        ],
        "retained_facts": {
            "hard_constraints": [{"text": "免费", "source_refs": ["goal.constraints[0]"]}],
            "learner_claims": [{"text": "会Python", "source_refs": ["goal.starting_point"]}],
        },
    }
    seen = []

    class Port:
        def generate_structured(self, **kw):
            seen.append(kw["payload"])
            return LLMResult(
                output(
                    required_requirements=[
                        {
                            "text": "本地工具",
                            "origin": "explicit",
                            "source_refs": ["clarification.answers[0]"],
                            "rationale": "",
                        }
                    ],
                    hard_constraints=clarification["retained_facts"]["hard_constraints"],
                    learner_claims=clarification["retained_facts"]["learner_claims"],
                ),
                "fake",
                "fixture",
            )

    result = GoalRequirementAnalyzer(Port()).analyze(
        goal, run_id="run_test", attempt_id="goal-analysis", clarification=clarification
    )
    assert result.status == "ready"
    assert result.project_context == goal.project_context and result.starting_point == goal.starting_point
    assert seen[0]["clarification"]["answers"][0]["answer_text"] == "本地工具"
    assert tuple(seen[0]["goal"]["constraints"]) == ("免费",)
    assert previous.learner_claims == result.learner_claims
    for bad in ("clarification.answers[1]", "question_fake", "system"):
        raw = output(
            required_requirements=[
                {"text": "产物", "origin": "explicit", "source_refs": [bad], "rationale": ""}
            ],
            hard_constraints=clarification["retained_facts"]["hard_constraints"],
            learner_claims=clarification["retained_facts"]["learner_claims"],
        )
        with pytest.raises(ValidationAppError):
            GoalRequirementProfileValidator().validate(raw, goal=goal, clarification=clarification)
    for field in ("hard_constraints", "learner_claims"):
        raw = output(
            hard_constraints=clarification["retained_facts"]["hard_constraints"],
            learner_claims=clarification["retained_facts"]["learner_claims"],
        )
        raw[field] = []
        with pytest.raises(ValidationAppError):
            GoalRequirementProfileValidator().validate(raw, goal=goal, clarification=clarification)
