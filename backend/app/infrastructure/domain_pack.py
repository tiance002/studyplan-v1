"""Repository-reviewed, versioned planning input. Runtime loading is read-only."""
import json
import re
import unicodedata
from pathlib import Path

from app.domain.domain_packs.models import DomainPack
from app.domain.enums import DomainPackStatus

CURRENT_PACKS = {
    "ai.fullstack": "ai-fullstack-v1.json",
    "agent.application": "agent-application-v4.json",
    "cloud.services": "cloud-services-v1.json",
    "python.engineering": "python-engineering-v2.json",
    "agent.knowledge_rag": "agent-knowledge-rag-v1.json",
    "agent.coding": "agent-coding-v1.json",
    "agent.workflow_automation": "agent-workflow-automation-v1.json",
}

# Compatibility view for existing specialized curricula; filenames have one owner.
DIRECTION_PACK_FILES = {key: filename for key, filename in CURRENT_PACKS.items()
                        if key.startswith("agent.") and key != "agent.application"}


def load_python_pack():
    return load_pack(CURRENT_PACKS["python.engineering"])


def load_pack(filename: str) -> dict:
    data = json.loads((Path(__file__).parent / "content" / filename).read_text(encoding="utf-8-sig"))
    pack = DomainPack.create(pack_key=data["pack_key"],version=data["version"],status=DomainPackStatus(data["status"]),
                            supported_scope=data["supported_scope"],title=data["title"],
                            stage_blueprints=tuple(data["stage_blueprints"]),resource_refs=tuple(data["resource_refs"]),
                            practice_blueprints=tuple(data["practice_blueprints"]),provenance=data["provenance"])
    pack.require_published()
    data.setdefault("resource_support", "reviewed_index")
    return data


def select_domain_pack(goal: str) -> dict:
    """Conservative, deterministic scope routing; never use Python as a fallback."""
    key = pack_key_for_goal(goal)
    if key in CURRENT_PACKS:
        return load_pack(CURRENT_PACKS[key])
    return unsupported_domain_pack()


def pack_key_for_goal(goal: str) -> str | None:
    text = unicodedata.normalize("NFKC", goal).casefold()
    ai = bool(re.search(r"(?<![a-z])ai(?![a-z])|人工智能|全栈.*(?:模型|智能)|(?:模型|智能).*全栈", text))
    cloud = bool(re.search(r"云服务|云计算|云平台|(?<![a-z])(?:cloud|azure|aws)(?![a-z])", text))
    if ai and cloud:
        return None
    if ai:
        return 'ai.fullstack'
    if cloud:
        return 'cloud.services'
    # A broad Agent spine with a later RAG focus is not a RAG-only curriculum.
    if (re.search(r"(?<![a-z])agent(?:s)?(?![a-z])|智能体", text)
            and re.search(r"系统学|从零|零基础|先学|入门", text)
            and re.search(r"后面|以后|之后|重点|再学", text)):
        return 'agent.application'
    # Target routing is deliberately bounded. A multi-direction target needs a
    # narrower GoalSpec; selecting the first match would invent its priority.
    specific = {
        "agent.knowledge_rag": r"(?<![a-z0-9])rag(?![a-z0-9])|knowledge\s*(?:/\s*rag\s*)?agents?\b|知识库|知识助手|知识问答|文档问答|检索增强",
        "agent.coding": r"\b(?:coding|code)\s*[- ]?\s*agents?\b|(?:编程|代码)(?:智能体|助手|\s*agent)",
        "agent.workflow_automation": r"\b(?:workflow|automation)\s*(?:/\s*automation\s*)?[- ]?\s*agents?\b|(?:工作流|自动化)\s*(?:智能体|助手|agent)|工单自动化",
    }
    matches = [key for key, pattern in specific.items() if re.search(pattern, text)]
    if matches:
        return matches[0] if len(matches) == 1 else None
    if re.search(r"(?<![a-z0-9])(?:agents?|rag|mcp|llm)(?![a-z0-9])|langgraph|智能体|知识助手|工具调用", text):
        return 'agent.application'
    if "python" in text and not re.search(r"机器学习|深度学习|数据分析|数据科学|量化|machine learning|data science", text):
        return 'python.engineering'
    return None


def unsupported_domain_pack() -> dict:
    return {"pack_key": "", "version": 0, "resource_support": "search_only",
            "supported_scope": "请先确认具体学习方向；当前仅生成通用结构和资料搜索建议。", "resources": []}
