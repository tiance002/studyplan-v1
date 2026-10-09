"""Three owned acceptance decisions over real checkpoints and the original Run/Job.

No HTTP route, new table or synthetic persistence failure is involved. A pause
revokes the Worker claim atomically; a scoped CAS decision requeues that same job.
"""
from contextlib import contextmanager
from urllib.parse import urlsplit

import psycopg
from app.agent_workflows.runtime import PostgresSaver
from app.core.errors import ConflictError, IdempotencyConflictError, NotFoundError, ValidationAppError
from app.core.ids import content_hash
from app.domain.planning.v2_runtime import (
    OWNED_REVIEW_STAGES,
    V2_EXECUTION_VERSION,
    OwnedV2ReviewPending,
    V2RecoveryBlocked,
    wire,
)
from app.infrastructure.db.plan_repository import to_psycopg_dsn
from app.infrastructure.db.planning_fence import lock_plan_version
from app.infrastructure.db.v2_revisions import budget_family, frozen_submission
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


def _owned_dsn(dsn):
    normalized = to_psycopg_dsn(dsn)
    parsed = urlsplit(normalized)
    if parsed.hostname not in {"127.0.0.1", "::1", "localhost"} or not parsed.path.removeprefix("/").startswith("studyplan_test_"):
        raise ValidationAppError("Acceptance review requires a loopback owned test database")
    return normalized


def _seal(value):
    value = wire(value)
    return value | {"digest": content_hash(value)}


def _intact(value):
    return type(value) is dict and value.get("digest") == content_hash({k: v for k, v in value.items() if k != "digest"})


def _records(conn, *, run_id, manifest, stage, actor_id, project_id):
    rows = conn.execute("SELECT detail FROM ai_run_events WHERE run_id=%s AND status='v2_owned_review' AND detail->>'stage'=%s",
        (run_id, stage)).fetchall()
    if not rows:
        return None, None
    if len(rows) != 1:
        raise V2RecoveryBlocked("Owned review is ambiguous")
    review = rows[0]["detail"]
    if not _intact(review) or any(review.get(k) != v for k, v in {
        "run_id": run_id, "budget_root_run_id": run_id, "actor_id": actor_id, "project_id": project_id,
        "manifest_hash": manifest["manifest_hash"], "stage": stage,
    }.items()):
        raise V2RecoveryBlocked("Owned review identity/manifest rejected")
    decisions = conn.execute("SELECT detail FROM ai_run_events WHERE run_id=%s AND status='v2_owned_review_decision' AND detail->>'review_hash'=%s",
        (run_id, review["digest"])).fetchall()
    if len(decisions) > 1:
        raise V2RecoveryBlocked("Owned review decision is ambiguous")
    decision = decisions[0]["detail"] if decisions else None
    if decision is not None and (not _intact(decision) or decision.get("decision") not in {"approve", "reject"}
            or any(decision.get(k) != review[k] for k in ("run_id", "actor_id", "project_id", "manifest_hash", "stage"))):
        raise V2RecoveryBlocked("Owned review decision binding rejected")
    return review, decision


def authorize_owned_dispatch(conn, calls, purpose):
    """Permit only the next authorized phase; called under the budget/fence lock."""
    gate = calls.manifest.get("owned_acceptance")
    if gate is None:
        return
    if purpose not in gate["purpose_limits"]:
        raise V2RecoveryBlocked("Owned acceptance purpose is not authorized")
    required = ("goal_analysis" if purpose == "planning.capability_planning" else
        "capability_planning" if purpose not in {"planning.goal_requirement_analysis"} else None)
    if required is not None:
        review, decision = _records(conn, run_id=calls.run_id, manifest=calls.manifest, stage=required,
            actor_id=calls.scope.actor_id, project_id=calls.project_id)
        if review is None or decision is None or decision["decision"] != "approve":
            raise V2RecoveryBlocked("Owned acceptance phase has no approval")


