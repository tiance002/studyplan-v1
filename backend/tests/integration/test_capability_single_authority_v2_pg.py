"""Owned PG proof for frozen CapabilityDecisionV2 dispatch and recovery identity."""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import httpx
import psycopg
import pytest
from app.application.capability_planning import CapabilityPlanner
from app.application.planning_budget import BudgetPolicy
from app.core.ids import content_hash
from app.domain.planning.capabilities import CAPABILITY_DECISION_SCHEMA, CAPABILITY_PURPOSE, CapabilityPlan
from app.domain.planning.capability_decisions import CAPABILITY_DECISION_PROTOCOL
from app.domain.planning.content_coverage import ReviewedContentIndex
from app.domain.planning.curriculum_compiler import CurriculumSourceFacts
from app.domain.planning.resource_research import ResearchBudget
from app.domain.planning.v2_runtime import (
    OWNED_ACCEPTANCE_GATE,
    PRODUCT_SEMANTICS_V2,
    V2_EXECUTION_VERSION,
    build_v2_manifest,
    purpose_schema,
)
from app.domain.runs.fencing import PlanningWriteFence
from app.domain.workspace.models import AuthContext
from app.infrastructure.checkpointer.v2_planning_executor import PgV2Checkpoints, PostgresSaver
from app.infrastructure.db.v2_owned_reviews import _seal
from app.infrastructure.providers.openai_compatible import OpenAICompatibleLLM
from app.infrastructure.providers.v2_attempts import PgV2Calls, V2RecoveryBlocked
from psycopg.types.json import Jsonb

from backend.tests.unit.test_capability_single_authority import _base_decision
from backend.tests.unit.test_item2_real_failure_contract import real_profile
from tests.pg_harness import create_test_database, harness_skip_reason, roles_created_by_harness

pytestmark = pytest.mark.postgres
ROOT = Path(__file__).resolve().parents[3]
STAMP = "2026-10-10T12:00:00+00:00"


@pytest.fixture(scope="module")
def business_db():
    assert os.environ.get("STUDYPLAN_TEST_PG_DEDICATED", "").lower() not in {"1", "true", "yes", "on"}
    assert harness_skip_reason() is None
    database = create_test_database(prefix="studyplan_test_capability_v2_business")
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=ROOT / "backend",
        env=dict(
            os.environ,
            STUDYPLAN_MIGRATION_DSN=database.migrator_dsn.replace("postgresql://", "postgresql+psycopg://"),
        ),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert not roles_created_by_harness()
    yield database


@pytest.fixture(scope="module")
def checkpoint_db():
    database = create_test_database(prefix="studyplan_test_capability_v2_checkpoint")
    with psycopg.connect(database.migrator_dsn, autocommit=True) as conn:
        PostgresSaver(conn).setup()
        conn.execute("GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO studyplan_app")
    yield database


