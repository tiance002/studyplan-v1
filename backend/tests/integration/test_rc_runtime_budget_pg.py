"""P1 ordinary worker/ledger boundaries in fresh owned PostgreSQL only."""

import json
import os
import subprocess
import sys
from copy import deepcopy
from dataclasses import asdict, replace
from pathlib import Path
from types import SimpleNamespace

import psycopg
import pytest

from app.agent_workflows.planning_batches import (
    DEFAULT_BUDGET, OUTLINE_PURPOSE, REPAIR_PURPOSE, SHORT_GENERATION_VERSION,
    allowed_attempt_keys, attempt_key, attempt_purpose, freeze_manifest,
)
from app.infrastructure.db.job_repository import PgPlanningJobRepository
from app.infrastructure.providers.runtime_factory import PersonalPlanningRuntimeFactory
from app.ports.llm import LLMFailure, LLMResult
from app.domain.runs.fencing import PlanningWriteFence
from tests.pg_harness import create_test_database, roles_created_by_harness
from tests.integration.test_planning_dispatch_fence_pg import (
    RecordingProvider, attempts, call, scenario,
    test_legacy_jobless_attempt_replay_keeps_pre_budget_fingerprint_compatibility as check_legacy_replay,
    test_replaced_lease_cannot_insert_a_new_attempt as check_replaced_lease,
    test_run_becomes_terminal_after_guard_before_dispatch as check_cancel,
)
from tests.integration.test_planning_jobs_pg import (
    queued_run, test_actor_project_listing_and_process_lock_are_scoped as check_admission,
    test_finished_or_unknown_runs_are_never_claimed as check_terminal_claim,
)
from tests.integration.test_run_budget_pg import CountingProvider

pytestmark = pytest.mark.postgres
BACKEND = Path(__file__).resolve().parents[2]
ROOT = BACKEND.parent
MODEL_REF = "mock:ordinary-runtime"


class OwnedDatabase:
    def __init__(self, db):
        self._db = db

    def __getattr__(self, name):
        return getattr(self._db, name)

    def __repr__(self):
        return f"OwnedDatabase(name={self._db.name!r})"


@pytest.fixture(scope="module")
def runtime_db():
    assert not os.environ.get("STUDYPLAN_TEST_PG_DEDICATED")
    before = roles_created_by_harness()
    db = create_test_database(prefix="studyplan_test_rc_runtime")
    assert db.name.startswith("studyplan_test_rc_runtime_")
    migrated = subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND, env=dict(os.environ, STUDYPLAN_MIGRATION_DSN=db.migrator_dsn),
        capture_output=True, text=True)
    assert migrated.returncode == 0, migrated.stderr
    with psycopg.connect(db.migrator_dsn) as conn:
        conn.execute("INSERT INTO learning_projects(project_id,owner_actor_id,title,goal_statement,stable_key) "
            "VALUES ('jobs_p1','jobs_a1','owned','goal','rc_owned_1'),"
            "('jobs_p2','jobs_a2','owned two','goal','rc_owned_2')")
    evidence = ROOT / "var/rc-runtime-20261005/review" / ("owned-" + db.name + ".json")
    with evidence.open("x", encoding="utf-8") as output:
        json.dump({"database": db.name, "new_owned": True, "migration": "PASS",
                   "provider_http_requests": 0, "role_mutations": 0}, output)
    assert roles_created_by_harness() == before == set()
    try:
        yield OwnedDatabase(db)
    finally:
        db.drop()
        assert roles_created_by_harness() == before


@pytest.fixture(autouse=True)
def clean_only_owned_runtime_database(runtime_db):
    with psycopg.connect(runtime_db.migrator_dsn) as conn:
        conn.execute("TRUNCATE ai_provider_attempts, ai_jobs, ai_runs CASCADE")


def test_allowlist_does_not_reclaim_unknown_planning_attempt(runtime_db):
    provider = RecordingProvider(LLMFailure("synthetic_unknown", "unknown", dispatch_unknown=True))
    repo, run, fence, provider, ledger = scenario(runtime_db, provider=provider)
    assert call(ledger, run, fence).dispatch_unknown
    with psycopg.connect(runtime_db.migrator_dsn) as conn:
        conn.execute("UPDATE ai_jobs SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE run_id=%s",
                     (run.run_id,))
    assert repo.claim(run.project_id, "restart-worker", 60) is None
    assert provider.calls == 1


