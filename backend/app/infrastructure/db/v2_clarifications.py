"""Initial clarification events and consent, within existing Run/Job transactions."""

from contextlib import contextmanager
from copy import deepcopy
from uuid import NAMESPACE_URL, uuid5

import psycopg
from app.core.errors import (
    ConflictError,
    DependencyUnavailableError,
    IdempotencyConflictError,
    NotFoundError,
    ValidationAppError,
)
from app.core.ids import content_hash
from app.domain.enums import AiRunNextAction, AiRunStatus
from app.domain.planning.clarification import (
    MAX_ANSWER_ROUNDS,
    answer_input,
    answers_for_questions,
    intact,
    sealed,
)
from app.domain.planning.goal_requirements import (
    GOAL_REQUIREMENT_PURPOSE,
    GOAL_REQUIREMENT_SCHEMA,
    GoalRequirementProfileValidator,
)
from app.domain.planning.intent import GoalSpec, goal_spec_from_payload, goal_spec_payload
from app.domain.planning.v2_runtime import V2_EXECUTION_VERSION, V2RecoveryBlocked
from app.domain.runs.models import RunRecord
from app.infrastructure.db.plan_repository import to_psycopg_dsn
from app.infrastructure.db.planning_fence import lock_plan_version
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


def root_of(submission, run_id):
    initial = submission["initial"]
    context = initial.get("v2_revision") or initial.get("v2_clarification")
    return context["budget_root_run_id"] if context else run_id


def _receipt(conn, *, run_id, manifest, payload):
    rows = conn.execute(
        "SELECT a.*,e.detail AS reservation FROM ai_provider_attempts a JOIN ai_run_events e "
        "ON e.run_id=a.run_id AND e.attempt_id=a.attempt_id AND e.status='v2_reservation' "
        "WHERE a.run_id=%s AND e.detail->>'step'='goal-analysis'",
        (run_id,),
    ).fetchall()
    if len(rows) != 1:
        raise V2RecoveryBlocked("Clarification requires one original Goal receipt")
    row, reserved = rows[0], rows[0]["reservation"]
    fields = (
        "run_id",
        "step",
        "purpose",
        "schema",
        "input_hash",
        "manifest_hash",
        "config_hash",
        "source_versions_hash",
    )
    response = row["response_payload"]
    if (
        row["status"] != "succeeded"
        or row["provider"] != "v2:" + GOAL_REQUIREMENT_PURPOSE
        or row["schema_name"] != GOAL_REQUIREMENT_SCHEMA
        or reserved.get("run_id") != run_id
        or reserved.get("purpose") != GOAL_REQUIREMENT_PURPOSE
        or reserved.get("schema") != GOAL_REQUIREMENT_SCHEMA
        or reserved.get("manifest_hash") != manifest["manifest_hash"]
        or reserved.get("source_versions_hash") != manifest["source_facts_hash"]
        or reserved.get("input_hash") != content_hash(payload)
        or reserved.get("digest") != content_hash({k: v for k, v in reserved.items() if k != "digest"})
        or content_hash({k: reserved.get(k) for k in fields}) != row["request_fingerprint"]
        or type(response) is not dict
        or response.get("kind") != "llm"
        or response.get("identity") != row["request_fingerprint"]
        or response.get("manifest_hash") != manifest["manifest_hash"]
        or response.get("digest") != content_hash({k: v for k, v in response.items() if k != "digest"})
    ):
        raise V2RecoveryBlocked("Clarification receipt/source integrity rejected")
    return row


def _event(conn, **binding):
    try:
        return _validated_event(conn, **binding)
    except (ValidationAppError, KeyError, TypeError, ValueError, AttributeError, RecursionError):
        raise V2RecoveryBlocked("Clarification stored facts are malformed") from None


