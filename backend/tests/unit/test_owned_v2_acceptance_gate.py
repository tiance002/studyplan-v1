"""Owned acceptance gates are opt-in; legacy manifests retain their bytes."""
from copy import deepcopy

import pytest
from app.core.errors import ValidationAppError
from app.core.ids import content_hash
from app.domain.planning.v2_runtime import manifest_intact

from backend.tests.unit.test_product_semantics_manifest import manifest


def test_owned_gate_freezes_exact_caps_and_purpose_limits():
    new = manifest(product_semantics="planning-v2-product-v2", acceptance_gate="scenario-a-review-v1")
    assert new["output_caps"]["planning.goal_requirement_analysis"] == 4096
    assert new["output_caps"]["planning.capability_planning"] == 4096
    assert new["output_caps"]["planning.curriculum_composition"] == 4096
    assert new["output_caps"]["planning.research_reader"] == 1024
    assert new["owned_acceptance"]["purpose_limits"] == {
        "planning.goal_requirement_analysis": 1, "planning.capability_planning": 1,
        "planning.research_reader": 6, "planning.curriculum_composition": 1,
        "research.search": 6, "research.body": 6,
    }
    assert manifest_intact(new)


@pytest.mark.parametrize("change", ["limit", "stage", "cap", "legacy", "version"])
def test_gate_rejects_modified_contract_even_with_rehashed_manifest(change):
    new = manifest(product_semantics="planning-v2-product-v2", acceptance_gate="scenario-a-review-v1")
    if change == "limit":
        new["owned_acceptance"]["purpose_limits"]["planning.capability_planning"] = 2
    elif change == "stage":
        new["owned_acceptance"]["review_stages"].pop()
    elif change == "cap":
        new["output_caps"]["planning.goal_requirement_analysis"] = 8192
    elif change == "legacy":
        new.pop("product_semantics")
    else:
        new["owned_acceptance"]["version"] = "unknown"
    new["manifest_hash"] = content_hash({k: v for k, v in new.items() if k != "manifest_hash"})
    assert not manifest_intact(new)


def test_opt_in_does_not_change_legacy_defaults_or_hash():
    old = manifest()
    assert "owned_acceptance" not in old
    assert manifest(acceptance_gate=None) == old
    assert old["output_caps"]["planning.goal_requirement_analysis"] == 8192
    unknown = deepcopy(old)
    unknown["owned_acceptance"] = {}
    unknown["manifest_hash"] = content_hash({k: v for k, v in unknown.items() if k != "manifest_hash"})
    assert not manifest_intact(unknown)
    with pytest.raises(ValidationAppError):
        manifest(acceptance_gate="unknown")