def review_stage(calls, checkpoints, state, stage, **values):
    """Pause only after a real checkpoint; successful prior decisions replay unchanged."""
    if "owned_acceptance" not in calls.manifest:
        return None
    payload_hash = content_hash(wire(values))
    with calls.tx() as conn:
        calls._lock(conn)
        review, decision = _records(conn, run_id=calls.run_id, manifest=calls.manifest, stage=stage,
            actor_id=calls.scope.actor_id, project_id=calls.project_id)
        if review is not None:
            if review["payload_hash"] != payload_hash or decision is None or decision["decision"] != "approve":
                raise V2RecoveryBlocked("Owned review replay differs or remains unapproved")
            state.update(values)
            return None
    state.update(values)
    snapshot = wire(state | {"stage": stage})
    checkpoints.save(snapshot)
    with calls.tx() as conn:
        calls._lock(conn)
        # The live lease serializes review creation against replacement/cancel.
        if conn.execute("SELECT 1 FROM ai_provider_attempts WHERE run_id=ANY(%s) AND status IN('dispatched','reconciliation_required') LIMIT 1",
                (list(calls._budget_manifests(conn)),)).fetchone():
            raise V2RecoveryBlocked("Unknown dispatch blocks owned review")
        run = conn.execute("SELECT version,thread_id FROM ai_runs WHERE run_id=%s FOR UPDATE", (calls.run_id,)).fetchone()
        review = _seal({"run_id": calls.run_id, "budget_root_run_id": calls.run_id, "actor_id": calls.scope.actor_id,
            "project_id": calls.project_id, "manifest_hash": calls.manifest["manifest_hash"], "stage": stage,
            "thread_id": run["thread_id"], "checkpoint_hash": content_hash(snapshot), "payload_hash": payload_hash,
            "run_version": run["version"] + 1})
        conn.execute("INSERT INTO ai_run_events(run_id,status,detail) VALUES(%s,'v2_owned_review',%s)", (calls.run_id, Jsonb(review)))
        changed = conn.execute("UPDATE ai_runs SET status='waiting_user',next_action='review_draft',result_ref=NULL,error_class='owned_acceptance_review',version=version+1,updated_at=clock_timestamp() WHERE run_id=%s AND version=%s AND status='running'",
            (calls.run_id, run["version"]))
        job = conn.execute("UPDATE ai_jobs SET status='completed',lease_expires_at=NULL,lease_token=NULL,worker_id=NULL WHERE job_id=%s AND run_id=%s AND lease_token=%s AND status='running'",
            (calls.fence.job_id, calls.run_id, calls.fence.lease_token))
        if changed.rowcount != 1 or job.rowcount != 1:
            raise ConflictError("Owned review pause CAS rejected")
    return OwnedV2ReviewPending(stage, review["digest"])


