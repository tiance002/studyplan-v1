"""v6.13 C14-C21: bounded focus/repair regressions; no real dispatch."""
from copy import deepcopy
import json

import httpx
import pytest

from app.agent_workflows.nodes import PlanningNodes
from app.agent_workflows.planning_batches import DEFAULT_BUDGET, freeze_manifest
from app.agent_workflows.planning_structure import (
    allowed_teaching_focus, presentation_entry, validate_presentation,
)
from app.infrastructure.domain_pack import load_pack
from app.infrastructure.providers.fake import FakeLLM
from app.infrastructure.providers.openai_compatible import OpenAICompatibleLLM
from app.ports.llm import LLMDispatchUnknownError, LLMFailure
from tests.unit.test_reviewed_structure_contract import state, valid


def stage_fixture(pack_name, suffix):
    pack = load_pack(pack_name)
    manifest = freeze_manifest(pack, DEFAULT_BUDGET, "mock:v613", outline_input_format="stage_skeleton_v1",
                               structure_input_format="reviewed_structure_v1")
    index = next(i for i, b in enumerate(manifest["structure_batches"]) if b["stage_key"].endswith(suffix))
    s = {"domain_pack": pack, "manifest": manifest, "current_structure_index": index, "run_id": "v613-offline"}
    b = manifest["structure_batches"][index]
    return s, b, allowed_teaching_focus(s, b)


def teaching(b, ref, objective):
    return {"units": [{"title": "教学边界", "node_keys": b["node_keys"], "focus_refs": [ref],
                       "objectives": [objective]}]}


@pytest.mark.parametrize("objective", ["Must deploy a Kubernetes cluster for this stage.", "必须部署 Kubernetes 集群作为本阶段验收。"])
def test_c14_w6_original_negation_does_not_grant_implementation(objective):
    s, b, focus = stage_fixture("agent-application-v7.json", ".w6")
    assert any("Kubernetes" in f["focus"] for f in focus)  # original frozen negative wording
    raw = teaching(b, focus[0]["ref"], objective)
    assert validate_presentation(raw, b, focus)
    entry = presentation_entry(raw, s, b)
    assert entry["nodes"] == entry["units"] == entry["relations"] == []
    fake = FakeLLM({"planning.structure": lambda *_: raw})
    delta = PlanningNodes(llm=fake).generate_structure_batch(s)
    assert len(fake.calls) == 1
    assert delta["structure_batches"][-1]["_presentation_errors"]


@pytest.mark.parametrize("objective", ["解释为何本阶段不部署 Kubernetes 集群。", "Explain why this stage does not deploy a Kubernetes cluster."])
def test_c15_w6_negative_explanation_is_legal(objective):
    _, b, focus = stage_fixture("agent-application-v7.json", ".w6")
    assert not validate_presentation(teaching(b, focus[0]["ref"], objective), b, focus)


@pytest.mark.parametrize("objective, legal", [
    ("Compare Kubernetes and a local service without deploying a cluster.", True),
    ("比较 Kubernetes 与本地服务，不要求部署集群。", True),
    ("Must deploy a Kubernetes cluster.", False),
    ("必须部署 Kubernetes 集群。", False),
])
def test_c15_comparison_ref_never_grants_practice(objective, legal):
    b = {"node_keys": ["node.current"]}
    focus = [{"ref": "stage.current:comparison_focus:0", "node_keys": b["node_keys"],
              "focus": "Compare Kubernetes with local service deployment; comparison only, no cluster deployment."}]
    assert bool(validate_presentation(teaching(b, focus[0]["ref"], objective), b, focus)) is not legal


def test_c15_unselected_ref_cannot_authorize_same_word():
    b = {"node_keys": ["node.current"]}
    focus = [{"ref": "node.current:objective:0", "node_keys": b["node_keys"], "focus": "解释本地服务的生命周期"},
             {"ref": "node.current:objective:1", "node_keys": b["node_keys"], "focus": "Deploy a Kubernetes cluster"}]
    assert validate_presentation(teaching(b, focus[0]["ref"], "Must deploy a Kubernetes cluster."), b, focus)


