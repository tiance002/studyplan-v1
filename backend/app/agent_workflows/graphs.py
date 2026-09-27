"""三张图的构建器。

设计约束（SOFTWARE_DESIGN.md §4 / ADR-0005）：

- 三张小图：``planning_graph``（唯一可 interrupt）、``summary_review_graph``、
  ``prompt_review_graph``。
- 只有**多步生成 / 有限修复 / 外部评审**的任务用 Graph；
  普通 CRUD 与状态机用应用服务，**不包 Graph**。
- 成果验收先用普通业务服务 + 按需模型调用，**不建第四张空图**。

**B1 实现说明**：本模块在**有 langgraph 时**构建真实 ``StateGraph``；
在 langgraph 未安装时（例如最小 CI 环境）退化为一个**同构的解释器**，
使「状态转移与路由」这一层的逻辑仍可被测试。

这样做的理由：图的核心风险在于**转移逻辑**（修复次数上限、interrupt
位置、取消后不得发布），而不是框架 API 调用。把这些逻辑写成可独立测试的
纯函数，得到框架后再用 ``StateGraph`` 装配，是风险最低的顺序。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from app.agent_workflows.nodes import (
    ROUTE_COMMIT,
    ROUTE_FAIL,
    ROUTE_REPAIR,
    PlanningNodes,
    route_after_decision,
    route_after_validate,
)
from app.agent_workflows.state import PlanningState, ReviewState
from app.agent_workflows.validators import MAX_REPAIR_ATTEMPTS

try:  # pragma: no cover - 取决于环境是否安装 langgraph
    from langgraph.graph import END, START, StateGraph  # type: ignore[import-not-found]
    from langgraph.types import interrupt  # type: ignore[import-not-found]

    LANGGRAPH_AVAILABLE = True
except Exception:  # noqa: BLE001 - 未安装 langgraph 时正常退化
    END = "__end__"  # type: ignore[assignment]
    START = "__start__"  # type: ignore[assignment]
    StateGraph = None  # type: ignore[assignment]
    interrupt = None  # type: ignore[assignment]
    LANGGRAPH_AVAILABLE = False


# ---------------------------------------------------------------------------
# 纯解释器：不依赖 langgraph，用于机械验证转移逻辑
# ---------------------------------------------------------------------------


@dataclass
class PlanningTrace:
    """一次规划图执行的轨迹（用于测试断言）。"""

    visited: list[str]
    state: PlanningState
    stopped_at: str | None = None  # 停在哪个节点（通常是 await_approval）
    failed_errors: list[str] | None = None


def run_planning_graph(
    nodes: PlanningNodes,
    initial: PlanningState,
    *,
    resume_decision: str | None = None,
    max_steps: int = 50,
) -> PlanningTrace:
    """planning_graph 的确定性解释器。

    与 ``StateGraph`` 的转移顺序**逐条对应**，使路由逻辑可在无框架环境下
    被单元测试机械证明。``resume_decision`` 模拟 ``Command(resume=...)``：
    为 ``None`` 时执行到 ``await_approval`` 即**停下**（模拟 interrupt），
    传入 ``approve``/``edit``/``cancel`` 时从该点继续。
    """
    state: PlanningState = dict(initial)  # type: ignore[assignment]
    visited: list[str] = []

    def merge(delta: dict[str, Any]) -> None:
        for key, value in delta.items():
            if key == "validation_errors":
                # 与 state.py 的 reducer 语义保持一致：累加。
                state["validation_errors"] = list(state.get("validation_errors") or []) + list(  # type: ignore[operator]
                    value or []
                )
            else:
                state[key] = value  # type: ignore[literal-required]

    def step(name: str, fn: Callable[[PlanningState], dict[str, Any]]) -> None:
        visited.append(name)
        merge(fn(state))

    step("normalize", nodes.normalize)

    if resume_decision is None:
        step("generate_outline", nodes.generate_outline)
        step("build_dependencies_and_units", nodes.build_dependencies_and_units)
        step("propose_practice", nodes.propose_practice)

        # 首次校验前先清空（normalize 可能已写入输入错误）。
        state["validation_errors"] = []

        steps = 0
        while True:
            steps += 1
            if steps > max_steps:
                raise RuntimeError("planning_graph 步数超限，可能存在路由环")
            step("validate", nodes.validate)
            errors = list(state.get("validation_errors") or [])
            route = route_after_validate(state)
            if route == "save_draft_projection":
                break
            if route == ROUTE_FAIL:
                step("record_failure", nodes.record_failure_node)
                return PlanningTrace(
                    visited=visited,
                    state=state,
                    stopped_at="failed_validation",
                    failed_errors=errors,
                )
            step("repair_content", nodes.repair_content)
            # 重新校验前清空上一轮错误：Graph State 的 reducer 是累加语义，
            # 若不重置，已修复的错误会永久留在列表里，使图永远无法通过校验。
            # （真实 StateGraph 中由 repair 节点返回完整新列表覆盖实现同等效果。）
            state["validation_errors"] = []

        step("save_draft_projection", nodes.save_draft_projection)
        # interrupt 点：停下，等待外部 resume。
        return PlanningTrace(visited=visited, state=state, stopped_at="await_approval")

    # ---- 恢复路径 ----
    state["decision"] = resume_decision
    step("apply_decision", nodes.apply_decision)
    route = route_after_decision(state)
    if route == "validate":
        while True:
            step("validate", nodes.validate)
            sub = route_after_validate(state)
            if sub == "save_draft_projection":
                step("save_draft_projection", nodes.save_draft_projection)
                break
            if sub == ROUTE_FAIL:
                errors = list(state.get("validation_errors") or [])
                step("record_failure", nodes.record_failure_node)
                return PlanningTrace(
                    visited=visited,
                    state=state,
                    stopped_at="failed_validation",
                    failed_errors=errors,
                )
            step("repair_content", nodes.repair_content)
            state["validation_errors"] = []
        route = ROUTE_COMMIT
    if route == ROUTE_COMMIT:
        step("commit_plan_idempotently", nodes.commit_plan_idempotently)
    return PlanningTrace(visited=visited, state=state, stopped_at=None)


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

    def merge(delta: dict[str, Any]) -> None:
        for key, value in delta.items():
            if key == "validation_errors":
                state["validation_errors"] = list(state.get("validation_errors") or []) + list(  # type: ignore[operator]
                    value or []
                )
            else:
                state[key] = value  # type: ignore[literal-required]

    visited.append("load_rubric_snapshot")
    merge(load_snapshot(state))
    visited.append("review_once")
    merge(review_once(state))
    visited.append("validate_review")
    errors = validate_review(state.get("review") or {})
    if errors:
        merge({"validation_errors": errors})
        return PlanningTrace(
            visited=visited,
            state=state,
            stopped_at="failed_validation",
            failed_errors=errors,
        )
    visited.append("persist_review_idempotently")
    state["result_id"] = persist_review(state)  # type: ignore[literal-required]
    return PlanningTrace(visited=visited, state=state, stopped_at=None)


# ---------------------------------------------------------------------------
# 真实 StateGraph 装配（langgraph 可用时）
# ---------------------------------------------------------------------------


def build_planning_graph(nodes: PlanningNodes) -> Any:
    """装配真实的 planning_graph ``StateGraph``。

    仅当 langgraph 可用时返回框架图；否则抛 ``RuntimeError``，
    提示调用方使用 ``run_planning_graph`` 解释器。
    """
    if not LANGGRAPH_AVAILABLE:
        raise RuntimeError(
            "langgraph 未安装，无法装配 StateGraph；"
            "B1 骨架可使用 run_planning_graph 解释器完成逻辑验证"
        )
    graph = StateGraph(PlanningState)
    graph.add_node("normalize", nodes.normalize)
    graph.add_node("generate_outline", nodes.generate_outline)
    graph.add_node("build_dependencies_and_units", nodes.build_dependencies_and_units)
    graph.add_node("propose_practice", nodes.propose_practice)
    graph.add_node("validate", nodes.validate)
    graph.add_node("repair_content", nodes.repair_content)
    graph.add_node("save_draft_projection", nodes.save_draft_projection)
    graph.add_node("await_approval", _await_approval)
    graph.add_node("apply_decision", nodes.apply_decision)
    graph.add_node("commit_plan_idempotently", nodes.commit_plan_idempotently)
    graph.add_node("cancel_draft", _cancel_draft)
    graph.add_node("record_failure", nodes.record_failure_node)

    graph.add_edge(START, "normalize")
    graph.add_edge("normalize", "generate_outline")
    graph.add_edge("generate_outline", "build_dependencies_and_units")
    graph.add_edge("build_dependencies_and_units", "propose_practice")
    graph.add_edge("propose_practice", "validate")
    graph.add_conditional_edges(
        "validate",
        route_after_validate,
        {
            "save_draft_projection": "save_draft_projection",
            ROUTE_REPAIR: "repair_content",
            ROUTE_FAIL: "record_failure",
        },
    )
    graph.add_edge("repair_content", "validate")
    graph.add_edge("save_draft_projection", "await_approval")
    graph.add_conditional_edges(
        "await_approval",
        route_after_decision,
        {
            ROUTE_COMMIT: "commit_plan_idempotently",
            "validate": "validate",
            "cancel_draft": "cancel_draft",
        },
    )
    graph.add_edge("commit_plan_idempotently", END)
    graph.add_edge("cancel_draft", END)
    graph.add_edge("record_failure", END)
    return graph.compile()


def _await_approval(state: PlanningState) -> dict[str, Any]:
    """独立等待节点。

    ``interrupt()`` **只**在这里调用；其前只做无副作用快照读取。
    恢复由业务接口鉴权后以 ``Command(resume=...)`` 驱动。
    """
    decision = interrupt(  # type: ignore[misc]
        {
            "kind": "plan_draft_approval",
            "draft_ref": state.get("draft_ref", ""),
            "draft_hash": state.get("draft_hash", ""),
            "options": ["approve", "edit", "cancel"],
        }
    )
    return {"decision": str(decision)}


def _cancel_draft(state: PlanningState) -> dict[str, Any]:
    """取消：草案被标记取消。

    **绝不允许** worker 稍后把它发布 —— 该保证由仓储层按状态过滤实现
    （见 ports/repository.py 的约束说明）。
    """
    return {"result_id": "", "decision": "cancel"}


__all__ = [
    "LANGGRAPH_AVAILABLE",
    "MAX_REPAIR_ATTEMPTS",
    "PlanningTrace",
    "build_planning_graph",
    "run_planning_graph",
    "run_review_graph",
]