def _validated_event(conn, *, actor_id, project_id, run_id, submission):
    rows = conn.execute(
        "SELECT detail FROM ai_run_events WHERE run_id=%s AND status='v2_clarification' ORDER BY event_id",
        (run_id,),
    ).fetchall()
    if len(rows) != 1:
        raise V2RecoveryBlocked("Clarification questions missing or ambiguous")
    event = rows[0]["detail"]
    initial, manifest = submission["initial"], submission["manifest"]
    if initial.get("v2_revision") is not None or manifest["expected_version"] != 0:
        raise V2RecoveryBlocked("Initial clarification cannot resume semantic replanning")
    continuation = initial.get("v2_clarification")
    round_number = continuation["round"] if continuation else 0
    goal = goal_spec_from_payload(initial.get("goal_spec")) or GoalSpec(initial["goal"])
    payload = {"goal": goal_spec_payload(goal)}
    if continuation:
        payload["clarification"] = answer_input(continuation["item1_input"])
    receipt = _receipt(conn, run_id=run_id, manifest=manifest, payload=payload)
    profile = GoalRequirementProfileValidator().validate(
        receipt["response_payload"]["value"]["payload"], goal=goal, clarification=payload.get("clarification")
    )
    expected = _freeze_payload(
        actor_id,
        project_id,
        run_id,
        root_of(submission, run_id),
        manifest,
        goal,
        profile,
        round_number,
        receipt,
    )
    if not intact(event) or event != expected:
        raise V2RecoveryBlocked("Clarification question/profile binding rejected")
    return event


def _freeze_payload(actor, project, run, root, manifest, goal, profile, round_number, receipt):
    if profile.status != "needs_clarification" or not 0 <= round_number <= MAX_ANSWER_ROUNDS:
        raise V2RecoveryBlocked("Only validated initial clarification may be frozen")
    version = round_number + 1
    questions = [
        {
            "question_id": "question_" + content_hash([run, profile.profile_hash, version, i, text]),
            "question_text": text,
        }
        for i, text in enumerate(profile.clarification_questions)
    ]
    return sealed(
        {
            "kind": "v2_initial_clarification",
            "actor_id": actor,
            "project_id": project,
            "run_id": run,
            "budget_root_run_id": root,
            "manifest_hash": manifest["manifest_hash"],
            "goal_spec": goal_spec_payload(goal),
            "goal_hash": manifest["goal_hash"],
            "profile": profile.to_payload(),
            "profile_hash": profile.profile_hash,
            "clarification_version": version,
            "round": round_number,
            "questions": questions,
            "can_submit_answers": round_number < MAX_ANSWER_ROUNDS,
            "receipt_ref": {
                "attempt_id": receipt["attempt_id"],
                "identity": receipt["request_fingerprint"],
                "digest": receipt["response_payload"]["digest"],
            },
        }
    )


def freeze_questions(calls, profile, goal):
    from app.infrastructure.db.v2_revisions import frozen_submission

    calls.guard()
    with calls.tx() as conn:
        calls._lock(conn)
        submission = frozen_submission(
            conn, actor_id=calls.scope.actor_id, project_id=calls.project_id, run_id=calls.run_id
        )
        context = submission["initial"].get("v2_clarification")
        payload = {"goal": goal_spec_payload(goal)}
        if context:
            payload["clarification"] = answer_input(context["item1_input"])
        receipt = _receipt(conn, run_id=calls.run_id, manifest=calls.manifest, payload=payload)
        verified = GoalRequirementProfileValidator().validate(
            receipt["response_payload"]["value"]["payload"],
            goal=goal,
            clarification=payload.get("clarification"),
        )
        if verified.to_payload() != profile.to_payload():
            raise V2RecoveryBlocked("Validated clarification differs from retained receipt")
        event = _freeze_payload(
            calls.scope.actor_id,
            calls.project_id,
            calls.run_id,
            root_of(submission, calls.run_id),
            calls.manifest,
            goal,
            profile,
            context["round"] if context else 0,
            receipt,
        )
        rows = conn.execute(
            "SELECT detail FROM ai_run_events WHERE run_id=%s AND status='v2_clarification'", (calls.run_id,)
        ).fetchall()
        if rows:
            if len(rows) != 1 or rows[0]["detail"] != event:
                raise V2RecoveryBlocked("Frozen clarification already differs")
        else:
            conn.execute(
                "INSERT INTO ai_run_events(run_id,status,detail) VALUES(%s,'v2_clarification',%s)",
                (calls.run_id, Jsonb(event)),
            )
    calls.guard()
    return event


