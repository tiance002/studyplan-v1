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

    assert llm.prompt_version == "v2-g2-v8-resource-roles"
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
        assert "Every emitted node, including parent/skill nodes" in system
        assert "required_unit_node_keys" in system
        assert "contains relations do not satisfy unit coverage" in system

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
        "缺少领域前置依赖：node.model_api -> node.tools（stage.tools）",
        "缺少子知识关联：node.tools.1（stage.tools）",
        "缺少子知识关联：node.tools.2（stage.tools）",
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


def test_stage_environment_practice_prompt_defines_json_and_required_fields():
    requests = []
    pack = load_pack("agent-application-v1.json")
    stage = next(s for s in pack["stage_blueprints"] if s["stable_key"] == "stage.environment")
    blueprint = next(p for p in pack["practice_blueprints"] if p["section_key"] == "stage.environment")
    payload = {
        "stage": {"stable_key": "stage.environment"},
        "structure": {"nodes": [{"stable_key": key} for key in stage["node_keys"]], "units": []},
        "practice_blueprint": blueprint,
    }

    def reply(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}]})

    with httpx.Client(transport=httpx.MockTransport(reply)) as client:
        llm = OpenAICompatibleLLM(base_url="https://provider.example", api_key="mock", model="mock", client=client)
        for purpose, schema in (("planning.practice", "PracticeProposalV1"),
                                ("planning.repair", "PracticeProposalV1")):
            llm.generate_structured(purpose=purpose, payload=payload, schema_name=schema,
                                    run_id="fake", attempt_id=purpose)

    assert llm.prompt_version == "v2-g2-v8-resource-roles"
    assert len(requests) == 2
    for body in requests:
        system = body["messages"][0]["content"]
        assert "role must be exactly 'core', 'supporting' or 'extension'" in system
        assert "'support' is invalid" in system
        assert "No markdown fences or trailing text" in system
        assert "stable_key, title, idea, tasks, task_knowledge_links" in system
        assert "section_key must match the supplied stage.stable_key" in system
        assert "task_stable_key" in system and "node_stable_key" in system
        message = json.loads(body["messages"][1]["content"])
        assert message["context"] == payload
        assert set(message["field_shape"]) == {
            "stable_key", "title", "idea", "tasks", "task_knowledge_links"
        }


def test_practice_provider_classifies_envelope_json_and_shape_without_retry_or_secret():
    secret = "test-secret-api-key"
    valid = {
        "stable_key": "practice.stage.environment", "title": "environment", "idea": "build",
        "tasks": [{"stable_key": "task.environment", "title": "setup", "goal": "run",
                   "section_key": "stage.environment", "order_index": 0,
                   "in_scope": ["setup"], "out_scope": [], "acceptance": ["check"],
                   "knowledge_links": [{"node_stable_key": "node.environment", "role": "core"}]}],
        "task_knowledge_links": [{"task_stable_key": "task.environment",
                                  "node_stable_key": "node.environment", "role": "core"}],
    }
    requests = []
    contents = ["```json\n{}\n```", json.dumps({"tasks": valid["tasks"]}),
                json.dumps(valid), None]

    def reply(request):
        requests.append(request)
        content = contents[len(requests) - 1]
        return httpx.Response(200, json={"model": "mock", "choices": [{
            "message": {"content": content}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 940, "completion_tokens": 1096}})

    with httpx.Client(transport=httpx.MockTransport(reply)) as client:
        llm = OpenAICompatibleLLM(base_url="https://provider.example", api_key=secret,
                                  model="mock", client=client)
        results = [llm.generate_structured(purpose="planning.practice", payload={},
                                           schema_name="PracticeProposalV1", run_id="fake",
                                           attempt_id=f"fake-{i}") for i in range(4)]

    malformed, missing, good, absent = results
    assert isinstance(malformed, LLMFailure)
    assert malformed.error_class == "provider_invalid_json"
    assert malformed.details["content_has_code_fence"] is True
    assert malformed.retryable is False
    assert isinstance(missing, LLMResult)
    assert missing.payload == {"tasks": valid["tasks"]}
    assert missing.diagnostics["missing_top_level_fields"] == [
        "idea", "stable_key", "task_knowledge_links", "title"
    ]
    assert isinstance(good, LLMResult)
    assert good.payload == valid
    assert isinstance(absent, LLMFailure)
    assert absent.error_class == "provider_invalid_envelope"
    assert absent.details["content_present"] is False
    assert absent.retryable is False
    assert len(requests) == 4
    for result in (malformed, missing, absent):
        diagnostic = json.dumps(result.details if isinstance(result, LLMFailure) else result.diagnostics)
        assert secret not in diagnostic
        assert "Authorization" not in diagnostic
        assert "```json" not in diagnostic
