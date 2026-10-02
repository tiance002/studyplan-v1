from dataclasses import replace

import psycopg
import pytest
from app.core.errors import AppError
from app.core.ids import new_id
from app.domain.planning.models import PlanDraft, PlanPublicationService
from app.domain.practice_changes import KnowledgeChoice, PracticeChangeCommand, TaskChange
from app.infrastructure.db.plan_repository import PgPlanRepository
from app.infrastructure.db.practice_changes import PgPracticeChanges

from tests.e2e.test_b2v_http_end_to_end import migrated_db as migrated_db
from tests.integration.test_prompts_pg import prompt_scenario as prompt_scenario
from tests.integration.test_prompts_pg import resource_scenario as resource_scenario

pytestmark = pytest.mark.postgres


@pytest.fixture
def practice_scenario(prompt_scenario):
    db, scope, cmd, container, current = prompt_scenario
    context = container.prompt_service.thread(scope, *cmd.position)
    main = context["practice_project"]
    return (
        db,
        scope,
        PracticeChangeCommand(
            cmd.project_id,
            cmd.plan_id,
            main["practice_project_id"],
            "My own project",
            "Build a personally selected observable product",
            None,
            (),
            current.version,
            "copy_active",
            "preview",
        ),
        container,
        current,
    )


def test_preview_then_publish_new_identity_preserves_old_plan(practice_scenario):
    db, scope, cmd, _, current = practice_scenario
    repo = PgPracticeChanges(db.app_dsn)
    preview = repo.preview(scope, cmd)
    assert preview["before"]["practice_project_id"] != preview["after"]["practice_project_id"]
    assert preview["impact"]["cloned_task_count"] == 1
    result = repo.decide(
        scope,
        cmd.project_id,
        preview["proposal_id"],
        "confirm",
        cmd.expected_version,
        preview["preview_hash"],
        "confirm",
        True,
    )
    assert result["created"] and result["revision"] == current.revision + 1
    assert (
        repo.decide(
            scope,
            cmd.project_id,
            preview["proposal_id"],
            "confirm",
            cmd.expected_version,
            preview["preview_hash"],
            "confirm",
            True,
        )
        == result
    )
    with psycopg.connect(db.migrator_dsn) as conn:
        assert (
            conn.execute(
                "SELECT title FROM practice_projects WHERE practice_project_id=%s", (cmd.practice_project_id,)
            ).fetchone()[0]
            == preview["before"]["title"]
        )
        assert (
            conn.execute(
                "SELECT task_id FROM plan_task_links WHERE project_id=%s AND plan_id=%s",
                (cmd.project_id, current.plan_id),
            ).fetchone()[0]
            == preview["task_changes"][0]["before"]["task_id"]
        )
        assert (
            conn.execute("SELECT count(*) FROM ai_runs WHERE project_id=%s", (cmd.project_id,)).fetchone()[0]
            == 0
        )


