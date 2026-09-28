"""planning_graph：三张图中唯一可暂停等待用户的图。

流程（SOFTWARE_DESIGN.md §4）：

    START -> normalize -> generate_outline -> build_dependencies_and_units
          -> propose_practice -> validate -> [repair <= 2] -> save_draft_projection
          -> await_approval [interrupt] -> apply_decision -> route_after_decision
          -> (cancel | edit -> validate | approve -> commit_plan_idempotently) -> END

**B1 范围说明**：本模块提供图的**结构与状态转移**，节点实现依赖注入的
Ports（``LLMPort`` 等）。B1 用 Fake LLM 跑通；真实模型在 B3 接入。

关键约束：

- ``interrupt()`` **只**在 ``await_approval`` 节点；
- 其前只做**无副作用快照读取**，不做付费模型调用或未保护写入；
- 内容修复**至多 2 次**，超限失败并**保留错误**；
- 提交必须 **幂等**（``run_id + operation_key`` 唯一且可重放）；
- **错误分三通道**（input / generation / structure），互不覆盖；
- **空学习目标直接失败**，绝不继续调用模型。

## B1 修复要点（三类错误的覆盖语义）

- ``normalize`` 只写 ``input_errors``；``input_errors`` 非空时由
  ``route_after_normalize`` 直接路由到失败，**不经过任何模型节点**。
- 模型节点失败时写 ``generation_errors``，``validate`` **不覆盖**它；
  路由函数同时检查 generation 与 structure 错误。
- ``validate`` 每次**完整重写** ``structure_errors``（覆盖语义），
  修复成功后旧结构错误自然消失，无需依赖 reducer 的重置技巧。
- ``validation_errors`` 是对外聚合视图，由节点显式计算。
"""

from __future__ import annotations

from collections.abc import Mapping as AbcMapping
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from app.agent_workflows.state import PlanningState
from app.agent_workflows.validators import MAX_REPAIR_ATTEMPTS, validate_plan_structure
from app.ports.llm import LLMFailure, LLMPort

#: 路由目标常量。
ROUTE_COMMIT = "commit_plan_idempotently"
ROUTE_REPAIR = "repair_content"
ROUTE_FAIL = "fail_validation"
ROUTE_DRAFT = "save_draft_projection"
ROUTE_CANCEL = "cancel_draft"
ROUTE_VALIDATE = "validate"


def aggregate_errors(state: Mapping[str, Any]) -> list[str]:
    """把三类错误按固定顺序拼成对外视图。

    顺序固定（input -> generation -> structure）以便日志与断言稳定。
    这是**唯一**允许把多通道错误合流的地方。
    """
    return [
        *(state.get("input_errors") or []),
        *(state.get("generation_errors") or []),
        *(state.get("structure_errors") or []),
    ]


def _as_list(value: Any) -> list[Any]:
    """把模型 payload 字段安全地规整为列表。

    ``payload.get(...)`` 的静态类型是 ``object``；直接在 ``list(...)`` 上调用
    既不安全也过不了类型检查。这里显式收敛：列表原样返回，``None`` 返回空表，
    其它可迭代对象转列表，其余视为空表（模型输出非预期结构）。
    """
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, (tuple, set, frozenset)):
        return list(value)
    return []


def _coerce_edit_delta(edited: Any) -> dict[str, Any]:
    """规整 ``apply_edit`` 的返回值。

    正式契约：返回**编辑后的完整草案结构**（mapping），至少含 ``draft_ref``，
    并可含 ``draft_hash`` 与新的 ``nodes``/``units``/``relations``/
    ``practice_proposal``/``outline``。这样随后的 ``validate`` 才能校验
    **新内容**，``save_draft_projection`` 才会保存新内容（B1.2 §二）。

    兼容：若返回字符串，则仅视为草案引用（旧契约），结构保持原样。
    """
    if isinstance(edited, AbcMapping):
        return dict(edited)
    if isinstance(edited, str):
        return {"draft_ref": edited}
    return {}


def _coerce_draft_result(result: Any) -> dict[str, str]:
    """规整 ``save_draft`` 的返回值。

    支持两种形态：
    - mapping：``{"draft_ref": ..., "draft_hash": ...}``（正式契约）；
    - 字符串：仅草案引用（旧契约）。
    """
    if isinstance(result, AbcMapping):
        return {
            "draft_ref": str(result.get("draft_ref", "") or ""),
            "draft_hash": str(result.get("draft_hash", "") or ""),
        }
    return {"draft_ref": str(result or ""), "draft_hash": ""}