def validate_continuation(conn, **binding):
    try:
        return _validated_continuation(conn, **binding)
    except (ValidationAppError, KeyError, TypeError, ValueError, AttributeError, RecursionError):
        raise V2RecoveryBlocked("Clarification consent facts are malformed") from None


def _validated_continuation(conn, *, actor_id, project_id, run_id, submission, seen=()):
    from app.infrastructure.db.v2_revisions import frozen_submission

    context, manifest = submission["initial"].get("v2_clarification"), submission["manifest"]
    if (
        not intact(context)
        or set(context)
        != {
            "kind",
            "actor_id",
            "project_id",
            "parent_run_id",
            "budget_root_run_id",
            "clarification_version",
            "round",
            "parent_event_hash",
            "input_hash",
            "item1_input",
            "context_hash",
        }
        or context["kind"] != "v2_initial_clarification_continuation"
        or context["actor_id"] != actor_id
        or context["project_id"] != project_id
        or manifest.get("v2_clarification_hash") != context["context_hash"]
        or type(context["round"]) is not int
        or not 1 <= context["round"] <= MAX_ANSWER_ROUNDS
        or submission["initial"].get("v2_revision") is not None
        or manifest["expected_version"] != 0
    ):
        raise V2RecoveryBlocked("Clarification submission binding rejected")
    parent = frozen_submission(
        conn, actor_id=actor_id, project_id=project_id, run_id=context["parent_run_id"], _seen=seen
    )
    state = conn.execute(
        "SELECT status,error_class,next_action FROM ai_runs WHERE run_id=%s", (context["parent_run_id"],)
    ).fetchone()
    if state != {"status": "failed", "error_class": "goal_clarification_required", "next_action": "none"}:
        raise V2RecoveryBlocked("Clarification parent is not safely answerable")
    event = _event(
        conn, actor_id=actor_id, project_id=project_id, run_id=context["parent_run_id"], submission=parent
    )
    item1 = answer_input(context["item1_input"])
    prior = parent["initial"].get("v2_clarification")
    prior_answers = prior["item1_input"]["answers"] if prior else []
    latest = item1["answers"][len(prior_answers) :]
    normalized = answers_for_questions(
        [{k: a[k] for k in ("question_id", "answer_text")} for a in latest], event["questions"]
    )
    expected_input = _item1_input(event, prior_answers, normalized)
    expected_fingerprint = content_hash({"parent_run_id": context["parent_run_id"],
        "clarification_version": context["clarification_version"], "answers": normalized})
    confirmations = conn.execute(
        "SELECT detail FROM ai_run_events WHERE run_id=%s AND status='v2_clarification_submission'",
        (context["parent_run_id"],),
    ).fetchall()
    expected_confirmation = sealed(
        {
            "kind": "v2_clarification_submission",
            "parent_run_id": context["parent_run_id"],
            "continuation_run_id": run_id,
            "input_hash": context["input_hash"],
            "continuation_hash": context["context_hash"],
        }
    )
    if (
        context["parent_event_hash"] != event["context_hash"]
        or context["budget_root_run_id"] != event["budget_root_run_id"]
        or context["round"] != event["round"] + 1
        or context["clarification_version"] != event["clarification_version"]
        or not event["can_submit_answers"]
        or item1 != expected_input
        or context["input_hash"] != expected_fingerprint
        or content_hash(goal_spec_payload(goal_spec_from_payload(submission["initial"]["goal_spec"])))
        != content_hash(event["goal_spec"])
        or manifest["goal_hash"] != parent["manifest"]["goal_hash"]
        or manifest["budget"] != parent["manifest"]["budget"]
        or len(confirmations) != 1
        or confirmations[0]["detail"] != expected_confirmation
    ):
        raise V2RecoveryBlocked("Clarification consent/questions/goal binding rejected")
    return context