@pytest.mark.parametrize("kind", ["resource", "practice"])
@pytest.mark.parametrize("action", ["save", "publish"])
def test_protected_link_is_rechecked_after_waiting_for_advisory(practice_scenario, kind, action):
    import time
    from concurrent.futures import ThreadPoolExecutor

    from app.infrastructure.db.planning_fence import lock_plan_version
    from psycopg.conninfo import make_conninfo

    db, scope, cmd, _, current = practice_scenario
    draft = PlanDraft(
        new_id("drf"),
        cmd.project_id,
        "",
        "Protected candidate",
        current.revision + 1,
        stages=current.stages,
        unit_links=current.unit_links,
        task_links=current.task_links,
        task_knowledge_links=current.task_knowledge_links,
        stage_resources=current.stage_resources,
        resource_snapshots=current.resource_snapshots,
    )
    repo = PgPlanRepository(db.app_dsn)
    repo.save_draft(draft, expected_version=current.version)
    marker = "protected-barrier-" + draft.draft_id
    ordinary = PgPlanRepository(make_conninfo(db.app_dsn, application_name=marker))

    def write():
        if action == "save":
            ordinary.save_draft(
                replace(draft, goal_snapshot="Bypass"),
                expected_hash=draft.content_hash,
                expected_version=current.version,
            )
        else:
            PlanPublicationService(ordinary).publish(
                draft=draft,
                presented_hash=draft.content_hash,
                expected_version=current.version,
                idempotency_key="bypass",
            )

    with psycopg.connect(db.migrator_dsn) as blocker, ThreadPoolExecutor(max_workers=1) as pool:
        lock_plan_version(blocker, cmd.project_id, None)
        pending = pool.submit(write)
        with psycopg.connect(db.admin_dsn, autocommit=True) as observer:
            deadline = time.monotonic() + 5
            while not observer.execute(
                "SELECT 1 FROM pg_stat_activity WHERE application_name=%s AND wait_event_type='Lock'",
                (marker,),
            ).fetchone():
                if pending.done():
                    pending.result()
                    pytest.fail("ordinary writer did not wait")
                assert time.monotonic() < deadline
                time.sleep(0.01)
        proposal = new_id("protected")
        if kind == "practice":
            blocker.execute(
                "INSERT INTO practice_change_proposals(proposal_id,project_id,actor_id,draft_id,base_plan_id,base_revision,base_version,status,preview_hash,payload) "
                "VALUES(%s,%s,%s,%s,%s,%s,%s,'pending','hash','{}')",
                (
                    proposal,
                    cmd.project_id,
                    scope.actor_id,
                    draft.draft_id,
                    current.plan_id,
                    current.revision,
                    current.version,
                ),
            )
        else:
            blocker.execute(
                "INSERT INTO resource_change_proposals(proposal_id,project_id,actor_id,draft_id,base_plan_id,base_revision,status,preview_hash,catalog_digest,payload) "
                "VALUES(%s,%s,%s,%s,%s,%s,'pending','hash','hash','{}')",
                (proposal, cmd.project_id, scope.actor_id, draft.draft_id, current.plan_id, current.revision),
            )
        blocker.execute(
            f"UPDATE plan_drafts SET {kind}_change_proposal_id=%s WHERE draft_id=%s",
            (proposal, draft.draft_id),
        )
        blocker.commit()
        with pytest.raises(AppError) as denied:
            pending.result(timeout=5)
        assert denied.value.http_status == 409
    assert repo.get_current(project_id=cmd.project_id).plan_id == current.plan_id
    assert (
        repo.get_draft(project_id=cmd.project_id, draft_id=draft.draft_id).content_hash == draft.content_hash
    )


def unchanged(repo, scope, cmd):
    main = next(
        p
        for p in repo.context(scope, cmd.project_id)["practice_projects"]
        if p["practice_project_id"] == cmd.practice_project_id
    )
    return replace(cmd, title=main["title"], idea=main["idea"], repo_url=main["repo_url"])


def edit(task, **changes):
    values = dict(
        operation="update",
        client_key="edit",
        task_id=task["task_id"],
        stage_id=task["stage_id"],
        title="A revised task",
        goal=task["goal"],
        in_scope=tuple(task["in_scope"]),
        out_scope=tuple(task["out_scope"]),
        acceptance=tuple(task["acceptance"]),
        knowledge_links=tuple(
            KnowledgeChoice(link["node_id"], link["role"]) for link in task["knowledge_links"]
        ),
    )
    values.update(changes)
    return TaskChange(**values)


