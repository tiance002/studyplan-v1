"""Offline coordinator boundaries; fixtures do not prove curriculum semantics."""
from copy import deepcopy
from dataclasses import replace

import pytest
from app.application.curriculum_composition import CurriculumComposer
from app.core.errors import ForbiddenError, ValidationAppError
from app.domain.planning.content_coverage import CoverageEvaluator, ReviewedContentIndex
from app.domain.planning.curriculum import ProjectCase, prepare_curriculum
from app.domain.planning.resource_gaps import extract
from app.domain.planning.resource_research import ResearchBudget, ResearchSession
from app.domain.resources.models import UnavailableResult
from app.ports.llm import LLMFailure, LLMNotDispatchedError, LLMResult
from app.ports.resource_index import ResourceInspectionResult

from backend.tests.unit.test_capability_planning import cap, plan, profile, wire
from backend.tests.unit.test_curriculum import context, output
from backend.tests.unit.test_resource_research import SCOPE, candidate, run


class Model:
    def __init__(self, response=None, *, cap=8192):
        self.response, self.cap, self.calls = response, cap, []

    def request_options(self, purpose):
        return {"max_tokens": self.cap}

    def generate_structured(self, **kwargs):
        self.calls.append(deepcopy(kwargs))
        if isinstance(self.response, Exception):
            raise self.response
        if self.response is not None:
            return self.response
        raise AssertionError("An explicit offline fixture response is required")


class Projects:
    def __init__(self, found=None, inspected=None):
        self.found = [candidate()] if found is None else found
        self.inspected = inspected or ResourceInspectionResult("succeeded", {"discovery": {}},
            [{"status": "succeeded", "bytes": 40}])
        self.find_calls, self.inspect_calls = [], []

    def find(self, query):
        self.find_calls.append(query)
        if isinstance(self.found, Exception):
            raise self.found
        return self.found

    def inspect(self, query):
        self.inspect_calls.append(query)
        if isinstance(self.inspected, Exception):
            raise self.inspected
        return self.inspected


def setup(*, project_study=False, budget=None, response=None, cap=8192, ctx=None):
    ctx = ctx or context()
    budget = budget or ResearchBudget(max_output_tokens=20000, max_total_requests=30, max_body_bytes=524288)
    session = ResearchSession("run", ctx.expected_session_hash(budget, actor_id=SCOPE.actor_id, project_id="project"), budget)
    # A completed Item5 result is the ancestry boundary; no research replay.
    session.completed = ctx.research
    session.usage.update(dict(ctx.to_payload()["sources"]["research_budget_usage"]))
    model = Model(response or LLMResult(output(ctx, project_study=project_study), "offline", "fixture",
                                      output_tokens=20, cost_micros=7), cap=cap)
    return ctx, session, model


def compose(ctx, session, model, projects=None, **kwargs):
    return CurriculumComposer(model, project_index=projects).compose(ctx, session=session, scope=SCOPE,
        project_id="project", attempt_id="curriculum-one", **kwargs)


def test_single_call_same_session_and_no_project_study_means_zero_case_calls():
    ctx, session, model = setup()
    projects = Projects()
    before = dict(session.usage)
    result = compose(ctx, session, model, projects)
    assert result.input_hash == ctx.input_hash
    assert len(model.calls) == 1 and not projects.find_calls and not projects.inspect_calls
    call = model.calls[0]
    assert call["payload"] == ctx.to_payload() and call["run_id"] == session.run_id
    assert call["purpose"] == "planning.curriculum_composition" and call["schema_name"] == "CurriculumPlanV1"
    assert session.usage["total_requests"] == before["total_requests"] + 1
    assert session.usage["reader_requests"] == before["reader_requests"]


@pytest.mark.parametrize("change", ["input_hash", "completed", "actor", "project"])
def test_invalid_ancestry_rejected_before_dispatch(change):
    ctx, session, model = setup()
    scope, project_id = SCOPE, "project"
    if change == "input_hash":
        session.input_hash = "f" * 64
    elif change == "completed":
        session.completed = None
    elif change == "actor":
        scope = replace(SCOPE, actor_id="other")
    else:
        project_id = "other"
    with pytest.raises((ValidationAppError, ForbiddenError)):
        CurriculumComposer(model).compose(ctx, session=session, scope=scope, project_id=project_id, attempt_id="one")
    assert not model.calls


@pytest.mark.parametrize("cap,budget_cap", [(8192, 4096), (8193, 20000), (0, 20000)])
def test_effective_provider_cap_cannot_be_under_reserved(cap, budget_cap):
    ctx, session, model = setup(cap=cap, budget=ResearchBudget(max_output_tokens=budget_cap))
    result = compose(ctx, session, model, max_output_tokens=1)
    assert isinstance(result, LLMFailure) and not model.calls


