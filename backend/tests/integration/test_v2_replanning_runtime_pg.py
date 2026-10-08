"""Item8 semantic runs, atomic admission and shared durable budget, owned PG only."""
import json
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import psycopg
import pytest
from app.agent_workflows.runtime import PostgresSaver
from app.application.plan_service import PlanService
from app.core.errors import ConflictError, IdempotencyConflictError, ValidationAppError, VersionConflictError
from app.domain.planning.content_coverage import ReviewedContentIndex
from app.domain.planning.curriculum_compiler import CurriculumSourceFacts
from app.domain.planning.intent import GoalSpec, goal_spec_payload
from app.domain.planning.models import PlanPublicationService
from app.domain.planning.resource_research import ResearchBudget
from app.domain.planning.v2_runtime import V2BudgetExceeded, V2RecoveryBlocked
from app.domain.runs.fencing import PlanningWriteFence
from app.infrastructure.db.job_repository import PgPlanningJobRepository
from app.infrastructure.db.plan_repository import PgPlanRepository
from app.infrastructure.db.run_repository import PgRunRepository
from app.infrastructure.db.v2_revisions import PgV2Revisions, validate_revision_basis
from app.infrastructure.providers.runtime_factory import OwnedV2PlanningRuntimeFactory
from app.infrastructure.providers.v2_attempts import PgV2Calls
from app.infrastructure.worker.planning_worker import PlanningWorker

from backend.tests.integration.test_v2_planning_runtime_pg import (
    PipelineBodies,
    PipelineProvider,
    PipelineSearch,
)
from backend.tests.integration.test_v2_replanning_pg import EVIDENCE, saved_history
from backend.tests.integration.test_v2_replanning_pg import checkpoint_db as cp_fixture
from backend.tests.integration.test_v2_replanning_pg import db as db_fixture
from backend.tests.integration.test_v2_replanning_pg import scope as scope_fixture

pytestmark = pytest.mark.postgres
db, checkpoint_db, scope = db_fixture, cp_fixture, scope_fixture


def environment(db, checkpoint_db, scope, *, budget=None, initialize=True):
    with psycopg.connect(checkpoint_db.migrator_dsn, autocommit=True) as conn:
        PostgresSaver(conn).setup()
        conn.execute("GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO studyplan_app")
    provider, search, bodies = PipelineProvider(), PipelineSearch(), PipelineBodies()
    factory = OwnedV2PlanningRuntimeFactory(db.app_dsn, checkpoint_db.app_dsn,
        source_facts=CurriculumSourceFacts(ReviewedContentIndex("empty", (), (), ())),
        budget=budget or ResearchBudget(max_output_tokens=131072, max_total_requests=50, max_cost_micros=1000000),
        binding_resolver=lambda scope, project: SimpleNamespace(model_ref="test:frozen"),
        provider_resolver=lambda scope, project, run, ref: provider, github=search, body_reader=bodies)
    jobs = PgPlanningJobRepository(db.app_dsn, actor_ids=(scope.actor_id,))
    repo, runs = PgPlanRepository(db.app_dsn), PgRunRepository(db.app_dsn)
    service = PlanService(repository=repo, runs=runs, catalog=None, resources=None, llm=None,
        graph_version="", planning_jobs=jobs, v2_runtime_factory=factory)
    worker = PlanningWorker(jobs=jobs, execute=service.execute_generation, actor_ids=(scope.actor_id,))
    revisions = PgV2Revisions(db.app_dsn, planning_jobs=jobs, runtime_factory=factory)
    project = scope.learning_project_scope[0]
    root = base = None
    if initialize:
        root = service.submit_owned_v2(scope=scope, project_id=project, goal_spec=GoalSpec("学习MCP"))
        assert worker.tick()
        run = runs.get_run(project_id=project, run_id=root)
        assert run.status.value == "succeeded", run
        draft = repo.get_draft(project_id=project, draft_id=run.result_ref)
        PlanPublicationService(repo).publish(draft=draft, presented_hash=draft.content_hash,
            expected_version=0, idempotency_key="root-confirm")
        base = repo.get_current(project_id=project)
    return SimpleNamespace(provider=provider, factory=factory, jobs=jobs, runs=runs, repo=repo, service=service,
        worker=worker, revisions=revisions, project=project, scope=scope, root=root, base=base)


def submit(env, key="semantic", goal=None):
    return env.revisions.submit_semantic(scope=env.scope, project_id=env.project,
        expected_version=1, current_plan_id=env.base.plan_id, idempotency_key=key,
        goal_spec=goal or GoalSpec("用MCP检查工具调用"))


