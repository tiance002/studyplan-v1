"""Owned PG counterexamples for coaching scope, fencing and single dispatch.

All HTTP provider requests use MockTransport. The existing owned database and
role harness is reused; no external endpoint or product database is contacted.
"""

import json
import socket
import threading
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import replace

import httpx
import psycopg
import pytest
from fastapi.testclient import TestClient
from app.application.planning_budget import BudgetPolicy
from app.composition import build_container
from app.core.config import get_settings
from app.core.ids import new_id
from app.domain.assistant import ASSISTANT_PROTOCOL, ASSISTANT_PURPOSE, INPUT_LIMIT
from app.infrastructure.db.job_repository import PgPlanningJobRepository
from app.infrastructure.providers.attempt_ledger import PgAttemptLLM
from app.infrastructure.providers.openai_compatible import OpenAICompatibleLLM
from app.infrastructure.providers.runtime_factory import PersonalPlanningRuntimeFactory
from app.main import create_app
from app.ports.llm import LLMFailure
from app.ports.planning_jobs import PlanningLeaseLostError

from tests.e2e.test_b2v_http_end_to_end import migrated_db as migrated_db  # noqa: F401
from tests.integration.test_assistant_http_pg import BASE, send, setup as setup, start
from tests.integration.test_prompts_pg import prompt_scenario as prompt_scenario  # noqa: F401
from tests.integration.test_prompts_pg import resource_scenario as resource_scenario  # noqa: F401
from tests.integration.test_summary_http_pg import login
from tests.pg_harness import create_test_database

pytestmark = pytest.mark.postgres
POLICY = BudgetPolicy(100, 100, 100, 100, 100, 100)


def _jobs(db, scope, admission="trusted_server"):
    return PgPlanningJobRepository(db.app_dsn, actor_ids=(scope.actor_id,), admission_mode=admission)


def _claim(jobs, project, admission="trusted_server"):
    claim = (jobs.claim_next("assistant-protocol-test", 30) if admission == "trusted_server"
             else jobs.claim(project, "assistant-protocol-test", 30))
    assert claim is not None
    return claim


def _scope(conn, scope, project):
    conn.execute("SELECT set_config('app.actor_id',%s,true),set_config('app.project_id',%s,true)",
                 (scope.actor_id, project))


def _payload(turn, claim):
    return dict(deepcopy(turn["payload"]), _project_id=claim.project_id, _assistant_claim=dict(
        job_id=claim.job_id, run_id=claim.run_id, project_id=claim.project_id,
        actor_id=claim.actor_id, lease_token=claim.lease_token))


def _mock_provider(client):
    provider = OpenAICompatibleLLM(base_url="https://fixture.invalid/v1", api_key="synthetic-key",
                                  model="synthetic-assistant", client=client, budget_policy=POLICY)
    provider.configuration_ref = "fixture:assistant"
    provider.prompt_version = ASSISTANT_PROTOCOL
    return provider


def _reply_response(content='{"reply":"请结合当前稿件补充边界。"}'):
    return httpx.Response(200, json={"model": "synthetic-assistant", "choices": [{
        "finish_reason": "stop", "message": {"content": content}}],
        "usage": {"prompt_tokens": 17, "completion_tokens": 9}})


