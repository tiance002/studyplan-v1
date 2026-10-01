"""Controlled ordinary publication in a fresh real PG database, no provider."""
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime

import psycopg
import pytest
from app.api.v1.resource_change_schemas import (
    ResourceCatalogView,
    ResourceChangePreviewView,
    ResourceChangeResultView,
)
from app.application.resource_changes import ResourceChangeService
from app.composition import build_container
from app.core.config import get_settings
from app.core.errors import AppError
from app.domain.enums import OutlineSectionKind, StageResourceRole, UnitProgress
from app.domain.learning_exposures import ExposureCommand
from app.domain.planning.models import PlanDraft, PlanPublicationService, PlanStage, PlanUnitLink
from app.domain.resource_changes import ResourceChangeCommand
from app.domain.resources.curation import StageResourceAssignment
from app.infrastructure.db import resource_changes
from app.infrastructure.db.learning_exposures import PgLearningExposures
from app.infrastructure.db.learning_resources import PgLearningResources
from app.infrastructure.db.plan_repository import PgPlanRepository
from app.infrastructure.db.resource_changes import PgResourceChanges

from tests.e2e.test_b2v_http_end_to_end import migrated_db as migrated_db

pytestmark = pytest.mark.postgres


@pytest.fixture
def scenario(migrated_db):
    settings = replace(get_settings(), database_url=migrated_db.app_dsn, llm_provider="fake",
                       planning_worker_admission_mode="trusted_server", local_session_token="")
    container = build_container(settings)
    from app.core.ids import new_id
    suffix = new_id("user")[-12:]
    token = container.browser_auth.register("变更用户" + suffix, "isolated resource replacement passphrase", "isolated-peer")
    scope = container.browser_auth.resolve(token)
    project = scope.learning_project_scope[0]
    unit, node = "unit-" + project, "node-" + project
    old, new = "src-old-" + project, "src-new-" + project
    now = datetime.now(UTC)
    with psycopg.connect(migrated_db.migrator_dsn) as conn:
        conn.execute("INSERT INTO knowledge_nodes(node_id,project_id,stable_key,title,node_type,source_status) "
                     "VALUES(%s,%s,'node.subject','Subject','concept','user_provided')", (node, project))
        conn.execute("INSERT INTO learning_units(unit_id,project_id,stable_key,title) VALUES(%s,%s,'unit.subject','Unit')",
                     (unit, project))
        conn.execute("INSERT INTO unit_node_links(link_id,project_id,unit_id,node_id,order_index,role) "
                     "VALUES(%s,%s,%s,%s,0,'primary')", ("link-" + project, project, unit, node))
        for source in (old, new):
            conn.execute("""INSERT INTO public_resource_sources(source_id,canonical_url,title,creator,media_type,
                language,source_version,verification_status,checked_at) VALUES(%s,'https://docs.python.org/3/',
                %s,'Synthetic isolated fixture','documentation','en',1,'reviewed',%s)""", (source, source, now))
            for key, index in (("a", 10), ("b", 30), ("c", 70)):
                conn.execute("""INSERT INTO public_resource_sections(section_id,source_id,order_index,title,url,
                    verification_status,checked_at,review_note) VALUES(%s,%s,%s,%s,'https://docs.python.org/3/',
                    'reviewed',%s,'isolated synthetic test index, not external verification')""",
                    (source + key, source, index, key, now))
    stage = PlanStage.create(stable_key="stage.subject", title="Subject", section_kind=OutlineSectionKind.CORE, order_index=0)
    assignment = StageResourceAssignment.create(project_id=project, stage_id=stage.stage_id,
        role=StageResourceRole.PRIMARY, source_ref=old, section_refs=(old + "a",), source_version=1, node_ids=(node,))
    draft = PlanDraft(new_id("drf"), project, "", "Controlled fixture", 1, stages=(stage,),
                      unit_links=(PlanUnitLink(stage.stage_id, unit, 0),), stage_resources=(assignment,))
    repo = PgPlanRepository(migrated_db.app_dsn)
    repo.save_draft(draft, expected_version=0)
    PlanPublicationService(repo).publish(draft=draft, presented_hash=draft.content_hash,
                                       expected_version=0, idempotency_key="initial-" + project)
    current = repo.get_current(project_id=project)
    command = ResourceChangeCommand(project, current.plan_id, current.stages[0].stage_id,
        current.stage_resources[0].assignment_id, new, 1, (new + "a", new + "b"), 1, "copy_active", "preview")
    return migrated_db, scope, command, container, current