def _extend_generation_errors(state: Mapping[str, Any], delta: dict[str, Any]) -> dict[str, Any]:
    """在生成阶段**累加** generation 错误，而不是覆盖。

    生成阶段有多个节点（outline / structure / practice），它们共享
    ``generation_errors`` 这一个通道。若各自覆盖，前一个节点的失败会被
    后一个节点的空列表冲掉（"空纲要却被判有效"这类缺陷的根源）。
    因此生成阶段统一用「已有 + 新增」的方式追加：
    - 成功节点传空列表 => 不新增、**也不清空**已有错误；
    - 需要清空（如修复成功）时显式传 ``generation_errors=None`` 语义，
      由调用方使用普通赋值，而不是走本助手。
    """
    incoming = list(delta.pop("generation_errors", []) or [])
    existing = list(state.get("generation_errors") or [])
    merged_errors = existing + [e for e in incoming if e not in existing]
    delta["generation_errors"] = merged_errors
    return delta


def _with_aggregate(delta: dict[str, Any], state: Mapping[str, Any]) -> dict[str, Any]:
    """在节点返回的增量上补写 ``validation_errors`` 聚合视图。

    节点只写自己负责的通道；聚合视图由本助手统一派生，避免每个节点
    各自手写拼接导致顺序或遗漏不一致。
    """
    merged = dict(state)
    merged.update(delta)
    delta.setdefault("validation_errors", aggregate_errors(merged))
    return delta


