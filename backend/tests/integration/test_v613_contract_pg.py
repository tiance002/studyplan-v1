"""v6.13 independently frozen authority and final projection PG acceptance; Fake only."""

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
OUT = ROOT / "var/v613/pg"
GOAL = "零基础系统学习 Agent 应用开发，先做一个最小应用。"
RAG_GOAL = "从零系统学习 Agent 应用开发，主要做资料问答，先学通用核心（含 Framework/MCP），再看小型开源核心，然后系统深化 RAG，最后学习成熟 RAG 工程相关切片与迁移验证；不做 RL、Browser、Coding 完整专项。"
SCENARIOS = [
    ("rag", RAG_GOAL, "agent.application"),
    ("system", GOAL, "agent.application"),
    ("mcp", "我只想学 MCP；已经会基础 Tool 调用。", "agent.application"),
    ("node", "我已有一个 Node.js API，希望学习部署、监控、自动发布和恢复。", "cloud.services"),
    ("browser", "我已会 Agent 核心，想系统学习 Browser Agent 的网页信息获取与验证。", "agent.application"),
    ("coding", "我已会 Agent 核心，想学习 Coding Agent 的任务执行、代码修改与验证。", "agent.application"),
    ("travel", "我已经有一个旅行规划 Agent，希望系统补 Agent 基础，并强化网页信息获取、可恢复规划和知识检索。", "agent.application"),
    ("voice", "我想学习语音 Agent。", "agent.application"),
    ("commerce", "我已经有一个电商后台，想把它改造成带 AI 商品文案与客服能力的全栈应用。", "ai.fullstack"),
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
    db = create_test_database("studyplan_test_v613_business")
    try:
        assert db.name.startswith("studyplan_test_v613_business_")
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
            for key in ("agent.application", "ai.fullstack", "cloud.services", "python.engineering"):
                seed_reviewed_pack(conn, load_pack(CURRENT_PACKS[key]))
        if os.environ.get("STUDYPLAN_V613_KEEP_OWNED") == "1":
            private = ROOT / "var/v613/private"
            private.mkdir(parents=True, exist_ok=True)
            (private / "fake-database.json").write_text(json.dumps(db.__dict__), encoding="utf-8")
        yield db
    finally:
        if os.environ.get("STUDYPLAN_V613_KEEP_OWNED") != "1":
            db.drop()
        assert not roles_created_by_harness()


@pytest.fixture(scope="module")
def checkpoint_db():
    assert not instance_is_dedicated() and not roles_created_by_harness()
    db = create_test_database("studyplan_test_v613_checkpoint")
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
        case_ids=['C25'] if name in {'browser','coding','travel','voice','commerce'} else ['C22' if name=='rag' else 'C24'],
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
    if os.environ.get("STUDYPLAN_V613_KEEP_OWNED") == "1":
        private = ROOT / "var/v613/private"
        (private / ("fake-" + name + ".json")).write_text(json.dumps({
            "username": username, "password": "Test-pass1!", "project_id": params["project_id"],
            "run_id": run["run_id"]}, ensure_ascii=False), encoding="utf-8")
    (OUT / ("manifest-" + name + ".json")).write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / ("plan-" + name + ".json")).write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")


@pytest.mark.parametrize('name,goal,support',[('python','我想学习 Python 做本地 CSV 数据清洗与分析。','reviewed_index'),('search','我想系统学习陶艺制作与釉色实验。','search_only')])
def test_generic_python_search_only_pg(reviewed_db,name,goal,support):
    container=build_container(settings_for(reviewed_db))
    with TestClient(create_app(container)) as client:
        _,params,headers=register(client,'v613python')
        run,url,draft=generate(client,container,params,headers,goal)
        plan=confirm(client,params,headers,url,draft)
        workspace=client.get('/api/v1/workspace',params=params).json()
        with psycopg.connect(reviewed_db.migrator_dsn) as conn:
            frozen=conn.execute("SELECT detail FROM ai_run_events WHERE run_id=%s AND detail->>'kind'='planning_submission'",(run['run_id'],)).fetchone()[0]
        assert frozen['manifest']['resource_support']==support
        if name=='search':
            assert 'structure_input_format' not in frozen['manifest']
        else:
            assert draft['source_pack_key']=='python.engineering' and draft['source_pack_version']==2
        assert workspace['stages'] and plan['unit_links'] and plan['task_links']
        assert not container.planning_worker.tick()
    evidence('pg-'+name,case_ids=['C13','C25'],database=reviewed_db.name,run_id=run['run_id'],plan_id=plan['plan_id'],resource_support=support, generic_open_scope_persisted='PASS')


