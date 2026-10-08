"""Owned PG / checkpoint / real auth HTTP; every external port is synthetic."""
import json
from dataclasses import replace
from types import SimpleNamespace
from uuid import uuid4

import pytest
from app import main
from app.application.container import AppContainer
from app.application.plan_service import PlanService
from app.core.config import get_settings
from app.domain.planning.content_coverage import ReviewedContentIndex
from app.domain.planning.curriculum_compiler import CurriculumSourceFacts
from app.domain.planning.resource_research import ResearchBudget
from app.infrastructure.db.browser_auth import PgBrowserAuth
from app.infrastructure.db.job_repository import PgPlanningJobRepository
from app.infrastructure.db.plan_repository import PgPlanRepository
from app.infrastructure.db.public_resource_catalog import PgPublicResourceCatalog
from app.infrastructure.db.run_repository import PgRunRepository
from app.infrastructure.db.v2_planning_persistence import PgV2PlanningPersistence
from app.infrastructure.providers.runtime_factory import OwnedV2PlanningRuntimeFactory
from app.infrastructure.worker.planning_worker import PlanningWorker
from fastapi.testclient import TestClient

from backend.tests.integration.test_v2_planning_http_pg import ForbiddenDispatch
from backend.tests.integration.test_v2_planning_runtime_pg import (
    EVIDENCE,
    PipelineBodies,
    PipelineProvider,
    PipelineSearch,
)
from backend.tests.integration.test_v2_planning_runtime_pg import checkpoint_db as checkpoint_fixture
from backend.tests.integration.test_v2_planning_runtime_pg import db as owned_fixture

pytestmark = pytest.mark.postgres
db = owned_fixture
checkpoint_db = checkpoint_fixture


def test_owned_http_202_worker_draft_confirm_current_history(db, checkpoint_db, monkeypatch):
    auth = PgBrowserAuth(db.app_dsn, 3600)
    token = auth.register("v2runtime_" + uuid4().hex[:12], "pytest42", "owned-test")
    scope = auth.resolve(token)
    project = scope.learning_project_scope[0]
    provider, search, bodies = PipelineProvider(), PipelineSearch(), PipelineBodies()
    facts = CurriculumSourceFacts(ReviewedContentIndex("empty", (), (), ()))
    factory = OwnedV2PlanningRuntimeFactory(db.app_dsn, checkpoint_db.app_dsn,
        source_facts=facts, budget=ResearchBudget(max_output_tokens=32768,
            max_total_requests=20, max_cost_micros=1000000),
        binding_resolver=lambda scope, project: SimpleNamespace(model_ref="test:frozen"),
        provider_resolver=lambda scope, project, run, ref: provider,
        github=search, body_reader=bodies)
    jobs = PgPlanningJobRepository(db.app_dsn, actor_ids=(scope.actor_id,))
    bridge = PgV2PlanningPersistence(db.app_dsn)
    service = PlanService(repository=PgPlanRepository(db.app_dsn), runs=PgRunRepository(db.app_dsn),
        catalog=ForbiddenDispatch(), resources=PgPublicResourceCatalog(db.app_dsn),
        llm=ForbiddenDispatch(), graph_version="", planning_jobs=jobs,
        v2_persistence=bridge, v2_runtime_factory=factory)
    worker = PlanningWorker(jobs=jobs, execute=service.execute_generation, actor_ids=(scope.actor_id,))
    settings = replace(get_settings(), app_env="development", session_cookie_secure=False)
    monkeypatch.setattr(main, "get_settings", lambda: settings)
    container = AppContainer(settings=settings, sessions=auth, browser_auth=auth,
        plan_service=service, planning_worker=worker)
    with TestClient(main.create_app(container)) as client:
        path, params = "/api/v1/plans/v2/owned/generate", {"project_id": project}
        payload = {"goal": "学习MCP"}
        assert client.post(path, params=params, json=payload).status_code == 401
        client.cookies.set(settings.session_cookie_name, token)
        assert client.post(path, params=params, json=payload).status_code == 403
        headers = {"X-CSRF-Token": auth.detail(token)[0]["csrf_token"]}
        assert client.post(path, params={"project_id": "not-owned"}, headers=headers,
                           json=payload).status_code == 403
        response = client.post(path, params=params, headers=headers, json=payload)
        assert response.status_code == 202
        submission = response.json()
        queued = client.get(submission["status_url"])
        assert queued.status_code == 200 and queued.json()["status"] == "queued"
        assert provider.calls == search.calls == bodies.calls == []
        assert worker.tick() is True
        finished = client.get(submission["status_url"])
        assert finished.status_code == 200
        run = finished.json()
        assert run["status"] == "succeeded", run
        assert run["next_action"] == "none"
        draft_path = "/api/v1/plans/drafts/" + run["result_ref"]
        draft_response = client.get(draft_path, params=params)
        assert draft_response.status_code == 200
        draft = draft_response.json()
        assert draft["v2_content"]["stages"]
        dispatches = (len(provider.calls), len(search.calls), len(bodies.calls))
        assert worker.tick() is False
        decision = {"decision": "approve", "expected_version": 0,
                    "draft_hash": draft["draft_hash"], "idempotency_key": "http-p3-confirm"}
        approved = client.post(draft_path + "/decision", params=params, headers=headers, json=decision)
        assert approved.status_code == 200
        plan = approved.json()["plan"]
        current = client.get("/api/v1/plans/current", params=params)
        history = client.get("/api/v1/plans/revisions/1", params=params)
        assert current.status_code == history.status_code == 200
        assert current.json() == history.json() == plan
        assert client.post("/api/v1/plans/generate", params=params, headers=headers,
                           json=payload).status_code == 503
        assert dispatches == (len(provider.calls), len(search.calls), len(bodies.calls))
        EVIDENCE.joinpath("http-runtime-readback.json").write_text(json.dumps({
            "authentication_csrf_scope": "PASS", "submission": submission,
            "queued": queued.json(), "finished": run, "draft": draft, "plan": plan,
            "current_history_equal": True, "synthetic_dispatch_counts": dispatches,
            "post_completion_dispatch_delta": 0, "public_generate_status": 503,
            "real_product_calls": 0}, ensure_ascii=False, indent=2), encoding="utf8")