def test_retained_known_paid_extra_id_fails_closed_without_repair_or_formal_write(setup):
    from pathlib import Path
    fixture=json.loads((Path(__file__).parents[1]/"fixtures/assistant_v1/known_extra_message_id.json").read_text(encoding="utf-8"))
    db,scope,cmd,container,_,_=setup
    calls=[]
    with httpx.Client(transport=httpx.MockTransport(lambda req: calls.append(req) or _reply_response(fixture["content"]))) as client:
        provider=_mock_provider(client)
        container.assistant_service.provider_resolver=lambda scope,project,run,ref,manifest:PgAttemptLLM(db.app_dsn,provider,manifest=manifest)
        with TestClient(create_app(container)) as api:
            headers=login(api,db,scope);q=dict(project_id=cmd.project_id)
            view,_=start(api,q,headers,cmd)
            view,_=send(api,q,headers,view["conversation_id"],"已保留原稿：输入是数据，超时需要核对证据。")
            assert container.planning_worker.tick()
            result=api.get(BASE+"/"+view["conversation_id"],params=q).json()
            assert len(result["messages"])==1 and result["messages"][0]["run_status"]=="failed"
            assert result["messages"][0]["error_class"]=="assistant_reply_invalid"
            assert result["formal_version"]==0 and result["formal_saves"]==[]
            assert not container.planning_worker.tick() and len(calls)==1
        with psycopg.connect(db.app_dsn) as conn:
            _scope(conn,scope,cmd.project_id)
            receipt=conn.execute("SELECT status,response_payload FROM ai_provider_attempts WHERE run_id=%s",(result["messages"][0]["run_id"],)).fetchone()
            assert receipt[0]=="succeeded" and set(receipt[1]["payload"])=={"reply","message_id"}
            assert conn.execute("SELECT status FROM practice_tasks WHERE task_id=%s",(cmd.task_id,)).fetchone()[0]=="pending"


@pytest.mark.parametrize("dispatched", [False, True], ids=["queued-zero", "dispatched-fenced"])
def test_cancel_preserves_durable_dispatch_and_rejects_late_finish(setup, dispatched):
    db, scope, cmd, container, _, offline = setup
    requests, entered, release = [], threading.Event(), threading.Event()

    def handler(request):
        requests.append(request)
        entered.set()
        assert release.wait(15), "test must release its own blocked synthetic provider"
        return _reply_response()

    with httpx.Client(transport=httpx.MockTransport(handler)) as transport:
        provider = _mock_provider(transport)
        container.assistant_service.provider_resolver = lambda actor, project, run, ref, manifest: PgAttemptLLM(
            db.app_dsn, provider, manifest=manifest)
        q = dict(project_id=cmd.project_id)
        with TestClient(create_app(container)) as client:
            headers = login(client, db, scope)
            view, _ = start(client, q, headers, cmd)
            identifier = view["conversation_id"]
            view, _ = send(client, q, headers, identifier, "精确原稿")
            run = view["messages"][0]
            if not dispatched:
                cancelled = client.post(BASE + "/" + identifier + "/cancel", params=q, headers=headers,
                    json=dict(run_id=run["run_id"], expected_version=run["run_version"], idempotency_key="cancel"))
                assert cancelled.status_code == 200, cancelled.text
                assert cancelled.json()["messages"][0]["run_status"] == "cancelled"
                assert not container.planning_worker.tick() and requests == [] and offline.calls == []
            else:
                with ThreadPoolExecutor(max_workers=1) as pool:
                    execution = pool.submit(container.planning_worker.tick)
                    try:
                        assert entered.wait(10)
                        with psycopg.connect(db.migrator_dsn) as conn:
                            assert conn.execute("SELECT status FROM ai_provider_attempts WHERE run_id=%s",
                                                (run["run_id"],)).fetchone()[0] == "dispatched"
                        current = client.get(BASE + "/" + identifier, params=q).json()["messages"][0]
                        body = dict(run_id=run["run_id"], expected_version=current["run_version"],
                                    idempotency_key="cancel-dispatched")
                        cancelled = client.post(BASE + "/" + identifier + "/cancel", params=q,
                                                headers=headers, json=body)
                        assert cancelled.status_code == 200, cancelled.text
                        assert cancelled.json()["messages"][0]["run_status"] == "reconciliation_required"
                        assert client.post(BASE + "/" + identifier + "/cancel", params=q,
                                           headers=headers, json=body).status_code == 200
                    finally:
                        release.set()
                    assert execution.result(timeout=10)
                final = client.get(BASE + "/" + identifier, params=q).json()
                assert len(final["messages"]) == 1
                assert final["messages"][0]["run_status"] == "reconciliation_required"
                assert not container.planning_worker.tick() and len(requests) == 1
                with psycopg.connect(db.migrator_dsn) as conn:
                    assert conn.execute("SELECT status FROM ai_provider_attempts WHERE run_id=%s",
                                        (run["run_id"],)).fetchone()[0] == "succeeded"
            with psycopg.connect(db.migrator_dsn) as conn:
                assert conn.execute("SELECT count(*) FROM assistant_messages WHERE run_id=%s AND role='assistant'",
                                    (run["run_id"],)).fetchone()[0] == 0


