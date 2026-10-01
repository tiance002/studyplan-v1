"""Position originals and review outcomes in a new isolated PostgreSQL database."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import psycopg
import pytest
from app.core.errors import AppError
from app.domain.summaries import SummarySaveCommand
from app.infrastructure.db.summaries import PgSummaries

from tests.e2e.test_b2v_http_end_to_end import migrated_db as migrated_db
from tests.integration.test_resource_changes_pg import scenario as scenario

pytestmark = pytest.mark.postgres


def command(scenario, raw=" \n短总结🙂\t ", version=0, key="save"):
    db, scope, cmd, container, current = scenario
    return SummarySaveCommand(cmd.project_id, cmd.plan_id, cmd.stage_id, current.unit_links[0].unit_id,
                              raw, version, key)


def test_short_exact_save_idempotent_cas_and_no_model_or_progress(scenario):
    db, scope, _, _, _ = scenario
    repo = PgSummaries(db.app_dsn)
    cmd = command(scenario)
    assert repo.thread(scope, *cmd.position)["version"] == 0
    result = repo.save(scope, cmd)
    assert result["attempt"]["content"] == cmd.content
    assert result["thread"]["version"] == 1
    assert repo.save(scope, cmd) == dict(result, replayed=True)
    with pytest.raises(AppError) as conflict:
        repo.save(scope, replace(cmd, content="异体"))
    assert conflict.value.http_status == 409
    with pytest.raises(AppError) as stale:
        repo.save(scope, replace(cmd, idempotency_key="stale"))
    assert stale.value.http_status == 409
    with psycopg.connect(db.migrator_dsn) as conn:
        for table in ("ai_runs", "learning_exposures", "unit_progress"):
            assert conn.execute(f"SELECT count(*) FROM {table} WHERE project_id=%s", (cmd.project_id,)).fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM ai_provider_attempts a JOIN ai_runs r USING(run_id) "
                            "WHERE r.project_id=%s", (cmd.project_id,)).fetchone()[0] == 0


def test_position_cas_concurrent_one_original(scenario):
    db, scope, _, _, _ = scenario
    repo = PgSummaries(db.app_dsn)
    def save(key):
        try:
            return repo.save(scope, command(scenario, key=key))["thread"]["version"]
        except AppError as error:
            return error.http_status
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(save, ["a", "b"])) == [1, 409]


def test_feedback_admission_duplicate_one_job_and_pending_bound(scenario):
    from app.application.model_binding import SubmissionBinding
    from app.application.planning_budget import BudgetPolicy
    from app.domain.summaries import summary_manifest
    db, scope, _, _, _ = scenario
    repo = PgSummaries(db.app_dsn)
    manifest = summary_manifest(SubmissionBinding("test:1", BudgetPolicy(20, 20, 20, 20, 20, 20)))
    attempts = [repo.save(scope, command(scenario, raw=str(n), version=n, key="save"+str(n)))["attempt"] for n in range(4)]
    first = repo.enqueue_review(scope, attempts[0]["project_id"], attempts[0]["attempt_id"], "review", manifest)
    assert repo.enqueue_review(scope, attempts[0]["project_id"], attempts[0]["attempt_id"], "review", manifest) == first
    assert repo.enqueue_review(scope, attempts[0]["project_id"], attempts[0]["attempt_id"], "other-key", manifest)["run_id"] == first["run_id"]
    for attempt in attempts[1:3]:
        repo.enqueue_review(scope, attempt["project_id"], attempt["attempt_id"], "review"+attempt["attempt_id"], manifest)
    with pytest.raises(AppError):
        repo.enqueue_review(scope, attempts[3]["project_id"], attempts[3]["attempt_id"], "fourth", manifest)
    with psycopg.connect(db.migrator_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM ai_jobs j JOIN ai_runs r USING(run_id) WHERE r.project_id=%s",
                            (attempts[0]["project_id"],)).fetchone()[0] == 3
        pending = conn.execute("SELECT b.attempt_id,r.run_id,r.version FROM summary_review_bindings b JOIN ai_runs r USING(run_id) "
                               "WHERE b.project_id=%s", (attempts[0]["project_id"],)).fetchall()
    for aid, rid, version in pending:
        repo.cancel_review(scope, attempts[0]["project_id"], aid, rid, version, "cleanup"+aid)


def reviewed(scenario, *, content=" 原文 "):
    from app.application.model_binding import SubmissionBinding
    from app.application.planning_budget import BudgetPolicy
    from app.application.summaries import SummaryService
    from app.domain.summaries import summary_manifest
    from app.infrastructure.db.job_repository import PgPlanningJobRepository
    db, scope, _, _, _ = scenario
    repo = PgSummaries(db.app_dsn)
    attempt = repo.save(scope, command(scenario, raw=content))["attempt"]
    binding = SubmissionBinding("test:1", BudgetPolicy(20, 20, 20, 20, 20, 20))
    handle = repo.enqueue_review(scope, attempt["project_id"], attempt["attempt_id"], "review", summary_manifest(binding))
    jobs = PgPlanningJobRepository(db.app_dsn, admission_mode="trusted_server")
    claim = jobs.claim_next("summary-test", 30)
    assert claim is not None and claim.run_id == handle["run_id"]
    assert jobs.read_claim_submission(claim)["kind"] == "summary_review_submission"
    return repo, attempt, handle, jobs, claim, SummaryService


class OfflineProvider:
    """Explicit offline adapter, no httpx client/no external dispatch."""
    model = "offline"
    prompt_version = "summary-review-v1"
    domain_pack = {}
    base_url = "https://offline.invalid"
    configuration_ref = "test:1"

    def __init__(self, *, failure=None, payload=None):
        from app.application.planning_budget import BudgetPolicy
        self.budget_policy = BudgetPolicy(20, 20, 20, 20, 20, 20)
        self.calls = 0
        self.payloads = []
        self.failure = failure
        self.payload = payload or {"conclusion": "needs_revision", "covered": ["已描述自己的理解"],
            "gaps": ["补充一个例子"], "misconceptions": [], "questions": ["怎样验证这个例子？"]}

    def request_options(self, purpose):
        return {"model": self.model, "max_tokens": 20}

    def generate_structured(self, **kwargs):
        from app.ports.llm import LLMResult
        self.calls += 1
        self.payloads.append(kwargs["payload"])
        return self.failure or LLMResult(self.payload, "offline", "explicit_offline_test")


def resolver(db, provider):
    from app.infrastructure.providers.attempt_ledger import PgAttemptLLM
    return lambda scope, project, run, model_ref, manifest: PgAttemptLLM(db.app_dsn, provider, manifest=manifest)


def test_one_feedback_pinned_original_later_head_and_receipt_survives_revoked_model(scenario):
    from app.api.v1.summary_schemas import SummaryAttemptView
    db, scope, _, _, _ = scenario
    repo, attempt, handle, jobs, claim, Service = reviewed(scenario)
    provider = OfflineProvider()
    newer = repo.save(scope, command(scenario, raw=" 新的编辑原文 ", version=1, key="second"))["attempt"]
    service = Service(repo, provider_resolver=resolver(db, provider), admission_mode="trusted_server")
    service.execute_review(claim.project_id, claim.run_id, guard=lambda: None, claim=claim)
    result = repo.attempt(scope, claim.project_id, attempt["attempt_id"])
    SummaryAttemptView.model_validate(result)
    assert result["content"] == " 原文 " and result["review"]["conclusion"] == "needs_revision"
    assert result["run_status"] == "succeeded" and provider.calls == 1
    assert repo.attempt(scope, claim.project_id, newer["attempt_id"])["review"] is None
    assert service.request_review(scope, claim.project_id, attempt["attempt_id"], "review", True) == handle
    # A retained attempt binding also survives revoked model configuration for a new click key.
    assert service.request_review(scope, claim.project_id, attempt["attempt_id"], "new-click", True)["run_id"] == handle["run_id"]
    with psycopg.connect(db.migrator_dsn) as conn:
        assert conn.execute("SELECT result_ref,next_action FROM ai_runs WHERE run_id=%s", (claim.run_id,)).fetchone() == (result["review"]["review_id"], "none")
        assert conn.execute("SELECT count(*) FROM summary_reviews WHERE attempt_id=%s", (attempt["attempt_id"],)).fetchone()[0] == 1
        assert conn.execute("SELECT count(*) FROM learning_exposures WHERE project_id=%s", (claim.project_id,)).fetchone()[0] == 0


def test_retained_provider_success_replays_after_business_crash_without_redispatch(scenario, monkeypatch):
    from app.ports.summaries import ReviewPersistenceInterrupted
    db, scope, _, _, _ = scenario
    repo, attempt, handle, jobs, claim, Service = reviewed(scenario)
    provider = OfflineProvider()
    service = Service(repo, provider_resolver=resolver(db, provider), admission_mode="trusted_server")
    original = repo.finish_review
    monkeypatch.setattr(repo, "finish_review", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("simulated process interruption")))
    with pytest.raises(ReviewPersistenceInterrupted):
        service.execute_review(claim.project_id, claim.run_id, guard=lambda: None, claim=claim)
    monkeypatch.setattr(repo, "finish_review", original)
    with psycopg.connect(db.migrator_dsn) as conn:
        assert conn.execute("SELECT status FROM ai_provider_attempts WHERE run_id=%s", (claim.run_id,)).fetchone()[0] == "succeeded"
        assert conn.execute("SELECT count(*) FROM summary_reviews WHERE attempt_id=%s", (attempt["attempt_id"],)).fetchone()[0] == 0
        conn.execute("UPDATE ai_jobs SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE job_id=%s", (claim.job_id,))
    replacement = jobs.claim_next("replacement", 30)
    assert replacement.run_id == claim.run_id and replacement.lease_token != claim.lease_token
    service.execute_review(replacement.project_id, replacement.run_id, guard=lambda: None, claim=replacement)
    assert provider.calls == 1
    assert repo.attempt(scope, claim.project_id, attempt["attempt_id"])["review"] is not None


def test_expired_dispatched_unknown_reconciled_never_redispatched(scenario):
    db, scope, _, _, _ = scenario
    repo, attempt, handle, jobs, claim, Service = reviewed(scenario)
    with psycopg.connect(db.migrator_dsn) as conn:
        conn.execute("INSERT INTO ai_provider_attempts(attempt_id,run_id,provider,model_id,prompt_version,status,request_fingerprint,schema_name) "
            "VALUES(%s,%s,'offline','offline','summary-review-v1','dispatched','unknown','SummaryReviewV1')",
            (claim.run_id + ":summary_review:1", claim.run_id))
        conn.execute("UPDATE ai_jobs SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE job_id=%s", (claim.job_id,))
    assert jobs.claim_next("replacement", 30) is None
    result = repo.attempt(scope, claim.project_id, attempt["attempt_id"])
    assert result["run_status"] == "reconciliation_required" and result["content"] == " 原文 " and result["review"] is None
    with psycopg.connect(db.migrator_dsn) as conn:
        assert conn.execute("SELECT status FROM ai_provider_attempts WHERE run_id=%s", (claim.run_id,)).fetchone()[0] == "dispatched"


def test_cancel_while_dispatched_keeps_ledger_and_rejects_late_review(scenario):
    from app.ports.planning_jobs import PlanningLeaseLostError
    db, scope, _, _, _ = scenario
    repo, attempt, handle, jobs, claim, Service = reviewed(scenario)
    provider = OfflineProvider()
    from app.infrastructure.providers.attempt_ledger import PgAttemptLLM
    manifest = repo.review_submission(claim)["manifest"]
    ledger = PgAttemptLLM(db.app_dsn, provider, manifest=manifest)
    ledger.generate_structured(purpose="summary.review", payload={"_project_id": claim.project_id, "content": attempt["content"],
        "rubric_snapshot": attempt["rubric_snapshot"], "_summary_claim": {"job_id": claim.job_id, "run_id": claim.run_id,
            "project_id": claim.project_id, "actor_id": claim.actor_id, "lease_token": claim.lease_token}},
        schema_name="SummaryReviewV1", run_id=claim.run_id, attempt_id=claim.run_id+":summary_review:1")
    with psycopg.connect(db.migrator_dsn) as conn:
        version = conn.execute("SELECT version FROM ai_runs WHERE run_id=%s", (claim.run_id,)).fetchone()[0]
    canceled = repo.cancel_review(scope, claim.project_id, attempt["attempt_id"], claim.run_id, version, "cancel")
    assert canceled["status"] == "cancelled"
    assert repo.cancel_review(scope, claim.project_id, attempt["attempt_id"], claim.run_id, version, "cancel") == canceled
    with pytest.raises(PlanningLeaseLostError):
        repo.finish_review(claim, attempt["attempt_id"], provider.payload)
    assert repo.attempt(scope, claim.project_id, attempt["attempt_id"])["review"] is None
    with psycopg.connect(db.migrator_dsn) as conn:
        assert conn.execute("SELECT status FROM ai_provider_attempts WHERE run_id=%s", (claim.run_id,)).fetchone()[0] == "succeeded"


def test_unknown_feedback_fails_honestly_original_retained(scenario):
    from app.ports.llm import LLMFailure
    db, scope, _, _, _ = scenario
    repo, attempt, handle, jobs, claim, Service = reviewed(scenario)
    provider = OfflineProvider(failure=LLMFailure("provider_transport_unknown", "unknown", dispatch_unknown=True))
    Service(repo, provider_resolver=resolver(db, provider)).execute_review(claim.project_id, claim.run_id, guard=lambda: None, claim=claim)
    assert repo.attempt(scope, claim.project_id, attempt["attempt_id"])["run_status"] == "reconciliation_required"
    assert provider.calls == 1


def test_invalid_legal_json_fails_without_repair_or_progress(scenario):
    db, scope, _, _, _ = scenario
    repo, attempt, handle, jobs, claim, Service = reviewed(scenario)
    provider = OfflineProvider(payload={"conclusion": "verified", "covered": ["x"],
                                       "gaps": [], "misconceptions": [], "questions": []})
    Service(repo, provider_resolver=resolver(db, provider)).execute_review(claim.project_id, claim.run_id, guard=lambda: None, claim=claim)
    original = repo.attempt(scope, claim.project_id, attempt["attempt_id"])
    assert original["run_status"] == "failed" and original["review"] is None and original["content"] == " 原文 "
    assert provider.calls == 1
    with psycopg.connect(db.migrator_dsn) as conn:
        assert conn.execute("SELECT status,error_class FROM ai_runs WHERE run_id=%s", (claim.run_id,)).fetchone() == ("failed", "summary_review_invalid")


def test_summary_ledger_manifest_cannot_reserve_second_key_or_fenceless_dispatch(scenario):
    from app.infrastructure.providers.attempt_ledger import PgAttemptLLM
    from app.ports.llm import LLMFailure
    db, scope, _, _, _ = scenario
    repo, attempt, handle, jobs, claim, Service = reviewed(scenario)
    provider = OfflineProvider()
    manifest = repo.review_submission(claim)["manifest"]
    payload = {"_project_id": claim.project_id, "content": attempt["content"], "rubric_snapshot": attempt["rubric_snapshot"]}
    def call(ledger, key):
        return ledger.generate_structured(purpose="summary.review", payload=payload, schema_name="SummaryReviewV1", run_id=claim.run_id, attempt_id=key)
    assert isinstance(call(PgAttemptLLM(db.app_dsn, provider), claim.run_id+":summary_review:1"), LLMFailure)
    assert isinstance(call(PgAttemptLLM(db.app_dsn, provider, manifest=manifest), claim.run_id+":summary_review:2"), LLMFailure)
    assert isinstance(call(PgAttemptLLM(db.app_dsn, provider, manifest=manifest), claim.run_id+":summary_review:1"), LLMFailure)
    assert provider.calls == 0
    repo.cancel_review(scope, claim.project_id, attempt["attempt_id"], claim.run_id, 2, "end-test")


def test_result_waits_for_run_lock_past_lease_expiry_and_commits_nothing(scenario):
    import time

    from app.ports.planning_jobs import PlanningLeaseLostError
    db, scope, _, _, _ = scenario
    repo, attempt, handle, jobs, claim, Service = reviewed(scenario)
    marker = "summary-result-expiry-" + claim.run_id
    from psycopg.conninfo import make_conninfo
    repo.dsn = make_conninfo(repo.dsn, application_name=marker)
    with psycopg.connect(db.migrator_dsn) as conn:
        conn.execute("UPDATE ai_jobs SET lease_expires_at=clock_timestamp()+interval '3 seconds' WHERE job_id=%s", (claim.job_id,))
    with psycopg.connect(db.migrator_dsn) as blocker, ThreadPoolExecutor(max_workers=1) as pool:
        blocker.execute("SELECT 1 FROM ai_runs WHERE run_id=%s FOR UPDATE", (claim.run_id,))
        pending = pool.submit(repo.finish_review, claim, attempt["attempt_id"], OfflineProvider().payload)
        try:
            with psycopg.connect(db.admin_dsn, autocommit=True) as observer:
                deadline = time.monotonic()+5
                while not observer.execute("SELECT 1 FROM pg_stat_activity WHERE application_name=%s AND wait_event_type='Lock'", (marker,)).fetchone():
                    if pending.done():
                        pending.result()
                        pytest.fail("Result unexpectedly committed without blocking")
                    assert time.monotonic() < deadline
                    time.sleep(0.01)
                observer.execute("SELECT pg_sleep(GREATEST(0,EXTRACT(EPOCH FROM lease_expires_at-clock_timestamp()))+0.05) FROM ai_jobs WHERE job_id=%s", (claim.job_id,))
        finally:
            blocker.commit()
        with pytest.raises(PlanningLeaseLostError):
            pending.result(timeout=5)
    assert repo.attempt(scope, claim.project_id, attempt["attempt_id"])["review"] is None
    # Explicit scoped cancellation clears this test's abandoned pending result; no unknown was dispatched.
    repo.cancel_review(scope, claim.project_id, attempt["attempt_id"], claim.run_id, 2, "end-test")


def test_cancel_and_review_commit_compete_atomically(scenario):
    db, scope, _, _, _ = scenario
    repo, attempt, handle, jobs, claim, Service = reviewed(scenario)
    def commit():
        try:
            return repo.finish_review(claim, attempt["attempt_id"], OfflineProvider().payload)
        except Exception:
            return "lost"
    def cancel():
        try:
            return repo.cancel_review(scope, claim.project_id, attempt["attempt_id"], claim.run_id, 2, "race-cancel")["status"]
        except AppError:
            return "lost"
    with ThreadPoolExecutor(max_workers=2) as pool:
        writes = [pool.submit(commit), pool.submit(cancel)]
        values = [result.result(timeout=5) for result in writes]
    assert values.count("lost") == 1
    final = repo.attempt(scope, claim.project_id, attempt["attempt_id"])
    assert (final["run_status"] == "succeeded") == (final["review"] is not None)


def test_thread_head_and_attempt_window_share_statement_snapshot(scenario, monkeypatch):
    import threading
    from contextlib import contextmanager
    db, scope, _, _, _ = scenario
    repo = PgSummaries(db.app_dsn)
    cmd = command(scenario)
    read_boundary, committed = threading.Event(), threading.Event()
    original_tx = repo._tx
    class Rows:
        def __init__(self, rows):
            self.rows = rows
        def fetchone(self):
            return self.rows[0] if self.rows else None
        def fetchall(self):
            return self.rows
    class Connection:
        def __init__(self, conn):
            self.conn = conn
        def execute(self, sql, params=()):
            result = self.conn.execute(sql, params)
            if "summary_position_heads" in sql:
                # Materialize the real database statement snapshot before a concurrent save.
                snapshot = result.fetchall()
                read_boundary.set()
                assert committed.wait(5)
                return Rows(snapshot)
            return result
    @contextmanager
    def reading(*args, **kwargs):
        with original_tx(*args, **kwargs) as conn:
            yield Connection(conn)
    monkeypatch.setattr(repo, "_tx", reading)
    def save_after_boundary():
        assert read_boundary.wait(5)
        PgSummaries(db.app_dsn).save(scope, cmd)
        committed.set()
    with ThreadPoolExecutor(max_workers=1) as pool:
        write = pool.submit(save_after_boundary)
        view = repo.thread(scope, *cmd.position)
        write.result(timeout=5)
    assert view["version"] == 0 and view["attempts"] == []
    next_view = PgSummaries(db.app_dsn).thread(scope, *cmd.position)
    assert next_view["version"] == 1 and next_view["attempts"][0]["version"] == 1


def test_cancel_before_ledger_reservation_sends_no_provider_request(scenario):
    db, scope, _, _, _ = scenario
    repo, attempt, handle, jobs, claim, Service = reviewed(scenario)
    provider = OfflineProvider()
    def cancel_then_resolve(*args):
        with psycopg.connect(db.migrator_dsn) as conn:
            version = conn.execute("SELECT version FROM ai_runs WHERE run_id=%s", (claim.run_id,)).fetchone()[0]
        repo.cancel_review(scope, claim.project_id, attempt["attempt_id"], claim.run_id, version, "cancel-before-dispatch")
        return resolver(db, provider)(*args)
    from app.ports.planning_jobs import PlanningLeaseLostError
    with pytest.raises(PlanningLeaseLostError):
        Service(repo, provider_resolver=cancel_then_resolve).execute_review(claim.project_id, claim.run_id, guard=lambda: None, claim=claim)
    assert provider.calls == 0


def test_model_context_omits_private_bindings_but_local_snapshot_keeps_them(scenario):
    import json

    from app.infrastructure.db.learning_resources import PgLearningResources
    db, scope, cmd, _, current = scenario
    position = {"project_id": cmd.project_id, "plan_id": cmd.plan_id, "stage_id": cmd.stage_id,
                "unit_id": current.unit_links[0].unit_id}
    PgLearningResources(db.app_dsn).select(scope, position, {"resource_id": "private-sentinel", "project_id": cmd.project_id,
        "url": "https://private.invalid/private-sentinel", "title": "private-sentinel",
        "source_note": "private-sentinel note", "media_type": "text", "language": "zh", "provenance": "user_provided",
        "verification_status": "unverified", "source_version": 1})
    repo, attempt, handle, jobs, claim, Service = reviewed(scenario)
    assert "private-sentinel" in json.dumps(attempt["rubric_snapshot"])
    provider = OfflineProvider()
    Service(repo, provider_resolver=resolver(db, provider)).execute_review(claim.project_id, claim.run_id, guard=lambda: None, claim=claim)
    assert "private-sentinel" not in json.dumps(provider.payloads)
    assert "source_snapshot" not in provider.payloads[0]["rubric_snapshot"]
    assert "private-sentinel" in json.dumps(repo.attempt(scope, claim.project_id, attempt["attempt_id"])["rubric_snapshot"])


def test_snapshot_immutable_history_cross_owner_forged_scope_wrong_position(scenario):
    from app.api.v1.summary_schemas import SummaryAttemptView
    db, scope, _, _, _ = scenario
    repo = PgSummaries(db.app_dsn)
    cmd = command(scenario)
    original = repo.save(scope, cmd)["attempt"]
    with psycopg.connect(db.migrator_dsn) as conn:
        conn.execute("UPDATE learning_units SET title='later title',objectives='[\"later objective\"]' WHERE unit_id=%s", (cmd.unit_id,))
    assert repo.attempt(scope, cmd.project_id, original["attempt_id"])["rubric_snapshot"] == original["rubric_snapshot"]
    forged = replace(scope, actor_id="forged", learning_project_scope=(cmd.project_id,))
    with pytest.raises(AppError) as denied:
        repo.attempt(forged, cmd.project_id, original["attempt_id"])
    assert denied.value.http_status == 403
    with psycopg.connect(db.app_dsn) as conn:
        conn.execute("SELECT set_config('app.actor_id','forged',true),set_config('app.project_id',%s,true)", (cmd.project_id,))
        assert conn.execute("SELECT attempt_id FROM summary_attempts WHERE attempt_id=%s", (original["attempt_id"],)).fetchone() is None
    with pytest.raises(AppError) as wrong:
        repo.save(scope, replace(cmd, stage_id="wrong-stage", idempotency_key="wrong"))
    assert wrong.value.http_status == 404
    with pytest.raises(psycopg.errors.RaiseException):
        with psycopg.connect(db.migrator_dsn) as conn:
            conn.execute("UPDATE summary_attempts SET content='rewritten' WHERE attempt_id=%s", (original["attempt_id"],))
    SummaryAttemptView.model_validate(repo.attempt(scope, cmd.project_id, original["attempt_id"]))


def test_paged_old_plan_history_legacy_feedback_and_bounded_thread(scenario):
    from app.api.v1.summary_schemas import SummaryAttemptView, SummaryHistoryView
    from app.domain.planning.models import PlanPublicationService
    from app.infrastructure.db.plan_repository import PgPlanRepository
    db, scope, _, _, current = scenario
    repo = PgSummaries(db.app_dsn)
    cmd = command(scenario)
    for n in range(22):
        repo.save(scope, replace(cmd, content=str(n), expected_version=n, idempotency_key=str(n)))
    thread = repo.thread(scope, *cmd.position)
    assert thread["version"] == 22 and len(thread["attempts"]) == 20 and thread["history_truncated"]
    assert thread["attempts"][0]["version"] == 3
    ids, cursor = [], None
    while True:
        page = repo.history(scope, cmd.project_id, cursor, 7)
        SummaryHistoryView.model_validate(page)
        ids.extend(x["attempt_id"] for x in page["items"])
        cursor = page["next_cursor"]
        if not cursor:
            break
    assert len(ids) == len(set(ids)) == 22
    with pytest.raises(AppError):
        repo.history(scope, cmd.project_id, "not-a-valid-cursor", 20)
    with psycopg.connect(db.migrator_dsn) as conn:
        conn.execute("INSERT INTO summary_attempts(attempt_id,project_id,unit_id,content,attempt_no,rubric_version) "
            "VALUES('legacy-'||%s,%s,%s,' Original historical whitespace ',23,1)", (cmd.project_id, cmd.project_id, cmd.unit_id))
        conn.execute("INSERT INTO summary_reviews(review_id,project_id,attempt_id,review) VALUES('legacy-review-'||%s,%s,'legacy-'||%s,'{\"feedback\":\"old feedback\"}')",
            (cmd.project_id, cmd.project_id, cmd.project_id))
    legacy = repo.attempt(scope, cmd.project_id, "legacy-" + cmd.project_id)
    SummaryAttemptView.model_validate(legacy)
    assert legacy["content"] == " Original historical whitespace " and legacy["plan_id"] is None
    assert legacy["review"] is None and legacy["legacy_review"] == {"feedback": "old feedback"}
    assert legacy["rubric_snapshot"]["snapshot_status"] == "legacy_unfrozen"
    # Ordinary new publication retains old position and originals, with a new empty head.
    from app.core.ids import new_id
    from app.domain.planning.models import PlanDraft
    draft = PlanDraft(new_id("drf"), cmd.project_id, "", "New plan", 1, stages=current.stages,
                      unit_links=current.unit_links, stage_resources=current.stage_resources,
                      resource_snapshots=current.resource_snapshots)
    plans = PgPlanRepository(db.app_dsn)
    plans.save_draft(draft, expected_version=1)
    PlanPublicationService(plans).publish(draft=draft, presented_hash=draft.content_hash, expected_version=1, idempotency_key="next")
    newer = plans.get_current(project_id=cmd.project_id)
    assert repo.thread(scope, cmd.project_id, newer.plan_id, newer.stages[0].stage_id, cmd.unit_id)["version"] == 0
    assert repo.thread(scope, *cmd.position)["version"] == 22
    with pytest.raises(AppError) as oldsave:
        repo.save(scope, replace(cmd, expected_version=22, idempotency_key="old-save"))
    assert oldsave.value.http_status == 409
    assert repo.save(scope, replace(cmd, content="0", expected_version=0, idempotency_key="0"))["replayed"]
