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
SCENARIOS = [
    ("travel", "我已经有一个旅行规划 Agent，希望系统补 Agent 基础，并强化网页信息获取、可恢复规划和知识检索。", "agent.application", "旅行规划 Agent", {"browser", "workflow", "rag"}),
    ("starter", "我没有项目想法，想系统学习 Agent 应用开发。", "agent.application", "研究与行动助手", set()),
    ("voice", "我想学语音 Agent。", "agent.application", "研究与行动助手", set()),
    ("commerce", "我已经有一个电商后台，想把它改造成带 AI 商品文案与客服能力的全栈应用。", "ai.fullstack", "电商后台", set()),
    ("node", "我已经有一个 Node.js API，想学习如何部署、监控、自动发布和恢复。", "cloud.services", "Node.js API", set()),
    ("knowledge", "我已经有一个自己的知识库项目，想学习 RAG 检索增强与证据回答 Agent。", "agent.application", "自己的知识库项目", {"rag"}),
]


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


@pytest.mark.parametrize("name,goal,key,carrier,recipes", SCENARIOS, ids=[s[0] for s in SCENARIOS])
def test_semantic_normal_generate_confirm_refresh_relogin_rls(semantic_db, name, goal, key, carrier, recipes):
    db = semantic_db[0]
    settings = settings_for(db)
    container = build_container(settings)
    with TestClient(create_app(container)) as client:
        username, params, headers = register(client)
        run, url, draft = generate(client, container, params, headers, goal)
        pack = load_pack(CURRENT_PACKS[key])
        assert draft["source_pack_key"] == key and draft["source_pack_version"] == pack["version"]
        with psycopg.connect(db.migrator_dsn) as conn:
            submitted = conn.execute("SELECT detail FROM ai_run_events WHERE run_id=%s AND detail->>'kind'='planning_submission'", (run["run_id"],)).fetchone()[0]
        frozen = submitted["initial"]["domain_pack"]
        context = frozen["semantic_context"]
        assert context["carrier_title"] == carrier
        assert context["carrier_kind"] == ("starter_candidate" if name in {"starter", "voice"} else "user_project")
        assert context["binding"] == "optional" and context["replacement_allowed"] is True
        assert recipes <= set(context["recipe_refs"]) and "agentic_rl" not in context["recipe_refs"]
        assert [s["stable_key"] for s in draft["stages"]] == [s["stable_key"] for s in frozen["stage_blueprints"]]
        selected_capabilities = {c for s in frozen["stage_blueprints"] for c in s.get("selection", {}).get("capabilities", [])}
        assert recipes <= selected_capabilities
        for stage in draft["stages"]:
            guidance = stage["learning_guidance"]
            assert carrier in guidance["practice_delta"]["baseline"]
            assert guidance["why_now"] and guidance["practice_delta"]["increment"] and guidance["practice_delta"]["validation"]
        candidates = [e for e in draft["extensions"] if e["topic"].startswith("项目学习：")]
        assert all(e["required"] is False and "可选" in e["guidance"] and "替换" in e["guidance"] for e in candidates)
        if name == "travel":
            assert all(any(e["stage_id"] == s["stage_id"] and e["topic"] == "贯穿评价与证据" for e in draft["extensions"]) for s in draft["stages"])
        if name == "starter":
            assert len(frozen["stage_blueprints"]) < len(pack["stage_blueprints"])
            assert all("默认项目候选（可替换）" in s["learning_guidance"]["practice_delta"]["baseline"] for s in draft["stages"])
        if name == "voice":
            assert context["research_gaps"] == ["voice"]
            gap = next(e for e in draft["extensions"] if e["topic"].startswith("资料缺口："))
            assert "needs_research_or_review" in gap["guidance"] and not gap["links"]
            assert not any("voice" in str(r.get("source_ref", "")).lower() for r in draft["stage_resources"])
        if name == "node":
            assert not any("FastAPI" in s["title"] for s in draft["stages"])
            assert not any("Task Service" in s["title"] for s in draft["stages"])
            assert "Task Service" not in json.dumps([s["learning_guidance"]["practice_delta"]["baseline"] for s in draft["stages"]])
            assert not any(s.get("selection", {}).get("fallback_only") for s in frozen["stage_blueprints"])
        if name == "knowledge":
            assert any("RAGFlow" in e["topic"] or "WeKnora" in e["topic"] for e in candidates)
        # The ordered reviewed chapter scopes and teaching roles survive the merge.
        downgraded = []
        sources = {s["source_id"]: s for s in frozen["resources"]}
        for stage in frozen["stage_blueprints"]:
            stage_id = next(s["stage_id"] for s in draft["stages"] if s["stable_key"] == stage["stable_key"])
            for expected in stage.get("resources", []):
                source = sources[expected["source_ref"]]
                section_index = {s["section_id"]: s for s in source["sections"]}
                unreviewed = key == "agent.application" and expected["role"] != "case_study" and (
                    source["verification_status"] != "reviewed" or any(section_index[ref]["verification_status"] != "reviewed" for ref in expected["section_refs"]))
                if unreviewed:
                    # Directory-only B3 Network/Frames/Dialogs is truthful scope
                    # evidence, never an approved teaching chapter. The existing
                    # Agent guard must strip its refs while retaining its role.
                    assert expected["role"] != "primary"
                    matches = [r for r in draft["stage_resources"] if r["stage_id"] == stage_id and r["role"] == expected["role"] and not r["source_ref"]]
                    assert matches and all(not r["ordered_sections"] and r["fallback_search_terms"] for r in matches)
                    downgraded.append({"stage_key": stage["stable_key"], "role": expected["role"], "source_title": source["title"], "sections": [section_index[ref]["title"] for ref in expected["section_refs"]], "status": "PASS", "behavior": "unreviewed refs stripped; explicit fallback"})
                    continue
                matches = [r for r in draft["stage_resources"] if r["stage_id"] == stage_id and r["source_ref"] == expected["source_ref"] and r["role"] == expected["role"]]
                assert matches, {"stage": stage["stable_key"], "expected": expected, "actual": [r for r in draft["stage_resources"] if r["stage_id"] == stage_id]}
                actual = matches[0]
                assert [s["section_id"] for s in actual["ordered_sections"]] == expected["section_refs"]
        plan = confirm(client, params, headers, url, draft)
        workspace = client.get("/api/v1/workspace", params=params).json()
        tasks = [t for s in workspace["stages"] for t in s["tasks"]]
        assert tasks and all(carrier in t["goal"] for t in tasks)
        with psycopg.connect(db.migrator_dsn) as conn:
            projects = conn.execute("SELECT title FROM practice_projects WHERE practice_project_id=ANY(%s)", ([t["practice_project_id"] for t in tasks],)).fetchall()
        assert projects and all(carrier in p[0] for p in projects)
        assert client.post("/api/v1/auth/logout", headers=headers).status_code == 200
    fresh = build_container(settings)
    with TestClient(create_app(fresh)) as client:
        assert client.post("/api/v1/auth/login", json={"username": username, "password": "Test-pass1!"}).status_code == 200
        assert client.get("/api/v1/workspace", params=params).json() == workspace
        assert client.get("/api/v1/plans/current", params=params).json() == plan
        assert not fresh.planning_worker.tick() and not fresh.plan_service._llm.calls
    with TestClient(create_app(build_container(settings))) as other:
        register(other, "v62other")
        assert other.get(url, params=params).status_code == 403
        assert other.get("/api/v1/workspace", params=params).status_code == 403
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / f"pg-{name}.json").write_text(json.dumps({"status": "PASS", "scenario": name, "goal": goal, "model": "Fake", "database": "owned real PG", "plan_id": plan["plan_id"], "pack_key": key, "pack_version": pack["version"], "semantic_context": context, "selected_capabilities": sorted(selected_capabilities), "stage_count": len(plan["stages"]), "review_scope_downgrades": downgraded, "refresh_relogin_no_redispatch": "PASS", "cross_account": "PASS"}, ensure_ascii=False, indent=2), encoding="utf-8")