@pytest.mark.parametrize("purpose", ["learn", "interview"])
def test_new_task_design_updates_guidance_without_rewriting_old_plan(practice_scenario, purpose):
    from app.domain.planning.guidance import LearningGuidance, PracticeDelta
    from app.domain.planning.intent import GoalSpec, purpose_requirements
    db, scope, cmd, _, current = practice_scenario
    plans = PgPlanRepository(db.app_dsn)
    guide = LearningGuidance("将本阶段知识用于当前任务", "旧教程关系未确认", ("本阶段实践",), (),
                             PracticeDelta("当前项目", ("原增量",), ("保留原行为",), ("旧验证要求",), ("后续复用",)))
    guided = PlanDraft(new_id("drf"), cmd.project_id, "", current.goal_snapshot, current.revision + 1,
                       goal_spec=GoalSpec(target=current.goal_snapshot, outcome_purpose=purpose),
                       stages=tuple(replace(s, learning_guidance=guide) for s in current.stages),
                       unit_links=current.unit_links, task_links=current.task_links,
                       task_knowledge_links=current.task_knowledge_links, stage_resources=current.stage_resources,
                       resource_snapshots=current.resource_snapshots, extensions=current.extensions)
    plans.save_draft(guided)
    PlanPublicationService(plans).publish(draft=guided, presented_hash=guided.content_hash,
                expected_version=current.version, idempotency_key="initial-guided-plan")
    current = plans.get_current(project_id=cmd.project_id)
    cmd = replace(cmd, plan_id=current.plan_id, expected_version=current.version)
    repo = PgPracticeChanges(db.app_dsn)
    task = repo.context(scope, cmd.project_id)["tasks"][0]
    original = next(s for s in current.stages if s.stage_id == task["stage_id"])
    assert original.learning_guidance is not None
    cmd = replace(unchanged(repo, scope, cmd), task_changes=(edit(task, goal="Add structured logging",
                  acceptance=("New specific logging check",)),), idempotency_key="guide-preview")
    preview = repo.preview(scope, cmd)
    result = confirm(repo, scope, cmd, preview, key="guide-confirm")
    published = plans.get_current(project_id=cmd.project_id)
    stage = next(s for s in published.stages if s.stable_key == original.stable_key)
    outputs = purpose_requirements(current.goal_spec)
    assert stage.learning_guidance.practice_delta.validation == ("New specific logging check", *outputs)
    assert published.goal_spec == current.goal_spec
    assert preview["task_changes"][0]["after"]["acceptance"] == ["New specific logging check", *outputs]
    assert "Add structured logging" in stage.learning_guidance.practice_delta.increment[0]
    old = plans.get_revision(project_id=cmd.project_id, revision=current.revision)
    assert next(s for s in old.stages if s.stable_key == original.stable_key).learning_guidance == original.learning_guidance
    assert result["created"]


def confirm(repo, scope, cmd, preview, key="confirm"):
    return repo.decide(
        scope,
        cmd.project_id,
        preview["proposal_id"],
        "confirm",
        cmd.expected_version,
        preview["preview_hash"],
        key,
        True,
    )


def test_same_project_task_change_add_and_ordinary_draft_bypass(practice_scenario):
    from app.api.v1.practice_change_schemas import (
        PracticeChangeContextView,
        PracticeChangePreviewView,
        PracticeChangeResultView,
    )

    db, scope, cmd, _, current = practice_scenario
    repo = PgPracticeChanges(db.app_dsn)
    context = repo.context(scope, cmd.project_id)
    PracticeChangeContextView.model_validate(context)
    first = context["tasks"][0]
    cmd = replace(
        unchanged(repo, scope, cmd),
        task_changes=(
            edit(first),
            edit(first, operation="add", task_id=None, client_key="new", title="New deliverable"),
        ),
    )
    preview = repo.preview(scope, cmd)
    PracticeChangePreviewView.model_validate(preview)
    assert preview["before"] == preview["after"]
    changed, added = preview["task_changes"]
    assert (
        changed["before"]["task_id"] == first["task_id"] and changed["after"]["task_id"] != first["task_id"]
    )
    assert changed["after"]["stable_key"] != first["stable_key"] and added["before"] is None
    plain = PgPlanRepository(db.app_dsn)
    draft = plain.get_draft(project_id=cmd.project_id, draft_id=preview["draft_id"])
    for write in (
        lambda: plain.save_draft(draft, expected_version=current.version),
        lambda: plain.cancel_draft(project_id=cmd.project_id, draft_id=draft.draft_id),
        lambda: PlanPublicationService(plain).publish(
            draft=draft,
            presented_hash=draft.content_hash,
            expected_version=current.version,
            idempotency_key="bypass",
        ),
    ):
        with pytest.raises(AppError) as denied:
            write()
        assert denied.value.http_status == 409
    with pytest.raises(AppError) as ack:
        repo.decide(
            scope,
            cmd.project_id,
            preview["proposal_id"],
            "confirm",
            cmd.expected_version,
            preview["preview_hash"],
            "unack",
        )
    assert ack.value.http_status == 400
    result = confirm(repo, scope, cmd, preview)
    PracticeChangeResultView.model_validate(result)
    newer = plain.get_current(project_id=cmd.project_id)
    assert len(newer.task_links) == 2 and all(t.task_id != first["task_id"] for t in newer.task_links)
    assert repo.get(scope, cmd.project_id, preview["proposal_id"])["status"] == "confirmed"
    with psycopg.connect(db.migrator_dsn) as conn:
        assert conn.execute(
            "SELECT title,stable_key FROM practice_tasks WHERE task_id=%s", (first["task_id"],)
        ).fetchone() == (first["title"], first["stable_key"])


