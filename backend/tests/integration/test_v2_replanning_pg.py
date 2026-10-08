"""Item8 owned PG evidence; no product database or external calls."""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from app.application.v2_revisions import V2RevisionService
from app.core.errors import (
    ConflictError,
    ForbiddenError,
    IdempotencyConflictError,
    ValidationAppError,
    VersionConflictError,
)
from app.domain.planning.models import PlanPublicationService
from app.domain.planning.revisions import LocalStageEdit
from app.domain.workspace.models import AuthContext
from app.infrastructure.db.plan_repository import PgPlanRepository
from app.infrastructure.db.v2_planning_persistence import PgV2PlanningPersistence
from app.infrastructure.db.v2_revisions import PgV2Revisions

from backend.tests.unit.test_curriculum_compiler import inputs
from tests.pg_harness import create_test_database, harness_skip_reason, roles_created_by_harness

pytestmark = pytest.mark.postgres
ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "var/planning-v2-item8-20261008"


class SafeDatabase:
    def __init__(self, database):
        self.database = database

    def __getattr__(self, name):
        return getattr(self.database, name)

    def __repr__(self):
        return "OwnedPgDatabase(" + self.database.name + ")"


def _database(prefix, *, migrate):
    assert os.environ.get("STUDYPLAN_TEST_PG_DEDICATED", "").lower() not in {"1", "true", "yes", "on"}
    assert harness_skip_reason() is None
    database = create_test_database(prefix=prefix)
    if migrate:
        env = dict(os.environ, STUDYPLAN_MIGRATION_DSN=database.migrator_dsn.replace("postgresql://", "postgresql+psycopg://"))
        result = subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=ROOT / "backend", env=env, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
    assert not roles_created_by_harness()
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    receipt = {"database": database.name, "roles_created": [], "migration": "0025" if migrate else "PostgresSaver-owned"}
    (EVIDENCE / ("owned-database-" + database.name + ".json")).write_text(json.dumps(receipt), encoding="utf8")
    return SafeDatabase(database)


@pytest.fixture(scope="module")
def db():
    return _database("studyplan_test_v2i8", migrate=True)


@pytest.fixture(scope="module")
def checkpoint_db():
    return _database("studyplan_test_v2i8cp", migrate=False)


@pytest.fixture
def scope(db):
    project = "item8_" + uuid4().hex
    actor = "item8_actor_" + uuid4().hex
    with psycopg.connect(db.migrator_dsn) as conn:
        conn.execute("INSERT INTO learning_projects(project_id,owner_actor_id,title,goal_statement,stable_key) VALUES(%s,%s,'Item8','Goal',%s)", (project, actor, project))
    return AuthContext(actor, "item8-session", datetime.now(timezone.utc), (project,))


def published_base(db, scope, *, systematic=False):
    curriculum, args = inputs(systematic=systematic)
    project = scope.learning_project_scope[0]
    draft = PgV2PlanningPersistence(db.app_dsn, allow_unbound_preview=True).persist(scope=scope, project_id=project, run_id="", expected_version=0, curriculum=curriculum, **args)
    repo = PgPlanRepository(db.app_dsn)
    result = PlanPublicationService(repo).publish(draft=draft, presented_hash=draft.content_hash, expected_version=0, idempotency_key="base-publish")
    return repo.get_revision(project_id=project, revision=result.revision)


def preview(service, scope, base, key="local", **kw):
    return service.preview_local(scope=scope, project_id=base.project_id, expected_version=base.revision,
        current_plan_id=base.plan_id, idempotency_key=key,
        stage_edits=(LocalStageEdit(base.stages[-1].stage_id, what_to_learn="先检查输入，再验证全部获准目标与失败路径"),), **kw)


