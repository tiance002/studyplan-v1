"""Immutable task-position originals and explicit version exports."""

from dataclasses import asdict, dataclass

from app.core.errors import ValidationAppError
from app.core.ids import content_hash
from app.domain.practice.models import PromptRevision
from app.domain.summaries import review_manifest, review_manifest_intact

PROMPT_PROTOCOL = "prompt-review-v1"
PROMPT_PURPOSE = "prompt.review"


@dataclass(frozen=True)
class PromptSaveCommand:
    project_id: str
    plan_id: str
    stage_id: str
    task_id: str
    user_draft: str
    expected_version: int
    idempotency_key: str

    def __post_init__(self):
        for key in ("project_id", "plan_id", "stage_id", "task_id", "idempotency_key"):
            value = getattr(self, key)
            if (
                not isinstance(value, str)
                or not value.strip()
                or len(value) > (128 if key == "idempotency_key" else 512)
                or "\x00" in value
                or any(0xD800 <= ord(char) <= 0xDFFF for char in value)
            ):
                raise ValidationAppError("Prompt 位置或幂等键无效")
        if type(self.expected_version) is not int or self.expected_version < 0:
            raise ValidationAppError("Prompt 版本无效")
        PromptRevision.create(task_id=self.task_id, user_draft=self.user_draft, revision_no=1)

    @property
    def position(self):
        return (self.project_id, self.plan_id, self.stage_id, self.task_id)

    def input_hash(self):
        return content_hash({key: value for key, value in asdict(self).items() if key != "idempotency_key"})


def prompt_manifest(binding):
    return review_manifest(binding, protocol=PROMPT_PROTOCOL)


def prompt_manifest_intact(manifest):
    return review_manifest_intact(manifest, protocol=PROMPT_PROTOCOL)


def validate_prompt_feedback(review):
    if not isinstance(review, dict) or set(review) != {"strengths", "gaps", "suggestions"}:
        return ["Prompt 反馈字段不符合约定"]
    for values in review.values():
        if (
            not isinstance(values, list)
            or len(values) > 20
            or any(
                not isinstance(item, str)
                or not item.strip()
                or len(item) > 2000
                or "\x00" in item
                or any(0xD800 <= ord(char) <= 0xDFFF for char in item)
                for item in values
            )
        ):
            return ["Prompt 反馈内容无效或超出约定"]
    if not any(review.values()):
        return ["Prompt 反馈没有可用内容"]
    return []


def prompt_review_context(snapshot):
    # Deliberately omit main-project idea/title, URLs, source/notes and identities.
    # Current consent covers only this original + task/knowledge requirements.
    task = snapshot.get("task", {})
    result = {
        key: task[key] for key in ("title", "goal", "in_scope", "out_scope", "acceptance") if key in task
    }
    result["knowledge_links"] = [
        {key: link[key] for key in ("stable_key", "title", "role", "content_version") if key in link}
        for link in task.get("knowledge_links", [])
    ]
    v2 = task.get("v2_content")
    if isinstance(v2, dict):
        result["v2_requirements"] = {
            "stage_outcome_refs": v2["stage"]["outcome_refs"],
            "tasks": [{key:t[key] for key in ("outcome_refs","knowledge_refs","practice_kind","acceptance")}
                for t in v2["tasks"]]}
    return result


def implementation_export(revision):
    snapshot = revision["task_snapshot"]
    task = snapshot.get("task", {})
    project = snapshot.get("practice_project", {})
    parts = [
        f"# 实现 Prompt · 修订 {revision['revision_no']}",
        f"路线版本：{snapshot.get('plan_revision', '旧记录未保存')}",
        "\n## 实践项目",
        str(project.get("title", "当时项目未保存")),
        str(project.get("idea", "")),
        "\n## 阶段任务",
        str(task.get("title", "当时任务要求未保存")),
        str(task.get("goal", "")),
    ]
    for field, title in (("in_scope", "实施范围"), ("out_scope", "范围之外"), ("acceptance", "验收要求")):
        parts += ["\n## " + title, *("- " + str(item) for item in task.get(field, []))]
    parts += [
        "\n## 关联知识",
        *(
            f"- {link['title']}（{link['role']}，内容版 {link['content_version']}）"
            for link in task.get("knowledge_links", [])
        ),
        "\n以上仅为保存时的要求，不代表实施或验收已完成。",
        "\n## 用户原文",
        revision["user_draft"],
    ]
    return "\n".join(parts)
