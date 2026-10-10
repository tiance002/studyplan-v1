"""Scoped research regressions; public materials and Reader evidence are synthetic."""
import hashlib
from copy import deepcopy
from dataclasses import asdict, replace

import httpx
import pytest
from app.application.teaching_resource_research import ResourceResearcher
from app.core.errors import ValidationAppError
from app.core.ids import content_hash
from app.domain.planning.capabilities import (
    CapabilityPlanValidator,
    DomainVerificationEvidence,
    verification_input_hash,
)
from app.domain.planning.capability_policy import CapabilityDefinition, LearningOutcome
from app.domain.planning.content_coverage import CoverageEvaluator, ReviewedContentIndex
from app.domain.planning.research_reader import TransientBody
from app.domain.planning.resource_gaps import extract
from app.domain.planning.resource_research import ResearchSession, research_input_hash

from backend.tests.unit import test_resource_research as f
from backend.tests.unit.test_capability_planning import cap, plan, profile, wire
from backend.tests.unit.test_research_comparison_v2 import Reader

V3 = "research_chapter_v3"


@pytest.fixture(autouse=True)
def forbid_network(monkeypatch):
    import socket
    def forbidden(*_args, **_kwargs):
        raise AssertionError("Real DNS/socket forbidden in research regression fixtures")
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)


def values(*, second_depth="applied"):
    p = profile("学习API与结构化输出")
    frozen = plan(p, wire(p, cap(p, "llm.api"), cap(p, "structured.output", desired_depth=second_depth)))
    coverage = CoverageEvaluator().evaluate(frozen, ReviewedContentIndex("empty", (), (), ()))
    return p, frozen, coverage, extract(frozen, coverage)


def seven_values():
    p = profile("学习公开合成的七项目标")
    definition = CapabilityDefinition("fixture.seven", "Synthetic seven", tuple(
        LearningOutcome(f"fixture.seven.o{i}", f"Explain synthetic public objective {i}") for i in range(7)),
        (), "applied", ())
    digest = content_hash(asdict(definition))
    evidence = DomainVerificationEvidence("domain_" + content_hash({"input_hash": verification_input_hash(p),
        "source_hash": digest}), verification_input_hash(p), ("domain-source:synthetic@v1#" + digest,),
        ("Explicit synthetic fixture",), "fixture", (definition,))
    frozen = CapabilityPlanValidator().validate(wire(p, cap(p, "fixture.seven")), profile=p,
                                               verification_evidence=(evidence,))
    coverage = CoverageEvaluator().evaluate(frozen, ReviewedContentIndex("empty", (), (), ()))
    return p, frozen, coverage, extract(frozen, coverage)


class Chapters:
    supports_outcome_selection = supports_chapter_selection = True

    def __init__(self, chapters):
        self.chapters, self.calls, self.produced = chapters, [], []

    def read(self, candidate, **options):
        self.calls.append((candidate.url, deepcopy(options)))
        excluded = set(options.get("exclude_paths", ()))
        selected = next(((path, text) for path, text in self.chapters[candidate.url] if path not in excluded), None)
        if selected is None:
            return TransientBody("unread", reason="no_matching_teaching_chapter", requests=1, bytes_read=12)
        path, text = selected
        url = candidate.url + "/blob/main/" + path
        metadata = {"resource_id": "resource_" + content_hash({"url": url}), "version": "git-blob:" + "a" * 40,
            "content_hash": hashlib.sha256(text.encode()).hexdigest(), "location": path + "#L1-L1"}
        result = TransientBody("succeeded", metadata["resource_id"], url, metadata["version"],
            [{"chunk_id": "chunk_" + content_hash(metadata), **metadata, "text": text}], requests=2,
            bytes_read=len(text.encode()))
        self.produced.append(result)
        return result


class ChapterReader(Reader):
    def __init__(self, support):
        super().__init__(tie=True)
        self.support = support

    def generate_structured(self, **kwargs):
        result = super().generate_structured(**kwargs)
        supported = self.support.get(kwargs["payload"]["chunks"][0]["text"], set())
        raw = deepcopy(result.payload)
        for outcome in raw["outcomes"]:
            if outcome["outcome_id"] not in supported:
                outcome["status"], outcome["evidence_refs"] = "unsupported", []
        return replace(result, payload=raw)


