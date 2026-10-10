"""One bounded offline-testable research coordinator, without runtime wiring."""
import re
from dataclasses import asdict, replace
from datetime import datetime
from urllib.parse import unquote, urlsplit

from app.core.errors import ValidationAppError
from app.core.ids import content_hash
from app.domain.enums import PreferenceScope
from app.domain.planning.capabilities import CAPABILITY_SCHEMA, validate_capability_planning_input
from app.domain.planning.capability_policy import CAPABILITY_POLICY
from app.domain.planning.constraint_adaptation import research_constraint_policy, research_permissions
from app.domain.planning.content_coverage import _qualified_mappings
from app.domain.planning.domain_verification import public_outcomes, reader_authority
from app.domain.planning.research_reader import (
    READER_OUTPUT_CAP,
    READER_PURPOSE,
    READER_SCHEMA,
    READER_SCHEMA_V2,
    TransientBody,
    validate_reader_input,
    validate_reader_output,
)
from app.domain.planning.resource_gaps import extract
from app.domain.planning.resource_research import (
    RESEARCH_CHAPTER_V3,
    RESEARCH_COMPARISON_V2,
    ResearchChapterReview,
    ResearchEntry,
    ResearchEvidenceRef,
    ResearchQualityEvidence,
    ResearchRequirement,
    ResearchResource,
    ResearchSession,
    ResearchUnreadChapter,
    ResourceResearchResult,
    reject,
    research_input_hash,
)
from app.domain.resources.models import (
    ResourcePreference,
    ResourceRecord,
    SourceSearchUnavailable,
    UnavailableResult,
)
from app.domain.workspace.models import AuthContext
from app.ports.llm import LLMFailure, LLMNotDispatchedError, LLMResult
from app.ports.resource_index import ResourceQuery