def test_long_guidance_new_synthetic_publication_for_edge(reviewed_db):
    from app.tools.map_semantic_content import bounded_extensions
    fixture = load_pack(CURRENT_PACKS['agent.application'])
    original = deepcopy(fixture)
    assert fixture['version'] == 7
    fixture['version'] = 7007
    stage = next(s for s in fixture['stage_blueprints'] if any('RAGFlow' in e['topic'] and e['topic'].startswith('项目学习：') for e in s.get('extensions', [])))
    candidate = next(e for e in stage['extensions'] if 'RAGFlow' in e['topic'] and e['topic'].startswith('项目学习：'))
    text = '学习方式：targeted_deep_dive\n' + 'PG 合成验收：检查状态与恢复证据。' * 60 + '\n最终产出与迁移必须完整保留。'
    assert len(text) > 850
    candidate['guidance'] = text
    stage['extensions'] = bounded_extensions(stage)
    with psycopg.connect(reviewed_db.migrator_dsn) as conn:
        seed_reviewed_pack(conn, fixture)
        assert conn.execute("SELECT published_payload FROM domain_packs WHERE pack_key='agent.application' AND version=7").fetchone()[0] == original
    container = build_container(settings_for(reviewed_db))
    with TestClient(create_app(container)) as client:
        username, params, headers = register(client, 'v613long')
        run, url, draft = generate(client, container, params, headers, RAG_GOAL)
        plan = confirm(client, params, headers, url, draft)
        workspace = client.get('/api/v1/workspace', params=params).json()
        assert plan['source_pack_version'] == 7007
        stage_id = next(s['stage_id'] for s in plan['stages'] if s['stable_key'] == stage['stable_key'])
        fragments = sorted((e for e in plan['extensions'] if e['stage_id'] == stage_id and 'RAGFlow' in e['topic']), key=lambda e:e['order_index'])
        assert len(fragments) >= 2 and text in ''.join(e['guidance'] for e in fragments)
        assert all(len(e['guidance']) <= 850 for e in fragments)
        with psycopg.connect(reviewed_db.migrator_dsn) as conn:
            submission = conn.execute("SELECT detail FROM ai_run_events WHERE run_id=%s AND detail->>'kind'='planning_submission'", (run['run_id'],)).fetchone()[0]
    for kind, payload in [('plan',plan),('workspace',workspace),('manifest',submission['manifest'])]:
        (OUT/(kind+'-long.json')).write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    if os.environ.get('STUDYPLAN_V613_KEEP_OWNED') == '1':
        private=ROOT/'var/v613/private'
        (private/'fake-long.json').write_text(json.dumps(dict(username=username,password='Test-pass1!',project_id=params['project_id'],run_id=run['run_id']),ensure_ascii=False),encoding='utf-8')
    evidence('pg-long', case_ids=['C23'], database=reviewed_db.name, fixture_provenance='Synthetic version7007 only; Agent7 version7 unchanged; display boundary fixture', text_chars=len(text), fragments=len(fragments), run_id=run['run_id'], plan_id=plan['plan_id'], ordered_lossless_readback='PASS')


def project_counts(db, project_id):
    from psycopg import sql
    tables=('plan_drafts','plan_revisions','knowledge_nodes','learning_units','practice_tasks')
    with psycopg.connect(db.migrator_dsn) as conn:
        return {table:conn.execute(sql.SQL('SELECT count(*) FROM {} WHERE project_id=%s').format(sql.Identifier(table)),(project_id,)).fetchone()[0] for table in tables}


def queued_authority(db, container, client, prefix='v613guard'):
    username,params,headers=register(client,prefix)
    response=client.post('/api/v1/plans/generate',params=params,headers=headers,json={'goal':GOAL})
    assert response.status_code == 202,response.text
    run_id=response.json()['run_id']
    with psycopg.connect(db.migrator_dsn) as conn:
        actor=conn.execute('SELECT actor_id FROM ai_runs WHERE run_id=%s',(run_id,)).fetchone()[0]
    authority=container.plan_service._planning_jobs.read_generation_authority(actor,params['project_id'],run_id)
    return username,params,headers,run_id,actor,authority['initial']