def app(db):
    return ResourceChangeService(PgResourceChanges(db.app_dsn))


def confirm(service, scope, cmd, preview, key="confirm", **changes):
    return service.decide(scope, cmd.project_id, preview["proposal_id"], "confirm", cmd.expected_version,
                          preview["preview_hash"], key, acknowledge_warnings=True, **changes)


def test_preview_is_ordinary_pending_and_get_is_read_only(scenario):
    db, scope, cmd, _, current = scenario
    service = app(db)
    preview = service.preview(scope, cmd)
    ResourceChangePreviewView.model_validate(preview)
    assert preview["status"] == "pending" and preview["base_plan_id"] == current.plan_id
    assert preview["before"]["source_ref"] != preview["after"]["source_ref"]
    assert preview["impact"]["workload"]["delta_sections"] == 1
    assert preview["warnings"] and preview["impact"]["coverage"]["mapping_status"] == "missing"
    assert app(db).preview(scope, cmd) == preview
    assert app(db).get(scope, cmd.project_id, preview["proposal_id"]) == preview
    with psycopg.connect(db.migrator_dsn) as conn:
        assert conn.execute("SELECT run_id FROM plan_drafts WHERE draft_id=%s", (preview["draft_id"],)).fetchone() == (None,)
        assert conn.execute("SELECT count(*) FROM ai_runs WHERE project_id=%s", (cmd.project_id,)).fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM plan_revisions WHERE project_id=%s", (cmd.project_id,)).fetchone()[0] == 1


def test_confirm_is_atomic_new_version_preserves_old_progress_and_copies_private_lineage(scenario):
    db, scope, cmd, container, current = scenario
    service = app(db)
    position = dict(project_id=cmd.project_id, plan_id=cmd.plan_id, stage_id=cmd.stage_id, unit_id=current.unit_links[0].unit_id)
    old_progress = PgLearningExposures(db.app_dsn).change(scope,
        ExposureCommand(**position, status=UnitProgress.COMPLETED, expected_version=0, idempotency_key="old-progress"))
    selected = PgLearningResources(db.app_dsn).select(scope, position, {
        "resource_id": "private-" + cmd.project_id, "project_id": cmd.project_id,
        "url": "https://docs.python.org/3/library/uuid.html", "title": "Private binding",
        "media_type": "text", "language": "en", "provenance": "user_provided", "verification_status": "unverified",
        "source_version": 7})
    preview = service.preview(scope, cmd)
    assert preview["impact"]["progress"]["completed_units"] == 1
    assert preview["impact"]["private_bindings"]["copy_count"] == 1
    with pytest.raises(AppError) as exc:
        service.decide(scope, cmd.project_id, preview["proposal_id"], "confirm", 1, preview["preview_hash"], "unacknowledged")
    assert exc.value.http_status == 400
    result = confirm(service, scope, cmd, preview)
    ResourceChangeResultView.model_validate(result)
    assert result["created"] and result["revision"] == 2 and result["copied_selections"] == 1
    assert confirm(app(db), scope, cmd, preview) == result
    assert PgLearningExposures(db.app_dsn).history(scope, **position) == [old_progress["event"]]
    newer = PgPlanRepository(db.app_dsn).get_current(project_id=cmd.project_id)
    views = PgLearningExposures(db.app_dsn).list(scope, cmd.project_id, newer.plan_id)
    assert all((v["status"], v["version"], v["recorded"]) == ("not_started", 0, False) for v in views)
    assert newer.unit_links[0].unit_id == current.unit_links[0].unit_id
    assert newer.stages[0].stage_id != current.stages[0].stage_id
    with psycopg.connect(db.migrator_dsn) as conn:
        copied = conn.execute("SELECT resource_snapshot FROM learning_resource_selections WHERE project_id=%s AND plan_id=%s",
                              (cmd.project_id, newer.plan_id)).fetchone()[0]
        assert copied["verification_status"] == "unverified"
        assert copied["selection_copy_lineage"]["original_selection_id"] == selected["selection_id"]
        assert copied["selection_copy_lineage"]["original_source_version"] == 7
        assert conn.execute("SELECT count(*) FROM learning_resource_selections WHERE project_id=%s AND plan_id=%s AND removed_at IS NULL",
                            (cmd.project_id, current.plan_id)).fetchone()[0] == 1
        # Owner catalog edits after publication cannot rewrite confirmed metadata.
        conn.execute("UPDATE public_resource_sources SET title='Later catalog title' WHERE source_id=%s", (cmd.source_ref,))
        conn.execute("UPDATE public_resource_sections SET title='Later chapter',url='https://docs.python.org/3/later' WHERE section_id=%s",
                     (cmd.section_refs[0],))
    frozen = container.plan_service.get_current(scope=scope, project_id=cmd.project_id).resources[0]
    assert frozen.title == preview["after"]["source"]["title"] != "Later catalog title"
    assert frozen.ordered_sections[0].title == preview["after"]["sections"][0]["title"]
    assert frozen.ordered_sections[0].url == preview["after"]["sections"][0]["url"]


