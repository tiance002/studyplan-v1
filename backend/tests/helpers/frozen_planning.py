"""Explicit frozen test inputs for retained lifecycle/security regression tests.

This harness is installed only on disposable test service instances. It never
selects content from user goal text and does not restore public generation.
"""
from copy import deepcopy
from types import MethodType
from typing import Any, Mapping

from app.agent_workflows.graphs import graph_thread_id
from app.agent_workflows.planning_batches import PROTOCOL_VERSION, freeze_manifest, run_batched_planning_graph
from app.agent_workflows.state import PlanningState
from app.application.plan_service import ERROR_PLANNING_FAILED
from app.core.errors import ConflictError, DependencyUnavailableError, ValidationAppError
from app.core.ids import new_id
from app.domain.enums import AiRunKind, AiRunNextAction, AiRunStatus, GraphName
from app.domain.generated_plan_changes import GeneratedPlanChangeCommand
from app.domain.planning.intent import GoalSpec, goal_spec_payload
from app.domain.runs.models import RunRecord
from app.domain.workspace.models import AuthContext
from app.ports.llm import LLMDispatchUnknownError


def install_frozen_generation(service, pack):
    """Bind one explicitly chosen reviewed pack to this test service instance."""
    service._test_frozen_pack = deepcopy(pack)
    service._freeze_submission = MethodType(_freeze_submission, service)
    service.generate = MethodType(generate, service)
    service.submit_generation = MethodType(submit_generation, service)
    return service


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
    if prepared_change is not None:
        raise DependencyUnavailableError("Generated route preparation is unavailable")
    run_id = new_id("run")
    thread_id = graph_thread_id(run_id=run_id, graph_version=self._graph_version)
    pack = deepcopy(self._test_frozen_pack)
    binding = self._binding_resolver(scope, project_id)
    manifest = freeze_manifest(
        pack=pack, policy=binding.budget_policy, model_ref=binding.model_ref, goal_spec=goal_spec,
        outline_input_format="stage_skeleton_v1",
        structure_input_format='reviewed_structure_v1',
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
        "expected_version": current.version if current else 0,
    }
    if pack:
        initial["domain_pack"] = pack
    if self._planning_jobs is None:
        self._generation_inputs[run_id] = deepcopy(initial)
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
    if route_command is not None:
        raise DependencyUnavailableError("Generated route preparation is unavailable")
    cleaned_goal = goal.strip()
    if not cleaned_goal:
        raise ValidationAppError("学习目标不能为空")

    run_id, thread_id, initial, manifest = self._freeze_submission(
        scope=scope, project_id=project_id, goal=cleaned_goal, prefs_snapshot=prefs_snapshot, goal_spec=goal_spec,
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
    self._planning_jobs.enqueue(run, dict(initial), manifest)
    return run_id

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
            self._runtime_factory(scope, project_id, run_id, _manifest.get("model_ref", ""), manifest=_manifest)
            if self._runtime_factory
            else None
        )
        executor = runtime.executor if runtime else self._executor
        nodes = self._build_nodes(project_id=project_id, run_id=run_id, goal=cleaned_goal,
                                  llm=runtime.llm if runtime else None, selected_pack=selected_pack,
                                  frozen_input=initial)
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
