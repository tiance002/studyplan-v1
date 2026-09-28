"""会话解析端口：把**服务端**会话令牌解析为 :class:`AuthContext`。

硬约束（SOFTWARE_DESIGN.md §7 / ADR-0004 第 4 条）：

    ``AuthContext`` 只能由服务端从**可信会话**派生。

API 层**绝不**接受客户端传入 ``actor_id`` / ``tenant_id`` / 项目授权；
客户端能提供的只有一个**不透明**令牌（通常是 HttpOnly Cookie）。
令牌 → 身份 → 项目范围的映射全部发生在服务端。

本端口**只读**：会话的建立（登录）属于认证域，不在本 Goal 范围。
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.domain.workspace.models import AuthContext


@runtime_checkable
class SessionResolverPort(Protocol):
    """把不透明会话令牌解析为授权上下文。"""

    def resolve(self, session_token: str) -> AuthContext | None:
        """解析令牌；无效/过期返回 ``None``（**不得**返回匿名上下文）。

        返回 ``None`` 而非「空 scope 的 AuthContext」是刻意的：
        前者由 API 层统一转成 401，后者可能被误当成"已登录但无项目"，
        从而把认证失败降级成授权失败。
        """
        ...


__all__ = ["SessionResolverPort"]
