"""Tracked owned Scenario A preparation, dispatch and independent review driver.

CLI preparation freezes the complete SourceFacts before the manifest. Owner
authorization is a separate, private evidence file supplied with its SHA256;
preparation never creates an approval. The Python entry uses the existing
PlanService, review gates, claim fence, checkpoints and PgV2Calls ledger.

External actions require a separate fresh Owner grant and reviewed official
price/balance receipts. Commands never create accounts/databases, retry, repair,
publish or approve a semantic review automatically. Credentials stay in local
environment variables; all evidence stays under ignored var/.
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
from urllib.parse import urlsplit

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.errors import ValidationAppError
from app.core.ids import canonical_json, content_hash
from app.domain.planning.capability_decisions import CAPABILITY_DECISION_PROTOCOL
from app.domain.planning.intent import GoalSpec, goal_spec_from_payload, goal_spec_payload
from app.domain.planning.resource_research import ResearchBudget
from app.domain.planning.v2_runtime import (
    OWNED_ACCEPTANCE_GATE,
    PURPOSE_SCHEMAS,
    build_v2_manifest,
    manifest_intact,
    owned_acceptance_policy,
    purpose_schema,
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
VERSION = "owned-scenario-a-preparation-v2"
OWNER_VERSION = "owned-scenario-a-owner-evidence-v1"
REVIEW_VERSION = "owned-scenario-a-independent-review-v1"


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


def _code_hashes():
    # Freeze the entire tracked driver, including the cold-source decoder and
    # external dispatch helper; a different helper cannot resume this packet.
    files = (Path(__file__), Path(__file__).with_name("planning_v2_owned_source_facts.py"),
             Path(__file__).with_name("planning_v2_acceptance_external.py"))
    return {p.name: _sha(p.read_bytes()) for p in files if p.exists()}


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
    if "capability_output_protocol" in manifest:
        plan["schema_names"] = {purpose: purpose_schema(manifest, purpose) for purpose in PURPOSE_SCHEMAS}
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


def prepare(output, *, goal, model_ref, request_options, root=ROOT, facts=None, budget=None,
            capability_output_protocol=None):
    """Zero-network/zero-DB preparation for a fresh batch; existing dirs reject."""
    if type(goal) is not GoalSpec:
        _reject("goal")
    output = _private_output(output, root)
    output.mkdir(parents=True, exist_ok=False)
    reference = (freeze_reviewed_source_facts(output / "source-facts.json", root=root) if facts is None
        else freeze_source_facts(output / "source-facts.json", facts))
    manifest = build_v2_manifest(goal, model_ref=model_ref, source_facts=read_source_facts(reference),
        budget=budget or scenario_budget(), checked_at=datetime.now(timezone.utc).isoformat(), expected_version=0,
        product_semantics="planning-v2-product-v2", acceptance_gate=OWNED_ACCEPTANCE_GATE,
        capability_output_protocol=capability_output_protocol)
    plan = request_plan(manifest)
    _options(request_options, manifest)
    packet = {"version": VERSION, "acceptance_id": "scenario-a-" + uuid.uuid4().hex,
        "repository_root": str(Path(root).resolve()), "head": _head(root),
        "runner_sha256": _sha(Path(__file__).read_bytes()), "code_hashes": _code_hashes(),
        "goal_spec": wire(goal_spec_payload(goal)),
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
    expected = {"version", "acceptance_id", "repository_root", "head", "runner_sha256", "code_hashes", "goal_spec",
        "source_facts_ref", "manifest", "request_options", "request_plan", "packet_hash"}
    if (type(packet) is not dict or set(packet) != expected or packet["version"] != VERSION
        or packet["packet_hash"] != content_hash({k: v for k, v in packet.items() if k != "packet_hash"})
        or packet["repository_root"] != str(Path(root).resolve()) or packet["head"] != _head(root)
        or packet["runner_sha256"] != _sha(Path(__file__).read_bytes())
        or packet["code_hashes"] != _code_hashes()):
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
        or set(grant["actions"]) - {"submit", "execute", "review"} or action not in grant["actions"]):
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


def _validated_owned_dsn(dsn):
    """No libpq URL/environment override may redirect the owned connection."""
    from app.infrastructure.db.v2_owned_reviews import _owned_dsn
    from psycopg.conninfo import conninfo_to_dict
    if type(dsn) is not str or any(os.environ.get(k) for k in ("PGHOSTADDR", "PGSERVICE", "PGSERVICEFILE")):
        _reject("owned_dsn_override")
    try:
        normalized = _owned_dsn(dsn)
        parsed, effective = urlsplit(normalized), conninfo_to_dict(normalized)
        if (parsed.query or parsed.fragment or effective.get("host") not in {"127.0.0.1", "::1", "localhost"}
                or not effective.get("dbname", "").startswith("studyplan_test_")
                or any(k in effective for k in ("hostaddr", "service", "servicefile"))):
            _reject("owned_dsn_override")
        return normalized
    except (ValueError, TypeError):
        _reject("owned_dsn")


def _owned_pair(dsn, checkpoint_dsn):
    from psycopg.conninfo import conninfo_to_dict
    pair = (_validated_owned_dsn(dsn), _validated_owned_dsn(checkpoint_dsn))
    effective = [conninfo_to_dict(value) for value in pair]
    # Different users, URL encodings or loopback aliases do not make two DBs.
    try:
        identities = [(int(v.get("port") or os.environ.get("PGPORT") or "5432"), v["dbname"]) for v in effective]
    except ValueError:
        _reject("owned_database_port")
    if any(not 1 <= port <= 65535 for port, _database in identities):
        _reject("owned_database_port")
    if identities[0] == identities[1]:
        _reject("owned_database_pair")
    return pair


class PreparedScenarioAFactory(FrozenOwnedV2PlanningRuntimeFactory):
    """Use the exact reviewed preparation manifest, including checked_at."""

    def __init__(self, *args, packet, external=None, **kwargs):
        self.packet = deepcopy(packet)
        self.external = external
        super().__init__(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        runtime = super().__call__(*args, **kwargs)
        if self.external is not None:
            self.external.bind_calls(runtime.calls)
        return runtime

    def build_submission(self, scope, project_id, goal_spec, expected_version):
        scope.require_project(project_id)
        manifest = self.packet["manifest"]
        if expected_version != 0 or content_hash(goal_spec_payload(goal_spec)) != manifest["goal_hash"]:
            _reject("prepared_submission")
        read_source_facts(self.snapshot, manifest=manifest)
        return deepcopy(manifest)


def assemble_prepared(path, *, dsn, checkpoint_dsn, scope, project_id, authorization, authorization_sha256,
                      action="submit", root=ROOT, external_options=None, external=None, external_settings=None):
    """Real owned assembly, default all external ports disabled.

    Only the tracked typed external helper can supply dispatch ports. Arbitrary
    JSON resolvers/imports remain rejected. PgV2Calls remains the durable root
    budget/fence/receipt authority alongside the global append-only journals.
    """
    dsn, checkpoint_dsn = _owned_pair(dsn, checkpoint_dsn)
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
        _reject("arbitrary_external_options")
    ports = SimpleNamespace(github=None, web=None, body_reader=None)
    resolver = _external_disabled
    if external is not None:
        from scripts.planning_v2_acceptance_external import AcceptanceExternal
        if not isinstance(external, AcceptanceExternal) or external.packet != packet or external_settings is None:
            _reject("external_packet_binding")
        if action != "submit":
            saved = _read(Path(path).resolve().parent / "submission.json")
            if (saved.get("manifest") != packet["manifest"] or saved.get("project_id") != project_id
                    or saved.get("actor_id") != scope.actor_id):
                _reject("external_submission_binding")
            external.bind_run(saved["run_id"], project_id, scope.actor_id)
        external.check("submit" if action in {"submit", "review"} else "execute")
        ports = external.resource_ports(external_settings)
        def resolver(actual_scope, actual_project, actual_run, model_ref):
            if (actual_scope.actor_id != scope.actor_id or actual_project != project_id
                    or model_ref != packet["manifest"]["model_ref"]):
                _reject("external_runtime_binding")
            external.bind_run(actual_run, project_id, scope.actor_id)
            return external.provider(external_settings, actual_run)
    factory = PreparedScenarioAFactory(dsn, checkpoint_dsn, packet=packet, external=external,
        snapshot=FrozenSourceFactsRef.from_payload(packet["source_facts_ref"]),
        budget=ResearchBudget(**packet["manifest"]["budget"]),
        binding_resolver=lambda *_: SimpleNamespace(model_ref=packet["manifest"]["model_ref"]),
        provider_resolver=resolver, github=ports.github, web=ports.web, body_reader=ports.body_reader,
        acceptance_gate=OWNED_ACCEPTANCE_GATE)
    jobs = PgPlanningJobRepository(dsn, actor_ids=(scope.actor_id,), max_attempts=4)

    class ForbiddenLegacy:
        def __getattr__(self, _name):
            _reject("legacy_port")

    service = PlanService(repository=PgPlanRepository(dsn), runs=PgRunRepository(dsn), catalog=ForbiddenLegacy(),
        resources=PgPublicResourceCatalog(dsn), llm=ForbiddenLegacy(), graph_version="",
        planning_jobs=jobs, v2_runtime_factory=factory)
    return SimpleNamespace(packet=packet, factory=factory, jobs=jobs, service=service, scope=scope,
        project_id=project_id, dsn=dsn, external=external, path=Path(path).resolve())


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
    if assembly.external is not None:
        assembly.external.bind_run(run_id, assembly.project_id, assembly.scope.actor_id)
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
    if assembly.external is None:
        _external_disabled()
    return assembly.service.execute_generation(claim.project_id, claim.run_id, guard=guard, claim=claim)


def _submission(assembly):
    value = _read(assembly.path.parent / "submission.json")
    if (type(value) is not dict or set(value) != {"run_id", "actor_id", "project_id", "manifest"}
            or value["actor_id"] != assembly.scope.actor_id or value["project_id"] != assembly.project_id
            or canonical_json(value["manifest"]) != canonical_json(assembly.packet["manifest"])):
        _reject("submission_binding")
    actual = assembly.jobs.read_submission(assembly.project_id, value["run_id"])
    if canonical_json(actual["manifest"]) != canonical_json(value["manifest"]):
        _reject("database_manifest_binding")
    if assembly.external is not None:
        assembly.external.bind_run(value["run_id"], assembly.project_id, assembly.scope.actor_id)
    return value


def _record_once(path, payload):
    """Cold retries of evidence writes are idempotent, never overwrites."""
    try:
        _exclusive(path, payload)
    except FileExistsError:
        if canonical_json(_read(path)) != canonical_json(wire(payload)):
            _reject("immutable_evidence_conflict")


def worker_tick(path, **options):
    """One native Worker claim, constrained to the frozen Run before mutation."""
    assembly = assemble_prepared(path, action="execute", **options)
    if assembly.external is None:
        _external_disabled()  # before claim; preparation never spends an attempt.
    submission = _submission(assembly)
    from app.core.ids import new_id
    from app.infrastructure.db.job_repository import PgPlanningJobRepository
    from app.infrastructure.worker.planning_worker import PlanningWorker

    class ExactJobs(PgPlanningJobRepository):
        def list_projects(self, actor_id):
            if actor_id != assembly.scope.actor_id:
                _reject("worker_actor")
            return (assembly.project_id,)

        def claim(self, project_id, worker_id, lease_seconds):
            # Use the existing claim transaction and lease semantics, with an
            # exact run selector. Another job is never claimed then rejected.
            if project_id != assembly.project_id:
                _reject("worker_project")
            with self._tx(actor_id=assembly.scope.actor_id, project_id=project_id) as conn:
                row = conn.execute("""SELECT j.job_id FROM ai_jobs j JOIN ai_runs r USING(run_id)
                    JOIN learning_projects p ON p.project_id=r.project_id
                    WHERE r.run_id=%s AND r.project_id=%s AND r.actor_id=%s
                    AND p.owner_actor_id=r.actor_id AND p.archived_at IS NULL
                    AND r.kind='plan_generate' AND r.graph_version='planning-v2-execution-v1'
                    AND r.status IN('queued','running')
                    AND NOT EXISTS(SELECT 1 FROM ai_provider_attempts a WHERE a.run_id=r.run_id
                        AND a.status IN('dispatched','reconciliation_required'))
                    AND (j.status='pending' OR (j.status='running' AND j.lease_expires_at<now()))
                    AND j.available_at<=now() AND j.attempts<%s FOR UPDATE OF j SKIP LOCKED""",
                    (submission["run_id"], project_id, assembly.scope.actor_id, self._max_attempts)).fetchone()
                if row is None:
                    return None
                token = new_id("lease")
                conn.execute("""UPDATE ai_jobs SET status='running',lease_token=%s,
                    lease_expires_at=now()+(%s * interval '1 second'),worker_id=%s,attempts=attempts+1
                    WHERE job_id=%s""", (token, lease_seconds, worker_id, row["job_id"]))
                changed = conn.execute("""UPDATE ai_runs SET status='running',next_action='wait',
                    version=version+1,updated_at=now() WHERE run_id=%s AND status IN('queued','running')""",
                    (submission["run_id"],))
                if changed.rowcount != 1:
                    _reject("worker_claim_cas")
                return JobClaim(row["job_id"], submission["run_id"], project_id, assembly.scope.actor_id, token)

    jobs = ExactJobs(assembly.dsn, actor_ids=(assembly.scope.actor_id,), max_attempts=4)
    def execute(project_id, run_id, *, guard, claim):
        def checked_guard():
            guard()
            # Reload the exact frozen files on every dispatch/recovery guard.
            load_prepared(path, root=options.get("root", ROOT))
            try:
                assembly.external.check("execute")
            except ValidationAppError:
                stopped = assembly.path.parent / "STOP.json"
                if stopped.exists() and _read(stopped).get("unknown") is True:
                    # PgV2Calls guards after storing the receipt as well as
                    # before dispatch. Preserve unknown reconciliation here;
                    # never turn it into an ordinary validation failure.
                    from app.domain.planning.v2_runtime import V2RecoveryBlocked
                    raise V2RecoveryBlocked("Owned external outcome requires reconciliation") from None
                raise
        return assembly.service.execute_generation(project_id, run_id, guard=checked_guard, claim=claim)
    worker = PlanningWorker(jobs=jobs, execute=execute, actor_ids=(assembly.scope.actor_id,))
    if not jobs.acquire_worker_lock():
        _reject("owned_worker_lock")
    try:
        return worker.tick()
    finally:
        jobs.release_worker_lock()
        assembly.external.close()


def read_review(path, **options):
    assembly = assemble_prepared(path, action="review", **options)
    submission = _submission(assembly)
    packet = assembly.factory.reviews().read(scope=assembly.scope, project_id=assembly.project_id,
        run_id=submission["run_id"])
    _record_once(assembly.path.parent / ("review-packet-" + packet["review"]["stage"] + ".json"), packet)
    return packet


def review_request(packet, frozen):
    row = frozen["review"]
    return {"version": REVIEW_VERSION, "acceptance_id": packet["acceptance_id"],
        "packet_hash": packet["packet_hash"], **{k: row[k] for k in
            ("run_id", "project_id", "actor_id", "stage", "run_version")},
        "review_hash": row["digest"], "state_hash": content_hash(frozen["state"]),
        "result": "NOT RUN", "reviewer": "", "rationale": "", "evidence_refs": []}


def validate_review_evidence(packet, frozen, evidence):
    row = frozen["review"]
    if (row.get("digest") != content_hash({k: v for k, v in row.items() if k != "digest"})
            or content_hash(frozen["state"]) != row.get("checkpoint_hash")
            or frozen["state"].get("stage") != row.get("stage")):
        _reject("review_checkpoint_integrity")
    expected = review_request(packet, frozen)
    tested_models = {v["model"] for v in packet["request_options"].values()}
    if (type(evidence) is not dict or set(evidence) != set(expected)
            or type(evidence["run_version"]) is not int
            or any(evidence[k] != expected[k] for k in expected if k not in
                {"result", "reviewer", "rationale", "evidence_refs"})
            or evidence["result"] not in {"PASS", "FAIL"}
            or type(evidence["reviewer"]) is not str or not evidence["reviewer"].strip()
            or evidence["reviewer"] in tested_models
            or type(evidence["rationale"]) is not str or not evidence["rationale"].strip()
            or type(evidence["evidence_refs"]) is not list or not evidence["evidence_refs"]
            or any(type(ref) is not str or not ref.strip() for ref in evidence["evidence_refs"])):
        _reject("independent_review_evidence")
    return "approve" if evidence["result"] == "PASS" else "reject"


def decide_review(path, *, stage, evidence, evidence_sha256, **options):
    assembly = assemble_prepared(path, action="review", **options)
    submission = _submission(assembly)
    from app.domain.planning.v2_runtime import OWNED_REVIEW_STAGES
    if stage not in OWNED_REVIEW_STAGES:
        _reject("review_stage")
    frozen = _read(assembly.path.parent / ("review-packet-" + stage + ".json"))
    row = frozen["review"]
    if (frozen["manifest"] != submission["manifest"] or row["run_id"] != submission["run_id"]
            or row["actor_id"] != assembly.scope.actor_id or row["project_id"] != assembly.project_id):
        _reject("review_submission_binding")
    raw = Path(evidence).read_bytes()
    if _sha(raw) != evidence_sha256:
        _reject("review_evidence_hash")
    decision = validate_review_evidence(assembly.packet, frozen, _decode(raw))
    intent = {"stage": stage, "review_hash": row["digest"], "expected_version": row["run_version"],
        "decision": decision, "evidence_hash": evidence_sha256,
        "idempotency_key": "independent-" + stage}
    # Persist intent first. A process lost after DB commit can repeat precisely
    # this same CAS/idempotency decision, not fabricate a different approval.
    _record_once(assembly.path.parent / ("decision-intent-" + stage + ".json"), intent)
    result = assembly.factory.reviews().decide(scope=assembly.scope, project_id=assembly.project_id,
        run_id=submission["run_id"], **intent)
    _record_once(assembly.path.parent / ("decision-" + stage + ".json"), intent | {"run_id": result})
    if decision == "reject":
        _record_once(assembly.path.parent / "STOP.json", {"phase": stage, "reason": "independent_semantic_fail",
            "retry": False})
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    prep = sub.add_parser("prepare", help="Freeze new local facts and manifest; external/DB requests zero")
    prep.add_argument("--goal-file", required=True)
    prep.add_argument("--request-options-file", required=True)
    prep.add_argument("--model-ref", required=True)
    prep.add_argument("--output", required=True)
    prep.add_argument("--capability-output-protocol", choices=(CAPABILITY_DECISION_PROTOCOL,))
    request = sub.add_parser("external-request", help="Write unsigned fresh external authorization request; zero network")
    request.add_argument("--packet", required=True)
    request.add_argument("--model-ledger", required=True)
    request.add_argument("--search-ledger", required=True)
    request.add_argument("--global-model-cap", type=int, required=True)
    request.add_argument("--global-search-cap", type=int, required=True)
    for command in ("preflight", "price-review-request", "approve-price", "submit", "tick", "review", "decide", "status"):
        command_parser = sub.add_parser(command)
        command_parser.add_argument("--packet", required=True)
        command_parser.add_argument("--external-grant")
        command_parser.add_argument("--external-grant-sha256")
        if command in {"submit", "tick", "review", "decide", "status"}:
            command_parser.add_argument("--authorization", required=True)
            command_parser.add_argument("--authorization-sha256", required=True)
            command_parser.add_argument("--dsn-env", required=True)
            command_parser.add_argument("--checkpoint-dsn-env", required=True)
            command_parser.add_argument("--session-env", required=True)
            command_parser.add_argument("--project-id", required=True)
        if command in {"approve-price", "decide"}:
            command_parser.add_argument("--evidence", required=True)
            command_parser.add_argument("--evidence-sha256", required=True)
        if command == "decide":
            command_parser.add_argument("--stage", required=True)
    args = parser.parse_args(argv)
    if args.action == "prepare":
        packet = prepare(args.output, goal=goal_spec_from_payload(_read(args.goal_file)), model_ref=args.model_ref,
            request_options=_read(args.request_options_file),
            capability_output_protocol=args.capability_output_protocol)
        print(canonical_json({"acceptance_id": packet["acceptance_id"], "manifest_hash": packet["manifest"]["manifest_hash"],
            "request_plan": packet["request_plan"], "external_requests": 0, "database_requests": 0,
            "external_authorization_required": True}))
        return
    from scripts.planning_v2_acceptance_external import AcceptanceExternal, external_authorization_request
    packet = load_prepared(args.packet)
    folder = Path(args.packet).resolve().parent
    if args.action == "external-request":
        grant = external_authorization_request(packet, evidence_dir=folder, model_ledger=args.model_ledger,
            search_ledger=args.search_ledger, global_model_cap=args.global_model_cap, global_search_cap=args.global_search_cap)
        _exclusive(folder / "external-authorization-request.json", grant)
        print("UNSIGNED_EXTERNAL_REQUEST_WRITTEN_ZERO_NETWORK")
        return
    external, settings = None, None
    if args.external_grant:
        # Read only paths/caps for construction. The helper verifies the exact
        # same file against the separately trusted Owner hash before any action.
        grant = _read(args.external_grant)
        external = AcceptanceExternal(packet, evidence_dir=folder, model_ledger=grant["model_ledger"],
            search_ledger=grant["search_ledger"], authorization=args.external_grant,
            authorization_sha256=args.external_grant_sha256, guard=lambda: load_prepared(args.packet))
        from app.core.config import get_settings
        settings = get_settings()
    try:
        if args.action in {"preflight", "price-review-request", "approve-price"}:
            if external is None:
                _external_disabled()
            if args.action == "preflight":
                external.preflight(settings)
                print("METADATA_RECEIVED_PRICE_REVIEW_REQUIRED")
            elif args.action == "price-review-request":
                _record_once(folder / "price-review-request.json", external.price_review_request())
                print("UNSIGNED_PRICE_REVIEW_WRITTEN")
            else:
                external.approve_price(args.evidence, sha256=args.evidence_sha256)
                print("PRICE_REVIEW_BOUND_ESTIMATE_ONLY")
            return
        from app.infrastructure.db.browser_auth import PgBrowserAuth
        # Refuse formal DSNs BEFORE even resolving the local browser session.
        dsn, checkpoint_dsn = _owned_pair(os.environ[args.dsn_env], os.environ[args.checkpoint_dsn_env])
        scope = PgBrowserAuth(dsn, 3600).resolve(os.environ[args.session_env])
        options = {"dsn": dsn, "checkpoint_dsn": checkpoint_dsn, "scope": scope,
            "project_id": args.project_id, "authorization": args.authorization,
            "authorization_sha256": args.authorization_sha256,
            "external": external, "external_settings": settings}
        if args.action == "submit":
            print(canonical_json({"run_id": submit_prepared(args.packet, **options)}))
        elif args.action == "tick":
            print(canonical_json({"claimed": worker_tick(args.packet, **options)}))
        elif args.action == "review":
            frozen = read_review(args.packet, **options)
            _record_once(folder / ("independent-review-request-" + frozen["review"]["stage"] + ".json"),
                review_request(packet, frozen))
            print(canonical_json({"stage": frozen["review"]["stage"], "result": "NOT RUN",
                "review_hash": frozen["review"]["digest"], "automatic_approval": False}))
        elif args.action == "decide":
            print(canonical_json({"run_id": decide_review(args.packet, stage=args.stage, evidence=args.evidence,
                evidence_sha256=args.evidence_sha256, **options)}))
        else:
            assembly = assemble_prepared(args.packet, action="review", **options)
            submission = _submission(assembly)
            run = assembly.service._runs.get_run(project_id=args.project_id, run_id=submission["run_id"])
            print(canonical_json(wire(asdict(run))))
    finally:
        if external is not None:
            external.close()


if __name__ == "__main__":
    main()
