"""Six roles and author-catalog intervals, without paid calls or Seed mutation."""
from copy import deepcopy

import pytest
from app.domain.domain_packs.validation import validate_seed
from app.domain.enums import StageResourceRole
from app.domain.resources import curation
from app.infrastructure.domain_pack import load_pack


def check(refs, role="primary", catalog=None):
    return curation.validate_section_selection(
        source_ref="src", section_refs=tuple(refs), role=StageResourceRole(role),
        catalog_order=catalog or {"a": ("src", 10), "b": ("src", 30), "c": ("src", 90)},
    )


def test_six_serialized_roles():
    assert {r.value for r in StageResourceRole} == {
        "primary", "supplement", "comparison", "reference", "case_study", "practice"}


def test_primary_sparse_author_indices_are_adjacent_by_rank():
    assert check(["a", "b"]) == []
    assert check(["b", "c"]) == []


@pytest.mark.parametrize("refs", [["a", "c"], ["b", "a"], ["a", "a"], [""], ["ghost"]])
def test_corrupt_primary_is_not_sorted_or_truncated(refs):
    assert check(refs)


def test_wrong_source_and_ambiguous_catalog_are_rejected():
    assert check(["a"], catalog={"a": ("other", 10)})
    assert check(["a"], catalog={"a": ("src", 10), "b": ("src", 10)})


@pytest.mark.parametrize("role", ["supplement", "comparison", "reference", "case_study", "practice"])
def test_secondary_selection_preserves_noncontiguous_submitted_order(role):
    assert check(["c", "a"], role) == []


@pytest.mark.parametrize("role", ["comparison", "case_study", "practice"])
def test_seed_accepts_new_roles_without_relabeling(role):
    pack = deepcopy(load_pack("python-engineering-v1.json"))
    item = pack["stage_blueprints"][0]["resources"][0]
    item["role"] = role
    item["section_refs"].reverse()
    assert validate_seed(pack)["stage_blueprints"][0]["resources"][0] == item


def test_seed_rejects_primary_gap_in_full_source_catalog():
    pack = deepcopy(load_pack("agent-application-v3.json"))
    item = pack["stage_blueprints"][0]["resources"][0]
    source = next(s for s in pack["resources"] if s["source_id"] == item["source_ref"])
    third = deepcopy(source["sections"][-1])
    third.update(section_id="sec_test_third", order_index=90)
    source["sections"].append(third)
    item["section_refs"] = [source["sections"][0]["section_id"], source["sections"][2]["section_id"]]
    with pytest.raises(ValueError):
        validate_seed(pack)


def test_output_loads_full_catalog_instead_of_selected_subset():
    from app.application.plan_resources import resolve_stage_resources

    source = curation.PublicResourceSource.create(canonical_url="https://example.com", title="Course")
    chapters = {key: curation.PublicResourceSection(
        section_id=key, source_id=source.source_id, order_index=index,
        title=key, url="https://example.com/" + key) for key, index in [("a", 10), ("b", 30), ("c", 90)]}

    class Catalog:
        def load_sources(self, *, source_ids):
            assert source_ids == [source.source_id]
            return {source.source_id: source}

        def load_source_sections(self, *, source_ids):
            assert source_ids == [source.source_id]
            return chapters

        def load_sections(self, *, section_ids):
            pytest.fail("Selected chapters cannot prove adjacency")

    selected = curation.StageResourceAssignment.create(project_id="p", stage_id="s",
        role=StageResourceRole.PRIMARY, source_ref=source.source_id, section_refs=("a", "c"))
    view, = resolve_stage_resources([selected], catalog=Catalog(), stage_titles={"s": "Course"})
    assert view.ordered_sections == () and view.warnings and view.fallback_search_terms
    assert selected.section_refs == ("a", "c")


def test_outline_prompt_exposes_six_roles_and_author_interval_offline():
    import json

    import httpx
    from app.infrastructure.providers.openai_compatible import OpenAICompatibleLLM

    requests = []

    def respond(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}]})

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        provider = OpenAICompatibleLLM(base_url="https://example.com", api_key="test", model="test", client=client)
        provider.generate_structured(purpose="planning.outline", payload={}, schema_name="PlanOutlineV1",
            run_id="r", attempt_id="a")
    prompt = requests[0]["messages"][0]["content"]
    for role in StageResourceRole:
        assert role.value in prompt
    assert "contiguous interval" in prompt and "Role alone does not make a supplement required" in prompt
