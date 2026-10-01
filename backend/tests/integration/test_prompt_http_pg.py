"""Real cookie/CSRF/PG Prompt originals, pinned feedback and versioned exports."""
import psycopg
import pytest
from app.application.model_binding import SubmissionBinding
from app.application.planning_budget import BudgetPolicy
from app.infrastructure.providers.attempt_ledger import PgAttemptLLM
from app.main import create_app
from app.ports.llm import LLMResult
from fastapi.testclient import TestClient

from tests.e2e.test_b2v_http_end_to_end import migrated_db as migrated_db
from tests.integration.test_prompts_pg import prompt_scenario as prompt_scenario
from tests.integration.test_prompts_pg import resource_scenario as resource_scenario
from tests.integration.test_summary_http_pg import login

pytestmark = pytest.mark.postgres


def target(command):
    return {"plan_id": command.plan_id, "stage_id": command.stage_id, "task_id": command.task_id}


def save(client, query, headers, command, raw, *, version=0, key="http-prompt-save"):
    response = client.post("/api/v1/prompts", params=query, headers=headers,
        json={**target(command), "user_draft": raw, "expected_version": version, "idempotency_key": key})
    assert response.status_code == 200
    return response.json()


def test_prompt_raw_exports_history_csrf_and_private_errors_http(prompt_scenario):
    db, scope, command, container, _ = prompt_scenario
    query = {"project_id": command.project_id}
    raw = " \n用户的短方案🙂\t "
    with TestClient(create_app(container)) as client:
        headers = login(client, db, scope)
        body = {**target(command), "user_draft": raw, "expected_version": 0, "idempotency_key": "http-prompt-save"}
        assert client.post("/api/v1/prompts", params=query, json=body).status_code == 403
        first = save(client, query, headers, command, raw)
        revision = first["revision"]
        assert revision["user_draft"] == raw
        assert first["thread"]["task"]["task_id"] == command.task_id
        assert first["thread"]["practice_project"]["title"]
        second = save(client, query, headers, command, "已保存的新方案", version=1, key="http-prompt-save-2")
        assert client.post("/api/v1/prompts", params=query, headers=headers, json=body).json()["revision"] == revision
        assert client.post("/api/v1/prompts", params=query, headers=headers,
            json={**body, "idempotency_key": "stale-save"}).status_code == 409
        for changed in ({"actor_id": "spoof"}, {"user_draft": {"private": "PRIVATE_PROMPT_VALIDATION"}}):
            malformed = client.post("/api/v1/prompts", params=query, headers=headers, json={**body, **changed})
            assert malformed.status_code == 422
            assert "PRIVATE_PROMPT_VALIDATION" not in malformed.text and raw not in malformed.text
        exports_url = "/api/v1/prompts/revisions/" + revision["revision_id"] + "/exports"
        export_body = {"format": "raw", "idempotency_key": "first-raw-export"}
        exported = client.post(exports_url, params=query, headers=headers, json=export_body)
        assert exported.status_code == 200
        export = exported.json()
        assert export["export_text"] == raw and export["revision_id"] == revision["revision_id"]
        assert client.post(exports_url, params=query, headers=headers, json=export_body).json() == export
        assert client.get("/api/v1/prompts/exports/" + export["export_id"], params=query).json() == export
        assert client.post(exports_url, params=query, headers=headers,
            json={**export_body, "format": "implementation"}).status_code == 409
        implementation = client.post(exports_url, params=query, headers=headers,
            json={"format": "implementation", "idempotency_key": "first-implementation-export"})
        assert implementation.status_code == 200
        assert raw in implementation.json()["export_text"]
        assert first["thread"]["task"]["title"] in implementation.json()["export_text"]
        page = client.get("/api/v1/prompts/history", params={**query, "limit": 1}).json()
        assert page["items"][0]["revision_id"] == second["revision"]["revision_id"] and page["next_cursor"]
        older = client.get("/api/v1/prompts/history", params={**query, "limit": 1, "cursor": page["next_cursor"]}).json()
        assert older["items"][0]["user_draft"] == raw and older["next_cursor"] is None
        reviewed = client.post("/api/v1/prompts/revisions/" + revision["revision_id"] + "/review",
            params=query, headers=headers, json={"consent_to_model": True, "idempotency_key": "unconfigured-review"})
        assert reviewed.status_code == 503
    with psycopg.connect(db.migrator_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM ai_runs WHERE project_id=%s", (command.project_id,)).fetchone()[0] == 0


def test_prompt_revision_and_exports_are_owner_scoped_http(prompt_scenario):
    db, scope, command, container, _ = prompt_scenario
    query = {"project_id": command.project_id}
    with TestClient(create_app(container)) as client:
        headers = login(client, db, scope)
        revision = save(client, query, headers, command, "账号A保存的原始方案")["revision"]
        exports_url = "/api/v1/prompts/revisions/" + revision["revision_id"] + "/exports"
        export = client.post(exports_url, params=query, headers=headers,
            json={"format": "raw", "idempotency_key": "owner-export"}).json()
        registration = client.post("/api/v1/auth/register", json={"username": "PromptOther" + scope.actor_id[-10:],
            "password": "isolated prompt second account passphrase"})
        assert registration.status_code == 200
        other_headers = {"X-CSRF-Token": registration.json()["csrf_token"]}
        for path in ("/api/v1/prompts/history", "/api/v1/prompts/revisions/" + revision["revision_id"],
                     "/api/v1/prompts/exports/" + export["export_id"]):
            assert client.get(path, params=query).status_code == 403
        assert client.get("/api/v1/prompts", params={**query, **target(command)}).status_code == 403
        assert client.post(exports_url, params=query, headers=other_headers,
            json={"format": "raw", "idempotency_key": "cross-account-export"}).status_code == 403


def test_composed_prompt_worker_pins_feedback_and_export_to_older_revision(prompt_scenario):
    db, scope, command, container, _ = prompt_scenario
    policy = BudgetPolicy(100, 100, 100, 100, 100, 100)

    class SyntheticPromptReview:
        model = "synthetic-prompt-fixture"
        prompt_version = "prompt-review-v1"
        base_url = "https://fixture.invalid"
        configuration_ref = "test:prompt-http"
        budget_policy = policy
        domain_pack = {}
        calls = 0

        def request_options(self, purpose):
            assert purpose == "prompt.review"
            return {"model": self.model, "max_tokens": 100}

        def generate_structured(self, **kwargs):
            self.calls += 1
            assert "第一版已保存方案" in kwargs["payload"].values()
            return LLMResult({"strengths": ["明确的离线测试输入"], "gaps": ["尚需实际实施"],
                "suggestions": ["补充一个可检查交付物"]}, self.model, "synthetic", input_tokens=1, output_tokens=1)

    provider = SyntheticPromptReview()
    service = container.prompt_service
    service.bind_submission = lambda *_: SubmissionBinding(provider.configuration_ref, policy)
    service.provider_resolver = lambda scope, project, run, ref, manifest: PgAttemptLLM(
        db.app_dsn, provider, manifest=manifest)
    query = {"project_id": command.project_id}
    with TestClient(create_app(container)) as client:
        headers = login(client, db, scope)
        first = save(client, query, headers, command, "第一版已保存方案")["revision"]
        revision_url = "/api/v1/prompts/revisions/" + first["revision_id"]
        review_body = {"consent_to_model": True, "idempotency_key": "composed-prompt-review"}
        submitted = client.post(revision_url + "/review", params=query, headers=headers, json=review_body)
        assert submitted.status_code == 202
        receipt = submitted.json()
        assert client.get(receipt["status_url"]).json()["status"] == "queued"
        second = save(client, query, headers, command, "反馈回来之前的新方案", version=1, key="composed-newer")["revision"]
        assert container.planning_worker.tick() and provider.calls == 1
        assert client.get(receipt["status_url"]).json()["status"] == "succeeded"
        retained = client.get(revision_url, params=query).json()
        assert retained["user_draft"] == first["user_draft"] and retained["review"]["run_id"] == receipt["run_id"]
        thread = client.get("/api/v1/prompts", params={**query, **target(command)}).json()
        assert thread["revisions"][-1]["revision_id"] == second["revision_id"]
        assert thread["revisions"][-1]["review"] is None
        exported = client.post(revision_url + "/exports", params=query, headers=headers,
            json={"format": "raw", "idempotency_key": "composed-older-export"})
        assert exported.status_code == 200 and exported.json()["export_text"] == first["user_draft"]
        assert client.post(revision_url + "/review", params=query, headers=headers, json=review_body).json() == receipt
        assert not container.planning_worker.tick() and provider.calls == 1
