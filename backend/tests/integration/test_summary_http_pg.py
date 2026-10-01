"""HTTP cookie/CSRF/owner boundaries over real isolated summary persistence."""
import psycopg
import pytest
from app.application.model_binding import SubmissionBinding
from app.application.planning_budget import BudgetPolicy
from app.infrastructure.providers.attempt_ledger import PgAttemptLLM
from app.main import create_app
from app.ports.llm import LLMResult
from fastapi.testclient import TestClient

from tests.e2e.test_b2v_http_end_to_end import migrated_db as migrated_db
from tests.integration.test_resource_changes_pg import scenario as scenario

pytestmark = pytest.mark.postgres


def login(client, db, scope):
    with psycopg.connect(db.migrator_dsn) as conn:
        username = conn.execute("SELECT username FROM auth_users WHERE actor_id=%s", (scope.actor_id,)).fetchone()[0]
    response = client.post("/api/v1/auth/login", json={"username": username,
        "password": "isolated resource replacement passphrase"})
    assert response.status_code == 200
    return {"X-CSRF-Token": response.json()["csrf_token"]}


def test_raw_history_replay_and_private_validation_http(scenario):
    db, scope, position, container, current = scenario
    query = {"project_id": position.project_id}
    target = {"plan_id": position.plan_id, "stage_id": position.stage_id,
              "unit_id": current.unit_links[0].unit_id}
    raw = " \n短总结🙂\t "
    with TestClient(create_app(container)) as client:
        headers = login(client, db, scope)
        body = {**target, "content": raw, "expected_version": 0, "idempotency_key": "http-save"}
        assert client.post("/api/v1/summaries", params=query, json=body).status_code == 403
        saved = client.post("/api/v1/summaries", params=query, headers=headers, json=body)
        assert saved.status_code == 200
        first = saved.json()["attempt"]
        assert first["content"] == raw
        assert client.get("/api/v1/summaries/attempts/" + first["attempt_id"], params=query).json()["content"] == raw
        second = client.post("/api/v1/summaries", params=query, headers=headers,
            json={**body, "content": "继续补写", "expected_version": 1, "idempotency_key": "http-save-2"})
        assert second.status_code == 200
        assert client.post("/api/v1/summaries", params=query, headers=headers, json=body).json()["attempt"] == first
        conflict = client.post("/api/v1/summaries", params=query, headers=headers,
            json={**body, "idempotency_key": "stale-new-key"})
        assert conflict.status_code == 409
        for changed in ({"actor_id": "spoof"}, {"content": {"private": "PRIVATE_VALIDATION_MARKER"}}):
            malformed = client.post("/api/v1/summaries", params=query, headers=headers, json={**body, **changed})
            assert malformed.status_code == 422
            assert "PRIVATE_VALIDATION_MARKER" not in malformed.text and raw not in malformed.text
        reviewed = client.post("/api/v1/summaries/attempts/" + first["attempt_id"] + "/review", params=query,
            headers=headers, json={"idempotency_key": "http-review", "consent_to_model": True})
        assert reviewed.status_code == 503  # No real model is substituted by this Fake deployment.
        page = client.get("/api/v1/summaries/history", params={**query, "limit": 1}).json()
        assert len(page["items"]) == 1 and page["next_cursor"]
        older = client.get("/api/v1/summaries/history", params={**query, "limit": 1, "cursor": page["next_cursor"]}).json()
        assert older["items"][0]["attempt_id"] == first["attempt_id"] and older["next_cursor"] is None
        assert client.get("/api/v1/summaries", params={**query, **target}).json()["version"] == 2


