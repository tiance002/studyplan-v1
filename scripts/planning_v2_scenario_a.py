"""Tracked Scenario A preparation and scoped owned assembly; default external zero.

CLI preparation freezes the complete SourceFacts before the manifest. Owner
authorization is a separate, private evidence file supplied with its SHA256;
preparation never creates an approval. The Python entry uses the existing
PlanService, review gates, claim fence, checkpoints and PgV2Calls ledger.

This is not a complete paid acceptance harness. It does not create databases or
accounts, inspect price/balance, manage the global paid/search journals, decide
reviews, retry, publish, or start a polling Worker. A future authorized harness
must supply its audited private ports and an existing exact Worker claim.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import uuid
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.errors import ValidationAppError
from app.core.ids import canonical_json, content_hash
from app.domain.planning.intent import GoalSpec, goal_spec_from_payload, goal_spec_payload
from app.domain.planning.resource_research import ResearchBudget
from app.domain.planning.v2_runtime import (
    OWNED_ACCEPTANCE_GATE,
    PURPOSE_SCHEMAS,
    build_v2_manifest,
    manifest_intact,
    owned_acceptance_policy,
    wire,
)
from app.domain.workspace.models import AuthContext
from app.ports.llm import LLMNotDispatchedError
from app.ports.planning_jobs import JobClaim

from scripts.planning_v2_owned_source_facts import (
    FrozenOwnedV2PlanningRuntimeFactory,
    FrozenSourceFactsRef,
    freeze_reviewed_source_facts,
    freeze_source_facts,
    read_source_facts,
)

ROOT = Path(__file__).resolve().parents[1]
VERSION = "owned-scenario-a-preparation-v1"
OWNER_VERSION = "owned-scenario-a-owner-evidence-v1"


def _reject(field):
    raise ValidationAppError("Owned Scenario A input rejected", field=field)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _reject("duplicate_json_key")
        result[key] = value
    return result


def _decode(raw):
    try:
        if len(raw) > 4 * 1024 * 1024:
            _reject("evidence_size")
        return json.loads(raw.decode("utf-8-sig"), object_pairs_hook=_unique)
    except (ValueError, UnicodeError):
        _reject("evidence_read")


def _read(path):
    try:
        return _decode(Path(path).read_bytes())
    except OSError:
        _reject("evidence_read")


def _exclusive(path, payload):
    with Path(path).open("xb") as stream:
        stream.write(canonical_json(wire(payload)).encode("utf-8"))
        stream.flush()
        os.fsync(stream.fileno())


def _head(root):
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()


def _private_output(output, root):
    output, root = Path(output), Path(root).resolve()
    if not output.is_absolute():
        output = root / output
    # Check every existing parent before resolving; do not write through links.
    if any(p.is_symlink() for p in (output, *output.parents)):
        _reject("output_link")
    output = output.resolve()
    if not output.is_relative_to(root / "var"):
        _reject("output_must_be_ignored_var")
    ignored = subprocess.run(["git", "check-ignore", "--quiet", str(output / "prepared.json")], cwd=root)
    if ignored.returncode != 0:
        _reject("output_not_ignored")
    return output


def scenario_budget():
    """Existing Scenario A worst reservations; these are internal units, not cash."""
    return ResearchBudget(max_searches=6, max_candidates=8, max_body_bytes=393216,
        max_reader_requests=6, max_output_tokens=18432, max_total_requests=27, max_cost_micros=186000)


def request_plan(manifest):
    """Review the entire existing owned policy, rather than just its next call."""
    if not manifest_intact(manifest) or manifest.get("owned_acceptance") != owned_acceptance_policy():
        _reject("owned_manifest")
    limits, budget = manifest["owned_acceptance"]["purpose_limits"], manifest["budget"]
    models = sum(limits[p] for p in PURPOSE_SCHEMAS)
    plan = {"purpose_limits": dict(limits), "model_requests": models,
        "search_requests": limits["research.search"], "body_operations": limits["research.body"],
        "body_http_requests": 2 * limits["research.body"], "metadata_requests": 0,
        "output_tokens": sum(limits[p] * manifest["output_caps"][p] for p in PURPOSE_SCHEMAS),
        "body_bytes": 65536 * limits["research.body"], "retry_limit": 0, "repair_limit": 0, "run_limit": 1}
    # The same worst reservations used by PgV2Calls/DurableIndex/DurableBody.
    plan["total_requests"] = models + plan["search_requests"] + plan["body_http_requests"]
    plan["cost_micros"] = models * budget["reader_cost_micros"] + plan["search_requests"] * budget["search_cost_micros"]
    for metric, amount in {"searches": plan["search_requests"], "reader_requests": limits["planning.research_reader"],
        "output_tokens": plan["output_tokens"], "body_bytes": plan["body_bytes"],
        "total_requests": plan["total_requests"], "cost_micros": plan["cost_micros"]}.items():
        if amount > budget["max_" + metric]:
            _reject("incomplete_manifest_budget")
    return plan


def _options(options, manifest):
    if type(options) is not dict or set(options) != set(PURPOSE_SCHEMAS):
        _reject("request_options")
    model = None
    for purpose, value in options.items():
        if (type(value) is not dict or set(value) not in ({"model", "max_tokens"}, {"model", "max_tokens", "thinking"})
            or type(value.get("model")) is not str or not 0 < len(value["model"]) <= 200
            or type(value.get("max_tokens")) is not int or value["max_tokens"] != manifest["output_caps"][purpose]
            or ("thinking" in value and value["thinking"] != {"type": "disabled"})):
            _reject("request_options")
        model = value["model"] if model is None else model
        if model != value["model"]:
            _reject("request_model_mismatch")


def prepare(output, *, goal, model_ref, request_options, root=ROOT, facts=None, budget=None):
    """Zero-network/zero-DB preparation for a fresh batch; existing dirs reject."""
    if type(goal) is not GoalSpec:
        _reject("goal")
    output = _private_output(output, root)
    output.mkdir(parents=True, exist_ok=False)
    reference = (freeze_reviewed_source_facts(output / "source-facts.json", root=root) if facts is None
        else freeze_source_facts(output / "source-facts.json", facts))
    manifest = build_v2_manifest(goal, model_ref=model_ref, source_facts=read_source_facts(reference),
        budget=budget or scenario_budget(), checked_at=datetime.now(timezone.utc).isoformat(), expected_version=0,
        product_semantics="planning-v2-product-v2", acceptance_gate=OWNED_ACCEPTANCE_GATE)
    plan = request_plan(manifest)
    _options(request_options, manifest)
    packet = {"version": VERSION, "acceptance_id": "scenario-a-" + uuid.uuid4().hex,
        "repository_root": str(Path(root).resolve()), "head": _head(root),
        "runner_sha256": _sha(Path(__file__).read_bytes()), "goal_spec": wire(goal_spec_payload(goal)),
        "source_facts_ref": asdict(reference), "manifest": manifest,
        "request_options": deepcopy(request_options), "request_plan": plan}
    packet["packet_hash"] = content_hash(packet)
    _exclusive(output / "prepared.json", packet)
    # An unsigned request template is not an approval; no authorize command exists.
    _exclusive(output / "owner-authorization-request.json", {"version": OWNER_VERSION,
        "acceptance_id": packet["acceptance_id"], "packet_hash": packet["packet_hash"], "owner_approved": False,
        "owner_evidence": "", "issued_at": "", "actions": [], "request_plan": plan,
        "budget": manifest["budget"], "request_options": packet["request_options"]})
    return packet


def load_prepared(path, *, root=ROOT):
    path = Path(path)
    _private_output(path.parent, root)
    packet = _read(path)
    expected = {"version", "acceptance_id", "repository_root", "head", "runner_sha256", "goal_spec",
        "source_facts_ref", "manifest", "request_options", "request_plan", "packet_hash"}
    if (type(packet) is not dict or set(packet) != expected or packet["version"] != VERSION
        or packet["packet_hash"] != content_hash({k: v for k, v in packet.items() if k != "packet_hash"})
        or packet["repository_root"] != str(Path(root).resolve()) or packet["head"] != _head(root)
        or packet["runner_sha256"] != _sha(Path(__file__).read_bytes())):
        _reject("prepared_integrity")
    try:
        if str(uuid.UUID(packet["acceptance_id"].removeprefix("scenario-a-"))).replace("-", "") != packet["acceptance_id"].removeprefix("scenario-a-"):
            _reject("acceptance_id")
        reference = FrozenSourceFactsRef.from_payload(packet["source_facts_ref"])
        if Path(reference.path) != path.resolve().parent / "source-facts.json":
            _reject("source_facts_location")
        read_source_facts(reference, manifest=packet["manifest"])
        goal = goal_spec_from_payload(packet["goal_spec"])
        if packet["manifest"]["goal_hash"] != content_hash(goal_spec_payload(goal)):
            _reject("goal_hash")
        if canonical_json(packet["request_plan"]) != canonical_json(request_plan(packet["manifest"])):
            _reject("request_plan")
        _options(packet["request_options"], packet["manifest"])
    except (ValueError, TypeError, KeyError, AttributeError):
        _reject("prepared_fields")
    return packet


def owner_authorization(packet, path, *, sha256, action):
    """Only caller-supplied fresh Owner evidence can authorize an action.

    The file and its hash receipt must be owner-controlled, like SourceFactsRef;
    hashes provide integrity, not authentication of an attacker-written grant.
    """
    raw = Path(path).read_bytes()
    if type(sha256) is not str or _sha(raw) != sha256:
        _reject("owner_evidence_hash")
    # Parse the exact bytes whose hash was verified. A second read could see a
    # replacement grant and bind its authority to the original file's receipt.
    grant = _decode(raw)
    expected = {"version", "acceptance_id", "packet_hash", "owner_approved", "owner_evidence", "issued_at",
        "actions", "request_plan", "budget", "request_options"}
    if (type(grant) is not dict or set(grant) != expected or grant["version"] != OWNER_VERSION
        or grant["owner_approved"] is not True or grant["acceptance_id"] != packet["acceptance_id"]
        or grant["packet_hash"] != packet["packet_hash"] or type(grant["owner_evidence"]) is not str
        or not 1 <= len(grant["owner_evidence"].strip()) <= 2000 or type(grant["actions"]) is not list
        or not grant["actions"] or len(set(grant["actions"])) != len(grant["actions"])
        or set(grant["actions"]) - {"submit", "execute"} or action not in grant["actions"]):
        _reject("owner_authorization")
    try:
        issued = datetime.fromisoformat(grant["issued_at"])
        prepared = datetime.fromisoformat(packet["manifest"]["checked_at"])
        current = datetime.now(timezone.utc)
        if issued.tzinfo is None or not prepared <= issued <= current or (current - issued).total_seconds() > 86400:
            _reject("fresh_owner_authorization")
    except (ValueError, TypeError):
        _reject("owner_timestamp")
    for field, actual in (("request_plan", packet["request_plan"]), ("budget", packet["manifest"]["budget"]),
        ("request_options", packet["request_options"])):
        if canonical_json(grant[field]) != canonical_json(actual):
            _reject("owner_" + field)
    return grant


def _external_disabled(*_args, **_kwargs):
    raise LLMNotDispatchedError("Scenario A external ports require a separately audited authorized harness")


class PreparedScenarioAFactory(FrozenOwnedV2PlanningRuntimeFactory):
    """Use the exact reviewed preparation manifest, including checked_at."""

    def __init__(self, *args, packet, **kwargs):
        self.packet = deepcopy(packet)
        super().__init__(*args, **kwargs)

    def build_submission(self, scope, project_id, goal_spec, expected_version):
        scope.require_project(project_id)
        manifest = self.packet["manifest"]
        if expected_version != 0 or content_hash(goal_spec_payload(goal_spec)) != manifest["goal_hash"]:
            _reject("prepared_submission")
        read_source_facts(self.snapshot, manifest=manifest)
        return deepcopy(manifest)


def assemble_prepared(path, *, dsn, checkpoint_dsn, scope, project_id, authorization, authorization_sha256,
                      action="submit", root=ROOT, external_options=None):
    """Real owned assembly, default all external ports disabled.

    external_options is an explicit private dependency supplied by a future
    audited harness, not loaded from JSON/CLI or dynamically imported modules.
    The existing durable ledger remains the sole dispatch/count authority.
    """
    packet = load_prepared(path, root=root)
    if type(scope) is not AuthContext:
        _reject("server_scope")
    scope.require_project(project_id)
    owner_authorization(packet, authorization, sha256=authorization_sha256, action=action)
    from app.application.plan_service import PlanService
    from app.infrastructure.db.job_repository import PgPlanningJobRepository
    from app.infrastructure.db.plan_repository import PgPlanRepository
    from app.infrastructure.db.public_resource_catalog import PgPublicResourceCatalog
    from app.infrastructure.db.run_repository import PgRunRepository

    if external_options is not None:
        # A default or JSON-configured resolver could accidentally dispatch.
        # Full audited transport/global-quota assembly has not been migrated.
        _reject("external_transport_runner_not_implemented")
    factory = PreparedScenarioAFactory(dsn, checkpoint_dsn, packet=packet,
        snapshot=FrozenSourceFactsRef.from_payload(packet["source_facts_ref"]),
        budget=ResearchBudget(**packet["manifest"]["budget"]),
        binding_resolver=lambda *_: SimpleNamespace(model_ref=packet["manifest"]["model_ref"]),
        provider_resolver=_external_disabled, acceptance_gate=OWNED_ACCEPTANCE_GATE)
    jobs = PgPlanningJobRepository(dsn, actor_ids=(scope.actor_id,), max_attempts=4)

    class ForbiddenLegacy:
        def __getattr__(self, _name):
            _reject("legacy_port")

    service = PlanService(repository=PgPlanRepository(dsn), runs=PgRunRepository(dsn), catalog=ForbiddenLegacy(),
        resources=PgPublicResourceCatalog(dsn), llm=ForbiddenLegacy(), graph_version="",
        planning_jobs=jobs, v2_runtime_factory=factory)
    return SimpleNamespace(packet=packet, factory=factory, jobs=jobs, service=service, scope=scope, project_id=project_id)


def submit_prepared(path, **options):
    """One new owned submission; a crash after start cannot create a second Run."""
    folder = Path(path).resolve().parent
    assembly = assemble_prepared(path, action="submit", **options)
    _exclusive(folder / "submission-started.json", {"acceptance_id": assembly.packet["acceptance_id"],
        "packet_hash": assembly.packet["packet_hash"], "actor_id": assembly.scope.actor_id,
        "project_id": assembly.project_id, "automatic_retry": False})
    run_id = assembly.service.submit_owned_v2(scope=assembly.scope, project_id=assembly.project_id,
        goal_spec=goal_spec_from_payload(assembly.packet["goal_spec"]))
    _exclusive(folder / "submission.json", {"run_id": run_id, "actor_id": assembly.scope.actor_id,
        "project_id": assembly.project_id, "manifest": assembly.packet["manifest"]})
    return run_id


def execute_claim(path, *, claim, guard, **options):
    """Default-denied exact claim entry; never selects another Run or polls jobs."""
    assembly = assemble_prepared(path, action="execute", **options)
    submission = _read(Path(path).resolve().parent / "submission.json")
    if (type(claim) is not JobClaim or claim.run_id != submission["run_id"]
        or claim.actor_id != assembly.scope.actor_id or claim.project_id != assembly.project_id
        or submission["manifest"] != assembly.packet["manifest"]):
        _reject("exact_owned_claim")
    guard()
    # No unsupported paid action is allowed to turn a live job into a failed
    # dispatch. Keep the claim/review untouched until the full harness exists.
    _external_disabled()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    prep = sub.add_parser("prepare", help="Freeze new local facts and manifest; external/DB requests zero")
    prep.add_argument("--goal-file", required=True)
    prep.add_argument("--request-options-file", required=True)
    prep.add_argument("--model-ref", required=True)
    prep.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    packet = prepare(args.output, goal=goal_spec_from_payload(_read(args.goal_file)), model_ref=args.model_ref,
        request_options=_read(args.request_options_file))
    print(canonical_json({"acceptance_id": packet["acceptance_id"], "manifest_hash": packet["manifest"]["manifest_hash"],
        "request_plan": packet["request_plan"], "external_requests": 0, "database_requests": 0,
        "execution_ready": False}))


if __name__ == "__main__":
    main()
