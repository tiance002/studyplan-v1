from dataclasses import replace

import psycopg
import pytest
from app.core.errors import AppError

from tests.e2e.test_b2v_http_end_to_end import migrated_db as migrated_db
from tests.integration.test_prompts_pg import prompt_scenario as prompt_scenario
from tests.integration.test_prompts_pg import resource_scenario as resource_scenario

pytestmark = pytest.mark.postgres


@pytest.fixture
def submission_scenario(prompt_scenario):
    from app.domain.practice_submissions import SubmissionEvidence, SubmissionSaveCommand

    db, scope, cmd, container, current = prompt_scenario
    return (
        db,
        scope,
        SubmissionSaveCommand(
            cmd.project_id,
            cmd.plan_id,
            cmd.stage_id,
            cmd.task_id,
            "  Exact\r\noriginal🙂\t ",
            None,
            (
                SubmissionEvidence(
                    "external_report", "  report ", "\n Actual measured result🙂 ", "http://localhost/report"
                ),
            ),
            "evaluation",
            None,
            current.version,
            1,
            0,
            "save",
        ),
        container,
        current,
    )


def repository(db):
    from app.infrastructure.db.practice_submissions import PgPracticeSubmissions

    return PgPracticeSubmissions(db.app_dsn)


def decision(cmd, saved, **changes):
    from app.domain.practice_submissions import CriterionCoverage, SubmissionDecisionCommand

    task = saved["submission"]["task_snapshot"]["task"]
    values = dict(
        project_id=cmd.project_id,
        submission_id=saved["submission"]["submission_id"],
        conclusion="accepted",
        rationale="  Manual observation, platform did not run tests🙂 ",
        coverage=tuple(CriterionCoverage(i, (0,), f" observed {i} ") for i in range(len(task["acceptance"]))),
        acknowledge_verification_limit=True,
        expected_plan_version=cmd.expected_plan_version,
        expected_task_version=saved["thread"]["task_version"],
        expected_version=saved["thread"]["version"],
        idempotency_key="decide",
    )
    values.update(changes)
    return SubmissionDecisionCommand(**values)


def test_raw_save_and_user_acceptance_are_immutable_and_do_not_verify_learning(submission_scenario):
    db, scope, cmd, _, current = submission_scenario
    repo = repository(db)
    empty = repo.thread(scope, *cmd.position)
    assert empty["version"] == 0 and not empty["submissions"]
    with psycopg.connect(db.migrator_dsn) as conn:
        knowledge_before = conn.execute(
            "SELECT node_id,source_status,content_version,objectives FROM knowledge_nodes WHERE project_id=%s ORDER BY node_id",
            (cmd.project_id,),
        ).fetchall()
    saved = repo.save(scope, cmd)
    item = saved["submission"]
    assert item["note"] == cmd.note and item["evidence"][0]["content"] == cmd.evidence[0].content
    assert item["evidence_grade"] == "reported" and not item["verification_available"]
    assert saved["thread"]["task"]["status"] == "awaiting_evidence"
    assert saved["thread"]["task_version"] == 2
    assert repo.save(scope, cmd) == saved
    accepted = repo.decide(scope, decision(cmd, saved))
    assert accepted["manual_confirmation"] and accepted["task_status"] == "accepted"
    assert accepted["submission"]["review"]["reviewer_kind"] == "user"
    assert repo.decide(scope, decision(cmd, saved)) == accepted
    assert repo.get(scope, cmd.project_id, item["submission_id"])["note"] == cmd.note
    with psycopg.connect(db.migrator_dsn) as conn:
        assert (
            conn.execute(
                "SELECT node_id,source_status,content_version,objectives FROM knowledge_nodes WHERE project_id=%s ORDER BY node_id",
                (cmd.project_id,),
            ).fetchall()
            == knowledge_before
        )
        assert (
            conn.execute(
                "SELECT count(*) FROM unit_progress WHERE project_id=%s", (cmd.project_id,)
            ).fetchone()[0]
            == 0
        )
        assert (
            conn.execute("SELECT count(*) FROM ai_runs WHERE project_id=%s", (cmd.project_id,)).fetchone()[0]
            == 0
        )
        assert (
            conn.execute(
                "SELECT count(*) FROM learning_exposures WHERE project_id=%s", (cmd.project_id,)
            ).fetchone()[0]
            == 0
        )
        assert (
            conn.execute(
                "SELECT verification FROM practice_submissions WHERE submission_id=%s",
                (item["submission_id"],),
            ).fetchone()[0]
            is None
        )