def ledger(db, env, run, provider=None):
    claim = env.jobs.claim(env.project, "item8-owned", 900)
    assert claim and claim.run_id == run
    with psycopg.connect(db.migrator_dsn) as conn:
        submission = conn.execute("SELECT detail FROM ai_run_events WHERE run_id=%s AND status='submission'", (run,)).fetchone()[0]
    fence = PlanningWriteFence(claim.job_id, run, env.project, env.scope.actor_id, claim.lease_token)
    return PgV2Calls(db.app_dsn, scope=env.scope, project_id=env.project, run_id=run,
        manifest=submission["manifest"], fence=fence, provider=provider or env.provider)


def debit(calls, key, invoke=lambda _: None):
    return calls.call(step=key, purpose="owned-budget-probe", schema="OwnedBudgetProbeV1", payload={"key": key},
        reserved={"total_requests": 1}, invoke=invoke, encode=lambda value: ({"kind": "probe", "value": {}}, {}))


def test_semantic_runs_item1_to_compiler_and_only_confirm_switches_current(db, checkpoint_db, scope):
    env = environment(db, checkpoint_db, scope)
    saved_history(db, scope, env.base)
    goal = GoalSpec("用MCP检查工具调用", scope=("MCP工具协议",), starting_point="已会Python",
        project_context="已有JSON CLI，保留现有输入输出")
    run = submit(env, goal=goal)
    assert submit(env, goal=goal) == run and run != env.root
    with pytest.raises(IdempotencyConflictError):
        submit(env, goal=GoalSpec("不同目标"))
    assert env.repo.get_current(project_id=env.project) == env.base
    assert env.worker.tick()
    result = env.runs.get_run(project_id=env.project, run_id=run)
    assert result.status.value == "succeeded", result
    draft = env.revisions.get_preview(scope=scope, project_id=env.project, draft_id=result.result_ref).draft
    ctx = draft.v2_revision.to_payload()
    from app.domain.planning.v2_runtime import wire
    assert ctx["approved_goal_spec"] == wire(goal_spec_payload(goal))
    assert draft.goal_spec == goal
    preview = draft.v2_revision.user_content(execution=draft.v2_execution)
    assert preview["changes"]["before"]["practice"] and preview["changes"]["after"]["practice"]
    assert preview["history"][0]["learning_status"] == "completed"
    assert all(h["target_stable_key"] is None and h["progress_inherited"] is False for h in preview["history"])
    assert env.repo.get_current(project_id=env.project) == env.base
    published = env.revisions.confirm(scope=scope, project_id=env.project, draft_id=draft.draft_id,
        expected_version=1, draft_hash=draft.content_hash, idempotency_key="semantic-confirm").plan
    assert published.revision == 2 and published.goal_spec == goal
    assert all(s["learning_status"] == "future" for s in env.revisions.context(scope=scope, project_id=env.project)["stages"])
    assert env.repo.get_revision(project_id=env.project, revision=1).stages == env.base.stages
    from dataclasses import replace

    from app.domain.planning.revisions import LocalStageEdit
    for forged in (replace(draft, v2_revision=None), replace(draft, goal_spec=None),
            replace(draft, goal_spec=replace(goal, target="different raw target")),
            replace(draft, goal_spec=replace(goal, scope=("different scope",)))):
        with pytest.raises(ValidationAppError):
            draft.v2_execution.validate_structure(forged)
    local = env.revisions.preview_local(scope=scope, project_id=env.project, current_plan_id=published.plan_id,
        expected_version=2, idempotency_key="semantic-then-local", stage_edits=(LocalStageEdit(
            published.stages[-1].stage_id, what_to_learn="在原目标内检查正常和失败结果"),)).draft
    assert local.goal_spec == goal
    forged_local = replace(local, goal_spec=replace(goal, target="local cannot replace target"))
    with env.revisions._connection(scope, env.project) as conn:
        with pytest.raises(ConflictError):
            validate_revision_basis(conn, forged_local, expected_version=2)
        from app.domain.planning.revisions import V2RevisionContext
        raw = local.v2_revision.to_payload()
        raw.pop("version")
        raw.pop("context_hash")
        raw["budget_root_run_id"] = run
        with pytest.raises(ConflictError):
            validate_revision_basis(conn, replace(local, v2_revision=V2RevisionContext.create(**raw)), expected_version=2)
    local_plan = env.revisions.confirm(scope=scope, project_id=env.project, draft_id=local.draft_id,
        expected_version=2, draft_hash=local.content_hash, idempotency_key="semantic-local-confirm").plan
    assert local_plan.goal_spec == goal
    third = env.revisions.submit_semantic(scope=scope, project_id=env.project, expected_version=3,
        current_plan_id=local_plan.plan_id, idempotency_key="third-semantic", goal_spec=GoalSpec("第三次MCP目标"))
    third_calls = ledger(db, env, third)
    assert third_calls.usage()["total_requests"] > 6
    with third_calls.tx() as conn:
        from app.infrastructure.db.v2_revisions import budget_family
        root, family = budget_family(conn, actor_id=scope.actor_id, project_id=env.project, run_id=third)
    assert root == env.root and set(family) == {env.root, run, third}
    EVIDENCE.joinpath("semantic-chain.json").write_text(json.dumps({"root_run": env.root, "new_run": run,
        "context": ctx, "preview": preview, "current_revision": 3, "ancestor_budget_root": root,
        "family_run_ids": list(family), "external_calls": 0}, ensure_ascii=False, indent=2), encoding="utf8")


