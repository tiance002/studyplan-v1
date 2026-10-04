"""v6.7 owned PG acceptance; ordinary cookie/CSRF submission and synthetic history.

No provider/network calls, product DB writes or global role changes. The only
historical fixture is a newly owned markerless queued run, never a real Run.
"""
import json
from copy import deepcopy
from pathlib import Path

import psycopg
import pytest
from app.agent_workflows.planning_batches import DEFAULT_BUDGET, freeze_manifest, manifest_is_intact
from app.composition import build_container
from app.core.ids import new_id
from app.domain.enums import AiRunNextAction, AiRunStatus
from app.domain.planning.semantic_content import adapt_semantic_pack
from app.domain.runs.models import RunRecord
from app.infrastructure.domain_pack import CURRENT_PACKS, load_pack
from app.main import create_app
from app.tools.seed_b3 import seed_reviewed_pack
from fastapi.testclient import TestClient

from tests.e2e.test_b2v_http_end_to_end import migrated_db as migrated_db  # noqa: F401
from tests.integration.test_v62_semantic_pg import confirm, register, settings_for
from tests.pg_harness import instance_is_dedicated, roles_created_by_harness

pytestmark = pytest.mark.postgres
# Stop at collection, before the imported migrated_db fixture can ensure_roles.
assert not instance_is_dedicated(), "v6.7 forbids global role mutation opt-in"
ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "var/v67"
GOAL = "我已经有一个旅行规划 Agent，希望系统补 Agent 基础，并强化网页信息获取、可恢复规划和知识检索。"


@pytest.fixture(scope="module")
def projection_db(migrated_db):
    assert not instance_is_dedicated(), "v6.7 forbids global role mutation opt-in"
    assert not roles_created_by_harness()
    assert migrated_db.name.startswith("studyplan_test_")
    with psycopg.connect(migrated_db.migrator_dsn) as conn:
        seed_reviewed_pack(conn, load_pack(CURRENT_PACKS["agent.application"]))
    yield migrated_db
    assert not roles_created_by_harness()


def submission(db, run_id):
    with psycopg.connect(db.migrator_dsn) as conn:
        return conn.execute("SELECT detail FROM ai_run_events WHERE run_id=%s AND detail->>'kind'='planning_submission'", (run_id,)).fetchone()[0]


def capture_fake(container):
    seen = []
    llm = container.plan_service._llm
    for purpose, handler in list(llm._handlers.items()):
        def record(kind, payload, original=handler):
            seen.append((kind, deepcopy(payload)))
            return original(kind, payload)
        llm.register(purpose, record)
    return seen


def save_evidence(name, **data):
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / ("pg-" + name + ".json")).write_text(json.dumps(dict(status="PASS", requested_model="gpt-6.1-sol", requested_effort="medium", actual_resolution="NOT OBSERVABLE", provider="Fake", real_provider_requests=0, global_role_mutations=0, **data), ensure_ascii=False, indent=2), encoding="utf-8")


def finish_draft(client, container, params, run_id):
    assert container.planning_worker.tick()
    run = client.get("/api/v1/runs/" + run_id, params=params).json()
    assert (run["status"], run["next_action"]) == ("succeeded", "none"), run
    url = "/api/v1/plans/drafts/" + run["result_ref"]
    response = client.get(url, params=params)
    assert response.status_code == 200, response.text
    return url, response.json()