@pytest.mark.parametrize(
    "bad", ["owner", "stage", "task", "plan", "head", "task_version", "plan_version", "parent"]
)
def test_save_scope_cas_and_parent_fail_without_history_writes(submission_scenario, bad):
    db, scope, cmd, _, _ = submission_scenario
    repo = repository(db)
    if bad == "owner":
        scope = replace(scope, actor_id="forged", learning_project_scope=(cmd.project_id,))
    else:
        changes = {
            "stage": dict(stage_id="wrong"),
            "task": dict(task_id="wrong"),
            "plan": dict(plan_id="wrong"),
            "head": dict(expected_version=1),
            "task_version": dict(expected_task_version=99),
            "plan_version": dict(expected_plan_version=99),
            "parent": dict(parent_submission_id="wrong"),
        }[bad]
        cmd = replace(cmd, **changes)
    with pytest.raises(AppError):
        repo.save(scope, cmd)
    with psycopg.connect(db.migrator_dsn) as conn:
        assert (
            conn.execute(
                "SELECT count(*) FROM practice_submissions WHERE project_id=%s", (cmd.project_id,)
            ).fetchone()[0]
            == 0
        )
        assert (
            conn.execute(
                "SELECT version FROM practice_tasks WHERE task_id=%s",
                (cmd.task_id if bad != "task" else submission_scenario[2].task_id,),
            ).fetchone()[0]
            == 1
        )


def test_saves_race_and_review_is_latest_only_with_retained_replay(submission_scenario):
    from concurrent.futures import ThreadPoolExecutor

    db, scope, cmd, _, _ = submission_scenario
    repo = repository(db)

    def save(i):
        try:
            return repo.save(scope, replace(cmd, idempotency_key=f"key{i}"))
        except AppError as error:
            assert error.http_status == 409
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        result = list(pool.map(save, range(2)))
    assert sum(item is not None for item in result) == 1
    first = next(item for item in result if item)
    second_cmd = replace(
        cmd,
        expected_version=1,
        expected_task_version=2,
        idempotency_key="second",
        parent_submission_id=first["submission"]["submission_id"],
    )
    second = repo.save(scope, second_cmd)
    assert (
        second["thread"]["version"] == 2
        and second["thread"]["task_version"] == first["thread"]["task_version"]
    )
    with pytest.raises(AppError):
        repo.decide(
            scope,
            decision(cmd, first, expected_task_version=second["thread"]["task_version"], expected_version=2),
        )
    reviewed = repo.decide(scope, decision(second_cmd, second, conclusion="needs_more_evidence"))
    assert reviewed["task_status"] == "awaiting_evidence"
    assert second["submission"]["parent_submission_id"] == first["submission"]["submission_id"]
    assert repo.save(scope, second_cmd) == second


@pytest.mark.parametrize(
    "bad", ["ack", "empty", "duplicate", "criterion", "evidence", "insufficient", "owner", "version"]
)
def test_manual_acceptance_rejects_invalid_coverage_without_review_or_status_effect(submission_scenario, bad):
    from app.domain.practice_submissions import CriterionCoverage

    db, scope, cmd, _, _ = submission_scenario
    repo = repository(db)
    if bad == "insufficient":
        cmd = replace(cmd, evidence=())
    saved = repo.save(scope, cmd)
    review = decision(cmd, saved)
    if bad == "ack":
        review = replace(review, acknowledge_verification_limit=False)
    elif bad == "empty":
        review = replace(review, coverage=())
    elif bad == "duplicate":
        review = replace(review, coverage=(review.coverage[0], review.coverage[0]))
    elif bad == "criterion":
        review = replace(review, coverage=(CriterionCoverage(99, (0,), "Observed"),))
    elif bad == "evidence":
        review = replace(review, coverage=(CriterionCoverage(0, (99,), "Observed"),))
    elif bad == "owner":
        scope = replace(scope, actor_id="forged", learning_project_scope=(cmd.project_id,))
    elif bad == "version":
        review = replace(review, expected_task_version=99)
    with pytest.raises(AppError):
        repo.decide(scope, review)
    with psycopg.connect(db.migrator_dsn) as conn:
        assert (
            conn.execute(
                "SELECT count(*) FROM acceptance_reviews WHERE project_id=%s", (cmd.project_id,)
            ).fetchone()[0]
            == 0
        )
        assert conn.execute(
            "SELECT status,version FROM practice_tasks WHERE task_id=%s", (cmd.task_id,)
        ).fetchone() == ("awaiting_evidence", 2)


