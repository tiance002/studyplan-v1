"""Task 7 (B3-F2): independent Fake end-to-end acceptance of ``b3f2-batch-v1``.

One disposable PostgreSQL, a deterministic Fake provider and the **real** LangGraph
executor, driven over the real HTTP routes. The new protocol only.

Covers, per the design revision:

1. full short generation -> ``succeeded`` + awaiting business draft -> approve -> publish, with a
   business-only, complete ``RunProgress``;
2. the submission frozen at enqueue (protocol + model descriptor + manifest hash
   + request/output budget);
3. checkpoint interruption recovery that does **not** re-dispatch already
   committed batches;
4. a ``waiting_user`` checkpoint is never auto-continued by the Worker;
5. cancel is a terminal, idempotent decision;
6. legacy / unknown protocols are explicitly refused (builder **and** service guard).

Only ``studyplan_test_*`` databases are used; each is dropped afterwards.
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import psycopg
import pytest

pytestmark = pytest.mark.postgres

BACKEND_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND_DIR))

from app.agent_workflows.nodes import PlanningNodes  # noqa: E402
from app.agent_workflows.planning_batches import (  # noqa: E402
    PROTOCOL_VERSION,
    manifest_is_intact,
)
from app.application.plan_service import PlanService  # noqa: E402
from app.composition import build_container  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.core.errors import ValidationAppError  # noqa: E402
from app.infrastructure.checkpointer.planning_executor import (  # noqa: E402
    PgPlanningExecutor,
    builder_for_version,
)
from app.infrastructure.domain_pack import load_pack  # noqa: E402
from app.infrastructure.providers.fake import FakeLLM  # noqa: E402
from app.ports.graph_runner import GraphRecoveryError  # noqa: E402

from tests.helpers.batched_planning import PRACTICE, STRUCTURE, ScriptedLLM  # noqa: E402
from tests.helpers.planning_worker import configure_test_worker  # noqa: E402
from tests.pg_harness import PgTestDatabase, create_test_database  # noqa: E402

AGENT_GOAL = "从 Python 基础学习 Agent 应用开发"
AGENT_PACK = "agent-application-v3.json"
#: 9 stages -> 1 outline + 9 structure + 9 practice = 19 requests; max 21 with 2 repairs.
EXPECTED_REQUESTS = 19
MAX_REQUESTS = 21
MAX_OUTPUT_BUDGET = 131072


# --------------------------------------------------------------------- fixtures


def _migrate(db: PgTestDatabase) -> None:
    dsn = db.migrator_dsn.replace("postgresql://", "postgresql+psycopg://")
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(BACKEND_DIR),
        env=dict(os.environ, STUDYPLAN_MIGRATION_DSN=dsn),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"alembic upgrade 失败：{result.stderr}"


@pytest.fixture(scope="module")
def agent_db() -> PgTestDatabase:
    """A disposable business DB with the reviewed Agent pack seeded."""
    from app.tools.seed_b3 import seed_reviewed_pack

    db = create_test_database(prefix="studyplan_test_b3f2_e2e")
    try:
        _migrate(db)
        with psycopg.connect(db.migrator_dsn, autocommit=True) as conn:
            seed_reviewed_pack(conn, load_pack(AGENT_PACK))
        yield db
    finally:
        db.drop()


@pytest.fixture(scope="module")
def checkpoint_db() -> PgTestDatabase:
    """A disposable, separate checkpoint DB (never the business DB)."""
    from app.agent_workflows.runtime import PostgresSaver

    db = create_test_database(prefix="studyplan_test_b3f2_e2e_cp")
    try:
        with PostgresSaver.from_conn_string(db.migrator_dsn) as saver:
            saver.setup()
        yield db
    finally:
        db.drop()


# ----------------------------------------------------------------------- client


def _client(agent_db: PgTestDatabase, checkpoint_db: PgTestDatabase):
    """Real container + real LangGraph executor + TestClient over a disposable PG."""
    from app.main import create_app
    from fastapi.testclient import TestClient

    settings = replace(
        get_settings(),
        database_url=agent_db.app_dsn,
        llm_provider="fake",
        local_session_token="",
    )
    container = build_container(settings)
    container.plan_service._executor = PgPlanningExecutor(
        checkpoint_db.migrator_dsn, llm=container.plan_service._llm
    )
    # NOTE: the worker is configured *after* registration — its allowlist is
    # derived from the actor's session cookie, which does not exist yet here.
    return TestClient(create_app(container))


def _register(client, username: str) -> dict:
    response = client.post(
        "/api/v1/auth/register", json={"username": username, "password": "Test-pass1!"}
    )
    assert response.status_code == 200, response.text
    return response.json()


def _scope(session: dict) -> tuple[str, dict]:
    project = session["project_ids"][0]
    return f"?project_id={project}", {"X-CSRF-Token": session["csrf_token"]}


def _fake(client):
    """The in-process Fake provider, for counting real dispatches."""
    return client.app.state.container.plan_service._llm


def _generate_to_run(client, session, goal=AGENT_GOAL) -> tuple[str, str, dict]:
    """Configure the worker, generate, drive it once; return ``(run_id, suffix, headers)``."""
    # The worker allowlist is derived from the session cookie, so it must be
    # configured *before* the generate call (which checks the allowlist).
    worker = configure_test_worker(client)
    suffix, headers = _scope(session)
    created = client.post(
        "/api/v1/plans/generate" + suffix, json={"goal": goal}, headers=headers
    )
    assert created.status_code == 202, created.text
    assert worker.tick()
    return created.json()["run_id"], suffix, headers


# ------------------------------------------------------------------- 1. happy path


def test_full_batched_generation_succeeds_with_awaiting_draft_and_publishes(agent_db, checkpoint_db):
    client = _client(agent_db, checkpoint_db)
    session = _register(client, "e2e完整路线")
    run_id, suffix, headers = _generate_to_run(client, session)

    run = client.get("/api/v1/runs/" + run_id + suffix).json()
    assert run["status"] == "succeeded", run
    assert run["next_action"] == "none"
    progress = run["progress"]
    assert progress["phase"] == "done"
    assert progress["total_stages"] == 9
    assert progress["completed_structure_batches"] == 9
    assert progress["completed_practice_batches"] == 9
    assert progress["completed_batches"] == 18
    assert progress["max_requests"] == MAX_REQUESTS
    # The in-process Fake writes no paid-attempt ledger, so the ledger-backed
    # counter stays 0 and usage stays unknown (never fabricated into a number).
    assert progress["request_count"] == 0
    assert progress["input_tokens"] is None and progress["output_tokens"] is None
    assert progress["usage_complete"] is False
    # The real dispatch count is proven by the Fake itself: 1 outline + 9 + 9.
    dispatched = [call[2] for call in _fake(client).calls]
    assert dispatched == (["planning.outline"] + ["planning.structure"] * 9 + ["planning.practice"] * 9)
    assert len(dispatched) == EXPECTED_REQUESTS
    # No graph internals are exposed.
    assert not ({"thread_id", "checkpoint", "node_name"} & set(progress))

    draft = client.get("/api/v1/plans/drafts/" + run["result_ref"] + suffix).json()
    assert len(draft["stages"]) == 9
    assert draft["source_pack_key"] == "agent.application"
    assert draft["status"] == "awaiting_approval"

    approved = client.post(
        "/api/v1/plans/drafts/" + run["result_ref"] + "/decision" + suffix,
        json={
            "decision": "approve",
            "expected_version": 0,
            "draft_hash": draft["draft_hash"],
            "idempotency_key": "e2e-approve",
        },
        headers=headers,
    )
    assert approved.status_code == 200, approved.text
    published = approved.json()["plan"]
    assert published["revision"] == 1
    assert client.get("/api/v1/plans/current" + suffix).json() == published
    assert client.get("/api/v1/runs/" + run_id + suffix).json()["status"] == "succeeded"
    assert client.get("/api/v1/runs/" + run_id + suffix).json()['result_ref'] == draft['draft_id']


# --------------------------------------------------- 2. frozen submission + budget


def test_submission_freezes_protocol_model_and_manifest(agent_db, checkpoint_db):
    client = _client(agent_db, checkpoint_db)
    session = _register(client, "e2e冻结清单")
    run_id, suffix, _ = _generate_to_run(client, session)

    with psycopg.connect(agent_db.migrator_dsn) as conn:
        conn.execute("SELECT set_config('app.project_id', %s, true)", (session["project_ids"][0],))
        submission = conn.execute(
            "SELECT detail FROM ai_run_events WHERE run_id = %s AND status = 'submission' "
            "AND detail->>'kind' = 'planning_submission'",
            (run_id,),
        ).fetchone()
    detail = submission[0]
    initial, manifest = detail["initial"], detail["manifest"]
    assert initial["protocol"] == PROTOCOL_VERSION
    from app.agent_workflows.planning_batches import SHORT_GENERATION_VERSION
    assert initial["graph_version"] == SHORT_GENERATION_VERSION
    assert initial["manifest"]["protocol"] == PROTOCOL_VERSION
    assert manifest["protocol"] == PROTOCOL_VERSION
    assert manifest["model_ref"]  # a frozen, non-secret descriptor
    assert manifest["max_requests"] == MAX_REQUESTS
    assert manifest["max_output_budget"] == MAX_OUTPUT_BUDGET
    assert manifest["structure_batches_count"] == 9
    assert manifest["practice_batches_count"] == 9
    # The manifest hash detects any post-freeze tampering.
    assert manifest_is_intact(manifest)
    tampered = {**manifest, "max_requests": 999}
    assert not manifest_is_intact(tampered)


# ------------------------------------------- 3. interruption recovery (no re-dispatch)


class _WorkerKilled(BaseException):
    """Simulates a killed Worker: escapes ``except Exception`` and leaves the checkpoint."""


class _KillAt(ScriptedLLM):
    def __init__(self, pack, purpose: str, kill_occurrence: int) -> None:
        super().__init__(pack)
        self._purpose = purpose
        self._kill_occurrence = kill_occurrence

    def generate_structured(self, **kwargs):
        if kwargs["purpose"] == self._purpose and self.count(self._purpose) + 1 == self._kill_occurrence:
            self.calls.append({"purpose": kwargs["purpose"]})  # count the blocked dispatch
            raise _WorkerKilled()
        return super().generate_structured(**kwargs)


def test_interrupted_run_resumes_without_recalling_completed_batches(checkpoint_db):
    from app.agent_workflows.planning_batches import freeze_manifest
    from app.infrastructure import domain_pack

    pack = domain_pack.select_domain_pack(AGENT_GOAL)
    manifest = freeze_manifest(pack, _budget(), "fake:planning-demo")
    thread_id = f"e2e-recover::{PROTOCOL_VERSION}"
    initial = {
        "goal": AGENT_GOAL, "run_id": "e2e-recover", "graph_version": PROTOCOL_VERSION,
        "domain_pack": pack, "manifest": manifest,
    }
    save = lambda s: {"draft_ref": "draft:e2e", "draft_hash": "h"}  # noqa: E731

    # First attempt: killed while dispatching the 5th structure batch (4 committed).
    first = _KillAt(pack, STRUCTURE, 5)
    with pytest.raises(_WorkerKilled):
        PgPlanningExecutor(checkpoint_db.migrator_dsn, llm=first).execute_or_resume(
            PlanningNodes(llm=first, save_draft=save), initial, thread_id, PROTOCOL_VERSION, lambda: None
        )
    assert first.count(STRUCTURE) == 5  # 4 completed + the one that was killed

    # Resume: only the remaining 5 structure and 9 practice batches are dispatched.
    second = ScriptedLLM(pack)
    trace = PgPlanningExecutor(checkpoint_db.migrator_dsn, llm=second).execute_or_resume(
        PlanningNodes(llm=second, save_draft=save), {"manifest": manifest}, thread_id,
        PROTOCOL_VERSION, lambda: None,
    )
    assert trace.stopped_at == "await_approval"
    assert second.count(STRUCTURE) == 5
    assert second.count(PRACTICE) == 9
    assert second.count() == 14


# --------------------------------------------- 4. waiting_user is never auto-continued


def test_waiting_user_checkpoint_is_not_auto_continued(checkpoint_db):
    from app.agent_workflows.planning_batches import freeze_manifest
    from app.infrastructure import domain_pack

    pack = domain_pack.select_domain_pack(AGENT_GOAL)
    manifest = freeze_manifest(pack, _budget(), "fake:planning-demo")
    thread_id = f"e2e-waiting::{PROTOCOL_VERSION}"
    llm = ScriptedLLM(pack)
    nodes = PlanningNodes(llm=llm, save_draft=lambda s: {"draft_ref": "draft:w", "draft_hash": "h"})
    executor = PgPlanningExecutor(checkpoint_db.migrator_dsn, llm=llm)
    executor.execute_or_resume(
        nodes,
        {"goal": AGENT_GOAL, "run_id": "e2e-waiting", "graph_version": PROTOCOL_VERSION,
         "domain_pack": pack, "manifest": manifest},
        thread_id, PROTOCOL_VERSION, lambda: None,
    )
    assert llm.count() == EXPECTED_REQUESTS

    # A second call must refuse to continue a checkpoint that is waiting for the user.
    with pytest.raises(GraphRecoveryError, match="等待用户确认"):
        executor.execute_or_resume(nodes, {"manifest": manifest}, thread_id, PROTOCOL_VERSION, lambda: None)
    assert llm.count() == EXPECTED_REQUESTS  # nothing new was dispatched


# --------------------------------------------------------------- 5. cancel is terminal


def test_cancel_is_terminal_and_idempotent(agent_db, checkpoint_db):
    client = _client(agent_db, checkpoint_db)
    session = _register(client, "e2e取消草案")
    run_id, suffix, headers = _generate_to_run(client, session)
    run = client.get("/api/v1/runs/" + run_id + suffix).json()
    draft_id = run["result_ref"]
    draft = client.get("/api/v1/plans/drafts/" + draft_id + suffix).json()

    body = {"decision": "cancel", "expected_version": 0, "draft_hash": draft["draft_hash"]}
    cancelled = client.post("/api/v1/plans/drafts/" + draft_id + "/decision" + suffix, json=body, headers=headers)
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["draft"]["status"] == "cancelled"
    # A cancelled draft can never be published afterwards.
    approved = client.post(
        "/api/v1/plans/drafts/" + draft_id + "/decision" + suffix,
        json={
            "decision": "approve",
            "expected_version": 0,
            "draft_hash": draft["draft_hash"],
            "idempotency_key": "e2e-cancel-then-approve",
        },
        headers=headers,
    )
    assert approved.status_code == 409, approved.text


# ------------------------------------------------- 6. legacy / unknown protocols refused


def test_legacy_and_unknown_protocols_are_refused(agent_db):
    assert builder_for_version(PROTOCOL_VERSION) is not None
    for refused in ("1", "planning-legacy-v1", "b3f2-batch-v99", ""):
        with pytest.raises(GraphRecoveryError, match="不支持的图协议版本"):
            builder_for_version(refused)

    # The service refuses to even start with a legacy configured version.
    settings = replace(get_settings(), database_url=agent_db.app_dsn, llm_provider="fake")
    container = build_container(settings)
    service = container.plan_service
    with pytest.raises(ValidationAppError, match="不是受支持的生成协议"):
        PlanService(
            repository=service._repo, runs=service._runs, catalog=service._catalog,
            resources=service._resources, llm=FakeLLM({}), graph_version="1",
        )


# ------------------------------------------------------------------------ helpers


def _budget():
    from app.application.planning_budget import BudgetPolicy

    return BudgetPolicy(4096, 8192, 4096, 8192, 8192, 393216)
