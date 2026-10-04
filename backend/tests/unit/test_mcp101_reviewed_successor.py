"""Scoped body review creates a new immutable source; old facts stay readable.

Expectations come from the published predecessor and the captured 10.1 audit,
never from the successor mapper or its resource qualifier.
"""

import hashlib
from copy import deepcopy
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.application.plan_resources import restrict_pack_resources
from app.domain.domain_packs.validation import validate_seed
from app.infrastructure.domain_pack import CURRENT_PACKS, load_pack


ROOT = Path(__file__).resolve().parents[3]
OLD_SOURCE = "src_v612_1f6742530460b0908234a6d3"
OLD_SECTION = "sec_v612_d79f6a54976fb31d5159ac60"
OLD_PACK_SHA = "624201cbd073a8b2a5bdec0fb9c5e70a00fcdf986dcd6229494f1b7a99016080"


def chapter(pack):
    return next(s for s in pack["resources"]
                if s.get("metadata", {}).get("scope_key") == "hello-common-ch10")


def section101(pack):
    return next(s for s in chapter(pack)["sections"] if s["order_index"] == 0)


def current():
    return load_pack(CURRENT_PACKS["agent.application"])


def stage_state(pack, code="A6"):
    stage = deepcopy(next(s for s in pack["stage_blueprints"] if s["stage_code"] == code))
    return {"outline": {"sections": [stage]}, "units": [
        {"stable_key": "unit.scoped-review." + code,
         "section_key": stage["stable_key"], "node_keys": deepcopy(stage["node_keys"])}]}


def test_current_approved_mcp101_reference_survives_pack_restriction():
    """Catch missing qualification/current binding, without changing the old Pack."""
    pack = current()
    chosen = section101(pack)
    assert chosen["verification_status"] == "reviewed"
    assert chosen["review_depth"] == "selected_sections_read"
    validate_seed(pack)
    before = stage_state(pack)
    after = restrict_pack_resources(before, pack)
    assert after["outline"]["sections"][0]["resources"] == before["outline"]["sections"][0]["resources"]
    assert after["outline"]["sections"][0]["resources"][0]["source_version"] == 2
    assert after["outline"]["sections"][0]["resources"][0]["section_refs"] == [chosen["section_id"]]


def test_old_published_pack_bytes_and_legacy_reference_remain_unchanged():
    """Catch overwriting a published review or reinterpreting the old Run."""
    path = ROOT / "backend/app/infrastructure/content/agent-application-v7.json"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == OLD_PACK_SHA
    old = load_pack("agent-application-v7.json")
    assert chapter(old)["source_id"] == OLD_SOURCE
    assert section101(old)["section_id"] == OLD_SECTION
    assert section101(old)["verification_status"] == "legacy_index"
    assert section101(old)["review_depth"] == "toc_checked"
    restricted = restrict_pack_resources(stage_state(old), old)
    ref = restricted["outline"]["sections"][0]["resources"][0]
    assert ref["role"] == "reference" and ref["order_index"] == 0
    assert ref["source_ref"] == "" and ref["section_refs"] == [] and ref["source_version"] == 0
    assert ref["fallback_search_terms"]


def aliases_by_author_order(old, new):
    """Derive expected bindings from fixed author order, not the mapper helper."""
    before, after = chapter(old), chapter(new)
    assert len(before["sections"]) == len(after["sections"]) == 4
    return {before["source_id"]: after["source_id"], **{
        b["section_id"]: a["section_id"]
        for b, a in zip(before["sections"], after["sections"], strict=True)}}


def expected_alias(value, aliases):
    if isinstance(value, dict):
        result = {key: expected_alias(item, aliases) for key, item in value.items()}
        if result.get("source_ref") == aliases[OLD_SOURCE]:
            result["source_version"] = 2
        return result
    if isinstance(value, list):
        return [expected_alias(item, aliases) for item in value]
    return aliases.get(value, value) if isinstance(value, str) else deepcopy(value)