def test_local_preview_confirm_history_and_hash(db, scope):
    base = published_base(db, scope)
    service = V2RevisionService(PgV2Revisions(db.app_dsn))
    bundle = preview(service, scope, base)
    assert bundle.draft.content_hash != base.structure_fingerprint()
    assert PgPlanRepository(db.app_dsn).get_current(project_id=base.project_id).plan_id == base.plan_id
    outcome = service.confirm(scope=scope, project_id=base.project_id, draft_id=bundle.draft.draft_id,
        expected_version=1, draft_hash=bundle.draft.content_hash, idempotency_key="confirm")
    assert outcome.plan.revision == 2
    assert outcome.plan.v2_revision.to_payload()["lineage"][0]["source_stage_id"] == base.stages[0].stage_id
    assert outcome.plan.stages[0].stage_id != base.stages[0].stage_id
    assert outcome.plan.stages[0].objective != base.stages[0].objective
    again = service.confirm(scope=scope, project_id=base.project_id, draft_id=bundle.draft.draft_id,
        expected_version=1, draft_hash=bundle.draft.content_hash, idempotency_key="confirm")
    assert again.plan.plan_id == outcome.plan.plan_id
    with pytest.raises(ConflictError):
        service.confirm(scope=scope, project_id=base.project_id, draft_id=bundle.draft.draft_id,
            expected_version=1, draft_hash="wrong-even-on-replay", idempotency_key="confirm")
    with pytest.raises(ConflictError):
        service.confirm(scope=scope, project_id=base.project_id, draft_id=bundle.draft.draft_id,
            expected_version=99, draft_hash=bundle.draft.content_hash, idempotency_key="confirm")
    fresh = PgPlanRepository(db.app_dsn)
    assert fresh.get_revision(project_id=base.project_id, revision=1).structure_fingerprint() == base.structure_fingerprint()
    assert fresh.get_current(project_id=base.project_id).plan_id == outcome.plan.plan_id
    assert service.get_preview(scope=scope, project_id=base.project_id, draft_id=bundle.draft.draft_id).draft.status.value == "approved"


def test_local_required_set_and_prerequisites_cannot_be_deleted_or_reordered(db, scope):
    base = published_base(db, scope, systematic=True)
    service = V2RevisionService(PgV2Revisions(db.app_dsn))
    for order in ((), (base.stages[2].stage_id, base.stages[1].stage_id, base.stages[0].stage_id)):
        with pytest.raises(ValidationAppError):
            preview(service, scope, base, key="bad" + str(len(order)), stage_order=order)


def test_local_wrong_hash_idempotency_scope_and_cancel(db, scope):
    base = published_base(db, scope)
    service = V2RevisionService(PgV2Revisions(db.app_dsn))
    draft = preview(service, scope, base).draft
    with pytest.raises(IdempotencyConflictError):
        preview(service, scope, base, stage_order=tuple(s.stage_id for s in base.stages))
    with pytest.raises(ConflictError):
        service.confirm(scope=scope, project_id=base.project_id, draft_id=draft.draft_id, expected_version=1, draft_hash="stale", idempotency_key="wrong")
    forged = AuthContext("other-account", "session", datetime.now(timezone.utc), (base.project_id,))
    with pytest.raises(ForbiddenError):
        service.get_preview(scope=forged, project_id=base.project_id, draft_id=draft.draft_id)
    service.cancel(scope=scope, project_id=base.project_id, draft_id=draft.draft_id, expected_version=1, draft_hash=draft.content_hash)
    with pytest.raises(ConflictError):
        service.confirm(scope=scope, project_id=base.project_id, draft_id=draft.draft_id, expected_version=1, draft_hash=draft.content_hash, idempotency_key="cancelled")


