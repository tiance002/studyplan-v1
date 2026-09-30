"""Read-only, application-role evidence for one B3-F2 run. Never calls a model."""

import argparse
import json

import psycopg
from app.agent_workflows.planning_batches import attempt_purpose, attempt_stage
from app.core.config import get_settings
from app.infrastructure.db.plan_repository import to_psycopg_dsn
from psycopg.rows import dict_row


def summarize(run, rows, draft, required):
    attempts = []
    for row in rows:
        response = row.get("response_payload") or {}
        diagnostics = response.get("diagnostics") or response.get("details") or {}
        attempts.append({
            **{key: row.get(key) for key in (
                "attempt_id", "schema_name", "status", "model_id", "input_tokens",
                "output_tokens", "latency_ms", "error_class",
            )},
            "purpose": diagnostics.get("purpose") or attempt_purpose(row["attempt_id"]),
            "stage_key": attempt_stage(row["attempt_id"]) or None,
            **{key: diagnostics.get(key) for key in (
                "max_tokens", "thinking", "finish_reason", "content_chars", "reasoning_chars",
            )},
        })

    def subtotal(key):
        known = [row[key] for row in attempts if row[key] is not None]
        return sum(known) if known else None

    usage_complete = bool(attempts) and all(
        row["status"] in {"succeeded", "failed"} and
        row["input_tokens"] is not None and row["output_tokens"] is not None
        for row in attempts
    )
    return {
        "run": run, "attempts": attempts, "request_count": len(attempts),
        "success_count": sum(row["status"] == "succeeded" for row in attempts),
        "failure_count": sum(row["status"] == "failed" for row in attempts),
        "unresolved_count": sum(row["status"] not in {"succeeded", "failed"} for row in attempts),
        "input_token_subtotal": subtotal("input_tokens"),
        "output_token_subtotal": subtotal("output_tokens"), "usage_complete": usage_complete,
        "latency_ms_subtotal": subtotal("latency_ms"),
        "latency_complete": bool(attempts) and all(row["latency_ms"] is not None for row in attempts),
        "final_status": run["status"],
        "draft_stage_count": len(draft.get("stages", [])) if draft is not None else None,
        "required_node_count": len(required) if required is not None else None,
        "required_node_coverage": len(set(required) & set(draft.get("node_stable_keys", [])))
        if required is not None and draft is not None else None,
    }


def inspect_run(dsn, *, actor_id, project_id, run_id):
    with psycopg.connect(to_psycopg_dsn(dsn), row_factory=dict_row) as conn:
        conn.execute("SET TRANSACTION READ ONLY")
        conn.execute("SELECT set_config('app.actor_id',%s,true),set_config('app.project_id',%s,true)",
                     (actor_id, project_id))
        role = conn.execute("SELECT rolsuper,rolbypassrls FROM pg_roles WHERE rolname=current_user").fetchone()
        if role["rolsuper"] or role["rolbypassrls"]:
            raise RuntimeError("Inspection requires the RLS-constrained application role")
        run = conn.execute("SELECT run_id,project_id,actor_id,status,version,error_class,result_ref "
                           "FROM ai_runs WHERE run_id=%s AND project_id=%s AND actor_id=%s",
                           (run_id, project_id, actor_id)).fetchone()
        if run is None:
            raise RuntimeError("Run is not visible in this actor/project scope")
        rows = conn.execute("SELECT attempt_id,schema_name,status,model_id,input_tokens,output_tokens,"
                            "latency_ms,error_class,response_payload FROM ai_provider_attempts "
                            "WHERE run_id=%s ORDER BY created_at,attempt_id", (run_id,)).fetchall()
        draft = conn.execute("SELECT payload FROM plan_drafts WHERE run_id=%s", (run_id,)).fetchone()
        submission = conn.execute("SELECT detail FROM ai_run_events WHERE run_id=%s AND status='submission' "
                                  "AND detail->>'kind'='planning_submission' ORDER BY event_id LIMIT 1",
                                  (run_id,)).fetchone()
        required = ((submission["detail"].get("manifest") or {}).get("required_node_keys")
                    if submission else None)
    return summarize(run, rows, draft["payload"] if draft else None, required)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--actor-id", required=True)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    report = inspect_run(get_settings().database_url, **vars(args))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
