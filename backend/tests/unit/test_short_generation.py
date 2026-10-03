"""Short generation completes at the saved draft; legacy graphs stay frozen."""

from app.agent_workflows.nodes import PlanningNodes
from app.agent_workflows.planning_batches import (
    DEFAULT_BUDGET,
    PROTOCOL_VERSION,
    build_short_planning_graph,
    freeze_manifest,
    run_batched_planning_graph,
)
from app.infrastructure import domain_pack

from tests.helpers.batched_planning import ScriptedLLM

SHORT_VERSION = "b3f2-short-v2"


def test_new_protocol_ends_after_draft_without_user_interrupt():
    pack = domain_pack.load_pack("agent-application-v3.json")
    llm = ScriptedLLM(pack)
    nodes = PlanningNodes(llm=llm, save_draft=lambda state: {"draft_ref": "draft:1", "draft_hash": "hash:1"})
    trace = run_batched_planning_graph(nodes, {
        "goal": "学习 Agent 应用开发", "run_id": "short:1", "domain_pack": pack,
        "graph_version": SHORT_VERSION,
    })
    assert trace.stopped_at is None
    assert trace.state["draft_ref"] == "draft:1"
    assert trace.visited[-1] == "save_draft_projection"
    assert len(llm.calls) == 19


def test_legacy_protocol_keeps_original_interrupt():
    pack = domain_pack.load_pack("agent-application-v3.json")
    llm = ScriptedLLM(pack)
    trace = run_batched_planning_graph(
        PlanningNodes(llm=llm, save_draft=lambda state: {"draft_ref": "old:1", "draft_hash": "h"}),
        {"goal": "学习 Agent 应用开发", "run_id": "old:1", "domain_pack": pack,
         "graph_version": PROTOCOL_VERSION},
    )
    assert trace.stopped_at == "await_approval"


def test_real_short_graph_has_terminal_checkpoint_after_draft():
    import pytest

    memory = pytest.importorskip("langgraph.checkpoint.memory")
    pack = domain_pack.load_pack("agent-application-v3.json")
    llm = ScriptedLLM(pack)
    nodes = PlanningNodes(llm=llm, save_draft=lambda state: {"draft_ref": "draft:1", "draft_hash": "hash:1"})
    graph = build_short_planning_graph(nodes, checkpointer=memory.InMemorySaver())
    config = {"configurable": {"thread_id": "short-real"}, "recursion_limit": 1000}
    graph.invoke({"goal": "学习 Agent 应用开发", "run_id": "short-real", "domain_pack": pack,
                  "graph_version": SHORT_VERSION, "manifest": freeze_manifest(pack, DEFAULT_BUDGET, "test")}, config)
    snapshot = graph.get_state(config)
    assert snapshot.next == ()
    assert snapshot.values["draft_ref"] == "draft:1"
    assert "await_approval" not in graph.get_graph().nodes
    assert len(llm.calls) == 19
