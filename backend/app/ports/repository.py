"""仓储端口：领域对象持久化边界。

设计约束：

- 所有查询**必须**带授权 scope（``AuthContext``），不得接受调用方自报的
  ``actor_id`` / ``tenant_id``（ADR-0004 第 4 条）。
- 实现分为内存（测试/骨架）与 PostgreSQL（生产）；
  **契约测试必须同时覆盖两者**。
- 关键约束（见 module-reuse-matrix.md §3 C6）：
  ``save_draft`` 必须**按状态过滤**，确保**已取消的草案不会被 worker 稍后发布**。
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.domain.catalog.models import KnowledgeNode, KnowledgeRelation, LearningUnit
from app.domain.planning.models import PlanDraft, PlanRevision
from app.domain.practice.models import PracticeProject, PracticeTask
from app.domain.reflections.models import SummaryAttempt, SummaryReview
from app.domain.resources.models import ResourcePreference, ResourceRecord
from app.domain.workspace.models import AuthContext, LearningProject


@runtime_checkable
class RepositoryPort(Protocol):
    """聚合仓储端口。

    V1 保持单一端口以减少抽象层数；B2 可按域拆分。
    每个方法都接收 ``scope``，实现须在 SQL 层（RLS）与应用层双重校验。
    """

    # ---- workspace ----
    def save_project(self, *, scope: AuthContext, project: LearningProject) -> None: ...

    def get_project(self, *, scope: AuthContext, project_id: str) -> LearningProject | None: ...

    # ---- catalog ----
    def save_node(self, *, scope: AuthContext, node: KnowledgeNode) -> None: ...

    def save_relation(self, *, scope: AuthContext, relation: KnowledgeRelation) -> None: ...

    def save_unit(self, *, scope: AuthContext, unit: LearningUnit) -> None: ...

    # ---- planning ----
    def get_draft(self, *, scope: AuthContext, draft_id: str) -> PlanDraft | None: ...

    def save_draft(self, *, scope: AuthContext, draft: PlanDraft) -> None: ...

    def get_current_plan(self, *, scope: AuthContext, project_id: str) -> PlanRevision | None: ...

    def find_publish_by_idempotency_key(
        self, *, scope: AuthContext, project_id: str, idempotency_key: str
    ) -> PlanRevision | None: ...

    # ---- reflections ----
    def save_summary_attempt(
        self, *, scope: AuthContext, attempt: SummaryAttempt
    ) -> None: ...

    def save_summary_review(self, *, scope: AuthContext, review: SummaryReview) -> None: ...

    # ---- resources ----
    def save_preference(
        self, *, scope: AuthContext, preference: ResourcePreference
    ) -> None: ...

    def save_resource(self, *, scope: AuthContext, resource: ResourceRecord) -> None: ...

    # ---- practice ----
    def save_practice_project(
        self, *, scope: AuthContext, project: PracticeProject
    ) -> None: ...

    def save_practice_task(self, *, scope: AuthContext, task: PracticeTask) -> None: ...


__all__ = ["RepositoryPort"]
