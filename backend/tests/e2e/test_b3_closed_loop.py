"""B3 minimum: actual StateGraph, separate PG checkpoint, HTTP decisions, paid ledger."""

import httpx
import psycopg
import pytest
from app.domain.enums import AiRunNextAction, AiRunStatus
from app.domain.runs.models import RunRecord
from app.infrastructure.checkpointer.planning_executor import PgPlanningExecutor
from app.infrastructure.db import PgRunRepository
from app.infrastructure.providers.attempt_ledger import PgAttemptLLM
from app.infrastructure.providers.openai_compatible import OpenAICompatibleLLM
from app.ports.llm import LLMResult
from langgraph.checkpoint.postgres import PostgresSaver

from tests.e2e.test_b2v_http_end_to_end import (
    ACTOR_A1,
    PROJECT_P1,
    _approve_body,
    _container,
    _decide,
    _generate_to_draft,
    _get_run,
)
from tests.e2e.test_b2v_http_end_to_end import (
    db as db,
)
from tests.e2e.test_b2v_http_end_to_end import (
    migrated_db as migrated_db,
)
from tests.pg_harness import create_test_database

pytestmark = pytest.mark.postgres


@pytest.fixture
def checkpoint_db():
    checkpoint = create_test_database(prefix="studyplan_test_b3_cp")
    try:
        with PostgresSaver.from_conn_string(checkpoint.migrator_dsn) as saver:
            saver.setup()
        yield checkpoint
    finally:
        checkpoint.drop()


def test_b3_real_graph_pg_http_approve_and_restart(db, checkpoint_db):
    from app.main import create_app
    from fastapi.testclient import TestClient

    from tests.e2e.test_b2v_http_end_to_end import COOKIE, SESSION_A1
    container = _container(db)
    base = container.plan_service
    executor = PgPlanningExecutor(checkpoint_db.migrator_dsn, llm=base._llm)
    base._executor = executor
    with TestClient(create_app(container)) as client:
        client.cookies.set(COOKIE, SESSION_A1)
        run, draft = _generate_to_draft(client)
        record = base._runs.get_run(project_id=PROJECT_P1, run_id=run["run_id"])
        with PostgresSaver.from_conn_string(checkpoint_db.migrator_dsn) as saver:
            assert saver.get_tuple({"configurable":{"thread_id":record.thread_id}}) is not None
        # Reconstruct the service/runtime, then approve the durable business draft.
        base._executor = PgPlanningExecutor(checkpoint_db.migrator_dsn, llm=base._llm)
        response = _decide(client, draft["draft_id"], _approve_body(draft,0,"b3-publish"))
        assert response.status_code == 200, response.text
        assert _get_run(client,run["run_id"])["status"] == "succeeded"
        with PostgresSaver.from_conn_string(checkpoint_db.migrator_dsn) as saver:
            saved = saver.get_tuple({"configurable":{"thread_id":record.thread_id}})
            values = saved.checkpoint["channel_values"]
            assert values["prefs_snapshot"]["mode"] == "text_first"
            assert type(values["prefs_snapshot"]["mode"]) is str
            assert values["result_id"] == response.json()["plan"]["plan_id"]
            assert values["decision"] == "approve"
        assert len(base._llm.calls) == 3


def test_b3_paid_ledger_replay_and_unknown(db):
    runs = PgRunRepository(db.app_dsn)
    runs.create_run(RunRecord(run_id="run-b3-ledger",actor_id=ACTOR_A1,project_id=PROJECT_P1,
                             kind="plan_generate",graph_name="planning",graph_version="1",
                             status=AiRunStatus.RUNNING,next_action=AiRunNextAction.WAIT,version=1))
    calls = []
    def reply(request):
        calls.append(request)
        return httpx.Response(200,json={"choices":[{"message":{"content":'{"outline_ref":"o","sections":[]}'}}]})
    provider = OpenAICompatibleLLM(base_url="https://example.org/v1",api_key="test",model="test",client=httpx.Client(transport=httpx.MockTransport(reply)))
    ledger = PgAttemptLLM(db.app_dsn,provider)
    args = dict(purpose="planning.outline",payload={"goal":"Python","_project_id":PROJECT_P1},schema_name="PlanOutlineV1",run_id="run-b3-ledger",attempt_id="b3-paid-1")
    assert isinstance(ledger.generate_structured(**args),LLMResult)
    assert isinstance(ledger.generate_structured(**args),LLMResult)
    assert len(calls) == 1
    def timeout(request):
        calls.append(request)
        raise httpx.ReadTimeout("unknown")
    provider.client = httpx.Client(transport=httpx.MockTransport(timeout))
    args["attempt_id"] = "b3-paid-2"
    assert ledger.generate_structured(**args).dispatch_unknown
    assert ledger.generate_structured(**args).dispatch_unknown
    assert len(calls) == 2
    with psycopg.connect(db.migrator_dsn) as conn:
        assert conn.execute("SELECT status FROM ai_provider_attempts WHERE attempt_id='b3-paid-2'").fetchone()[0] == "reconciliation_required"


def test_b3_checkpoint_ack_failure_reconciles_without_republish(db, checkpoint_db):
    from app.main import create_app
    from fastapi.testclient import TestClient

    from tests.e2e.test_b2v_http_end_to_end import COOKIE, SESSION_A1
    container = _container(db)
    service = container.plan_service
    executor = PgPlanningExecutor(checkpoint_db.migrator_dsn,llm=service._llm)
    service._executor = executor
    with TestClient(create_app(container)) as client:
        client.cookies.set(COOKIE,SESSION_A1)
        run,draft = _generate_to_draft(client)
        original_finish = executor.finish
        def fail(**kwargs):
            raise RuntimeError("checkpoint offline")
        executor.finish = fail
        body = _approve_body(draft,0,"b3-ack")
        first = _decide(client,draft["draft_id"],body)
        assert first.status_code == 200, first.text
        assert _get_run(client,run["run_id"])["next_action"] == "reconcile"
        executor.finish = original_finish
        replay = _decide(client,draft["draft_id"],body)
        assert replay.status_code == 200, replay.text
        assert replay.json()["plan"]["plan_id"] == first.json()["plan"]["plan_id"]
        assert _get_run(client,run["run_id"])["status"] == "succeeded"
        assert len(service._llm.calls) == 3


def test_b3_http_session_resolves_server_scope(db):
    from app.main import create_app
    from fastapi.testclient import TestClient

    from tests.e2e.test_b2v_http_end_to_end import SESSION_A1
    client = TestClient(create_app(_container(db)))
    assert client.post("/api/v1/session",json={"token":"unknown"}).status_code == 401
    assert client.post("/api/v1/session",json={"token":SESSION_A1,"actor_id":"forged"}).status_code == 422
    response = client.post("/api/v1/session",json={"token":SESSION_A1})
    assert response.status_code == 200
    assert response.json()["project_ids"] == [PROJECT_P1]
    assert "HttpOnly" in response.headers["set-cookie"]
    assert client.get("/api/v1/session").json()["project_ids"] == [PROJECT_P1]
