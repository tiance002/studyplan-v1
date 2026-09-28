"""``PlanningCatalogPort`` 的 PostgreSQL 实现：把图产物物化为**稳定实体**。

## 为什么需要它

计划快照（``plan_unit_links`` / ``plan_task_links`` / ``plan_task_knowledge_links``）
只**引用**既有实体 ID，而 0003/0004 的复合 FK 要求这些实体真实存在于**同一项目**。
因此「生成草案 → 发布」之间必须先物化：

    knowledge_nodes / learning_units / unit_node_links / knowledge_relations
    practice_projects / practice_tasks / task_knowledge_links

## 幂等（按 ``stable_key`` 复用）

实体 ID 由 ``(project_id, content_version, stable_key)`` **确定性派生**，并用
``ON CONFLICT ... DO NOTHING`` 复用既有行。因此「同一目标重新生成」不会
造出重复节点/单元/任务，也不会破坏历史计划的引用。

## 边界

本模块**不做任何业务规则**（不判重、不算覆盖率、不合并相似标题）；
它只把已经通过结构校验的图产物落库。
"""

from __future__ import annotations

import base64
import hashlib
import json
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from typing import Any

import psycopg
from app.core.ids import new_id
from app.infrastructure.db.plan_repository import to_psycopg_dsn
from app.ports.runs import CatalogIds
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

__all__ = ["PgPlanningCatalog", "stable_entity_id"]

def stable_entity_id(prefix: str, project_id: str, stable_key: str) -> str:
    """Lossless encoding; dots, underscores, whitespace and long keys stay distinct."""
    identity = json.dumps([project_id, stable_key], ensure_ascii=False, separators=(",", ":"))
    encoded = base64.urlsafe_b64encode(identity.encode("utf-8")).decode("ascii").rstrip("=")
    return f"{prefix}_{encoded}"


def _as_dicts(raw: object) -> list[dict[str, object]]:
    if not isinstance(raw, (list, tuple)):
        return []
    return [dict(item) for item in raw if isinstance(item, dict)]


def _str_list(raw: object) -> list[str]:
    """把 JSON 数组规整为非空字符串列表（图产物是 JSON 可序列化结构）。"""
    if not isinstance(raw, (list, tuple)):
        return []
    return [str(v).strip() for v in raw if str(v).strip()]


def _as_dict(raw: object) -> dict[str, object]:
    if not isinstance(raw, dict):
        return {}
    return {str(k): v for k, v in raw.items()}


def _text(value: object, default: str = "") -> str:
    return str(value).strip() if value is not None else default


