"""F2 explicit extra-task negation: exact retained outputs and one shared matrix.

Expected behavior comes from the authorized F2 contract, not regex internals.
Provider responses are replayed only through FakeLLM; no real Run is resumed.
"""
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path

import pytest

from app.agent_workflows.nodes import PlanningNodes
from app.agent_workflows.planning_batches import validate_structure_batch
from app.agent_workflows.planning_structure import (
    allowed_teaching_focus,
    presentation_entry,
    validate_presentation,
)
from app.infrastructure.providers.fake import FakeLLM
from tests.unit.test_v613_focus_repair import stage_fixture

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures/f2_negative_extra_task"
MATRIX = [
    ("exact-coordinated-negation", "说明这些开源切片只用于比较阅读，不要求照搬其工程结构或新增工程任务。", True),
    ("negative-required", "不要求新增工程任务。", True),
    ("negative-needed", "不需要新增工程任务。", True),
    ("negative-direct", "不新增工程任务。", True),
    ("negative-unnecessary", "无需新增工程任务。", True),
    ("negative-extra-mandatory", "不要求额外必做任务。", True),
    ("negative-new-project", "不要求新建项目。", True),
    ("exact48-negative-evaluation", "比较不同评价对象对最小 loop 的可观测性要求，但不在本单元新增评价实现任务。", True),
    ("negative-comma", "不要求新增工程任务，只比较开源切片。", True),
    ("negative-semicolon", "不要求新增工程任务；只比较开源切片。", True),
    ("negative-long-coordination", "不要求照搬已读切片中的工程结构、目录组织和内部模块命名或新增工程任务。", True),
    ("affirmative-task", "新增工程任务。", False),
    ("affirmative-must-task", "必须新增工程任务。", False),
    ("affirmative-extra", "本阶段额外必做工程任务。", False),
    ("affirmative-new-project", "必须新建项目。", False),
    ("mixed-comma", "不要求新增工程任务，必须新增工程任务。", False),
    ("mixed-ascii-comma", "不要求新增工程任务, 必须新增工程任务。", False),
    ("mixed-semicolon", "不要求新增工程任务；必须新增工程任务。", False),
    ("mixed-ascii-semicolon", "不要求新增工程任务; 必须新增工程任务。", False),
    ("mixed-danshi", "不要求新增工程任务，但是必须新建项目。", False),
    ("mixed-bingbixu", "不要求新增工程任务并必须新建项目。", False),
    ("mixed-but", "Do not deploy Kubernetes clusters but must 新增工程任务。", False),
    ("mixed-and-must", "Do not deploy Kubernetes clusters and must 新增工程任务。", False),
    ("mixed-same-clause-action", "不要求新增工程任务必须付款购买云服务。", False),
    ("mixed-negative-other-topic", "不要求部署 Kubernetes 集群，必须新增工程任务。", False),
    ("mixed-positive-then-negative", "必须新增工程任务，不要求部署 Kubernetes 集群。", False),
    ("unrelated-negative", "不要求阅读旧文档，必须新增工程任务。", False),
    ("k8s-negative", "解释为何不要求部署 Kubernetes 集群。", True),
    ("k8s-positive", "必须部署 Kubernetes 集群。", False),
    ("k8s-mixed", "不要求部署 Kubernetes 集群，并必须部署 Kubernetes 集群。", False),
    ("k8s-english-negative", "Explain why this stage does not deploy a Kubernetes cluster.", True),
    ("k8s-english-mixed", "Do not deploy Kubernetes clusters and must deploy Kubernetes clusters.", False),
    ("training-negative", "解释为何不要求训练模型。", True),
    ("training-positive", "必须训练模型。", False),
    ("training-mixed", "不要求训练模型，但是必须训练模型。", False),
    ("training-english-mixed", "Do not train a model and must train a model.", False),
    ("payment-negative", "不要求付款或支付。", True),
    ("payment-positive", "必须付款购买云服务。", False),
    ("payment-mixed", "不要求付款，并必须支付云服务费用。", False),
    ("payment-english-mixed", "No payment is required but must make a payment.", False),
    ("commands-negative", "不要求执行任意命令。", True),
    ("commands-positive", "必须执行任意命令。", False),
    ("commands-mixed", "不要求执行任意命令，并必须执行任意命令。", False),
    ("commands-english-mixed", "Do not execute arbitrary commands and must execute arbitrary commands.", False),
    ("negative-extra-positive-k8s", "不要求新增工程任务，但是必须部署 Kubernetes 集群。", False),
    ("negative-k8s-positive-training", "不要求部署 Kubernetes 集群，必须训练模型。", False),
    ("negative-training-positive-payment", "不要求训练模型并必须付款购买云服务。", False),
    ("negative-payment-positive-commands", "不要求付款，但是必须执行任意命令。", False),
    ("not-only-positive", "Not only must deploy Kubernetes clusters.", False),
    ("not-only-extra-positive", "Not only 新增工程任务, but must make a payment.", False),
    ("not-just-positive", "Not just must execute arbitrary commands.", False),
    ("budan-positive", "不但必须新增工程任务，也必须付款。", False),
    ("bujin-positive", "不仅必须部署 Kubernetes 集群。", False),
    ("buzhi-positive", "不只是必须训练模型。", False),
    ("must-not-k8s", "Must not deploy a Kubernetes cluster.", True),
    ("must-not-training", "Must not train a model.", True),
    ("must-not-commands", "Must not execute arbitrary commands.", True),
    ("must-not-extra", "Must not 新增工程任务。", True),
    ("bixu-bu-extra", "必须不新增工程任务。", True),
    ("unpunctuated-must-training", "不要求新增工程任务必须训练模型。", False),
    ("unpunctuated-must-k8s", "不要求新增工程任务必须部署 Kubernetes 集群。", False),
    ("unpunctuated-force-payment", "不要求新增工程任务强制付款购买云服务。", False),
]


