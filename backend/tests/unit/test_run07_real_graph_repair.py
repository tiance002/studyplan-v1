"""Practice repair regression on the actual StateGraph, without provider/DB I/O."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from app.agent_workflows.nodes import PlanningNodes
from app.agent_workflows.planning_batches import (
    DEFAULT_BUDGET,
    build_short_planning_graph as build_fixture_graph,
    freeze_manifest,
    recursion_limit,
    route_after_batch_repair,
    run_batched_planning_graph,
)
from app.infrastructure.domain_pack import load_pack
from app.ports.llm import LLMDispatchUnknownError, LLMFailure
from langgraph.checkpoint.memory import InMemorySaver

from tests.helpers.batched_planning import PRACTICE, REPAIR, STRUCTURE, ScriptedLLM

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "b3f2_run07_practice_repair.json"
GOAL = "从 Python 基础学习 Agent 应用开发"
ROLE_ERROR = "实践批次第 2 条任务知识关联的 role 非法：'support'（stage.model_api）"


class Run07Fake(ScriptedLLM):
    def __init__(self, pack, *, persistent=False, repair_failure=None):
        super().__init__(pack)
        self.data = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.persistent = persistent
        self.repair_failure = repair_failure

    def _skeleton(self, payload):
        return deepcopy(self.data["outline"])

    def _structure(self, payload):
        return deepcopy(next(batch for batch in self.data["structure_batches"]
                             if batch["stage_key"] == payload["stage"]["stable_key"]))

    def _practice(self, payload):
        stage = payload["stage"]["stable_key"]
        batch = next((b for b in self.data["practice_batches"] if b["stage_key"] == stage), None)
        return deepcopy(batch["payload"]) if batch else super()._practice(payload)

    def _repair(self, payload):
        assert payload["target"]["kind"] == "practice"
        assert payload["errors"] == [ROLE_ERROR]
        assert payload["context"]["stage"]["stable_key"] == "stage.model_api"
        result = deepcopy(self.data["repair_outputs"][self.count(REPAIR) - 1])
        if not self.persistent:
            # Explicit corrected Fake answer, never production normalization.
            for link in result["task_knowledge_links"]:
                if link["role"] == "support":
                    link["role"] = "supporting"
        return result

    def generate_structured(self, **kwargs):
        if kwargs["purpose"] == REPAIR and self.repair_failure:
            self.calls.append(dict(kwargs))
            return LLMFailure(self.repair_failure, "offline failure",
                              dispatch_unknown=self.repair_failure == "provider_transport_unknown")
        return super().generate_structured(**kwargs)


def _real_run(fake, pack):
    drafts, failures = [], []

    def save(state):
        drafts.append(deepcopy(state))
        return {"draft_ref": "offline-draft", "draft_hash": "offline-hash"}

    manifest = freeze_manifest(pack, DEFAULT_BUDGET, "mock:run07")
    nodes = PlanningNodes(llm=fake, save_draft=save,
                          on_failure=lambda state, errors: failures.append(list(errors)))
    graph = build_fixture_graph(nodes, checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "offline-run07"}, "recursion_limit": recursion_limit(manifest)}
    initial = {"goal": GOAL, "run_id": "offline-run07", "domain_pack": pack, "manifest": manifest}
    updates = list(graph.stream(initial, config, stream_mode="updates"))
    visited = [name for update in updates for name in update if name != "__interrupt__"]
    snapshot = graph.get_state(config)
    return snapshot, visited, drafts, failures


def test_saved_run07_outputs_and_checkpoint_prove_original_routing_failure():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    original = next(b["payload"] for b in data["practice_batches"] if b["stage_key"] == "stage.model_api")
    assert data["repair_outputs"] == [original, original]
    assert data["final_errors"] == ["结构批次缺失"]
    after_first = next(s for s in data["checkpoint_tail"] if s["step"] == 35)
    assert after_first["repair_target"]["kind"] == "practice"
    assert after_first["errors"] == [ROLE_ERROR]
    assert after_first["next_channels"] == ["branch:to:validate_structure_batch"]


@pytest.mark.parametrize("persistent", [False, True])
def test_real_stategraph_revalidates_practice_and_matches_interpreter(persistent):
    pack = load_pack("agent-application-v1.json")
    fake = Run07Fake(pack, persistent=persistent)
    snapshot, visited, drafts, failures = _real_run(fake, pack)
    for index, name in enumerate(visited):
        if name == "repair_batch":
            assert visited[index + 1] == "validate_practice_batch"
    assert "结构批次缺失" not in snapshot.values["validation_errors"]
    if persistent:
        assert snapshot.next == ()
        assert failures == [[ROLE_ERROR]]
        assert snapshot.values["repair_count"] == 2
        assert fake.count(REPAIR) == 2
        assert fake.count() == 14
        assert fake.count(PRACTICE) == 2
        assert drafts == []
    else:
        assert snapshot.next == ()
        assert snapshot.values["validation_errors"] == []
        assert snapshot.values["draft_ref"] == "offline-draft"
        assert len(drafts) == 1 and failures == []
        assert fake.count(REPAIR) == 1
        assert fake.count() == 20
        assert fake.count(PRACTICE) == 9
        assert visited.count("merge_and_validate") == 1
    interpreter_fake = Run07Fake(pack, persistent=persistent)
    trace = run_batched_planning_graph(PlanningNodes(llm=interpreter_fake, save_draft=lambda state: "d"),
                                      {"goal": GOAL, "run_id": "offline-run07", "domain_pack": pack})
    assert trace.stopped_at == ("failed" if persistent else None)
    assert trace.state["validation_errors"] == snapshot.values["validation_errors"]
    assert [c["attempt_id"] for c in fake.calls] == [c["attempt_id"] for c in interpreter_fake.calls]


def test_structure_repair_still_returns_to_structure_validator():
    pack = load_pack("agent-application-v1.json")
    fake = ScriptedLLM(pack, invalid_at=(STRUCTURE, 1))
    snapshot, visited, drafts, failures = _real_run(fake, pack)
    index = visited.index("repair_batch")
    assert visited[index + 1] == "validate_structure_batch"
    assert snapshot.next == ()
    assert fake.count(REPAIR) == 1 and fake.count() == 20
    assert len(drafts) == 1 and failures == []


def test_normal_actual_stategraph_saves_draft_in_nineteen_requests():
    pack = load_pack("agent-application-v1.json")
    fake = ScriptedLLM(pack)
    snapshot, _, drafts, failures = _real_run(fake, pack)
    assert snapshot.next == ()
    assert fake.count() == 19 and fake.count(REPAIR) == 0
    assert len(drafts) == 1 and failures == []


def test_two_repairs_across_both_batch_kinds_share_the_same_cap():
    pack = load_pack("agent-application-v1.json")

    class MixedFake(ScriptedLLM):
        def _practice(self, payload):
            result = super()._practice(payload)
            if self.count(PRACTICE) == 1 and self.count(REPAIR) == 1:
                result["task_knowledge_links"][0]["role"] = "support"
            return result

    fake = MixedFake(pack, invalid_at=(STRUCTURE, 1))
    snapshot, visited, drafts, failures = _real_run(fake, pack)
    assert snapshot.next == ()
    assert fake.count() == 21 and fake.count(REPAIR) == 2
    assert snapshot.values["repair_count"] == 2
    assert snapshot.values["manifest"]["max_requests"] == 21
    assert [visited[i + 1] for i, name in enumerate(visited) if name == "repair_batch"] == [
        "validate_structure_batch", "validate_practice_batch",
    ]
    assert len(drafts) == 1 and failures == []
    assert len({c["attempt_id"] for c in fake.calls}) == len(fake.calls)


@pytest.mark.parametrize("target", [{}, {"kind": "unknown"}, {"kind": ""}])
def test_unknown_repair_target_fails_closed(target):
    assert route_after_batch_repair({"repair_target": target}) == "fail_batched"


def test_transport_unknown_during_practice_repair_preserves_dispatch_unknown_and_stops():
    pack = load_pack("agent-application-v1.json")
    fake = Run07Fake(pack, repair_failure="provider_transport_unknown")
    with pytest.raises(LLMDispatchUnknownError, match="provider_transport_unknown"):
        _real_run(fake, pack)
    assert fake.count(REPAIR) == 1 and fake.count() == 13


@pytest.mark.parametrize("error", ["provider_invalid_json", "provider_output_truncated"])
def test_practice_repair_provider_failure_fails_without_second_dispatch_or_wrong_validator(error):
    pack = load_pack("agent-application-v1.json")
    fake = Run07Fake(pack, repair_failure=error)
    snapshot, visited, drafts, failures = _real_run(fake, pack)
    assert visited[-2:] == ["repair_batch", "record_failure"]
    assert snapshot.next == ()
    assert snapshot.values["generation_errors"] == [f"修复失败：{error}"]
    assert fake.count(REPAIR) == 1 and fake.count() == 13
    assert drafts == [] and failures
