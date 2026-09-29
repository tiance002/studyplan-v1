"""PostgreSQL 实现的 ``PlanRepositoryPort``（B2-C §「真实 PG 端口契约」）。

## 事务契约（Goal §6 / B2-C §3）

``publish_revision`` **必须**在单一事务内完成：

    草案状态检查 → 版本检查 → 新建 PlanRevision → 写 unit/task 链接 →
    切换当前引用 → 标记被替代版本 → 更新草案状态 → 写发布记录

任何一步失败整体回滚，**不得留下半发布状态**——尤其**不得**把被替代版本
错误地留在 SUPERSEDED（回滚必须恢复其原状态）。本实现靠
``with psycopg.connect(...)`` 的事务边界实现：块内异常 → 自动 ROLLBACK。

## 幂等（不靠「先查后写」）

幂等由 **DB 唯一索引** ``plan_publications_project_idem_unique
ON (project_id, idempotency_key)`` 保证。并发下只有一个事务能插入成功，
另一个收到 ``UniqueViolation`` 并整体回滚。应用层先用
``find_publish_by_idempotency_key`` 复用既有结果（同键同体）或报 409（同键异体）。

## 隔离（RLS）

所有语句都在 ``SET LOCAL app.project_id`` 上下文下执行，连接使用**应用角色**
（``studyplan_app``，NOBYPASSRLS）。因此跨项目读写会被数据库直接拒绝，
而不是仅靠应用层自觉。

## 结构载体

按设计 §3，结构以**规范化子表**（``plan_stages`` / ``plan_unit_links`` /
``plan_task_links`` / ``stage_resource_assignments`` / ``knowledge_extensions``）
为准；``plan_revisions.structure`` 同步写入一份等价 jsonb 快照，供审计与
调试，**不作为读回依据**（避免两份真相分叉）。
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from typing import Any

import psycopg
from app.core.errors import ConflictError
from app.core.ids import new_id
from app.domain.enums import (
    OutlineSectionKind,
    PlanDraftStatus,
    PlanRevisionStatus,
    StageResourceRole,
    TaskKnowledgeRole,
)
from app.domain.planning.models import (
    PlanDraft,
    PlanRevision,
    PlanStage,
    PlanTaskKnowledgeLink,
    PlanTaskLink,
    PlanUnitLink,
    PublishRecord,
)
from app.domain.resources.curation import (
    KnowledgeExtension,
    StageResourceAssignment,
)
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

__all__ = ["PgPlanRepository", "to_psycopg_dsn"]

#: 可被发布的草案状态（其余一律拒绝：已取消 / 已处理 / 已失效）。
PUBLISHABLE_DRAFT_STATUSES: tuple[str, ...] = (
    PlanDraftStatus.PENDING.value,
    PlanDraftStatus.AWAITING_APPROVAL.value,
)

#: 终态草案不可再被 ``save_draft`` 改写（B2-V §二.3/.4）。
TERMINAL_DRAFT_STATUSES: tuple[str, ...] = (
    PlanDraftStatus.CANCELLED.value,
    PlanDraftStatus.APPROVED.value,
)


def to_psycopg_dsn(dsn: str) -> str:
    """把 ``postgresql+psycopg://`` 形式的 DSN 转成 psycopg 可用的形式。"""
    return dsn.replace("postgresql+psycopg://", "postgresql://")


# --------------------------------------------------------------------- 序列化


def _stage_payload(stage: PlanStage) -> dict[str, Any]:
    return {
        "stage_id": stage.stage_id,
        "stable_key": stage.stable_key,
        "title": stage.title,
        "section_kind": str(stage.section_kind),
        "order_index": stage.order_index,
        "objective": stage.objective,
    }


def _unit_link_payload(link: PlanUnitLink) -> dict[str, Any]:
    return {
        "stage_id": link.stage_id,
        "unit_id": link.unit_id,
        "order_index": link.order_index,
    }


def _task_link_payload(link: PlanTaskLink) -> dict[str, Any]:
    return {
        "stage_id": link.stage_id,
        "task_id": link.task_id,
        "order_index": link.order_index,
    }


def _task_knowledge_payload(link: PlanTaskKnowledgeLink) -> dict[str, Any]:
    return {"task_id": link.task_id, "node_id": link.node_id, "role": str(link.role)}


