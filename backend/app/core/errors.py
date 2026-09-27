"""统一错误模型与错误码。

错误视图固定包含 code / message / request_id / details。
不得回显敏感输入（原文总结、完整用户 Prompt、密钥、token）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    """对外稳定错误码。前端按此分支，不解析 message。"""

    VALIDATION_ERROR = "validation_error"
    UNAUTHENTICATED = "unauthenticated"
    FORBIDDEN = "forbidden"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    VERSION_CONFLICT = "version_conflict"
    IDEMPOTENCY_CONFLICT = "idempotency_conflict"
    UNPROCESSABLE = "unprocessable"
    RATE_LIMITED = "rate_limited"
    DEPENDENCY_UNAVAILABLE = "dependency_unavailable"
    RECONCILIATION_REQUIRED = "reconciliation_required"
    INTERNAL_ERROR = "internal_error"


#: 错误码 -> HTTP 状态码。统一映射，避免各处硬编码。
STATUS_BY_CODE: dict[ErrorCode, int] = {
    ErrorCode.VALIDATION_ERROR: 400,
    ErrorCode.UNAUTHENTICATED: 401,
    ErrorCode.FORBIDDEN: 403,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.CONFLICT: 409,
    ErrorCode.VERSION_CONFLICT: 409,
    ErrorCode.IDEMPOTENCY_CONFLICT: 409,
    ErrorCode.UNPROCESSABLE: 422,
    ErrorCode.RATE_LIMITED: 429,
    ErrorCode.DEPENDENCY_UNAVAILABLE: 503,
    ErrorCode.RECONCILIATION_REQUIRED: 409,
    ErrorCode.INTERNAL_ERROR: 500,
}


@dataclass(slots=True)
class AppError(Exception):
    """所有业务异常的基类。子类只补充语义，不改变错误体结构。"""

    code: ErrorCode
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    request_id: str | None = None

    def __post_init__(self) -> None:
        super().__init__(self.message)

    @property
    def http_status(self) -> int:
        return STATUS_BY_CODE.get(self.code, 500)

    def to_view(self, *, request_id: str | None = None) -> dict[str, Any]:
        return {
            "code": str(self.code),
            "message": self.message,
            "request_id": request_id or self.request_id or "",
            "details": self.details,
        }


class ValidationAppError(AppError):
    def __init__(self, message: str, **details: Any) -> None:
        super().__init__(ErrorCode.VALIDATION_ERROR, message, details)


class UnauthenticatedError(AppError):
    def __init__(self, message: str = "未登录或会话已过期") -> None:
        super().__init__(ErrorCode.UNAUTHENTICATED, message)


class ForbiddenError(AppError):
    def __init__(self, message: str = "无权访问该资源") -> None:
        super().__init__(ErrorCode.FORBIDDEN, message)


class NotFoundError(AppError):
    def __init__(self, message: str = "资源不存在") -> None:
        super().__init__(ErrorCode.NOT_FOUND, message)


class ConflictError(AppError):
    def __init__(self, message: str, **details: Any) -> None:
        super().__init__(ErrorCode.CONFLICT, message, details)


class VersionConflictError(AppError):
    def __init__(self, message: str = "版本已变化，请刷新后重试", **details: Any) -> None:
        super().__init__(ErrorCode.VERSION_CONFLICT, message, details)


class IdempotencyConflictError(AppError):
    def __init__(self, message: str = "同一幂等键携带了不同的请求体") -> None:
        super().__init__(ErrorCode.IDEMPOTENCY_CONFLICT, message)


class DependencyUnavailableError(AppError):
    """外部依赖不可用。只做明确降级，不伪造结果。"""

    def __init__(self, message: str, **details: Any) -> None:
        super().__init__(ErrorCode.DEPENDENCY_UNAVAILABLE, message, details)


class ReconciliationRequiredError(AppError):
    """付费调用上游结果未知。禁止自动重发，需人工核对或显式开启新尝试。"""

    def __init__(self, message: str = "上游结果未知，需人工核对", **details: Any) -> None:
        super().__init__(ErrorCode.RECONCILIATION_REQUIRED, message, details)
