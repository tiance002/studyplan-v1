"""Item8 real cookie/CSRF + owned PG; all external responses are synthetic."""

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from types import SimpleNamespace
from uuid import uuid4

import psycopg
import pytest
from app import main
from app.agent_workflows.runtime import PostgresSaver
from app.application.container import AppContainer
from app.application.learning_exposures import LearningExposureService
from app.application.plan_service import PlanService
from app.application.practice_submissions import PracticeSubmissionService
from app.application.v2_revisions import V2RevisionService
from app.core.config import get_settings
from app.domain.planning.content_coverage import ReviewedContentIndex
from app.domain.planning.curriculum_compiler import CurriculumSourceFacts
from app.domain.planning.resource_research import ResearchBudget
from app.infrastructure.db.browser_auth import PgBrowserAuth
from app.infrastructure.db.job_repository import PgPlanningJobRepository
from app.infrastructure.db.learning_exposures import PgLearningExposures
from app.infrastructure.db.plan_repository import PgPlanRepository
from app.infrastructure.db.practice_submissions import PgPracticeSubmissions
from app.infrastructure.db.public_resource_catalog import PgPublicResourceCatalog
from app.infrastructure.db.run_repository import PgRunRepository
from app.infrastructure.db.v2_planning_persistence import PgV2PlanningPersistence
from app.infrastructure.db.v2_revisions import PgV2Revisions
from app.infrastructure.db.workspace import PgWorkspaceReader
from app.infrastructure.providers.runtime_factory import OwnedV2PlanningRuntimeFactory
from app.infrastructure.worker.planning_worker import PlanningWorker
from fastapi.testclient import TestClient

from backend.tests.integration.test_v2_planning_http_pg import ForbiddenDispatch
from backend.tests.integration.test_v2_planning_runtime_pg import (
    PipelineBodies,
    PipelineProvider,
    PipelineSearch,
)
from backend.tests.integration.test_v2_replanning_pg import EVIDENCE, published_base, saved_history
from backend.tests.integration.test_v2_replanning_pg import checkpoint_db as owned_checkpoint_fixture
from backend.tests.integration.test_v2_replanning_pg import db as owned_fixture

pytestmark = pytest.mark.postgres
db = owned_fixture
checkpoint_db = owned_checkpoint_fixture


def environment(db, checkpoint_db, monkeypatch, *, provider=None):
    with psycopg.connect(checkpoint_db.migrator_dsn, autocommit=True) as conn:
        PostgresSaver(conn).setup()
        conn.execute("GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO studyplan_app")
    auth = PgBrowserAuth(db.app_dsn, 3600)
    username = "v2rev_" + uuid4().hex[:12]
    token = auth.register(username, "pytest42", "owned-test")
    scope = auth.resolve(token)
    project = scope.learning_project_scope[0]
    provider, search, bodies = provider or PipelineProvider(), PipelineSearch(), PipelineBodies()
    factory = OwnedV2PlanningRuntimeFactory(db.app_dsn, checkpoint_db.app_dsn,
        source_facts=CurriculumSourceFacts(ReviewedContentIndex("empty", (), (), ())),
        budget=ResearchBudget(max_output_tokens=131072, max_total_requests=50, max_cost_micros=1000000),
        binding_resolver=lambda scope, project: SimpleNamespace(model_ref="test:frozen"),
        provider_resolver=lambda scope, project, run, ref: provider, github=search, body_reader=bodies)
    jobs = PgPlanningJobRepository(db.app_dsn, actor_ids=(scope.actor_id,))
    service = PlanService(repository=PgPlanRepository(db.app_dsn), runs=PgRunRepository(db.app_dsn),
        catalog=ForbiddenDispatch(), resources=PgPublicResourceCatalog(db.app_dsn),
        llm=ForbiddenDispatch(), graph_version="", planning_jobs=jobs,
        v2_persistence=PgV2PlanningPersistence(db.app_dsn), v2_runtime_factory=factory)
    changes = V2RevisionService(PgV2Revisions(db.app_dsn, planning_jobs=jobs, runtime_factory=factory))
    worker = PlanningWorker(jobs=jobs, execute=service.execute_generation, actor_ids=(scope.actor_id,))
    settings = replace(get_settings(), app_env="development", session_cookie_secure=False)
    monkeypatch.setattr(main, "get_settings", lambda: settings)
    app = main.create_app(AppContainer(settings=settings, sessions=auth, browser_auth=auth,
        plan_service=service, v2_revision_service=changes, planning_worker=worker,
        workspace_reader=PgWorkspaceReader(db.app_dsn),
        exposure_service=LearningExposureService(PgLearningExposures(db.app_dsn)),
        practice_submission_service=PracticeSubmissionService(PgPracticeSubmissions(db.app_dsn))))
    return SimpleNamespace(app=app, auth=auth, username=username, token=token, scope=scope,
        project=project, worker=worker, settings=settings, provider=provider, search=search, bodies=bodies)


