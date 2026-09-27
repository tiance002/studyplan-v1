"""三张图共用的最小 State 定义。

设计约束（SOFTWARE_DESIGN.md §4「状态最小化」）：

    Graph State 只存 ``run_id/project_id/goal/prefs_snapshot/outline_ref/
    draft_ref/validation_errors/repair_count/decision/result_id`` 等
    有限 JSON 可序列化字段；不写入密钥、无限历史、完整检索文本、二进制附件。

**为什么用 ``TypedDict`` 而不是 Pydantic**：LangGraph 需要 State 是
可被其 reducer 机制处理的普通映射；Pydantic 模型会引入额外序列化层。
业务校验收在 DTO 层（``api/v1``）与领域模型里，不在这里做。

**单写入者原则**：每个字段只由一个节点写。需要多节点累加的字段
（``validation_errors`` / ``repair_count``）显式使用 reducer，
**不依赖平行写同一键碰运气**。
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


class PlanningState(TypedDict, total=False):
    """planning_graph 的状态。

    字段与设计 §4 逐条对应。所有值必须 JSON 可序列化。
    """

    # ---- 身份与进度 ----
    run_id: str
    project_id: str
    graph_version: str
    # ---- 输入 ----
    goal: str
    prefs_snapshot: dict[str, Any]
    # ---- 生成中间产物（只存引用/结构化内容，不存完整检索文本）----
    outline_ref: str
    outline: dict[str, Any]
    nodes: list[dict[str, Any]]
    units: list[dict[str, Any]]
    relations: list[dict[str, Any]]
    practice_proposal: dict[str, Any]
    # ---- 校验与修复 ----
    #: 多节点累加：用 reducer 显式表达"合并"语义，避免后写覆盖前写。
    validation_errors: Annotated[list[str], operator.add]
    repair_count: int
    # ---- 等待用户 ----
    draft_ref: str
    draft_hash: str
    decision: str
    # ---- 结果 ----
    result_id: str


class ReviewState(TypedDict, total=False):
    """summary_review_graph 与 prompt_review_graph 共用的状态。

    ⚠️ 这两张图**不设 interrupt**：每次修订是新的 ``attempt/revision + run``，
    不让图挂起数月（设计 §4）。
    """

    run_id: str
    project_id: str
    graph_version: str
    # ---- 被评审对象 ----
    subject_id: str
    rubric_snapshot: dict[str, Any]
    # ---- 评审输出 ----
    review: dict[str, Any]
    validation_errors: Annotated[list[str], operator.add]
    result_id: str


__all__ = ["PlanningState", "ReviewState"]