def test_sibling_budget_cap_is_shared(db, checkpoint_db, scope):
    env = environment(db, checkpoint_db, scope)
    one, two = submit(env, "sibling-one"), submit(env, "sibling-two")
    first, second = ledger(db, env, one), ledger(db, env, two)
    before = first.usage()["total_requests"]
    assert before > 0
    # Two siblings race for the last request under the original root cap.
    for n in range(first.manifest["budget"]["max_total_requests"] - before - 1):
        debit(first, "fill-" + str(n))
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(debit, calls, "race") for calls in (first, second)]
        outcomes = []
        for future in futures:
            try:
                future.result(timeout=20)
                outcomes.append("PASS")
            except (V2BudgetExceeded, V2RecoveryBlocked):
                outcomes.append("BLOCKED")
    assert sorted(outcomes) == ["BLOCKED", "PASS"]
    third = submit(env, "sibling-third")
    with pytest.raises(V2BudgetExceeded):
        debit(ledger(db, env, third), "new-run-no-refund")


def test_unknown_sibling_blocks_new_run_and_existing_sibling_without_dispatch(db, checkpoint_db, scope):
    env = environment(db, checkpoint_db, scope)
    one, two = submit(env, "unknown-one"), submit(env, "unknown-two")
    first, second = ledger(db, env, one), ledger(db, env, two)
    dispatched = []
    def timeout(_):
        dispatched.append("unknown")
        raise TimeoutError("synthetic dispatch unknown")
    result = debit(first, "unknown", timeout)
    assert result["kind"] == "failure" and result["value"]["dispatch_unknown"]
    assert debit(first, "unknown", timeout)["value"]["dispatch_unknown"]
    with pytest.raises(V2RecoveryBlocked):
        debit(first, "unknown-other", timeout)
    with pytest.raises(V2RecoveryBlocked):
        submit(env, "unknown-cannot-restart")
    with pytest.raises(V2RecoveryBlocked):
        debit(second, "must-not-dispatch", lambda _: dispatched.append("unsafe"))
    assert dispatched == ["unknown"]
    assert first.usage()["total_requests"] == second.usage()["total_requests"]
    assert env.repo.get_current(project_id=env.project) == env.base


