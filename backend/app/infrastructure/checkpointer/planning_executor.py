"""Persist actual StateGraph checkpoints; version-selected generation and resume.

The stored ``graph_version`` decides *which* builder runs a thread:

- ``b3f2-batch-v1`` -> the batched protocol (``build_batched_planning_graph``);
- a known legacy version -> the original single-pass graph;
- anything else -> refused, never guessed from the current default.

A thread's checkpoint is only ever resumed, never re-explained by a different
protocol, and a terminal or waiting-for-user checkpoint is never regenerated.
"""
from __future__ import annotations

from contextlib import contextmanager

import psycopg
from app.agent_workflows.graphs import PlanningTrace, build_planning_graph
from app.agent_workflows.nodes import PlanningNodes
from app.agent_workflows.planning_batches import (
    PROTOCOL_VERSION,
    build_batched_planning_graph,
    recursion_limit,
)
from app.agent_workflows.runtime import Command, PostgresSaver
from app.ports.graph_runner import GraphRecoveryError
from psycopg.rows import dict_row

#: Versions the legacy single-pass builder is known to have produced.
LEGACY_GRAPH_VERSIONS = frozenset({"1", "planning-legacy-v1"})


def builder_for_version(graph_version: str):
    """Select the graph builder for a stored version; unknown versions are refused."""
    if graph_version == PROTOCOL_VERSION:
        return build_batched_planning_graph
    if graph_version in LEGACY_GRAPH_VERSIONS:
        return build_planning_graph
    raise GraphRecoveryError(f"未知图版本，拒绝按当前默认版本解释：{graph_version!r}")


class PgPlanningExecutor:
    def __init__(self, dsn, *, llm):
        self.dsn = dsn
        self.llm = llm

    @contextmanager
    def _saver(self, thread_id):
        # Session advisory lock serializes a thread across processes; closed on exit.
        with psycopg.connect(self.dsn, autocommit=True, row_factory=dict_row) as conn:
            conn.execute("SELECT pg_advisory_lock(hashtextextended(%s,0))", (thread_id,))
            yield PostgresSaver(conn)

    def execute(self, nodes, initial, thread_id):
        """Legacy single-pass entry point (kept for existing callers)."""
        return self.execute_or_resume(
            nodes, initial, thread_id,
            graph_version=str((initial or {}).get("graph_version") or "1"),
            guard=lambda: None,
        )

    def execute_or_resume(self, nodes, initial, thread_id, graph_version, guard):
        """Run or resume one thread under its stored graph version.

        - no checkpoint -> first invoke with the frozen initial state;
        - a non-terminal checkpoint -> resume with ``invoke(None, config)`` and let
          the graph continue from the last completed batch (no re-generation);
        - a terminal or waiting-for-user checkpoint -> refuse to regenerate.
        The ``guard`` (zero-argument) revalidates the lease and Run status before
        each step and before every dispatch.
        """
        builder = builder_for_version(graph_version)
        with self._saver(thread_id) as saver:
            graph = builder(nodes, checkpointer=saver)
            config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 1000}
            manifest = (initial or {}).get("manifest")
            if graph_version == PROTOCOL_VERSION and isinstance(manifest, dict):
                config["recursion_limit"] = recursion_limit(manifest)
            guard()
            existing = graph.get_state(config)
            if existing.values:
                if not existing.next:
                    raise GraphRecoveryError("Checkpoint 已到终态，拒绝重新生成")
                if existing.next == ("await_approval",):
                    raise GraphRecoveryError("Checkpoint 等待用户确认，Worker 不得自动续跑")
                guard()
                graph.invoke(None, config)
            else:
                graph.invoke(initial, config)
            snapshot = graph.get_state(config)
            if snapshot.next == ("await_approval",):
                return PlanningTrace([], snapshot.values, "await_approval")
            if not snapshot.next:
                return PlanningTrace([], snapshot.values, None)
            return PlanningTrace([], snapshot.values, "failed_validation")

    def finish(self, *, thread_id, graph_version, decision, result_id, draft_hash):
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
