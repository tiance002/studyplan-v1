"""Owned real PG: V2 compile, atomic Draft, explicit publication and fresh readback."""

import json
import os
import subprocess
import sys
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import psycopg
import pytest
from app.core.errors import (
    ConflictError,
    ForbiddenError,
    IdempotencyConflictError,
    ValidationAppError,
    VersionConflictError,
)
from app.domain.enums import OutlineSectionKind
from app.domain.planning.models import PlanPublicationService
from app.domain.workspace.models import AuthContext
from app.infrastructure.db.plan_repository import PgPlanRepository
from app.infrastructure.db.v2_planning_persistence import PgV2PlanningPersistence
from psycopg.rows import dict_row

from backend.tests.unit.test_curriculum_compiler import inputs
from tests.pg_harness import create_test_database, harness_skip_reason, roles_created_by_harness

pytestmark = pytest.mark.postgres
ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "var/planning-v2-item7-p2-20261008"


class SafeDatabase:
    def __init__(self, database):
        self.database = database

    def __getattr__(self, name):
        return getattr(self.database, name)

    def __repr__(self):
        return "OwnedPgDatabase(" + self.database.name + ")"


@pytest.fixture(scope="module")
def db():
    assert os.environ.get("STUDYPLAN_TEST_PG_DEDICATED", "").lower() not in {"1", "true", "yes", "on"}
    assert harness_skip_reason() is None
    database = create_test_database(prefix="studyplan_test_v2p2")
    env = dict(
        os.environ,
        STUDYPLAN_MIGRATION_DSN=database.migrator_dsn.replace("postgresql://", "postgresql+psycopg://"),
    )
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=ROOT / "backend",
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    receipt = json.dumps(
        {
            "database": database.name,
            "roles_created": sorted(roles_created_by_harness()),
            "migration": "0025",
            "migration_result": "PASS",
        }
    )
    (EVIDENCE / ("owned-database-" + database.name + ".json")).write_text(receipt, encoding="utf8")
    (EVIDENCE / "owned-database.json").write_text(receipt, encoding="utf8")
    assert not roles_created_by_harness()
    yield SafeDatabase(database)
    # Retained owned DB is evidence for the independent readback/review.


@pytest.fixture
def scope(db):
    from uuid import uuid4

    project = "p2_" + uuid4().hex[:12]
    with psycopg.connect(db.migrator_dsn) as conn:
        conn.execute(
            "INSERT INTO learning_projects(project_id,owner_actor_id,title,goal_statement,stable_key) VALUES(%s,%s,'V2 test','Goal',%s)",
            (project, "p2actor", project),
        )
    return AuthContext("p2actor", "p2session", datetime.now(timezone.utc), (project,))


def persist(db, scope, run="", **overrides):
    curriculum, arguments = inputs(project="已有CLI，不新建演示项目", excluded=True)
    return PgV2PlanningPersistence(db.app_dsn, allow_unbound_preview=True).persist(
        scope=scope,
        project_id=scope.learning_project_scope[0],
        run_id=run,
        expected_version=overrides.pop("expected_version", 0),
        curriculum=curriculum,
        **(arguments | overrides),
    )


def claimed_run(db, scope):
    from app.core.ids import new_id
    from app.domain.runs.fencing import PlanningWriteFence

    run, job, token = new_id("run"), new_id("job"), new_id("lease")
    project = scope.learning_project_scope[0]
    with psycopg.connect(db.migrator_dsn) as conn:
        conn.execute(
            "INSERT INTO ai_runs(run_id,actor_id,project_id,kind,graph_name,graph_version,status,next_action,thread_id,version) "
            "VALUES(%s,%s,%s,'plan_generate','planning','planning-v2-test','running','wait',%s,1)",
            (run, scope.actor_id, project, run),
        )
        conn.execute(
            "INSERT INTO ai_jobs(job_id,run_id,job_key,status,lease_token,lease_expires_at) VALUES(%s,%s,%s,'running',%s,clock_timestamp()+interval '5 minutes')",
            (job, run, "planning:" + run, token),
        )
    return run, PlanningWriteFence(job, run, project, scope.actor_id, token)


