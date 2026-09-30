"""运行投影端口（``ai_runs``）与规划目录物化端口。

两个端口都**只**服务于「应用层编排」，不含任何业务规则：

- :class:`RunRepositoryPort`：写/读对外运行状态。每次调用都必须带项目上下文，
  实现须在 SQL 层（RLS）与应用层双重校验。
- :class:`PlanningCatalogPort`：把图产物（节点/单元/关系/实践/任务关联）
  幂等地物化为**既有稳定实体**，返回稳定键 → 实体 ID 的映射。
  计划快照只引用这些实体，因此物化必须发生在发布之前。
"""

from __future__ import annotations

from typing import Protocol, Sequence, runtime_checkable

from app.domain.runs.models import RunRecord


@runtime_checkable
class RunRepositoryPort(Protocol):
    """对外运行状态投影的读写。"""

    def create_run(self, run: RunRecord) -> None: ...

    def get_run(self, *, project_id: str, run_id: str) -> RunRecord | None: ...

    def get_progress(self, *, project_id: str, run_id: str) -> dict[str, object] | None:
        """Latest **business** progress for a run, corrected by the paid-attempt ledger.

        Returns ``None`` when the run never published progress (for example a run
        from an older protocol). Never exposes thread ids, node names, raw
        checkpoints or prompts; token counts stay ``None`` when unknown.
        """
        ...

    def update_run(
        self,
        *,
        project_id: str,
        run_id: str,
        expected_version: int,
        status: str,
        next_action: str,
        result_ref: str | None = None,
        error_class: str | None = None,
    ) -> RunRecord:
        """**状态条件**更新（乐观并发）：版本号自增，返回更新后的记录。"""
        ...


@runtime_checkable
class PlanningCatalogPort(Protocol):
    """把图产物物化为稳定实体（幂等：按 ``stable_key`` 复用）。"""

    def materialize(
        self,
        *,
        project_id: str,
        nodes: Sequence[dict[str, object]],
        units: Sequence[dict[str, object]],
        relations: Sequence[dict[str, object]],
        practice: dict[str, object] | None = None,
    ) -> "CatalogIds": ...


class CatalogIds:
    """物化结果：稳定键 → 实体 ID。

    ``practice`` 里的任务稳定键映射到 ``task_id``。
    """

    __slots__ = ("node_ids", "unit_ids", "practice_project_id", "task_ids")

    def __init__(
        self,
        *,
        node_ids: dict[str, str],
        unit_ids: dict[str, str],
        practice_project_id: str,
        task_ids: dict[str, str],
    ) -> None:
        self.node_ids = node_ids
        self.unit_ids = unit_ids
        self.practice_project_id = practice_project_id
        self.task_ids = task_ids


__all__ = ["CatalogIds", "PlanningCatalogPort", "RunRepositoryPort"]
