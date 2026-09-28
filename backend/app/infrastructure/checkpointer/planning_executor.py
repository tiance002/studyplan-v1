"""Persist actual StateGraph checkpoints; synchronous minimal runtime, no queue claim."""
from __future__ import annotations

from contextlib import contextmanager

import psycopg
from app.agent_workflows.graphs import PlanningTrace, build_planning_graph
from app.agent_workflows.nodes import PlanningNodes
from app.agent_workflows.runtime import Command, PostgresSaver
from app.ports.graph_runner import GraphRecoveryError
from psycopg.rows import dict_row


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
        with self._saver(thread_id) as saver:
            graph = build_planning_graph(nodes, checkpointer=saver)
            config = {"configurable": {"thread_id":thread_id}}
            existing = graph.get_state(config)
            if existing.values:
                raise GraphRecoveryError("Refusing to redispatch an existing generation")
            graph.invoke(initial, config)
            snapshot = graph.get_state(config)
            waiting = snapshot.next == ("await_approval",)
            return PlanningTrace([], snapshot.values, "await_approval" if waiting else "failed_validation")

    def finish(self, *, thread_id, graph_version, decision, result_id, draft_hash):
        # Business publish/cancel already committed. These callbacks acknowledge its
        # durable result and never repeat the business operation or a model call.
        nodes = PlanningNodes(llm=self.llm, commit_plan=lambda s:result_id)
        with self._saver(thread_id) as saver:
            graph = build_planning_graph(nodes, checkpointer=saver)
            config = {"configurable": {"thread_id":thread_id}}
            snapshot = graph.get_state(config)
            if snapshot.values.get("graph_version") != graph_version:
                raise GraphRecoveryError("Graph version mismatch")
            if not snapshot.next:
                if snapshot.values.get("decision") != decision or str(snapshot.values.get("result_id") or "") != result_id:
                    raise GraphRecoveryError("Checkpoint result mismatch")
                return
            if snapshot.next != ("await_approval",):
                raise GraphRecoveryError("Checkpoint is not waiting for approval")
            graph.invoke(Command(resume={"decision":decision,"draft_hash":draft_hash}), config)
            if graph.get_state(config).next:
                raise GraphRecoveryError("Graph did not finish")
