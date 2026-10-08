"""Small, read-only projection of retained local review evidence.

The two outcome bindings below are a curated interpretation of the retained
review, not fields originally present in that review. No title matching, source
fetching, publication inheritance or runtime execution qualification is implied.
"""
import hashlib
import json
from pathlib import Path

from app.core.errors import ValidationAppError
from app.core.ids import content_hash
from app.domain.planning.content_coverage import (
    OutcomeMapping,
    ReviewedContentIndex,
    ReviewedSection,
    ReviewEvidence,
)

_PACK = "backend/app/infrastructure/content/agent-application-v8.json"
_DOC = "docs/research/semantic-corrected-2026-10-04/AGENT_APPLICATION_DEEP_REVIEW.md"
_PACK_HASH = "6171e7bbed660d3f1d81d0c65b7b102eef0c2ec8dd7a3c40e54d4e3093985d0b"
_DOC_HASH = "3349acbc6b407d48560a48a9c7891ac20856aaa8dddf8702faf9823797bab55c"
_SECTION_HASH = "8278e9f8bae2291a5446080f771f0080381b02ce9c5734e0cc994f9ef74e9b38"
_REVIEW_HASH = "2be64ad62fee6b73832ff08fd404bed705ba9a4b8b47120bdc46c4b9bd3cbd07"
_SOURCE = "src_mcp101_a7ca881ee83ac722491299cd"
_SECTION = "sec_mcp101_09e62ff389cb388eb744e738"
_OUTCOMES = ("mcp.roles", "mcp.interfaces")


def _require(condition, field):
    if not condition:
        raise ValidationAppError("Reviewed Content 映射来源完整性错误", field=field)


def _frozen_bytes(root, path, expected_hash):
    try:
        data = (root / path).read_bytes()
    except OSError:
        raise ValidationAppError("Reviewed Content 映射来源不可读", field=path) from None
    _require(hashlib.sha256(data).hexdigest() == expected_hash, path)
    return data


def load_reviewed_content_index(*, root=None) -> ReviewedContentIndex:
    """Load only the pinned v8 MCP 10.2 identity and its existing review.

    Pins bind pack/document bytes and canonical section/review objects. They do
    not claim to be hashes of tutorial bodies (not retained for this section).
    A changed configured source is an integrity error, never normal `none`.
    ``root`` allows offline validation of frozen copies without any DB access.
    """
    root = Path(root) if root is not None else Path(__file__).resolve().parents[3]
    pack_bytes = _frozen_bytes(root, _PACK, _PACK_HASH)
    _frozen_bytes(root, _DOC, _DOC_HASH)
    try:
        pack = json.loads(pack_bytes.decode("utf-8-sig"))
        source = pack["resources"][13]
        section = source["sections"][1]
        review = source["review_evidence"]["chapter_review"]
        _require((pack["pack_key"], pack["version"]) == ("agent.application", 8), "content_version")
        _require((source["source_id"], source["source_version"]) == (_SOURCE, 2), "source_identity")
        _require(section["section_id"] == _SECTION, "section_identity")
        _require(source["verification_status"] == section["verification_status"] == "reviewed", "review_status")
        _require(section["review_depth"] == "selected_sections_read", "review_depth")
        _require(content_hash(section) == _SECTION_HASH, "section_record_hash")
        _require(content_hash(review) == _REVIEW_HASH, "review_record_hash")
        limitations = tuple(value for key in ("mentions_only_or_not_verified", "executable_examples_not_run", "risks")
                            for value in review[key])
    except (KeyError, IndexError, TypeError, ValueError, UnicodeError):
        raise ValidationAppError("Reviewed Content 映射来源结构错误", field="reviewed_index") from None

    refs = (f"repo:{_PACK}#/resources/13/sections/1",
            f"repo:{_PACK}#/resources/13/review_evidence/chapter_review",
            f"repo:{_DOC}#L197-L205")
    evidence = tuple(ReviewEvidence(ref, digest, (_SECTION,), _OUTCOMES, "selected_sections_read", limitations)
                     for ref, digest in zip(refs, (_SECTION_HASH, _REVIEW_HASH, _DOC_HASH), strict=True))
    reviewed = ReviewedSection("agent.application", 8, _PACK_HASH, _SOURCE, 2, _SECTION,
                               "reviewed", "reviewed", "selected_sections_read", refs)
    mappings = tuple(OutcomeMapping(outcome_id, "agent.application", 8, _SOURCE, 2, _SECTION, refs)
                     for outcome_id in _OUTCOMES)
    return ReviewedContentIndex("planning-v2-reviewed-v1", (reviewed,), mappings, evidence)
