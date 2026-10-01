"""Actual isolated PG assertions for position-bound self-reported progress."""
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import psycopg
import pytest
from app.api.v1.exposure_schemas import ExposureChangeView
from app.application.learning_exposures import LearningExposureService
from app.core.errors import AppError
from app.core.ids import new_id
from app.domain.enums import UnitProgress
from app.domain.learning_exposures import ExposureCommand
from app.infrastructure.db.learning_exposures import PgLearningExposures
from app.infrastructure.db.learning_resources import PgLearningResources
from app.infrastructure.db.planning_fence import lock_plan_version

from tests.e2e.test_b2v_http_end_to_end import migrated_db as migrated_db
from tests.integration.test_learning_resources_pg import scenario as scenario

pytestmark = pytest.mark.postgres


@pytest.fixture(autouse=True)
def clean_exposures(scenario):
    db, _, target = scenario
    with psycopg.connect(db.migrator_dsn) as conn:
        # Only the harness-created studyplan_test_* database is modified.
        conn.execute("TRUNCATE learning_exposure_events,learning_exposures")
        conn.execute("UPDATE plan_revisions SET status='superseded' WHERE project_id=%s AND plan_id<>%s",
                     (target["project_id"], target["plan_id"]))
        conn.execute("UPDATE plan_revisions SET status='approved' WHERE plan_id=%s", (target["plan_id"],))


def service(db):
    return LearningExposureService(PgLearningExposures(db.app_dsn))


def command(target, key, status=UnitProgress.IN_PROGRESS, expected_version=0):
    return ExposureCommand(**target, status=status, expected_version=expected_version, idempotency_key=key)


def test_virtual_get_has_no_writes_and_ignores_global_legacy_progress(scenario):
    db, scope, target = scenario
    with psycopg.connect(db.migrator_dsn) as conn:
        legacy = conn.execute("INSERT INTO unit_progress(project_id,unit_id,status,version) "
                              "VALUES(%s,%s,'completed',7) ON CONFLICT(project_id,unit_id) "
                              "DO UPDATE SET status='completed' RETURNING status",
                              (target["project_id"], target["unit_id"])).fetchone()
        assert legacy == ("completed",)
        before = conn.execute("SELECT count(*) FROM learning_exposures").fetchone()[0]
    views = service(db).list(scope, target["project_id"], target["plan_id"])
    found = next(v for v in views if v["unit_id"] == target["unit_id"])
    assert (found["status"], found["version"], found["recorded"]) == ("not_started", 0, False)
    assert found["node_snapshot"]
    with psycopg.connect(db.migrator_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM learning_exposures").fetchone()[0] == before
        assert conn.execute("SELECT count(*) FROM learning_exposure_events").fetchone()[0] == 0


def test_idempotency_and_cas_are_one_persistent_operation(scenario):
    db, scope, target = scenario
    app = service(db)
    cmd = command(target, "exposure-start")
    first = app.change(scope, cmd)
    ExposureChangeView.model_validate(first)
    assert first["exposure"]["version"] == 1
    replay = service(db).change(scope, cmd)
    assert replay["exposure"] == first["exposure"] and replay["event"] == first["event"]
    assert replay["replayed"]
    for changed in (replace(cmd, status=UnitProgress.SKIPPED), replace(cmd, expected_version=1)):
        with pytest.raises(AppError) as exc:
            app.change(scope, changed)
        assert exc.value.http_status == 409
    def attempt(status):
        try:
            return app.change(scope, command(target, "race-" + status.value, status, 1))["exposure"]["version"]
        except AppError as exc:
            return exc.http_status
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(attempt, (UnitProgress.COMPLETED, UnitProgress.SKIPPED))) == [2, 409]
    assert len(app.history(scope, **target)) == 2


def test_owner_scope_and_position_validation_are_fail_closed(scenario):
    db, scope, target = scenario
    forged = replace(scope, actor_id="forged-other-actor")
    missing_scope = replace(scope, learning_project_scope=())
    app = service(db)
    app.change(scope, command(target, "owner-visible"))
    for bad in (forged, missing_scope):
        for action in (lambda bad=bad: app.list(bad, target["project_id"], target["plan_id"]),
                       lambda bad=bad: app.change(bad, command(target, "forged")),
                       lambda bad=bad: app.history(bad, **target)):
            with pytest.raises(AppError) as exc:
                action()
            assert exc.value.http_status == 403
    for field in ("plan_id", "stage_id", "unit_id"):
        with pytest.raises(AppError) as exc:
            app.change(scope, command(dict(target, **{field: "wrong-" + field}), field))
        assert exc.value.http_status == 404
    with psycopg.connect(db.app_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM learning_exposures").fetchone()[0] == 0
        conn.execute("SELECT set_config('app.project_id',%s,true),set_config('app.actor_id','forged',true)",
                     (target["project_id"],))
        assert conn.execute("SELECT count(*) FROM learning_exposure_events").fetchone()[0] == 0
        conn.execute("SELECT set_config('app.actor_id',%s,true)", (scope.actor_id,))
        assert conn.execute("SELECT count(*) FROM learning_exposures").fetchone()[0] == 1
        assert conn.execute("SELECT count(*) FROM learning_exposure_events").fetchone()[0] == 1


def test_concurrent_same_key_returns_same_receipt_once(scenario):
    db, scope, target = scenario
    app = service(db)
    cmd = command(target, "concurrent-identical")
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: app.change(scope, cmd), range(2)))
    assert results[0]["event"] == results[1]["event"]
    assert results[0]["exposure"] == results[1]["exposure"]
    assert sorted(item["replayed"] for item in results) == [False, True]
    assert len(app.history(scope, **target)) == 1


