"""Offline readiness checks. No real database or provider is contacted."""

import json
import os
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from app.infrastructure.providers.openai_compatible import OpenAICompatibleLLM
from app.ports.llm import LLMFailure, LLMResult
from app.tools import b3f2_controlled_live as controlled_live
from app.tools.b3f2_controlled_live import StopAfterFailure, main, validate_provider
from app.tools.b3f2_inspect import summarize


def test_default_gate_refuses_before_reading_settings(monkeypatch):
    def forbidden_settings():
        raise AssertionError("Default gate must not read deployment settings")

    monkeypatch.setattr("app.core.config.get_settings", forbidden_settings)
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    with pytest.raises(SystemExit, match="NOT RUN"):
        main([])


def test_paid_gate_requires_acceptance_id_before_settings(monkeypatch):
    monkeypatch.delenv("B3F2_USERNAME", raising=False)
    monkeypatch.delenv("B3F2_PASSWORD", raising=False)
    monkeypatch.setattr("app.core.config.get_settings", lambda: pytest.fail("settings must not be read"))
    with pytest.raises(SystemExit, match="AcceptanceId"):
        main(["--confirm-paid-run", "--project-id", "project-1"])


def test_cli_rejects_invalid_acceptance_id_before_credentials(monkeypatch):
    monkeypatch.delenv("B3F2_USERNAME", raising=False)
    monkeypatch.delenv("B3F2_PASSWORD", raising=False)
    with pytest.raises(SystemExit, match="Invalid AcceptanceId"):
        main(["--confirm-paid-run", "--acceptance-id", "../x", "--project-id", "project-1"])


def test_cli_requires_explicit_valid_acceptance_id(monkeypatch):
    monkeypatch.delenv("B3F2_USERNAME", raising=False)
    monkeypatch.delenv("B3F2_PASSWORD", raising=False)
    with pytest.raises(SystemExit, match="B3F2_USERNAME"):
        main(["--confirm-paid-run", "--acceptance-id", "b3f2-real-20260930-02",
              "--project-id", "project-1"])


def _powershell():
    return shutil.which("pwsh") or shutil.which("powershell")


def _run_controlled_live_powershell(*arguments):
    executable = _powershell()
    if executable is None:
        pytest.skip("PowerShell is unavailable")
    script = Path(__file__).resolve().parents[3] / "scripts" / "b3f2-controlled-live.ps1"
    env = os.environ.copy()
    for name in ("B3F2_USERNAME", "B3F2_PASSWORD", "PLANNING_WORKER_ACTOR_IDS",
                 "CHECKPOINT_DATABASE_URL", "LLM_API_KEY"):
        env.pop(name, None)
    env.update({
        "DATABASE_URL": "dsn-secret-marker",
        "MODEL_SETTINGS_ENCRYPTION_KEY": "encryption-secret-marker",
    })
    return subprocess.run(
        [executable, "-NoLogo", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
         "-File", str(script), *arguments],
        cwd=script.parents[1], env=env, capture_output=True, text=True, timeout=15, check=False,
    )


def test_powershell_gate_requires_confirmation_and_acceptance_id():
    refused = _run_controlled_live_powershell()
    assert refused.returncode == 2
    assert "explicit -ConfirmPaidRun" in refused.stdout

    missing_id = _run_controlled_live_powershell("-ConfirmPaidRun", "-ProjectId", "project-1")
    assert missing_id.returncode == 2
    assert "AcceptanceId" in missing_id.stdout
    for secret in ("dsn-secret-marker", "encryption-secret-marker"):
        assert secret not in missing_id.stdout + missing_id.stderr

    missing_project = _run_controlled_live_powershell(
        "-ConfirmPaidRun", "-AcceptanceId", "b3f2-real-20260930-02",
    )
    assert missing_project.returncode == 2
    assert "ProjectId" in missing_project.stdout


@pytest.mark.parametrize("acceptance_id", [
    "../x", "a/b", "a\\b", "legacy", "1", "first", "b3f2-real-20260930-01",
    "CON", "con.json", "NUL.txt", "PRN", "AUX", "COM1.foo", "com9.json", "LPT1", "lpt9.txt",
])
def test_powershell_rejects_path_acceptance_ids_before_starting_python(acceptance_id):
    result = _run_controlled_live_powershell(
        "-ConfirmPaidRun", "-AcceptanceId", acceptance_id, "-ProjectId", "project-1",
    )
    assert result.returncode == 2
    assert "Invalid AcceptanceId" in result.stdout


