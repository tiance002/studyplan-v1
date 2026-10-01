from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import psycopg
import pytest
from app.core.errors import AppError
from app.core.ids import new_id
from app.domain.enums import TaskKnowledgeRole
from app.domain.planning.models import PlanDraft, PlanPublicationService, PlanTaskKnowledgeLink, PlanTaskLink
from app.domain.prompts import PromptSaveCommand
from app.infrastructure.db.plan_repository import PgPlanRepository
from app.infrastructure.db.prompts import PgPrompts

from tests.e2e.test_b2v_http_end_to_end import migrated_db as migrated_db
from tests.integration.test_resource_changes_pg import scenario as resource_scenario  # noqa: F401
from tests.integration.test_summaries_pg import OfflineProvider as SummaryOfflineProvider
from tests.integration.test_summaries_pg import resolver

pytestmark = pytest.mark.postgres


@pytest.fixture
def prompt_scenario(resource_scenario):  # noqa: F811 - pytest fixture dependency, also re-exported for root HTTP tests
    db, scope, cmd, container, old = resource_scenario
    task, practice = "task-" + cmd.project_id, "practice-" + cmd.project_id
    node = old.stage_resources[0].node_ids[0]
    with psycopg.connect(db.migrator_dsn) as conn:
        conn.execute(
            "INSERT INTO practice_projects(practice_project_id,project_id,title,idea,status,repo_url) "
            "VALUES(%s,%s,'Prompt main project','Build a small observable tool','idea','https://private.invalid/private-project-sentinel')",
            (practice, cmd.project_id),
        )
        conn.execute(
            "INSERT INTO practice_tasks(task_id,project_id,practice_project_id,stable_key,title,goal,in_scope,out_scope,acceptance,status) "
            "VALUES(%s,%s,%s,'task.subject','Task subject','Explain implementation boundaries','[\"A feature\"]','[\"No invented test\"]','[\"Demonstrate an observable result\"]','pending')",
            (task, cmd.project_id, practice),
        )
    draft = PlanDraft(
        new_id("drf"),
        cmd.project_id,
        "",
        "Prompt test plan",
        1,
        stages=old.stages,
        unit_links=old.unit_links,
        task_links=(PlanTaskLink(old.stages[0].stage_id, task, 0),),
        task_knowledge_links=(PlanTaskKnowledgeLink(task, node, TaskKnowledgeRole.CORE),),
        stage_resources=old.stage_resources,
        resource_snapshots=old.resource_snapshots,
    )
    plans = PgPlanRepository(db.app_dsn)
    plans.save_draft(draft, expected_version=1)
    PlanPublicationService(plans).publish(
        draft=draft, presented_hash=draft.content_hash, expected_version=1, idempotency_key="prompt-plan"
    )
    current = plans.get_current(project_id=cmd.project_id)
    return (
        db,
        scope,
        PromptSaveCommand(
            cmd.project_id, current.plan_id, current.stages[0].stage_id, task, " \n鍐欚煓俓t ", 0, "save"
        ),
        container,
        current,
    )


def test_raw_save_exact_and_explicit_revision_exports(prompt_scenario):
    db, scope, cmd, _, _ = prompt_scenario
    repo = PgPrompts(db.app_dsn)
    result = repo.save(scope, cmd)
    assert result["revision"]["user_draft"] == cmd.user_draft
    assert result["thread"]["version"] == 1
    assert repo.save(scope, cmd) == dict(result, replayed=True)
    first = result["revision"]
    repo.save(scope, replace(cmd, user_draft="Later original", expected_version=1, idempotency_key="later"))
    raw = repo.export(scope, cmd.project_id, first["revision_id"], "raw", "raw")
    assert raw["export_text"] == cmd.user_draft
    assert repo.export(scope, cmd.project_id, first["revision_id"], "raw", "raw") == raw
    assert repo.get_export(scope, cmd.project_id, raw["export_id"]) == raw
    implementation = repo.export(
        scope, cmd.project_id, first["revision_id"], "implementation", "implementation"
    )
    assert implementation["export_text"].endswith(cmd.user_draft)
    assert "Demonstrate an observable result" in implementation["export_text"]
    assert "Later original" not in implementation["export_text"]






