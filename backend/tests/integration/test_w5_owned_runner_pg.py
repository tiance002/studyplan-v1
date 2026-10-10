"""One real owned PG/Worker/review chain over actual HTTP provider MockTransport.

Synthetic MCP teaching fixtures prove assembly, not Scenario A teaching quality.
No production DB, real API request, or historical journal is accessed.
"""
import hashlib
import json
import socket
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
from uuid import uuid4

import httpx
import psycopg
import pytest
from app.core.config import get_settings
from app.core.errors import ValidationAppError
from app.domain.planning.content_coverage import ReviewedContentIndex
from app.domain.planning.curriculum_compiler import CurriculumSourceFacts
from app.domain.planning.intent import GoalSpec
from app.infrastructure.db.browser_auth import PgBrowserAuth

from backend.tests.integration import test_v2_planning_runtime_pg as fixture
from backend.tests.integration.test_owned_v2_acceptance_gate_pg import Provider
from scripts import planning_v2_scenario_a as runner
from scripts.planning_v2_acceptance_external import (
    AcceptanceExternal,
    actual_request_options,
    external_authorization_request,
    model_configuration_ref,
)

pytestmark = pytest.mark.postgres
EVIDENCE = runner.ROOT / "var/codex-goals/w5-runner-closure-20261010"


@pytest.fixture(scope="module")
def db():
    original = fixture.EVIDENCE
    fixture.EVIDENCE = EVIDENCE
    try:
        yield next(fixture.db.__wrapped__())
    finally:
        fixture.EVIDENCE = original


@pytest.fixture(scope="module")
def checkpoint_db():
    original = fixture.EVIDENCE
    fixture.EVIDENCE = EVIDENCE
    try:
        yield next(fixture.checkpoint_db.__wrapped__())
    finally:
        fixture.EVIDENCE = original


@pytest.fixture(autouse=True)
def loopback_only(monkeypatch):
    connect, getaddrinfo = socket.socket.connect, socket.getaddrinfo
    def allowed_connect(sock, address):
        assert address[0] in {"127.0.0.1", "::1", "localhost"}, "Actual external network forbidden"
        return connect(sock, address)
    def allowed_dns(host, *args, **kwargs):
        assert host in {"127.0.0.1", "::1", "localhost"}, "Actual external DNS forbidden"
        return getaddrinfo(host, *args, **kwargs)
    monkeypatch.setattr(socket.socket, "connect", allowed_connect)
    monkeypatch.setattr(socket, "getaddrinfo", allowed_dns)