def test_new_submission_freezes_projection_and_rehydrates_confirmed_plan(projection_db):
    db = projection_db
    settings = settings_for(db)
    first = build_container(settings)
    with TestClient(create_app(first)) as client:
        username, params, headers = register(client, "v67new")
        queued = client.post("/api/v1/plans/generate", params=params, headers=headers,
            json={"goal": GOAL, "goal_spec": {"target": GOAL, "starting_point": "有基础编程认知；初学者"}})
        assert queued.status_code == 202, queued.text
        run_id = queued.json()["run_id"]
        assert not first.plan_service._llm.calls
        frozen = submission(db, run_id)
        manifest = frozen["initial"]["manifest"]
        assert manifest == frozen["manifest"]
        assert manifest["outline_input_format"] == "stage_skeleton_v1"
        assert manifest_is_intact(manifest)
        changed = deepcopy(manifest)
        changed.pop("outline_input_format")
        assert not manifest_is_intact(changed)
        assert client.post("/api/v1/auth/logout", headers=headers).status_code == 200

    # Queued persisted work survives a process restart and consumes its frozen marker.
    fresh = build_container(settings)
    seen = capture_fake(fresh)
    with TestClient(create_app(fresh)) as client:
        login = client.post("/api/v1/auth/login", json={"username": username, "password": "Test-pass1!"})
        assert login.status_code == 200
        headers = {"X-CSRF-Token": login.json()["csrf_token"]}
        url, draft = finish_draft(client, fresh, params, run_id)
        assert submission(db, run_id) == frozen
        outline = next(payload for kind, payload in seen if kind == "planning.outline")
        assert outline["_outline_input_format"] == "stage_skeleton_v1"
        assert "frozen_stages" in outline
        assert not ({"domain_pack", "manifest", "resources", "publication_evidence", "practice_blueprints", "extensions", "learning_guidance"} & set(outline))
        payload_chars = len(json.dumps(outline, ensure_ascii=False))
        # This ordinary beginner submission selects 27 stages. Per-stage bounds
        # complement the dedicated six-stage wire guard in the unit suite.
        assert payload_chars <= 1000 + 800 * len(manifest["stages"])
        pack = frozen["initial"]["domain_pack"]
        stage_ids = {s["stable_key"]: s["stage_id"] for s in draft["stages"]}
        assert list(stage_ids) == [s["stable_key"] for s in pack["stage_blueprints"]]
        sources = {s["source_id"]: s for s in pack["resources"]}
        resource_count = section_count = 0
        for stage in pack["stage_blueprints"]:
            actual_stage = next(s for s in draft["stages"] if s["stable_key"] == stage["stable_key"])
            expected_guide = next(s for s in manifest["stages"] if s["stage_key"] == stage["stable_key"])["learning_guidance"]
            assert actual_stage["learning_guidance"] == expected_guide
            for expected in stage.get("resources", []):
                source = sources[expected["source_ref"]]
                sections = {s["section_id"]: s for s in source["sections"]}
                reviewed = source["verification_status"] == "reviewed" and all(sections[r]["verification_status"] == "reviewed" for r in expected["section_refs"])
                rows = [r for r in draft["stage_resources"] if r["stage_id"] == stage_ids[stage["stable_key"]] and r["role"] == expected["role"]]
                if reviewed or expected["role"] == "case_study":
                    row = next(r for r in rows if r["source_ref"] == expected["source_ref"])
                    assert [s["section_id"] for s in row["ordered_sections"]] == expected["section_refs"]
                    assert row["source_version"] == expected["source_version"]
                    section_count += len(expected["section_refs"])
                else:
                    assert any(not r["source_ref"] and not r["ordered_sections"] and r["fallback_search_terms"] for r in rows)
                resource_count += 1
            for expected in stage.get("extensions", []):
                rows = [e for e in draft["extensions"] if e["stage_id"] == stage_ids[stage["stable_key"]] and e["topic"] == expected["topic"]]
                assert rows and rows[0]["guidance"] == expected["guidance"]
                assert rows[0]["required"] == expected.get("required", False)
        assert all(not s.get("public_seed_status", "").startswith("hold_") for s in pack["resources"])
        plan = confirm(client, params, headers, url, draft)
        with psycopg.connect(db.migrator_dsn) as conn:
            persisted_nodes = {row[0]: row for row in conn.execute(
                "SELECT stable_key,title,objectives FROM knowledge_nodes WHERE project_id=%s", (params["project_id"],)).fetchall()}
            rubrics = [row[0] for row in conn.execute(
                "SELECT rubric FROM learning_units WHERE project_id=%s", (params["project_id"],)).fetchall()]
            persisted_tasks = {row[0]: row for row in conn.execute(
                "SELECT stable_key,goal,in_scope,out_scope,acceptance FROM practice_tasks WHERE project_id=%s", (params["project_id"],)).fetchall()}
        knowledge = {key: item for rubric in rubrics for key, item in rubric["canonical_knowledge"].items()}
        practice = {key: item for rubric in rubrics for key, item in rubric["canonical_practice"].items()}
        selected_keys = {key for stage in manifest["stages"] for key in stage["node_keys"]}
        assert set(knowledge) == selected_keys
        for node in pack["knowledge_blueprints"]:
            key = node["stable_key"]
            if key not in selected_keys:
                continue
            assert persisted_nodes[key][1:] == (node["title"], node["objectives"])
            for field in ("stable_key", "title", "node_type", "objectives", "scope", "acceptance", "parent_key", "prerequisite_keys"):
                if field in node:
                    assert knowledge[key][field] == node[field], (key, field)
            assert knowledge[key]["scope"] and knowledge[key]["acceptance"]
        expected_tasks = {b["stable_key"] for b in pack["practice_blueprints"] if b["section_key"] in stage_ids}
        assert set(practice) == set(persisted_tasks) == expected_tasks
        for key, task in practice.items():
            assert persisted_tasks[key][1:] == (task["goal"], task["in_scope"], task["out_scope"], task["acceptance"])
        assert not fresh.planning_worker.tick()
        assert {kind for kind, _ in seen} >= {"planning.outline", "planning.structure", "planning.practice"}
        assert all("旅行规划 Agent" in s["learning_guidance"]["practice_delta"]["baseline"] for s in plan["stages"])
    save_evidence("projection", database=db.name, run_id=run_id, manifest_hash=manifest["manifest_hash"], marker=manifest["outline_input_format"], stage_count=len(manifest["stages"]), queued_restart_marker="PASS", outline_payload_chars=payload_chars, payload_ceiling=1000 + 800 * len(manifest["stages"]), six_stage_payload_guard="separate unit fixture", resources=resource_count, reviewed_section_refs=section_count, extensions=len(draft["extensions"]), canonical_knowledge_persisted=len(knowledge), canonical_practice_persisted=len(practice), scope_acceptance_rubric_readback="PASS", explicit_synthetic_confirm="PASS", plan_id=plan["plan_id"])