@pytest.mark.parametrize("bad", ["nochange", "stage", "node", "task", "owner"])
def test_invalid_scope_and_nochange_write_no_candidates(practice_scenario, bad):
    db, scope, cmd, _, current = practice_scenario
    repo = PgPracticeChanges(db.app_dsn)
    ctx = repo.context(scope, cmd.project_id)
    if bad == "nochange":
        cmd = unchanged(repo, scope, cmd)
    elif bad == "owner":
        scope = replace(scope, actor_id="forged", learning_project_scope=(cmd.project_id,))
    else:
        changes = (
            {"stage_id": "other-stage"}
            if bad == "stage"
            else {"task_id": "other-task"}
            if bad == "task"
            else {"knowledge_links": (KnowledgeChoice("unplanned", "core"),)}
        )
        if bad == "node":
            with psycopg.connect(db.migrator_dsn) as conn:
                conn.execute(
                    "INSERT INTO knowledge_nodes(node_id,project_id,stable_key,title,node_type,source_status) VALUES('unplanned',%s,'node.unplanned','Unplanned','concept','user_provided')",
                    (cmd.project_id,),
                )
        cmd = replace(cmd, task_changes=(edit(ctx["tasks"][0], **changes),))
    with psycopg.connect(db.migrator_dsn) as conn:
        before = conn.execute(
            "SELECT count(*) FROM practice_tasks WHERE project_id=%s", (cmd.project_id,)
        ).fetchone()[0]
    with pytest.raises(AppError):
        repo.preview(scope, cmd)
    with psycopg.connect(db.migrator_dsn) as conn:
        assert (
            conn.execute(
                "SELECT count(*) FROM practice_tasks WHERE project_id=%s", (cmd.project_id,)
            ).fetchone()[0]
            == before
        )
        assert (
            conn.execute(
                "SELECT count(*) FROM practice_change_proposals WHERE project_id=%s", (cmd.project_id,)
            ).fetchone()[0]
            == 0
        )


@pytest.mark.parametrize(
    "change", ["project", "task", "node", "candidate_project", "candidate_task", "original"]
)
def test_basis_and_candidate_drift_rejects_confirmation(practice_scenario, change):
    from app.domain.prompts import PromptSaveCommand
    from app.infrastructure.db.prompts import PgPrompts

    db, scope, cmd, _, current = practice_scenario
    repo = PgPracticeChanges(db.app_dsn)
    preview = repo.preview(scope, cmd)
    target = preview["task_changes"][0]
    if change == "original":
        PgPrompts(db.app_dsn).save(
            scope,
            PromptSaveCommand(
                cmd.project_id,
                cmd.plan_id,
                target["before"]["stage_id"],
                target["before"]["task_id"],
                "New original",
                0,
                "original",
            ),
        )
    else:
        with psycopg.connect(db.migrator_dsn) as conn:
            if change == "project":
                conn.execute(
                    "UPDATE practice_projects SET idea='Basis changed in isolated test' WHERE practice_project_id=%s",
                    (cmd.practice_project_id,),
                )
            elif change == "task":
                conn.execute(
                    "UPDATE practice_tasks SET acceptance='[\"Different requirement\"]' WHERE task_id=%s",
                    (target["before"]["task_id"],),
                )
            elif change == "node":
                conn.execute(
                    "UPDATE knowledge_nodes SET title='Changed knowledge',content_version=content_version+1 WHERE node_id=%s",
                    (target["before"]["knowledge_links"][0]["node_id"],),
                )
            elif change == "candidate_project":
                conn.execute(
                    "UPDATE practice_projects SET idea='Candidate changed in isolated test' WHERE practice_project_id=%s",
                    (preview["after"]["practice_project_id"],),
                )
            else:
                conn.execute(
                    "UPDATE practice_tasks SET title='Candidate changed' WHERE task_id=%s",
                    (target["after"]["task_id"],),
                )
    with pytest.raises(AppError) as conflict:
        confirm(repo, scope, cmd, preview)
    assert conflict.value.http_status == 409
    assert PgPlanRepository(db.app_dsn).get_current(project_id=cmd.project_id).plan_id == current.plan_id
    assert repo.get(scope, cmd.project_id, preview["proposal_id"])["status"] == "pending"