class OfflineProvider(SummaryOfflineProvider):
    prompt_version = "prompt-review-v1"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if "payload" not in kwargs:
            self.payload = {
                "strengths": ["Scope is clear"],
                "gaps": ["Add an observable check"],
                "suggestions": ["Show expected inputs"],
            }


def reviewed(prompt_scenario):
    from app.application.model_binding import SubmissionBinding
    from app.application.planning_budget import BudgetPolicy
    from app.application.prompts import PromptService
    from app.domain.prompts import prompt_manifest
    from app.infrastructure.db.job_repository import PgPlanningJobRepository

    db, scope, cmd, _, _ = prompt_scenario
    repo = PgPrompts(db.app_dsn)
    revision = repo.save(scope, cmd)["revision"]
    manifest = prompt_manifest(SubmissionBinding("test:1", BudgetPolicy(20, 20, 20, 20, 20, 20)))
    handle = repo.enqueue_review(scope, cmd.project_id, revision["revision_id"], "review", manifest)
    jobs = PgPlanningJobRepository(db.app_dsn, admission_mode="trusted_server")
    claim = jobs.claim_next("prompt-test", 30)
    assert claim is not None and claim.run_id == handle["run_id"]
    assert jobs.read_claim_submission(claim)["kind"] == "prompt_review_submission"
    return repo, revision, handle, jobs, claim, PromptService


def test_concurrent_cas_and_receipt_heterogeneous_body(prompt_scenario):
    db, scope, cmd, _, _ = prompt_scenario
    repo = PgPrompts(db.app_dsn)

    def save(key):
        try:
            return repo.save(scope, replace(cmd, idempotency_key=key))["thread"]["version"]
        except AppError as error:
            return error.http_status

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(save, ["a", "b"])) == [1, 409]
    retained = repo.history(scope, cmd.project_id)["items"][0]
    with pytest.raises(AppError) as conflict:
        repo.save(scope, replace(cmd, user_draft="different", idempotency_key="a"))
    assert conflict.value.http_status == 409
    with psycopg.connect(db.migrator_dsn) as conn:
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
    assert retained["version"] == 1


def test_owner_rls_wrong_stage_and_immutable_snapshots(prompt_scenario):
    db, scope, cmd, _, _ = prompt_scenario
    repo = PgPrompts(db.app_dsn)
    revision = repo.save(scope, cmd)["revision"]
    with psycopg.connect(db.migrator_dsn) as conn:
        conn.execute(
            "UPDATE practice_tasks SET title='Later title',acceptance='[\"later check\"]' WHERE task_id=%s",
            (cmd.task_id,),
        )
    assert (
        repo.attempt(scope, cmd.project_id, revision["revision_id"])["task_snapshot"]
        == revision["task_snapshot"]
    )
    with pytest.raises(AppError) as denied:
        repo.attempt(
            replace(scope, actor_id="forged", learning_project_scope=(cmd.project_id,)),
            cmd.project_id,
            revision["revision_id"],
        )
    assert denied.value.http_status == 403
    with psycopg.connect(db.app_dsn) as conn:
        conn.execute(
            "SELECT set_config('app.actor_id','forged',true),set_config('app.project_id',%s,true)",
            (cmd.project_id,),
        )
        assert (
            conn.execute(
                "SELECT revision_id FROM prompt_revisions WHERE revision_id=%s", (revision["revision_id"],)
            ).fetchone()
            is None
        )
        assert (
            conn.execute(
                "SELECT export_id FROM prompt_exports WHERE project_id=%s", (cmd.project_id,)
            ).fetchone()
            is None
        )
    with pytest.raises(AppError) as wrong:
        repo.save(scope, replace(cmd, stage_id="wrong-stage", idempotency_key="wrong"))
    assert wrong.value.http_status == 404
    with pytest.raises(psycopg.errors.RaiseException):
        with psycopg.connect(db.migrator_dsn) as conn:
            conn.execute(
                "UPDATE prompt_revisions SET user_draft='rewrite' WHERE revision_id=%s",
                (revision["revision_id"],),
            )


