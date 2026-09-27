"""planning_graph：三张图中唯一可暂停等待用户的图。

流程（SOFTWARE_DESIGN.md §4）：

    START -> normalize -> generate_outline -> build_dependencies_and_units
          -> propose_practice -> validate -> [repair <= 2] -> save_draft_projection
          -> await_approval [interrupt] -> (cancel | edit+validate | approve)
          -> commit_plan_idempotently -> END

**B1 范围说明**：本模块提供图的**结构与状态转移**，节点实现依赖注入的
Ports（``LLMPort`` 等）。B1 用 Fake LLM 跑通；真实模型在 B3 接入。

关键约束：

- ``interrupt()`` **只**在 ``await_approval`` 节点；
- 其前只做**无副作用快照读取**，不做付费模型调用或未保护写入；
- 内容修复**至多 2 次**，超限失败并**保留错误**；
- 提交必须 **幂等**（``run_id + operation_key`` 唯一且可重放）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from app.agent_workflows.state import PlanningState
from app.agent_workflows.validators import MAX_REPAIR_ATTEMPTS, validate_plan_structure
from app.ports.llm import LLMPort, LLMFailure

#: 校验/修复循环的路由目标。
ROUTE_COMMIT = "commit_plan_idempotently"
ROUTE_REPAIR = "repair_content"
ROUTE_FAIL = "fail_validation"


@dataclass
class PlanningNodes:
    """planning_graph 的节点实现。

    每个节点是**纯函数式**的：接收 state，返回 state 的增量 dict。
    所有 I/O 通过注入的 Ports，节点本身不持有连接。
    """

    llm: LLMPort
    #: 保存草案投影（写业务草案表）—— 由应用层注入，图不自行 SQL。
    save_draft: Callable[[PlanningState], str] = field(default=lambda s: "")
    #: 幂等提交 —— 必须实现 run_id + operation_key 唯一。
    commit_plan: Callable[[PlanningState], str] = field(default=lambda s: "")
    #: 记录失败（保留错误，供人工核对）。
    on_failure: Callable[[PlanningState, list[str]], None] = field(
        default=lambda s, e: None
    )

    def normalize(self, state: PlanningState) -> dict[str, Any]:
        """规范化输入。无副作用，不调模型。"""
        goal = str(state.get("goal", "")).strip()
        errors: list[str] = []
        if not goal:
            errors.append("学习目标不能为空")
        return {
            "goal": goal,
            "prefs_snapshot": dict(state.get("prefs_snapshot") or {}),
            "validation_errors": errors,
            "repair_count": 0,
        }

    def generate_outline(self, state: PlanningState) -> dict[str, Any]:
        """生成全量领域索引纲要。

        设计 §1 要求「一次生成完整可浏览纲要」。这里只产生**结构化纲要**，
        详细卡片按需展开 —— 因此不在这里生成每张卡片正文。
        """
        result = self.llm.generate_structured(
            purpose="planning.outline",
            payload={"goal": state.get("goal"), "prefs": state.get("prefs_snapshot")},
            schema_name="OutlineV1",
            run_id=state.get("run_id", ""),
            attempt_id=f"{state.get('run_id', '')}:outline:1",
        )
        if isinstance(result, LLMFailure):
            # 失败必须显式记录；不能返回空纲要假装成功。
            return {
                "validation_errors": [f"纲要生成失败：{result.error_class}"],
                "outline": {},
                "outline_ref": "",
            }
        payload = result.payload
        return {
            "outline": payload,
            "outline_ref": str(payload.get("outline_ref", "outline:1")),
        }

    def build_dependencies_and_units(self, state: PlanningState) -> dict[str, Any]:
        """基于纲要产出知识节点、关系与学习单元。"""
        outline = state.get("outline") or {}
        result = self.llm.generate_structured(
            purpose="planning.structure",
            payload={"goal": state.get("goal"), "outline": outline},
            schema_name="KnowledgeStructureV1",
            run_id=state.get("run_id", ""),
            attempt_id=f"{state.get('run_id', '')}:structure:1",
        )
        if isinstance(result, LLMFailure):
            return {
                "validation_errors": [f"知识结构生成失败：{result.error_class}"],
                "nodes": [],
                "units": [],
                "relations": [],
            }
        payload = result.payload
        return {
            "nodes": list(payload.get("nodes") or []),  # type: ignore[arg-type]
            "units": list(payload.get("units") or []),  # type: ignore[arg-type]
            "relations": list(payload.get("relations") or []),  # type: ignore[arg-type]
        }

    def propose_practice(self, state: PlanningState) -> dict[str, Any]:
        """提出主实践项目候选与分阶段任务。

        设计 §1：用户可提供想法或从候选中选；**可延后选择**（不阻断结构生成）。
        """
        result = self.llm.generate_structured(
            purpose="planning.practice",
            payload={
                "goal": state.get("goal"),
                "units": state.get("units") or [],
            },
            schema_name="PracticeProposalV1",
            run_id=state.get("run_id", ""),
            attempt_id=f"{state.get('run_id', '')}:practice:1",
        )
        if isinstance(result, LLMFailure):
            return {
                "validation_errors": [f"实践任务生成失败：{result.error_class}"],
                "practice_proposal": {},
            }
        return {"practice_proposal": result.payload}

    def validate(self, state: PlanningState) -> dict[str, Any]:
        """确定性结构校验。**不调用模型** —— 见 validators.py 的理由。"""
        proposal = state.get("practice_proposal") or {}
        outcome = validate_plan_structure(
            nodes=list(state.get("nodes") or []),
            units=list(state.get("units") or []),
            relations=list(state.get("relations") or []),
            tasks=list(proposal.get("tasks") or []),
            task_knowledge_links=list(proposal.get("task_knowledge_links") or []),
        )
        return {"validation_errors": outcome.errors}

    def repair_content(self, state: PlanningState) -> dict[str, Any]:
        """有界修复：把校验错误回灌给模型重生成。

        **修复次数上限 2**（``MAX_REPAIR_ATTEMPTS``）。计数在路由函数里
        递增，这里只负责重生成。
        """
        attempt = int(state.get("repair_count", 0)) + 1
        result = self.llm.generate_structured(
            purpose="planning.repair",
            payload={
                "goal": state.get("goal"),
                "errors": state.get("validation_errors") or [],
                "outline": state.get("outline") or {},
            },
            schema_name="KnowledgeStructureV1",
            run_id=state.get("run_id", ""),
            attempt_id=f"{state.get('run_id', '')}:repair:{attempt}",
        )
        if isinstance(result, LLMFailure):
            return {
                "validation_errors": [f"修复失败：{result.error_class}"],
                "repair_count": attempt,
            }
        payload = result.payload
        # 注意：**重置**上一轮错误（返回完整新列表覆盖 reducer 累加结果），
        # 避免已修复的错误永远留在列表里使图无法通过校验。
        # 真实 StateGraph 中 reducer 为 ``operator.add``，因此这里返回一个
        # 清空信号由调用方处理；解释器与图构建器都遵循同一约定。
        return {
            "nodes": list(payload.get("nodes") or []),  # type: ignore[arg-type]
            "units": list(payload.get("units") or []),  # type: ignore[arg-type]
            "relations": list(payload.get("relations") or []),  # type: ignore[arg-type]
            "validation_errors": [],
            "repair_count": attempt,
        }

    def save_draft_projection(self, state: PlanningState) -> dict[str, Any]:
        """把草案投影到**受授权业务草案表**。

        checkpoint 只保存 ``draft_ref`` 引用，不保存草案正文（ADR-0002）。
        """
        draft_ref = self.save_draft(state)
        return {"draft_ref": draft_ref}

    def apply_decision(self, state: PlanningState) -> dict[str, Any]:
        """处理用户在 ``await_approval`` 处的决定。

        - ``cancel``：**不得**被 worker 稍后发布（由仓储按状态过滤保证）；
        - ``edit``：修改后必须**重新校验**；
        - ``approve``：进入幂等提交。
        """
        decision = str(state.get("decision", "")).lower()
        if decision == "cancel":
            return {"validation_errors": [], "result_id": ""}
        if decision == "edit":
            # 编辑后重新校验：清空旧错误，由 validate 节点重新产出。
            return {"validation_errors": [], "repair_count": 0}
        return {}

    def commit_plan_idempotently(self, state: PlanningState) -> dict[str, Any]:
        """幂等提交。

        ``commit_plan`` 必须实现：先按 ``run_id + operation_key`` 查是否
        已成功，已成功则**返回同一结果**而不是再建一份计划
        （SOFTWARE_DESIGN.md §5 / 验收条款「重复批准不能造成重复计划」）。
        """
        result_id = self.commit_plan(state)
        return {"result_id": result_id}

    def record_failure_node(self, state: PlanningState) -> dict[str, Any]:
        """修复次数超限：失败并**保留错误**（不静默丢弃）。"""
        self.on_failure(state, list(state.get("validation_errors") or []))
        return {}


def route_after_validate(state: PlanningState) -> str:
    """校验后的路由。

    先判断是否已通过；未通过则检查修复配额，**用尽即失败**，
    绝不允许无限修复（设计 §4「内容修复次数上限 2，超限失败并保留错误」）。
    """
    if not (state.get("validation_errors") or []):
        return "save_draft_projection"
    if int(state.get("repair_count", 0)) >= MAX_REPAIR_ATTEMPTS:
        return ROUTE_FAIL
    return ROUTE_REPAIR


def route_after_decision(state: PlanningState) -> str:
    """等待用户后的路由。"""
    decision = str(state.get("decision", "")).lower()
    if decision in {"approve", ""}:
        return ROUTE_COMMIT
    if decision == "edit":
        return "validate"
    return "cancel_draft"


__all__ = [
    "PlanningNodes",
    "ROUTE_COMMIT",
    "ROUTE_FAIL",
    "ROUTE_REPAIR",
    "route_after_decision",
    "route_after_validate",
]