@pytest.mark.parametrize("drift", ["task", "project", "knowledge", "role"])
def test_decision_compares_saved_requirements_not_only_mutable_version(submission_scenario, drift):
    db, scope, cmd, _, _ = submission_scenario
    repo = repository(db)
    saved = repo.save(scope, cmd)
    with psycopg.connect(db.migrator_dsn) as conn:
        if drift == "task":
            conn.execute(
                "UPDATE practice_tasks SET goal='different requirement' WHERE task_id=%s", (cmd.task_id,)
            )
        elif drift == "project":
            conn.execute(
                "UPDATE practice_projects SET idea='Different project content' WHERE practice_project_id=%s",
                (saved["thread"]["practice_project"]["practice_project_id"],),
            )
        elif drift == "knowledge":
            conn.execute(
                "UPDATE knowledge_nodes SET content_version=content_version+1 WHERE node_id=%s",
                (saved["thread"]["task"]["knowledge_links"][0]["node_id"],),
            )
        else:
            conn.execute(
                "UPDATE plan_task_knowledge_links SET role='supporting' WHERE plan_id=%s AND task_id=%s",
                (cmd.plan_id, cmd.task_id),
            )
    with pytest.raises(AppError) as error:
        repo.decide(scope, decision(cmd, saved))
    assert error.value.http_status == 409
    assert (
        repo.get(scope, cmd.project_id, saved["submission"]["submission_id"])["task_snapshot"]
        == saved["submission"]["task_snapshot"]
    )


def test_accepted_supplement_preserves_task_status_and_each_original(submission_scenario):
    db, scope, cmd, _, _ = submission_scenario
    repo = repository(db)
    first = repo.save(scope, cmd)
    accepted = repo.decide(scope, decision(cmd, first))
    supplement_cmd = replace(
        cmd,
        note="  Supplement🙂 ",
        expected_version=1,
        expected_task_version=accepted["task_version"],
        idempotency_key="supplement",
        parent_submission_id=first["submission"]["submission_id"],
    )
    supplement = repo.save(scope, supplement_cmd)
    assert supplement["thread"]["task_version"] == accepted["task_version"]
    assert supplement["thread"]["task"]["status"] == "accepted"
    review = repo.decide(
        scope,
        decision(
            supplement_cmd,
            supplement,
            conclusion="not_passed",
            coverage=(),
            idempotency_key="supplement-review",
        ),
    )
    assert review["task_status"] == "accepted" and review["task_version"] == accepted["task_version"]
    assert review["submission"]["review"]["conclusion"] == "not_passed"
    assert repo.get(scope, cmd.project_id, first["submission"]["submission_id"]) == accepted["submission"]
    assert repo.decide(scope, decision(cmd, first)) == accepted
    assert repo.save(scope, cmd) == first


def test_review_and_save_transactions_roll_back_at_receipt_and_compete_once(submission_scenario, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor

    db, scope, cmd, _, _ = submission_scenario
    repo = repository(db)
    original = repo._record
    monkeypatch.setattr(repo, "_record", lambda *args: (_ for _ in ()).throw(RuntimeError("after changes")))
    with pytest.raises(RuntimeError):
        repo.save(scope, cmd)
    assert repo.thread(scope, *cmd.position)["version"] == 0
    assert repo.thread(scope, *cmd.position)["task_version"] == 1
    monkeypatch.setattr(repo, "_record", original)
    saved = repo.save(scope, cmd)
    monkeypatch.setattr(repo, "_record", lambda *args: (_ for _ in ()).throw(RuntimeError("after review")))
    with pytest.raises(RuntimeError):
        repo.decide(scope, decision(cmd, saved))
    assert repo.get(scope, cmd.project_id, saved["submission"]["submission_id"])["review"] is None
    assert repo.thread(scope, *cmd.position)["task"]["status"] == "awaiting_evidence"
    monkeypatch.setattr(repo, "_record", original)

    def decide(i):
        try:
            return repo.decide(scope, decision(cmd, saved, idempotency_key=f"review-{i}"))
        except AppError as error:
            assert error.http_status == 409
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(decide, range(2)))
    assert sum(result is not None for result in results) == 1
    with psycopg.connect(db.migrator_dsn) as conn:
        assert (
            conn.execute(
                "SELECT count(*) FROM acceptance_reviews WHERE project_id=%s", (cmd.project_id,)
            ).fetchone()[0]
            == 1
        )


