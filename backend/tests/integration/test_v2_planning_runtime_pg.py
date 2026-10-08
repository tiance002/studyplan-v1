"""P3 owned PG tests; external ports are explicit synthetic fixtures."""

import json
import os
import subprocess
import sys
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import psycopg
import pytest
from app.domain.planning.content_coverage import ReviewedContentIndex
from app.domain.planning.curriculum_compiler import CurriculumSourceFacts
from app.domain.planning.resource_research import ResearchBudget
from app.domain.planning.v2_runtime import build_v2_manifest
from app.domain.runs.fencing import PlanningWriteFence
from app.domain.workspace.models import AuthContext
from app.infrastructure.checkpointer.v2_planning_runtime import V2PlanningRuntime
from app.infrastructure.db.job_repository import PgPlanningJobRepository
from app.infrastructure.providers.v2_attempts import PgV2Calls, V2BudgetExceeded, V2RecoveryBlocked
from app.ports.llm import LLMFailure, LLMResult
from app.ports.planning_jobs import PlanningLeaseLostError
from psycopg.types.json import Jsonb

from tests.pg_harness import create_test_database, harness_skip_reason, roles_created_by_harness

pytestmark = pytest.mark.postgres
ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "var/planning-v2-item7-p3-20261008"
STAMP = "2026-10-08T12:00:00+00:00"


@pytest.fixture(scope="module")
def checkpoint_db():
    from app.agent_workflows.runtime import PostgresSaver

    database = create_test_database(prefix="studyplan_test_v2p3_checkpoint")
    with psycopg.connect(database.migrator_dsn, autocommit=True) as conn:
        PostgresSaver(conn).setup()
        conn.execute("GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO studyplan_app")
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / ("owned-database-" + database.name + ".json")).write_text(
        json.dumps({"database": database.name, "purpose": "checkpoint", "roles_created": []}), encoding="utf8"
    )

    class SafeDatabase:
        def __getattr__(self, name):
            return getattr(database, name)

        def __repr__(self):
            return "OwnedPgDatabase(" + database.name + ")"

    yield SafeDatabase()


@pytest.fixture(scope="module")
def db():
    assert os.environ.get("STUDYPLAN_TEST_PG_DEDICATED", "").lower() not in {"1", "true", "yes", "on"}
    assert harness_skip_reason() is None
    database = create_test_database(prefix="studyplan_test_v2p3")
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=ROOT / "backend",
        env=dict(
            os.environ,
            STUDYPLAN_MIGRATION_DSN=database.migrator_dsn.replace("postgresql://", "postgresql+psycopg://"),
        ),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert not roles_created_by_harness()
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    receipt = json.dumps({"database": database.name, "migration": "0025", "roles_created": []})
    (EVIDENCE / ("owned-database-" + database.name + ".json")).write_text(receipt, encoding="utf8")
    (EVIDENCE / "owned-database.json").write_text(receipt, encoding="utf8")

    class SafeDatabase:
        def __getattr__(self, name):
            return getattr(database, name)

        def __repr__(self):
            return "OwnedPgDatabase(" + database.name + ")"

    yield SafeDatabase()


@pytest.fixture
def bound(db):
    from uuid import uuid4

    project, run, job, token = [prefix + uuid4().hex for prefix in ("p3_", "run_", "job_", "lease_")]
    scope = AuthContext("p3actor", "session", datetime.now(timezone.utc), (project,))
    with psycopg.connect(db.migrator_dsn) as conn:
        conn.execute(
            "INSERT INTO learning_projects(project_id,owner_actor_id,title,goal_statement,stable_key) VALUES(%s,%s,'P3','Goal',%s)",
            (project, scope.actor_id, project),
        )
        conn.execute(
            "INSERT INTO ai_runs(run_id,actor_id,project_id,kind,graph_name,graph_version,status,next_action,thread_id,version) VALUES(%s,%s,%s,'plan_generate','planning','planning-v2-execution-v1','running','wait',%s,1)",
            (run, scope.actor_id, project, run),
        )
        conn.execute(
            "INSERT INTO ai_jobs(job_id,run_id,job_key,status,lease_token,lease_expires_at) VALUES(%s,%s,%s,'running',%s,clock_timestamp()+interval '15 minutes')",
            (job, run, "planning:" + run, token),
        )
    facts = CurriculumSourceFacts(ReviewedContentIndex("empty", (), (), ()))
    budget = ResearchBudget(max_output_tokens=32768, max_total_requests=20, max_cost_micros=1000000)
    manifest = build_v2_manifest(
        "学习MCP", model_ref="test:frozen", source_facts=facts, budget=budget, checked_at=STAMP
    )
    with psycopg.connect(db.migrator_dsn) as conn:
        conn.execute(
            "INSERT INTO ai_run_events(run_id,status,detail) VALUES(%s,'submission',%s)",
            (
                run,
                Jsonb(
                    {
                        "kind": "planning_submission",
                        "actor_id": scope.actor_id,
                        "project_id": project,
                        "initial": {"goal": "学习MCP", "manifest": manifest},
                        "manifest": manifest,
                    }
                ),
            ),
        )
    fence = PlanningWriteFence(job, run, project, scope.actor_id, token)
    return scope, run, fence, facts, manifest


