"""Bounded v6.1 content checks; no model, cloud, clone or database execution."""
import json
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from app.agent_workflows.planning_batches import DEFAULT_BUDGET, freeze_manifest, manifest_is_intact
from app.domain.domain_packs.validation import validate_seed
from app.domain.resources.curation import KnowledgeExtension

CONTENT = Path(__file__).parents[2] / "app" / "infrastructure" / "content"
FILES = ("ai-fullstack-v1.json", "cloud-services-v1.json", "agent-application-v4.json")


def pack(filename):
    return json.loads((CONTENT / filename).read_text(encoding="utf-8"))


@pytest.mark.parametrize("filename", FILES)
def test_minimal_pack_validates_and_freezes_all_content(filename):
    data = validate_seed(pack(filename))
    manifest = freeze_manifest(data, DEFAULT_BUDGET, "fake:v61-content")
    assert manifest_is_intact(manifest)
    assert [s["stage_key"] for s in manifest["stages"]] == [s["stable_key"] for s in data["stage_blueprints"]]
    assert set(manifest["required_node_keys"]) == set(data["required_node_keys"])
    assert len(data["stage_blueprints"]) <= 8
    for stage in data["stage_blueprints"]:
        assert stage["learning_guidance"]["practice_delta"]["reuse"]
        assert stage["learning_guidance"]["reading_prerequisites"]
        assert any(p["section_key"] == stage["stable_key"] for p in data["practice_blueprints"])
        for extension in stage["extensions"]:
            KnowledgeExtension.create(project_id="test-project", stage_id="test-stage", **extension)


@pytest.mark.parametrize("filename", FILES)
def test_repo_card_uses_one_root_and_existing_extension_fields(filename):
    data = pack(filename)
    sources = {s["source_id"]: s for s in data["resources"]}
    cards = []
    for stage in data["stage_blueprints"]:
        cases = [r for r in stage["resources"] if r["role"] == "case_study"]
        assert len(cases) <= 1
        assert "source_slice" not in stage["learning_guidance"]
        for case in cases:
            source = sources[case["source_ref"]]
            assert source["media_type"] == "repo"
            parsed = urlsplit(source["canonical_url"])
            assert parsed.netloc == "github.com"
            assert len(parsed.path.strip("/").split("/")) == 2
            assert not parsed.query and not parsed.fragment
            assert case["section_refs"] == []
            ext = next(e for e in stage["extensions"] if e["topic"] == "项目学习：" + source["title"])
            assert ext["links"] == [source["canonical_url"]]
            assert ext["concepts"] and len(ext["guidance"]) <= 1000
            assert all(prefix in ext["guidance"] for prefix in ("为什么现在：", "学习深度：", "暂不涉及："))
            assert any("迁移" in q for q in ext["thinking_prompts"])
            cards.append(ext)
    assert cards
    assert not {"commit", "ref", "files", "file_path", "function_name", "call_chain"}.intersection(
        key for source in sources.values() for key in source)


def test_representative_route_order_and_minimum_entry():
    ai = pack("ai-fullstack-v1.json")
    assert [s["stable_key"] for s in ai["stage_blueprints"]] == [
        "stage.web", "stage.own_project", "stage.genai", "stage.repo"]
    assert ai["knowledge_blueprints"][0]["prerequisite_keys"] == []
    assert "SQL" not in ai["stage_blueprints"][0]["learning_guidance"]["reading_prerequisites"][0]
    cloud = pack("cloud-services-v1.json")
    assert [s["stable_key"] for s in cloud["stage_blueprints"]] == [
        "stage.service", "stage.docker", "stage.cloud", "stage.manual_deploy",
        "stage.cicd", "stage.manual_resources", "stage.iac", "stage.repo"]
    agent = pack("agent-application-v4.json")
    assert [s["stable_key"] for s in agent["stage_blueprints"]] == [
        "stage.entry", "stage.agent_spine", "stage.comparison", "stage.rag", "stage.runtime_repo"]
    assert agent["stage_blueprints"][2]["inclusion"] == "optional"
    assert any(r["role"] == "comparison" for r in agent["stage_blueprints"][2]["resources"])
    assert all("genai" not in key.lower() for key in agent["required_node_keys"])
    assert agent["version"] == 4 and pack("agent-application-v3.json")["version"] == 3


@pytest.mark.parametrize("filename", FILES)
def test_minimal_pack_does_not_claim_deep_source_review(filename):
    data = pack(filename)
    assert data["curriculum_review"]["status"] == "outline_checked"
    assert data["curriculum_review"]["review_status"] == "selected_scope_pending"
    assert data["curriculum_review"]["provider_execution"] == "NOT RUN"
    assert all(s["verification_status"] in {"unverified", "legacy_index"} for s in data["resources"])
    assert all(sec["verification_status"] in {"unverified", "legacy_index"}
               for source in data["resources"] for sec in source["sections"])
