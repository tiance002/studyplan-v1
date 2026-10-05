"""Closed coaching contract. Messages are never formal learning artifacts."""
import json

from app.core.errors import ValidationAppError
from app.core.ids import content_hash
from app.domain.summaries import review_manifest, review_manifest_intact

ASSISTANT_PROTOCOL = "assistant-coaching-v1"
ASSISTANT_PURPOSE = "assistant.coach"
INPUT_LIMIT = 42000
NATURAL_CHAT = "natural-chat-v11"


def project_reply(value):
    """Consume only presentation fields. Provider IDs never become authority.

    The original reply-only wire shape remains readable; explicit modern fields
    must satisfy the modern contract. This does not recover historical failed Runs.
    """
    if not isinstance(value, dict):
        raise ValidationAppError("助手回复必须是 JSON 对象")
    result = {"reply": value.get("reply"), "status": value.get("status", "continue"),
              "proposal": value.get("proposal")}
    for key, limit in (("reply", 16000), ("proposal", 20000)):
        text = result[key]
        if key == "proposal" and text is None:
            continue
        if (not isinstance(text, str) or not text.strip() or len(text) > limit
                or "\x00" in text or any(0xD800 <= ord(c) <= 0xDFFF for c in text)):
            raise ValidationAppError("助手文本必须非空、有界且有效")
    if (result["status"] not in ("continue", "ready_to_draft")
            or result["status"] == "continue" and result["proposal"] is not None
            or result["status"] == "ready_to_draft" and result["proposal"] is None
            or "status" not in value and "proposal" in value):
        raise ValidationAppError("助手候选稿状态不一致")
    return result


def validate_message(intent, content):
    if (intent not in {"work_draft", "question"} or not isinstance(content, str)
            or not content.strip() or len(content) > 20000 or "\x00" in content
            or any(0xD800 <= ord(c) <= 0xDFFF for c in content)):
        raise ValidationAppError("请选择工作稿或追问，并输入不超过20000字的有效原文")
    return content


def validate_reply(value):
    try:
        project_reply(value)
    except ValidationAppError as exc:
        return [str(exc)]
    return []


def build_input(mode, context, draft, trigger, history, *, natural=False, completed_rounds=None):
    # Only completed turns from this conversation enter history. Immutable
    # identities let us remove duplication without comparing private text.
    omitted = {trigger["message_id"]}
    if draft:
        omitted.add(draft["message_id"])
    recent = [dict(role=m["role"], content=m["content"], message_id=m["message_id"])
              for m in history[-12:] if m["message_id"] not in omitted]
    result = dict(mode=mode, context=context, work_draft=draft,
                  current_message={k: trigger[k] for k in ("message_id", "intent", "content")}, history=recent)
    if natural:
        result["dialogue_contract"] = NATURAL_CHAT
        # One whole-conversation count; never introduce per-issue counters.
        result["completed_rounds"] = completed_rounds if completed_rounds is not None else sum(m["role"] == "assistant" for m in history)
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