def execute(input_values, *, github, bodies, reader, budget=None, session=None):
    p, frozen, coverage, gaps = input_values
    budget = budget or f.ResearchBudget(max_reader_requests=6, max_body_bytes=393216,
        max_total_requests=24, max_output_tokens=6144, max_cost_micros=200000)
    session = session or ResearchSession("chapter-v3", research_input_hash(gaps, frozen, coverage, p, budget,
        project_id="project", checked_at=f.STAMP, actor_id="actor", rules_version=V3), budget, rules_version=V3)
    researcher = ResourceResearcher(github=github, web=f.Search([]), body_reader=bodies, llm=reader,
                                  allow_fixture_domains=True)
    result = researcher.research(gaps, plan=frozen, coverage=coverage, profile=p, session=session,
        scope=f.SCOPE, project_id="project", checked_at=f.STAMP)
    return result, session, researcher


def test_negative_chapter_does_not_eliminate_unread_sibling_and_replay_is_exact():
    v = values()
    api = {o.outcome_id for o in v[1].learning_outcomes if o.outcome_id.startswith("llm.api.")}
    structured = {o.outcome_id for o in v[1].learning_outcomes if o.outcome_id.startswith("structured.output.")}
    url = "https://github.com/synthetic/book"
    bodies = Chapters({url: [("api.md", "Synthetic API explanation"), ("structured.md", "Synthetic structured explanation")]})
    reader = ChapterReader({"Synthetic API explanation": api, "Synthetic structured explanation": structured})
    result, session, researcher = execute(v, github=f.Search([f.candidate(url)]), bodies=bodies, reader=reader)
    assert all(e.status == "resolved" for e in result.entries)
    assert any(call[1].get("exclude_paths") == ("api.md",) for call in bodies.calls)
    # A later comparison may review a sibling's previously unasked scope.
    assert len(reader.calls) == 3
    before = len(bodies.calls), len(reader.calls)
    restored = ResearchSession.restore(session.snapshot())
    replay = researcher.research(v[3], plan=v[1], coverage=v[2], profile=v[0], session=restored,
                                scope=f.SCOPE, project_id="project", checked_at=f.STAMP)
    assert replay.result_hash == result.result_hash and before == (len(bodies.calls), len(reader.calls))
    assert "Synthetic API explanation" not in repr(session.snapshot().to_payload())


def test_seven_outcomes_progress_under_six_request_bound_on_same_chapter():
    v = seven_values()
    url, text = "https://github.com/synthetic/seven", "Synthetic seven objective chapter"
    reader = ChapterReader({text: {o.outcome_id for o in v[1].learning_outcomes}})
    bodies = Chapters({url: [("seven.md", text)]})
    result, session, _ = execute(v, github=f.Search([f.candidate(url)]), bodies=bodies, reader=reader)
    assert result.entries[0].status == "resolved"
    assert [len(c["payload"]["must_teach"]) for c in reader.calls] == [6, 1]
    assert all(not c[1].get("exclude_paths") for c in bodies.calls[:2])
    assert session.usage["reader_requests"] == 2


def test_late_joint_evidence_refreshes_earlier_entry_and_retains_attempt_reason():
    v = values()
    urls = ["https://github.com/synthetic/" + x for x in ("a", "b0", "b1")]
    class Search(f.Search):
        def find(self, query):
            self.calls.append(query)
            return [f.candidate(urls[0])] if query.node_keys[0].startswith("llm.api.") else [f.candidate(u) for u in urls[1:]]
    bodies = Chapters({u: [("chapter.md", "Synthetic " + u.rsplit("/", 1)[-1] + " explanation")] for u in urls})
    reader = ChapterReader({"Synthetic b1 explanation": {o.outcome_id for o in v[1].learning_outcomes}})
    result, _, _ = execute(v, github=Search(), bodies=bodies, reader=reader)
    assert all(e.status == "resolved" for e in result.entries)
    assert "outcomes_unresolved" in result.entries[0].comparison_reasons
    assert result.entries[0].reason_codes == ()
    assert all("/b1/" in r.url for e in result.entries for r in e.resources)