def _new_acceptance_api(name):
    function = getattr(controlled_live, name, None)
    assert callable(function), f"controlled-live {name} behavior is not implemented"
    return function


def _git_dir(tmp_path):
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    return git_dir


def _make_directory_symlink(link, target):
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError as exc:
        if os.name == "nt" and (isinstance(exc, PermissionError) or getattr(exc, "winerror", None) == 1314):
            pytest.skip("Directory symlink creation is unavailable without elevation")
        raise


def _make_directory_junction(link, target):
    target.mkdir(parents=True)
    result = subprocess.run(
        ["cmd.exe", "/c", "mklink", "/J", str(link), str(target)],
        capture_output=True, text=True, timeout=10, check=False,
    )
    if result.returncode != 0:
        pytest.skip("Directory junction creation is unavailable without elevation")
    attributes = getattr(link.lstat(), "st_file_attributes", 0)
    if not attributes & 0x400:  # FILE_ATTRIBUTE_REPARSE_POINT
        os.rmdir(link)
        pytest.skip("This Python runtime does not expose reparse-point attributes")


def test_acceptance_id_validation_rejects_reserved_and_unsafe_values():
    validate = _new_acceptance_api("validate_acceptance_id")
    assert validate("b3f2-real-20260930-02") == "b3f2-real-20260930-02"
    assert validate("A_2.release-x") == "A_2.release-x"
    assert validate("x" * 80) == "x" * 80
    for invalid in ("", "../x", "a/b", "a\\b", "..", "bad..id", "bad\nid",
                    "x" * 81, "legacy", "1", "first", "b3f2-real-20260930-01",
                    "CON", "con.json", "NUL.txt", "PRN", "AUX", "COM1.foo", "com9.json",
                    "LPT1", "lpt9.txt"):
        with pytest.raises(ValueError):
            validate(invalid)


def test_acceptance_paths_are_confined_and_leave_legacy_files_untouched(tmp_path):
    paths_for = _new_acceptance_api("acceptance_paths")
    git_dir = _git_dir(tmp_path)
    legacy_journal = git_dir / "b3f2-controlled-live.json"
    legacy_evidence = git_dir / "b3f2-controlled-live-evidence.json"
    legacy_journal.write_bytes(b"legacy journal stays byte-for-byte\n")
    legacy_evidence.write_bytes(b"legacy evidence stays byte-for-byte\n")
    original = (legacy_journal.read_bytes(), legacy_evidence.read_bytes())

    journal, evidence = paths_for(git_dir, "b3f2-real-20260930-02")
    acceptance_dir = (git_dir / "b3f2-controlled-live").resolve()
    assert journal.parent.resolve() == acceptance_dir
    assert evidence.parent.resolve() == acceptance_dir
    assert journal.name == "b3f2-real-20260930-02.json"
    assert evidence.name == "b3f2-real-20260930-02-evidence.json"
    assert acceptance_dir.parent == git_dir.resolve()
    assert (legacy_journal.read_bytes(), legacy_evidence.read_bytes()) == original


@pytest.mark.parametrize("target_kind", ["git_sibling", "outside_repo"])
def test_controlled_live_directory_symlink_fails_before_submission(tmp_path, target_kind):
    submit_run = _new_acceptance_api("submit_authorized_run")
    git_dir = _git_dir(tmp_path)
    target = git_dir / "logs" if target_kind == "git_sibling" else tmp_path / "outside"
    target.mkdir()
    _make_directory_symlink(git_dir / "b3f2-controlled-live", target)
    submissions = []

    def unexpected_submission():
        submissions.append("run-created")
        return SimpleNamespace(status_code=202, json=lambda: {"run_id": "mock-run"})

    with pytest.raises(ValueError, match="symlink|reparse"):
        submit_run(git_dir=git_dir, acceptance_id="b3f2-real-20260930-02", project_id="project-1",
                   actor_id="actor-1", model_id="deepseek-flash",
                   post=unexpected_submission)

    assert submissions == []
    assert not (target / "b3f2-real-20260930-02.json").exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows junction/reparse-point behavior")