def ordinary_scenario(db, monkeypatch, *, provider=None, manifest=None, run_id="rc_budget_run"):
    manifest = manifest or freeze_manifest(
        {"resource_support": "search_only", "stage_blueprints": []},
        DEFAULT_BUDGET, MODEL_REF, generic_stage_count=3)
    initial = {"goal": "owned generic", "manifest": deepcopy(manifest),
               "domain_pack": {"resource_support": "search_only", "stage_blueprints": []}}
    run = replace(queued_run(run_id), graph_version=SHORT_GENERATION_VERSION)
    repo = PgPlanningJobRepository(db.app_dsn, actor_ids=(run.actor_id,))
    repo.enqueue(run, initial, manifest)
    claim = repo.claim(run.project_id, "rc-budget-worker", 60)
    assert claim is not None
    fence = PlanningWriteFence(**asdict(claim))
    provider = provider or CountingProvider()
    provider.budget_policy = DEFAULT_BUDGET
    settings = SimpleNamespace(llm_allowed_hosts=(), database_url=db.app_dsn,
                               checkpoint_database_url=db.app_dsn)
    factory = PersonalPlanningRuntimeFactory(settings, SimpleNamespace())
    monkeypatch.setattr(factory, "for_bound_run", lambda *args: provider)
    scope = SimpleNamespace(require_project=lambda p: None)
    ledger = factory(scope, run.project_id, run.run_id, MODEL_REF, manifest=manifest).llm
    return repo, run, fence, provider, ledger, manifest, factory, scope


def dispatch(ledger, run, fence, key, *, purpose=None):
    return ledger.generate_structured(purpose=purpose or attempt_purpose(key),
        payload={"_project_id": run.project_id, "_planning_claim": asdict(fence)},
        schema_name="RuntimeBudgetOnlyV1", run_id=run.run_id, attempt_id=key)


def seed_retained_keys(db, run, keys, status="succeeded"):
    with psycopg.connect(db.migrator_dsn) as conn:
        for key in keys:
            conn.execute("INSERT INTO ai_provider_attempts(attempt_id,run_id,provider,model_id,prompt_version,status) "
                "VALUES (%s,%s,'owned-fake','mock-model','test',%s)", (key, run.run_id, status))


def test_nth_request_allowed_then_n_plus_one_rejected_after_runtime_restart(runtime_db, monkeypatch):
    repo, run, fence, provider, ledger, manifest, factory, scope = ordinary_scenario(runtime_db, monkeypatch)
    keys = sorted(allowed_attempt_keys(run.run_id, manifest))
    normal = [key for key in keys if attempt_purpose(key) != REPAIR_PURPOSE]
    repairs = [key for key in keys if attempt_purpose(key) == REPAIR_PURPOSE]
    target = normal[-1]
    prior = [key for key in normal if key != target] + repairs[:2]
    assert len(prior) == manifest["max_requests"] - 1
    seed_retained_keys(runtime_db, run, prior)
    assert isinstance(dispatch(ledger, run, fence, target), LLMResult)
    assert provider.calls == 1
    restarted = factory(scope, run.project_id, run.run_id, MODEL_REF, manifest=manifest).llm
    failed = dispatch(restarted, run, fence, repairs[2])
    assert isinstance(failed, LLMFailure) and failed.error_class == "run_budget_exhausted"
    assert provider.calls == 1 and len(attempts(runtime_db, run)) == manifest["max_requests"]


def test_output_budget_rejected_before_provider_with_request_count_below_cap(runtime_db, monkeypatch):
    _, run, fence, provider, ledger, manifest, _, _ = ordinary_scenario(runtime_db, monkeypatch)
    repairs = sorted(key for key in allowed_attempt_keys(run.run_id, manifest)
                     if attempt_purpose(key) == REPAIR_PURPOSE)
    # Simulate retained pre-fix rows. No historical product attempt is changed.
    seed_retained_keys(runtime_db, run, repairs[:7])
    target = attempt_key(run.run_id, OUTLINE_PURPOSE, "", 0, 0)
    assert 7 < manifest["max_requests"]
    failed = dispatch(ledger, run, fence, target)
    assert isinstance(failed, LLMFailure) and failed.error_class == "run_budget_exhausted"
    assert provider.calls == 0 and len(attempts(runtime_db, run)) == 7


def test_repair_total_two_across_batches_survives_runtime_restart(runtime_db, monkeypatch):
    _, run, fence, provider, ledger, manifest, factory, scope = ordinary_scenario(runtime_db, monkeypatch)
    batches = manifest["structure_batches"]
    keys = [attempt_key(run.run_id, REPAIR_PURPOSE, b["stage_key"], b["batch_index"], 1)
            for b in batches]
    assert len(keys) == 3
    assert isinstance(dispatch(ledger, run, fence, keys[0]), LLMResult)
    assert isinstance(dispatch(ledger, run, fence, keys[1]), LLMResult)
    restarted = factory(scope, run.project_id, run.run_id, MODEL_REF, manifest=manifest).llm
    result = dispatch(restarted, run, fence, keys[2])
    assert isinstance(result, LLMFailure) and result.error_class == "run_budget_exhausted"
    assert provider.calls == 2 and len(attempts(runtime_db, run)) == 2