def test_c16_cloud_reviewed_cluster_practice_remains_legal():
    s, b, focus = stage_fixture("cloud-services-v4.json", ".s5")
    ref = next(f["ref"] for f in focus if ":learning_focus:" in f["ref"] and "Kubernetes" in f["focus"])
    raw = teaching(b, ref, "Create a local Kubernetes cluster with Minikube and deploy the reviewed application.")
    assert not validate_presentation(raw, b, focus)
    fake = FakeLLM({"planning.structure": lambda *_: raw})
    delta = PlanningNodes(llm=fake).generate_structure_batch(s)
    assert len(fake.calls) == 1
    assert not delta["structure_batches"][-1]["_presentation_errors"]


@pytest.mark.parametrize("objective", ["必须付款购买云服务作为验收。", "Must make a payment to purchase cloud infrastructure."])
def test_c17_payment_mention_in_negative_scope_is_not_authorization(objective):
    b = {"node_keys": ["node.current"]}
    focus = [{"ref": "node.current:scope:0", "node_keys": b["node_keys"], "focus": "不需要付款；no payment required"}]
    assert validate_presentation(teaching(b, focus[0]["ref"], objective), b, focus)


def repair_fixture(raw=None):
    s = state()
    b = s["manifest"]["structure_batches"][s["current_structure_index"]]
    raw = deepcopy(raw if raw is not None else valid(s))
    entry = presentation_entry(raw, s, b)
    index = s["current_structure_index"]
    s.update(structure_batches=[{}] * index + [entry], repair_target={"kind": "structure", "stage_key": b["stage_key"],
             "batch_index": index}, structure_errors=entry["_presentation_errors"], repair_count=0)
    return s, raw


def adapter_repair(s, output=None):
    seen = []
    def respond(request):
        seen.append(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {
            "content": json.dumps(output if output is not None else valid(s), ensure_ascii=False)}}]})
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        llm = OpenAICompatibleLLM(base_url="https://api.deepseek.com/v1", api_key="synthetic", model="deepseek-flash", client=client)
        delta = PlanningNodes(llm=llm).repair_batch(s)
    return delta, seen


def test_c18_original_11058_failed_object_reaches_mock_transport_complete():
    raw = valid(state())
    raw["units"][0]["objectives"] = ["explain" + "x" * 1800 for _ in range(6)]
    raw["units"][0]["acceptance"] = ["unauthorized"]
    assert len(json.dumps(raw, ensure_ascii=False)) == 11058
    s, original = repair_fixture(raw)
    assert len(s["structure_errors"]) == 1
    delta, seen = adapter_repair(s)
    assert len(seen) == 1
    wire = json.loads(seen[0]["messages"][1]["content"])["context"]
    assert wire["batch"] == original
    assert wire["errors"] == s["structure_errors"]
    assert delta["repair_count"] == 1 and not delta.get("generation_errors")


def test_c19_escaped_unicode_evidence_is_complete_and_bytes_differ():
    raw = valid(state())
    raw["units"][0]["objectives"] = [('解释\\"\n' * 300) for _ in range(6)]
    raw["units"][0]["acceptance"] = ["unauthorized"]
    encoded = json.dumps(raw, ensure_ascii=False)
    assert len(encoded.encode("utf-8")) > len(encoded)
    s, original = repair_fixture(raw)
    delta, seen = adapter_repair(s)
    assert len(seen) == 1
    wire = json.loads(seen[0]["messages"][1]["content"])["context"]
    assert wire["batch"] == original and wire["errors"] == s["structure_errors"]
    assert delta["repair_count"] == 1


def test_c20_oversized_object_preflight_http0_does_not_consume_actual_repair():
    raw = valid(state())
    raw["units"][0]["objectives"] = ["x" * 2_000_000]
    s, _ = repair_fixture(raw)
    delta, seen = adapter_repair(s)
    assert not seen and delta["generation_errors"]
    assert delta.get("repair_count", s["repair_count"]) == 0


def test_c21_partial_actual_repairs_stop_at_two_and_preserve_evidence():
    s, original = repair_fixture({"units": []})
    fake = FakeLLM({"planning.repair": lambda *_: {"patch": {"units": []}}})
    nodes = PlanningNodes(llm=fake)
    for _ in range(2):
        s.update(nodes.repair_batch(s))
        assert s["structure_batches"][s["current_structure_index"]]["_presentation_errors"]
    assert s["repair_count"] == len(fake.calls) == 2
    delta = nodes.repair_batch(s)
    assert delta["generation_errors"] and len(fake.calls) == 2
    assert original == {"units": []}