def initial_plan(client, env):
    params = {"project_id": env.project}
    client.cookies.set(env.settings.session_cookie_name, env.token)
    headers = {"X-CSRF-Token": env.auth.detail(env.token)[0]["csrf_token"]}
    result = client.post("/api/v1/plans/v2/owned/generate", params=params, headers=headers,
                         json={"goal": "学习MCP"})
    assert result.status_code == 202, result.text
    assert env.worker.tick() is True
    run = client.get(result.json()["status_url"]).json()
    assert run["status"] == "succeeded", run
    draft = client.get("/api/v1/plans/drafts/" + run["result_ref"], params=params).json()
    result = client.post("/api/v1/plans/drafts/" + draft["draft_id"] + "/decision",
        params=params, headers=headers, json={"decision": "approve", "expected_version": 0,
            "draft_hash": draft["draft_hash"], "idempotency_key": "http8-base"})
    assert result.status_code == 200, result.text
    return result.json()["plan"], headers


def test_local_preview_cookie_scope_confirm_conflict_cancel_and_fresh_history(db, checkpoint_db, monkeypatch):
    env = environment(db, checkpoint_db, monkeypatch)
    params = {"project_id": env.project}
    path = "/api/v1/plans/v2/changes"
    with TestClient(env.app) as client:
        assert client.get(path + "/context", params=params).status_code == 401
        base, headers = initial_plan(client, env)
        counts = tuple(len(p.calls) for p in (env.provider, env.search, env.bodies))
        assert client.get(path + "/context", params=params).status_code == 200
        body = {"current_plan_id": base["plan_id"], "expected_version": 1,
            "idempotency_key": "http8-local", "stage_edits": [{"stage_id": base["stages"][-1]["stage_id"],
                "what_to_learn": "在既有目标范围内检查输入，并验证正常及失败结果"}]}
        assert client.post(path + "/local", params=params, json=body).status_code == 403
        assert client.post(path + "/local", params={"project_id": "not-owned"}, headers=headers,
                           json=body).status_code == 403
        assert client.post(path + "/local", params=params, headers=headers,
                           json=body | {"is_semantic": False}).status_code == 422
        clarification = client.post(path + "/classify", params=params, headers=headers,
                                    json={"change_text": "帮我调整一下路线"})
        assert clarification.status_code == 200
        assert clarification.json()["status"] == "needs_clarification"
        result = client.post(path + "/local", params=params, headers=headers, json=body)
        assert result.status_code == 200, result.text
        draft = result.json()
        assert draft["v2_revision"]["change_kind"] == "local"
        assert client.post(path + "/local", params=params, headers=headers, json=body).json() == draft
        assert client.post(path + "/local", params=params, headers=headers,
                           json=body | {"stage_edits": []}).status_code == 409
        stale = client.post(path + "/local", params=params, headers=headers,
            json=body | {"idempotency_key": "http8-stale", "stage_edits": [{
                "stage_id": base["stages"][-1]["stage_id"], "title": "合法未来说明"}]}).json()
        decision = {"expected_version": 1, "draft_hash": draft["draft_hash"], "idempotency_key": "http8-confirm"}
        target = path + "/" + draft["draft_id"]
        assert client.post(target + "/confirm", params=params, headers=headers,
                           json=decision | {"draft_hash": "stale"}).status_code == 409
        result = client.post(target + "/confirm", params=params, headers=headers, json=decision)
        assert result.status_code == 200, result.text
        current = result.json()["plan"]
        assert current["revision"] == 2
        assert client.post(target + "/confirm", params=params, headers=headers, json=decision).json()["plan"] == current
        for changed in ({"draft_hash": "wrong-on-replay"}, {"expected_version": 2}):
            assert client.post(target + "/confirm", params=params, headers=headers,
                               json=decision | changed).status_code == 409
        assert client.post(path + "/" + stale["draft_id"] + "/confirm", params=params, headers=headers,
            json=decision | {"draft_hash": stale["draft_hash"], "idempotency_key": "stale-confirm"}).status_code == 409
        cancel_preview = client.post(path + "/local", params=params, headers=headers,
            json={"current_plan_id": current["plan_id"], "expected_version": 2,
                "idempotency_key": "http8-cancel", "stage_edits": [{
                    "stage_id": current["stages"][-1]["stage_id"], "title": "准备取消的说明"}]}).json()
        cancel = {"expected_version": 2, "draft_hash": cancel_preview["draft_hash"], "idempotency_key": "cancel-confirm"}
        cancel_path = path + "/" + cancel_preview["draft_id"]
        result = client.post(cancel_path + "/cancel", params=params, headers=headers, json=cancel)
        assert result.status_code == 200, result.text
        assert result.json()["draft"]["status"] == "cancelled"
        assert client.post(cancel_path + "/confirm", params=params, headers=headers, json=cancel).status_code == 409
        assert client.post("/api/v1/plans/generate", params=params, headers=headers,
                           json={"goal": "synthetic"}).status_code == 503
        assert counts == tuple(len(p.calls) for p in (env.provider, env.search, env.bodies))
    # New server-resolved session and connections read both revisions exactly.
    fresh_token = env.auth.login(env.username, "pytest42", "owned-fresh")
    with TestClient(env.app) as client:
        client.cookies.set(env.settings.session_cookie_name, fresh_token)
        fresh = client.get("/api/v1/plans/current", params=params).json()
        old = client.get("/api/v1/plans/revisions/1", params=params).json()
        assert fresh == current
        assert old["stages"] == base["stages"] and old["v2_content"] == base["v2_content"]
        assert old["status"] == "superseded"
    EVIDENCE.joinpath("http-local-readback.json").write_text(json.dumps({
        "base": base, "preview": draft, "current": current, "history": old,
        "fresh_session": "PASS", "cookie_csrf_scope": "PASS", "stale_and_cancel": "PASS",
        "local_dispatch_delta": 0, "initial_synthetic_dispatch_counts": counts,
        "product_external_calls": 0, "public_generate_status": 503}, ensure_ascii=False, indent=2), encoding="utf8")


