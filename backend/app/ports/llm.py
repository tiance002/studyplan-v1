"""LLM 端口：唯一允许调用模型的形状。

设计要点（SOFTWARE_DESIGN.md §2 §5）：

- ``generate_structured`` 强制结构化输出。``schema_name`` 用于把请求与
  一份**可校验的 schema** 绑定；返回的 dict 由调用方按该 schema 校验。
- ``run_id`` + ``attempt_id`` 是**付费调用的账务标识**：
  同一 ``attempt_id`` 的结果必须可留存、可重放；已 dispatched 且结果未知时
  **不得**自动再发一次相同付费调用。
- 实现**不得**自动重试（见 ADR-0005 C8）；重试策略由应用层有界决定。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class LLMResult:
    """一次结构化生成的返回。

    ``raw_usage`` 只记录计量事实（tokens / cost），不含提示词原文，
    以便写入 ``ai_provider_attempts`` 而不泄露用户内容。
    """

    payload: dict[str, object]
    model_id: str
    provider: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_micros: int = 0
    latency_ms: int = 0
    finish_reason: str = "stop"
    attempts: int = 1


@dataclass(frozen=True, slots=True)
class LLMFailure:
    """一次失败的模型调用。

    ``retryable`` 表达"**是否可以安全重试**"，而不是"值不值得重试"。
    其结果未知的失败（如网络超时后上游可能已计费）必须为 ``False``，
    由应用层转入 ``reconciliation_required``。
    """

    error_class: str
    message: str
    retryable: bool = False
    dispatch_unknown: bool = False
    details: dict[str, object] = field(default_factory=dict)


class LLMDispatchUnknownError(RuntimeError):
    """Paid dispatch outcome unknown; reconcile before another call."""


class LLMUnavailableError(RuntimeError):
    """Provider 不可用。

    **禁止**被实现转换成"返回一个空但成功的 payload" —— 那会让上层
    以为模型真的产出了内容（设计 §2：Failure DTO 不准静默转成空成功）。
    """


@runtime_checkable
class LLMPort(Protocol):
    """结构化生成端口。

    实现可以是 Fake（测试）或真实云适配器（B3）。
    Fake **仅用于测试**，不得部署为真实评审能力。
    """

    def generate_structured(
        self,
        *,
        purpose: str,
        payload: dict[str, object],
        schema_name: str,
        run_id: str,
        attempt_id: str,
    ) -> LLMResult | LLMFailure: ...


__all__ = ["LLMFailure", "LLMPort", "LLMResult", "LLMUnavailableError"]
