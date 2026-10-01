"""Ordinary user-proposed resource replacement, without an AI Run."""
from dataclasses import dataclass

from app.core.errors import ValidationAppError
from app.core.ids import content_hash


@dataclass(frozen=True, slots=True)
class ResourceChangeCommand:
    project_id: str
    plan_id: str
    stage_id: str
    assignment_id: str
    source_ref: str
    source_version: int
    section_refs: tuple[str, ...]
    expected_version: int
    copy_policy: str
    idempotency_key: str

    def __post_init__(self):
        for field in ("project_id", "plan_id", "stage_id", "assignment_id", "source_ref", "idempotency_key"):
            value = getattr(self, field)
            if not isinstance(value, str) or not value.strip() or len(value) > (128 if field == "idempotency_key" else 512):
                raise ValidationAppError("资源替换标识不合法", field=field)
        if type(self.expected_version) is not int or self.expected_version < 0:
            raise ValidationAppError("expected_version 必须为非负整数")
        if type(self.source_version) is not int or self.source_version < 1:
            raise ValidationAppError("请选择明确的资源版本")
        if self.copy_policy not in {"copy_active", "keep_history_only"}:
            raise ValidationAppError("必须明确选择私人资料沿用策略")
        if not self.section_refs or len(set(self.section_refs)) != len(self.section_refs):
            raise ValidationAppError("章节选择不可为空或重复")
        for section in self.section_refs:
            if not isinstance(section, str) or not section.strip() or len(section) > 512:
                raise ValidationAppError("章节标识不合法")

    def input_hash(self):
        return content_hash({"project_id": self.project_id, "plan_id": self.plan_id,
            "stage_id": self.stage_id, "assignment_id": self.assignment_id,
            "source_ref": self.source_ref, "source_version": self.source_version,
            "section_refs": self.section_refs, "expected_version": self.expected_version,
            "copy_policy": self.copy_policy})
