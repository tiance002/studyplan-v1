"""Discovery preserves upstream evidence and stable relevance order."""
import json
from dataclasses import asdict

import httpx
import pytest
from app.application.resource_discovery_contract import DiscoveryEvidence, SelectionMapping
from app.core.errors import ValidationAppError
from app.domain.enums import MediaType, ResourceProvenance, ResourceVerificationStatus
from app.domain.resources.discovery import validate_private_mapping
from app.domain.resources.models import DEFAULT_SYSTEM_PREFERENCE, ResourceRecord, rank_resources
from app.infrastructure.resources.tavily import TavilyResourceIndex

from tests.unit.test_tavily_resource_index import query, streaming_json


def record(title):
    return ResourceRecord(resource_id=title, project_id="project", title=title,
        url=f"https://example.org/{title}", media_type=MediaType.TEXT, language="und",
        provenance=ResourceProvenance.SEARCH_CANDIDATE,
        verification_status=ResourceVerificationStatus.UNVERIFIED)


def test_equal_candidates_keep_provider_order_instead_of_title_order():
    resources = [record("Z tutorial"), record("A tutorial")]
    assert [r.title for r in rank_resources(resources, preference=DEFAULT_SYSTEM_PREFERENCE)] == [
        "Z tutorial", "A tutorial"]


def test_tavily_retains_actual_rank_score_and_bounded_snippet():
    adapter = TavilyResourceIndex("test", transport=httpx.MockTransport(lambda _: streaming_json({
        "results": [{"title": "Z", "url": "https://example.org/z", "score": 0.85,
                     "content": "<b>RAG chapter</b> " + "x" * 2500},
                    {"title": "A", "url": "https://example.org/a"}]})))
    resources = adapter.find(query())
    evidence = asdict(resources[0])["discovery"]
    assert evidence["provider_rank"] == 1
    assert evidence["provider_score"] == 0.85
    assert evidence["source"] == "web"
    assert evidence["snippet"].startswith("RAG chapter")
    assert len(evidence["snippet"]) <= 2000
    assert resources[1].discovery["provider_score"] is None
    assert resources[0].verification_status is ResourceVerificationStatus.UNVERIFIED
    json.dumps(evidence)


def test_chapter_read_label_without_file_receipt_cannot_be_mapped():
    evidence = DiscoveryEvidence(chapters=[{"path": "lesson.md", "title": "Lesson", "order": 0, "status": "read"}],
        selection_mapping=SelectionMapping(module_keys=["allowed"], chapter_paths=["lesson.md"]))
    with pytest.raises(ValidationAppError):
        validate_private_mapping(evidence, ["allowed"])


def test_actual_provider_score_and_original_rank_break_otherwise_equal_ties():
    low, high, tied = record("A"), record("Z"), record("B")
    low.discovery = {"source": "web", "provider_rank": 1, "provider_score": 0.2}
    high.discovery = {"source": "web", "provider_rank": 2, "provider_score": 0.9}
    tied.discovery = {"source": "web", "provider_rank": 3, "provider_score": 0.9}
    assert [r.resource_id for r in rank_resources([low, high, tied], preference=DEFAULT_SYSTEM_PREFERENCE)] == ["Z", "B", "A"]


def test_actual_teaching_evidence_precedes_higher_provider_score_installation_reference():
    tutorial, installation = record("Tutorial"), record("Install")
    tutorial.discovery = {"source": "web", "provider_rank": 2, "provider_score": 0.6,
        "signals": {"topic_overlap": 1, "teaching_structure": True, "prerequisites": True, "exercises": True}}
    installation.discovery = {"source": "web", "provider_rank": 1, "provider_score": 0.9,
        "recommended_role": "reference", "signals": {"topic_overlap": 1}}
    assert rank_resources([installation, tutorial], preference=DEFAULT_SYSTEM_PREFERENCE)[0] is tutorial


@pytest.mark.parametrize("discovery", [
    {"signals": "malformed", "provider_score": float("nan"), "provider_rank": "invalid"},
    {"signals": {"topic_overlap": True}, "provider_score": float("inf"), "provider_rank": False},
])
def test_domain_ranking_treats_malformed_raw_metadata_as_neutral(discovery):
    first, second = record("Z"), record("A")
    first.discovery = discovery
    assert rank_resources([first, second], preference=DEFAULT_SYSTEM_PREFERENCE) == [first, second]
