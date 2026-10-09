"""One owned business/checkpoint pair, real Worker/HTTP, wholly synthetic ports."""

import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import psycopg
import pytest
from app import main
from app.agent_workflows.runtime import PostgresSaver
from app.application.container import AppContainer
from app.application.plan_service import PlanService
from app.application.v2_revisions import V2RevisionService
from app.core.config import get_settings
from app.core.errors import ConflictError
from app.core.ids import content_hash
from app.domain.planning.content_coverage import ReviewedContentIndex
from app.domain.planning.curriculum_compiler import CurriculumSourceFacts
from app.domain.planning.intent import GoalSpec
from app.domain.planning.resource_research import ResearchBudget
from app.infrastructure.db.browser_auth import PgBrowserAuth
from app.infrastructure.db.job_repository import PgPlanningJobRepository
from app.infrastructure.db.plan_repository import PgPlanRepository
from app.infrastructure.db.public_resource_catalog import PgPublicResourceCatalog
from app.infrastructure.db.run_repository import PgRunRepository
from app.infrastructure.db.v2_revisions import PgV2Revisions, budget_family
from app.infrastructure.providers.runtime_factory import OwnedV2PlanningRuntimeFactory
from app.infrastructure.providers.v2_attempts import PgV2Calls
from app.infrastructure.worker.planning_worker import PlanningWorker
from app.ports.llm import LLMFailure, LLMResult
from app.ports.planning_jobs import PlanningLeaseLostError
from fastapi.testclient import TestClient
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from backend.tests.integration.test_v2_planning_http_pg import ForbiddenDispatch
from backend.tests.integration.test_v2_planning_runtime_pg import (
    PipelineBodies,
    PipelineProvider,
    PipelineSearch,
)
from tests.pg_harness import create_test_database, harness_skip_reason, roles_created_by_harness

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "var/planning-v2-item9-clarification-20261009"
pytestmark = pytest.mark.postgres


@pytest.fixture(scope="module")
def databases():
    assert os.environ.get("STUDYPLAN_TEST_PG_DEDICATED", "").lower() not in {"1", "true", "yes", "on"}
    assert harness_skip_reason() is None
    business = create_test_database(prefix="studyplan_test_item9clarification")
    checkpoint = create_test_database(prefix="studyplan_test_item9clarification_cp")
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=ROOT / "backend",
        env=dict(
            os.environ,
            STUDYPLAN_MIGRATION_DSN=business.migrator_dsn.replace("postgresql://", "postgresql+psycopg://"),
        ),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    with psycopg.connect(checkpoint.migrator_dsn, autocommit=True) as conn:
        PostgresSaver(conn).setup()
        conn.execute("GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO studyplan_app")
    with psycopg.connect(business.migrator_dsn, row_factory=dict_row) as conn:
        columns = conn.execute(
            "SELECT column_name,data_type,is_nullable FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name='ai_run_events' ORDER BY ordinal_position"
        ).fetchall()
    assert not roles_created_by_harness()
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    EVIDENCE.joinpath("owned-databases.json").write_text(
        json.dumps(
            {
                "business": business.name,
                "checkpoint": checkpoint.name,
                "roles_created": [],
                "migration_exit": result.returncode,
                "run_event_schema": columns,
                "public_calls": 0,
            },
            indent=2,
        ),
        encoding="utf8",
    )
    EVIDENCE.joinpath("owned-" + business.name + ".json").write_text(
        EVIDENCE.joinpath("owned-databases.json").read_text(encoding="utf8"), encoding="utf8"
    )

    class Safe:
        def __init__(self, value):
            self.value = value

        def __getattr__(self, key):
            return getattr(self.value, key)

        def __repr__(self):
            return "OwnedPgDatabase(" + self.value.name + ")"

    yield Safe(business), Safe(checkpoint)


class ClarificationProvider(PipelineProvider):
    """Reuse real validators, preserve structured original user facts exactly."""

    def __init__(self, rounds=1, *, unknown=False, incomplete=False):
        super().__init__()
        self.rounds, self.unknown, self.incomplete = rounds, unknown, incomplete

    def generate_structured(self, **kw):
        from app.domain.planning.constraint_adaptation import (
            constraints_unresolved,
            curriculum_constraint_assessments,
        )

        from backend.tests.unit.test_curriculum import output as curriculum_output
        from backend.tests.unit.test_goal_requirement_analysis import output

        if kw["purpose"] == "planning.goal_requirement_analysis":
            self.calls.append(kw)
            if self.unknown:
                return LLMFailure("provider_transport_unknown", "synthetic unknown", dispatch_unknown=True)
            goal, clarification = kw["payload"]["goal"], kw["payload"].get("clarification")
            constraints = [
                {"text": text, "source_refs": [f"goal.constraints[{i}]"]}
                for i, text in enumerate(goal["constraints"])
            ]
            claims = (
                [{"text": goal["starting_point"], "source_refs": ["goal.starting_point"]}]
                if goal["starting_point"]
                else []
            )
            if clarification:
                constraints = clarification["retained_facts"]["hard_constraints"]
                claims = clarification["retained_facts"]["learner_claims"]
            need = self.rounds > 0
            self.rounds -= int(need)
            value = output(
                target_summary=goal["target"],
                required_requirements=[
                    {
                        "text": goal["target"],
                        "origin": "explicit",
                        "rationale": "",
                        "source_refs": ["goal.target"]
                        + ([clarification["answers"][-1]["source_ref"]] if clarification else []),
                    }
                ],
                hard_constraints=constraints,
                learner_claims=claims,
                status="needs_clarification" if need else "ready",
                clarification_questions=["本次最终产物是什么？"] if need else [],
            )
            return LLMResult(value, self.model, "fixture", input_tokens=20, output_tokens=16, cost_micros=100)
        if kw["purpose"] == "planning.curriculum_composition":
            self.calls.append(kw)
            payload = kw["payload"]
            value = curriculum_output(
                SimpleNamespace(to_payload=lambda: payload, input_hash=payload["input_hash"]),
                project_study=self.incomplete,
            )
            value["status"] = (
                "incomplete"
                if (
                    value["unresolved"]
                    or self.incomplete
                    or constraints_unresolved(curriculum_constraint_assessments(value, payload))
                )
                else "complete"
            )
            return LLMResult(value, self.model, "fixture", input_tokens=20, output_tokens=16, cost_micros=100)
        return super().generate_structured(**kw)


