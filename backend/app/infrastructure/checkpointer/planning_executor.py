"""Persist current short-generation checkpoints with lease and integrity guards."""
from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

import psycopg
from app.agent_workflows.graphs import PlanningTrace
from app.agent_workflows.nodes import PlanningNodes
from app.agent_workflows.planning_batches import (
    SHORT_GENERATION_VERSION,
    build_short_planning_graph,
    manifest_is_intact,
    recursion_limit,
)
from app.agent_workflows.planning_outline import STAGE_SKELETON_V1, frozen_pack_is_intact
from app.agent_workflows.planning_structure import check_structure_checkpoint
from app.agent_workflows.runtime import PostgresSaver
from app.agent_workflows.state import PlanningState
from app.ports.graph_runner import GraphRecoveryError
from psycopg.rows import dict_row

__all__ = ["PgPlanningExecutor", "builder_for_version"]


def builder_for_version(graph_version: str) -> Any:
    """Only the current frozen protocol is executable; never reinterpret old threads."""
    if graph_version == SHORT_GENERATION_VERSION:
        return build_short_planning_graph
    raise GraphRecoveryError(f"不支持的图协议版本，拒绝执行：{graph_version!r}")


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
            graph_version=str((initial or {}).get("graph_version") or ""),
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
        if nodes.frozen_input is None and initial is not None:
            from copy import deepcopy
            nodes.frozen_input = deepcopy(initial)
        manifest = (initial or {}).get("manifest")
        with self._saver(thread_id) as saver:
            graph = builder(nodes, checkpointer=saver)
            config: dict[str, Any] = {"configurable": {"thread_id": thread_id}, "recursion_limit": 1000}
            if isinstance(manifest, dict):
                config["recursion_limit"] = recursion_limit(manifest)
            guard()
            existing = graph.get_state(config)
            if existing.values:
                try:
                    check_structure_checkpoint(existing.values)
                    nodes.check_projection(existing.values, final=existing.next == ('save_draft_projection',),
                                           pending_repair=existing.next == ('repair_batch',))
                except ValueError as exc:
                    raise GraphRecoveryError(str(exc)) from exc
                stored_manifest = existing.values.get("manifest")
                if isinstance(stored_manifest, dict):
                    if ("manifest_hash" in stored_manifest or "outline_input_format" in stored_manifest) and not manifest_is_intact(stored_manifest):
                        raise GraphRecoveryError("Checkpoint frozen manifest integrity mismatch")
                    if isinstance(manifest, dict) and json.dumps(stored_manifest, sort_keys=True, ensure_ascii=False) != json.dumps(manifest, sort_keys=True, ensure_ascii=False):
                        raise GraphRecoveryError("Checkpoint frozen manifest mismatch")
                    if stored_manifest.get("outline_input_format") == STAGE_SKELETON_V1 and not frozen_pack_is_intact(existing.values.get("domain_pack") or {}, stored_manifest):
                        raise GraphRecoveryError("Checkpoint frozen pack integrity mismatch")
                elif isinstance(manifest, dict) and manifest.get("outline_input_format") == STAGE_SKELETON_V1:
                    raise GraphRecoveryError("Checkpoint frozen manifest missing")
                stored_version = existing.values.get("graph_version")
                if stored_version is not None and stored_version != graph_version:
                    raise GraphRecoveryError("Checkpoint graph version mismatch")
                if not existing.next:
                    # Recover committed result without another provider request.
                    return PlanningTrace([], existing.values, None)
                if existing.next == ("await_approval",):
                    raise GraphRecoveryError("Checkpoint 等待用户确认，Worker 不得自动续跑")
                guard()
                self._stream(graph, None, config, progress)
            else:
                self._stream(graph, initial, config, progress)
            snapshot = graph.get_state(config)
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
