from dataclasses import replace

import psycopg
import pytest
from app.composition import build_container
from app.core.config import get_settings
from app.infrastructure.domain_pack import load_pack, load_python_pack
from app.main import create_app
from fastapi.testclient import TestClient

from tests.e2e.test_b2v_http_end_to_end import migrated_db as fixture_db
from tests.e2e.test_b3_closed_loop import checkpoint_db as checkpoint_db
from tests.helpers.planning_worker import configure_test_worker

pytestmark = pytest.mark.postgres


@pytest.fixture(scope="module")
def migrated_db():
    yield from fixture_db.__wrapped__()


def route(client, session, goal):
    worker = configure_test_worker(client)
    project = session["project_ids"][0]
    suffix = f"?project_id={project}"
    headers = {"X-CSRF-Token": session["csrf_token"]}
    generated = client.post("/api/v1/plans/generate" + suffix, json={"goal": goal}, headers=headers)
    assert generated.status_code == 202, generated.text
    assert worker.tick()
    run = client.get("/api/v1/runs/" + generated.json()["run_id"] + suffix).json()
    assert run["status"] == "waiting_user", run
    url = "/api/v1/plans/drafts/" + run["result_ref"]
    draft_response = client.get(url + suffix)
    assert draft_response.status_code == 200, draft_response.text
    return draft_response.json(), url, suffix, headers


def test_agent_pack_chapters_nodes_publish_readback_and_history(migrated_db):
    from app.tools.seed_b3 import seed_reviewed_pack

    pack = load_pack("agent-application-v1.json")
    with psycopg.connect(migrated_db.migrator_dsn) as conn:
        seed_reviewed_pack(conn, pack)
        seed_reviewed_pack(conn, load_python_pack())
    settings = replace(get_settings(), database_url=migrated_db.app_dsn, llm_provider="fake", local_session_token="")
    client = TestClient(create_app(build_container(settings)))
    session = client.post("/api/v1/auth/register", json={"username": "完整路线甲", "password": "123456"}).json()
    draft, url, suffix, headers = route(client, session, "从 Python 基础学习 Agent 应用开发")
    assert draft["source_pack_key"] == "agent.application" and draft["source_pack_version"] == 1
    assert len(draft["stages"]) > 2
    expected_chapters = {c["section_id"]: c["url"] for r in pack["resources"] for c in r["sections"]}
    assert draft["stage_resources"] and all(r["node_ids"] and r["ordered_sections"] for r in draft["stage_resources"])
    for item in draft["stage_resources"]:
        assert item["verification_status"] == "reviewed" and item["documentation_version"]
        for section in item["ordered_sections"]:
            assert section["url"] == expected_chapters[section["section_id"]]
    body = {"decision": "approve", "expected_version": 0, "draft_hash": draft["draft_hash"], "idempotency_key": "agent-full-route"}
    approved = client.post(url + "/decision" + suffix, json=body, headers=headers)
    assert approved.status_code == 200, approved.text
    published = approved.json()["plan"]
    readback = client.get("/api/v1/plans/current" + suffix).json()
    assert readback == published
    assert [r["node_ids"] for r in readback["stage_resources"]] == [r["node_ids"] for r in draft["stage_resources"]]
    assert [r["ordered_sections"] for r in readback["stage_resources"]] == [r["ordered_sections"] for r in draft["stage_resources"]]
    assert readback["source_pack_key"] == draft["source_pack_key"]
    workspace = client.get("/api/v1/workspace" + suffix).json()
    for stage in workspace["stages"]:
        node_ids = {n["node_id"] for n in stage["nodes"]}
        assert all(set(r["node_ids"]) <= node_ids for r in stage["resources"])
        assert any(n["child_ids"] for n in stage["nodes"])
        assert all(n["progress"] is None for n in stage["nodes"])
    with psycopg.connect(migrated_db.app_dsn) as conn:
        conn.execute("SELECT set_config('app.project_id',%s,true)", (session["project_ids"][0],))
        with pytest.raises(psycopg.errors.CheckViolation):
            conn.execute("UPDATE stage_resource_assignments SET node_ids=%s WHERE assignment_id=%s",
                         (psycopg.types.json.Jsonb([workspace["stages"][1]["nodes"][0]["node_id"]]),
                          readback["stage_resources"][0]["assignment_id"]))
    # Repeated confirmation and historical catalog/progress references survive replan.
    assert client.post(url + "/decision" + suffix, json=body, headers=headers).json()["plan"] == published
    old_unit = workspace["stages"][0]["units"][0]["unit_id"]
    with psycopg.connect(migrated_db.migrator_dsn) as conn:
        conn.execute("INSERT INTO unit_progress(project_id,unit_id,status,version) VALUES (%s,%s,'completed',1)",
                     (session["project_ids"][0], old_unit))
    python_draft, pyurl, pysuffix, pyheaders = route(client, session, "Python 工程入门和命令行工具")
    assert python_draft["source_pack_key"] == "python.engineering"
    pyapproved = client.post(pyurl + "/decision" + pysuffix, headers=pyheaders, json={
        "decision": "approve", "expected_version": 1, "draft_hash": python_draft["draft_hash"], "idempotency_key": "python-replan"
    })
    assert pyapproved.status_code == 200, pyapproved.text
    with psycopg.connect(migrated_db.migrator_dsn) as conn:
        assert conn.execute("SELECT status FROM unit_progress WHERE unit_id=%s", (old_unit,)).fetchone()[0] == "completed"
        assert conn.execute("SELECT count(*) FROM plan_revisions WHERE project_id=%s", (session["project_ids"][0],)).fetchone()[0] == 2
    other = TestClient(create_app(build_container(settings)))
    other.post("/api/v1/auth/register", json={"username": "完整路线乙", "password": "123456"})
    assert other.get("/api/v1/workspace" + suffix).status_code == 403
    assert other.get(url + suffix).status_code == 403
    # The same actor's second space has its own plan and entity references.
    with psycopg.connect(migrated_db.migrator_dsn) as conn:
        actor = conn.execute("SELECT actor_id FROM auth_users WHERE username=%s", ("完整路线甲",)).fetchone()[0]
        conn.execute("INSERT INTO learning_projects(project_id,owner_actor_id,title,goal_statement,stable_key) VALUES ('b3f2-space-two',%s,'另一空间','另一个目标','b3f2.space.two')", (actor,))
    second_session = {**client.get("/api/v1/session").json(), "project_ids": ["b3f2-space-two"]}
    assert client.get(url + "?project_id=b3f2-space-two").status_code == 404
    second, _, _, _ = route(client, second_session, "Python 工程入门")
    assert second["project_id"] == "b3f2-space-two"
    assert not {u["unit_id"] for u in second["unit_links"]} & {u["unit_id"] for u in readback["unit_links"]}


