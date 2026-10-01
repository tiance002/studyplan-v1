"""HTTP submission returns while the explicitly started worker owns generation.

Covers the B3-F2 Task 5 contract: the new ``b3f2-batch-v1`` protocol is the only
one enqueued, and ``GET /runs/{id}`` exposes a **business** progress projection
(per-batch, no graph internals, no fabricated metrics).
"""

from __future__ import annotations

import threading

import pytest
from app.infrastructure.providers.fake import FakeLLM

from tests.e2e.test_b2v_http_end_to_end import (
    GOAL_A,
    PROJECT_P1,
    V1,
    _client,
    _get_run,
    _outline_handler,
    _practice_handler,
    _structure_handler,
    migrated_db,  # noqa: F401 - imported fixture dependency for db
)
from tests.e2e.test_b2v_http_end_to_end import (
    db as db,
)

pytestmark = pytest.mark.postgres

#: Fields that must never appear in an authorised run payload.
_GRAPH_INTERNALS = frozenset(
    {"thread_id", "graph_version", "node_name", "nodes", "checkpoint", "prompt", "stage_key", "attempt_id"}
)


def test_http_queues_without_call_then_worker_generates(db) -> None:
    entered = threading.Event()
    release = threading.Event()

    def blocking_outline(purpose, payload):
        entered.set()
        assert release.wait(10), "test must release the Fake model"
        return _outline_handler(purpose, payload)

    llm = FakeLLM({
        "planning.outline": blocking_outline,
        "planning.structure": _structure_handler,
        "planning.practice": _practice_handler,
    })
    client = _client(db, llm=llm)
    try:
        response = client.post(
            f"{V1}/plans/generate", params={"project_id": PROJECT_P1},
            json={"goal": GOAL_A, "prefs_snapshot": {"mode": "text_first", "language": "zh"}},
        )
        assert response.status_code == 202, response.text
        run_id = response.json()["run_id"]
        assert llm.calls == []
        assert _get_run(client, run_id)["status"] == "queued"

        worker = client.app.state.container.planning_worker
        work = threading.Thread(target=worker.tick)
        work.start()
        assert entered.wait(5), "worker did not reach the Fake model"

        # A second request completes while the first run is blocked in its model call.
        second = client.post(
            f"{V1}/plans/generate", params={"project_id": PROJECT_P1},
            json={"goal": GOAL_A + " second", "prefs_snapshot": {"mode": "text_first", "language": "zh"}},
        )
        assert second.status_code == 202, second.text
        assert _get_run(client, run_id)["status"] == "running"
    finally:
        release.set()
        if "work" in locals():
            work.join(15)
            assert not work.is_alive()
        client.close()

    assert any(call[0] == run_id for call in llm.calls)


def test_old_worker_returning_after_lease_loss_cannot_dispatch_or_save_draft(db) -> None:
    import psycopg
    from app.infrastructure.db.job_repository import PgPlanningJobRepository

    from tests.e2e.test_b2v_http_end_to_end import ACTOR_A1, _client

    entered, release = threading.Event(), threading.Event()

    def blocked(purpose, payload):
        entered.set()
        assert release.wait(10)
        return _outline_handler(purpose, payload)

    llm = FakeLLM({"planning.outline": blocked, "planning.structure": _structure_handler,
                   "planning.practice": _practice_handler})
    with _client(db, llm=llm) as client:
        response = client.post(f"{V1}/plans/generate", params={"project_id": PROJECT_P1}, json={"goal": GOAL_A})
        assert response.status_code == 202
        run_id = response.json()["run_id"]
        worker_thread = threading.Thread(target=client.app.state.container.planning_worker.tick)
        worker_thread.start()
        try:
            assert entered.wait(5)
            with psycopg.connect(db.migrator_dsn) as conn:
                conn.execute("UPDATE ai_jobs SET lease_expires_at=now()-interval '1 second' WHERE run_id=%s", (run_id,))
            replacement = PgPlanningJobRepository(db.app_dsn, actor_ids=(ACTOR_A1,))
            claim = replacement.claim(PROJECT_P1, "replacement", 30)
            assert claim is not None
        finally:
            release.set()
            worker_thread.join(15)
        assert not worker_thread.is_alive()
        assert len(llm.calls) == 1
        assert _get_run(client, run_id)["status"] == "running"
        with psycopg.connect(db.migrator_dsn) as conn:
            assert conn.execute("SELECT count(*) FROM plan_drafts WHERE run_id=%s", (run_id,)).fetchone()[0] == 0
        assert replacement.check_claim(claim)