def test_atomic_rollback_cancel_competition_and_stale_cancel(practice_scenario, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor

    from app.infrastructure.db import practice_changes

    db, scope, cmd, _, current = practice_scenario
    repo = PgPracticeChanges(db.app_dsn)
    preview = repo.preview(scope, cmd)
    original = practice_changes.copy_private_selections
    monkeypatch.setattr(
        practice_changes,
        "copy_private_selections",
        lambda *args: (_ for _ in ()).throw(RuntimeError("Injected after publication")),
    )
    with pytest.raises(RuntimeError):
        confirm(repo, scope, cmd, preview)
    assert repo.get(scope, cmd.project_id, preview["proposal_id"])["status"] == "pending"
    assert PgPlanRepository(db.app_dsn).get_current(project_id=cmd.project_id).plan_id == current.plan_id
    with psycopg.connect(db.migrator_dsn) as conn:
        assert (
            conn.execute(
                "SELECT count(*) FROM practice_change_receipts WHERE project_id=%s AND action='confirm'",
                (cmd.project_id,),
            ).fetchone()[0]
            == 0
        )
    monkeypatch.setattr(practice_changes, "copy_private_selections", original)
    stale = repo.preview(scope, replace(cmd, title="Another candidate", idempotency_key="another"))

    def decide(action):
        try:
            return repo.decide(
                scope,
                cmd.project_id,
                preview["proposal_id"],
                action,
                cmd.expected_version,
                preview["preview_hash"],
                action,
                True,
            )["status"]
        except AppError:
            return "lost"

    with ThreadPoolExecutor(max_workers=2) as pool:
        result = list(pool.map(decide, ["confirm", "cancel"]))
    assert result.count("lost") == 1
    if "cancelled" in result:
        confirm(repo, scope, cmd, stale, "confirm-another")
    else:
        with pytest.raises(AppError):
            confirm(repo, scope, cmd, stale, "confirm-another")
        cancelled = repo.decide(
            scope,
            cmd.project_id,
            stale["proposal_id"],
            "cancel",
            cmd.expected_version,
            stale["preview_hash"],
            "cancel-stale",
        )
        assert cancelled["status"] == "cancelled"
        assert (
            repo.decide(
                scope,
                cmd.project_id,
                stale["proposal_id"],
                "cancel",
                cmd.expected_version,
                stale["preview_hash"],
                "cancel-stale",
            )
            == cancelled
        )


def test_prompt_history_and_export_are_retained_for_old_task(practice_scenario):
    from app.domain.prompts import PromptSaveCommand
    from app.infrastructure.db.prompts import PgPrompts

    db, scope, cmd, _, current = practice_scenario
    repo = PgPracticeChanges(db.app_dsn)
    task = repo.context(scope, cmd.project_id)["tasks"][0]
    prompts = PgPrompts(db.app_dsn)
    raw = "  \nOriginal older task🙂\t "
    revision = prompts.save(
        scope,
        PromptSaveCommand(cmd.project_id, cmd.plan_id, task["stage_id"], task["task_id"], raw, 0, "original"),
    )["revision"]
    exported = prompts.export(scope, cmd.project_id, revision["revision_id"], "implementation", "export")
    preview = repo.preview(scope, cmd)
    confirm(repo, scope, cmd, preview)
    assert (
        prompts.attempt(scope, cmd.project_id, revision["revision_id"])["task_snapshot"]
        == revision["task_snapshot"]
    )
    assert prompts.get_export(scope, cmd.project_id, exported["export_id"]) == exported
    assert prompts.export(scope, cmd.project_id, revision["revision_id"], "raw", "raw")["export_text"] == raw
    assert prompts.history(scope, cmd.project_id)["items"][0]["user_draft"] == raw
    after = repo.context(scope, cmd.project_id)
    newtask = after["tasks"][0]
    assert newtask["status"] == "pending" and newtask["task_id"] != task["task_id"]
    assert (
        prompts.thread(scope, cmd.project_id, after["plan_id"], newtask["stage_id"], newtask["task_id"])[
            "version"
        ]
        == 0
    )


def test_two_previews_compete_for_one_version_and_loser_can_cancel(practice_scenario):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    db, scope, cmd, _, current = practice_scenario
    repo = PgPracticeChanges(db.app_dsn)
    previews = [
        repo.preview(scope, replace(cmd, title=f"Candidate {i}", idempotency_key=f"preview-{i}"))
        for i in range(2)
    ]
    barrier = Barrier(2)

    def decide(index):
        barrier.wait(timeout=5)
        try:
            return confirm(repo, scope, cmd, previews[index], f"confirm-{index}")
        except AppError as error:
            assert error.http_status == 409
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(decide, range(2)))
    assert sum(result is not None for result in results) == 1
    winner = next(result for result in results if result is not None)
    loser = results.index(None)
    assert winner["revision"] == current.revision + 1
    cancelled = repo.decide(
        scope,
        cmd.project_id,
        previews[loser]["proposal_id"],
        "cancel",
        cmd.expected_version,
        previews[loser]["preview_hash"],
        "cancel-loser",
    )
    assert cancelled["status"] == "cancelled"
    assert (
        repo.decide(
            scope,
            cmd.project_id,
            previews[loser]["proposal_id"],
            "cancel",
            cmd.expected_version,
            previews[loser]["preview_hash"],
            "cancel-loser",
        )
        == cancelled
    )
    with psycopg.connect(db.migrator_dsn) as conn:
        assert (
            conn.execute(
                "SELECT count(*) FROM plan_revisions WHERE project_id=%s AND revision=%s",
                (cmd.project_id, current.revision + 1),
            ).fetchone()[0]
            == 1
        )


