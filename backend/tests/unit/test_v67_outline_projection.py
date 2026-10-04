"""Frozen new outline contracts, plus a pre-patch legacy wire golden."""
import hashlib
import json
from copy import deepcopy
from pathlib import Path

import httpx
import pytest
from app.agent_workflows.nodes import PlanningNodes
from app.agent_workflows.planning_batches import DEFAULT_BUDGET, freeze_manifest, manifest_is_intact
from app.domain.planning.semantic_content import adapt_semantic_pack
from app.infrastructure.domain_pack import load_pack
from app.infrastructure.providers.fake import FakeLLM
from app.infrastructure.providers.openai_compatible import OpenAICompatibleLLM

GOAL = "零基础系统学习 Agent 应用开发，先做一个最小应用。"
FORMAT = "stage_skeleton_v1"
GOLDEN = Path(__file__).parents[1] / "fixtures/v67_legacy_outline.json"


def initial():
    pack = adapt_semantic_pack(load_pack("agent-application-v5.json"), GOAL, None)
    return {"goal": GOAL, "prefs_snapshot": {"mode": "mixed", "pace": "normal", "language": "zh", "official_priority": True},
            "domain_pack": pack, "manifest": freeze_manifest(pack, DEFAULT_BUDGET, "mock:offline"), "run_id": "v67-fixture"}