def _task_knowledge_from(row: dict[str, Any]) -> PlanTaskKnowledgeLink:
    return PlanTaskKnowledgeLink(
        task_id=str(row["task_id"]),
        node_id=str(row["node_id"]),
        role=TaskKnowledgeRole(str(row.get("role") or TaskKnowledgeRole.CORE)),
    )


def _assignment_payload(a: StageResourceAssignment) -> dict[str, Any]:
    return {
        "assignment_id": a.assignment_id,
        "stage_id": a.stage_id,
        "role": str(a.role),
        "source_ref": a.source_ref,
        "section_refs": list(a.section_refs),
        "order_index": a.order_index,
        "source_version": a.source_version,
        "fallback_search_terms": list(a.fallback_search_terms),
        **({"node_ids": list(a.node_ids)} if a.node_ids else {}),
    }


def _extension_payload(e: KnowledgeExtension) -> dict[str, Any]:
    return {
        "extension_id": e.extension_id,
        "stage_id": e.stage_id,
        "topic": e.topic,
        "concepts": list(e.concepts),
        "guidance": e.guidance,
        "links": list(e.links),
        "search_hints": list(e.search_hints),
        "thinking_prompts": list(e.thinking_prompts),
        "required": e.required,
        "order_index": e.order_index,
        "unit_id": e.unit_id,
    }


def _structure_payload(revision: PlanRevision) -> dict[str, Any]:
    """``plan_revisions.structure`` 的等价快照（审计用，非读回依据）。"""
    return {
        "stages": [_stage_payload(s) for s in revision.stages],
        "unit_links": [_unit_link_payload(x) for x in revision.unit_links],
        "task_links": [_task_link_payload(x) for x in revision.task_links],
        "task_knowledge_links": [
            _task_knowledge_payload(x) for x in revision.task_knowledge_links
        ],
        "stage_resources": [_assignment_payload(x) for x in revision.stage_resources],
        "extensions": [_extension_payload(x) for x in revision.extensions],
        "approved_at": revision.approved_at.isoformat() if revision.approved_at else None,
    }


def _draft_payload(draft: PlanDraft) -> dict[str, Any]:
    return {
        "goal_snapshot": draft.goal_snapshot,
        "revision_candidate": draft.revision_candidate,
        "stages": [_stage_payload(s) for s in draft.stages],
        "unit_refs": list(draft.unit_refs),
        "task_refs": list(draft.task_refs),
        "node_stable_keys": list(draft.node_stable_keys),
        "unit_links": [_unit_link_payload(x) for x in draft.unit_links],
        "task_links": [_task_link_payload(x) for x in draft.task_links],
        "task_knowledge_links": [
            _task_knowledge_payload(x) for x in draft.task_knowledge_links
        ],
        "stage_resources": [_assignment_payload(x) for x in draft.stage_resources],
        "extensions": [_extension_payload(x) for x in draft.extensions],
        "source_pack_key": draft.source_pack_key,
        "source_pack_version": draft.source_pack_version,
        "practice_project_idea": draft.practice_project_idea,
        "validation_warnings": list(draft.validation_warnings),
    }


def _as_list(raw: object) -> list[object]:
    return list(raw) if isinstance(raw, (list, tuple)) else []


def _stage_from(row: dict[str, Any]) -> PlanStage:
    return PlanStage(
        stage_id=str(row["stage_id"]),
        stable_key=str(row["stable_key"]),
        title=str(row["title"]),
        section_kind=OutlineSectionKind(str(row["section_kind"])),
        order_index=int(row["order_index"]),  # type: ignore[arg-type]
        objective=str(row.get("objective") or ""),
    )


def _unit_link_from(row: dict[str, Any]) -> PlanUnitLink:
    return PlanUnitLink(
        stage_id=str(row["stage_id"]),
        unit_id=str(row["unit_id"]),
        order_index=int(row["order_index"]),  # type: ignore[arg-type]
    )


def _task_link_from(row: dict[str, Any]) -> PlanTaskLink:
    return PlanTaskLink(
        stage_id=str(row["stage_id"]),
        task_id=str(row["task_id"]),
        order_index=int(row["order_index"]),  # type: ignore[arg-type]
    )


