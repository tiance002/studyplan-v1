"""Cookie/CSRF, private errors and explicit decisions on real isolated PG."""
from dataclasses import asdict

import psycopg
import pytest
from app.main import create_app
from fastapi.testclient import TestClient

from tests.e2e.test_b2v_http_end_to_end import migrated_db as migrated_db  # noqa: F401
from tests.integration.test_practice_changes_pg import practice_scenario as practice_scenario  # noqa: F401
from tests.integration.test_prompts_pg import prompt_scenario as prompt_scenario  # noqa: F401
from tests.integration.test_prompts_pg import resource_scenario as resource_scenario  # noqa: F401
from tests.integration.test_summary_http_pg import login

pytestmark = pytest.mark.postgres


def preview_body(command):
    body = asdict(command)
    body.pop("project_id")
    return body


def test_practice_preview_requires_csrf_and_never_echoes_private_input(practice_scenario):
    db, scope, command, container, current = practice_scenario
    query = {"project_id": command.project_id}
    with TestClient(create_app(container)) as client:
        headers = login(client, db, scope)
        context = client.get("/api/v1/practice-changes/context", params=query)
        assert context.status_code == 200
        assert context.json()["plan_id"] == current.plan_id
        body = preview_body(command)
        assert client.post("/api/v1/practice-changes", params=query, json=body).status_code == 403
        for malformed in ({"idea": {"private": "PRIVATE_PRACTICE_422"}},
                          {"expected_version": True}, {"actor_id": "spoof"}):
            response = client.post("/api/v1/practice-changes", params=query, headers=headers,
                                   json={**body, **malformed})
            assert response.status_code == 422
            assert "PRIVATE_PRACTICE_422" not in response.text and command.idea not in response.text
        with psycopg.connect(db.migrator_dsn) as conn:
            assert conn.execute("SELECT count(*) FROM practice_change_proposals WHERE project_id=%s",
                                (command.project_id,)).fetchone()[0] == 0
            assert conn.execute("SELECT count(*) FROM ai_runs WHERE project_id=%s",
                                (command.project_id,)).fetchone()[0] == 0


def test_practice_preview_explicit_confirm_replay_and_history_http(practice_scenario):
    db, scope, command, container, current = practice_scenario
    query = {"project_id": command.project_id}
    with TestClient(create_app(container)) as client:
        headers = login(client, db, scope)
        response = client.post("/api/v1/practice-changes", params=query, headers=headers,
                               json=preview_body(command))
        assert response.status_code == 200
        preview = response.json()
        assert preview["after"]["title"] == command.title
        assert client.get("/api/v1/practice-changes/context", params=query).json()["plan_id"] == current.plan_id
        path = "/api/v1/practice-changes/" + preview["proposal_id"]
        assert client.get(path, params=query).json() == preview
        decision = {"expected_version": command.expected_version, "preview_hash": preview["preview_hash"],
                    "idempotency_key": "http-practice-confirm", "acknowledge_warnings": True}
        assert client.post(path + "/confirm", params=query, json=decision).status_code == 403
        if preview["warnings"]:
            assert client.post(path + "/confirm", params=query, headers=headers,
                               json={**decision, "acknowledge_warnings": False}).status_code == 400
        result = client.post(path + "/confirm", params=query, headers=headers, json=decision)
        assert result.status_code == 200
        assert result.json()["created"] and result.json()["revision"] == current.revision + 1
        assert client.post(path + "/confirm", params=query, headers=headers, json=decision).json() == result.json()
        assert client.get(path, params=query).json()["status"] == "confirmed"
        assert client.get("/api/v1/practice-changes/context", params=query).json()["plan_id"] == result.json()["plan_id"]
        assert client.post(path + "/cancel", params=query, headers=headers, json=decision).status_code == 409
    with psycopg.connect(db.migrator_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM plan_task_links WHERE project_id=%s AND plan_id=%s",
                            (command.project_id, current.plan_id)).fetchone()[0] == len(current.task_links)
        assert conn.execute("SELECT count(*) FROM ai_runs WHERE project_id=%s",
                            (command.project_id,)).fetchone()[0] == 0


def test_practice_context_preview_decision_owner_scoped_http(practice_scenario):
    db, scope, command, container, current = practice_scenario
    query = {"project_id": command.project_id}
    with TestClient(create_app(container)) as client:
        headers = login(client, db, scope)
        response = client.post("/api/v1/practice-changes", params=query, headers=headers,
                               json=preview_body(command))
        assert response.status_code == 200
        preview = response.json()
        registration = client.post("/api/v1/auth/register", json={
            "username": "PracticeOther" + scope.actor_id[-10:],
            "password": "isolated practice second account passphrase"})
        assert registration.status_code == 200
        other_headers = {"X-CSRF-Token": registration.json()["csrf_token"]}
        path = "/api/v1/practice-changes/" + preview["proposal_id"]
        for endpoint in ("/api/v1/practice-changes/context", path):
            assert client.get(endpoint, params=query).status_code == 403
        assert client.post("/api/v1/practice-changes", params=query, headers=other_headers,
                           json=preview_body(command)).status_code == 403
        for action in ("confirm", "cancel"):
            assert client.post(path + "/" + action, params=query, headers=other_headers, json={
                "expected_version": command.expected_version, "preview_hash": preview["preview_hash"],
                "idempotency_key": "cross-owner", "acknowledge_warnings": True}).status_code == 403