def calls(db, bound, provider):
    scope, run, fence, facts, manifest = bound
    return PgV2Calls(
        db.app_dsn,
        scope=scope,
        project_id=fence.project_id,
        run_id=run,
        manifest=manifest,
        fence=fence,
        provider=provider,
    )


class Provider:
    configuration_ref = "test:frozen"
    model = "synthetic"

    def __init__(self, result=None):
        self.result, self.calls = result, []

    def request_options(self, purpose):
        return {"max_tokens": 8192 if purpose == "planning.curriculum_composition" else 1024}

    def generate_structured(self, **kw):
        self.calls.append(kw)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result or LLMResult({"safe": True}, self.model, "fixture", output_tokens=10)


class PipelineProvider(Provider):
    """Synthetic semantics; real Item1–6 validators and Compiler all execute."""

    def generate_structured(self, **kw):
        from types import SimpleNamespace

        from app.domain.planning.goal_requirements import GoalRequirementProfile
        from app.domain.planning.v2_execution import _decode

        from backend.tests.unit.test_capability_planning import cap, wire
        from backend.tests.unit.test_curriculum import output as curriculum_output
        from backend.tests.unit.test_goal_requirement_analysis import output as profile_output
        from backend.tests.unit.test_resource_research import Reader

        self.calls.append(kw)
        payload = kw["payload"]
        if kw["purpose"] == "planning.goal_requirement_analysis":
            target = payload["goal"]["target"]
            value = profile_output(
                target_summary=target,
                required_requirements=[
                    {"text": target, "origin": "explicit", "source_refs": ["goal.target"], "rationale": ""}
                ],
            )
        elif kw["purpose"] == "planning.capability_planning":
            p = _decode(
                GoalRequirementProfile, {k: v for k, v in payload["profile"].items() if k != "profile_hash"}
            )
            value = wire(p, cap(p, "mcp", project_usage="excluded"))
        elif kw["purpose"] == "planning.research_reader":
            value = Reader().generate_structured(**kw).payload
        elif kw["purpose"] == "planning.curriculum_composition":
            value = curriculum_output(
                SimpleNamespace(to_payload=lambda: payload, input_hash=payload["input_hash"])
            )
        else:
            raise AssertionError("Unexpected product purpose")
        return LLMResult(value, self.model, "fixture", input_tokens=20, output_tokens=16, cost_micros=100)


class PipelineSearch:
    def __init__(self):
        self.calls = []

    def find(self, query):
        from backend.tests.unit.test_resource_research import candidate

        self.calls.append(query)
        return [replace(candidate(), project_id=query.extra["project_id"])]


class PipelineBodies:
    def __init__(self):
        self.calls = []

    def read(self, candidate, **kw):
        from backend.tests.unit.test_resource_research import body

        self.calls.append((candidate, kw))
        return body()


def invoke(ledger, bound, attempt="analysis"):
    return ledger.generate_structured(
        purpose="planning.goal_requirement_analysis",
        schema_name="GoalRequirementProfileV1",
        payload={"goal": {"target": "学习MCP"}},
        run_id=bound[1],
        attempt_id=attempt,
    )


def test_success_receipt_replay_and_budget_do_not_reset(db, bound):
    provider = Provider()
    first = calls(db, bound, provider)
    assert isinstance(invoke(first, bound), LLMResult)
    before = first.usage()
    resumed = calls(db, bound, provider)
    assert isinstance(invoke(resumed, bound), LLMResult)
    assert resumed.usage() == before
    assert len(provider.calls) == 1


def test_unknown_prevents_same_and_changed_identity_dispatch(db, bound):
    provider = Provider(TimeoutError())
    first = calls(db, bound, provider)
    assert invoke(first, bound).dispatch_unknown
    resumed = calls(db, bound, provider)
    assert invoke(resumed, bound).dispatch_unknown
    with pytest.raises(V2RecoveryBlocked):
        invoke(resumed, bound, "analysis-new")
    assert len(provider.calls) == 1
    assert resumed.usage()["total_requests"] == 1


def test_length_is_failed_truncation_without_repair(db, bound):
    provider = Provider(LLMResult({"broken": "json"}, "synthetic", "fixture", finish_reason="length"))
    result = invoke(calls(db, bound, provider), bound)
    assert isinstance(result, LLMFailure) and result.error_class == "provider_output_truncated"
    assert len(provider.calls) == 1