def test_c21_unknown_dispatch_stops_without_repair_replay():
    s, _ = repair_fixture({"units": []})
    class Unknown:
        calls = 0
        def generate_structured(self, **kwargs):
            self.calls += 1
            return LLMFailure("transport_unknown", "offline synthetic unknown", dispatch_unknown=True)
    llm = Unknown()
    with pytest.raises(LLMDispatchUnknownError):
        PlanningNodes(llm=llm).repair_batch(s)
    assert llm.calls == 1 and s["repair_count"] == 0


def test_c19_distinct_ceiling_helpers_cover_serialized_field_bounds():
    from app.agent_workflows.planning_batches import structure_payload
    from app.agent_workflows.planning_structure import (
        presentation_message_ceiling, presentation_output_ceiling, presentation_repair_message_ceiling,
    )
    s = state()
    b = s["manifest"]["structure_batches"][s["current_structure_index"]]
    context = structure_payload(s, b)
    output = presentation_output_ceiling(context)
    # Aggregate output bounds remain part of validity: individual field maxima
    # do not authorize a simultaneous megabyte-scale combination.
    candidates = []
    for repetitions in range(1, 401):
        candidate = valid(s)
        candidate["units"][0]["title"] = "界" * 200
        candidate["units"][0]["objectives"] = [('解释\\"\n' * repetitions) for _ in range(20)]
        encoded = json.dumps(candidate, ensure_ascii=False)
        if len(encoded) <= output["chars"] and len(encoded.encode("utf-8")) <= output["utf8_bytes"]:
            candidates.append((candidate, encoded))
    assert candidates
    raw, serialized = candidates[-1]
    assert not validate_presentation(raw, b, allowed_teaching_focus(s, b))
    assert not presentation_entry(raw, s, b)["_presentation_errors"]
    repair = presentation_repair_message_ceiling(context, failed_object=raw, errors=["extra field"])
    for metrics in (output, repair):
        assert set(metrics) >= {"chars", "utf8_bytes"}
        assert type(metrics["chars"]) is int and type(metrics["utf8_bytes"]) is int
    assert len(serialized) <= output["chars"]
    assert len(serialized.encode("utf-8")) <= output["utf8_bytes"]
    assert repair["chars"] > presentation_message_ceiling(context)
    assert repair["chars"] >= len(serialized)
    assert repair["utf8_bytes"] >= len(serialized.encode("utf-8"))
    oversized = deepcopy(raw)
    oversized["units"][0]["objectives"] = ["解释" * output["chars"]]
    assert presentation_entry(oversized, s, b)["_presentation_errors"]


def test_c20_preflight_rejection_never_opens_attempt_ledger(monkeypatch):
    from app.infrastructure.providers.attempt_ledger import PgAttemptLLM
    raw = valid(state())
    raw["units"][0]["objectives"] = ["x" * 2_000_000]
    s, _ = repair_fixture(raw)
    http_requests, db_connections = [], []
    def respond(request):
        http_requests.append(request)
        raise AssertionError("local preflight must prevent HTTP")
    def connect(project_id):
        db_connections.append(project_id)
        raise AssertionError("local preflight must prevent ledger reservation/writes")
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        provider = OpenAICompatibleLLM(base_url="https://api.deepseek.com/v1", api_key="synthetic",
                                       model="deepseek-flash", client=client)
        ledger = PgAttemptLLM("postgresql://synthetic:synthetic@127.0.0.1:1/unused", provider,
                              manifest=s["manifest"])
        monkeypatch.setattr(ledger, "_connect", connect)
        delta = PlanningNodes(llm=ledger).repair_batch(s)
    assert delta["generation_errors"] and delta.get("repair_count", 0) == 0
    assert http_requests == db_connections == []