def test_unsupported_direction_never_binds_known_python_resources(migrated_db):
    settings = replace(get_settings(), database_url=migrated_db.app_dsn, llm_provider="fake", local_session_token="")
    client = TestClient(create_app(build_container(settings)))
    session = client.post("/api/v1/auth/register", json={"username": "通用路线", "password": "123456"}).json()
    draft, _, _, _ = route(client, session, "水彩构图入门")
    assert draft["source_pack_key"] == "" and draft["source_pack_version"] == 0
    assert all(not r["source_ref"] and not r["ordered_sections"] and r["fallback_search_terms"] for r in draft["stage_resources"])


def test_mock_http_provider_full_pg_graph_and_ledger(migrated_db, checkpoint_db):
    import json

    import httpx
    from app.infrastructure.checkpointer.planning_executor import PgPlanningExecutor
    from app.infrastructure.providers.attempt_ledger import PgAttemptLLM
    from app.infrastructure.providers.openai_compatible import OpenAICompatibleLLM
    from app.infrastructure.providers.planning_demo import selected_output
    from app.tools.seed_b3 import seed_reviewed_pack

    with psycopg.connect(migrated_db.migrator_dsn) as conn:
        seed_reviewed_pack(conn, load_pack("agent-application-v1.json"))
    calls = []
    def reply(request):
        body = json.loads(request.content)
        prompt = json.loads(body["messages"][1]["content"])
        calls.append(prompt)
        payload = {**prompt["context"], "domain_pack": prompt["domain_pack"]}
        response = selected_output(prompt["purpose"], payload)
        return httpx.Response(200, json={"model": "mock-route-model", "usage": {"prompt_tokens": 100, "completion_tokens": 200},
                                       "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(response)}}]})
    settings = replace(get_settings(), database_url=migrated_db.app_dsn, llm_provider="fake", local_session_token="")
    container = build_container(settings)
    with httpx.Client(transport=httpx.MockTransport(reply)) as transport:
        provider = OpenAICompatibleLLM(base_url="https://mock.example/v1", api_key="test", model="mock-route-model", client=transport)
        ledger = PgAttemptLLM(migrated_db.app_dsn, provider)
        container.plan_service._llm = ledger
        container.plan_service._executor = PgPlanningExecutor(checkpoint_db.migrator_dsn, llm=ledger)
        with TestClient(create_app(container)) as client:
            session = client.post("/api/v1/auth/register", json={"username": "适配器完整路线", "password": "123456"}).json()
            draft, url, suffix, headers = route(client, session, "Agent应用开发与知识助手")
            assert len(draft["stages"]) == 9 and draft["source_pack_key"] == "agent.application"
            # b3f2-batch-v1: one request per node — 1 skeleton + 9 structure + 9 practice.
            assert [c["purpose"] for c in calls] == (
                ["planning.outline"] + ["planning.structure"] * 9 + ["planning.practice"] * 9
            )
            assert all(c["domain_pack"]["pack_key"] == "agent.application" for c in calls)
            body = {"decision": "approve", "expected_version": 0, "draft_hash": draft["draft_hash"], "idempotency_key": "mock-full-route"}
            approved = client.post(url + "/decision" + suffix, json=body, headers=headers)
            assert approved.status_code == 200, approved.text
            assert client.post(url + "/decision" + suffix, json=body, headers=headers).json()["plan"] == approved.json()["plan"]
            assert len(calls) == 19
            assert client.get("/api/v1/plans/current" + suffix).json() == approved.json()["plan"]
            with psycopg.connect(migrated_db.migrator_dsn) as conn:
                attempts = conn.execute("SELECT status,input_tokens,output_tokens FROM ai_provider_attempts WHERE run_id IN (SELECT run_id FROM ai_runs WHERE project_id=%s)", (session["project_ids"][0],)).fetchall()
                assert attempts == [("succeeded", 100, 200)] * 19


def test_failed_provider_usage_is_retained_and_replayed_without_dispatch(migrated_db):
    import json

    import httpx
    from app.infrastructure.providers.attempt_ledger import PgAttemptLLM
    from app.infrastructure.providers.openai_compatible import OpenAICompatibleLLM

    settings = replace(get_settings(), database_url=migrated_db.app_dsn, llm_provider="fake", local_session_token="")
    container = build_container(settings)
    client = TestClient(create_app(container))
    session = client.post("/api/v1/auth/register", json={"username": "失败用量留存", "password": "123456"}).json()
    draft, _, _, _ = route(client, session, "Agent开发")
    with psycopg.connect(migrated_db.migrator_dsn) as conn:
        run_id = conn.execute("SELECT run_id FROM plan_drafts WHERE draft_id=%s", (draft["draft_id"],)).fetchone()[0]
    calls = []
    def reply(request):
        calls.append(request)
        return httpx.Response(200, json={"usage": {"prompt_tokens": 111, "completion_tokens": 8000},
                                        "choices": [{"finish_reason": "length", "message": {"content": ""}}]})
    with httpx.Client(transport=httpx.MockTransport(reply)) as transport:
        ledger = PgAttemptLLM(migrated_db.app_dsn, OpenAICompatibleLLM(base_url="https://mock.example/v1", api_key="test", model="mock", client=transport))
        args = dict(purpose="planning.outline", payload={"_project_id": session["project_ids"][0]}, schema_name="OutlineV1", run_id=run_id, attempt_id=run_id + ":usage-check")
        first = ledger.generate_structured(**args)
        replay = ledger.generate_structured(**args)
        assert first.error_class == replay.error_class == "provider_output_truncated"
        assert first.input_tokens == replay.input_tokens == 111
        assert first.output_tokens == replay.output_tokens == 8000
        assert len(calls) == 1
        with psycopg.connect(migrated_db.migrator_dsn) as conn:
            row = conn.execute("SELECT status,input_tokens,output_tokens,response_payload FROM ai_provider_attempts WHERE attempt_id=%s", (args["attempt_id"],)).fetchone()
            assert row[:3] == ("failed", 111, 8000)
            assert "reasoning_content" not in json.dumps(row[3])
