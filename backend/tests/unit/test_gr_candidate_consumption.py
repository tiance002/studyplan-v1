"""Frozen candidate identity consumption; no catalog writes or model requests."""
from copy import deepcopy
from types import SimpleNamespace

import pytest
from app.api.v1.views import resource_view
from app.application.plan_service import PlanService


def fixture():
    assignment = SimpleNamespace(assignment_id="asg", stage_id="gr", source_ref="src",
                                 source_version=1, role="case_study")
    view = dict(assignment_id="asg", stage_id="gr", role="case_study", creator="review",
                source_ref="src", source_version=1, ordered_sections=[], fallback_search_terms=[],
                warnings=[], node_ids=[], title="Candidate", media_type="repo", language="en",
                documentation_version="", verification_status="legacy_index")
    snapshot = dict(assignment_id="asg", stage_id="gr", role="case_study", source_ref="src",
                    source_version=1, snapshot_status="frozen", view=view,
                    source=dict(source_id="src", source_version=1, media_type="repo",
                                verification_status="legacy_index", checked_at="2026-10-03",
                                canonical_url="https://github.com/infiniflow/ragflow"))
    service = PlanService.__new__(PlanService)
    class NoCatalog:
        def load_sources(self, *, source_ids):
            assert not source_ids, "Do not use the current catalog for frozen identity"
            return {}
        def load_source_sections(self, *, source_ids):
            assert not source_ids
            return {}
    service._resources = NoCatalog()
    return service, assignment, snapshot


def test_metadata_only_candidate_exposes_frozen_url_without_changing_facts():
    service, assignment, snapshot = fixture()
    before = deepcopy(snapshot)
    result = resource_view(service._resolve([assignment], [], [snapshot])[0])
    assert result.canonical_url == snapshot["source"]["canonical_url"]
    assert result.source_ref == "src" and result.source_version == 1
    assert result.verification_status == "legacy_index"
    assert result.ordered_sections == [] and result.warnings == []
    assert snapshot == before


@pytest.mark.parametrize("path,value", [
    (("source", "source_id"), "other"), (("source", "source_version"), 2),
    (("source_ref",), "other"), (("source_version",), 2),
    (("stage_id",), "other"), (("role",), "primary"),
    (("snapshot_status",), "unresolved_reference"),
    (("source", "verification_status"), "unverified"),
    (("source", "checked_at"), None), (("source", "media_type"), "course"),
    (("source", "canonical_url"), "https://github.com/e/a?token=private"),
    (("view", "source_ref"), "other"), (("view", "warnings"), ["unresolved"]),
])
def test_inconsistent_or_unqualified_frozen_identity_exposes_no_url(path, value):
    service, assignment, snapshot = fixture()
    target = snapshot
    for field in path[:-1]:
        target = target[field]
    target[path[-1]] = value
    # Never trust a URL supplied in the view itself.
    snapshot["view"]["canonical_url"] = "https://github.com/forged/repo"
    result = resource_view(service._resolve([assignment], [], [snapshot])[0])
    assert result.canonical_url is None


def test_old_snapshot_without_source_remains_unbound_without_current_catalog():
    service, assignment, snapshot = fixture()
    snapshot.pop("source")
    result = resource_view(service._resolve([assignment], [], [snapshot])[0])
    assert result.canonical_url is None