def _item1_input(event, prior_answers, answers):
    values = deepcopy(prior_answers)
    for question, answer in zip(event["questions"], answers, strict=True):
        values.append(
            {
                **question,
                "answer_text": answer["answer_text"],
                "clarification_version": event["clarification_version"],
                "source_ref": f"clarification.answers[{len(values)}]",
            }
        )
    return answer_input(
        {
            "answers": values,
            "retained_facts": {
                key: [{k: fact[k] for k in ("text", "source_refs")} for fact in event["profile"][key]]
                for key in ("hard_constraints", "learner_claims")
            },
        }
    )


class PgV2Clarifications:
    def __init__(self, dsn, *, factory=None, jobs=None):
        self.dsn, self.factory, self.jobs = to_psycopg_dsn(dsn), factory, jobs

    @contextmanager
    def tx(self, scope, project):
        scope.require_project(project)
        with psycopg.connect(self.dsn, row_factory=dict_row) as conn:
            conn.execute(
                "SELECT set_config('app.actor_id',%s,true),set_config('app.project_id',%s,true)",
                (scope.actor_id, project),
            )
            yield conn

    def read(self, *, scope, project_id, run_id):
        from app.infrastructure.db.v2_revisions import frozen_submission

        with self.tx(scope, project_id) as conn:
            state = conn.execute(
                "SELECT status,error_class,next_action,actor_id,graph_version FROM ai_runs WHERE run_id=%s AND project_id=%s",
                (run_id, project_id),
            ).fetchone()
            if state is None or state["actor_id"] != scope.actor_id:
                raise NotFoundError("运行不存在")
            if (state["status"], state["error_class"], state["next_action"], state["graph_version"]) != (
                "failed",
                "goal_clarification_required",
                "none",
                V2_EXECUTION_VERSION,
            ):
                return None
            try:
                submission = frozen_submission(
                    conn, actor_id=scope.actor_id, project_id=project_id, run_id=run_id
                )
                event = _event(
                    conn, actor_id=scope.actor_id, project_id=project_id, run_id=run_id, submission=submission
                )
                confirmations = conn.execute(
                    "SELECT detail FROM ai_run_events WHERE run_id=%s AND status='v2_clarification_submission'",
                    (run_id,),
                ).fetchall()
                child = confirmations[0]["detail"]["continuation_run_id"] if len(confirmations) == 1 else None
                if confirmations:
                    if len(confirmations) != 1:
                        raise V2RecoveryBlocked("Clarification consent ambiguous")
                    frozen_submission(conn, actor_id=scope.actor_id, project_id=project_id, run_id=child)
                return {
                    "clarification_version": event["clarification_version"],
                    "questions": event["questions"],
                    "can_submit_answers": event["can_submit_answers"] and child is None,
                    "message": "需要补充信息"
                    if event["can_submit_answers"]
                    else "已达到两轮澄清上限，请重新确认目标或人工调整",
                    "continuation_run_id": child,
                }
            except (V2RecoveryBlocked, ValidationAppError, KeyError, TypeError, ValueError):
                return None

    def submit(self, *, scope, project_id, parent_run_id, clarification_version, answers, idempotency_key):
        from app.infrastructure.db.v2_revisions import budget_family, frozen_submission

        factory, jobs = self.factory, self.jobs
        if (
            factory is None
            or getattr(factory, "owned_only", False) is not True
            or jobs is None
            or to_psycopg_dsn(factory.dsn) != self.dsn
            or getattr(jobs, "_dsn", None) != self.dsn
        ):
            raise DependencyUnavailableError("V2 owned clarification is not configured")
        if type(idempotency_key) is not str or not idempotency_key.strip() or len(idempotency_key) > 128:
            raise ValidationAppError("澄清幂等键无效")
        if type(clarification_version) is not int or not 1 <= clarification_version <= 2:
            raise ValidationAppError("澄清版本无效或已达到轮次上限")
        run_id = (
            "run_"
            + uuid5(
                NAMESPACE_URL, f"studyplan:v2clarification:{scope.actor_id}:{project_id}:{idempotency_key}"
            ).hex
        )
        with self.tx(scope, project_id) as conn:
            parent = frozen_submission(
                conn, actor_id=scope.actor_id, project_id=project_id, run_id=parent_run_id
            )
            root = root_of(parent, parent_run_id)
            conn.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", ("studyplan:plan-budget:" + root,)
            )
            lock_plan_version(conn, project_id, None)
            parent = frozen_submission(
                conn, actor_id=scope.actor_id, project_id=project_id, run_id=parent_run_id
            )
            state = conn.execute(
                "SELECT status,error_class,next_action FROM ai_runs WHERE run_id=%s FOR UPDATE",
                (parent_run_id,),
            ).fetchone()
            if state != {
                "status": "failed",
                "error_class": "goal_clarification_required",
                "next_action": "none",
            }:
                raise ConflictError("此运行不允许澄清续接", reason="clarification_not_answerable")
            event = _event(
                conn, actor_id=scope.actor_id, project_id=project_id, run_id=parent_run_id, submission=parent
            )
            if clarification_version != event["clarification_version"] or not event["can_submit_answers"]:
                raise ConflictError("澄清问题版本已变化或达到轮次上限", reason="clarification_version_stale")
            answers = answers_for_questions(answers, event["questions"])
            fingerprint = content_hash(
                {
                    "parent_run_id": parent_run_id,
                    "clarification_version": clarification_version,
                    "answers": answers,
                }
            )
            existing = conn.execute("SELECT run_id FROM ai_runs WHERE run_id=%s", (run_id,)).fetchone()
            if existing:
                old = frozen_submission(conn, actor_id=scope.actor_id, project_id=project_id, run_id=run_id)
                if old["initial"].get("v2_clarification", {}).get("input_hash") != fingerprint:
                    raise IdempotencyConflictError("同一澄清身份已绑定不同答案")
                return run_id
            if conn.execute(
                "SELECT 1 FROM ai_run_events WHERE run_id=%s AND status='v2_clarification_submission'",
                (parent_run_id,),
            ).fetchone():
                raise ConflictError(
                    "本轮答案已提交，请读取已创建的运行", reason="clarification_already_submitted"
                )
            _, family = budget_family(
                conn, actor_id=scope.actor_id, project_id=project_id, run_id=parent_run_id
            )
            if conn.execute(
                "SELECT 1 FROM ai_provider_attempts WHERE run_id=ANY(%s) AND status IN('dispatched','reconciliation_required') LIMIT 1",
                (list(family),),
            ).fetchone():
                raise V2RecoveryBlocked("Unknown family dispatch blocks clarification")
            from app.infrastructure.providers.v2_attempts import PgV2Calls

            usage = PgV2Calls.family_reservations(conn, family, list(family))
            budget = family[root]["budget"]
            if (
                any(usage[k] > budget["max_" + k] for k in usage)
                or usage["total_requests"] >= budget["max_total_requests"]
            ):
                raise ConflictError(
                    "共享预算已用尽，不能创建新的澄清运行", reason="clarification_budget_exhausted"
                )
            lock_plan_version(conn, project_id, 0)
            goal = goal_spec_from_payload(event["goal_spec"])
            manifest = factory.build_submission(scope, project_id, goal, 0)
            if manifest["budget"] != family[root]["budget"]:
                raise ValidationAppError("澄清不能重置或提高共享预算")
            prior = parent["initial"].get("v2_clarification")
            item1 = _item1_input(event, prior["item1_input"]["answers"] if prior else [], answers)
            context = sealed(
                {
                    "kind": "v2_initial_clarification_continuation",
                    "actor_id": scope.actor_id,
                    "project_id": project_id,
                    "parent_run_id": parent_run_id,
                    "budget_root_run_id": root,
                    "clarification_version": clarification_version,
                    "round": event["round"] + 1,
                    "parent_event_hash": event["context_hash"],
                    "input_hash": fingerprint,
                    "item1_input": item1,
                }
            )
            manifest["v2_clarification_hash"] = context["context_hash"]
            manifest["manifest_hash"] = content_hash(
                {k: v for k, v in manifest.items() if k != "manifest_hash"}
            )
            initial = {
                "goal": goal.target,
                "goal_spec": goal_spec_payload(goal),
                "manifest": manifest,
                "v2_clarification": context,
            }
            confirmation = sealed(
                {
                    "kind": "v2_clarification_submission",
                    "parent_run_id": parent_run_id,
                    "continuation_run_id": run_id,
                    "input_hash": fingerprint,
                    "continuation_hash": context["context_hash"],
                }
            )
            conn.execute(
                "INSERT INTO ai_run_events(run_id,status,detail) VALUES(%s,'v2_clarification_submission',%s)",
                (parent_run_id, Jsonb(confirmation)),
            )
            run = RunRecord(
                run_id,
                scope.actor_id,
                project_id,
                "plan_generate",
                "planning",
                V2_EXECUTION_VERSION,
                AiRunStatus.QUEUED,
                AiRunNextAction.WAIT,
                thread_id="thread_" + run_id[4:],
            )
            jobs.in_transaction(conn).enqueue(run, initial, manifest)
            return run_id