def _assignment_from(row: dict[str, Any], *, project_id: str, plan_id: str) -> StageResourceAssignment:
    return StageResourceAssignment(
        assignment_id=str(row["assignment_id"]),
        project_id=project_id,
        plan_id=plan_id,
        stage_id=str(row["stage_id"]),
        role=StageResourceRole(str(row["role"])),
        source_ref=str(row.get("source_ref") or ""),
        section_refs=tuple(str(s) for s in _as_list(row.get("section_refs"))),
        order_index=int(row.get("order_index") or 0),
        source_version=int(row.get("source_version") or 0),
        fallback_search_terms=tuple(str(s) for s in _as_list(row.get("fallback_search_terms"))),
        snapshot_at=row.get("snapshot_at"),  # type: ignore[arg-type]
        node_ids=tuple(str(n) for n in _as_list(row.get("node_ids"))),
    )


def _extension_from(row: dict[str, Any], *, project_id: str, plan_id: str) -> KnowledgeExtension:
    unit_id = row.get("unit_id")
    return KnowledgeExtension(
        extension_id=str(row["extension_id"]),
        project_id=project_id,
        plan_id=plan_id,
        stage_id=str(row["stage_id"]),
        topic=str(row["topic"]),
        concepts=tuple(str(s) for s in _as_list(row.get("concepts"))),
        guidance=str(row.get("guidance") or ""),
        links=tuple(str(s) for s in _as_list(row.get("links"))),
        search_hints=tuple(str(s) for s in _as_list(row.get("search_hints"))),
        thinking_prompts=tuple(str(s) for s in _as_list(row.get("thinking_prompts"))),
        required=bool(row.get("required")),
        order_index=int(row.get("order_index") or 0),
        unit_id=str(unit_id) if unit_id is not None else None,
    )


