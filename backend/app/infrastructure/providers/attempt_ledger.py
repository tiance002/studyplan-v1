"""Paid attempts are durable before dispatch and replay only retained results."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict

import psycopg
from app.agent_workflows.planning_batches import (
    allowed_attempt_keys,
    attempt_purpose,
    attempt_stage,
    budget_violation,
    manifest_is_intact,
    output_budget_for,
)
from app.infrastructure.db.plan_repository import to_psycopg_dsn
from app.ports.llm import LLMDispatchUnknownError, LLMFailure, LLMNotDispatchedError, LLMResult
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


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
            return None
        if not manifest_is_intact(self.manifest):
            return "run_manifest_violation"
        if attempt_id not in allowed_attempt_keys(run_id, self.manifest):
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
        rows = conn.execute(
            "SELECT attempt_id FROM ai_provider_attempts WHERE run_id=%s", (run_id,)
        ).fetchall()
        keys = {str(row["attempt_id"]) for row in rows}
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
        project_id = str(payload.get("_project_id") or "")
        request_options = self.provider.request_options(purpose)
        identity = [purpose,payload,schema_name,self.provider.model,self.provider.prompt_version,
                    self.provider.domain_pack,request_options,self.provider.budget_policy.as_dict()]
        fingerprint = hashlib.sha256(json.dumps([*identity,self.provider.base_url,self.provider.configuration_ref], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        # Preserve replay of pre-budget deployment attempts. This fingerprint is
        # only used to read an existing result; it never authorizes a new dispatch.
        legacy_identity = [purpose,payload,schema_name,self.provider.model,
                          self.provider.prompt_version,self.provider.domain_pack]
        legacy_fingerprint = hashlib.sha256(json.dumps(legacy_identity, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        with self._connect(project_id) as conn:
            rejection = self._budget_rejection(conn, run_id=run_id, attempt_id=attempt_id, purpose=purpose)
            if rejection is not None:
                return LLMFailure(rejection, "Run budget or manifest guard rejected this dispatch")
            inserted = conn.execute("""INSERT INTO ai_provider_attempts
                (attempt_id,run_id,provider,model_id,prompt_version,status,request_fingerprint,schema_name)
                VALUES (%s,%s,'openai_compatible',%s,%s,'dispatched',%s,%s)
                ON CONFLICT (attempt_id) DO NOTHING RETURNING attempt_id""",
                (attempt_id,run_id,self.provider.model,self.provider.prompt_version,fingerprint,schema_name)).fetchone()
            if not inserted:
                row = conn.execute("SELECT * FROM ai_provider_attempts WHERE attempt_id=%s", (attempt_id,)).fetchone()
                compatible = (row is not None and row["run_id"] == run_id and (
                    row["request_fingerprint"] == fingerprint or
                    (self.provider.configuration_ref == "deployment" and row["request_fingerprint"] == legacy_fingerprint)
                ))
                if not compatible:
                    return LLMFailure("attempt_conflict", "Attempt identity mismatch")
                if row["status"] == "succeeded":
                    return LLMResult(**row["response_payload"])
                if row["status"] in {"dispatched","reconciliation_required"}:
                    return LLMFailure("attempt_dispatch_unknown", "Reconcile before another dispatch", dispatch_unknown=True)
                if row["response_payload"]:
                    return LLMFailure(**row["response_payload"])
                return LLMFailure(row["error_class"] or "attempt_failed", "Retained failed attempt")
        # Connection commits 'dispatched' BEFORE the external network request.
        try:
            result = self.provider.generate_structured(purpose=purpose,payload=payload,schema_name=schema_name,run_id=run_id,attempt_id=attempt_id)
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
