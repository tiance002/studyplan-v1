"""New owned PG acceptance of F2 negative extra-task boundary; Fake only."""

import json
import hashlib
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
from app.domain.planning.semantic_content import adapt_semantic_pack
from app.infrastructure.checkpointer.planning_executor import PgPlanningExecutor, builder_for_version
from app.infrastructure.domain_pack import CURRENT_PACKS, load_pack
from app.infrastructure.providers.planning_demo import build_planning_demo
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
OUT = ROOT / "var/f2-negative-extra-task-20261004/pg"
GOAL = "零基础系统学习 Agent 应用开发，先做一个最小应用。"
RAG_GOAL = "从零系统学习 Agent 应用开发，主要做资料问答，先学通用核心（含 Framework/MCP），再看小型开源核心，然后系统深化 RAG，最后学习成熟 RAG 工程相关切片与迁移验证；不做 RL、Browser、Coding 完整专项。"



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
    db = create_test_database("studyplan_test_f2negative_business")
    try:
        assert db.name.startswith("studyplan_test_f2negative_business_")
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
            for key in ("agent.application",):
                seed_reviewed_pack(conn, load_pack(CURRENT_PACKS[key]))
        if os.environ.get("STUDYPLAN_F2NEGATIVE_KEEP_OWNED") == "1":
            private = ROOT / "var/f2-negative-extra-task-20261004/pg/private"
            private.mkdir(parents=True, exist_ok=True)
            (private / "fake-database.json").write_text(json.dumps(db.__dict__), encoding="utf-8")
        yield db
    finally:
        if os.environ.get("STUDYPLAN_F2NEGATIVE_KEEP_OWNED") != "1":
            db.drop()
        assert not roles_created_by_harness()


@pytest.mark.parametrize("raw_number", [None,48,49,50], ids=["full-fake","raw48","raw49","raw50"])
def test_new_owned_rag_confirm_negative_task_presentation_pg(reviewed_db, raw_number):
    name = "rag-fake" if raw_number is None else "rag-raw" + str(raw_number)
    goal, key = RAG_GOAL, "agent.application"
    protection = json.loads((ROOT / "var/f2-negative-extra-task-20261004/protection.json").read_text(encoding="utf-8"))["hashes"]
    assert all(hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==value for path,value in protection.items())
    container = build_container(settings_for(reviewed_db))
    replayed = []
    raw_sha = None
    if raw_number is not None:
        raw_path = ROOT / f"var/gr-binding-20261004/paid/responses/{raw_number}.body"
        raw_bytes = raw_path.read_bytes()
        raw_sha = hashlib.sha256(raw_bytes).hexdigest()
        original = container.plan_service._llm._handlers["planning.structure"]
        parsed = json.loads(json.loads(raw_bytes)["choices"][0]["message"]["content"])
        def retained_raw_structure(purpose, payload):
            if payload["stage"]["stage_key"].endswith(".a1"):
                replayed.append(deepcopy(parsed))
                return deepcopy(parsed)
            return original(purpose, payload)
        container.plan_service._llm.register("planning.structure", retained_raw_structure)
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
        if True:
            a2 = next(s for s in workspace["stages"] if s["stage"]["stable_key"].endswith(".a2"))
            assert len(a2["units"]) == 3 and len(a2["nodes"]) == 1
            assert all(u["node_ids"] == [a2["nodes"][0]["node_id"]] for u in a2["units"])
            assert len({u["title"] for u in a2["units"]}) == 3 and len(a2["tasks"]) == 1
        stage_checks = {}
        for suffix in (".a2", ".a5", ".a6", ".gr"):
            stages = [s for s in workspace["stages"] if s["stage"]["stable_key"].endswith(suffix)]
            assert len(stages)==1, (suffix, [s["stage"]["stable_key"] for s in workspace["stages"]])
            current=stages[0]
            assert len(current["tasks"])==1
            stage_checks[suffix]={"task_count":1,"node_count":len(current["nodes"]),"unit_count":len(current["units"])}
        gr_stage=next(s for s in plan["stages"] if s["stable_key"].endswith(".gr"))
        gr_candidates=[r for r in plan["stage_resources"] if r["stage_id"]==gr_stage["stage_id"] and r["role"]=="case_study"]
        assert len(gr_candidates)==2
        assert {r["canonical_url"] for r in gr_candidates}=={"https://github.com/infiniflow/ragflow","https://github.com/Tencent/WeKnora"}
        assert all(r["source_version"]==1 and r["verification_status"]=="legacy_index" and not r["ordered_sections"] for r in gr_candidates)
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
    assert len(replayed)==(0 if raw_number is None else 1)
    assert all(hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==value for path,value in protection.items())
    evidence(
        "pg-" + name,
        raw_response_number=raw_number,
        raw_response_sha256=raw_sha,
        offline_raw_replay_count=len(replayed),
        repair_requests=0,
        protected_history_hashmatch="PASS",
        database=reviewed_db.name,
        run_id=run["run_id"],
        plan_id=plan["plan_id"],
        structure_marker=manifest["structure_input_format"],
        stage_count=len(manifest["stages"]),
        canonical_nodes=len(knowledge),
        canonical_relations=len(relations),
        requests=before,
        canonical_practice=len(practice),
        stage_checks=stage_checks,
        gr_candidates=gr_candidates,
        canonical_rubric_readback="PASS",
        synthetic_confirm="PASS",
        terminal_no_redispatch="PASS",
    )
    (OUT / ("workspace-" + name + ".json")).write_text(
        json.dumps(workspace, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if os.environ.get("STUDYPLAN_F2NEGATIVE_KEEP_OWNED") == "1":
        private = ROOT / "var/f2-negative-extra-task-20261004/pg/private"
        (private / ("fake-" + name + ".json")).write_text(json.dumps({
            "username": username, "password": "Test-pass1!", "project_id": params["project_id"],
            "run_id": run["run_id"]}, ensure_ascii=False), encoding="utf-8")
    (OUT / ("manifest-" + name + ".json")).write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / ("plan-" + name + ".json")).write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