def test_controlled_live_directory_junction_fails_before_submission(tmp_path):
    submit_run = _new_acceptance_api("submit_authorized_run")
    git_dir = _git_dir(tmp_path)
    target = git_dir / "logs"
    link = git_dir / "b3f2-controlled-live"
    _make_directory_junction(link, target)
    submissions = []

    try:
        def unexpected_submission():
            submissions.append("run-created")
            return SimpleNamespace(status_code=202, json=lambda: {"run_id": "mock-run"})

        with pytest.raises(ValueError, match="symlink|reparse"):
            submit_run(git_dir=git_dir, acceptance_id="b3f2-real-20260930-02", project_id="project-1",
                       actor_id="actor-1", model_id="deepseek-flash",
                       post=unexpected_submission)
        assert submissions == []
        assert not (target / "b3f2-real-20260930-02.json").exists()
    finally:
        os.rmdir(link)


def test_new_acceptance_is_exclusive_and_journal_precedes_run_submission(tmp_path):
    paths_for = _new_acceptance_api("acceptance_paths")
    submit_run = _new_acceptance_api("submit_authorized_run")
    git_dir = _git_dir(tmp_path)
    journal, evidence = paths_for(git_dir, "b3f2-real-20260930-02")
    submissions = []

    def post():
        assert json.loads(journal.read_text(encoding="utf-8"))["status"] == "submission_intent"
        submissions.append("run-1")
        return SimpleNamespace(status_code=202, json=lambda: {"run_id": "run-1"})

    kwargs = dict(git_dir=git_dir,
                  acceptance_id="b3f2-real-20260930-02", project_id="project-1",
                  actor_id="actor-1", model_id="deepseek-flash", post=post)
    run_id = submit_run(**kwargs)
    assert run_id == "run-1"
    saved = json.loads(journal.read_text(encoding="utf-8"))
    assert saved == {
        "acceptance_id": "b3f2-real-20260930-02", "actor_id": "actor-1",
        "project_id": "project-1", "model_id": "deepseek-flash",
        "run_id": "run-1", "status": "submitted",
    }

    with pytest.raises(FileExistsError):
        submit_run(**kwargs)
    assert submissions == ["run-1"]
    assert not evidence.exists()


def test_existing_evidence_stops_before_submission_and_is_not_overwritten(tmp_path):
    paths_for = _new_acceptance_api("acceptance_paths")
    submit_run = _new_acceptance_api("submit_authorized_run")
    git_dir = _git_dir(tmp_path)
    journal, evidence = paths_for(git_dir, "b3f2-real-20260930-02")
    evidence.parent.mkdir(parents=True)
    evidence.write_bytes(b"evidence belongs to an earlier operation")
    original = evidence.read_bytes()
    submissions = []

    with pytest.raises(FileExistsError):
        submit_run(git_dir=git_dir,
                   acceptance_id="b3f2-real-20260930-02", project_id="project-1",
                   actor_id="actor-1", model_id="deepseek-flash",
                   post=lambda: submissions.append("unexpected"))
    assert submissions == []
    assert not journal.exists()
    assert evidence.read_bytes() == original


def test_post_failure_consumes_acceptance_and_suppresses_exception_secrets(tmp_path):
    paths_for = _new_acceptance_api("acceptance_paths")
    submit_run = _new_acceptance_api("submit_authorized_run")
    git_dir = _git_dir(tmp_path)
    journal, evidence = paths_for(git_dir, "b3f2-real-20260930-02")
    submissions = []

    def failed_post():
        submissions.append("attempted")
        raise RuntimeError("Authorization: Bearer exception-secret-marker")

    kwargs = dict(git_dir=git_dir,
                  acceptance_id="b3f2-real-20260930-02", project_id="project-1",
                  actor_id="actor-1", model_id="deepseek-flash", post=failed_post)
    with pytest.raises(SystemExit) as error:
        submit_run(**kwargs)
    assert "exception-secret-marker" not in str(error.value)
    assert json.loads(journal.read_text(encoding="utf-8"))["status"] == "submission_intent"
    with pytest.raises(FileExistsError):
        submit_run(**kwargs)
    assert submissions == ["attempted"]


