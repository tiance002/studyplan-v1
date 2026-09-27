"""catalog 领域：知识节点、关系、学习单元与依赖图校验。

核心不变量：
1. ``prerequisite`` / ``contains`` 关系构成的图**必须无环**。
2. 关系不可跨项目（scope 校验）；``related`` / ``alternative`` 允许非树形。
3. 节点与单元都是**项目私有**的 AI 草稿，验证后才可能共享；
   稳定键 ≠ 标题，标题可改，键不可随文案变化。
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterable

from app.core.errors import ConflictError, NotFoundError, ValidationAppError
from app.core.ids import new_id, require_stable_key, slugify_stable_key
from app.domain.enums import KnowledgeNodeType, RelationType, TaskKnowledgeRole

#: 这些关系类型参与「有序依赖」判定，必须无环。
ACYCLIC_RELATION_TYPES: frozenset[RelationType] = frozenset(
    {RelationType.PREREQUISITE, RelationType.CONTAINS}
)

DEFAULT_RUBRIC_VERSION = 1


@dataclass(slots=True)
class KnowledgeNode:
    """最小知识点。

    ``source_status`` 记录来源可信度；AI 生成先是 ``ai_draft``，
    验证后才可成为共享知识。
    """

    node_id: str
    project_id: str
    stable_key: str
    title: str
    node_type: KnowledgeNodeType
    objectives: list[str] = field(default_factory=list)
    content_version: int = 1
    source_status: str = "ai_draft"
    supersedes_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @staticmethod
    def create(
        *,
        project_id: str,
        stable_key: str,
        title: str,
        node_type: KnowledgeNodeType,
        objectives: Iterable[str] = (),
        now: datetime | None = None,
    ) -> "KnowledgeNode":
        key = require_stable_key(
            stable_key if stable_key else slugify_stable_key(title, fallback_prefix="node")
        )
        _require_text(title, "节点标题", max_len=200)
        return KnowledgeNode(
            node_id=new_id("nod"),
            project_id=project_id,
            stable_key=key,
            title=title.strip(),
            node_type=node_type,
            objectives=[o.strip() for o in objectives if o and o.strip()],
            created_at=now or datetime.now(timezone.utc),
        )

    def revise_content(self, *, title: str | None = None, objectives: Iterable[str] | None = None) -> None:
        """内容修订：标题可改，``stable_key`` 不变。"""
        if title is not None:
            _require_text(title, "节点标题", max_len=200)
            self.title = title.strip()
        if objectives is not None:
            self.objectives = [o.strip() for o in objectives if o and o.strip()]
        self.content_version += 1


@dataclass(frozen=True, slots=True)
class KnowledgeRelation:
    """节点间关系。``scope`` 用于隔离跨项目关系。"""

    relation_id: str
    scope: str  # project_id 或 "global"
    from_id: str
    to_id: str
    relation_type: RelationType

    @staticmethod
    def create(
        *,
        scope: str,
        from_id: str,
        to_id: str,
        relation_type: RelationType,
    ) -> "KnowledgeRelation":
        if from_id == to_id:
            raise ValidationAppError("节点不能与自身建立关系")
        return KnowledgeRelation(
            relation_id=new_id("rel"),
            scope=scope,
            from_id=from_id,
            to_id=to_id,
            relation_type=relation_type,
        )


@dataclass(slots=True)
class LearningUnit:
    """学习单元：总结与评审的主体。

    ``rubric_version`` 与内容版本分开管理：新 rubric 改动时，
    旧总结保留，但不宣称已满足新目标。
    """

    unit_id: str
    project_id: str
    stable_key: str
    title: str
    objectives: list[str] = field(default_factory=list)
    rubric: dict[str, object] = field(default_factory=dict)
    rubric_version: int = DEFAULT_RUBRIC_VERSION
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @staticmethod
    def create(
        *,
        project_id: str,
        stable_key: str,
        title: str,
        objectives: Iterable[str] = (),
        rubric: dict[str, object] | None = None,
        now: datetime | None = None,
    ) -> "LearningUnit":
        key = require_stable_key(
            stable_key if stable_key else slugify_stable_key(title, fallback_prefix="unit")
        )
        _require_text(title, "单元标题", max_len=200)
        return LearningUnit(
            unit_id=new_id("unt"),
            project_id=project_id,
            stable_key=key,
            title=title.strip(),
            objectives=[o.strip() for o in objectives if o and o.strip()],
            rubric=dict(rubric or {}),
            created_at=now or datetime.now(timezone.utc),
        )

    def snapshot_rubric(self) -> dict[str, object]:
        """取 rubric 快照：总结提交时必须连同 rubric_version 一起保存，
        使历史评审结论可追溯到当时的评判标准。
        """
        return {
            "unit_id": self.unit_id,
            "stable_key": self.stable_key,
            "rubric_version": self.rubric_version,
            "objectives": list(self.objectives),
            "rubric": dict(self.rubric),
        }


@dataclass(frozen=True, slots=True)
class UnitNodeLink:
    """单元包含节点（一个单元多节点；节点可被多单元复用）。"""

    unit_id: str
    node_id: str
    order_index: int
    role: TaskKnowledgeRole = TaskKnowledgeRole.CORE


@dataclass(slots=True)
class DependencyGraph:
    """依赖图的无环校验器。

    用 Kahn 拓扑排序实现：能在 O(V+E) 内既判环又给出环上节点，
    比递归 DFS 更适合需要输出「哪些节点参与成环」的场景。
    """

    _edges: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    _indegree: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    _nodes: set[str] = field(default_factory=set)

    def add_node(self, node_id: str) -> None:
        self._nodes.add(node_id)
        self._indegree.setdefault(node_id, 0)

    def add_edge(self, from_id: str, to_id: str) -> None:
        """from -> to 表示 from 是 to 的前置。"""
        self.add_node(from_id)
        self.add_node(to_id)
        if to_id in self._edges[from_id]:
            return
        self._edges[from_id].add(to_id)
        self._indegree[to_id] += 1

    def find_cycle(self) -> list[str]:
        """返回一个环（节点序列）；无环时返回空列表。"""
        indegree = dict(self._indegree)
        queue: deque[str] = deque(
            n for n in self._nodes if indegree.get(n, 0) == 0
        )
        visited = 0
        while queue:
            current = queue.popleft()
            visited += 1
            for nxt in self._edges.get(current, ()):  # type: ignore[arg-type]
                indegree[nxt] -= 1
                if indegree[nxt] == 0:
                    queue.append(nxt)

        if visited == len(self._nodes):
            return []

        # 仍有入度的节点处在环中或依赖环
        remaining = {n for n in self._nodes if indegree.get(n, 0) > 0}
        return _extract_cycle(self._edges, remaining)

    def is_acyclic(self) -> bool:
        return not self.find_cycle()

    def topological_order(self) -> list[str]:
        """稳定的拓扑序：同层按节点 ID 排序，保证生成结果可复现。"""
        indegree = dict(self._indegree)
        ready = sorted(n for n in self._nodes if indegree.get(n, 0) == 0)
        order: list[str] = []
        while ready:
            current = ready.pop(0)
            order.append(current)
            for nxt in sorted(self._edges.get(current, ())):  # type: ignore[arg-type]
                indegree[nxt] -= 1
                if indegree[nxt] == 0:
                    ready.append(nxt)
                    ready.sort()
        if len(order) != len(self._nodes):
            raise ConflictError("依赖图存在环，无法拓扑排序")
        return order


def _extract_cycle(edges: dict[str, set[str]], candidates: set[str]) -> list[str]:
    """在候选集合中找出任意一个具体环，便于报错定位。"""
    for start in sorted(candidates):
        path: list[str] = []
        seen: dict[str, int] = {}
        current = start
        while current is not None and current in candidates:
            if current in seen:
                return path[seen[current]:] + [current]
            seen[current] = len(path)
            path.append(current)
            nxt = [n for n in sorted(edges.get(current, ())) if n in candidates]  # type: ignore[arg-type]
            current = nxt[0] if nxt else None  # type: ignore[assignment]
    return sorted(candidates)


def build_dependency_graph(
    relations: Iterable[KnowledgeRelation],
) -> DependencyGraph:
    """把有序关系装配成依赖图。``related`` / ``alternative`` 不参与环判定。"""
    graph = DependencyGraph()
    for relation in relations:
        if relation.relation_type in ACYCLIC_RELATION_TYPES:
            graph.add_edge(relation.from_id, relation.to_id)
        else:
            graph.add_node(relation.from_id)
            graph.add_node(relation.to_id)
    return graph


def validate_relations(
    *,
    project_id: str,
    relations: Iterable[KnowledgeRelation],
    known_node_ids: set[str] | None = None,
) -> None:
    """校验关系集合。

    - 跨项目拒绝。
    - 引用不存在的节点拒绝（当提供了 ``known_node_ids``）。
    - 有序关系成环拒绝，错误信息带具体环路径。
    """
    relation_list = list(relations)
    for relation in relation_list:
        if relation.scope not in {project_id, "global"}:
            raise ValidationAppError("不允许跨项目的知识关系")
    if known_node_ids is not None:
        for relation in relation_list:
            for node_id in (relation.from_id, relation.to_id):
                if node_id not in known_node_ids:
                    raise NotFoundError("关系引用了不存在的知识节点")
    cycle = build_dependency_graph(relation_list).find_cycle()
    if cycle:
        raise ConflictError(
            "前置依赖存在环，请修复后再提交",
            cycle=[_short(node) for node in cycle],
        )


def _short(node_id: str) -> str:
    return node_id if len(node_id) <= 16 else f"{node_id[:13]}..."


def _require_text(value: str, field: str, *, max_len: int) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValidationAppError(f"{field}不能为空")
    if len(value) > max_len:
        raise ValidationAppError(f"{field}长度不得超过 {max_len} 字符")


__all__ = [
    "ACYCLIC_RELATION_TYPES",
    "DEFAULT_RUBRIC_VERSION",
    "DependencyGraph",
    "KnowledgeNode",
    "KnowledgeRelation",
    "LearningUnit",
    "UnitNodeLink",
    "build_dependency_graph",
    "validate_relations",
]
