"""Owned PG acceptance of reviewed presentation structures; Fake only."""

import json
import os
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import psycopg
import pytest
from app.agent_workflows.nodes import PlanningNodes
from app.agent_workflows.planning_batches import DEFAULT_BUDGET, SHORT_GENERATION_VERSION, freeze_manifest
from app.agent_workflows.planning_structure import REVIEWED_STRUCTURE_V1
from app.agent_workflows.runtime import PostgresSaver
from app.composition import build_container
from app.core.ids import new_id
from app.infrastructure.checkpointer.planning_executor import PgPlanningExecutor, builder_for_version
from app.infrastructure.domain_pack import CURRENT_PACKS, load_pack
from tests.helpers.planning_responses import build_planning_demo
from app.main import create_app
from app.ports.graph_runner import GraphRecoveryError
from app.tools.seed_b3 import seed_reviewed_pack
from fastapi.testclient import TestClient
from langgraph.errors import GraphRecursionError

from tests.integration.test_v62_semantic_pg import confirm, generate, register, settings_for
from tests.pg_harness import create_test_database, instance_is_dedicated, roles_created_by_harness

pytestmark = pytest.mark.postgres
assert not instance_is_dedicated(), "No global role mutation opt-in permitted"
ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "var/v612/pg"
GOAL = "零基础系统学习 Agent 应用开发，先做一个最小应用。"
RAG_GOAL = "从零系统学习 Agent 应用开发，主要做资料问答，先学通用核心（含 Framework/MCP），再看小型开源核心，然后系统深化 RAG，最后学习成熟 RAG 工程相关切片与迁移验证；不做 RL、Browser、Coding 完整专项。"
SCENARIOS = [
    ("rag", RAG_GOAL, "agent.application"),
    ("system", GOAL, "agent.application"),
    ("mcp", "我只想学 MCP；已经会基础 Tool 调用。", "agent.application"),
    ("node", "我已有一个 Node.js API，希望学习部署、监控、自动发布和恢复。", "cloud.services"),
]


