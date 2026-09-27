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

两者必须**行为一致**：真实 Graph 用真实 ``Command(resume=...)`` 驱动，
解释器用 ``resume_decision`` 参数模拟；同一测试场景会在两处运行并断言
关键结论相同（见 ``backend/tests/unit/test_graph_workflows.py`` 与
``backend/tests/integration/test_real_langgraph.py``）。

## B1 修复：确认流程正式接入执行路径

历史实现的真实 StateGraph **注册了 ``apply_decision`` 却没有把它接进边**：
``await_approval`` 直接条件路由到 commit/validate/cancel，决定从未经过
``apply_decision``，于是非法 decision、edit 的应用、cancel 的持久化
全部落空。本版修正为：

    await_approval
      -> apply_decision            （写决定语义、调应用层端口）
      -> route_after_decision
      -> commit / validate(重新校验) / cancel_draft
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from app.agent_workflows.nodes import (
    ROUTE_CANCEL,
    ROUTE_COMMIT,
    ROUTE_DRAFT,
    ROUTE_FAIL,
    ROUTE_REPAIR,
    ROUTE_VALIDATE,
    PlanningNodes,
    aggregate_errors,
    route_after_decision,
    route_after_generate,
    route_after_normalize,
    route_after_validate,
)
from app.agent_workflows.state import PlanningState, ReviewState
from app.agent_workflows.validators import MAX_REPAIR_ATTEMPTS

try:  # pragma: no cover - 取决于环境是否安装 langgraph
    from langgraph.graph import END, START, StateGraph  # type: ignore[import-not-found]
    from langgraph.types import Command, interrupt  # type: ignore[import-not-found]

    LANGGRAPH_AVAILABLE = True
except Exception:  # noqa: BLE001 - 未安装 langgraph 时正常退化
    END = "__end__"  # type: ignore[assignment]
    START = "__start__"  # type: ignore[assignment]
    Command = None  # type: ignore[assignment,misc]
    StateGraph = None  # type: ignore[assignment,misc]
    interrupt = None  # type: ignore[assignment]
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


def _run_generate_and_repair_loop(
    nodes: PlanningNodes,
    state: PlanningState,
    visited: list[str],
    *,
    max_steps: int,
) -> PlanningTrace | None:
    """生成 + 校验 + 有界修复循环。返回失败轨迹，或 None 表示通过。

    与真实 StateGraph 的等价性：真实图中 ``validate`` 通过后走
    ``save_draft_projection``；这里返回 None 由调用方继续。
    """
    steps = 0
    while True:
        steps += 1
        if steps > max_steps:
            raise RuntimeError("planning_graph 步数超限，可能存在路由环")
        visited.append("validate")
        _merge(state, nodes.validate(state))
        route = route_after_validate(state)
        if route == ROUTE_DRAFT:
            return None
        if route == ROUTE_FAIL:
            visited.append("record_failure")
            _merge(state, nodes.record_failure_node(state))
            return PlanningTrace(
                visited=visited,
                state=state,
                stopped_at="failed_validation",
                failed_errors=list(state.get("validation_errors") or []),
            )
        visited.append("repair_content")
        _merge(state, nodes.repair_content(state))


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

    visited.append("normalize")
    _merge(state, nodes.normalize(state))

    if resume_decision is None:
        if route_after_normalize(state) == ROUTE_FAIL:
            visited.append("record_failure")
            _merge(state, nodes.record_failure_node(state))
            return PlanningTrace(
                visited=visited,
                state=state,
                stopped_at="failed_validation",
                failed_errors=list(state.get("validation_errors") or []),
            )

        visited.append("generate_outline")
        _merge(state, nodes.generate_outline(state))
        visited.append("build_dependencies_and_units")
        _merge(state, nodes.build_dependencies_and_units(state))
        visited.append("propose_practice")
        _merge(state, nodes.propose_practice(state))

        if route_after_generate(state) == ROUTE_FAIL:
            visited.append("record_failure")
            _merge(state, nodes.record_failure_node(state))
            return PlanningTrace(
                visited=visited,
                state=state,
                stopped_at="failed_validation",
                failed_errors=list(state.get("validation_errors") or []),
            )

        failure = _run_generate_and_repair_loop(nodes, state, visited, max_steps=max_steps)
        if failure is not None:
            return failure

        visited.append("save_draft_projection")
        _merge(state, nodes.save_draft_projection(state))
        # interrupt 点：停下，等待外部 resume。
        return PlanningTrace(visited=visited, state=state, stopped_at="await_approval")

    # ---- 恢复路径：真实图中由 Command(resume=...) 驱动 ----
    state["decision"] = resume_decision
    visited.append("apply_decision")
    _merge(state, nodes.apply_decision(state))
    route = route_after_decision(state)
    if route == ROUTE_FAIL:
        visited.append("record_failure")
        _merge(state, nodes.record_failure_node(state))
        return PlanningTrace(
            visited=visited,
            state=state,
            stopped_at="failed_validation",
            failed_errors=list(state.get("validation_errors") or []),
        )
    if route == ROUTE_VALIDATE:
        # edit：应用编辑后**重新校验**；通过则保存新草案并**重新等待确认**。
        failure = _run_generate_and_repair_loop(nodes, state, visited, max_steps=max_steps)
        if failure is not None:
            return failure
        visited.append("save_draft_projection")
        _merge(state, nodes.save_draft_projection(state))
        return PlanningTrace(visited=visited, state=state, stopped_at="await_approval")
    if route == ROUTE_COMMIT:
        visited.append("commit_plan_idempotently")
        _merge(state, nodes.commit_plan_idempotently(state))
        return PlanningTrace(visited=visited, state=state, stopped_at=None)
    # cancel
    visited.append("cancel_draft")
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
# 真实 StateGraph 装配（langgraph 可用时）
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
            "checkpoint 缺少 graph_version，无法确认可安全恢复；请重新发起规划"
        )
    if checkpoint_graph_version != current_graph_version:
        raise GraphVersionMismatchError(
            f"图版本不一致：checkpoint={checkpoint_graph_version!r}，"
            f"当前={current_graph_version!r}；请重新发起规划而不是恢复旧断点"
        )