@pytest.mark.parametrize("drift", ["add", "remove", "replace"])
def test_private_selection_drift_rejects_exact_copy_set(practice_scenario, drift):
    from app.infrastructure.db.learning_resources import PgLearningResources

    db, scope, cmd, _, current = practice_scenario
    resources = PgLearningResources(db.app_dsn)
    position = dict(
        project_id=cmd.project_id,
        plan_id=cmd.plan_id,
        stage_id=current.stages[0].stage_id,
        unit_id=current.unit_links[0].unit_id,
    )

    def select(suffix):
        return resources.select(
            scope,
            position,
            dict(
                resource_id="private-" + suffix + cmd.project_id,
                project_id=cmd.project_id,
                url="https://docs.python.org/3/library/" + suffix + ".html",
                title=suffix,
                media_type="text",
                language="en",
                provenance="user_provided",
                verification_status="unverified",
                source_version=7,
            ),
        )

    old = select("uuid") if drift != "add" else None
    repo = PgPracticeChanges(db.app_dsn)
    preview = repo.preview(scope, cmd)
    if old:
        resources.remove(scope, position, old["selection_id"])
    if drift != "remove":
        select("typing")
    with pytest.raises(AppError) as conflict:
        confirm(repo, scope, cmd, preview)
    assert conflict.value.http_status == 409
    assert repo.get(scope, cmd.project_id, preview["proposal_id"])["status"] == "pending"


