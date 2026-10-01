"""Progress belongs to a plan/unit position, independently of knowledge mastery."""
from dataclasses import dataclass
from uuid import NAMESPACE_URL, uuid5

from app.core.errors import ValidationAppError
from app.core.ids import canonical_json, content_hash
from app.domain.enums import UnitProgress, can_transition_progress


def exposure_id(project_id: str, plan_id: str, stage_id: str, unit_id: str) -> str:
    position = canonical_json([project_id, plan_id, stage_id, unit_id])
    return f"exp_{uuid5(NAMESPACE_URL, 'studyplan:exposure:' + position).hex}"


def require_transition(current: UnitProgress, target: UnitProgress) -> None:
    if not can_transition_progress(current, target):
        raise ValidationAppError("当前出现位置的进度不能这样变更", current=current.value, target=target.value)


@dataclass(frozen=True, slots=True)
class ExposureCommand:
    project_id: str
    plan_id: str
    stage_id: str
    unit_id: str
    status: UnitProgress
    expected_version: int
    idempotency_key: str

    def __post_init__(self):
        for field in ("project_id", "plan_id", "stage_id", "unit_id", "idempotency_key"):
            value = getattr(self, field)
            limit = 128 if field == "idempotency_key" else 512
            if not isinstance(value, str) or not value.strip() or len(value) > limit:
                raise ValidationAppError("进度命令标识不合法", field=field)
        if type(self.expected_version) is not int or self.expected_version < 0:
            raise ValidationAppError("expected_version 必须为非负整数")
        if not isinstance(self.status, UnitProgress):
            raise ValidationAppError("未知学习进度")

    @property
    def position(self) -> tuple[str, str, str, str]:
        return self.project_id, self.plan_id, self.stage_id, self.unit_id

    def input_hash(self) -> str:
        return content_hash({"position": self.position, "status": self.status.value,
                             "expected_version": self.expected_version})
