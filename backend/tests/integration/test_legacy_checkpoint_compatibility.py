"""Task 4: the new program confirms/cancels *real* 39e79ad checkpoints.

The legacy waiting_user checkpoints here are produced by the **actual pre-Task-1
code** (commit ``39e79ad``), extracted into a throwaway tree and executed in a
child process. A new graph that merely imitates the old state shape is not
evidence, so the source hashes are pinned in the report.

Scope of this file: the executor-level compatibility contract — the new program
resumes the old thread under its stored version, reaches a terminal state, adds
zero model calls, and leaves the legacy draft hash and graph version untouched.
Business-level publication idempotency (one publication per approval, cancel
publishes nothing) is covered by ``backend/tests/unit/test_plan_publication.py``
and ``backend/tests/e2e/test_b3_closed_loop.py``.

Only a disposable ``studyplan_test_*`` database is used.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.postgres

psycopg = pytest.importorskip("psycopg")
pytest.importorskip("langgraph")

BACKEND_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND_DIR))

from app.agent_workflows.runtime import PostgresSaver  # noqa: E402
from app.infrastructure.checkpointer.planning_executor import PgPlanningExecutor  # noqa: E402
from app.ports.graph_runner import GraphRecoveryError  # noqa: E402

from tests.helpers.legacy_planning_checkpoint import (  # noqa: E402
    LEGACY_COMMIT,
    export_legacy_source,
    run_legacy_child,
)
from tests.pg_harness import PgTestDatabase, create_test_database  # noqa: E402


class CountingLLM:
    """Port-shaped LLM that must never be called during legacy acknowledgement."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def generate_structured(self, *, purpose, payload, schema_name, run_id, attempt_id):
        self.calls.append(purpose)
        raise AssertionError("legacy acknowledgement must not call the model")


@pytest.fixture(scope="module")
def legacy_source(tmp_path_factory: pytest.TempPathFactory):
    dest = tmp_path_factory.mktemp("legacy_source")
    return export_legacy_source(dest, repo_root=BACKEND_DIR.parent)


@pytest.fixture(scope="module")
def legacy_db() -> PgTestDatabase:
    db = create_test_database(prefix="studyplan_test_legacy_ckpt")
    try:
        yield db
    finally:
        db.drop()


def _thread_state(dsn: str, thread_id: str) -> dict:
    with PostgresSaver.from_conn_string(dsn) as saver:
        saved = saver.get_tuple({"configurable": {"thread_id": thread_id}})
        assert saved is not None, "checkpoint must exist"
        return dict(saved.checkpoint["channel_values"])


def _make_legacy_checkpoint(legacy_source, db: PgTestDatabase, tmp_path: Path, thread_id: str) -> dict:
    out_path = tmp_path / f"{thread_id.replace(':', '_')}.json"
    info = run_legacy_child(legacy_source, dsn=db.migrator_dsn, thread_id=thread_id, out_path=out_path)
    assert info["next"] == ["await_approval"], "legacy run must stop waiting for the user"
    assert info["graph_version"] == "1"
    assert info["model_calls"] == 3
    return info


def test_legacy_approve_is_acknowledged_without_regeneration(
    legacy_source, legacy_db: PgTestDatabase, tmp_path: Path
) -> None:
    thread_id = "run-legacy-approve::1"
    info = _make_legacy_checkpoint(legacy_source, legacy_db, tmp_path, thread_id)

    llm = CountingLLM()
    executor = PgPlanningExecutor(legacy_db.migrator_dsn, llm=llm)
    executor.finish(thread_id=thread_id, graph_version="1", decision="approve",
                    result_id="plan:legacy", draft_hash=info["draft_hash"])

    values = _thread_state(legacy_db.migrator_dsn, thread_id)
    assert values["graph_version"] == "1", "legacy graph version must not change"
    assert values["draft_hash"] == "hash:legacy", "legacy draft hash must not change"
    assert values["draft_ref"] == "draft:legacy"
    assert values["result_id"] == "plan:legacy"
    assert llm.calls == [], "no model call during legacy acknowledgement"

    # Repeated acknowledgement is a no-op, not a second publish.
    executor.finish(thread_id=thread_id, graph_version="1", decision="approve",
                    result_id="plan:legacy", draft_hash=info["draft_hash"])
    assert _thread_state(legacy_db.migrator_dsn, thread_id)["result_id"] == "plan:legacy"
    assert llm.calls == []


def test_legacy_cancel_publishes_nothing(
    legacy_source, legacy_db: PgTestDatabase, tmp_path: Path
) -> None:
    thread_id = "run-legacy-cancel::1"
    info = _make_legacy_checkpoint(legacy_source, legacy_db, tmp_path, thread_id)

    llm = CountingLLM()
    executor = PgPlanningExecutor(legacy_db.migrator_dsn, llm=llm)
    executor.finish(thread_id=thread_id, graph_version="1", decision="cancel",
                    result_id="", draft_hash=info["draft_hash"])

    values = _thread_state(legacy_db.migrator_dsn, thread_id)
    assert values["graph_version"] == "1"
    assert values["draft_hash"] == "hash:legacy"
    assert values.get("result_id", "") == "", "cancel must not publish a plan"
    assert values["decision"] == "cancel"
    assert llm.calls == []


def test_legacy_checkpoint_is_not_reinterpreted_by_the_new_protocol(
    legacy_source, legacy_db: PgTestDatabase, tmp_path: Path
) -> None:
    """The stored version selects the legacy builder; the batched graph never runs."""
    thread_id = "run-legacy-version::1"
    _make_legacy_checkpoint(legacy_source, legacy_db, tmp_path, thread_id)

    llm = CountingLLM()
    executor = PgPlanningExecutor(legacy_db.migrator_dsn, llm=llm)
    # Asking for a different (unknown) version must be refused, never guessed.
    with pytest.raises(GraphRecoveryError, match="未知图版本"):
        executor.finish(thread_id=thread_id, graph_version="b3f2-batch-v99", decision="approve",
                        result_id="plan:legacy", draft_hash="hash:legacy")
    values = _thread_state(legacy_db.migrator_dsn, thread_id)
    assert values["graph_version"] == "1"
    assert llm.calls == []


def test_legacy_source_is_pinned_to_the_pre_task_commit(legacy_source) -> None:
    assert LEGACY_COMMIT == "39e79ad"
    assert set(legacy_source.hashes) == {
        "backend/app/agent_workflows/graphs.py",
        "backend/app/agent_workflows/nodes.py",
        "backend/app/agent_workflows/state.py",
        "backend/app/agent_workflows/validators.py",
    }
    assert all(len(digest) == 64 for digest in legacy_source.hashes.values())