@pytest.mark.parametrize("negative", [
    "Do not deploy Kubernetes clusters; explain why cluster deployment is excluded.",
    "不要求部署 Kubernetes 集群；只解释为何此阶段不部署集群。",
    "Compare Kubernetes with local services; comparison only, no cluster deployment.",
    "仅比较 Kubernetes 与本地服务，不要求部署集群。",
])
def test_c16_cloud_s5_selected_negative_ref_cannot_grant_practice(negative):
    pack = load_pack("cloud-services-v4.json")
    stage = next(s for s in pack["stage_blueprints"] if s["stage_code"] == "S5")
    stage["learning_guidance"]["learning_focus"] = [negative]
    manifest = freeze_manifest(pack, DEFAULT_BUDGET, "mock:v613-negative-cloud",
                               outline_input_format="stage_skeleton_v1", structure_input_format="reviewed_structure_v1")
    s = {"domain_pack": pack, "manifest": manifest}
    b = next(b for b in manifest["structure_batches"] if b["stage_key"] == stage["stable_key"])
    focus = allowed_teaching_focus(s, b)
    selected = next(f for f in focus if ":learning_focus:0" in f["ref"])
    assert validate_presentation(teaching(b, selected["ref"], "Must deploy a Kubernetes cluster."), b, focus)


def test_c16_cloud_s5_selected_comparison_ref_cannot_grant_practice():
    _, b, focus = stage_fixture("cloud-services-v4.json", ".s5")
    selected = next(f for f in focus if ":comparison_focus:" in f["ref"])
    assert validate_presentation(teaching(b, selected["ref"], "Must deploy a Kubernetes cluster."), b, focus)


def test_c20_oversized_fake_repair_is_rejected_before_dispatch():
    raw = valid(state())
    raw["units"][0]["objectives"] = ["x" * 2_000_000]
    s, _ = repair_fixture(raw)
    fake = FakeLLM({"planning.repair": lambda *_: valid(s)})
    delta = PlanningNodes(llm=fake).repair_batch(s)
    assert delta["generation_errors"] and delta.get("repair_count", 0) == 0
    assert not fake.calls


