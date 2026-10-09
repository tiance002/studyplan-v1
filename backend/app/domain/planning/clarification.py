"""Small initial clarification bindings; no dispatch, retry or goal rewriting."""

from copy import deepcopy
from json import loads

from app.core.errors import ValidationAppError
from app.core.ids import canonical_json, content_hash

MAX_ANSWER_ROUNDS = 2


def sealed(value):
    value = loads(canonical_json(value))
    value["context_hash"] = content_hash(value)
    return value


def intact(value):
    return type(value) is dict and value.get("context_hash") == content_hash(
        {k: v for k, v in value.items() if k != "context_hash"}
    )


def answer_input(value):
    """Return isolated, explicitly low-trust Item1 input or reject its shape."""
    if type(value) is not dict or set(value) != {"answers", "retained_facts"}:
        raise ValidationAppError("澄清输入结构无效")
    answers, facts = value["answers"], value["retained_facts"]
    if type(answers) is not list or not 1 <= len(answers) <= 6:
        raise ValidationAppError("澄清答案数量无效")
    seen = set()
    for index, item in enumerate(answers):
        if (
            type(item) is not dict
            or set(item)
            != {"question_id", "question_text", "answer_text", "clarification_version", "source_ref"}
            or type(item["clarification_version"]) is not int
            or not 1 <= item["clarification_version"] <= 2
            or item["source_ref"] != f"clarification.answers[{index}]"
            or any(
                type(item[k]) is not str or not item[k].strip() or len(item[k]) > limit
                for k, limit in (("question_id", 80), ("question_text", 500), ("answer_text", 2000))
            )
            or item["question_id"] in seen
        ):
            raise ValidationAppError("澄清答案来源或内容无效")
        seen.add(item["question_id"])
    versions = [item["clarification_version"] for item in answers]
    if versions != sorted(versions) or versions[0] != 1 or any(versions.count(v) > 3 for v in (1, 2)):
        raise ValidationAppError("澄清轮次或每轮问题数无效")
    if type(facts) is not dict or set(facts) != {"hard_constraints", "learner_claims"}:
        raise ValidationAppError("澄清已有事实无效")
    for values in facts.values():
        if type(values) is not list or len(values) > 20:
            raise ValidationAppError("澄清已有事实无效")
        for fact in values:
            if (
                type(fact) is not dict
                or set(fact) != {"text", "source_refs"}
                or type(fact["text"]) is not str
                or not fact["text"].strip()
                or len(fact["text"]) > 2000
                or type(fact["source_refs"]) is not list
                or not 1 <= len(fact["source_refs"]) <= 10
                or any(type(ref) is not str for ref in fact["source_refs"])
            ):
                raise ValidationAppError("澄清已有事实无效")
    return deepcopy(value)


def answers_for_questions(answers, questions):
    if type(answers) is not list or not 1 <= len(answers) <= 3:
        raise ValidationAppError("请回答本轮全部澄清问题")
    normalized = {}
    for item in answers:
        if (
            type(item) is not dict
            or set(item) != {"question_id", "answer_text"}
            or type(item["question_id"]) is not str
            or item["question_id"] in normalized
            or type(item["answer_text"]) is not str
            or not item["answer_text"].strip()
            or len(item["answer_text"]) > 2000
        ):
            raise ValidationAppError("澄清答案无效")
        normalized[item["question_id"]] = item["answer_text"].strip()
    if set(normalized) != {q["question_id"] for q in questions}:
        raise ValidationAppError("澄清问题身份已变化或不存在")
    return [{"question_id": q["question_id"], "answer_text": normalized[q["question_id"]]} for q in questions]