@dataclass
class PlanningNodes:
    """planning_graph 的节点实现。

    每个节点是**纯函数式**的：接收 state，返回 state 的增量 dict。
    所有 I/O 通过注入的 Ports，节点本身不持有连接。
    """

    llm: LLMPort
    #: 保存草案投影（写业务草案表）—— 由应用层注入，图不自行 SQL。
    #: 返回草案引用字符串，或 ``{"draft_ref", "draft_hash"}`` mapping。
    save_draft: Callable[[PlanningState], Any] = field(default=lambda s: "")
    #: 幂等提交 —— 必须实现 run_id + operation_key 唯一。
    commit_plan: Callable[[PlanningState], str] = field(default=lambda s: "")
    #: 应用用户编辑并保存**新的草案版本**（不发布）。
    #: **必须返回编辑后的完整草案结构**（mapping）：至少含 ``draft_ref``，
    #: 并含新的 ``nodes``/``units``/``relations``/``practice_proposal``
    #: 与 ``draft_hash``，使随后的 validate 校验新内容、save_draft 保存新内容。
    apply_edit: Callable[[PlanningState], Any] = field(default=lambda s: {})
    #: 持久化草案取消状态（供 worker 按状态过滤，杜绝取消后发布）。
    cancel_draft: Callable[[PlanningState], None] = field(default=lambda s: None)
    #: 记录失败（保留错误，供人工核对）。
    on_failure: Callable[[PlanningState, list[str]], None] = field(
        default=lambda s, e: None
    )

    def normalize(self, state: PlanningState) -> dict[str, Any]:
        """规范化输入。无副作用，不调模型。

        只写 ``input_errors``：非空即由路由直接失败，**不进入生成阶段**。
        """
        goal = str(state.get("goal", "")).strip()
        input_errors: list[str] = []
        if not goal:
            input_errors.append("学习目标不能为空")
        return _with_aggregate(
            {
                "goal": goal,
                "prefs_snapshot": dict(state.get("prefs_snapshot") or {}),
                "input_errors": input_errors,
                "generation_errors": [],
                "structure_errors": [],
                "validation_history": [],
                "repair_count": 0,
                "edited_draft": False,
            },
            state,
        )

    def generate_outline(self, state: PlanningState) -> dict[str, Any]:
        """生成全量领域索引纲要。

        设计 §1 要求「一次生成完整可浏览纲要」。这里只产生**结构化纲要**，
        详细卡片按需展开 —— 因此不在这里生成每张卡片正文。

        失败必须写入 ``generation_errors``，**不得**返回空纲要假装成功。
        """
        result = self.llm.generate_structured(
            purpose="planning.outline",
            payload={"goal": state.get("goal"), "prefs": state.get("prefs_snapshot")},
            schema_name="OutlineV1",
            run_id=state.get("run_id", ""),
            attempt_id=f"{state.get('run_id', '')}:outline:1",
        )
        if isinstance(result, LLMFailure):
            return _with_aggregate(
                _extend_generation_errors(
                    state,
                    {
                        "generation_errors": [f"纲要生成失败：{result.error_class}"],
                        "outline": {},
                        "outline_ref": "",
                    },
                ),
                state,
            )
        payload = result.payload
        # 空纲要必须被视为无效：不能因为它"没报错"就当作有效计划。
        if not payload or not payload.get("sections"):
            return _with_aggregate(
                _extend_generation_errors(
                    state,
                    {
                        "generation_errors": ["纲要生成失败：模型返回空纲要"],
                        "outline": {},
                        "outline_ref": "",
                    },
                ),
                state,
            )
        return _with_aggregate(
            {"outline": payload, "outline_ref": str(payload.get("outline_ref", "outline:1"))},
            state,
        )

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
            return _with_aggregate(
                _extend_generation_errors(
                    state,
                    {
                        "generation_errors": [f"知识结构生成失败：{result.error_class}"],
                        "nodes": [],
                        "units": [],
                        "relations": [],
                    },
                ),
                state,
            )
        payload = result.payload
        nodes = _as_list(payload.get("nodes"))
        units = _as_list(payload.get("units"))
        relations = _as_list(payload.get("relations"))
        errors: list[str] = []
        if not nodes:
            errors.append("知识结构生成失败：模型返回空知识节点")
        if not units:
            errors.append("知识结构生成失败：模型返回空学习单元")
        return _with_aggregate(
            _extend_generation_errors(
                state,
                {
                    "nodes": nodes,
                    "units": units,
                    "relations": relations,
                    "generation_errors": errors,
                },
            ),
            state,
        )

    def propose_practice(self, state: PlanningState) -> dict[str, Any]:
        """提出主实践项目候选与分阶段任务。

        设计 §1：用户可提供想法或从候选中选；**可延后选择**（不阻断结构生成）。
        """
        result = self.llm.generate_structured(
            purpose="planning.practice",
            payload={"goal": state.get("goal"), "units": state.get("units") or []},
            schema_name="PracticeProposalV1",
            run_id=state.get("run_id", ""),
            attempt_id=f"{state.get('run_id', '')}:practice:1",
        )
        if isinstance(result, LLMFailure):
            return _with_aggregate(
                _extend_generation_errors(
                    state,
                    {
                        "generation_errors": [f"实践任务生成失败：{result.error_class}"],
                        "practice_proposal": {},
                    },
                ),
                state,
            )
        return _with_aggregate({"practice_proposal": result.payload}, state)

    def validate(self, state: PlanningState) -> dict[str, Any]:
        """确定性结构校验。**不调用模型** —— 见 validators.py 的理由。

        **完整重写** ``structure_errors``（覆盖语义）。这样：
        - 修复成功后旧结构错误自然消失（无需 reducer 重置技巧）；
        - 历史错误不影响本轮结果。
        ``generation_errors`` **不在此处清空**：模型失败不得被空结构
        "看起来通过"覆盖。后者由路由函数优先判定。
        """
        proposal = state.get("practice_proposal") or {}
        outcome = validate_plan_structure(
            nodes=list(state.get("nodes") or []),
            units=list(state.get("units") or []),
            relations=list(state.get("relations") or []),
            tasks=list(proposal.get("tasks") or []),
            task_knowledge_links=list(proposal.get("task_knowledge_links") or []),
        )
        return _with_aggregate({"structure_errors": list(outcome.errors)}, state)

    def repair_content(self, state: PlanningState) -> dict[str, Any]:
        """有界修复：把校验错误回灌给模型重生成。

        **修复次数上限 2**（``MAX_REPAIR_ATTEMPTS``）。计数在路由函数里
        递增，这里只负责重生成。

        失败写入 ``generation_errors``（**不覆盖 structure_errors**，
        以便路由据配额决定是否继续/失败）。
        """
        attempt = int(state.get("repair_count", 0)) + 1
        attempt_id = f"{state.get('run_id', '')}:repair:{attempt}"
        result = self.llm.generate_structured(
            purpose="planning.repair",
            payload={
                "goal": state.get("goal"),
                # 回灌**本轮**校验错误，而不是历史错误。
                "errors": list(state.get("structure_errors") or state.get("validation_errors") or []),
                "outline": state.get("outline") or {},
            },
            schema_name="KnowledgeStructureV1",
            run_id=state.get("run_id", ""),
            attempt_id=attempt_id,
        )
        if isinstance(result, LLMFailure):
            # 结果未知的付费调用不得自动重新派发：交给路由，不在此处重试。
            # 注意：repair 阶段是对已有 generation 错误的**重试通道**，
            # 这里用普通赋值（覆盖）会丢掉原始生成错误，因此改为追加。
            return _with_aggregate(
                _extend_generation_errors(
                    state,
                    {
                        "generation_errors": [f"修复失败：{result.error_class}"],
                        "repair_count": attempt,
                        "last_repair_attempt_id": attempt_id,
                    },
                ),
                state,
            )
        payload = result.payload
        nodes = _as_list(payload.get("nodes"))
        units = _as_list(payload.get("units"))
        relations = _as_list(payload.get("relations"))
        gen_errors: list[str] = []
        if not nodes:
            gen_errors.append("修复失败：模型返回空知识节点")
        if not units:
            gen_errors.append("修复失败：模型返回空学习单元")
        # 修复**成功**时清空旧的 generation 错误（普通赋值，覆盖语义）：
        # 这正是"修复成功后旧错误消失"的必要条件。
        return _with_aggregate(
            {
                "nodes": nodes,
                "units": units,
                "relations": relations,
                "generation_errors": gen_errors,
                "repair_count": attempt,
                "last_repair_attempt_id": attempt_id,
            },
            state,
        )

    def save_draft_projection(self, state: PlanningState) -> dict[str, Any]:
        """把草案投影到**受授权业务草案表**。

        checkpoint 只保存 ``draft_ref`` 引用，不保存草案正文（ADR-0002）。

        **保存的是当前 state 里的内容** —— 生成路径下是模型产物；编辑路径下
        已被 ``apply_decision`` 覆盖为**用户编辑后的新结构**，因此不会把旧结构
        重新写回新草案（B1.2 §二）。若 ``save_draft`` 同时返回 ``draft_hash``，
        则一并更新，使后续 approve 必须使用**新**草案的 hash。
        """
        coerced = _coerce_draft_result(self.save_draft(state))
        delta: dict[str, Any] = {"draft_ref": coerced["draft_ref"]}
        if coerced["draft_hash"]:
            delta["draft_hash"] = coerced["draft_hash"]
        return delta

    def apply_decision(self, state: PlanningState) -> dict[str, Any]:
        """处理用户在 ``await_approval`` 处的决定。

        **本节点负责"决定合法性"和"副作用"的接线，但发布语义只有一份**：
        approve 的校验与发布由注入的 ``commit_plan``（应用层协调）完成，
        edit 由 ``apply_edit``（应用层）落地，cancel 由 ``cancel_draft``
        （应用层）持久化。Graph 不自行实现第二套发布规则。

        - 非法/缺失 decision -> 写入 ``input_errors``，由路由判定失败，
          **绝不默认 approve**。
        - ``edit``：应用用户实际编辑内容，然后走重新校验。
        - ``approve``：校验草案引用/hash/expected_version/幂等键（由
          ``commit_plan`` 内部完成），进入幂等提交。
        - ``cancel``：持久化取消状态，不产生正式计划。
        """
        decision = str(state.get("decision", "")).strip().lower()
        if decision == "cancel":
            self.cancel_draft(state)
            return _with_aggregate(
                {"structure_errors": [], "generation_errors": [], "result_id": ""},
                state,
            )
        if decision == "edit":
            if not (state.get("edited_stages") or []):
                return _with_aggregate(
                    {"input_errors": ["edit 决定必须携带实际的编辑内容"]}, state
                )
            # 应用编辑并保存新的草案版本（应用层实现），**不发布**。
            edited = self.apply_edit(state)
            edit_delta = _coerce_edit_delta(edited)
            new_ref = str(edit_delta.get("draft_ref", "") or "")
            if not new_ref:
                return _with_aggregate(
                    {"input_errors": ["编辑保存失败：未获得新的草案引用"]}, state
                )
            merged: dict[str, Any] = {
                "draft_ref": new_ref,
                "repair_count": 0,
                "generation_errors": [],
                "structure_errors": [],
                # 标记为「用户编辑后的重新校验」：结构非法时直接失败，
                # 不用模型静默修复覆盖用户的实际编辑。
                "edited_draft": True,
            }
            # **关键**：用编辑后的实际内容覆盖旧结构，确保 validate 校验新内容、
            # save_draft_projection 保存新内容（而不是把旧结构写回新草案）。
            for key in (
                "nodes",
                "units",
                "relations",
                "practice_proposal",
                "outline",
                "draft_hash",
            ):
                if key in edit_delta:
                    merged[key] = edit_delta[key]
            return _with_aggregate(merged, state)
        if decision == "approve":
            return {}
        # 非法/空 decision：不默认 approve。
        return _with_aggregate(
            {"input_errors": [f"非法的确认决定：{state.get('decision')!r}"]}, state
        )

    def commit_plan_idempotently(self, state: PlanningState) -> dict[str, Any]:
        """幂等提交。

        ``commit_plan`` 必须实现：先按 ``run_id + operation_key`` 查是否
        已成功，已成功则**返回同一结果**而不是再建一份计划
        （SOFTWARE_DESIGN.md §5 / 验收条款「重复批准不能造成重复计划」）。
        草案 hash / expected_version / 取消态校验也在应用层同事务内完成，
        失败时抛业务异常（409），不再生成第二套规则。
        """
        result_id = self.commit_plan(state)
        return {"result_id": result_id}

    def record_failure_node(self, state: PlanningState) -> dict[str, Any]:
        """修复次数超限 / 输入非法：失败并**保留错误**（不静默丢弃）。"""
        self.on_failure(state, list(state.get("validation_errors") or []))
        return {}