@pytest.mark.parametrize("policy", ["copy_active", "keep_history_only"])
def test_private_policy_lineage_and_old_exposure_preserved(practice_scenario, policy):
    from app.domain.enums import UnitProgress
    from app.domain.learning_exposures import ExposureCommand
    from app.infrastructure.db.learning_exposures import PgLearningExposures
    from app.infrastructure.db.learning_resources import PgLearningResources

    db, scope, cmd, _, current = practice_scenario
    position = dict(
        project_id=cmd.project_id,
        plan_id=cmd.plan_id,
        stage_id=current.stages[0].stage_id,
        unit_id=current.unit_links[0].unit_id,
    )
    exposures = PgLearningExposures(db.app_dsn)
    progress = exposures.change(
        scope,
        ExposureCommand(
            **position, status=UnitProgress.COMPLETED, expected_version=0, idempotency_key="complete"
        ),
    )
    selection = PgLearningResources(db.app_dsn).select(
        scope,
        position,
        dict(
            resource_id="private-" + cmd.project_id,
            project_id=cmd.project_id,
            url="https://docs.python.org/3/library/uuid.html",
            title="private",
            media_type="text",
            language="en",
            provenance="user_provided",
            verification_status="unverified",
            source_version=7,
        ),
    )
    cmd = replace(cmd, copy_policy=policy)
    repo = PgPracticeChanges(db.app_dsn)
    preview = repo.preview(scope, cmd)
    result = confirm(repo, scope, cmd, preview)
    assert result["copied_selections"] == (1 if policy == "copy_active" else 0)
    assert exposures.history(scope, **position) == [progress["event"]]
    assert all(
        v["version"] == 0 and v["status"] == "not_started"
        for v in exposures.list(scope, cmd.project_id, result["plan_id"])
    )
    with psycopg.connect(db.migrator_dsn) as conn:
        copied = conn.execute(
            "SELECT resource_snapshot FROM learning_resource_selections WHERE project_id=%s AND plan_id=%s",
            (cmd.project_id, result["plan_id"]),
        ).fetchall()
        if copied:
            assert (
                copied[0][0]["selection_copy_lineage"]["original_selection_id"] == selection["selection_id"]
            )
            assert copied[0][0]["selection_copy_lineage"]["original_source_version"] == 7
            assert copied[0][0]["verification_status"] == "unverified"


@pytest.mark.parametrize("legacy", [True, False])
def test_only_missing_source_observations_are_rechecked_frozen_history_preserved(practice_scenario, legacy):
    db, scope, cmd, _, current = practice_scenario
    source = current.stage_resources[0].source_ref
    if legacy:
        with psycopg.connect(db.migrator_dsn) as conn:
            conn.execute(
                "UPDATE plan_revisions SET structure=structure-'resource_snapshots' WHERE project_id=%s AND plan_id=%s",
                (cmd.project_id, current.plan_id),
            )
    repo = PgPracticeChanges(db.app_dsn)
    preview = repo.preview(scope, cmd)
    draft = PgPlanRepository(db.app_dsn).get_draft(project_id=cmd.project_id, draft_id=preview["draft_id"])
    with psycopg.connect(db.migrator_dsn) as conn:
        conn.execute(
            "UPDATE public_resource_sources SET title='Catalog later title' WHERE source_id=%s", (source,)
        )
    if legacy:
        assert any("新版本预览时观察" in warning for warning in preview["warnings"])
        with pytest.raises(AppError) as drift:
            confirm(repo, scope, cmd, preview)
        assert drift.value.http_status == 409
    else:
        result = confirm(repo, scope, cmd, preview)
        published = PgPlanRepository(db.app_dsn).get_current(project_id=cmd.project_id)
        assert result["created"]
        assert (
            published.resource_snapshots[0]["source"]["title"]
            == current.resource_snapshots[0]["source"]["title"]
        )
        assert draft.resource_snapshots == current.resource_snapshots


def test_receipts_payload_immutability_owner_and_pending_context_hidden(practice_scenario):
    db, scope, cmd, _, current = practice_scenario
    repo = PgPracticeChanges(db.app_dsn)
    before = repo.context(scope, cmd.project_id)
    preview = repo.preview(scope, cmd)
    assert repo.context(scope, cmd.project_id) == before
    assert repo.preview(scope, cmd) == preview
    with pytest.raises(AppError) as conflict:
        repo.preview(scope, replace(cmd, title="Heterogeneous body"))
    assert conflict.value.http_status == 409
    with pytest.raises(AppError) as denied:
        repo.get(
            replace(scope, actor_id="forged", learning_project_scope=(cmd.project_id,)),
            cmd.project_id,
            preview["proposal_id"],
        )
    assert denied.value.http_status == 403
    with psycopg.connect(db.app_dsn) as conn:
        conn.execute(
            "SELECT set_config('app.actor_id','forged',true),set_config('app.project_id',%s,true)",
            (cmd.project_id,),
        )
        assert (
            conn.execute(
                "SELECT proposal_id FROM practice_change_proposals WHERE project_id=%s", (cmd.project_id,)
            ).fetchone()
            is None
        )
    with pytest.raises(psycopg.errors.RaiseException):
        with psycopg.connect(db.migrator_dsn) as conn:
            conn.execute(
                "UPDATE practice_change_proposals SET payload='{}' WHERE proposal_id=%s",
                (preview["proposal_id"],),
            )
    result = repo.decide(
        scope,
        cmd.project_id,
        preview["proposal_id"],
        "cancel",
        cmd.expected_version,
        preview["preview_hash"],
        "cancel",
    )
    assert repo.preview(scope, cmd) == preview
    assert repo.get(scope, cmd.project_id, preview["proposal_id"])["status"] == "cancelled"
    assert result["plan_id"] is None


