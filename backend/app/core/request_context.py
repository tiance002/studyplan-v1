"""请求上下文：request_id 贯穿日志、错误体与外部调用。

不得放入密钥或用户原文。request_id 可以在响应头与错误体中回传，
但必须与日志中的同名字段一致，便于跨服务排查。
"""

from __future__ import annotations

import contextvars
import logging
import time
import uuid
from contextlib import contextmanager
from typing import Any, Iterator

logger = logging.getLogger("studyplan.request")

_request_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default=""
)
_run_id: contextvars.ContextVar[str] = contextvars.ContextVar("run_id", default="")


def new_request_id() -> str:
    return f"req_{uuid.uuid4().hex[:20]}"


def set_request_id(request_id: str) -> contextvars.Token[str]:
    return _request_id.set(request_id)


def get_request_id() -> str:
    return _request_id.get()


def set_run_id(run_id: str) -> contextvars.Token[str]:
    return _run_id.set(run_id)


def get_run_id() -> str:
    return _run_id.get()


def reset_request_id(token: contextvars.Token[str]) -> None:
    _request_id.reset(token)


@contextmanager
def request_scope(request_id: str | None = None) -> Iterator[str]:
    """绑定一个 request_id 作用域。"""
    rid = request_id or new_request_id()
    token = set_request_id(rid)
    try:
        yield rid
    finally:
        reset_request_id(token)


@contextmanager
def bind_run(run_id: str) -> Iterator[None]:
    token = set_run_id(run_id)
    try:
        yield
    finally:
        _run_id.reset(token)


class LatencyTimer:
    """最小日志字段之一的 latency 采集器。"""

    __slots__ = ("_start",)

    def __init__(self) -> None:
        self._start = time.perf_counter()

    @property
    def elapsed_ms(self) -> int:
        return int((time.perf_counter() - self._start) * 1000)


def log_event(event: str, **fields: Any) -> None:
    """结构化日志。

    允许字段：request_id / run_id / graph_name / graph_version / node_name /
    attempt_id / provider / model_id / prompt_version / latency_ms /
    input_tokens / output_tokens / cost / error_class。

    禁止：原文总结、完整用户 Prompt、密钥、token、cookie。
    """
    payload: dict[str, Any] = {
        "event": event,
        "request_id": get_request_id(),
    }
    rid = get_run_id()
    if rid:
        payload["run_id"] = rid
    payload.update({k: v for k, v in fields.items() if v is not None})
    logger.info("studyplan_event", extra={"payload": payload})