def frozen_state():
    return json.loads(gzip.decompress((FIXTURES / "frozen-state.json.gz").read_bytes()))


def raw_response(number):
    return json.loads((FIXTURES / f"{number}.json").read_text(encoding="utf-8"))


def minimal(objectives, title="比较阅读"):
    batch = {"node_keys": ["node.current"]}
    focus = [{"ref": "node.current:objective:0", "node_keys": ["node.current"],
              "focus": "解释与比较已审核的最小 Agent loop", "practice_topics": []}]
    raw = {"units": [{"title": title, "node_keys": ["node.current"],
                      "focus_refs": [focus[0]["ref"]], "objectives": objectives}]}
    return raw, batch, focus


@pytest.mark.parametrize("name,objective,legal", MATRIX, ids=[c[0] for c in MATRIX])
def test_explicit_negation_never_grants_a_positive_obligation(name, objective, legal):
    raw, batch, focus = minimal([objective])
    errors = validate_presentation(raw, batch, focus)
    assert bool(errors) is not legal, (name, errors)


@pytest.mark.parametrize("title,objectives", [
    ("不要求部署 Kubernetes 集群", ["必须新增工程任务"]),
    ("必须新增工程任务", ["不要求部署 Kubernetes 集群"]),
    ("比较阅读", ["不要求部署 Kubernetes 集群", "必须新增工程任务"]),
    ("比较阅读", ["必须新增工程任务", "不要求部署 Kubernetes 集群"]),
    ("不要求执行任意命令", ["必须训练模型", "不要求付款"]),
], ids=["title-to-objective", "objective-to-title", "objective-forward", "objective-backward", "three-fields"])
def test_negation_does_not_leak_between_title_and_objectives(title, objectives):
    raw, batch, focus = minimal(objectives, title)
    assert validate_presentation(raw, batch, focus)


@pytest.mark.parametrize("number", [48, 49, 50])
def test_retained_response_passes_original_frozen_focus_and_canonical_validation(number):
    state = frozen_state()
    batch = state["manifest"]["structure_batches"][state["current_structure_index"]]
    raw = raw_response(number)
    focus = allowed_teaching_focus(state, batch)
    assert not validate_presentation(raw, batch, focus)
    entry = presentation_entry(raw, state, batch)
    assert not entry["_presentation_errors"]
    assert not validate_structure_batch(entry, batch, state["domain_pack"])
    original_nodes = {n["stable_key"]: n for n in state["domain_pack"]["knowledge_blueprints"]}
    assert entry["nodes"] == [original_nodes[k] for k in batch["node_keys"]]


