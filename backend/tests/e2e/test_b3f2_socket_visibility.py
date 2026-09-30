"""20 complete nine-stage Agent runs through socket, PG, Fake and Worker."""

import json

import pytest

from tests.e2e import test_batched_agent_route as agent
from tests.e2e.test_batched_agent_route import agent_db as agent_db
from tests.e2e.test_batched_agent_route import checkpoint_db as checkpoint_db
from tests.helpers.planning_worker import configure_test_worker
from tests.helpers.socket_app import socket_client

pytestmark = pytest.mark.postgres


def test_twenty_runs_visible_without_retry(agent_db, checkpoint_db, capsys):
    app = agent._client(agent_db, checkpoint_db).app
    with socket_client(app) as client:
        session = agent._register(client, "socket连续二十次")
        project_id = session["project_ids"][0]
        scope = app.state.container.sessions.resolve(client.cookies.get(
            app.state.container.settings.session_cookie_name,
        ))
        assert scope is not None
        assert scope.actor_id and project_id in scope.learning_project_scope
        worker = configure_test_worker(client)
        suffix, headers = agent._scope(session)
        repository = app.state.container.plan_service._runs
        records = []
        for index in range(20):
            response = client.post("/api/v1/plans/generate" + suffix,
                                   json={"goal": agent.AGENT_GOAL}, headers=headers)
            assert response.status_code == 202, response.text
            run_id = response.json()["run_id"]
            queued = client.get("/api/v1/runs/" + run_id + suffix)
            assert queued.status_code == 200, queued.text
            assert queued.json()["status"] == "queued"
            assert worker.tick()
            # Same application role, same repository and RLS transaction as API.
            row = repository.get_run(project_id=project_id, run_id=run_id)
            assert row is not None and row.status.value == "waiting_user"
            assert row.project_id == project_id and row.actor_id == scope.actor_id
            with repository._tx(project_id) as conn:
                context = conn.execute("SELECT current_setting('app.project_id'), "
                                       "current_user, rolbypassrls FROM pg_roles "
                                       "WHERE rolname=current_user").fetchone()
                assert context["current_setting"] == project_id
                assert context["rolbypassrls"] is False
            view = client.get("/api/v1/runs/" + run_id + suffix)
            assert view.status_code == 200, view.text
            assert view.headers.get("x-request-id")
            run = view.json()
            assert run["status"] == "waiting_user"
            assert run["progress"]["total_stages"] == 9
            assert run["progress"]["completed_batches"] == 18
            draft = client.get("/api/v1/plans/drafts/" + run["result_ref"] + suffix)
            assert draft.status_code == 200, draft.text
            assert len(draft.json()["stages"]) == 9
            # Draft DTO's business node keys, no reduced fixture or graph.
            stored = app.state.container.plan_service._repo.get_draft(
                project_id=project_id, draft_id=run["result_ref"],
            )
            required = {key for stage in agent.load_pack(agent.AGENT_PACK)["stage_blueprints"]
                        for key in stage["node_keys"]}
            assert len(required) == 27
            assert required <= set(stored.node_stable_keys)
            records.append({"index": index + 1, "run_id": run_id,
                            "project_id": project_id, "actor_id": scope.actor_id,
                            "status": row.status.value, "version": row.version,
                            "http_status": view.status_code, "stages": 9, "coverage": 27})
        assert len(agent._fake(client).calls) == 20 * 19
        assert len(records) == 20
        from app.tools.b3f2_inspect import inspect_run
        report = inspect_run(agent_db.app_dsn, actor_id=scope.actor_id,
                             project_id=project_id, run_id=records[-1]["run_id"])
        assert report["draft_stage_count"] == 9 and report["required_node_coverage"] == 27
        assert report["input_token_subtotal"] is None and report["usage_complete"] is False
        missing = client.get("/api/v1/runs/does-not-exist" + suffix)
        assert missing.status_code == 404 and "code" in missing.json()
        forbidden = client.get("/api/v1/runs/" + records[-1]["run_id"] + "?project_id=other")
        assert forbidden.status_code == 403
        # Only non-secret diagnostic facts, printable with pytest -s.
        with capsys.disabled():
            print(json.dumps({"runs": records, "passed": 20, "not_found": 0}, ensure_ascii=False))
