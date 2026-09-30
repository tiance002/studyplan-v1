"""One explicitly authorized paid Run, using existing personal model settings."""

import argparse
import json
import os
import re
import stat
import tempfile
from dataclasses import replace
from pathlib import Path
from typing import Callable, Mapping
from urllib.parse import urlsplit

from app.ports.graph_runner import PlanningRuntime
from app.ports.llm import LLMFailure

GOAL = "从零学习 Agent 应用开发，并完成一个可验收的知识库 Agent 项目"
BUDGETS = {"planning.outline": 4096, "planning.structure": 8192,
           "planning.practice": 4096, "planning.repair": 8192}
_ACCEPTANCE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}")
_RESERVED_ACCEPTANCE_IDS = frozenset({
    "legacy", "1", "first", "b3f2-real-20260930-01", "b3f2-real-20260930-1",
})
_WINDOWS_DEVICE_ACCEPTANCE_ID = re.compile(
    r"(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?", re.IGNORECASE,
)
_RUN_STATUSES = frozenset({
    "queued", "running", "waiting_user", "succeeded", "failed", "cancelled", "reconciliation_required",
})
_EVIDENCE_ATTEMPT_FIELDS = (
    "attempt_id", "schema_name", "status", "model_id", "input_tokens", "output_tokens",
    "latency_ms", "error_class", "purpose", "stage_key", "max_tokens", "thinking",
    "finish_reason", "content_chars", "reasoning_chars",
)


def validate_acceptance_id(acceptance_id: str) -> str:
    """Validate a manually supplied identifier without interpreting it as a path."""
    if (not isinstance(acceptance_id, str) or not _ACCEPTANCE_ID.fullmatch(acceptance_id)
            or ".." in acceptance_id or acceptance_id.casefold() in _RESERVED_ACCEPTANCE_IDS
            or _WINDOWS_DEVICE_ACCEPTANCE_ID.fullmatch(acceptance_id)):
        raise ValueError("Invalid AcceptanceId")
    return acceptance_id


def _is_symlink_or_reparse_point(path: Path) -> bool:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return False
    attributes = getattr(metadata, "st_file_attributes", 0)
    reparse_point = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return stat.S_ISLNK(metadata.st_mode) or bool(attributes & reparse_point)


def acceptance_paths(git_dir: str | Path, acceptance_id: str) -> tuple[Path, Path]:
    """Return paths confined to the fixed per-acceptance directory under .git."""
    acceptance_id = validate_acceptance_id(acceptance_id)
    root = Path(git_dir).resolve()
    if not root.is_dir():
        raise ValueError("Git metadata directory is unavailable")
    directory = root / "b3f2-controlled-live"
    if _is_symlink_or_reparse_point(directory):
        raise ValueError("Acceptance journal directory is a symlink or reparse point")
    resolved_directory = directory.resolve()
    if resolved_directory.parent != root:
        raise ValueError("Acceptance journal directory escaped Git metadata directory")
    journal = resolved_directory / f"{acceptance_id}.json"
    evidence = resolved_directory / f"{acceptance_id}-evidence.json"
    if journal.resolve().parent != resolved_directory or evidence.resolve().parent != resolved_directory:
        raise ValueError("Acceptance file path escaped its fixed directory")
    return journal, evidence


def _ensure_acceptance_paths(git_dir: str | Path, acceptance_id: str) -> tuple[Path, Path]:
    journal, evidence = acceptance_paths(git_dir, acceptance_id)
    journal.parent.mkdir(mode=0o700, parents=False, exist_ok=True)
    # Re-resolve after mkdir so a pre-existing symlink cannot redirect writes.
    return acceptance_paths(git_dir, acceptance_id)