@pytest.mark.parametrize("invalidate", ["cancel", "lease", "actor", "project"])
def test_real_run_fence_rejects_late_or_wrong_results(db, scope, invalidate):
    from app.ports.planning_jobs import PlanningLeaseLostError

    run, fence = claimed_run(db, scope)
    if invalidate in {"cancel", "lease"}:
        with psycopg.connect(db.migrator_dsn) as conn:
            if invalidate == "cancel":
                conn.execute("UPDATE ai_runs SET status='cancelled' WHERE run_id=%s", (run,))
            else:
                conn.execute(
                    "UPDATE ai_jobs SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE run_id=%s",
                    (run,),
                )
    elif invalidate == "actor":
        fence = replace(fence, actor_id="other")
    else:
        fence = replace(fence, project_id="other")
    with pytest.raises((ConflictError, PlanningLeaseLostError)):
        persist(db, scope, run=run, write_fence=fence)
    with psycopg.connect(db.migrator_dsn) as conn:
        assert (
            conn.execute(
                "SELECT count(*) FROM plan_drafts WHERE project_id=%s", (scope.learning_project_scope[0],)
            ).fetchone()[0]
            == 0
        )


def test_real_run_fenced_persistence_replay_then_cancel_guard(db, scope):
    from app.ports.planning_jobs import PlanningLeaseLostError

    run, fence = claimed_run(db, scope)
    first = persist(db, scope, run=run, write_fence=fence)
    assert first.run_id == run
    assert first.v2_execution.to_payload()["bindings"]["run_id"] == run
    replay = persist(db, scope, run=run, write_fence=fence)
    assert replay.draft_id == first.draft_id
    assert replay.v2_execution.to_payload() == first.v2_execution.to_payload()
    with psycopg.connect(db.migrator_dsn) as conn:
        assert (
            conn.execute(
                "SELECT count(*) FROM plan_drafts WHERE project_id=%s", (first.project_id,)
            ).fetchone()[0]
            == 1
        )
        conn.execute("UPDATE ai_runs SET status='cancelled' WHERE run_id=%s", (run,))
    with pytest.raises((ConflictError, PlanningLeaseLostError)):
        persist(db, scope, run=run, write_fence=fence)


def test_verified_knowledge_reuse_and_immutable_revision_history(db, scope):
    from app.domain.planning.curriculum_compiler import PublicKnowledgeBinding, knowledge_definition_hash

    first = persist(db, scope)
    repo = PgPlanRepository(db.app_dsn)
    pub1 = PlanPublicationService(repo).publish(
        draft=first, presented_hash=first.content_hash, expected_version=0, idempotency_key="history-1"
    )
    old = repo.get_revision(project_id=first.project_id, revision=1)
    fingerprint = old.structure_fingerprint()
    raw = first.v2_execution.to_payload()
    node = raw["compiled"]["nodes"][0]
    identity = raw["bindings"]["nodes"][node["stable_key"]]
    binding = PublicKnowledgeBinding(node["stable_key"], identity, "1", knowledge_definition_hash(node))
    run, fence = claimed_run(db, scope)
    second = persist(
        db, scope, run=run, write_fence=fence, expected_version=1, public_knowledge_bindings=(binding,)
    )
    assert second.v2_execution.to_payload()["bindings"]["nodes"][node["stable_key"]] == identity
    with psycopg.connect(db.migrator_dsn) as conn:
        assert (
            conn.execute(
                "SELECT count(*) FROM knowledge_nodes WHERE project_id=%s", (first.project_id,)
            ).fetchone()[0]
            == 1
        )
    pub2 = PlanPublicationService(repo).publish(
        draft=second, presented_hash=second.content_hash, expected_version=1, idempotency_key="history-2"
    )
    assert pub1.plan_id != pub2.plan_id
    history = PgPlanRepository(db.app_dsn).get_revision(project_id=first.project_id, revision=1)
    assert history.structure_fingerprint() == fingerprint
    assert str(history.status) == "superseded"
    assert repo.get_current(project_id=first.project_id).plan_id == pub2.plan_id
    assert len(repo.list_revisions(project_id=first.project_id)) == 2


