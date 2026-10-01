"""Persistent scoped settings, CAS and restore-inheritance on owned test PG."""

import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

import psycopg
import pytest
from app.application.plan_service import DecisionCommand
from app.application.resource_preferences import ResourcePreferenceService
from app.composition import build_container
from app.core.config import get_settings
from app.core.errors import AppError, ConflictError, ValidationAppError
from app.domain.enums import DraftDecision, PreferenceScope
from app.infrastructure.db.resource_preferences import PgResourcePreferences
from app.infrastructure.domain_pack import load_pack
from app.tools.seed_b3 import seed_reviewed_pack

from tests.e2e.test_b2v_http_end_to_end import migrated_db as migrated_db

pytestmark = pytest.mark.postgres


@pytest.fixture(scope="module")
def preference_scenario(migrated_db):
    with psycopg.connect(migrated_db.migrator_dsn) as conn:
        seed_reviewed_pack(conn, load_pack("agent-application-v3.json"))
    container = build_container(replace(get_settings(), database_url=migrated_db.app_dsn, llm_provider="fake",
        local_session_token="", planning_worker_admission_mode="trusted_server"))
    token = container.browser_auth.register("资料偏好用户", "long preference test passphrase", "preference-peer")
    scope = container.browser_auth.resolve(token)
    project = scope.learning_project_scope[0]
    run_id = container.plan_service.submit_generation(scope=scope, project_id=project, goal="学习Agent应用开发")
    assert container.planning_worker.tick()
    finished = container.plan_service.get_run(scope=scope, project_id=project, run_id=run_id)
    draft = container.plan_service.get_draft(scope=scope, project_id=project, draft_id=finished.run.result_ref).draft
    published = container.plan_service.decide(scope=scope, project_id=project, draft_id=draft.draft_id,
        command=DecisionCommand(DraftDecision.APPROVE, 0, draft.content_hash, "preference-publish"))
    plan = published.plan
    targets = [{"project_id": project, "plan_id": plan.plan_id, "stage_id": link.stage_id,
                "unit_id": link.unit_id, "node_id": None} for link in plan.unit_links[:2]]
    with psycopg.connect(migrated_db.migrator_dsn) as conn:
        nodes = conn.execute("SELECT node_id FROM unit_node_links WHERE project_id=%s AND unit_id=%s ORDER BY node_id",
                            (project, targets[0]["unit_id"])).fetchall()
    assert len(targets) == 2 and nodes
    targets.append(dict(targets[0], node_id=nodes[0][0]))
    other_token = container.browser_auth.register("资料偏好另一用户", "long other preference passphrase", "other-peer")
    other = container.browser_auth.resolve(other_token)
    return migrated_db, scope, targets, other


@pytest.fixture()
def preferences(preference_scenario):
    db, scope, targets, other = preference_scenario
    with psycopg.connect(db.migrator_dsn) as conn:
        conn.execute("TRUNCATE preferences, preference_overrides")
    service = ResourcePreferenceService(PgResourcePreferences(db.app_dsn))
    return db, service, scope, targets, other


def put(service, scope, target, scope_name, version, **values):
    return service.put(scope, target, scope_name=scope_name, mode=values.get("mode", "video_first"),
        language=values.get("language", "en"), official_priority=False, pace="fast", expected_version=version)


def test_project_unit_node_precedence_and_other_locations_unchanged(preferences):
    db, service, scope, targets, other = preferences
    first, second, node = targets
    put(service, scope, first, "project", 0, mode="text_first", language="zh")
    put(service, scope, first, "unit", 0)
    node_context = put(service, scope, node, "node", 0, mode="mixed", language="fr")
    assert node_context["effective"]["scope"] == PreferenceScope.NODE
    assert node_context["effective"]["language"] == "fr"
    assert service.get_context(scope, first)["effective"]["language"] == "en"
    assert service.get_context(scope, second)["effective"]["language"] == "zh"
    assert service.project_default(other, other.learning_project_scope[0]).scope == PreferenceScope.SYSTEM
    assert service.project_default(scope, first["project_id"]).language == "zh"
    with psycopg.connect(db.app_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM preferences").fetchone()[0] == 0


def test_restore_inheritance_cas_and_aba_version_never_reused(preferences):
    _, service, scope, targets, _ = preferences
    target = targets[0]
    put(service, scope, target, "project", 0, language="zh")
    first = put(service, scope, target, "unit", 0)
    assert first["versions"]["unit"] == 1
    inherited = service.restore(scope, target, scope_name="unit", expected_version=1)
    assert inherited["unit"] is None and inherited["inherited"]
    assert inherited["versions"]["unit"] == 2
    assert inherited["effective"]["language"] == "zh"
    with pytest.raises(ConflictError):
        put(service, scope, target, "unit", 0, language="de")
    replaced = put(service, scope, target, "unit", 2, language="fr")
    assert replaced["versions"]["unit"] == 3
    with pytest.raises(ConflictError):
        service.restore(scope, target, scope_name="unit", expected_version=1)
    with pytest.raises(ConflictError):
        put(service, scope, target, "unit", 1, language="de")
    assert service.get_context(scope, target)["unit"]["language"] == "fr"


def test_concurrent_cas_updates_have_one_winner(preferences):
    _, service, scope, targets, _ = preferences
    target = targets[0]
    put(service, scope, target, "unit", 0)

    def update(language):
        try:
            return put(service, scope, target, "unit", 1, language=language)["unit"]["language"]
        except ConflictError:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(update, ("fr", "de")))
    assert outcomes.count("conflict") == 1
    current = service.get_context(scope, target)
    assert current["versions"]["unit"] == 2
    assert current["unit"]["language"] in {"fr", "de"}