def test_stale_fence_cannot_dispatch(db, bound):
    scope, run, fence, facts, manifest = bound
    with psycopg.connect(db.migrator_dsn) as conn:
        conn.execute("UPDATE ai_jobs SET lease_token='replacement' WHERE run_id=%s", (run,))
    provider = Provider()
    with pytest.raises(PlanningLeaseLostError):
        invoke(calls(db, bound, provider), bound)
    assert provider.calls == []


def test_cancel_during_provider_retains_receipt_without_late_writes(db, bound):
    scope, run, fence, facts, manifest = bound

    class CancelProvider(Provider):
        def generate_structured(self, **kw):
            with psycopg.connect(db.app_dsn) as conn:
                conn.execute(
                    "SELECT set_config('app.project_id',%s,true),set_config('app.actor_id',%s,true)",
                    (fence.project_id, scope.actor_id),
                )
                version = conn.execute("SELECT version FROM ai_runs WHERE run_id=%s", (run,)).fetchone()[0]
            PgPlanningJobRepository(db.app_dsn, actor_ids=(scope.actor_id,)).cancel_run(
                actor_id=scope.actor_id,
                project_id=fence.project_id,
                run_id=run,
                expected_version=version,
                idempotency_key="cancel-p3",
            )
            return super().generate_structured(**kw)

    provider = CancelProvider()
    with pytest.raises(PlanningLeaseLostError):
        invoke(calls(db, bound, provider), bound)
    with psycopg.connect(db.migrator_dsn) as conn:
        assert (
            conn.execute("SELECT status FROM ai_runs WHERE run_id=%s", (run,)).fetchone()[0]
            == "reconciliation_required"
        )
        assert conn.execute("SELECT count(*) FROM plan_drafts WHERE run_id=%s", (run,)).fetchone()[0] == 0


def runtime(db, checkpoint_db, bound, provider=None, search=None, bodies=None, checkpoints=None, **kw):
    from app.infrastructure.checkpointer.v2_planning_executor import PgV2Checkpoints
    from app.infrastructure.db.v2_planning_persistence import PgV2PlanningPersistence

    provider, search, bodies = (
        provider or PipelineProvider(),
        search or PipelineSearch(),
        bodies or PipelineBodies(),
    )
    ledger = calls(db, bound, provider)
    cp = checkpoints or PgV2Checkpoints(checkpoint_db.app_dsn, calls=ledger, thread_id=bound[1])
    result = V2PlanningRuntime(
        calls=ledger,
        checkpoints=cp,
        persistence=PgV2PlanningPersistence(db.app_dsn),
        source_facts=bound[3],
        github=search,
        body_reader=bodies,
        **kw,
    )
    return result, provider, search, bodies


def initial(bound):
    return {"goal": "学习MCP", "manifest": bound[4]}


def test_complete_real_chain_and_all_checkpoints_missing_zero_dispatch(db, checkpoint_db, bound):
    first, provider, search, bodies = runtime(db, checkpoint_db, bound)
    draft = first.execute(initial(bound))
    assert not isinstance(draft, LLMFailure)
    before = (len(provider.calls), len(search.calls), len(bodies.calls))
    assert before == (4, 1, 1)
    from app.infrastructure.db.plan_repository import PgPlanRepository

    fresh = PgPlanRepository(db.app_dsn).get_draft(project_id=bound[2].project_id, draft_id=draft.draft_id)
    assert fresh.content_hash == draft.content_hash and fresh.v2_execution
    with psycopg.connect(checkpoint_db.migrator_dsn) as conn:
        for table in ("checkpoint_writes", "checkpoint_blobs", "checkpoints"):
            conn.execute(
                "DELETE FROM " + table + " WHERE thread_id=%s AND checkpoint_ns='planning-v2-execution-v1'",
                (bound[1],),
            )
    resumed, *_ = runtime(db, checkpoint_db, bound, provider, search, bodies)
    recovered = resumed.execute(initial(bound))
    assert recovered.content_hash == draft.content_hash
    assert (len(provider.calls), len(search.calls), len(bodies.calls)) == before
    assert resumed.calls.usage() == first.calls.usage()
    assert resumed.calls.usage()["candidates"] == 1
    EVIDENCE.joinpath("success-recovery.json").write_text(
        json.dumps(
            {
                "run_id": bound[1],
                "draft_id": draft.draft_id,
                "hash": draft.content_hash,
                "dispatch_before": before,
                "dispatch_after": before,
                "budget": resumed.calls.usage(),
                "result": "PASS",
            }
        ),
        encoding="utf8",
    )