def test_full_40k_export_and_wrong_key_body(prompt_scenario):
    db, scope, cmd, _, _ = prompt_scenario
    repo = PgPrompts(db.app_dsn)
    raw = " " + "写" * 39998 + "\n"
    revision = repo.save(scope, replace(cmd, user_draft=raw))["revision"]
    exported = repo.export(scope, cmd.project_id, revision["revision_id"], "implementation", "export")
    assert len(exported["export_text"]) > 40000 and exported["export_text"].endswith(raw)
    with pytest.raises(AppError) as conflict:
        repo.export(scope, cmd.project_id, revision["revision_id"], "raw", "export")
    assert conflict.value.http_status == 409


def test_shared_summary_prompt_pending_limit_three(prompt_scenario):
    from app.application.model_binding import SubmissionBinding
    from app.application.planning_budget import BudgetPolicy
    from app.domain.prompts import prompt_manifest
    from app.domain.summaries import SummarySaveCommand, summary_manifest
    from app.infrastructure.db.summaries import PgSummaries

    db, scope, cmd, _, current = prompt_scenario
    binding = SubmissionBinding("test:1", BudgetPolicy(20, 20, 20, 20, 20, 20))
    summaries = PgSummaries(db.app_dsn)
    sumcmd = SummarySaveCommand(
        cmd.project_id, cmd.plan_id, cmd.stage_id, current.unit_links[0].unit_id, "short", 0, "summary"
    )
    original = summaries.save(scope, sumcmd)["attempt"]
    summaries.enqueue_review(
        scope, cmd.project_id, original["attempt_id"], "summary-review", summary_manifest(binding)
    )
    repo = PgPrompts(db.app_dsn)
    rows = [
        repo.save(scope, replace(cmd, user_draft=str(n), expected_version=n, idempotency_key=str(n)))[
            "revision"
        ]
        for n in range(3)
    ]
    handles = []
    for n in range(2):
        handles.append(
            repo.enqueue_review(
                scope, cmd.project_id, rows[n]["revision_id"], "review" + str(n), prompt_manifest(binding)
            )
        )
    with pytest.raises(AppError) as limit:
        repo.enqueue_review(scope, cmd.project_id, rows[2]["revision_id"], "fourth", prompt_manifest(binding))
    assert limit.value.http_status == 409
    with psycopg.connect(db.migrator_dsn) as conn:
        pending = conn.execute(
            "SELECT run_id,version FROM ai_runs WHERE project_id=%s", (cmd.project_id,)
        ).fetchall()
    for run, version in pending:
        if run == handles[0]["run_id"]:
            repo.cancel_review(scope, cmd.project_id, rows[0]["revision_id"], run, version, "end0")
        elif run == handles[1]["run_id"]:
            repo.cancel_review(scope, cmd.project_id, rows[1]["revision_id"], run, version, "end1")
        else:
            summaries.cancel_review(
                scope, cmd.project_id, original["attempt_id"], run, version, "end-summary"
            )


def test_saved_original_pinned_and_local_private_context_omitted(prompt_scenario):
    import json

    from app.api.v1.prompt_schemas import PromptRevisionView

    db, scope, cmd, _, _ = prompt_scenario
    repo, revision, handle, jobs, claim, Service = reviewed(prompt_scenario)
    assert "private-project-sentinel" in json.dumps(revision["task_snapshot"])
    newer = repo.save(
        scope, replace(cmd, user_draft="New editor", expected_version=1, idempotency_key="second")
    )["revision"]
    provider = OfflineProvider()
    service = Service(repo, provider_resolver=resolver(db, provider), admission_mode="trusted_server")
    service.execute_review(claim.project_id, claim.run_id, guard=lambda: None, claim=claim)
    result = repo.attempt(scope, cmd.project_id, revision["revision_id"])
    PromptRevisionView.model_validate(result)
    assert (
        result["run_status"] == "succeeded" and result["user_draft"] == cmd.user_draft and provider.calls == 1
    )
    assert repo.attempt(scope, cmd.project_id, newer["revision_id"])["review"] is None
    assert "private-project-sentinel" not in json.dumps(provider.payloads)
    assert "practice_project" not in provider.payloads[0]["task_snapshot"]
    assert "node_id" not in json.dumps(provider.payloads[0]["task_snapshot"])
    assert service.request_review(scope, cmd.project_id, revision["revision_id"], "review", True) == handle
    assert (
        service.request_review(scope, cmd.project_id, revision["revision_id"], "new-click", True)["run_id"]
        == handle["run_id"]
    )


