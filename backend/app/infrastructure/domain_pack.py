"""Repository-reviewed, versioned planning input. Runtime loading is read-only."""
import json
from pathlib import Path

from app.domain.domain_packs.models import DomainPack
from app.domain.enums import DomainPackStatus


def load_python_pack():
    data = json.loads((Path(__file__).parent / "content" / "python-engineering-v1.json").read_text(encoding="utf-8-sig"))
    pack = DomainPack.create(pack_key=data["pack_key"],version=data["version"],status=DomainPackStatus.PUBLISHED,
                            supported_scope=data["supported_scope"],title=data["title"],
                            stage_blueprints=tuple(data["stage_blueprints"]),resource_refs=tuple(data["resource_refs"]),
                            practice_blueprints=tuple(data["practice_blueprints"]),provenance=data["provenance"])
    pack.require_published()
    return data
