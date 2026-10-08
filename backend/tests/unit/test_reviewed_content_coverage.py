"""Current real review qualification and local frozen mapping; no new tutorial reads."""
import hashlib
import json
from pathlib import Path

import pytest
from app.core.errors import ValidationAppError
from app.domain.planning.content_coverage import CoverageEvaluator, CoverageResultValidator
from app.infrastructure.reviewed_content_coverage import load_reviewed_content_index

from backend.tests.unit.test_capability_planning import cap, plan, profile, wire

ROOT = Path(__file__).resolve().parents[3]
PACK = Path("backend/app/infrastructure/content/agent-application-v8.json")
DOC = Path("docs/research/semantic-corrected-2026-10-04/AGENT_APPLICATION_DEEP_REVIEW.md")
SOURCE = "src_mcp101_a7ca881ee83ac722491299cd"
SECTION = "sec_mcp101_09e62ff389cb388eb744e738"


def mcp_plan(depth="applied", route="narrow_goal"):
    p = profile("按冻结范围学习MCP")
    return plan(p, wire(p, cap(p, "mcp", desired_depth=depth, project_usage="excluded"), route_kind=route))


def copied_index_files(tmp_path):
    pack = json.loads((ROOT / PACK).read_text(encoding="utf-8-sig"))
    for path in (PACK, DOC):
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / path).read_bytes())
    return pack


def test_real_existing_index_mapping_is_scoped_to_two_concept_outcomes_and_actual_review():
    index = load_reviewed_content_index()
    assert index.policy_version == "v2"
    assert {m.outcome_id for m in index.mappings} == {"mcp.roles", "mcp.interfaces"}
    assert len(index.sections) == 1
    section = index.sections[0]
    assert (section.content_id, section.content_version, section.source_id, section.source_version, section.section_id) == (
        "agent.application", 8, SOURCE, 2, SECTION)
    assert section.content_hash == hashlib.sha256((ROOT / PACK).read_bytes()).hexdigest()
    assert section.review_depth == "selected_sections_read" and section.verification_status == "reviewed"
    assert any("/review_evidence/chapter_review" in ev.reference for ev in index.evidence)
    assert any("AGENT_APPLICATION_DEEP_REVIEW.md" in ev.reference and ev.sha256 == hashlib.sha256((ROOT / DOC).read_bytes()).hexdigest()
               for ev in index.evidence)
    assert all(ev.limitations for ev in index.evidence)


@pytest.mark.parametrize("depth,route,expected", [
    ("foundation", "narrow_goal", "full"),
    ("applied", "narrow_goal", "partial"),
    ("foundation", "systematic_agent_route", "partial"),
])
def test_real_mcp_concepts_full_does_not_imply_application_is_covered(depth, route, expected):
    frozen = mcp_plan(depth, route)
    index = load_reviewed_content_index()
    result = CoverageEvaluator().evaluate(frozen, index)
    assert CoverageResultValidator().validate(result, plan=frozen, index=index) == result
    assert result.to_payload() == CoverageEvaluator().evaluate(frozen, load_reviewed_content_index()).to_payload()
    item = result.entries[0]
    assert item.coverage == expected
    assert set(item.covered_outcomes) == {"mcp.roles", "mcp.interfaces"}
    assert item.missing_outcomes == (() if expected == "full" else ("mcp.minimal_connection",))
    assert len(item.content_refs) == 1 and item.content_refs[0].section.section_id == SECTION


def test_real_tool_calling_keeps_both_outcomes_missing_without_precise_review_mapping():
    p = profile("学习工具调用")
    frozen = plan(p, wire(p, cap(p, "llm.api"), cap(p, "tool.calling")))
    result = CoverageEvaluator().evaluate(frozen, load_reviewed_content_index())
    assert all(e.coverage == "none" for e in result.entries)
    tool = next(e for e in result.entries if e.capability_id == "tool.calling")
    assert set(tool.missing_outcomes) == {"tool.calling.input_validation", "tool.calling.invoke_result"}


@pytest.mark.parametrize("change", ["source_version", "section_id", "toc_only", "review_removed", "review_scope"])
def test_configured_actual_mapping_cannot_silently_survive_changed_identity_or_review(tmp_path, change):
    pack = copied_index_files(tmp_path)
    source = pack["resources"][13]
    if change == "source_version":
        source["source_version"] += 1
    elif change == "section_id":
        source["sections"][1]["section_id"] = "sec_other"
    elif change == "toc_only":
        source["sections"][1].update(verification_status="legacy_index", review_depth="toc_checked")
    elif change == "review_removed":
        del source["review_evidence"]["chapter_review"]
    else:
        source["review_evidence"]["chapter_review"]["teaches"] = ["chapter title only"]
    (tmp_path / PACK).write_text(json.dumps(pack, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValidationAppError):
        load_reviewed_content_index(root=tmp_path)


def test_review_document_change_is_explicit_error_not_normal_none(tmp_path):
    copied_index_files(tmp_path)
    (tmp_path / DOC).write_text("README related to MCP, no body review", encoding="utf-8")
    with pytest.raises(ValidationAppError):
        load_reviewed_content_index(root=tmp_path)


def test_old_toc_version_cannot_inherit_successor_review_mapping(tmp_path):
    copied_index_files(tmp_path)
    old = ROOT / "backend/app/infrastructure/content/agent-application-v7.json"
    pack = json.loads(old.read_text(encoding="utf-8-sig"))
    source = next(s for s in pack["resources"] if s.get("metadata", {}).get("scope_key") == "hello-common-ch10")
    assert source["sections"][0]["verification_status"] == "legacy_index"
    assert source["sections"][0]["review_depth"] == "toc_checked"
    (tmp_path / PACK).write_bytes(old.read_bytes())
    with pytest.raises(ValidationAppError):
        load_reviewed_content_index(root=tmp_path)