def environment(databases, monkeypatch, *, provider=None, budget=None):
    db, cp = databases
    auth = PgBrowserAuth(db.app_dsn, 3600)
    token = auth.register("item9_" + uuid4().hex[:12], "pytest42", "owned")
    scope = auth.resolve(token)
    project = scope.learning_project_scope[0]
    provider, search, body = provider or ClarificationProvider(), PipelineSearch(), PipelineBodies()
    factory = OwnedV2PlanningRuntimeFactory(
        db.app_dsn,
        cp.app_dsn,
        source_facts=CurriculumSourceFacts(ReviewedContentIndex("empty", (), (), ())),
        budget=budget
        or ResearchBudget(max_output_tokens=131072, max_total_requests=50, max_cost_micros=1000000),
        binding_resolver=lambda *_: SimpleNamespace(model_ref="test:frozen"),
        provider_resolver=lambda *_: provider,
        github=search,
        body_reader=body,
    )
    jobs, runs, repo = (
        PgPlanningJobRepository(db.app_dsn, actor_ids=(scope.actor_id,)),
        PgRunRepository(db.app_dsn),
        PgPlanRepository(db.app_dsn),
    )
    service = PlanService(
        repository=repo,
        runs=runs,
        catalog=ForbiddenDispatch(),
        resources=PgPublicResourceCatalog(db.app_dsn),
        llm=ForbiddenDispatch(),
        graph_version="",
        planning_jobs=jobs,
        v2_runtime_factory=factory,
    )
    revisions = PgV2Revisions(db.app_dsn, planning_jobs=jobs, runtime_factory=factory)
    worker = PlanningWorker(jobs=jobs, execute=service.execute_generation, actor_ids=(scope.actor_id,))
    settings = replace(get_settings(), app_env="development", session_cookie_secure=False)
    monkeypatch.setattr(main, "get_settings", lambda: settings)
    container = AppContainer(
        settings=settings,
        sessions=auth,
        browser_auth=auth,
        plan_service=service,
        planning_worker=worker,
        v2_revision_service=V2RevisionService(revisions),
    )
    client = TestClient(main.create_app(container))
    client.cookies.set(settings.session_cookie_name, token)
    return SimpleNamespace(
        db=db,
        cp=cp,
        auth=auth,
        token=token,
        scope=scope,
        project=project,
        provider=provider,
        search=search,
        body=body,
        factory=factory,
        jobs=jobs,
        runs=runs,
        repo=repo,
        service=service,
        revisions=revisions,
        worker=worker,
        client=client,
        params={"project_id": project},
        headers={"X-CSRF-Token": auth.detail(token)[0]["csrf_token"]},
    )


def first(env, goal=None):
    goal = goal or GoalSpec(
        "学习MCP", starting_point="已会Python", constraints=("教材必须免费",), project_context="已有CLI项目"
    )
    run_id = env.service.submit_owned_v2(scope=env.scope, project_id=env.project, goal_spec=goal)
    assert env.worker.tick()
    view = env.client.get("/api/v1/runs/" + run_id, params=env.params)
    assert view.status_code == 200
    return run_id, view.json()


def request(run_id, view, *, key="clarification"):
    return {
        "parent_run_id": run_id,
        "clarification_version": view["clarification"]["clarification_version"],
        "answers": [
            {"question_id": q["question_id"], "answer_text": "本地MCP工具演示"}
            for q in view["clarification"]["questions"]
        ],
        "idempotency_key": key,
    }


def post(env, payload):
    return env.client.post(
        "/api/v1/plans/v2/owned/clarifications", params=env.params, headers=env.headers, json=payload
    )


def snapshot(env, run):
    with psycopg.connect(env.db.migrator_dsn, row_factory=dict_row) as conn:
        return {
            "run": conn.execute("SELECT * FROM ai_runs WHERE run_id=%s", (run,)).fetchone(),
            "receipts": conn.execute(
                "SELECT * FROM ai_provider_attempts WHERE run_id=%s ORDER BY attempt_id", (run,)
            ).fetchall(),
        }


