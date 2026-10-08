"""Real owned PG and real cookie/CSRF resolution; no provider dispatch."""
import json
from dataclasses import replace
from uuid import uuid4

import pytest
from app import main
from app.application.container import AppContainer
from app.application.plan_service import PlanService
from app.core.config import get_settings
from app.infrastructure.db.browser_auth import PgBrowserAuth
from app.infrastructure.db.plan_repository import PgPlanRepository
from app.infrastructure.db.public_resource_catalog import PgPublicResourceCatalog
from app.infrastructure.db.run_repository import PgRunRepository
from app.infrastructure.db.v2_planning_persistence import PgV2PlanningPersistence
from fastapi.testclient import TestClient

from backend.tests.integration.test_v2_planning_persistence_pg import EVIDENCE
from backend.tests.integration.test_v2_planning_persistence_pg import db as owned_db_fixture
from backend.tests.unit.test_curriculum_compiler import inputs

pytestmark = pytest.mark.postgres
db = owned_db_fixture


class ForbiddenDispatch:
    def __getattr__(self, name):
        raise AssertionError("No product dispatch authorized")


def test_owned_cookie_csrf_scope_edit_confirm_current_history(db, monkeypatch):
    auth = PgBrowserAuth(db.app_dsn, 3600)
    # Synthetic local account; credentials and tokens never enter evidence.
    token = auth.register("v2http_" + uuid4().hex[:12], "pytest42", "owned-test")
    scope = auth.resolve(token)
    project = scope.learning_project_scope[0]
    curriculum, arguments = inputs(project="已有本地CLI", excluded=True)
    bridge = PgV2PlanningPersistence(db.app_dsn, allow_unbound_preview=True)
    draft = bridge.persist(scope=scope, project_id=project, run_id="", expected_version=0,
                           curriculum=curriculum, **arguments)
    settings = replace(get_settings(), app_env="development", session_cookie_secure=False)
    monkeypatch.setattr(main, "get_settings", lambda: settings)
    service = PlanService(repository=PgPlanRepository(db.app_dsn), runs=PgRunRepository(db.app_dsn),
        catalog=ForbiddenDispatch(), resources=PgPublicResourceCatalog(db.app_dsn),
        llm=ForbiddenDispatch(), graph_version="", v2_persistence=bridge)
    container = AppContainer(settings=settings, sessions=auth, browser_auth=auth, plan_service=service)
    with TestClient(main.create_app(container)) as client:
        path = f"/api/v1/plans/drafts/{draft.draft_id}"
        params = {"project_id": project}
        assert client.get(path, params=params).status_code == 401
        client.cookies.set(settings.session_cookie_name, token)
        response = client.get(path, params=params)
        assert response.status_code == 200
        original = response.json()
        assert original["v2_content"]["practice"]["carrier"]["kind"] == "user_project"
        assert client.get(path, params={"project_id": "not-owned"}).status_code == 403
        decision = {"decision": "approve", "expected_version": 0,
                    "draft_hash": original["draft_hash"], "idempotency_key": "http-confirm"}
        assert client.post(path + "/decision", params=params, json=decision).status_code == 403
        csrf = {"X-CSRF-Token": auth.detail(token)[0]["csrf_token"]}
        assert client.post(path + "/decision", params=params, json=decision,
                           headers=csrf | {"Origin": "https://not-trusted.invalid"}).status_code == 403
        stages = [stage | {"title": stage["title"] + " · 我的课程"} for stage in original["stages"]]
        response = client.post(path + "/decision", params=params, headers=csrf,
            json={"decision": "edit", "expected_version": 0,
                  "draft_hash": original["draft_hash"], "edited_stages": stages})
        assert response.status_code == 200
        edited = response.json()["draft"]
        assert edited["draft_hash"] != original["draft_hash"]
        assert client.post(path + "/decision", params=params, headers=csrf, json=decision).status_code == 409
        decision["draft_hash"] = edited["draft_hash"]
        response = client.post(path + "/decision", params=params, headers=csrf, json=decision)
        assert response.status_code == 200
        plan = response.json()["plan"]
        assert plan["stages"][0]["title"] == stages[0]["title"]
        current = client.get("/api/v1/plans/current", params=params)
        history = client.get("/api/v1/plans/revisions/1", params=params)
        assert current.status_code == history.status_code == 200
        assert current.json() == history.json() == plan
        assert client.get("/api/v1/plans/revisions/1", params={"project_id": "not-owned"}).status_code == 403
        assert client.post("/api/v1/plans/generate", params=params, headers=csrf,
                           json={"goal": "synthetic goal"}).status_code == 503
        EVIDENCE.joinpath("http-readback.json").write_text(json.dumps({
            "authentication": "PASS", "CSRF": "PASS", "project_scope": "PASS",
            "edited_draft": edited, "published_plan": plan, "fresh_current_history": "PASS",
            "public_generate": "503", "product_calls": 0}, ensure_ascii=False, indent=2), encoding="utf-8")