@pytest.mark.parametrize("admission", ["allowlist", "trusted_server"])
def test_expired_dispatched_same_scope_new_conversation_cannot_redispatch(setup, admission):
    db, scope, cmd, container, _, provider = setup
    service = container.assistant_service
    service.admission_mode, service.actor_ids = admission, (scope.actor_id,)
    q = dict(project_id=cmd.project_id)
    with TestClient(create_app(container)) as client:
        headers = login(client, db, scope)
        view, _ = start(client, q, headers, cmd)
        view, body = send(client, q, headers, view["conversation_id"], "过期未知原稿")
        jobs = _jobs(db, scope, admission)
        claim = _claim(jobs, cmd.project_id, admission)
        turn = service.repository.turn(claim)
        with psycopg.connect(db.migrator_dsn) as conn:
            conn.execute("""INSERT INTO ai_provider_attempts(attempt_id,run_id,provider,model_id,prompt_version,
                status,request_fingerprint,schema_name) VALUES(%s,%s,'openai_compatible','synthetic-assistant',
                %s,'dispatched','synthetic-process-interruption','AssistantReplyV1')""",
                (claim.run_id + ":assistant_reply:1", claim.run_id, ASSISTANT_PROTOCOL))
            conn.execute("UPDATE ai_jobs SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE job_id=%s",
                         (claim.job_id,))
        other, _ = start(client, q, headers, cmd, key="same-scope-new-conversation")
        rejected = client.post(BASE + "/" + other["conversation_id"] + "/messages", params=q,
                               headers=headers, json=dict(body, idempotency_key="different-send-key"))
        assert rejected.status_code == 409, rejected.text
        with pytest.raises(PlanningLeaseLostError):
            service.repository.finish(claim, turn, {"reply": "迟到结果不得写入"})
        if admission == "trusted_server":
            assert jobs.claim_next("expired-reconcile-test", 30) is None
        else:
            assert jobs.claim(cmd.project_id, "expired-allowlist-test", 30) is None
        with psycopg.connect(db.migrator_dsn) as conn:
            assert conn.execute("SELECT count(*) FROM ai_runs WHERE project_id=%s AND kind='assistant_reply'",
                                (cmd.project_id,)).fetchone()[0] == 1
            assert conn.execute("SELECT count(*) FROM ai_provider_attempts WHERE run_id=%s",
                                (claim.run_id,)).fetchone()[0] == 1
        assert provider.calls == []


