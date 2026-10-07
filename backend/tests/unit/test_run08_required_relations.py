"""Run 08 business outputs replayed through deterministic validators and StateGraph."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from app.agent_workflows.nodes import PlanningNodes
from app.agent_workflows.planning_batches import (
    DEFAULT_BUDGET,
    build_short_planning_graph as build_fixture_graph,
    freeze_manifest,
    merge_batches,
    recursion_limit,
    run_batched_planning_graph,
    structure_payload,
    validate_structure_batch,
)
from app.agent_workflows.validators import validate_route_structure
from app.infrastructure.domain_pack import load_pack
from langgraph.checkpoint.memory import InMemorySaver

from tests.helpers.batched_planning import PRACTICE, REPAIR, STRUCTURE, ScriptedLLM

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "b3f2_run08_required_relations.json"
MISSING = {
    "stage.model_api": ("node.environment", "node.model_api"),
    "stage.capstone": ("node.reliability", "node.capstone"),
}


def _data():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _error(stage):
    source, target = MISSING[stage]
    return f"缺少领域前置依赖：{source} -> {target}（{stage}）"


def _corrected(batch):
    # A corrected offline provider answer, never production edge injection.
    result = deepcopy(batch)
    source, target = MISSING[batch["stage_key"]]
    result["relations"].append({"from_stable_key": source, "to_stable_key": target,
                                "relation_type": "prerequisite"})
    return result


def test_saved_run08_reproduces_the_two_final_validation_errors():
    data = _data()
    pack = load_pack("agent-application-v1.json")
    manifest = freeze_manifest(pack, DEFAULT_BUDGET, "mock:run08")
    merged = merge_batches(data["outline"], data["structure_batches"], data["practice_batches"],
                           pack, manifest=manifest)
    assert merged["errors"] == []
    assert validate_route_structure({"domain_pack": pack, "outline": data["outline"], **merged}) == [
        "缺少领域前置依赖：node.environment -> node.model_api",
        "缺少领域前置依赖：node.reliability -> node.capstone",
    ] == data["final_errors"]


@pytest.mark.parametrize("stage", MISSING)
def test_saved_omission_is_detected_locally_without_mutating_the_payload(stage):
    batch = next(b for b in _data()["structure_batches"] if b["stage_key"] == stage)
    original = deepcopy(batch)
    pack = load_pack("agent-application-v1.json")
    manifest = freeze_manifest(pack, DEFAULT_BUDGET, "mock:run08")
    spec = next(b for b in manifest["structure_batches"] if b["stage_key"] == stage)
    assert validate_structure_batch(batch, spec, pack) == [_error(stage)]
    assert batch == original
    assert validate_structure_batch(_corrected(batch), spec, pack) == []


@pytest.mark.parametrize("mode", ["missing", "reversed", "wrong_type"])
@pytest.mark.parametrize("relation_type", ["contains", "prerequisite"])
def test_declared_local_relations_require_exact_type_and_direction(mode, relation_type):
    pack = load_pack("agent-application-v1.json")
    manifest = freeze_manifest(pack, DEFAULT_BUDGET, "mock")
    spec = manifest["structure_batches"][1]
    context = structure_payload({"domain_pack": pack, "manifest": manifest}, spec)
    batch = ScriptedLLM(pack)._structure(context)
    edge = next(r for r in batch["relations"] if r["relation_type"] == relation_type)
    target = edge["to_stable_key"]
    expected = (f"缺少子知识关联：{target}（{spec['stage_key']}）" if relation_type == "contains" else
                f"缺少领域前置依赖：{edge['from_stable_key']} -> {target}（{spec['stage_key']}）")
    if mode == "missing":
        batch["relations"].remove(edge)
    elif mode == "reversed":
        edge["from_stable_key"], edge["to_stable_key"] = edge["to_stable_key"], edge["from_stable_key"]
    else:
        edge["relation_type"] = "prerequisite" if relation_type == "contains" else "contains"
    assert validate_structure_batch(batch, spec, pack) == [expected]


def test_generic_batch_without_frozen_inventory_is_unaffected():
    pack = {"resource_support": "search_only"}
    manifest = freeze_manifest(pack, DEFAULT_BUDGET, "mock")
    spec = manifest["structure_batches"][0]
    context = structure_payload({"domain_pack": pack, "manifest": manifest}, spec)
    assert validate_structure_batch(ScriptedLLM(pack)._structure(context), spec, pack) == []


def test_required_prerequisite_within_the_same_stage_is_checked():
    pack = load_pack("agent-application-v1.json")
    blueprint = next(b for b in pack["knowledge_blueprints"] if b["stable_key"] == "node.model_api.1")
    blueprint["prerequisite_keys"] = ["node.model_api"]
    manifest = freeze_manifest(pack, DEFAULT_BUDGET, "mock")
    spec = manifest["structure_batches"][1]
    context = structure_payload({"domain_pack": pack, "manifest": manifest}, spec)
    batch = ScriptedLLM(pack)._structure(context)
    assert validate_structure_batch(batch, spec, pack) == []
    batch["relations"] = [r for r in batch["relations"] if r != {
        "from_stable_key": "node.model_api", "to_stable_key": "node.model_api.1", "relation_type": "prerequisite",
    }]
    assert validate_structure_batch(batch, spec, pack) == [
        "缺少领域前置依赖：node.model_api -> node.model_api.1（stage.model_api）",
    ]


class Run08Fake(ScriptedLLM):
    def __init__(self, pack, *, persistent=False, initially_correct=False):
        super().__init__(pack)
        self.data = _data()
        self.persistent = persistent
        self.initially_correct = initially_correct

    def _skeleton(self, payload):
        return deepcopy(self.data["outline"])

    def _structure(self, payload):
        stage = payload["stage"]["stable_key"]
        batch = next(b for b in self.data["structure_batches"] if b["stage_key"] == stage)
        return _corrected(batch) if self.initially_correct and stage in MISSING else deepcopy(batch)

    def _practice(self, payload):
        stage = payload["stage"]["stable_key"]
        return deepcopy(next(b["payload"] for b in self.data["practice_batches"] if b["stage_key"] == stage))

    def _repair(self, payload):
        stage = payload["target"]["stage_key"]
        assert payload["target"]["kind"] == "structure"
        assert payload["errors"] == [_error(stage)]
        assert payload["context"]["stage"]["stable_key"] == stage
        source, _ = MISSING[stage]
        assert source in payload["context"]["declared_external_prerequisite_keys"]
        assert source not in payload["context"]["required_unit_node_keys"]
        return deepcopy(payload["batch"]) if self.persistent else _corrected(payload["batch"])


def _real_run(fake, pack):
    drafts, failures = [], []

    def save(state):
        drafts.append(deepcopy(state))
        return {"draft_ref": "offline-draft", "draft_hash": "offline-hash"}

    manifest = freeze_manifest(pack, DEFAULT_BUDGET, "mock:run08")
    nodes = PlanningNodes(llm=fake, save_draft=save,
                          on_failure=lambda state, errors: failures.append(list(errors)))
    graph = build_fixture_graph(nodes, checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "offline-run08"}, "recursion_limit": recursion_limit(manifest)}
    initial = {"goal": "从 Python 基础学习 Agent 应用开发", "run_id": "offline-run08",
               "domain_pack": pack, "manifest": manifest}
    updates = list(graph.stream(initial, config, stream_mode="updates"))
    visited = [name for update in updates for name in update if name != "__interrupt__"]
    return graph.get_state(config), visited, drafts, failures


@pytest.mark.parametrize("persistent", [False, True])
def test_real_graph_repairs_missing_edges_locally_and_obeys_shared_cap(persistent):
    pack = load_pack("agent-application-v1.json")
    fake = Run08Fake(pack, persistent=persistent)
    snapshot, visited, drafts, failures = _real_run(fake, pack)
    assert fake.count(REPAIR) == snapshot.values["repair_count"] == 2
    assert [visited[i + 1] for i, name in enumerate(visited) if name == "repair_batch"] == [
        "validate_structure_batch", "validate_structure_batch",
    ]
    assert len({call["attempt_id"] for call in fake.calls}) == len(fake.calls)
    if persistent:
        assert snapshot.next == ()
        assert snapshot.values["validation_errors"] == [_error("stage.model_api")]
        assert failures == [[_error("stage.model_api")]]
        assert drafts == [] and "merge_and_validate" not in visited
        assert fake.count() == 5 and fake.count(STRUCTURE) == 2 and fake.count(PRACTICE) == 0
    else:
        assert snapshot.next == ()
        assert snapshot.values["validation_errors"] == []
        assert len(drafts) == 1 and failures == []
        assert fake.count() == snapshot.values["manifest"]["max_requests"] == 21
        assert fake.count(STRUCTURE) == 9 and fake.count(PRACTICE) == 9
        assert visited.count("merge_and_validate") == 1
    interpreter_fake = Run08Fake(pack, persistent=persistent)
    trace = run_batched_planning_graph(PlanningNodes(llm=interpreter_fake, save_draft=lambda state: "d"),
                                      {"goal": "从 Python 基础学习 Agent 应用开发", "run_id": "offline-run08",
                                       "domain_pack": pack})
    assert trace.stopped_at == ("failed" if persistent else None)
    assert trace.state["validation_errors"] == snapshot.values["validation_errors"]
    assert [c["attempt_id"] for c in fake.calls] == [c["attempt_id"] for c in interpreter_fake.calls]


def test_complete_saved_answers_need_only_nineteen_requests():
    pack = load_pack("agent-application-v1.json")
    fake = Run08Fake(pack, initially_correct=True)
    snapshot, _, drafts, failures = _real_run(fake, pack)
    assert snapshot.next == ()
    assert snapshot.values["validation_errors"] == []
    assert fake.count() == 19 and fake.count(REPAIR) == 0
    assert len(drafts) == 1 and failures == []