def test_successor_changes_only_chapter10_catalog_identity_and_authorized_review():
    """Catch curriculum changes, stale aliases or unrelated source rewrites."""
    old, new = load_pack("agent-application-v7.json"), current()
    assert new["version"] == 8
    aliases = aliases_by_author_order(old, new)
    assert len(aliases) == 5 and len(set(aliases.values())) == 5
    assert not set(aliases) & set(aliases.values())
    assert all(len(identity) <= 64 for identity in aliases.values())
    assert new["provenance"] == old["provenance"]
    assert new["knowledge_blueprints"] == old["knowledge_blueprints"]
    assert new["practice_blueprints"] == old["practice_blueprints"]
    assert new["stage_blueprints"] == expected_alias(old["stage_blueprints"], aliases)
    assert new["resource_refs"] == expected_alias(old["resource_refs"], aliases)
    before_sources = {s["source_id"]: s for s in old["resources"]}
    after_sources = {s["source_id"]: s for s in new["resources"]}
    assert len(before_sources) == len(after_sources)
    assert set(after_sources) == (set(before_sources) - {OLD_SOURCE}) | {aliases[OLD_SOURCE]}
    for identifier, source in before_sources.items():
        if identifier != OLD_SOURCE:
            assert after_sources[identifier] == source
    before, after = chapter(old), chapter(new)
    assert before["source_version"] == 1 and after["source_version"] == 2
    for b, a in zip(before["sections"], after["sections"], strict=True):
        assert a["section_id"] == aliases[b["section_id"]]
        if b["section_id"] != OLD_SECTION:
            assert a == {**b, "section_id": aliases[b["section_id"]]}
        else:
            qualification_fields = {"section_id", "verification_status", "review_depth",
                                    "checked_at", "review_note", "body_review"}
            assert {k: v for k, v in a.items() if k not in qualification_fields} == {
                k: v for k, v in b.items() if k not in qualification_fields}
    assert after["runtime_validation"] == before["runtime_validation"] == "not_run"
    assert after["review_evidence"]["chapter_review"] == before["review_evidence"]["chapter_review"]


def test_mapper_publishes_reproducible_scoped_evidence_without_mutating_predecessor():
    """Catch mapper drift, expanded review claims or missing bounded provenance."""
    from app.tools.map_mcp101_review import build_mcp101_reviewed_pack

    old = load_pack("agent-application-v7.json")
    immutable_copy = deepcopy(old)
    mapped = build_mcp101_reviewed_pack()
    assert old == immutable_copy
    assert mapped == current() == build_mcp101_reviewed_pack()
    evidence = mapped["publication_evidence"]["mcp101_scoped_review"]
    assert evidence["base_pack"] == "agent.application/7"
    assert evidence["base_provenance"] == old["provenance"]
    assert evidence["identity_map"] == aliases_by_author_order(old, mapped)
    review = section101(mapped)["body_review"]
    assert review == evidence["review"]
    assert review == chapter(mapped)["review_evidence"]["additional_section_review"]
    assert review["date"] == "2026-10-05"
    assert review["reviewed_scope"] == ["10.1.1", "10.1.2", "10.1.3", "10.1.4"]
    assert review["body_language"] == "en"
    assert review["runtime_validation"] == "not_run"
    assert review["observed_git_blob"] == "98b0700c4adf3259efc1842a307c9b2c2238fc9b"
    assert review["body_sha256"] == "e68e510739fc08527f994eac7ab4104b5abc38f4b51c3e788d2fa9ef2111a60d"
    assert review["section_sha256"] == "97ff3dbbab2119cb15c85d072cbe534b58f8abcb60d69fc63eaf8dbc68220e4d"
    assert review["section_utf8_bytes"] == 13346
    assert review["captured_section_file_utf8_bytes"] == 13551
    assert review["captured_section_file_sha256"] == "ddbb8acb2a13eca2ac1293138e393c15809d45c7c01251018f7853837d9201e4"


@pytest.mark.parametrize("mutation", ["hold", "directory_as_reviewed", "undated_review",
                                     "old_source", "wrong_version", "foreign_section"])