def test_retained_provider_success_replays_after_business_crash_without_redispatch(
    prompt_scenario, monkeypatch
):
    from app.ports.summaries import ReviewPersistenceInterrupted

    db, scope, cmd, _, _ = prompt_scenario
    repo, attempt, handle, jobs, claim, Service = reviewed(prompt_scenario)
    provider = OfflineProvider()
    service = Service(repo, provider_resolver=resolver(db, provider), admission_mode="trusted_server")
    original = repo.finish_review
    monkeypatch.setattr(
        repo,
        "finish_review",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("simulated process interruption")),
    )
    with pytest.raises(ReviewPersistenceInterrupted):
        service.execute_review(claim.project_id, claim.run_id, guard=lambda: None, claim=claim)
    monkeypatch.setattr(repo, "finish_review", original)
    with psycopg.connect(db.migrator_dsn) as conn:
        assert (
            conn.execute(
                "SELECT status FROM ai_provider_attempts WHERE run_id=%s", (claim.run_id,)
            ).fetchone()[0]
            == "succeeded"
        )
        assert (
            conn.execute(
                "SELECT count(*) FROM prompt_reviews WHERE revision_id=%s", (attempt["revision_id"],)
            ).fetchone()[0]
            == 0
        )
        conn.execute(
            "UPDATE ai_jobs SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE job_id=%s",
            (claim.job_id,),
        )
    replacement = jobs.claim_next("replacement", 30)
    assert replacement.run_id == claim.run_id and replacement.lease_token != claim.lease_token
    service.execute_review(replacement.project_id, replacement.run_id, guard=lambda: None, claim=replacement)
    assert provider.calls == 1
    assert repo.attempt(scope, claim.project_id, attempt["revision_id"])["review"] is not None


def test_expired_dispatched_unknown_reconciled_never_redispatched(prompt_scenario):
    db, scope, cmd, _, _ = prompt_scenario
    repo, attempt, handle, jobs, claim, Service = reviewed(prompt_scenario)
    with psycopg.connect(db.migrator_dsn) as conn:
        conn.execute(
            "INSERT INTO ai_provider_attempts(attempt_id,run_id,provider,model_id,prompt_version,status,request_fingerprint,schema_name) "
            "VALUES(%s,%s,'offline','offline','prompt-review-v1','dispatched','unknown','PromptReviewV1')",
            (claim.run_id + ":prompt_review:1", claim.run_id),
        )
        conn.execute(
            "UPDATE ai_jobs SET lease_expires_at=clock_timestamp()-interval '1 second' WHERE job_id=%s",
            (claim.job_id,),
        )
    assert jobs.claim_next("replacement", 30) is None
    result = repo.attempt(scope, claim.project_id, attempt["revision_id"])
    assert (
        result["run_status"] == "reconciliation_required"
        and result["user_draft"] == cmd.user_draft
        and result["review"] is None
    )
    with psycopg.connect(db.migrator_dsn) as conn:
        assert (
            conn.execute(
                "SELECT status FROM ai_provider_attempts WHERE run_id=%s", (claim.run_id,)
            ).fetchone()[0]
            == "dispatched"
        )