def test_changed_factory_cap_or_cross_database_dependency_rejects_before_enqueue(db, checkpoint_db, scope):
    from dataclasses import replace

    from app.core.errors import DependencyUnavailableError
    env = environment(db, checkpoint_db, scope)
    env.factory.budget = replace(env.factory.budget, max_total_requests=51)
    with pytest.raises(ValidationAppError):
        submit(env, "cap-increase")
    env.factory.dsn = checkpoint_db.app_dsn
    with pytest.raises(DependencyUnavailableError):
        submit(env, "cross-database")
    with psycopg.connect(db.migrator_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM ai_runs WHERE project_id=%s", (env.project,)).fetchone()[0] == 1


def test_progress_change_after_submission_blocks_all_semantic_dispatch(db, checkpoint_db, scope):
    env = environment(db, checkpoint_db, scope)
    run = submit(env, "progress-stale")
    before = len(env.provider.calls)
    saved_history(db, scope, env.base, accept=False)
    assert env.worker.tick()
    result = env.runs.get_run(project_id=env.project, run_id=run)
    assert result.status.value == "failed" and result.error_class == "v2_persistence_conflict"
    assert len(env.provider.calls) == before
    assert env.repo.get_current(project_id=env.project) == env.base


@pytest.mark.parametrize("tamper", ["context", "compiler_manifest"])
def test_context_or_compiler_manifest_cannot_replace_runtime_authority(db, checkpoint_db, scope, tamper):
    from app.core.ids import content_hash
    from psycopg.types.json import Jsonb
    env = environment(db, checkpoint_db, scope)
    run = submit(env, "tamper-" + tamper)
    with psycopg.connect(db.migrator_dsn) as conn:
        event = conn.execute("SELECT event_id,detail FROM ai_run_events WHERE run_id=%s AND status='submission'", (run,)).fetchone()
        detail = event[1]
        if tamper == "context":
            detail["initial"]["v2_revision"]["approved_goal_spec"]["target"] = "different goal"
            ctx = detail["initial"]["v2_revision"]
            ctx["context_hash"] = content_hash({k: v for k, v in ctx.items() if k != "context_hash"})
        else:
            detail["manifest"] = detail["initial"]["manifest"] = env.base.v2_execution.to_payload()["manifest"]
        conn.execute("UPDATE ai_run_events SET detail=%s WHERE event_id=%s", (Jsonb(detail), event[0]))
    before = len(env.provider.calls)
    assert env.worker.tick()
    assert env.runs.get_run(project_id=env.project, run_id=run).status.value == "reconciliation_required"
    assert len(env.provider.calls) == before
    assert env.repo.get_current(project_id=env.project) == env.base


def test_enqueue_shares_existing_transaction_and_rolls_back_all_rows(db, checkpoint_db, scope, monkeypatch):
    env = environment(db, checkpoint_db, scope)
    original = PgPlanningJobRepository._insert_job
    def interrupted(conn, run_id, key):
        original(conn, run_id, key)
        raise RuntimeError("owned transaction interruption")
    monkeypatch.setattr(PgPlanningJobRepository, "_insert_job", staticmethod(interrupted))
    with pytest.raises(RuntimeError, match="interruption"):
        submit(env, "atomic")
    run = env.revisions._identity(scope, env.project, "atomic", "semantic")
    with psycopg.connect(db.migrator_dsn) as conn:
        for table in ("ai_runs", "ai_run_events", "ai_jobs"):
            assert conn.execute(f"SELECT count(*) FROM {table} WHERE run_id=%s", (run,)).fetchone()[0] == 0


def test_fresh_worker_recovers_semantic_context_and_receipts_without_new_dispatch(db, checkpoint_db, scope, monkeypatch):
    from app.infrastructure.checkpointer.v2_planning_executor import PgV2Checkpoints
    from app.ports.summaries import ReviewPersistenceInterrupted
    env = environment(db, checkpoint_db, scope)
    run = submit(env, "checkpoint-recovery")
    original = PgV2Checkpoints.save
    def interrupt(self, state):
        if self.calls.run_id == run and state["stage"] == "deterministic_compiler":
            raise ReviewPersistenceInterrupted("owned checkpoint interruption")
        return original(self, state)
    monkeypatch.setattr(PgV2Checkpoints, "save", interrupt)
    assert env.worker.tick()
    retained = env.runs.get_run(project_id=env.project, run_id=run)
    assert retained.status.value == "running" and retained.result_ref is None
    assert env.repo.get_current(project_id=env.project) == env.base
    counts = tuple(len(port.calls) for port in (env.provider, env.factory.github, env.factory.body_reader))
    with psycopg.connect(db.migrator_dsn) as conn:
        conn.execute("UPDATE ai_jobs SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE run_id=%s", (run,))
        submission = conn.execute("SELECT detail FROM ai_run_events WHERE run_id=%s AND status='submission'", (run,)).fetchone()[0]
    monkeypatch.setattr(PgV2Checkpoints, "save", original)
    jobs = PgPlanningJobRepository(db.app_dsn, actor_ids=(scope.actor_id,))
    fresh = PlanService(repository=PgPlanRepository(db.app_dsn), runs=PgRunRepository(db.app_dsn),
        catalog=None, resources=None, llm=None, graph_version="", planning_jobs=jobs,
        v2_runtime_factory=env.factory)
    worker = PlanningWorker(jobs=jobs, execute=fresh.execute_generation, actor_ids=(scope.actor_id,))
    assert worker.tick()
    recovered = env.runs.get_run(project_id=env.project, run_id=run)
    assert recovered.status.value == "succeeded", recovered
    draft = env.repo.get_draft(project_id=env.project, draft_id=recovered.result_ref)
    assert draft.v2_revision.to_payload() == submission["initial"]["v2_revision"]
    assert counts == tuple(len(port.calls) for port in (env.provider, env.factory.github, env.factory.body_reader))
    assert env.repo.get_current(project_id=env.project) == env.base


def _initial_submission(env, expected_version):
    from app.core.ids import new_id
    from app.domain.enums import AiRunNextAction, AiRunStatus
    from app.domain.planning.v2_runtime import V2_EXECUTION_VERSION
    from app.domain.runs.models import RunRecord
    goal = GoalSpec("不能重置预算的首次入口")
    manifest = env.factory.build_submission(env.scope, env.project, goal, expected_version)
    run = RunRecord(new_id("run"), env.scope.actor_id, env.project, "plan_generate", "planning",
        V2_EXECUTION_VERSION, AiRunStatus.QUEUED, AiRunNextAction.WAIT, thread_id=new_id("thread"))
    initial = {"goal": goal.target, "goal_spec": goal_spec_payload(goal), "manifest": manifest}
    return run, initial, manifest


def _project_rows(db, env):
    with psycopg.connect(db.migrator_dsn) as conn:
        return tuple(conn.execute(query, (env.project,)).fetchone()[0] for query in (
            "SELECT count(*) FROM ai_runs WHERE project_id=%s",
            "SELECT count(*) FROM ai_jobs j JOIN ai_runs r USING(run_id) WHERE r.project_id=%s",
            "SELECT count(*) FROM ai_run_events e JOIN ai_runs r USING(run_id) WHERE r.project_id=%s AND e.status='submission'"))


def _insert_legacy_submission(db, env, run, initial, manifest):
    from psycopg.types.json import Jsonb
    with psycopg.connect(db.migrator_dsn) as conn:
        conn.execute("INSERT INTO ai_runs(run_id,actor_id,project_id,kind,graph_name,graph_version,status,next_action,thread_id) "
            "VALUES(%s,%s,%s,%s,%s,%s,'queued','wait',%s)",
            (run.run_id, run.actor_id, run.project_id, run.kind, run.graph_name, run.graph_version, run.thread_id))
        conn.execute("INSERT INTO ai_run_events(run_id,status,detail) VALUES(%s,'submission',%s)",
            (run.run_id, Jsonb({"kind": "planning_submission", "actor_id": run.actor_id,
                "project_id": run.project_id, "initial": initial, "manifest": manifest})))
        env.jobs._insert_job(conn, run.run_id, "planning:" + run.run_id)


def test_existing_current_blocks_new_initial_root_for_cancelled_and_unknown_families(db, checkpoint_db, scope, monkeypatch):
    env = environment(db, checkpoint_db, scope)
    original = env.factory.build_submission
    bindings = []
    def counted(*args):
        bindings.append(1)
        return original(*args)
    monkeypatch.setattr(env.factory, "build_submission", counted)
    states = []
    for state in ("published", "cancelled_sibling", "unknown_sibling"):
        if state == "cancelled_sibling":
            run = submit(env, state)
            cancelled = env.jobs.cancel_run(actor_id=scope.actor_id, project_id=env.project,
                run_id=run, expected_version=env.runs.get_run(project_id=env.project, run_id=run).version,
                idempotency_key="cancel-sibling")
            assert cancelled.status.value == "cancelled"
        elif state == "unknown_sibling":
            run = submit(env, state)
            calls = ledger(db, env, run)
            def unknown(_):
                raise TimeoutError("new owned synthetic unknown")
            assert debit(calls, "unknown-family", unknown)["value"]["dispatch_unknown"]
        before, bound = _project_rows(db, env), len(bindings)
        ports = tuple(len(port.calls) for port in (env.provider, env.factory.github, env.factory.body_reader))
        with pytest.raises(ConflictError):
            env.service.submit_owned_v2(scope=scope, project_id=env.project, goal_spec=GoalSpec("新目标"))
        assert _project_rows(db, env) == before
        assert len(bindings) == bound
        assert tuple(len(port.calls) for port in (env.provider, env.factory.github, env.factory.body_reader)) == ports
        assert env.repo.get_current(project_id=env.project) == env.base
        states.append({"family_state": state, "rows_before_after": before, "new_bindings": 0, "new_dispatch": 0})
    EVIDENCE.joinpath("r2-closure-initial-root-gate.json").write_text(json.dumps({"database": db.name,
        "project_id": env.project, "current_plan_id": env.base.plan_id, "states": states,
        "external_calls": 0}, ensure_ascii=False, indent=2), encoding="utf8")


@pytest.mark.parametrize("expected_version", [0, 1])
def test_unbound_submission_or_stale_initial_version_rejected_before_enqueue(db, checkpoint_db, scope, expected_version):
    env = environment(db, checkpoint_db, scope)
    run, initial, manifest = _initial_submission(env, expected_version)
    before = _project_rows(db, env)
    with pytest.raises((VersionConflictError, V2RecoveryBlocked)):
        env.jobs.enqueue(run, initial, manifest)
    assert _project_rows(db, env) == before
    assert env.repo.get_current(project_id=env.project) == env.base


@pytest.mark.parametrize("expected_version", [0, 1])
def test_preexisting_unbound_run_is_blocked_before_dispatch(db, checkpoint_db, scope, expected_version):
    env = environment(db, checkpoint_db, scope)
    run, initial, manifest = _initial_submission(env, expected_version)
    # Explicitly emulate a pre-fix submission in this NEW Item8-owned database.
    _insert_legacy_submission(db, env, run, initial, manifest)
    ports = tuple(len(port.calls) for port in (env.provider, env.factory.github, env.factory.body_reader))
    dispatched = []
    calls = ledger(db, env, run.run_id)
    with pytest.raises((V2RecoveryBlocked, VersionConflictError)):
        debit(calls, "legacy-direct-must-not-dispatch", lambda _: dispatched.append(1))
    with psycopg.connect(db.migrator_dsn) as conn:
        conn.execute("UPDATE ai_jobs SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE run_id=%s", (run.run_id,))
    assert env.worker.tick()
    result = env.runs.get_run(project_id=env.project, run_id=run.run_id)
    assert result.status.value == "reconciliation_required" and result.error_class == "v2_recovery_blocked"
    assert dispatched == []
    assert tuple(len(port.calls) for port in (env.provider, env.factory.github, env.factory.body_reader)) == ports
    assert env.repo.get_current(project_id=env.project) == env.base
    with psycopg.connect(db.migrator_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM ai_provider_attempts WHERE run_id=%s", (run.run_id,)).fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM plan_drafts WHERE run_id=%s", (run.run_id,)).fetchone()[0] == 0
    EVIDENCE.joinpath("r2-closure-legacy-unbound-run-" + str(expected_version) + ".json").write_text(json.dumps({"database": db.name,
        "run_id": run.run_id, "status": result.status.value, "new_attempts": 0, "new_dispatch": 0,
        "drafts": 0, "current_unchanged": True, "external_calls": 0}, indent=2), encoding="utf8")


def test_initial_root_is_atomic_and_unknown_without_current_cannot_restart(db, checkpoint_db, scope):
    env = environment(db, checkpoint_db, scope, initialize=False)
    def start():
        try:
            return env.service.submit_owned_v2(scope=scope, project_id=env.project, goal_spec=GoalSpec("学习MCP"))
        except ConflictError:
            return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: start(), range(2)))
    assert sum(run is not None for run in results) == 1
    root = next(run for run in results if run is not None)
    assert _project_rows(db, env) == (1, 1, 1)
    queued = env.runs.get_run(project_id=env.project, run_id=root)
    with psycopg.connect(db.migrator_dsn) as conn:
        previous = conn.execute("SELECT detail FROM ai_run_events WHERE run_id=%s AND status='submission'", (root,)).fetchone()[0]
    env.jobs.enqueue(queued, previous["initial"], previous["manifest"])
    assert _project_rows(db, env) == (1, 1, 1)
    assert start() is None
    calls = ledger(db, env, root)
    dispatched = []
    def unknown(_):
        dispatched.append(1)
        raise TimeoutError("new owned initial root dispatch unknown")
    assert debit(calls, "unknown-initial", unknown)["value"]["dispatch_unknown"]
    before = _project_rows(db, env)
    assert start() is None and _project_rows(db, env) == before
    env.jobs.enqueue(queued, previous["initial"], previous["manifest"])
    assert _project_rows(db, env) == before
    assert env.repo.get_current(project_id=env.project) is None and dispatched == [1]
    EVIDENCE.joinpath("r2-closure-initial-root-atomic-unknown.json").write_text(json.dumps({"database": db.name,
        "run_id": root, "concurrent_root_count": 1, "rows": before, "dispatch_count": 1,
        "retry_dispatch_count": 0, "current": None, "external_calls": 0}, indent=2), encoding="utf8")