@pytest.mark.parametrize("where", ["verdict", "envelope", "failure"])
def test_reader_body_echo_never_enters_receipt_or_checkpoint(db, checkpoint_db, bound, where):
    secret = "UNTRUSTED_TUTORIAL_BODY_CANARY_8b622783"
    from backend.tests.unit.test_resource_research import body

    class EchoProvider(PipelineProvider):
        def generate_structured(self, **kw):
            result = super().generate_structured(**kw)
            if kw["purpose"] == "planning.research_reader":
                if where == "verdict":
                    result.payload["outcomes"][0]["rationale"] = secret
                elif where == "envelope":
                    result = replace(
                        result,
                        model_id=secret,
                        provider=secret,
                        finish_reason=secret,
                        diagnostics={"body": secret},
                    )
                else:
                    result = LLMFailure(secret, secret, details={"body": secret})
            return result

    class SecretBody(PipelineBodies):
        def read(self, candidate, **kw):
            self.calls.append((candidate, kw))
            return body(secret)

    service, *_ = runtime(db, checkpoint_db, bound, provider=EchoProvider(), bodies=SecretBody())
    service.execute(initial(bound))
    with psycopg.connect(db.migrator_dsn) as conn:
        retained = conn.execute(
            "SELECT response_payload::text FROM ai_provider_attempts WHERE run_id=%s", (bound[1],)
        ).fetchall()
        events = conn.execute(
            "SELECT detail::text FROM ai_run_events WHERE run_id=%s", (bound[1],)
        ).fetchall()
    assert all(secret not in row[0] for row in retained + events)
    with psycopg.connect(checkpoint_db.migrator_dsn) as conn:
        rows = conn.execute("SELECT blob FROM checkpoint_blobs WHERE thread_id=%s", (bound[1],)).fetchall()
    assert all(secret.encode() not in bytes(row[0]) for row in rows if row[0] is not None)


def test_unknown_body_observed_excess_kept_across_restart(db, checkpoint_db, bound):
    from app.domain.planning.research_reader import TransientBody

    class ExcessBody(PipelineBodies):
        def read(self, candidate, **kw):
            self.calls.append((candidate, kw))
            return TransientBody("unknown", requests=4, bytes_read=70000)

    service, provider, search, bodies = runtime(db, checkpoint_db, bound, bodies=ExcessBody())
    result = service.execute(initial(bound))
    assert isinstance(result, LLMFailure) and result.dispatch_unknown
    usage = service.calls.usage()
    assert usage["body_bytes"] == 70000 and usage["total_requests"] == 7
    resumed, *_ = runtime(db, checkpoint_db, bound, provider, search, bodies)
    result = resumed.execute(initial(bound))
    assert result.dispatch_unknown
    assert resumed.calls.usage() == usage and len(bodies.calls) == 1


def test_retained_overrun_stays_blocked_after_restart(db, bound):
    provider = Provider(LLMResult({"safe": True}, "synthetic", "fixture", output_tokens=1025))
    ledger = calls(db, bound, provider)
    first = invoke(ledger, bound)
    replay = invoke(calls(db, bound, provider), bound)
    assert isinstance(first, LLMFailure) and first.error_class == "v2_budget_exceeded"
    assert isinstance(replay, LLMFailure) and replay.error_class == "v2_budget_exceeded"
    assert not first.dispatch_unknown and not replay.dispatch_unknown
    assert len(provider.calls) == 1
    assert ledger.usage()["output_tokens"] == 1025


def test_checkpoint_thread_is_bound_to_actual_run(db, checkpoint_db, bound):
    from app.infrastructure.checkpointer.v2_planning_executor import PgV2Checkpoints

    with pytest.raises(V2RecoveryBlocked):
        PgV2Checkpoints(
            checkpoint_db.app_dsn, calls=calls(db, bound, Provider()), thread_id="another-run-thread"
        )


