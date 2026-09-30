import json

import httpx
from app.agent_workflows.planning_batches import validate_structure_batch
from app.agent_workflows.validators import validate_plan_structure, validate_route_structure
from app.application.planning_budget import BudgetPolicy
from app.infrastructure.domain_pack import load_pack
from app.infrastructure.providers.openai_compatible import OpenAICompatibleLLM
from app.ports.llm import LLMFailure, LLMResult


def test_real_provider_protocol_and_timeout():
    calls = []
    def reply(request):
        calls.append(request)
        return httpx.Response(200, json={"model":"test-model", "choices":[{"message":{"content":'{"sections":[],"outline_ref":"o"}'},"finish_reason":"stop"}], "usage":{"prompt_tokens":10,"completion_tokens":4}})
    budget = BudgetPolicy(4096,8192,4096,8192,8192,393216)
    llm = OpenAICompatibleLLM(base_url="https://provider.example/v1", api_key="test", model="test-model", budget_policy=budget, client=httpx.Client(transport=httpx.MockTransport(reply)))
    result = llm.generate_structured(purpose="planning.outline", payload={"goal":"Python"}, schema_name="PlanOutlineV1", run_id="r", attempt_id="a")
    assert isinstance(result, LLMResult)
    assert result.input_tokens == 10 and result.output_tokens == 4
    assert calls[0].url.path == "/v1/chat/completions"
    assert calls[0].headers["Authorization"] == "Bearer test"
    def timeout(request):
        raise httpx.ReadTimeout("outcome unknown")
    llm = OpenAICompatibleLLM(base_url="https://provider.example/v1", api_key="test", model="test-model", budget_policy=budget, client=httpx.Client(transport=httpx.MockTransport(timeout)))
    result = llm.generate_structured(purpose="planning.outline", payload={}, schema_name="PlanOutlineV1", run_id="r", attempt_id="a")
    assert isinstance(result, LLMFailure) and result.dispatch_unknown and not result.retryable


def test_transport_failure_records_exception_type_without_leaking_or_retrying():
    api_key = "test-secret-api-key"
    requests = []

    def fail_transport(request):
        requests.append(request)
        raise httpx.ReadError(f"failed Authorization: Bearer {api_key}")

    with httpx.Client(transport=httpx.MockTransport(fail_transport)) as client:
        llm = OpenAICompatibleLLM(base_url="https://provider.example", api_key=api_key,
                                  model="test-model", client=client)
        result = llm.generate_structured(purpose="planning.structure", payload={},
                                         schema_name="KnowledgeStructureV1", run_id="r", attempt_id="a")

    assert isinstance(result, LLMFailure)
    assert result.error_class == "provider_transport_unknown"
    assert result.dispatch_unknown is True
    assert result.retryable is False
    assert result.details["transport_exception_type"] == "ReadError"
    assert len(requests) == 1
    safe_diagnostics = json.dumps(result.details)
    assert api_key not in safe_diagnostics
    assert "Authorization" not in safe_diagnostics


def test_structure_and_repair_prompt_define_valid_relation_contract():
    requests = []

    def reply(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}]})

    budget = BudgetPolicy(4096,8192,4096,8192,8192,393216)
    llm = OpenAICompatibleLLM(base_url="https://provider.example",api_key="test",model="test", budget_policy=budget,
                              client=httpx.Client(transport=httpx.MockTransport(reply)))
    for purpose in ("planning.structure", "planning.repair"):
        llm.generate_structured(purpose=purpose,payload={},schema_name="KnowledgeStructureV1",run_id="r",attempt_id=purpose)

    assert llm.prompt_version == "b3f2-v4-relations"
    assert len(requests) == 2
    for request in requests:
        system = request["messages"][0]["content"]
        assert "relation_type must be exactly one of 'prerequisite' or 'contains'" in system
        assert "'part_of' is forbidden" in system
        assert "from_stable_key=parent_key" in system
        assert "to_stable_key=stable_key" in system
        assert "relation_type='contains'" in system
        assert "from_stable_key=prerequisite_key" in system
        assert "relation_type='prerequisite'" in system
        assert "fix both relation_type and endpoint direction" in system

        context = json.loads(request["messages"][1]["content"])
        relations = context["field_shape"]["relations"]
        assert relations
        keys = {item[key] for item in relations for key in ("from_stable_key", "to_stable_key")}
        outcome = validate_plan_structure(nodes=[{"stable_key":key} for key in keys],
                                           units=[],relations=relations,tasks=[])
        assert outcome.errors == []


