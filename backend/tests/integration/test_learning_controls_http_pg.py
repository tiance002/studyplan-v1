"""Current-plan controls through real HTTP/session/PG, without external calls."""
from dataclasses import replace

import psycopg
import pytest
from app.application.learning_resources import LearningResourceService
from app.composition import build_container
from app.core.config import get_settings
from app.domain.enums import MediaType, ResourceProvenance, ResourceVerificationStatus
from app.domain.resources.models import ResourceRecord
from app.infrastructure.db.learning_resources import PgLearningResources
from app.main import create_app
from fastapi.testclient import TestClient

from tests.e2e.test_b2v_http_end_to_end import migrated_db as migrated_db
from tests.integration.test_resource_preferences_pg import preference_scenario as preference_scenario

pytestmark = pytest.mark.postgres


class OfflineSearch:
    """Inspectable adapter double; never contacts an external search service."""
    def __init__(self):
        self.queries = []

    def find(self, query):
        self.queries.append(query)
        return [ResourceRecord(resource_id="text-candidate", project_id=query.extra["project_id"],
                    url="https://docs.python.org/3/", title="Text", media_type=MediaType.TEXT, language="en",
                    provenance=ResourceProvenance.SEARCH_CANDIDATE, verification_status=ResourceVerificationStatus.UNVERIFIED),
                ResourceRecord(resource_id="video-candidate", project_id=query.extra["project_id"],
                    url="https://example.com/video", title="Video", media_type=MediaType.VIDEO, language="fr",
                    provenance=ResourceProvenance.SEARCH_CANDIDATE, verification_status=ResourceVerificationStatus.UNVERIFIED)]


def test_controls_http_projection_history_preferences_and_frozen_submission(preference_scenario):
    db, scope, targets, _ = preference_scenario
    first, second, node = targets
    settings = replace(get_settings(), database_url=db.app_dsn, llm_provider="fake", local_session_token="",
                       planning_worker_admission_mode="trusted_server")
    container = build_container(settings)
    index = OfflineSearch()
    container = replace(container, resource_service=LearningResourceService(PgLearningResources(db.app_dsn), index,
        1000, preference_resolver=container.preference_service.resolve))
    project = first["project_id"]
    params = {"project_id": project}
    body = {key: value for key, value in first.items() if key not in {"project_id", "node_id"}}
    with TestClient(create_app(container)) as client:
        client.cookies.set(settings.session_cookie_name, container.browser_auth.issue(scope.actor_id))
        headers = {"X-CSRF-Token": client.get("/api/v1/session").json()["csrf_token"]}
        listing = client.get("/api/v1/exposures", params={**params, "plan_id": first["plan_id"]})
        assert listing.status_code == 200, listing.text
        assert all(item["version"] == 0 and not item["recorded"] for item in listing.json())
        changing = dict(body, status="in_progress", expected_version=0, idempotency_key="http-exposure-start")
        assert client.put("/api/v1/exposures", params=params, json=changing).status_code == 403
        changed = client.put("/api/v1/exposures", params=params, json=changing, headers=headers)
        assert changed.status_code == 200, changed.text
        replay = client.put("/api/v1/exposures", params=params, json=changing, headers=headers)
        assert replay.status_code == 200 and replay.json()["replayed"]
        history = client.get("/api/v1/exposures/history", params={**params, **body})
        assert history.status_code == 200 and len(history.json()) == 1
        workspace = client.get("/api/v1/workspace", params=params).json()
        units = {u["unit_id"]: u for stage in workspace["stages"] for u in stage["units"]}
        assert units[first["unit_id"]]["progress"] == "in_progress"
        assert units[first["unit_id"]]["exposure_version"] == 1
        assert units[second["unit_id"]]["exposure_version"] == 0
        assert all(n["progress"] is None for stage in workspace["stages"] for n in stage["nodes"])
        setting = dict(body, scope="project", mode="text_first", language="en", official_priority=False,
                       pace="slow", expected_version=0)
        saved = client.put("/api/v1/preferences", params=params, json=setting, headers=headers)
        assert saved.status_code == 200, saved.text
        local = dict(setting, scope="node", node_id=node["node_id"], mode="video_first", language="fr")
        assert client.put("/api/v1/preferences", params=params, json=local, headers=headers).status_code == 200
        search_body = dict(body, node_id=node["node_id"], query="Learning sources", idempotency_key="node-preference-search")
        search = client.post("/api/v1/resources/searches", params=params, json=search_body, headers=headers)
        assert search.status_code == 200, search.text
        assert search.json()["status"] == "succeeded", search.text
        assert search.json()["candidates"][0]["resource_id"] == "video-candidate"
        assert index.queries[0].preference.scope_ref == node["node_id"]
        restoring = dict(body, node_id=node["node_id"], scope="node", expected_version=1)
        restored = client.request("DELETE", "/api/v1/preferences", params=params, json=restoring, headers=headers)
        assert restored.status_code == 200, restored.text
        assert restored.json()["effective"]["language"] == "en"
        assert restored.json()["node"] is None and restored.json()["versions"]["node"] == 2
        cached = client.post("/api/v1/resources/searches", params=params, json=search_body, headers=headers)
        assert cached.status_code == 200 and cached.json() == search.json() and len(index.queries) == 1
        search_body["idempotency_key"] = "project-preference-search"
        searched_again = client.post("/api/v1/resources/searches", params=params, json=search_body, headers=headers)
        assert searched_again.status_code == 200 and searched_again.json()["candidates"][0]["resource_id"] == "text-candidate"
        assert index.queries[-1].preference.language == "en"
        stale = client.put("/api/v1/preferences", params=params, json=local, headers=headers)
        assert stale.status_code == 409
        generated = client.post("/api/v1/plans/generate", params=params,
                                json={"goal": "学习Agent应用开发"}, headers=headers)
        assert generated.status_code == 202, generated.text
        run_id = generated.json()["run_id"]
        updated = dict(setting, expected_version=1, language="zh")
        assert client.put("/api/v1/preferences", params=params, json=updated, headers=headers).status_code == 200
    with psycopg.connect(db.migrator_dsn) as conn:
        row = conn.execute("SELECT detail FROM ai_run_events WHERE run_id=%s AND status='submission'", (run_id,)).fetchone()
        assert row[0]["initial"]["prefs_snapshot"] == {"mode": "text_first", "language": "en",
                                            "official_priority": False, "pace": "slow"}
        assert conn.execute("SELECT count(*) FROM learning_exposure_events WHERE project_id=%s",
                            (project,)).fetchone()[0] == 1