def test_unknown_keeps_pending_reservation_and_restores_blocked():
    ctx, session, model = setup(response=LLMFailure("unknown", "fixed", dispatch_unknown=True))
    result = compose(ctx, session, model)
    assert result.dispatch_unknown and session.blocked and session.snapshot().pending_count == 1
    assert session.usage["output_tokens"] >= 8192 and session.usage["cost_micros"] >= session.budget.reader_cost_micros
    assert ResearchSession.restore(session.snapshot()).blocked


def test_unknown_model_retains_pending_and_accounts_observed_output_overrun():
    response = LLMFailure("unknown", "fixed", dispatch_unknown=True, output_tokens=9000)
    ctx, session, model = setup(response=response)
    before = dict(session.usage)
    assert compose(ctx, session, model) is response
    assert session.usage["output_tokens"] == before["output_tokens"] + max(8192, 9000)
    assert session.usage["cost_micros"] == before["cost_micros"] + session.budget.reader_cost_micros
    assert session.snapshot().pending_count == 1 and session.unknown_measurement and session.blocked
    restored = ResearchSession.restore(session.snapshot())
    assert isinstance(compose(ctx, restored, model), LLMFailure) and len(model.calls) == 1


@pytest.mark.parametrize("response", [LLMFailure("invalid_json", "fixed", output_tokens=12),
    LLMFailure("truncated", "fixed", output_tokens=12), LLMFailure("rejected", "fixed", output_tokens=12)])
def test_known_failure_class_preserved_settled_and_no_retry(response):
    ctx, session, model = setup(response=response)
    before = session.usage["output_tokens"]
    assert compose(ctx, session, model) is response
    assert session.blocked and not session.snapshot().pending_count and len(model.calls) == 1
    assert session.usage["output_tokens"] == before + 12 and session.unknown_measurement


def test_proven_not_dispatched_releases_reserve():
    ctx, session, model = setup(response=LLMNotDispatchedError("offline"))
    before = dict(session.usage)
    result = compose(ctx, session, model)
    assert result.error_class == "curriculum_not_dispatched" and session.usage == before


def test_unknown_usage_keeps_worst_cost_and_output():
    ctx, session, model = setup()
    model.response = LLMResult(output(ctx), "offline", "fixture")
    before = dict(session.usage)
    compose(ctx, session, model)
    assert session.usage["output_tokens"] == before["output_tokens"] + 8192
    assert session.usage["cost_micros"] == before["cost_micros"] + session.budget.reader_cost_micros
    assert session.unknown_measurement


def test_invalid_output_and_observed_overrun_stop_without_case_calls():
    ctx, session, model = setup(response=LLMResult({}, "offline", "fixture", output_tokens=9000))
    projects = Projects()
    result = compose(ctx, session, model, projects)
    assert isinstance(result, LLMFailure) and session.blocked and session.usage["output_tokens"] >= 9000
    assert not projects.find_calls and not projects.inspect_calls


def test_project_search_inspect_is_bounded_private_safe_and_cannot_qualify():
    ctx, session, model = setup(project_study=True)
    projects = Projects()
    reader_requests = session.usage["reader_requests"]
    result = compose(ctx, session, model, projects)
    assert len(model.calls) == len(projects.find_calls) == len(projects.inspect_calls) == 1
    assert result.status == "incomplete"
    query = projects.find_calls[0]
    assert query.extra["query"] == " ".join(ctx.public_outcome_texts[o] for o in query.node_keys)
    snapshot = projects.inspect_calls[0].candidate
    assert snapshot["title"] == "Project case candidate"
    assert set(snapshot["discovery"]) == {"source", "repo"}
    assert snapshot["discovery"]["repo"] == {"owner": "demo", "name": "tutorial"}
    assert session.usage["reader_requests"] == reader_requests and not session.snapshot().pending_count
    finding = result.to_payload()["case_findings"][0]
    assert finding["candidates"][0]["qualification"] == "reviewed_candidate"
    assert "discovery" not in str(finding) and "教程" not in str(finding)


@pytest.mark.parametrize("found,reason", [([], "no_case_candidate"), (UnavailableResult("private"), "search_unclassified")])
def test_empty_or_untyped_unavailable_keeps_unresolved(found, reason):
    ctx, session, model = setup(project_study=True)
    projects = Projects(found=found)
    result = compose(ctx, session, model, projects)
    assert result.status == "incomplete" and not projects.inspect_calls
    assert reason in result.to_payload()["case_findings"][0]["reason_codes"]
    assert session.blocked == isinstance(found, UnavailableResult)


def test_inspection_unknown_blocks_whole_shared_run():
    ctx, session, model = setup(project_study=True)
    projects = Projects(inspected=ResourceInspectionResult("reconciliation_required", None, []))
    result = compose(ctx, session, model, projects)
    assert result.status == "incomplete" and session.blocked and session.snapshot().pending_count == 1