def test_generic_draft_routes_cannot_bypass_resource_preview_transaction(scenario):
    db, scope, cmd, _, _ = scenario
    preview = app(db).preview(scope, cmd)
    repo = PgPlanRepository(db.app_dsn)
    draft = repo.get_draft(project_id=cmd.project_id, draft_id=preview["draft_id"])
    for action in (lambda: repo.save_draft(draft, expected_hash=draft.content_hash),
                   lambda: repo.cancel_draft(project_id=cmd.project_id, draft_id=draft.draft_id),
                   lambda: PlanPublicationService(repo).publish(draft=draft, presented_hash=draft.content_hash,
                        expected_version=1, idempotency_key="bypass")):
        with pytest.raises(AppError) as exc:
            action()
        assert exc.value.http_status == 409
    assert app(db).get(scope, cmd.project_id, preview["proposal_id"])["status"] == "pending"


def test_duplicate_and_heterogeneous_keys_and_confirm_cancel_race(scenario):
    db, scope, cmd, _, _ = scenario
    service = app(db)
    preview = service.preview(scope, cmd)
    with pytest.raises(AppError) as exc:
        service.preview(scope, replace(cmd, copy_policy="keep_history_only"))
    assert exc.value.http_status == 409
    def attempt(action):
        try:
            return service.decide(scope, cmd.project_id, preview["proposal_id"], action, 1,
                                  preview["preview_hash"], "race-" + action, True)["status"]
        except AppError as exc:
            return exc.http_status
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(attempt, ("confirm", "cancel")))
    assert sum(isinstance(item, str) for item in outcomes) == 1 and outcomes.count(409) == 1
    with pytest.raises(AppError) as exc:
        service.decide(scope, cmd.project_id, preview["proposal_id"], "cancel", 1, preview["preview_hash"], "preview", True)
    assert exc.value.http_status == 409


def test_two_previews_cas_and_receipt_survives_subsequent_plan(scenario):
    db, scope, cmd, _, _ = scenario
    service = app(db)
    one = service.preview(scope, cmd)
    second_cmd = replace(cmd, section_refs=(cmd.source_ref + "b", cmd.source_ref + "c"), idempotency_key="preview-2")
    two = service.preview(scope, second_cmd)
    def attempt(pair):
        command, preview = pair
        try:
            return confirm(service, scope, command, preview, "confirm-" + preview["proposal_id"])
        except AppError as exc:
            return exc.http_status
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(attempt, ((cmd, one), (second_cmd, two))))
    assert sum(isinstance(item, dict) for item in outcomes) == 1 and outcomes.count(409) == 1
    winner = next(item for item in outcomes if isinstance(item, dict))
    preview = one if winner["proposal_id"] == one["proposal_id"] else two
    winner_cmd = cmd if preview is one else second_cmd
    newer = PgPlanRepository(db.app_dsn).get_current(project_id=cmd.project_id)
    third_cmd = replace(cmd, plan_id=newer.plan_id, stage_id=newer.stages[0].stage_id,
                        assignment_id=newer.stage_resources[0].assignment_id,
                        section_refs=(cmd.source_ref + "c",), expected_version=2, idempotency_key="preview-3")
    third = service.preview(scope, third_cmd)
    assert confirm(service, scope, third_cmd, third, "confirm-third")["revision"] == 3
    assert confirm(app(db), scope, winner_cmd, preview, "confirm-" + preview["proposal_id"]) == winner