def test_joint_evidence_at_wrong_depth_never_fills_other_entry():
    v = values(second_depth="deep")
    url, text = "https://github.com/synthetic/depth", "Synthetic shallow only"
    bodies = Chapters({url: [("chapter.md", text)]})
    reader = ChapterReader({text: {o.outcome_id for o in v[1].learning_outcomes if o.outcome_id.startswith("llm.api.")}})
    result, _, _ = execute(v, github=f.Search([f.candidate(url)]), bodies=bodies, reader=reader)
    assert result.entries[0].status == "resolved" and result.entries[1].status == "unresolved"
    assert all(r.evidence[0].outcome_id.startswith("llm.api.") for r in result.entries[0].resources)


def test_unknown_blocks_v3_and_never_retries():
    v = values()
    url = "https://github.com/synthetic/unknown"
    bodies = Chapters({url: [("chapter.md", "Synthetic unknown response")]})
    reader = Reader()
    reader.mode = "unknown"
    result, session, researcher = execute(v, github=f.Search([f.candidate(url)]), bodies=bodies, reader=reader)
    assert session.blocked and len(reader.calls) == 1
    replay = researcher.research(v[3], plan=v[1], coverage=v[2], profile=v[0],
        session=ResearchSession.restore(session.snapshot()), scope=f.SCOPE, project_id="project", checked_at=f.STAMP)
    assert replay.result_hash == result.result_hash and len(reader.calls) == 1


def test_seventh_outcome_is_asked_even_when_first_six_are_unsupported():
    v = seven_values()
    url, text = "https://github.com/synthetic/seven-negative", "Synthetic seventh support"
    reader = ChapterReader({text: {"fixture.seven.o6"}})
    bodies = Chapters({url: [("seven.md", text)]})
    result, _, _ = execute(v, github=f.Search([f.candidate(url)]), bodies=bodies, reader=reader)
    assert result.entries[0].status == "partial"
    assert {o.outcome_id for o in result.entries[0].unresolved_outcomes} == {f"fixture.seven.o{i}" for i in range(6)}
    assert [len(c["payload"]["must_teach"]) for c in reader.calls] == [6, 1]


def test_v3_marker_is_opt_in_and_old_hash_payloads_are_unchanged():
    from app.domain.planning.v2_runtime import manifest_intact, research_rules_version

    from backend.tests.unit.test_product_semantics_manifest import manifest
    old = manifest(product_semantics="planning-v2-product-v2")
    assert manifest(product_semantics="planning-v2-product-v2", research_rules_version=None) == old
    assert research_rules_version(old) == "research_comparison_v2"
    new = manifest(product_semantics="planning-v2-product-v2", research_rules_version=V3)
    assert new["manifest_hash"] != old["manifest_hash"] and manifest_intact(new)
    with pytest.raises(ValidationAppError):
        manifest(research_rules_version=V3)
    tampered = deepcopy(new)
    tampered["research_rules_version"] = "unknown"
    tampered["manifest_hash"] = content_hash({k: v for k, v in tampered.items() if k != "manifest_hash"})
    assert not manifest_intact(tampered)
    v = f.inputs()
    budget = f.ResearchBudget()
    historical = ResearchSession("old", research_input_hash(v[3], v[1], v[2], v[0], budget,
        project_id="project", checked_at=f.STAMP, actor_id="actor", rules_version="research_comparison_v2"),
        budget, rules_version="research_comparison_v2")
    payload = historical.snapshot().to_payload()
    assert "chapter_reviews" not in payload and "unread_chapters" not in payload


@pytest.mark.parametrize("tamper", ["version", "depth"])
def test_completed_replay_rejects_wrong_source_version_and_wrong_depth(tamper):
    v = values()
    url, text = "https://github.com/synthetic/binding", "Synthetic binding example"
    bodies = Chapters({url: [("chapter.md", text)]})
    reader = ChapterReader({text: {o.outcome_id for o in v[1].learning_outcomes}})
    _result, session, researcher = execute(v, github=f.Search([f.candidate(url)]), bodies=bodies, reader=reader)
    restored = ResearchSession.restore(session.snapshot())
    key = next(iter(restored.inspected))
    if tamper == "version":
        restored.inspected[key] = tuple(replace(r, version="git-blob:" + "b" * 40) for r in restored.inspected[key])
    else:
        restored.inspected[key.replace("#depth:applied", "#depth:deep")] = restored.inspected.pop(key)
    before = len(bodies.calls), len(reader.calls)
    with pytest.raises(ValidationAppError):
        researcher.research(v[3], plan=v[1], coverage=v[2], profile=v[0], session=restored,
                           scope=f.SCOPE, project_id="project", checked_at=f.STAMP)
    assert before == (len(bodies.calls), len(reader.calls))


