"""Position-scoped original revisions and single-dispatch reflection review."""
from dataclasses import asdict, dataclass

from app.core.errors import ValidationAppError
from app.core.ids import content_hash
from app.domain.enums import SummaryReviewConclusion
from app.domain.reflections.models import SummaryReview, evaluate_review_completeness

SUMMARY_PROTOCOL = "summary-review-v1"
SUMMARY_PURPOSE = "summary.review"


@dataclass(frozen=True)
class SummarySaveCommand:
    project_id: str
    plan_id: str
    stage_id: str
    unit_id: str
    content: str
    expected_version: int
    idempotency_key: str

    def __post_init__(self):
        for key in ("project_id", "plan_id", "stage_id", "unit_id", "idempotency_key"):
            value = getattr(self, key)
            if (not isinstance(value, str) or not value.strip() or len(value) > (128 if key == "idempotency_key" else 512)
                    or "\x00" in value or any(0xD800 <= ord(char) <= 0xDFFF for char in value)):
                raise ValidationAppError("总结位置或幂等键无效")
        if type(self.expected_version) is not int or self.expected_version < 0:
            raise ValidationAppError("总结版本无效")
        if not isinstance(self.content, str) or not self.content.strip() or len(self.content) > 20000:
            raise ValidationAppError("总结需为 1–20000 个字符的非空原文")
        if "\x00" in self.content or any(0xD800 <= ord(char) <= 0xDFFF for char in self.content):
            raise ValidationAppError("总结含无法保存的字符，请检查后重新保存")

    @property
    def position(self):
        return (self.project_id, self.plan_id, self.stage_id, self.unit_id)

    def input_hash(self):
        return content_hash({k: v for k, v in asdict(self).items() if k != "idempotency_key"})


def summary_manifest(binding):
    policy = binding.budget_policy
    body = {"protocol": SUMMARY_PROTOCOL, "model_ref": binding.model_ref, "max_requests": 1,
            "output_cap": min(policy.practice, policy.deployment_cap, policy.model_cap),
            "budget_policy": policy.as_dict(), "consent_to_model": True}
    return {**body, "manifest_hash": content_hash(body)}


def summary_manifest_intact(manifest):
    if not isinstance(manifest, dict):
        return False
    body = {k: v for k, v in manifest.items() if k != "manifest_hash"}
    return (body.get("protocol") == SUMMARY_PROTOCOL and type(body.get("max_requests")) is int and body.get("max_requests") == 1
            and type(body.get("output_cap")) is int and body["output_cap"] > 0
            and body.get("consent_to_model") is True and bool(body.get("model_ref"))
            and manifest.get("manifest_hash") == content_hash(body))


def validate_feedback(review):
    fields = {"conclusion", "covered", "gaps", "misconceptions", "questions"}
    if not isinstance(review, dict) or set(review) != fields:
        return ["反馈字段不符合约定"]
    if not isinstance(review["conclusion"], str) or review["conclusion"] not in {"satisfied", "needs_revision", "misconception"}:
        return ["反馈结论无效"]
    for name in fields - {"conclusion"}:
        values = review[name]
        if not isinstance(values, list) or len(values) > 20 or any(
            not isinstance(item, str) or not item.strip() or len(item) > 2000 or "\x00" in item
            or any(0xD800 <= ord(char) <= 0xDFFF for char in item) for item in values
        ):
            return ["反馈内容超出约定边界"]
    value = SummaryReview.create(attempt_id="validation", unit_id="validation", rubric_version=1,
        conclusion=SummaryReviewConclusion(review["conclusion"]), **{k: review[k] for k in fields - {"conclusion"}})
    return evaluate_review_completeness(value)


def review_rubric_context(snapshot):
    """Consent covers original + learning requirements, never private sources."""
    fields = ("unit_title", "unit_stable_key", "rubric_version", "objectives", "rubric", "plan_revision")
    result = {key: snapshot[key] for key in fields if key in snapshot}
    result["node_snapshot"] = [{key: node[key] for key in ("stable_key", "title", "objectives", "content_version") if key in node}
        for node in snapshot.get("node_snapshot", []) if isinstance(node, dict)]
    return result