def saved_history(db, scope, base, *, accept=True):
    from app.domain.enums import UnitProgress
    from app.domain.learning_exposures import ExposureCommand
    from app.domain.practice_submissions import (
        CriterionCoverage,
        SubmissionDecisionCommand,
        SubmissionEvidence,
        SubmissionSaveCommand,
    )
    from app.domain.prompts import PromptSaveCommand
    from app.domain.summaries import SummarySaveCommand
    from app.infrastructure.db.learning_exposures import PgLearningExposures
    from app.infrastructure.db.practice_submissions import PgPracticeSubmissions
    from app.infrastructure.db.prompts import PgPrompts
    from app.infrastructure.db.summaries import PgSummaries
    stage = base.stages[0]
    unit = next(link.unit_id for link in base.unit_links if link.stage_id == stage.stage_id)
    exposures = PgLearningExposures(db.app_dsn)
    exposures.change(scope, ExposureCommand(base.project_id, base.plan_id, stage.stage_id, unit,
        UnitProgress.IN_PROGRESS, 0, "history-started"))
    exposures.change(scope, ExposureCommand(base.project_id, base.plan_id, stage.stage_id, unit,
        UnitProgress.COMPLETED, 1, "history-read-completed"))
    task = next(link.task_id for link in base.task_links if link.stage_id == stage.stage_id)
    summary = PgSummaries(db.app_dsn).save(scope, SummarySaveCommand(base.project_id, base.plan_id,
        stage.stage_id, None, "原总结：精确旧版本的学习证据🙂", 0, "history-summary"))["attempt"]
    prompt = PgPrompts(db.app_dsn).save(scope, PromptSaveCommand(base.project_id, base.plan_id,
        stage.stage_id, task, "原Prompt：保留旧任务版本🙂", 0, "history-prompt"))["revision"]
    repository = PgPracticeSubmissions(db.app_dsn)
    cmd = SubmissionSaveCommand(base.project_id, base.plan_id, stage.stage_id, task,
        "原成果：人工观察正常与失败行为🙂", None, (SubmissionEvidence("external_report", "测试记录", "实际观察", None),),
        "evaluation", None, base.revision, 1, 0, "history-submission")
    saved = repository.save(scope, cmd)
    acceptance = saved["submission"]["task_snapshot"]["task"]["acceptance"]
    decision = SubmissionDecisionCommand(base.project_id, saved["submission"]["submission_id"], "accepted", "用户明确确认可检查证据",
        tuple(CriterionCoverage(i, (0,), "本项已观察") for i in range(len(acceptance))), True,
        base.revision, saved["thread"]["task_version"], saved["thread"]["version"], "history-accept")
    accepted = repository.decide(scope, decision) if accept else saved
    return summary, prompt, accepted


def test_completed_prefix_and_exact_artifacts_survive_local_publication(db, scope):
    from app.infrastructure.db.learning_exposures import PgLearningExposures
    from app.infrastructure.db.practice_submissions import PgPracticeSubmissions
    from app.infrastructure.db.prompts import PgPrompts
    from app.infrastructure.db.summaries import PgSummaries
    base = published_base(db, scope, systematic=True)
    summary, prompt, accepted = saved_history(db, scope, base)
    old_exposures = PgLearningExposures(db.app_dsn).history(scope, base.project_id, base.plan_id,
        base.stages[0].stage_id, base.unit_links[0].unit_id)
    service = V2RevisionService(PgV2Revisions(db.app_dsn))
    ctx = service.context(scope=scope, project_id=base.project_id)
    assert ctx["stages"][0]["learning_status"] == "completed" and ctx["stages"][0]["protected"]
    with pytest.raises(ValidationAppError):
        service.preview_local(scope=scope, project_id=base.project_id, expected_version=1, current_plan_id=base.plan_id,
            idempotency_key="completed", stage_edits=(LocalStageEdit(base.stages[0].stage_id, title="不得改历史"),))
    draft = preview(service, scope, base).draft
    outcome = service.confirm(scope=scope, project_id=base.project_id, draft_id=draft.draft_id,
        expected_version=1, draft_hash=draft.content_hash, idempotency_key="history-confirm")
    assert outcome.plan.stages[0].title == base.stages[0].title
    assert PgSummaries(db.app_dsn).attempt(scope, base.project_id, summary["attempt_id"]) == summary
    assert PgPrompts(db.app_dsn).attempt(scope, base.project_id, prompt["revision_id"]) == prompt
    assert PgPracticeSubmissions(db.app_dsn).get(scope, base.project_id, accepted["submission"]["submission_id"]) == accepted["submission"]
    assert PgLearningExposures(db.app_dsn).history(scope, base.project_id, base.plan_id,
        base.stages[0].stage_id, base.unit_links[0].unit_id) == old_exposures
    new_context = service.context(scope=scope, project_id=base.project_id)
    assert all(s["learning_status"] == "future" for s in new_context["stages"])
    assert new_context["stages"][0]["historical_learning_status"] == "completed"
    assert new_context["stages"][0]["protected"] is True
    with psycopg.connect(db.migrator_dsn) as conn:
        for table in ("summary_attempts", "prompt_revisions", "practice_submissions", "learning_exposures"):
            assert conn.execute(f"SELECT count(*) FROM {table} WHERE project_id=%s AND plan_id=%s", (base.project_id, outcome.plan.plan_id)).fetchone()[0] == 0
    (EVIDENCE / "r1-history-readback.json").write_text(json.dumps({"old_revision": 1, "current_revision": 2,
        "summary_id": summary["attempt_id"], "prompt_id": prompt["revision_id"], "submission_id": accepted["submission"]["submission_id"],
        "lineage": outcome.plan.v2_revision.to_payload()["lineage"], "new_progress": new_context["stages"]}, ensure_ascii=False), encoding="utf8")