class PgOwnedV2Reviews:
    def __init__(self, dsn, checkpoint_dsn):
        self.dsn, self.checkpoint_dsn = _owned_dsn(dsn), _owned_dsn(checkpoint_dsn)
        if self.dsn == self.checkpoint_dsn:
            raise ValidationAppError("Owned review requires separate checkpoint database")

    @contextmanager
    def tx(self, scope, project_id):
        scope.require_project(project_id)
        with psycopg.connect(self.dsn, row_factory=dict_row) as conn:
            conn.execute("SELECT set_config('app.actor_id',%s,true),set_config('app.project_id',%s,true)", (scope.actor_id, project_id))
            yield conn

    def _pending(self, conn, scope, project_id, run_id):
        submission = frozen_submission(conn, actor_id=scope.actor_id, project_id=project_id, run_id=run_id)
        manifest = submission["manifest"]
        if "owned_acceptance" not in manifest:
            raise ValidationAppError("Run has no frozen owned review policy")
        run = conn.execute("SELECT status,next_action,error_class,version,thread_id,result_ref FROM ai_runs WHERE run_id=%s AND actor_id=%s AND project_id=%s",
            (run_id, scope.actor_id, project_id)).fetchone()
        if run is None:
            raise NotFoundError("Owned review run not found")
        if (run["status"], run["next_action"], run["error_class"], run["result_ref"]) != ("waiting_user", "review_draft", "owned_acceptance_review", None):
            raise ConflictError("Run is not awaiting an owned review")
        pending = []
        for stage in OWNED_REVIEW_STAGES:
            review, decision = _records(conn, run_id=run_id, manifest=manifest, stage=stage, actor_id=scope.actor_id, project_id=project_id)
            if review is not None and decision is None:
                pending.append(review)
        if len(pending) != 1 or pending[0]["run_version"] != run["version"] or pending[0]["thread_id"] != run["thread_id"]:
            raise V2RecoveryBlocked("Owned review pending version/stage rejected")
        review = pending[0]
        with psycopg.connect(self.checkpoint_dsn, autocommit=True) as checkpoint:
            checkpoint.execute("SELECT pg_advisory_lock(hashtextextended(%s,0))", (run["thread_id"],))
            config = {"configurable": {"thread_id": run["thread_id"], "checkpoint_ns": V2_EXECUTION_VERSION}}
            item = PostgresSaver(checkpoint).get_tuple(config)
        value = item.checkpoint["channel_values"]["state"] if item else None
        if not _intact(value) or value.get("run_id") != run_id or value.get("manifest_hash") != manifest["manifest_hash"]:
            raise V2RecoveryBlocked("Owned review actual checkpoint binding rejected")
        state = value["state"]
        if state.get("stage") != review["stage"] or content_hash(state) != review["checkpoint_hash"]:
            raise V2RecoveryBlocked("Owned review actual checkpoint stage/hash rejected")
        return manifest, review, state

    def read(self, *, scope, project_id, run_id):
        with self.tx(scope, project_id) as conn:
            manifest, review, state = self._pending(conn, scope, project_id, run_id)
            return {"manifest": manifest, "review": review, "state": state}

    def decide(self, *, scope, project_id, run_id, stage, review_hash, expected_version,
               decision, idempotency_key, evidence_hash):
        if (stage not in OWNED_REVIEW_STAGES or decision not in {"approve", "reject"}
                or type(expected_version) is not int or expected_version < 1
                or type(idempotency_key) is not str or not 0 < len(idempotency_key) <= 128
                or type(evidence_hash) is not str or len(evidence_hash) != 64
                or any(c not in "0123456789abcdef" for c in evidence_hash)):
            raise ValidationAppError("Owned review decision needs exact version and evidence hash")
        fingerprint = content_hash({"stage": stage, "review_hash": review_hash, "expected_version": expected_version,
            "decision": decision, "evidence_hash": evidence_hash})
        key_hash = content_hash(idempotency_key)
        with self.tx(scope, project_id) as conn:
            root, family = budget_family(conn, actor_id=scope.actor_id, project_id=project_id, run_id=run_id)
            if root != run_id or "owned_acceptance" not in family[root]:
                raise V2RecoveryBlocked("Owned review must retain its original root")
            conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", ("studyplan:plan-budget:" + root,))
            lock_plan_version(conn, project_id, 0)
            conn.execute("SELECT 1 FROM ai_jobs j JOIN ai_runs r USING(run_id) JOIN learning_projects p ON p.project_id=r.project_id WHERE r.run_id=%s AND r.actor_id=%s AND r.project_id=%s AND p.owner_actor_id=%s AND p.archived_at IS NULL FOR UPDATE OF j,r,p",
                (run_id, scope.actor_id, project_id, scope.actor_id))
            previous = conn.execute("SELECT detail FROM ai_run_events WHERE run_id=%s AND status='v2_owned_review_decision' AND detail->>'key_hash'=%s", (run_id, key_hash)).fetchall()
            if previous:
                if len(previous) != 1 or not _intact(previous[0]["detail"]) or previous[0]["detail"].get("fingerprint") != fingerprint:
                    raise IdempotencyConflictError("Owned review key is already bound differently")
                return run_id
            if conn.execute("SELECT 1 FROM ai_provider_attempts WHERE run_id=ANY(%s) AND status IN('dispatched','reconciliation_required') LIMIT 1", (list(family),)).fetchone():
                raise V2RecoveryBlocked("Unknown family dispatch blocks owned review continuation")
            manifest, review, _ = self._pending(conn, scope, project_id, run_id)
            if (review["stage"], review["digest"], review["run_version"]) != (stage, review_hash, expected_version):
                raise ConflictError("Owned review decision is stale")
            from app.infrastructure.providers.v2_attempts import PgV2Calls
            usage = PgV2Calls.family_reservations(conn, family, list(family))
            if any(usage[k] > manifest["budget"]["max_" + k] for k in usage):
                raise V2RecoveryBlocked("Owned review budget integrity rejected")
            event = _seal({k: review[k] for k in ("run_id", "actor_id", "project_id", "manifest_hash", "stage")} | {
                "review_hash": review_hash, "decision": decision, "evidence_hash": evidence_hash,
                "expected_version": expected_version, "key_hash": key_hash, "fingerprint": fingerprint})
            conn.execute("INSERT INTO ai_run_events(run_id,status,detail) VALUES(%s,'v2_owned_review_decision',%s)", (run_id, Jsonb(event)))
            changed = conn.execute("UPDATE ai_runs SET status=%s,next_action=%s,error_class=%s,version=version+1,updated_at=clock_timestamp() WHERE run_id=%s AND version=%s AND status='waiting_user' AND error_class='owned_acceptance_review'",
                ("queued" if decision == "approve" else "failed", "wait" if decision == "approve" else "none",
                 None if decision == "approve" else "owned_acceptance_rejected", run_id, expected_version))
            job = conn.execute("UPDATE ai_jobs SET status=%s,available_at=clock_timestamp(),lease_expires_at=NULL,lease_token=NULL,worker_id=NULL WHERE run_id=%s AND status='completed' AND lease_token IS NULL",
                ("pending" if decision == "approve" else "failed", run_id))
            if changed.rowcount != 1 or job.rowcount != 1:
                raise ConflictError("Owned review continuation CAS rejected")
            return run_id
