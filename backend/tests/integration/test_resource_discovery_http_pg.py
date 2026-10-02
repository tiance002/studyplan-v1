"""Normal cookie/CSRF HTTP + real PG; GitHub upstream is an explicit offline fixture."""
from dataclasses import replace

import psycopg
import pytest
from app.composition import build_container
from app.core.config import get_settings
from app.main import create_app
from fastapi.testclient import TestClient

from tests.e2e.test_b2v_http_end_to_end import migrated_db as migrated_db
from tests.integration.test_learning_resources_pg import scenario as scenario
from tests.integration.test_resource_discovery_pg import GitHubFixture, app

pytestmark = pytest.mark.postgres


def test_explicit_node_survives_http_inspection_recovery_private_mapping_and_refresh(scenario):
    db, scope, target = scenario
    with psycopg.connect(db.migrator_dsn) as conn:
        node = conn.execute("SELECT node_id FROM unit_node_links WHERE project_id=%s AND unit_id=%s LIMIT 1",
                            (target["project_id"], target["unit_id"])).fetchone()[0]
    settings = replace(get_settings(), database_url=db.app_dsn, llm_provider="fake", local_session_token="")
    upstream = GitHubFixture()
    service = app(db, upstream)
    container = replace(build_container(settings), resource_service=service)
    params = dict(target, node_id=node)
    body_position = {key: value for key, value in params.items() if key != "project_id"}
    with TestClient(create_app(container)) as client:
        client.cookies.set(settings.session_cookie_name, container.browser_auth.issue(scope.actor_id))
        headers = {"X-CSRF-Token": client.get("/api/v1/session").json()["csrf_token"]}
        search_body = dict(body_position, query="RAG", source="github", idempotency_key="http-node-search")
        assert client.post("/api/v1/resources/searches", params={"project_id":target["project_id"]}, json=search_body).status_code == 403
        first = client.post("/api/v1/resources/searches", params={"project_id":target["project_id"]}, headers=headers, json=search_body)
        assert first.status_code == 200, first.text
        search = first.json()
        allowed = search["context_snapshot"]["module_keys"]
        assert allowed and upstream.calls == 1
        assert client.get("/api/v1/resources/searches/" + search["search_id"], params=params).json() == search
        assert client.get("/api/v1/resources/searches/" + search["search_id"], params=target).status_code == 404
        inspect_body = dict(body_position, search_id=search["search_id"], candidate_id="candidate-1", idempotency_key="http-node-inspection")
        response = client.post("/api/v1/resources/inspections", params={"project_id":target["project_id"]}, headers=headers, json=inspect_body)
        assert response.status_code == 200, response.text
        inspected = response.json()
        assert inspected["status"] == "succeeded" and upstream.reads == 1
        assert client.get("/api/v1/resources/inspections/by-key/http-node-inspection", params=params).json() == inspected
        assert client.post("/api/v1/resources/inspections", params={"project_id":target["project_id"]}, headers=headers, json=inspect_body).json() == inspected
        assert upstream.reads == 1
        selection_body = dict(body_position, search_id=search["search_id"], candidate_id="candidate-1",
                              module_keys=allowed[:1], chapter_paths=["ch1.md"], role="supplement")
        forged = client.post("/api/v1/resources/selections", params={"project_id":target["project_id"]}, headers=headers,
                             json=dict(selection_body, module_keys=["foreign.module"]))
        assert forged.status_code == 400, forged.text
        selected_response = client.post("/api/v1/resources/selections", params={"project_id":target["project_id"]}, headers=headers, json=selection_body)
        assert selected_response.status_code == 200, selected_response.text
        selected = selected_response.json()
        assert selected["resource"]["discovery"]["selection_mapping"]["module_keys"] == allowed[:1]
        assert selected["resource"]["verification_status"] == "unverified"
        assert client.get("/api/v1/resources/selections", params=params).json() == [selected]
    # A new HTTP process/session reads the exact retained selection; no upstream dispatch.
    with TestClient(create_app(container)) as refreshed:
        refreshed.cookies.set(settings.session_cookie_name, container.browser_auth.issue(scope.actor_id))
        assert refreshed.get("/api/v1/resources/selections", params=params).json() == [selected]
    assert upstream.calls == upstream.reads == 1
    with TestClient(create_app(container)) as anonymous:
        assert anonymous.get("/api/v1/resources/inspections/" + inspected["inspection_id"], params=params).status_code == 401