def test_progress_change_and_concurrent_publication_reject_stale_preview(db, scope):
    from concurrent.futures import ThreadPoolExecutor

    from app.domain.summaries import SummarySaveCommand
    from app.infrastructure.db.summaries import PgSummaries
    base = published_base(db, scope, systematic=True)
    service = V2RevisionService(PgV2Revisions(db.app_dsn))
    stale = preview(service, scope, base, key="stale-progress").draft
    PgSummaries(db.app_dsn).save(scope, SummarySaveCommand(base.project_id, base.plan_id, base.stages[0].stage_id,
        None, "预览后新保存的总结", 0, "after-preview"))
    with pytest.raises(ConflictError) as error:
        service.confirm(scope=scope, project_id=base.project_id, draft_id=stale.draft_id,
            expected_version=1, draft_hash=stale.content_hash, idempotency_key="stale-confirm")
    assert error.value.details["reason"] == "revision_progress_stale"
    drafts = [preview(service, scope, base, key="race" + str(i)).draft for i in range(2)]
    def confirm(index):
        d = drafts[index]
        try:
            return service.confirm(scope=scope, project_id=base.project_id, draft_id=d.draft_id,
                expected_version=1, draft_hash=d.content_hash, idempotency_key="race-confirm" + str(index)).plan.revision
        except (ConflictError, VersionConflictError):
            return "conflict"
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(confirm, range(2)))
    assert results.count(2) == 1 and results.count("conflict") == 1


def test_local_legal_reorder_preserves_exact_entity_links(db, scope):
    base = published_base(db, scope, systematic=True)
    service = V2RevisionService(PgV2Revisions(db.app_dsn))
    order = (base.stages[0].stage_id, base.stages[2].stage_id, base.stages[1].stage_id)
    bundle = service.preview_local(scope=scope, project_id=base.project_id, expected_version=1,
        current_plan_id=base.plan_id, idempotency_key="legal-reorder", stage_order=order)
    outcome = service.confirm(scope=scope, project_id=base.project_id, draft_id=bundle.draft.draft_id,
        expected_version=1, draft_hash=bundle.draft.content_hash, idempotency_key="reorder-confirm")
    assert [s.stable_key for s in outcome.plan.stages] == [base.stages[i].stable_key for i in (0, 2, 1)]
    assert {link.task_id for link in outcome.plan.task_links} == {link.task_id for link in base.task_links}


def test_material_binding_change_after_preview_rejects_confirm(db, scope):
    base = published_base(db, scope)
    service = V2RevisionService(PgV2Revisions(db.app_dsn))
    draft = preview(service, scope, base).draft
    binding = next(iter(base.v2_execution.to_payload()["bindings"]["materials"].values()))
    with psycopg.connect(db.migrator_dsn) as conn:
        conn.execute("UPDATE resource_records SET url='https://invalid.example/replaced' WHERE project_id=%s AND resource_id=%s",
            (base.project_id, binding["resource_id"]))
    try:
        with pytest.raises(ConflictError):
            service.confirm(scope=scope, project_id=base.project_id, draft_id=draft.draft_id,
                expected_version=1, draft_hash=draft.content_hash, idempotency_key="source-reject")
        with psycopg.connect(db.migrator_dsn) as conn:
            assert conn.execute("SELECT plan_id FROM plan_revisions WHERE project_id=%s AND status='approved'", (base.project_id,)).fetchone()[0] == base.plan_id
            assert conn.execute("SELECT status FROM plan_drafts WHERE project_id=%s AND draft_id=%s", (base.project_id, draft.draft_id)).fetchone()[0] == "awaiting_approval"
    finally:
        with psycopg.connect(db.migrator_dsn) as conn:
            conn.execute("UPDATE resource_records SET url=%s WHERE project_id=%s AND resource_id=%s", (binding["resource_url"], base.project_id, binding["resource_id"]))


