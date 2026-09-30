"""Create *real* legacy waiting_user checkpoints from the pre-Task-1 code.

The design requires old-graph compatibility evidence produced by the actual code
that shipped before this work (commit ``39e79ad``), not by a new graph that merely
imitates the old state shape. This helper extracts ``backend/app`` at that commit
into a temporary directory, records the source hashes, and runs a child process
that imports *that* ``app`` package to drive the legacy graph to its interrupt.

The extracted tree is throwaway test data. Nothing here touches the existing
business database, existing checkpoints, or the current working tree.
"""

from __future__ import annotations

import hashlib
import io
import subprocess
import sys
import tarfile
from dataclasses import dataclass
from pathlib import Path

#: The commit immediately before the B3-F2 implementation began.
LEGACY_COMMIT = "39e79ad"

#: Modules whose exact source defines the legacy graph behaviour.
LEGACY_SOURCES = (
    "backend/app/agent_workflows/graphs.py",
    "backend/app/agent_workflows/nodes.py",
    "backend/app/agent_workflows/state.py",
    "backend/app/agent_workflows/validators.py",
)


@dataclass(frozen=True)
class LegacySource:
    """An extracted legacy tree plus the hashes that pin its behaviour."""

    import_root: Path
    hashes: dict[str, str]

    @property
    def digest(self) -> str:
        return hashlib.sha256(
            "".join(f"{name}:{self.hashes[name]}" for name in sorted(self.hashes)).encode()
        ).hexdigest()


def export_legacy_source(dest: Path, *, repo_root: Path, commit: str = LEGACY_COMMIT) -> LegacySource:
    """Extract ``backend/app`` at ``commit`` into ``dest`` and hash the key modules."""
    archive = subprocess.run(
        ["git", "archive", commit, "backend/app"],
        cwd=str(repo_root), capture_output=True, check=True,
    )
    with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as tar:
        tar.extractall(dest, filter="data")
    hashes: dict[str, str] = {}
    for name in LEGACY_SOURCES:
        path = dest / name
        hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return LegacySource(import_root=dest / "backend", hashes=hashes)


#: Child script: run the *legacy* graph to its interrupt and record the checkpoint.
LEGACY_CHILD_SCRIPT = '''
import json, sys
sys.path.insert(0, sys.argv[4])  # the extracted 39e79ad backend

from app.agent_workflows.graphs import build_planning_graph
from app.agent_workflows.nodes import PlanningNodes
from app.infrastructure.providers.fake import FakeLLM
from langgraph.checkpoint.postgres import PostgresSaver

dsn, thread_id, out_path, _root = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]

GOOD_NODES = [{"stable_key": "n1", "title": "N"}]
GOOD_UNITS = [{"stable_key": "u1", "title": "U", "order_index": 0}]
GOOD_TASKS = [{"stable_key": "t1", "title": "T", "order_index": 0, "acceptance": ["a"]}]
GOOD_LINKS = [{"task_stable_key": "t1", "node_stable_key": "n1", "role": "core"}]
calls = []

def outline(purpose, payload):
    calls.append(purpose)
    return {"outline_ref": "o:1", "sections": ["core"]}

def structure(purpose, payload):
    calls.append(purpose)
    return {"nodes": GOOD_NODES, "units": GOOD_UNITS, "relations": []}

def practice(purpose, payload):
    calls.append(purpose)
    return {"tasks": GOOD_TASKS, "task_knowledge_links": GOOD_LINKS}

llm = FakeLLM({"planning.outline": outline, "planning.structure": structure,
               "planning.practice": practice})
nodes = PlanningNodes(llm=llm, save_draft=lambda s: {"draft_ref": "draft:legacy",
                                                     "draft_hash": "hash:legacy"},
                      commit_plan=lambda s: "plan:legacy")

with PostgresSaver.from_conn_string(dsn) as saver:
    saver.setup()
    graph = build_planning_graph(nodes, checkpointer=saver)
    cfg = {"configurable": {"thread_id": thread_id}}
    graph.invoke({"run_id": "run-legacy", "project_id": "legacy_p1", "goal": "学会 Agent",
                  "graph_version": "1"}, cfg)
    state = graph.get_state(cfg)
    payload = {"next": list(state.next), "draft_ref": state.values.get("draft_ref"),
               "draft_hash": state.values.get("draft_hash"),
               "graph_version": state.values.get("graph_version"),
               "model_calls": len(calls)}
with open(out_path, "w", encoding="utf-8") as fh:
    json.dump(payload, fh, ensure_ascii=False)
print("LEGACY_CHILD_OK")
'''


def run_legacy_child(source: LegacySource, *, dsn: str, thread_id: str, out_path: Path) -> dict:
    """Run the extracted legacy code in a fresh process to persist one checkpoint."""
    result = subprocess.run(
        [sys.executable, "-c", LEGACY_CHILD_SCRIPT, dsn, thread_id, str(out_path), str(source.import_root)],
        capture_output=True, text=True, cwd=str(source.import_root.parent),
    )
    if result.returncode != 0:
        raise AssertionError(f"legacy child failed: {result.stderr[-1500:]}")
    import json

    return json.loads(out_path.read_text(encoding="utf-8"))


__all__ = [
    "LEGACY_COMMIT",
    "LEGACY_CHILD_SCRIPT",
    "LEGACY_SOURCES",
    "LegacySource",
    "export_legacy_source",
    "run_legacy_child",
]