def saved(path, value):
    raw = json.dumps(value, ensure_ascii=False).encode()
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def make(db, checkpoint_db, monkeypatch, *, unknown=False, synthetic_resources=True, global_model_cap=280):
    from app.infrastructure.providers.endpoint_policy import ModelEndpointPolicy
    monkeypatch.setattr(ModelEndpointPolicy, "validate", lambda self, value: value
        if httpx.URL(value).host in {"api.deepseek.com", "api-docs.deepseek.com", "api.tavily.com"} else pytest.fail("Mock endpoint not authorized"))
    settings = replace(get_settings(), llm_provider="openai_compatible", llm_model_id="deepseek-flash",
        llm_base_url="https://api.deepseek.com", llm_api_key="synthetic-offline-key", llm_max_output_tokens=4096,
        llm_outline_output_tokens=4096, llm_structure_output_tokens=4096,
        llm_practice_output_tokens=4096, llm_repair_output_tokens=4096,
        tavily_api_key="" if synthetic_resources else "synthetic-search-key", llm_allowed_hosts=("api.deepseek.com",))
    folder = EVIDENCE / ("assembly-" + uuid4().hex)
    packet = runner.prepare(folder, goal=GoalSpec("学习MCP"), model_ref=model_configuration_ref(settings),
        request_options=actual_request_options(settings), facts=CurriculumSourceFacts(ReviewedContentIndex("empty", (), (), ())))
    auth = PgBrowserAuth(db.app_dsn, 3600)
    token = auth.register("w5_" + uuid4().hex[:14], "pytest42", "owned-offline")
    scope = auth.resolve(token)
    project = scope.learning_project_scope[0]
    grant = runner._read(folder / "owner-authorization-request.json")
    grant.update(owner_approved=True, owner_evidence="Synthetic offline fixture, not real external authority",
        issued_at=datetime.now(timezone.utc).isoformat(), actions=["submit", "execute", "review"])
    owner = folder / "synthetic-owner.json"
    digest = saved(owner, grant)
    options = dict(dsn=db.app_dsn, checkpoint_dsn=checkpoint_db.app_dsn, scope=scope, project_id=project,
        authorization=owner, authorization_sha256=digest, external_settings=settings)
    for name in ("mock-model-global", "mock-search-global"):
        (folder / name).mkdir()
    external_grant = external_authorization_request(packet, evidence_dir=folder,
        model_ledger=folder / "mock-model-global", search_ledger=folder / "mock-search-global",
        global_model_cap=global_model_cap, global_search_cap=1000)
    external_grant.update(owner_approved=True, owner_evidence="Synthetic offline bounded external fixture",
        issued_at=datetime.now(timezone.utc).isoformat(), actions=["preflight", "execute"], residual_cash_risk_accepted=True)
    external_owner = folder / "synthetic-external-owner.json"
    external_sha = saved(external_owner, external_grant)
    provider = Provider()
    requests = []
    def model_http(request):
        requests.append(request)
        if unknown:
            raise httpx.ReadTimeout("Synthetic result lost", request=request)
        body = json.loads(request.content)
        message = json.loads(body["messages"][1]["content"])
        purpose, payload = message["purpose"], message["context"]
        # Real wire is sent only AFTER both global and durable reservations.
        global_rows = sorted((folder / "mock-model-global").glob("request-*.json"))
        record = json.loads(global_rows[-1].read_bytes())
        with psycopg.connect(db.migrator_dsn) as conn:
            assert conn.execute("SELECT count(*) FROM ai_run_events WHERE run_id=%s AND attempt_id=%s AND status='v2_reservation'",
                (record["run_id"], record["attempt_id"])).fetchone()[0] == 1
        assert len(global_rows) == len(provider.calls) + 1
        result = provider.generate_structured(purpose=purpose, payload=payload)
        return httpx.Response(200, json={"model": "deepseek-flash",
            "choices": [{"message": {"content": json.dumps(result.payload)}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 20, "completion_tokens": 16, "total_tokens": 36}})
    def metadata(request):
        if request.url.host == "api-docs.deepseek.com":
            return httpx.Response(200, content=b"<p>deepseek-flash CNY peak input 2 output 8 per million</p>")
        return httpx.Response(200, json={"is_available": True, "balance_infos": [{"currency": "CNY",
            "total_balance": "10", "granted_balance": "0", "topped_up_balance": "10"}]})
    from backend.tests.unit.test_w5_acceptance_external import file_response
    def github(request):
        if request.url.path == "/search/repositories":
            return httpx.Response(200, json={"items": []})
        if request.url.path.endswith("/readme"):
            return file_response("README.md", "[MCP lesson](lesson.md)")
        return file_response("lesson.md", "Transient W5 body sentinel never persisted")
    def web(request):
        return httpx.Response(200, json={"results": [], "usage": {"credits": 1}})
    def cold():
        external = AcceptanceExternal(packet, evidence_dir=folder, model_ledger=folder / "mock-model-global",
            search_ledger=folder / "mock-search-global", authorization=external_owner,
            authorization_sha256=external_sha, guard=lambda: runner.load_prepared(folder / "prepared.json"),
            model_transport=httpx.MockTransport(model_http), metadata_transport=httpx.MockTransport(metadata),
            github_transport=httpx.MockTransport(github), web_transport=httpx.MockTransport(web))
        return external
    external = cold()
    external.preflight(settings)
    price = external.price_review_request()
    price.update(input_peak_per_million="2", output_peak_per_million="8", approved=True,
        reviewed_at=datetime.now(timezone.utc).isoformat())
    price_path = folder / "synthetic-independent-price.json"
    external.approve_price(price_path, sha256=saved(price_path, price))
    # Algorithm/adapter tests separately use actual Github/Tavily/body Mock HTTP.
    # This PG representative uses bounded synthetic teaching evidence to close
    # all three real model contracts and Compiler/persistence without network.
    if synthetic_resources:
        monkeypatch.setattr(AcceptanceExternal, "resource_ports", lambda self, settings, run_id=None:
            type("Ports", (), {"github": fixture.PipelineSearch(), "web": None, "body_reader": fixture.PipelineBodies()})())
    run = runner.submit_prepared(folder / "prepared.json", external=external, **options)
    return folder, packet, options, run, cold, requests


def test_cold_owned_driver_three_independent_reviews_then_draft_no_redispatch(db, checkpoint_db, monkeypatch):
    folder, packet, options, run, cold, requests = make(db, checkpoint_db, monkeypatch)
    path = folder / "prepared.json"
    for stage in ("goal_analysis", "capability_planning", "curriculum_composition"):
        assert runner.worker_tick(path, external=cold(), **options)
        assert not runner.worker_tick(path, external=cold(), **options)
        frozen = runner.read_review(path, external=cold(), **options)
        assert frozen["review"]["stage"] == stage and frozen["review"]["budget_root_run_id"] == run
        evidence = runner.review_request(packet, frozen)
        evidence.update(result="PASS", reviewer="synthetic-independent-reviewer", rationale="Offline fixture checked",
            evidence_refs=["synthetic:input-and-real-checkpoint"])
        evidence_path = folder / ("synthetic-independent-" + stage + ".json")
        digest = saved(evidence_path, evidence)
        assert runner.decide_review(path, stage=stage, evidence=evidence_path, evidence_sha256=digest,
            external=cold(), **options) == run
        assert runner.decide_review(path, stage=stage, evidence=evidence_path, evidence_sha256=digest,
            external=cold(), **options) == run  # exact cold idempotent decision, no new request.
    before = len(requests)
    assert runner.worker_tick(path, external=cold(), **options)
    assert not runner.worker_tick(path, external=cold(), **options)
    assert len(requests) == before == 4
    with psycopg.connect(db.migrator_dsn) as conn:
        assert conn.execute("SELECT r.status,j.status,j.attempts FROM ai_runs r JOIN ai_jobs j USING(run_id) WHERE run_id=%s", (run,)).fetchone() == ("succeeded", "completed", 4)
        assert conn.execute("SELECT count(*) FROM plan_drafts WHERE run_id=%s", (run,)).fetchone()[0] == 1
        assert conn.execute("SELECT count(*) FROM ai_run_events WHERE run_id=%s AND status='v2_owned_review_decision'", (run,)).fetchone()[0] == 3
        assert conn.execute("SELECT count(*) FROM ai_runs WHERE project_id=%s", (options["project_id"],)).fetchone()[0] == 1


def test_unknown_stays_reconciliation_and_cold_driver_never_dispatches_again(db, checkpoint_db, monkeypatch):
    folder, _, options, run, cold, requests = make(db, checkpoint_db, monkeypatch, unknown=True)
    assert runner.worker_tick(folder / "prepared.json", external=cold(), **options)
    assert len(requests) == 1
    with psycopg.connect(db.migrator_dsn) as conn:
        assert conn.execute("SELECT r.status,j.status FROM ai_runs r JOIN ai_jobs j USING(run_id) WHERE run_id=%s", (run,)).fetchone() == ("reconciliation_required", "reconciliation_required")
        assert conn.execute("SELECT count(*) FROM ai_provider_attempts WHERE run_id=%s AND status='reconciliation_required'", (run,)).fetchone()[0] == 1
        assert conn.execute("SELECT count(*) FROM plan_drafts WHERE run_id=%s", (run,)).fetchone()[0] == 0
    with pytest.raises(ValidationAppError):
        runner.worker_tick(folder / "prepared.json", external=cold(), **options)
    assert len(requests) == 1


def test_actual_resource_transports_match_pg_parent_and_nested_receipts(db, checkpoint_db, monkeypatch):
    from app.domain.runs.fencing import PlanningWriteFence
    from app.infrastructure.checkpointer.v2_planning_runtime import DurableBody, DurableIndex
    from app.infrastructure.db.run_repository import PgRunRepository
    from app.infrastructure.providers.v2_transport import guarded_port

    from backend.tests.unit.test_w5_acceptance_external import candidate, query
    from scripts.planning_v2_acceptance_external import ledger_snapshot
    folder, packet, options, run, cold, requests = make(db, checkpoint_db, monkeypatch, synthetic_resources=False)
    path = folder / "prepared.json"
    for stage in ("goal_analysis", "capability_planning"):
        assert runner.worker_tick(path, external=cold(), **options)
        frozen = runner.read_review(path, external=cold(), **options)
        evidence = runner.review_request(packet, frozen)
        evidence.update(result="PASS", reviewer="synthetic-reviewer", rationale="Offline prerequisite reviewed", evidence_refs=["synthetic"])
        evidence_path = folder / ("synthetic-prerequisite-" + stage + ".json")
        runner.decide_review(path, stage=stage, evidence=evidence_path,
            evidence_sha256=saved(evidence_path, evidence), external=cold(), **options)
    assembly = runner.assemble_prepared(path, action="execute", external=cold(), **options)
    claim = assembly.jobs.claim(options["project_id"], "owned-resource-seam", 300)
    fence = PlanningWriteFence(claim.job_id, run, claim.project_id, claim.actor_id, claim.lease_token)
    runtime = assembly.factory(options["scope"], options["project_id"], run, manifest=packet["manifest"], write_fence=fence,
        thread_id=PgRunRepository(db.app_dsn).get_run(project_id=options["project_id"], run_id=run).thread_id,
        guard=lambda: None)
    calls = runtime.calls
    calls.current_review_scope, calls.current_review_candidate_hash = [], "synthetic-scope"
    scoped_query = replace(query(), scope=options["scope"], extra={"project_id": options["project_id"], "query": "MCP tutorial"})
    assert DurableIndex(calls, guarded_port(calls, assembly.factory.github), "actual-github").find(scoped_query) == []
    assert DurableIndex(calls, guarded_port(calls, assembly.factory.web), "actual-web").find(scoped_query) == []
    record = replace(candidate(), project_id=options["project_id"])
    body = DurableBody(calls, guarded_port(calls, assembly.factory.body_reader)).read(record, paths=("lesson.md",), max_bytes=65536)
    assert body.status == "succeeded" and body.requests == 2 and body.chunks
    body.close()
    global_rows = ledger_snapshot(folder / "mock-search-global")
    http_rows = ledger_snapshot(folder / "external-body-http")
    assert len(global_rows) == len(http_rows) == 2
    with psycopg.connect(db.migrator_dsn) as conn:
        for record, result in global_rows + http_rows:
            parent = record["parent_attempt_id"]
            assert result["unknown"] is False
            assert conn.execute("SELECT count(*) FROM ai_provider_attempts WHERE run_id=%s AND attempt_id=%s AND status='succeeded'", (run, parent)).fetchone()[0] == 1
            assert conn.execute("SELECT count(*) FROM ai_run_events WHERE run_id=%s AND attempt_id=%s AND status='v2_nested_dispatch' AND (detail->>'ordinal')::int=%s", (run, parent, record["pg_child_ordinal"])).fetchone()[0] == 1
        assert conn.execute("SELECT count(*) FROM ai_run_events WHERE run_id=%s AND status='v2_nested_result'", (run,)).fetchone()[0] == 4
        assert conn.execute("SELECT count(*) FROM plan_drafts WHERE run_id=%s", (run,)).fetchone()[0] == 0
    assert len(requests) == 2  # only Goal/Capability Model HTTP Mock requests.
    assert all(b"Transient W5 body sentinel" not in p.read_bytes() for p in folder.rglob("*.json"))


def test_tampered_review_checkpoint_cannot_approve_real_pending_run(db, checkpoint_db, monkeypatch):
    folder, packet, options, run, cold, requests = make(db, checkpoint_db, monkeypatch)
    path = folder / "prepared.json"
    assert runner.worker_tick(path, external=cold(), **options)
    frozen = runner.read_review(path, external=cold(), **options)
    tampered = deepcopy(frozen)
    tampered["state"]["original_goal"] = "Substituted safe text"
    saved(folder / "review-packet-goal_analysis.json", tampered)
    evidence = runner.review_request(packet, tampered)
    evidence.update(result="PASS", reviewer="synthetic-reviewer", rationale="Checked substituted fixture", evidence_refs=["synthetic"])
    evidence_path = folder / "synthetic-tampered-review.json"
    with pytest.raises(ValidationAppError):
        runner.decide_review(path, stage="goal_analysis", evidence=evidence_path,
            evidence_sha256=saved(evidence_path, evidence), external=cold(), **options)
    with psycopg.connect(db.migrator_dsn) as conn:
        assert conn.execute("SELECT status FROM ai_runs WHERE run_id=%s", (run,)).fetchone()[0] == "waiting_user"
        assert conn.execute("SELECT count(*) FROM ai_run_events WHERE run_id=%s AND status='v2_owned_review_decision'", (run,)).fetchone()[0] == 0
    assert len(requests) == 1


def test_exhausted_global_cap_is_known_not_dispatched_without_false_unknown(db, checkpoint_db, monkeypatch):
    folder, _packet, options, run, cold, requests = make(db, checkpoint_db, monkeypatch, global_model_cap=1)
    # A paired synthetic historical debit consumes the cap; no real journal is touched.
    saved(folder / "mock-model-global/request-01.json", {"number": 1, "acceptance_id": "synthetic-history"})
    saved(folder / "mock-model-global/result-01.json", {"number": 1, "unknown": False})
    assert runner.worker_tick(folder / "prepared.json", external=cold(), **options)
    with psycopg.connect(db.migrator_dsn) as conn:
        assert conn.execute("SELECT r.status,j.status FROM ai_runs r JOIN ai_jobs j USING(run_id) WHERE run_id=%s", (run,)).fetchone() == ("failed", "failed")
        assert conn.execute("SELECT count(*) FROM ai_provider_attempts WHERE run_id=%s AND status='reconciliation_required'", (run,)).fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM plan_drafts WHERE run_id=%s", (run,)).fetchone()[0] == 0
    assert len(requests) == 0
    assert len(list((folder / "mock-model-global").glob("request-*.json"))) == 1
    with pytest.raises(ValidationAppError):
        runner.worker_tick(folder / "prepared.json", external=cold(), **options)


def test_exact_run_selection_and_independent_fail_leave_other_job_untouched(db, checkpoint_db, monkeypatch):
    folder, packet, options, run, cold, requests = make(db, checkpoint_db, monkeypatch)
    other, job = "run_" + uuid4().hex, "job_" + uuid4().hex
    with psycopg.connect(db.migrator_dsn) as conn:
        conn.execute("""INSERT INTO ai_runs(run_id,actor_id,project_id,kind,graph_name,graph_version,status,next_action,thread_id,version)
            VALUES(%s,%s,%s,'plan_generate','planning','unrelated-owned-test','queued','wait',%s,1)""",
            (other, options["scope"].actor_id, options["project_id"], other))
        conn.execute("""INSERT INTO ai_jobs(job_id,run_id,job_key,status,created_at)
            VALUES(%s,%s,%s,'pending',clock_timestamp()-interval '1 day')""", (job, other, "planning:" + other))
    path = folder / "prepared.json"
    assert runner.worker_tick(path, external=cold(), **options)
    frozen = runner.read_review(path, external=cold(), **options)
    evidence = runner.review_request(packet, frozen)
    evidence.update(result="FAIL", reviewer="synthetic-independent-reviewer", rationale="Synthetic semantic rejection",
        evidence_refs=["synthetic:negative"])
    evidence_path = folder / "synthetic-independent-fail.json"
    runner.decide_review(path, stage="goal_analysis", evidence=evidence_path,
        evidence_sha256=saved(evidence_path, evidence), external=cold(), **options)
    with pytest.raises(ValidationAppError):
        runner.worker_tick(path, external=cold(), **options)
    with psycopg.connect(db.migrator_dsn) as conn:
        assert conn.execute("SELECT r.status,j.status,j.attempts FROM ai_runs r JOIN ai_jobs j USING(run_id) WHERE run_id=%s", (other,)).fetchone() == ("queued", "pending", 0)
        assert conn.execute("SELECT r.status,j.status FROM ai_runs r JOIN ai_jobs j USING(run_id) WHERE run_id=%s", (run,)).fetchone() == ("failed", "failed")
    assert len(requests) == 1
