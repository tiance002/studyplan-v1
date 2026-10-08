"""V2 namespace over the existing attempt/event ledger, with one shared budget.

Request bodies are fingerprinted, never retained. Reservations commit before
dispatch; successful receipts are immutable and unknown outcomes never retry.
The budget retains the worst reservation (or a larger observed lower bound),
so restart, missing usage and local ResearchSession settlement cannot refund it.
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from dataclasses import asdict

import psycopg
from app.core.errors import ConflictError, ValidationAppError
from app.core.ids import content_hash
from app.domain.planning.research_reader import READER_PURPOSE, validate_reader_output
from app.domain.planning.resource_research import (
    METRICS,
    ResearchEvidenceRef,
    ResearchResource,
)
from app.domain.planning.v2_runtime import (
    PURPOSE_SCHEMAS,
    V2_EXECUTION_VERSION,
    V2BudgetExceeded,
    V2RecoveryBlocked,
    manifest_intact,
    wire,
)
from app.infrastructure.db.plan_repository import to_psycopg_dsn
from app.infrastructure.db.planning_fence import lock_plan_version, lock_planning_write
from app.ports.llm import LLMFailure, LLMNotDispatchedError, LLMResult
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


class PgV2Calls:
    def __init__(
        self,
        dsn,
        *,
        scope,
        project_id,
        run_id,
        manifest,
        fence,
        provider,
        guard=lambda: None,
        domain_approvals=(),
    ):
        scope.require_project(project_id)
        if (
            not manifest_intact(manifest)
            or fence is None
            or fence.run_id != run_id
            or fence.project_id != project_id
            or fence.actor_id != scope.actor_id
            or getattr(provider, "configuration_ref", None) != manifest["model_ref"]
        ):
            raise ValidationAppError("V2 dispatch requires frozen configuration and current scope/fence")
        self.dsn, self.scope, self.project_id, self.run_id = to_psycopg_dsn(dsn), scope, project_id, run_id
        self.manifest = json.loads(json.dumps(manifest))
        self.fence, self.provider, self.guard = fence, provider, guard
        self.domain_approvals = tuple(domain_approvals)
        self.current_body = None

    @contextmanager
    def tx(self):
        with psycopg.connect(self.dsn, row_factory=dict_row) as conn:
            conn.execute(
                "SELECT set_config('app.project_id',%s,true),set_config('app.actor_id',%s,true)",
                (self.project_id, self.scope.actor_id),
            )
            yield conn

    def _lock(self, conn, *, published_draft_id=None):
        from app.domain.planning.revisions import V2RevisionContext
        from app.infrastructure.db.v2_revisions import (
            budget_family,
            frozen_submission,
            published_v2_draft,
            validate_semantic_input,
        )
        submission = frozen_submission(conn, actor_id=self.scope.actor_id, project_id=self.project_id, run_id=self.run_id)
        context = V2RevisionContext.from_payload(submission["initial"].get("v2_revision"))
        root = context.to_payload()["budget_root_run_id"] if context else self.run_id
        conn.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", ("studyplan:plan-budget:" + root,)
        )
        self.budget_root_run_id = root
        budget_family(conn, actor_id=self.scope.actor_id, project_id=self.project_id, run_id=self.run_id)
        lock_plan_version(conn, self.project_id, None)
        lock_planning_write(conn, project_id=self.project_id, run_id=self.run_id, fence=self.fence)
        run = conn.execute(
            "SELECT graph_version,kind FROM ai_runs WHERE run_id=%s", (self.run_id,)
        ).fetchone()
        if run is None or run["graph_version"] != V2_EXECUTION_VERSION or run["kind"] != "plan_generate":
            raise ConflictError("V2 run version mismatch")
        submissions = conn.execute(
            "SELECT detail FROM ai_run_events WHERE run_id=%s AND status='submission' AND detail->>'kind'='planning_submission' ORDER BY event_id",
            (self.run_id,),
        ).fetchall()
        if (
            len(submissions) != 1
            or submissions[0]["detail"].get("actor_id") != self.scope.actor_id
            or submissions[0]["detail"].get("project_id") != self.project_id
            or submissions[0]["detail"].get("manifest") != self.manifest
            or submissions[0]["detail"].get("initial", {}).get("manifest") != self.manifest
        ):
            raise V2RecoveryBlocked("V2 dispatch differs from server-persisted frozen submission")
        own_published = published_draft_id is not None and published_v2_draft(conn,
            actor_id=self.scope.actor_id, project_id=self.project_id, run_id=self.run_id, draft_id=published_draft_id)
        if context is not None and not own_published:
            validate_semantic_input(conn, actor_id=self.scope.actor_id, project_id=self.project_id,
                run_id=self.run_id, manifest=self.manifest, context=context)
        elif context is None and not own_published:
            lock_plan_version(conn, self.project_id, 0)

    def _reservations(self, conn, *, related_only=False):
        from app.infrastructure.db.v2_revisions import budget_family
        _, manifests = budget_family(conn, actor_id=self.scope.actor_id, project_id=self.project_id, run_id=self.run_id)
        run_ids = [run for run in manifests if not related_only or run != self.run_id]
        rows = conn.execute(
            "SELECT run_id,detail FROM ai_run_events WHERE run_id=ANY(%s) AND status='v2_reservation' ORDER BY event_id",
            (run_ids,),
        ).fetchall()
        usage = dict.fromkeys(METRICS, 0)
        seen = set()
        for row in rows:
            d = row["detail"]
            if (
                d.get("manifest_hash") != manifests[row["run_id"]]["manifest_hash"]
                or d.get("run_id") != row["run_id"]
                or d.get("digest") != content_hash({k: v for k, v in d.items() if k != "digest"})
                or d["attempt_id"] in seen
                or set(d["reserved"]) - set(METRICS)
            ):
                raise V2RecoveryBlocked("V2 reservation identity/integrity mismatch")
            seen.add(d["attempt_id"])
            for metric, value in d["reserved"].items():
                if type(value) is not int or not 0 <= value <= 10**12:
                    raise V2RecoveryBlocked("V2 reservation metric invalid")
                usage[metric] += value
        excess = conn.execute(
            "SELECT run_id,detail FROM ai_run_events WHERE run_id=ANY(%s) AND status='v2_observed_excess'", (run_ids,)
        ).fetchall()
        for row in excess:
            d = row["detail"]
            if d.get("manifest_hash") != manifests[row["run_id"]]["manifest_hash"] or d.get("digest") != content_hash(
                {k: v for k, v in d.items() if k != "digest"}
            ):
                raise V2RecoveryBlocked("V2 observed budget integrity mismatch")
            for metric, value in d["excess"].items():
                if metric not in METRICS or type(value) is not int or not 0 <= value <= 10**12:
                    raise V2RecoveryBlocked("V2 observed budget invalid")
                usage[metric] += value
        candidates = conn.execute(
            "SELECT run_id,detail FROM ai_run_events WHERE run_id=ANY(%s) AND status='v2_candidate_admission'",
            (run_ids,),
        ).fetchall()
        seen = set()
        for row in candidates:
            d = row["detail"]
            if (
                d.get("manifest_hash") != manifests[row["run_id"]]["manifest_hash"]
                or d.get("digest") != content_hash({k: v for k, v in d.items() if k != "digest"})
                or d.get("identity") in seen
            ):
                raise V2RecoveryBlocked("V2 candidate admission integrity mismatch")
            seen.add(d["identity"])
            usage["candidates"] += 1
        return usage

    def _budget_manifests(self, conn):
        from app.infrastructure.db.v2_revisions import budget_family
        return budget_family(conn, actor_id=self.scope.actor_id, project_id=self.project_id, run_id=self.run_id)[1]

    def admit_candidate(self, url):
        identity = content_hash({"run_id": self.run_id, "candidate_url": url})
        with self.tx() as conn:
            self._lock(conn)
            existing = conn.execute(
                "SELECT detail FROM ai_run_events WHERE run_id=%s AND status='v2_candidate_admission' AND detail->>'identity'=%s",
                (self.run_id, identity),
            ).fetchall()
            if existing:
                self._reservations(conn)
                if len(existing) != 1:
                    raise V2RecoveryBlocked("Candidate admission is ambiguous")
                return
            usage = self._reservations(conn)
            if usage["candidates"] + 1 > self.manifest["budget"]["max_candidates"]:
                raise V2BudgetExceeded()
            detail = {
                "identity": identity,
                "run_id": self.run_id,
                "manifest_hash": self.manifest["manifest_hash"],
                "url_hash": content_hash(url),
            }
            detail["digest"] = content_hash(detail)
            conn.execute(
                "INSERT INTO ai_run_events(run_id,status,detail) VALUES(%s,'v2_candidate_admission',%s)",
                (self.run_id, Jsonb(detail)),
            )

    def usage(self, *, related_only=False):
        with self.tx() as conn:
            return self._reservations(conn, related_only=related_only)

    def _identity(self, step, purpose, schema, payload, options):
        facts = {
            "run_id": self.run_id,
            "step": step,
            "purpose": purpose,
            "schema": schema,
            "input_hash": content_hash(wire(payload)),
            "manifest_hash": self.manifest["manifest_hash"],
            "config_hash": content_hash(
                {
                    "model_ref": self.manifest["model_ref"],
                    "model": getattr(self.provider, "model", ""),
                    "options": options,
                }
            ),
            "source_versions_hash": self.manifest["source_facts_hash"],
        }
        return facts, content_hash(facts)

    def _retained(self, row, identity):
        if row["run_id"] != self.run_id or row["request_fingerprint"] != identity:
            raise V2RecoveryBlocked("V2 attempt identity conflict")
        if row["status"] in {"dispatched", "reconciliation_required"}:
            return {
                "kind": "failure",
                "value": asdict(
                    LLMFailure("attempt_dispatch_unknown", "Reconciliation required", dispatch_unknown=True)
                ),
            }
        with self.tx() as conn:
            reservations = conn.execute(
                "SELECT detail FROM ai_run_events WHERE run_id=%s AND attempt_id=%s AND status='v2_reservation'",
                (self.run_id, row["attempt_id"]),
            ).fetchall()
            overrun = conn.execute(
                "SELECT 1 FROM ai_run_events WHERE run_id=%s AND attempt_id=%s AND status='v2_observed_excess' LIMIT 1",
                (self.run_id, row["attempt_id"]),
            ).fetchone()
        if len(reservations) != 1:
            raise V2RecoveryBlocked("V2 receipt reservation missing or ambiguous")
        reserved = reservations[0]["detail"]
        facts = {
            k: reserved[k]
            for k in (
                "run_id",
                "step",
                "purpose",
                "schema",
                "input_hash",
                "manifest_hash",
                "config_hash",
                "source_versions_hash",
            )
        }
        if (
            content_hash(facts) != identity
            or reserved.get("digest") != content_hash({k: v for k, v in reserved.items() if k != "digest"})
            or row["schema_name"] != reserved["schema"]
            or row["provider"] != "v2:" + reserved["purpose"]
        ):
            raise V2RecoveryBlocked("V2 receipt purpose/schema/source binding mismatch")
        if overrun:
            raise V2BudgetExceeded()
        data = row["response_payload"]
        if (
            type(data) is not dict
            or data.get("identity") != identity
            or data.get("manifest_hash") != self.manifest["manifest_hash"]
            or data.get("digest") != content_hash({k: v for k, v in data.items() if k != "digest"})
            or (row["status"] == "succeeded") != (data.get("kind") not in {"failure"})
        ):
            raise V2RecoveryBlocked("V2 receipt integrity mismatch")
        return data

    def call(self, *, step, purpose, schema, payload, reserved, invoke, encode, options=None):
        self.guard()
        facts, identity = self._identity(step, purpose, schema, payload, options or {})
        attempt = self.run_id + ":v2:" + step + ":" + identity[:24]
        with self.tx() as conn:
            self._lock(conn)
            old = conn.execute(
                "SELECT * FROM ai_provider_attempts WHERE attempt_id=%s", (attempt,)
            ).fetchone()
            if old is not None:
                return self._retained(old, identity)
            if conn.execute(
                "SELECT 1 FROM ai_provider_attempts WHERE run_id=ANY(%s) AND status IN('dispatched','reconciliation_required') LIMIT 1",
                (list(self._budget_manifests(conn)),),
            ).fetchone():
                raise V2RecoveryBlocked("Uncertain V2 dispatch blocks every new identity")
            usage = self._reservations(conn)
            if set(reserved) - set(METRICS) or any(
                type(v) is not int or v < 0 or usage[k] + v > self.manifest["budget"]["max_" + k]
                for k, v in reserved.items()
            ):
                raise V2BudgetExceeded()
            detail = facts | {"attempt_id": attempt, "reserved": reserved}
            detail["digest"] = content_hash(detail)
            conn.execute(
                "INSERT INTO ai_run_events(run_id,node_name,attempt_id,status,detail) VALUES(%s,%s,%s,'v2_reservation',%s)",
                (self.run_id, step, attempt, Jsonb(detail)),
            )
            conn.execute(
                "INSERT INTO ai_provider_attempts(attempt_id,run_id,provider,model_id,prompt_version,status,request_fingerprint,schema_name) VALUES(%s,%s,%s,%s,%s,'dispatched',%s,%s)",
                (
                    attempt,
                    self.run_id,
                    "v2:" + purpose,
                    getattr(self.provider, "model", "external"),
                    V2_EXECUTION_VERSION,
                    identity,
                    schema,
                ),
            )
        # Both the request identity and all worst debits are committed now.
        try:
            self.active_dispatch = {"attempt_id": attempt, "reserved": reserved, "children": 0}
            value = invoke(attempt)
            data, measured = encode(value)
        except LLMNotDispatchedError:
            data, measured = (
                {
                    "kind": "failure",
                    "value": asdict(LLMFailure("provider_not_dispatched", "Provider preflight rejected")),
                },
                {},
            )
        except V2BudgetExceeded:
            data, measured = (
                {
                    "kind": "failure",
                    "value": asdict(
                        LLMFailure("v2_budget_exceeded", "V2 frozen budget rejected continuation")
                    ),
                },
                {},
            )
        except Exception:
            data, measured = (
                {
                    "kind": "failure",
                    "value": asdict(
                        LLMFailure(
                            "provider_exception_unknown", "Reconciliation required", dispatch_unknown=True
                        )
                    ),
                },
                {},
            )
        finally:
            self.active_dispatch = None
        measured = {
            k: v if type(v) is int and 0 <= v <= 10**12 else None for k, v in measured.items() if k in METRICS
        }
        data = wire(data | {"identity": identity, "manifest_hash": self.manifest["manifest_hash"]})
        data["digest"] = content_hash(data)
        unknown = data["kind"] == "failure" and data["value"].get("dispatch_unknown") is True
        status = (
            "reconciliation_required" if unknown else "failed" if data["kind"] == "failure" else "succeeded"
        )
        excess = {
            k: max(0, v - reserved.get(k, 0))
            for k, v in measured.items()
            if k in METRICS and type(v) is int and v >= 0
        }
        with self.tx() as conn:
            conn.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s,0))",
                ("studyplan:plan-budget:" + self.budget_root_run_id,),
            )
            cursor = conn.execute(
                "UPDATE ai_provider_attempts SET status=%s,response_payload=%s,error_class=%s,output_tokens=%s,cost_micros=%s WHERE attempt_id=%s AND run_id=%s AND status='dispatched'",
                (
                    status,
                    Jsonb(data),
                    data["value"].get("error_class") if data["kind"] == "failure" else None,
                    measured.get("output_tokens")
                    if type(measured.get("output_tokens")) is int
                    and measured["output_tokens"] <= 2_000_000_000
                    else None,
                    measured.get("cost_micros"),
                    attempt,
                    self.run_id,
                ),
            )
            if cursor.rowcount != 1:
                raise V2RecoveryBlocked("V2 receipt persistence conflict")
            if any(excess.values()):
                d = {"manifest_hash": self.manifest["manifest_hash"], "attempt_id": attempt, "excess": excess}
                d["digest"] = content_hash(d)
                conn.execute(
                    "INSERT INTO ai_run_events(run_id,attempt_id,status,detail) VALUES(%s,%s,'v2_observed_excess',%s)",
                    (self.run_id, attempt, Jsonb(d)),
                )
        # Receipts may retain a late result for reconciliation; current business
        # state and checkpoints require the still-live lease after the call.
        self.guard()
        with self.tx() as conn:
            self._lock(conn)
        if any(excess.values()):
            raise V2BudgetExceeded()
        return data

    def request_options(self, purpose):
        return self.provider.request_options(purpose)

    def generate_structured(self, *, purpose, payload, schema_name, run_id, attempt_id):
        # Existing Item5/6 distinguish typed known failures from dispatch
        # exceptions. A local durable budget rejection has no unknown outcome.
        try:
            return self._generate_structured(
                purpose=purpose,
                payload=payload,
                schema_name=schema_name,
                run_id=run_id,
                attempt_id=attempt_id,
            )
        except V2BudgetExceeded:
            return LLMFailure("v2_budget_exceeded", "V2 frozen budget rejected continuation")

    def _generate_structured(self, *, purpose, payload, schema_name, run_id, attempt_id):
        if run_id != self.run_id or PURPOSE_SCHEMAS.get(purpose) != schema_name:
            raise ValidationAppError("V2 purpose/schema/run mismatch")
        options = self.request_options(purpose)
        cap = options.get("max_tokens")
        if type(cap) is not int or not 0 < cap <= self.manifest["output_caps"][purpose]:
            raise V2BudgetExceeded()
        reserved = {
            "total_requests": 1,
            "output_tokens": cap,
            "cost_micros": self.manifest["budget"]["reader_cost_micros"],
        }
        if purpose == READER_PURPOSE:
            reserved["reader_requests"] = 1

        def encode(result):
            measured = {
                "output_tokens": getattr(result, "output_tokens", None),
                "cost_micros": getattr(result, "cost_micros", None),
            }

            def amount(value):
                return value if type(value) is int and 0 <= value <= 2_000_000_000 else None

            if isinstance(result, LLMFailure):
                import re

                code = (
                    (
                        result.error_class
                        if result.error_class
                        in {
                            "provider_output_truncated",
                            "provider_invalid_json",
                            "endpoint_preflight_rejected",
                        }
                        else "reader_provider_failed"
                    )
                    if purpose == READER_PURPOSE
                    else result.error_class
                )
                if not isinstance(code, str) or not re.fullmatch(r"[a-z_]{1,80}", code):
                    code = "provider_failed"
                safe = LLMFailure(
                    code,
                    "V2 provider failed",
                    dispatch_unknown=result.dispatch_unknown is True,
                    input_tokens=amount(result.input_tokens),
                    output_tokens=amount(result.output_tokens),
                    latency_ms=amount(result.latency_ms),
                )
                return {"kind": "failure", "value": asdict(safe)}, measured
            if type(result) is not LLMResult:
                return {
                    "kind": "failure",
                    "value": asdict(
                        LLMFailure(
                            "provider_response_unknown", "Reconciliation required", dispatch_unknown=True
                        )
                    ),
                }, measured
            if result.finish_reason == "length":
                return {
                    "kind": "failure",
                    "value": asdict(
                        LLMFailure(
                            "provider_output_truncated",
                            "Provider output truncated",
                            input_tokens=amount(result.input_tokens),
                            output_tokens=amount(result.output_tokens),
                        )
                    ),
                }, measured
            extra = {}
            if purpose == READER_PURPOSE:
                try:
                    validate_reader_output(result.payload, payload, domain_approvals=self.domain_approvals)
                    extra["inspection"] = self._inspection(result, payload)
                except (ValueError, TypeError, KeyError, ValidationAppError):
                    return {
                        "kind": "failure",
                        "value": asdict(
                            LLMFailure(
                                "reader_privacy_or_schema_invalid",
                                "Reader response rejected",
                                input_tokens=amount(result.input_tokens),
                                output_tokens=amount(result.output_tokens),
                            )
                        ),
                    }, measured
            # Provider envelope strings are untrusted too: a valid Reader
            # payload cannot authorize body text in model/finish/diagnostics.
            safe = LLMResult(
                result.payload,
                getattr(self.provider, "model", "configured"),
                "v2",
                input_tokens=amount(result.input_tokens),
                output_tokens=amount(result.output_tokens),
                cost_micros=amount(result.cost_micros),
                latency_ms=amount(result.latency_ms) or 0,
                finish_reason="stop",
                attempts=1,
                diagnostics={},
            )
            return {"kind": "llm", "value": asdict(safe), **extra}, measured

        data = self.call(
            step=attempt_id,
            purpose=purpose,
            schema=schema_name,
            payload=payload,
            reserved=reserved,
            options=options,
            invoke=lambda ident: self.provider.generate_structured(
                purpose=purpose, payload=payload, schema_name=schema_name, run_id=run_id, attempt_id=ident
            ),
            encode=encode,
        )
        return LLMFailure(**data["value"]) if data["kind"] == "failure" else LLMResult(**data["value"])

    def _inspection(self, result, payload):
        verdict = result.payload
        body = self.current_body
        if body is None:
            raise ValueError("Reader has no bound transient body")
        fit = verdict["teaching_fit"]
        acceptable = all(
            fit[k] == v
            for k, v in {
                "continuity": "sufficient",
                "beginner_fit": "suitable",
                "examples": "present",
                "version_fit": "compatible",
            }.items()
        )
        chunks = {c["chunk_id"]: c for c in body.chunks}
        refs = tuple(
            ResearchEvidenceRef(
                o["outcome_id"], r["chunk_id"], r["content_hash"], chunks[r["chunk_id"]]["location"], "body"
            )
            for o in verdict["outcomes"]
            if o["status"] == "supported"
            for r in o["evidence_refs"]
        )
        limits = tuple(sorted({v for o in verdict["outcomes"] for v in o["limitations"]}))[:12]
        resource = ResearchResource(
            body.resource_id,
            body.url,
            body.version,
            self.manifest["checked_at"],
            "confirmed",
            "research_checked",
            refs,
            tuple(sorted(fit.items())),
            limits,
        )
        return {
            "candidate_url": self.current_candidate_url,
            "must_teach": payload["must_teach"],
            "body_chunks": [
                {k: c[k] for k in ("chunk_id", "resource_id", "version", "content_hash", "location")}
                for c in body.chunks
            ],
            "resource": wire(asdict(resource)) if acceptable else None,
            "body_usage": {"total_requests": body.requests, "body_bytes": body.bytes_read},
            "reader_usage": {
                "total_requests": 1,
                "reader_requests": 1,
                "output_tokens": result.output_tokens,
                "cost_micros": result.cost_micros,
            },
            "reasons": []
            if acceptable and len({r.outcome_id for r in refs}) == len(payload["must_teach"])
            else ["outcomes_unresolved" if acceptable else "teaching_fit_unresolved"],
        }

    def inspected(self, candidate_url, remaining):
        wanted = wire([asdict(o) for o in remaining])
        with self.tx() as conn:
            rows = conn.execute(
                "SELECT * FROM ai_provider_attempts WHERE run_id=%s AND provider=%s AND status='succeeded' ORDER BY created_at,attempt_id",
                (self.run_id, "v2:" + READER_PURPOSE),
            ).fetchall()
            for row in rows:
                d = self._retained(row, row["request_fingerprint"])
                item = d.get("inspection")
                if item and item["candidate_url"] == candidate_url and item["must_teach"] == wanted:
                    from app.domain.planning.v2_execution import _decode

                    return (
                        () if item["resource"] is None else (_decode(ResearchResource, item["resource"]),),
                        tuple(item["reasons"]),
                        item,
                    )
        return None