def route_after_normalize(state: PlanningState) -> str:
    """输入规范化后的路由。

    ``input_errors`` 非空（如空学习目标）**直接失败**，绝不进入生成阶段，
    因此不会产生任何模型调用。
    """
    if state.get("input_errors"):
        return ROUTE_FAIL
    return "generate_outline"


def route_after_generate(state: PlanningState) -> str:
    """生成阶段结束后的路由：有 generation_errors 直接失败。"""
    if state.get("generation_errors"):
        return ROUTE_FAIL
    return ROUTE_VALIDATE


def route_after_validate(state: PlanningState) -> str:
    """校验后的路由。

    判定顺序（关键）：
    1. ``generation_errors`` 非空 -> 失败。**模型失败不得被空结构校验覆盖**，
       因此这一条必须先于"结构是否为空"的判定。
    2. ``structure_errors`` 为空 -> 通过，保存草案。
    3. **用户编辑后的重新校验**（``edited_draft``）：结构非法即**直接失败**，
       **不**用模型静默修复覆盖用户的实际编辑（B1.2 §二）。
    4. 否则看修复配额：用尽即失败，否则修复（设计 §4 上限 2）。
    """
    if state.get("generation_errors"):
        return ROUTE_FAIL
    if state.get("input_errors"):
        return ROUTE_FAIL
    if not (state.get("structure_errors") or []):
        return ROUTE_DRAFT
    if state.get("edited_draft"):
        return ROUTE_FAIL
    if int(state.get("repair_count", 0)) >= MAX_REPAIR_ATTEMPTS:
        return ROUTE_FAIL
    return ROUTE_REPAIR


def route_after_decision(state: PlanningState) -> str:
    """等待用户后的路由。

    **非法/缺失 decision 不得默认 approve**：返回失败。
    """
    if state.get("input_errors"):
        return ROUTE_FAIL
    decision = str(state.get("decision", "")).strip().lower()
    if decision == "approve":
        return ROUTE_COMMIT
    if decision == "edit":
        return ROUTE_VALIDATE
    if decision == "cancel":
        return ROUTE_CANCEL
    return ROUTE_FAIL


__all__ = [
    "ROUTE_CANCEL",
    "ROUTE_COMMIT",
    "ROUTE_DRAFT",
    "ROUTE_FAIL",
    "ROUTE_REPAIR",
    "ROUTE_VALIDATE",
    "PlanningNodes",
    "aggregate_errors",
    "route_after_decision",
    "route_after_generate",
    "route_after_normalize",
    "route_after_validate",
]