def test_old_plan_archive_and_receipts_remain_after_real_practice_replacement(submission_scenario):
    from app.domain.practice_changes import PracticeChangeCommand
    from app.infrastructure.db.practice_changes import PgPracticeChanges

    db, scope, cmd, _, current = submission_scenario
    repo = repository(db)
    saved = repo.save(scope, cmd)
    accepted = repo.decide(scope, decision(cmd, saved))
    main = saved["thread"]["practice_project"]
    changes = PgPracticeChanges(db.app_dsn)
    preview = changes.preview(
        scope,
        PracticeChangeCommand(
            cmd.project_id,
            cmd.plan_id,
            main["practice_project_id"],
            "Different main",
            "Different manually specified main",
            None,
            (),
            current.version,
            "keep_history_only",
            "preview",
        ),
    )
    published = changes.decide(
        scope,
        cmd.project_id,
        preview["proposal_id"],
        "confirm",
        current.version,
        preview["preview_hash"],
        "confirm",
        True,
    )
    assert published["plan_id"] != cmd.plan_id
    assert repo.save(scope, cmd) == saved
    assert repo.decide(scope, decision(cmd, saved)) == accepted
    assert repo.thread(scope, *cmd.position)["submissions"][0] == accepted["submission"]
    assert repo.history(scope, cmd.project_id)["items"][0] == accepted["submission"]
    with pytest.raises(AppError):
        repo.decide(scope, replace(decision(cmd, saved), idempotency_key="old-decision-new-key"))
    with pytest.raises(AppError):
        repo.save(
            scope,
            replace(
                cmd,
                idempotency_key="old-again",
                expected_task_version=accepted["task_version"],
                expected_version=1,
            ),
        )
    archive = repo.outcomes(scope, cmd.project_id)
    group = next(group for group in archive["groups"] if group["kind"] == "evaluation")
    assert group["total_records"] == 1 and group["items"][0]["task_title"] == saved["thread"]["task"]["title"]
    assert group["items"][0]["manual_confirmation"]