def test_markerless_owned_historical_submission_recovers_legacy(projection_db):
    db = projection_db
    settings = settings_for(db)
    first = build_container(settings)
    with TestClient(create_app(first)) as client:
        username, params, _ = register(client, "v67legacy")
    pack = adapt_semantic_pack(load_pack(CURRENT_PACKS["agent.application"]), GOAL, None)
    manifest = freeze_manifest(pack, DEFAULT_BUDGET, "fake:planning-demo")
    assert "outline_input_format" not in manifest and manifest_is_intact(manifest)
    with psycopg.connect(db.migrator_dsn) as conn:
        actor_id = conn.execute("SELECT owner_actor_id FROM learning_projects WHERE project_id=%s", (params["project_id"],)).fetchone()[0]
    run_id = new_id("run")
    graph_version = first.plan_service._graph_version
    thread_id = "planning:" + run_id
    run = RunRecord(run_id=run_id, actor_id=actor_id, project_id=params["project_id"], kind="plan_generate", graph_name="planning", graph_version=graph_version, status=AiRunStatus.QUEUED, next_action=AiRunNextAction.WAIT, thread_id=thread_id)
    initial = dict(run_id=run_id, project_id=params["project_id"], graph_version=graph_version, goal=GOAL, prefs_snapshot={}, manifest=manifest, protocol=manifest["protocol"], expected_version=0, domain_pack=pack)
    first.plan_service._planning_jobs.enqueue(run, initial, manifest)
    before = submission(db, run_id)
    fresh = build_container(settings)
    seen = capture_fake(fresh)
    with TestClient(create_app(fresh)) as client:
        assert client.post("/api/v1/auth/login", json={"username": username, "password": "Test-pass1!"}).status_code == 200
        _, draft = finish_draft(client, fresh, params, run_id)
        assert draft["stages"]
    outline = next(payload for kind, payload in seen if kind == "planning.outline")
    assert "manifest" in outline and "domain_pack" in outline
    assert "_outline_input_format" not in outline
    assert submission(db, run_id) == before
    assert "outline_input_format" not in before["manifest"]
    assert not fresh.planning_worker.tick()
    save_evidence("legacy", database=db.name, run_id=run_id, retained_manifest_hash=manifest["manifest_hash"], markerless_recovery="PASS", stored_submission_unchanged="PASS", outline_legacy_shape="PASS")


def test_owned_failed_run_cannot_claim_or_redispatch(projection_db):
    db = projection_db
    settings = settings_for(db)
    first = build_container(settings)
    with TestClient(create_app(first)) as client:
        _, params, headers = register(client, "v67failed")
        queued = client.post("/api/v1/plans/generate", params=params, headers=headers, json={"goal": GOAL})
        assert queued.status_code == 202
        run_id = queued.json()["run_id"]
        first.plan_service._llm.register("planning.outline", lambda *_: (_ for _ in ()).throw(ValueError("synthetic terminal failure")))
        assert first.planning_worker.tick()
        response = client.get(queued.json()["status_url"])
        assert response.json()["status"] == "failed", response.text
    before = submission(db, run_id)
    fresh = build_container(settings)
    assert not fresh.planning_worker.tick()
    assert not fresh.plan_service._llm.calls
    assert submission(db, run_id) == before
    with psycopg.connect(db.migrator_dsn) as conn:
        job = conn.execute("SELECT status FROM ai_jobs WHERE run_id=%s", (run_id,)).fetchone()[0]
    # Interpreted terminal graph failure returns normally to the worker; the
    # consumed job is completed while its associated Run remains failed.
    assert job == "completed"
    save_evidence("failed", database=db.name, run_id=run_id, run_status="failed", job_status=job, failed_no_claim="PASS", restart_no_dispatch="PASS", real_v65_run_touched=False)