# ------------------------------------------------------- Task 5 业务进度投影


def test_progress_is_per_batch_and_never_exposes_graph_internals(db) -> None:
    """GET 逐批进度：queued → running（结构/实践批次）→ succeeded；无图内部字段。"""
    entered = threading.Event()
    release = threading.Event()

    def blocking_practice(purpose, payload):
        if payload["stage"]["stable_key"] == "stage.core":
            entered.set()
            assert release.wait(10), "test must release the Fake model"
        return _practice_handler(purpose, payload)

    llm = FakeLLM({
        "planning.outline": _outline_handler,
        "planning.structure": _structure_handler,
        "planning.practice": blocking_practice,
    })
    with _client(db, llm=llm) as client:
        response = client.post(
            f"{V1}/plans/generate", params={"project_id": PROJECT_P1},
            json={"goal": GOAL_A, "prefs_snapshot": {"mode": "text_first", "language": "zh"}},
        )
        assert response.status_code == 202, response.text
        run_id = response.json()["run_id"]

        # queued：尚无任何已提交批次，因此没有进度事件。
        queued = _get_run(client, run_id)
        assert queued["status"] == "queued"
        assert queued["progress"] is None
        assert llm.calls == [], "GET must never call the model"

        work = threading.Thread(target=client.app.state.container.planning_worker.tick)
        work.start()
        try:
            assert entered.wait(10), "worker did not reach the second practice batch"
            calls_before = len(llm.calls)
            mid = _get_run(client, run_id)
            assert len(llm.calls) == calls_before, "GET must never call the model"

            assert mid["status"] == "running", mid
            progress = mid["progress"]
            assert progress is not None
            # 2 structure batches committed, 1 practice batch committed, second in flight.
            assert progress["phase"] == "practice"
            assert progress["total_stages"] == 2
            assert progress["completed_structure_batches"] == 2
            assert progress["total_structure_batches"] == 2
            assert progress["completed_practice_batches"] == 1
            assert progress["total_practice_batches"] == 2
            assert progress["completed_batches"] == 3
            assert progress["current_stage_index"] == 1
            assert progress["current_stage_title"].startswith("核心实现")
            # 1 skeleton + 2 structure + 2 practice + at most 2 repairs.
            assert progress["max_requests"] == 7
            assert progress["failure_phase"] == "" and progress["failure_stage"] == ""
            assert not (_GRAPH_INTERNALS & set(progress)), progress
        finally:
            release.set()
            work.join(20)
            assert not work.is_alive()

        final = _get_run(client, run_id)
        assert final["status"] == "succeeded"
        assert final["progress"]["phase"] == "done"
        assert final["progress"]["completed_batches"] == 4
        assert final["progress"]["completed_structure_batches"] == 2
        assert final["progress"]["completed_practice_batches"] == 2
        assert not (_GRAPH_INTERNALS & set(final["progress"])), final["progress"]
        assert not (_GRAPH_INTERNALS & set(final)), final