@pytest.mark.parametrize('mutation',['valid','canonical_rubric','teaching','dual_presentation','resource_role'])
def test_independent_pg_pre_save_projection_authority(reviewed_db,checkpoint_db,mutation):
    settings=settings_for(reviewed_db)
    container=build_container(settings)
    with TestClient(create_app(container)) as client:
        _,params,_,run_id,actor,initial=queued_authority(reviewed_db,container,client)
    project_id=params['project_id']
    claim=container.plan_service._planning_jobs.claim_next('v613-checkpoint-owned',300)
    assert claim is not None and claim.run_id==run_id
    pack=initial['domain_pack']
    thread_id=new_id('checkpoint')
    nodes=container.plan_service._build_nodes(project_id=project_id,run_id=run_id,goal=initial['goal'],selected_pack=pack,frozen_input=initial)
    config={'configurable':{'thread_id':thread_id},'recursion_limit':1000}
    with PostgresSaver.from_conn_string(checkpoint_db.migrator_dsn) as saver:
        graph=builder_for_version(SHORT_GENERATION_VERSION)(nodes,checkpointer=saver)
        graph.invoke(initial,config,interrupt_before=['save_draft_projection'])
        partial=graph.get_state(config)
        assert partial.next == ('save_draft_projection',)
        assert partial.values['units'] and partial.values['nodes']
        state=deepcopy(partial.values)
    authority=container.plan_service._planning_jobs.read_generation_authority(actor,project_id,run_id)
    assert authority['initial'] == initial
    assert len(authority['receipts']) == 1+2*len(initial['manifest']['stages'])
    assert all(n==0 for n in project_counts(reviewed_db,project_id).values())
    delta={}
    if mutation=='canonical_rubric':
        units=deepcopy(state['units']); key=next(iter(units[0]['rubric']['canonical_knowledge']))
        units[0]['rubric']['canonical_knowledge'][key]['scope']=['forged scope']
        delta={'units':units}
    elif mutation=='teaching':
        units=deepcopy(state['units']); units[0]['rubric']['teaching']['focus_refs']=['forged.focus']
        delta={'units':units}
    elif mutation=='dual_presentation':
        batches=deepcopy(state['structure_batches']);batches[0]['_reviewed_presentation']['units'][0]['title']='forged presentation'
        units=deepcopy(state['units']);units[0]['title']='forged presentation'
        delta={'structure_batches':batches,'units':units}
    elif mutation=='resource_role':
        outline=deepcopy(state['outline']);outline['sections'][0]['resources'][0]['role']='supplementary'
        delta={'outline':outline}
    if delta:
        with PostgresSaver.from_conn_string(checkpoint_db.migrator_dsn) as saver:
            graph=builder_for_version(SHORT_GENERATION_VERSION)(nodes,checkpointer=saver)
            graph.update_state(config,delta)
    fresh=build_container(settings)
    independent=fresh.plan_service._planning_jobs.read_generation_authority(actor,project_id,run_id)
    fresh_nodes=fresh.plan_service._build_nodes(project_id=project_id,run_id=run_id,goal=initial['goal'],selected_pack=independent['initial']['domain_pack'],frozen_input=independent['initial'])
    executor=PgPlanningExecutor(checkpoint_db.migrator_dsn,llm=fresh.plan_service._llm)
    if mutation=='valid':
        result=executor.execute_or_resume(fresh_nodes,independent['initial'],thread_id,SHORT_GENERATION_VERSION,lambda:None)
        counts=project_counts(reviewed_db,project_id)
        assert counts['plan_drafts']==1 and counts['knowledge_nodes']>0 and counts['plan_revisions']==0
        again=executor.execute_or_resume(fresh_nodes,independent['initial'],thread_id,SHORT_GENERATION_VERSION,lambda:None)
        assert again.state == result.state and project_counts(reviewed_db,project_id)==counts
        error_path=None
    else:
        with pytest.raises(GraphRecoveryError) as rejected:
            executor.execute_or_resume(fresh_nodes,independent['initial'],thread_id,SHORT_GENERATION_VERSION,lambda:None)
        error_path=str(rejected.value)
        forged=deepcopy(state);forged.update(delta)
        with pytest.raises(ValueError):
            fresh.plan_service._persist_draft(project_id=project_id,run_id=run_id,goal=initial['goal'],state=forged,selected_pack=independent['initial']['domain_pack'])
        assert all(n==0 for n in project_counts(reviewed_db,project_id).values())
    assert fresh.plan_service._llm.calls == []
    assert fresh.plan_service._planning_jobs.read_generation_authority(actor,project_id,run_id)==independent
    assert fresh.plan_service._planning_jobs.finish(claim,'completed' if mutation=='valid' else 'failed')
    evidence('pg-projection-'+mutation,case_ids=['C06'] if mutation=='valid' else ['C02','C03','C04' if mutation=='dual_presentation' else 'C05'], database=reviewed_db.name,checkpoint_database=checkpoint_db.name,run_id=run_id,mutation=mutation, retained_receipts=len(independent['receipts']), additional_fake_calls=0, rejection_path=error_path,business_counts=project_counts(reviewed_db,project_id), independent_database_authority='PASS')