def test_archive_pagination_thread_window_and_legacy_are_truthful(submission_scenario):
    from app.api.v1.submission_schemas import PracticeOutcomeView, PracticeSubmissionHistoryView
    from app.core.ids import new_id

    db, scope, cmd, _, _ = submission_scenario
    repo = repository(db)
    with psycopg.connect(db.migrator_dsn) as conn:
        legacy = new_id("legacy")
        conn.execute(
            "INSERT INTO practice_submissions(submission_id,project_id,task_id,note,evidence,evidence_grade,verification) VALUES(%s,%s,%s,' legacy raw ', '[\"retained text\"]','verified','{\"old\":true}')",
            (legacy, cmd.project_id, cmd.task_id),
        )
        conn.execute(
            "INSERT INTO acceptance_reviews(review_id,project_id,submission_id,conclusion,reviewer_kind,rationale) VALUES(%s,%s,%s,'accepted','system','old actual feedback')",
            (new_id("legacyreview"), cmd.project_id, legacy),
        )
    previous = None
    task_version = 1
    for i in range(22):
        saved = repo.save(
            scope,
            replace(
                cmd,
                expected_version=i,
                expected_task_version=task_version,
                idempotency_key=f"save-{i}",
                parent_submission_id=previous,
            ),
        )
        previous = saved["submission"]["submission_id"]
        task_version = saved["thread"]["task_version"]
    thread = repo.thread(scope, *cmd.position)
    assert thread["version"] == 22 and len(thread["submissions"]) == 20 and thread["history_truncated"]
    assert [row["version"] for row in thread["submissions"]] == list(range(3, 23))
    ids = []
    cursor = None
    while True:
        page = repo.history(scope, cmd.project_id, cursor, 5)
        PracticeSubmissionHistoryView.model_validate(page)
        ids.extend(item["submission_id"] for item in page["items"])
        cursor = page["next_cursor"]
        if cursor is None:
            break
    assert len(ids) == 23 and len(set(ids)) == 23 and ids[-1] == legacy
    old = repo.get(scope, cmd.project_id, legacy)
    assert old["legacy_evidence"] == ["retained text"] and old["evidence"] == []
    assert old["evidence_grade"] == "verified" and not old["verification_available"]
    assert (
        old["task_snapshot"]["snapshot_status"] == "legacy_unfrozen" and old["task_snapshot"]["task"] is None
    )
    assert old["review"]["rationale"] == "old actual feedback" and not old["review"]["manual_confirmation"]
    with pytest.raises(AppError):
        repo.decide(scope, replace(decision(cmd, saved), submission_id=legacy))
    archive = repo.outcomes(scope, cmd.project_id, limit=5)
    PracticeOutcomeView.model_validate(archive)
    assert len(archive["groups"]) == 7 and sum(g["total_records"] for g in archive["groups"]) == 23
    assert sum(len(g["items"]) for g in archive["groups"]) == 5
    foreign_cursor = repo.history(scope, cmd.project_id, limit=1)["next_cursor"]
    import base64
    import json

    raw = json.loads(base64.urlsafe_b64decode(foreign_cursor + "=" * (-len(foreign_cursor) % 4)))
    raw["project"] = "other"
    wrong = base64.urlsafe_b64encode(json.dumps(raw).encode()).decode()
    for bad in [wrong, "not-a-valid-cursor", "x" * 1025]:
        with pytest.raises(AppError):
            repo.history(scope, cmd.project_id, bad)


def test_sql_scope_immutability_and_heterogeneous_receipts(submission_scenario):
    from app.infrastructure.db.plan_repository import to_psycopg_dsn

    db, scope, cmd, _, _ = submission_scenario
    repo = repository(db)
    saved = repo.save(scope, cmd)
    reviewed = repo.decide(scope, decision(cmd, saved))
    with pytest.raises(AppError):
        repo.save(scope, replace(cmd, note="Different", idempotency_key=cmd.idempotency_key))
    with pytest.raises(AppError):
        repo.decide(scope, decision(cmd, saved, idempotency_key=cmd.idempotency_key))
    with psycopg.connect(to_psycopg_dsn(db.app_dsn)) as conn:
        assert conn.execute("SELECT count(*) FROM practice_submissions").fetchone()[0] == 0
        conn.execute(
            "SELECT set_config('app.project_id',%s,true),set_config('app.actor_id','forged',true)",
            (cmd.project_id,),
        )
        assert conn.execute("SELECT count(*) FROM acceptance_reviews").fetchone()[0] == 0
    for table, column, identifier in [
        ("practice_submissions", "submission_id", saved["submission"]["submission_id"]),
        ("acceptance_reviews", "review_id", reviewed["submission"]["review"]["review_id"]),
        ("submission_receipts", "idempotency_key", cmd.idempotency_key),
    ]:
        with psycopg.connect(db.migrator_dsn) as conn:
            with pytest.raises(psycopg.Error):
                conn.execute(f"DELETE FROM {table} WHERE {column}=%s", (identifier,))
    with psycopg.connect(to_psycopg_dsn(db.app_dsn)) as conn:
        conn.execute(
            "SELECT set_config('app.project_id',%s,true),set_config('app.actor_id',%s,true)",
            (cmd.project_id, scope.actor_id),
        )
        with pytest.raises(psycopg.Error):
            conn.execute(
                "UPDATE practice_submissions SET note='overwrite' WHERE submission_id=%s",
                (saved["submission"]["submission_id"],),
            )