def test_real_compile_persist_confirm_fresh_complete(db, scope):
    draft = persist(db, scope)
    project = draft.project_id
    repo = PgPlanRepository(db.app_dsn)
    read = repo.get_draft(project_id=project, draft_id=draft.draft_id)
    assert read.content_hash == draft.content_hash
    assert read.v2_execution.to_payload() == draft.v2_execution.to_payload()
    assert repo.get_current(project_id=project) is None
    raw = read.v2_execution.to_payload()
    assert raw["compiled"]["practice"]["tasks"][0]["practice_kind"] == "micro_exercise"
    assert not read.stage_resources  # research_checked is not promoted to public catalog
    published = PlanPublicationService(repo).publish(
        draft=read, presented_hash=read.content_hash, expected_version=0, idempotency_key="confirm"
    )
    fresh = PgPlanRepository(db.app_dsn).get_current(project_id=project)
    assert fresh.plan_id == published.plan_id
    assert fresh.v2_execution.to_payload()["compiled"] == raw["compiled"]
    assert fresh.v2_execution.to_payload()["manifest"] == raw["manifest"]
    assert set(s.stage_id for s in fresh.stages).isdisjoint(s.stage_id for s in draft.stages)
    assert fresh.v2_execution.semantic_payload() == draft.v2_execution.semantic_payload()
    assert fresh.v2_execution.user_content()["practice"] == raw["compiled"]["practice"]
    assert (
        PlanPublicationService(repo)
        .publish(
            draft=repo.get_draft(project_id=project, draft_id=draft.draft_id),
            presented_hash=draft.content_hash,
            expected_version=0,
            idempotency_key="confirm",
        )
        .plan_id
        == published.plan_id
    )
    (EVIDENCE / "roundtrip.json").write_text(
        json.dumps(
            {
                "draft_id": draft.draft_id,
                "plan_id": fresh.plan_id,
                "project_id": project,
                "draft_hash": draft.content_hash,
                "fingerprint": fresh.structure_fingerprint(),
                "snapshot": fresh.v2_execution.to_payload(),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf8",
    )


def test_same_run_same_body_reused_different_rejected(db, scope):
    first = persist(db, scope)
    assert persist(db, scope).draft_id == first.draft_id
    curriculum, args = inputs(project="不同载体", excluded=True)
    with pytest.raises(IdempotencyConflictError):
        PgV2PlanningPersistence(db.app_dsn, allow_unbound_preview=True).persist(
            scope=scope,
            project_id=first.project_id,
            run_id="",
            expected_version=0,
            curriculum=curriculum,
            **args,
        )


def test_atomic_entity_draft_rollback(db, scope, monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("injected final Draft failure")

    monkeypatch.setattr(PgPlanRepository, "save_draft", fail)
    with pytest.raises(RuntimeError):
        persist(db, scope)
    with psycopg.connect(db.migrator_dsn) as conn:
        for table in (
            "knowledge_nodes",
            "learning_units",
            "unit_node_links",
            "practice_projects",
            "practice_tasks",
            "task_knowledge_links",
            "resource_records",
            "plan_drafts",
        ):
            assert (
                conn.execute(
                    f"SELECT count(*) FROM {table} WHERE project_id=%s", (scope.learning_project_scope[0],)
                ).fetchone()[0]
                == 0
            ), table


def test_description_edit_recompile_current_hash_and_stale_reject(db, scope):
    draft = persist(db, scope)
    bridge = PgV2PlanningPersistence(db.app_dsn)
    edited = tuple(
        replace(s, title=s.title + " · 我的标题", objective=s.objective + "，记录检查证据")
        for s in draft.stages
    )
    current = bridge.edit_descriptions(
        scope=scope,
        project_id=draft.project_id,
        draft_id=draft.draft_id,
        expected_version=0,
        expected_hash=draft.content_hash,
        stages=edited,
    )
    assert current.content_hash != draft.content_hash
    before, after = draft.v2_execution.to_payload(), current.v2_execution.to_payload()
    assert before["original_curriculum_hash"] == after["original_curriculum_hash"]
    assert before["manifest"]["input_curriculum_plan_hash"] != after["manifest"]["input_curriculum_plan_hash"]
    assert before["manifest"]["compiled_payload_digest"] != after["manifest"]["compiled_payload_digest"]
    with pytest.raises(ConflictError):
        PlanPublicationService(PgPlanRepository(db.app_dsn)).publish(
            draft=current, presented_hash=draft.content_hash, expected_version=0, idempotency_key="stale"
        )
    PlanPublicationService(PgPlanRepository(db.app_dsn)).publish(
        draft=current, presented_hash=current.content_hash, expected_version=0, idempotency_key="edited"
    )
    assert (
        PgPlanRepository(db.app_dsn).get_current(project_id=draft.project_id).stages[0].title
        == edited[0].title
    )


def test_scope_cas_and_marker_tamper_rejected(db, scope):
    draft = persist(db, scope)
    denied = replace(scope, actor_id="another")
    with pytest.raises(ForbiddenError):
        persist(db, denied)
    assert PgPlanRepository(db.app_dsn).get_draft(project_id="wrong", draft_id=draft.draft_id) is None
    with pytest.raises(VersionConflictError):
        PlanPublicationService(PgPlanRepository(db.app_dsn)).publish(
            draft=draft, presented_hash=draft.content_hash, expected_version=1, idempotency_key="cas"
        )
    draft.stages = (replace(draft.stages[0], section_kind=OutlineSectionKind.CORE),)
    with pytest.raises(ValidationAppError):
        PgPlanRepository(db.app_dsn).save_draft(draft)


def test_database_entity_mismatch_blocks_confirm(db, scope):
    draft = persist(db, scope)
    node = next(iter(draft.v2_execution.to_payload()["bindings"]["nodes"].values()))
    with psycopg.connect(db.migrator_dsn) as conn:
        conn.execute("UPDATE knowledge_nodes SET objectives='[\"changed\"]'::jsonb WHERE node_id=%s", (node,))
    with pytest.raises(ConflictError):
        PlanPublicationService(PgPlanRepository(db.app_dsn)).publish(
            draft=draft, presented_hash=draft.content_hash, expected_version=0, idempotency_key="bad"
        )
    with psycopg.connect(db.migrator_dsn) as conn:
        assert (
            conn.execute(
                "SELECT count(*) FROM plan_revisions WHERE project_id=%s", (draft.project_id,)
            ).fetchone()[0]
            == 0
        )


def test_unbound_run_and_scope_fence_cannot_write(db, scope):
    curriculum, args = inputs()
    for run in ("cancelled_run", "another_project_run", ""):
        with pytest.raises(ConflictError):
            PgV2PlanningPersistence(db.app_dsn).persist(
                scope=scope,
                project_id=scope.learning_project_scope[0],
                run_id=run,
                expected_version=0,
                curriculum=curriculum,
                **args,
            )
    draft = persist(db, scope)
    draft.run_id = "other"
    with pytest.raises(ValidationAppError):
        PgPlanRepository(db.app_dsn).save_draft(draft)


@pytest.mark.parametrize("mode", ["whole_core", "slices"])
def test_long_guidance_project_study_and_real_consumers(db, scope, mode):
    from types import SimpleNamespace

    from app.core.ids import content_hash
    from app.domain.planning.curriculum import ProjectCase, validate_curriculum_output
    from app.domain.prompts import prompt_review_context
    from app.domain.summaries import review_rubric_context
    from app.infrastructure.db.learning_exposures import PgLearningExposures
    from app.infrastructure.db.prompts import PgPrompts
    from app.infrastructure.db.summaries import PgSummaries

    from backend.tests.unit.test_curriculum import output, prepared

    curriculum, args = inputs(project="已有私有CLI", excluded=True)
    refs = tuple(
        args["context"].to_payload()["capabilities"][0]["outcomes"][i]["outcome_id"] for i in range(3)
    )
    case = ProjectCase(
        "case_fixture",
        "https://github.com/demo/tutorial",
        "v1",
        mode,
        refs,
        (("fixture:bounded", content_hash({"synthetic": True})),),
        "bounded_reviewed",
    )
    ctx = prepared(args["profile"], args["capability_plan"], project_cases=(case,))
    raw = output(ctx, project_study=True)
    raw["project_study_requirements"][0].update(mode=mode, selected_case_ref=case.case_id)
    raw["stages"][0]["guidance"]["previous_relation"] = "教学描述" * 350
    raw["stages"][0]["what_to_learn"] = "学习描述" * 350
    raw["status"] = "complete"
    candidate = validate_curriculum_output(raw, ctx.to_payload())
    args = args | {"context": ctx, "source_facts": replace(args["source_facts"], project_cases=(case,))}
    draft = PgV2PlanningPersistence(db.app_dsn, allow_unbound_preview=True).persist(
        scope=scope,
        project_id=scope.learning_project_scope[0],
        run_id="",
        expected_version=0,
        curriculum=candidate,
        **args,
    )
    repo = PgPlanRepository(db.app_dsn)
    PlanPublicationService(repo).publish(
        draft=draft, presented_hash=draft.content_hash, expected_version=0, idempotency_key="consumer"
    )
    plan = repo.get_current(project_id=draft.project_id)
    assert plan.v2_execution.user_content()["project_study"][0]["requirement"]["mode"] == mode
    assert (
        plan.v2_execution.user_content()["stages"][0]["guidance"]["previous_relation"]
        == raw["stages"][0]["guidance"]["previous_relation"]
    )
    exposure = PgLearningExposures(db.app_dsn).list(scope, plan.project_id, plan.plan_id)[0]
    assert (
        exposure["source_snapshot"]["v2_content"]["materials"]
        == plan.v2_execution.stage_content(plan.stages[0].stage_id)["materials"]
    )
    with psycopg.connect(db.app_dsn, row_factory=dict_row) as conn:
        conn.execute("SELECT set_config('app.project_id',%s,true)", (plan.project_id,))
        row = PgLearningExposures._plan(conn, plan.project_id, plan.plan_id)
        pos = (plan.project_id, plan.plan_id, plan.stages[0].stage_id, plan.task_links[0].task_id)
        _, task = PgPrompts._context(conn, pos)
        assert (
            task["v2_content"]["tasks"][0]["acceptance"]
            == candidate.to_payload()["stages"][0]["tasks"][0]["acceptance"]
        )
        prompt = prompt_review_context({"task": task})
        assert prompt["v2_requirements"]["tasks"][0]["practice_kind"] == "micro_exercise"
        assert "已有私有CLI" not in json.dumps(prompt, ensure_ascii=False)
        command = SimpleNamespace(
            position=(*pos[:3], None),
            project_id=plan.project_id,
            plan_id=plan.plan_id,
            stage_id=plan.stages[0].stage_id,
        )
        stage = PgSummaries._stage(conn, command.position)
        snap = PgSummaries._stage_snapshot(conn, command, row, stage)
        public = review_rubric_context(snap)
        assert (
            public["v2_requirements"]["units"][0]["rubric"]
            == candidate.to_payload()["stages"][0]["units"][0]["rubric"]
        )
        assert "已有私有CLI" not in json.dumps(public, ensure_ascii=False)
    from app.api.v1.views import draft_view, plan_view
    from app.application.plan_service import DraftBundle, PlanBundle

    views = {
        "draft": draft_view(DraftBundle(draft, ())).model_dump(mode="json"),
        "plan": plan_view(PlanBundle(plan, ())).model_dump(mode="json"),
    }
    (EVIDENCE / ("fresh-api-" + mode + ".json")).write_text(
        json.dumps(views, ensure_ascii=False, indent=2), encoding="utf8"
    )


def test_actual_public_catalog_version_and_research_source_preserved(db, scope):
    from app.domain.planning.curriculum import validate_curriculum_output
    from app.domain.planning.curriculum_compiler import CurriculumSourceFacts
    from app.infrastructure.domain_pack import load_pack
    from app.tools.seed_b3 import seed_reviewed_pack

    from backend.tests.unit.test_curriculum import local_mcp_inputs, output, prepared

    p, capabilities, index, source, proof = local_mcp_inputs()
    with psycopg.connect(db.migrator_dsn) as conn:
        seed_reviewed_pack(conn, load_pack("agent-application-v8.json"))
    ctx = prepared(p, capabilities, index, catalog_sources=(source,), access_proofs=(proof,))
    curriculum = validate_curriculum_output(output(ctx), ctx.to_payload())
    args = dict(
        context=ctx,
        profile=p,
        capability_plan=capabilities,
        source_facts=CurriculumSourceFacts(index, (source,), (proof,)),
    )
    draft = PgV2PlanningPersistence(db.app_dsn, allow_unbound_preview=True).persist(
        scope=scope,
        project_id=scope.learning_project_scope[0],
        run_id="",
        expected_version=0,
        curriculum=curriculum,
        **args,
    )
    assert len(draft.stage_resources) == 1
    assert draft.stage_resources[0].source_version == source.source_version
    snapshot = draft.v2_execution.to_payload()
    materials = snapshot["compiled"]["resource_assignments"]
    assert {a["source_snapshot"]["qualification"] for a in materials} == {
        "public_reviewed",
        "research_checked",
    }
    PlanPublicationService(PgPlanRepository(db.app_dsn)).publish(
        draft=draft, presented_hash=draft.content_hash, expected_version=0, idempotency_key="public"
    )
    read = PgPlanRepository(db.app_dsn).get_current(project_id=draft.project_id)
    assert read.v2_execution.to_payload()["compiled"] == snapshot["compiled"]
    assert read.resource_snapshots[0]["source"]["source_version"] == source.source_version
    assert {
        a["source_snapshot"]["source_version"] for a in read.v2_execution.user_content()["materials"]
    } == {a["source_snapshot"]["source_version"] for a in materials}


def test_public_knowledge_requires_prior_exact_outcome_provenance(db, scope):
    from app.domain.planning.curriculum_compiler import PublicKnowledgeBinding, knowledge_definition_hash

    initial = persist(db, scope)
    payload = initial.v2_execution.to_payload()
    knowledge = payload["compiled"]["nodes"][0]
    identity = payload["bindings"]["nodes"][knowledge["stable_key"]]
    binding = PublicKnowledgeBinding(
        knowledge["stable_key"], identity, "1", knowledge_definition_hash(knowledge)
    )
    # A different server Run is not invented for this test. A second private
    # project cannot reuse the first project's identity even with an exact title.
    from uuid import uuid4

    other = "p2_" + uuid4().hex[:12]
    with psycopg.connect(db.migrator_dsn) as conn:
        conn.execute(
            "INSERT INTO learning_projects(project_id,owner_actor_id,title,goal_statement,stable_key) VALUES(%s,'p2actor','t','g',%s)",
            (other, other),
        )
    other_scope = replace(scope, learning_project_scope=(other,))
    with pytest.raises(ValidationAppError):
        persist(db, other_scope, public_knowledge_bindings=(binding,))


@pytest.mark.parametrize("tamper", ["source_url", "source_title", "section_url", "section_review"])
def test_first_public_binding_rejects_same_identity_substitution(db, tamper):
    from app.domain.planning.curriculum import validate_curriculum_output
    from app.domain.planning.curriculum_compiler import CurriculumSourceFacts, compile_curriculum
    from app.infrastructure.db.v2_planning_persistence import _public_catalog
    from app.infrastructure.domain_pack import load_pack
    from app.tools.seed_b3 import seed_reviewed_pack

    from backend.tests.unit.test_curriculum import local_mcp_inputs, output, prepared

    p, capabilities, index, source, proof = local_mcp_inputs()
    with psycopg.connect(db.migrator_dsn) as conn:
        seed_reviewed_pack(conn, load_pack("agent-application-v8.json"))
    ctx = prepared(p, capabilities, index, catalog_sources=(source,), access_proofs=(proof,))
    result = compile_curriculum(
        validate_curriculum_output(output(ctx), ctx.to_payload()),
        context=ctx,
        profile=p,
        capability_plan=capabilities,
        source_facts=CurriculumSourceFacts(index, (source,), (proof,)),
    )
    material = next(
        a["source_snapshot"]
        for a in result.to_payload()["resource_assignments"]
        if a["source_snapshot"]["qualification"] == "public_reviewed"
    )
    with psycopg.connect(db.migrator_dsn, row_factory=dict_row) as conn:
        if tamper == "source_url":
            conn.execute(
                "UPDATE public_resource_sources SET canonical_url='https://example.com/substituted' WHERE source_id=%s",
                (source.source_id,),
            )
        elif tamper == "source_title":
            conn.execute(
                "UPDATE public_resource_sources SET title='Different source' WHERE source_id=%s",
                (source.source_id,),
            )
        elif tamper == "section_url":
            conn.execute(
                "UPDATE public_resource_sections SET url='https://example.com/substituted' WHERE section_id=%s",
                (material["section_refs"][0],),
            )
        else:
            conn.execute(
                "UPDATE public_resource_sections SET review_note='Different review' WHERE section_id=%s",
                (material["section_refs"][0],),
            )
        with pytest.raises(ValidationAppError):
            _public_catalog(conn, material)
        conn.rollback()
