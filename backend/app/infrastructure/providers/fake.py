"""Fake LLM 适配器：**仅用于测试与骨架运行**。

设计约束（SOFTWARE_DESIGN.md §2）：

    fake **不允许部署为真实评审能力**。

因此本模块刻意：

1. 由 ``LLM_PROVIDER=fake`` 显式开启，**不会**被真实配置误用；
2. 返回值带 ``provider="fake"``，可被上层与日志识别；
3. 未配置脚本时**明确失败**，而不是返回"看起来成功但内容空洞"的结果
   —— "静默成功"比"诚实失败"危险得多（旧工程 `ScriptedProvider`
   的设计教训，见 module-reuse-matrix.md §3 C7）。
"""

from __future__ import annotations

from typing import Callable

from app.ports.llm import LLMFailure, LLMResult

FakeHandler = Callable[[str, dict[str, object]], dict[str, object]]


class FakeLLM:
    """按 ``purpose`` 分发的确定性 Fake。

    ``handlers`` 是 ``purpose -> callable(purpose, payload) -> dict``。
    未注册的 purpose **抛错**，绝不返回空 dict。
    """

    def __init__(
        self,
        handlers: dict[str, FakeHandler] | None = None,
        *,
        model_id: str = "fake-structured-1",
    ) -> None:
        self._handlers = dict(handlers or {})
        self._model_id = model_id
        self.calls: list[tuple[str, str, str]] = []

    def register(self, purpose: str, handler: FakeHandler) -> None:
        self._handlers[purpose] = handler

    def generate_structured(
        self,
        *,
        purpose: str,
        payload: dict[str, object],
        schema_name: str,
        run_id: str,
        attempt_id: str,
    ) -> LLMResult | LLMFailure:
        self.calls.append((run_id, attempt_id, purpose))
        handler = self._handlers.get(purpose)
        if handler is None:
            # 明确失败：不返回空成功。上层据此进入 failed，而不是"生成了空计划"。
            return LLMFailure(
                error_class="fake_handler_missing",
                message=f"FakeLLM 未注册 purpose={purpose!r} 的处理器，拒绝返回空结果",
                retryable=False,
                dispatch_unknown=False,
                details={"schema_name": schema_name},
            )
        try:
            result = handler(purpose, payload)
        except Exception as exc:  # noqa: BLE001 - Fake 用于测试，需把异常转成 Failure DTO
            return LLMFailure(
                error_class="fake_handler_error",
                message=f"FakeLLM 处理器抛出异常：{type(exc).__name__}",
                retryable=False,
            )
        if not isinstance(result, dict):
            return LLMFailure(
                error_class="fake_bad_payload",
                message="FakeLLM 处理器必须返回 dict",
                retryable=False,
            )
        return LLMResult(
            payload=result,
            model_id=self._model_id,
            provider="fake",
            input_tokens=len(str(payload)) // 4,
            output_tokens=len(str(result)) // 4,
        )


def build_fake_llm(handlers: dict[str, FakeHandler] | None = None) -> FakeLLM:
    return FakeLLM(handlers)


__all__ = ["FakeHandler", "FakeLLM", "build_fake_llm"]