def test_publication_rejects_held_unqualified_or_mixed_catalog_bindings(mutation):
    """Catch an expanded publication exception for the newly reviewed chapter."""
    pack = deepcopy(current())
    source = chapter(pack)
    section = section101(pack)
    assignment = next(s for s in pack["stage_blueprints"] if s["stage_code"] == "A6")["resources"][0]
    if mutation == "hold":
        source["public_seed_status"] = "hold_content_review"
    elif mutation == "directory_as_reviewed":
        section["review_depth"] = "toc_checked"
    elif mutation == "undated_review":
        section["checked_at"] = None
    elif mutation == "old_source":
        assignment["source_ref"] = OLD_SOURCE
    elif mutation == "wrong_version":
        assignment["source_version"] = 1
    elif mutation == "foreign_section":
        assignment["section_refs"] = [next(s for s in pack["resources"]
            if s["source_id"] != source["source_id"] and s["sections"])["sections"][0]["section_id"]]
    with pytest.raises(ValueError):
        validate_seed(pack)


@pytest.mark.parametrize("mutation", ["version", "source", "foreign_section", "wrong_applicability", "legacy_section"])
def test_reviewed_successor_does_not_make_invalid_references_approved(mutation):
    """Catch an A6 bypass that accepts unrelated or unqualified references."""
    pack = deepcopy(current())
    state = stage_state(pack)
    resource = state["outline"]["sections"][0]["resources"][0]
    if mutation == "version":
        resource["source_version"] = 1
    elif mutation == "source":
        resource["source_ref"] = "src.outside.selected.pack"
    elif mutation == "foreign_section":
        resource["section_refs"] = [next(s for s in pack["resources"]
            if s["source_id"] != chapter(pack)["source_id"] and s["sections"])["sections"][0]["section_id"]]
    elif mutation == "wrong_applicability":
        section101(pack)["applicable_node_keys"] = ["node.foreign.stage"]
    elif mutation == "legacy_section":
        section101(pack)["verification_status"] = "legacy_index"
        section101(pack)["review_depth"] = "toc_checked"
    after = restrict_pack_resources(state, pack)["outline"]["sections"][0]["resources"][0]
    assert after["source_ref"] == "" and after["section_refs"] == [] and after["source_version"] == 0
    assert after["role"] == "reference" and after["order_index"] == 0
    assert after["fallback_search_terms"]


def test_metadata_repo_empty_sections_and_old_pending_index_contract_survive():
    """Catch new review guard broadening into unrelated candidate/legacy paths."""
    pack = current()
    state = stage_state(pack, "GR")
    expected = deepcopy(state["outline"]["sections"][0]["resources"])
    assert len(expected) == 2 and all(r["role"] == "case_study" and not r["section_refs"] for r in expected)
    assert restrict_pack_resources(state, pack)["outline"]["sections"][0]["resources"] == expected
    legacy = load_pack("agent-application-v4.json")
    assert legacy["curriculum_review"]["review_status"] == "selected_scope_pending"
    stage = next(s for s in legacy["stage_blueprints"] if s["resources"] and s["resources"][0]["section_refs"])
    prior = {"outline": {"sections": [deepcopy(stage)]}, "units": [{
        "section_key": stage["stable_key"], "node_keys": deepcopy(stage["node_keys"])}]}
    assert restrict_pack_resources(prior, legacy)["outline"]["sections"][0]["resources"] == stage["resources"]


def resource_projection(pack=None, code="A6"):
    from app.application.draft_projection import project_draft
    from app.ports.runs import CatalogIds

    pack = deepcopy(pack or current())
    state = stage_state(pack, code)
    node_keys = state["units"][0]["node_keys"]
    catalog = CatalogIds(node_ids={key: f"node-projected-{i}" for i, key in enumerate(node_keys)},
        unit_ids={state["units"][0]["stable_key"]: "unit-projected"},
        practice_project_id="practice-projected", task_ids={})
    draft = project_draft(project_id="p-projection", run_id="r-projection", goal_snapshot="scoped review",
        revision_candidate=1, state=state, catalog=catalog, source_pack_key=pack["pack_key"],
        source_pack_version=pack["version"])
    stage_ids = {stage.stable_key: stage.stage_id for stage in draft.stages}
    return pack, state, draft, stage_ids, catalog.node_ids


def final_guard(**kwargs):
    from app.application import plan_resources

    assert callable(getattr(plan_resources, "assert_frozen_resource_projection", None)), "final frozen resource guard is missing"
    return plan_resources.assert_frozen_resource_projection(**kwargs)