@pytest.mark.parametrize("change", ["insert", "metadata", "version"])
def test_catalog_index_changes_after_preview_require_new_preview(scenario, change):
    db, scope, cmd, _, _ = scenario
    service = app(db)
    preview = service.preview(scope, cmd)
    with psycopg.connect(db.migrator_dsn) as conn:
        if change == "insert":
            conn.execute("INSERT INTO public_resource_sections(section_id,source_id,order_index,title,url) "
                         "VALUES(%s,%s,20,'Inserted chapter','https://docs.python.org/3/')", (cmd.source_ref + "new", cmd.source_ref))
        elif change == "metadata":
            conn.execute("UPDATE public_resource_sources SET title='Changed' WHERE source_id=%s", (cmd.source_ref,))
        else:
            conn.execute("UPDATE public_resource_sources SET source_version=2 WHERE source_id=%s", (cmd.source_ref,))
    with pytest.raises(AppError) as exc:
        confirm(service, scope, cmd, preview)
    assert exc.value.http_status == 409
    assert PgPlanRepository(db.app_dsn).get_current(project_id=cmd.project_id).version == 1
    assert service.get(scope, cmd.project_id, preview["proposal_id"])["status"] == "pending"


def test_changed_assignment_cannot_keep_stale_frozen_snapshot(scenario):
    db, _, cmd, _, current = scenario
    from app.core.ids import new_id
    repo = PgPlanRepository(db.app_dsn)
    for updates in ({"source_ref": cmd.source_ref}, {"source_version": 2},
                    {"section_refs": (current.stage_resources[0].source_ref + "b",)}):
        assignments = (replace(current.stage_resources[0], **updates),)
        draft = PlanDraft(new_id("drf"), cmd.project_id, "", current.goal_snapshot, 2,
            stages=current.stages, unit_links=current.unit_links, stage_resources=assignments,
            resource_snapshots=current.resource_snapshots)
        with pytest.raises(AppError) as exc:
            repo.save_draft(draft)
        assert exc.value.http_status == 400
        assert repo.get_draft(project_id=cmd.project_id, draft_id=draft.draft_id) is None
    assert PgPlanRepository(db.app_dsn).get_current(project_id=cmd.project_id).version == 1


