"""Sequential Item1→6→Compiler→P2 runtime; no second Worker or business graph."""

from __future__ import annotations

from dataclasses import asdict

from app.application.capability_planning import CapabilityPlanner
from app.application.curriculum_composition import CurriculumComposer
from app.application.goal_requirement_analysis import GoalRequirementAnalyzer
from app.application.teaching_resource_research import ResourceResearcher
from app.core.errors import ConflictError, ValidationAppError, VersionConflictError
from app.core.ids import content_hash
from app.domain.enums import MediaType, ResourceProvenance, ResourceVerificationStatus
from app.domain.planning.capabilities import CapabilityPlan, CapabilityPlanningPending
from app.domain.planning.content_coverage import CoverageEvaluator
from app.domain.planning.curriculum import CurriculumPlan, prepare_curriculum
from app.domain.planning.curriculum_compiler import compile_curriculum
from app.domain.planning.domain_verification import bind_domain_approval
from app.domain.planning.goal_requirements import GoalRequirementProfile
from app.domain.planning.intent import GoalSpec, goal_spec_from_payload, goal_spec_payload
from app.domain.planning.research_reader import TransientBody
from app.domain.planning.resource_gaps import extract
from app.domain.planning.resource_research import (
    ResearchBudget,
    ResearchSession,
    ResearchSnapshot,
    research_input_hash,
)
from app.domain.planning.v2_execution import _decode
from app.domain.resources.models import ResourceRecord, UnavailableResult
from app.infrastructure.providers.v2_attempts import (
    V2RecoveryBlocked,
    wire,
)
from app.ports.llm import LLMFailure
from app.ports.resource_index import ResourceInspectionResult


class DurableIndex:
    def __init__(self, ledger, index, name):
        self.ledger, self.index, self.name = ledger, index, name

    def find(self, query):
        if query.scope.actor_id != self.ledger.scope.actor_id:
            raise ValidationAppError("V2 search actor mismatch")
        self.ledger.scope.require_project(query.extra.get("project_id"))
        payload = {
            "query": query.extra.get("query"),
            "outcomes": list(query.node_keys),
            "limit": query.limit,
            "project_id": self.ledger.project_id,
        }

        def encode(result):
            if (
                isinstance(result, UnavailableResult)
                or type(result) is not list
                or len(result) > 5
                or any(type(r) is not ResourceRecord for r in result)
            ):
                return {
                    "kind": "failure",
                    "value": asdict(
                        LLMFailure("search_unclassified", "Search outcome unknown", dispatch_unknown=True)
                    ),
                }, {}
            candidates = []
            for r in result:
                if r.project_id != self.ledger.project_id:
                    raise ValueError("Search scope mismatch")
                # Retain discovery metadata, never a provider excerpt/body.
                row = wire(asdict(r))
                row["source_note"] = ""
                row["title"] = "Resource candidate"
                row["discovery"] = {
                    "source": r.discovery.get("source", "github"),
                    "repo": r.discovery.get("repo", {}),
                }
                candidates.append(row)
            return {"kind": "search", "value": candidates}, {"searches": 1, "total_requests": 1}

        d = self.ledger.call(
            step=self.name + "-search",
            purpose="research.search",
            schema="V2ResourceSearchV1",
            payload=payload,
            reserved={
                "searches": 1,
                "total_requests": 1,
                "cost_micros": self.ledger.manifest["budget"]["search_cost_micros"],
            },
            invoke=lambda ident: self.index.find(query),
            encode=encode,
        )
        if d["kind"] == "failure":
            return UnavailableResult("V2 search requires reconciliation")
        values = []
        for row in d["value"]:
            row = dict(row)
            row["media_type"] = MediaType(row["media_type"])
            row["provenance"] = ResourceProvenance(row["provenance"])
            row["verification_status"] = ResourceVerificationStatus(row["verification_status"])
            if row["checked_at"]:
                from datetime import datetime

                row["checked_at"] = datetime.fromisoformat(row["checked_at"])
            values.append(ResourceRecord(**row))
        return values

    def inspect(self, query):
        def encode(result):
            measured = {}
            if type(result) is ResourceInspectionResult and type(result.receipts) is list:
                measured = {
                    "body_bytes": sum(
                        r["bytes"]
                        for r in result.receipts
                        if type(r) is dict and type(r.get("bytes")) is int and 0 <= r["bytes"] <= 10**12
                    ),
                    "total_requests": sum(
                        type(r) is dict
                        and r.get("status")
                        in {"succeeded", "failed", "dispatched", "reconciliation_required"}
                        for r in result.receipts
                    ),
                }
            if type(result) is not ResourceInspectionResult or result.status not in {"succeeded", "failed"}:
                return {
                    "kind": "failure",
                    "value": asdict(
                        LLMFailure(
                            "inspection_unknown", "Inspection requires reconciliation", dispatch_unknown=True
                        )
                    ),
                }, measured
            receipts = result.receipts
            if type(receipts) is not list or any(
                type(r) is not dict
                or r.get("status") not in {"succeeded", "failed", "not_dispatched"}
                or type(r.get("bytes")) is not int
                or r["bytes"] < 0
                for r in receipts
            ):
                raise ValueError("Invalid inspect receipt")
            safe = [{"status": r["status"], "bytes": r["bytes"]} for r in receipts]
            return {"kind": "inspection", "value": {"status": result.status, "receipts": safe}}, {
                "total_requests": sum(r["status"] != "not_dispatched" for r in receipts),
                "body_bytes": sum(r["bytes"] for r in receipts),
            }

        d = self.ledger.call(
            step=self.name + "-inspect",
            purpose="research.case_inspect",
            schema="V2CaseInspectionV1",
            payload={"candidate": query.candidate, "query": query.query, "paths": query.paths},
            reserved={
                "candidates": 1,
                "total_requests": 3,
                "body_bytes": 262144,
                "cost_micros": 3 * self.ledger.manifest["budget"]["search_cost_micros"],
            },
            invoke=lambda ident: self.index.inspect(query),
            encode=encode,
        )
        if d["kind"] == "failure":
            return ResourceInspectionResult("unknown", None, [])
        return ResourceInspectionResult(d["value"]["status"], None, d["value"]["receipts"])