def test_cancel_while_dispatched_keeps_ledger_and_rejects_late_review(prompt_scenario):
    from app.ports.planning_jobs import PlanningLeaseLostError

    db, scope, cmd, _, _ = prompt_scenario
    repo, attempt, handle, jobs, claim, Service = reviewed(prompt_scenario)
    provider = OfflineProvider()
    from app.infrastructure.providers.attempt_ledger import PgAttemptLLM

    manifest = repo.review_submission(claim)["manifest"]
    ledger = PgAttemptLLM(db.app_dsn, provider, manifest=manifest)
    ledger.generate_structured(
        purpose="prompt.review",
        payload={
            "_project_id": claim.project_id,
            "user_draft": attempt["user_draft"],
            "task_snapshot": attempt["task_snapshot"],
            "_prompt_claim": {
                "job_id": claim.job_id,
                "run_id": claim.run_id,
                "project_id": claim.project_id,
                "actor_id": claim.actor_id,
                "lease_token": claim.lease_token,
            },
        },
        schema_name="PromptReviewV1",
        run_id=claim.run_id,
        attempt_id=claim.run_id + ":prompt_review:1",
    )
    with psycopg.connect(db.migrator_dsn) as conn:
        version = conn.execute("SELECT version FROM ai_runs WHERE run_id=%s", (claim.run_id,)).fetchone()[0]
    canceled = repo.cancel_review(
        scope, claim.project_id, attempt["revision_id"], claim.run_id, version, "cancel"
    )
    assert canceled["status"] == "cancelled"
    assert (
        repo.cancel_review(scope, claim.project_id, attempt["revision_id"], claim.run_id, version, "cancel")
        == canceled
    )
    with pytest.raises(PlanningLeaseLostError):
        repo.finish_review(claim, attempt["revision_id"], provider.payload)
    assert repo.attempt(scope, claim.project_id, attempt["revision_id"])["review"] is None
    with psycopg.connect(db.migrator_dsn) as conn:
        assert (
            conn.execute(
                "SELECT status FROM ai_provider_attempts WHERE run_id=%s", (claim.run_id,)
            ).fetchone()[0]
            == "succeeded"
        )


def test_unknown_feedback_fails_honestly_original_retained(prompt_scenario):
    from app.ports.llm import LLMFailure

    db, scope, cmd, _, _ = prompt_scenario
    repo, attempt, handle, jobs, claim, Service = reviewed(prompt_scenario)
    provider = OfflineProvider(
        failure=LLMFailure("provider_transport_unknown", "unknown", dispatch_unknown=True)
    )
    Service(repo, provider_resolver=resolver(db, provider)).execute_review(
        claim.project_id, claim.run_id, guard=lambda: None, claim=claim
    )
    assert (
        repo.attempt(scope, claim.project_id, attempt["revision_id"])["run_status"]
        == "reconciliation_required"
    )
    assert provider.calls == 1


def test_result_waits_for_run_lock_past_lease_expiry_and_commits_nothing(prompt_scenario):
    import time

    from app.ports.planning_jobs import PlanningLeaseLostError

    db, scope, cmd, _, _ = prompt_scenario
    repo, attempt, handle, jobs, claim, Service = reviewed(prompt_scenario)
    marker = "summary-result-expiry-" + claim.run_id
    from psycopg.conninfo import make_conninfo

    repo.dsn = make_conninfo(repo.dsn, application_name=marker)
    with psycopg.connect(db.migrator_dsn) as conn:
        conn.execute(
            "UPDATE ai_jobs SET lease_expires_at=clock_timestamp()+interval '3 seconds' WHERE job_id=%s",
            (claim.job_id,),
        )
    with psycopg.connect(db.migrator_dsn) as blocker, ThreadPoolExecutor(max_workers=1) as pool:
        blocker.execute("SELECT 1 FROM ai_runs WHERE run_id=%s FOR UPDATE", (claim.run_id,))
        pending = pool.submit(repo.finish_review, claim, attempt["revision_id"], OfflineProvider().payload)
        try:
            with psycopg.connect(db.admin_dsn, autocommit=True) as observer:
                deadline = time.monotonic() + 5
                while not observer.execute(
                    "SELECT 1 FROM pg_stat_activity WHERE application_name=%s AND wait_event_type='Lock'",
                    (marker,),
                ).fetchone():
                    if pending.done():
                        pending.result()
                        pytest.fail("Result unexpectedly committed without blocking")
                    assert time.monotonic() < deadline
                    time.sleep(0.01)
                observer.execute(
                    "SELECT pg_sleep(GREATEST(0,EXTRACT(EPOCH FROM lease_expires_at-clock_timestamp()))+0.05) FROM ai_jobs WHERE job_id=%s",
                    (claim.job_id,),
                )
        finally:
            blocker.commit()
        with pytest.raises(PlanningLeaseLostError):
            pending.result(timeout=5)
    assert repo.attempt(scope, claim.project_id, attempt["revision_id"])["review"] is None
    # Explicit scoped cancellation clears this test's abandoned pending result; no unknown was dispatched.
    repo.cancel_review(scope, claim.project_id, attempt["revision_id"], claim.run_id, 2, "end-test")