def _write_json_exclusive(path: Path, value: Mapping[str, object]) -> None:
    """Create a new JSON record once. A partial file remains consumed on error."""
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    descriptor = os.open(str(path), flags, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as file:
        json.dump(value, file, ensure_ascii=False, indent=2)
        file.write("\n")
        file.flush()
        os.fsync(file.fileno())


def _replace_journal_json(path: Path, value: Mapping[str, object]) -> None:
    """Atomically advance the owning submission's journal state."""
    parent = path.parent.resolve()
    if path.is_symlink() or path.resolve().parent != parent:
        raise RuntimeError("Acceptance journal path is not a regular in-directory file")
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as file:
            json.dump(value, file, ensure_ascii=False, indent=2)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except OSError:
            pass
        raise


def _read_acceptance_journal(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise RuntimeError("Acceptance journal is unreadable; its ID remains consumed") from None
    if not isinstance(value, dict):
        raise RuntimeError("Acceptance journal is invalid; its ID remains consumed")
    return value


def advance_acceptance_journal(
    git_dir: str | Path,
    acceptance_id: str,
    *,
    run_id: str,
    project_id: str,
    model_id: str,
    status: str,
    request_count: int | None = None,
) -> None:
    """Advance one journal while preventing an AcceptanceId from binding two Runs."""
    acceptance_id = validate_acceptance_id(acceptance_id)
    journal, _ = acceptance_paths(git_dir, acceptance_id)
    record = _read_acceptance_journal(journal)
    if record.get("acceptance_id") != acceptance_id:
        raise RuntimeError("Acceptance journal ID mismatch")
    if record.get("project_id") != project_id or record.get("model_id") != model_id:
        raise RuntimeError("Acceptance journal identity mismatch")
    existing_run_id = record.get("run_id")
    if existing_run_id is not None and existing_run_id != run_id:
        raise RuntimeError("AcceptanceId is already bound to a different Run")
    if not isinstance(run_id, str) or not run_id or not isinstance(status, str) or not status:
        raise RuntimeError("Acceptance journal update is invalid")
    if status != "submitted" and status not in _RUN_STATUSES:
        raise RuntimeError("Acceptance journal Run status is invalid")
    if request_count is not None and (not isinstance(request_count, int) or isinstance(request_count, bool)
                                      or request_count < 0):
        raise RuntimeError("Acceptance request count is invalid")

    if record.get("status") == "submission_intent":
        if status != "submitted":
            raise RuntimeError("A submission intent must bind its Run before final status")
    elif record.get("status") == "submitted":
        if status == "submitted":
            raise RuntimeError("Acceptance Run is already submitted")
    else:
        raise RuntimeError("Acceptance journal is already finalized")

    record.update({"run_id": run_id, "project_id": project_id, "model_id": model_id, "status": status})
    if request_count is not None:
        record["request_count"] = request_count
    _replace_journal_json(journal, record)


def submit_authorized_run(
    *,
    git_dir: str | Path,
    acceptance_id: str,
    project_id: str,
    actor_id: str,
    model_id: str,
    post: Callable[[], object],
) -> str:
    """Consume one AcceptanceId before calling POST; ambiguous outcomes stay consumed."""
    acceptance_id = validate_acceptance_id(acceptance_id)
    journal, evidence = _ensure_acceptance_paths(git_dir, acceptance_id)
    if evidence.exists() or evidence.is_symlink():
        raise FileExistsError("Acceptance evidence already exists; stop without submitting")
    _write_json_exclusive(journal, {
        "acceptance_id": acceptance_id,
        "actor_id": actor_id,
        "project_id": project_id,
        "model_id": model_id,
        "status": "submission_intent",
    })
    try:
        response = post()
    except Exception:
        raise SystemExit("Submission outcome unknown; this AcceptanceId is consumed; do not retry it") from None
    if getattr(response, "status_code", None) != 202:
        raise SystemExit("Submission was not accepted; this AcceptanceId is consumed; do not retry it")
    try:
        run_id = response.json().get("run_id")
    except Exception:
        raise SystemExit("Accepted submission has no usable Run ID; this AcceptanceId is consumed") from None
    if not isinstance(run_id, str) or not run_id.strip():
        raise SystemExit("Accepted submission has no usable Run ID; this AcceptanceId is consumed")
    advance_acceptance_journal(
        git_dir, acceptance_id, run_id=run_id, project_id=project_id, model_id=model_id, status="submitted",
    )
    return run_id


def build_acceptance_evidence(
    acceptance_id: str,
    run_id: str,
    project_id: str,
    report: Mapping[str, object],
) -> dict[str, object]:
    """Build a metadata-only evidence record from explicitly allowed inspection fields."""
    acceptance_id = validate_acceptance_id(acceptance_id)
    attempts = report.get("attempts", [])
    request_count = report.get("request_count")
    final_status = report.get("final_status")
    if not isinstance(attempts, list) or not isinstance(request_count, int) or isinstance(request_count, bool):
        raise ValueError("Run inspection summary is incomplete")
    if request_count < 0 or request_count != len(attempts):
        raise ValueError("Run inspection request count is inconsistent")
    if not isinstance(final_status, str) or not final_status:
        raise ValueError("Run inspection status is unavailable")
    if not isinstance(run_id, str) or not run_id or not isinstance(project_id, str) or not project_id:
        raise ValueError("Run inspection identity is unavailable")
    attempt_summary = []
    for attempt in attempts:
        if not isinstance(attempt, dict):
            raise ValueError("Run inspection attempt summary is invalid")
        attempt_summary.append({key: attempt[key] for key in _EVIDENCE_ATTEMPT_FIELDS if key in attempt})
    return {
        "acceptance_id": acceptance_id,
        "run_id": run_id,
        "project_id": project_id,
        "final_status": final_status,
        "request_count": request_count,
        "attempt_summary": attempt_summary,
    }


def write_acceptance_evidence(
    git_dir: str | Path,
    acceptance_id: str,
    run_id: str,
    project_id: str,
    report: Mapping[str, object],
) -> dict[str, object]:
    """Write this AcceptanceId's evidence exactly once and only for its bound Run."""
    acceptance_id = validate_acceptance_id(acceptance_id)
    evidence = build_acceptance_evidence(acceptance_id, run_id, project_id, report)
    journal, evidence_path = _ensure_acceptance_paths(git_dir, acceptance_id)
    record = _read_acceptance_journal(journal)
    if (record.get("acceptance_id") != acceptance_id or record.get("run_id") != run_id
            or record.get("project_id") != project_id or record.get("status") != evidence["final_status"]
            or record.get("request_count") != evidence["request_count"]):
        raise RuntimeError("Acceptance evidence does not match its journal Run")
    _write_json_exclusive(evidence_path, evidence)
    return evidence


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
    parser.add_argument("--acceptance-id")
    parser.add_argument("--project-id")
    args = parser.parse_args(argv)
    if not args.confirm_paid_run:
        raise SystemExit("NOT RUN: explicit -ConfirmPaidRun authorization is required")
    if not args.project_id:
        raise SystemExit("An existing dedicated acceptance project is required")
    if not args.acceptance_id:
        raise SystemExit("NOT RUN: an explicit AcceptanceId (--acceptance-id) is required")
    try:
        args.acceptance_id = validate_acceptance_id(args.acceptance_id)
    except ValueError:
        raise SystemExit("Invalid AcceptanceId") from None
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
            git_dir = Path(__file__).resolve().parents[3] / ".git"
            headers = {"X-CSRF-Token": response.json()["csrf_token"]}
            run_id = submit_authorized_run(
                git_dir=git_dir,
                acceptance_id=args.acceptance_id,
                project_id=args.project_id,
                actor_id=scope.actor_id,
                model_id=selected.model_id,
                post=lambda: client.post(
                    "/api/v1/plans/generate", params={"project_id": args.project_id},
                    headers=headers, json={"goal": GOAL},
                ),
            )

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
            advance_acceptance_journal(
                git_dir, args.acceptance_id, run_id=run_id, project_id=args.project_id,
                model_id=selected.model_id, status=report["final_status"],
                request_count=report["request_count"],
            )
            evidence = write_acceptance_evidence(
                git_dir, args.acceptance_id, run_id, args.project_id, report,
            )
            print(json.dumps(evidence, ensure_ascii=False, indent=2))
            if report["final_status"] != "waiting_user" or report["request_count"] > 21:
                raise SystemExit("Stopped after failure/reconciliation; no retry or second Run")
            if report["draft_stage_count"] != 9 or report["required_node_coverage"] != 27:
                raise SystemExit("Draft coverage failed; no second Run")
        finally:
            jobs.release_worker_lock()


if __name__ == "__main__":
    main()
