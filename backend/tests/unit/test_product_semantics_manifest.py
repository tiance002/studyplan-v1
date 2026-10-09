"""Version selection is frozen before dispatch; old receipts stay legacy."""
from copy import deepcopy

import pytest
from app.core.errors import ValidationAppError
from app.core.ids import content_hash
from app.domain.planning.content_coverage import ReviewedContentIndex
from app.domain.planning.curriculum_compiler import CurriculumSourceFacts
from app.domain.planning.resource_research import ResearchBudget
from app.domain.planning.v2_runtime import build_v2_manifest, manifest_intact


def manifest(**kwargs):
    return build_v2_manifest("学习 MCP", model_ref="mock:bound",
        source_facts=CurriculumSourceFacts(ReviewedContentIndex("empty", (), (), ())),
        budget=ResearchBudget(), checked_at="2026-10-10T00:00:00+00:00", **kwargs)


def test_legacy_manifest_has_no_new_marker():
    old = manifest()
    assert "product_semantics" not in old
    assert manifest_intact(old)


def test_new_marker_bound_and_unknown_versions_rejected():
    new = manifest(product_semantics="planning-v2-product-v2")
    assert manifest_intact(new)
    assert new["manifest_hash"] != manifest()["manifest_hash"]
    bad = deepcopy(new)
    bad["product_semantics"] = "unrecognized"
    bad["manifest_hash"] = content_hash({k: v for k, v in bad.items() if k != "manifest_hash"})
    assert not manifest_intact(bad)
    with pytest.raises(ValidationAppError):
        manifest(product_semantics="unrecognized")


def test_schema_selection_cannot_upgrade_legacy_or_downgrade_new():
    from app.domain.planning.v2_runtime import purpose_schema
    assert purpose_schema(manifest(), "planning.research_reader") == "ResearchReaderV1"
    assert purpose_schema(manifest(), "planning.curriculum_composition") == "CurriculumPlanV1"
    new = manifest(product_semantics="planning-v2-product-v2")
    assert purpose_schema(new, "planning.research_reader") == "ResearchReaderV2"
    assert purpose_schema(new, "planning.curriculum_composition") == "CurriculumPlanV2"
