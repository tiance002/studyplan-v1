import json

import httpx
import pytest
from app.infrastructure import domain_pack
from app.infrastructure.providers.openai_compatible import OpenAICompatibleLLM




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


def test_reviewed_required_node_validation_rejects_missing_branch():
    from app.agent_workflows.nodes import PlanningNodes
    from app.infrastructure.providers.fake import FakeLLM
    from tests.helpers.planning_responses import selected_output

    pack = domain_pack.load_pack("agent-application-v1.json")
    # Keep the content protection assertion; retired route length/task-count
    # and interrupt expectations are not a product contract for Planning V2.
    nodes = PlanningNodes(llm=FakeLLM())
    payload = {"goal": "Agent开发", "domain_pack": pack}
    broken = {**payload, **selected_output("planning.structure", payload),
              "outline": selected_output("planning.outline", payload),
              "practice_proposal": selected_output("planning.practice", payload)}
    assert set(pack["required_node_keys"]) <= {n["stable_key"] for n in broken["nodes"]}
    broken["nodes"] = broken["nodes"][:2]
    errors = nodes.validate(broken)["structure_errors"]
    assert any("领域纲要缺少" in e for e in errors)




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
    result = restrict_pack_resources(state, {"resource_support": "search_only", "resources": []})
    resource = result["outline"]["sections"][0]["resources"][0]
    assert resource["source_ref"] == "" and resource["section_refs"] == []
    assert resource["fallback_search_terms"]


def test_provider_shape_examples_are_domain_neutral_and_describe_resource_links():
    from app.infrastructure.providers.openai_compatible import SHAPES

    assert "python" not in json.dumps(SHAPES)
    resource = SHAPES["planning.outline"]["sections"][0]["resources"][0]
    assert {"node_keys", "source_ref", "section_refs", "source_version", "fallback_search_terms"} <= resource.keys()
