"""One owned PG seam: actual HTTP adapters, durable replay and unknown fencing."""
import json
import os
import subprocess
import sys
from pathlib import Path

import httpx
import psycopg
import pytest
from app.infrastructure.checkpointer.v2_planning_runtime import DurableBody, DurableIndex
from app.infrastructure.providers.v2_attempts import V2RecoveryBlocked
from app.infrastructure.resources.github import GitHubResourceIndex

from tests.integration.test_v2_planning_runtime_pg import Provider, calls
from tests.integration.test_v2_planning_runtime_pg import bound as runtime_bound
from tests.pg_harness import create_test_database, harness_skip_reason, roles_created_by_harness
from tests.unit.test_deep_audit_resource_adapters import body_adapter
from tests.unit.test_tavily_resource_index import query, streaming_json
from tests.unit.test_teaching_body import candidate

pytestmark = pytest.mark.postgres
ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module")
def db():
    assert os.environ.get("STUDYPLAN_TEST_PG_DEDICATED", "").lower() not in {"1", "true", "yes", "on"}
    assert harness_skip_reason() is None
    database = create_test_database(prefix="studyplan_test_delivery_seams")
    result = subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=ROOT / "backend",
        env=dict(os.environ, STUDYPLAN_MIGRATION_DSN=database.migrator_dsn.replace("postgresql://", "postgresql+psycopg://")),
        capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert not roles_created_by_harness()
    (ROOT / "var/codex-goals/delivery-seams-fix-20261010/owned-pg.json").write_text(
        json.dumps({"database": database.name, "migration": "existing head", "roles_created": []}), encoding="utf8")
    yield database


@pytest.fixture
def bound(db):
    return runtime_bound.__wrapped__(db)