class DurableBody:
    def __init__(self, ledger, reader):
        self.ledger, self.reader = ledger, reader

    def read(self, candidate, **kwargs):
        live = []

        def invoke(ident):
            value = self.reader.read(candidate, **kwargs)
            live.append(value)
            return value

        def encode(body):
            measured = (
                {"total_requests": body.requests, "body_bytes": body.bytes_read}
                if type(body) is TransientBody
                else {}
            )
            if type(body) is not TransientBody or body.status == "unknown":
                return {
                    "kind": "failure",
                    "value": asdict(
                        LLMFailure("body_unknown", "Body read requires reconciliation", dispatch_unknown=True)
                    ),
                }, measured
            if (
                body.status not in {"succeeded", "failed"}
                or type(body.requests) is not int
                or type(body.bytes_read) is not int
                or body.requests < 0
                or body.bytes_read < 0
            ):
                raise ValueError("Body receipt invalid")
            if body.status == "succeeded" and not ResourceResearcher._body_binding(body, candidate):
                return {
                    "kind": "failure",
                    "value": asdict(LLMFailure("body_binding_invalid", "Body binding rejected")),
                }, {"total_requests": body.requests, "body_bytes": body.bytes_read}
            if body.status == "succeeded":
                import hashlib

                if (
                    type(body.chunks) is not list
                    or not 0 < len(body.chunks) <= 2
                    or any(
                        type(c) is not dict
                        or set(c)
                        != {"chunk_id", "resource_id", "version", "content_hash", "location", "text"}
                        or type(c["text"]) is not str
                        or len(c["text"].encode()) > 16384
                        or hashlib.sha256(c["text"].encode()).hexdigest() != c["content_hash"]
                        or c["chunk_id"]
                        != "chunk_"
                        + content_hash(
                            {k: c[k] for k in ("resource_id", "version", "content_hash", "location")}
                        )
                        for c in body.chunks
                    )
                ):
                    return {
                        "kind": "failure",
                        "value": asdict(LLMFailure("body_binding_invalid", "Body binding rejected")),
                    }, measured
            return {
                "kind": "body_metadata",
                "value": {
                    "resource_id": body.resource_id if body.status == "succeeded" else "",
                    "url": body.url if body.status == "succeeded" else "",
                    "version": body.version if body.status == "succeeded" else "",
                    "status": body.status,
                    "chunks": [
                        {k: c[k] for k in ("chunk_id", "resource_id", "version", "content_hash", "location")}
                        for c in body.chunks
                    ]
                    if body.status == "succeeded"
                    else [],
                },
            }, measured

        try:
            d = self.ledger.call(
                step="teaching-body",
                purpose="research.body",
                schema="V2TransientBodyV1",
                payload={"url": candidate.url, "discovery": candidate.discovery, "options": kwargs},
                reserved={"total_requests": 2, "body_bytes": 65536},
                invoke=invoke,
                encode=encode,
            )
            if not live:
                raise V2RecoveryBlocked(
                    "Body-only receipt has no validated Reader outcome; no body redispatch"
                )
            body = live[0]
            if d["kind"] == "failure":
                body.close()
                return TransientBody(
                    "unknown" if d["value"].get("dispatch_unknown") else "failed",
                    requests=body.requests,
                    bytes_read=body.bytes_read,
                )
            self.ledger.current_body = body
            self.ledger.current_candidate_url = candidate.url
            return body
        except BaseException:
            for body in live:
                if type(body) is TransientBody:
                    body.close()
            raise


