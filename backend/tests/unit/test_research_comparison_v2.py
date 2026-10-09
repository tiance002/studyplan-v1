"""Offline v2 finite comparison; materials remain explicitly synthetic."""
from copy import deepcopy
from dataclasses import replace

from app.core.ids import content_hash
from app.domain.planning.resource_research import ResearchSession, research_input_hash

from backend.tests.unit import test_resource_research as f

V2 = "research_comparison_v2"


class Bodies(f.Bodies):
    def read(self, candidate, **kwargs):
        result = f.body("Synthetic tutorial with example and explanation for bounded comparison")
        result.url = candidate.url + "/blob/main/chapter.md"
        result.resource_id = "resource_" + content_hash({"url": result.url})
        chunk = result.chunks[0]
        chunk["resource_id"] = result.resource_id
        chunk["chunk_id"] = "chunk_" + content_hash({k: chunk[k] for k in
            ("resource_id", "version", "content_hash", "location")})
        self.calls.append(candidate.url)
        self.produced.append(result)
        return result


class Reader(f.Reader):
    def __init__(self, tie=False):
        super().__init__()
        self.tie = tie

    def generate_structured(self, **kwargs):
        result = super().generate_structured(**kwargs)
        raw = deepcopy(result.payload)
        zh = len(self.calls) == 1
        raw["teaching_fit"]["language"] = "zh" if zh else "en"
        chunk = kwargs["payload"]["chunks"][0]
        raw["quality_evidence"] = {dimension: {"category": "adequate" if zh or self.tie else "strong",
            "rationale": "Synthetic equal coverage" if zh or self.tie else "Synthetic fuller worked failure examples",
            "evidence_refs": [{"chunk_id": chunk["chunk_id"], "content_hash": chunk["content_hash"]}]}
            for dimension in ("continuity", "beginner_fit", "examples", "version_fit")}
        return replace(result, payload=raw)


def execute(*, tie=False, budget=None, values=None, same=False):
    values = values or f.inputs()
    p, plan, coverage, gaps = values
    budget = budget or f.ResearchBudget()
    session = ResearchSession("v2-run", research_input_hash(gaps, plan, coverage, p, budget,
        project_id="project", checked_at=f.STAMP, actor_id="actor", rules_version=V2), budget, rules_version=V2)
    zh = f.candidate("https://github.com/zh/tutorial")
    en = replace(f.candidate("https://github.com/en/tutorial"), language="en")
    result = f.run(values, budget=budget, github=f.Search([en, zh]), web=f.Search([]),
        bodies=Bodies(), reader=Reader(tie), session=session)
    return result


def test_v2_compares_full_scope_and_prefers_stronger_english_before_language():
    result, session, _, _, bodies, reader, _ = execute()
    assert len(reader.calls) == 2
    assert reader.calls[0]["payload"]["must_teach"] == reader.calls[1]["payload"]["must_teach"]
    entry = result.entries[0]
    assert entry.comparison_status == "sufficient"
    assert entry.comparison_order[0] == next(r.resource_id for r in entry.resources if "/en/" in r.url)
    assert result.to_payload()["rules_version"] == V2
    assert ResearchSession.restore(session.snapshot()).rules_version == V2
    assert all(not b.chunks for b in bodies.produced)


def test_v2_equal_quality_uses_chinese_tiebreak():
    result, _, _, _, _, reader, _ = execute(tie=True)
    assert len(reader.calls) == 2
    entry = result.entries[0]
    assert entry.comparison_order[0] == next(r.resource_id for r in entry.resources if "/zh/" in r.url)


def test_v2_budget_cutoff_retains_resolution_but_comparison_insufficient():
    result, _, _, _, _, reader, _ = execute(budget=f.ResearchBudget(max_reader_requests=1))
    assert len(reader.calls) == 1 and result.entries[0].status == "resolved"
    assert result.entries[0].comparison_status == "insufficient"


def test_legacy_payload_exactly_omits_all_v2_fields():
    result, session, *_ = f.run()
    payload = result.to_payload()
    assert "rules_version" not in payload
    assert "comparison_status" not in payload["entries"][0]
    assert "quality_evidence" not in payload["entries"][0]["resources"][0]
    assert session.snapshot().rules_version == "legacy"


def test_joint_review_reuses_same_depth_and_never_shallow_for_deep():
    from app.domain.planning.content_coverage import CoverageEvaluator, ReviewedContentIndex
    from app.domain.planning.resource_gaps import extract

    from backend.tests.unit.test_capability_planning import cap, plan, profile, wire

    def values(depth):
        p = profile("学习工具调用")
        frozen = plan(p, wire(p, cap(p, "llm.api", desired_depth="foundation"),
            cap(p, "tool.calling", desired_depth=depth)))
        coverage = CoverageEvaluator().evaluate(frozen, ReviewedContentIndex("empty", (), (), ()))
        return p, frozen, coverage, extract(frozen, coverage)

    same_result, _, _, _, _, same_reader, _ = execute(values=values("foundation"))
    assert len(same_reader.calls) == 2
    assert all(e.status == "resolved" for e in same_result.entries)
    result, session, _, _, _, reader, _ = execute(values=values("deep"))
    assert len(reader.calls) == 4
    shallow = reader.calls[0]["payload"]
    assert shallow["learner_context"]["desired_depth"] == "foundation"
    assert not any(o["outcome_id"].startswith("tool.calling") for o in shallow["must_teach"])
    assert reader.calls[2]["payload"]["learner_context"]["desired_depth"] == "deep"
    assert all(e.status == "resolved" for e in result.entries)
    restored = ResearchSession.restore(session.snapshot())
    assert set(restored.inspected) == set(session.inspected)
    assert all("#depth:" in key for key in restored.inspected)


def test_new_scope_reads_only_new_outcomes_and_conservatively_merges_quality():
    from app.application.teaching_resource_research import ResourceResearcher

    from backend.tests.unit.test_product_fix_boundaries import actual_inputs
    values = actual_inputs()
    p, plan, coverage, gaps = values
    budget = f.ResearchBudget()
    session = ResearchSession("scope-reuse", research_input_hash(gaps, plan, coverage, p, budget,
        project_id="project", checked_at=f.STAMP, actor_id="actor", rules_version=V2), budget, rules_version=V2)
    result, _, _, _, _, reader, _ = f.run(values, session=session, github=f.Search(), bodies=Bodies(), reader=Reader())
    assert {o["outcome_id"] for o in reader.calls[2]["payload"]["must_teach"]} == {"tool.calling.invoke_result"}
    resource = next(e for e in result.entries if e.requirement.capability_id == "llm.api").resources[0]
    strong = replace(resource, quality_evidence=tuple(replace(q, category="strong") for q in resource.quality_evidence))
    adequate = replace(resource, quality_evidence=tuple(replace(q, category="adequate") for q in resource.quality_evidence))
    assert all(q.category == "adequate" for q in ResourceResearcher._merge_resources([strong, adequate])[0].quality_evidence)