def test_late_normalizer_loss_is_rejected_before_it_can_be_saved():
    """Catch a normalizer clearing an independently approved frozen identity."""
    from app.core.errors import ConflictError

    pack, state, draft, stage_ids, node_ids = resource_projection()
    assignments = list(draft.stage_resources)
    assignments[0] = replace(assignments[0], source_ref="", source_version=0,
        section_refs=(), fallback_search_terms=("explicit but erroneous fallback",))
    with pytest.raises(ConflictError) as exc:
        final_guard(state=state, pack=pack, assignments=assignments,
                    stage_ids=stage_ids, node_ids=node_ids)
    assert exc.value.details["reason"] == "frozen_resource_projection_invalid"


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "source", "version", "section",
                                     "role", "order", "missing_node", "foreign_node", "stage"])
def test_final_frozen_guard_rejects_identity_or_scope_loss(mutation):
    """Catch every independently frozen source identity dimension at last boundary."""
    from app.core.errors import ConflictError
    from app.domain.enums import StageResourceRole

    pack, state, draft, stage_ids, node_ids = resource_projection()
    assignments = list(draft.stage_resources)
    original = assignments[0]
    if mutation == "missing":
        assignments.pop(0)
    elif mutation == "duplicate":
        assignments.append(replace(original, assignment_id="asg-duplicate"))
    else:
        changes = {
            "source": {"source_ref": OLD_SOURCE},
            "version": {"source_version": 1},
            "section": {"section_refs": (OLD_SECTION,)},
            "role": {"role": StageResourceRole.COMPARISON},
            "order": {"order_index": 99},
            "missing_node": {"node_ids": ()},
            "foreign_node": {"node_ids": ("node-foreign",)},
            "stage": {"stage_id": "stage-foreign"},
        }[mutation]
        assignments[0] = replace(original, **changes)
    with pytest.raises(ConflictError) as exc:
        final_guard(state=state, pack=pack, assignments=assignments,
                    stage_ids=stage_ids, node_ids=node_ids)
    assert exc.value.details["reason"] == "frozen_resource_projection_invalid"


@pytest.mark.parametrize("code", ["A6", "GR"])
def test_final_guard_accepts_exact_teaching_and_metadata_repo_projections(code):
    pack, state, draft, stage_ids, node_ids = resource_projection(code=code)
    final_guard(state=state, pack=pack, assignments=draft.stage_resources,
                stage_ids=stage_ids, node_ids=node_ids)


def test_final_guard_allows_truthful_legacy_fallback_without_inventing_review():
    from app.application.draft_projection import project_draft
    from app.ports.runs import CatalogIds

    old = load_pack("agent-application-v7.json")
    pack, state, draft, stage_ids, node_ids = resource_projection(old)
    restricted = restrict_pack_resources(state, pack)
    normalized = project_draft(project_id=draft.project_id, run_id=draft.run_id,
        goal_snapshot=draft.goal_snapshot, revision_candidate=1, state=restricted,
        catalog=CatalogIds(node_ids=node_ids, unit_ids={state["units"][0]["stable_key"]: "unit-projected"},
            practice_project_id="practice-projected", task_ids={}))
    normalized_stage_id = normalized.stages[0].stage_id
    final_guard(state=state, pack=pack, assignments=normalized.stage_resources,
        stage_ids={normalized.stages[0].stable_key: normalized_stage_id}, node_ids=node_ids)


@pytest.mark.parametrize("mapping", ["node", "stage"])
def test_final_guard_rejects_missing_catalog_identity_with_domain_conflict(mapping):
    from app.core.errors import ConflictError

    pack, state, draft, stage_ids, node_ids = resource_projection()
    if mapping == "node":
        node_ids = {}
    else:
        stage_ids = {}
    with pytest.raises(ConflictError) as exc:
        final_guard(state=state, pack=pack, assignments=draft.stage_resources,
                    stage_ids=stage_ids, node_ids=node_ids)
    assert exc.value.details["reason"] == "frozen_resource_projection_invalid"