def test_stage_tools_relation_fixture_rejects_part_of_and_accepts_contract_edges():
    pack = load_pack("agent-application-v1.json")
    batch = {
        "stage_key": "stage.tools",
        "node_keys": ["node.tools", "node.tools.1", "node.tools.2"],
        "declared_external_prerequisite_keys": ["node.model_api"],
    }
    nodes = [
        {"stable_key": "node.tools", "title": "tools", "node_type": "skill", "objectives": ["objective"]},
        {"stable_key": "node.tools.1", "title": "schema", "node_type": "concept", "objectives": ["objective"]},
        {"stable_key": "node.tools.2", "title": "structured", "node_type": "concept", "objectives": ["objective"]},
    ]
    units = [{
        "stable_key": "unit.stage.tools",
        "title": "tools",
        "section_key": "stage.tools",
        "order_index": 0,
        "node_keys": [node["stable_key"] for node in nodes],
        "objectives": ["objective"],
    }]
    invalid = {
        "nodes": nodes,
        "units": units,
        "relations": [
            {"from_stable_key": "node.tools.1", "to_stable_key": "node.tools", "relation_type": "part_of"},
            {"from_stable_key": "node.tools.2", "to_stable_key": "node.tools", "relation_type": "part_of"},
        ],
    }
    assert validate_structure_batch(invalid, batch, pack) == [
        "关系类型非法：'part_of'",
        "关系类型非法：'part_of'",
    ]

    repaired = {
        "nodes": nodes,
        "units": units,
        "relations": [
            {"from_stable_key": "node.tools", "to_stable_key": "node.tools.1", "relation_type": "contains"},
            {"from_stable_key": "node.tools", "to_stable_key": "node.tools.2", "relation_type": "contains"},
            {"from_stable_key": "node.model_api", "to_stable_key": "node.tools", "relation_type": "prerequisite"},
        ],
    }
    assert repaired["nodes"] == invalid["nodes"]
    assert repaired["units"] == invalid["units"]
    assert validate_structure_batch(repaired, batch, pack) == []

    route_state = {
        "domain_pack": {
            "resource_support": "reviewed_index",
            "stage_blueprints": [{"stable_key": "stage.tools"}],
            "resource_refs": [],
            "required_node_keys": batch["node_keys"],
            "knowledge_blueprints": [
                {"stable_key": "node.tools", "parent_key": None, "prerequisite_keys": ["node.model_api"]},
                {"stable_key": "node.tools.1", "parent_key": "node.tools", "prerequisite_keys": []},
                {"stable_key": "node.tools.2", "parent_key": "node.tools", "prerequisite_keys": []},
            ],
        },
        "outline": {"sections": [{"stable_key": "stage.tools", "resources": []}]},
        "nodes": nodes,
        "units": units,
        "tasks": [],
        "practice_proposal": {"tasks": [{"section_key": "stage.tools"}]},
        "relations": repaired["relations"],
    }
    assert validate_route_structure(route_state) == []


def test_injected_purpose_policy_sets_actual_http_output_budget():
    requests = []
    budget = BudgetPolicy(3072, 7168, 2048, 6144, 8192, 16384)

    def reply(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={"model": "other", "choices": [{
            "message": {"content": '{"outline_ref":"o","sections":[{"stable_key":"s"}]}'},
            "finish_reason": "stop",
        }], "usage": {"prompt_tokens": 3, "completion_tokens": 2}})

    with httpx.Client(transport=httpx.MockTransport(reply)) as client:
        llm = OpenAICompatibleLLM(base_url="https://provider.example", api_key="mock", model="other",
                                  budget_policy=budget, client=client)
        for purpose in ("planning.outline", "planning.structure", "planning.practice", "planning.repair"):
            llm.generate_structured(purpose=purpose, payload={}, schema_name="test", run_id="r", attempt_id=purpose)

    assert [body["max_tokens"] for body in requests] == [3072, 7168, 2048, 6144]


def test_success_with_missing_usage_keeps_unknown_values_null():
    budget = BudgetPolicy(4096,8192,4096,8192,8192,16384)
    body = {"outline_ref": "o", "sections": [{"stable_key": "stage.a"}]}
    response = httpx.Response(200, json={"model": "explicit-model", "choices": [{
        "message": {"content": json.dumps(body)}, "finish_reason": "stop",
    }]})
    with httpx.Client(transport=httpx.MockTransport(lambda request: response)) as client:
        llm = OpenAICompatibleLLM(base_url="https://provider.example", api_key="mock", model="explicit-model",
                                  budget_policy=budget, client=client)
        result = llm.generate_structured(purpose="planning.outline", payload={}, schema_name="test",
                                         run_id="r", attempt_id="a")
    assert isinstance(result, LLMResult)
    assert result.input_tokens is None
    assert result.output_tokens is None
    assert result.cost_micros is None
    assert result.diagnostics["max_tokens"] == 4096
    assert result.diagnostics["requested_model"] == "explicit-model"