def evidence(name, **details):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / (name + ".json")).write_text(
        json.dumps(
            dict(
                status="PASS",
                provider="Fake",
                requested_model="gpt-6.1-sol",
                requested_effort="medium",
                actual_resolution="NOT OBSERVABLE",
                real_provider_requests=0,
                global_role_mutations=0,
                **details,
            ),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def capture(llm):
    seen = []
    for purpose, handler in list(llm._handlers.items()):

        def record(kind, payload, original=handler):
            seen.append((kind, deepcopy(payload)))
            return original(kind, payload)

        llm.register(purpose, record)
    return seen


@pytest.fixture(scope="module")
def reviewed_db():
    assert not instance_is_dedicated() and not roles_created_by_harness()
    db = create_test_database("studyplan_test_reviewed_structure")
    try:
        assert db.name.startswith("studyplan_test_reviewed_structure_")
        migration = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=ROOT / "backend",
            env=dict(os.environ, STUDYPLAN_MIGRATION_DSN=db.migrator_dsn),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert migration.returncode == 0, migration.stderr
        with psycopg.connect(db.migrator_dsn) as conn:
            for key in ("agent.application", "ai.fullstack", "cloud.services"):
                seed_reviewed_pack(conn, load_pack(CURRENT_PACKS[key]))
        if os.environ.get("STUDYPLAN_V612_KEEP_OWNED") == "1":
            private = ROOT / "var/v612/private"
            private.mkdir(parents=True, exist_ok=True)
            (private / "fake-database.json").write_text(json.dumps(db.__dict__), encoding="utf-8")
        yield db
    finally:
        if os.environ.get("STUDYPLAN_V612_KEEP_OWNED") != "1":
            db.drop()
        assert not roles_created_by_harness()


@pytest.fixture(scope="module")
def checkpoint_db():
    assert not instance_is_dedicated() and not roles_created_by_harness()
    db = create_test_database("studyplan_test_reviewed_checkpoint")
    try:
        with PostgresSaver.from_conn_string(db.migrator_dsn) as saver:
            saver.setup()
        yield db
    finally:
        db.drop()
        assert not roles_created_by_harness()


@pytest.mark.parametrize("name,goal,key", SCENARIOS)
def test_generate_fake_draft_confirm_canonical_pg(reviewed_db, name, goal, key):
    container = build_container(settings_for(reviewed_db))
    seen = capture(container.plan_service._llm)
    with TestClient(create_app(container)) as client:
        username, params, headers = register(client, "reviewed" + name)
        run, url, draft = generate(client, container, params, headers, goal)
        with psycopg.connect(reviewed_db.migrator_dsn) as conn:
            frozen = conn.execute(
                "SELECT detail FROM ai_run_events WHERE run_id=%s AND detail->>'kind'='planning_submission'",
                (run["run_id"],),
            ).fetchone()[0]
        manifest, pack = frozen["manifest"], frozen["initial"]["domain_pack"]
        assert manifest["structure_input_format"] == REVIEWED_STRUCTURE_V1
        assert pack["pack_key"] == key
        selected = {k for s in manifest["stages"] for k in s["node_keys"]}
        canonical = {n["stable_key"]: n for n in pack["knowledge_blueprints"] if n["stable_key"] in selected}
        structure_payloads = [p for kind, p in seen if kind == "planning.structure"]
        assert len(structure_payloads) == len(manifest["structure_batches"])
        for payload, batch in zip(structure_payloads, manifest["structure_batches"], strict=True):
            assert payload["_structure_input_format"] == REVIEWED_STRUCTURE_V1
            assert payload["allowed_node_keys"] == batch["node_keys"]
            assert not {"node_blueprints", "resources", "domain_pack", "manifest"} & set(payload)
        assert len(container.plan_service._llm.calls) == 1 + 2 * len(manifest["stages"])
        assert not any(kind == "planning.repair" for kind, _ in seen)
        plan = confirm(client, params, headers, url, draft)
        workspace = client.get("/api/v1/workspace", params=params).json()
        if name in {"rag", "system"}:
            a2 = next(s for s in workspace["stages"] if s["stage"]["stable_key"].endswith(".a2"))
            assert len(a2["units"]) == 3 and len(a2["nodes"]) == 1
            assert all(u["node_ids"] == [a2["nodes"][0]["node_id"]] for u in a2["units"])
            assert len({u["title"] for u in a2["units"]}) == 3 and len(a2["tasks"]) == 1
        with psycopg.connect(reviewed_db.migrator_dsn) as conn:
            nodes = {
                r[0]: r[1:]
                for r in conn.execute(
                    "SELECT stable_key,title,objectives FROM knowledge_nodes WHERE project_id=%s",
                    (params["project_id"],),
                )
            }
            rubrics = [
                r[0]
                for r in conn.execute(
                    "SELECT rubric FROM learning_units WHERE project_id=%s", (params["project_id"],)
                )
            ]
            tasks = {
                r[0]: r[1:]
                for r in conn.execute(
                    "SELECT stable_key,goal,in_scope,out_scope,acceptance FROM practice_tasks WHERE project_id=%s",
                    (params["project_id"],),
                )
            }
            relations = set(
                conn.execute(
                    "SELECT f.stable_key,t.stable_key,r.relation_type FROM knowledge_relations r "
                    "JOIN knowledge_nodes f ON f.node_id=r.from_node_id JOIN knowledge_nodes t ON t.node_id=r.to_node_id "
                    "WHERE r.project_id=%s",
                    (params["project_id"],),
                ).fetchall()
            )
        knowledge = {k: n for r in rubrics for k, n in r["canonical_knowledge"].items()}
        assert all(r.get("teaching", {}).get("focus_refs") for r in rubrics)
        practice = {k: n for r in rubrics for k, n in r["canonical_practice"].items()}
        assert set(nodes) == set(knowledge) == selected
        expected_tasks = {t["stable_key"]: t for t in pack["practice_blueprints"]}
        assert set(practice) == set(tasks) == set(expected_tasks)
        for task_key, task in expected_tasks.items():
            assert tasks[task_key] == tuple(
                practice[task_key][field] for field in ("goal", "in_scope", "out_scope", "acceptance")
            )
            for field in ("goal", "in_scope", "out_scope", "acceptance"):
                if field in task:
                    assert practice[task_key][field] == task[field]
        expected_edges = set()
        for k, node in canonical.items():
            assert nodes[k] == (node["title"], node["objectives"])
            for field in (
                "stable_key",
                "title",
                "node_type",
                "objectives",
                "scope",
                "acceptance",
                "parent_key",
                "prerequisite_keys",
            ):
                if field in node:
                    assert knowledge[k][field] == node[field], (k, field)
            if node.get("parent_key"):
                expected_edges.add((node["parent_key"], k, "contains"))
            expected_edges.update(
                (prereq, k, "prerequisite") for prereq in node.get("prerequisite_keys") or []
            )
        assert relations == expected_edges
        before = len(container.plan_service._llm.calls)
        assert client.get("/api/v1/plans/current", params=params).json() == plan
        assert client.post("/api/v1/auth/logout", headers=headers).status_code == 200
        assert (
            client.post(
                "/api/v1/auth/login", json={"username": username, "password": "Test-pass1!"}
            ).status_code
            == 200
        )
        assert client.get("/api/v1/workspace", params=params).json() == workspace
        assert not container.planning_worker.tick()
        assert len(container.plan_service._llm.calls) == before
    evidence(
        "pg-" + name,
        database=reviewed_db.name,
        run_id=run["run_id"],
        plan_id=plan["plan_id"],
        structure_marker=manifest["structure_input_format"],
        stage_count=len(manifest["stages"]),
        canonical_nodes=len(knowledge),
        canonical_relations=len(relations),
        requests=before,
        canonical_practice=len(practice),
        canonical_rubric_readback="PASS",
        synthetic_confirm="PASS",
        terminal_no_redispatch="PASS",
    )
    (OUT / ("workspace-" + name + ".json")).write_text(
        json.dumps(workspace, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if os.environ.get("STUDYPLAN_V612_KEEP_OWNED") == "1":
        private = ROOT / "var/v612/private"
        (private / ("fake-" + name + ".json")).write_text(json.dumps({
            "username": username, "password": "Test-pass1!", "project_id": params["project_id"],
            "run_id": run["run_id"]}, ensure_ascii=False), encoding="utf-8")
    (OUT / ("manifest-" + name + ".json")).write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / ("plan-" + name + ".json")).write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")


def initial_state():
    pack = load_pack(CURRENT_PACKS["agent.application"])
    manifest = freeze_manifest(
        pack,
        DEFAULT_BUDGET,
        "fake:planning-demo",
        outline_input_format="stage_skeleton_v1",
        structure_input_format=REVIEWED_STRUCTURE_V1,
    )
    return json.loads(
        json.dumps(
            dict(
                goal=GOAL,
                run_id=new_id("run"),
                graph_version=SHORT_GENERATION_VERSION,
                domain_pack=pack,
                manifest=manifest,
            ),
            ensure_ascii=False,
        )
    )


def partial_checkpoint(db, initial, llm, nodes, thread_id):
    index = next(
        i for i, stage in enumerate(initial["domain_pack"]["stage_blueprints"]) if stage["stage_code"] == "A2"
    )
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 3 + 3 * index}
    with PostgresSaver.from_conn_string(db.migrator_dsn) as saver:
        graph = builder_for_version(SHORT_GENERATION_VERSION)(nodes, checkpointer=saver)
        with pytest.raises(GraphRecursionError):
            graph.invoke(initial, config)
        state = graph.get_state(config)
        assert state.next == ("validate_structure_batch",)
        assert state.values["current_structure_index"] == index
        assert (
            state.values["structure_batches"][-1]["stage_key"]
            == initial["manifest"]["stages"][index]["stage_key"]
        )
        assert state.values["structure_batches"][0]["_reviewed_presentation"]["units"]
        return deepcopy(state.values)


def test_checkpoint_restart_resumes_without_repeating_structure(checkpoint_db):
    initial, llm, saves = initial_state(), build_planning_demo(), []
    captured = capture(llm)

    def save(state):
        saves.append(deepcopy(state))
        return {"draft_ref": "owned-reviewed-draft", "draft_hash": "owned-reviewed-hash"}

    nodes = PlanningNodes(llm=llm, save_draft=save)
    thread_id = new_id("checkpoint")
    partial = partial_checkpoint(checkpoint_db, initial, llm, nodes, thread_id)
    assert captured[0][0] == "planning.outline"
    assert all(kind == "planning.structure" for kind, _ in captured[1:])
    executor = PgPlanningExecutor(checkpoint_db.migrator_dsn, llm=llm)
    result = executor.execute_or_resume(nodes, initial, thread_id, SHORT_GENERATION_VERSION, lambda: None)
    assert not result.stopped_at and len(saves) == 1
    assert (
        result.state["structure_batches"][: len(partial["structure_batches"])] == partial["structure_batches"]
    )
    stages = len(initial["manifest"]["stages"])
    assert len(llm.calls) == 1 + 2 * stages
    before = deepcopy(llm.calls)
    again = executor.execute_or_resume(nodes, initial, thread_id, SHORT_GENERATION_VERSION, lambda: None)
    assert again.state == result.state and llm.calls == before and len(saves) == 1
    evidence(
        "pg-checkpoint-resume",
        database=checkpoint_db.name,
        stage_count=stages,
        requests=len(llm.calls),
        checkpoint_stop="A2 structure complete / before validate",
        prior_structures_retained="PASS",
        partial_checkpoint_restart="PASS",
        terminal_no_redispatch="PASS",
    )


@pytest.mark.parametrize(
    "mutation", ["marker", "pack", "assembled_nodes", "assembled_scope", "assembled_prerequisite"]
)
def test_tampered_checkpoint_refuses_before_dispatch(checkpoint_db, mutation):
    initial, llm, saves = initial_state(), build_planning_demo(), []
    nodes = PlanningNodes(llm=llm, save_draft=lambda state: saves.append(state))
    thread_id = new_id("checkpoint")
    state = partial_checkpoint(checkpoint_db, initial, llm, nodes, thread_id)
    if mutation == "marker":
        changed = deepcopy(state["manifest"])
        changed.pop("structure_input_format")
        delta = {"manifest": changed}
    elif mutation == "pack":
        changed = deepcopy(state["domain_pack"])
        changed["knowledge_blueprints"][0]["scope"] = ["forged"]
        delta = {"domain_pack": changed}
    else:
        changed = deepcopy(state["structure_batches"])
        field = {
            "assembled_nodes": "title",
            "assembled_scope": "scope",
            "assembled_prerequisite": "prerequisite_keys",
        }[mutation]
        changed[-1]["nodes"][0][field] = "forged canonical knowledge" if field == "title" else ["forged"]
        delta = {"structure_batches": changed}
    with PostgresSaver.from_conn_string(checkpoint_db.migrator_dsn) as saver:
        graph = builder_for_version(SHORT_GENERATION_VERSION)(nodes, checkpointer=saver)
        graph.update_state({"configurable": {"thread_id": thread_id}}, delta)
    before = deepcopy(llm.calls)
    executor = PgPlanningExecutor(checkpoint_db.migrator_dsn, llm=llm)
    with pytest.raises(GraphRecoveryError):
        executor.execute_or_resume(nodes, initial, thread_id, SHORT_GENERATION_VERSION, lambda: None)
    assert llm.calls == before and not saves
    evidence(
        "pg-checkpoint-tamper-" + mutation,
        database=checkpoint_db.name,
        mutation=mutation,
        checkpoint_rejected="PASS",
        additional_dispatches=0,
        saved_drafts=0,
    )