@pytest.fixture(scope="module")
def prepared_successor_generation():
    """One shared ordinary common-core Fake, with independent F1 receipts."""
    from app.agent_workflows.nodes import PlanningNodes
    from app.agent_workflows.planning_batches import (
        DEFAULT_BUDGET, SHORT_GENERATION_VERSION, freeze_manifest, run_batched_planning_graph,
    )
    from app.domain.planning.semantic_content import adapt_semantic_pack
    from app.infrastructure.providers.planning_demo import build_planning_demo

    goal = "零基础系统学习 Agent 应用开发，先做一个最小应用。"
    pack = adapt_semantic_pack(current(), goal, None)
    initial = {"goal": goal, "project_id": "p-mcp101-unit", "run_id": "r-mcp101-unit",
        "domain_pack": pack, "graph_version": SHORT_GENERATION_VERSION, "expected_version": 0,
        "prefs_snapshot": {"language": "zh"}, "manifest": freeze_manifest(
            pack, DEFAULT_BUDGET, "mock:scoped-review", outline_input_format="stage_skeleton_v1",
            structure_input_format="reviewed_structure_v1")}
    fake = build_planning_demo()
    nodes = PlanningNodes(llm=fake, save_draft=lambda _: "unit-only-no-database",
                          frozen_input=deepcopy(initial))
    trace = run_batched_planning_graph(nodes, deepcopy(initial))
    assert not trace.state.get("generation_errors") and not trace.state.get("validation_errors")
    assert trace.state.get("draft_ref") == "unit-only-no-database"
    return initial, deepcopy(trace.state), deepcopy(nodes._raw_receipts), fake


class ScopedResourceCatalog:
    """The complete catalog read port; storage/network side effects are excluded."""

    def __init__(self, pack):
        from app.domain.resources.curation import PublicResourceSection, PublicResourceSource

        self.sources = {s["source_id"]: PublicResourceSource(
            source_id=s["source_id"], canonical_url=s["canonical_url"], title=s["title"],
            creator=s["creator"], media_type=s["media_type"], language=s["language"],
            source_version=s["source_version"], verification_status=s["verification_status"],
            checked_at=datetime.fromisoformat(s["checked_at"]) if s.get("checked_at") else None,
            documentation_version=s.get("documentation_version", ""), provenance=pack["provenance"])
            for s in pack["resources"]}
        self.sections = {s["section_id"]: PublicResourceSection(
            section_id=s["section_id"], source_id=source["source_id"], order_index=s["order_index"],
            title=s["title"], url=s["url"], anchor=s.get("anchor", ""),
            verification_status=s["verification_status"], review_note=s.get("review_note", ""),
            checked_at=datetime.fromisoformat(s["checked_at"]) if s.get("checked_at") else None)
            for source in pack["resources"] for s in source["sections"]}

    def load_sources(self, *, source_ids):
        return {key: self.sources[key] for key in source_ids if key in self.sources}

    def load_source_sections(self, *, source_ids):
        return {key: section for key, section in self.sections.items() if section.source_id in source_ids}


def persistence_fixture(prepared):
    from app.agent_workflows.planning_batches import SHORT_GENERATION_VERSION
    from app.application.plan_service import PlanService
    from app.ports.runs import CatalogIds

    initial, state, receipts, fake = prepared
    saved = []
    catalog = CatalogIds(
        node_ids={n["stable_key"]: f"node-{i}" for i, n in enumerate(state["nodes"])},
        unit_ids={u["stable_key"]: f"unit-{i}" for i, u in enumerate(state["units"])},
        task_ids={t["stable_key"]: f"task-{i}" for i, t in enumerate(state["practice_proposal"]["tasks"])},
        practice_project_id="practice-unit")
    repo = SimpleNamespace(get_draft=lambda **_: None, get_current=lambda **_: None,
        save_draft=lambda draft, **_: saved.append(deepcopy(draft)))
    service = PlanService(repository=repo, runs=SimpleNamespace(get_run=lambda **_: None),
        catalog=SimpleNamespace(materialize=lambda **_: catalog),
        resources=ScopedResourceCatalog(initial["domain_pack"]), llm=fake,
        graph_version=SHORT_GENERATION_VERSION)
    service._generation_inputs[initial["run_id"]] = deepcopy(initial)
    service._generation_receipts[initial["run_id"]] = deepcopy(receipts)
    return service, saved, initial, deepcopy(state), fake


