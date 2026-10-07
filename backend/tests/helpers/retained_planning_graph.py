"""Retained test-only graph for repair, cancellation and checkpoint regressions.

The retired interrupt-based planning pipeline is not an application entry point.
This fixture retains existing safety assertions without exposing that builder in
production imports. No application module may import tests.helpers.
"""
from __future__ import annotations
from typing import Any
from app.agent_workflows.graphs import LANGGRAPH_AVAILABLE, PlanningTrace, _merge
from app.agent_workflows.nodes import (
    PlanningNodes, ROUTE_DRAFT, ROUTE_FAIL, ROUTE_VALIDATE, ROUTE_COMMIT,
    ROUTE_REPAIR, ROUTE_CANCEL, route_after_normalize, route_after_generate,
    route_after_validate, route_after_decision,
)
from app.agent_workflows.state import PlanningState
if LANGGRAPH_AVAILABLE:
    from langgraph.graph import END, START, StateGraph
    from langgraph.types import interrupt


class TransitionNodes(PlanningNodes):
    """Historical graph transition fixture, not the current frozen compiler.

    These pre-manifest scenarios test repair limits, error replacement, explicit
    decisions and callback ordering. They have no frozen source or receipts.
    Keep the snapshot callback used by those tests separate from production's
    checked_projection, which must reject exactly these markerless inputs.
    Current projection/source/receipt rejection is tested using PlanningNodes.
    """

    def save_draft_projection(self, state):
        from app.agent_workflows.nodes import _coerce_draft_result
        coerced = _coerce_draft_result(self.save_draft(state))
        delta = {"draft_ref": coerced["draft_ref"]}
        if coerced["draft_hash"]:
            delta["draft_hash"] = coerced["draft_hash"]
        return delta

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