def test_actual_provider_cap_and_purpose_mismatch_refuse_before_any_attempt(runtime_db, monkeypatch):
    _, run, fence, provider, ledger, manifest, _, _ = ordinary_scenario(runtime_db, monkeypatch)
    target = attempt_key(run.run_id, OUTLINE_PURPOSE, "", 0, 0)
    monkeypatch.setattr(provider, "request_options", lambda p: {"model": provider.model, "max_tokens": 4097})
    result = dispatch(ledger, run, fence, target)
    assert isinstance(result, LLMFailure) and result.error_class == "run_budget_exhausted"
    result = dispatch(ledger, run, fence, target, purpose="planning.practice")
    assert isinstance(result, LLMFailure) and result.error_class == "run_manifest_violation"
    assert provider.calls == 0 and not attempts(runtime_db, run)


@pytest.mark.parametrize("short,job", [(True, True), (True, False), (False, True)])
def test_modern_or_jobbacked_dispatch_missing_manifest_fails_closed(runtime_db, short, job):
    _, run, fence, provider, ledger = scenario(runtime_db, short=short, job=job)
    ledger.manifest = None
    result = call(ledger, run, fence)
    assert isinstance(result, LLMFailure) and result.error_class == "run_manifest_violation"
    assert provider.calls == 0 and not attempts(runtime_db, run)


def test_known_result_replay_after_lease_change_and_restart_has_no_new_dispatch(runtime_db):
    from app.infrastructure.providers.attempt_ledger import PgAttemptLLM

    repo, run, fence, provider, ledger = scenario(runtime_db)
    first = call(ledger, run, fence)
    with psycopg.connect(runtime_db.migrator_dsn) as conn:
        conn.execute("UPDATE ai_jobs SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE run_id=%s", (run.run_id,))
    claim = repo.claim(run.project_id, "replacement-known", 60)
    assert claim is not None
    restarted = PgAttemptLLM(runtime_db.app_dsn, provider, manifest=deepcopy(ledger.manifest))
    assert call(restarted, run, PlanningWriteFence(**asdict(claim))) == first
    assert provider.calls == 1 and len(attempts(runtime_db, run)) == 1


def test_retained_pre_budget_legacy_result_remains_readable(runtime_db):
    check_legacy_replay(runtime_db)


def test_expired_lease_fence_and_cancel_keep_provider_zero(runtime_db):
    check_replaced_lease(runtime_db)
    # Clear only this fixture's fresh DB between two inherited scenarios.
    with psycopg.connect(runtime_db.migrator_dsn) as conn:
        conn.execute("TRUNCATE ai_provider_attempts, ai_jobs, ai_runs CASCADE")
    check_cancel(runtime_db, "cancelled")


@pytest.mark.parametrize("status", ["failed", "reconciliation_required"])
def test_terminal_failed_or_unknown_run_is_not_claimed(runtime_db, status):
    check_terminal_claim(runtime_db, status)


@pytest.mark.parametrize("mode", ["allowlist", "trusted_server"])
def test_dispatched_attempt_not_reclaimed_after_expired_lease(runtime_db, mode):
    repo, run, _, _, _ = scenario(runtime_db)
    key = attempt_key(run.run_id, OUTLINE_PURPOSE, "", 0, 0)
    seed_retained_keys(runtime_db, run, [key], status="dispatched")
    with psycopg.connect(runtime_db.migrator_dsn) as conn:
        conn.execute("UPDATE ai_jobs SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE run_id=%s", (run.run_id,))
    if mode == "allowlist":
        assert repo.claim(run.project_id, "restart-dispatched", 60) is None
    else:
        trusted = PgPlanningJobRepository(runtime_db.app_dsn, actor_ids=(), admission_mode="trusted_server")
        assert trusted.claim_next("restart-dispatched", 60) is None


def test_admission_actor_scope_and_single_worker_lock(runtime_db):
    check_admission(runtime_db)


@pytest.fixture(scope="module")
def runtime_checkpoint_db():
    from app.agent_workflows.runtime import PostgresSaver

    assert not os.environ.get("STUDYPLAN_TEST_PG_DEDICATED") and not roles_created_by_harness()
    db = create_test_database(prefix="studyplan_test_rc_checkpoint")
    with PostgresSaver.from_conn_string(db.migrator_dsn) as saver:
        saver.setup()
    try:
        yield OwnedDatabase(db)
    finally:
        db.drop()
        assert not roles_created_by_harness()