def test_legal_draft_edit_and_cancel_fence(reviewed_db):
    container=build_container(settings_for(reviewed_db))
    with TestClient(create_app(container)) as client:
        _,params,headers=register(client,'v613edit')
        _,url,draft=generate(client,container,params,headers,GOAL)
        stages=deepcopy(draft['stages']);stages[0]['title']='用户合法编辑后的阶段标题'
        edited=client.post(url+'/decision',params=params,headers=headers,json=dict(decision='edit',expected_version=0,draft_hash=draft['draft_hash'],edited_stages=stages))
        assert edited.status_code==200,edited.text
        edited_draft=client.get(url,params=params).json()
        assert edited_draft['stages'][0]['title']==stages[0]['title']
        plan=confirm(client,params,headers,url,edited_draft)
        assert plan['stages'][0]['title']==stages[0]['title']
        _,cancel_params,cancel_headers=register(client,'v613cancel')
        queued=client.post('/api/v1/plans/generate',params=cancel_params,headers=cancel_headers,json={'goal':GOAL})
        assert queued.status_code==202
        cancelled=client.post('/api/v1/runs/'+queued.json()['run_id']+'/cancel',params=cancel_params,headers=cancel_headers,json=dict(expected_version=1,idempotency_key='v613-cancel'))
        assert cancelled.status_code==200,cancelled.text
        assert not container.planning_worker.tick()
    evidence('pg-edit-cancel',case_ids=['C07','C08'],legal_user_title_preserved='PASS',confirm_idempotency='PASS',cancel_prevents_claim='PASS', limitations='Resource/task edit, future prefix, lease expiry and concurrent confirm not exercised by this scoped case')