@pytest.fixture(scope="module")
def checkpoint_db():
    from app.agent_workflows.runtime import PostgresSaver

    from tests.pg_harness import create_test_database

    assert not instance_is_dedicated() and not roles_created_by_harness()
    db = create_test_database(prefix="studyplan_test_v67_checkpoint")
    assert db.name.startswith("studyplan_test_v67_checkpoint_")
    try:
        with PostgresSaver.from_conn_string(db.migrator_dsn) as saver:
            saver.setup()
        yield db
    finally:
        db.drop()
        assert not roles_created_by_harness()


@pytest.mark.parametrize("format_marker", [None, "stage_skeleton_v1"], ids=["legacy", "projection"])
def test_real_checkpoint_resumes_frozen_format_rejecting_altered_manifest(checkpoint_db, format_marker):
    from app.agent_workflows.nodes import PlanningNodes
    from app.agent_workflows.planning_batches import PROTOCOL_VERSION, SHORT_GENERATION_VERSION
    from app.agent_workflows.runtime import PostgresSaver
    from app.infrastructure.checkpointer.planning_executor import PgPlanningExecutor, builder_for_version
    from app.infrastructure.providers.planning_demo import build_planning_demo
    from app.ports.graph_runner import GraphRecoveryError
    from langgraph.errors import GraphRecursionError

    goal = "零基础系统学习 Agent 应用开发，先做一个最小应用。"
    # This is the historical six-stage checkpoint protocol representative.
    # Keep its old published content explicit as CURRENT_PACKS evolves.
    pack = adapt_semantic_pack(load_pack("agent-application-v5.json"), goal, None)
    manifest = freeze_manifest(pack, DEFAULT_BUDGET, "fake:planning-demo", outline_input_format=format_marker)
    assert len(manifest["stages"]) == 6
    version = SHORT_GENERATION_VERSION if format_marker else PROTOCOL_VERSION
    thread_id = new_id("checkpoint")
    initial = dict(goal=goal, run_id=new_id("run"), graph_version=version, domain_pack=pack, manifest=manifest)
    # Match a real persisted submission's JSONB representation (guidance tuples
    # become JSON arrays); the manifest digest already uses canonical JSON.
    initial = json.loads(json.dumps(initial, ensure_ascii=False))
    manifest = initial["manifest"]
    llm = build_planning_demo()
    captured = []
    for purpose, handler in list(llm._handlers.items()):
        def record(kind, payload, original=handler):
            captured.append((kind, deepcopy(payload)))
            return original(kind, payload)
        llm.register(purpose, record)
    saves = []
    def save(state):
        saves.append(deepcopy(state))
        return {"draft_ref": "owned-checkpoint-draft", "draft_hash": "owned-hash"}
    nodes = PlanningNodes(llm=llm, save_draft=save)
    builder = builder_for_version(version)
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 2}
    with PostgresSaver.from_conn_string(checkpoint_db.migrator_dsn) as saver:
        graph = builder(nodes, checkpointer=saver)
        with pytest.raises(GraphRecursionError):
            graph.invoke(initial, config)
        partial = graph.get_state(config)
        assert partial.next and partial.values["outline"]["sections"]
        assert partial.values["manifest"] == manifest
    assert [kind for kind, _ in captured] == ["planning.outline"]
    outline_before = deepcopy(captured[0][1])
    if format_marker:
        assert outline_before["_outline_input_format"] == format_marker
    else:
        assert "_outline_input_format" not in outline_before
        assert "manifest" in outline_before and "domain_pack" in outline_before

    # Recovery refuses a changed frozen manifest before any further dispatch.
    altered = deepcopy(initial)
    if format_marker:
        altered["manifest"].pop("outline_input_format")
    else:
        altered["manifest"]["outline_input_format"] = "stage_skeleton_v1"
    assert not manifest_is_intact(altered["manifest"])
    altered["goal"] = "must never replace stored goal"
    executor = PgPlanningExecutor(checkpoint_db.migrator_dsn, llm=llm)
    calls_before_rejection = deepcopy(llm.calls)
    with pytest.raises(GraphRecoveryError):
        executor.execute_or_resume(nodes, altered, thread_id, version, lambda: None)
    assert llm.calls == calls_before_rejection
    result = executor.execute_or_resume(nodes, initial, thread_id, version, lambda: None)
    assert result.state["manifest"] == manifest
    assert result.state["goal"] == goal
    # Merge rehydrates resources/guidance onto the outline. The personalized
    # skeleton fields and ordered identities remain those already checkpointed.
    def skeleton_fields(outline):
        return [{field: stage[field] for field in ("stable_key", "title", "objective")}
                for stage in outline["sections"]]
    assert skeleton_fields(result.state["outline"]) == skeleton_fields(partial.values["outline"])
    assert len(saves) == 1
    assert [kind for kind, _ in captured].count("planning.outline") == 1
    calls_before_terminal = deepcopy(llm.calls)
    if format_marker:
        assert result.stopped_at is None
        again = executor.execute_or_resume(nodes, initial, thread_id, version, lambda: None)
        assert again.state == result.state
    else:
        assert result.stopped_at == "await_approval"
        with pytest.raises(GraphRecoveryError, match="等待用户确认"):
            executor.execute_or_resume(nodes, initial, thread_id, version, lambda: None)
    assert llm.calls == calls_before_terminal and len(saves) == 1
    save_evidence("checkpoint-" + ("projection" if format_marker else "legacy"), database=checkpoint_db.name,
        marker=format_marker, graph_version=version, stage_count=6, manifest_hash=manifest["manifest_hash"],
        partial_checkpoint_restart="PASS", altered_manifest_refused="PASS", outline_dispatches=1,
        model_dispatches=len(llm.calls), terminal_no_redispatch="PASS", legacy_await_approval_refusal="PASS" if not format_marker else "NOT RUN")


