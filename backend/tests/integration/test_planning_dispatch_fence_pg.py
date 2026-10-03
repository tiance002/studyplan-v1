"""Normal planning dispatch uses its live claim in the durable Attempt transaction.

Only the owned disposable jobs database and a counting synthetic provider are
used. These tests send no external requests and modify no product database.
"""

from __future__ import annotations

import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace

import psycopg
import pytest
from app.agent_workflows.planning_batches import (
    OUTLINE_PURPOSE,
    SHORT_GENERATION_VERSION,
    attempt_key,
    freeze_manifest,
)
from app.application.plan_service import PlanService, _ScopedLLM
from app.domain.runs.fencing import PlanningWriteFence
from app.infrastructure import domain_pack
from app.infrastructure.db.job_repository import PgPlanningJobRepository
from app.infrastructure.providers.attempt_ledger import PgAttemptLLM
from app.ports.llm import LLMFailure, LLMResult
from app.ports.planning_jobs import PlanningLeaseLostError
from psycopg.conninfo import make_conninfo
from psycopg.rows import dict_row

from tests.integration.test_planning_jobs_pg import jobs_db as jobs_db
from tests.integration.test_planning_jobs_pg import queued_run
from tests.integration.test_run_budget_pg import AGENT_GOAL, POLICY, CountingProvider

pytestmark = pytest.mark.postgres


@pytest.fixture(autouse=True)
def clear_owned_dispatch_database(jobs_db):
    with psycopg.connect(jobs_db.migrator_dsn, autocommit=True) as conn:
        conn.execute("TRUNCATE ai_provider_attempts, ai_jobs, ai_runs CASCADE")


class RecordingProvider(CountingProvider):
    def __init__(self, outcome=None, on_dispatch=lambda: None):
        super().__init__()
        self.payloads = []
        self.outcome = outcome
        self.on_dispatch = on_dispatch

    def generate_structured(self, **kwargs):
        self.payloads.append(kwargs["payload"])
        self.on_dispatch()
        result = super().generate_structured(**kwargs)
        return self.outcome if self.outcome is not None else result


def scenario(db, *, run_id="dispatch_run", short=True, job=True, provider=None):
    run = replace(queued_run(run_id), graph_version=SHORT_GENERATION_VERSION if short else "b3f2-batch-v1")
    manifest = freeze_manifest(domain_pack.select_domain_pack(AGENT_GOAL), POLICY, "mock:1")
    repo = PgPlanningJobRepository(db.app_dsn, actor_ids=("jobs_a1", "jobs_a2"))
    if job:
        repo.enqueue(run, {"goal": AGENT_GOAL}, manifest)
        claim = repo.claim("jobs_p1", "dispatch-test", 60)
        assert claim is not None
        fence = PlanningWriteFence(**asdict(claim))
    else:
        with psycopg.connect(db.migrator_dsn) as conn:
            conn.execute(
                "INSERT INTO ai_runs (run_id,actor_id,project_id,kind,graph_name,graph_version,status,next_action,thread_id,version) "
                "VALUES (%s,'jobs_a1','jobs_p1','plan_generate','planning',%s,'running','wait',%s,1)",
                (run_id, run.graph_version, run.thread_id),
            )
        fence = None
    provider = provider or RecordingProvider()
    ledger = PgAttemptLLM(db.app_dsn, provider, manifest=manifest)
    return repo, run, fence, provider, ledger


def call(ledger, run, fence=None, *, payload=None):
    context = {"goal": AGENT_GOAL, "_project_id": run.project_id}
    if fence is not None:
        context["_planning_claim"] = asdict(fence)
    if payload is not None:
        context.update(payload)
    return ledger.generate_structured(
        purpose=OUTLINE_PURPOSE, payload=context, schema_name="OutlineV1", run_id=run.run_id,
        attempt_id=attempt_key(run.run_id, OUTLINE_PURPOSE, "", 0, 0),
    )


def attempts(db, run):
    with psycopg.connect(db.migrator_dsn, row_factory=dict_row) as conn:
        return conn.execute("SELECT * FROM ai_provider_attempts WHERE run_id=%s", (run.run_id,)).fetchall()