def test_final_aggregation_keeps_refusal_comparison_insufficient_with_two_supported_resources():
    v = f.inputs()
    urls = ["https://github.com/synthetic/" + x for x in ("bad", "good0", "good1")]
    bodies = Chapters({u: [("chapter.md", "Synthetic " + u.rsplit("/", 1)[-1] + " example")] for u in urls})
    supported = {o.outcome_id for o in v[1].learning_outcomes}
    reader = ChapterReader({"Synthetic good0 example": supported, "Synthetic good1 example": supported})
    result, _, _ = execute(v, github=f.Search([f.candidate(u) for u in urls]), bodies=bodies, reader=reader)
    assert all(e.status == "resolved" and len(e.resources) == 2 for e in result.entries)
    assert all(e.comparison_status == "insufficient" for e in result.entries)
    assert any("body_unread" in e.comparison_reasons for e in result.entries)


@pytest.mark.parametrize("capacity_refusal", [False, True])
def test_actual_adapters_chinese_chapter_negative_then_joint_positive_reaches_curriculum(capacity_refusal):
    from app.domain.planning.curriculum import prepare_curriculum
    from app.infrastructure.resources.github import GitHubResourceIndex
    from app.infrastructure.resources.teaching_body import GitHubTeachingBody

    from backend.tests.unit.test_github_resource_index import repositories
    from backend.tests.unit.test_teaching_body import file_payload, reply
    v = values()
    texts = {"docs/04-结构化输出.md": "X" * 16385 if capacity_refusal else "Synthetic insufficient chapter",
             "docs/api.md": "Synthetic joint API and structured worked example"}
    readme = "[Contributing](CONTRIBUTING.md)\n[模型结构化输出](docs/04-结构化输出.md)\n[API](docs/api.md)"
    requests = []
    def respond(request):
        requests.append(request.url.path)
        if request.url.path == "/search/repositories":
            return reply(repositories([("course", "Synthetic Chinese curriculum")]))
        if request.url.path.endswith("/readme"):
            return reply(file_payload("README.md", readme.encode()))
        path = request.url.path.split("/contents/", 1)[1]
        assert path in texts
        return reply(file_payload(path, texts[path].encode()))
    transport = httpx.MockTransport(respond)
    reader = ChapterReader({texts["docs/api.md"]: {o.outcome_id for o in v[1].learning_outcomes}})
    body = GitHubTeachingBody(transport=transport)
    result, session, researcher = execute(v, github=GitHubResourceIndex(transport=transport), bodies=body, reader=reader)
    assert all(e.status == "resolved" for e in result.entries)
    assert requests.index("/repos/author/course/contents/docs/04-结构化输出.md") < requests.index("/repos/author/course/contents/docs/api.md")
    assert len(reader.calls) == (1 if capacity_refusal else 2)
    assert ("body_unread" if capacity_refusal else "outcomes_unresolved") in result.entries[0].comparison_reasons
    assert not session.blocked and session.usage["reader_requests"] == len(reader.calls)
    context = prepare_curriculum(v[0], v[1], v[2], result, ReviewedContentIndex("empty", (), (), ()), semantics_version=2)
    assert all(not c["unavailable_outcomes"] for c in context.to_payload()["capabilities"])
    assert context.to_payload()["sources"]["gap_set_hash"] == v[3].result_hash
    before = len(requests), len(reader.calls)
    replay = researcher.research(v[3], plan=v[1], coverage=v[2], profile=v[0],
        session=ResearchSession.restore(session.snapshot()), scope=f.SCOPE, project_id="project", checked_at=f.STAMP)
    assert replay.result_hash == result.result_hash and before == (len(requests), len(reader.calls))
