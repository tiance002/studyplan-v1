"""会话存储（B2-V §六 骨架实现）：不透明令牌 → :class:`AuthContext`。

## 定位

V1 骨架使用**进程内**会话存储 + 显式注入，仅供开发与真实端到端测试使用。
它证明了「AuthContext 由服务端派生」这一条约束是可机械验证的：

- 客户端只能提供一个**不透明**令牌（Cookie）；
- 令牌到身份、到项目范围的映射只发生在服务端；
- 未注册的令牌解析为 ``None``（→ 401），不会退化成匿名上下文。

## 为什么不是"读请求头里的 actor_id"

那正是被禁止的做法：客户端自报身份等于没有认证。真实部署应把本类替换为
**受签名/加密保护**的会话存储（HttpOnly + SameSite + 服务端会话表），
见 B2-V 报告的 B3 输入。

## 边界

本模块**不**实现登录、口令校验、会话轮换与撤销 —— 那些属于认证域，
不在本 Goal 范围。它只做「已建立的会话 → 授权上下文」的确定性解析。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.core.config import Settings
from app.core.errors import DependencyUnavailableError
from app.domain.workspace.models import AuthContext

__all__ = ["InMemorySessionStore", "SessionRecord"]


def validate_local_binding(settings: Settings) -> None:
    """Only explicit server configuration may select an existing identity/project."""
    actor, project = settings.local_actor_id, settings.local_project_id
    if (not actor or actor != actor.strip() or actor == "local_actor"
            or any(c in actor for c in ",;\r\n")
            or not project or project != project.strip() or project == "local_project"
            or actor not in settings.planning_worker_actor_ids):
        raise DependencyUnavailableError(
            "本地入口绑定不可用：请在本机确认 STUDYPLAN_LOCAL_ACTOR_ID、"
            "STUDYPLAN_LOCAL_PROJECT_ID 与 PLANNING_WORKER_ACTOR_IDS；不会创建新身份"
        )


@dataclass(frozen=True, slots=True)
class SessionRecord:
    """一条已建立的服务端会话。"""

    token: str
    actor_id: str
    session_id: str
    learning_project_scope: tuple[str, ...] = ()
    issued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if not self.token or not self.actor_id or not self.session_id:
            raise ValueError("会话缺少 token / actor_id / session_id")

    def to_auth_context(self) -> AuthContext:
        """派生授权上下文。

        项目范围来自**服务端会话**，而不是请求体：这正是「不得接受客户端
        传入项目授权」的实现方式。
        """
        return AuthContext(
            actor_id=self.actor_id,
            session_id=self.session_id,
            issued_at=self.issued_at,
            learning_project_scope=self.learning_project_scope,
        )


class InMemorySessionStore:
    """进程内会话存储，实现 :class:`~app.ports.sessions.SessionResolverPort`。"""

    def __init__(self, sessions: tuple[SessionRecord, ...] = ()) -> None:
        self._by_token: dict[str, SessionRecord] = {s.token: s for s in sessions}

    def add(self, session: SessionRecord) -> None:
        """登记/覆盖一条会话（测试与骨架装配使用）。"""
        self._by_token[session.token] = session

    def resolve(self, session_token: str) -> AuthContext | None:
        if not session_token:
            return None
        record = self._by_token.get(session_token)
        return record.to_auth_context() if record is not None else None