def test_review_conclusion_change_invalidates_basis_even_without_new_submission(db, scope):
    from app.domain.practice_submissions import CriterionCoverage, SubmissionDecisionCommand
    from app.infrastructure.db.practice_submissions import PgPracticeSubmissions
    base = published_base(db, scope, systematic=True)
    _, _, saved = saved_history(db, scope, base, accept=False)
    service = V2RevisionService(PgV2Revisions(db.app_dsn))
    assert service.context(scope=scope, project_id=base.project_id)["stages"][0]["learning_status"] == "started"
    draft = preview(service, scope, base).draft
    task = saved["submission"]["task_snapshot"]["task"]
    PgPracticeSubmissions(db.app_dsn).decide(scope, SubmissionDecisionCommand(base.project_id,
        saved["submission"]["submission_id"], "accepted", "明确人工核对", tuple(CriterionCoverage(i, (0,), "观察通过") for i in range(len(task["acceptance"]))),
        True, base.revision, saved["thread"]["task_version"], saved["thread"]["version"], "review-after-preview"))
    with pytest.raises(ConflictError) as error:
        service.confirm(scope=scope, project_id=base.project_id, draft_id=draft.draft_id,
            expected_version=1, draft_hash=draft.content_hash, idempotency_key="review-stale")
    assert error.value.details["reason"] == "revision_progress_stale"


@pytest.mark.parametrize("accepted", [False, True])
def test_two_local_revisions_keep_exact_started_or_completed_prefix_protected(db, scope, accepted):
    base = published_base(db, scope, systematic=True)
    saved_history(db, scope, base, accept=accepted)
    service = V2RevisionService(PgV2Revisions(db.app_dsn))
    current = base
    for index in range(2):
        d = service.preview_local(scope=scope, project_id=base.project_id, expected_version=current.revision,
            current_plan_id=current.plan_id, idempotency_key="continuation" + str(index),
            stage_edits=(LocalStageEdit(current.stages[-1].stage_id, what_to_learn="未来说明第" + str(index) + "次修订"),)).draft
        current = service.confirm(scope=scope, project_id=base.project_id, draft_id=d.draft_id,
            expected_version=current.revision, draft_hash=d.content_hash, idempotency_key="continue-confirm" + str(index)).plan
        context = service.context(scope=scope, project_id=base.project_id)
        assert context["stages"][0]["learning_status"] == "future"
        assert context["stages"][0]["historical_learning_status"] == ("completed" if accepted else "started")
        assert context["stages"][0]["protected"]
        history = current.v2_revision.user_content()["history"][0]
        assert history["source_plan_id"] == base.plan_id and history["source_revision"] == 1
        assert history["learning_status"] == ("completed" if accepted else "started")
        from app.infrastructure.db.workspace import PgWorkspaceReader
        workspace = PgWorkspaceReader(db.app_dsn).read(scope, base.project_id,
            [link.unit_id for link in current.unit_links], [link.task_id for link in current.task_links], plan_id=current.plan_id)
        old_ref = workspace["historical_learning_by_stage"][current.stages[0].stage_id]
        assert old_ref == {"source_plan_id": base.plan_id, "source_revision": 1,
            "source_stage_id": base.stages[0].stage_id, "learning_status": "completed" if accepted else "started"}
        assert not workspace["summary_stage_ids"] and not workspace["accepted_task_positions"]
        with pytest.raises(ValidationAppError):
            service.preview_local(scope=scope, project_id=base.project_id, expected_version=current.revision,
                current_plan_id=current.plan_id, idempotency_key="cannot-rewrite" + str(index),
                stage_edits=(LocalStageEdit(current.stages[0].stage_id, title="不得洗掉原历史保护"),))
