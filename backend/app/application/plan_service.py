"""计划用例服务（B2-V §六）：把「生成 → 查看 → 编辑 → 重新校验 → 确认 → 发布」
编排成一条**真实可跑**的业务链。

## 职责边界

本模块是**应用层**：它只做编排，不放业务规则。

- 领域规则（发布原子性、草案哈希、结构指纹、状态机）在
  :mod:`app.domain.planning.models` —— **只有一份**；
- 持久化语义（单事务、状态条件、行数检查、RLS）在 ``PlanRepositoryPort``
  的实现里；
- 新生成由 ``b3f2-short-v2`` 图推进到草案持久化后结束；批次内容、
  有界修复与模型 attempt 预算复用 ``b3f2-batch-v1``。

## 为什么决策路径不重新驱动 Graph

``await_approval`` 之后**没有任何模型调用**：它只是一次状态机迁移。
设计文档明确「普通 CRUD 与状态机用应用服务，不包 Graph」。因此决策路径
直接读**数据库里的草案**并调用 :class:`PlanPublicationService`：

- **进程重启可恢复**：决策所需的一切（草案内容、哈希、状态、当前版本）
  都在数据库里，不依赖任何内存状态或 checkpoint；
- **发布语义只有一份**：不再出现「图内一套、服务里一套」的分叉。

## 生成路径

生成是**多步 + 有界修复**，属于设计文档允许用 Graph 的场景，因此
``generate`` 保存持久化 ``PlanDraft`` 后完成，Run 的 result_ref 指向草案，
状态为 succeeded + none。批准、编辑、取消独立走业务事务。

## 历史协议保全

新 Run 一律使用 ``b3f2-short-v2``；旧 ``b3f2-batch-v1`` waiting_user 草案
仍可走业务确认，但不续跑或改写旧 checkpoint。未知协议版本一律明确拒绝。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Sequence, cast
from uuid import NAMESPACE_URL, uuid5

from app.agent_workflows.graphs import graph_thread_id
from app.agent_workflows.nodes import PlanningNodes
from app.agent_workflows.planning_batches import (
    DEFAULT_BUDGET,
    PROTOCOL_VERSION,
    SHORT_GENERATION_VERSION,
    derive_progress,
    freeze_manifest,
    run_batched_planning_graph,
)
from app.agent_workflows.state import PlanningState
from app.application.draft_projection import project_draft
from app.application.model_binding import SubmissionBinding
from app.application.plan_resources import (
    StageResourceView,
    normalize_stage_resources,
    resolve_stage_resources,
    restrict_pack_resources,
)
from app.core.errors import ConflictError, NotFoundError, ValidationAppError, VersionConflictError
from app.core.ids import content_hash, new_id
from app.domain.enums import (
    AiRunKind,
    AiRunNextAction,
    AiRunStatus,
    DraftDecision,
    GraphName,
    PlanDraftStatus,
    StageResourceRole,
)
from app.domain.generated_plan_changes import GeneratedPlanChangeCommand
from app.domain.planning.intent import GoalSpec, goal_spec_from_payload, goal_spec_payload
from app.domain.planning.models import (
    PlanDraft,
    PlanPublicationService,
    PlanRepositoryPort,
    PlanRevision,
    PlanStage,
    revision_from_draft,
)
from app.domain.planning.semantic_content import adapt_semantic_pack
from app.domain.resources.curation import ResolvedSection, StageResourceAssignment
from app.domain.runs.fencing import PlanningWriteFence
from app.domain.runs.models import RunRecord
from app.domain.workspace.models import AuthContext
from app.ports.generated_plan_changes import GeneratedPlanChangesPort
from app.ports.graph_runner import PlanningExecutorPort, PlanningRuntime
from app.ports.llm import LLMDispatchUnknownError, LLMPort
from app.ports.planning_jobs import JobClaim, PlanningJobsPort, PlanningLeaseLostError
from app.ports.public_resources import PublicResourceCatalogPort
from app.ports.runs import PlanningCatalogPort, RunRepositoryPort

logger = logging.getLogger(__name__)

__all__ = [
    "DecisionCommand",
    "DecisionOutcome",
    "DraftBundle",
    "PlanBundle",
    "PlanService",
    "RunBundle",
]

#: 生成失败时对外暴露的**稳定**错误类别（不泄露图内部节点名）。
ERROR_PLANNING_FAILED = "planning_failed"


def _unbound_submission(scope: AuthContext, project_id: str) -> SubmissionBinding:
    """Fallback binding for a service without a model runtime (Fake/in-process).

    It freezes the deployment default budget and a non-secret descriptor. Real
    deployments always wire :meth:`PersonalPlanningRuntimeFactory.bind_submission`.
    """
    return SubmissionBinding(model_ref="unbound:deployment", budget_policy=DEFAULT_BUDGET)


@dataclass(frozen=True, slots=True)
class RunBundle:
    """运行投影 + 业务进度（供 API 映射为 ``RunView``）。"""

    run: RunRecord
    progress: dict[str, object] | None = None


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
        planning_executor: PlanningExecutorPort | None = None,
        runtime_factory: Callable[...,PlanningRuntime] | None = None,
        domain_pack_selector: Callable[[str], dict[str, Any]] | None = None,
        planning_jobs: PlanningJobsPort | None = None,
        worker_actor_ids: tuple[str, ...] = (),
        binding_resolver: Callable[[AuthContext, str], SubmissionBinding] | None = None,
        planning_worker_admission_mode: str = "allowlist",
        preference_resolver: Callable[[AuthContext, str], Any] | None = None,
        route_changes: GeneratedPlanChangesPort | None = None,
    ) -> None:
        self._repo = repository
        self._runs = runs
        self._catalog = catalog
        self._resources = resources
        self._llm = llm
        self._executor = planning_executor
        self._runtime_factory = runtime_factory
        #: 旧部署配置可启动，但所有新 Run 固定新生命周期协议。
        if graph_version and graph_version not in {PROTOCOL_VERSION, SHORT_GENERATION_VERSION}:
            raise ValidationAppError(
                f"GRAPH_VERSION={graph_version!r} 不是受支持的生成协议；"
                f"新生成协议为 {SHORT_GENERATION_VERSION!r}，请更新部署配置"
            )
        self._graph_version = SHORT_GENERATION_VERSION
        self._source_pack_key = source_pack_key
        self._source_pack_version = source_pack_version
        self._publication = PlanPublicationService(repository)
        self._domain_pack_selector = domain_pack_selector
        self._planning_jobs = planning_jobs
        self._worker_actor_ids = tuple(dict.fromkeys(worker_actor_ids))
        if planning_worker_admission_mode not in {"allowlist", "trusted_server"}:
            raise ValidationAppError("规划 Worker admission mode 无效")
        self._planning_worker_admission_mode = planning_worker_admission_mode
        self._binding_resolver = binding_resolver or _unbound_submission
        self._preference_resolver = preference_resolver
        self._route_changes = route_changes

    # ------------------------------------------------------------------ 生成

    def _freeze_submission(
        self,
        *,
        scope: AuthContext,
        project_id: str,
        goal: str,
        prefs_snapshot: Mapping[str, Any] | None = None,
        goal_spec: GoalSpec | None = None,
        prepared_change: dict[str, Any] | None = None,
    ) -> tuple[str, str, PlanningState, dict[str, Any]]:
        """Freeze protocol, model configuration and batch catalog for a new run.

        Everything the run will later depend on is captured here, before the run
        row exists, so a later settings change cannot alter what was submitted.
        """
        run_id = prepared_change['run_id'] if prepared_change else new_id("run")
        thread_id = graph_thread_id(run_id=run_id, graph_version=self._graph_version)
        selected = (prepared_change['pack'] if prepared_change else
                    self._domain_pack_selector(goal_spec.target if goal_spec else goal) if self._domain_pack_selector else None)
        pack: dict[str, Any] = dict(selected) if isinstance(selected, Mapping) else {}
        if not prepared_change:
            pack = adapt_semantic_pack(pack, goal, goal_spec)
        binding = self._binding_resolver(scope, project_id)
        manifest = freeze_manifest(
            pack=pack, policy=binding.budget_policy, model_ref=binding.model_ref, goal_spec=goal_spec,
            route_change_hash=content_hash(prepared_change['metadata']) if prepared_change else '',
        )
        current = self._repo.get_current(project_id=project_id)
        if prefs_snapshot is None and self._preference_resolver is not None:
            preference = self._preference_resolver(scope, project_id)
            prefs_snapshot = {"mode": preference.mode.value, "language": preference.language,
                              "official_priority": preference.official_priority, "pace": preference.pace}
        initial: PlanningState = {
            "run_id": run_id,
            "project_id": project_id,
            "graph_version": self._graph_version,
            "goal": goal,
            **({"goal_spec": goal_spec_payload(goal_spec)} if goal_spec else {}),
            "prefs_snapshot": dict(prefs_snapshot or {}),
            "manifest": manifest,
            "protocol": PROTOCOL_VERSION,
            "expected_version": prepared_change['metadata']['base_version'] if prepared_change else current.version if current else 0,
        }
        if prepared_change:
            initial['route_change'] = prepared_change['metadata']
        if pack:
            initial["domain_pack"] = pack
        return run_id, thread_id, initial, manifest

    def submit_generation(
        self,
        *,
        scope: AuthContext,
        project_id: str,
        goal: str,
        prefs_snapshot: Mapping[str, Any] | None = None,
        goal_spec: GoalSpec | None = None,
        route_command: GeneratedPlanChangeCommand | None = None,
    ) -> str:
        """Validate and durably enqueue one planning run; never invoke the model."""
        scope.require_project(project_id)
        if self._planning_jobs is None:
            raise ValidationAppError("规划后台 Worker 未装配")
        if self._planning_worker_admission_mode != "trusted_server" and scope.actor_id not in self._worker_actor_ids:
            from app.core.errors import ForbiddenError

            raise ForbiddenError(
                "当前账户尚未纳入本地规划 Worker 服务范围；开放注册云端 V1 需先完成免人工登记的 RLS 安全领取"
            )
        prepared = None
        if route_command is not None:
            if route_command.project_id != project_id or self._route_changes is None:
                raise ValidationAppError('路线变更服务未装配或项目不一致')
            existing = self._route_changes.existing_submission(scope, route_command)
            if existing:
                return existing
            prepared = self._route_changes.prepare(scope, route_command, self._domain_pack_selector)
            goal, goal_spec = prepared['goal'], goal_spec_from_payload(prepared['goal_spec'])
        cleaned_goal = goal.strip()
        if not cleaned_goal:
            raise ValidationAppError("学习目标不能为空")

        run_id, thread_id, initial, manifest = self._freeze_submission(
            scope=scope, project_id=project_id, goal=cleaned_goal, prefs_snapshot=prefs_snapshot, goal_spec=goal_spec,
            prepared_change=prepared,
        )
        run = RunRecord(
            run_id=run_id,
            actor_id=scope.actor_id,
            project_id=project_id,
            kind=AiRunKind.PLAN_GENERATE.value,
            graph_name=GraphName.PLANNING.value,
            graph_version=self._graph_version,
            status=AiRunStatus.QUEUED,
            next_action=AiRunNextAction.WAIT,
            thread_id=thread_id,
            version=1,
        )
        try:
            self._planning_jobs.enqueue(run, dict(initial), manifest)
        except ConflictError:
            # A simultaneous identical submission returns the durable original,
            # without rebinding settings or repeating provider dispatch.
            if route_command and self._route_changes:
                existing = self._route_changes.existing_submission(scope, route_command)
                if existing:
                    return existing
            raise
        return run_id

    def _progress_sink(self, claim: JobClaim | None) -> Callable[[PlanningState], None] | None:
        """Business-progress publisher for one fenced claim.

        Progress is diagnostic and recomputable from the checkpoint, so a write
        failure must not abort generation; it is logged and retried on the next
        stable point. A lost lease simply stops reporting (``publish_progress``
        returns ``False``) without touching the run.
        """
        jobs = self._planning_jobs
        if claim is None or jobs is None:
            return None

        def publish(state: PlanningState) -> None:
            try:
                jobs.publish_progress(claim, derive_progress(state))
            except Exception:  # progress is best-effort; generation must continue
                logger.warning("planning progress publish failed for run %s", claim.run_id, exc_info=True)

        return publish

    def execute_generation(
        self,
        project_id: str,
        run_id: str,
        *,
        guard: Callable[[], None] = lambda: None,
        claim: JobClaim | None = None,
    ) -> None:
        """Execute one persisted submission. Only the fenced Worker calls this."""
        if self._planning_jobs is None:
            raise ValidationAppError("规划后台 Worker 未装配")
        guard()
        submission = (self._planning_jobs.read_claim_submission(claim) if claim is not None
                      else self._planning_jobs.read_submission(project_id, run_id))
        initial = submission.get("initial")
        if not isinstance(initial, dict):
            raise ConflictError("规划提交内容格式错误", reason="planning_submission_invalid")
        run = self._runs.get_run(project_id=project_id, run_id=run_id)
        if run is None or run.status not in {AiRunStatus.QUEUED, AiRunStatus.RUNNING}:
            return
        scope = AuthContext(
            actor_id=run.actor_id,
            session_id="planning-worker",
            issued_at=datetime.now(timezone.utc),
            learning_project_scope=(project_id,),
        )
        goal = str(initial.get("goal") or "")
        selected_pack = initial.get("domain_pack")
        if not isinstance(selected_pack, Mapping):
            selected_pack = None
        manifest = initial.get("manifest")
        model_ref = str((manifest or {}).get("model_ref") or "") if isinstance(manifest, Mapping) else ""
        progress = self._progress_sink(claim)
        write_fence = (PlanningWriteFence(job_id=claim.job_id, run_id=claim.run_id,
                        project_id=claim.project_id, actor_id=claim.actor_id,
                        lease_token=claim.lease_token) if claim is not None else None)
        try:
            route_change = initial.get('route_change')
            if route_change:
                if (self._route_changes is None or not isinstance(manifest, Mapping)
                        or manifest.get('route_change_hash') != content_hash(route_change)):
                    raise ConflictError('路线变更与冻结清单不一致')
                self._route_changes.validate_generation(scope, route_change)
            runtime = (
                self._runtime_factory(scope, project_id, run_id, model_ref)
                if self._runtime_factory
                else None
            )
            executor = runtime.executor if runtime else self._executor
            nodes = self._build_nodes(
                project_id=project_id,
                run_id=run_id,
                goal=goal,
                llm=runtime.llm if runtime else None,
                selected_pack=selected_pack,
                guard=guard,
                write_fence=write_fence,
                route_change=route_change,
            )
            trace = (
                self._run_executor(executor, nodes, initial, run.thread_id, run.graph_version, guard, progress)
                if executor is not None
                else run_batched_planning_graph(
                    nodes, cast(PlanningState, initial), progress=progress
                )
            )
        except PlanningLeaseLostError:
            raise
        except LLMDispatchUnknownError:
            guard()
            self._update_run(
                project_id=project_id, run_id=run_id,
                status=AiRunStatus.RECONCILIATION_REQUIRED,
                next_action=AiRunNextAction.RECONCILE,
                error_class="provider_dispatch_unknown",
                write_fence=write_fence,
            )
            return
        except Exception:
            guard()
            self._update_run(
                project_id=project_id, run_id=run_id,
                status=AiRunStatus.FAILED, next_action=AiRunNextAction.RETRY,
                error_class=ERROR_PLANNING_FAILED,
                write_fence=write_fence,
            )
            return

        guard()
        self._complete_generation(project_id=project_id, run_id=run_id,
                                  graph_version=run.graph_version, trace=trace,
                                  write_fence=write_fence, progress=progress)

    def generate(
        self,
        *,
        scope: AuthContext,
        project_id: str,
        goal: str,
        prefs_snapshot: Mapping[str, Any] | None = None,
        goal_spec: GoalSpec | None = None,
    ) -> str:
        """发起一次规划生成，返回 ``run_id``。

        先校验项目归属（``scope.require_project``），再创建运行投影，
        然后推进短规划图并持久化草案，最后更新计算运行状态。
        """
        scope.require_project(project_id)
        cleaned_goal = goal.strip()
        if not cleaned_goal:
            raise ValidationAppError("学习目标不能为空")

        run_id, thread_id, initial, _manifest = self._freeze_submission(
            scope=scope, project_id=project_id, goal=cleaned_goal, prefs_snapshot=prefs_snapshot, goal_spec=goal_spec
        )
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

        selected_pack = initial.get("domain_pack")
        try:
            runtime = (
                self._runtime_factory(scope, project_id, run_id, _manifest.get("model_ref", ""))
                if self._runtime_factory
                else None
            )
            executor = runtime.executor if runtime else self._executor
            nodes = self._build_nodes(project_id=project_id, run_id=run_id, goal=cleaned_goal,
                                      llm=runtime.llm if runtime else None, selected_pack=selected_pack)
            trace = (
                self._run_executor(executor, nodes, initial, thread_id, self._graph_version, lambda: None)
                if executor is not None
                else run_batched_planning_graph(nodes, initial)
            )
        except LLMDispatchUnknownError:
            self._update_run(project_id=project_id, run_id=run_id,
                             status=AiRunStatus.RECONCILIATION_REQUIRED,
                             next_action=AiRunNextAction.RECONCILE,
                             error_class="provider_dispatch_unknown")
            if self._executor is not None:
                return run_id
            raise
        except Exception:
            self._update_run(project_id=project_id, run_id=run_id,
                             status=AiRunStatus.FAILED, next_action=AiRunNextAction.RETRY,
                             error_class=ERROR_PLANNING_FAILED)
            if self._executor is not None:
                return run_id
            raise

        self._complete_generation(project_id=project_id, run_id=run_id,
                                  graph_version=self._graph_version, trace=trace)
        return run_id

    def _complete_generation(self, *, project_id: str, run_id: str,
                             graph_version: str, trace: Any,
                             write_fence: PlanningWriteFence | None = None,
                             progress: Callable[[PlanningState], None] | None = None) -> None:
        """A successful computation must reference its persisted business draft."""
        short = graph_version == SHORT_GENERATION_VERSION
        expected_stop = None if short else "await_approval"
        draft_id = str(trace.state.get("draft_ref") or "")
        draft = self._repo.get_draft(project_id=project_id, draft_id=draft_id) if draft_id else None
        if (trace.stopped_at == expected_stop and draft is not None
                and draft.run_id == run_id and draft.project_id == project_id
                and draft.content_hash == trace.state.get("draft_hash")):
            try:
                self._update_run(project_id=project_id, run_id=run_id,
                    status=AiRunStatus.SUCCEEDED if short else AiRunStatus.WAITING_USER,
                    next_action=AiRunNextAction.NONE if short else AiRunNextAction.REVIEW_DRAFT,
                    result_ref=draft_id, write_fence=write_fence,
                    expected_plan_version=trace.state.get("expected_version"))
            except VersionConflictError:
                self._update_run(project_id=project_id, run_id=run_id,
                    status=AiRunStatus.FAILED, next_action=AiRunNextAction.RETRY,
                    error_class=ERROR_PLANNING_FAILED, write_fence=write_fence)
        else:
            # A repair failure can retain only repair_target, rather than the
            # graph's failure_stage. Publish its business location before the
            # Run becomes terminal (fenced progress refuses terminal Runs).
            failed_state = dict(trace.state)
            target = failed_state.get("repair_target") or {}
            if not failed_state.get("failure_stage") and isinstance(target, Mapping):
                failed_state["failure_stage"] = str(target.get("stage_key") or "")
            if progress is not None:
                progress(cast(PlanningState, failed_state))
            self._update_run(project_id=project_id, run_id=run_id,
                status=AiRunStatus.FAILED, next_action=AiRunNextAction.RETRY,
                error_class=ERROR_PLANNING_FAILED, write_fence=write_fence)

    # -------------------------------------------------------------- 读取视图

    def cancel_generation(self, *, scope: AuthContext, project_id: str, run_id: str,
                          expected_version: int, idempotency_key: str) -> RunRecord:
        scope.require_project(project_id)
        if self._planning_jobs is None:
            raise ValidationAppError("规划后台 Worker 未装配")
        return self._planning_jobs.cancel_run(actor_id=scope.actor_id, project_id=project_id,
            run_id=run_id, expected_version=expected_version, idempotency_key=idempotency_key)

    def list_runs(self, *, scope: AuthContext, project_id: str, limit: int = 10) -> tuple[RunRecord, ...]:
        scope.require_project(project_id)
        if not 1 <= limit <= 20:
            raise ValidationAppError("运行列表一次最多读取20条")
        # A read-only recovery index. It never claims, resumes or dispatches work.
        # Progress is read separately for the explicitly selected Run.
        return self._runs.list_runs(project_id=project_id, actor_id=scope.actor_id, limit=limit)

    def get_run(self, *, scope: AuthContext, project_id: str, run_id: str) -> RunBundle:
        """运行投影 + 业务进度。

        **没有**「按总时长判定中断」的逻辑：一个仍在续租的 Worker 可以让 19 批
        生成持续任意长时间。租约丢失、终态与未知派发分别由 Worker 与账本处理，
        而不是靠墙上时钟猜测。
        """
        scope.require_project(project_id)
        run = self._runs.get_run(project_id=project_id, run_id=run_id)
        if run is None or run.actor_id != scope.actor_id:
            raise NotFoundError("运行不存在")
        return RunBundle(
            run=run,
            progress=self._runs.get_progress(project_id=project_id, run_id=run_id),
        )

    def get_draft(self, *, scope: AuthContext, project_id: str, draft_id: str) -> DraftBundle:
        scope.require_project(project_id)
        draft = self._repo.get_draft(project_id=project_id, draft_id=draft_id)
        if draft is None:
            raise NotFoundError("草案不存在")
        return DraftBundle(draft=draft, resources=self._resolve(draft.stage_resources, draft.stages, draft.resource_snapshots))

    def get_current(self, *, scope: AuthContext, project_id: str) -> PlanBundle | None:
        scope.require_project(project_id)
        revision = self._repo.get_current(project_id=project_id)
        if revision is None:
            return None
        return PlanBundle(
            revision=revision,
            resources=self._resolve(revision.stage_resources, revision.stages, revision.resource_snapshots,
                                    legacy=not revision.resource_snapshots),
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
        try:
            result = self._publication.decide_draft(
                draft=draft,
                decision=DraftDecision.APPROVE,
                expected_version=command.expected_version,
                presented_hash=command.draft_hash,
                idempotency_key=command.idempotency_key,
            )
        except (ConflictError, VersionConflictError):
            # A simultaneous same-key approval can commit after the domain's
            # initial idempotency read. Re-read only that durable result; never
            # retry a publication or relax its version/hash checks.
            if self._repo.find_publish_by_idempotency_key(
                    project_id=project_id, idempotency_key=command.idempotency_key) is None:
                raise
            result = self._publication.decide_draft(
                draft=draft, decision=DraftDecision.APPROVE,
                expected_version=command.expected_version, presented_hash=command.draft_hash,
                idempotency_key=command.idempotency_key)
        assert result is not None  # APPROVE 一定返回发布结果
        refreshed = self._repo.get_draft(project_id=project_id, draft_id=draft.draft_id)
        final_draft = refreshed or draft
        plan = self._repo.get_revision(project_id=project_id, revision=result.revision)
        if plan is None or plan.plan_id != result.plan_id:
            raise ConflictError("Published revision missing", reason="publication_inconsistent")
        plan_resources: tuple[StageResourceView, ...] = ()
        if plan is not None:
            plan_resources = self._resolve(plan.stage_resources, plan.stages, plan.resource_snapshots)
        self._finalize_run(draft=final_draft, decision="approve", result_ref=result.plan_id)
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
                learning_guidance=by_id[stage.stage_id].learning_guidance,
            )
            for index, stage in enumerate(ordered)
        )
        draft.apply_edit(stages=new_stages)  # 置为 PENDING
        # 用**唯一**的版本构造入口重新校验（结构非法即抛，不会发布坏结构）。
        revision_from_draft(draft, revision=draft.revision_candidate)
        draft.status = PlanDraftStatus.AWAITING_APPROVAL
        self._repo.save_draft(draft, expected_hash=command.draft_hash,
                              expected_version=command.expected_version)
        return DecisionOutcome(
            run_id=draft.run_id,
            draft=draft,
            resources=self._resolve(draft.stage_resources, draft.stages),
        )

    def _cancel(
        self, *, draft: PlanDraft, project_id: str, command: DecisionCommand
    ) -> DecisionOutcome:
        """取消草案：**状态条件**更新，已发布的草案不会被取消。"""
        if not command.draft_hash:
            raise ValidationAppError("cancel requires current draft_hash")
        self._publication.decide_draft(
            draft=draft,
            decision=DraftDecision.CANCEL,
            expected_version=command.expected_version,
            presented_hash=command.draft_hash,
        )
        refreshed = self._repo.get_draft(project_id=project_id, draft_id=draft.draft_id)
        final_draft = refreshed or draft
        self._finalize_run(draft=final_draft, decision="cancel")
        return DecisionOutcome(
            run_id=final_draft.run_id,
            draft=final_draft,
            resources=self._resolve(final_draft.stage_resources, final_draft.stages),
        )

    @staticmethod
    def _run_executor(
        executor: PlanningExecutorPort,
        nodes: PlanningNodes,
        initial: Any,
        thread_id: str,
        graph_version: str,
        guard: Callable[[], None],
        progress: Callable[[PlanningState], None] | None = None,
    ) -> Any:
        """Run or resume one thread under the stored (official) graph version."""
        return executor.execute_or_resume(
            nodes, initial, thread_id, graph_version, guard, progress=progress
        )

    def _build_nodes(self, *, project_id: str, run_id: str, goal: str, llm: LLMPort | None = None,
                     selected_pack: Mapping[str, Any] | None = None,
                     guard: Callable[[], None] = lambda: None,
                     write_fence: PlanningWriteFence | None = None,
                     route_change: dict[str, Any] | None = None) -> PlanningNodes:
        """装配图节点，并把「保存草案」接回应用层的投影 + 物化 + 仓储。"""

        def save_draft(state: PlanningState) -> dict[str, str]:
            guard()
            return self._persist_draft(
                project_id=project_id, run_id=run_id, goal=goal, state=state, selected_pack=selected_pack,
                write_fence=write_fence,
                route_change=route_change,
            )

        return PlanningNodes(
            llm=_ScopedLLM(llm if llm is not None else self._llm, project_id, guard,
                           write_fence=write_fence),
            save_draft=save_draft,
            # 短生成在保存草案后结束，以下回调不会被执行；
            # 决策路径由本服务的 decide() 负责，**不**重复实现第二套规则。
            commit_plan=lambda state: "",
            apply_edit=lambda state: {},
            cancel_draft=lambda state: None,
        )

    def _persist_draft(
        self, *, project_id: str, run_id: str, goal: str, state: PlanningState,
        selected_pack: Mapping[str, Any] | None = None,
        write_fence: PlanningWriteFence | None = None,
        route_change: dict[str, Any] | None = None,
    ) -> dict[str, str]:
        """把图产物投影为 ``PlanDraft`` 并持久化（B2-V §三 §五）。"""
        if selected_pack is not None:
            state = restrict_pack_resources(state, selected_pack)  # type: ignore[assignment]
        base_version = state.get("expected_version")
        scope = None
        if route_change:
            if self._route_changes is None or (state.get('manifest') or {}).get('route_change_hash') != content_hash(route_change):
                raise ConflictError('路线变更与冻结清单不一致')
            scope = AuthContext(actor_id=route_change['actor_id'], session_id='planning-worker',
                                issued_at=datetime.now(timezone.utc), learning_project_scope=(project_id,))
            self._route_changes.validate_generation(scope, route_change)
        # The immutable submission has one draft identity. A crash after its
        # commit but before the graph checkpoint reuses the retained business
        # result and does not materialize another candidate or dispatch again.
        draft_id = f"drf_{uuid5(NAMESPACE_URL, f'studyplan:draft:{project_id}:{run_id}').hex}"
        existing = self._repo.get_draft(project_id=project_id, draft_id=draft_id)
        if existing is not None:
            if (existing.run_id != run_id or existing.goal_snapshot != goal
                    or (base_version is not None and existing.revision_candidate != int(base_version) + 1)):
                raise ConflictError("草案与冻结提交不一致", reason="planning_submission_invalid")
            if route_change and self._route_changes:
                existing = self._route_changes.save_generated(scope, route_change, existing, write_fence)
            else:
                self._repo.save_draft(existing, expected_hash=existing.content_hash,
                                      expected_version=base_version, write_fence=write_fence)
            return {"draft_ref": existing.draft_id, "draft_hash": existing.content_hash}
        catalog_ids = self._catalog.materialize(
            project_id=project_id,
            nodes=list(state.get("nodes") or []),
            units=list(state.get("units") or []),
            relations=list(state.get("relations") or []),
            practice=dict(state.get("practice_proposal") or {}),
            write_fence=write_fence,
            expected_plan_version=base_version,
            **({'existing_node_ids': route_change['node_reuse']} if route_change and route_change['node_reuse'] else {}),
        )
        current = self._repo.get_current(project_id=project_id)
        revision_candidate = (int(base_version) if base_version is not None
                              else (current.revision if current else 0)) + 1
        draft = project_draft(
            project_id=project_id,
            run_id=run_id,
            goal_snapshot=goal,
            revision_candidate=revision_candidate,
            state=state,
            draft_id=draft_id,
            catalog=catalog_ids,
            source_pack_key=str(selected_pack.get("pack_key", "")) if selected_pack is not None else self._source_pack_key,
            source_pack_version=int(selected_pack.get("version", 0)) if selected_pack is not None else self._source_pack_version,
        )
        # §五：落库前把无法核验的公共资源引用降级为搜索建议，
        # 使正式版本的 source_ref 外键不会指向不存在的来源。
        draft.stage_resources = normalize_stage_resources(
            draft.stage_resources,
            catalog=self._resources,
            stage_titles={s.stage_id: s.title for s in draft.stages},
        )
        if route_change and self._route_changes:
            draft = self._route_changes.save_generated(scope, route_change, draft, write_fence)
        else:
            self._repo.save_draft(draft, expected_version=base_version, write_fence=write_fence)
        return {"draft_ref": draft.draft_id, "draft_hash": draft.content_hash}

    def _resolve(
        self, assignments: Sequence[StageResourceAssignment], stages: Sequence[PlanStage], snapshots=(), *, legacy=False
    ) -> tuple[StageResourceView, ...]:
        if not assignments:
            return ()
        frozen = {item.get("assignment_id"): item.get("view") for item in snapshots if item.get("view")}
        unresolved = [a for a in assignments if a.assignment_id not in frozen]
        dynamic = resolve_stage_resources(
            unresolved,
            catalog=self._resources,
            stage_titles={s.stage_id: s.title for s in stages},
        )
        by_id = {view.assignment_id: replace(view, warnings=(*view.warnings,
            "此旧记录未保存当时来源元数据；当前目录值仅供参考")) if legacy else view for view in dynamic}
        for identifier, value in frozen.items():
            data = dict(value)
            data["role"] = StageResourceRole(data["role"])
            data["ordered_sections"] = tuple(ResolvedSection(**item) for item in data["ordered_sections"])
            for field in ("fallback_search_terms", "warnings", "node_ids"):
                data[field] = tuple(data.get(field, ()))
            by_id[identifier] = StageResourceView(**data)
        return tuple(by_id[a.assignment_id] for a in assignments)

    def _finalize_run(self, *, draft: PlanDraft, decision: str, result_ref: str = "") -> None:
        """Acknowledge legacy business decisions without altering checkpoints.

        New computation Runs are already succeeded and continue to reference the
        draft after edit/publish/cancel. Only historic waiting projections change.
        """
        run = self._runs.get_run(project_id=draft.project_id, run_id=draft.run_id)
        if run is None or run.graph_version == SHORT_GENERATION_VERSION or run.is_terminal:
            return
        status = AiRunStatus.SUCCEEDED if decision == "approve" else AiRunStatus.CANCELLED
        self._update_run(project_id=draft.project_id,run_id=draft.run_id,status=status,
                         next_action=AiRunNextAction.NONE,result_ref=result_ref or None)

    def _update_run(
        self,
        *,
        project_id: str,
        run_id: str,
        status: AiRunStatus,
        next_action: AiRunNextAction,
        result_ref: str | None = None,
        error_class: str | None = None,
        write_fence: PlanningWriteFence | None = None,
        expected_plan_version: int | None = None,
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
            write_fence=write_fence,
            expected_plan_version=expected_plan_version,
        )


class _ScopedLLM:
    """Carry server scope and its transient claim to the durable dispatch guard."""
    def __init__(self, llm: LLMPort, project_id: str, guard: Callable[[], None] = lambda: None,
                 *, write_fence: PlanningWriteFence | None = None):
        self.llm = llm
        self.project_id = project_id
        self.guard = guard
        self.write_fence = write_fence

    def generate_structured(self, *, purpose, payload, schema_name, run_id, attempt_id):
        self.guard()
        context = {key: value for key, value in payload.items() if key != "_planning_claim"}
        context["_project_id"] = self.project_id
        if self.write_fence is not None:
            context["_planning_claim"] = {
                "job_id": self.write_fence.job_id,
                "run_id": self.write_fence.run_id,
                "project_id": self.write_fence.project_id,
                "actor_id": self.write_fence.actor_id,
                "lease_token": self.write_fence.lease_token,
            }
        return self.llm.generate_structured(purpose=purpose,
            payload=context,schema_name=schema_name,
            run_id=run_id,attempt_id=attempt_id)
