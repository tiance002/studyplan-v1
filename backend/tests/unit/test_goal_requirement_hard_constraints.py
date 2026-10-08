"""Constraint prompt wiring and structural fixtures; real semantic eval is pending."""
import json
from copy import deepcopy

import httpx
import pytest
from app.application.goal_requirement_analysis import GoalRequirementAnalyzer
from app.core.errors import ValidationAppError
from app.domain.planning.goal_requirements import GoalRequirementProfileValidator
from app.domain.planning.intent import GoalSpec
from app.infrastructure.providers.openai_compatible import OpenAICompatibleLLM


def fact(text, *refs):
    return {"text": text, "source_refs": list(refs)}


def wire(target, constraints=(), claims=(), *, status="ready", questions=()):
    return {"schema_version": 1, "target_summary": target,
            "required_requirements": [{"text": target, "origin": "explicit", "source_refs": ["goal.target"],
                                       "rationale": ""}],
            "hard_constraints": list(constraints), "learner_claims": list(claims),
            "clarification_questions": list(questions), "status": status}


def cases():
    readonly = GoalSpec("做一个只读 GitHub Code Review Agent，不能修改代码", outcome_purpose="interview")
    free = GoalSpec("学习 Agent，只使用免费教程和本地文件")
    python = GoalSpec("我会 Python，想学习 Agent")
    structured = GoalSpec("学习 Agent", constraints=("教程正文必须免费", "项目不能写入远程服务"))
    merged = GoalSpec("做只读 Code Review Agent", constraints=("项目只读，不能修改代码",))
    plain = GoalSpec("学习 Agent 开发")
    conflict = GoalSpec("做一个不能修改文件的 Agent", constraints=("Agent 必须写入文件",))
    return [
        (readonly, wire(readonly.target, [fact("只读，不能修改代码", "goal.target")])),
        (free, wire(free.target, [fact("只使用免费教程", "goal.target"), fact("只使用本地文件", "goal.target")])),
        (python, wire("学习 Agent", claims=[fact("我会 Python", "goal.target")])),
        (structured, wire(structured.target, [fact(text, f"goal.constraints[{i}]")
                                             for i, text in enumerate(structured.constraints)])),
        (merged, wire(merged.target, [fact(merged.constraints[0], "goal.target", "goal.constraints[0]")])),
        (plain, wire(plain.target)),
        (conflict, wire(conflict.target, [fact("不能修改文件", "goal.target"),
                                        fact(conflict.constraints[0], "goal.constraints[0]")],
                        status="needs_clarification", questions=["首版应保持只读，还是允许写入文件？"])),
    ]


@pytest.mark.parametrize("goal,raw", cases(), ids=["readonly-target", "free-local-target", "python-claim",
    "structured-verbatim", "equivalent-merged", "no-invented-limit", "conflict-kept"])
def test_correct_classification_fixtures_have_valid_refs_and_stable_identity(goal, raw):
    # Hand-authored expected classifications exercise representation/validation,
    # not the ability of a real model to derive these classifications.
    validator = GoalRequirementProfileValidator()
    profile = validator.validate(deepcopy(raw), goal=goal)
    replay = validator.validate(deepcopy(raw), goal=goal)
    assert [(x.text, x.source_refs) for x in profile.hard_constraints] == [
        (x["text"], tuple(sorted(x["source_refs"]))) for x in raw["hard_constraints"]]
    assert [(x.text, x.source_refs) for x in profile.learner_claims] == [
        (x["text"], tuple(sorted(x["source_refs"]))) for x in raw["learner_claims"]]
    assert profile.status == raw["status"]
    assert profile.clarification_questions == tuple(raw["clarification_questions"])
    assert profile.outcome_purpose == goal.outcome_purpose
    assert profile.profile_hash == replay.profile_hash
    assert profile.hard_constraints == replay.hard_constraints
    assert all(x.constraint_id.startswith("constraint_") for x in profile.hard_constraints)
    assert not {"stages", "resources", "capabilities"} & profile.to_payload().keys()


def test_real_transport_wires_explicit_constraint_extraction_guidance():
    goal, raw = cases()[0]
    calls = []

    def respond(request):
        calls.append(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(raw)},
                                                    "finish_reason": "stop"}]})

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        provider = OpenAICompatibleLLM(base_url="https://provider.example/v1", api_key="test-only",
                                        model="mock", client=client)
        result = GoalRequirementAnalyzer(provider).analyze(goal, run_id="constraint-test", attempt_id="one")
    assert len(calls) == 1 and result.hard_constraints[0].source_refs == ("goal.target",)
    system = calls[0]["messages"][0]["content"]
    # Lock only the new classification boundary, not every prompt sentence.
    assert "所有获准非空输入" in system
    assert "即使goal.constraints为空" in system
    assert "required_requirements和hard_constraints可表达同一事实" in system
    assert "text取结构化原文" in system
    assert "没有明确限制时hard_constraints为空" in system
    assert "冲突时保留两侧限制" in system
    context = json.loads(calls[0]["messages"][1]["content"])["context"]["goal"]
    assert context["target"] == goal.target and context["constraints"] == []


@pytest.mark.parametrize("fault", ["omit", "paraphrase", "wrong-ref"])
def test_structured_constraints_still_require_verbatim_text_and_indexed_ref(fault):
    goal = GoalSpec("只读 Agent", constraints=("不能修改代码",))
    raw = wire(goal.target, [fact(goal.constraints[0], "goal.target", "goal.constraints[0]")])
    if fault == "omit":
        raw["hard_constraints"] = []
    elif fault == "paraphrase":
        raw["hard_constraints"][0]["text"] = "不进行修改"
    else:
        raw["hard_constraints"][0]["source_refs"] = ["goal.target"]
    with pytest.raises(ValidationAppError):
        GoalRequirementProfileValidator().validate(raw, goal=goal)


def test_case2_missing_target_constraint_remains_a_semantic_eval_gap():
    goal, _ = cases()[0]
    # Mirrors the failure category: a requirement mentions read-only but no
    # hard constraint is emitted. Structure cannot prove natural-language intent.
    profile = GoalRequirementProfileValidator().validate(wire(goal.target), goal=goal)
    assert profile.status == "ready" and profile.hard_constraints == ()
    assert profile.required_requirements[0].text == goal.target
    # SEMANTIC_EVAL_REQUIRED: no keyword/NLP validator or fake model is added.