def test_acceptance_id_cannot_be_bound_to_a_second_run(tmp_path):
    paths_for = _new_acceptance_api("acceptance_paths")
    submit_run = _new_acceptance_api("submit_authorized_run")
    advance = _new_acceptance_api("advance_acceptance_journal")
    git_dir = _git_dir(tmp_path)
    journal, evidence = paths_for(git_dir, "b3f2-real-20260930-02")
    submit_run(git_dir=git_dir,
               acceptance_id="b3f2-real-20260930-02", project_id="project-1",
               actor_id="actor-1", model_id="deepseek-flash",
               post=lambda: SimpleNamespace(status_code=202, json=lambda: {"run_id": "run-1"}))
    original = journal.read_bytes()

    with pytest.raises(RuntimeError, match="Run"):
        advance(git_dir, "b3f2-real-20260930-02", run_id="run-2",
                project_id="project-1", model_id="deepseek-flash", status="succeeded")
    assert journal.read_bytes() == original


def test_dispatch_unknown_keeps_journal_and_same_id_cannot_submit_another_run(tmp_path):
    paths_for = _new_acceptance_api("acceptance_paths")
    submit_run = _new_acceptance_api("submit_authorized_run")
    advance = _new_acceptance_api("advance_acceptance_journal")
    git_dir = _git_dir(tmp_path)
    journal, evidence = paths_for(git_dir, "b3f2-real-20260930-02")
    submissions = []
    run_id = submit_run(git_dir=git_dir,
                        acceptance_id="b3f2-real-20260930-02", project_id="project-1",
                        actor_id="actor-1", model_id="deepseek-flash",
                        post=lambda: (submissions.append("run-1") or
                                      SimpleNamespace(status_code=202, json=lambda: {"run_id": "run-1"})))

    class UnknownProvider:
        calls = 0

        def generate_structured(self, **kwargs):
            self.calls += 1
            return LLMFailure("provider_transport_unknown", "offline", dispatch_unknown=True)

    provider = UnknownProvider()
    failure = StopAfterFailure(provider, run_id).generate_structured(run_id=run_id, attempt_id="stage.tools")
    assert failure.dispatch_unknown is True
    assert provider.calls == 1
    advance(git_dir, "b3f2-real-20260930-02", run_id=run_id,
            project_id="project-1", model_id="deepseek-flash",
            status="reconciliation_required", request_count=4)
    saved = json.loads(journal.read_text(encoding="utf-8"))
    assert saved["status"] == "reconciliation_required"
    assert saved["run_id"] == run_id

    with pytest.raises(FileExistsError):
        submit_run(git_dir=git_dir,
                   acceptance_id="b3f2-real-20260930-02", project_id="project-1",
                   actor_id="actor-1", model_id="deepseek-flash",
                   post=lambda: submissions.append("run-2"))
    assert submissions == ["run-1"]