def aggregate_boundary_objects(context, escaped):
    """Same valid field shape either side of the independently bounded object."""
    from app.agent_workflows.planning_structure import presentation_output_ceiling
    limit = presentation_output_ceiling(context)
    seed = valid(state())
    pattern = '解释\\"\n' if escaped else 'x'
    below = None
    # Keep each individual objective <=2000 chars and all twenty fields valid.
    for repetitions in range(1, 2000 // len(pattern) + 1):
        candidate = deepcopy(seed)
        candidate["units"][0]["objectives"] = [pattern * repetitions] * 20
        encoded = json.dumps(candidate, ensure_ascii=False)
        if len(encoded) <= limit["chars"] and len(encoded.encode("utf-8")) <= limit["utf8_bytes"]:
            below = candidate
        else:
            assert below is not None
            return below, candidate
    raise AssertionError("fixture must straddle the stage aggregate bound")


@pytest.mark.parametrize("escaped", [False, True], ids=["ascii", "escaped_unicode"])
def test_c19_aggregate_boundary_complete_repair_and_zero_ledger_reservation(monkeypatch, escaped):
    from app.agent_workflows.planning_batches import structure_payload
    from app.infrastructure.providers.attempt_ledger import PgAttemptLLM
    s = state()
    b = s["manifest"]["structure_batches"][s["current_structure_index"]]
    below, above = aggregate_boundary_objects(structure_payload(s, b), escaped)
    assert not presentation_entry(below, s, b)["_presentation_errors"]
    assert "局部规模上界" in " ".join(presentation_entry(above, s, b)["_presentation_errors"])
    local, _ = repair_fixture(below)
    local["structure_errors"] = ["synthetic bounded validator error"]
    delta, seen = adapter_repair(local)
    assert len(seen) == 1 and delta["repair_count"] == 1
    wire = json.loads(seen[0]["messages"][1]["content"])["context"]
    assert wire["batch"] == below and wire["errors"] == local["structure_errors"]
    oversized_state, _ = repair_fixture(above)
    connections, requests = [], []
    def respond(request):
        requests.append(request)
        raise AssertionError("aggregate overflow must not dispatch")
    def connect(project_id):
        connections.append(project_id)
        raise AssertionError("aggregate overflow must not reserve ledger attempt")
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        provider = OpenAICompatibleLLM(base_url="https://api.deepseek.com/v1", api_key="synthetic", model="deepseek-flash", client=client)
        ledger = PgAttemptLLM("postgresql://synthetic:synthetic@127.0.0.1:1/unused", provider, manifest=oversized_state["manifest"])
        monkeypatch.setattr(ledger, "_connect", connect)
        rejected = PlanningNodes(llm=ledger).repair_batch(oversized_state)
    assert rejected["generation_errors"] and rejected.get("repair_count", 0) == 0
    assert connections == requests == []


def test_c20_direct_attempt_wrapper_preflights_before_ledger_connection(monkeypatch):
    from app.agent_workflows.planning_batches import structure_payload
    from app.agent_workflows.planning_structure import FOCUS_FORMAT, REVIEWED_STRUCTURE_V1, STRUCTURE_SCHEMA
    from app.infrastructure.providers.attempt_ledger import PgAttemptLLM
    s = state()
    b = s["manifest"]["structure_batches"][s["current_structure_index"]]
    failed = valid(s)
    failed["units"][0]["objectives"] = ["x" * 2_000_000]
    payload = {"_structure_input_format": REVIEWED_STRUCTURE_V1, "_structure_focus_format": FOCUS_FORMAT,
               "context": structure_payload(s, b), "batch": failed, "errors": ["oversized"],
               "target": {"kind": "structure", "stage_key": b["stage_key"]}}
    connections, requests = [], []
    def connect(project_id):
        connections.append(project_id)
        raise AssertionError("direct wrapper local rejection must not reserve ledger")
    def respond(request):
        requests.append(request)
        raise AssertionError("direct wrapper local rejection must not dispatch")
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        provider = OpenAICompatibleLLM(base_url="https://api.deepseek.com/v1", api_key="synthetic", model="deepseek-flash", client=client)
        ledger = PgAttemptLLM("postgresql://synthetic:synthetic@127.0.0.1:1/unused", provider, manifest=s["manifest"])
        monkeypatch.setattr(ledger, "_connect", connect)
        failure = ledger.generate_structured(purpose="planning.repair", payload=payload,
                    schema_name=STRUCTURE_SCHEMA, run_id=s["run_id"], attempt_id="unused-local-only")
    assert isinstance(failure, LLMFailure) and failure.details["dispatched"] is False
    assert connections == requests == []


@pytest.mark.parametrize("constraint", [
    "Do not deploy Kubernetes clusters; local services only.",
    "不部署 Kubernetes 集群，只使用本地服务。",
])
def test_c16_explicit_goal_constraint_overrides_positive_cloud_focus(constraint):
    from app.domain.planning.intent import GoalSpec
    pack = load_pack("cloud-services-v4.json")
    manifest = freeze_manifest(pack, DEFAULT_BUDGET, "mock:v613-constraint",
                               goal_spec=GoalSpec(target="学习云服务部署", constraints=(constraint,)),
                               outline_input_format="stage_skeleton_v1", structure_input_format="reviewed_structure_v1")
    s = {"domain_pack": pack, "manifest": manifest}
    b = next(b for b in manifest["structure_batches"] if b["stage_key"].endswith(".s5"))
    focus = allowed_teaching_focus(s, b)
    ref = next(f["ref"] for f in focus if ":learning_focus:" in f["ref"] and "Kubernetes" in f["focus"])
    assert validate_presentation(teaching(b, ref, "Must deploy a Kubernetes cluster."), b, focus)
    assert not validate_presentation(teaching(b, ref, "Explain why this route does not deploy Kubernetes clusters."), b, focus)


@pytest.mark.parametrize("constraints", [
    ("No model training.", "Use local Kubernetes practice."),
    ("不训练模型。", "使用本地 Kubernetes 实践。"),
])
def test_c16_unrelated_negative_constraint_preserves_reviewed_cloud_practice(constraints):
    from app.domain.planning.intent import GoalSpec
    pack = load_pack("cloud-services-v4.json")
    manifest = freeze_manifest(pack, DEFAULT_BUDGET, "mock:v613-unrelated-constraint",
                               goal_spec=GoalSpec(target="学习云服务部署", constraints=constraints),
                               outline_input_format="stage_skeleton_v1", structure_input_format="reviewed_structure_v1")
    s = {"domain_pack": pack, "manifest": manifest}
    b = next(b for b in manifest["structure_batches"] if b["stage_key"].endswith(".s5"))
    focus = allowed_teaching_focus(s, b)
    ref = next(f["ref"] for f in focus if ":learning_focus:" in f["ref"] and "Kubernetes" in f["focus"])
    assert not validate_presentation(teaching(b, ref, "Create a local Kubernetes cluster with Minikube and deploy the reviewed application."), b, focus)
