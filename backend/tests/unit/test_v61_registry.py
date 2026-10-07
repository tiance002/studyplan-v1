import pytest
from app.infrastructure import domain_pack




def test_one_registry_has_unique_matching_immutable_pack_identifiers():
    assert {"ai.fullstack", "agent.application", "cloud.services", "python.engineering"} <= domain_pack.CURRENT_PACKS.keys()
    assert len(set(domain_pack.CURRENT_PACKS.values())) == len(domain_pack.CURRENT_PACKS)
    for key, filename in domain_pack.CURRENT_PACKS.items():
        assert domain_pack.load_pack(filename)["pack_key"] == key