def test_frozen_decision_v2_dispatch_receipt_and_cold_restore(business_db, checkpoint_db):
    profile = real_profile()
    decision = _base_decision(profile)
    project, run, job, token = [prefix + uuid4().hex for prefix in ("decisionv2_", "run_", "job_", "lease_")]
    actor = "decisionv2_actor_" + uuid4().hex
    scope = AuthContext(actor, "session", datetime.now(timezone.utc), (project,))
    facts = CurriculumSourceFacts(ReviewedContentIndex("empty", (), (), ()))
    budget = ResearchBudget(max_total_requests=16, max_output_tokens=4096, max_cost_micros=100000)
    goal = "系统学习Agent结构化输出和工具调用"
    manifest = build_v2_manifest(
        goal,
        model_ref="deployment",
        source_facts=facts,
        budget=budget,
        checked_at=STAMP,
        product_semantics=PRODUCT_SEMANTICS_V2,
        acceptance_gate=OWNED_ACCEPTANCE_GATE,
        capability_output_protocol=CAPABILITY_DECISION_PROTOCOL,
    )
    assert purpose_schema(manifest, CAPABILITY_PURPOSE) == CAPABILITY_DECISION_SCHEMA
    initial = {"goal": goal, "manifest": manifest}
    with psycopg.connect(business_db.migrator_dsn) as conn:
        conn.execute(
            "INSERT INTO learning_projects(project_id,owner_actor_id,title,goal_statement,stable_key) "
            "VALUES(%s,%s,'Decision V2','Item 2 protocol witness',%s)",
            (project, actor, project),
        )
        conn.execute(
            "INSERT INTO ai_runs(run_id,actor_id,project_id,kind,graph_name,graph_version,status,next_action,thread_id,version) "
            "VALUES(%s,%s,%s,'plan_generate','planning',%s,'running','wait',%s,1)",
            (run, actor, project, V2_EXECUTION_VERSION, run),
        )
        conn.execute(
            "INSERT INTO ai_jobs(job_id,run_id,job_key,status,lease_token,lease_expires_at) "
            "VALUES(%s,%s,%s,'running',%s,clock_timestamp()+interval '15 minutes')",
            (job, run, "planning:" + run, token),
        )
        conn.execute(
            "INSERT INTO ai_run_events(run_id,status,detail) VALUES(%s,'submission',%s)",
            (run, Jsonb({"kind": "planning_submission", "actor_id": actor, "project_id": project,
                         "initial": initial, "manifest": manifest})),
        )
        # Synthetic prior approval isolates the capability-stage dispatch;
        # this does not claim the real Goal review process passed.
        review = _seal({
            "run_id": run,
            "budget_root_run_id": run,
            "actor_id": actor,
            "project_id": project,
            "manifest_hash": manifest["manifest_hash"],
            "stage": "goal_analysis",
            "thread_id": run,
            "checkpoint_hash": "a" * 64,
            "payload_hash": "b" * 64,
            "run_version": 2,
        })
        conn.execute(
            "INSERT INTO ai_run_events(run_id,status,detail) VALUES(%s,'v2_owned_review',%s)",
            (run, Jsonb(review)),
        )
        decision_record = _seal({
            "run_id": run,
            "actor_id": actor,
            "project_id": project,
            "manifest_hash": manifest["manifest_hash"],
            "stage": "goal_analysis",
            "review_hash": review["digest"],
            "decision": "approve",
            "evidence_hash": "c" * 64,
            "expected_version": 2,
            "key_hash": "d" * 64,
            "fingerprint": "e" * 64,
        })
        conn.execute(
            "INSERT INTO ai_run_events(run_id,status,detail) VALUES(%s,'v2_owned_review_decision',%s)",
            (run, Jsonb(decision_record)),
        )

    wire_requests = []

    def handle(request):
        body = json.loads(request.content)
        wire_requests.append(body)
        message_bytes = json.dumps(body["messages"], ensure_ascii=False, separators=(",", ":")).encode()
        assert len(message_bytes) <= 32768
        assert body["model"] == "deepseek-flash" and body["max_tokens"] == 4096
        assert body["thinking"] == {"type": "disabled"}
        user = json.loads(body["messages"][1]["content"])
        assert user["schema"] == CAPABILITY_DECISION_SCHEMA
        assert user["field_shape"]["claim_decisions"]
        return httpx.Response(200, json={
            "model": "deepseek-flash",
            "choices": [{"message": {"content": json.dumps(decision, ensure_ascii=False)},
                         "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 23, "completion_tokens": 19, "total_tokens": 42},
        })

    def provider():
        return OpenAICompatibleLLM(
            base_url="https://api.deepseek.com",
            api_key="offline-test-only",
            model="deepseek-flash",
            client=httpx.Client(transport=httpx.MockTransport(handle)),
            budget_policy=BudgetPolicy(4096, 4096, 4096, 4096, 4096, 4096),
        )

    fence = PlanningWriteFence(job, run, project, actor, token)
    first_calls = PgV2Calls(business_db.app_dsn, scope=scope, project_id=project, run_id=run,
                            manifest=manifest, fence=fence, provider=provider())
    first_plan = CapabilityPlanner(first_calls).plan(
        profile, run_id=run, attempt_id="capability-planning", output_protocol=CAPABILITY_DECISION_PROTOCOL
    )
    assert isinstance(first_plan, CapabilityPlan)
    assert len(wire_requests) == 1
    with psycopg.connect(business_db.migrator_dsn) as conn:
        attempt = conn.execute(
            "SELECT schema_name,status,response_payload FROM ai_provider_attempts WHERE run_id=%s",
            (run,),
        ).fetchone()
    assert attempt[0] == CAPABILITY_DECISION_SCHEMA and attempt[1] == "succeeded"
    assert attempt[2]["value"]["payload"] == decision

    # A fresh W5 ledger reuses the durable receipt; it must not dispatch again.
    resumed_calls = PgV2Calls(business_db.app_dsn, scope=scope, project_id=project, run_id=run,
                              manifest=manifest, fence=fence, provider=provider())
    resumed_plan = CapabilityPlanner(resumed_calls).plan(
        profile, run_id=run, attempt_id="capability-planning", output_protocol=CAPABILITY_DECISION_PROTOCOL
    )
    assert isinstance(resumed_plan, CapabilityPlan) and resumed_plan.plan_hash == first_plan.plan_hash
    assert len(wire_requests) == 1

    state = {"stage": "capability_planning", "plan_hash": first_plan.plan_hash,
             "source_goal_profile_hash": profile.profile_hash}
    PgV2Checkpoints(checkpoint_db.app_dsn, calls=first_calls, thread_id=run).save(state)
    cold_calls = PgV2Calls(business_db.app_dsn, scope=scope, project_id=project, run_id=run,
                           manifest=manifest, fence=fence, provider=provider())
    restored = PgV2Checkpoints(checkpoint_db.app_dsn, calls=cold_calls, thread_id=run).load()
    assert restored == state
    assert len(wire_requests) == 1

    legacy_manifest = build_v2_manifest(
        goal,
        model_ref="deployment",
        source_facts=facts,
        budget=budget,
        checked_at=STAMP,
        product_semantics=PRODUCT_SEMANTICS_V2,
        acceptance_gate=OWNED_ACCEPTANCE_GATE,
    )
    assert purpose_schema(legacy_manifest, CAPABILITY_PURPOSE) != CAPABILITY_DECISION_SCHEMA
    legacy_calls = PgV2Calls(business_db.app_dsn, scope=scope, project_id=project, run_id=run,
                             manifest=legacy_manifest, fence=fence, provider=provider())
    with pytest.raises(V2RecoveryBlocked):
        PgV2Checkpoints(checkpoint_db.app_dsn, calls=legacy_calls, thread_id=run).load()
    assert len(wire_requests) == 1
    assert content_hash(manifest) != content_hash(legacy_manifest)
