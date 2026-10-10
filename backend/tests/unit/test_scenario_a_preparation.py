"""Tracked owned preparation/real assembly seam; every external/DB call forbidden."""
import hashlib
import json
import socket
import subprocess
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import psycopg
import pytest
from app.application.plan_service import PlanService
from app.core.errors import ValidationAppError
from app.core.ids import content_hash
from app.domain.planning.intent import GoalSpec
from app.domain.planning.resource_research import ResearchBudget
from app.domain.workspace.models import AuthContext
from app.infrastructure.db.job_repository import PgPlanningJobRepository
from app.ports.llm import LLMNotDispatchedError
from app.ports.planning_jobs import JobClaim

from scripts import planning_v2_scenario_a as runner
from scripts.planning_v2_owned_source_facts import freeze_reviewed_source_facts, read_source_facts


@pytest.fixture(autouse=True)
def forbidden_external_and_database(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("No network/DB in owned runner preparation tests")
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(psycopg, "connect", forbidden)


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True)
    (tmp_path / ".gitignore").write_text("var/\n", encoding="utf-8")
    monkeypatch.setattr(runner, "_head", lambda _root: "a" * 40)
    original = freeze_reviewed_source_facts(tmp_path / "original-source.json", root=runner.ROOT)
    options = {p: {"model": "future-owner-model", "max_tokens": 1024 if p == "planning.research_reader" else 4096}
        for p in runner.PURPOSE_SCHEMAS}
    output = tmp_path / "var" / "fresh-owned"
    packet = runner.prepare(output, root=tmp_path, goal=GoalSpec("从基础学习 Tool Calling 和 RAG"),
        model_ref="deployment:future-owner-bound", request_options=options, facts=read_source_facts(original))
    return tmp_path, output / "prepared.json", packet


def owner_evidence(prepared, **changes):
    _root, path, packet = prepared
    grant = json.loads((path.parent / "owner-authorization-request.json").read_bytes())
    grant.update(owner_approved=True, owner_evidence="Synthetic unit fixture; no real Owner grant or external authority",
        issued_at=datetime.now(timezone.utc).isoformat(), actions=["submit", "execute"])
    grant.update(changes)
    evidence = path.parent / "synthetic-owner.json"
    evidence.write_text(json.dumps(grant), encoding="utf-8")
    return evidence, hashlib.sha256(evidence.read_bytes()).hexdigest()


def assembly_options(prepared, **changes):
    root, _path, _packet = prepared
    authorization, digest = owner_evidence(prepared)
    values = {"root": root, "dsn": "postgresql://private:private@127.0.0.1/studyplan_test_new_business",
        "checkpoint_dsn": "postgresql://private:private@127.0.0.1/studyplan_test_new_checkpoint",
        "scope": AuthContext("owned", "server-session", datetime.now(timezone.utc), ("new-project",)),
        "project_id": "new-project", "authorization": authorization, "authorization_sha256": digest}
    values.update(changes)
    return values


@pytest.mark.parametrize("value", [
    "postgresql://synthetic:synthetic@127.0.0.1/studyplan_test_fixture?dbname=studyplan_formal",
    "postgresql://synthetic:synthetic@127.0.0.1/studyplan_test_fixture?host=remote.invalid",
    "postgresql://synthetic:synthetic@127.0.0.1/studyplan_test_fixture?hostaddr=203.0.113.4",
    "postgresql://synthetic:synthetic@127.0.0.1/studyplan_test_fixture?service=remote",
    "postgresql://synthetic:synthetic@127.0.0.1/studyplan_test_fixture#override",
])
def test_effective_owned_dsn_overrides_rejected_before_any_connection(value):
    with pytest.raises(ValidationAppError):
        runner._validated_owned_dsn(value)


def test_owned_pair_and_environment_cannot_redirect_connection(monkeypatch):
    value = "postgresql://synthetic:synthetic@127.0.0.1:5432/studyplan_test_fixture"
    assert runner._validated_owned_dsn(value) == value
    with pytest.raises(ValidationAppError):
        runner._owned_pair(value, value.replace("127.0.0.1:5432", "localhost"))
    with pytest.raises(ValidationAppError):
        runner._owned_pair(value, value.replace(":5432", ":05432"))
    for name in ("PGHOSTADDR", "PGSERVICE", "PGSERVICEFILE"):
        monkeypatch.setenv(name, "synthetic-redirect")
        with pytest.raises(ValidationAppError):
            runner._validated_owned_dsn(value)
        monkeypatch.delenv(name)