def test_existing_stage_with_wrong_unit_is_rejected(scenario):
    db, scope, target = scenario
    stage = new_id("stage")
    with psycopg.connect(db.migrator_dsn) as conn:
        conn.execute("""INSERT INTO plan_stages(stage_id,project_id,plan_id,stable_key,title,order_index,
            section_kind,objective) SELECT %s,project_id,plan_id,%s,title,
            (SELECT max(order_index)+1 FROM plan_stages WHERE plan_id=%s),section_kind,objective
            FROM plan_stages WHERE stage_id=%s""", (stage, stage, target["plan_id"], target["stage_id"]))
    with pytest.raises(AppError) as exc:
        service(db).change(scope, command(dict(target, stage_id=stage), "existing-wrong-stage"))
    assert exc.value.http_status == 404


def test_same_node_in_long_id_second_unit_is_independent(scenario):
    db, scope, target = scenario
    unit = "unit-" + "u" * 400
    with psycopg.connect(db.migrator_dsn) as conn:
        conn.execute("""INSERT INTO learning_units(unit_id,project_id,stable_key,title,rubric,objectives)
            SELECT %s,project_id,'exposure-second-position','Second occurrence',rubric,objectives
            FROM learning_units WHERE unit_id=%s ON CONFLICT DO NOTHING""", (unit, target["unit_id"]))
        conn.execute("""INSERT INTO unit_node_links(link_id,project_id,unit_id,node_id,order_index,role)
            SELECT %s||node_id,project_id,%s,node_id,order_index,role FROM unit_node_links WHERE unit_id=%s
            ON CONFLICT DO NOTHING""", ("exposure-copy-", unit, target["unit_id"]))
        conn.execute("""INSERT INTO plan_unit_links(link_id,project_id,plan_id,stage_id,unit_id,order_index)
            VALUES('exposure-second-link',%s,%s,%s,%s,1000) ON CONFLICT DO NOTHING""",
            (target["project_id"], target["plan_id"], target["stage_id"], unit))
    app = service(db)
    first = app.change(scope, command(target, "complete-first", UnitProgress.COMPLETED))
    second = dict(target, unit_id=unit)
    virtual = next(v for v in app.list(scope, target["project_id"], target["plan_id"]) if v["unit_id"] == unit)
    assert virtual["node_snapshot"] == first["exposure"]["node_snapshot"]
    assert (virtual["status"], virtual["version"]) == ("not_started", 0)
    assert virtual["exposure_id"] != first["exposure"]["exposure_id"]
    skipped = app.change(scope, command(second, "skip-second", UnitProgress.SKIPPED))
    assert skipped["exposure"]["status"] == "skipped"
    returned = app.change(scope, command(second, "return-second", UnitProgress.IN_PROGRESS, 1))
    assert returned["event"]["from_status"] == "skipped"
    app.change(scope, command(second, "complete-second", UnitProgress.COMPLETED, 2))
    assert len(app.history(scope, **target)) == 1 and len(app.history(scope, **second)) == 3


def next_plan(conn, target):
    plan, stage = new_id("plan"), new_id("stage")
    conn.execute("""INSERT INTO plan_revisions(plan_id,project_id,revision,goal_snapshot,status,structure,
        source_pack_key,source_pack_version) SELECT %s,project_id,(SELECT max(revision)+1 FROM plan_revisions
        WHERE project_id=%s),goal_snapshot,'superseded',structure,source_pack_key,source_pack_version
        FROM plan_revisions WHERE plan_id=%s""", (plan, target["project_id"], target["plan_id"]))
    conn.execute("""INSERT INTO plan_stages(stage_id,project_id,plan_id,stable_key,title,order_index,
        section_kind,objective) SELECT %s,project_id,%s,stable_key,title,order_index,section_kind,objective
        FROM plan_stages WHERE stage_id=%s""", (stage, plan, target["stage_id"]))
    conn.execute("""INSERT INTO plan_unit_links(link_id,project_id,plan_id,stage_id,unit_id,order_index)
        VALUES(%s,%s,%s,%s,%s,0)""", (new_id("link"), target["project_id"], plan, stage, target["unit_id"]))
    return dict(target, plan_id=plan, stage_id=stage)


