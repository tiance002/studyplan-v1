"""Persist actual StateGraph checkpoints for the one official generation protocol.

There is exactly **one** generation protocol: ``b3f2-batch-v1``. This module
therefore does not route by version any more — it either builds the batched graph
or refuses.

Rules that still hold:

- a thread's checkpoint is only ever resumed, never re-explained by a different
  protocol;
- a terminal or waiting-for-user checkpoint is never regenerated;
- the ``guard`` revalidates the lease and Run status before each step and before
  every paid dispatch;
- business progress is emitted only after a checkpoint has been committed.
"""
from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

import psycopg
from app.agent_workflows.graphs import PlanningTrace
from app.agent_workflows.nodes import PlanningNodes
from app.agent_workflows.planning_batches import (
    PROTOCOL_VERSION,
    build_batched_planning_graph,
    recursion_limit,
)
from app.agent_workflows.runtime import Command, PostgresSaver
from app.agent_workflows.state import PlanningState
from app.ports.graph_runner import GraphRecoveryError
from psycopg.rows import dict_row

__all__ = ["PgPlanningExecutor", "builder_for_version"]


def builder_for_version(graph_version: str) -> Any:
    """Return the builder for the only supported protocol; refuse anything else.

    A legacy or unknown version is **never** guessed from the current default:
    re-explaining an old thread with the new protocol would silently change what
    the stored checkpoint means. Refusing is the safe outcome.
    """
    if graph_version == PROTOCOL_VERSION:
        return build_batched_planning_graph
    raise GraphRecoveryError(
        f"不支持的图协议版本，拒绝按当前默认版本解释：{graph_version!r}；"
        f"当前唯一协议为 {PROTOCOL_VERSION!r}"
    )


class PgPlanningExecutor:
    def __init__(self, dsn, *, llm):
        self.dsn = dsn
        self.llm = llm

    @contextmanager
    def _saver(self, thread_id) -> Iterator[PostgresSaver]:
        # Session advisory lock serializes a thread across processes; closed on exit.
        with psycopg.connect(self.dsn, autocommit=True, row_factory=dict_row) as conn:
            conn.execute("SELECT pg_advisory_lock(hashtextextended(%s,0))", (thread_id,))
            yield PostgresSaver(conn)

    def execute(self, nodes: PlanningNodes, initial: PlanningState, thread_id: str) -> Any:
        """Run a thread that carries no stored version (synchronous callers)."""
        return self.execute_or_resume(
            nodes, initial, thread_id,
            graph_version=str((initial or {}).get("graph_version") or PROTOCOL_VERSION),
            guard=lambda: None,
        )

    def execute_or_resume(
        self,
        nodes: PlanningNodes,
        initial: PlanningState | None,
        thread_id: str,
        graph_version: str,
        guard: Callable[[], None],
        *,
        progress: Callable[[PlanningState], None] | None = None,
    ) -> Any:
        """Run or resume one thread under the official protocol.

        - no checkpoint -> first invoke with the frozen initial state;
        - a non-terminal checkpoint -> resume with ``invoke(None, config)`` and let
          the graph continue from the last completed batch (no re-generation);
        - a terminal or waiting-for-user checkpoint -> refuse to regenerate.

        ``progress`` is called once per committed checkpoint (never mid-batch), so
        a crash simply re-derives progress from the checkpoint instead of losing it.
        """
        builder = builder_for_version(graph_version)
        manifest = (initial or {}).get("manifest")
        with self._saver(thread_id) as saver:
            graph = builder(nodes, checkpointer=saver)
            config: dict[str, Any] = {"configurable": {"thread_id": thread_id}, "recursion_limit": 1000}
            if isinstance(manifest, dict):
                config["recursion_limit"] = recursion_limit(manifest)
            guard()
            existing = graph.get_state(config)
            if existing.values:
                if not existing.next:
                    raise GraphRecoveryError("Checkpoint 已到终态，拒绝重新生成")
                if existing.next == ("await_approval",):
                    raise GraphRecoveryError("Checkpoint 等待用户确认，Worker 不得自动续跑")
                guard()
                self._stream(graph, None, config, progress)
            else:
                self._stream(graph, initial, config, progress)
            snapshot = graph.get_state(config)
            if snapshot.next == ("await_approval",):
                return PlanningTrace([], snapshot.values, "await_approval")
            if not snapshot.next:
                return PlanningTrace([], snapshot.values, None)
            return PlanningTrace([], snapshot.values, "failed_validation")

    @staticmethod
    def _stream(
        graph: Any,
        payload: Any,
        config: dict[str, Any],
        progress: Callable[[PlanningState], None] | None,
    ) -> None:
        """Advance the graph, reporting each committed state to ``progress``.

        ``stream_mode="values"`` yields the accumulated state once per committed
        checkpoint, which is exactly the "stable point" the design asks for.
        """
        if progress is None:
            graph.invoke(payload, config)
            return
        for state in graph.stream(payload, config, stream_mode="values"):
            if isinstance(state, dict):
                progress(state)  # type: ignore[arg-type]

    def finish(self, *, thread_id, graph_version, decision, result_id, draft_hash) -> None:
        # Business publish/cancel already committed. These callbacks acknowledge its
        # durable result and never repeat the business operation or a model call.
        nodes = PlanningNodes(llm=self.llm, commit_plan=lambda s: result_id)
        builder = builder_for_version(graph_version)
        with self._saver(thread_id) as saver:
            graph = builder(nodes, checkpointer=saver)
            config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 1000}
            snapshot = graph.get_state(config)
            if snapshot.values.get("graph_version") != graph_version:
                raise GraphRecoveryError("Graph version mismatch")
            if not snapshot.next:
                if snapshot.values.get("decision") != decision or str(snapshot.values.get("result_id") or "") != result_id:
                    raise GraphRecoveryError("Checkpoint result mismatch")
                return
            if snapshot.next != ("await_approval",):
                raise GraphRecoveryError("Checkpoint is not waiting for approval")
            graph.invoke(Command(resume={"decision": decision, "draft_hash": draft_hash}), config)
            if graph.get_state(config).next:
                raise GraphRecoveryError("Graph did not finish")