def test_observed_inspection_bytes_overrun_is_recorded_and_blocks():
    ctx, session, model = setup(project_study=True)
    projects = Projects(inspected=ResourceInspectionResult("succeeded", {"discovery": {}},
        [{"status": "succeeded", "bytes": 262145}]))
    before = session.usage["body_bytes"]
    result = compose(ctx, session, model, projects)
    assert result.status == "incomplete" and session.blocked
    assert session.usage["body_bytes"] == before + 262145


def test_unknown_inspection_keeps_pending_and_accounts_observed_overrun_lower_bound():
    ctx, session, model = setup(project_study=True)
    projects = Projects(inspected=ResourceInspectionResult("reconciliation_required", None,
        [{"status": "reconciliation_required", "bytes": 262145}]))
    before = session.usage["body_bytes"]
    result = compose(ctx, session, model, projects)
    assert result.status == "incomplete" and session.blocked and session.snapshot().pending_count == 1
    assert session.usage["body_bytes"] == before + max(262144, 262145) and session.unknown_measurement
    restored = ResearchSession.restore(session.snapshot())
    assert restored.blocked and restored.usage["body_bytes"] == session.usage["body_bytes"]
    assert isinstance(compose(ctx, restored, model, projects), LLMFailure)
    assert len(model.calls) == len(projects.find_calls) == len(projects.inspect_calls) == 1


def test_no_index_preserves_explicit_unresolved_reason():
    ctx, session, model = setup(project_study=True)
    result = compose(ctx, session, model)
    assert "case_index_unavailable" in result.to_payload()["case_findings"][0]["reason_codes"]


def test_existing_qualified_case_with_outcome_superset_waits_for_selection_without_search():
    p = profile("学习MCP")
    frozen = plan(p, wire(p, cap(p, "mcp")))
    index = ReviewedContentIndex("empty", (), (), ())
    coverage = CoverageEvaluator().evaluate(frozen, index)
    research, *_ = run((p, frozen, coverage, extract(frozen, coverage)))
    outcomes = tuple(o.outcome_id for o in frozen.learning_capabilities[0].learning_outcomes)
    case = ProjectCase("case_reviewed_fixture", "https://github.com/demo/reviewed", "fixture-v1", "slices", outcomes,
        (("fixture:bounded-behavior", "a" * 64),), "bounded_reviewed", ("Synthetic bounded review",))
    ctx = prepare_curriculum(p, frozen, coverage, research, index, project_cases=(case,))
    raw = output(ctx, project_study=True)
    raw["project_study_requirements"][0]["outcome_refs"] = list(outcomes[:-1])
    ctx, session, model = setup(ctx=ctx, response=LLMResult(raw, "offline", "fixture", output_tokens=20))
    projects = Projects()
    result = compose(ctx, session, model, projects)
    assert result.status == "incomplete" and not projects.find_calls and not projects.inspect_calls
    finding = result.to_payload()["case_findings"][0]
    assert finding["candidates"] == [] and finding["reason_codes"] == ["case_selection_pending"]
    assert result.to_payload()["project_study_requirements"][0]["selected_case_ref"] is None
    assert len(model.calls) == 1


def test_candidate_from_other_project_cannot_be_inspected():
    ctx, session, model = setup(project_study=True)
    wrong = candidate()
    wrong.project_id = "other"
    projects = Projects(found=[wrong])
    result = compose(ctx, session, model, projects)
    assert result.status == "incomplete" and not projects.inspect_calls


def test_inspection_budget_insufficient_does_not_dispatch_or_create_budget():
    budget = ResearchBudget(max_output_tokens=20000, max_body_bytes=100)
    ctx, session, model = setup(project_study=True, budget=budget)
    projects = Projects()
    result = compose(ctx, session, model, projects)
    assert result.status == "incomplete" and not projects.inspect_calls and session.budget is budget
    assert "budget_exhausted" in result.to_payload()["case_findings"][0]["reason_codes"]


def test_existing_pending_session_cannot_start_composition():
    ctx, session, model = setup()
    session.reserve("old-dispatch", total_requests=1)
    assert isinstance(compose(ctx, session, model), LLMFailure) and not model.calls


def test_same_composer_does_not_reissue_same_context():
    ctx, session, model = setup()
    composer = CurriculumComposer(model)
    first = composer.compose(ctx, session=session, scope=SCOPE, project_id="project", attempt_id="one")
    second = composer.compose(ctx, session=session, scope=SCOPE, project_id="project", attempt_id="two")
    assert first.input_hash == ctx.input_hash and isinstance(second, LLMFailure) and len(model.calls) == 1