def test_consecutive_local_revisions_expose_exact_historical_completion(db, checkpoint_db, monkeypatch):
    env = environment(db, checkpoint_db, monkeypatch)
    base = published_base(db, env.scope, systematic=True)
    _, _, accepted = saved_history(db, env.scope, base)
    params = {"project_id": env.project}
    path = "/api/v1/plans/v2/changes"
    with TestClient(env.app) as client:
        client.cookies.set(env.settings.session_cookie_name, env.token)
        headers = {"X-CSRF-Token": env.auth.detail(env.token)[0]["csrf_token"]}
        current = client.get("/api/v1/plans/current", params=params).json()
        outcomes = client.get("/api/v1/outcomes", params=params)
        assert outcomes.status_code == 200, outcomes.text
        outcomes = outcomes.json()
        artifact = next(item for group in outcomes["groups"] for item in group["items"])
        assert artifact["submission_id"] == accepted["submission"]["submission_id"]
        assert artifact["plan_revision"] == 1 and artifact["conclusion"] == "accepted"
        for revision in (1, 2):
            context = client.get(path + "/context", params=params).json()
            assert context["stages"][0]["protected"]
            result = client.post(path + "/local", params=params, headers=headers,
                json={"current_plan_id": current["plan_id"], "expected_version": revision,
                    "idempotency_key": f"history-preview-{revision}", "stage_edits": [{
                        "stage_id": current["stages"][-1]["stage_id"], "title": f"未来阶段说明{revision}"}]})
            assert result.status_code == 200, result.text
            draft = result.json()
            result = client.post(path + "/" + draft["draft_id"] + "/confirm", params=params, headers=headers,
                json={"expected_version": revision, "draft_hash": draft["draft_hash"],
                      "idempotency_key": f"history-confirm-{revision}"})
            assert result.status_code == 200, result.text
            current = result.json()["plan"]
            workspace = client.get("/api/v1/workspace", params=params)
            assert workspace.status_code == 200, workspace.text
            workspace = workspace.json()
            assert workspace["completed_stages"] == 0
            assert workspace["historically_completed_stages"] == 1
            first = workspace["stages"][0]
            assert first["completion"]["status"] == "incomplete"
            assert first["historical_learning"] == {"source_plan_id": base.plan_id,
                "source_revision": 1, "source_stage_id": base.stages[0].stage_id,
                "learning_status": "completed"}
            assert all(unit["progress"] == "not_started" for unit in first["units"])
        denied = client.post(path + "/local", params=params, headers=headers,
            json={"current_plan_id": current["plan_id"], "expected_version": 3,
                "idempotency_key": "cannot-edit-historical", "stage_edits": [{
                    "stage_id": current["stages"][0]["stage_id"], "title": "不得改历史"}]})
        assert denied.status_code == 400, denied.text
        assert denied.json()["code"] == "validation_error"
        assert client.get("/api/v1/outcomes", params=params).json() == outcomes
        assert not any(p.calls for p in (env.provider, env.search, env.bodies))
        EVIDENCE.joinpath("http-local-history-readback.json").write_text(json.dumps({
            "current": current, "workspace": workspace, "outcomes": outcomes,
            "protected_prefix_status": denied.status_code,
            "product_external_calls": 0}, ensure_ascii=False, indent=2), encoding="utf8")


