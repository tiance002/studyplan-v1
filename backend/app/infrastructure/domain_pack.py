"""Controlled content file registry and read-only loader; no goal routing."""
import json
from pathlib import Path

from app.domain.domain_packs.models import DomainPack
from app.domain.enums import DomainPackStatus

CURRENT_PACKS = {
    "ai.fullstack": "ai-fullstack-v4.json",
    "agent.application": "agent-application-v8.json",
    "cloud.services": "cloud-services-v4.json",
    "python.engineering": "python-engineering-v2.json",
    "agent.knowledge_rag": "agent-knowledge-rag-v1.json",
    "agent.coding": "agent-coding-v1.json",
    "agent.workflow_automation": "agent-workflow-automation-v1.json",
}

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