def test_successful_repair_receipt_precedes_checkpoint_replay_http_zero(reviewed_db,checkpoint_db,monkeypatch):
    """Known success replay through actual PG ledger and injected MockTransport."""
    from dataclasses import asdict
    import httpx
    from app.agent_workflows.planning_batches import structure_payload
    from app.domain.runs.fencing import PlanningWriteFence
    from app.infrastructure.providers.attempt_ledger import PgAttemptLLM
    from app.infrastructure.providers.openai_compatible import OpenAICompatibleLLM

    container=build_container(settings_for(reviewed_db))
    with TestClient(create_app(container)) as client:
        _,params,_,run_id,actor,initial=queued_authority(reviewed_db,container,client,'v613receipt')
    claim=container.plan_service._planning_jobs.claim_next('v613-receipt-owned',300)
    assert claim is not None and claim.run_id==run_id
    fence=PlanningWriteFence(**asdict(claim))
    project_id=params['project_id']
    fake=build_planning_demo()
    valid=fake._handlers['planning.structure']('planning.structure',structure_payload(initial,initial['manifest']['structure_batches'][0]))
    responses=[{'units':[]},valid]
    http_calls=[]
    def transport(request):
        http_calls.append(request.method)
        assert len(http_calls)<=2,'Unexpected new MockTransport dispatch'
        return httpx.Response(200,json={'choices':[{'message':{'content':json.dumps(responses[len(http_calls)-1],ensure_ascii=False)},'finish_reason':'stop'}],'usage':{'prompt_tokens':10,'completion_tokens':10}})
    with httpx.Client(transport=httpx.MockTransport(transport)) as http_client:
        provider=OpenAICompatibleLLM(base_url='https://owned-mock.invalid/v1',api_key='synthetic-test-only',model='owned-mock',client=http_client,budget_policy=DEFAULT_BUDGET)
        class Mixed:
            def __init__(self):
                self.ledger=PgAttemptLLM(reviewed_db.app_dsn,provider,manifest=initial['manifest'])
            def generate_structured(self,**kwargs):
                if kwargs['purpose'] in {'planning.structure','planning.repair'}:
                    return self.ledger.generate_structured(**kwargs)
                return fake.generate_structured(**kwargs)
        mixed=Mixed()
        nodes=container.plan_service._build_nodes(project_id=project_id,run_id=run_id,goal=initial['goal'],selected_pack=initial['domain_pack'],frozen_input=initial,llm=mixed,write_fence=fence)
        thread_id=new_id('checkpoint')
        config={'configurable':{'thread_id':thread_id},'recursion_limit':1000}
        with PostgresSaver.from_conn_string(checkpoint_db.migrator_dsn) as saver:
            graph=builder_for_version(SHORT_GENERATION_VERSION)(nodes,checkpointer=saver)
            graph.invoke(initial,config,interrupt_before=['repair_batch'])
            before=graph.get_state(config)
            assert before.next==('repair_batch',) and before.values['repair_count']==0
            old=deepcopy(before.values)
        assert len(http_calls)==1 and old['structure_errors']
        # Provider success commits before the graph delta/checkpoint is committed.
        success_delta=nodes.repair_batch(old)
        assert success_delta['repair_count']==1 and len(http_calls)==2
        with PostgresSaver.from_conn_string(checkpoint_db.migrator_dsn) as saver:
            saved=builder_for_version(SHORT_GENERATION_VERSION)(nodes,checkpointer=saver).get_state(config)
            assert saved.next==('repair_batch',) and saved.values['repair_count']==0
            assert saved.values['structure_batches']==old['structure_batches']
        fresh=build_container(settings_for(reviewed_db))
        authority=fresh.plan_service._planning_jobs.read_generation_authority(actor,project_id,run_id)
        with psycopg.connect(reviewed_db.migrator_dsn) as conn:
            rows=conn.execute('SELECT status,schema_name FROM ai_provider_attempts WHERE run_id=%s ORDER BY attempt_id',(run_id,)).fetchall()
        assert len(rows)==2 and all(row==('succeeded','ReviewedStructureV1') for row in rows)
        fresh_nodes=fresh.plan_service._build_nodes(project_id=project_id,run_id=run_id,goal=initial['goal'],selected_pack=authority['initial']['domain_pack'],frozen_input=authority['initial'],llm=Mixed(),write_fence=fence)
        executor=PgPlanningExecutor(checkpoint_db.migrator_dsn,llm=fresh_nodes.llm)
        # Exercise the real executor's pending-repair authority check, then stop
        # after exactly one compiled graph node to exclude unrelated next stages.
        monkeypatch.setattr(executor,'_stream',lambda graph,payload,config,progress:graph.invoke(payload,config,interrupt_after=['repair_batch']))
        replay=executor.execute_or_resume(fresh_nodes,authority['initial'],thread_id,SHORT_GENERATION_VERSION,lambda:None)
        assert replay.state['repair_count']==1
        assert replay.state['structure_batches']==success_delta['structure_batches']
        assert len(http_calls)==2 and len(fake.calls)==1 and not fresh.plan_service._llm.calls
        assert all(n==0 for n in project_counts(reviewed_db,project_id).values())
        assert fresh.plan_service._planning_jobs.finish(claim,'completed')
    evidence('pg-known-repair-replay',case_ids=['C06','C21'],database=reviewed_db.name,checkpoint_database=checkpoint_db.name,run_id=run_id,retained_successful_attempts=2, mock_http_initial=2,mock_http_during_recovery=0,real_http=0,known_success_replay='PASS',pending_repair_authority='PASS',scope='Controlled compiled recovery stops immediately after one repair node; no final Draft saving expected')
