import pytest
from app.infrastructure import domain_pack


@pytest.mark.parametrize("goal,key", [
    ("零基础系统学 Agent，后面重点 RAG。", "agent.application"),
    ("做 AI 资料工作台。", "ai.fullstack"),
    ("学习云服务，能开发、部署和运维 API。", "cloud.services"),
    ("AI Fullstack", "ai.fullstack"), ("Azure cloud services", "cloud.services"),
    ("Python 工程入门", "python.engineering"),
    ("学习 AI Fullstack 和云服务两个方向", None),
    ("想成为工程师", None), ("Workflow Agent", "agent.workflow_automation"),
])
def test_conservative_primary_and_preserved_specialized_routes(goal, key):
    assert domain_pack.pack_key_for_goal(goal) == key
    selected = domain_pack.select_domain_pack(goal)
    if key:
        runtime_key = 'agent.application' if key.startswith('agent.') else key
        assert selected == domain_pack.load_pack(domain_pack.CURRENT_PACKS[runtime_key])
    else:
        assert selected["resource_support"] == "search_only"


def test_one_registry_has_unique_matching_immutable_pack_identifiers():
    assert {"ai.fullstack", "agent.application", "cloud.services", "python.engineering"} <= domain_pack.CURRENT_PACKS.keys()
    assert len(set(domain_pack.CURRENT_PACKS.values())) == len(domain_pack.CURRENT_PACKS)
    for key, filename in domain_pack.CURRENT_PACKS.items():
        assert domain_pack.load_pack(filename)["pack_key"] == key