def test_cross_actor_wrong_unit_node_and_system_write_rejected(preferences):
    db, service, scope, targets, other = preferences
    target = targets[0]
    with psycopg.connect(db.migrator_dsn) as conn:
        foreign_node = conn.execute("""SELECT node_id FROM unit_node_links WHERE project_id=%s
            AND node_id NOT IN (SELECT node_id FROM unit_node_links WHERE project_id=%s AND unit_id=%s)
            LIMIT 1""", (target["project_id"], target["project_id"], target["unit_id"])).fetchone()
    assert foreign_node is not None
    spoofed = replace(other, learning_project_scope=(target["project_id"],))
    for bad_scope, bad_target in [(spoofed, target), (scope, dict(target, unit_id="wrong-unit")),
                                  (scope, dict(target, node_id="wrong-node")), (scope, dict(target, node_id=foreign_node[0])),
                                  (scope, dict(target, stage_id="wrong-stage"))]:
        with pytest.raises(AppError):
            put(service, bad_scope, bad_target, "unit", 0)
    with pytest.raises(ValidationAppError):
        put(service, scope, target, "system", 0)
    assert service.get_context(scope, target)["unit"] is None


def test_legacy_project_ref_reads_normalized_but_invalid_mode_is_explicit(preferences):
    db, service, scope, targets, _ = preferences
    target = targets[0]
    with psycopg.connect(db.migrator_dsn) as conn:
        conn.execute("INSERT INTO preferences(preference_id,project_id,scope,scope_ref,media_type,language,official_priority,pace,version) "
            "VALUES ('legacy',%s,'project','','text_first','zh',true,'normal',5)", (target["project_id"],))
        conn.execute("INSERT INTO preference_overrides(override_id,project_id,scope,scope_ref,media_type) "
            "VALUES ('old-override',%s,'unit',%s,'video')", (target["project_id"], target["unit_id"]))
    context = service.get_context(scope, target)
    assert context["project"]["scope_ref"] == target["project_id"]
    assert context["effective"]["mode"] == "text_first"
    assert context["unit"] is None
    updated = put(service, scope, target, "project", 5)
    assert updated["versions"]["project"] == 6
    with psycopg.connect(db.migrator_dsn) as conn:
        assert conn.execute("SELECT scope_ref FROM preferences WHERE preference_id='legacy'").fetchone()[0] == target["project_id"]
        conn.execute("UPDATE preferences SET media_type='video' WHERE preference_id='legacy'")
    context = service.get_context(scope, target)
    assert context["invalid_scopes"] == ["project"] and context["effective"] is None
    with pytest.raises(ValidationAppError, match="历史"):
        service.resolve(scope, target)


def test_multiple_invalid_legacy_layers_can_be_repaired_independently(preferences):
    db, service, scope, targets, _ = preferences
    target = targets[0]
    with psycopg.connect(db.migrator_dsn) as conn:
        for name, ref in (("project", ""), ("unit", target["unit_id"])):
            conn.execute("INSERT INTO preferences(preference_id,project_id,scope,scope_ref,media_type,language,official_priority,pace,version) "
                "VALUES(%s,%s,%s,%s,'video','zh',true,'normal',5)",
                ("invalid-"+name, target["project_id"], name, ref))
    context = service.get_context(scope, target)
    assert context["invalid_scopes"] == ["project", "unit"] and context["effective"] is None
    repaired = put(service, scope, target, "project", 5)
    assert repaired["invalid_scopes"] == ["unit"] and repaired["versions"]["project"] == 6
    assert service.project_default(scope, target["project_id"]).mode.value == "video_first"
    restored = service.restore(scope, target, scope_name="unit", expected_version=5)
    assert restored["invalid_scopes"] == [] and restored["versions"]["unit"] == 6
    assert restored["effective"]["scope"].value == "project"