def test_zero_network_preparation_freezes_full_facts_before_manifest_and_unsigned_request(prepared):
    root, path, packet = prepared
    loaded = runner.load_prepared(path, root=root)
    assert loaded == packet
    facts = read_source_facts(runner.FrozenSourceFactsRef.from_payload(packet["source_facts_ref"]), manifest=packet["manifest"])
    assert facts.reviewed_index.sections and facts.access_proofs and facts.catalog_sources[0].created_at.tzinfo
    assert packet["request_plan"] | {"purpose_limits": None} == {
        "purpose_limits": None, "model_requests": 9, "search_requests": 6, "body_operations": 6,
        "body_http_requests": 12, "metadata_requests": 0, "output_tokens": 18432, "body_bytes": 393216,
        "retry_limit": 0, "repair_limit": 0, "run_limit": 1, "total_requests": 27, "cost_micros": 186000,
        "research_rules_version": "research_chapter_v3"}
    request = json.loads((path.parent / "owner-authorization-request.json").read_bytes())
    assert request["owner_approved"] is False and request["actions"] == [] and request["owner_evidence"] == ""
    assert not list(path.parent.glob("submission*.json"))


def test_actual_owned_plan_service_and_jobs_reuse_exact_prepared_manifest(prepared):
    _root, path, packet = prepared
    options = assembly_options(prepared)
    assembly = runner.assemble_prepared(path, **options)
    assert type(assembly.service) is PlanService and type(assembly.jobs) is PgPlanningJobRepository
    assert assembly.jobs._max_attempts == 4
    actual = assembly.factory.build_submission(options["scope"], options["project_id"],
        runner.goal_spec_from_payload(packet["goal_spec"]), 0)
    assert actual == packet["manifest"] and actual["owned_acceptance"]["version"] == runner.OWNED_ACCEPTANCE_GATE
    with pytest.raises(LLMNotDispatchedError):
        assembly.factory(options["scope"], options["project_id"], "new-only", manifest=actual,
            write_fence=None, thread_id="new-thread", guard=lambda: None)


def test_real_plan_service_submit_creates_only_one_new_run_and_no_attempts(prepared, monkeypatch):
    from app.infrastructure.db.plan_repository import PgPlanRepository
    _root, path, packet = prepared
    enqueued = []
    monkeypatch.setattr(PgPlanRepository, "get_current", lambda self, **_kw: None)
    monkeypatch.setattr(PgPlanningJobRepository, "enqueue", lambda self, run, initial, manifest: enqueued.append((run, initial, manifest)))
    options = assembly_options(prepared)
    run_id = runner.submit_prepared(path, **options)
    assert len(enqueued) == 1 and enqueued[0][0].run_id == run_id
    assert enqueued[0][2] == packet["manifest"]
    assert enqueued[0][1]["manifest"] == packet["manifest"]
    assert json.loads((path.parent / "submission.json").read_bytes())["run_id"] == run_id
    with pytest.raises(FileExistsError):
        runner.submit_prepared(path, **options)
    assert len(enqueued) == 1
    claim = JobClaim("new-job", run_id, "new-project", "owned", "new-lease")
    with pytest.raises(LLMNotDispatchedError):
        runner.execute_claim(path, claim=claim, guard=lambda: None, **options)
    assert len(enqueued) == 1


@pytest.mark.parametrize("changes", [
    {"owner_approved": False}, {"owner_approved": 1}, {"owner_evidence": ""}, {"actions": ["approve"]},
    {"actions": ["submit"]}, {"acceptance_id": "old-acceptance"}, {"packet_hash": "b" * 64},
    {"issued_at": "2026-01-01T00:00:00+00:00"}, {"issued_at": "2099-01-01T00:00:00+00:00"},
])
def test_old_missing_or_invalid_owner_evidence_cannot_authorize_execution(prepared, changes):
    _root, _path, packet = prepared
    evidence, digest = owner_evidence(prepared, **changes)
    with pytest.raises(ValidationAppError):
        runner.owner_authorization(packet, evidence, sha256=digest, action="execute")


