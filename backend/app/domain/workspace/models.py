"""workspace 领域：用户身份引用、学习空间、成员授权。

关键约束：
- ``AuthContext`` 由**服务端**从可信会话生成，绝不接受前端请求体传入。
- 学习空间（LearningProject）是用户在平台的学习空间；
  实践项目（PracticeProject）在 practice 域，二者不是同一概念。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.core.errors import ForbiddenError, ValidationAppError
from app.core.ids import new_id, slugify_stable_key

MIN_USERNAME_LEN = 2
MAX_USERNAME_LEN = 32
MIN_PASSWORD_LEN = 15
MAX_PASSWORD_LEN = 128


@dataclass(frozen=True, slots=True)
class AuthContext:
    """服务端生成的授权上下文。

    这是所有应用服务的**第一个**入参。仓储查询必须带它，
    而不是接受调用方自报的 actor_id / tenant_id。
    """

    actor_id: str
    session_id: str
    issued_at: datetime
    learning_project_scope: tuple[str, ...] = ()

    def can_access_project(self, project_id: str) -> bool:
        return project_id in self.learning_project_scope

    def require_project(self, project_id: str) -> None:
        if not self.can_access_project(project_id):
            # 统一 403，不区分「不存在」与「无权限」，避免枚举探测。
            raise ForbiddenError("无权访问该项目")


@dataclass(slots=True)
class Actor:
    """平台用户。密码只存散列，本对象不持有明文。"""

    actor_id: str
    username: str
    display_name: str
    password_hash: str
    created_at: datetime
    is_active: bool = True


@dataclass(slots=True)
class LearningProject:
    """用户的学习空间。"""

    project_id: str
    owner_actor_id: str
    title: str
    goal_statement: str
    stable_key: str
    created_at: datetime
    updated_at: datetime
    version: int = 1
    archived_at: datetime | None = None

    @staticmethod
    def create(
        *,
        owner_actor_id: str,
        title: str,
        goal_statement: str,
        stable_key: str | None = None,
        now: datetime | None = None,
    ) -> "LearningProject":
        _require_text(title, "学习空间标题", max_len=120)
        _require_text(goal_statement, "学习目标", max_len=2000)
        moment = now or datetime.now(timezone.utc)
        key = stable_key or slugify_stable_key(title, fallback_prefix="proj")
        return LearningProject(
            project_id=new_id("lpr"),
            owner_actor_id=owner_actor_id,
            title=title.strip(),
            goal_statement=goal_statement.strip(),
            stable_key=key,
            created_at=moment,
            updated_at=moment,
        )

    @property
    def is_archived(self) -> bool:
        return self.archived_at is not None

    def rename(self, *, title: str, now: datetime | None = None) -> None:
        _require_text(title, "学习空间标题", max_len=120)
        self.title = title.strip()
        self.updated_at = now or datetime.now(timezone.utc)
        self.version += 1


@dataclass(slots=True)
class Membership:
    """用户与学习空间的授权关系。"""

    membership_id: str
    project_id: str
    actor_id: str
    role: str  # owner / editor / viewer
    created_at: datetime

    @staticmethod
    def create(
        *,
        project_id: str,
        actor_id: str,
        role: str = "owner",
        now: datetime | None = None,
    ) -> "Membership":
        if role not in {"owner", "editor", "viewer"}:
            raise ValidationAppError(f"非法的成员角色：{role}")
        return Membership(
            membership_id=new_id("mem"),
            project_id=project_id,
            actor_id=actor_id,
            role=role,
            created_at=now or datetime.now(timezone.utc),
        )


@dataclass(frozen=True, slots=True)
class CredentialPolicy:
    """V2 新设密码：15–128 Unicode 码点；已存密码验证单独兼容。"""

    username_min: int = MIN_USERNAME_LEN
    username_max: int = MAX_USERNAME_LEN
    password_min: int = MIN_PASSWORD_LEN
    password_max: int = MAX_PASSWORD_LEN
    require_invite_code: bool = False

    def validate_username(self, username: str) -> str:
        value = username.strip()
        if not (self.username_min <= len(value) <= self.username_max):
            raise ValidationAppError(
                f"用户名长度需在 {self.username_min}-{self.username_max} 之间"
            )
        if any(ch.isspace() for ch in value):
            raise ValidationAppError("用户名不能包含空白字符")
        return value

    def validate_password(self, password: str) -> str:
        return self._validate_password(password, self.password_min)

    def validate_login_password(self, password: str) -> str:
        return self._validate_password(password, 1)

    def _validate_password(self, password: str, minimum: int) -> str:
        if not (minimum <= len(password) <= self.password_max):
            raise ValidationAppError(
                f"密码长度需在 {minimum}-{self.password_max} 个字符之间"
            )
        try:
            password.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ValidationAppError("密码含非法字符") from exc
        return password


DEFAULT_CREDENTIAL_POLICY = CredentialPolicy()


def _require_text(value: str, field: str, *, max_len: int) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValidationAppError(f"{field}不能为空")
    if len(value) > max_len:
        raise ValidationAppError(f"{field}长度不得超过 {max_len} 字符")


@dataclass(slots=True)
class WorkspaceSummary:
    """学习空间概览：用于前端首页，不含图内部信息。"""

    project_id: str
    title: str
    goal_statement: str
    current_plan_id: str | None
    version: int
    extra: dict[str, object] = field(default_factory=dict)


__all__ = [
    "DEFAULT_CREDENTIAL_POLICY",
    "MAX_PASSWORD_LEN",
    "MAX_USERNAME_LEN",
    "MIN_PASSWORD_LEN",
    "MIN_USERNAME_LEN",
    "Actor",
    "AuthContext",
    "CredentialPolicy",
    "LearningProject",
    "Membership",
    "WorkspaceSummary",
]