def test_waited_publication_rechecks_current_plan_before_write(preferences):
    db, service, scope, targets, _ = preferences
    target = targets[0]
    with psycopg.connect(db.migrator_dsn) as blocker, ThreadPoolExecutor(max_workers=1) as pool:
        blocker.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", ("plan-decision:" + target["project_id"],))
        future = pool.submit(put, service, scope, target, "unit", 0)
        try:
            deadline = time.monotonic() + 5
            with psycopg.connect(db.admin_dsn, autocommit=True) as observer:
                while not observer.execute("SELECT 1 FROM pg_stat_activity WHERE datname=current_database() AND wait_event_type='Lock' AND query LIKE 'SELECT pg_advisory_xact_lock%'").fetchone():
                    assert time.monotonic() < deadline
                    time.sleep(0.01)
            # A waiter on the project advisory lock must not already hold the
            # project row; generation/publication acquire advisory first too.
            blocker.execute("SELECT project_id FROM learning_projects WHERE project_id=%s FOR UPDATE NOWAIT",
                            (target["project_id"],))
            blocker.execute("UPDATE plan_revisions SET status='superseded' WHERE project_id=%s AND plan_id=%s",
                            (target["project_id"], target["plan_id"]))
        finally:
            blocker.commit()
        try:
            with pytest.raises(AppError):
                future.result(timeout=5)
            with psycopg.connect(db.migrator_dsn) as conn:
                assert conn.execute("SELECT count(*) FROM preferences").fetchone()[0] == 0
        finally:
            with psycopg.connect(db.migrator_dsn) as conn:
                conn.execute("UPDATE plan_revisions SET status='approved' WHERE plan_id=%s", (target["plan_id"],))


def test_node_restore_inherits_complete_unit_setting_without_project_mutation(preferences):
    _, service, scope, targets, _ = preferences
    unit, _, node = targets
    put(service, scope, unit, "project", 0, mode="text_first", language="zh")
    put(service, scope, unit, "unit", 0, language="en")
    put(service, scope, node, "node", 0, mode="mixed", language="fr")
    restored = service.restore(scope, node, scope_name="node", expected_version=1)
    assert restored["node"] is None and restored["versions"]["node"] == 2
    assert restored["effective"] == restored["unit"]
    assert restored["project"]["mode"] == "text_first"
    assert restored["project"]["language"] == "zh"


def test_archived_owner_read_and_write_denied(preferences):
    db, service, scope, targets, _ = preferences
    target = targets[0]
    with psycopg.connect(db.migrator_dsn) as conn:
        conn.execute("UPDATE learning_projects SET archived_at=now() WHERE project_id=%s", (target["project_id"],))
    try:
        with pytest.raises(AppError):
            put(service, scope, target, "project", 0)
        with pytest.raises(AppError):
            service.get_context(scope, target)
        with pytest.raises(AppError):
            service.project_default(scope, target["project_id"])
    finally:
        with psycopg.connect(db.migrator_dsn) as conn:
            conn.execute("UPDATE learning_projects SET archived_at=NULL WHERE project_id=%s", (target["project_id"],))


def test_migration_refuses_losing_retained_tombstone_history(preferences):
    db, service, scope, targets, _ = preferences
    target = targets[0]
    put(service, scope, target, "unit", 0)
    service.restore(scope, target, scope_name="unit", expected_version=1)
    # Recreated slot has deleted_at=NULL but version3 still identifies retained history.
    put(service, scope, target, "unit", 2)
    env = dict(os.environ, STUDYPLAN_MIGRATION_DSN=db.migrator_dsn.replace("postgresql://", "postgresql+psycopg://"))
    result = subprocess.run([sys.executable, "-m", "alembic", "downgrade", "0014"],
        cwd=Path(__file__).resolve().parents[2], env=env, capture_output=True, text=True)
    assert result.returncode != 0 and "Preference tombstone/version history prevents downgrade" in result.stderr
    assert service.get_context(scope, target)["versions"]["unit"] == 3