def _parse_dt(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None


# ------------------------------------------------------------------- 仓储实现


class PgPlanRepository:
    """``PlanRepositoryPort`` 的 PostgreSQL 实现。

    每次调用使用一个独立连接；``publish_revision`` 的整个写入序列落在
    单个事务内。构造只接收 DSN，便于在测试里指向临时库。
    """

    def __init__(self, dsn: str) -> None:
        self._dsn = to_psycopg_dsn(dsn)

    @contextmanager
    def _tx(self, project_id: str) -> Iterator[psycopg.Connection[dict[str, Any]]]:
        """开启一个带项目上下文的单事务连接。

        退出时正常提交、异常回滚——这正是 ``publish_revision`` 原子性的来源。
        """
        with psycopg.connect(
            self._dsn, row_factory=dict_row
        ) as conn:  # type: psycopg.Connection[dict[str, Any]]
            # set_config(..., is_local=true)：上下文仅在本事务内有效。
            conn.execute("SELECT set_config('app.project_id', %s, true)", (project_id,))
            yield conn

    # ------------------------------------------------------------- 草案

    def save_draft(self, draft: PlanDraft, *, expected_hash: str | None = None) -> None:
        """保存草案；**状态条件**更新 + **检查受影响行数**（B2-V §二.4）。

        - 已 ``cancelled`` / 已 ``approved`` 的草案不得被改写（行数为 0）；
        - 被条件挡下时**抛** :class:`ConflictError`，不静默忽略。
        """
        with self._tx(draft.project_id) as conn:
            cursor = conn.execute(
                """
                INSERT INTO plan_drafts
                    (draft_id, project_id, run_id, status, content_hash,
                     revision_candidate, payload, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, now())
                ON CONFLICT (draft_id) DO UPDATE SET
                    status = EXCLUDED.status,
                    content_hash = EXCLUDED.content_hash,
                    revision_candidate = EXCLUDED.revision_candidate,
                    payload = EXCLUDED.payload,
                    updated_at = now()
                WHERE plan_drafts.project_id = EXCLUDED.project_id
                  AND plan_drafts.status <> ALL(%s)
                  AND plan_drafts.content_hash = %s
                """,
                (
                    draft.draft_id,
                    draft.project_id,
                    draft.run_id or None,
                    draft.status.value,
                    draft.content_hash,
                    draft.revision_candidate,
                    Jsonb(_draft_payload(draft)),
                    list(TERMINAL_DRAFT_STATUSES),
                    expected_hash if expected_hash is not None else draft.content_hash,
                ),
            )
            if cursor.rowcount != 1:
                row = conn.execute("SELECT status FROM plan_drafts WHERE project_id=%s AND draft_id=%s",
                                   (draft.project_id, draft.draft_id)).fetchone()
                terminal = row is not None and row["status"] in TERMINAL_DRAFT_STATUSES
                raise ConflictError(
                    "Draft terminal or stale; reload before editing",
                    reason="draft_terminal" if terminal else "draft_stale",
                    draft_id=draft.draft_id,
                )

    def cancel_draft(self, *, project_id: str, draft_id: str) -> None:
        """**状态条件**取消草案（B2-V §二.4）。

        只有 ``awaiting_approval`` / ``pending`` 的草案可被取消；已被发布的
        草案不会被取消（行数为 0 → 抛冲突），因此「发布与取消并发」中
        失败的一方一定会**显式报错**，不会留下不一致状态。
        """
        with self._tx(project_id) as conn:
            cursor = conn.execute(
                "UPDATE plan_drafts SET status = %s, updated_at = now() "
                "WHERE project_id = %s AND draft_id = %s AND status = ANY(%s)",
                (
                    PlanDraftStatus.CANCELLED.value,
                    project_id,
                    draft_id,
                    list(PUBLISHABLE_DRAFT_STATUSES),
                ),
            )
            if cursor.rowcount != 1:
                raise ConflictError(
                    "草案已处理（已取消或已发布），不能再取消",
                    reason="draft_not_cancellable",
                    draft_id=draft_id,
                )

    def get_draft(self, *, project_id: str, draft_id: str) -> PlanDraft | None:
        with self._tx(project_id) as conn:
            row = conn.execute(
                "SELECT * FROM plan_drafts WHERE project_id = %s AND draft_id = %s",
                (project_id, draft_id),
            ).fetchone()
        if row is None:
            return None
        payload = row.get("payload") or {}
        if not isinstance(payload, dict):
            payload = {}
        return PlanDraft(
            draft_id=str(row["draft_id"]),
            project_id=str(row["project_id"]),
            run_id=str(row.get("run_id") or ""),
            goal_snapshot=str(payload.get("goal_snapshot") or ""),
            revision_candidate=int(row.get("revision_candidate") or 1),
            stages=tuple(_stage_from(s) for s in _as_list(payload.get("stages"))),  # type: ignore[arg-type]
            unit_refs=tuple(str(s) for s in _as_list(payload.get("unit_refs"))),
            task_refs=tuple(str(s) for s in _as_list(payload.get("task_refs"))),
            node_stable_keys=tuple(str(s) for s in _as_list(payload.get("node_stable_keys"))),
            unit_links=tuple(_unit_link_from(x) for x in _as_list(payload.get("unit_links"))),  # type: ignore[arg-type]
            task_links=tuple(_task_link_from(x) for x in _as_list(payload.get("task_links"))),  # type: ignore[arg-type]
            task_knowledge_links=tuple(
                _task_knowledge_from(x) for x in _as_list(payload.get("task_knowledge_links"))  # type: ignore[arg-type]
            ),
            stage_resources=tuple(
                _assignment_from(a, project_id=project_id, plan_id="")  # type: ignore[arg-type]
                for a in _as_list(payload.get("stage_resources"))
            ),
            extensions=tuple(
                _extension_from(e, project_id=project_id, plan_id="")  # type: ignore[arg-type]
                for e in _as_list(payload.get("extensions"))
            ),
            source_pack_key=str(payload.get("source_pack_key") or ""),
            source_pack_version=int(payload.get("source_pack_version") or 0),
            practice_project_idea=str(payload.get("practice_project_idea") or ""),
            status=PlanDraftStatus(str(row["status"])),
            validation_warnings=tuple(
                str(s) for s in _as_list(payload.get("validation_warnings"))
            ),
            created_at=row.get("created_at"),  # type: ignore[arg-type]
        )

    # ------------------------------------------------------------- 版本读

    def get_current(self, *, project_id: str) -> PlanRevision | None:
        with self._tx(project_id) as conn:
            row = conn.execute(
                "SELECT * FROM plan_revisions WHERE project_id = %s AND status = 'approved'",
                (project_id,),
            ).fetchone()
            if row is None:
                return None
            return self._load_revision(conn, row)

    def get_revision(self, *, project_id: str, revision: int) -> PlanRevision | None:
        with self._tx(project_id) as conn:
            row = conn.execute(
                "SELECT * FROM plan_revisions WHERE project_id = %s AND revision = %s",
                (project_id, revision),
            ).fetchone()
            if row is None:
                return None
            return self._load_revision(conn, row)

    def list_revisions(self, *, project_id: str) -> list[PlanRevision]:
        with self._tx(project_id) as conn:
            rows = conn.execute(
                "SELECT * FROM plan_revisions WHERE project_id = %s ORDER BY revision",
                (project_id,),
            ).fetchall()
            return [self._load_revision(conn, row) for row in rows]

    def _load_revision(self, conn: psycopg.Connection[dict[str, Any]], row: dict[str, Any]) -> PlanRevision:
        project_id = str(row["project_id"])
        plan_id = str(row["plan_id"])
        stages = conn.execute(
            "SELECT * FROM plan_stages WHERE project_id = %s AND plan_id = %s ORDER BY order_index",
            (project_id, plan_id),
        ).fetchall()
        unit_links = conn.execute(
            "SELECT l.* FROM plan_unit_links l "
            "JOIN plan_stages s ON s.project_id = l.project_id AND s.stage_id = l.stage_id "
            "WHERE l.project_id = %s AND l.plan_id = %s "
            "ORDER BY s.order_index, l.order_index",
            (project_id, plan_id),
        ).fetchall()
        task_links = conn.execute(
            "SELECT l.* FROM plan_task_links l "
            "JOIN plan_stages s ON s.project_id = l.project_id AND s.stage_id = l.stage_id "
            "WHERE l.project_id = %s AND l.plan_id = %s "
            "ORDER BY s.order_index, l.order_index",
            (project_id, plan_id),
        ).fetchall()
        assignments = conn.execute(
            "SELECT a.* FROM stage_resource_assignments a "
            "JOIN plan_stages s ON s.project_id = a.project_id AND s.stage_id = a.stage_id "
            "WHERE a.project_id = %s AND a.plan_id = %s "
            "ORDER BY s.order_index, a.order_index",
            (project_id, plan_id),
        ).fetchall()
        extensions = conn.execute(
            "SELECT e.* FROM knowledge_extensions e "
            "JOIN plan_stages s ON s.project_id = e.project_id AND s.stage_id = e.stage_id "
            "WHERE e.project_id = %s AND e.plan_id = %s "
            "ORDER BY s.order_index, e.order_index",
            (project_id, plan_id),
        ).fetchall()
        task_knowledge = conn.execute(
            "SELECT * FROM plan_task_knowledge_links "
            "WHERE project_id = %s AND plan_id = %s ORDER BY order_index",
            (project_id, plan_id),
        ).fetchall()
        structure = row.get("structure") or {}
        approved_at = _parse_dt(structure.get("approved_at")) if isinstance(structure, dict) else None
        return PlanRevision(
            plan_id=plan_id,
            project_id=project_id,
            revision=int(row["revision"]),  # type: ignore[arg-type]
            goal_snapshot=str(row["goal_snapshot"]),
            stages=tuple(_stage_from(s) for s in stages),  # type: ignore[arg-type]
            unit_links=tuple(_unit_link_from(x) for x in unit_links),  # type: ignore[arg-type]
            task_links=tuple(_task_link_from(x) for x in task_links),  # type: ignore[arg-type]
            task_knowledge_links=tuple(
                PlanTaskKnowledgeLink(
                    task_id=str(x["task_id"]),
                    node_id=str(x["node_id"]),
                    role=TaskKnowledgeRole(str(x["role"])),
                )
                for x in task_knowledge
            ),
            stage_resources=tuple(
                _assignment_from(a, project_id=project_id, plan_id=plan_id)  # type: ignore[arg-type]
                for a in assignments
            ),
            extensions=tuple(
                _extension_from(e, project_id=project_id, plan_id=plan_id)  # type: ignore[arg-type]
                for e in extensions
            ),
            source_pack_key=str(row.get("source_pack_key") or ""),
            source_pack_version=int(row.get("source_pack_version") or 0),
            status=PlanRevisionStatus(str(row["status"])),
            approved_at=approved_at,
            created_at=row.get("created_at"),  # type: ignore[arg-type]
        )

    # ------------------------------------------------------------- 幂等记录

    def find_publish_by_idempotency_key(
        self, *, project_id: str, idempotency_key: str
    ) -> PublishRecord | None:
        with self._tx(project_id) as conn:
            row = conn.execute(
                "SELECT plan_id, revision, idempotency_key, body_fingerprint, structure_fingerprint "
                "FROM plan_publications WHERE project_id = %s AND idempotency_key = %s",
                (project_id, idempotency_key),
            ).fetchone()
        if row is None:
            return None
        return PublishRecord(
            plan_id=str(row["plan_id"]),
            revision=int(row["revision"]),  # type: ignore[arg-type]
            idempotency_key=str(row["idempotency_key"]),
            body_fingerprint=str(row["body_fingerprint"]),
            structure_fingerprint=str(row["structure_fingerprint"]),
        )

    # ------------------------------------------------------------- 原子发布

    def publish_revision(
        self,
        *,
        draft: PlanDraft,
        revision: PlanRevision,
        superseded: PlanRevision | None,
        idempotency_key: str,
        body_fingerprint: str,
        created: bool = True,
    ) -> None:
        """**单事务**落定一次发布。任一步失败整体回滚（B2-V §二）。

        事务内**先复核草案最新状态**（``FOR UPDATE`` 行锁），再按状态条件更新
        草案并检查受影响行数——因此调用方持有的**过期对象不会被信任**：
        「已取消的草案被旧对象发布」「取消与发布并发」都会在数据库层被挡住，
        且失败方**显式报错**而不是静默产生不一致。

        ``created=False`` 为「结构与当前路线一致 → 复用当前版本」：
        只更新草案状态 + 写发布记录（B2-V §四：复用也必须持久化幂等结果）。
        """
        project_id = revision.project_id
        with self._tx(project_id) as conn:
            # 0) **事务内复核草案最新状态**（不信任调用方持有的旧对象）。
            row = conn.execute(
                "SELECT status, content_hash FROM plan_drafts "
                "WHERE project_id = %s AND draft_id = %s FOR UPDATE",
                (project_id, draft.draft_id),
            ).fetchone()
            if row is None:
                raise ConflictError(
                    "草案不存在，无法发布",
                    reason="draft_not_found",
                    draft_id=draft.draft_id,
                )
            db_status = str(row["status"])
            if db_status not in PUBLISHABLE_DRAFT_STATUSES:
                raise ConflictError(
                    "草案已被取消或已处理，不能再发布",
                    reason="draft_not_publishable",
                    status=db_status,
                )
            # 草案内容也必须与调用方声称的一致：防止发布**过期内容**。
            if str(row["content_hash"]) != draft.content_hash:
                raise ConflictError(
                    "草案内容已变化，请重新加载后再确认",
                    reason="draft_hash_mismatch",
                )

            if created:
                # 1) 先把旧的当前版本置为 superseded，避免与
                #    plan_revisions_current_unique(project_id WHERE approved) 冲突。
                if superseded is not None:
                    conn.execute(
                        "UPDATE plan_revisions SET status = %s "
                        "WHERE project_id = %s AND plan_id = %s",
                        (PlanRevisionStatus.SUPERSEDED.value, project_id, superseded.plan_id),
                    )

                # 2) 新版本本体（structure 为等价快照，读回以子表为准）。
                conn.execute(
                    """
                    INSERT INTO plan_revisions
                        (plan_id, project_id, revision, goal_snapshot, status, structure,
                         source_pack_key, source_pack_version)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        revision.plan_id,
                        project_id,
                        revision.revision,
                        revision.goal_snapshot,
                        revision.status.value,
                        Jsonb(_structure_payload(revision)),
                        revision.source_pack_key,
                        revision.source_pack_version,
                    ),
                )

                # 3) 阶段与链接（规范化子表）。
                for stage in revision.stages:
                    conn.execute(
                        """
                        INSERT INTO plan_stages
                            (stage_id, project_id, plan_id, stable_key, title,
                             section_kind, objective, order_index)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            stage.stage_id,
                            project_id,
                            revision.plan_id,
                            stage.stable_key,
                            stage.title,
                            str(stage.section_kind),
                            stage.objective,
                            stage.order_index,
                        ),
                    )
                for link in revision.unit_links:
                    conn.execute(
                        "INSERT INTO plan_unit_links"
                        "(link_id, project_id, plan_id, stage_id, unit_id, order_index) "
                        "VALUES (%s, %s, %s, %s, %s, %s)",
                        (
                            new_id("lnk"),
                            project_id,
                            revision.plan_id,
                            link.stage_id,
                            link.unit_id,
                            link.order_index,
                        ),
                    )
                for task_link in revision.task_links:
                    conn.execute(
                        "INSERT INTO plan_task_links"
                        "(link_id, project_id, plan_id, stage_id, task_id, order_index) "
                        "VALUES (%s, %s, %s, %s, %s, %s)",
                        (
                            new_id("lnk"),
                            project_id,
                            revision.plan_id,
                            task_link.stage_id,
                            task_link.task_id,
                            task_link.order_index,
                        ),
                    )

                # 3b) 任务-知识链接（B2-V §四 §五：规范化表 + 复合 FK）。
                for index, tk in enumerate(revision.task_knowledge_links):
                    conn.execute(
                        "INSERT INTO plan_task_knowledge_links"
                        "(link_id, project_id, plan_id, task_id, node_id, role, order_index) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                        (
                            new_id("tkl"),
                            project_id,
                            revision.plan_id,
                            tk.task_id,
                            tk.node_id,
                            str(tk.role),
                            index,
                        ),
                    )

                # 4) V1.2：阶段资源主线与扩展知识快照。
                for assignment in revision.stage_resources:
                    conn.execute(
                        """
                        INSERT INTO stage_resource_assignments
                            (assignment_id, project_id, plan_id, stage_id, role, source_ref,
                             section_refs, order_index, source_version, fallback_search_terms,
                             snapshot_at, node_ids)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            assignment.assignment_id,
                            project_id,
                            revision.plan_id,
                            assignment.stage_id,
                            str(assignment.role),
                            # 无核验来源时存 NULL（不是空串）：FK 只约束真实来源。
                            assignment.source_ref or None,
                            Jsonb(list(assignment.section_refs)),
                            assignment.order_index,
                            assignment.source_version,
                            Jsonb(list(assignment.fallback_search_terms)),
                            assignment.snapshot_at,
                            Jsonb(list(assignment.node_ids)),
                        ),
                    )
                for extension in revision.extensions:
                    conn.execute(
                        """
                        INSERT INTO knowledge_extensions
                            (extension_id, project_id, plan_id, stage_id, unit_id, topic,
                             concepts, guidance, links, search_hints, thinking_prompts,
                             required, order_index)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            extension.extension_id,
                            project_id,
                            revision.plan_id,
                            extension.stage_id,
                            extension.unit_id,
                            extension.topic,
                            Jsonb(list(extension.concepts)),
                            extension.guidance,
                            Jsonb(list(extension.links)),
                            Jsonb(list(extension.search_hints)),
                            Jsonb(list(extension.thinking_prompts)),
                            extension.required,
                            extension.order_index,
                        ),
                    )

            # 5) 草案状态：**状态条件**更新 + **检查受影响行数**（B2-V §二.4）。
            #    终态恒为 approved（不再读取调用方对象的状态，避免陈旧值）。
            cursor = conn.execute(
                "UPDATE plan_drafts SET status = %s, updated_at = now() "
                "WHERE project_id = %s AND draft_id = %s AND status = ANY(%s)",
                (
                    PlanDraftStatus.APPROVED.value,
                    project_id,
                    draft.draft_id,
                    list(PUBLISHABLE_DRAFT_STATUSES),
                ),
            )
            if cursor.rowcount != 1:
                raise ConflictError(
                    "草案状态已变化，发布已中止",
                    reason="draft_not_publishable",
                    draft_id=draft.draft_id,
                )

            # 6) 发布记录：幂等唯一索引在此生效（并发下唯一胜出）。
            conn.execute(
                """
                INSERT INTO plan_publications
                    (publication_id, project_id, plan_id, draft_hash, idempotency_key,
                     body_fingerprint, structure_fingerprint, revision)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    new_id("pub"),
                    project_id,
                    revision.plan_id,
                    draft.content_hash,
                    idempotency_key,
                    body_fingerprint,
                    revision.structure_fingerprint(),
                    revision.revision,
                ),
            )

    def set_current(self, *, project_id: str, plan_id: str) -> None:
        """把 ``plan_id`` 设为当前版本（其余 approved 置为 superseded）。"""
        with self._tx(project_id) as conn:
            conn.execute(
                "UPDATE plan_revisions SET status = %s "
                "WHERE project_id = %s AND status = 'approved' AND plan_id <> %s",
                (PlanRevisionStatus.SUPERSEDED.value, project_id, plan_id),
            )
            conn.execute(
                "UPDATE plan_revisions SET status = 'approved' "
                "WHERE project_id = %s AND plan_id = %s",
                (project_id, plan_id),
            )
