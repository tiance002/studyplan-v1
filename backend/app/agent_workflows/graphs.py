"""Shared review execution, trace and checkpoint version isolation.

The retired interrupt-based planning graph has no production builder here.
Historical graph safety scenarios live only in tests.helpers.retained_planning_graph.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from app.agent_workflows.state import PlanningState, ReviewState

try:  # pragma: no cover - 取决于环境是否安装 langgraph
    import langgraph.graph  # noqa: F401 - optional framework availability

    LANGGRAPH_AVAILABLE = True
except Exception:  # noqa: BLE001 - 未安装 langgraph 时正常退化
    LANGGRAPH_AVAILABLE = False


# ---------------------------------------------------------------------------
# 纯解释器：不依赖 langgraph，用于机械验证转移逻辑
# ---------------------------------------------------------------------------


@dataclass
class PlanningTrace:
    """一次规划图执行的轨迹（用于测试断言）。

    两张图（planning / review）共用本轨迹容器，状态类型取二者的并集。
    """

    visited: list[str]
    state: PlanningState | ReviewState
    stopped_at: str | None = None  # 停在哪个节点（await_approval / 失败）
    failed_errors: list[str] | None = None


def _merge(state: PlanningState | ReviewState, delta: dict[str, Any]) -> None:
    """覆盖语义合并。

    B1 修复后所有错误字段都是**普通覆盖字段**（不再用 ``operator.add``），
    因此这里逐键覆盖即可 —— 这正是"修复成功后旧错误消失"的关键。

    ``state`` 是 LangGraph 的 TypedDict 状态；运行期即普通 dict，
    这里以可变 dict 视角写入，避免两套状态类型互相牵扯。
    """
    mutable: dict[str, Any] = state  # type: ignore[assignment]
    mutable.update(delta)


def run_review_graph(
    *,
    review_once: Callable[[ReviewState], dict[str, Any]],
    load_snapshot: Callable[[ReviewState], dict[str, Any]],
    persist_review: Callable[[ReviewState], str],
    initial: ReviewState,
    validate_review: Callable[[dict[str, Any]], list[str]],
) -> PlanningTrace:
    """总结/Prompt 评审图的确定性解释器。

    两张图的形状相同（``load → review → validate → persist``），
    因此共用一个执行器，避免两份重复逻辑分别演化（设计 §2 禁止重复业务引擎）。
    """
    state: ReviewState = dict(initial)  # type: ignore[assignment]
    visited: list[str] = []

    visited.append("load_rubric_snapshot")
    _merge(state, load_snapshot(state))
    visited.append("review_once")
    _merge(state, review_once(state))
    visited.append("validate_review")
    errors = validate_review(dict(state.get("review") or {}))
    if errors:
        _merge(state, {"validation_errors": list(errors)})
        return PlanningTrace(
            visited=visited,
            state=state,
            stopped_at="failed_validation",
            failed_errors=list(errors),
        )
    visited.append("persist_review_idempotently")
    state["result_id"] = persist_review(state)  # type: ignore[literal-required]
    return PlanningTrace(visited=visited, state=state, stopped_at=None)


# ---------------------------------------------------------------------------
# Checkpoint 命名空间与版本隔离
# ---------------------------------------------------------------------------


def graph_thread_id(*, run_id: str, graph_version: str) -> str:
    """把 ``graph_version`` 编入 checkpoint 的 thread 命名空间。

    **为什么必须这样做**：LangGraph 的 checkpoint **只按 ``thread_id`` 索引**，
    ``configurable`` 里的其它键（包括 ``graph_version``）**不参与**命名。
    B1 审查发现：若直接把业务 run_id 当 thread_id，则升级图版本后，旧
    checkpoint 会被新图**静默恢复**，用一个已变更的状态结构跑出错的结果。

    因此 thread_id 必须显式包含版本，使不同版本的图在物理上无法碰撞。
    这比"在 resume 前礼貌地检查一下"更强：它把约定变成**不可能违反**的约束。
    """
    if not run_id:
        raise ValueError("run_id 不能为空")
    return f"{run_id}::{graph_version or '1'}"


def assert_resumable(
    *,
    checkpoint_graph_version: str | None,
    current_graph_version: str,
) -> None:
    """恢复前校验图版本一致；不一致时**显式失败**，不静默跑错版本。

    供应用层在 ``Command(resume=...)`` 之前调用。与 ``graph_thread_id`` 一起
    构成双重保险：命名空间隔离 + 显式校验。
    """
    if checkpoint_graph_version is None:
        raise GraphVersionMismatchError(
            "checkpoint 缺少 graph_version，无法确认可安全恢复"
        )
    if checkpoint_graph_version != current_graph_version:
        raise GraphVersionMismatchError(
            f"图版本不一致：checkpoint={checkpoint_graph_version!r}，"
            f"当前={current_graph_version!r}；不能恢复不匹配的旧断点"
        )


class GraphVersionMismatchError(RuntimeError):
    """图版本不一致：恢复被拒绝。

    **不得**被降级为"重新用旧状态跑一遍" —— 那会用错误的状态结构产出
    看似成功的计划，是最危险的失败模式。
    """


__all__ = [
    "LANGGRAPH_AVAILABLE",
    "GraphVersionMismatchError",
    "PlanningTrace",
    "assert_resumable",
    "graph_thread_id",
    "run_review_graph",
]
