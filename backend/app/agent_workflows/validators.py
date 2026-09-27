"""规划结构校验：确定性规则，不依赖模型。

设计约束（SOFTWARE_DESIGN.md §4）：

    规划验证包含依赖无环、顺序一致、任务知识关联合法、数量软上限、
    必填验收标准，**内容修复次数上限 2**，超限失败并保留错误。

这些规则刻意放在**纯函数**里：可以用单元测试机械证明，
不需要起图、不需要 Postgres、不需要模型。

**为什么不用模型自我校验**：模型说"我检查过了，没问题"不构成证据；
只有确定性的、可复现的规则才能作为发布门禁。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.catalog.models import (
    KnowledgeRelation,
    build_dependency_graph,
)
from app.domain.enums import RelationType, TaskKnowledgeRole

#: 数量软上限（设计 §6「控制用量」）。**超限只警告，不阻断发布**。
SOFT_LIMIT_UNITS = 30
SOFT_LIMIT_NODES = 120
SOFT_LIMIT_TASKS = 12

#: 内容修复次数上限。超限失败并保留错误，**不无限重试**。
MAX_REPAIR_ATTEMPTS = 2


@dataclass(slots=True)
class ValidationOutcome:
    """一次校验的结果。

    ``errors`` 阻断发布；``warnings`` 只提示（软上限）。
    """

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def validate_plan_structure(
    *,
    nodes: list[dict[str, object]],
    units: list[dict[str, object]],
    relations: list[dict[str, object]],
    tasks: list[dict[str, object]],
    task_knowledge_links: list[dict[str, object]] | None = None,
) -> ValidationOutcome:
    """校验规划草案的结构合法性。

    检查项（每项都对应一条可机械验证的不变量）：

    1. **依赖无环**：``prerequisite`` / ``contains`` 构成的图必须无环。
    2. **顺序一致**：单元 / 任务的 ``order_index`` 无重复、无负值，
       且不超出集合长度（防止前端按序渲染时出现空洞）。
    3. **任务知识关联合法**：``role`` 必须是合法枚举值；
       引用的 ``node_stable_key`` / ``task_stable_key`` 必须存在。
    4. **必填验收标准**：每个任务至少一条 ``acceptance``。
    5. **稳定键唯一且非空**：节点 / 单元 / 任务的 ``stable_key``
       在两两之间不得重复（重复会让局部重规划无法精确映射）。
    6. **数量软上限**：超过只产生 warning。
    """
    outcome = ValidationOutcome()

    _check_stable_keys_unique(outcome, nodes=nodes, units=units, tasks=tasks)
    _check_acyclic(outcome, relations=relations, nodes=nodes)
    _check_order_index(outcome, items=units, label="单元")
    _check_order_index(outcome, items=tasks, label="任务")
    _check_acceptance(outcome, tasks=tasks)

    known_node_keys = {str(n.get("stable_key", "")) for n in nodes}
    known_task_keys = {str(t.get("stable_key", "")) for t in tasks}
    _check_task_links(
        outcome,
        links=task_knowledge_links or [],
        known_node_keys=known_node_keys,
        known_task_keys=known_task_keys,
    )

    _check_soft_limits(outcome, nodes=nodes, units=units, tasks=tasks)
    return outcome


def _check_stable_keys_unique(
    outcome: ValidationOutcome,
    *,
    nodes: list[dict[str, object]],
    units: list[dict[str, object]],
    tasks: list[dict[str, object]],
) -> None:
    for label, items in (("知识节点", nodes), ("学习单元", units), ("实践任务", tasks)):
        seen: set[str] = set()
        for item in items:
            key = str(item.get("stable_key", "")).strip()
            if not key:
                outcome.errors.append(f"{label}存在空的 stable_key")
                continue
            if key in seen:
                outcome.errors.append(f"{label}的稳定键重复：{key}")
            seen.add(key)


def _check_acyclic(
    outcome: ValidationOutcome,
    *,
    relations: list[dict[str, object]],
    nodes: list[dict[str, object]],
) -> None:
    known = {str(n.get("stable_key", "")) for n in nodes}
    parsed: list[KnowledgeRelation] = []
    for index, raw in enumerate(relations):
        try:
            relation_type = RelationType(str(raw.get("relation_type", "")))
        except ValueError:
            outcome.errors.append(
                f"第 {index} 条关系的类型非法：{raw.get('relation_type')!r}"
            )
            continue
        from_key = str(raw.get("from_stable_key", ""))
        to_key = str(raw.get("to_stable_key", ""))
        if from_key not in known:
            outcome.errors.append(f"关系引用了不存在的节点：{from_key}")
            continue
        if to_key not in known:
            outcome.errors.append(f"关系引用了不存在的节点：{to_key}")
            continue
        if from_key == to_key:
            outcome.errors.append(f"节点不能与自身建立关系：{from_key}")
            continue
        parsed.append(
            KnowledgeRelation.create(
                scope="draft",
                from_id=from_key,
                to_id=to_key,
                relation_type=relation_type,
            )
        )

    cycle = build_dependency_graph(parsed).find_cycle()
    if cycle:
        outcome.errors.append("前置依赖存在环：" + " -> ".join(cycle))


def _check_order_index(
    outcome: ValidationOutcome, *, items: list[dict[str, object]], label: str
) -> None:
    seen: set[int] = set()
    for item in items:
        raw = item.get("order_index", None)
        if raw is None:
            outcome.errors.append(f"{label}缺少 order_index")
            continue
        index = _strict_int(raw)
        if index is None:
            # 严格拒绝：不得把 3.7 / True / "3.0" 静默截断成整数（Goal §9.1）。
            outcome.errors.append(f"{label}的 order_index 不是整数：{raw!r}")
            continue
        if index < 0:
            outcome.errors.append(f"{label}的 order_index 不能为负：{index}")
        if index in seen:
            outcome.errors.append(f"{label}的 order_index 重复：{index}")
        seen.add(index)
    if seen and len(items) > 0:
        limit = len(items)
        over = sorted(i for i in seen if i >= limit)
        if over:
            outcome.warnings.append(
                f"{label}的 order_index 超出数量范围（{over[:3]}...），可能造成渲染空洞"
            )


def _strict_int(raw: object) -> int | None:
    """严格整数判定。

    只有真正的整数（``int`` 且非 ``bool``）才接受。
    ``bool`` 是 ``int`` 的子类但不是有效序号；``3.7`` / ``"3.0"`` / ``"3.7"``
    一律拒绝——避免静默截断掩盖模型输出错误（Goal §9.1）。
    """
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return raw
    return None


def _check_acceptance(outcome: ValidationOutcome, *, tasks: list[dict[str, object]]) -> None:
    for task in tasks:
        acceptance = task.get("acceptance") or []
        if not isinstance(acceptance, list) or not [
            a for a in acceptance if str(a).strip()
        ]:
            key = task.get("stable_key", "?")
            outcome.errors.append(f"任务 {key} 缺少必填验收标准")


def _check_task_links(
    outcome: ValidationOutcome,
    *,
    links: list[dict[str, object]],
    known_node_keys: set[str],
    known_task_keys: set[str],
) -> None:
    for index, link in enumerate(links):
        task_key = str(link.get("task_stable_key", ""))
        node_key = str(link.get("node_stable_key", ""))
        if task_key not in known_task_keys:
            outcome.errors.append(f"第 {index} 条任务知识关联引用了不存在的任务：{task_key}")
        if node_key not in known_node_keys:
            outcome.errors.append(f"第 {index} 条任务知识关联引用了不存在的节点：{node_key}")
        role = link.get("role", TaskKnowledgeRole.CORE.value)
        try:
            TaskKnowledgeRole(str(role))
        except ValueError:
            outcome.errors.append(f"第 {index} 条任务知识关联的 role 非法：{role!r}")


def _check_soft_limits(
    outcome: ValidationOutcome,
    *,
    nodes: list[dict[str, object]],
    units: list[dict[str, object]],
    tasks: list[dict[str, object]],
) -> None:
    checks = (
        ("学习单元", len(units), SOFT_LIMIT_UNITS),
        ("知识节点", len(nodes), SOFT_LIMIT_NODES),
        ("实践任务", len(tasks), SOFT_LIMIT_TASKS),
    )
    for label, count, limit in checks:
        if count > limit:
            outcome.warnings.append(
                f"{label}数量 {count} 超过建议上限 {limit}，建议合并或延后（不阻断发布）"
            )


__all__ = [
    "MAX_REPAIR_ATTEMPTS",
    "SOFT_LIMIT_NODES",
    "SOFT_LIMIT_TASKS",
    "SOFT_LIMIT_UNITS",
    "ValidationOutcome",
    "validate_plan_structure",
]