def test_real_http_clarification_complete_confirm_fresh_readback(databases, monkeypatch):
    env = environment(databases, monkeypatch)
    with env.client:
        availability = env.client.get("/api/v1/plans/v2/availability", params=env.params)
        assert availability.json()["initial_generation"] and availability.json()["semantic_replanning"]
        run, view = first(env)
        assert view["status"] == "failed" and view["error"]["code"] == "goal_clarification_required"
        assert view["error"]["message"].startswith("需要补充信息")
        assert view["clarification"]["can_submit_answers"]
        original = snapshot(env, run)
        body = request(run, view)
        assert (
            env.client.post("/api/v1/plans/v2/owned/clarifications", params=env.params, json=body).status_code
            == 403
        )
        response = post(env, body)
        assert response.status_code == 202, response.text
        child = response.json()["run_id"]
        assert child != run and post(env, body).json()["run_id"] == child
        changed = {**body, "answers": [{**body["answers"][0], "answer_text": "另一个答案"}]}
        assert post(env, changed).status_code == 409
        assert env.worker.tick()
        done = env.client.get(response.json()["status_url"]).json()
        assert done["status"] == "succeeded", json.dumps(done, ensure_ascii=False)
        assert snapshot(env, run) == original
        profile_calls = [
            c for c in env.provider.calls if c["purpose"] == "planning.goal_requirement_analysis"
        ]
        new_input = profile_calls[-1]["payload"]
        assert new_input["goal"] == profile_calls[0]["payload"]["goal"]
        assert new_input["clarification"]["answers"][0]["question_id"] == body["answers"][0]["question_id"]
        assert new_input["clarification"]["answers"][0]["answer_text"] == body["answers"][0]["answer_text"]
        draft = env.client.get("/api/v1/plans/drafts/" + done["result_ref"], params=env.params).json()
        path = "/api/v1/plans/drafts/" + draft["draft_id"] + "/decision"
        decision = {
            "decision": "approve",
            "expected_version": 0,
            "draft_hash": draft["draft_hash"],
            "idempotency_key": "confirm",
        }
        approved = env.client.post(path, params=env.params, headers=env.headers, json=decision)
        assert approved.status_code == 200, approved.text
        plan = approved.json()["plan"]
        current = env.client.get("/api/v1/plans/current", params=env.params).json()
        history = env.client.get("/api/v1/plans/revisions/1", params=env.params).json()
        assert current == history == plan
        assert PgPlanRepository(env.db.app_dsn).get_current(project_id=env.project).plan_id == plan["plan_id"]
        assert (
            env.client.post(
                "/api/v1/plans/generate", params=env.params, headers=env.headers, json={"goal": "学习MCP"}
            ).status_code
            == 503
        )
        assert not env.worker.tick()
        with psycopg.connect(env.db.app_dsn, row_factory=dict_row) as conn:
            conn.execute(
                "SELECT set_config('app.actor_id',%s,true),set_config('app.project_id',%s,true)",
                (env.scope.actor_id, env.project),
            )
            root, family = budget_family(
                conn, actor_id=env.scope.actor_id, project_id=env.project, run_id=child
            )
            usage = PgV2Calls.family_reservations(conn, family, list(family))
        assert root == run and set(family) == {run, child} and usage["total_requests"] > 1
        EVIDENCE.joinpath("http-success-chain.json").write_text(
            json.dumps(
                {
                    "root": run,
                    "child": child,
                    "original": view,
                    "finished": done,
                    "draft": draft,
                    "plan": plan,
                    "budget_usage": usage,
                    "real_product_calls": 0,
                    "cookie_csrf": "PASS",
                    "fresh_readback": "PASS",
                    "original_run_receipt_unchanged": True,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf8",
        )


@pytest.mark.parametrize(
    "case,expected",
    [
        ("question", 400),
        ("version", 409),
        ("empty", 400),
        ("duplicate", 400),
        ("hash", 422),
        ("long", 422),
        ("missing", 422),
    ],
)
def test_http_question_version_answer_binding_matrix(databases, monkeypatch, case, expected):
    env = environment(databases, monkeypatch)
    with env.client:
        run, view = first(env)
        body = request(run, view)
        if case == "question":
            body["answers"][0]["question_id"] = "question_fake"
        elif case == "version":
            body["clarification_version"] = 2
        elif case == "empty":
            body["answers"][0]["answer_text"] = "   "
        elif case == "duplicate":
            body["answers"] *= 2
        elif case == "hash":
            body["profile_hash"] = "f" * 64
        elif case == "long":
            body["answers"][0]["answer_text"] = "x" * 2001
        else:
            body["answers"] = []
        assert post(env, body).status_code == expected
        with psycopg.connect(env.db.migrator_dsn) as conn:
            assert (
                conn.execute("SELECT count(*) FROM ai_runs WHERE project_id=%s", (env.project,)).fetchone()[0]
                == 1
            )
        assert len(env.provider.calls) == 1


@pytest.mark.parametrize(
    "case",
    [
        "cross_actor",
        "cross_project",
        "receipt",
        "profile",
        "manifest",
        "cancelled",
        "ordinary_failed",
        "unknown",
        "reconciliation",
    ],
)
def test_forbidden_parent_and_tamper_matrix(databases, monkeypatch, case):
    env = environment(databases, monkeypatch)
    with env.client:
        run, view = first(env)
        body = request(run, view)
        if case == "cross_actor":
            token = env.auth.register("other_" + uuid4().hex[:12], "pytest42", "owned")
            other = env.auth.resolve(token)
            env.client.cookies.set(get_settings().session_cookie_name, token)
            assert env.client.get("/api/v1/runs/" + run, params=env.params).status_code == 403
            env.headers = {"X-CSRF-Token": env.auth.detail(token)[0]["csrf_token"]}
            env.params = {"project_id": other.learning_project_scope[0]}
            assert post(env, body).status_code == 409
            return
        if case == "cross_project":
            response = env.client.post(
                "/api/v1/plans/v2/owned/clarifications",
                params={"project_id": "other"},
                headers=env.headers,
                json=body,
            )
            assert response.status_code == 403
            return
        with psycopg.connect(env.db.migrator_dsn, row_factory=dict_row) as conn:
            if case == "receipt":
                conn.execute(
                    "UPDATE ai_provider_attempts SET response_payload=jsonb_set(response_payload,'{digest}','\"tampered\"') WHERE run_id=%s",
                    (run,),
                )
            elif case == "profile":
                conn.execute(
                    "UPDATE ai_run_events SET detail=jsonb_set(detail,'{profile_hash}','\"tampered\"') WHERE run_id=%s AND status='v2_clarification'",
                    (run,),
                )
            elif case == "manifest":
                conn.execute(
                    "UPDATE ai_run_events SET detail=jsonb_set(detail,'{manifest,goal_hash}','\"tampered\"') WHERE run_id=%s AND status='submission'",
                    (run,),
                )
            elif case == "cancelled":
                conn.execute("UPDATE ai_runs SET status='cancelled' WHERE run_id=%s", (run,))
            elif case == "ordinary_failed":
                conn.execute("UPDATE ai_runs SET error_class='provider_invalid_json' WHERE run_id=%s", (run,))
            elif case == "reconciliation":
                conn.execute(
                    "UPDATE ai_runs SET status='reconciliation_required',next_action='reconcile' WHERE run_id=%s",
                    (run,),
                )
            else:
                conn.execute(
                    "UPDATE ai_runs SET error_class='provider_transport_unknown' WHERE run_id=%s", (run,)
                )
        assert post(env, body).status_code == 409
        latest = env.client.get("/api/v1/runs/" + run, params=env.params).json()
        assert latest["clarification"] is None
        assert len(env.provider.calls) == 1


@pytest.mark.parametrize("different_keys", [False, True])
def test_concurrent_answer_identity_and_ordinary_initial_guard(databases, monkeypatch, different_keys):
    env = environment(databases, monkeypatch)
    run, view = first(env)
    body = request(run, view)

    def submit(body):
        try:
            return env.service.submit_owned_clarification(scope=env.scope, project_id=env.project, **body)
        except ConflictError:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        children = list(pool.map(submit, [body, {**body, "idempotency_key": "second"} if different_keys else body]))
    if different_keys:
        assert children.count("conflict") == 1
    else:
        assert children[0] == children[1] != "conflict"
    assert submit({**body, "idempotency_key": "another"}) == "conflict"
    with pytest.raises(ConflictError, match="已有规划运行"):
        env.service.submit_owned_v2(
            scope=env.scope, project_id=env.project, goal_spec=GoalSpec("第二个初始目标")
        )
    with psycopg.connect(env.db.migrator_dsn) as conn:
        assert (
            conn.execute("SELECT count(*) FROM ai_runs WHERE project_id=%s", (env.project,)).fetchone()[0]
            == 2
        )
    EVIDENCE.joinpath("concurrency.json").write_text(
        json.dumps(
            {
                "same_body_same_run": children[0] == children[1],
                "different_keys_one_child": different_keys,
                "different_key_conflict": True,
                "ordinary_second_root": "409",
                "family_run_count": 2,
            }
        ),
        encoding="utf8",
    )


def test_two_explicit_rounds_no_auto_third_request(databases, monkeypatch):
    env = environment(databases, monkeypatch, provider=ClarificationProvider(rounds=3))
    run, view = first(env)
    roots = [run]
    for round_number in (1, 2):
        assert view["clarification"]["can_submit_answers"]
        response = post(env, request(run, view, key="round" + str(round_number)))
        assert response.status_code == 202, response.text
        run = response.json()["run_id"]
        roots.append(run)
        assert env.worker.tick()
        view = env.client.get(response.json()["status_url"]).json()
        assert view["clarification"]["clarification_version"] == round_number + 1
        assert not env.worker.tick()
    assert not view["clarification"]["can_submit_answers"]
    assert post(env, request(run, view, key="third")).status_code == 422
    assert len(env.provider.calls) == 3
    inputs = [
        c["payload"]["clarification"]["answers"]
        for c in env.provider.calls
        if "clarification" in c["payload"]
    ]
    assert [len(values) for values in inputs] == [1, 2]
    assert inputs[-1][0] == inputs[0][0]


@pytest.mark.parametrize("case", ["cap", "excess", "unknown_sibling", "budget_reset"])
def test_shared_original_budget_admission_matrix(databases, monkeypatch, case):
    budget = ResearchBudget(
        max_output_tokens=131072, max_total_requests=1 if case == "cap" else 50, max_cost_micros=1000000
    )
    env = environment(databases, monkeypatch, budget=budget)
    run, view = first(env)
    with psycopg.connect(env.db.migrator_dsn, row_factory=dict_row) as conn:
        if case == "excess":
            manifest = env.jobs.read_submission(env.project, run)["manifest"]
            detail = {
                "manifest_hash": manifest["manifest_hash"],
                "attempt_id": "probe",
                "excess": {"total_requests": 50},
            }
            detail["digest"] = content_hash(detail)
            conn.execute(
                "INSERT INTO ai_run_events(run_id,status,detail) VALUES(%s,'v2_observed_excess',%s)",
                (run, Jsonb(detail)),
            )
        elif case == "unknown_sibling":
            conn.execute(
                "INSERT INTO ai_provider_attempts(attempt_id,run_id,provider,model_id,status) VALUES(%s,%s,'synthetic','fixture','reconciliation_required')",
                ("unknown_" + uuid4().hex, run),
            )
    if case == "budget_reset":
        env.factory.budget = replace(budget, max_total_requests=budget.max_total_requests + 1)
    assert post(env, request(run, view)).status_code in {400, 409}
    with psycopg.connect(env.db.migrator_dsn) as conn:
        assert (
            conn.execute("SELECT count(*) FROM ai_runs WHERE project_id=%s", (env.project,)).fetchone()[0]
            == 1
        )
    assert len(env.provider.calls) == 1


def test_unknown_child_retains_identity_budget_no_redispatch(databases, monkeypatch):
    env = environment(databases, monkeypatch)
    run, view = first(env)
    response = post(env, request(run, view))
    assert response.status_code == 202
    child = response.json()["run_id"]
    env.provider.unknown = True
    assert env.worker.tick()
    unknown = env.client.get(response.json()["status_url"]).json()
    assert unknown["status"] == "reconciliation_required" and unknown["clarification"] is None
    assert not env.worker.tick()
    assert post(env, {**request(run, view), "parent_run_id": child}).status_code == 409
    before = len(env.provider.calls)
    assert post(env, request(run, view)).json()["run_id"] == child
    assert len(env.provider.calls) == before
    with psycopg.connect(env.db.app_dsn, row_factory=dict_row) as conn:
        conn.execute(
            "SELECT set_config('app.actor_id',%s,true),set_config('app.project_id',%s,true)",
            (env.scope.actor_id, env.project),
        )
        _, family = budget_family(conn, actor_id=env.scope.actor_id, project_id=env.project, run_id=child)
        assert PgV2Calls.family_reservations(conn, family, list(family))["total_requests"] == 2


def test_success_receipt_recovery_and_new_worker_fence(databases, monkeypatch):
    env = environment(databases, monkeypatch)
    run = env.service.submit_owned_v2(scope=env.scope, project_id=env.project, goal_spec=GoalSpec("学习MCP"))
    claim = env.jobs.claim(env.project, "old-worker", 600)
    original = env.provider.generate_structured

    def lose_fence(**kw):
        result = original(**kw)
        with psycopg.connect(env.db.migrator_dsn) as conn:
            conn.execute(
                "UPDATE ai_jobs SET lease_token='replacement',lease_expires_at=clock_timestamp()-interval '1 second' WHERE run_id=%s",
                (run,),
            )
        return result

    env.provider.generate_structured = lose_fence
    with pytest.raises(PlanningLeaseLostError):
        env.service.execute_generation(env.project, run, claim=claim)
    with psycopg.connect(env.db.migrator_dsn) as conn:
        assert (
            conn.execute(
                "SELECT count(*) FROM ai_provider_attempts WHERE run_id=%s AND status='succeeded'", (run,)
            ).fetchone()[0]
            == 1
        )
        assert (
            conn.execute(
                "SELECT count(*) FROM ai_run_events WHERE run_id=%s AND status='v2_clarification'", (run,)
            ).fetchone()[0]
            == 0
        )
    env.provider.generate_structured = original
    assert env.worker.tick()
    recovered = env.client.get("/api/v1/runs/" + run, params=env.params).json()
    assert recovered["clarification"]["can_submit_answers"]
    assert len(env.provider.calls) == 1
    assert not env.worker.tick()
    EVIDENCE.joinpath("receipt-fence-recovery.json").write_text(
        json.dumps(
            {
                "run": run,
                "receipt_without_checkpoint": "PASS",
                "old_fence_rejected": "PASS",
                "new_worker_recovery": "PASS",
                "synthetic_dispatch_count": 1,
                "redispatch_delta": 0,
            }
        ),
        encoding="utf8",
    )


def test_normal_ready_and_incomplete_typed_diagnostics(databases, monkeypatch):
    env = environment(databases, monkeypatch, provider=ClarificationProvider(rounds=0, incomplete=True))
    run, view = first(env)
    assert view["status"] == "failed" and view["error"]["code"] == "v2_curriculum_incomplete", view
    assert view["result_ref"] is None and view["clarification"] is None
    assert view["planning_issues"]
    assert {i["code"] for i in view["planning_issues"]} == {
        "curriculum_incomplete",
        "project_case_unresolved",
    }
    assert all(set(issue) == {"code", "message"} for issue in view["planning_issues"])
    with psycopg.connect(env.db.migrator_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM plan_drafts WHERE run_id=%s", (run,)).fetchone()[0] == 0


def test_ready_then_semantic_replanning_uses_original_clarification_root(databases, monkeypatch):
    env = environment(databases, monkeypatch)
    root, view = first(env, GoalSpec("学习MCP"))
    response = post(env, request(root, view))
    assert response.status_code == 202 and env.worker.tick()
    child = response.json()["run_id"]
    run = env.runs.get_run(project_id=env.project, run_id=child)
    draft = env.repo.get_draft(project_id=env.project, draft_id=run.result_ref)
    from app.domain.planning.models import PlanPublicationService

    base = PlanPublicationService(env.repo).publish(
        draft=draft, presented_hash=draft.content_hash, expected_version=0, idempotency_key="root-confirm"
    )
    current = env.repo.get_current(project_id=env.project)
    from app.domain.planning.revisions import LocalStageEdit

    local = env.revisions.preview_local(
        scope=env.scope,
        project_id=env.project,
        current_plan_id=current.plan_id,
        expected_version=1,
        idempotency_key="local-after-clarification",
        stage_edits=(
            LocalStageEdit(current.stages[-1].stage_id, what_to_learn="在原目标内核对正常与失败结果"),
        ),
    ).draft
    assert local.v2_revision.to_payload()["budget_root_run_id"] == root
    cancelled = env.revisions.cancel(
        scope=env.scope,
        project_id=env.project,
        draft_id=local.draft_id,
        expected_version=1,
        draft_hash=local.content_hash,
    )
    assert cancelled.draft.status.value == "cancelled"
    semantic = env.revisions.submit_semantic(
        scope=env.scope,
        project_id=env.project,
        current_plan_id=current.plan_id,
        expected_version=1,
        idempotency_key="semantic",
        goal_spec=GoalSpec("继续学习MCP"),
    )
    assert env.worker.tick()
    result = env.runs.get_run(project_id=env.project, run_id=semantic)
    assert result.status.value == "succeeded", result
    preview = env.revisions.get_preview(
        scope=env.scope, project_id=env.project, draft_id=result.result_ref
    ).draft
    assert preview.v2_revision.to_payload()["budget_root_run_id"] == root
    final = env.revisions.confirm(
        scope=env.scope,
        project_id=env.project,
        draft_id=preview.draft_id,
        expected_version=1,
        draft_hash=preview.content_hash,
        idempotency_key="semantic-confirm",
    ).plan
    assert final.revision == 2
    assert env.repo.get_revision(project_id=env.project, revision=1).plan_id == base.plan_id
    with env.revisions._connection(env.scope, env.project) as conn:
        budget_root, family = budget_family(
            conn, actor_id=env.scope.actor_id, project_id=env.project, run_id=semantic
        )
    assert budget_root == root and set(family) == {root, child, semantic}
    EVIDENCE.joinpath("clarification-semantic-chain.json").write_text(
        json.dumps(
            {
                "root": root,
                "child": child,
                "semantic": semantic,
                "budget_family": list(family),
                "revision": final.revision,
                "original_history_preserved": True,
            }
        ),
        encoding="utf8",
    )


def test_normal_ready_then_semantic_still_works(databases, monkeypatch):
    env = environment(databases, monkeypatch, provider=ClarificationProvider(rounds=0))
    root, view = first(env, GoalSpec("学习MCP"))
    assert view["status"] == "succeeded" and view["clarification"] is None
    draft = env.repo.get_draft(project_id=env.project, draft_id=view["result_ref"])
    from app.domain.planning.models import PlanPublicationService

    PlanPublicationService(env.repo).publish(
        draft=draft,
        presented_hash=draft.content_hash,
        expected_version=0,
        idempotency_key="old-ready-confirm",
    )
    current = env.repo.get_current(project_id=env.project)
    run = env.revisions.submit_semantic(
        scope=env.scope,
        project_id=env.project,
        current_plan_id=current.plan_id,
        expected_version=1,
        idempotency_key="old-semantic",
        goal_spec=GoalSpec("继续学习MCP"),
    )
    assert env.worker.tick()
    result = env.runs.get_run(project_id=env.project, run_id=run)
    assert result.status.value == "succeeded", result
    assert (
        env.revisions.get_preview(
            scope=env.scope, project_id=env.project, draft_id=result.result_ref
        ).draft.v2_revision.to_payload()["budget_root_run_id"]
        == root
    )


def test_semantic_needs_clarification_cannot_use_initial_continuation(databases, monkeypatch):
    env = environment(databases, monkeypatch, provider=ClarificationProvider(rounds=0))
    root, view = first(env, GoalSpec("学习MCP"))
    draft = env.repo.get_draft(project_id=env.project, draft_id=view["result_ref"])
    from app.domain.planning.models import PlanPublicationService

    PlanPublicationService(env.repo).publish(
        draft=draft,
        presented_hash=draft.content_hash,
        expected_version=0,
        idempotency_key="semantic-needs-confirm",
    )
    current = env.repo.get_current(project_id=env.project)
    env.provider.rounds = 1
    run = env.revisions.submit_semantic(
        scope=env.scope,
        project_id=env.project,
        current_plan_id=current.plan_id,
        expected_version=1,
        idempotency_key="semantic-needs",
        goal_spec=GoalSpec("继续学习MCP"),
    )
    assert env.worker.tick()
    result = env.client.get("/api/v1/runs/" + run, params=env.params).json()
    assert result["error"]["code"] == "goal_clarification_required" and result["clarification"] is None
    assert (
        post(
            env,
            {
                "parent_run_id": run,
                "clarification_version": 1,
                "answers": [{"question_id": "question_fake", "answer_text": "新事实"}],
                "idempotency_key": "invalid-initial",
            },
        ).status_code
        == 409
    )


def test_question_persistence_interruption_recovers_without_redispatch(databases, monkeypatch):
    from app.infrastructure.db import v2_clarifications

    env = environment(databases, monkeypatch)
    original = v2_clarifications.freeze_questions

    def interrupted(*args, **kwargs):
        raise psycopg.OperationalError("synthetic owned write interruption")

    monkeypatch.setattr(v2_clarifications, "freeze_questions", interrupted)
    run = env.service.submit_owned_v2(scope=env.scope, project_id=env.project, goal_spec=GoalSpec("学习MCP"))
    assert env.worker.tick()
    partial = env.client.get("/api/v1/runs/" + run, params=env.params).json()
    assert partial["status"] == "running" and partial["clarification"] is None
    with psycopg.connect(env.db.migrator_dsn) as conn:
        assert conn.execute("SELECT status FROM ai_jobs WHERE run_id=%s", (run,)).fetchone()[0] == "running"
        conn.execute("UPDATE ai_jobs SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE run_id=%s", (run,))
    monkeypatch.setattr(v2_clarifications, "freeze_questions", original)
    assert env.worker.tick()
    finished = env.client.get("/api/v1/runs/" + run, params=env.params).json()
    assert finished["status"] == "failed" and finished["clarification"]["can_submit_answers"]
    assert len(env.provider.calls) == 1


@pytest.mark.parametrize("tamper", ["missing_context", "changed_context"])
def test_runtime_context_must_match_frozen_child_before_any_dispatch(databases, monkeypatch, tamper):
    from copy import deepcopy

    from app.domain.planning.v2_runtime import V2RecoveryBlocked
    from app.domain.runs.fencing import PlanningWriteFence

    env = environment(databases, monkeypatch)
    run, view = first(env, GoalSpec("学习MCP"))
    response = post(env, request(run, view))
    assert response.status_code == 202
    child = response.json()["run_id"]
    claim = env.jobs.claim(env.project, "context-check", 600)
    submission = env.jobs.read_claim_submission(claim)
    initial = deepcopy(submission["initial"])
    if tamper == "missing_context":
        initial.pop("v2_clarification")
    else:
        initial["v2_clarification"]["item1_input"]["answers"][0]["answer_text"] = "forged runtime answer"
    fence = PlanningWriteFence(claim.job_id, child, env.project, env.scope.actor_id, claim.lease_token)
    runtime = env.factory(env.scope, env.project, child, manifest=submission["manifest"],
        write_fence=fence, thread_id=env.runs.get_run(project_id=env.project, run_id=child).thread_id, guard=lambda: None)
    before = len(env.provider.calls)
    try:
        with pytest.raises(V2RecoveryBlocked):
            runtime.execute(initial)
    finally:
        delta = len(env.provider.calls) - before
        EVIDENCE.joinpath(f"runtime-context-{tamper}-dispatch-delta-{delta}.json").write_text(
            json.dumps({"case": tamper, "dispatch_delta": delta}), encoding="utf8")
    assert len(env.provider.calls) == before


def test_availability_uses_current_actor_admission_and_actual_owned_assembly(databases, monkeypatch):
    env = environment(databases, monkeypatch)
    with env.client:
        path = "/api/v1/plans/v2/availability"
        env.jobs._actor_ids = ()
        view = env.client.get(path, params=env.params).json()
        assert not view["initial_generation"] and not view["clarification"] and not view["semantic_replanning"]
        rejected = env.client.post("/api/v1/plans/v2/owned/generate", params=env.params, headers=env.headers,
            json={"goal": "学习MCP"})
        assert rejected.status_code == 403
        assert env.provider.calls == []
        env.jobs._admission_mode = "trusted_server"
        view = env.client.get(path, params=env.params).json()
        assert view["initial_generation"] and view["clarification"] and view["semantic_replanning"]
        env.service._v2_runtime_factory = None
        view = env.client.get(path, params=env.params).json()
        assert not view["initial_generation"] and not view["clarification"] and not view["semantic_replanning"]
        assert env.client.post("/api/v1/plans/generate", params=env.params, headers=env.headers,
            json={"goal": "学习MCP"}).status_code == 503


def test_resealed_false_answer_fingerprint_rejects_before_dispatch(databases, monkeypatch):
    from app.domain.planning.clarification import sealed
    env = environment(databases, monkeypatch)
    root, view = first(env, GoalSpec("学习MCP"))
    response = post(env, request(root, view))
    child = response.json()["run_id"]
    submission = env.jobs.read_submission(env.project, child)
    context = submission["initial"]["v2_clarification"]
    context.pop("context_hash")
    context["input_hash"] = "f" * 64
    context = sealed(context)
    submission["initial"]["v2_clarification"] = context
    manifest = submission["manifest"]
    manifest["v2_clarification_hash"] = context["context_hash"]
    manifest["manifest_hash"] = content_hash({k: v for k, v in manifest.items() if k != "manifest_hash"})
    submission["initial"]["manifest"] = manifest
    with psycopg.connect(env.db.migrator_dsn, row_factory=dict_row) as conn:
        conn.execute("UPDATE ai_run_events SET detail=%s WHERE run_id=%s AND status='submission'", (Jsonb(submission), child))
        confirmation = conn.execute("SELECT detail FROM ai_run_events WHERE run_id=%s AND status='v2_clarification_submission'", (root,)).fetchone()["detail"]
        confirmation.pop("context_hash")
        confirmation.update(input_hash=context["input_hash"], continuation_hash=context["context_hash"])
        conn.execute("UPDATE ai_run_events SET detail=%s WHERE run_id=%s AND status='v2_clarification_submission'", (Jsonb(sealed(confirmation)), root))
    before = len(env.provider.calls)
    assert env.worker.tick()
    result = env.client.get(response.json()["status_url"]).json()
    assert result["status"] == "reconciliation_required", result
    assert len(env.provider.calls) == before


@pytest.mark.parametrize("tamper", ["source_snapshot", "server_context"])
def test_resealed_incomplete_checkpoint_is_validated_before_public_issues(databases, monkeypatch, tamper):
    from app.core.ids import canonical_json
    from app.domain.runs.fencing import PlanningWriteFence
    from app.infrastructure.db import v2_clarifications
    from app.ports.summaries import ReviewPersistenceInterrupted

    env = environment(databases, monkeypatch, provider=ClarificationProvider(rounds=0, incomplete=True))
    original = v2_clarifications.freeze_planning_issues
    def stop(*args, **kwargs):
        raise ReviewPersistenceInterrupted("owned interruption before issue event")
    monkeypatch.setattr(v2_clarifications, "freeze_planning_issues", stop)
    root, view = first(env, GoalSpec("学习MCP"))
    assert view["status"] == "running"
    with psycopg.connect(env.db.migrator_dsn, row_factory=dict_row) as conn:
        row = conn.execute("SELECT j.*,r.thread_id FROM ai_jobs j JOIN ai_runs r USING(run_id) WHERE j.run_id=%s", (root,)).fetchone()
    manifest = env.jobs.read_submission(env.project, root)["manifest"]
    fence = PlanningWriteFence(row["job_id"], root, env.project, env.scope.actor_id, row["lease_token"])
    runtime = env.factory(env.scope, env.project, root, manifest=manifest, write_fence=fence,
        thread_id=row["thread_id"], guard=lambda: None)
    state = runtime.checkpoints.load()
    document = json.loads(state["curriculum"]["json"])
    if tamper == "source_snapshot":
        document["compile_sources"]["profile_hash"] = "f" * 64
    else:
        document["compile_context"]["profile_context"]["starting_point"] = "forged"
    state["curriculum"]["json"] = canonical_json(document)
    runtime.checkpoints.save(state)
    monkeypatch.setattr(v2_clarifications, "freeze_planning_issues", original)
    with psycopg.connect(env.db.migrator_dsn) as conn:
        conn.execute("UPDATE ai_jobs SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE run_id=%s", (root,))
    before = len(env.provider.calls)
    assert env.worker.tick()
    result = env.client.get("/api/v1/runs/" + root, params=env.params).json()
    assert result["status"] == "failed" and result["error"]["code"] == "v2_validation_failed", result
    assert result["planning_issues"] == []
    assert len(env.provider.calls) == before


def test_incomplete_issue_database_interruption_reuses_success_receipts(databases, monkeypatch):
    from app.infrastructure.db import v2_clarifications
    env = environment(databases, monkeypatch, provider=ClarificationProvider(rounds=0, incomplete=True))
    original = v2_clarifications.freeze_planning_issues
    def interrupted(*args, **kwargs):
        raise psycopg.OperationalError("owned issue event write failed")
    monkeypatch.setattr(v2_clarifications, "freeze_planning_issues", interrupted)
    root, view = first(env, GoalSpec("学习MCP"))
    assert view["status"] == "running" and not view["planning_issues"]
    with psycopg.connect(env.db.migrator_dsn) as conn:
        assert conn.execute("SELECT status FROM ai_jobs WHERE run_id=%s", (root,)).fetchone()[0] == "running"
        conn.execute("UPDATE ai_jobs SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE run_id=%s", (root,))
    monkeypatch.setattr(v2_clarifications, "freeze_planning_issues", original)
    before = (len(env.provider.calls), len(env.search.calls), len(env.body.calls))
    assert env.worker.tick()
    result = env.client.get("/api/v1/runs/" + root, params=env.params).json()
    assert result["error"]["code"] == "v2_curriculum_incomplete" and result["planning_issues"]
    assert (len(env.provider.calls), len(env.search.calls), len(env.body.calls)) == before
