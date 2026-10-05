"""Closed coaching contract. Messages are never formal learning artifacts."""
import json

from app.core.errors import ValidationAppError
from app.core.ids import content_hash
from app.domain.summaries import review_manifest, review_manifest_intact

ASSISTANT_PROTOCOL = "assistant-coaching-v1"
ASSISTANT_PURPOSE = "assistant.coach"
INPUT_LIMIT = 42000


def validate_message(intent, content):
    if (intent not in {"work_draft", "question"} or not isinstance(content, str)
            or not content.strip() or len(content) > 20000 or "\x00" in content
            or any(0xD800 <= ord(c) <= 0xDFFF for c in content)):
        raise ValidationAppError("请选择工作稿或追问，并输入不超过20000字的有效原文")
    return content


def validate_reply(value):
    if (not isinstance(value, dict) or set(value) != {"reply"}
            or not isinstance(value["reply"], str) or not value["reply"].strip()
            or len(value["reply"]) > 16000 or "\x00" in value["reply"]
            or any(0xD800 <= ord(c) <= 0xDFFF for c in value["reply"])):
        return ["reply 必须是唯一字段且为非空、有界的 Markdown 文本"]
    return []


def build_input(mode, context, draft, trigger, history):
    # Only completed turns from this conversation enter history. Immutable
    # identities let us remove duplication without comparing private text.
    omitted = {trigger["message_id"]}
    if draft:
        omitted.add(draft["message_id"])
    recent = [dict(role=m["role"], content=m["content"], message_id=m["message_id"])
              for m in history[-12:] if m["message_id"] not in omitted]
    result = dict(mode=mode, context=context, work_draft=draft,
                  current_message={k: trigger[k] for k in ("message_id", "intent", "content")}, history=recent)
    if len(json.dumps(result, ensure_ascii=False)) > INPUT_LIMIT:
        raise ValidationAppError("本轮原文、工作稿和上下文超过输入上限；请明确缩短后再发送")
    return result


def assistant_manifest(binding):
    body = review_manifest(binding, protocol=ASSISTANT_PROTOCOL)
    body.pop("manifest_hash")
    body["input_limit"] = INPUT_LIMIT
    return dict(body, manifest_hash=content_hash(body))


def manifest_intact(value):
    if not (review_manifest_intact(value, protocol=ASSISTANT_PROTOCOL)
            and value.get("input_limit") == INPUT_LIMIT):
        return False
    from app.application.planning_budget import BudgetPolicy
    try:
        policy = BudgetPolicy(**value["budget_policy"])
    except (KeyError, TypeError, ValidationAppError):
        return False
    return value["output_cap"] == min(policy.practice, policy.deployment_cap, policy.model_cap)
