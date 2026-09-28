"""计划用例服务（B2-V §六）：把「生成 → 查看 → 编辑 → 重新校验 → 确认 → 发布」
编排成一条**真实可跑**的业务链。

## 职责边界

本模块是**应用层**：它只做编排，不放业务规则。

- 领域规则（发布原子性、草案哈希、结构指纹、状态机）在
  :mod:`app.domain.planning.models` —— **只有一份**；
- 持久化语义（单事务、状态条件、行数检查、RLS）在 ``PlanRepositoryPort``
  的实现里；
- 图的推进由 :func:`app.agent_workflows.graphs.run_planning_graph` 完成。

## 为什么决策路径不重新驱动 Graph

``await_approval`` 之后**没有任何模型调用**：它只是一次状态机迁移。
设计文档明确「普通 CRUD 与状态机用应用服务，不包 Graph」。因此决策路径
直接读**数据库里的草案**并调用 :class:`PlanPublicationService`：

- **进程重启可恢复**：决策所需的一切（草案内容、哈希、状态、当前版本）
  都在数据库里，不依赖任何内存状态或 checkpoint；
- **发布语义只有一份**：不再出现「图内一套、服务里一套」的分叉。

## 生成路径

生成是**多步 + 有界修复**，属于设计文档允许用 Graph 的场景，因此
``generate`` 通过 :func:`run_planning_graph` 推进到 ``await_approval``，
并把图产物投影为持久化的 ``PlanDraft``（草案正文存业务表，图只存引用）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from app.agent_workflows.graphs import graph_thread_id, run_planning_graph
from app.agent_workflows.nodes import PlanningNodes
from app.agent_workflows.state import PlanningState
from app.application.draft_projection import project_draft
from app.application.plan_resources import (
    StageResourceView,
    normalize_stage_resources,
    resolve_stage_resources,
)
from app.core.errors import ConflictError, NotFoundError, ValidationAppError
from app.core.ids import new_id
from app.domain.enums import (
    AiRunKind,
    AiRunNextAction,
    AiRunStatus,
    DraftDecision,
    GraphName,
    PlanDraftStatus,
)
from app.domain.planning.models import (
    PlanDraft,
    PlanPublicationService,
    PlanRepositoryPort,
    PlanRevision,
    PlanStage,
    revision_from_draft,
)
from app.domain.resources.curation import StageResourceAssignment
from app.domain.runs.models import RunRecord
from app.domain.workspace.models import AuthContext
from app.ports.llm import LLMDispatchUnknownError, LLMPort
from app.ports.public_resources import PublicResourceCatalogPort
from app.ports.runs import PlanningCatalogPort, RunRepositoryPort

__all__ = [
    "DecisionCommand",
    "DecisionOutcome",
    "DraftBundle",
    "PlanBundle",
    "PlanService",
]

#: 生成失败时对外暴露的**稳定**错误类别（不泄露图内部节点名）。
ERROR_PLANNING_FAILED = "planning_failed"


@dataclass(frozen=True, slots=True)
class DraftBundle:
    """草案 + 已核验的资源视图（供 API 映射为 ``PlanDraftView``）。"""

    draft: PlanDraft
    resources: tuple[StageResourceView, ...]


@dataclass(frozen=True, slots=True)
class PlanBundle:
    """正式版本 + 已核验的资源视图（供 API 映射为 ``PlanView``）。"""

    revision: PlanRevision
    resources: tuple[StageResourceView, ...]


@dataclass(frozen=True, slots=True)
class DecisionCommand:
    """一次用户决定的**应用层**命令（不依赖任何 Web 框架 DTO）。"""

    decision: DraftDecision
    expected_version: int
    draft_hash: str = ""
    idempotency_key: str = ""
    edited_stages: tuple[PlanStage, ...] | None = None


@dataclass(frozen=True, slots=True)
class DecisionOutcome:
    """决定的处理结果。"""

    run_id: str
    draft: PlanDraft
    resources: tuple[StageResourceView, ...]
    plan: PlanRevision | None = None
    plan_resources: tuple[StageResourceView, ...] = ()
    created: bool = False


class PlanService:
    """计划用例编排器。所有依赖都是**端口**，因此可被真实 PG 与 Fake 实现共用。"""

    def __init__(
        self,
        *,
        repository: PlanRepositoryPort,
        runs: RunRepositoryPort,
        catalog: PlanningCatalogPort,
        resources: PublicResourceCatalogPort,
        llm: LLMPort,
        graph_version: str,
        source_pack_key: str = "",
        source_pack_version: int = 0,
    ) -> None:
        self._repo = repository
        self._runs = runs
        self._catalog = catalog
        self._resources = resources
        self._llm = llm
        self._graph_version = graph_version
        self._source_pack_key = source_pack_key
        self._source_pack_version = source_pack_version
        self._publication = PlanPublicationService(repository)

    # ------------------------------------------------------------------ 生成

    def generate(
        self,
        *,
        scope: AuthContext,
        project_id: str,
        goal: str,
        prefs_snapshot: Mapping[str, Any] | None = None,
    ) -> str:
        """发起一次规划生成，返回 ``run_id``。

        先校验项目归属（``scope.require_project``），再创建运行投影，
        然后推进规划图到 ``await_approval``，最后按图的结果更新运行状态。
        """
        scope.require_project(project_id)
        cleaned_goal = goal.strip()
        if not cleaned_goal:
            raise ValidationAppError("学习目标不能为空")

        run_id = new_id("run")
        thread_id = graph_thread_id(run_id=run_id, graph_version=self._graph_version)
        self._runs.create_run(
            RunRecord(
                run_id=run_id,
                actor_id=scope.actor_id,
                project_id=project_id,
                kind=AiRunKind.PLAN_GENERATE.value,
                graph_name=GraphName.PLANNING.value,
                graph_version=self._graph_version,
                status=AiRunStatus.RUNNING,
                next_action=AiRunNextAction.WAIT,
                thread_id=thread_id,
                version=1,
            )
        )

        initial: PlanningState = {
            "run_id": run_id,
            "project_id": project_id,
            "graph_version": self._graph_version,
            "goal": cleaned_goal,
            "prefs_snapshot": dict(prefs_snapshot or {}),
        }
        try:
            nodes = self._build_nodes(project_id=project_id, run_id=run_id, goal=cleaned_goal)
            trace = run_planning_graph(nodes, initial)
        except LLMDispatchUnknownError:
            self._update_run(project_id=project_id, run_id=run_id,
                             status=AiRunStatus.RECONCILIATION_REQUIRED,
                             next_action=AiRunNextAction.RECONCILE,
                             error_class="provider_dispatch_unknown")
            raise
        except Exception:
            self._update_run(project_id=project_id, run_id=run_id,
                             status=AiRunStatus.FAILED, next_action=AiRunNextAction.RETRY,
                             error_class=ERROR_PLANNING_FAILED)
            raise

        if trace.stopped_at == "await_approval":
            draft_id = str(trace.state.get("draft_ref") or "")
            self._update_run(
                project_id=project_id,
                run_id=run_id,
                status=AiRunStatus.WAITING_USER,
                next_action=AiRunNextAction.REVIEW_DRAFT,
                result_ref=draft_id or None,
            )
        else:
            self._update_run(
                project_id=project_id,
                run_id=run_id,
                status=AiRunStatus.FAILED,
                next_action=AiRunNextAction.RETRY,
                error_class=ERROR_PLANNING_FAILED,
            )
        return run_id

    # -------------------------------------------------------------- 读取视图

    def get_run(self, *, scope: AuthContext, project_id: str, run_id: str) -> RunRecord:
        scope.require_project(project_id)
        run = self._runs.get_run(project_id=project_id, run_id=run_id)
        if run is None:
            raise NotFoundError("运行不存在")
        return run

    def get_draft(self, *, scope: AuthContext, project_id: str, draft_id: str) -> DraftBundle:
        scope.require_project(project_id)
        draft = self._repo.get_draft(project_id=project_id, draft_id=draft_id)
        if draft is None:
            raise NotFoundError("草案不存在")
        return DraftBundle(draft=draft, resources=self._resolve(draft.stage_resources, draft.stages))

    def get_current(self, *, scope: AuthContext, project_id: str) -> PlanBundle | None:
        scope.require_project(project_id)
        revision = self._repo.get_current(project_id=project_id)
        if revision is None:
            return None
        return PlanBundle(
            revision=revision,
            resources=self._resolve(revision.stage_resources, revision.stages),
        )

    # ------------------------------------------------------------------ 决定

    def decide(
        self,
        *,
        scope: AuthContext,
        project_id: str,
        draft_id: str,
        command: DecisionCommand,
    ) -> DecisionOutcome:
        """处理 approve / edit / cancel。

        **项目归属先校验**，再从数据库读草案；随后交给
        :class:`PlanPublicationService`（发布/取消）或本服务的编辑逻辑。
        所有副作用都以数据库中的最新状态为准，因此进程重启后仍可安全处理。
        """
        scope.require_project(project_id)
        draft = self._repo.get_draft(project_id=project_id, draft_id=draft_id)
        if draft is None:
            raise NotFoundError("草案不存在")

        match command.decision:
            case DraftDecision.APPROVE:
                return self._approve(draft=draft, project_id=project_id, command=command)
            case DraftDecision.EDIT:
                return self._edit(draft=draft, project_id=project_id, command=command)
            case DraftDecision.CANCEL:
                return self._cancel(draft=draft, project_id=project_id, command=command)
            case _:  # pragma: no cover - 枚举已封闭
                raise ValidationAppError(f"未知决定：{command.decision}")

    # ------------------------------------------------------------------ 内部

    def _approve(
        self, *, draft: PlanDraft, project_id: str, command: DecisionCommand
    ) -> DecisionOutcome:
        """确认发布。幂等键在**发布服务内最先**被检查，因此重放返回原结果。"""
        result = self._publication.decide_draft(
            draft=draft,
            decision=DraftDecision.APPROVE,
            expected_version=command.expected_version,
            presented_hash=command.draft_hash,
            idempotency_key=command.idempotency_key,
        )
        assert result is not None  # APPROVE 一定返回发布结果
        refreshed = self._repo.get_draft(project_id=project_id, draft_id=draft.draft_id)
        final_draft = refreshed or draft
        plan = self._repo.get_revision(project_id=project_id, revision=result.revision)
        if plan is None or plan.plan_id != result.plan_id:
            raise ConflictError("Published revision missing", reason="publication_inconsistent")
        plan_resources: tuple[StageResourceView, ...] = ()
        if plan is not None:
            plan_resources = self._resolve(plan.stage_resources, plan.stages)
        self._update_run(
            project_id=project_id,
            run_id=final_draft.run_id,
            status=AiRunStatus.SUCCEEDED,
            next_action=AiRunNextAction.NONE,
            result_ref=result.plan_id,
        )
        return DecisionOutcome(
            run_id=final_draft.run_id,
            draft=final_draft,
            resources=self._resolve(final_draft.stage_resources, final_draft.stages),
            plan=plan,
            plan_resources=plan_resources,
            created=result.created,
        )

    def _edit(
        self, *, draft: PlanDraft, project_id: str, command: DecisionCommand
    ) -> DecisionOutcome:
        """应用用户编辑 → **重新校验** → 保存新草案（不发布）。"""
        if not command.draft_hash:
            raise ValidationAppError("edit requires current draft_hash")
        if command.draft_hash != draft.content_hash:
            raise ConflictError("Draft changed", reason="draft_stale")
        if not command.edited_stages:
            raise ValidationAppError("edit 必须携带修改后的阶段列表")

        by_id = {s.stage_id: s for s in draft.stages}
        incoming_ids = {s.stage_id for s in command.edited_stages}
        unknown = sorted(incoming_ids - set(by_id))
        if unknown:
            raise ValidationAppError("编辑引用了不存在的阶段", unknown=unknown)
        missing = sorted(set(by_id) - incoming_ids)
        if missing:
            raise ValidationAppError("编辑必须覆盖草案的全部阶段", missing=missing)

        # 按用户给出的顺序重排并**归一化** order_index（0..n-1），
        # 使「拖动排序」也能通过确定性结构校验。
        ordered = sorted(command.edited_stages, key=lambda s: s.order_index)
        new_stages = tuple(
            PlanStage(
                stage_id=by_id[stage.stage_id].stage_id,
                stable_key=by_id[stage.stage_id].stable_key,
                title=stage.title,
                section_kind=stage.section_kind,
                order_index=index,
                objective=stage.objective,
            )
            for index, stage in enumerate(ordered)
        )
        draft.apply_edit(stages=new_stages)  # 置为 PENDING
        # 用**唯一**的版本构造入口重新校验（结构非法即抛，不会发布坏结构）。
        revision_from_draft(draft, revision=draft.revision_candidate)
        draft.status = PlanDraftStatus.AWAITING_APPROVAL
        self._repo.save_draft(draft, expected_hash=command.draft_hash)
        return DecisionOutcome(
            run_id=draft.run_id,
            draft=draft,
            resources=self._resolve(draft.stage_resources, draft.stages),
        )

    def _cancel(
        self, *, draft: PlanDraft, project_id: str, command: DecisionCommand
    ) -> DecisionOutcome:
        """取消草案：**状态条件**更新，已发布的草案不会被取消。"""
        self._publication.decide_draft(
            draft=draft,
            decision=DraftDecision.CANCEL,
            expected_version=command.expected_version,
        )
        refreshed = self._repo.get_draft(project_id=project_id, draft_id=draft.draft_id)
        final_draft = refreshed or draft
        self._update_run(
            project_id=project_id,
            run_id=final_draft.run_id,
            status=AiRunStatus.CANCELLED,
            next_action=AiRunNextAction.NONE,
        )
        return DecisionOutcome(
            run_id=final_draft.run_id,
            draft=final_draft,
            resources=self._resolve(final_draft.stage_resources, final_draft.stages),
        )

    def _build_nodes(self, *, project_id: str, run_id: str, goal: str) -> PlanningNodes:
        """装配图节点，并把「保存草案」接回应用层的投影 + 物化 + 仓储。"""

        def save_draft(state: PlanningState) -> dict[str, str]:
            return self._persist_draft(
                project_id=project_id, run_id=run_id, goal=goal, state=state
            )

        return PlanningNodes(
            llm=self._llm,
            save_draft=save_draft,
            # 生成路径在 await_approval 处停下，以下回调不会被执行；
            # 决策路径由本服务的 decide() 负责，**不**重复实现第二套规则。
            commit_plan=lambda state: "",
            apply_edit=lambda state: {},
            cancel_draft=lambda state: None,
        )

    def _persist_draft(
        self, *, project_id: str, run_id: str, goal: str, state: PlanningState
    ) -> dict[str, str]:
        """把图产物投影为 ``PlanDraft`` 并持久化（B2-V §三 §五）。"""
        catalog_ids = self._catalog.materialize(
            project_id=project_id,
            nodes=list(state.get("nodes") or []),
            units=list(state.get("units") or []),
            relations=list(state.get("relations") or []),
            practice=dict(state.get("practice_proposal") or {}),
        )
        current = self._repo.get_current(project_id=project_id)
        revision_candidate = (current.revision if current else 0) + 1
        draft = project_draft(
            project_id=project_id,
            run_id=run_id,
            goal_snapshot=goal,
            revision_candidate=revision_candidate,
            state=state,
            catalog=catalog_ids,
            source_pack_key=self._source_pack_key,
            source_pack_version=self._source_pack_version,
        )
        # §五：落库前把无法核验的公共资源引用降级为搜索建议，
        # 使正式版本的 source_ref 外键不会指向不存在的来源。
        draft.stage_resources = normalize_stage_resources(
            draft.stage_resources,
            catalog=self._resources,
            stage_titles={s.stage_id: s.title for s in draft.stages},
        )
        self._repo.save_draft(draft)
        return {"draft_ref": draft.draft_id, "draft_hash": draft.content_hash}

    def _resolve(
        self, assignments: Sequence[StageResourceAssignment], stages: Sequence[PlanStage]
    ) -> tuple[StageResourceView, ...]:
        if not assignments:
            return ()
        return resolve_stage_resources(
            assignments,
            catalog=self._resources,
            stage_titles={s.stage_id: s.title for s in stages},
        )

    def _update_run(
        self,
        *,
        project_id: str,
        run_id: str,
        status: AiRunStatus,
        next_action: AiRunNextAction,
        result_ref: str | None = None,
        error_class: str | None = None,
    ) -> None:
        """更新运行投影；**已是终态则跳过**，使重复确认不会反复改写运行版本。"""
        if not run_id:
            return
        current = self._runs.get_run(project_id=project_id, run_id=run_id)
        if current is None:
            return
        if current.is_terminal:
            return
        self._runs.update_run(
            project_id=project_id,
            run_id=run_id,
            expected_version=current.version,
            status=status.value,
            next_action=next_action.value,
            result_ref=result_ref,
            error_class=error_class,
        )
