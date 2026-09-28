"""Paid attempts are durable before dispatch and replay only retained results."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict

import psycopg
from app.infrastructure.db.plan_repository import to_psycopg_dsn
from app.ports.llm import LLMDispatchUnknownError, LLMFailure, LLMResult
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


class PgAttemptLLM:
    def __init__(self, dsn, provider):
        self.dsn = to_psycopg_dsn(dsn)
        self.provider = provider

    def _connect(self, project_id):
        conn = psycopg.connect(self.dsn, row_factory=dict_row)
        conn.execute("SELECT set_config('app.project_id', %s, true)", (project_id,))
        return conn

    def generate_structured(self, *, purpose, payload, schema_name, run_id, attempt_id):
        project_id = str(payload.get("_project_id") or "")
        fingerprint = hashlib.sha256(json.dumps([purpose,payload,schema_name,self.provider.model,self.provider.prompt_version,self.provider.domain_pack], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        with self._connect(project_id) as conn:
            inserted = conn.execute("""INSERT INTO ai_provider_attempts
                (attempt_id,run_id,provider,model_id,prompt_version,status,request_fingerprint,schema_name)
                VALUES (%s,%s,'openai_compatible',%s,%s,'dispatched',%s,%s)
                ON CONFLICT (attempt_id) DO NOTHING RETURNING attempt_id""",
                (attempt_id,run_id,self.provider.model,self.provider.prompt_version,fingerprint,schema_name)).fetchone()
            if not inserted:
                row = conn.execute("SELECT * FROM ai_provider_attempts WHERE attempt_id=%s", (attempt_id,)).fetchone()
                if row is None or row["request_fingerprint"] != fingerprint or row["run_id"] != run_id:
                    return LLMFailure("attempt_conflict", "Attempt identity mismatch")
                if row["status"] == "succeeded":
                    return LLMResult(**row["response_payload"])
                if row["status"] in {"dispatched","reconciliation_required"}:
                    return LLMFailure("attempt_dispatch_unknown", "Reconcile before another dispatch", dispatch_unknown=True)
                return LLMFailure(row["error_class"] or "attempt_failed", "Retained failed attempt")
        # Connection commits 'dispatched' BEFORE the external network request.
        try:
            result = self.provider.generate_structured(purpose=purpose,payload=payload,schema_name=schema_name,run_id=run_id,attempt_id=attempt_id)
        except Exception as exc:
            # Never retry an exception after durable dispatch.
            result = LLMFailure("provider_exception_unknown", "Provider outcome unknown", dispatch_unknown=True)
            cause = exc
        else:
            cause = None
        status = "succeeded" if isinstance(result, LLMResult) else ("reconciliation_required" if result.dispatch_unknown else "failed")
        data = asdict(result) if isinstance(result, LLMResult) else None
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