def test_known_negative_receipts_replay_and_unknown_blocks_next_identity(db, bound):
    from dataclasses import replace
    scope, run, fence, *_ = bound
    ledger = calls(db, bound, Provider())
    scoped_query = replace(query(), scope=scope, extra={"project_id": fence.project_id, "query": "tool tutorial"})
    requests = []
    index = GitHubResourceIndex(transport=httpx.MockTransport(lambda r: requests.append(r) or streaming_json({"items": []})))
    assert DurableIndex(ledger, index, "empty").find(scoped_query) == []
    # New store object, same frozen run: no source redispatch.
    assert DurableIndex(calls(db, bound, Provider()), index, "empty").find(scoped_query) == []
    body_reader, body_requests = body_adapter("[Contributing](CONTRIBUTING.md)", {})
    first = DurableBody(ledger, body_reader).read(candidate())
    restored = DurableBody(calls(db, bound, Provider()), body_reader).read(candidate())
    assert first.status == restored.status == "unread" and len(body_requests) == first.requests == restored.requests == 1
    assert first.bytes_read == restored.bytes_read > 0 and len(requests) == 1
    with psycopg.connect(db.migrator_dsn) as conn:
        rows = conn.execute("SELECT status,response_payload FROM ai_provider_attempts WHERE run_id=%s ORDER BY attempt_id", (run,)).fetchall()
        assert len(rows) == 2 and all(row[0] == "succeeded" for row in rows)
        assert {row[1]["kind"] for row in rows} == {"search", "body_metadata"}
        reservations = conn.execute("SELECT detail FROM ai_run_events WHERE run_id=%s AND status='v2_reservation'", (run,)).fetchall()
        assert len(reservations) == 2  # original worst reservations remain; no invented cash/refund.
    def lost(request):
        requests.append(request)
        raise httpx.ReadTimeout("synthetic lost response", request=request)
    DurableIndex(ledger, GitHubResourceIndex(transport=httpx.MockTransport(lost)), "unknown").find(scoped_query)
    with pytest.raises(V2RecoveryBlocked, match="Uncertain"):
        DurableIndex(ledger, index, "next").find(scoped_query)
    assert len(requests) == 2  # empty + unknown; next identity never reaches HTTP.
    with psycopg.connect(db.migrator_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM ai_provider_attempts WHERE run_id=%s AND status='reconciliation_required'", (run,)).fetchone()[0] == 1


def test_product_v2_selection_keeps_existing_body_identity_and_blocks_body_only_replay(db, bound):
    from dataclasses import asdict
    from uuid import uuid4

    from app.domain.planning.resource_research import ResearchBudget
    from app.domain.planning.v2_runtime import build_v2_manifest
    from app.domain.runs.fencing import PlanningWriteFence
    from app.domain.workspace.models import AuthContext
    from psycopg.types.json import Jsonb

    original_scope, _, _, facts, original = bound
    project = "seams_v2_" + uuid4().hex
    scope = AuthContext(original_scope.actor_id, original_scope.session_id, original_scope.issued_at, (project,))
    run, job, token = (prefix + uuid4().hex for prefix in ("run_", "job_", "lease_"))
    manifest = build_v2_manifest("学习MCP", model_ref=original["model_ref"], source_facts=facts,
        budget=ResearchBudget(**original["budget"]), checked_at=original["checked_at"],
        product_semantics="planning-v2-product-v2")
    # Brand-new synthetic fixture, frozen product-v2 from its first insert;
    # no historical Run or already submitted manifest is edited.
    with psycopg.connect(db.migrator_dsn) as conn:
        conn.execute("INSERT INTO learning_projects(project_id,owner_actor_id,title,goal_statement,stable_key) VALUES(%s,%s,'Synthetic product v2','Goal',%s)",
                     (project, scope.actor_id, project))
        conn.execute("INSERT INTO ai_runs(run_id,actor_id,project_id,kind,graph_name,graph_version,status,next_action,thread_id,version) VALUES(%s,%s,%s,'plan_generate','planning','planning-v2-execution-v1','running','wait',%s,1)",
                     (run, scope.actor_id, project, run))
        conn.execute("INSERT INTO ai_jobs(job_id,run_id,job_key,status,lease_token,lease_expires_at) VALUES(%s,%s,%s,'running',%s,clock_timestamp()+interval '15 minutes')",
                     (job, run, "planning:" + run, token))
        conn.execute("INSERT INTO ai_run_events(run_id,status,detail) VALUES(%s,'submission',%s)",
                     (run, Jsonb({"kind": "planning_submission", "actor_id": scope.actor_id,
                       "project_id": project, "initial": {"goal": "学习MCP", "manifest": manifest}, "manifest": manifest})))
    fence = PlanningWriteFence(job, run, project, scope.actor_id, token)
    inputs = (scope, run, fence, facts, manifest)
    ledger = calls(db, inputs, Provider())
    from app.domain.planning.capability_policy import CAPABILITY_POLICY
    definition = next(d for d in CAPABILITY_POLICY.definitions if d.capability_id == "tool.calling")
    outcomes = [asdict(o) for o in definition.learning_outcomes]
    ledger.current_review_scope = outcomes
    ledger.current_review_candidate_hash = "synthetic_exact_candidate"
    reader, requests = body_adapter("[Tool Calling](docs/tool.md)", {"docs/tool.md": "# Tool Calling\nSynthetic tutorial"})
    options = {"max_bytes": 65536, "timeout_seconds": 15}
    body = DurableBody(ledger, reader).read(candidate(), **options)
    assert body.status == "succeeded"
    body.close()
    cold = calls(db, inputs, Provider())
    cold.current_review_scope = outcomes
    cold.current_review_candidate_hash = ledger.current_review_candidate_hash
    with pytest.raises(V2RecoveryBlocked, match="Body-only"):
        DurableBody(cold, reader).read(candidate(), must_teach=tuple(o["text"] for o in outcomes), **options)
    with pytest.raises(V2RecoveryBlocked, match="frozen review scope"):
        DurableBody(cold, reader).read(candidate(), must_teach=("Unexpected scope",), **options)
    assert len(requests) == 2
    with psycopg.connect(db.migrator_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM ai_provider_attempts WHERE run_id=%s", (run,)).fetchone()[0] == 1
