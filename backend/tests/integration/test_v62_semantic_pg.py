"""v6.2 semantic acceptance through ordinary cookie/CSRF HTTP, worker/Fake, owned PG.

No Plan/Draft injection, provider calls, product database or global role changes.
The module fixture publishes an old plan before seeding the next immutable packs.
"""
import json
import os
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import psycopg
import pytest
from app.composition import build_container
from app.core.config import get_settings
from app.core.ids import new_id
from app.domain.domain_packs.validation import seed_digest
from app.infrastructure.domain_pack import CURRENT_PACKS, load_pack
from app.main import create_app
from app.tools.seed_b3 import seed_reviewed_pack
from fastapi.testclient import TestClient

from tests.e2e.test_b2v_http_end_to_end import migrated_db as migrated_db  # noqa: F401

pytestmark = pytest.mark.postgres
ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "var/v62"
OLD = {"agent.application": "agent-application-v4.json", "ai.fullstack": "ai-fullstack-v1.json", "cloud.services": "cloud-services-v1.json"}



def settings_for(db, **kwargs):
    return replace(get_settings(), database_url=db.app_dsn, llm_provider="fake", local_session_token="", planning_worker_admission_mode="trusted_server", **kwargs)


def register(client, prefix="v62"):
    username = prefix + new_id("usr")[-12:]
    response = client.post("/api/v1/auth/register", json={"username": username, "password": "Test-pass1!"})
    assert response.status_code == 200, response.text
    return username, {"project_id": response.json()["project_ids"][0]}, {"X-CSRF-Token": response.json()["csrf_token"]}


def generate(client, container, params, headers, goal):
    response = client.post("/api/v1/plans/generate", params=params, headers=headers, json={"goal": goal, "goal_spec": {"target": goal, "starting_point": "有基础编程认知；初学者"}})
    assert response.status_code == 202, response.text
    assert container.planning_worker.tick()
    run = client.get(response.json()["status_url"]).json()
    assert (run["status"], run["next_action"]) == ("succeeded", "none"), run
    url = "/api/v1/plans/drafts/" + run["result_ref"]
    draft = client.get(url, params=params).json()
    return run, url, draft


def confirm(client, params, headers, url, draft):
    # Every scenario has a fresh registered project: optimistic version is the
    # current published plan version (zero), not the draft's own edit version.
    body = {"decision": "approve", "expected_version": 0, "draft_hash": draft["draft_hash"], "idempotency_key": "v62-confirm"}
    response = client.post(url + "/decision", params=params, headers=headers, json=body)
    assert response.status_code == 200, response.text
    assert client.post(url + "/decision", params=params, headers=headers, json=body).json() == response.json()
    plan = response.json()["plan"]
    for field in ("source_pack_key", "source_pack_version", "goal_spec"):
        assert plan[field] == draft[field], field
    # Publication materializes new stage/assignment/extension IDs. Compare every
    # semantic field and task/unit reference after aligning the stable stage key.
    def semantic_rows(snapshot, field):
        stage_keys = {s["stage_id"]: s["stable_key"] for s in snapshot["stages"]}
        return [{**{k: v for k, v in row.items() if k not in {"stage_id", "assignment_id", "extension_id"}}, "stage_key": stage_keys[row["stage_id"]]} for row in snapshot[field]]
    for field in ("stages", "stage_resources", "extensions", "unit_links", "task_links"):
        assert semantic_rows(plan, field) == semantic_rows(draft, field), field
    assert client.get("/api/v1/plans/current", params=params).json() == plan
    return plan


@pytest.fixture(scope="module")
def semantic_db(migrated_db):
    # Prevent dedicated-instance opt-in from authorizing global role mutation here.
    from tests.pg_harness import roles_created_by_harness
    assert not roles_created_by_harness()
    with psycopg.connect(migrated_db.migrator_dsn) as conn:
        for filename in OLD.values():
            seed_reviewed_pack(conn, load_pack(filename))
    container = build_container(settings_for(migrated_db))
    from tests.helpers.frozen_planning import install_frozen_generation
    install_frozen_generation(container.plan_service, load_pack(OLD["agent.application"]))
    with TestClient(create_app(container)) as client:
        username, params, headers = register(client, "v62old")
        _, url, draft = generate(client, container, params, headers, "零基础系统学 Agent，后面重点 RAG。")
        assert draft["source_pack_version"] == 4
        old_plan = confirm(client, params, headers, url, draft)
    with psycopg.connect(migrated_db.migrator_dsn) as conn:
        for key in OLD:
            data = load_pack(CURRENT_PACKS[key])
            assert data["version"] > load_pack(OLD[key])["version"]
            assert data.get("semantic_policy", {}).get("version") in {1, 2}
            seed_reviewed_pack(conn, data)
            seed_reviewed_pack(conn, data)
    yield migrated_db, username, params, old_plan


def test_seed_immutable_hold_excluded_and_old_snapshot_unchanged(semantic_db):
    db, username, params, old_plan = semantic_db
    catalog = json.loads((ROOT / "docs/research/semantic-corrected-2026-10-04/RESOURCE_CATALOG_NORMALIZED_DRAFT.json").read_text(encoding="utf-8-sig"))
    rows = catalog.get("resources", catalog.get("items", []))
    holds = [r for r in rows if str(r.get("public_seed_status", "")).startswith("hold_")]
    assert len(holds) == 4
    with psycopg.connect(db.migrator_dsn) as conn:
        for key in OLD:
            data = load_pack(CURRENT_PACKS[key])
            stored = conn.execute("SELECT published_payload FROM domain_packs WHERE pack_key=%s AND version=%s", (key, data["version"])).fetchone()[0]
            assert stored == data
            for source in stored["resources"]:
                assert not source.get("public_seed_status", "").startswith("hold_")
                assert source.get("metadata", {}).get("stable_key") not in {r["stable_key"] for r in holds}
                assert source.get("metadata", {}).get("scope_key") not in {r["scope_key"] for r in holds}
            changed = deepcopy(data)
            changed["title"] += " modified"
            with pytest.raises(ValueError, match="Immutable"):
                seed_reviewed_pack(conn, changed)
            conn.rollback()
    fresh = build_container(settings_for(db))
    with TestClient(create_app(fresh)) as client:
        assert client.post("/api/v1/auth/login", json={"username": username, "password": "Test-pass1!"}).status_code == 200
        assert client.get("/api/v1/plans/current", params=params).json() == old_plan
        assert client.get("/api/v1/workspace", params=params).json()["plan"] == old_plan
        assert not fresh.planning_worker.tick() and not fresh.plan_service._llm.calls
