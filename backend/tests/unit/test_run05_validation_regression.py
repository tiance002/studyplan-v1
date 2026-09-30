"""Run 05 checkpoint business payloads, exercised without DB or provider I/O."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from app.agent_workflows.nodes import PlanningNodes
from app.agent_workflows.planning_batches import (
    DEFAULT_BUDGET,
    freeze_manifest,
    merge_batches,
    run_batched_planning_graph,
    validate_practice_batch,
    validate_structure_batch,
)
from app.agent_workflows.validators import validate_plan_structure, validate_route_structure
from app.infrastructure.domain_pack import load_pack

from tests.helpers.batched_planning import OUTLINE, PRACTICE, REPAIR, STRUCTURE, ScriptedLLM

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "b3f2_run05_validation.json"
GOAL = "从 Python 基础学习 Agent 应用开发"


def _data():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _pack_manifest():
    pack = load_pack("agent-application-v1.json")
    manifest = freeze_manifest(pack, DEFAULT_BUDGET, "mock:run05")
    assert manifest["pack_hash"] == _data()["source"]["pack_hash"]
    return pack, manifest


def _final_errors(data):
    pack, manifest = _pack_manifest()
    merged = merge_batches(data["outline"], data["structure_batches"], data["practice_batches"],
                           pack, manifest=manifest)
    proposal = merged["practice_proposal"]
    plan = validate_plan_structure(nodes=merged["nodes"], units=merged["units"],
                                   relations=merged["relations"], tasks=proposal["tasks"],
                                   task_knowledge_links=proposal["task_knowledge_links"])
    route = validate_route_structure({**merged, "domain_pack": pack})
    return merged["errors"], plan.errors, route


def _corrected(data):
    """Explicit offline repair answers; production code does not normalize data."""
    corrected = deepcopy(data)
    for batch in corrected["structure_batches"]:
        attached = {key for unit in batch["units"] for key in unit["node_keys"]}
        missing = {node["stable_key"] for node in batch["nodes"]} - attached
        batch["units"][0]["node_keys"].extend(sorted(missing))
    for batch in corrected["practice_batches"]:
        for link in batch["payload"]["task_knowledge_links"]:
            if link["role"] == "support":
                link["role"] = "supporting"
    return corrected


def test_persisted_run05_reproduces_exact_merge_plan_and_route_outcomes():
    data = _data()
    # Captured by executing the baseline validators against the checkpoint,
    # before this fix. No live Attempt replay or model call is involved.
    assert data["source"]["baseline_sha"] == "b8136781f78d4688d20543d042661c3fd94cf550"
    assert all(not errors for errors in data["baseline_structure_errors"].values())
    assert all(not errors for errors in data["baseline_practice_errors"].values())
    assert _final_errors(data) == (data["merge_errors"], data["plan_errors"], data["route_errors"])
    assert data["merge_errors"] == []
    assert len(data["plan_errors"]) == 12
    assert all("role 非法：'support'" in error for error in data["plan_errors"])
    assert data["route_errors"] == [
        "知识节点未关联到学习单元",
        "资源知识关联不属于当前阶段：stage.rag",
        "资源知识关联不属于当前阶段：stage.context",
    ]


def test_every_actual_error_is_found_in_its_own_batch():
    data = _data()
    pack, manifest = _pack_manifest()
    structures = {batch["stage_key"]: batch for batch in data["structure_batches"]}
    bad_structures = {}
    for batch, spec in zip(data["structure_batches"], manifest["structure_batches"], strict=True):
        errors = validate_structure_batch(batch, spec, pack)
        if errors:
            bad_structures[batch["stage_key"]] = errors
    assert bad_structures == {
        "stage.rag": ["结构批次知识节点未关联到学习单元：node.rag（stage.rag）"],
        "stage.context": ["结构批次知识节点未关联到学习单元：node.context（stage.context）"],
    }
    bad_practices = {}
    for batch in data["practice_batches"]:
        stage = batch["stage_key"]
        errors = validate_practice_batch(batch["payload"], stage, structures[stage])
        if errors:
            bad_practices[stage] = errors
    assert set(bad_practices) == {
        "stage.model_api", "stage.tools", "stage.rag", "stage.mcp", "stage.context",
        "stage.reliability", "stage.capstone",
    }
    assert sum(len(errors) for errors in bad_practices.values()) == 12
    for stage, errors in bad_practices.items():
        assert all("role 非法：'support'" in error and stage in error for error in errors)


def test_offline_corrected_historical_batches_pass_local_and_final_validation():
    data = _corrected(_data())
    pack, manifest = _pack_manifest()
    for batch, spec in zip(data["structure_batches"], manifest["structure_batches"], strict=True):
        assert validate_structure_batch(batch, spec, pack) == []
    for batch in data["practice_batches"]:
        structure = next(b for b in data["structure_batches"] if b["stage_key"] == batch["stage_key"])
        assert validate_practice_batch(batch["payload"], batch["stage_key"], structure) == []
    assert _final_errors(data) == ([], [], [])


@pytest.mark.parametrize("role,valid", [
    ("core", True), ("supporting", True), ("extension", True), ("omitted", True),
    ("support", False), ("SUPPORTING", False), (None, False), (True, False),
])
def test_local_link_role_contract_matches_final_enum_and_default(role, valid):
    data = _corrected(_data())
    batch = data["practice_batches"][0]
    link = batch["payload"]["task_knowledge_links"][0]
    if role == "omitted":
        link.pop("role")
    else:
        link["role"] = role
    local = validate_practice_batch(batch["payload"], batch["stage_key"], data["structure_batches"][0])
    _, final, route = _final_errors(data)
    assert (local == []) is valid
    assert (final == []) is valid
    assert route == []


class HistoricalFake(ScriptedLLM):
    """Use saved business objects as fixture responses, never the live ledger."""

    def __init__(self, pack, *, broken=(), persistent=False):
        super().__init__(pack)
        self.original = _data()
        self.corrected = _corrected(self.original)
        self.broken = set(broken)
        self.persistent = persistent

    def _answer(self, data, purpose, stage):
        collection = "structure_batches" if purpose == STRUCTURE else "practice_batches"
        batch = next(b for b in data[collection] if b["stage_key"] == stage)
        return deepcopy(batch if purpose == STRUCTURE else batch["payload"])

    def _skeleton(self, payload):
        return deepcopy(self.original["outline"])

    def _structure(self, payload):
        stage = payload["stage"]["stable_key"]
        data = self.original if (STRUCTURE, stage) in self.broken else self.corrected
        return self._answer(data, STRUCTURE, stage)

    def _practice(self, payload):
        stage = payload["stage"]["stable_key"]
        data = self.original if (PRACTICE, stage) in self.broken else self.corrected
        return self._answer(data, PRACTICE, stage)

    def _repair(self, payload):
        target = payload["target"]
        purpose = STRUCTURE if target["kind"] == "structure" else PRACTICE
        data = self.original if self.persistent else self.corrected
        return self._answer(data, purpose, target["stage_key"])


def _run(fake, pack):
    drafts = []

    def save(state):
        drafts.append(deepcopy(state))
        return {"draft_ref": "offline-draft", "draft_hash": "offline-hash"}

    nodes = PlanningNodes(llm=fake, save_draft=save)
    trace = run_batched_planning_graph(nodes, {"goal": GOAL, "run_id": "offline-run05", "domain_pack": pack})
    return trace, drafts


@pytest.mark.parametrize("broken", [
    (), ((STRUCTURE, "stage.rag"),), ((PRACTICE, "stage.model_api"),),
    ((STRUCTURE, "stage.rag"), (PRACTICE, "stage.model_api")),
])
def test_saved_stage_errors_take_local_repair_and_corrected_path_reaches_draft(broken):
    pack, _ = _pack_manifest()
    fake = HistoricalFake(pack, broken=broken)
    trace, drafts = _run(fake, pack)
    assert trace.stopped_at == "await_approval"
    assert trace.state["structure_errors"] == []
    assert len(drafts) == 1
    assert trace.state["draft_ref"] == "offline-draft"
    assert (fake.count(OUTLINE), fake.count(STRUCTURE), fake.count(PRACTICE)) == (1, 9, 9)
    assert fake.count(REPAIR) == len(broken)
    assert fake.count() == 19 + len(broken) <= 21
    repaired = set()
    for call in fake.calls:
        if call["purpose"] != REPAIR:
            continue
        local = call["payload"]
        target = local["target"]
        purpose = STRUCTURE if target["kind"] == "structure" else PRACTICE
        stage = target["stage_key"]
        repaired.add((purpose, stage))
        assert local["errors"]
        assert local["context"]["stage"]["stable_key"] == stage
        assert local["batch"] == fake._answer(fake.original, purpose, stage)
        # The call repairs the invalid batch before proceeding to later batches.
        index = fake.calls.index(call)
        assert fake.calls[index - 1]["purpose"] == purpose
        assert local["manifest"]["max_repairs"] == 2
    assert repaired == set(broken)
    assert len({c["attempt_id"] for c in fake.calls}) == len(fake.calls)


@pytest.mark.parametrize("purpose,stage", [(STRUCTURE, "stage.rag"), (PRACTICE, "stage.model_api")])
def test_persistent_saved_error_stops_after_exactly_two_local_repairs(purpose, stage):
    pack, _ = _pack_manifest()
    fake = HistoricalFake(pack, broken=((purpose, stage),), persistent=True)
    trace, drafts = _run(fake, pack)
    assert trace.stopped_at == "failed"
    assert trace.state["repair_count"] == fake.count(REPAIR) == 2
    assert trace.state["validation_errors"]
    assert drafts == []
    assert fake.count() <= 21
    assert fake.calls[-1]["purpose"] == REPAIR


def test_unchanged_run05_content_requires_more_than_cap_and_stops_without_full_retry():
    pack, _ = _pack_manifest()
    broken = {(STRUCTURE, b["stage_key"]) for b in _data()["structure_batches"]}
    broken |= {(PRACTICE, b["stage_key"]) for b in _data()["practice_batches"]}
    fake = HistoricalFake(pack, broken=broken)
    trace, drafts = _run(fake, pack)
    assert trace.stopped_at == "failed"
    assert fake.count(REPAIR) == 2
    assert fake.count(OUTLINE) == 1
    assert fake.count(PRACTICE) == 2
    assert fake.count() == 14
    assert any("role 非法：'support'" in error for error in trace.state["validation_errors"])
    assert drafts == []