_ISSUE_MESSAGES = {
    "required_material_unresolved": "部分必要学习目标尚无合格教材，无法确认路线。",
    "constraint_unresolved": "已有硬约束尚未获得可信满足证据，需要处理限制。",
    "project_case_unresolved": "必要项目学习案例尚未选定，教学安排未完成。",
    "curriculum_incomplete": "教学安排尚未完整，当前没有可确认草案。",
}


def freeze_planning_issues(calls, curriculum, *, diagnostics):
    """Only fixed descriptions of already validated incomplete curriculum facts."""
    codes = ["curriculum_incomplete"]
    if diagnostics["unresolved"]:
        codes.append("required_material_unresolved")
    if any(a["status"] != "satisfied" for a in diagnostics["constraint_assessments"]):
        codes.append("constraint_unresolved")
    if diagnostics["unselected_project_study"]:
        codes.append("project_case_unresolved")
    event = sealed(
        {
            "kind": "v2_planning_issues",
            "run_id": calls.run_id,
            "actor_id": calls.scope.actor_id,
            "project_id": calls.project_id,
            "manifest_hash": calls.manifest["manifest_hash"],
            "curriculum_hash": curriculum.plan_hash,
            "issues": [{"code": code, "message": _ISSUE_MESSAGES[code]} for code in codes],
        }
    )
    with calls.tx() as conn:
        calls._lock(conn)
        rows = conn.execute(
            "SELECT detail FROM ai_run_events WHERE run_id=%s AND status='v2_planning_issues'",
            (calls.run_id,),
        ).fetchall()
        if rows:
            if len(rows) != 1 or rows[0]["detail"] != event:
                raise V2RecoveryBlocked("Incomplete curriculum facts differ")
        else:
            conn.execute(
                "INSERT INTO ai_run_events(run_id,status,detail) VALUES(%s,'v2_planning_issues',%s)",
                (calls.run_id, Jsonb(event)),
            )