def test_old_version_history_is_readable_without_progress_propagation(scenario):
    db, scope, target = scenario
    app = service(db)
    original = app.change(scope, command(target, "old-complete", UnitProgress.COMPLETED))
    with psycopg.connect(db.migrator_dsn) as conn:
        newer = next_plan(conn, target)
        conn.execute("UPDATE plan_revisions SET status='superseded' WHERE plan_id=%s", (target["plan_id"],))
        conn.execute("UPDATE plan_revisions SET status='approved' WHERE plan_id=%s", (newer["plan_id"],))
    assert app.history(scope, **target) == [original["event"]]
    assert app.list(scope, target["project_id"], target["plan_id"])[0]["recorded"]
    virtual = app.list(scope, newer["project_id"], newer["plan_id"])[0]
    assert (virtual["status"], virtual["version"], virtual["recorded"]) == ("not_started", 0, False)
    assert app.history(scope, **newer) == []
    replay = app.change(scope, command(target, "old-complete", UnitProgress.COMPLETED))
    assert replay == dict(original, replayed=True)
    assert app.history(scope, **target) == [original["event"]]
    with pytest.raises(AppError) as exc:
        app.change(scope, command(target, "late-old", UnitProgress.IN_PROGRESS, 1))
    assert exc.value.http_status == 409
    app.change(scope, command(newer, "new-start"))
    assert app.history(scope, **target) == [original["event"]]


def test_waited_publication_rechecks_current_plan_before_write(scenario):
    db, scope, target = scenario
    with psycopg.connect(db.migrator_dsn) as setup:
        newer = next_plan(setup, target)
    with ThreadPoolExecutor(max_workers=1) as pool:
        with psycopg.connect(db.migrator_dsn) as publication:
            lock_plan_version(publication, target["project_id"], None)
            future = pool.submit(service(db).change, scope, command(target, "waited-publication"))
            deadline = time.monotonic() + 5
            with psycopg.connect(db.migrator_dsn, autocommit=True) as observer:
                while time.monotonic() < deadline:
                    waiting = observer.execute("SELECT count(*) FROM pg_locks l JOIN pg_stat_activity a USING(pid) "
                        "WHERE a.datname=current_database() AND l.locktype='advisory' AND NOT l.granted").fetchone()[0]
                    if waiting:
                        break
                    time.sleep(0.02)
                else:
                    pytest.fail("Exposure did not demonstrably wait on publication advisory lock")
            publication.execute("UPDATE plan_revisions SET status='superseded' WHERE plan_id=%s", (target["plan_id"],))
            publication.execute("UPDATE plan_revisions SET status='approved' WHERE plan_id=%s", (newer["plan_id"],))
        with pytest.raises(AppError) as exc:
            future.result(timeout=5)
        assert exc.value.http_status == 409
    assert service(db).history(scope, **target) == []


def test_each_operation_snapshots_bindings_and_history_is_immutable(scenario, monkeypatch):
    db, scope, target = scenario
    app = service(db)
    first = app.change(scope, command(target, "snapshot-before"))
    resource = {"resource_id": new_id("res"), "project_id": target["project_id"],
                "url": "https://docs.python.org/3/library/uuid.html", "title": "UUID reference",
                "media_type": "text", "language": "en", "provenance": "user_provided",
                "verification_status": "unverified", "checked_at": None}
    selected = PgLearningResources(db.app_dsn).select(scope, target, resource)
    second = app.change(scope, command(target, "snapshot-after", UnitProgress.COMPLETED, 1))
    assert selected["selection_id"] in {item["selection_id"] for item in second["event"]["source_snapshot"]["private_selections"]}
    assert selected["selection_id"] not in {item["selection_id"] for item in first["event"]["source_snapshot"]["private_selections"]}
    PgLearningResources(db.app_dsn).remove(scope, target, selected["selection_id"])
    assert app.history(scope, **target) == [first["event"], second["event"]]
    with psycopg.connect(db.migrator_dsn) as conn:
        with pytest.raises(psycopg.errors.RaiseException):
            with conn.transaction():
                conn.execute("UPDATE learning_exposure_events SET from_status='skipped' WHERE event_id=%s",
                             (first["event"]["event_id"],))
    # A failed event insertion must roll back the current-state update too.
    monkeypatch.setattr("app.infrastructure.db.learning_exposures.new_id", lambda _: first["event"]["event_id"])
    with pytest.raises(psycopg.errors.UniqueViolation):
        app.change(scope, command(target, "atomic-fail", UnitProgress.IN_PROGRESS, 2))
    persisted = next(v for v in app.list(scope, target["project_id"], target["plan_id"]) if v["unit_id"] == target["unit_id"])
    assert persisted == second["exposure"]
    assert app.history(scope, **target) == [first["event"], second["event"]]