@pytest.mark.parametrize("field", ["request_plan", "budget", "request_options"])
def test_purpose_limit_complete_budget_and_options_cannot_expand_in_owner_evidence(prepared, field):
    _root, _path, packet = prepared
    changed = deepcopy(packet[field] if field != "budget" else packet["manifest"]["budget"])
    changed[next(iter(changed))] = 999
    evidence, digest = owner_evidence(prepared, **{field: changed})
    with pytest.raises(ValidationAppError):
        runner.owner_authorization(packet, evidence, sha256=digest, action="execute")


@pytest.mark.parametrize("first_approved", [False, True])
def test_owner_hash_and_authority_use_same_bytes_when_file_changes_after_first_read(prepared, monkeypatch, first_approved):
    _root, _path, packet = prepared
    evidence, digest = owner_evidence(prepared, owner_approved=first_approved)
    first = evidence.read_bytes()
    replacement = json.loads(first)
    replacement["owner_approved"] = not first_approved
    original_read = Path.read_bytes
    reads = []

    def replaced_read(path):
        if path == evidence:
            reads.append(path)
            if len(reads) == 1:
                path.write_text(json.dumps(replacement), encoding="utf-8")
                return first
        return original_read(path)

    monkeypatch.setattr(Path, "read_bytes", replaced_read)
    if first_approved:
        assert runner.owner_authorization(packet, evidence, sha256=digest, action="execute")["owner_approved"] is True
    else:
        with pytest.raises(ValidationAppError):
            runner.owner_authorization(packet, evidence, sha256=digest, action="execute")
    assert reads == [evidence]


@pytest.mark.parametrize("raw", [b"\xff", b'{"owner_approved":true,"owner_approved":false}', b"x" * (4 * 1024 * 1024 + 1)],
    ids=["invalid-utf8", "duplicate-key", "oversized"])
def test_hash_matched_owner_bytes_still_require_utf8_unique_keys_and_size_limit(prepared, raw):
    _root, path, packet = prepared
    evidence = path.parent / "synthetic-owner-invalid.json"
    evidence.write_bytes(raw)
    with pytest.raises(ValidationAppError):
        runner.owner_authorization(packet, evidence, sha256=hashlib.sha256(raw).hexdigest(), action="execute")


def test_whole_manifest_budget_rejects_default_research_budget_before_external_ports(prepared):
    _root, _path, packet = prepared
    manifest = deepcopy(packet["manifest"])
    manifest["budget"] = runner.asdict(ResearchBudget())
    manifest["manifest_hash"] = content_hash({k: v for k, v in manifest.items() if k != "manifest_hash"})
    with pytest.raises(ValidationAppError):
        runner.request_plan(manifest)


@pytest.mark.parametrize("tamper", ["manifest", "source", "runner", "head"])
def test_manifest_full_snapshot_and_implementation_changes_reject_before_assembly(prepared, tamper):
    root, path, packet = prepared
    changed = deepcopy(packet)
    if tamper == "source":
        source = Path(packet["source_facts_ref"]["path"])
        source.write_bytes(source.read_bytes() + b" ")
    elif tamper == "manifest":
        changed["manifest"]["budget"]["max_total_requests"] += 1
    else:
        changed["runner_sha256" if tamper == "runner" else "head"] = "b" * (64 if tamper == "runner" else 40)
    changed["packet_hash"] = content_hash({k: v for k, v in changed.items() if k != "packet_hash"})
    path.write_text(json.dumps(changed), encoding="utf-8")
    with pytest.raises(ValidationAppError):
        runner.load_prepared(path, root=root)


def test_no_external_options_or_formal_database_fallback_can_enable_runner(prepared):
    _root, path, _packet = prepared
    for changes in ({"external_options": {"provider_resolver": lambda *_: pytest.fail("Resolver called")}},
                    {"dsn": "postgresql://private:private@127.0.0.1/studyplan_formal"}):
        with pytest.raises(ValidationAppError):
            runner.assemble_prepared(path, **assembly_options(prepared, **changes))


def test_cli_help_exposes_controlled_driver_without_auto_authorize_or_retry(capsys):
    with pytest.raises(SystemExit) as stopped:
        runner.main(["--help"])
    assert stopped.value.code == 0
    output = capsys.readouterr().out
    assert "external-request" in output and "preflight" in output and "decide" in output and "tick" in output
    assert "authorize," not in output and "sub.add_parser(\"retry\")" not in output