class GraphVersionMismatchError(RuntimeError):
    """图版本不一致：恢复被拒绝。

    **不得**被降级为"重新用旧状态跑一遍" —— 那会用错误的状态结构产出
    看似成功的计划，是最危险的失败模式。
    """


def build_planning_graph(nodes: PlanningNodes, *, checkpointer: Any = None) -> Any:
    """装配真实的 planning_graph ``StateGraph``。

    仅当 langgraph 可用时返回框架图；否则抛 ``RuntimeError``，
    提示调用方使用 ``run_planning_graph`` 解释器。

    图的执行路径与本模块解释器**逐节点对应**，特别是
    ``await_approval -> apply_decision -> route_after_decision``。
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
    graph.add_conditional_edges(
        "normalize",
        route_after_normalize,
        {"generate_outline": "generate_outline", ROUTE_FAIL: "record_failure"},
    )
    graph.add_edge("generate_outline", "build_dependencies_and_units")
    graph.add_edge("build_dependencies_and_units", "propose_practice")
    graph.add_conditional_edges(
        "propose_practice",
        route_after_generate,
        {ROUTE_VALIDATE: "validate", ROUTE_FAIL: "record_failure"},
    )
    graph.add_conditional_edges(
        "validate",
        route_after_validate,
        {
            ROUTE_DRAFT: "save_draft_projection",
            ROUTE_REPAIR: "repair_content",
            ROUTE_FAIL: "record_failure",
        },
    )
    graph.add_edge("repair_content", "validate")
    graph.add_edge("save_draft_projection", "await_approval")
    # 确认流程：await_approval 后**必须**经过 apply_decision 再路由。
    graph.add_edge("await_approval", "apply_decision")
    graph.add_conditional_edges(
        "apply_decision",
        route_after_decision,
        {
            ROUTE_COMMIT: "commit_plan_idempotently",
            ROUTE_VALIDATE: "validate",
            ROUTE_CANCEL: "cancel_draft",
            ROUTE_FAIL: "record_failure",
        },
    )
    graph.add_edge("commit_plan_idempotently", END)
    graph.add_edge("cancel_draft", END)
    graph.add_edge("record_failure", END)
    return graph.compile(checkpointer=checkpointer)


def _await_approval(state: PlanningState) -> dict[str, Any]:
    """独立等待节点。

    ``interrupt()`` **只**在这里调用；其前只做无副作用快照读取。
    恢复由业务接口鉴权后以 ``Command(resume=...)`` 驱动。

    ``resume`` 的值可以是：
    - 字符串 ``"approve"`` / ``"edit"`` / ``"cancel"``；
    - 结构化 dict：``{"decision": "edit", "edited_stages": [...],
      "idempotency_key": "...", "expected_version": 1, "draft_hash": "..."}``。

    结构化形式是 B2 的正式契约；字符串形式保留给最小测试与兼容。
    """
    decision = interrupt(  # type: ignore[misc]
        {
            "kind": "plan_draft_approval",
            "draft_ref": state.get("draft_ref", ""),
            "draft_hash": state.get("draft_hash", ""),
            "expected_version": state.get("expected_version", 0),
            "options": ["approve", "edit", "cancel"],
        }
    )
    delta: dict[str, Any] = {"decision": str(decision)}
    if isinstance(decision, dict):
        delta = {
            "decision": str(decision.get("decision", "")),
            "edited_stages": list(decision.get("edited_stages") or []),
            "decision_idempotency_key": str(decision.get("idempotency_key", "")),
            "expected_version": int(decision.get("expected_version", state.get("expected_version", 0)) or 0),
            "draft_hash": str(decision.get("draft_hash", state.get("draft_hash", ""))),
        }
    return delta


def _cancel_draft(state: PlanningState) -> dict[str, Any]:
    """取消：草案被标记取消。

    **绝不允许** worker 稍后把它发布 —— 该保证由仓储层按状态过滤实现
    （见 ports/repository.py 的约束说明）；本节点只保证图内不会进入提交。
    """
    return {"result_id": "", "decision": "cancel"}


__all__ = [
    "LANGGRAPH_AVAILABLE",
    "MAX_REPAIR_ATTEMPTS",
    "GraphVersionMismatchError",
    "PlanningTrace",
    "aggregate_errors",
    "assert_resumable",
    "build_planning_graph",
    "graph_thread_id",
    "run_planning_graph",
    "run_review_graph",
]