def test_domain_verification_exact_remaining_budget_and_trusted_receipt_recovery(db, checkpoint_db, bound):
    from app.domain.planning.domain_verification import bind_domain_approval

    from backend.tests.unit.test_capability_planning import cap, plan, profile, wire
    from backend.tests.unit.test_domain_verification import pinned_reader, source

    source_record = source()
    scope, run, fence, facts, manifest = bound
    manifest = build_v2_manifest(
        "学习MCP",
        model_ref="test:frozen",
        source_facts=facts,
        budget=ResearchBudget(
            max_total_requests=4, max_body_bytes=65536, max_output_tokens=32768, max_cost_micros=1000000
        ),
        checked_at=STAMP,
        domain_sources=(source_record,),
    )
    bound = (scope, run, fence, facts, manifest)
    with psycopg.connect(db.migrator_dsn) as conn:
        conn.execute(
            "UPDATE ai_run_events SET detail=%s WHERE run_id=%s AND status='submission'",
            (
                Jsonb(
                    {
                        "kind": "planning_submission",
                        "actor_id": scope.actor_id,
                        "project_id": fence.project_id,
                        "initial": initial(bound),
                        "manifest": manifest,
                    }
                ),
                run,
            ),
        )
    reader, requests = pinned_reader()
    service, provider, *_ = runtime(
        db, checkpoint_db, bound, provider=Provider(), bodies=reader, domain_sources=(source_record,)
    )
    invoke(service.calls, bound, "analysis-first")
    invoke(service.calls, bound, "analysis-second")
    p = profile("学习MCP")
    approvals = service._verify_domains(p, {"ros2.action"})
    assert len(approvals) == 1 and len(requests) == 2
    frozen = plan(
        p,
        wire(p, cap(p, "ros2.action")),
        verification_evidence=(approvals[0].evidence,),
        domain_approvals=approvals,
    )
    bound_approval = bind_domain_approval(approvals[0], frozen)
    restarted, *_ = runtime(
        db, checkpoint_db, bound, provider, bodies=reader, domain_sources=(source_record,)
    )
    restored = restarted._verify_domains(p, {"ros2.action"})
    assert (
        len(requests) == 2
        and bind_domain_approval(restored[0], frozen).approval_hash == bound_approval.approval_hash
    )
    assert restarted.calls.usage()["total_requests"] == 4
    with psycopg.connect(db.migrator_dsn) as conn:
        events = conn.execute(
            "SELECT status,detail::text FROM ai_run_events WHERE run_id=%s", (run,)
        ).fetchall()
        assert sum(row[0] == "v2_nested_dispatch" for row in events) == 2
        from backend.tests.unit.test_domain_verification import TEXT

        assert all(TEXT not in row[1] for row in events)
    # A changed server registry cannot match a retained success receipt.
    changed = replace(source_record, version="different")
    rejected, *_ = runtime(db, checkpoint_db, bound, provider, bodies=reader, domain_sources=(changed,))
    with pytest.raises(V2RecoveryBlocked):
        rejected.execute(initial(bound))
    assert len(requests) == 2


def make_worker_service(
    db, checkpoint_db, *, provider=None, factory_transform=None, search=None, bodies=None, budget=None
):
    from types import SimpleNamespace
    from uuid import uuid4

    from app.application.plan_service import PlanService
    from app.domain.planning.intent import GoalSpec
    from app.infrastructure.db.plan_repository import PgPlanRepository
    from app.infrastructure.db.public_resource_catalog import PgPublicResourceCatalog
    from app.infrastructure.db.run_repository import PgRunRepository
    from app.infrastructure.providers.runtime_factory import OwnedV2PlanningRuntimeFactory
    from app.infrastructure.worker.planning_worker import PlanningWorker

    project = "p3worker_" + uuid4().hex[:12]
    actor = "p3worker_" + uuid4().hex[:12]
    scope = AuthContext(actor, "session", datetime.now(timezone.utc), (project,))
    with psycopg.connect(db.migrator_dsn) as conn:
        conn.execute(
            "INSERT INTO learning_projects(project_id,owner_actor_id,title,goal_statement,stable_key) VALUES(%s,%s,'P3 worker','Goal',%s)",
            (project, actor, project),
        )
    provider, search, bodies = (
        provider or PipelineProvider(),
        search or PipelineSearch(),
        bodies or PipelineBodies(),
    )
    facts = CurriculumSourceFacts(ReviewedContentIndex("empty", (), (), ()))
    factory = OwnedV2PlanningRuntimeFactory(
        db.app_dsn,
        checkpoint_db.app_dsn,
        source_facts=facts,
        budget=budget
        or ResearchBudget(max_output_tokens=32768, max_total_requests=20, max_cost_micros=1000000),
        binding_resolver=lambda scope, project: SimpleNamespace(model_ref="test:frozen"),
        provider_resolver=lambda scope, project, run, ref: provider,
        github=search,
        body_reader=bodies,
    )
    factory = factory_transform(factory) if factory_transform else factory
    jobs = PgPlanningJobRepository(db.app_dsn, actor_ids=(actor,))
    service = PlanService(
        repository=PgPlanRepository(db.app_dsn),
        runs=PgRunRepository(db.app_dsn),
        catalog=None,
        resources=PgPublicResourceCatalog(db.app_dsn),
        llm=provider,
        graph_version="",
        planning_jobs=jobs,
        v2_runtime_factory=factory,
    )
    worker = PlanningWorker(jobs=jobs, execute=service.execute_generation, actor_ids=(actor,))
    run = service.submit_owned_v2(scope=scope, project_id=project, goal_spec=GoalSpec("学习MCP"))
    return service, worker, jobs, scope, run, provider, search, bodies