REPLAN_TARGET = "我已会 Python，学习 MCP 的最小接入，并基于现有 CLI 实践"
REPLAN_PROJECT = "已有本地 JSON 待办 CLI；继续使用现有项目。"


class RevisionProvider(PipelineProvider):
    """Explicit synthetic responses test field flow, never real semantic quality."""

    def generate_structured(self, **kw):
        from app.domain.planning.goal_requirements import GoalRequirementProfile
        from app.domain.planning.v2_execution import _decode
        from app.ports.llm import LLMResult

        from backend.tests.unit.test_capability_planning import cap, known_python, wire
        from backend.tests.unit.test_goal_requirement_analysis import output

        if kw["purpose"] == "planning.goal_requirement_analysis" and kw["payload"]["goal"]["target"] == REPLAN_TARGET:
            self.calls.append(kw)
            value = output(target_summary=REPLAN_TARGET,
                required_requirements=[{"text": "学习 MCP 最小接入并在现有 CLI 实践", "origin": "explicit",
                    "source_refs": ["goal.target", "project_context"], "rationale": ""}],
                learner_claims=[{"text": "我已会 Python", "source_refs": ["goal.target"]}])
            return LLMResult(value, self.model, "synthetic-revision", input_tokens=20, output_tokens=16, cost_micros=100)
        if kw["purpose"] == "planning.capability_planning" and kw["payload"]["profile"]["target_summary"] == REPLAN_TARGET:
            self.calls.append(kw)
            profile = _decode(GoalRequirementProfile,
                {k: v for k, v in kw["payload"]["profile"].items() if k != "profile_hash"})
            value = wire(profile, known_python(profile), cap(profile, "mcp"), claim_bindings=[{
                "claim_ref": profile.learner_claims[0].claim_id, "capability_id": "python.core"}])
            return LLMResult(value, self.model, "synthetic-revision", input_tokens=20, output_tokens=16, cost_micros=100)
        return super().generate_structured(**kw)