def test_evidence_is_allowlisted_secret_free_and_exclusive(tmp_path):
    paths_for = _new_acceptance_api("acceptance_paths")
    submit_run = _new_acceptance_api("submit_authorized_run")
    advance = _new_acceptance_api("advance_acceptance_journal")
    build_evidence = _new_acceptance_api("build_acceptance_evidence")
    write_evidence = _new_acceptance_api("write_acceptance_evidence")
    git_dir = _git_dir(tmp_path)
    _, evidence_path = paths_for(git_dir, "b3f2-real-20260930-02")
    submit_run(git_dir=git_dir, acceptance_id="b3f2-real-20260930-02", project_id="project-1",
               actor_id="actor-1", model_id="deepseek-flash",
               post=lambda: SimpleNamespace(status_code=202, json=lambda: {"run_id": "run-1"}))
    advance(git_dir, "b3f2-real-20260930-02", run_id="run-1", project_id="project-1",
            model_id="deepseek-flash", status="waiting_user", request_count=1)
    report = {
        "final_status": "waiting_user", "request_count": 1,
        "attempts": [{"attempt_id": "attempt-1", "status": "succeeded",
                      "model_id": "deepseek-flash", "input_tokens": 12, "output_tokens": 8,
                      "api_key": "api-key-secret-marker", "authorization": "authorization-secret-marker",
                      "prompt": "prompt-secret-marker"}],
        "api_key": "api-key-secret-marker", "password": "password-secret-marker",
        "cookie": "cookie-secret-marker", "session_token": "session-secret-marker",
        "dsn": "dsn-secret-marker", "encryption_key": "encryption-secret-marker",
    }
    evidence = build_evidence("b3f2-real-20260930-02", "run-1", "project-1", report)
    assert evidence["acceptance_id"] == "b3f2-real-20260930-02"
    assert evidence["run_id"] == "run-1"
    assert evidence["project_id"] == "project-1"
    assert evidence["final_status"] == "waiting_user"
    assert evidence["request_count"] == 1
    assert evidence["attempt_summary"][0]["attempt_id"] == "attempt-1"
    serialized = json.dumps(evidence)
    for secret in ("api-key-secret-marker", "authorization-secret-marker", "prompt-secret-marker",
                   "password-secret-marker", "cookie-secret-marker", "session-secret-marker",
                   "dsn-secret-marker", "encryption-secret-marker"):
        assert secret not in serialized
    for forbidden_key in ("api_key", "authorization", "password", "cookie", "session_token",
                          "dsn", "encryption_key", "prompt"):
        assert forbidden_key not in serialized.lower()

    write_evidence(git_dir, "b3f2-real-20260930-02", "run-1", "project-1", report)
    original = evidence_path.read_bytes()
    with pytest.raises(FileExistsError):
        write_evidence(git_dir, "b3f2-real-20260930-02", "run-1", "project-1", report)
    assert evidence_path.read_bytes() == original


def test_exact_deepseek_options_are_checked_without_dispatch():
    provider = OpenAICompatibleLLM(base_url="https://api.deepseek.com", api_key="offline", model="deepseek-flash")
    validate_provider(provider)
    provider.model = "some-other-model"
    with pytest.raises(RuntimeError, match="deepseek-flash"):
        validate_provider(provider)


@pytest.mark.parametrize("failure", ["provider_output_truncated", "provider_invalid_json",
                                     "provider_invalid_shape", "provider_invalid_envelope",
                                     "provider_transport_unknown"])
def test_first_failure_prevents_next_attempt(failure):
    class Provider:
        calls = 0

        def generate_structured(self, **kwargs):
            self.calls += 1
            return LLMFailure(failure, "offline", dispatch_unknown=failure.endswith("unknown"))

    provider = Provider()
    guarded = StopAfterFailure(provider, "run")
    guarded.generate_structured(run_id="run", attempt_id="one")
    with pytest.raises(RuntimeError, match="stopped"):
        guarded.generate_structured(run_id="run", attempt_id="two")
    assert provider.calls == 1


def test_request_ceiling_duplicate_and_run_identity():
    class Provider:
        calls = 0

        def generate_structured(self, **kwargs):
            self.calls += 1
            return LLMResult(payload={}, model_id="offline", provider="fake")

    provider = Provider()
    guarded = StopAfterFailure(provider, "run")
    for index in range(21):
        guarded.generate_structured(run_id="run", attempt_id=str(index))
    for run, attempt in (("run", "21"), ("run", "0"), ("other", "x")):
        with pytest.raises(RuntimeError, match="stopped"):
            guarded.generate_structured(run_id=run, attempt_id=attempt)
    assert provider.calls == 21


def test_inspection_keeps_unknown_usage_null_and_partial_subtotals_honest():
    row = {"attempt_id": "run:b3f2-batch-v1:planning.structure:stage.one:0:0",
           "status": "failed", "input_tokens": None, "output_tokens": None}
    report = summarize({"status": "failed"}, [row], None, ["node.one"])
    assert report["attempts"][0]["purpose"] == "planning.structure"
    assert report["attempts"][0]["stage_key"] == "stage.one"
    assert report["input_token_subtotal"] is None and report["output_token_subtotal"] is None
    assert report["usage_complete"] is False
    assert report["draft_stage_count"] is None
    report = summarize({"status": "failed"}, [row, {**row, "input_tokens": 7, "output_tokens": 9}], None, [])
    assert report["input_token_subtotal"] == 7 and report["usage_complete"] is False