def test_existing_worker_reclaims_after_draft_before_terminal_without_new_dispatch(db, checkpoint_db):
    from app.ports.summaries import ReviewPersistenceInterrupted

    captured = []

    class InterruptOnce:
        owned_only = True

        def __init__(self, inner):
            self.inner, self.once = inner, True

        def build_submission(self, *args):
            return self.inner.build_submission(*args)

        def __call__(self, *args, **kw):
            service = self.inner(*args, **kw)
            captured.append(service)
            execute = service.execute

            def interrupted(initial):
                result = execute(initial)
                if self.once:
                    self.once = False
                    raise ReviewPersistenceInterrupted("Simulated Worker crash after committed Draft")
                return result

            service.execute = interrupted
            return service

    service, worker, jobs, scope, run, provider, search, bodies = make_worker_service(
        db, checkpoint_db, factory_transform=InterruptOnce
    )
    assert worker.tick()
    before = (len(provider.calls), len(search.calls), len(bodies.calls))
    with psycopg.connect(db.migrator_dsn) as conn:
        row = conn.execute(
            "SELECT r.status,j.status,j.lease_token FROM ai_runs r JOIN ai_jobs j USING(run_id) WHERE run_id=%s",
            (run,),
        ).fetchone()
        assert row[:2] == ("running", "running")
        old_token = row[2]
        draft = conn.execute("SELECT draft_id FROM plan_drafts WHERE run_id=%s", (run,)).fetchone()[0]
        conn.execute(
            "UPDATE ai_jobs SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE run_id=%s",
            (run,),
        )
    from app.infrastructure.worker.planning_worker import PlanningWorker

    replacement = PlanningWorker(jobs=jobs, execute=service.execute_generation, actor_ids=(scope.actor_id,))
    assert replacement.tick()
    with psycopg.connect(db.migrator_dsn) as conn:
        row = conn.execute(
            "SELECT r.status,r.next_action,r.result_ref,j.status,j.lease_token FROM ai_runs r JOIN ai_jobs j USING(run_id) WHERE run_id=%s",
            (run,),
        ).fetchone()
    assert row[:4] == ("succeeded", "none", draft, "completed") and row[4] != old_token
    assert (len(provider.calls), len(search.calls), len(bodies.calls)) == before
    with pytest.raises(PlanningLeaseLostError):
        captured[0].calls.generate_structured(
            purpose="planning.goal_requirement_analysis",
            schema_name="GoalRequirementProfileV1",
            payload={"goal": {"target": "学习MCP"}},
            run_id=run,
            attempt_id="goal-analysis",
        )
    EVIDENCE.joinpath("worker-restart.json").write_text(
        json.dumps(
            {
                "run_id": run,
                "draft_id": draft,
                "replacement_claim": "PASS",
                "zero_new_dispatch": "PASS",
                "old_fence": "PASS",
            }
        ),
        encoding="utf8",
    )


@pytest.mark.parametrize("failure", ["reader_length", "reader_privacy", "incomplete"])
def test_known_failure_reaches_worker_terminal_without_unknown_or_draft(db, checkpoint_db, failure):
    class KnownFailure(PipelineProvider):
        def generate_structured(self, **kw):
            result = super().generate_structured(**kw)
            if kw["purpose"] == "planning.research_reader" and failure == "reader_length":
                return LLMFailure("provider_output_truncated", "Not retained", output_tokens=16)
            if kw["purpose"] == "planning.research_reader" and failure == "reader_privacy":
                result.payload["outcomes"][0]["rationale"] = kw["payload"]["chunks"][0]["text"]
            if kw["purpose"] == "planning.curriculum_composition" and failure == "incomplete":
                from types import SimpleNamespace

                from backend.tests.unit.test_curriculum import output

                result = replace(
                    result,
                    payload=output(
                        SimpleNamespace(
                            to_payload=lambda: kw["payload"], input_hash=kw["payload"]["input_hash"]
                        ),
                        project_study=True,
                    ),
                )
            return result

    _, worker, _, scope, run, provider, search, bodies = make_worker_service(
        db, checkpoint_db, provider=KnownFailure()
    )
    assert worker.tick()
    with psycopg.connect(db.migrator_dsn) as conn:
        row = conn.execute(
            "SELECT r.status,r.next_action,r.error_class,j.status FROM ai_runs r JOIN ai_jobs j USING(run_id) WHERE run_id=%s",
            (run,),
        ).fetchone()
        assert row[:2] == ("failed", "none") and row[3] == "failed"
        if failure == "reader_length":
            assert row[2] == "provider_output_truncated"
        assert conn.execute("SELECT count(*) FROM plan_drafts WHERE run_id=%s", (run,)).fetchone()[0] == 0