class DurableResourceResearcher(ResourceResearcher):
    """Only adds receipt recovery; the ordinary Item5 coordinator stays intact."""

    def __init__(self, ledger, **kwargs):
        self.ledger = ledger
        super().__init__(**kwargs)

    def _inspect(self, candidate, requirement, remaining, plan, session, checked_at):
        self.ledger.admit_candidate(candidate.url)
        recovered = self.ledger.inspected(candidate.url, remaining)
        if recovered is not None:
            # The successfully validated Reader receipt already binds exact
            # source/chunk/outcome metadata; no synthetic body is constructed.
            if checked_at != self.ledger.manifest["checked_at"]:
                raise V2RecoveryBlocked("Reader recovery timestamp mismatch")
            resources, reasons, metadata = recovered
            reservation = session.reserve("body", total_requests=2, body_bytes=65536)
            if reservation is None:
                return (), ("budget_exhausted",)
            session.settle(reservation, **metadata["body_usage"])
            reservation = session.reserve(
                "reader",
                total_requests=1,
                reader_requests=1,
                output_tokens=1024,
                cost_micros=session.budget.reader_cost_micros,
            )
            if reservation is None:
                return (), ("budget_exhausted",)
            session.settle(reservation, **metadata["reader_usage"])
            return resources, reasons
        return super()._inspect(candidate, requirement, remaining, plan, session, checked_at)