@pytest.mark.parametrize("main_changed", [True, False])
def test_clone_scope_all_target_tasks_or_only_changed_task(practice_scenario, main_changed):
    from app.domain.enums import TaskKnowledgeRole
    from app.domain.planning.models import PlanTaskKnowledgeLink, PlanTaskLink

    db, scope, cmd, _, current = practice_scenario
    original = PgPracticeChanges(db.app_dsn).context(scope, cmd.project_id)["tasks"][0]
    other_project, second, other = new_id("ppj"), new_id("tsk"), new_id("tsk")
    with psycopg.connect(db.migrator_dsn) as conn:
        conn.execute(
            "INSERT INTO practice_projects(practice_project_id,project_id,title,idea,status) VALUES(%s,%s,'Other project','Other independent project idea','idea')",
            (other_project, cmd.project_id),
        )
        for task, project, key in (
            (second, cmd.practice_project_id, "task.second"),
            (other, other_project, "task.other"),
        ):
            conn.execute(
                "INSERT INTO practice_tasks(task_id,project_id,practice_project_id,stable_key,title,goal,in_scope,out_scope,acceptance,status) "
                "VALUES(%s,%s,%s,%s,'Other task','Observable goal','[\"in\"]','[\"out\"]','[\"check\"]','accepted')",
                (task, cmd.project_id, project, key),
            )
    stage = current.stages[0].stage_id
    node = original["knowledge_links"][0]["node_id"]
    draft = PlanDraft(
        new_id("drf"),
        cmd.project_id,
        "",
        current.goal_snapshot,
        current.revision + 1,
        stages=current.stages,
        unit_links=current.unit_links,
        task_links=current.task_links + (PlanTaskLink(stage, second, 1), PlanTaskLink(stage, other, 2)),
        task_knowledge_links=current.task_knowledge_links
        + (
            PlanTaskKnowledgeLink(second, node, TaskKnowledgeRole.CORE),
            PlanTaskKnowledgeLink(other, node, TaskKnowledgeRole.CORE),
        ),
        stage_resources=current.stage_resources,
        resource_snapshots=current.resource_snapshots,
    )
    plans = PgPlanRepository(db.app_dsn)
    plans.save_draft(draft, expected_version=current.version)
    PlanPublicationService(plans).publish(
        draft=draft,
        presented_hash=draft.content_hash,
        expected_version=current.version,
        idempotency_key="expand",
    )
    current = plans.get_current(project_id=cmd.project_id)
    cmd = replace(cmd, plan_id=current.plan_id, expected_version=current.version)
    repo = PgPracticeChanges(db.app_dsn)
    context = repo.context(scope, cmd.project_id)
    original = next(t for t in context["tasks"] if t["task_id"] == original["task_id"])
    if not main_changed:
        cmd = unchanged(repo, scope, cmd)
    cmd = replace(cmd, task_changes=(edit(original),))
    preview = repo.preview(scope, cmd)
    confirm(repo, scope, cmd, preview)
    new_ids = {t["task_id"] for t in repo.context(scope, cmd.project_id)["tasks"]}
    assert other in new_ids and original["task_id"] not in new_ids
    assert (second not in new_ids) == main_changed
    assert preview["impact"]["cloned_task_count"] == (2 if main_changed else 1)
    assert all(d["after"]["status"] == "pending" for d in preview["task_changes"])
    with psycopg.connect(db.migrator_dsn) as conn:
        assert (
            conn.execute("SELECT status FROM practice_tasks WHERE task_id=%s", (second,)).fetchone()[0]
            == "accepted"
        )