def test_authorized_ordinary_worker_factory_pg_checkpoint_and_draft(runtime_db, runtime_checkpoint_db, monkeypatch):
    from app.application.model_binding import SubmissionBinding
    from app.composition import build_container
    from app.core.config import get_settings
    from app.infrastructure.checkpointer.planning_executor import PgPlanningExecutor
    from app.infrastructure.domain_pack import CURRENT_PACKS, load_pack
    from tests.helpers.planning_responses import build_planning_demo
    from app.main import create_app
    from app.tools.seed_b3 import seed_reviewed_pack
    from fastapi.testclient import TestClient
    from tests.integration.test_v62_semantic_pg import register

    with psycopg.connect(runtime_db.migrator_dsn) as conn:
        seed_reviewed_pack(conn, load_pack(CURRENT_PACKS["agent.application"]))
    settings = replace(get_settings(), database_url=runtime_db.app_dsn,
        database_url_sync=runtime_db.app_dsn, checkpoint_database_url=runtime_checkpoint_db.migrator_dsn,
        llm_provider="fake", local_session_token="", planning_worker_admission_mode="trusted_server",
        planning_worker_actor_ids=(), search_provider="", github_discovery_enabled=False,
        rag_base_url="", rag_api_key="")
    fake = build_planning_demo()

    class WholeRunProvider(CountingProvider):
        def generate_structured(self, **kwargs):
            self.calls += 1
            result = fake.generate_structured(**kwargs)
            assert isinstance(result, LLMResult)
            # Actual PG Attempt receipts are the sole authority, so do not emit
            # the in-process Fake event protocol in addition to durable rows.
            return replace(result, model_id=self.model, provider="owned_counting_fake")

    provider = WholeRunProvider()
    provider.budget_policy = DEFAULT_BUDGET
    provider.configuration_ref = MODEL_REF
    container = build_container(settings)
    factory = PersonalPlanningRuntimeFactory(settings, SimpleNamespace())
    monkeypatch.setattr(factory, "for_bound_run", lambda *args: provider)
    container.plan_service._runtime_factory = factory
    container.plan_service._binding_resolver = lambda *args: SubmissionBinding(MODEL_REF, DEFAULT_BUDGET)
    observed = []
    original = PgPlanningExecutor.execute_or_resume

    def observe(self, nodes, initial, *args, **kwargs):
        assert self.llm.manifest == initial["manifest"]
        assert self.llm.manifest is not initial["manifest"]
        observed.append(deepcopy(self.llm.manifest))
        return original(self, nodes, initial, *args, **kwargs)

    monkeypatch.setattr(PgPlanningExecutor, "execute_or_resume", observe)
    with TestClient(create_app(container)) as client:
        _, params, headers = register(client, "rc-runtime")
        response = client.post("/api/v1/plans/generate", params=params, headers=headers,
            json={"goal": "零基础系统学习 Agent 应用开发，先做一个最小应用。"})
        assert response.status_code == 202, response.text
        run_id = response.json()["run_id"]
        with psycopg.connect(runtime_db.migrator_dsn) as conn:
            submission = conn.execute("SELECT detail FROM ai_run_events WHERE run_id=%s AND detail->>'kind'='planning_submission'", (run_id,)).fetchone()[0]
        assert provider.calls == 0 and not observed
        assert container.planning_worker.tick()
        status = client.get(response.json()["status_url"]).json()
        assert (status["status"], status["next_action"]) == ("succeeded", "none"), status
        draft = client.get("/api/v1/plans/drafts/" + status["result_ref"], params=params).json()
        assert (draft["source_pack_key"], draft["source_pack_version"]) == ("agent.application", 8)
        assert observed == [submission["manifest"]]
        with psycopg.connect(runtime_db.migrator_dsn) as conn:
            rows = conn.execute("SELECT attempt_id,status FROM ai_provider_attempts WHERE run_id=%s", (run_id,)).fetchall()
        assert len(rows) == provider.calls == len(fake.calls)
        assert all(row[1] == "succeeded" for row in rows)
        assert provider.calls == 1 + len(submission["manifest"]["structure_batches"]) + len(submission["manifest"]["practice_batches"])
        assert not container.planning_worker.tick()
        with psycopg.connect(runtime_checkpoint_db.migrator_dsn) as conn:
            assert conn.execute("SELECT count(*) FROM checkpoints").fetchone()[0] > 0
        with (ROOT / "var/rc-runtime-20261005/review" / ("ordinary-worker-authority-" + run_id + ".json")).open("x", encoding="utf-8") as output:
            json.dump({"status": "PASS", "business_database": runtime_db.name,
                "checkpoint_database": runtime_checkpoint_db.name, "run_id": run_id,
                "manifest_hash": submission["manifest"]["manifest_hash"], "runtime_manifest_equals_pg_submission": True,
                "fake_dispatches": provider.calls, "real_http": 0, "draft_ref": status["result_ref"]}, output)