def test_semantic_new_run_full_chain_preview_confirm_and_fresh_readback(db, checkpoint_db, monkeypatch):
    env = environment(db, checkpoint_db, monkeypatch, provider=RevisionProvider())
    params = {"project_id": env.project}
    path = "/api/v1/plans/v2/changes"
    with TestClient(env.app) as client:
        base, headers = initial_plan(client, env)
        before = tuple(len(p.calls) for p in (env.provider, env.search, env.bodies))
        body = {"current_plan_id": base["plan_id"], "expected_version": 1,
            "idempotency_key": "semantic-http-new", "goal_spec": {"target": REPLAN_TARGET,
                "desired_depth": "applied", "project_context": REPLAN_PROJECT}}
        assert client.post("/api/v1/plans/v2/owned/replan", params=params, json=body).status_code == 403
        assert client.post("/api/v1/plans/v2/owned/replan", params={"project_id": "other"}, headers=headers,
                           json=body).status_code == 403
        result = client.post("/api/v1/plans/v2/owned/replan", params=params, headers=headers, json=body)
        assert result.status_code == 202, result.text
        handle = result.json()
        assert client.get("/api/v1/plans/current", params=params).json() == base
        assert client.post("/api/v1/plans/v2/owned/replan", params=params, headers=headers, json=body).json() == handle
        assert client.post("/api/v1/plans/v2/owned/replan", params=params, headers=headers,
            json=body | {"goal_spec": {"target": "不同新目标"}}).status_code == 409
        assert env.worker.tick() is True
        run = client.get(handle["status_url"]).json()
        assert run["status"] == "succeeded", run
        draft_result = client.get(path + "/" + run["result_ref"], params=params)
        assert draft_result.status_code == 200, draft_result.text
        draft = draft_result.json()
        assert draft["v2_revision"]["change_kind"] == "semantic"
        assert draft["v2_content"]["profile"]["project_context"] == REPLAN_PROJECT
        assert draft["v2_content"]["profile"]["learner_claims"][0]["text"] == "我已会 Python"
        capabilities = draft["v2_content"]["capabilities"]["capabilities"]
        assert next(c for c in capabilities if c["capability_id"] == "python.core")["disposition"] == "accepted_known"
        assert all("python.core" not in stage["capability_ids"] for stage in draft["v2_content"]["stages"])
        assert draft["v2_content"]["practice"]["carrier"]["kind"] == "user_project"
        assert draft["v2_content"]["practice"]["carrier"]["description"] == REPLAN_PROJECT
        assert client.get("/api/v1/plans/current", params=params).json() == base
        purposes = [call["purpose"] for call in env.provider.calls[before[0]:]]
        assert purposes == ["planning.goal_requirement_analysis", "planning.capability_planning",
                            "planning.research_reader", "planning.curriculum_composition"]
        result = client.post(path + "/" + draft["draft_id"] + "/confirm", params=params, headers=headers,
            json={"expected_version": 1, "draft_hash": draft["draft_hash"], "idempotency_key": "semantic-confirm"})
        assert result.status_code == 200, result.text
        current = result.json()["plan"]
        assert current["revision"] == 2 and current["goal_snapshot"] == REPLAN_TARGET
        assert current["v2_revision"]["changes"]
        assert client.post("/api/v1/plans/generate", params=params, headers=headers,
                           json={"goal": "synthetic"}).status_code == 503
    fresh_token = env.auth.login(env.username, "pytest42", "semantic-fresh")
    with TestClient(env.app) as client:
        client.cookies.set(env.settings.session_cookie_name, fresh_token)
        assert client.get("/api/v1/plans/current", params=params).json() == current
        old = client.get("/api/v1/plans/revisions/1", params=params).json()
        assert old["v2_content"] == base["v2_content"] and old["stages"] == base["stages"]
    EVIDENCE.joinpath("http-semantic-readback.json").write_text(json.dumps({
        "input": body, "handle": handle, "base": base, "preview": draft, "current": current,
        "history": old, "synthetic_purposes": purposes, "product_external_calls": 0,
        "fresh_login": "PASS"}, ensure_ascii=False, indent=2), encoding="utf8")