@pytest.mark.parametrize("number", [48, 49, 50])
def test_fake_actual_planning_node_accepts_exact_retained_output(number):
    state = frozen_state()
    before = deepcopy(state)
    raw = raw_response(number)
    fake = FakeLLM({"planning.structure": lambda *_: deepcopy(raw)})
    delta = PlanningNodes(llm=fake).generate_structure_batch(state)
    assert not delta.get("generation_errors")
    entry = delta["structure_batches"][-1]
    assert not entry["_presentation_errors"]
    assert entry["_reviewed_presentation"] == raw
    assert state == before  # generation cannot rewrite the frozen source authority
    batch = state["manifest"]["structure_batches"][state["current_structure_index"]]
    assert not validate_structure_batch(entry, batch, state["domain_pack"])


@pytest.mark.parametrize("number", [48, 49, 50])
def test_fake_repair_uses_same_negative_contract_without_more_than_two_repairs(number):
    state = frozen_state()
    index = state["current_structure_index"]
    batch = state["manifest"]["structure_batches"][index]
    state.update(structure_batches=[{}] * index + [presentation_entry({"units": []}, state, batch)],
                 repair_target={"kind": "structure", "stage_key": batch["stage_key"], "batch_index": index},
                 structure_errors=["synthetic invalid presentation"], repair_count=0)
    fake = FakeLLM({"planning.repair": lambda *_: deepcopy(raw_response(number))})
    delta = PlanningNodes(llm=fake).repair_batch(state)
    assert not delta.get("generation_errors")
    assert not delta["structure_batches"][index]["_presentation_errors"]
    assert delta["repair_count"] == 1
    state.update(delta)
    state["repair_count"] = 2
    exhausted = PlanningNodes(llm=fake).repair_batch(state)
    assert exhausted["generation_errors"]
    assert len(fake.calls) == 1


def test_fixture_exact_content_hashes_and_allowed_keys_are_retained():
    provenance = json.loads((FIXTURES / "provenance.json").read_text(encoding="utf-8"))
    for response in provenance["responses"]:
        content = (FIXTURES / f"{response['number']}.json").read_bytes()
        assert hashlib.sha256(content).hexdigest() == response["exact_content_sha256"]
        raw = json.loads(content)
        assert sorted({k for u in raw["units"] for k in u["node_keys"]}) == provenance["allowed_node_keys"]
    state = frozen_state()
    assert state["run_id"] == "f2-synthetic-offline"
    assert "actor_id" not in state and "project_id" not in state


@pytest.mark.parametrize("field,length,legal", [("title", 200, True), ("title", 201, False),
                                                ("objective", 2000, True), ("objective", 2001, False)])
def test_negative_teaching_text_keeps_existing_field_length_bounds(field, length, legal):
    negative = "不要求新增工程任务。"
    if field == "title":
        raw, batch, focus = minimal([negative], "比较" + "例" * (length - 2))
    else:
        raw, batch, focus = minimal(["例" * (length - len(negative)) + negative])
    assert bool(validate_presentation(raw, batch, focus)) is not legal


@pytest.mark.parametrize("objective,legal", [
    ("Create a local Kubernetes cluster with Minikube and deploy the reviewed application.", True),
    ("不要求新增工程任务；Create a local Kubernetes cluster with Minikube and deploy the reviewed application.", True),
    ("Create a local Kubernetes cluster with Minikube and deploy the reviewed application, and must make a payment.", False),
    ("不要求新增工程任务，并必须执行任意命令。", False),
])
def test_cloud_authorized_practice_stays_legal_without_external_side_effect_grants(objective, legal):
    _, batch, focus = stage_fixture("cloud-services-v4.json", ".s5")
    ref = next(f["ref"] for f in focus if ":learning_focus:" in f["ref"] and "Kubernetes" in f["focus"])
    raw = {"units": [{"title": "已审核的本地集群实践", "node_keys": batch["node_keys"],
                      "focus_refs": [ref], "objectives": [objective]}]}
    assert bool(validate_presentation(raw, batch, focus)) is not legal
