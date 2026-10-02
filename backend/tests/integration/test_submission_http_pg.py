"""Real Cookie/CSRF boundary and exact unknown-request recovery on isolated PG."""
from dataclasses import asdict

import psycopg
import pytest
from app.main import create_app
from fastapi.testclient import TestClient

from tests.e2e.test_b2v_http_end_to_end import migrated_db as migrated_db  # noqa: F401
from tests.integration.test_practice_submissions_pg import decision
from tests.integration.test_practice_submissions_pg import (
    submission_scenario as submission_scenario,  # noqa: F401
)
from tests.integration.test_prompts_pg import prompt_scenario as prompt_scenario  # noqa: F401
from tests.integration.test_prompts_pg import resource_scenario as resource_scenario  # noqa: F401
from tests.integration.test_summary_http_pg import login

pytestmark = pytest.mark.postgres


def body(command):
    value = asdict(command)
    value.pop("project_id")
    return value


def test_submission_cookie_csrf_private_422_and_no_spoofing(submission_scenario):
    db, scope, command, container, _ = submission_scenario
    query = {"project_id": command.project_id}
    with TestClient(create_app(container)) as client:
        assert client.get("/api/v1/outcomes", params=query).status_code == 401
        headers = login(client, db, scope)
        thread = client.get("/api/v1/submissions", params={**query, **dict(zip(("plan_id", "stage_id", "task_id"), command.position[1:], strict=True))})
        assert thread.status_code == 200 and thread.json()["version"] == 0
        original = body(command)
        assert client.post("/api/v1/submissions", params=query, json=original).status_code == 403
        for invalid in (
            {"note": {"private": "PRIVATE_SUBMISSION_422"}},
            {"expected_version": True}, {"expected_task_version": "1"},
            {"actor_id": "spoof"}, {"evidence_grade": "verified"},
            {"verification": {"method": "platform"}},
        ):
            response = client.post("/api/v1/submissions", params=query, headers=headers, json={**original, **invalid})
            assert response.status_code == 422
            assert "PRIVATE_SUBMISSION_422" not in response.text and command.note not in response.text
    with psycopg.connect(db.migrator_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM practice_submissions WHERE project_id=%s", (command.project_id,)).fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM ai_runs WHERE project_id=%s", (command.project_id,)).fetchone()[0] == 0


def test_manual_decision_requires_saved_criteria_and_retains_originals(submission_scenario):
    db, scope, command, container, _ = submission_scenario
    query = {"project_id": command.project_id}
    with TestClient(create_app(container)) as client:
        headers = login(client, db, scope)
        response = client.post("/api/v1/submissions", params=query, headers=headers, json=body(command))
        assert response.status_code == 200
        saved = response.json()
        assert saved["submission"]["note"] == command.note
        assert saved["submission"]["evidence_grade"] == "reported"
        assert not saved["submission"]["verification_available"]
        path = "/api/v1/submissions/" + saved["submission"]["submission_id"] + "/decision"
        manual = body(decision(command, saved))
        manual.pop("submission_id")
        assert client.post(path, params=query, json=manual).status_code == 403
        assert client.post(path, params=query, headers=headers, json={**manual, "reviewer_kind": "model"}).status_code == 422
        assert client.post(path, params=query, headers=headers, json={**manual, "acknowledge_verification_limit": False}).status_code == 400
        assert client.post(path, params=query, headers=headers, json={**manual, "coverage": []}).status_code == 400
        accepted = client.post(path, params=query, headers=headers, json=manual)
        assert accepted.status_code == 200
        result = accepted.json()
        assert result["task_status"] == "accepted" and result["manual_confirmation"]
        assert result["submission"]["review"]["reviewer_kind"] == "user"
        assert result["submission"]["evidence_grade"] == "reported"
        assert client.post(path, params=query, headers=headers, json=manual).json() == result
        history = client.get("/api/v1/submissions/history", params=query).json()
        assert history["items"] == [result["submission"]]
        archive = client.get("/api/v1/outcomes", params=query)
        assert archive.status_code == 200
        groups = archive.json()["groups"]
        assert len(groups) == 7 and sum(g["total_records"] for g in groups) == 1
        item = next(g for g in groups if g["kind"] == "evaluation")["items"][0]
        assert item["manual_confirmation"] and item["evidence_grade"] == "reported"
    with psycopg.connect(db.migrator_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM ai_runs WHERE project_id=%s", (command.project_id,)).fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM learning_exposures WHERE project_id=%s", (command.project_id,)).fetchone()[0] == 0


def test_exact_receipts_recover_after_new_plan_but_new_old_plan_actions_conflict(submission_scenario):
    from app.domain.practice_changes import PracticeChangeCommand
    from app.infrastructure.db.practice_changes import PgPracticeChanges

    db, scope, command, container, current = submission_scenario
    query = {"project_id": command.project_id}
    with TestClient(create_app(container)) as client:
        headers = login(client, db, scope)
        saved_response = client.post("/api/v1/submissions", params=query, headers=headers, json=body(command))
        assert saved_response.status_code == 200
        saved = saved_response.json()
        manual = body(decision(command, saved))
        manual.pop("submission_id")
        path = "/api/v1/submissions/" + saved["submission"]["submission_id"] + "/decision"
        accepted_response = client.post(path, params=query, headers=headers, json=manual)
        assert accepted_response.status_code == 200
        changes = PgPracticeChanges(db.app_dsn)
        preview = changes.preview(scope, PracticeChangeCommand(command.project_id, command.plan_id,
            saved["thread"]["practice_project"]["practice_project_id"], "New main", "New manually chosen project",
            None, (), current.version, "keep_history_only", "http-preview-after-submission"))
        published = changes.decide(scope, command.project_id, preview["proposal_id"], "confirm", current.version,
            preview["preview_hash"], "http-confirm-after-submission", True)
        assert published["plan_id"] != command.plan_id
        assert client.post("/api/v1/submissions", params=query, headers=headers, json=body(command)).json() == saved
        assert client.post(path, params=query, headers=headers, json=manual).json() == accepted_response.json()
        assert client.post("/api/v1/submissions", params=query, headers=headers,
            json={**body(command), "idempotency_key": "new-old-save"}).status_code == 409
        assert client.post(path, params=query, headers=headers,
            json={**manual, "idempotency_key": "new-old-decision"}).status_code == 409
        assert client.get(path.removesuffix("/decision"), params=query).json() == accepted_response.json()["submission"]


def test_submission_and_outcome_owner_boundaries_include_receipt_replays(submission_scenario):
    db, scope, command, container, _ = submission_scenario
    query = {"project_id": command.project_id}
    with TestClient(create_app(container)) as client:
        headers = login(client, db, scope)
        saved = client.post("/api/v1/submissions", params=query, headers=headers, json=body(command))
        assert saved.status_code == 200
        item = saved.json()["submission"]
        registration = client.post("/api/v1/auth/register", json={
            "username": "SubmissionOther" + scope.actor_id[-10:],
            "password": "submitpass1"})
        assert registration.status_code == 200
        other_headers = {"X-CSRF-Token": registration.json()["csrf_token"]}
        for endpoint in ("/api/v1/outcomes", "/api/v1/submissions/history", "/api/v1/submissions/" + item["submission_id"]):
            assert client.get(endpoint, params=query).status_code == 403
        assert client.post("/api/v1/submissions", params=query, headers=other_headers, json=body(command)).status_code == 403
        manual = body(decision(command, saved.json()))
        manual.pop("submission_id")
        assert client.post("/api/v1/submissions/" + item["submission_id"] + "/decision", params=query,
            headers=other_headers, json=manual).status_code == 403
