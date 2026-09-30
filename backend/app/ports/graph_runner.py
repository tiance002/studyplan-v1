"""GraphRunner 端口：启动与恢复 LangGraph 工作流。

设计约束（SOFTWARE_DESIGN.md §2 §4 §5）：

- ``thread_id`` 由**服务端**创建并映射，**永不返回客户端**。
- 恢复必须**先鉴权**，且以当时的 ``graph_version`` 执行；
  同一线程的并发恢复必须**串行化**。
- 不同 graph version 的 waiting_user run 必须保持可恢复版本
  或明确安全终止，不能随部署升级直接重解释旧状态。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from app.domain.enums import GraphName
from app.ports.llm import LLMPort


@dataclass(frozen=True, slots=True)
class StartRequest:
    """启动一次图运行。"""

    run_id: str
    graph_name: GraphName
    graph_version: str
    thread_id: str
    project_id: str
    actor_id: str
    inputs: dict[str, object]


@dataclass(frozen=True, slots=True)
class ResumeRequest:
    """恢复一次等待中的图运行。"""

    run_id: str
    thread_id: str
    graph_version: str
    decision_id: str
    decision: dict[str, object]


class GraphRecoveryError(RuntimeError):
    """恢复失败（版本不匹配 / 断点不可读 / 并发恢复冲突）。"""


@runtime_checkable
class GraphRunnerPort(Protocol):
    """图运行端口。

    ``start`` 只负责推进到下一个稳定点（可能停在 ``interrupt``）；
    ``resume`` 只接受**业务接口已鉴权**的恢复请求。
    """

    def start(self, request: StartRequest) -> None: ...

    def resume(self, request: ResumeRequest) -> None: ...


__all__ = ["GraphRecoveryError", "GraphRunnerPort", "PlanningRuntime", "ResumeRequest", "StartRequest"]


class PlanningExecutorPort(Protocol):
    """Generation and acknowledgment of already committed business decisions."""

    def execute(self, nodes: Any, initial: Any, thread_id: str) -> Any: ...

    def execute_or_resume(
        self,
        nodes: Any,
        initial: Any,
        thread_id: str,
        graph_version: str,
        guard: Any,
        *,
        progress: Any = None,
    ) -> Any:
        """Run or resume one thread under its stored graph version.

        ``guard`` is a zero-argument callable revalidating the lease and Run status
        before each step and before every paid dispatch. ``progress`` is an
        optional ``Callable[[state], None]`` invoked once per committed checkpoint.
        """
        ...

    def finish(self, *, thread_id: str, graph_version: str, decision: str,
               result_id: str, draft_hash: str) -> None: ...
@dataclass(frozen=True)
class PlanningRuntime:
    llm: LLMPort
    executor: PlanningExecutorPort