@pytest.mark.parametrize("terminal", ["failed", "cancelled"])
def test_terminal_initial_root_without_current_cannot_restart(db, checkpoint_db, scope, monkeypatch, terminal):
    from app.ports.llm import LLMFailure
    env = environment(db, checkpoint_db, scope, initialize=False)
    root = env.service.submit_owned_v2(scope=scope, project_id=env.project, goal_spec=GoalSpec("学习MCP"))
    if terminal == "cancelled":
        run = env.runs.get_run(project_id=env.project, run_id=root)
        env.jobs.cancel_run(actor_id=scope.actor_id, project_id=env.project, run_id=root,
            expected_version=run.version, idempotency_key="cancel-initial")
    else:
        monkeypatch.setattr(env.provider, "generate_structured", lambda **kw: LLMFailure("owned_known_failure", "synthetic known failure"))
        assert env.worker.tick()
    assert env.runs.get_run(project_id=env.project, run_id=root).status.value == terminal
    before = _project_rows(db, env)
    with pytest.raises(ConflictError):
        env.service.submit_owned_v2(scope=scope, project_id=env.project, goal_spec=GoalSpec("换目标也不能重置"))
    assert _project_rows(db, env) == before
    assert env.repo.get_current(project_id=env.project) is None


def test_legacy_two_initial_roots_cannot_dispatch_around_original_unknown(db, checkpoint_db, scope):
    env = environment(db, checkpoint_db, scope, initialize=False)
    first = env.service.submit_owned_v2(scope=scope, project_id=env.project, goal_spec=GoalSpec("学习MCP"))
    calls = ledger(db, env, first)
    def unknown(_):
        raise TimeoutError("owned pre-fix original unknown")
    assert debit(calls, "original-unknown", unknown)["value"]["dispatch_unknown"]
    second, initial, manifest = _initial_submission(env, 0)
    _insert_legacy_submission(db, env, second, initial, manifest)
    direct = ledger(db, env, second.run_id)
    with pytest.raises(V2RecoveryBlocked):
        debit(direct, "second-root-cannot-reset", lambda _: pytest.fail("second root dispatched"))
    with psycopg.connect(db.migrator_dsn) as conn:
        conn.execute("UPDATE ai_jobs SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE run_id=%s", (second.run_id,))
    assert env.worker.tick()
    assert env.runs.get_run(project_id=env.project, run_id=second.run_id).status.value == "reconciliation_required"
    assert env.repo.get_current(project_id=env.project) is None and env.provider.calls == []
    with psycopg.connect(db.migrator_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM ai_provider_attempts WHERE run_id=%s", (second.run_id,)).fetchone()[0] == 0
    EVIDENCE.joinpath("r2-closure-legacy-double-root.json").write_text(json.dumps({"database": db.name,
        "original_unknown": first, "second_root": second.run_id, "second_attempts": 0,
        "new_dispatch": 0, "current": None, "external_calls": 0}, indent=2), encoding="utf8")


@pytest.mark.parametrize("already_published", [False, True])
def test_completed_legacy_root_cannot_confirm_or_replan_around_another_root(db, checkpoint_db, scope, already_published):
    env = environment(db, checkpoint_db, scope, initialize=False)
    first = env.service.submit_owned_v2(scope=scope, project_id=env.project, goal_spec=GoalSpec("学习MCP"))
    assert env.worker.tick()
    result = env.runs.get_run(project_id=env.project, run_id=first)
    draft = env.repo.get_draft(project_id=env.project, draft_id=result.result_ref)
    if already_published:
        PlanPublicationService(env.repo).publish(draft=draft, presented_hash=draft.content_hash,
            expected_version=0, idempotency_key="legacy-before-duplicate")
        env.base = env.repo.get_current(project_id=env.project)
    second, initial, manifest = _initial_submission(env, 0)
    _insert_legacy_submission(db, env, second, initial, manifest)
    with pytest.raises(V2RecoveryBlocked):
        if already_published:
            submit(env, "legacy-double-root-replan")
        else:
            PlanPublicationService(env.repo).publish(draft=draft, presented_hash=draft.content_hash,
                expected_version=0, idempotency_key="legacy-double-root-confirm")
    assert env.repo.get_current(project_id=env.project) == env.base


@pytest.mark.parametrize("window", ["final_checkpoint", "run_finalize"])
@pytest.mark.parametrize("winner", ["own_draft", "local_draft"])
def test_publication_between_semantic_persistence_and_completion_has_exact_terminal_state(
        db, checkpoint_db, scope, monkeypatch, window, winner):
    from app.domain.enums import AiRunStatus
    from app.domain.planning.revisions import LocalStageEdit
    from app.infrastructure.db.v2_planning_persistence import PgV2PlanningPersistence
    env = environment(db, checkpoint_db, scope)
    local = env.revisions.preview_local(scope=scope, project_id=env.project,
        current_plan_id=env.base.plan_id, expected_version=1, idempotency_key="cas-local",
        stage_edits=(LocalStageEdit(env.base.stages[-1].stage_id, what_to_learn="保留全部原目标，检查正常和失败结果"),)).draft
    run = submit(env, "terminal-cas-" + window + "-" + winner)
    published, counts = [], []
    def confirm(draft):
        chosen = draft if winner == "own_draft" else local
        result = env.revisions.confirm(scope=scope, project_id=env.project, draft_id=chosen.draft_id,
            expected_version=1, draft_hash=chosen.content_hash, idempotency_key="cas-winner")
        published.append(result.plan)
        counts.append(tuple(len(port.calls) for port in (env.provider, env.factory.github, env.factory.body_reader)))
    if window == "final_checkpoint":
        original = PgV2PlanningPersistence.persist
        def after_persist(self, **kw):
            draft = original(self, **kw)
            if kw["run_id"] == run:
                confirm(draft)
            return draft
        monkeypatch.setattr(PgV2PlanningPersistence, "persist", after_persist)
    else:
        original = env.service._update_run
        def before_finalize(**kw):
            if kw["run_id"] == run and kw["status"] == AiRunStatus.SUCCEEDED:
                confirm(env.repo.get_draft(project_id=env.project, draft_id=kw["result_ref"]))
            return original(**kw)
        monkeypatch.setattr(env.service, "_update_run", before_finalize)
    assert env.worker.tick()
    result = env.runs.get_run(project_id=env.project, run_id=run)
    assert result.status.value == ("succeeded" if winner == "own_draft" else "failed"), result
    assert result.next_action.value == "none"
    if winner == "local_draft":
        assert result.error_class == "v2_persistence_conflict"
    else:
        assert result.result_ref == env.repo.get_draft(project_id=env.project, draft_id=result.result_ref).draft_id
    assert len(published) == 1 and env.repo.get_current(project_id=env.project).plan_id == published[0].plan_id
    historical = env.repo.get_revision(project_id=env.project, revision=1)
    assert historical.structure_fingerprint() == env.base.structure_fingerprint()
    assert historical.v2_execution == env.base.v2_execution and historical.stages == env.base.stages
    assert counts == [tuple(len(port.calls) for port in (env.provider, env.factory.github, env.factory.body_reader))]
    with psycopg.connect(db.migrator_dsn) as conn:
        job = conn.execute("SELECT status FROM ai_jobs WHERE run_id=%s", (run,)).fetchone()[0]
    assert job == ("completed" if winner == "own_draft" else "failed")
    EVIDENCE.joinpath("r2-closure-terminal-cas-" + window + "-" + winner + ".json").write_text(json.dumps({
        "database": db.name, "run_id": run, "window": window, "winner": winner,
        "run_status": result.status.value, "job_status": job, "error_class": result.error_class,
        "current_plan_id": published[0].plan_id, "post_publication_dispatch": 0, "external_calls": 0}, indent=2), encoding="utf8")


@pytest.mark.parametrize("input_drift", [None, "goal", "source_facts"])
def test_own_published_semantic_result_recovers_after_final_checkpoint_interruption_without_dispatch(db, checkpoint_db, scope, monkeypatch, input_drift):
    from app.infrastructure.checkpointer.v2_planning_executor import PgV2Checkpoints
    from app.infrastructure.db.v2_planning_persistence import PgV2PlanningPersistence
    from app.ports.summaries import ReviewPersistenceInterrupted
    env = environment(db, checkpoint_db, scope)
    run = submit(env, "own-published-completion-recovery")
    original_persist, original_save = PgV2PlanningPersistence.persist, PgV2Checkpoints.save
    published, published_drafts = [], []
    def publish_after_persist(self, **kw):
        draft = original_persist(self, **kw)
        if kw["run_id"] == run:
            published_drafts.append(draft.draft_id)
            published.append(env.revisions.confirm(scope=scope, project_id=env.project, draft_id=draft.draft_id,
                expected_version=1, draft_hash=draft.content_hash, idempotency_key="confirm-before-interruption").plan)
        return draft
    def interrupted_final_save(self, state):
        if self.calls.run_id == run and state["stage"] == "draft_persistence":
            raise ReviewPersistenceInterrupted("owned crash after exact own publication")
        return original_save(self, state)
    monkeypatch.setattr(PgV2PlanningPersistence, "persist", publish_after_persist)
    monkeypatch.setattr(PgV2Checkpoints, "save", interrupted_final_save)
    assert env.worker.tick()
    assert env.runs.get_run(project_id=env.project, run_id=run).status.value == "running"
    assert len(published) == 1 and env.repo.get_current(project_id=env.project).plan_id == published[0].plan_id
    counts = tuple(len(port.calls) for port in (env.provider, env.factory.github, env.factory.body_reader))
    with psycopg.connect(db.migrator_dsn) as conn:
        conn.execute("UPDATE ai_jobs SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE run_id=%s", (run,))
    monkeypatch.setattr(PgV2PlanningPersistence, "persist", original_persist)
    monkeypatch.setattr(PgV2Checkpoints, "save", original_save)
    jobs = PgPlanningJobRepository(db.app_dsn, actor_ids=(scope.actor_id,))
    factory = env.factory
    if input_drift == "source_facts":
        factory.source_facts = CurriculumSourceFacts(ReviewedContentIndex("changed-source-version", (), (), ()))
    elif input_drift == "goal":
        from copy import deepcopy
        def drifted_input_factory(*args, **kw):
            runtime = env.factory(*args, **kw)
            execute = runtime.execute
            def execute_different_goal(initial):
                altered = deepcopy(initial)
                altered["goal_spec"]["target"] = "worker input drift must not bypass frozen goal"
                return execute(altered)
            runtime.execute = execute_different_goal
            return runtime
        factory = drifted_input_factory
    fresh = PlanService(repository=PgPlanRepository(db.app_dsn), runs=PgRunRepository(db.app_dsn),
        catalog=None, resources=None, llm=None, graph_version="", planning_jobs=jobs, v2_runtime_factory=factory)
    assert PlanningWorker(jobs=jobs, execute=fresh.execute_generation, actor_ids=(scope.actor_id,)).tick()
    recovered = env.runs.get_run(project_id=env.project, run_id=run)
    if input_drift:
        assert recovered.status.value == "reconciliation_required" and recovered.error_class == "v2_recovery_blocked", recovered
    else:
        assert recovered.status.value == "succeeded" and recovered.next_action.value == "none", recovered
        assert recovered.result_ref == published_drafts[0]
    draft = env.repo.get_draft(project_id=env.project, draft_id=published_drafts[0])
    assert draft.status.value == "approved" and draft.run_id == run
    assert counts == tuple(len(port.calls) for port in (env.provider, env.factory.github, env.factory.body_reader))
    assert env.repo.get_current(project_id=env.project).plan_id == published[0].plan_id
    EVIDENCE.joinpath("r2-closure-own-published-result-recovery-" + (input_drift or "valid") + ".json").write_text(json.dumps({"database": db.name,
        "run_id": run, "draft_id": draft.draft_id, "current_plan_id": published[0].plan_id,
        "run_status": recovered.status.value, "input_drift": input_drift, "new_dispatch": 0, "external_calls": 0}, indent=2), encoding="utf8")