class PgPlanningCatalog:
    """幂等物化图产物。所有写入在**单个事务**内完成。"""

    def __init__(self, dsn: str) -> None:
        self._dsn = to_psycopg_dsn(dsn)

    @contextmanager
    def _tx(self, project_id: str) -> Iterator[psycopg.Connection[dict[str, Any]]]:
        with psycopg.connect(
            self._dsn, row_factory=dict_row
        ) as conn:  # type: psycopg.Connection[dict[str, Any]]
            conn.execute("SELECT set_config('app.project_id', %s, true)", (project_id,))
            yield conn

    def materialize(
        self,
        *,
        project_id: str,
        nodes: Sequence[dict[str, object]],
        units: Sequence[dict[str, object]],
        relations: Sequence[dict[str, object]],
        practice: dict[str, object] | None = None,
    ) -> CatalogIds:
        node_ids: dict[str, str] = {}
        unit_ids: dict[str, str] = {}
        task_ids: dict[str, str] = {}
        practice_project_id = ""

        # Immutable generation snapshot. Identical graph content reuses its entities;
        # changed content gets new IDs, while legacy IDs/FKs remain untouched.
        content = json.dumps([nodes, units, relations, practice], sort_keys=True,
                             ensure_ascii=False, separators=(",", ":"))
        namespace = project_id + ":" + hashlib.sha256(content.encode()).hexdigest()
        with self._tx(project_id) as conn:
            for node in nodes:
                key = _text(node.get("stable_key"))
                if not key:
                    continue
                node_id = stable_entity_id("nod", namespace, key)
                node_ids[key] = node_id
                conn.execute(
                    """
                    INSERT INTO knowledge_nodes
                        (node_id, project_id, stable_key, title, node_type,
                         objectives, source_status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (node_id) DO NOTHING
                    """,
                    (
                        node_id,
                        project_id,
                        key,
                        _text(node.get("title"), key),
                        _text(node.get("node_type"), "concept"),
                        Jsonb(_str_list(node.get("objectives"))),
                        # 模型产物一律标记为 AI 草稿，**不得**冒充已验证来源。
                        "ai_draft",
                    ),
                )

            for unit in units:
                key = _text(unit.get("stable_key"))
                if not key:
                    continue
                unit_id = stable_entity_id("unt", namespace, key)
                unit_ids[key] = unit_id
                conn.execute(
                    """
                    INSERT INTO learning_units
                        (unit_id, project_id, stable_key, title, objectives, rubric,
                         rubric_version)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (unit_id) DO NOTHING
                    """,
                    (
                        unit_id,
                        project_id,
                        key,
                        _text(unit.get("title"), key),
                        Jsonb(_str_list(unit.get("objectives"))),
                        Jsonb(_as_dict(unit.get("rubric"))),
                        1,
                    ),
                )
                # 单元包含的节点（按 order_index）。
                node_keys = _str_list(unit.get("node_keys"))
                for order, node_key in enumerate(node_keys):
                    node_id = node_ids.get(node_key)
                    if not node_id:
                        continue
                    conn.execute(
                        """
                        INSERT INTO unit_node_links
                            (link_id, project_id, unit_id, node_id, order_index, role)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (unit_id, node_id) DO NOTHING
                        """,
                        (new_id("unl"), project_id, unit_id, node_id, order, "core"),
                    )

            for relation in relations:
                from_key = _text(relation.get("from_stable_key"))
                to_key = _text(relation.get("to_stable_key"))
                from_id = node_ids.get(from_key)
                to_id = node_ids.get(to_key)
                if not from_id or not to_id or from_id == to_id:
                    continue
                conn.execute(
                    """
                    INSERT INTO knowledge_relations
                        (relation_id, project_id, from_node_id, to_node_id, relation_type)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (project_id, from_node_id, to_node_id, relation_type)
                    DO NOTHING
                    """,
                    (
                        new_id("rel"),
                        project_id,
                        from_id,
                        to_id,
                        _text(relation.get("relation_type"), "prerequisite"),
                    ),
                )

            if practice:
                practice_project_id, task_ids = self._materialize_practice(
                    conn, project_id=project_id, namespace=namespace, practice=practice, node_ids=node_ids
                )

        return CatalogIds(
            node_ids=node_ids,
            unit_ids=unit_ids,
            practice_project_id=practice_project_id,
            task_ids=task_ids,
        )

    # ------------------------------------------------------------------ 实践

    def _materialize_practice(
        self,
        conn: psycopg.Connection[dict[str, Any]],
        *,
        project_id: str,
        practice: dict[str, object],
        namespace: str,
        node_ids: dict[str, str],
    ) -> tuple[str, dict[str, str]]:
        project_key = _text(practice.get("stable_key"), "practice")
        practice_project_id = stable_entity_id("ppj", namespace, project_key)
        conn.execute(
            """
            INSERT INTO practice_projects
                (practice_project_id, project_id, title, idea, status)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (practice_project_id) DO NOTHING
            """,
            (
                practice_project_id,
                project_id,
                _text(practice.get("title"), project_key),
                _text(practice.get("idea"), "待补充的项目想法"),
                "idea",
            ),
        )

        task_ids: dict[str, str] = {}
        for task in _as_dicts(practice.get("tasks")):
            key = _text(task.get("stable_key"))
            if not key:
                continue
            task_id = stable_entity_id("ptk", namespace, key)
            task_ids[key] = task_id
            acceptance = _str_list(task.get("acceptance"))
            conn.execute(
                """
                INSERT INTO practice_tasks
                    (task_id, project_id, practice_project_id, stable_key, title,
                     goal, in_scope, out_scope, acceptance, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (task_id) DO NOTHING
                """,
                (
                    task_id,
                    project_id,
                    practice_project_id,
                    key,
                    _text(task.get("title"), key),
                    _text(task.get("goal"), "完成该阶段的可验收交付物"),
                    Jsonb(_str_list(task.get("in_scope"))),
                    Jsonb(_str_list(task.get("out_scope"))),
                    Jsonb(acceptance),
                    "pending",
                ),
            )
            for link in _as_dicts(task.get("knowledge_links")):
                node_id = node_ids.get(_text(link.get("node_stable_key")))
                if not node_id:
                    continue
                conn.execute(
                    """
                    INSERT INTO task_knowledge_links (link_id, project_id, task_id, node_id, role)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (task_id, node_id) DO NOTHING
                    """,
                    (
                        new_id("tkl"),
                        project_id,
                        task_id,
                        node_id,
                        _text(link.get("role"), "core"),
                    ),
                )
        return practice_project_id, task_ids
