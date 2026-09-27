"""幂等键处理。

规则（来自设计文档）：
- 同键同体 -> 返回同一结果，不重复产生副作用。
- 同键异体 -> 409 ``idempotency_conflict``。

本模块提供**存储无关**的判定逻辑；具体记录的持久化由 infrastructure 提供。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol

from app.core.errors import IdempotencyConflictError
from app.core.ids import content_hash, is_valid_operation_key


@dataclass(frozen=True, slots=True)
class IdempotencyRecord:
    """一次幂等操作的落库记录。"""

    scope_key: str
    body_hash: str
    response: dict[str, Any]
    status_code: int
    created_at: datetime
    expires_at: datetime

    def is_expired(self, *, now: datetime | None = None) -> bool:
        moment = now or datetime.now(timezone.utc)
        return moment >= self.expires_at


class IdempotencyStore(Protocol):
    """幂等记录存储端口。内存实现与 Postgres 实现共用同一契约测试。"""

    def get(self, scope_key: str) -> IdempotencyRecord | None: ...

    def put(self, record: IdempotencyRecord) -> None: ...


DEFAULT_TTL = timedelta(hours=24)


def build_scope_key(*, actor_id: str, operation: str, key: str) -> str:
    """幂等域 = 主体 + 操作 + 客户端提供的键。

    加上 actor_id 与 operation 是防止：A 用户的键与 B 用户碰撞，
    或同一键被复用到不同语义的操作上（如 generate 与 decision）。
    """
    if not is_valid_operation_key(key):
        raise IdempotencyConflictError("Idempotency-Key 格式非法")
    return f"{actor_id}:{operation}:{key}"


def fingerprint(body: Any) -> str:
    return content_hash(body)


def resolve(
    store: IdempotencyStore,
    *,
    scope_key: str,
    body: Any,
    now: datetime | None = None,
) -> dict[str, Any] | None:
    """查询是否可复用既有结果。

    - 命中且未过期且 body 一致 -> 返回原响应（调用方应直接复用，不再执行副作用）。
    - 命中但 body 不一致 -> 抛 409。
    - 未命中 / 已过期 -> 返回 None，调用方继续执行。
    """
    record = store.get(scope_key)
    if record is None or record.is_expired(now=now):
        return None

    incoming = fingerprint(body)
    if record.body_hash != incoming:
        raise IdempotencyConflictError(
            "同一 Idempotency-Key 已用于不同的请求体，请更换幂等键"
        )
    return record.response


def remember(
    store: IdempotencyStore,
    *,
    scope_key: str,
    body: Any,
    response: dict[str, Any],
    status_code: int = 200,
    ttl: timedelta = DEFAULT_TTL,
    now: datetime | None = None,
) -> IdempotencyRecord:
    moment = now or datetime.now(timezone.utc)
    record = IdempotencyRecord(
        scope_key=scope_key,
        body_hash=fingerprint(body),
        response=response,
        status_code=status_code,
        created_at=moment,
        expires_at=moment + ttl,
    )
    store.put(record)
    return record


@dataclass(slots=True)
class InMemoryIdempotencyStore:
    """骨架模式实现。生产用 Postgres 表 + 唯一约束。"""

    _records: dict[str, IdempotencyRecord] = field(default_factory=dict)

    def get(self, scope_key: str) -> IdempotencyRecord | None:
        return self._records.get(scope_key)

    def put(self, record: IdempotencyRecord) -> None:
        self._records[record.scope_key] = record
