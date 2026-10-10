"""Algorithm counterexamples use synthetic evidence, not real textbook review."""
from dataclasses import replace

from app.application.teaching_resource_research import ResourceResearcher
from app.domain.planning.resource_research import ResearchSession, research_input_hash

from backend.tests.unit import test_research_comparison_v2 as v
from backend.tests.unit import test_resource_research as f


def test_project_usage_prompt_keeps_exclusion_distinct_from_optional_without_new_field():
    from app.infrastructure.providers.capability_planning_contract import CAPABILITY_SYSTEM
    assert all(rule in CAPABILITY_SYSTEM for rule in (
        "非必用不能自动推出excluded", "可追溯的用户限制或真实项目适配依据", "不增加理由输出字段",
        "保留现有 CLI", "保留optional"))


def test_legacy_body_options_remain_exact_without_new_selection_input():
    class LegacyBodies(f.Bodies):
        supports_outcome_selection = True
        def read(self, candidate, **kwargs):
            assert kwargs == {"max_bytes": 65536, "timeout_seconds": 15}
            return super().read(candidate, **kwargs)
    result, *_ = f.run(bodies=LegacyBodies())
    assert result.rules_version == "legacy"


def test_wider_coverage_with_weaker_quality_is_not_joint_dominance():
    result, *_ = v.execute()
    broad, narrow = result.entries[0].resources
    broad = replace(broad, resource_id="broad", quality_evidence=tuple(replace(q, category="adequate") for q in broad.quality_evidence))
    narrow = replace(narrow, resource_id="focused", evidence=narrow.evidence[:1],
                     quality_evidence=tuple(replace(q, category="strong") for q in narrow.quality_evidence))
    assert ResourceResearcher._incomparable([broad, narrow])


def test_disjoint_outcome_coverage_is_incomparable_even_at_equal_quality():
    result, *_ = v.execute(tie=True)
    a, b = result.entries[0].resources
    a, b = replace(a, evidence=a.evidence[:1]), replace(b, evidence=b.evidence[1:])
    assert ResourceResearcher._incomparable([a, b])


def test_partial_github_reaches_authorized_web_fallback():
    class PartialFirst(v.Reader):
        def generate_structured(self, **kwargs):
            response = super().generate_structured(**kwargs)
            if len(self.calls) == 1:
                for row in response.payload["outcomes"][1:]:
                    row.update(status="unsupported", evidence_refs=[])
            return response

    values = f.inputs()
    p, plan, coverage, gaps = values
    budget = f.ResearchBudget()
    session = ResearchSession("partial", research_input_hash(gaps, plan, coverage, p, budget,
        project_id="project", checked_at=f.STAMP, actor_id="actor", rules_version=v.V2), budget, rules_version=v.V2)
    github = f.Search([f.candidate("https://github.com/one/tutorial")])
    web = f.Search([f.candidate("https://github.com/two/tutorial")])
    result, *_ = f.run(values, session=session, github=github, web=web, bodies=v.Bodies(), reader=PartialFirst())
    assert web.calls and result.entries[0].status == "resolved"


def test_first_required_comparison_cannot_starve_next_required_scope():
    from app.domain.planning.content_coverage import CoverageEvaluator, ReviewedContentIndex
    from app.domain.planning.resource_gaps import extract

    from backend.tests.unit.test_capability_planning import cap, plan, profile, wire

    p = profile("学习工具调用")
    frozen = plan(p, wire(p, cap(p, "llm.api", desired_depth="foundation"),
                         cap(p, "tool.calling", desired_depth="deep")))
    coverage = CoverageEvaluator().evaluate(frozen, ReviewedContentIndex("empty", (), (), ()))
    result, _, _, _, _, reader, _ = v.execute(values=(p, frozen, coverage, extract(frozen, coverage)),
                                            budget=f.ResearchBudget(max_reader_requests=2))
    scopes = [{o["outcome_id"].split(".")[0] for o in row["payload"]["must_teach"]} for row in reader.calls]
    assert scopes == [{"llm"}, {"tool"}]
    assert all(e.status == "resolved" for e in result.entries)
