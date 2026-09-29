"""HTTP submission returns while the explicitly started worker owns generation."""

from __future__ import annotations

import threading

import pytest
from app.infrastructure.providers.fake import FakeLLM

from tests.e2e.test_b2v_http_end_to_end import (
    GOAL_A,
    PROJECT_P1,
    V1,
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
    from tests.e2e.test_b2v_http_end_to_end import _client

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