def test_cross_account_summary_and_history_http(scenario):
    db, scope, position, container, current = scenario
    query = {"project_id": position.project_id}
    target = {"plan_id": position.plan_id, "stage_id": position.stage_id,
              "unit_id": current.unit_links[0].unit_id}
    with TestClient(create_app(container)) as client:
        headers = login(client, db, scope)
        first = client.post("/api/v1/summaries", params=query, headers=headers,
            json={**target, "content": "只有账号A可见的原文", "expected_version": 0, "idempotency_key": "private-save"}).json()["attempt"]
        registered = client.post("/api/v1/auth/register", json={"username": "SummaryOther" + scope.actor_id[-10:],
            "password": "isolated summary second account passphrase"})
        assert registered.status_code == 200
        other_headers = {"X-CSRF-Token": registered.json()["csrf_token"]}
        assert client.get("/api/v1/summaries", params={**query, **target}).status_code == 403
        assert client.get("/api/v1/summaries/history", params=query).status_code == 403
        assert client.get("/api/v1/summaries/attempts/" + first["attempt_id"], params=query).status_code == 403
        assert client.post("/api/v1/summaries", params=query, headers=other_headers,
            json={**target, "content": "篡改", "expected_version": 1, "idempotency_key": "other"}).status_code == 403


def test_composed_worker_dispatches_summary_and_pins_older_original(scenario):
    """Real HTTP/PG/worker/ledger, explicitly synthetic model (no network)."""
    db, scope, position, container, current = scenario
    policy = BudgetPolicy(100, 100, 100, 100, 100, 100)

    class SyntheticReview:
        model = "synthetic-summary-fixture"
        prompt_version = "summary-review-v1"
        base_url = "https://fixture.invalid"
        configuration_ref = "test:summary-http"
        budget_policy = policy
        domain_pack = {}
        calls = 0

        def request_options(self, purpose):
            assert purpose == "summary.review"
            return {"model": self.model, "max_tokens": 100}

        def generate_structured(self, **kwargs):
            self.calls += 1
            assert kwargs["payload"]["content"] == "第一条已保存原文"
            return LLMResult({"conclusion": "needs_revision", "covered": ["测试替身说明覆盖"],
                "gaps": ["仅为离线测试反馈"], "misconceptions": [], "questions": ["继续核对边界？"]},
                self.model, "synthetic", input_tokens=1, output_tokens=1)

    provider = SyntheticReview()
    service = container.summary_service
    service.bind_submission = lambda *_: SubmissionBinding(provider.configuration_ref, policy)
    service.provider_resolver = lambda scope, project, run, ref, manifest: PgAttemptLLM(
        db.app_dsn, provider, manifest=manifest)
    query = {"project_id": position.project_id}
    target = {"plan_id": position.plan_id, "stage_id": position.stage_id,
              "unit_id": current.unit_links[0].unit_id}
    with TestClient(create_app(container)) as client:
        headers = login(client, db, scope)
        first = client.post("/api/v1/summaries", params=query, headers=headers,
            json={**target, "content": "第一条已保存原文", "expected_version": 0, "idempotency_key": "worker-save"}).json()["attempt"]
        review_url = "/api/v1/summaries/attempts/" + first["attempt_id"] + "/review"
        body = {"idempotency_key": "worker-review", "consent_to_model": True}
        submitted = client.post(review_url, params=query, headers=headers, json=body)
        assert submitted.status_code == 202
        receipt = submitted.json()
        assert client.get(receipt["status_url"]).json()["status"] == "queued"
        second = client.post("/api/v1/summaries", params=query, headers=headers,
            json={**target, "content": "反馈前已经保存的更新原文", "expected_version": 1, "idempotency_key": "worker-save-2"}).json()["attempt"]
        assert container.planning_worker.tick()
        assert provider.calls == 1
        assert client.get(receipt["status_url"]).json()["status"] == "succeeded"
        older = client.get("/api/v1/summaries/attempts/" + first["attempt_id"], params=query).json()
        assert older["review"]["run_id"] == receipt["run_id"] and older["content"] == first["content"]
        latest = client.get("/api/v1/summaries", params={**query, **target}).json()
        assert latest["attempts"][-1]["attempt_id"] == second["attempt_id"]
        assert latest["attempts"][-1]["content"] == second["content"] and latest["attempts"][-1]["review"] is None
        assert client.post(review_url, params=query, headers=headers, json=body).json() == receipt
        assert not container.planning_worker.tick() and provider.calls == 1