def test_cancel_and_review_commit_compete_atomically(prompt_scenario):
    db, scope, cmd, _, _ = prompt_scenario
    repo, attempt, handle, jobs, claim, Service = reviewed(prompt_scenario)

    def commit():
        try:
            return repo.finish_review(claim, attempt["revision_id"], OfflineProvider().payload)
        except Exception:
            return "lost"

    def cancel():
        try:
            return repo.cancel_review(
                scope, claim.project_id, attempt["revision_id"], claim.run_id, 2, "race-cancel"
            )["status"]
        except AppError:
            return "lost"

    with ThreadPoolExecutor(max_workers=2) as pool:
        writes = [pool.submit(commit), pool.submit(cancel)]
        values = [result.result(timeout=5) for result in writes]
    assert values.count("lost") == 1
    final = repo.attempt(scope, claim.project_id, attempt["revision_id"])
    assert (final["run_status"] == "succeeded") == (final["review"] is not None)


def test_cancel_before_ledger_reservation_sends_no_provider_request(prompt_scenario):
    db, scope, cmd, _, _ = prompt_scenario
    repo, attempt, handle, jobs, claim, Service = reviewed(prompt_scenario)
    provider = OfflineProvider()

    def cancel_then_resolve(*args):
        with psycopg.connect(db.migrator_dsn) as conn:
            version = conn.execute("SELECT version FROM ai_runs WHERE run_id=%s", (claim.run_id,)).fetchone()[
                0
            ]
        repo.cancel_review(
            scope, claim.project_id, attempt["revision_id"], claim.run_id, version, "cancel-before-dispatch"
        )
        return resolver(db, provider)(*args)

    from app.ports.planning_jobs import PlanningLeaseLostError

    with pytest.raises(PlanningLeaseLostError):
        Service(repo, provider_resolver=cancel_then_resolve).execute_review(
            claim.project_id, claim.run_id, guard=lambda: None, claim=claim
        )
    assert provider.calls == 0


def test_old_plan_history_legacy_feedback_and_bounded_window(prompt_scenario):
    from app.api.v1.prompt_schemas import PromptHistoryView, PromptRevisionView

    db, scope, cmd, _, current = prompt_scenario
    repo = PgPrompts(db.app_dsn)
    for n in range(22):
        repo.save(scope, replace(cmd, user_draft=str(n), expected_version=n, idempotency_key=str(n)))
    thread = repo.thread(scope, *cmd.position)
    assert thread["version"] == 22 and len(thread["revisions"]) == 20 and thread["history_truncated"]
    assert thread["revisions"][0]["version"] == 3
    ids, cursor = [], None
    while True:
        page = repo.history(scope, cmd.project_id, cursor, 7)
        PromptHistoryView.model_validate(page)
        ids.extend(item["revision_id"] for item in page["items"])
        cursor = page["next_cursor"]
        if not cursor:
            break
    assert len(ids) == len(set(ids)) == 22
    with pytest.raises(AppError):
        repo.history(scope, cmd.project_id, "invalid", 20)
    with psycopg.connect(db.migrator_dsn) as conn:
        conn.execute(
            "INSERT INTO prompt_revisions(revision_id,project_id,task_id,revision,user_draft) VALUES(%s,%s,%s,23,' Legacy whitespace ')",
            ("legacy-" + cmd.project_id, cmd.project_id, cmd.task_id),
        )
        conn.execute(
            'INSERT INTO prompt_reviews(review_id,project_id,revision_id,review) VALUES(%s,%s,%s,\'{"feedback":"old feedback"}\')',
            ("legacy-review-" + cmd.project_id, cmd.project_id, "legacy-" + cmd.project_id),
        )
    legacy = repo.attempt(scope, cmd.project_id, "legacy-" + cmd.project_id)
    PromptRevisionView.model_validate(legacy)
    assert (
        legacy["plan_id"] is None
        and legacy["review"] is None
        and legacy["legacy_review"] == {"feedback": "old feedback"}
    )
    assert legacy["task_snapshot"]["snapshot_status"] == "legacy_unfrozen"
    draft = PlanDraft(
        new_id("drf"),
        cmd.project_id,
        "",
        "Next plan",
        2,
        stages=current.stages,
        unit_links=current.unit_links,
        task_links=current.task_links,
        task_knowledge_links=current.task_knowledge_links,
        stage_resources=current.stage_resources,
        resource_snapshots=current.resource_snapshots,
    )
    plans = PgPlanRepository(db.app_dsn)
    plans.save_draft(draft, expected_version=2)
    PlanPublicationService(plans).publish(
        draft=draft, presented_hash=draft.content_hash, expected_version=2, idempotency_key="next"
    )
    nextplan = plans.get_current(project_id=cmd.project_id)
    assert (
        repo.thread(scope, cmd.project_id, nextplan.plan_id, nextplan.stages[0].stage_id, cmd.task_id)[
            "version"
        ]
        == 0
    )
    assert repo.thread(scope, *cmd.position)["version"] == 22
    with pytest.raises(AppError) as oldsave:
        repo.save(scope, replace(cmd, expected_version=22, idempotency_key="old-save"))
    assert oldsave.value.http_status == 409
    assert repo.save(scope, replace(cmd, user_draft="0", idempotency_key="0"))["replayed"]
    old = repo.attempt(scope, cmd.project_id, ids[0])
    assert (
        repo.export(scope, cmd.project_id, old["revision_id"], "raw", "old-export")["export_text"]
        == old["user_draft"]
    )


