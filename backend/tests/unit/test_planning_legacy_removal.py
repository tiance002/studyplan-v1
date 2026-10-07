"""Breaking cleanup: public generation refuses before every side effect."""
from dataclasses import replace
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.application.container import AppContainer
from app.application.plan_service import PlanService
from app.application.sessions import InMemorySessionStore, SessionRecord
from app.core.config import get_settings
from app.core.errors import DependencyUnavailableError, ForbiddenError
from app.domain.workspace.models import AuthContext
from app.infrastructure.db.generated_plan_changes import PgGeneratedPlanChanges
from app.main import create_app


class NoSideEffects:
    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        def forbidden(*args, **kwargs):
            self.calls.append(name)
            pytest.fail(f"Unexpected side effect or dependency access: {name}")
        return forbidden

    def __call__(self, *args, **kwargs):
        self.calls.append("binding/runtime")
        pytest.fail("Must reject before binding or runtime construction")


def scope():
    return AuthContext("cleanup-actor", "cleanup-session", datetime.now(timezone.utc), ("cleanup-project",))


def service():
    denied = NoSideEffects()
    instance = PlanService(repository=denied, runs=denied, catalog=denied,
        resources=denied, llm=denied, graph_version="b3f2-short-v2",
        planning_jobs=denied, binding_resolver=denied, runtime_factory=denied,
        preference_resolver=denied, route_changes=denied,
        planning_worker_admission_mode="trusted_server")
    return instance, denied


@pytest.mark.parametrize("method", ["generate", "submit_generation"])
def test_generation_rejects_before_run_job_binding_provider_or_plan_access(method):
    instance, denied = service()
    with pytest.raises(DependencyUnavailableError, match="学习计划生成正在升级"):
        getattr(instance, method)(scope=scope(), project_id="cleanup-project", goal="任意新目标")
    assert denied.calls == []


@pytest.mark.parametrize("method", ["generate", "submit_generation"])
def test_project_scope_still_precedes_generation_error(method):
    instance, denied = service()
    with pytest.raises(ForbiddenError):
        getattr(instance, method)(scope=scope(), project_id="foreign-project", goal="任意目标")
    assert denied.calls == []


def test_generated_route_change_has_no_preparation_or_existing_run_bypass():
    instance, denied = service()
    with pytest.raises(DependencyUnavailableError):
        instance.submit_generation(scope=scope(), project_id="cleanup-project", goal="新目标",
            route_command=SimpleNamespace(project_id="cleanup-project"))
    adapter = PgGeneratedPlanChanges("postgresql://unused/unused")
    with pytest.raises(DependencyUnavailableError):
        adapter.prepare(scope(), SimpleNamespace(project_id="cleanup-project"))
    assert denied.calls == []


def test_api_boot_and_generation_fail_closed_without_any_storage_access(monkeypatch):
    instance, denied = service()
    settings = replace(get_settings(), app_env="development", llm_provider="fake",
        database_url="", database_url_sync="", local_session_token="",
        session_cookie_secure=False)
    monkeypatch.setattr("app.main.get_settings", lambda: settings)
    sessions = InMemorySessionStore((SessionRecord("cleanup-cookie", "cleanup-actor",
        "cleanup-session", ("cleanup-project",)),))
    container = AppContainer(settings=settings, sessions=sessions, plan_service=instance)
    app = create_app(container)
    assert "/api/v1/plans/generate" in app.openapi()["paths"]
    with TestClient(app) as client:
        assert client.get("/healthz").status_code == 200
        assert client.post("/api/v1/plans/generate", params={"project_id": "cleanup-project"},
            json={"goal": "新目标"}).status_code == 401
        client.cookies.set(settings.session_cookie_name, "cleanup-cookie")
        response = client.post("/api/v1/plans/generate", params={"project_id": "cleanup-project"},
            json={"goal": "新目标"})
        assert response.status_code == 503
        assert response.json()["code"] == "dependency_unavailable"
        assert response.json()["message"] == "学习计划生成正在升级，当前暂不可创建新路线。"
        assert denied.calls == []
        assert client.get("/api/v1/session").status_code == 200
        instance._runs = SimpleNamespace(list_runs=lambda **kwargs: ())
        instance._repo = SimpleNamespace(get_current=lambda **kwargs: None)
        assert client.get("/api/v1/runs", params={"project_id": "cleanup-project"}).json() == []
        assert client.get("/api/v1/plans/current", params={"project_id": "cleanup-project"}).status_code == 404
    assert denied.calls == []


def test_retired_checkpoint_protocol_is_rejected_before_database_access():
    from app.infrastructure.checkpointer.planning_executor import builder_for_version
    from app.ports.graph_runner import GraphRecoveryError
    with pytest.raises(GraphRecoveryError):
        builder_for_version("b3f2-batch-v1")
    assert callable(builder_for_version("b3f2-short-v2"))


def test_published_plan_without_snapshot_does_not_reread_current_catalog():
    from app.core.errors import ConflictError
    instance, denied = service()
    with pytest.raises(ConflictError) as exc:
        instance._resolve([SimpleNamespace(assignment_id="fixture-assignment")], [],
            require_snapshot=True)
    assert exc.value.details["reason"] == "resource_snapshot_missing"
    assert denied.calls == []


def test_markerless_merge_and_structure_are_rejected():
    from app.agent_workflows.planning_batches import merge_batches
    from app.agent_workflows.planning_structure import check_frozen_structure
    rejected = merge_batches({}, [], [], {}, manifest={})
    assert rejected["errors"]
    assert rejected["nodes"] == rejected["units"] == []
    with pytest.raises(ValueError):
        check_frozen_structure({"manifest": {}, "domain_pack": {}})


def test_composition_still_wires_nonplanning_services_without_sql(monkeypatch):
    import psycopg
    from app.composition import build_container
    denied = NoSideEffects()
    monkeypatch.setattr(psycopg, "connect", denied)
    settings = replace(get_settings(), app_env="development", llm_provider="fake",
        database_url="postgresql://unused/unused", local_session_token="",
        github_discovery_enabled=False, search_provider="")
    container = build_container(settings)
    for name in ("plan_service", "browser_auth", "resource_service", "assistant_service",
                 "summary_service", "prompt_service", "practice_submission_service"):
        assert getattr(container, name) is not None
    # No old planning demo is installed as a fallback by application composition.
    from app.infrastructure.providers.fake import FakeLLM
    assert isinstance(container.plan_service._llm, FakeLLM)
    assert not container.plan_service._llm._handlers
    assert denied.calls == []
