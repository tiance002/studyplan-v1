"""Specific learning outcomes precede generic Agent/Python keywords."""
import pytest
from app.infrastructure import domain_pack


@pytest.mark.parametrize("goal,key", [
    ("Knowledge / RAG Agent", "agent.knowledge_rag"),
    ("学习 RAG，做文档问答智能体", "agent.knowledge_rag"),
    ("从 Python 开始做知识库 Agent", "agent.knowledge_rag"),
    ("学习 LangGraph 和 RAG，做知识助手", "agent.knowledge_rag"),
    ("Coding Agent", "agent.coding"),
    ("Ｃｏｄｉｎｇ Ａｇｅｎｔ", "agent.coding"),
    ("学习 Python 编程智能体，修复小型 CLI", "agent.coding"),
    ("代码助手：读取代码并提出修改", "agent.coding"),
    ("Workflow / Automation Agent", "agent.workflow_automation"),
    ("workflow agent with LangGraph", "agent.workflow_automation"),
    ("本地工单自动化智能体", "agent.workflow_automation"),
    ("学习工作流 Agent 和工具调用", "agent.workflow_automation"),
    ("从 Python 基础开始学习 Agent 应用开发", "agent.application"),
    ("Agent开发", "agent.application"),
    ("学习 MCP 工具调用和 LLM API", "agent.application"),
    ("Python 工程入门", "python.engineering"),
    ("Python机器学习", None),
    ("Coding Agent 与 Workflow Agent 都要学", None),
    ("RAG Agent 和 Coding Agent 两个方向", None),
    ("学习 JavaScript 网页开发", None),
])
def test_specific_outcome_routing(goal, key):
    assert domain_pack.pack_key_for_goal(goal) == key


@pytest.mark.parametrize("goal", ["RAG Agent", "Coding Agent", "Workflow Agent"])
def test_runtime_recipes_share_current_spine_without_deleting_legacy_direction(monkeypatch, goal):
    filename = domain_pack.CURRENT_PACKS['agent.application']
    calls = []
    monkeypatch.setattr(domain_pack, "load_pack", lambda name: calls.append(name) or {"filename": name})
    assert domain_pack.select_domain_pack(goal) == {"filename": filename}
    assert calls == [filename]


def test_multiple_agent_recipes_use_reviewed_spine_instead_of_python_or_generic():
    selected = domain_pack.select_domain_pack("Python Coding Agent 和 RAG Agent")
    assert selected['pack_key'] == 'agent.application'
    assert selected["resource_support"] == "reviewed_index"
    assert selected['resources']
