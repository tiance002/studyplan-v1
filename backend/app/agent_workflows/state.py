"""三张图共用的最小 State 定义。

设计约束（SOFTWARE_DESIGN.md §4「状态最小化」）：

    Graph State 只存 ``run_id/project_id/goal/prefs_snapshot/outline_ref/
    draft_ref/validation_errors/repair_count/decision/result_id`` 等
    有限 JSON 可序列化字段；不写入密钥、无限历史、完整检索文本、二进制附件。

**为什么用 ``TypedDict`` 而不是 Pydantic**：LangGraph 需要 State 是
可被其 reducer 机制处理的普通映射；Pydantic 模型会引入额外序列化层。
业务校验收在 DTO 层（``api/v1``）与领域模型里，不在这里做。

## 错误字段的三种语义（B1 修复：不得互相覆盖）

历史实现把所有错误塞进一个 ``validation_errors`` 且使用
``operator.add`` reducer，导致两个真实缺陷：

1. 修复节点返回空列表时 reducer 的"累加"语义**无法清除**旧错误，
   于是"第一次修复成功"永远无法通过校验；
2. ``normalize`` 写入的**输入错误**会在结构校验前被清空，
   使空学习目标也能继续调用模型。

本版把三类错误**分字段存放，全部为覆盖语义（普通字段）**：

- ``input_errors``      —— 输入层错误（空目标等）。**非空即直接失败**，
                           不进入生成阶段，不调用模型。
- ``generation_errors`` —— 模型调用失败（``LLMFailure``）。**非空即失败**，
                           不得被后续空结构校验覆盖成"看起来成功"。
- ``structure_errors``  —— 本轮结构校验的结果。每次 ``validate`` **完整重写**，
                           因此修复成功后旧错误自然消失。

``validation_errors`` 保留为**对外聚合视图**（= 三类错误拼接），供路由与
记录使用，仍然是覆盖语义。``validation_history`` 仅用于审计，**不参与**
任何路由判断，避免历史错误影响最新校验结果。

**单写入者原则**：每个字段只由一个节点写。需要跨节点保留的错误由对应
节点各自写入自己的字段；**不依赖平行写同一键碰运气**。
"""

from __future__ import annotations

from typing import Any, TypedDict


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
    domain_pack: dict[str, Any]
    # ---- 生成中间产物（只存引用/结构化内容，不存完整检索文本）----
    outline_ref: str
    outline: dict[str, Any]
    nodes: list[dict[str, Any]]
    units: list[dict[str, Any]]
    relations: list[dict[str, Any]]
    practice_proposal: dict[str, Any]
    # ---- 错误（三通道分离，全部覆盖语义）----
    #: 输入层错误：非空即直接失败，**不调用模型**。
    input_errors: list[str]
    #: 模型调用失败：非空即失败，不得被后续空结构校验覆盖。
    generation_errors: list[str]
    #: 本轮结构校验结果：每次 validate 完整重写，修复成功后自动清空。
    structure_errors: list[str]
    #: 对外聚合视图（三类拼接），覆盖语义；供路由与记录使用。
    validation_errors: list[str]
    #: 仅审计用途，**不参与路由**；不因历史错误影响最新校验。
    validation_history: list[str]
    repair_count: int
    #: 上一次修复使用的 attempt_id，供付费调用账务与幂等判定。
    last_repair_attempt_id: str
    # ---- 等待用户 ----
    draft_ref: str
    draft_hash: str
    expected_version: int
    decision: str
    decision_idempotency_key: str
    edited_stages: list[dict[str, Any]]
    #: 本轮是否为「用户编辑后的重新校验」。为 True 时结构非法**直接失败**，
    #: 不用模型静默修复覆盖用户的实际编辑（B1.2 §二）。
    edited_draft: bool
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
    validation_errors: list[str]
    validation_history: list[str]
    result_id: str


__all__ = ["PlanningState", "ReviewState"]