class V2PlanningRuntime:
    def __init__(
        self,
        *,
        calls,
        checkpoints,
        persistence,
        source_facts,
        github=None,
        web=None,
        body_reader=None,
        project_index=None,
        domain_approvals=(),
        verification_evidence=(),
        domain_sources=(),
    ):
        self.calls, self.checkpoints, self.persistence, self.facts = (
            calls,
            checkpoints,
            persistence,
            source_facts,
        )
        from app.infrastructure.providers.v2_transport import guarded_port

        self.github, self.web, self.body_reader, self.project_index = (
            guarded_port(calls, p) for p in (github, web, body_reader, project_index)
        )
        self.approvals, self.evidence = tuple(domain_approvals), tuple(verification_evidence)
        self.domain_sources = tuple(domain_sources)
        if any(getattr(e, "evidence_kind", None) != "source_verification" for e in self.evidence):
            raise ValidationAppError("Runtime cannot accept fixture domain authority")

    def execute(self, initial):
        from app.domain.planning.revisions import V2RevisionContext
        revision = V2RevisionContext.from_payload(initial.get("v2_revision"))
        clarification = initial.get("v2_clarification")
        manifest = self.calls.manifest
        if (clarification is None) != ("v2_clarification_hash" not in manifest):
            raise V2RecoveryBlocked("Runtime clarification marker/context mismatch")
        if clarification is not None:
            from app.infrastructure.db.v2_revisions import frozen_submission
            with self.calls.tx() as conn:
                self.calls._lock(conn)
                submission = frozen_submission(conn, actor_id=self.calls.scope.actor_id,
                    project_id=self.calls.project_id, run_id=self.calls.run_id)
                if submission["initial"].get("v2_clarification") != clarification:
                    raise V2RecoveryBlocked("Runtime clarification differs from durable consent")
        if revision is None and manifest["expected_version"] != 0:
            raise V2RecoveryBlocked("Existing revision requires bound replanning context")
        if (revision is None) != ("v2_revision_hash" not in manifest):
            raise V2RecoveryBlocked("Runtime revision marker/context mismatch")
        goal = goal_spec_from_payload(initial.get("goal_spec")) or GoalSpec(initial["goal"])
        if (
            manifest["goal_hash"] != content_hash(goal_spec_payload(goal))
            or manifest["source_facts_hash"] != content_hash(wire(asdict(self.facts)))
            or manifest["domain_registry_hash"]
            != content_hash([wire(asdict(s)) for s in self.domain_sources])
        ):
            raise V2RecoveryBlocked("V2 frozen input/source versions mismatch")
        # Publication is durable business truth even if its final checkpoint
        # or Run projection was interrupted. Recover only this exact result;
        # ordinary requests continue to require the original current basis.
        from uuid import NAMESPACE_URL, uuid5

        from app.infrastructure.db.plan_repository import PgPlanRepository
        from app.infrastructure.db.v2_revisions import published_v2_draft
        draft_id = "drf_" + uuid5(NAMESPACE_URL,
            f"studyplan:v2draft:{self.calls.project_id}:{self.calls.run_id}").hex
        self.calls.guard()
        with self.calls.tx() as conn:
            if published_v2_draft(conn, actor_id=self.calls.scope.actor_id, project_id=self.calls.project_id,
                    run_id=self.calls.run_id, draft_id=draft_id):
                self.calls._lock(conn, published_draft_id=draft_id)
                return PgPlanRepository("", connection=conn).get_draft(project_id=self.calls.project_id, draft_id=draft_id)
        if revision is not None:
            from app.infrastructure.db.v2_revisions import validate_semantic_input
            with self.calls.tx() as conn:
                self.calls._lock(conn)
                validate_semantic_input(conn, actor_id=self.calls.scope.actor_id, project_id=self.calls.project_id,
                    run_id=self.calls.run_id, manifest=manifest, context=revision)
        state = self.checkpoints.load() or {}

        def save(stage, **values):
            state.update(values)
            from app.ports.planning_jobs import PlanningLeaseLostError
            from app.ports.summaries import ReviewPersistenceInterrupted

            try:
                self.checkpoints.save(state | {"stage": stage})
            except (PlanningLeaseLostError, V2RecoveryBlocked, ReviewPersistenceInterrupted,
                    ConflictError, VersionConflictError):
                raise
            except Exception:
                raise ReviewPersistenceInterrupted("V2 checkpoint persistence interrupted") from None

        profile = GoalRequirementAnalyzer(self.calls).analyze(
            goal, run_id=self.calls.run_id, attempt_id="goal-analysis",
            clarification=clarification["item1_input"] if clarification else None,
        )
        if not isinstance(profile, GoalRequirementProfile) or profile.status != "ready":
            if isinstance(profile, GoalRequirementProfile) and revision is None:
                import psycopg
                from app.infrastructure.db.v2_clarifications import freeze_questions
                from app.ports.summaries import ReviewPersistenceInterrupted
                try:
                    freeze_questions(self.calls, profile, goal)
                except psycopg.Error:
                    raise ReviewPersistenceInterrupted("Clarification persistence interrupted") from None
                save("goal_clarification", profile=profile.to_payload())
            return (
                profile
                if isinstance(profile, LLMFailure)
                else LLMFailure("goal_clarification_required", "Goal needs clarification")
            )
        save("goal_analysis", profile=profile.to_payload())
        planner = CapabilityPlanner(self.calls)
        plan = planner.plan(
            profile,
            run_id=self.calls.run_id,
            attempt_id="capability-planning",
            verification_evidence=self.evidence,
            domain_approvals=self.approvals,
        )
        if isinstance(plan, CapabilityPlanningPending) and plan.status == "needs_verification":
            requested = {
                ref
                for issue in plan.issues
                if issue.code == "domain_verification_required"
                for ref in issue.refs
            }
            self.approvals = self._verify_domains(profile, requested)
            self.evidence = tuple(a.evidence for a in self.approvals)
            if self.approvals:
                self.calls.provider.domain_approvals = self.approvals
                plan = planner.plan(
                    profile,
                    run_id=self.calls.run_id,
                    attempt_id="capability-verified",
                    verification_evidence=self.evidence,
                    domain_approvals=self.approvals,
                )
        if not isinstance(plan, CapabilityPlan):
            return (
                plan
                if isinstance(plan, LLMFailure)
                else LLMFailure("capability_verification_required", "Capability selection needs verification")
            )
        approvals = tuple(bind_domain_approval(a, plan) for a in self.approvals)
        self.calls.domain_approvals = approvals
        self.calls.provider.domain_approvals = approvals
        self.persistence.domain_approvals = approvals
        save("capability_planning", capability_plan=plan.to_payload())
        coverage = CoverageEvaluator().evaluate(plan, self.facts.reviewed_index)
        gaps = extract(plan, coverage)
        save("coverage_gaps", coverage=coverage.to_payload(), gaps_hash=gaps.result_hash)
        budget = ResearchBudget(**manifest["budget"])
        expected = research_input_hash(
            gaps,
            plan,
            coverage,
            profile,
            budget,
            project_id=self.calls.project_id,
            checked_at=manifest["checked_at"],
            actor_id=self.calls.scope.actor_id,
        )
        if state.get("research_snapshot"):
            session = ResearchSession.restore(_decode(ResearchSnapshot, state["research_snapshot"]))
            if session.input_hash != expected or session.run_id != self.calls.run_id:
                raise V2RecoveryBlocked("Research checkpoint input binding mismatch")
        else:
            session = ResearchSession(self.calls.run_id, expected, budget)
            session.usage.update(self.calls.usage(related_only=True))
            with self.calls.tx() as conn:
                rows = conn.execute(
                    "SELECT detail FROM ai_run_events WHERE run_id=%s AND status='v2_reservation' AND detail->>'purpose'=ANY(%s)",
                    (
                        self.calls.run_id,
                        [
                            "planning.goal_requirement_analysis",
                            "planning.capability_planning",
                            "domain.verification",
                        ],
                    ),
                ).fetchall()
            for row in rows:
                for k, v in row["detail"]["reserved"].items():
                    session.usage[k] += v
        github = DurableIndex(self.calls, self.github, "github") if self.github else None
        web = DurableIndex(self.calls, self.web, "web") if self.web else None
        body = DurableBody(self.calls, self.body_reader) if self.body_reader else None

        class Catalog:
            def load_sources(inner, *, source_ids):
                return {s.source_id: s for s in self.facts.catalog_sources if s.source_id in source_ids}

        researcher = DurableResourceResearcher(
            self.calls,
            github=github,
            web=web,
            body_reader=body,
            llm=self.calls,
            reviewed_index=self.facts.reviewed_index,
            catalog=Catalog(),
            access_proofs=self.facts.access_proofs,
            domain_approvals=approvals,
        )
        research = researcher.research(
            gaps,
            plan=plan,
            coverage=coverage,
            profile=profile,
            session=session,
            scope=self.calls.scope,
            project_id=self.calls.project_id,
            checked_at=manifest["checked_at"],
        )
        if session.blocked:
            with self.calls.tx() as conn:
                pending = conn.execute(
                    "SELECT 1 FROM ai_provider_attempts WHERE run_id=%s AND status IN('dispatched','reconciliation_required') LIMIT 1",
                    (self.calls.run_id,),
                ).fetchone()
                failed = conn.execute(
                    "SELECT error_class FROM ai_provider_attempts WHERE run_id=%s AND status='failed' ORDER BY created_at DESC,attempt_id DESC LIMIT 1",
                    (self.calls.run_id,),
                ).fetchone()
            return LLMFailure(
                "research_reconciliation_required"
                if pending
                else failed["error_class"]
                if failed
                else "research_failed",
                "Research stopped conservatively",
                dispatch_unknown=bool(pending),
            )
        # Count local candidate admission too; the per-request durable ledger
        # remains the authority for all external dispatch metrics.
        save("resource_research", research_snapshot=wire(asdict(session.snapshot())))
        context = prepare_curriculum(
            profile,
            plan,
            coverage,
            research,
            self.facts.reviewed_index,
            catalog_sources=self.facts.catalog_sources,
            access_proofs=self.facts.access_proofs,
            project_cases=self.facts.project_cases,
            domain_approvals=approvals,
        )
        if state.get("curriculum"):
            doc = state["curriculum"]
            curriculum = CurriculumPlan(doc["json"], doc["findings"])
        else:
            composer = CurriculumComposer(
                self.calls,
                project_index=DurableIndex(self.calls, self.project_index, "project-case")
                if self.project_index
                else None,
            )
            curriculum = composer.compose(
                context,
                session=session,
                scope=self.calls.scope,
                project_id=self.calls.project_id,
                attempt_id="curriculum-composition",
            )
            if not isinstance(curriculum, CurriculumPlan):
                return curriculum
            save(
                "curriculum_composition",
                curriculum={"json": curriculum._json, "findings": curriculum._findings},
            )
        try:
            compiled = compile_curriculum(
                curriculum, context=context, profile=profile, capability_plan=plan, source_facts=self.facts
            )
        except ValidationAppError as error:
            if error.details.get("field") != "incomplete":
                raise
            # Compiler has already revalidated authorities, server snapshots and
            # case findings. Only its bounded diagnostics may become public facts.
            import psycopg
            from app.infrastructure.db.v2_clarifications import freeze_planning_issues
            from app.ports.summaries import ReviewPersistenceInterrupted
            try:
                freeze_planning_issues(self.calls, curriculum, diagnostics=error.details["diagnostics"])
            except psycopg.Error:
                raise ReviewPersistenceInterrupted("Incomplete facts persistence interrupted") from None
            return LLMFailure("v2_curriculum_incomplete", "Validated curriculum remains incomplete")
        save("deterministic_compiler", compiled_digest=compiled.digest)
        self.calls.guard()
        import psycopg

        try:
            draft = self.persistence.persist(
                scope=self.calls.scope,
                project_id=self.calls.project_id,
                run_id=self.calls.run_id,
                expected_version=manifest["expected_version"],
                curriculum=curriculum,
                context=context,
                profile=profile,
                capability_plan=plan,
                source_facts=self.facts,
                write_fence=self.calls.fence,
                v2_revision=revision,
            )
        except psycopg.Error:
            from app.ports.summaries import ReviewPersistenceInterrupted

            raise ReviewPersistenceInterrupted("V2 Draft transaction interrupted") from None
        save("draft_persistence", draft_id=draft.draft_id)
        return draft

    def _verify_domains(self, profile, requested):
        from app.application.domain_verification import DomainVerifier
        from app.domain.planning.domain_verification import _issue_approval, verification_session_hash

        sources = [s for s in self.domain_sources if requested & {d.capability_id for d in s.capabilities}]
        if (
            not sources
            or requested - {d.capability_id for s in sources for d in s.capabilities}
            or self.body_reader is None
        ):
            return ()
        approvals = []
        for source in sources:
            budget = ResearchBudget(**self.calls.manifest["budget"])

            def invoke(ident, source=source, budget=budget):
                session = ResearchSession(
                    self.calls.run_id,
                    verification_session_hash(
                        profile,
                        source,
                        budget=budget,
                        actor_id=self.calls.scope.actor_id,
                        project_id=self.calls.project_id,
                    ),
                    budget,
                )
                session.usage.update(self.calls.usage())
                # The durable parent reservation already committed; Item2's
                # existing producer must reserve that same operation locally,
                # so its starting usage excludes only this call's worst debit.
                session.usage["total_requests"] -= 2
                session.usage["body_bytes"] -= 65536
                return DomainVerifier(self.body_reader, sources=(source,)).verify(
                    profile,
                    source_id=source.source_id,
                    session=session,
                    scope=self.calls.scope,
                    project_id=self.calls.project_id,
                )

            def encode(result, source=source):
                measured = {"total_requests": result.requests, "body_bytes": result.bytes_read}
                if result.status != "verified" or result.approval is None:
                    return {
                        "kind": "failure",
                        "value": asdict(
                            LLMFailure(
                                "domain_verification_" + result.status,
                                "Domain verification incomplete",
                                dispatch_unknown=result.status == "unknown",
                            )
                        ),
                    }, measured
                return {
                    "kind": "domain_verification",
                    "value": {
                        "profile_hash": profile.profile_hash,
                        "source_hash": source.source_hash,
                        "evidence": result.evidence.to_payload(),
                        "approval_hash": result.approval.approval_hash,
                    },
                }, measured

            data = self.calls.call(
                step="domain-" + source.source_id,
                purpose="domain.verification",
                schema="V2DomainVerificationReceiptV1",
                payload={"profile_hash": profile.profile_hash, "source_hash": source.source_hash},
                reserved={"total_requests": 2, "body_bytes": 65536},
                invoke=invoke,
                encode=encode,
            )
            if data["kind"] == "failure":
                if data["value"].get("dispatch_unknown"):
                    raise V2RecoveryBlocked("Domain verification outcome unknown")
                return ()
            # Authority comes from the current trusted registry AND a validated
            # server durable success receipt, never from JSON issuer data.
            approval = _issue_approval(profile, source)
            if data["value"] != {
                "profile_hash": profile.profile_hash,
                "source_hash": source.source_hash,
                "evidence": approval.evidence.to_payload(),
                "approval_hash": approval.approval_hash,
            }:
                raise V2RecoveryBlocked("Trusted domain verification receipt mismatch")
            approvals.append(approval)
        return tuple(approvals)