class ResourceResearcher:
    def __init__(self, *, github, web, body_reader, llm, reviewed_index=None, access_proofs=(), catalog=None,
                 domain_approvals=(), allow_fixture_domains=False):
        self.github, self.web, self.body_reader, self.llm = github, web, body_reader, llm
        self.reviewed_index, self.access_proofs, self.catalog = reviewed_index, tuple(access_proofs), catalog
        self._domain_approvals = tuple(domain_approvals)
        self._allow_fixture_domains = allow_fixture_domains

    def research(self, gap_set, *, plan, coverage, profile, session, scope, project_id, checked_at):
        if type(scope) is not AuthContext:
            reject("authorization")
        scope.require_project(project_id)
        if type(session) is not ResearchSession:
            reject("session")
        try:
            stamp = datetime.fromisoformat(checked_at)
            if stamp.tzinfo is None:
                reject("checked_at")
            if extract(plan, coverage) != gap_set or profile.profile_hash != plan.source_goal_profile_hash:
                reject("source_binding")
            if not validate_capability_planning_input({"profile": profile.to_payload(),
                    "policy": CAPABILITY_POLICY.to_payload(),
                    "verification_evidence": [e.to_payload() for e in plan.verification_evidence]}, CAPABILITY_SCHEMA):
                reject("profile")
            expected = research_input_hash(gap_set, plan, coverage, profile, session.budget,
                project_id=project_id, checked_at=checked_at, actor_id=scope.actor_id, rules_version=session.rules_version)
            if session.input_hash != expected:
                reject("session_input_hash")
            public = public_outcomes(plan, domain_approvals=self._domain_approvals,
                                     allow_fixture_domains=self._allow_fixture_domains)
            config_hash = content_hash({"reviewed_index": self.reviewed_index.index_hash if self.reviewed_index else None,
                "access_proofs": [asdict(p) for p in self.access_proofs], "public_outcomes": public,
                "constraint_policy": research_constraint_policy(profile.hard_constraints)})
            if session.config_hash and session.config_hash != config_hash:
                reject("session_configuration")
            session.config_hash = config_hash
            requirements = tuple(ResearchRequirement(gap.capability_id, gap.missing_outcomes, gap.importance,
                gap.desired_depth, gap.requirement_refs, profile.starting_point, profile.hard_constraints, profile.learner_claims)
                for gap in gap_set.gaps)
            wanted_outcomes = {outcome.outcome_id for requirement in requirements for outcome in requirement.must_teach}
            missing_outcomes = set(wanted_outcomes)
            outcome_depths = {o.outcome_id: c.desired_depth for c in plan.learning_capabilities for o in c.learning_outcomes}
            if session.rules_version in {RESEARCH_COMPARISON_V2, RESEARCH_CHAPTER_V3}:
                wanted_outcomes.update(o.outcome_id for o in plan.learning_outcomes if public.get(o.outcome_id) == o.text)
            for cache_identity, findings in session.inspected.items():
                candidate_url = cache_identity.split("#review:", 1)[0] if session.rules_version in {RESEARCH_COMPARISON_V2, RESEARCH_CHAPTER_V3} else cache_identity
                for resource in findings:
                    if (type(resource) is not ResearchResource or replace(resource) != resource
                        or resource.checked_at != checked_at or resource.qualification != "research_checked"
                        or resource.free_access != "confirmed"
                        or not self._source_binding(resource.resource_id, resource.url, resource.version, candidate_url)
                        or any(ref.outcome_id not in wanted_outcomes or ref.hash_scope != "body" for ref in resource.evidence)):
                        reject("inspected_source_binding")
                    if session.rules_version in {RESEARCH_COMPARISON_V2, RESEARCH_CHAPTER_V3} and (
                            "#review:" not in cache_identity or
                            "#depth:" not in cache_identity or
                            any(outcome_depths.get(ref.outcome_id) != cache_identity.rsplit("#depth:", 1)[-1]
                                for ref in resource.evidence) or
                            (session.rules_version != RESEARCH_CHAPTER_V3 and
                             {r.outcome_id for r in resource.evidence} - set(session.inspected_scopes.get(cache_identity, ())))):
                        reject("inspected_scope_binding")
            if session.rules_version == RESEARCH_CHAPTER_V3:
                for cache_identity, reviews in session.chapter_reviews.items():
                    origin = cache_identity.split("#review:", 1)[0]
                    depth = cache_identity.rsplit("#depth:", 1)[-1]
                    if "#review:" not in cache_identity or "#depth:" not in cache_identity:
                        reject("chapter_source_binding")
                    for review in reviews:
                        if (type(review) is not ResearchChapterReview or replace(review) != review
                                or not self._source_binding(review.resource_id, review.url, review.version, origin)
                                or any(outcome_depths.get(o) != depth or o not in wanted_outcomes for o in review.outcome_ids)):
                            reject("chapter_source_binding")
                for cache_identity, findings in session.inspected.items():
                    reviews = session.chapter_reviews.get(cache_identity, ())
                    for resource in findings:
                        if any(not any(review.resource_id == resource.resource_id and review.url == resource.url
                                and review.version == resource.version and ref.outcome_id in review.outcome_ids
                                and (ref.reference, ref.sha256, ref.location) in review.chunks
                                for review in reviews) for ref in resource.evidence):
                            reject("chapter_evidence_binding")
                for identity, reviews in session.unread_chapters.items():
                    if "#review:" not in identity or "#depth:" not in identity or any(
                            type(r) is not ResearchUnreadChapter or replace(r) != r or any(
                                outcome_depths.get(o) != identity.rsplit("#depth:", 1)[-1] or o not in wanted_outcomes
                                for o in r.outcome_ids) for r in reviews):
                        reject("chapter_source_binding")
            completed = session.completed
            if completed is not None:
                if type(completed) is not ResourceResearchResult or replace(completed) != completed:
                    reject("completed_result")
                if ((completed.source_gap_set_hash, completed.source_capability_plan_hash,
                     completed.source_coverage_result_hash, completed.source_profile_hash)
                    != (gap_set.result_hash, plan.plan_hash, coverage.result_hash, profile.profile_hash)
                    or completed.checked_at != checked_at
                    or completed.rules_version != session.rules_version
                    or completed.budget_usage != tuple(sorted(session.usage.items()))
                    or tuple(entry.requirement for entry in completed.entries) != requirements):
                    reject("completed_source_binding")
        except (TypeError, ValueError, AttributeError, KeyError):
            reject("research_input")
        if session.completed is not None:
            return session.completed
        entries = {}
        v2 = session.rules_version in {RESEARCH_COMPARISON_V2, RESEARCH_CHAPTER_V3}
        v3 = session.rules_version == RESEARCH_CHAPTER_V3
        constraints_allowed, external_allowed = research_permissions(profile.hard_constraints)
        essential = {c.capability_id for c in plan.learning_capabilities
                     if c.learning_requirement == "required" or c.learning_target_refs}
        # A recommended prerequisite of an essential capability still needs a
        # coverage attempt. This scheduling fact never changes its importance.
        while True:
            expanded = essential | {p for c in plan.learning_capabilities if c.capability_id in essential
                                    for p in c.prerequisite_refs}
            if expanded == essential:
                break
            essential = expanded
        required_work = sorted((r for r in requirements if r.capability_id in essential), key=lambda r: r.capability_id)
        elective_work = sorted((r for r in requirements if r.capability_id not in essential), key=lambda r: r.capability_id)
        # One new candidate per essential scope first; only then spend on
        # remaining coverage/comparison. Keep discovered batches in-memory so
        # the second visit cannot re-search or re-dispatch a prior candidate.
        work = list(required_work or elective_work) if v2 else requirements
        visited, discovered = set(), {}
        for work_position, requirement in enumerate(work):
            previous_entry = entries.get(requirement.capability_id)
            resources = list(previous_entry.resources) if previous_entry else []
            reasons = [r for r in previous_entry.comparison_reasons if r not in
                       {"single_candidate_only", "comparison_unavailable", "finite_scope_only"}] if previous_entry else []
            first_turn = v2 and requirement.capability_id in essential and requirement.capability_id not in visited
            visited.add(requirement.capability_id)
            turn_yielded = False
            comparison_complete = True
            if not constraints_allowed:
                reasons.append("constraints_pending")
            elif any(public.get(o.outcome_id) != o.text for o in requirement.must_teach):
                reasons.append("public_descriptor_unapproved")
            elif session.blocked:
                reasons.append("research_stopped")
            else:
                resources.extend(self._reviewed(requirement, checked_at))
                if v2:
                    wanted = {o.outcome_id for o in requirement.must_teach}
                    for cache_identity, findings in session.inspected.items():
                        if not cache_identity.endswith("#depth:" + requirement.desired_depth):
                            continue
                        for resource in findings:
                            refs = tuple(ref for ref in resource.evidence if ref.outcome_id in wanted)
                            if refs:
                                resources.append(replace(resource, evidence=refs))
                    resources = self._merge_resources(resources)
                for provider_position, index in enumerate((self.github, self.web)):
                    remaining = self._remaining(requirement, resources)
                    if (not remaining and (not v2 or resources and all(r.qualification == "public_reviewed" for r in resources)
                            or v2 and len(resources) >= 2)) or session.blocked:
                        break
                    if not external_allowed:
                        reasons.append("network_forbidden")
                        break
                    if index is None:
                        continue
                    # Only Policy/approved public definitions go to discovery,
                    # never Profile/project context/starting point/claims/limits.
                    query = ResourceQuery(scope, tuple(o.outcome_id for o in (requirement.must_teach if v2 else remaining)),
                        ResourcePreference(PreferenceScope.PROJECT, project_id), limit=5,
                        extra={"project_id": project_id, "query": "tutorial guide examples " + " ".join(o.text for o in (requirement.must_teach if v2 else remaining))})
                    batch_key = (requirement.capability_id, provider_position)
                    if batch_key in discovered:
                        candidates = discovered[batch_key]
                    else:
                        reservation = session.reserve("search", searches=1, total_requests=1,
                                                      cost_micros=session.budget.search_cost_micros)
                        if reservation is None:
                            reasons.append("budget_exhausted" if not session.blocked else "research_stopped")
                            break
                        try:
                            candidates = index.find(query)
                        except Exception:
                            session.mark_unknown()
                            reasons.append("research_unknown")
                            break
                        if type(candidates) is SourceSearchUnavailable:
                            if candidates.status == "unknown":
                                session.mark_unknown()
                                reasons.append("search_unknown")
                                break
                            session.settle(reservation, total_requests=candidates.requests, searches=candidates.requests)
                            reasons.append("search_failed" if candidates.status == "failed" else "search_not_dispatched")
                            if candidates.stop_required:
                                session.blocked = True
                                break
                            candidates = []
                        elif isinstance(candidates, UnavailableResult):
                            session.mark_unknown()
                            reasons.append("search_unclassified")
                            break
                        else:
                            session.settle(reservation, total_requests=1, searches=1)
                        discovered[batch_key] = candidates
                    if type(candidates) is not list or len(candidates) > 5 or any(type(c) is not ResourceRecord for c in candidates):
                        reasons.append("candidate_invalid")
                        continue
                    for candidate in sorted(candidates, key=lambda c: c.language != "zh"):
                        if candidate.project_id != project_id:
                            reasons.append("candidate_invalid")
                            session.blocked = True
                            break
                        remaining = self._remaining(requirement, resources)
                        if (not remaining and (not v2 or len(resources) >= 2)) or session.blocked:
                            comparison_complete = not session.blocked
                            break
                        scope_outcomes = self._review_scope(requirement, remaining, plan, session, missing_outcomes) if v2 else remaining
                        cache_key = self._cache_key(candidate, requirement.desired_depth) if v2 else candidate.url
                        if v3:
                            resources, why, attempted = self._inspect_chapters(candidate, requirement, resources,
                                plan, session, checked_at, missing_outcomes, first_turn)
                            reasons.extend(why)
                            if why:
                                comparison_complete = False
                            if first_turn and attempted:
                                turn_yielded = True
                                break
                            continue
                        if cache_key in session.inspected and (not v2 or
                                {o.outcome_id for o in scope_outcomes} <= set(session.inspected_scopes.get(cache_key, ()))):
                            wanted = {o.outcome_id for o in requirement.must_teach}
                            for resource in session.inspected[cache_key]:
                                refs = tuple(ref for ref in resource.evidence if ref.outcome_id in wanted)
                                if refs:
                                    filtered = replace(resource, evidence=refs)
                                    if filtered not in resources:
                                        resources.append(filtered)
                            if v2:
                                resources = self._merge_resources(resources)
                            continue
                        if v2:
                            reviewed = set(session.inspected_scopes.get(cache_key, ()))
                            scope_outcomes = tuple(o for o in scope_outcomes if o.outcome_id not in reviewed)
                        admission = session.reserve("candidate", candidates=1)
                        if admission is None:
                            reasons.append("budget_exhausted")
                            comparison_complete = False
                            break
                        session.settle(admission, candidates=1)
                        checked, why = self._inspect(candidate, requirement, scope_outcomes, plan, session, checked_at)
                        wanted = {o.outcome_id for o in requirement.must_teach}
                        filtered_checked = tuple(replace(r, evidence=tuple(ref for ref in r.evidence if ref.outcome_id in wanted)) for r in checked)
                        resources.extend(resource for resource in filtered_checked if resource not in resources and (resource.evidence or not v2))
                        if v2:
                            resources = self._merge_resources(resources)
                        reasons.extend(why)
                        if why:
                            comparison_complete = False
                        previous = session.inspected.get(cache_key, ()) if v2 else ()
                        session.inspected[cache_key] = tuple(sorted(set(previous + tuple(checked)), key=lambda r: (r.resource_id, r.version, repr(r.evidence))))
                        if v2:
                            session.inspected_scopes[cache_key] = tuple(sorted(set(session.inspected_scopes.get(cache_key, ())) |
                                {o.outcome_id for o in scope_outcomes}))
                        if first_turn:
                            turn_yielded = True
                            break
                    if turn_yielded or v2 and not self._remaining(requirement, resources):
                        break  # partial evidence never suppresses later providers
            missing = self._remaining(requirement, resources)
            if missing and not reasons:
                reasons.append("no_suitable_free_resource")
            status = "resolved" if not missing else "partial" if len(missing) < len(requirement.must_teach) else "unresolved"
            if v2 and (len(resources) < 2 or any(not r.quality_evidence for r in resources)):
                comparison_complete = False
                reasons.append("single_candidate_only" if len(resources) == 1 else "comparison_unavailable")
            entries[requirement.capability_id] = ResearchEntry(requirement, status,
                tuple(sorted(resources, key=lambda r: (r.resource_id, r.version))), missing,
                tuple(sorted(set(reasons))) if missing else (),
                "sufficient" if v2 and comparison_complete and resources and not missing and not self._incomparable(resources) else "insufficient" if v2 else "legacy",
                self._comparison_order(resources) if v2 else (),
                tuple(sorted(set(reasons) | {"finite_scope_only"} |
                    ({"quality_incomparable"} if self._incomparable(resources) else set()))) if v2 else ())
            if v2 and required_work and work_position == len(required_work) - 1:
                work.extend(sorted(required_work, key=lambda r:
                    (not entries[r.capability_id].unresolved_outcomes, r.capability_id)))
                work.extend(elective_work)
        if v3:
            # Late joint review evidence is authoritative only for its exact
            # source/version/depth/outcome scope. Rebuild before freezing once.
            for requirement in requirements:
                previous = entries[requirement.capability_id]
                resources = self._merge_resources(list(previous.resources) + self._cached(requirement, session))
                missing = self._remaining(requirement, resources)
                reasons = set(previous.comparison_reasons) - {"single_candidate_only", "comparison_unavailable", "quality_incomparable"}
                if len(resources) < 2 or any(not r.quality_evidence for r in resources):
                    reasons.add("single_candidate_only" if len(resources) == 1 else "comparison_unavailable")
                incomparable = self._incomparable(resources)
                if incomparable:
                    reasons.add("quality_incomparable")
                incomplete = reasons & {"budget_exhausted", "budget_exceeded", "research_stopped", "research_unknown",
                    "search_unknown", "search_failed", "search_not_dispatched", "search_unclassified", "body_unread",
                    "body_failed", "body_binding_invalid", "reader_not_dispatched", "reader_failed", "reader_invalid",
                    "candidate_invalid", "network_forbidden", "constraints_pending", "public_descriptor_unapproved"}
                comparison = "sufficient" if (not missing and len(resources) >= 2 and
                    all(r.quality_evidence for r in resources) and not incomparable and not incomplete) else "insufficient"
                entries[requirement.capability_id] = ResearchEntry(requirement,
                    "resolved" if not missing else "partial" if len(missing) < len(requirement.must_teach) else "unresolved",
                    tuple(resources), missing, previous.reason_codes if missing else (), comparison,
                    self._comparison_order(resources), tuple(sorted(reasons | {"finite_scope_only"})))
        result = ResourceResearchResult(gap_set.result_hash, plan.plan_hash, coverage.result_hash, profile.profile_hash,
            tuple(entries.values()), checked_at, tuple(sorted(session.usage.items())), session.rules_version)
        session.completed = result
        return result

    def _review_scope(self, requirement, remaining, plan, session, missing_outcomes):
        """One dependency-neighbour scope; never union the entire required set."""
        if session.rules_version not in {RESEARCH_COMPARISON_V2, RESEARCH_CHAPTER_V3}:
            return remaining
        public = public_outcomes(plan, domain_approvals=self._domain_approvals,
                                 allow_fixture_domains=self._allow_fixture_domains)
        selected = list((remaining or requirement.must_teach)[:6] if session.rules_version == RESEARCH_CHAPTER_V3
                        else requirement.must_teach[:6])
        related = {requirement.capability_id}
        for capability in plan.learning_capabilities:
            if requirement.capability_id in capability.prerequisite_refs:
                related.add(capability.capability_id)
            if capability.capability_id == requirement.capability_id:
                related.update(capability.prerequisite_refs)
        for other in sorted(plan.learning_capabilities, key=lambda c: c.capability_id):
            if (other.capability_id in related and other.learning_requirement == "required"
                    and other.desired_depth == requirement.desired_depth):
                for outcome in other.learning_outcomes:
                    if (outcome.outcome_id in missing_outcomes and outcome not in selected
                            and public.get(outcome.outcome_id) == outcome.text and len(selected) < 6):
                        selected.append(outcome)
        return tuple(selected)

    @staticmethod
    def _cached(requirement, session):
        wanted = {o.outcome_id for o in requirement.must_teach}
        return [replace(resource, evidence=refs)
            for identity, findings in session.inspected.items()
            if identity.endswith("#depth:" + requirement.desired_depth)
            for resource in findings
            if (refs := tuple(ref for ref in resource.evidence if ref.outcome_id in wanted))]

    @staticmethod
    def _excluded_chapters(candidate, requirement, outcomes, session):
        wanted = {o.outcome_id for o in outcomes}
        chapters = {}
        for review in session.chapter_reviews.get(ResourceResearcher._cache_key(candidate, requirement.desired_depth), ()):
            for chunk in review.chunks:
                chapters.setdefault(chunk[2].rsplit("#L", 1)[0], set()).update(review.outcome_ids)
        for review in session.unread_chapters.get(ResourceResearcher._cache_key(candidate, requirement.desired_depth), ()):
            chapters.setdefault(review.path, set()).update(review.outcome_ids)
        return tuple(sorted(path for path, reviewed in chapters.items() if wanted <= reviewed))

    @staticmethod
    def _record_unread_chapter(candidate, requirement, outcomes, session, path):
        review = ResearchUnreadChapter(path, tuple(o.outcome_id for o in outcomes))
        origin, repo = urlsplit(candidate.url), candidate.discovery.get("repo", {})
        if (candidate.discovery.get("source") != "github" or type(repo) is not dict
                or origin.scheme != "https" or origin.netloc not in {"github.com", "github.com:443"}
                or origin.path != "/" + str(repo.get("owner")) + "/" + str(repo.get("name"))
                or origin.query or origin.fragment):
            reject("unread_chapter_source")
        key = ResourceResearcher._cache_key(candidate, requirement.desired_depth)
        session.unread_chapters[key] = tuple(sorted(set(session.unread_chapters.get(key, ()) + (review,)),
                                                 key=lambda r: (r.path, r.outcome_ids)))

    @staticmethod
    def _record_chapter(candidate, requirement, outcomes, session, *, resource_id, url, version, chunks):
        review = ResearchChapterReview(resource_id, url, version, tuple(o.outcome_id for o in outcomes), tuple(
            (c["chunk_id"], c["content_hash"], c["location"]) for c in chunks))
        if not ResourceResearcher._source_binding(resource_id, url, version, candidate.url):
            reject("chapter_source_binding")
        key = ResourceResearcher._cache_key(candidate, requirement.desired_depth)
        previous = session.chapter_reviews.get(key, ())
        if any(r.resource_id == resource_id and r.version != version for r in previous):
            reject("research_source_version_conflict")
        session.chapter_reviews[key] = tuple(sorted(set(previous + (review,)), key=lambda r: (r.url, r.version, r.outcome_ids)))

    def _inspect_chapters(self, candidate, requirement, resources, plan, session, checked_at, missing_outcomes, first_turn):
        key, reasons, attempted = self._cache_key(candidate, requirement.desired_depth), [], False
        while not session.blocked:
            remaining = self._remaining(requirement, resources)
            if not remaining and len(resources) >= 2:
                break
            exhausted = set(session.inspected_scopes.get(key, ()))
            scope_remaining = tuple(o for o in (remaining or requirement.must_teach) if o.outcome_id not in exhausted)
            if not scope_remaining:
                break
            supported = {ref.outcome_id for findings in session.inspected.values() for resource in findings for ref in resource.evidence}
            scope = self._review_scope(requirement, scope_remaining, plan, session, missing_outcomes - supported - exhausted)
            if {o.outcome_id for o in scope} <= set(session.inspected_scopes.get(key, ())):
                break  # Only repository exhaustion, never a chapter negative.
            admission = session.reserve("candidate", candidates=1)
            if admission is None:
                reasons.append("budget_exhausted")
                break
            session.settle(admission, candidates=1)
            before = session.chapter_reviews.get(key, ())
            before_unread = session.unread_chapters.get(key, ())
            checked, why = self._inspect(candidate, requirement, scope, plan, session, checked_at)
            attempted = True
            reasons.extend(why)
            previous = session.inspected.get(key, ())
            session.inspected[key] = tuple(sorted(set(previous + tuple(checked)), key=lambda r: (r.resource_id, r.version, repr(r.evidence))))
            resources = self._merge_resources(resources + self._cached(requirement, session))
            if (session.chapter_reviews.get(key, ()) == before and
                    session.unread_chapters.get(key, ()) == before_unread) and not session.blocked:
                session.inspected_scopes[key] = tuple(sorted(set(session.inspected_scopes.get(key, ())) |
                                                            {o.outcome_id for o in scope}))
            if first_turn or session.blocked:
                break
        return resources, tuple(reasons), attempted

    @staticmethod
    def _merge_resources(resources):
        merged = {}
        for resource in resources:
            existing = merged.get(resource.resource_id)
            if existing is not None:
                if existing.version != resource.version or existing.url != resource.url:
                    reject("research_source_version_conflict")
                quality = existing.quality_evidence
                if quality and resource.quality_evidence:
                    later = {q.dimension: q for q in resource.quality_evidence}
                    quality = tuple(later[q.dimension] if q.category == "strong" and later[q.dimension].category == "adequate"
                        else q for q in quality)
                resource = replace(existing, evidence=tuple(set(existing.evidence + resource.evidence)),
                    limitations=tuple(sorted(set(existing.limitations + resource.limitations)))[:12], quality_evidence=quality)
            merged[resource.resource_id] = resource
        return list(merged.values())

    @staticmethod
    def _cache_key(candidate, desired_depth):
        # Discovery identity is frozen too. Changed source-version metadata may
        # not reuse an earlier scope just because the repository URL is equal.
        return candidate.url + "#review:" + content_hash(candidate.discovery) + "#depth:" + desired_depth

    @staticmethod
    def _comparison_relation(a, b):
        """Joint evidence/quality relation; no scalar score or hidden weighting."""
        dimensions = ("continuity", "beginner_fit", "examples", "version_fit")
        aq, bq = ({q.dimension: q.category for q in r.quality_evidence} for r in (a, b))
        if any(q.get(d) not in {"adequate", "strong"} for q in (aq, bq) for d in dimensions):
            return "incomparable"
        ac, bc = ({ref.outcome_id for ref in r.evidence} for r in (a, b))
        av, bv = (tuple(q[d] == "strong" for d in dimensions) for q in (aq, bq))
        if ac == bc and av == bv:
            return "equal"
        if ac >= bc and all(x >= y for x, y in zip(av, bv, strict=True)):
            return "better"
        if bc >= ac and all(y >= x for x, y in zip(av, bv, strict=True)):
            return "worse"
        return "incomparable"

    @staticmethod
    def _comparison_order(resources):
        # Stable finite preference: evidence coverage, multidimensional quality,
        # then Chinese only when coverage and every quality dimension tie.
        dimensions = ("continuity", "beginner_fit", "examples", "version_fit")
        def quality(resource):
            return tuple(dict((q.dimension, q.category) for q in resource.quality_evidence).get(d) for d in dimensions)
        pending, ordered = list(resources), []
        while pending:
            front = [r for r in pending if not any(ResourceResearcher._comparison_relation(other, r) == "better"
                                                 for other in pending)]
            # Language can break only genuinely comparable equal-quality ties.
            front.sort(key=lambda r: r.resource_id)
            for profile in dict.fromkeys((tuple(sorted({ref.outcome_id for ref in r.evidence})), quality(r)) for r in front):
                tied = [r for r in front if (tuple(sorted({ref.outcome_id for ref in r.evidence})), quality(r)) == profile]
                tied.sort(key=lambda r: (dict(r.teaching_fit).get("language") != "zh" if None not in profile[1] else False,
                    r.resource_id))
                ordered.extend(r.resource_id for r in tied)
            pending = [r for r in pending if r not in front]
        return tuple(ordered)

    @staticmethod
    def _incomparable(resources):
        return any(ResourceResearcher._comparison_relation(a, b) == "incomparable"
                   for i, a in enumerate(resources) for b in resources[i + 1:])

    @staticmethod
    def _remaining(requirement, resources):
        supported = {ref.outcome_id for resource in resources if resource.free_access == "confirmed"
                     and resource.qualification in {"public_reviewed", "research_checked"} for ref in resource.evidence}
        return tuple(o for o in requirement.must_teach if o.outcome_id not in supported)

    def _reviewed(self, requirement, checked_at):
        if self.reviewed_index is None or self.catalog is None:
            return ()
        definitions = {d.capability_id: d for d in CAPABILITY_POLICY.definitions}
        mappings = _qualified_mappings(self.reviewed_index, definitions)
        sources = self.catalog.load_sources(source_ids=tuple({s.source_id for s in self.reviewed_index.sections}))
        resources = {}
        for outcome in requirement.must_teach:
            for section, reviews in mappings.get(outcome.outcome_id, ()):
                source = sources.get(section.source_id)
                proof = next((p for p in self.access_proofs if p.source_id == section.source_id
                    and p.source_version == section.source_version and p.content_hash == section.content_hash
                    and p.access == "free_public"), None)
                if source is None or source.source_version != section.source_version or proof is None:
                    continue
                key = (section.source_id, section.source_version)
                refs = resources.setdefault(key, [source, []])[1]
                refs.extend(ResearchEvidenceRef(outcome.outcome_id, r.reference, r.sha256,
                            section.section_id, "review_record") for r in reviews)
        return tuple(ResearchResource(source.source_id, source.canonical_url, f"source:{version}", checked_at,
            "confirmed", "public_reviewed", tuple(refs), (("basis", "retained_scoped_review"),),
            ("Retained scoped review; no new body read or runtime validation",))
            for (_, version), (source, refs) in resources.items())

    @staticmethod
    def _source_binding(resource_id, url, version, candidate_url):
        if resource_id != "resource_" + content_hash({"url": url}):
            return False
        origin, chapter = urlsplit(candidate_url), urlsplit(url)
        if (origin.scheme != "https" or chapter.scheme != "https" or origin.hostname != "github.com"
                or origin.netloc not in {"github.com", "github.com:443"} or origin.query or origin.fragment
                or not re.fullmatch(r"/[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}", origin.path)
                or chapter.netloc != "github.com" or chapter.query or chapter.fragment
                or not chapter.path.startswith(origin.path.rstrip("/") + "/blob/")
                or not re.fullmatch(r"git-blob:[0-9a-f]{40}", version)):
            return False
        return len(chapter.path.split("/")) >= 6

    @staticmethod
    def _body_binding(body, candidate):
        if type(body) is not TransientBody or not ResourceResearcher._source_binding(
                body.resource_id, body.url, body.version, candidate.url):
            return False
        chapter = urlsplit(body.url)
        parts = chapter.path.split("/")
        path = unquote("/".join(parts[5:]))
        return all(type(chunk) is dict and chunk.get("resource_id") == body.resource_id
                   and chunk.get("version") == body.version and chunk.get("location") ==
                   f"{path}#L1-L{max(1, len(chunk.get('text', '').splitlines()))}" for chunk in body.chunks)

    def _inspect(self, candidate, requirement, remaining, plan, session, checked_at):
        reservation = session.reserve("body", total_requests=2, body_bytes=65536)
        if reservation is None:
            return (), ("budget_exhausted",)
        body, payload = None, None
        try:
            try:
                options = {"max_bytes": 65536, "timeout_seconds": 15}
                if session.rules_version in {RESEARCH_COMPARISON_V2, RESEARCH_CHAPTER_V3} and getattr(self.body_reader, "supports_outcome_selection", False):
                    options["must_teach"] = tuple(o.text for o in remaining)
                if session.rules_version == RESEARCH_CHAPTER_V3 and getattr(self.body_reader, "supports_chapter_selection", False):
                    options["exclude_paths"] = self._excluded_chapters(candidate, requirement, remaining, session)
                body = self.body_reader.read(candidate, **options)
            except Exception:
                session.mark_unknown()
                return (), ("research_unknown",)
            if type(body) is not TransientBody:
                session.mark_unknown()
                return (), ("research_unknown",)
            if body.status == "unknown":
                session.mark_unknown()
                return (), ("research_unknown",)
            try:
                session.settle(reservation, total_requests=body.requests, body_bytes=body.bytes_read)
            except ValidationAppError:
                session.blocked = True
                return (), ("budget_exceeded",)
            if body.status == "failed":
                session.blocked = True
                return (), ("body_failed",)
            if body.status != "succeeded":
                if session.rules_version == RESEARCH_CHAPTER_V3 and body.status == "unread" and body.attempted_path:
                    if body.attempted_path in options.get("exclude_paths", ()):
                        session.blocked = True
                        return (), ("body_binding_invalid",)
                    self._record_unread_chapter(candidate, requirement, remaining, session, body.attempted_path)
                return (), ("body_unread",)
            if not self._body_binding(body, candidate):
                session.blocked = True
                return (), ("body_binding_invalid",)
            if session.rules_version == RESEARCH_CHAPTER_V3:
                if any(c["location"].rsplit("#L", 1)[0] in options.get("exclude_paths", ()) for c in body.chunks):
                    session.blocked = True
                    return (), ("body_binding_invalid",)
            payload = {"must_teach": [asdict(o) for o in remaining], "chunks": body.chunks,
                "learner_context": {"accepted_known": sorted(c.capability_id for c in plan.accepted_known_capabilities
                    if CAPABILITY_POLICY.get(c.capability_id) is not None), "desired_depth": requirement.desired_depth}}
            schema = READER_SCHEMA_V2 if session.rules_version in {RESEARCH_COMPARISON_V2, RESEARCH_CHAPTER_V3} else READER_SCHEMA
            if schema == READER_SCHEMA_V2:
                payload["rules_version"] = RESEARCH_COMPARISON_V2
            authority = reader_authority(plan, domain_approvals=self._domain_approvals,
                                         allow_fixture_domains=self._allow_fixture_domains)
            if authority is not None:
                payload["domain_authority"] = authority
                payload["learner_context"]["accepted_known"] = sorted(
                    c.capability_id for c in plan.accepted_known_capabilities)
            if not validate_reader_input(payload, schema, domain_approvals=self._domain_approvals,
                                         allow_fixture_domains=self._allow_fixture_domains):
                session.blocked = True
                return (), ("body_binding_invalid",)
            if session.rules_version == RESEARCH_CHAPTER_V3:
                self._record_chapter(candidate, requirement, remaining, session, resource_id=body.resource_id,
                    url=body.url, version=body.version, chunks=body.chunks)
            reader_reservation = session.reserve("reader", total_requests=1, reader_requests=1,
                output_tokens=READER_OUTPUT_CAP, cost_micros=session.budget.reader_cost_micros)
            if reader_reservation is None:
                return (), ("budget_exhausted",)
            try:
                response = self.llm.generate_structured(purpose=READER_PURPOSE, schema_name=schema, payload=payload,
                    run_id=session.run_id, attempt_id=f"research-reader-{reader_reservation}")
            except LLMNotDispatchedError:
                session.settle(reader_reservation, total_requests=0, reader_requests=0, output_tokens=0, cost_micros=0)
                session.blocked = True
                return (), ("reader_not_dispatched",)
            except Exception:
                session.mark_unknown()
                return (), ("research_unknown",)
            if isinstance(response, LLMFailure):
                if response.dispatch_unknown:
                    session.mark_unknown()
                    return (), ("research_unknown",)
                try:
                    session.settle(reader_reservation, total_requests=1, reader_requests=1,
                                   output_tokens=response.output_tokens)
                except ValidationAppError:
                    session.blocked = True
                    return (), ("budget_exceeded",)
                session.blocked = True
                return (), ("reader_failed",)
            if type(response) is not LLMResult:
                session.mark_unknown()
                return (), ("research_unknown",)
            try:
                session.settle(reader_reservation, total_requests=1, reader_requests=1,
                               output_tokens=response.output_tokens, cost_micros=response.cost_micros)
            except ValidationAppError:
                session.blocked = True
                return (), ("budget_exceeded",)
            if response.finish_reason == "length":
                session.blocked = True
                return (), ("reader_invalid",)
            try:
                verdict = validate_reader_output(response.payload, payload, domain_approvals=self._domain_approvals,
                                                 allow_fixture_domains=self._allow_fixture_domains)
            except (ValueError, TypeError, KeyError):
                session.blocked = True
                return (), ("reader_invalid",)
            fit = verdict["teaching_fit"]
            if any(fit[key] != value for key, value in {"continuity": "sufficient", "beginner_fit": "suitable",
                    "examples": "present", "version_fit": "compatible"}.items()):
                return (), ("teaching_fit_unresolved",)
            if session.rules_version in {RESEARCH_COMPARISON_V2, RESEARCH_CHAPTER_V3} and any(
                    q["category"] not in {"adequate", "strong"} for q in verdict["quality_evidence"].values()):
                return (), ("teaching_fit_unresolved",)
            chunks = {c["chunk_id"]: c for c in body.chunks}
            refs = tuple(ResearchEvidenceRef(item["outcome_id"], ref["chunk_id"], ref["content_hash"],
                         chunks[ref["chunk_id"]]["location"], "body")
                         for item in verdict["outcomes"] if item["status"] == "supported" for ref in item["evidence_refs"])
            limits = tuple(sorted({limit for item in verdict["outcomes"] for limit in item["limitations"]}))[:12]
            quality = tuple(ResearchQualityEvidence(dimension, opinion["category"], opinion["rationale"],
                tuple(ResearchEvidenceRef(remaining[0].outcome_id, ref["chunk_id"], ref["content_hash"],
                    chunks[ref["chunk_id"]]["location"], "body") for ref in opinion["evidence_refs"]))
                for dimension, opinion in verdict.get("quality_evidence", {}).items())
            resource = ResearchResource(body.resource_id, body.url, body.version, checked_at, "confirmed",
                "research_checked", refs, tuple(sorted(fit.items())), limits, quality)
            return (resource,), ("outcomes_unresolved",) if len({r.outcome_id for r in refs}) < len(remaining) else ()
        finally:
            if payload is not None:
                payload.clear()
            if type(body) is TransientBody:
                body.close()