def captured(state):
    captured_body = {}
    captured_payload = {}

    def respond(request):
        captured_body.update(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": json.dumps({"outline_ref": "fixture", "sections": [
            {"stable_key": s["stage_key"], "title": s["title"], "objective": s["objective"]} for s in state["manifest"]["stages"]]})}}]})

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        provider = OpenAICompatibleLLM(base_url="https://api.deepseek.com/v1", api_key="synthetic", model="deepseek-flash", client=client)

        class Capture:
            def generate_structured(self, **kwargs):
                captured_payload.update(deepcopy(kwargs["payload"]))
                return provider.generate_structured(**kwargs)

        delta = PlanningNodes(llm=Capture(), save_draft=lambda _: "unused").generate_skeleton(state)
        assert not delta.get("generation_errors"), delta
        identity = ["planning.outline", captured_payload, "OutlineV1", provider.model, provider.prompt_version, provider.domain_pack,
                    provider.request_options("planning.outline"), provider.budget_policy.as_dict(), provider.base_url, provider.configuration_ref]
        fingerprint = hashlib.sha256(json.dumps(identity, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        return captured_body, captured_payload, fingerprint


def wire_summary(state):
    body, payload, fingerprint = captured(state)
    messages = body["messages"]
    return {"messages_sha256": hashlib.sha256(json.dumps(messages, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
            "payload_sha256": hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
            "fingerprint": fingerprint, "messages_chars": sum(len(m["content"]) for m in messages),
            "http_bytes": len(httpx.Request("POST", "https://example.com", json=body).content)}


def test_legacy_wire_hash_fingerprint_golden():
    state = initial()
    assert "outline_input_format" not in state["manifest"]
    assert wire_summary(state) == json.loads(GOLDEN.read_text(encoding="utf-8"))


def new_state():
    state = initial()
    state["manifest"] = freeze_manifest(state["domain_pack"], DEFAULT_BUDGET, "mock:offline", outline_input_format=FORMAT)
    return state


def test_new_marker_is_hash_bound_and_default_remains_legacy():
    old = initial()["manifest"]
    new = new_state()["manifest"]
    assert new["outline_input_format"] == FORMAT
    assert new["manifest_hash"] != old["manifest_hash"]
    assert manifest_is_intact(new)
    new.pop("outline_input_format")
    assert not manifest_is_intact(new)


def test_new_outline_no_full_pack_or_reviewed_fields_and_size_guard():
    body, payload, _ = captured(new_state())
    context = json.loads(body["messages"][1]["content"])
    assert "domain_pack" not in context and "manifest" not in context["context"]
    assert payload["_outline_input_format"] == FORMAT
    assert "_outline_input_format" not in context["context"]
    assert len(context["context"]["frozen_stages"]) == 6
    wire = json.dumps(context, ensure_ascii=False)
    for forbidden in ("publication_evidence", "review_evidence", "source_ref", "section_refs", "learning_guidance", "extensions", "practice_blueprints", "resources", "https://"):
        assert forbidden not in wire
    # v6.6 Option1 measured 4112 chars. 6500 permits template wording and
    # bounded goal/prefs projection variation while detecting catalog leakage.
    assert sum(len(m["content"]) for m in body["messages"]) <= 6500
    assert len(httpx.Request("POST", "https://example.com", json=body).content) <= 14000
    assert set(context["field_shape"]["sections"][0]) == {"stable_key", "title", "objective"}
    assert body["max_tokens"] == 4096


@pytest.mark.parametrize("mutation", ["drop", "add", "reorder", "empty_title", "empty_objective", "authority"])
def test_new_skeleton_rejects_keys_order_empty_or_authority(mutation):
    state = new_state()
    sections = [{"stable_key": s["stage_key"], "title": s["title"], "objective": s["objective"]} for s in state["manifest"]["stages"]]
    if mutation == "drop":
        sections.pop()
    elif mutation == "add":
        sections.append({"stable_key": "forged", "title": "x", "objective": "y"})
    elif mutation == "reorder":
        sections.reverse()
    elif mutation.startswith("empty_"):
        sections[0][mutation.removeprefix("empty_")] = " "
    else:
        sections[0]["resources"] = []
    fake = FakeLLM({"planning.outline": lambda *_: {"sections": sections}})
    assert PlanningNodes(llm=fake, save_draft=lambda _: "unused").generate_skeleton(state)["generation_errors"]


def test_unknown_or_tampered_marker_never_dispatches():
    state = new_state()
    state["manifest"]["outline_input_format"] = "unknown"
    fake = FakeLLM({"planning.outline": lambda *_: {}})
    assert PlanningNodes(llm=fake, save_draft=lambda _: "unused").generate_skeleton(state)["generation_errors"]
    assert fake.calls == []


@pytest.mark.parametrize("mutation", ["delete", "null"])
def test_removing_new_marker_cannot_dispatch_legacy_payload(mutation):
    state = new_state()
    if mutation == "delete":
        del state["manifest"]["outline_input_format"]
    else:
        state["manifest"]["outline_input_format"] = None
    fake = FakeLLM({"planning.outline": lambda *_: {}})
    assert not manifest_is_intact(state["manifest"])
    assert PlanningNodes(llm=fake, save_draft=lambda _: "unused").generate_skeleton(state)["generation_errors"]
    assert fake.calls == []


def test_new_frozen_pack_cannot_be_changed_before_outline_dispatch():
    state = new_state()
    state["domain_pack"]["knowledge_blueprints"][0]["title"] = "forged"
    fake = FakeLLM({"planning.outline": lambda *_: {}})
    assert PlanningNodes(llm=fake, save_draft=lambda _: "unused").generate_skeleton(state)["generation_errors"]
    assert fake.calls == []


def test_marker_removal_cannot_choose_legacy_merge():
    from app.agent_workflows.planning_batches import merge_batches

    from tests.unit.test_v67_content_protection import generated
    pack, manifest, outline, structures, practices = generated()
    del manifest["outline_input_format"]
    result = merge_batches(outline, structures, practices, pack, manifest=manifest)
    assert result["errors"] and "冻结清单" in result["errors"][0]


def test_starting_point_constraints_prefs_semantics_allowlist():
    from app.agent_workflows.planning_outline import outline_payload
    from app.domain.planning.intent import GoalSpec
    state = new_state()
    state["prefs_snapshot"]["private_notes"] = "do not send"
    state["domain_pack"]["semantic_context"]["full_review"] = "do not send"
    state["manifest"] = freeze_manifest(state["domain_pack"], DEFAULT_BUDGET, "mock:offline", outline_input_format=FORMAT,
        goal_spec=GoalSpec(target=GOAL, starting_point="起点", constraints=("本机练习",)))
    projected = outline_payload(state)
    assert projected["goal_spec"]["starting_point"] == "起点"
    assert projected["goal_spec"]["constraints"] == ["本机练习"]
    assert "private_notes" not in projected["prefs"]
    assert "full_review" not in projected["semantic_context"]


def test_real_worker_fake_answers_new_frozen_outline_contract():
    from app.infrastructure.providers.planning_demo import build_planning_demo
    state = new_state()
    result = PlanningNodes(llm=build_planning_demo(), save_draft=lambda _: "unused").generate_skeleton(state)
    assert not result.get("generation_errors"), result
    assert [s["stable_key"] for s in result["outline"]["sections"]] == [s["stage_key"] for s in state["manifest"]["stages"]]


CASES = [
    ("agent-application-v5.json", "我已经有一个旅行规划 Agent，希望系统补 Agent 基础，并强化网页信息获取、可恢复规划和知识检索。", "user_project", {"browser", "workflow", "rag"}),
    ("agent-application-v5.json", "我没有项目想法，想系统学习 Agent 应用开发。", "starter_candidate", set()),
    ("agent-application-v5.json", "我想学语音 Agent。", "starter_candidate", set()),
    ("cloud-services-v2.json", "我已经有一个 Node.js API，想学习部署、监控、自动发布和恢复。", "user_project", set()),
    ("ai-fullstack-v2.json", "我的项目：客服知识库；希望学习 AI Fullstack 和 AI 全栈应用开发。", "user_project", set()),
]


@pytest.mark.parametrize("file,goal,carrier,recipes", CASES)
def test_new_format_full_fake_semantic_route_rehydration(file, goal, carrier, recipes):
    from app.agent_workflows.planning_batches import (
        practice_payload,
        run_batched_planning_graph,
        structure_payload,
    )
    from app.domain.planning.intent import GoalSpec
    from app.infrastructure.providers.planning_demo import selected_output
    pack = adapt_semantic_pack(load_pack(file), goal, GoalSpec(target=goal))
    manifest = freeze_manifest(pack, DEFAULT_BUDGET, "mock:offline", outline_input_format=FORMAT)
    state = {"goal": goal, "domain_pack": pack, "manifest": manifest, "run_id": "new-semantic-fixture"}
    calls = []

    def answer(purpose, payload):
        calls.append((purpose, deepcopy(payload)))
        return selected_output(purpose, payload)

    fake = FakeLLM({p: answer for p in ("planning.outline", "planning.structure", "planning.practice", "planning.repair")})
    trace = run_batched_planning_graph(PlanningNodes(llm=fake, save_draft=lambda _: "fixture"), state)
    assert trace.stopped_at == "await_approval", trace.failed_errors
    merged = trace.state
    context = pack["semantic_context"]
    assert context["carrier_kind"] == carrier and context["binding"] == "optional"
    assert context["replacement_allowed"] is True and recipes <= set(context["recipe_refs"])
    assert "横切" in context["evaluation"]
    assert not any(s.get("recipe") == "agentic_rl" for s in pack["stage_blueprints"])
    if "语音" in goal:
        assert "voice" in context["research_gaps"]
        assert any("needs_research_or_review" in e["guidance"] for s in merged["outline"]["sections"] for e in s["extensions"])
    for section, original, spec in zip(merged["outline"]["sections"], pack["stage_blueprints"], manifest["stages"], strict=True):
        assert section["resources"] == original["resources"]
        assert section["extensions"] == original["extensions"]
        assert section["learning_guidance"] == spec["learning_guidance"]
        assert not any(e.get("required") for e in section["extensions"] if e.get("topic", "").startswith("项目学习："))
    assert all(not str(r.get("public_seed_status", "")).startswith("hold_") for r in pack["resources"])
    legacy = deepcopy(state)
    legacy["manifest"] = freeze_manifest(pack, DEFAULT_BUDGET, "mock:offline")
    # Production downstream wire context stays exactly local and equivalent.
    for batch in manifest["structure_batches"]:
        assert structure_payload(state, batch) == structure_payload(legacy, batch)
    for batch in manifest["practice_batches"]:
        assert practice_payload(state, batch["stage_key"]) == practice_payload(legacy, batch["stage_key"])
    assert all("domain_pack" not in payload for purpose, payload in calls if purpose != "planning.outline")


def test_six_stage_new_format_exact_18_resources_35_refs_13_extensions_guides():
    from app.agent_workflows.planning_batches import run_batched_planning_graph
    from app.infrastructure.providers.planning_demo import build_planning_demo
    state = new_state()
    trace = run_batched_planning_graph(PlanningNodes(llm=build_planning_demo(), save_draft=lambda _: "fixture"), state)
    assert trace.stopped_at == "await_approval", trace.failed_errors
    sections = trace.state["outline"]["sections"]
    assert sum(len(s["resources"]) for s in sections) == 18
    assert sum(len(r["section_refs"]) for s in sections for r in s["resources"]) == 35
    assert sum(len(s["extensions"]) for s in sections) == 13
    for section, source, spec in zip(sections, state["domain_pack"]["stage_blueprints"], state["manifest"]["stages"], strict=True):
        assert section["resources"] == source["resources"]
        assert section["extensions"] == source["extensions"]
        assert section["learning_guidance"] == spec["learning_guidance"]


def test_new_generic_search_only_fake_keeps_nonempty_stage_goals():
    from app.infrastructure.providers.planning_demo import build_planning_demo
    state = {"goal": "学习未审核主题", "domain_pack": {}, "run_id": "generic-new", "manifest": freeze_manifest({}, DEFAULT_BUDGET, "mock:offline", outline_input_format=FORMAT)}
    result = PlanningNodes(llm=build_planning_demo(), save_draft=lambda _: "unused").generate_skeleton(state)
    assert not result.get("generation_errors"), result


def test_provider_size_guard_rejects_leakage_before_mock_transport():
    from app.agent_workflows.planning_outline import outline_payload
    from app.ports.llm import LLMFailure
    calls = []
    def forbidden(request):
        calls.append(request)
        raise AssertionError("must reject before any dispatch")
    payload = outline_payload(new_state())
    payload["frozen_stages"][0]["objective"] = "x" * 100000
    with httpx.Client(transport=httpx.MockTransport(forbidden)) as client:
        provider = OpenAICompatibleLLM(base_url="https://api.deepseek.com/v1", api_key="synthetic", model="deepseek-flash", client=client)
        result = provider.generate_structured(purpose="planning.outline", payload=payload, schema_name="OutlineV1", run_id="fixture", attempt_id="fixture")
    assert isinstance(result, LLMFailure) and result.error_class == "outline_payload_too_large"
    assert calls == []
