"""Bounded curriculum composition on the caller's existing research session."""
import re
from dataclasses import replace

from app.core.errors import ValidationAppError
from app.core.ids import content_hash
from app.domain.enums import PreferenceScope
from app.domain.planning.constraint_adaptation import composition_dispatch_allowed
from app.domain.planning.curriculum import (
    CURRICULUM_OUTPUT_CAP,
    CURRICULUM_PURPOSE,
    CaseFinding,
    CurriculumContext,
    ProjectCase,
    curriculum_schema,
    record_case_findings,
    valid_curriculum_input,
    validate_curriculum_output,
)
from app.domain.planning.resource_research import (
    METRICS,
    ResearchBudget,
    ResearchSession,
    ResourceResearchResult,
)
from app.domain.resources.models import ResourcePreference, ResourceRecord, UnavailableResult
from app.domain.workspace.models import AuthContext
from app.ports.llm import LLMFailure, LLMNotDispatchedError, LLMResult
from app.ports.resource_index import ResourceInspectionQuery, ResourceInspectionResult, ResourceQuery


def _failure(code, *, unknown=False):
    return LLMFailure(code, "Curriculum composition stopped", dispatch_unknown=unknown)


def _reject(field):
    raise ValidationAppError("Curriculum composition input rejected", field=field)


