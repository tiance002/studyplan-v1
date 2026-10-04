"""Paid attempts are durable before dispatch and replay only retained results."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict

import psycopg
from app.agent_workflows.planning_batches import (
    REPAIR_PURPOSE,
    SHORT_GENERATION_VERSION,
    allowed_attempt_keys,
    attempt_purpose,
    attempt_stage,
    budget_violation,
    manifest_is_intact,
    output_budget_for,
)
from app.domain.prompts import PROMPT_PROTOCOL, PROMPT_PURPOSE, prompt_manifest_intact
from app.domain.runs.fencing import PlanningWriteFence
from app.domain.summaries import SUMMARY_PROTOCOL, SUMMARY_PURPOSE, summary_manifest_intact
from app.infrastructure.db.plan_repository import to_psycopg_dsn
from app.infrastructure.db.planning_fence import lock_plan_version, lock_planning_write
from app.ports.llm import LLMDispatchUnknownError, LLMFailure, LLMNotDispatchedError, LLMResult
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

REVIEW_PROTOCOLS = {
    SUMMARY_PURPOSE: (SUMMARY_PROTOCOL, summary_manifest_intact, "_summary_claim", ":summary_review:1", "summary_review"),
    PROMPT_PURPOSE: (PROMPT_PROTOCOL, prompt_manifest_intact, "_prompt_claim", ":prompt_review:1", "prompt_review"),
}


class PgAttemptLLM:
    def __init__(self, dsn, provider, *, manifest=None):
        self.dsn = to_psycopg_dsn(dsn)
        self.provider = provider
        #: Frozen execution manifest; when present every dispatch is budget-guarded.
        self.manifest = manifest

    def _connect(self, project_id):
        conn = psycopg.connect(self.dsn, row_factory=dict_row)
        conn.execute("SELECT set_config('app.project_id', %s, true)", (project_id,))
        return conn

    def _budget_rejection(self, conn, *, run_id, attempt_id, purpose):
        """Return a rejection reason before any paid dispatch, or ``None``.

        Runs inside the same transaction that records the attempt, so the count
        of unique attempts and the reserved output budget are consistent with the
        row we are about to insert. A replay of an existing attempt never consumes
        fresh quota, and an unknown/unregistered key can never bypass the frozen
        batch catalog.
        """
        if self.manifest is None:
            if purpose in REVIEW_PROTOCOLS:
                return "run_manifest_violation"
            conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (f"studyplan:plan-budget:{run_id}",))
            retained = conn.execute(
                "SELECT 1 FROM ai_provider_attempts WHERE attempt_id=%s AND run_id=%s",
                (attempt_id, run_id),
            ).fetchone()
            if retained is None:
                run = conn.execute(
                    "SELECT graph_version,EXISTS(SELECT 1 FROM ai_jobs j WHERE j.run_id=r.run_id) AS has_job "
                    "FROM ai_runs r WHERE r.run_id=%s", (run_id,),
                ).fetchone()
                if run is not None and (run["has_job"] or run["graph_version"] == SHORT_GENERATION_VERSION):
                    return "run_manifest_violation"
            return None
        if purpose in REVIEW_PROTOCOLS or self.manifest.get("protocol") in {SUMMARY_PROTOCOL, PROMPT_PROTOCOL}:
            protocol, valid, _, suffix, _ = REVIEW_PROTOCOLS.get(purpose, (None, lambda value: False, None, "", None))
            if (not valid(self.manifest)
                    or attempt_id != run_id + suffix
                    or self.provider.prompt_version != protocol
                    or self.provider.configuration_ref != self.manifest["model_ref"]):
                return "run_manifest_violation"
            conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (f"studyplan:plan-budget:{run_id}",))
            rows = conn.execute("SELECT attempt_id FROM ai_provider_attempts WHERE run_id=%s", (run_id,)).fetchall()
            if any(row["attempt_id"] != attempt_id for row in rows) or len(rows) > 1:
                return "run_budget_exceeded"
            options = self.provider.request_options(purpose)
            if type(options.get("max_tokens")) is not int or not 0 < options["max_tokens"] <= self.manifest["output_cap"]:
                return "run_budget_exceeded"
            return None
        if not manifest_is_intact(self.manifest):
            return "run_manifest_violation"
        if attempt_id not in allowed_attempt_keys(run_id, self.manifest):
            return "run_manifest_violation"
        if attempt_purpose(attempt_id) != purpose:
            return "run_manifest_violation"
        conn.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
            (f"studyplan:plan-budget:{run_id}",),
        )
        existing = conn.execute(
            "SELECT 1 FROM ai_provider_attempts WHERE attempt_id=%s AND run_id=%s",
            (attempt_id, run_id),
        ).fetchone()
        if existing is not None:
            return None  # Replay: counted once, never charged twice.
        options = self.provider.request_options(purpose)
        output_cap = output_budget_for(self.manifest, purpose)
        if type(options.get("max_tokens")) is not int or not 0 < options["max_tokens"] <= output_cap:
            return "run_budget_exhausted"
        rows = conn.execute(
            "SELECT attempt_id FROM ai_provider_attempts WHERE run_id=%s", (run_id,)
        ).fetchall()
        keys = {str(row["attempt_id"]) for row in rows}
        if purpose == REPAIR_PURPOSE and sum(
            attempt_purpose(key) == REPAIR_PURPOSE for key in keys
        ) >= int(self.manifest["max_repairs"]):
            return "run_budget_exhausted"
        reserved = sum(output_budget_for(self.manifest, attempt_purpose(key)) for key in keys)
        reserved += output_budget_for(self.manifest, purpose)
        return budget_violation(
            self.manifest,
            request_count=len(keys),
            reserved_output=reserved,
            stage_key=attempt_stage(attempt_id),
            purpose=purpose,
        )

    def generate_structured(self, *, purpose, payload, schema_name, run_id, attempt_id):
        rejected = self.preflight(purpose=purpose,payload=payload,schema_name=schema_name)
        if rejected is not None:
            return rejected
        project_id = str(payload.get("_project_id") or "")
        request_options = self.provider.request_options(purpose)
        transient_keys = {"_planning_claim"}
        if purpose in REVIEW_PROTOCOLS:
            transient_keys.add(REVIEW_PROTOCOLS[purpose][2])
        semantic_payload = {k: v for k, v in payload.items() if k not in transient_keys}
        identity = [purpose,semantic_payload,schema_name,self.provider.model,self.provider.prompt_version,
                    self.provider.domain_pack,request_options,self.provider.budget_policy.as_dict()]
        fingerprint = hashlib.sha256(json.dumps([*identity,self.provider.base_url,self.provider.configuration_ref], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        # Preserve replay of pre-budget deployment attempts. This fingerprint is
        # only used to read an existing result; it never authorizes a new dispatch.
        legacy_identity = [purpose,semantic_payload,schema_name,self.provider.model,
                          self.provider.prompt_version,self.provider.domain_pack]
        legacy_fingerprint = hashlib.sha256(json.dumps(legacy_identity, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        with self._connect(project_id) as conn:
            rejection = self._budget_rejection(conn, run_id=run_id, attempt_id=attempt_id, purpose=purpose)
            if rejection is not None:
                return LLMFailure(rejection, "Run budget or manifest guard rejected this dispatch")
            if purpose not in REVIEW_PROTOCOLS:
                retained = conn.execute("SELECT * FROM ai_provider_attempts WHERE attempt_id=%s", (attempt_id,)).fetchone()
                if retained is not None:
                    # Reading an already retained receipt needs no live lease.
                    # Business writes still require their own live write fence.
                    return self._retained_result(retained, run_id, fingerprint, legacy_fingerprint)
                run = conn.execute(
                    "SELECT kind,graph_version,EXISTS(SELECT 1 FROM ai_jobs j WHERE j.run_id=r.run_id) AS has_job "
                    "FROM ai_runs r WHERE r.run_id=%s", (run_id,),
                ).fetchone()
                if run is None or run["kind"] != "plan_generate":
                    return LLMFailure("run_manifest_violation", "Planning run protocol mismatch")
                if run["has_job"] or run["graph_version"] == SHORT_GENERATION_VERSION:
                    raw_fence = payload.get("_planning_claim")
                    fields = {"job_id", "run_id", "project_id", "actor_id", "lease_token"}
                    if (not isinstance(raw_fence, dict) or set(raw_fence) != fields
                            or any(not isinstance(value, str) or not value for value in raw_fence.values())):
                        return LLMFailure("planning_claim_missing", "Planning dispatch requires its exact live server claim")
                    fence = PlanningWriteFence(**raw_fence)
                    # Cancellation uses this same order: budget advisory, project
                    # decision advisory, then live job/run/project row locks.
                    lock_plan_version(conn, project_id, None)
                    lock_planning_write(conn, project_id=project_id, run_id=run_id, fence=fence)
            if purpose in REVIEW_PROTOCOLS:
                protocol, _, claim_key, _, kind = REVIEW_PROTOCOLS[purpose]
                raw_fence = payload.get(claim_key)
                if not isinstance(raw_fence, dict) or set(raw_fence) != {"job_id", "run_id", "project_id", "actor_id", "lease_token"}:
                    return LLMFailure("summary_claim_missing" if purpose == SUMMARY_PURPOSE else "prompt_claim_missing", "Review dispatch requires its exact live server claim")
                fence = PlanningWriteFence(**raw_fence)
                lock_plan_version(conn, project_id, None)
                lock_planning_write(conn, project_id=project_id, run_id=run_id, fence=fence)
                run = conn.execute("SELECT kind,graph_version FROM ai_runs WHERE run_id=%s", (run_id,)).fetchone()
                if run is None or run["kind"] != kind or run["graph_version"] != protocol:
                    return LLMFailure("run_manifest_violation", "Summary run protocol mismatch")
            inserted = conn.execute("""INSERT INTO ai_provider_attempts
                (attempt_id,run_id,provider,model_id,prompt_version,status,request_fingerprint,schema_name)
                VALUES (%s,%s,'openai_compatible',%s,%s,'dispatched',%s,%s)
                ON CONFLICT (attempt_id) DO NOTHING RETURNING attempt_id""",
                (attempt_id,run_id,self.provider.model,self.provider.prompt_version,fingerprint,schema_name)).fetchone()
            if not inserted:
                row = conn.execute("SELECT * FROM ai_provider_attempts WHERE attempt_id=%s", (attempt_id,)).fetchone()
                return self._retained_result(row, run_id, fingerprint, legacy_fingerprint)
        # Connection commits 'dispatched' BEFORE the external network request.
        provider_payload = {key: value for key, value in payload.items() if key != "_planning_claim"}
        try:
            result = self.provider.generate_structured(purpose=purpose,payload=provider_payload,schema_name=schema_name,run_id=run_id,attempt_id=attempt_id)
        except LLMNotDispatchedError:
            result = LLMFailure("endpoint_preflight_rejected","No provider request was sent")
            cause = None
        except Exception as exc:
            # Never retry an exception after durable dispatch.
            result = LLMFailure("provider_exception_unknown", "Provider outcome unknown", dispatch_unknown=True)
            cause = exc
        else:
            cause = None
        status = "succeeded" if isinstance(result, LLMResult) else ("reconciliation_required" if result.dispatch_unknown else "failed")
        data = asdict(result)
        try:
            with self._connect(project_id) as conn:
                cursor = conn.execute("""UPDATE ai_provider_attempts SET status=%s,response_payload=%s,
                    input_tokens=%s,output_tokens=%s,latency_ms=%s,error_class=%s
                    WHERE attempt_id=%s AND run_id=%s AND status='dispatched'""",
                    (status,Jsonb(data),getattr(result,"input_tokens",None),getattr(result,"output_tokens",None),
                     getattr(result,"latency_ms",None),getattr(result,"error_class",None),attempt_id,run_id))
                if cursor.rowcount != 1:
                    raise RuntimeError("Attempt outcome write conflict")
        except Exception as exc:
            raise LLMDispatchUnknownError("Attempt outcome persistence failed") from exc
        if cause:
            raise LLMDispatchUnknownError("Provider outcome unknown") from cause
        return result

    def preflight(self, *, purpose, payload, schema_name):
        check=getattr(self.provider,'preflight',None)
        return check(purpose=purpose,payload=payload,schema_name=schema_name) if check else None

    def _retained_result(self, row, run_id, fingerprint, legacy_fingerprint):
        compatible = (row is not None and row["run_id"] == run_id and (
            row["request_fingerprint"] == fingerprint or
            (self.provider.configuration_ref == "deployment" and row["request_fingerprint"] == legacy_fingerprint)
        ))
        if not compatible:
            return LLMFailure("attempt_conflict", "Attempt identity mismatch")
        if row["status"] == "succeeded":
            return LLMResult(**row["response_payload"])
        if row["status"] in {"dispatched", "reconciliation_required"}:
            return LLMFailure("attempt_dispatch_unknown", "Reconcile before another dispatch", dispatch_unknown=True)
        if row["response_payload"]:
            return LLMFailure(**row["response_payload"])
        return LLMFailure(row["error_class"] or "attempt_failed", "Retained failed attempt")