def test_history_only_is_explicit_and_does_not_copy_private_bindings(scenario):
    db, scope, cmd, _, current = scenario
    position = dict(project_id=cmd.project_id, plan_id=cmd.plan_id, stage_id=cmd.stage_id, unit_id=current.unit_links[0].unit_id)
    selected = PgLearningResources(db.app_dsn).select(scope, position, {"resource_id": "private-" + cmd.project_id,
        "project_id": cmd.project_id, "url": "https://docs.python.org/3/library/typing.html", "title": "Private",
        "media_type": "text", "language": "en", "provenance": "user_provided", "verification_status": "unverified"})
    cmd = replace(cmd, copy_policy="keep_history_only")
    service = app(db)
    preview = service.preview(scope, cmd)
    assert preview["impact"]["private_bindings"] == {"policy": "keep_history_only", "active_count": 1,
                                                    "copy_count": 0, "history_retained": True}
    result = confirm(service, scope, cmd, preview)
    assert result["copied_selections"] == 0
    assert PgLearningResources(db.app_dsn).list_selected(scope, position) == [selected]
    with psycopg.connect(db.migrator_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM learning_resource_selections WHERE plan_id=%s", (result["plan_id"],)).fetchone()[0] == 0


def test_failed_receipt_rolls_back_publication_and_releases_catalog_lock(scenario, monkeypatch):
    db, scope, cmd, _, current = scenario
    service = app(db)
    preview = service.preview(scope, cmd)
    original = PgResourceChanges._save_receipt
    def fail_receipt(conn, scope, project, key, action, fingerprint, response):
        if action == "confirm":
            raise RuntimeError("isolated receipt failpoint")
        original(conn, scope, project, key, action, fingerprint, response)
    monkeypatch.setattr(PgResourceChanges, "_save_receipt", staticmethod(fail_receipt))
    with pytest.raises(RuntimeError, match="receipt failpoint"):
        confirm(service, scope, cmd, preview)
    with psycopg.connect(db.migrator_dsn) as conn:
        conn.execute("SET LOCAL lock_timeout='1s'")
        # This needs the source row lock too; succeeding proves rollback freed it.
        conn.execute("UPDATE public_resource_sources SET title=title WHERE source_id=%s", (cmd.source_ref,))
        assert conn.execute("SELECT count(*) FROM plan_revisions WHERE project_id=%s", (cmd.project_id,)).fetchone()[0] == 1
        assert conn.execute("SELECT status FROM plan_drafts WHERE draft_id=%s", (preview["draft_id"],)).fetchone() == ("awaiting_approval",)
        assert conn.execute("SELECT status FROM resource_change_proposals WHERE proposal_id=%s", (preview["proposal_id"],)).fetchone() == ("pending",)
        assert conn.execute("SELECT count(*) FROM resource_change_receipts WHERE project_id=%s AND action='confirm'",
                            (cmd.project_id,)).fetchone()[0] == 0
    assert PgPlanRepository(db.app_dsn).get_current(project_id=cmd.project_id).plan_id == current.plan_id


def test_reviewed_catalog_and_exact_scope_adjacency_are_enforced(scenario):
    db, scope, cmd, _, _ = scenario
    service = app(db)
    indexes = service.catalog(scope, cmd.project_id)
    assert len(indexes) <= 100
    for index in indexes:
        ResourceCatalogView.model_validate(index)
        assert index["source"]["verification_status"] == "reviewed" and len(index["sections"]) <= 300
    for invalid in (replace(cmd, section_refs=(cmd.source_ref + "a", cmd.source_ref + "c")),
                    replace(cmd, section_refs=tuple(reversed(cmd.section_refs))),
                    replace(cmd, source_ref="manual-private-unreviewed-source")):
        with pytest.raises(AppError) as exc:
            service.preview(scope, invalid)
        assert exc.value.http_status == 400
    for invalid in (replace(cmd, expected_version=2), replace(cmd, stage_id="another-stage")):
        with pytest.raises(AppError) as exc:
            service.preview(scope, invalid)
        assert exc.value.http_status in {404, 409}
    with pytest.raises(AppError) as exc:
        service.preview(replace(scope, actor_id="forged-actor"), cmd)
    assert exc.value.http_status == 403


@pytest.mark.parametrize("drift", ["add", "remove", "replace"])
def test_private_binding_drift_cannot_change_confirmed_copy_set(scenario, drift):
    db, scope, cmd, _, current = scenario
    resources = PgLearningResources(db.app_dsn)
    position = dict(project_id=cmd.project_id, plan_id=cmd.plan_id, stage_id=cmd.stage_id, unit_id=current.unit_links[0].unit_id)
    def select(suffix):
        return resources.select(scope, position, {"resource_id": "private-" + suffix + cmd.project_id,
            "project_id": cmd.project_id, "url": "https://docs.python.org/3/library/" + suffix + ".html",
            "title": suffix, "media_type": "text", "language": "en", "provenance": "user_provided",
            "verification_status": "unverified"})
    first = select("uuid") if drift != "add" else None
    service = app(db)
    preview = service.preview(scope, cmd)
    if first:
        resources.remove(scope, position, first["selection_id"])
    if drift != "remove":
        select("typing")
    with pytest.raises(AppError) as exc:
        confirm(service, scope, cmd, preview)
    assert exc.value.http_status == 409
    assert PgPlanRepository(db.app_dsn).get_current(project_id=cmd.project_id).version == 1
    assert service.get(scope, cmd.project_id, preview["proposal_id"])["status"] == "pending"


def test_catalog_wait_past_worker_expiry_rejects_draft_write(scenario, monkeypatch):
    db, scope, cmd, _, current = scenario
    from app.core.ids import new_id
    from app.domain.enums import AiRunNextAction, AiRunStatus
    from app.domain.runs.fencing import PlanningWriteFence
    from app.domain.runs.models import RunRecord
    from app.infrastructure.db.run_repository import PgRunRepository
    from app.ports.planning_jobs import PlanningLeaseLostError

    run = RunRecord(run_id=new_id("run"), project_id=cmd.project_id, actor_id=scope.actor_id,
        kind="plan_generate", graph_name="planning", graph_version="b3f2-short-v2", thread_id=new_id("thread"),
        status=AiRunStatus.RUNNING, next_action=AiRunNextAction.WAIT)
    PgRunRepository(db.app_dsn).create_run(run)
    job = new_id("job")
    with psycopg.connect(db.migrator_dsn) as conn:
        expiry = conn.execute("""INSERT INTO ai_jobs(job_id,run_id,job_key,status,lease_token,lease_expires_at)
            VALUES(%s,%s,%s,'running','source-expiry',clock_timestamp()+interval '2 seconds') RETURNING lease_expires_at""",
            (job, run.run_id, job)).fetchone()[0]
    fence = PlanningWriteFence(job, run.run_id, cmd.project_id, scope.actor_id, "source-expiry")
    draft = PlanDraft(new_id("drf"), cmd.project_id, run.run_id, current.goal_snapshot, 2,
        stages=current.stages, unit_links=current.unit_links, stage_resources=current.stage_resources)
    reached = threading.Event()
    original = resource_changes.capture_resource_snapshots
    def observed_capture(*args):
        reached.set()
        return original(*args)
    monkeypatch.setattr(resource_changes, "capture_resource_snapshots", observed_capture)
    with ThreadPoolExecutor(max_workers=1) as pool:
        with psycopg.connect(db.migrator_dsn) as holder:
            holder.execute("SELECT source_id FROM public_resource_sources WHERE source_id=%s FOR UPDATE",
                           (current.stage_resources[0].source_ref,))
            future = pool.submit(PgPlanRepository(db.app_dsn).save_draft, draft, expected_version=1, write_fence=fence)
            assert reached.wait(5), "Initial live fence must pass before source capture blocks"
            with psycopg.connect(db.migrator_dsn, autocommit=True) as observer:
                deadline = time.monotonic()+5
                while time.monotonic() < deadline:
                    waiting = observer.execute("SELECT count(*) FROM pg_locks l JOIN pg_stat_activity a USING(pid) "
                        "WHERE a.datname=current_database() AND NOT l.granted AND l.locktype='transactionid'").fetchone()[0]
                    if waiting:
                        break
                    time.sleep(0.02)
                else:
                    pytest.fail("Snapshot did not demonstrably wait on the source row")
                while observer.execute("SELECT clock_timestamp() < %s", (expiry,)).fetchone()[0]:
                    time.sleep(0.02)
                assert not future.done()
        with pytest.raises(PlanningLeaseLostError):
            future.result(timeout=5)
    assert PgPlanRepository(db.app_dsn).get_draft(project_id=cmd.project_id, draft_id=draft.draft_id) is None


def test_catalog_lock_blocks_insert_during_confirm_and_preserves_select_only_role(scenario, monkeypatch):
    db, scope, cmd, _, _ = scenario
    service = app(db)
    preview = service.preview(scope, cmd)
    with psycopg.connect(db.app_dsn) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            with conn.transaction():
                conn.execute("UPDATE public_resource_sources SET title='forbidden' WHERE source_id=%s", (cmd.source_ref,))
        assert conn.execute("SELECT public.lock_reviewed_resource_index(NULL)").fetchone() == (False,)
        assert conn.execute("SELECT public.lock_reviewed_resource_index(%s)", ("x" * 513,)).fetchone() == (False,)
        assert conn.execute("SELECT public.lock_reviewed_resource_index('unknown')").fetchone() == (False,)
    reached = threading.Event()
    release = threading.Event()
    original = resource_changes.PlanPublicationService.publish
    def paused_publish(self, **kwargs):
        reached.set()
        assert release.wait(5)
        return original(self, **kwargs)
    monkeypatch.setattr(resource_changes.PlanPublicationService, "publish", paused_publish)
    def insert():
        with psycopg.connect(db.migrator_dsn) as conn:
            conn.execute("INSERT INTO public_resource_sections(section_id,source_id,order_index,title,url) "
                "VALUES(%s,%s,20,'Insert after confirm','https://docs.python.org/3/')", (cmd.source_ref + "queued", cmd.source_ref))
    with ThreadPoolExecutor(max_workers=2) as pool:
        confirming = pool.submit(confirm, service, scope, cmd, preview)
        assert reached.wait(5)
        inserting = pool.submit(insert)
        try:
            deadline = time.monotonic()+5
            with psycopg.connect(db.migrator_dsn, autocommit=True) as observer:
                while time.monotonic() < deadline:
                    waiting = observer.execute("SELECT count(*) FROM pg_locks l JOIN pg_stat_activity a USING(pid) "
                        "WHERE a.datname=current_database() AND NOT l.granted AND l.locktype='transactionid'").fetchone()[0]
                    if waiting:
                        break
                    time.sleep(0.02)
                else:
                    pytest.fail("Chapter FK insertion did not demonstrably wait behind confirmation source lock")
            assert not inserting.done()
        finally:
            release.set()
        assert confirming.result(timeout=5)["revision"] == 2
        inserting.result(timeout=5)