def test_request_budget_rejection_is_known_worker_failure_before_any_attempt(db, checkpoint_db):
    _, worker, _, _, run, provider, search, bodies = make_worker_service(
        db,
        checkpoint_db,
        budget=ResearchBudget(max_total_requests=0, max_output_tokens=32768, max_cost_micros=1000000),
    )
    assert worker.tick()
    with psycopg.connect(db.migrator_dsn) as conn:
        row = conn.execute(
            "SELECT r.status,r.next_action,r.error_class,j.status FROM ai_runs r JOIN ai_jobs j USING(run_id) WHERE run_id=%s",
            (run,),
        ).fetchone()
        assert row == ("failed", "none", "v2_budget_exceeded", "failed")
        assert (
            conn.execute("SELECT count(*) FROM ai_provider_attempts WHERE run_id=%s", (run,)).fetchone()[0]
            == 0
        )
        assert conn.execute("SELECT count(*) FROM plan_drafts WHERE run_id=%s", (run,)).fetchone()[0] == 0
    assert provider.calls == search.calls == bodies.calls == []


def test_composition_durable_budget_rejection_is_known_worker_failure(db, checkpoint_db):
    _, worker, _, _, run, provider, search, bodies = make_worker_service(
        db,
        checkpoint_db,
        budget=ResearchBudget(max_total_requests=20, max_output_tokens=10500, max_cost_micros=1000000),
    )
    assert worker.tick()
    with psycopg.connect(db.migrator_dsn) as conn:
        row = conn.execute(
            "SELECT r.status,r.next_action,r.error_class,j.status FROM ai_runs r JOIN ai_jobs j USING(run_id) WHERE run_id=%s",
            (run,),
        ).fetchone()
        assert row == ("failed", "none", "v2_budget_exceeded", "failed")
        assert conn.execute("SELECT count(*) FROM plan_drafts WHERE run_id=%s", (run,)).fetchone()[0] == 0
        assert (
            conn.execute(
                "SELECT count(*) FROM ai_provider_attempts WHERE run_id=%s AND provider='v2:planning.curriculum_composition'",
                (run,),
            ).fetchone()[0]
            == 0
        )
    assert len(provider.calls) == 3 and len(search.calls) == len(bodies.calls) == 1
    assert all(call["purpose"] != "planning.curriculum_composition" for call in provider.calls)


@pytest.mark.parametrize("rejection", ["missing_factory", "manifest_mismatch"])
def test_v2_initialization_rejection_ends_actual_worker_run(db, checkpoint_db, rejection):
    service, worker, _, _, run, provider, search, bodies = make_worker_service(db, checkpoint_db)
    if rejection == "missing_factory":
        service._v2_runtime_factory = None
    else:
        with psycopg.connect(db.migrator_dsn) as conn:
            conn.execute(
                "UPDATE ai_run_events SET detail=jsonb_set(detail,'{initial,manifest,checked_at}',to_jsonb('changed'::text)) WHERE run_id=%s AND status='submission'",
                (run,),
            )
    assert worker.tick()
    with psycopg.connect(db.migrator_dsn) as conn:
        row = conn.execute(
            "SELECT r.status,r.next_action,r.error_class,j.status FROM ai_runs r JOIN ai_jobs j USING(run_id) WHERE run_id=%s",
            (run,),
        ).fetchone()
        expected = "v2_runtime_unavailable" if rejection == "missing_factory" else "v2_persistence_conflict"
        assert row == ("failed", "none", expected, "failed")
        assert (
            conn.execute("SELECT count(*) FROM ai_provider_attempts WHERE run_id=%s", (run,)).fetchone()[0]
            == 0
        )
    assert provider.calls == search.calls == bodies.calls == []


def test_candidate_admission_exact_budget_replays_and_rejects_without_provider_attempt(db, bound):
    ledger = calls(db, bound, Provider())
    cap = bound[4]["budget"]["max_candidates"]
    for index in range(cap):
        ledger.admit_candidate("https://github.com/owner/resource-" + str(index))
    ledger.admit_candidate("https://github.com/owner/resource-0")
    assert ledger.usage()["candidates"] == cap
    with pytest.raises(V2BudgetExceeded):
        ledger.admit_candidate("https://github.com/owner/excess")
    with psycopg.connect(db.migrator_dsn) as conn:
        assert (
            conn.execute("SELECT count(*) FROM ai_provider_attempts WHERE run_id=%s", (bound[1],)).fetchone()[
                0
            ]
            == 0
        )
        assert (
            conn.execute(
                "SELECT count(*) FROM ai_run_events WHERE run_id=%s AND status='v2_candidate_admission'",
                (bound[1],),
            ).fetchone()[0]
            == cap
        )
    assert ledger.usage()["candidates"] == cap


def test_dispatched_without_receipt_blocks_reclaim_and_new_identity(db, bound):
    class KilledProvider(Provider):
        def generate_structured(self, **kw):
            self.calls.append(kw)
            raise SystemExit("Simulated process kill after dispatch")

    provider = KilledProvider()
    with pytest.raises(SystemExit):
        invoke(calls(db, bound, provider), bound)
    restarted = calls(db, bound, provider)
    assert invoke(restarted, bound).dispatch_unknown
    with pytest.raises(V2RecoveryBlocked):
        invoke(restarted, bound, "new-identity")
    with psycopg.connect(db.migrator_dsn) as conn:
        conn.execute(
            "UPDATE ai_jobs SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE run_id=%s",
            (bound[1],),
        )
    jobs = PgPlanningJobRepository(db.app_dsn, actor_ids=(bound[0].actor_id,))
    assert jobs.claim(bound[2].project_id, "replacement-worker", 300) is None
    assert len(provider.calls) == 1 and restarted.usage()["total_requests"] == 1


