"""HTTP routing/DTO guards only; real cookie/PG acceptance is separate."""

from dataclasses import replace
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from app import main
from app.api.v1.deps import get_auth_context
from app.application.container import AppContainer
from app.core.config import get_settings
from app.domain.workspace.models import AuthContext
from fastapi.testclient import TestClient


@pytest.fixture
def app(monkeypatch):
    settings = replace(get_settings(), app_env="development", session_cookie_secure=False)
    monkeypatch.setattr(main, "get_settings", lambda: settings)
    container = AppContainer(settings=settings, sessions=SimpleNamespace(resolve=lambda token: None),
                             v2_revision_service=SimpleNamespace())
    application = main.create_app(container)
    application.dependency_overrides[get_auth_context] = lambda: AuthContext(
        "synthetic", "offline", datetime.now(timezone.utc), ("p",)
    )
    return application


def test_v2_local_change_has_explicit_preview_and_confirmation_routes(app):
    paths = app.openapi()["paths"]
    assert "/api/v1/plans/v2/changes/local" in paths
    assert "/api/v1/plans/v2/changes/{draft_id}/confirm" in paths
    assert "/api/v1/plans/v2/changes/{draft_id}/cancel" in paths


def test_v2_local_request_cannot_self_declare_semantics_or_coerce_version(app):
    with TestClient(app) as client:
        body = {"current_plan_id": "plan", "expected_version": 1,
                "idempotency_key": "key", "stage_edits": []}
        for extra in ({"is_semantic": False}, {"expected_version": True},
                      {"goal_spec": {"target": "a new goal"}}, {"source_override": "fake"}):
            result = client.post("/api/v1/plans/v2/changes/local", params={"project_id": "p"},
                                 json=body | extra)
            assert result.status_code == 422


def test_semantic_replan_has_an_owned_route_and_requires_explicit_goal_spec(app):
    assert "/api/v1/plans/v2/owned/replan" in app.openapi()["paths"]
    with TestClient(app) as client:
        body = {"current_plan_id": "plan", "expected_version": 1,
                "idempotency_key": "new-run", "goal_spec": {"target": "学习新的目标"}}
        for changed in ({"goal_spec": None}, {"expected_version": True}, {"model_ref": "other"},
                        {"budget": {"max_total_requests": 500}}, {"is_semantic": False},
                        {"goal_spec": {"target": "新目标", "accepted_known": ["python"]}}):
            assert client.post("/api/v1/plans/v2/owned/replan", params={"project_id": "p"},
                               json=body | changed).status_code == 422