@pytest.mark.parametrize("mutation", ["remove", "null"])
def test_tampered_stored_checkpoint_marker_refused_before_dispatch(checkpoint_db, mutation):
    from app.agent_workflows.nodes import PlanningNodes
    from app.agent_workflows.planning_batches import SHORT_GENERATION_VERSION
    from app.agent_workflows.runtime import PostgresSaver
    from app.infrastructure.checkpointer.planning_executor import PgPlanningExecutor, builder_for_version
    from app.infrastructure.providers.planning_demo import build_planning_demo
    from app.ports.graph_runner import GraphRecoveryError
    from langgraph.errors import GraphRecursionError

    goal = "零基础系统学习 Agent 应用开发，先做一个最小应用。"
    pack = adapt_semantic_pack(load_pack(CURRENT_PACKS["agent.application"]), goal, None)
    manifest = freeze_manifest(pack, DEFAULT_BUDGET, "fake:planning-demo", outline_input_format="stage_skeleton_v1")
    initial = dict(goal=goal, run_id=new_id("run"), graph_version=SHORT_GENERATION_VERSION, domain_pack=pack, manifest=manifest)
    initial = json.loads(json.dumps(initial, ensure_ascii=False))
    manifest = initial["manifest"]
    thread_id = new_id("checkpoint")
    llm = build_planning_demo()
    nodes = PlanningNodes(llm=llm, save_draft=lambda _: {"draft_ref": "unused", "draft_hash": "unused"})
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 2}
    with PostgresSaver.from_conn_string(checkpoint_db.migrator_dsn) as saver:
        graph = builder_for_version(SHORT_GENERATION_VERSION)(nodes, checkpointer=saver)
        with pytest.raises(GraphRecursionError):
            graph.invoke(initial, config)
        state = graph.get_state(config)
        assert state.values["outline"]["sections"]
        changed = deepcopy(state.values["manifest"])
        if mutation == "remove":
            changed.pop("outline_input_format")
        else:
            changed["outline_input_format"] = None
        assert changed["manifest_hash"] == manifest["manifest_hash"] and not manifest_is_intact(changed)
        graph.update_state(config, {"manifest": changed})
    calls_before = deepcopy(llm.calls)
    executor = PgPlanningExecutor(checkpoint_db.migrator_dsn, llm=llm)
    with pytest.raises(GraphRecoveryError):
        executor.execute_or_resume(nodes, initial, thread_id, SHORT_GENERATION_VERSION, lambda: None)
    assert llm.calls == calls_before
    save_evidence("checkpoint-tamper-" + mutation, database=checkpoint_db.name, mutation=mutation,
        original_digest_retained=True, checkpoint_manifest_rejected="PASS", additional_model_dispatches=0)