def test_caller_resigned_budget_cannot_replace_frozen_submission(db, bound):
    from app.core.ids import content_hash

    scope, run, fence, facts, manifest = bound
    changed = json.loads(json.dumps(manifest))
    changed["budget"]["max_total_requests"] += 100
    changed["manifest_hash"] = content_hash({k: v for k, v in changed.items() if k != "manifest_hash"})
    altered = (scope, run, fence, facts, changed)
    provider = Provider()
    with pytest.raises(V2RecoveryBlocked):
        invoke(calls(db, altered, provider), altered)
    assert provider.calls == []


def test_unknown_domain_full_chain_restores_registry_receipt_and_bound_plan(db, checkpoint_db, bound):
    from app.domain.planning.goal_requirements import GoalRequirementProfile
    from app.domain.planning.v2_execution import _decode
    from app.infrastructure.resources.teaching_body import GitHubTeachingBody

    from backend.tests.unit.test_capability_planning import cap, wire
    from backend.tests.unit.test_domain_verification import pinned_reader, source
    from backend.tests.unit.test_resource_research import body

    source_record = source()
    pinned, requests = pinned_reader()

    class CombinedBody:
        _transport = pinned._transport

        def read(self, candidate, **kw):
            if candidate.url == source_record.repo_url:
                return GitHubTeachingBody(transport=self._transport).read(candidate, **kw)
            return body()

    class UnknownProvider(PipelineProvider):
        def generate_structured(self, **kw):
            if kw["purpose"] == "planning.capability_planning":
                self.calls.append(kw)
                p = _decode(
                    GoalRequirementProfile,
                    {k: v for k, v in kw["payload"]["profile"].items() if k != "profile_hash"},
                )
                return LLMResult(
                    wire(p, cap(p, "ros2.action", project_usage="excluded")),
                    self.model,
                    "fixture",
                    input_tokens=20,
                    output_tokens=16,
                    cost_micros=100,
                )
            return super().generate_structured(**kw)

    scope, run, fence, facts, _ = bound
    manifest = build_v2_manifest(
        "学习ROS2 Action",
        model_ref="test:frozen",
        source_facts=facts,
        budget=ResearchBudget(max_output_tokens=32768, max_total_requests=20, max_cost_micros=1000000),
        checked_at=STAMP,
        domain_sources=(source_record,),
    )
    bound = (scope, run, fence, facts, manifest)
    payload = {"goal": "学习ROS2 Action", "manifest": manifest}
    with psycopg.connect(db.migrator_dsn) as conn:
        conn.execute(
            "UPDATE ai_run_events SET detail=%s WHERE run_id=%s AND status='submission'",
            (
                Jsonb(
                    {
                        "kind": "planning_submission",
                        "actor_id": scope.actor_id,
                        "project_id": fence.project_id,
                        "initial": payload,
                        "manifest": manifest,
                    }
                ),
                run,
            ),
        )
    first, provider, search, bodies = runtime(
        db,
        checkpoint_db,
        bound,
        provider=UnknownProvider(),
        bodies=CombinedBody(),
        domain_sources=(source_record,),
    )
    draft = first.execute(payload)
    assert not isinstance(draft, LLMFailure)
    authority = first.calls.domain_approvals[0]
    assert authority.plan_hash is not None
    dispatches = (len(provider.calls), len(search.calls), len(requests))
    assert dispatches == (5, 1, 2)
    with psycopg.connect(checkpoint_db.migrator_dsn) as conn:
        for table in ("checkpoint_writes", "checkpoint_blobs", "checkpoints"):
            conn.execute(
                "DELETE FROM " + table + " WHERE thread_id=%s AND checkpoint_ns='planning-v2-execution-v1'",
                (run,),
            )
    recovered, *_ = runtime(
        db, checkpoint_db, bound, provider, search, bodies, domain_sources=(source_record,)
    )
    resumed = recovered.execute(payload)
    assert resumed.content_hash == draft.content_hash
    assert recovered.calls.domain_approvals[0].approval_hash == authority.approval_hash
    assert (len(provider.calls), len(search.calls), len(requests)) == dispatches
    EVIDENCE.joinpath("domain-recovery.json").write_text(
        json.dumps(
            {
                "run_id": run,
                "trusted_registry_receipt": "PASS",
                "actual_plan_hash": authority.plan_hash,
                "zero_new_dispatch": "PASS",
            }
        ),
        encoding="utf8",
    )