class CurriculumComposer:
    def __init__(self, llm, *, project_index=None):
        self.llm = llm
        self.project_index = project_index
        # In-process accidental re-entry protection only. Durable attempts and
        # successful receipts belong to Item7, not to this coordinator.
        self._composed = set()

    def compose(self, context, *, session, scope, project_id, attempt_id,
                max_output_tokens=8192):
        if type(scope) is not AuthContext:
            _reject("authorization")
        scope.require_project(project_id)
        if (type(context) is not CurriculumContext or type(session) is not ResearchSession
                or type(session.budget) is not ResearchBudget):
            _reject("context_session")
        payload = context.to_payload()
        schema_name = curriculum_schema(payload)
        if not valid_curriculum_input(payload, schema_name, domain_approvals=context._domain_approvals,
                                      allow_fixture_domains=context._allow_fixture_domains):
            _reject("context")
        if not composition_dispatch_allowed(payload["constraints"]):
            return _failure("curriculum_constraints_pending")
        if (type(context.research) is not ResourceResearchResult or replace(context.research) != context.research
                or context.research.result_hash != payload["sources"]["research_hash"]
                or type(session.completed) is not ResourceResearchResult or replace(session.completed) != session.completed
                or session.input_hash != context.expected_session_hash(session.budget, actor_id=scope.actor_id, project_id=project_id)
                or session.completed.result_hash != context.research.result_hash):
            _reject("session_ancestry")
        if (set(session.usage) != set(METRICS) or any(type(v) is not int or v < 0 for v in session.usage.values())
                or type(session.blocked) is not bool or not isinstance(session.run_id, str) or not session.run_id.strip()):
            _reject("session_state")
        if not session.blocked and any(v > getattr(session.budget, "max_" + k) for k, v in session.usage.items()):
            _reject("session_usage")
        if any(session.usage.get(metric, -1) < amount for metric, amount in context.research.budget_usage):
            _reject("session_usage_rollback")
        if not isinstance(attempt_id, str) or not attempt_id.strip() or len(attempt_id) > 200:
            _reject("attempt_id")
        identity = (session.run_id, context.input_hash)
        if session.blocked or session.snapshot().pending_count or identity in self._composed:
            return _failure("curriculum_session_blocked")
        if type(max_output_tokens) is not int or not 1 <= max_output_tokens <= CURRICULUM_OUTPUT_CAP:
            return _failure("curriculum_budget_invalid")
        options = getattr(self.llm, "request_options", None)
        try:
            cap = options(CURRICULUM_PURPOSE).get("max_tokens") if callable(options) else max_output_tokens
        except Exception:
            return _failure("curriculum_budget_invalid")
        if type(cap) is not int or not 1 <= cap <= CURRICULUM_OUTPUT_CAP:
            return _failure("curriculum_budget_invalid")
        reservation = session.reserve("curriculum", total_requests=1, output_tokens=cap,
                                      cost_micros=session.budget.reader_cost_micros)
        if reservation is None:
            return _failure("curriculum_budget_exhausted")
        self._composed.add(identity)
        try:
            response = self.llm.generate_structured(purpose=CURRICULUM_PURPOSE, schema_name=schema_name,
                payload=payload, run_id=session.run_id, attempt_id=attempt_id)
        except LLMNotDispatchedError:
            session.settle(reservation, total_requests=0, output_tokens=0, cost_micros=0)
            session.blocked = True
            return _failure("curriculum_not_dispatched")
        except Exception:
            self._keep_unknown(session, {}, {})
            return _failure("curriculum_dispatch_unknown", unknown=True)
        if isinstance(response, LLMFailure) and response.dispatch_unknown:
            self._keep_unknown(session, {"output_tokens": response.output_tokens}, {"output_tokens": cap})
            return response
        if (isinstance(response, LLMFailure) and response.details.get("dispatched") is False
                and response.output_tokens in (None, 0) and response.input_tokens in (None, 0)):
            session.settle(reservation, total_requests=0, output_tokens=0, cost_micros=0)
            session.blocked = True
            return response
        try:
            session.settle(reservation, total_requests=1, output_tokens=getattr(response, "output_tokens", None),
                           cost_micros=getattr(response, "cost_micros", None))
        except ValidationAppError:
            session.blocked = True
            return response if isinstance(response, LLMFailure) else _failure("curriculum_budget_exceeded")
        if isinstance(response, LLMFailure):
            session.blocked = True
            return response
        if type(response) is not LLMResult or response.finish_reason == "length":
            session.blocked = True
            return _failure("curriculum_truncated" if isinstance(response, LLMResult) else "curriculum_response_invalid")
        try:
            curriculum = validate_curriculum_output(response.payload, payload, domain_approvals=context._domain_approvals,
                                                    allow_fixture_domains=context._allow_fixture_domains)
        except (ValidationAppError, TypeError, ValueError, KeyError):
            session.blocked = True
            return _failure("curriculum_output_invalid")
        findings, inspected = [], {}
        for requirement in curriculum.project_study_requirements:
            if requirement["selected_case_ref"]:
                continue
            available = any(case["qualification"] == "bounded_reviewed" and case["mode"] == requirement["mode"]
                and set(requirement["outcome_refs"]) <= set(case["outcome_refs"]) for case in payload["project_cases"])
            if available:
                # Qualified cases remain in the frozen input. Candidate
                # findings cannot promote them or select one for the user.
                cases, reasons = (), ("case_selection_pending",)
            else:
                cases, reasons = self._find_case(requirement, context, session, scope, project_id, inspected)
            findings.append(CaseFinding(requirement["requirement_id"], requirement["requirement_hash"], cases, reasons))
        return record_case_findings(curriculum, tuple(findings)) if findings else curriculum

    def _find_case(self, requirement, context, session, scope, project_id, inspected):
        if session.blocked:
            return (), ("research_stopped",)
        refs = tuple(requirement["outcome_refs"])
        public = context.public_outcome_texts
        if any(ref not in public for ref in refs):
            return (), ("public_descriptor_unapproved",)
        if self.project_index is None:
            return (), ("case_index_unavailable",)
        query = " ".join(public[ref] for ref in refs)
        if len(query) > 500:
            return (), ("public_query_too_large",)
        preference = ResourcePreference(PreferenceScope.PROJECT, project_id)
        reservation = session.reserve("case-search", searches=1, total_requests=1,
                                      cost_micros=session.budget.search_cost_micros)
        if reservation is None:
            return (), ("budget_exhausted",)
        try:
            candidates = self.project_index.find(ResourceQuery(scope, refs, preference, limit=5,
                extra={"project_id": project_id, "query": query}))
        except Exception:
            session.mark_unknown()
            return (), ("search_unknown",)
        if isinstance(candidates, UnavailableResult):
            # The old search port cannot prove dispatch status or cost. Never
            # classify unknown from its free-form (possibly private) text.
            session.mark_unknown()
            return (), ("search_unclassified",)
        session.settle(reservation, searches=1, total_requests=1)
        if type(candidates) is not list or len(candidates) > 5:
            return (), ("case_candidate_invalid",)
        candidate = next((c for c in candidates if type(c) is ResourceRecord and c.project_id == project_id
            and isinstance(c.url, str) and re.fullmatch(r"https://github\.com/[A-Za-z0-9_-][A-Za-z0-9_.-]{0,99}/[A-Za-z0-9_-][A-Za-z0-9_.-]{0,99}", c.url)), None)
        if candidate is None:
            return (), ("no_case_candidate",)
        case = ProjectCase("case_" + content_hash({"url": candidate.url}), candidate.url, "unknown",
            requirement["mode"], refs, limitations=("Candidate metadata only; behavior and source slice are not reviewed",))
        if candidate.url in inspected:
            return (case,), inspected[candidate.url]
        inspect = getattr(self.project_index, "inspect", None)
        if not callable(inspect):
            return (case,), ("inspection_unavailable", "candidate_only")
        reservation = session.reserve("case-inspect", candidates=1, total_requests=3, body_bytes=262144,
                                      cost_micros=3 * session.budget.search_cost_micros)
        if reservation is None:
            return (), ("budget_exhausted",)
        owner, name = candidate.url.removeprefix("https://github.com/").split("/")
        # No private random ResourceRecord identity, snippet, title, branch or
        # notes cross this boundary. Existing GitHub inspect accepts this shape.
        snapshot = {"resource_id": "resource_" + content_hash({"url": candidate.url}), "project_id": project_id,
            "url": candidate.url, "title": "Project case candidate",
            "discovery": {"source": "github", "repo": {"owner": owner, "name": name}}}
        try:
            result = inspect(ResourceInspectionQuery(scope, snapshot, query, preference))
        except Exception:
            self._inspection_unknown(session)
            return (case,), ("inspection_unknown", "candidate_only")
        if type(result) is not ResourceInspectionResult or result.status not in {"succeeded", "failed"}:
            self._inspection_unknown(session, result)
            return (case,), ("inspection_unknown", "candidate_only")
        receipts = result.receipts
        if (type(receipts) is not list or not receipts or any(type(r) is not dict
                or r.get("status") not in {"succeeded", "failed", "not_dispatched"}
                or type(r.get("bytes")) is not int or r["bytes"] < 0 for r in receipts)):
            self._inspection_unknown(session, result)
            return (case,), ("inspection_unknown", "candidate_only")
        requests = sum(r["status"] != "not_dispatched" for r in receipts)
        try:
            session.settle(reservation, candidates=1, total_requests=requests,
                body_bytes=sum(r["bytes"] for r in receipts), cost_micros=0 if requests == 0 else None)
        except ValidationAppError:
            return (case,), ("budget_exceeded", "candidate_only")
        reasons = ("candidate_only",) if result.status == "succeeded" else ("inspection_failed", "candidate_only")
        inspected[candidate.url] = reasons
        return (case,), reasons

    @staticmethod
    def _inspection_unknown(session, result=None):
        # Keep this call's pending reservation and all unknown worst debits.
        # A finite receipt can nevertheless prove a larger observed lower
        # bound. Only the excess over THIS call's reservation is added; prior
        # usage must not disappear. This branch returns without settlement.
        # Item7 reconciliation must recognize this raised lower bound rather
        # than applying it a second time.
        if type(result) is ResourceInspectionResult and type(result.receipts) is list:
            byte_lower_bound = sum(r["bytes"] for r in result.receipts if type(r) is dict
                and type(r.get("bytes")) is int and 0 <= r["bytes"] <= 10**12)
            request_lower_bound = sum(type(r) is dict and r.get("status") in
                {"succeeded", "failed", "dispatched", "reconciliation_required"} for r in result.receipts)
            CurriculumComposer._keep_unknown(session,
                {"body_bytes": byte_lower_bound, "total_requests": request_lower_bound},
                {"body_bytes": 262144, "total_requests": 3})
            return
        CurriculumComposer._keep_unknown(session, {}, {})

    @staticmethod
    def _keep_unknown(session, observed, reserved):
        for metric, value in observed.items():
            if type(value) is int and 0 <= value <= 10**12:
                session.usage[metric] += max(0, value - reserved[metric])
        session.unknown_measurement = True
        session.mark_unknown()