def test_progress_keeps_unknown_usage_null_and_reports_no_paid_attempts(db) -> None:
    """未记录付费计量时保持 NULL，绝不用 0 冒充；``usage_complete`` 为 False。"""
    llm = FakeLLM({
        "planning.outline": _outline_handler,
        "planning.structure": _structure_handler,
        "planning.practice": _practice_handler,
    })
    with _client(db, llm=llm) as client:
        response = client.post(
            f"{V1}/plans/generate", params={"project_id": PROJECT_P1}, json={"goal": GOAL_A}
        )
        run_id = response.json()["run_id"]
        assert client.app.state.container.planning_worker.tick()
        progress = _get_run(client, run_id)["progress"]

    assert progress is not None
    # The in-process Fake writes no paid attempts, so the ledger subtotal is empty.
    assert progress["request_count"] == 0
    assert progress["input_tokens"] is None, "missing usage must stay NULL, never 0"
    assert progress["output_tokens"] is None
    assert progress["usage_complete"] is False


def test_failed_run_reports_business_failure_location(db) -> None:
    """失败运行只暴露业务失败位置（阶段/阶段类型），不暴露图节点名。"""
    def empty_structure(purpose, payload):
        if payload["stage"]["stable_key"] == "stage.core":
            return {"nodes": [], "units": [], "relations": []}
        return _structure_handler(purpose, payload)

    llm = FakeLLM({
        "planning.outline": _outline_handler,
        "planning.structure": empty_structure,
        "planning.practice": _practice_handler,
    })
    with _client(db, llm=llm) as client:
        response = client.post(
            f"{V1}/plans/generate", params={"project_id": PROJECT_P1}, json={"goal": GOAL_A}
        )
        run_id = response.json()["run_id"]
        assert client.app.state.container.planning_worker.tick()
        view = _get_run(client, run_id)

    assert view["status"] == "failed", view
    assert view["next_action"] == "retry"
    assert view["error"]["code"] == "planning_failed"
    progress = view["progress"]
    assert progress is not None
    assert progress["failure_phase"] == "structure"
    assert progress["failure_stage"] == "stage.core"
    assert progress["completed_structure_batches"] == 1
    assert not (_GRAPH_INTERNALS & set(progress)), progress


def test_run_without_progress_returns_null_progress(db) -> None:
    """没有进度事件的运行（例如历史数据）返回 ``progress: null``，不伪造。"""
    import psycopg
    from app.domain.enums import AiRunNextAction, AiRunStatus
    from app.domain.runs.models import RunRecord
    from app.infrastructure.db import PgRunRepository

    from tests.e2e.test_b2v_http_end_to_end import ACTOR_A1

    runs = PgRunRepository(db.app_dsn)
    runs.create_run(RunRecord(
        run_id="run-legacy-no-progress", actor_id=ACTOR_A1, project_id=PROJECT_P1,
        kind="plan_generate", graph_name="planning", graph_version="1",
        status=AiRunStatus.WAITING_USER, next_action=AiRunNextAction.REVIEW_DRAFT, version=1,
    ))
    with _client(db) as client:
        view = _get_run(client, "run-legacy-no-progress")
    assert view["status"] == "waiting_user"
    assert view["progress"] is None
    with psycopg.connect(db.migrator_dsn) as conn:
        assert conn.execute(
            "SELECT count(*) FROM ai_run_events WHERE run_id='run-legacy-no-progress'"
        ).fetchone()[0] == 0


def test_get_run_does_not_interrupt_a_long_healthy_run(db) -> None:
    """健康的长时间运行不会因墙上时钟被改判为中断（旧总时长逻辑已移除）。"""
    import psycopg

    llm = FakeLLM({
        "planning.outline": _outline_handler,
        "planning.structure": _structure_handler,
        "planning.practice": _practice_handler,
    })
    with _client(db, llm=llm) as client:
        response = client.post(
            f"{V1}/plans/generate", params={"project_id": PROJECT_P1}, json={"goal": GOAL_A}
        )
        run_id = response.json()["run_id"]
        assert client.app.state.container.planning_worker.tick()
        with psycopg.connect(db.migrator_dsn) as conn:
            conn.execute(
                "UPDATE ai_runs SET status='running',next_action='wait',"
                "updated_at=now()-interval '7 days' WHERE run_id=%s",
                (run_id,),
            )
        view = _get_run(client, run_id)

    assert view["status"] == "running", view
    assert view["next_action"] == "wait"
    assert view["error"] is None
