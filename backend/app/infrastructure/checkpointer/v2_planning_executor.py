"""Small sequential V2 state on the existing guarded PostgresSaver."""

import psycopg
from app.agent_workflows.runtime import PostgresSaver
from app.core.ids import content_hash
from app.infrastructure.db.plan_repository import to_psycopg_dsn
from app.infrastructure.providers.v2_attempts import V2_EXECUTION_VERSION, V2RecoveryBlocked


class PgV2Checkpoints:
    def __init__(self, dsn, *, calls, thread_id):
        self.dsn, self.calls, self.thread_id = to_psycopg_dsn(dsn), calls, thread_id
        with calls.tx() as conn:
            row = conn.execute(
                "SELECT thread_id FROM ai_runs WHERE run_id=%s AND project_id=%s AND actor_id=%s",
                (calls.run_id, calls.project_id, calls.scope.actor_id),
            ).fetchone()
        if row is None or row["thread_id"] != thread_id:
            raise V2RecoveryBlocked("V2 checkpoint thread differs from actual Run binding")
        self.config = {"configurable": {"thread_id": thread_id, "checkpoint_ns": V2_EXECUTION_VERSION}}

    def load(self):
        self.calls.guard()
        with psycopg.connect(self.dsn, autocommit=True) as conn:
            conn.execute("SELECT pg_advisory_lock(hashtextextended(%s,0))", (self.thread_id,))
            result = PostgresSaver(conn).get_tuple(self.config)
        if result is None:
            return None
        value = result.checkpoint["channel_values"]["state"]
        if (
            value.get("manifest_hash") != self.calls.manifest["manifest_hash"]
            or value.get("run_id") != self.calls.run_id
            or value.get("digest") != content_hash({k: v for k, v in value.items() if k != "digest"})
        ):
            raise V2RecoveryBlocked("V2 checkpoint identity/integrity mismatch")
        return value["state"]

    def save(self, state):
        from langgraph.checkpoint.base import empty_checkpoint

        self.calls.guard()
        value = {
            "run_id": self.calls.run_id,
            "manifest_hash": self.calls.manifest["manifest_hash"],
            "state": state,
        }
        value["digest"] = content_hash(value)
        with self.calls.tx() as business:
            self.calls._lock(business, published_draft_id=state.get("draft_id")
                if state.get("stage") == "draft_persistence" else None)
            with psycopg.connect(self.dsn, autocommit=True) as conn:
                conn.execute("SELECT pg_advisory_lock(hashtextextended(%s,0))", (self.thread_id,))
                saver = PostgresSaver(conn)
                previous = saver.get_tuple(self.config)
                if previous:
                    old = previous.checkpoint["channel_values"]["state"]
                    if (
                        old.get("run_id") != self.calls.run_id
                        or old.get("manifest_hash") != self.calls.manifest["manifest_hash"]
                    ):
                        raise V2RecoveryBlocked("V2 previous checkpoint belongs to another frozen Run")
                checkpoint = empty_checkpoint()
                version = 1 + (previous.checkpoint["channel_versions"].get("state", 0) if previous else 0)
                checkpoint["channel_values"] = {"state": value}
                checkpoint["channel_versions"] = {"state": version}
                self.config = saver.put(
                    previous.config if previous else self.config,
                    checkpoint,
                    {"source": "update", "step": version, "parents": {}},
                    {"state": version},
                )
        self.calls.guard()