def read_planning_issues(dsn, *, scope, project_id, run_id):
    from app.infrastructure.db.v2_revisions import frozen_submission

    with PgV2Clarifications(dsn).tx(scope, project_id) as conn:
        state = conn.execute(
            "SELECT status,error_class,actor_id FROM ai_runs WHERE run_id=%s AND project_id=%s",
            (run_id, project_id),
        ).fetchone()
        if (
            state is None
            or state["actor_id"] != scope.actor_id
            or state["status"] != "failed"
            or state["error_class"] != "v2_curriculum_incomplete"
        ):
            return ()
        try:
            submission = frozen_submission(
                conn, actor_id=scope.actor_id, project_id=project_id, run_id=run_id
            )
            rows = conn.execute(
                "SELECT detail FROM ai_run_events WHERE run_id=%s AND status='v2_planning_issues'", (run_id,)
            ).fetchall()
            if len(rows) != 1:
                return ()
            event = rows[0]["detail"]
            if (
                not intact(event)
                or event.get("manifest_hash") != submission["manifest"]["manifest_hash"]
                or event.get("actor_id") != scope.actor_id
                or event.get("project_id") != project_id
                or event.get("run_id") != run_id
                or not 1 <= len(event["issues"]) <= 4
                or any(
                    item != {"code": item["code"], "message": _ISSUE_MESSAGES.get(item["code"])}
                    for item in event["issues"]
                )
            ):
                return ()
            return tuple(event["issues"])
        except (V2RecoveryBlocked, KeyError, ValueError, TypeError):
            return ()