def test_app_role_rejects_spoofed_actor_and_frozen_field_writes(setup):
    db, scope, cmd, container, _, provider = setup
    service = container.assistant_service
    body = dict(plan_id=cmd.plan_id, stage_id=cmd.stage_id, mode="summary", task_id=None, idempotency_key="rls")
    view = service.create(scope, cmd.project_id, body)
    view = service.send(scope, cmd.project_id, view["conversation_id"], dict(
        content="RLS 原稿", intent="work_draft", consent_to_model=True, idempotency_key="rls-message"))
    identifier, draft = view["conversation_id"], view["current_draft_message_id"]
    _, reservation = service.repository.reserve_save(scope, cmd.project_id, identifier, dict(
        content="正式保存预约", draft_message_id=draft, expected_version=0, idempotency_key="reserved-save"))
    with psycopg.connect(db.app_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM assistant_conversations").fetchone()[0] == 0
        _scope(conn, scope, cmd.project_id)
        for sql, values in [
            ("""INSERT INTO assistant_conversations(conversation_id,project_id,actor_id,plan_id,plan_revision,
                stage_id,mode,title,context,context_hash) SELECT %s,project_id,%s,plan_id,plan_revision,
                stage_id,mode,title,context,context_hash FROM assistant_conversations WHERE conversation_id=%s""",
             (new_id("aconv"), "different-actor", identifier)),
            ("""INSERT INTO assistant_receipts(receipt_id,project_id,actor_id,idempotency_key,action,input_hash,
                response_snapshot) VALUES(%s,%s,'different-actor','spoof-key','create','hash','{}')""",
             (new_id("arcpt"), cmd.project_id)),
            ("UPDATE assistant_conversations SET context='{}',context_hash='changed' WHERE conversation_id=%s",
             (identifier,)),
            ("UPDATE assistant_formal_saves SET content='changed' WHERE save_id=%s", (reservation["save_id"],)),
            ("UPDATE assistant_turns SET payload='{}' WHERE conversation_id=%s", (identifier,)),
            ("UPDATE assistant_messages SET content='changed' WHERE message_id=%s", (draft,)),
        ]:
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                with conn.transaction():
                    conn.execute(sql, values)
        conn.execute("UPDATE assistant_conversations SET current_draft_message_id=%s WHERE conversation_id=%s",
                     (draft, identifier))
        conn.execute("SELECT set_config('app.actor_id','different-actor',true)")
        for table in ("assistant_conversations", "assistant_messages", "assistant_turns",
                      "assistant_receipts", "assistant_formal_saves"):
            assert conn.execute(f"SELECT count(*) FROM {table} WHERE project_id=%s", (cmd.project_id,)).fetchone()[0] == 0
    assert provider.calls == []
    run = view["messages"][0]
    service.cancel(scope, cmd.project_id, identifier, dict(run_id=run["run_id"],
        expected_version=run["run_version"], idempotency_key="rls-cleanup"))


def test_question_without_draft_is_rejected_by_api_before_any_run(setup):
    db, scope, cmd, container, _, provider = setup
    q = dict(project_id=cmd.project_id)
    with TestClient(create_app(container)) as client:
        headers = login(client, db, scope)
        view, _ = start(client, q, headers, cmd)
        response = client.post(BASE + "/" + view["conversation_id"] + "/messages", params=q, headers=headers,
            json=dict(content="无绑定追问", intent="question", consent_to_model=True, idempotency_key="no-draft"))
        assert response.status_code == 400, response.text
        assert client.get(BASE + "/" + view["conversation_id"], params=q).json()["messages"] == []
        with psycopg.connect(db.migrator_dsn) as conn:
            assert conn.execute("SELECT count(*) FROM ai_runs WHERE project_id=%s", (cmd.project_id,)).fetchone()[0] == 0
        assert not container.planning_worker.tick() and provider.calls == []


@pytest.mark.parametrize("violation", ["purpose", "manifest", "input", "cap", "second_attempt"])
def test_frozen_turn_guard_rejects_extra_purpose_input_and_budget_without_http(setup, violation):
    db, scope, cmd, container, _, _ = setup
    service = container.assistant_service
    view = service.create(scope, cmd.project_id, dict(plan_id=cmd.plan_id, stage_id=cmd.stage_id,
        mode="summary", task_id=None, idempotency_key="budget-start"))
    view = service.send(scope, cmd.project_id, view["conversation_id"], dict(content="预算原稿", intent="work_draft",
        consent_to_model=True, idempotency_key="budget-message"))
    claim = _claim(_jobs(db, scope), cmd.project_id)
    turn = service.repository.turn(claim)
    requests = []
    with httpx.Client(transport=httpx.MockTransport(lambda request: requests.append(request) or _reply_response())) as client:
        provider = _mock_provider(client)
        manifest, payload = deepcopy(turn["manifest"]), _payload(turn, claim)
        purpose, attempt = ASSISTANT_PURPOSE, claim.run_id + ":assistant_reply:1"
        if violation == "purpose":
            purpose = "planning.repair"
        elif violation == "manifest":
            manifest["max_requests"] = 2
        elif violation == "input":
            payload["context"] = {"objectives": ["x" * (INPUT_LIMIT + 1)]}
        elif violation == "cap":
            provider.request_options = lambda purpose: dict(model=provider.model, max_tokens=101)
        else:
            attempt = claim.run_id + ":assistant_reply:2"
        result = PgAttemptLLM(db.app_dsn, provider, manifest=manifest).generate_structured(
            purpose=purpose, payload=payload, schema_name="AssistantReplyV1", run_id=claim.run_id, attempt_id=attempt)
        assert isinstance(result, LLMFailure)
        assert result.error_class in {"run_manifest_violation", "assistant_input_invalid", "run_budget_exceeded"}
        assert not result.dispatch_unknown and requests == []
    with psycopg.connect(db.migrator_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM ai_provider_attempts WHERE run_id=%s", (claim.run_id,)).fetchone()[0] == 0
    service.repository.finish(claim, turn, error="synthetic-guard-rejected")


def test_message_pagination_keeps_old_current_draft_and_exact_latest_text(setup):
    db, scope, cmd, container, _, provider = setup
    service = container.assistant_service
    view = service.create(scope, cmd.project_id, dict(plan_id=cmd.plan_id, stage_id=cmd.stage_id,
        mode="summary", task_id=None, idempotency_key="paged-start"))
    identifier, draft, original, latest = view["conversation_id"], new_id("amsg"), " \n早期完整工作稿🙂\t ", " \n最后追问精确正文🙂\t "
    with psycopg.connect(db.app_dsn) as conn:
        _scope(conn, scope, cmd.project_id)
        conn.execute("""INSERT INTO assistant_messages(message_id,project_id,conversation_id,sequence,role,intent,content)
            VALUES(%s,%s,%s,1,'user','work_draft',%s)""", (draft, cmd.project_id, identifier, original))
        rows = [(new_id("amsg"), cmd.project_id, identifier, sequence,
                 latest if sequence == 131 else f"追问 {sequence}", draft) for sequence in range(2, 132)]
        with conn.cursor() as cursor:
            cursor.executemany("""INSERT INTO assistant_messages(message_id,project_id,conversation_id,sequence,role,
                intent,content,draft_message_id) VALUES(%s,%s,%s,%s,'user','question',%s,%s)""", rows)
        conn.execute("UPDATE assistant_conversations SET current_draft_message_id=%s WHERE conversation_id=%s",
                     (draft, identifier))
    q = dict(project_id=cmd.project_id)
    with TestClient(create_app(container)) as client:
        login(client, db, scope)
        first = client.get(BASE + "/" + identifier, params=q).json()
        assert first["messages_truncated"] and first["message_cursor"] == 12
        assert len(first["messages"]) == 121  # bounded window plus its explicitly pinned draft
        assert first["current_draft_message_id"] == draft
        assert first["messages"][0]["content"] == original and first["messages"][-1]["content"] == latest
        older = client.get(BASE + "/" + identifier, params={**q, "before_sequence": first["message_cursor"]}).json()
        assert not older["messages_truncated"] and older["message_cursor"] is None
        merged = {message["sequence"]: message for message in [*older["messages"], *first["messages"]]}
        assert set(merged) == set(range(1, 132)) and merged[1]["content"] == original and merged[131]["content"] == latest
        listed = client.get(BASE, params=q).json()["items"][0]
        assert listed["current_draft_message_id"] == draft and "messages" not in listed
    assert provider.calls == []


@pytest.fixture(scope="module")
def assistant_checkpoint_db():
    checkpoint = create_test_database(prefix="studyplan_test_assistant_cp")
    try:
        yield checkpoint
    finally:
        checkpoint.drop()


@pytest.mark.parametrize("mode,invalid", [("summary", False), ("practice", False), ("summary", True)])
def test_real_composition_factory_mock_transport_one_turn_and_no_json_repair(
        setup, assistant_checkpoint_db, monkeypatch, mode, invalid):
    db, scope, cmd, _, _, _ = setup
    requests = []

    def handler(request):
        requests.append(request)
        return _reply_response('{"reply":' if invalid else '{"reply":"具体缺口：请说明输入与验收边界。"}')

    def synthetic_dns(host, port, *args, **kwargs):
        assert host == "fixture.invalid"
        return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", port))]

    monkeypatch.setattr("app.infrastructure.providers.endpoint_policy.socket.getaddrinfo", synthetic_dns)
    original_factory = PersonalPlanningRuntimeFactory._deployment_provider
    with httpx.Client(transport=httpx.MockTransport(handler)) as transport:
        def factory_provider(factory):
            provider = original_factory(factory)
            assert isinstance(provider, OpenAICompatibleLLM)
            provider.client = transport
            return provider

        monkeypatch.setattr(PersonalPlanningRuntimeFactory, "_deployment_provider", factory_provider)
        settings = replace(get_settings(), database_url=db.app_dsn, database_url_sync=db.app_dsn,
            checkpoint_database_url=assistant_checkpoint_db.app_dsn, llm_provider="openai_compatible",
            llm_base_url="https://fixture.invalid/v1", llm_api_key="synthetic-key", llm_model_id="synthetic-assistant",
            llm_allowed_hosts=("fixture.invalid",), llm_max_output_tokens=100, llm_outline_output_tokens=100,
            llm_structure_output_tokens=100, llm_practice_output_tokens=100, llm_repair_output_tokens=100,
            llm_model_max_output_tokens=100, planning_worker_admission_mode="trusted_server", local_session_token="",
            search_provider="", github_discovery_enabled=False)
        container = build_container(settings)
        raw = " \n真实装配但仅本地 MockTransport 的原文🙂\t "
        q = dict(project_id=cmd.project_id)
        with TestClient(create_app(container)) as client:
            headers = login(client, db, scope)
            view, _ = start(client, q, headers, cmd, mode)
            view, body = send(client, q, headers, view["conversation_id"], raw)
            identifier, run = view["conversation_id"], view["messages"][0]["run_id"]
            with psycopg.connect(db.migrator_dsn) as conn:
                manifest = conn.execute("SELECT manifest FROM assistant_turns WHERE run_id=%s", (run,)).fetchone()[0]
                assert manifest["model_ref"].startswith("deployment:")
                assert manifest["max_requests"] == 1 and manifest["output_cap"] == 100
            assert container.planning_worker.tick()
            got = client.get(BASE + "/" + identifier, params=q).json()
            assert got["messages"][0]["content"] == raw and got["formal_version"] == 0 and got["formal_saves"] == []
            assert got["messages"][0]["run_status"] == ("failed" if invalid else "succeeded")
            assert len(got["messages"]) == (1 if invalid else 2)
            assert client.post(BASE + "/" + identifier + "/messages", params=q, headers=headers,
                               json=body).status_code == 202
            assert not container.planning_worker.tick() and len(requests) == 1
            sent = json.loads(requests[0].content)
            model_input = json.loads(sent["messages"][1]["content"])
            assert model_input["purpose"] == ASSISTANT_PURPOSE and model_input["schema"] == "AssistantReplyV1"
            assert model_input["context"]["current_message"]["content"] == raw
            assert "private.invalid" not in json.dumps(model_input)
            assert sent["max_tokens"] == 100 and requests[0].url.host == "fixture.invalid"
            with psycopg.connect(db.migrator_dsn) as conn:
                attempts = conn.execute("SELECT attempt_id,status,error_class,input_tokens,output_tokens FROM ai_provider_attempts WHERE run_id=%s",
                                        (run,)).fetchall()
                assert len(attempts) == 1 and attempts[0][0] == run + ":assistant_reply:1"
                assert attempts[0][1:3] == (("failed", "provider_invalid_json") if invalid else ("succeeded", None))
                assert attempts[0][3:] == (17, 9)
                assert conn.execute("SELECT status FROM practice_tasks WHERE task_id=%s", (cmd.task_id,)).fetchone()[0] == "pending"
