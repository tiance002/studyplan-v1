"""Personal secrets: real PG isolation, CAS and immutable run binding."""
from concurrent.futures import ThreadPoolExecutor

import psycopg
import pytest
from app.core.errors import ConflictError
from app.infrastructure.db.model_settings import PgModelSettings
from cryptography.fernet import Fernet

from tests.e2e.test_b2v_http_end_to_end import ACTOR_A1, PROJECT_P1, _container
from tests.e2e.test_b2v_http_end_to_end import db as db
from tests.e2e.test_b2v_http_end_to_end import migrated_db as migrated_db
from tests.e2e.test_b3_closed_loop import checkpoint_db as checkpoint_db

pytestmark = pytest.mark.postgres


def test_encrypted_settings_cas_isolation_and_revocation(db):
    actor = ACTOR_A1 + "-settings"
    key = Fernet.generate_key().decode()
    repo = PgModelSettings(db.app_dsn, key)
    args = dict(base_url="https://api.deepseek.com", model_id="model-one", protocol="openai", api_key="private-test-key")
    assert repo.get(actor) is None
    one = repo.save(actor, expected_version=0, **args)
    assert one.version == 1
    assert repo.get("another-actor") is None
    assert "private-test-key" not in repr(one)
    with psycopg.connect(db.migrator_dsn) as conn:
        ciphertext = conn.execute("SELECT encrypted_api_key FROM user_model_setting_versions WHERE actor_id=%s", (actor,)).fetchone()[0]
        assert "private-test-key" not in ciphertext
    def edit(model):
        try:
            return repo.save(actor, expected_version=1, **{**args,"model_id":model,"api_key":""}).version
        except ConflictError:
            return "conflict"
    with ThreadPoolExecutor(2) as pool:
        outcomes = list(pool.map(edit,["two","three"]))
    assert sorted(map(str,outcomes)) == ["2","conflict"]
    assert repo.resolve(actor).api_key == "private-test-key"
    with pytest.raises(ConflictError):
        repo.clear(actor, expected_version=1)
    repo.clear(actor,expected_version=2)
    assert not repo.get(actor).has_api_key
    assert repo.resolve(actor) is None
    with psycopg.connect(db.migrator_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM user_model_setting_versions WHERE encrypted_api_key IS NOT NULL").fetchone()[0] == 0
    with psycopg.connect(db.app_dsn) as conn:
        conn.execute("SELECT set_config('app.actor_id','another-actor',true)")
        assert conn.execute("SELECT count(*) FROM user_model_setting_versions").fetchone()[0] == 0


def test_run_configuration_stays_fixed_and_wrong_master_key_fails(db):
    repo = PgModelSettings(db.app_dsn,Fernet.generate_key().decode())
    args = dict(base_url="https://api.deepseek.com",model_id="first",protocol="openai",api_key="test-key")
    repo.save(ACTOR_A1,expected_version=0,**args)
    container = _container(db)
    from app.domain.enums import AiRunNextAction, AiRunStatus
    from app.domain.runs.models import RunRecord
    container.plan_service._runs.create_run(RunRecord(run_id="settings-run",actor_id=ACTOR_A1,project_id=PROJECT_P1,
        kind="plan_generate",graph_name="planning",graph_version="1",status=AiRunStatus.RUNNING,next_action=AiRunNextAction.WAIT,version=1))
    selected = repo.bind_run(ACTOR_A1,PROJECT_P1,"settings-run")
    repo.save(ACTOR_A1,expected_version=1,**{**args,"model_id":"second"})
    assert selected.model_id == "first"
    assert repo.bind_run(ACTOR_A1,PROJECT_P1,"settings-run").model_id == "first"
    with pytest.raises(Exception,match="credential"):
        PgModelSettings(db.app_dsn,Fernet.generate_key().decode()).resolve(ACTOR_A1)
    repo.clear(ACTOR_A1,expected_version=2)
    with pytest.raises(Exception,match="credential"):
        repo.bind_run(ACTOR_A1,PROJECT_P1,"settings-run")
    with psycopg.connect(db.migrator_dsn) as conn:
        assert conn.execute("SELECT settings_version FROM ai_run_model_settings WHERE run_id='settings-run'").fetchone()[0] == 1


def test_http_model_settings_redaction_and_server_identity(db):
    from dataclasses import replace

    from app.application.model_settings import ModelSettingsService
    from app.main import create_app
    from fastapi.testclient import TestClient

    from tests.e2e.test_b2v_http_end_to_end import COOKIE, SESSION_A1, SESSION_A2
    container = _container(db)
    key = Fernet.generate_key().decode()
    service = ModelSettingsService(PgModelSettings(db.app_dsn,key),lambda url:url)
    container = replace(container,settings=replace(container.settings,model_settings_encryption_key=key),model_settings_service=service)
    with TestClient(create_app(container)) as client:
        assert client.get('/api/v1/model-settings').status_code == 401
        client.cookies.set(COOKIE,SESSION_A1)
        current = client.get('/api/v1/model-settings').json()
        body = dict(expected_version=current['version'],base_url='https://api.deepseek.com',model_id='http-model',api_key='private-http-secret')
        response = client.put('/api/v1/model-settings',json=body)
        assert response.status_code == 200, response.text
        assert 'private-http-secret' not in response.text
        assert response.json()['source'] == 'personal'
        assert client.put('/api/v1/model-settings',json=body).status_code == 409
        assert client.put('/api/v1/model-settings',json={**body,'actor_id':'another-actor'}).status_code == 422
        invalid = client.put('/api/v1/model-settings',json={**body,'api_key':{'secret':'do-not-echo'}})
        assert invalid.status_code == 422
        assert 'do-not-echo' not in invalid.text
        client.cookies.set(COOKIE,SESSION_A2)
        assert client.get('/api/v1/model-settings').json()['has_api_key'] is False


def test_per_run_factory_never_mutates_shared_model(db, monkeypatch):
    from dataclasses import replace

    from app.core.config import get_settings
    from app.domain.enums import AiRunNextAction, AiRunStatus
    from app.domain.runs.models import RunRecord
    from app.infrastructure.providers.runtime_factory import PersonalPlanningRuntimeFactory

    from tests.e2e.test_b2v_http_end_to_end import ACTOR_A2, PROJECT_P2, SESSION_A1, SESSION_A2
    repo = PgModelSettings(db.app_dsn,Fernet.generate_key().decode())
    for actor,model in [(ACTOR_A1,"actor-one"),(ACTOR_A2,"actor-two")]:
        current = repo.get(actor)
        repo.save(actor,expected_version=current.version if current else 0,base_url="https://api.deepseek.com",
                  model_id=model,protocol="openai",api_key="test-key")
    container = _container(db)
    for run,actor,project in [("runtime-one",ACTOR_A1,PROJECT_P1),("runtime-two",ACTOR_A2,PROJECT_P2)]:
        container.plan_service._runs.create_run(RunRecord(run_id=run,actor_id=actor,project_id=project,kind="plan_generate",
            graph_name="planning",graph_version="1",status=AiRunStatus.RUNNING,next_action=AiRunNextAction.WAIT,version=1))
    factory = PersonalPlanningRuntimeFactory(replace(get_settings(),database_url=db.app_dsn),repo)
    with ThreadPoolExecutor(2) as pool:
        a,b = list(pool.map(lambda args:factory(*args),[(container.sessions.resolve(SESSION_A1),PROJECT_P1,"runtime-one"),(container.sessions.resolve(SESSION_A2),PROJECT_P2,"runtime-two")]))
    assert a.llm.provider.model == "actor-one"
    assert b.llm.provider.model == "actor-two"
    assert a.llm.provider is not b.llm.provider
    assert a.executor is not b.executor


def test_personal_runtime_works_without_deployment_credentials(db):
    from dataclasses import replace

    from app.core.config import get_settings
    from app.domain.enums import AiRunNextAction, AiRunStatus
    from app.domain.runs.models import RunRecord
    from app.infrastructure.providers.runtime_factory import PersonalPlanningRuntimeFactory

    from tests.e2e.test_b2v_http_end_to_end import SESSION_A1
    repo = PgModelSettings(db.app_dsn,Fernet.generate_key().decode())
    current = repo.get(ACTOR_A1)
    repo.save(ACTOR_A1,expected_version=current.version if current else 0,base_url="https://api.deepseek.com",
              model_id="personal-only",protocol="openai",api_key="test-key")
    container = _container(db)
    container.plan_service._runs.create_run(RunRecord(run_id="personal-only-run",actor_id=ACTOR_A1,project_id=PROJECT_P1,
        kind="plan_generate",graph_name="planning",graph_version="1",status=AiRunStatus.RUNNING,next_action=AiRunNextAction.WAIT,version=1))
    settings = replace(get_settings(),database_url=db.app_dsn,llm_api_key="",llm_model_id="")
    runtime = PersonalPlanningRuntimeFactory(settings,repo)(container.sessions.resolve(SESSION_A1),PROJECT_P1,"personal-only-run")
    assert runtime.llm.provider.model == "personal-only"
    assert runtime.llm.provider.api_key == "test-key"


def test_pre_settings_deployment_attempt_replays_without_dispatch(db):
    import hashlib
    import json

    from app.domain.enums import AiRunNextAction, AiRunStatus
    from app.domain.runs.models import RunRecord
    from app.infrastructure.providers.attempt_ledger import PgAttemptLLM
    from app.infrastructure.providers.openai_compatible import OpenAICompatibleLLM


    run_id = "pre-settings-attempt"
    container = _container(db)
    container.plan_service._runs.create_run(RunRecord(run_id=run_id,actor_id=ACTOR_A1,project_id=PROJECT_P1,
        kind="plan_generate",graph_name="planning",graph_version="1",status=AiRunStatus.RUNNING,next_action=AiRunNextAction.WAIT,version=1))
    provider = OpenAICompatibleLLM(base_url="https://api.deepseek.com",api_key="test",model="legacy-model")
    calls = []
    def fail_if_dispatched(**kwargs):
        calls.append(kwargs)
        raise AssertionError("retained response must not redispatch")
    provider.generate_structured = fail_if_dispatched
    payload = {"goal":"Python","_project_id":PROJECT_P1}
    schema_name = "OutlineV1"
    fingerprint = hashlib.sha256(json.dumps(["planning.outline",payload,schema_name,provider.model,
        provider.prompt_version,provider.domain_pack],sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    from psycopg.types.json import Jsonb
    retained = dict(payload={"outline_ref":"old","sections":["foundation"]},model_id="legacy-model",provider="openai_compatible",
                    input_tokens=1,output_tokens=2,cost_micros=0,latency_ms=3,finish_reason="stop",attempts=1)
    with psycopg.connect(db.migrator_dsn) as conn:
        conn.execute("""INSERT INTO ai_provider_attempts(attempt_id,run_id,provider,model_id,prompt_version,status,
            request_fingerprint,schema_name,response_payload) VALUES (%s,%s,'openai_compatible',%s,%s,'succeeded',%s,%s,%s)""",
            ("legacy-a",run_id,provider.model,provider.prompt_version,fingerprint,schema_name,Jsonb(retained)))
    result = PgAttemptLLM(db.app_dsn,provider).generate_structured(purpose="planning.outline",payload=payload,
                    schema_name=schema_name,run_id=run_id,attempt_id="legacy-a")
    assert result.payload == retained["payload"]
    assert calls == []


def test_personal_settings_drive_http_real_graph_without_shared_provider(db, checkpoint_db, monkeypatch):
    import json
    from dataclasses import replace

    import httpx
    from app.infrastructure.checkpointer.planning_executor import PgPlanningExecutor
    from app.infrastructure.providers import runtime_factory as module
    from app.infrastructure.providers.openai_compatible import OpenAICompatibleLLM
    from app.infrastructure.providers.runtime_factory import UnconfiguredLLM
    from app.main import create_app
    from fastapi.testclient import TestClient

    from tests.e2e.test_b2v_http_end_to_end import (
        COOKIE,
        SESSION_A1,
        _approve_body,
        _decide,
        _generate_to_draft,
        _outline_handler,
        _practice_handler,
        _structure_handler,
    )
    repo = PgModelSettings(db.app_dsn,Fernet.generate_key().decode())
    old = repo.get(ACTOR_A1)
    repo.save(ACTOR_A1,expected_version=old.version if old else 0,base_url="https://api.deepseek.com",model_id="personal-http-model",protocol="openai",api_key="personal-request-key")
    calls = []
    handlers = {"planning.outline":_outline_handler,"planning.structure":_structure_handler,"planning.practice":_practice_handler}
    def reply(request):
        calls.append(request)
        assert request.headers["Authorization"] == "Bearer personal-request-key"
        content = json.loads(json.loads(request.content)["messages"][1]["content"])
        payload = handlers[content["purpose"]](content["purpose"],content["context"])
        return httpx.Response(200,json={"choices":[{"message":{"content":json.dumps(payload)}}]})
    def provider(**kwargs):
        return OpenAICompatibleLLM(**{**kwargs,"endpoint_guard":lambda url:url},client=httpx.Client(transport=httpx.MockTransport(reply)))
    monkeypatch.setattr(module,"OpenAICompatibleLLM",provider)
    container = _container(db)
    base = container.plan_service
    base._runtime_factory = module.PersonalPlanningRuntimeFactory(replace(container.settings,database_url=db.app_dsn,checkpoint_database_url=checkpoint_db.migrator_dsn),repo)
    base._executor = PgPlanningExecutor(checkpoint_db.migrator_dsn,llm=UnconfiguredLLM())
    with TestClient(create_app(container)) as client:
        client.cookies.set(COOKIE,SESSION_A1)
        run,draft = _generate_to_draft(client)
        assert _decide(client,draft['draft_id'],_approve_body(draft,0,'personal-approved')).status_code == 200
    assert len(calls) == 3
    with psycopg.connect(db.migrator_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM ai_run_model_settings WHERE run_id=%s AND actor_id=%s",(run['run_id'],ACTOR_A1)).fetchone()[0] == 1
        assert conn.execute("SELECT DISTINCT model_id FROM ai_provider_attempts WHERE run_id=%s",(run['run_id'],)).fetchall() == [('personal-http-model',)]