def invalidate(db, run, *, run_status=None, job_status=None):
    with psycopg.connect(db.migrator_dsn) as conn:
        if run_status:
            conn.execute("UPDATE ai_runs SET status=%s WHERE run_id=%s", (run_status, run.run_id))
        if job_status:
            conn.execute("UPDATE ai_jobs SET status=%s,lease_token=NULL,lease_expires_at=NULL WHERE run_id=%s", (job_status, run.run_id))


@pytest.mark.parametrize("claim", [None, {}, {"lease_token": "fake"}, "fake"])
def test_job_backed_dispatch_requires_exact_server_claim(jobs_db, claim):
    _, run, _, provider, ledger = scenario(jobs_db)
    result = call(ledger, run, payload={"_planning_claim": claim})
    assert isinstance(result, LLMFailure)
    assert result.error_class == "planning_claim_missing"
    assert provider.calls == 0
    assert attempts(jobs_db, run) == []


@pytest.mark.parametrize("status", ["cancelled", "succeeded", "failed", "waiting_user", "reconciliation_required"])
def test_run_becomes_terminal_after_guard_before_dispatch(jobs_db, status):
    _, run, fence, provider, ledger = scenario(jobs_db)

    def guard():
        invalidate(jobs_db, run, run_status=status)

    scoped = _ScopedLLM(ledger, run.project_id, guard, write_fence=fence)
    with pytest.raises(PlanningLeaseLostError):
        scoped.generate_structured(
            purpose=OUTLINE_PURPOSE, payload={"goal": AGENT_GOAL}, schema_name="OutlineV1",
            run_id=run.run_id, attempt_id=attempt_key(run.run_id, OUTLINE_PURPOSE, "", 0, 0),
        )
    assert provider.calls == 0
    assert attempts(jobs_db, run) == []


@pytest.mark.parametrize("status", ["cancelled", "completed", "failed", "reconciliation_required"])
def test_job_becomes_terminal_after_guard_before_dispatch(jobs_db, status):
    _, run, fence, provider, ledger = scenario(jobs_db)
    invalidate(jobs_db, run, job_status=status)
    with pytest.raises(PlanningLeaseLostError):
        call(ledger, run, fence)
    assert provider.calls == 0
    assert attempts(jobs_db, run) == []


def test_replaced_lease_cannot_insert_a_new_attempt(jobs_db):
    repo, run, fence, provider, ledger = scenario(jobs_db)
    with psycopg.connect(jobs_db.migrator_dsn) as conn:
        conn.execute("UPDATE ai_jobs SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE run_id=%s", (run.run_id,))
    replacement = repo.claim(run.project_id, "replacement", 60)
    assert replacement is not None and replacement.lease_token != fence.lease_token
    with pytest.raises(PlanningLeaseLostError):
        call(ledger, run, fence)
    assert provider.calls == 0
    assert attempts(jobs_db, run) == []


@pytest.mark.parametrize("field,value", [("project_id", "jobs_p2"), ("actor_id", "jobs_a2"), ("run_id", "foreign-run"), ("job_id", "foreign-job")])
def test_foreign_claim_cannot_authorize_dispatch(jobs_db, field, value):
    _, run, fence, provider, ledger = scenario(jobs_db)
    with pytest.raises(PlanningLeaseLostError):
        call(ledger, run, replace(fence, **{field: value}))
    assert provider.calls == 0
    assert attempts(jobs_db, run) == []