def test_concurrent_http_confirm_publishes_exactly_one_revision(db, checkpoint_db, monkeypatch):
    env = environment(db, checkpoint_db, monkeypatch)
    original = published_base(db, env.scope)
    params = {"project_id": env.project}
    path = "/api/v1/plans/v2/changes"
    with TestClient(env.app) as client:
        client.cookies.set(env.settings.session_cookie_name, env.token)
        headers = {"X-CSRF-Token": env.auth.detail(env.token)[0]["csrf_token"]}
        previews = []
        for suffix in ("a", "b"):
            result = client.post(path + "/local", params=params, headers=headers,
                json={"current_plan_id": original.plan_id, "expected_version": 1,
                      "idempotency_key": "concurrent-preview-" + suffix, "stage_edits": [{
                          "stage_id": original.stages[0].stage_id, "title": "合法未来说明" + suffix}]})
            assert result.status_code == 200, result.text
            previews.append(result.json())

        def confirm(draft):
            return client.post(path + "/" + draft["draft_id"] + "/confirm", params=params, headers=headers,
                json={"expected_version": 1, "draft_hash": draft["draft_hash"],
                      "idempotency_key": "concurrent-confirm-" + draft["draft_id"]})

        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(confirm, previews))
        assert sorted(response.status_code for response in responses) == [200, 409]
        current = client.get("/api/v1/plans/current", params=params).json()
        assert current["revision"] == 2
        assert client.get("/api/v1/plans/revisions/3", params=params).status_code == 404
        assert client.get("/api/v1/plans/revisions/1", params=params).json()["stages"][0]["title"] == original.stages[0].title
        assert not any(p.calls for p in (env.provider, env.search, env.bodies))
        EVIDENCE.joinpath("http-concurrent-cas.json").write_text(json.dumps({
            "confirm_statuses": [response.status_code for response in responses], "current": current,
            "product_external_calls": 0}, ensure_ascii=False, indent=2), encoding="utf8")


def test_existing_current_cannot_start_an_unbound_initial_root_via_http(db, checkpoint_db, monkeypatch):
    env = environment(db, checkpoint_db, monkeypatch)
    original = published_base(db, env.scope)
    params = {"project_id": env.project}

    def counts():
        with psycopg.connect(db.migrator_dsn) as conn:
            return conn.execute("""SELECT
                (SELECT count(*) FROM ai_runs WHERE project_id=%s),
                (SELECT count(*) FROM ai_jobs j JOIN ai_runs r USING(run_id) WHERE r.project_id=%s),
                (SELECT count(*) FROM ai_run_events e JOIN ai_runs r USING(run_id)
                    WHERE r.project_id=%s AND e.status='submission')""",
                (env.project, env.project, env.project)).fetchone()

    before = counts()
    with TestClient(env.app) as client:
        client.cookies.set(env.settings.session_cookie_name, env.token)
        headers = {"X-CSRF-Token": env.auth.detail(env.token)[0]["csrf_token"]}
        result = client.post("/api/v1/plans/v2/owned/generate", params=params, headers=headers,
                             json={"goal": "不得通过初始入口重新分配预算"})
        after = counts()
        EVIDENCE.joinpath(f"http-initial-gate-{result.status_code}.json").write_text(json.dumps({
            "status": result.status_code, "before": before, "after": after,
            "product_external_calls": 0}, ensure_ascii=False, indent=2), encoding="utf8")
        assert result.status_code == 409, result.text
        assert before == after
        assert client.get("/api/v1/plans/current", params=params).json()["plan_id"] == original.plan_id
        assert not any(p.calls for p in (env.provider, env.search, env.bodies))
