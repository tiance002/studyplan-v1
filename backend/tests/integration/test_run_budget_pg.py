"""Task 3: the ledger enforces the frozen run budget before any paid dispatch.

Runs only against a disposable ``studyplan_test_*`` database (never the existing
business database). No provider request is ever made: the counting provider only
records how many times it was actually invoked, so "zero external calls" is a
real assertion, not a proxy.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.postgres

import psycopg  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND_DIR))

from app.agent_workflows.planning_batches import (  # noqa: E402
    OUTLINE_PURPOSE,
    STRUCTURE_PURPOSE,
    allowed_attempt_keys,
    attempt_key,
    freeze_manifest,
)
from app.application.planning_budget import BudgetPolicy  # noqa: E402
from app.infrastructure import domain_pack  # noqa: E402
from app.infrastructure.providers.attempt_ledger import PgAttemptLLM  # noqa: E402
from app.ports.llm import LLMFailure, LLMResult  # noqa: E402

from tests.pg_harness import PgTestDatabase, create_test_database  # noqa: E402

POLICY = BudgetPolicy(4096, 8192, 4096, 8192, 8192, 393216)
AGENT_GOAL = "从 Python 基础开始学习 Agent 应用开发"


class CountingProvider:
    """Minimal provider that only counts real dispatches."""

    def __init__(self) -> None:
        self.calls = 0
        self.model = "mock-model"
        self.prompt_version = "test"
        self.domain_pack: dict = {}
        self.base_url = "https://provider.example"
        self.configuration_ref = "deployment"
        self.budget_policy = POLICY

    def request_options(self, purpose: str) -> dict[str, object]:
        return {"model": self.model, "max_tokens": self.budget_policy.for_purpose(purpose)}

    def generate_structured(self, *, purpose, payload, schema_name, run_id, attempt_id):
        self.calls += 1
        return LLMResult(payload={"ok": True}, model_id=self.model, provider="mock")


@pytest.fixture(scope="module")
def budget_db() -> PgTestDatabase:
    db = create_test_database(prefix="studyplan_test_b3f2_budget")
    dsn = db.migrator_dsn.replace("postgresql://", "postgresql+psycopg://")
    env = dict(os.environ, STUDYPLAN_MIGRATION_DSN=dsn)
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(BACKEND_DIR), env=env, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    with psycopg.connect(db.migrator_dsn, autocommit=True) as conn:
        conn.execute(
            "INSERT INTO learning_projects(project_id,owner_actor_id,title,goal_statement,stable_key) "
            "VALUES ('budget_p1','budget_a1','t','g','budget_k1')"
        )
    try:
        yield db
    finally:
        db.drop()


@pytest.fixture(autouse=True)
def clean_disposable_budget_database(budget_db: PgTestDatabase) -> None:
    with psycopg.connect(budget_db.migrator_dsn, autocommit=True) as conn:
        conn.execute("TRUNCATE ai_provider_attempts, ai_runs CASCADE")


def insert_run(db: PgTestDatabase, run_id: str) -> None:
    with psycopg.connect(db.migrator_dsn, autocommit=True) as conn:
        conn.execute(
            """INSERT INTO ai_runs
            (run_id,actor_id,project_id,kind,graph_name,graph_version,status,next_action,thread_id,version)
            VALUES (%s,'budget_a1','budget_p1','plan_generate','planning','b3f2-batch-v1','queued','wait',%s,1)""",
            (run_id, f"planning:{run_id}"),
        )


def seed_attempts(db: PgTestDatabase, run_id: str, keys, status: str = "succeeded") -> None:
    with psycopg.connect(db.migrator_dsn, autocommit=True) as conn:
        for key in keys:
            conn.execute(
                "INSERT INTO ai_provider_attempts"
                "(attempt_id,run_id,provider,model_id,prompt_version,status) "
                "VALUES (%s,%s,'mock','mock-model','test',%s)",
                (key, run_id, status),
            )


def _manifest() -> dict:
    return freeze_manifest(domain_pack.load_pack("agent-application-v1.json"), POLICY, "mock:1")


def test_over_cap_dispatch_is_rejected_without_a_provider_call(budget_db: PgTestDatabase) -> None:
    run_id = "budget_run_cap"
    insert_run(budget_db, run_id)
    manifest = _manifest()
    keys = sorted(allowed_attempt_keys(run_id, manifest))
    batch = manifest["structure_batches"][0]
    target = attempt_key(run_id, STRUCTURE_PURPOSE, batch["stage_key"], batch["batch_index"], 0)
    assert target in keys
    seed_attempts(budget_db, run_id, [k for k in keys if k != target][:manifest["max_requests"]])

    provider = CountingProvider()
    llm = PgAttemptLLM(budget_db.app_dsn, provider, manifest=manifest)
    result = llm.generate_structured(
        purpose=STRUCTURE_PURPOSE, payload={"_project_id": "budget_p1"},
        schema_name="KnowledgeStructureV1", run_id=run_id, attempt_id=target,
    )
    assert isinstance(result, LLMFailure)
    assert result.error_class == "run_budget_exhausted"
    assert provider.calls == 0


def test_unregistered_attempt_key_cannot_bypass_the_frozen_catalog(budget_db: PgTestDatabase) -> None:
    run_id = "budget_run_unknown"
    insert_run(budget_db, run_id)
    provider = CountingProvider()
    llm = PgAttemptLLM(budget_db.app_dsn, provider, manifest=_manifest())
    result = llm.generate_structured(
        purpose=STRUCTURE_PURPOSE, payload={"_project_id": "budget_p1"},
        schema_name="KnowledgeStructureV1", run_id=run_id,
        attempt_id=f"{run_id}:b3f2-batch-v1:planning.structure:stage.tools:99:0",
    )
    assert isinstance(result, LLMFailure)
    assert result.error_class == "run_manifest_violation"
    assert provider.calls == 0


def test_tampered_manifest_is_rejected_before_dispatch(budget_db: PgTestDatabase) -> None:
    run_id = "budget_run_tamper"
    insert_run(budget_db, run_id)
    manifest = _manifest()
    manifest["max_requests"] = 999
    provider = CountingProvider()
    llm = PgAttemptLLM(budget_db.app_dsn, provider, manifest=manifest)
    result = llm.generate_structured(
        purpose=OUTLINE_PURPOSE, payload={"_project_id": "budget_p1"},
        schema_name="OutlineV1", run_id=run_id,
        attempt_id=attempt_key(run_id, OUTLINE_PURPOSE, "", 0, 0),
    )
    assert isinstance(result, LLMFailure)
    assert result.error_class == "run_manifest_violation"
    assert provider.calls == 0


def test_successful_replay_is_not_recharged_or_redispatched(budget_db: PgTestDatabase) -> None:
    run_id = "budget_run_replay"
    insert_run(budget_db, run_id)
    provider = CountingProvider()
    llm = PgAttemptLLM(budget_db.app_dsn, provider, manifest=_manifest())
    target = attempt_key(run_id, OUTLINE_PURPOSE, "", 0, 0)
    first = llm.generate_structured(
        purpose=OUTLINE_PURPOSE, payload={"_project_id": "budget_p1"},
        schema_name="OutlineV1", run_id=run_id, attempt_id=target,
    )
    assert isinstance(first, LLMResult)
    assert provider.calls == 1
    second = llm.generate_structured(
        purpose=OUTLINE_PURPOSE, payload={"_project_id": "budget_p1"},
        schema_name="OutlineV1", run_id=run_id, attempt_id=target,
    )
    assert isinstance(second, LLMResult)
    assert provider.calls == 1
    with psycopg.connect(budget_db.migrator_dsn) as conn:
        count = conn.execute(
            "SELECT count(*) FROM ai_provider_attempts WHERE run_id=%s", (run_id,)
        ).fetchone()[0]
    assert count == 1


def test_unknown_or_dispatched_attempts_still_occupy_the_budget(budget_db: PgTestDatabase) -> None:
    run_id = "budget_run_unknown_quota"
    insert_run(budget_db, run_id)
    manifest = _manifest()
    keys = sorted(allowed_attempt_keys(run_id, manifest))
    batch = manifest["structure_batches"][0]
    target = attempt_key(run_id, STRUCTURE_PURPOSE, batch["stage_key"], batch["batch_index"], 0)
    seed_attempts(budget_db, run_id, [k for k in keys if k != target][:manifest["max_requests"]],
                  status="reconciliation_required")
    provider = CountingProvider()
    llm = PgAttemptLLM(budget_db.app_dsn, provider, manifest=manifest)
    result = llm.generate_structured(
        purpose=STRUCTURE_PURPOSE, payload={"_project_id": "budget_p1"},
        schema_name="KnowledgeStructureV1", run_id=run_id, attempt_id=target,
    )
    assert isinstance(result, LLMFailure)
    assert result.error_class == "run_budget_exhausted"
    assert provider.calls == 0