def test_claim_is_not_provider_context_or_semantic_fingerprint(jobs_db):
    repo, run, fence, provider, ledger = scenario(jobs_db)
    first = call(ledger, run, fence)
    assert isinstance(first, LLMResult)
    assert provider.payloads == [{"goal": AGENT_GOAL, "_project_id": "jobs_p1"}]
    identity = [
        "planning.outline", {"goal": AGENT_GOAL, "_project_id": "jobs_p1"}, "OutlineV1",
        "mock-model", "test", {}, {"model": "mock-model", "max_tokens": 4096},
        POLICY.as_dict(), "https://provider.example", "deployment",
    ]
    expected = hashlib.sha256(json.dumps(identity, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    assert attempts(jobs_db, run)[0]["request_fingerprint"] == expected
    with psycopg.connect(jobs_db.migrator_dsn) as conn:
        conn.execute("UPDATE ai_jobs SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE run_id=%s", (run.run_id,))
    replacement = repo.claim(run.project_id, "replacement", 60)
    assert replacement is not None and replacement.lease_token != fence.lease_token
    replay = call(ledger, run, PlanningWriteFence(**asdict(replacement)))
    assert replay == first
    assert provider.calls == 1
    assert len(attempts(jobs_db, run)) == 1


def test_nodes_use_server_claim_and_ignore_payload_scope_spoof(jobs_db):
    _, run, fence, provider, ledger = scenario(jobs_db)
    service = PlanService.__new__(PlanService)
    service._llm = ledger
    nodes = service._build_nodes(
        project_id=run.project_id, run_id=run.run_id, goal=AGENT_GOAL, write_fence=fence,
    )
    result = nodes.llm.generate_structured(
        purpose=OUTLINE_PURPOSE,
        payload={"goal": AGENT_GOAL, "_project_id": "jobs_p2", "_planning_claim": {"lease_token": "spoof"}},
        schema_name="OutlineV1", run_id=run.run_id,
        attempt_id=attempt_key(run.run_id, OUTLINE_PURPOSE, "", 0, 0),
    )
    assert isinstance(result, LLMResult)
    assert provider.payloads == [{"goal": AGENT_GOAL, "_project_id": "jobs_p1"}]
    assert len(attempts(jobs_db, run)) == 1


def test_scoped_payload_cannot_supply_claim_without_server_fence(jobs_db):
    _, run, fence, provider, ledger = scenario(jobs_db)
    scoped = _ScopedLLM(ledger, run.project_id)
    result = scoped.generate_structured(
        purpose=OUTLINE_PURPOSE, payload={"goal": AGENT_GOAL, "_planning_claim": asdict(fence)},
        schema_name="OutlineV1", run_id=run.run_id,
        attempt_id=attempt_key(run.run_id, OUTLINE_PURPOSE, "", 0, 0),
    )
    assert isinstance(result, LLMFailure) and result.error_class == "planning_claim_missing"
    assert provider.calls == 0
    assert attempts(jobs_db, run) == []


def test_unknown_attempt_replays_after_token_change_without_redispatch(jobs_db):
    provider = RecordingProvider(LLMFailure("transport_unknown", "unknown", dispatch_unknown=True))
    repo, run, fence, provider, ledger = scenario(jobs_db, provider=provider)
    assert call(ledger, run, fence).dispatch_unknown
    with psycopg.connect(jobs_db.migrator_dsn) as conn:
        conn.execute("UPDATE ai_jobs SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE run_id=%s", (run.run_id,))
    replacement = repo.claim(run.project_id, "replacement", 60)
    assert replacement is not None
    replay = call(ledger, run, PlanningWriteFence(**asdict(replacement)))
    assert isinstance(replay, LLMFailure) and replay.dispatch_unknown
    assert replay.error_class == "attempt_dispatch_unknown"
    assert provider.calls == 1
    assert attempts(jobs_db, run)[0]["status"] == "reconciliation_required"


@pytest.mark.parametrize("outcome", [None, LLMFailure("transport_unknown", "unknown", dispatch_unknown=True)])
def test_late_provider_outcome_retained_after_dispatch_claim_invalidated(jobs_db, outcome):
    provider = RecordingProvider(outcome)
    _, run, fence, provider, ledger = scenario(jobs_db, provider=provider)

    def cancel_after_dispatched_commit():
        assert attempts(jobs_db, run)[0]["status"] == "dispatched"
        invalidate(jobs_db, run, run_status="cancelled", job_status="cancelled")

    provider.on_dispatch = cancel_after_dispatched_commit
    result = call(ledger, run, fence)
    assert result == (outcome if outcome is not None else LLMResult(payload={"ok": True}, model_id="mock-model", provider="mock"))
    retained = attempts(jobs_db, run)
    assert len(retained) == 1
    assert retained[0]["status"] == ("succeeded" if outcome is None else "reconciliation_required")
    assert retained[0]["response_payload"] == asdict(result)
    assert provider.calls == 1
    replay = call(ledger, run)
    if outcome is None:
        assert replay == result
    else:
        assert isinstance(replay, LLMFailure) and replay.error_class == "attempt_dispatch_unknown"
        assert replay.dispatch_unknown
    assert provider.calls == 1
    assert attempts(jobs_db, run) == retained


def test_cancel_first_budget_lock_serializes_manifestless_dispatch(jobs_db):
    _, run, fence, provider, ledger = scenario(jobs_db)
    ledger.manifest = None
    marker = "planning-dispatch-budget-wait"
    ledger.dsn = make_conninfo(ledger.dsn, application_name=marker)
    with ThreadPoolExecutor(max_workers=1) as pool, psycopg.connect(jobs_db.migrator_dsn) as cancellation:
        cancellation.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (f"studyplan:plan-budget:{run.run_id}",))
        pending = pool.submit(call, ledger, run, fence)
        try:
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                # An administrator observes only this owned database's blocked
                # app connection; the migrator cannot see another role's waits.
                with psycopg.connect(jobs_db.admin_dsn) as observer:
                    waiting = observer.execute(
                        "SELECT 1 FROM pg_stat_activity WHERE application_name=%s AND wait_event_type='Lock'",
                        (marker,),
                    ).fetchone()
                if waiting:
                    break
                if pending.done():
                    pytest.fail("Dispatch bypassed the cancellation budget lock")
                time.sleep(0.01)
            else:
                pytest.fail("Dispatch did not reach the cancellation budget lock")
            assert provider.calls == 0
            assert attempts(jobs_db, run) == []
            cancellation.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (f"plan-decision:{run.project_id}",))
            cancellation.execute("UPDATE ai_jobs SET status='cancelled',lease_token=NULL,lease_expires_at=NULL WHERE run_id=%s", (run.run_id,))
            cancellation.execute("UPDATE ai_runs SET status='cancelled' WHERE run_id=%s", (run.run_id,))
        finally:
            cancellation.commit()
        with pytest.raises(PlanningLeaseLostError):
            pending.result(timeout=5)
    assert provider.calls == 0
    assert attempts(jobs_db, run) == []