def test_six_semantic_browser(semantic_db):
    import socket
    import subprocess
    import threading
    import time
    import urllib.request

    import uvicorn
    if os.environ.get("STUDYPLAN_V62_BROWSER") != "1":
        pytest.skip("owned Chrome explicitly enabled")
    ui = os.environ.get("STUDYPLAN_URL", "http://127.0.0.1:5178")
    assert urllib.request.urlopen(ui, timeout=5).status == 200, "start the existing root Vite preview first"
    container = build_container(settings_for(semantic_db[0], allow_origins=(ui,)))
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    server = uvicorn.Server(uvicorn.Config(create_app(container), log_level="error"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    stop, errors = threading.Event(), []
    def work():
        while not stop.is_set():
            try:
                container.planning_worker.tick()
            except Exception as exc:
                errors.append(repr(exc))
                return
            stop.wait(0.1)
    worker = threading.Thread(target=work, daemon=True)
    thread.start()
    worker.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started and thread.is_alive() and time.monotonic() < deadline:
            time.sleep(0.05)
        assert server.started
        result = subprocess.run(["node", "frontend/tests/v62-semantic-pg.browser.cjs"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300, env=dict(os.environ, STUDYPLAN_V62_API=f"http://127.0.0.1:{sock.getsockname()[1]}"))
        EVIDENCE.mkdir(parents=True, exist_ok=True)
        (EVIDENCE / "browser-process.log").write_text(result.stdout + result.stderr, encoding="utf-8")
        assert result.returncode == 0, result.stdout + result.stderr
        assert not errors, errors
    finally:
        stop.set()
        worker.join(10)
        server.should_exit = True
        thread.join(10)
        sock.close()
        assert not worker.is_alive() and not thread.is_alive(), "owned API/worker cleanup failed"


def test_change_goal_semantic_private_selection_public_digest_and_history(semantic_db):
    """The existing generated change API must use the same semantic adapter."""
    db = semantic_db[0]
    settings = settings_for(db)
    container = build_container(settings)
    evidence = []
    def historical_structure(plan_id):
        # Owned, read-only snapshots of immutable structural rows; current/old
        # revision status is lifecycle state and intentionally changes on publish.
        result = {}
        with psycopg.connect(db.migrator_dsn) as conn:
            for table in ("plan_stages", "stage_resource_assignments", "knowledge_extensions", "plan_unit_links", "plan_task_links"):
                rows = conn.execute(psycopg.sql.SQL("SELECT to_jsonb(t) FROM {} t WHERE plan_id=%s").format(psycopg.sql.Identifier(table)), (plan_id,)).fetchall()
                result[table] = sorted((row[0] for row in rows), key=lambda row: json.dumps(row, sort_keys=True))
            revision = conn.execute("SELECT to_jsonb(t) FROM plan_revisions t WHERE plan_id=%s", (plan_id,)).fetchone()[0]
            result["revision"] = {k: v for k, v in revision.items() if k not in {"status", "version", "updated_at"}}
        return result
    with TestClient(create_app(container)) as client:
        username, params, headers = register(client, "v62change")
        _, url, draft = generate(client, container, params, headers, SCENARIOS[1][1])
        current = confirm(client, params, headers, url, draft)
        for scenario in (SCENARIOS[0], SCENARIOS[4]):
            name, goal, key, carrier, recipes = scenario
            old = current
            before = historical_structure(old["plan_id"])
            body = {"plan_id": old["plan_id"], "expected_version": old["version"], "operation": "change_goal", "idempotency_key": "v62-change-" + name, "goal": goal, "goal_spec": {"target": goal, "starting_point": "有基础编程认知；初学者"}}
            queued = client.post("/api/v1/plan-changes/generate", params=params, headers=headers, json=body)
            assert queued.status_code == 202, queued.text
            assert client.post("/api/v1/plan-changes/generate", params=params, headers=headers, json=body).json() == queued.json()
            with psycopg.connect(db.migrator_dsn) as conn:
                submission = conn.execute("SELECT detail FROM ai_run_events WHERE run_id=%s AND detail->>'kind'='planning_submission'", (queued.json()["run_id"],)).fetchone()[0]
            frozen = submission["initial"]["domain_pack"]
            metadata = submission["initial"]["route_change"]
            public_pack = load_pack(CURRENT_PACKS[key])
            assert metadata["pack_hash"] == seed_digest(public_pack)
            assert metadata["pack_hash"] != seed_digest(frozen)
            assert frozen["semantic_context"]["carrier_title"] == carrier
            assert recipes <= set(frozen["semantic_context"]["recipe_refs"])
            assert len(frozen["stage_blueprints"]) < len(public_pack["stage_blueprints"])
            expected_keys = [s["stable_key"] for s in frozen["stage_blueprints"]]
            assert metadata["after_stage_keys"] == expected_keys
            assert container.planning_worker.tick()
            run = client.get(queued.json()["status_url"]).json()
            assert (run["status"], run["next_action"]) == ("succeeded", "none"), run
            change_url = "/api/v1/plan-changes/" + run["result_ref"]
            preview = client.get(change_url, params=params).json()
            assert preview["after_stage_keys"] == expected_keys
            assert [s["stable_key"] for s in preview["draft"]["stages"]] == expected_keys
            assert all(carrier in s["learning_guidance"]["practice_delta"]["baseline"] for s in preview["draft"]["stages"])
            decision = {"expected_version": old["version"], "preview_hash": preview["preview_hash"], "idempotency_key": "v62-change-confirm-" + name, "acknowledge_reset": True}
            approved = client.post(change_url + "/confirm", params=params, headers=headers, json=decision)
            assert approved.status_code == 200, approved.text
            assert client.post(change_url + "/confirm", params=params, headers=headers, json=decision).json() == approved.json()
            current = client.get("/api/v1/plans/current", params=params).json()
            assert current["plan_id"] != old["plan_id"] and current["revision"] == old["revision"] + 1
            assert current["goal_snapshot"] == goal and current["source_pack_key"] == key
            assert [s["stable_key"] for s in current["stages"]] == expected_keys
            workspace = client.get("/api/v1/workspace", params=params).json()
            assert all(carrier in task["goal"] for stage in workspace["stages"] for task in stage["tasks"])
            assert historical_structure(old["plan_id"]) == before
            assert not container.planning_worker.tick()
            evidence.append({"scenario": name, "status": "PASS", "carrier": carrier, "public_pack_hash": metadata["pack_hash"], "private_pack_hash": seed_digest(frozen), "plan_id": current["plan_id"], "previous_plan_id": old["plan_id"], "old_structure_unchanged": "PASS"})
        assert client.post("/api/v1/auth/logout", headers=headers).status_code == 200
    fresh = build_container(settings)
    with TestClient(create_app(fresh)) as client:
        assert client.post("/api/v1/auth/login", json={"username": username, "password": "Test-pass1!"}).status_code == 200
        assert client.get("/api/v1/plans/current", params=params).json() == current
        assert not fresh.planning_worker.tick() and not fresh.plan_service._llm.calls
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / "pg-change-goal.json").write_text(json.dumps({"status": "PASS", "model": "Fake", "database": "owned PG", "evidence": evidence}, ensure_ascii=False, indent=2), encoding="utf-8")


def test_future_semantic_route_keeps_carrier_selected_keys_and_history(semantic_db):
    db = semantic_db[0]
    settings = settings_for(db)
    container = build_container(settings)
    with TestClient(create_app(container)) as client:
        _, params, headers = register(client, 'v62future')
        _, url, draft = generate(client, container, params, headers, SCENARIOS[4][1])
        old = confirm(client, params, headers, url, draft)
        keys = [s['stable_key'] for s in old['stages']]
        with psycopg.connect(db.migrator_dsn) as conn:
            original = conn.execute('SELECT to_jsonb(s) FROM plan_stages s WHERE plan_id=%s ORDER BY stable_key', (old['plan_id'],)).fetchall()
        queued = client.post('/api/v1/plan-changes/generate', params=params, headers=headers,
            json=dict(plan_id=old['plan_id'], expected_version=old['version'], operation='regenerate_future_plan', idempotency_key='v62-future'))
        assert queued.status_code == 202, queued.text
        with psycopg.connect(db.migrator_dsn) as conn:
            submission = conn.execute("SELECT detail FROM ai_run_events WHERE run_id=%s AND detail->>'kind'='planning_submission'", (queued.json()['run_id'],)).fetchone()[0]
        frozen = submission['initial']['domain_pack']
        assert [s['stable_key'] for s in frozen['stage_blueprints']] == keys
        assert frozen['semantic_context']['carrier_title'] == 'Node.js API'
        assert container.planning_worker.tick()
        run = client.get(queued.json()['status_url']).json()
        assert run['status'] == 'succeeded', run
        change_url = '/api/v1/plan-changes/' + run['result_ref']
        preview = client.get(change_url, params=params).json()
        assert preview['after_stage_keys'] == keys
        assert all('Node.js API' in s['learning_guidance']['practice_delta']['baseline'] for s in preview['draft']['stages'])
        approved = client.post(change_url + '/confirm', params=params, headers=headers,
            json=dict(expected_version=old['version'], preview_hash=preview['preview_hash'], idempotency_key='v62-future-confirm', acknowledge_reset=True))
        assert approved.status_code == 200, approved.text
        newer = client.get('/api/v1/plans/current', params=params).json()
        # The deterministic Fake produces identical semantics: publication must
        # preserve the existing revision rather than invent an empty new one.
        assert approved.json()['created'] is False and newer == old
        workspace = client.get('/api/v1/workspace', params=params).json()
        assert all('Node.js API' in task['goal'] for stage in workspace['stages'] for task in stage['tasks'])
        with psycopg.connect(db.migrator_dsn) as conn:
            assert conn.execute('SELECT to_jsonb(s) FROM plan_stages s WHERE plan_id=%s ORDER BY stable_key', (old['plan_id'],)).fetchall() == original
        assert not container.planning_worker.tick()
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / 'pg-future-route.json').write_text(json.dumps(dict(status='PASS', model='Fake', database=db.name,
        carrier='Node.js API', exact_stage_keys=keys, previous_plan_id=old['plan_id'], plan_id=newer['plan_id'], old_stages_unchanged='PASS'), ensure_ascii=False, indent=2), encoding='utf-8')
