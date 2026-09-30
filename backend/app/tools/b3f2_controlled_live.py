"""One explicitly authorized paid Run, using existing personal model settings."""

import argparse
import json
import os
from dataclasses import replace
from pathlib import Path
from urllib.parse import urlsplit

from app.ports.graph_runner import PlanningRuntime
from app.ports.llm import LLMFailure

GOAL = "从零学习 Agent 应用开发，并完成一个可验收的知识库 Agent 项目"
BUDGETS = {"planning.outline": 4096, "planning.structure": 8192,
           "planning.practice": 4096, "planning.repair": 8192}


class StopAfterFailure:
    """No second dispatch after any failure, duplicate ID, or request ceiling."""

    def __init__(self, llm, run_id):
        self.llm, self.run_id = llm, run_id
        self.attempts = set()
        self.stopped = False

    def generate_structured(self, **kwargs):
        attempt = kwargs["attempt_id"]
        if self.stopped or kwargs["run_id"] != self.run_id or attempt in self.attempts or len(self.attempts) >= 21:
            raise RuntimeError("Controlled live dispatch stopped; no retry is authorized")
        self.attempts.add(attempt)
        try:
            result = self.llm.generate_structured(**kwargs)
        except Exception:
            self.stopped = True
            raise
        if isinstance(result, LLMFailure):
            self.stopped = True
        return result


def validate_provider(provider):
    if provider.model != "deepseek-flash" or urlsplit(provider.base_url).hostname != "api.deepseek.com":
        raise RuntimeError("Existing personal settings must select official deepseek-flash")
    for purpose, limit in BUDGETS.items():
        options = provider.request_options(purpose)
        if options.get("max_tokens") != limit or options.get("thinking") != {"type": "disabled"}:
            raise RuntimeError("Controlled live budget/thinking preflight failed")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm-paid-run", action="store_true")
    parser.add_argument("--project-id")
    args = parser.parse_args(argv)
    if not args.confirm_paid_run:
        raise SystemExit("NOT RUN: explicit -ConfirmPaidRun authorization is required")
    if not args.project_id:
        raise SystemExit("An existing dedicated acceptance project is required")
    username = os.environ.get("B3F2_USERNAME")
    password = os.environ.get("B3F2_PASSWORD")
    if not username or not password:
        raise SystemExit("Set B3F2_USERNAME/B3F2_PASSWORD privately in this process")

    # All database/network imports and settings reads are after the paid gate.
    from app.composition import build_container
    from app.core.config import get_settings
    from app.main import create_app
    from app.tools.b3f2_inspect import inspect_run
    from fastapi.testclient import TestClient

    settings = get_settings()
    if settings.use_fake_llm or not settings.is_development:
        raise SystemExit("Requires the existing local real-provider deployment configuration")
    settings = replace(settings, llm_outline_output_tokens=4096, llm_structure_output_tokens=8192,
                       llm_practice_output_tokens=4096, llm_repair_output_tokens=8192,
                       llm_max_output_tokens=8192, worker_max_attempts=1)
    container = build_container(settings)
    service = container.plan_service
    with TestClient(create_app(container)) as client:
        response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
        if response.status_code != 200:
            raise SystemExit("Login failed; no generation submitted")
        token = client.cookies.get(settings.session_cookie_name)
        scope = container.sessions.resolve(token)
        scope.require_project(args.project_id)
        if scope.actor_id not in settings.planning_worker_actor_ids:
            raise SystemExit("Existing Worker allowlist must include this actor")
        factory = service._runtime_factory
        selected = factory.repository.resolve(scope.actor_id)
        if selected is None:
            raise SystemExit("Existing personal model credentials are required")
        validate_provider(factory._personal_provider(scope.actor_id, selected))
        jobs = service._planning_jobs
        # Acquire the same single-worker lock used by the Worker CLI.
        if not jobs.acquire_worker_lock():
            raise SystemExit("Stop the external Worker before controlled acceptance")
        try:
            with jobs._tx(actor_id=scope.actor_id, project_id=args.project_id) as conn:
                pending = conn.execute("SELECT 1 FROM ai_runs WHERE project_id=%s "
                                       "AND status IN ('queued','running','reconciliation_required') LIMIT 1",
                                       (args.project_id,)).fetchone()
                if pending:
                    raise SystemExit("Project already has an active/unresolved Run; no generation submitted")
            journal = Path(__file__).resolve().parents[3] / ".git" / "b3f2-controlled-live.json"
            # Exclusive creation consumes this authorization even on ambiguous POST.
            with journal.open("x", encoding="utf-8") as file:
                json.dump({"actor_id": scope.actor_id, "project_id": args.project_id,
                           "status": "submission_intent", "model": selected.model_id}, file)
            headers = {"X-CSRF-Token": response.json()["csrf_token"]}
            response = client.post("/api/v1/plans/generate", params={"project_id": args.project_id},
                                   headers=headers, json={"goal": GOAL})
            if response.status_code != 202:
                raise SystemExit("POST not accepted; authorization retained, no retry")
            run_id = response.json()["run_id"]
            journal.write_text(json.dumps({"actor_id": scope.actor_id, "project_id": args.project_id,
                                           "run_id": run_id, "status": "submitted"}), encoding="utf-8")

            def bounded_runtime(auth, project, run, model_ref=""):
                runtime = factory(auth, project, run, model_ref)
                validate_provider(runtime.llm.provider)
                return PlanningRuntime(StopAfterFailure(runtime.llm, run_id), runtime.executor)

            service._runtime_factory = bounded_runtime
            worker = container.planning_worker
            claim = jobs.claim(args.project_id, worker._worker_id, worker._lease_seconds)
            if claim is None or claim.run_id != run_id:
                raise SystemExit("Exact Run claim failed; do not retry generation")
            worker._process(claim)  # one fenced claim, never a polling Worker loop
            report = inspect_run(settings.database_url, actor_id=scope.actor_id,
                                 project_id=args.project_id, run_id=run_id)
            output = journal.parent / "b3f2-controlled-live-evidence.json"
            output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps(report, ensure_ascii=False, indent=2))
            if report["final_status"] != "waiting_user" or report["request_count"] > 21:
                raise SystemExit("Stopped after failure/reconciliation; no retry or second Run")
            if report["draft_stage_count"] != 9 or report["required_node_coverage"] != 27:
                raise SystemExit("Draft coverage failed; no second Run")
        finally:
            jobs.release_worker_lock()


if __name__ == "__main__":
    main()