def test_short_run_without_job_fails_closed(jobs_db):
    _, run, _, provider, ledger = scenario(jobs_db, job=False)
    result = call(ledger, run)
    assert isinstance(result, LLMFailure) and result.error_class == "planning_claim_missing"
    assert provider.calls == 0
    assert attempts(jobs_db, run) == []


def test_pre_batch_jobless_dispatch_and_replay_remain_compatible(jobs_db):
    _, run, _, provider, ledger = scenario(jobs_db, short=False, job=False)
    with psycopg.connect(jobs_db.migrator_dsn) as conn:
        conn.execute("UPDATE ai_runs SET graph_version='1' WHERE run_id=%s", (run.run_id,))
    first = call(ledger, run)
    assert isinstance(first, LLMResult)
    assert call(ledger, run) == first
    assert provider.calls == 1
    assert len(attempts(jobs_db, run)) == 1


def test_legacy_jobless_attempt_replay_keeps_pre_budget_fingerprint_compatibility(jobs_db):
    _, run, _, provider, ledger = scenario(jobs_db, short=False, job=False)
    payload = {"goal": AGENT_GOAL, "_project_id": run.project_id}
    identity = ["planning.outline", payload, "OutlineV1", "mock-model", "test", {}]
    fingerprint = hashlib.sha256(json.dumps(identity, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    result = LLMResult(payload={"legacy": True}, model_id="mock-model", provider="mock")
    from psycopg.types.json import Jsonb

    with psycopg.connect(jobs_db.migrator_dsn) as conn:
        conn.execute(
            "INSERT INTO ai_provider_attempts(attempt_id,run_id,provider,model_id,prompt_version,status,request_fingerprint,response_payload,schema_name) "
            "VALUES (%s,%s,'mock','mock-model','test','succeeded',%s,%s,'OutlineV1')",
            (attempt_key(run.run_id, OUTLINE_PURPOSE, "", 0, 0), run.run_id, fingerprint, Jsonb(asdict(result))),
        )
    assert call(ledger, run) == result
    assert provider.calls == 0
    assert len(attempts(jobs_db, run)) == 1