def test_actual_save_entry_rejects_late_normalizer_loss(prepared_successor_generation, monkeypatch):
    """Catch removal, misplacement or missing authority at the application save hook."""
    import app.application.plan_service as module
    from app.core.errors import ConflictError

    service, saved, initial, state, fake = persistence_fixture(prepared_successor_generation)
    normalizer = module.normalize_stage_resources
    approved_section = section101(initial["domain_pack"])["section_id"]

    def lose_approved_reference(*args, **kwargs):
        assignments = list(normalizer(*args, **kwargs))
        index = next(i for i, a in enumerate(assignments) if a.section_refs == (approved_section,))
        assignments[index] = replace(assignments[index], source_ref="", section_refs=(),
            source_version=0, fallback_search_terms=("synthetic late loss",))
        return tuple(assignments)

    monkeypatch.setattr(module, "normalize_stage_resources", lose_approved_reference)
    before_calls = len(fake.calls)
    with pytest.raises(ConflictError) as exc:
        service._persist_draft(project_id=initial["project_id"], run_id=initial["run_id"],
            goal=initial["goal"], state=state, selected_pack=initial["domain_pack"])
    assert exc.value.details["reason"] == "frozen_resource_projection_invalid"
    assert not saved and len(fake.calls) == before_calls


def test_actual_save_entry_preserves_exact_new_chapter_binding(prepared_successor_generation):
    service, saved, initial, state, fake = persistence_fixture(prepared_successor_generation)
    before_calls = len(fake.calls)
    result = service._persist_draft(project_id=initial["project_id"], run_id=initial["run_id"],
        goal=initial["goal"], state=state, selected_pack=initial["domain_pack"])
    assert len(saved) == 1 and result["draft_ref"] == saved[0].draft_id
    stage_id = next(s.stage_id for s in saved[0].stages if s.stable_key == "stage.v62.agent.application.a6")
    assignment = next(a for a in saved[0].stage_resources if a.stage_id == stage_id and a.order_index == 0)
    assert assignment.source_ref == chapter(initial["domain_pack"])["source_id"]
    assert assignment.source_version == 2
    assert assignment.section_refs == (section101(initial["domain_pack"])["section_id"],)
    assert assignment.node_ids and len(fake.calls) == before_calls


def test_existing_user_edited_draft_is_reused_before_new_projection_guard(
    prepared_successor_generation, monkeypatch,
):
    """Catch a new guard replaying frozen generation over a retained user edit."""
    import app.application.plan_service as module

    service, saved, initial, state, fake = persistence_fixture(prepared_successor_generation)
    service._persist_draft(project_id=initial["project_id"], run_id=initial["run_id"],
        goal=initial["goal"], state=state, selected_pack=initial["domain_pack"])
    existing = deepcopy(saved[0])
    approved_section = section101(initial["domain_pack"])["section_id"]
    assignments = list(existing.stage_resources)
    index = next(i for i, a in enumerate(assignments) if a.section_refs == (approved_section,))
    assignments[index] = replace(assignments[index], source_ref="", source_version=0,
        section_refs=(), fallback_search_terms=("retained user edit",))
    existing.stage_resources = tuple(assignments)
    expected_hash = existing.content_hash
    service._repo.get_draft = lambda **_: existing

    def unexpected_new_projection(*args, **kwargs):
        raise AssertionError("Retained draft must return before new projection")

    monkeypatch.setattr(module, "assert_frozen_resource_projection", unexpected_new_projection)
    monkeypatch.setattr(module, "normalize_stage_resources", unexpected_new_projection)
    service._catalog.materialize = unexpected_new_projection
    before_calls = len(fake.calls)
    result = service._persist_draft(project_id=initial["project_id"], run_id=initial["run_id"],
        goal=initial["goal"], state=deepcopy(state), selected_pack=initial["domain_pack"])
    assert result == {"draft_ref": existing.draft_id, "draft_hash": expected_hash}
    assert len(saved) == 2 and saved[-1].content_hash == expected_hash
    assert saved[-1].stage_resources == existing.stage_resources
    assert len(fake.calls) == before_calls