def test_parent_must_be_an_existing_record_of_exact_position(submission_scenario):
    from app.core.ids import new_id

    db, scope, cmd, _, _ = submission_scenario
    repo = repository(db)
    parent = new_id("legacyparent")
    with psycopg.connect(db.migrator_dsn) as conn:
        conn.execute(
            "INSERT INTO practice_submissions(submission_id,project_id,task_id,note,evidence_grade) VALUES(%s,%s,%s,'old note','insufficient')",
            (parent, cmd.project_id, cmd.task_id),
        )
    with pytest.raises(AppError) as error:
        repo.save(scope, replace(cmd, parent_submission_id=parent))
    assert error.value.http_status == 409
    assert repo.thread(scope, *cmd.position)["version"] == 0
    assert repo.get(scope, cmd.project_id, parent)["note"] == "old note"


def test_nonempty_downgrade_guard_refuses_before_any_destructive_statement(submission_scenario, monkeypatch):
    import importlib.util
    from pathlib import Path

    db, scope, cmd, _, _ = submission_scenario
    repo = repository(db)
    saved = repo.save(scope, cmd)
    path = Path(__file__).parents[2] / "alembic" / "versions" / "0022_practice_submissions.py"
    spec = importlib.util.spec_from_file_location("test_submission_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with psycopg.connect(db.migrator_dsn) as conn:
        monkeypatch.setattr(migration.op, "execute", conn.execute)
        with pytest.raises(psycopg.Error, match="refuse destructive downgrade"):
            migration.downgrade()
    assert repo.get(scope, cmd.project_id, saved["submission"]["submission_id"]) == saved["submission"]
    with psycopg.connect(db.migrator_dsn) as conn:
        assert conn.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "0022"


def test_save_waiting_for_publication_rechecks_current_plan_before_original_write(submission_scenario):
    import time
    from concurrent.futures import ThreadPoolExecutor

    from app.core.ids import new_id
    from app.domain.planning.models import PlanDraft, PlanPublicationService
    from app.infrastructure.db.plan_repository import PgPlanRepository, to_psycopg_dsn
    from app.infrastructure.db.planning_fence import lock_plan_version
    from app.infrastructure.db.practice_submissions import PgPracticeSubmissions
    from psycopg.conninfo import make_conninfo
    from psycopg.rows import dict_row

    db, scope, cmd, _, current = submission_scenario
    marker = "submission-wait-" + new_id("barrier")
    waiting = PgPracticeSubmissions(make_conninfo(to_psycopg_dsn(db.app_dsn), application_name=marker))
    with (
        ThreadPoolExecutor(max_workers=1) as pool,
        psycopg.connect(db.migrator_dsn, row_factory=dict_row) as blocker,
    ):
        blocker.execute("SET LOCAL statement_timeout='10000ms'")
        lock_plan_version(blocker, cmd.project_id, None)
        pending = pool.submit(waiting.save, scope, cmd)
        with psycopg.connect(db.admin_dsn, autocommit=True) as observer:
            deadline = time.monotonic() + 5
            while not observer.execute(
                "SELECT 1 FROM pg_stat_activity WHERE application_name=%s AND wait_event_type='Lock'",
                (marker,),
            ).fetchone():
                if pending.done():
                    pending.result()
                    pytest.fail("save did not wait for actual publication lock")
                assert time.monotonic() < deadline
                time.sleep(0.01)
        repo = PgPlanRepository(db.app_dsn, connection=blocker)
        draft = PlanDraft(
            "draft-submission-new-plan",
            cmd.project_id,
            "",
            "New controlled goal",
            current.revision + 1,
            stages=current.stages,
            unit_links=current.unit_links,
            task_links=current.task_links,
            task_knowledge_links=current.task_knowledge_links,
            stage_resources=current.stage_resources,
            resource_snapshots=current.resource_snapshots,
        )
        repo.save_draft(draft, expected_version=current.version)
        published = PlanPublicationService(repo).publish(
            draft=draft,
            presented_hash=draft.content_hash,
            expected_version=current.version,
            idempotency_key="publish-before-save",
        )
        assert published.created
        blocker.commit()
        with pytest.raises(AppError) as error:
            pending.result(timeout=5)
        assert error.value.http_status == 409
    assert repository(db).thread(scope, *cmd.position)["version"] == 0
    with psycopg.connect(db.migrator_dsn) as conn:
        assert (
            conn.execute(
                "SELECT count(*) FROM practice_submissions WHERE project_id=%s", (cmd.project_id,)
            ).fetchone()[0]
            == 0
        )