def test_prompt_ledger_rejects_unbounded_wrong_key_and_fenceless_dispatch(prompt_scenario):
    from app.infrastructure.providers.attempt_ledger import PgAttemptLLM
    from app.ports.llm import LLMFailure

    db, scope, cmd, _, _ = prompt_scenario
    repo, revision, handle, jobs, claim, Service = reviewed(prompt_scenario)
    provider = OfflineProvider()
    manifest = repo.review_submission(claim)["manifest"]

    def call(ledger, key):
        return ledger.generate_structured(
            purpose="prompt.review",
            payload={"_project_id": cmd.project_id, "user_draft": cmd.user_draft, "task_snapshot": {}},
            schema_name="PromptReviewV1",
            run_id=claim.run_id,
            attempt_id=key,
        )

    assert isinstance(call(PgAttemptLLM(db.app_dsn, provider), claim.run_id + ":prompt_review:1"), LLMFailure)
    assert isinstance(
        call(PgAttemptLLM(db.app_dsn, provider, manifest=manifest), claim.run_id + ":prompt_review:2"),
        LLMFailure,
    )
    assert isinstance(
        call(PgAttemptLLM(db.app_dsn, provider, manifest=manifest), claim.run_id + ":prompt_review:1"),
        LLMFailure,
    )
    assert provider.calls == 0
    repo.cancel_review(scope, cmd.project_id, revision["revision_id"], claim.run_id, 2, "end")


def test_invalid_json_feedback_fails_without_repair(prompt_scenario):
    db, scope, cmd, _, _ = prompt_scenario
    repo, revision, handle, jobs, claim, Service = reviewed(prompt_scenario)
    provider = OfflineProvider(payload={"strengths": ["x"], "gaps": [], "suggestions": [], "verified": True})
    Service(repo, provider_resolver=resolver(db, provider)).execute_review(
        claim.project_id, claim.run_id, guard=lambda: None, claim=claim
    )
    final = repo.attempt(scope, cmd.project_id, revision["revision_id"])
    assert (
        final["run_status"] == "failed"
        and final["review"] is None
        and final["user_draft"] == cmd.user_draft
        and provider.calls == 1
    )


def test_thread_head_and_attempt_window_share_statement_snapshot(prompt_scenario, monkeypatch):
    import threading
    from contextlib import contextmanager
    db, scope, _, _, _ = prompt_scenario
    repo = PgPrompts(db.app_dsn)
    cmd = prompt_scenario[2]
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
            if "prompt_position_heads" in sql:
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
        PgPrompts(db.app_dsn).save(scope, cmd)
        committed.set()
    with ThreadPoolExecutor(max_workers=1) as pool:
        write = pool.submit(save_after_boundary)
        view = repo.thread(scope, *cmd.position)
        write.result(timeout=5)
    assert view["version"] == 0 and view["revisions"] == []
    next_view = PgPrompts(db.app_dsn).thread(scope, *cmd.position)
    assert next_view["version"] == 1 and next_view["revisions"][0]["version"] == 1
