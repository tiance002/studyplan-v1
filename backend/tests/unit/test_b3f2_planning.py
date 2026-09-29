import json

import httpx
import pytest
from app.infrastructure import domain_pack
from app.infrastructure.providers.openai_compatible import OpenAICompatibleLLM


@pytest.mark.parametrize("goal,expected", [
    ("从 Python 基础开始学习 Agent 应用开发", "agent.application"),
    ("Agent开发", "agent.application"),
    ("Python机器学习", ""),
    ("学习 LangGraph 和 RAG，做知识助手", "agent.application"),
    ("学习 MCP 工具调用和 LLM API", "agent.application"),
    ("我想学习 Python 工程入门和命令行工具", "python.engineering"),
    ("学习绘画与水彩构图", ""),
    ("学习 JavaScript 网页开发", ""),
])
def test_select_pack_by_actual_direction(goal, expected):
    selected = domain_pack.select_domain_pack(goal)
    assert selected.get("pack_key", "") == expected
    assert selected.get("version", 0) == (1 if expected else 0)
    if not expected:
        assert not selected.get("resources")
        assert selected["resource_support"] == "search_only"


def test_provider_uses_per_run_pack_without_shared_selection():
    calls = []
    def reply(request):
        calls.append(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": '{"outline_ref":"o","sections":[]}'}}]})
    with httpx.Client(transport=httpx.MockTransport(reply)) as client:
        provider = OpenAICompatibleLLM(base_url="https://provider.example/v1", api_key="test", model="test", client=client,
                                      domain_pack={"pack_key": "python.engineering", "version": 1})
        for selected in ({"pack_key": "agent.application", "version": 1}, {"resource_support": "search_only"}):
            provider.generate_structured(purpose="planning.outline", payload={"goal": "goal", "domain_pack": selected},
                                         schema_name="OutlineV1", run_id="r", attempt_id="a")
    assert [json.loads(c["messages"][1]["content"])["domain_pack"].get("pack_key", "") for c in calls] == ["agent.application", ""]
    assert provider.domain_pack["pack_key"] == "python.engineering"
    assert "2 stages" not in calls[0]["messages"][0]["content"]


def test_fake_complete_route_and_missing_branch_rejected():
    from copy import deepcopy

    from app.agent_workflows.graphs import run_planning_graph
    from app.agent_workflows.nodes import PlanningNodes
    from app.infrastructure.providers.planning_demo import build_planning_demo

    pack = domain_pack.select_domain_pack("Agent开发")
    nodes = PlanningNodes(llm=build_planning_demo(), save_draft=lambda state: "draft")
    trace = run_planning_graph(nodes, {"goal": "Agent开发", "run_id": "test", "domain_pack": pack})
    assert trace.stopped_at == "await_approval"
    assert len(trace.state["outline"]["sections"]) > 2
    assert set(pack["required_node_keys"]) <= {n["stable_key"] for n in trace.state["nodes"]}
    assert len(trace.state["practice_proposal"]["tasks"]) == len(trace.state["outline"]["sections"])
    broken = deepcopy(trace.state)
    broken["nodes"] = broken["nodes"][:2]
    errors = nodes.validate(broken)["structure_errors"]
    assert any("领域纲要缺少" in e for e in errors)


def test_unsupported_fake_has_no_curated_source_and_uses_actual_goal():
    from app.agent_workflows.graphs import run_planning_graph
    from app.agent_workflows.nodes import PlanningNodes
    from app.infrastructure.providers.planning_demo import build_planning_demo

    goal = "学习水彩构图"
    trace = run_planning_graph(PlanningNodes(llm=build_planning_demo(), save_draft=lambda s: "draft"),
                               {"goal": goal, "run_id": "other", "domain_pack": domain_pack.select_domain_pack(goal)})
    assert trace.stopped_at == "await_approval"
    sections = trace.state["outline"]["sections"]
    assert all(goal in s["title"] for s in sections)
    assert all(not r["source_ref"] and not r["section_refs"] for s in sections for r in s["resources"])


def test_truncated_provider_output_is_not_success():
    from app.ports.llm import LLMFailure

    with httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={
        "usage": {"prompt_tokens": 123, "completion_tokens": 8000},
        "choices": [{"finish_reason": "length", "message": {"content": '{"outline_ref":"o","sections":[]}'}}]
    }))) as client:
        provider = OpenAICompatibleLLM(base_url="https://provider.example", api_key="test", model="test", client=client)
        result = provider.generate_structured(purpose="planning.outline", payload={}, schema_name="OutlineV1", run_id="r", attempt_id="a")
    assert isinstance(result, LLMFailure)
    assert result.error_class == "provider_output_truncated"
    assert result.input_tokens == 123 and result.output_tokens == 8000


@pytest.mark.parametrize("base_url,model,disabled", [
    ("https://api.deepseek.com/v1", "deepseek-flash", True),
    ("https://api.deepseek.com", "deepseek-flash", True),
    ("https://provider.example/v1", "deepseek-flash", False),
    ("https://api.deepseek.com", "custom-model", False),
])
def test_official_deepseek_flash_json_planning_does_not_default_to_high_thinking(base_url, model, disabled):
    requests = []
    def reply(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": '{"outline_ref":"o","sections":[]}'}}]})
    with httpx.Client(transport=httpx.MockTransport(reply)) as client:
        OpenAICompatibleLLM(base_url=base_url, api_key="test", model=model, client=client).generate_structured(
            purpose="planning.outline", payload={}, schema_name="OutlineV1", run_id="test", attempt_id="test")
    if disabled:
        assert requests[0]["thinking"] == {"type": "disabled"}
    else:
        assert "thinking" not in requests[0]


def test_outside_selected_pack_reference_becomes_search_only():
    from app.application.plan_resources import restrict_pack_resources

    state = {"outline": {"sections": [{"stable_key": "stage.other", "title": "水彩构图", "resources": [
        {"role": "primary", "source_ref": "src_python_tutorial_v1", "section_refs": ["sec_python_control_v1"], "source_version": 1}
    ]}]}, "nodes": [], "units": []}
    result = restrict_pack_resources(state, domain_pack.select_domain_pack("水彩构图"))
    resource = result["outline"]["sections"][0]["resources"][0]
    assert resource["source_ref"] == "" and resource["section_refs"] == []
    assert resource["fallback_search_terms"]


def test_provider_shape_examples_are_domain_neutral_and_describe_resource_links():
    from app.infrastructure.providers.openai_compatible import SHAPES

    assert "python" not in json.dumps(SHAPES)
    resource = SHAPES["planning.outline"]["sections"][0]["resources"][0]
    assert {"node_keys", "source_ref", "section_refs", "source_version", "fallback_search_terms"} <= resource.keys()
