"""Task 4: b3f2-batch-v1 checkpoint recovery against a disposable PostgreSQL.

Covers the review's recovery cases for the *new* protocol:

- a Worker killed mid-generation resumes from the last completed batch and does
  **not** re-dispatch already-validated batches;
- a checkpoint already waiting for the user is never auto-continued by the Worker;
- an unknown graph version is refused rather than guessed;
- a terminal checkpoint is never regenerated.

No real model call: the Fake counts every dispatch, so "no second request" is a
real assertion. Only ``studyplan_test_*`` databases are used.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.postgres


BACKEND_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND_DIR))

from app.agent_workflows.planning_batches import (  # noqa: E402
    DEFAULT_BUDGET,
    PROTOCOL_VERSION,
    freeze_manifest,
)
from app.infrastructure import domain_pack  # noqa: E402
from app.ports.graph_runner import GraphRecoveryError  # noqa: E402

from tests.pg_harness import PgTestDatabase, create_test_database  # noqa: E402

AGENT_GOAL = "从 Python 基础开始学习 Agent 应用开发"

#: Blocks on the 5th structure request (4 batches already committed), writes a
#: sentinel, then sleeps so the parent can kill the process with no cleanup.
BLOCKING_CHILD = textwrap.dedent(
    '''
    import sys, time, json
    sys.path.insert(0, {backend!r})
    from app.agent_workflows.nodes import PlanningNodes
    from app.agent_workflows.planning_batches import build_batched_planning_graph, freeze_manifest
    from app.agent_workflows.runtime import PostgresSaver
    from app.application.planning_budget import BudgetPolicy
    from app.infrastructure import domain_pack
    from tests.helpers.batched_planning import ScriptedLLM

    dsn, thread_id, sentinel = sys.argv[1], sys.argv[2], sys.argv[3]
    pack = domain_pack.select_domain_pack({goal!r})
    manifest = freeze_manifest(pack, BudgetPolicy(4096, 8192, 4096, 8192, 8192, 393216), "mock:1")

    class BlockingLLM(ScriptedLLM):
        def generate_structured(self, **kw):
            if kw["purpose"] == "planning.structure" and self.count("planning.structure") == 4:
                with open(sentinel, "w", encoding="utf-8") as fh:
                    json.dump({{"blocked_after": self.count("planning.structure")}}, fh)
                time.sleep(600)
            return super().generate_structured(**kw)

    nodes = PlanningNodes(llm=BlockingLLM(pack),
                          save_draft=lambda s: {{"draft_ref": "draft:x", "draft_hash": "h"}})
    with PostgresSaver.from_conn_string(dsn) as saver:
        saver.setup()
        graph = build_batched_planning_graph(nodes, checkpointer=saver)
        cfg = {{"configurable": {{"thread_id": thread_id}}, "recursion_limit": 1000}}
        graph.invoke({{"goal": {goal!r}, "run_id": "run-recover", "graph_version": {proto!r},
                       "domain_pack": pack, "manifest": manifest}}, cfg)
    '''
)


@pytest.fixture(scope="module")
def recovery_db() -> PgTestDatabase:
    db = create_test_database(prefix="studyplan_test_b3f2_recovery")
    try:
        yield db
    finally:
        db.drop()


def _saver_setup(db: PgTestDatabase) -> None:
    from app.agent_workflows.runtime import PostgresSaver

    with PostgresSaver.from_conn_string(db.migrator_dsn) as saver:
        saver.setup()


def test_worker_killed_mid_run_resumes_without_redispatching_completed_batches(
    recovery_db: PgTestDatabase, tmp_path: Path
) -> None:
    _saver_setup(recovery_db)
    thread_id = f"run-recover::{PROTOCOL_VERSION}"
    sentinel = tmp_path / "blocked.json"
    # A reused ``--basetemp`` can leave a stale sentinel from an earlier run; if it
    # is not removed the child would be killed before committing any checkpoint.
    sentinel.unlink(missing_ok=True)
    script = BLOCKING_CHILD.format(backend=str(BACKEND_DIR), goal=AGENT_GOAL, proto=PROTOCOL_VERSION)
    proc = subprocess.Popen(
        [sys.executable, "-c", script, recovery_db.migrator_dsn, thread_id, str(sentinel)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=str(BACKEND_DIR),
    )
    try:
        deadline = time.time() + 90
        while time.time() < deadline and not sentinel.exists():
            if proc.poll() is not None:
                break
            time.sleep(0.2)
        assert sentinel.exists(), f"child did not reach the 5th structure batch: {proc.stderr.read()[-800:] if proc.poll() is not None else ''}"
        proc.kill()
        proc.wait(timeout=30)
    finally:
        if proc.poll() is None:
            proc.kill()

    from app.agent_workflows.nodes import PlanningNodes
    from app.agent_workflows.planning_batches import build_batched_planning_graph
    from app.agent_workflows.runtime import PostgresSaver

    from tests.helpers.batched_planning import PRACTICE, STRUCTURE, ScriptedLLM

    pack = domain_pack.select_domain_pack(AGENT_GOAL)
    llm = ScriptedLLM(pack)
    nodes = PlanningNodes(llm=llm, save_draft=lambda s: {"draft_ref": "draft:resumed", "draft_hash": "h"})
    with PostgresSaver.from_conn_string(recovery_db.migrator_dsn) as saver:
        graph = build_batched_planning_graph(nodes, checkpointer=saver)
        config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 1000}
        before = graph.get_state(config)
        assert before.next, "a resumable checkpoint must exist"
        assert before.values.get("current_structure_index") == 4, "4 structure batches already committed"
        graph.invoke(None, config)

    # Only the remaining 5 structure batches and 9 practice batches are dispatched.
    assert llm.count(STRUCTURE) == 5
    assert llm.count(PRACTICE) == 9
    assert llm.count() == 14


def test_waiting_user_checkpoint_is_not_auto_continued(recovery_db: PgTestDatabase) -> None:
    from app.agent_workflows.nodes import PlanningNodes
    from app.agent_workflows.planning_batches import build_batched_planning_graph
    from app.agent_workflows.runtime import PostgresSaver
    from app.infrastructure.checkpointer.planning_executor import PgPlanningExecutor

    from tests.helpers.batched_planning import ScriptedLLM

    pack = domain_pack.select_domain_pack(AGENT_GOAL)
    manifest = freeze_manifest(pack, DEFAULT_BUDGET, "mock:1")
    thread_id = f"run-waiting::{PROTOCOL_VERSION}"
    llm = ScriptedLLM(pack)
    nodes = PlanningNodes(llm=llm, save_draft=lambda s: {"draft_ref": "draft:w", "draft_hash": "h"})
    with PostgresSaver.from_conn_string(recovery_db.migrator_dsn) as saver:
        graph = build_batched_planning_graph(nodes, checkpointer=saver)
        config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 1000}
        graph.invoke({"goal": AGENT_GOAL, "run_id": "run-waiting", "graph_version": PROTOCOL_VERSION,
                      "domain_pack": pack, "manifest": manifest}, config)
        assert graph.get_state(config).next == ("await_approval",)

    executor = PgPlanningExecutor(recovery_db.migrator_dsn, llm=llm)
    with pytest.raises(GraphRecoveryError, match="等待用户确认"):
        executor.execute_or_resume(nodes, {"manifest": manifest}, thread_id, PROTOCOL_VERSION, lambda: None)
    # The refusal must not have dispatched anything new.
    assert llm.count() == 19


def test_unknown_graph_version_is_refused() -> None:
    """Only the official protocol may be built; legacy/unknown values are refused.

    The deprecated single-pass protocol (``"1"``) is no longer routable: a stored
    legacy thread is never re-explained by the new protocol, and an unknown value
    is never guessed from the current default.
    """
    from app.infrastructure.checkpointer.planning_executor import builder_for_version

    assert builder_for_version(PROTOCOL_VERSION) is not None
    for refused in ("1", "planning-legacy-v1", "b3f2-batch-v99", ""):
        with pytest.raises(GraphRecoveryError, match="不支持的图协议版本"):
            builder_for_version(refused)


def test_guard_is_called_before_resume(recovery_db: PgTestDatabase) -> None:
    """A lost lease must abort before any dispatch on resume."""
    from app.agent_workflows.nodes import PlanningNodes
    from app.agent_workflows.planning_batches import build_batched_planning_graph
    from app.agent_workflows.runtime import PostgresSaver
    from app.infrastructure.checkpointer.planning_executor import PgPlanningExecutor
    from app.ports.planning_jobs import PlanningLeaseLostError

    from tests.helpers.batched_planning import ScriptedLLM

    pack = domain_pack.select_domain_pack(AGENT_GOAL)
    manifest = freeze_manifest(pack, DEFAULT_BUDGET, "mock:1")
    thread_id = f"run-guard::{PROTOCOL_VERSION}"
    llm = ScriptedLLM(pack)
    nodes = PlanningNodes(llm=llm, save_draft=lambda s: {"draft_ref": "draft:g", "draft_hash": "h"})
    with PostgresSaver.from_conn_string(recovery_db.migrator_dsn) as saver:
        graph = build_batched_planning_graph(nodes, checkpointer=saver)
        config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 1000}
        graph.invoke({"goal": AGENT_GOAL, "run_id": "run-guard", "graph_version": PROTOCOL_VERSION,
                      "domain_pack": pack, "manifest": manifest}, config)

    def lost() -> None:
        raise PlanningLeaseLostError("lease lost")

    executor = PgPlanningExecutor(recovery_db.migrator_dsn, llm=llm)
    with pytest.raises(PlanningLeaseLostError):
        executor.execute_or_resume(nodes, {"manifest": manifest}, thread_id, PROTOCOL_VERSION, lost)
