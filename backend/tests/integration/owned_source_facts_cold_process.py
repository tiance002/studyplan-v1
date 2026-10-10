"""Independent A/B process probe; subprocess DSNs stay in environment only."""

from __future__ import annotations

import hashlib
import json
import os
import socket
import sys
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / "backend")]

import psycopg  # noqa: E402
from app.core.errors import ValidationAppError  # noqa: E402
from app.core.ids import canonical_json, content_hash  # noqa: E402
from app.domain.enums import ResourceSourceVisibility  # noqa: E402
from app.domain.planning.intent import GoalSpec  # noqa: E402
from app.domain.planning.resource_research import ResearchBudget  # noqa: E402
from app.domain.planning.v2_runtime import wire  # noqa: E402
from app.domain.workspace.models import AuthContext  # noqa: E402
from app.infrastructure.db.browser_auth import PgBrowserAuth  # noqa: E402

from backend.tests.integration.test_owned_v2_acceptance_gate_pg import Provider  # noqa: E402
from scripts.planning_v2_owned_source_facts import (  # noqa: E402
    FrozenOwnedV2PlanningRuntimeFactory,
    FrozenSourceFactsRef,
    assemble_owned_planning,
    freeze_reviewed_source_facts,
    read_source_facts,
)


class ForbiddenPort:
    def __init__(self):
        self.calls = []

    def find(self, *args, **kwargs):
        self.calls.append("search")
        raise AssertionError("Search invocation forbidden")

    def read(self, *args, **kwargs):
        self.calls.append("body")
        raise AssertionError("Body invocation forbidden")

    def __getattr__(self, name):
        if name == "_transport":
            # Native guarded_port checks this optional adapter capability via
            # hasattr; absence is ordinary introspection, not a dispatch.
            raise AttributeError(name)
        self.calls.append("unconfigured:" + name)
        raise AssertionError("Unconfigured external port forbidden: " + name)


def deny_external_network(dsn):
    port = urlsplit(dsn).port or 5432
    denied = []

    def audit(event, args):
        if event == "socket.connect":
            target = args[1]
            if not (
                type(target) is tuple and target[0] in {"127.0.0.1", "localhost", "::1"} and target[1] == port
            ):
                denied.append(event)
                raise PermissionError("Cold test denies external network")
        elif event == "socket.getaddrinfo":
            if args[0] not in {"127.0.0.1", "localhost", "::1"} or args[1] != port:
                denied.append(event)
                raise PermissionError("Cold test denies external DNS")

    sys.addaudithook(audit)
    with socket.socket() as probe:
        try:
            probe.connect(("203.0.113.10", 443))
        except PermissionError:
            pass
        else:
            raise AssertionError("External network was not denied")
    assert denied == ["socket.connect"]
    return denied


def options(provider, resolved, forbidden):
    def resolve(*args):
        resolved.append("mock-provider")
        return provider

    return dict(
        budget=ResearchBudget(
            max_searches=6,
            max_body_bytes=393216,
            max_reader_requests=6,
            max_output_tokens=18432,
            max_total_requests=27,
            max_cost_micros=186000,
        ),
        binding_resolver=lambda *args: SimpleNamespace(model_ref="test:frozen"),
        provider_resolver=resolve,
        github=forbidden,
        body_reader=forbidden,
        acceptance_gate="scenario-a-review-v1",
    )


def facts_summary(facts):
    raw = canonical_json(wire(asdict(facts))).encode("utf-8")
    source = facts.catalog_sources[0]
    assert type(source.created_at) is datetime and source.created_at.tzinfo is not None
    assert type(source.visibility) is ResourceSourceVisibility
    assert facts.reviewed_index.sections and facts.reviewed_index.mappings and facts.reviewed_index.evidence
    assert facts.access_proofs
    return {
        "source_facts_hash": content_hash(wire(asdict(facts))),
        "canonical_bytes": len(raw),
        "canonical_sha256": hashlib.sha256(raw).hexdigest(),
        "created_at": source.created_at.isoformat(),
        "created_at_type": type(source.created_at).__name__,
        "visibility_type": type(source.visibility).__name__,
        "source_id": source.source_id,
        "source_version": source.source_version,
        "reviewed_index_hash": facts.reviewed_index.index_hash,
        "reviewed_counts": {
            k: len(getattr(facts.reviewed_index, k)) for k in ("sections", "mappings", "evidence")
        },
        "access_proof_count": len(facts.access_proofs),
    }


def counts(migrator_dsn, run):
    with psycopg.connect(migrator_dsn) as conn:
        row = conn.execute(
            "SELECT status,next_action,error_class FROM ai_runs WHERE run_id=%s", (run,)
        ).fetchone()
        attempts = conn.execute(
            "SELECT count(*) FROM ai_provider_attempts WHERE run_id=%s", (run,)
        ).fetchone()[0]
        drafts = conn.execute("SELECT count(*) FROM plan_drafts WHERE run_id=%s", (run,)).fetchone()[0]
        job = conn.execute("SELECT status,attempts FROM ai_jobs WHERE run_id=%s", (run,)).fetchone()
    return {
        "status": row[0],
        "next_action": row[1],
        "error_class": row[2],
        "provider_attempts": attempts,
        "draft_count": drafts,
        "job_status": job[0],
        "job_claims": job[1],
    }


def negative_matrix(
    out, reference, manifest, scope, dsn, checkpoint, factory_options, provider, resolved, forbidden
):
    original = json.loads(Path(reference.path).read_bytes())
    rows = []
    for variant in (
        "missing",
        "bytes",
        "snapshot_version",
        "unknown_field",
        "facts_hash_corruption",
        "manifest_mismatch",
        "corehash_created_at",
        "corehash_source_version",
    ):
        path = out / ("negative-" + variant + ".json")
        payload = deepcopy(original)
        if variant == "snapshot_version":
            payload["snapshot_version"] = "unknown-v999"
        if variant == "unknown_field":
            payload["body"] = "forbidden"
        if variant == "manifest_mismatch":
            payload["source_facts"]["catalog_sources"][0]["title"] += " changed future snapshot"
        if variant == "corehash_created_at":
            payload["source_facts"]["catalog_sources"][0]["created_at"] = "2026-10-11T00:00:00+00:00"
        if variant == "corehash_source_version":
            payload["source_facts"]["catalog_sources"][0]["source_version"] = 99
            payload["source_identity"]["catalog_sources"][0]["source_version"] = 99
        payload["source_facts_hash"] = content_hash(payload["source_facts"])
        if variant == "facts_hash_corruption":
            payload["source_facts_hash"] = "a" * 64
        payload["snapshot_hash"] = content_hash({k: v for k, v in payload.items() if k != "snapshot_hash"})
        raw = canonical_json(payload).encode("utf-8")
        changed = FrozenSourceFactsRef(
            str(path), hashlib.sha256(raw).hexdigest(), payload["source_facts_hash"]
        )
        if variant != "missing":
            with path.open("xb") as stream:
                stream.write(raw + b" " if variant == "bytes" else raw)
        rejected = False
        try:
            factory = FrozenOwnedV2PlanningRuntimeFactory(
                dsn, checkpoint, snapshot=changed, **factory_options
            )
            # Use the real durable DB manifest read for this owned Run. The
            # factory must reject before it ever resolves a Provider/fence.
            factory(
                scope,
                scope.learning_project_scope[0],
                "unused-before-provider",
                manifest=manifest,
                write_fence=None,
                thread_id="unused",
                guard=lambda: None,
            )
        except ValidationAppError:
            rejected = True
        assert rejected, variant
        assert not resolved and not provider.calls and not forbidden.calls, variant
        rows.append(
            {
                "variant": variant,
                "result": "PASS",
                "provider_resolutions": len(resolved),
                "mock_calls": len(provider.calls),
                "forbidden_port_attempts": len(forbidden.calls),
                "external_invocations": len(forbidden.calls),
            }
        )
    return rows


def main():
    phase, folder = sys.argv[1:]
    out = Path(folder)
    assert out.is_absolute()
    dsn, checkpoint, migrator = (
        os.environ[k] for k in ("COLD_TEST_APP_DSN", "COLD_TEST_CHECKPOINT_DSN", "COLD_TEST_MIGRATOR_DSN")
    )
    for value in (dsn, checkpoint, migrator):
        parsed = urlsplit(value)
        assert parsed.hostname in {"localhost", "127.0.0.1", "::1"}
        assert parsed.path.removeprefix("/").startswith("studyplan_test_")
    denied = deny_external_network(dsn)
    provider, forbidden, resolved = Provider(), ForbiddenPort(), []
    factory_options = options(provider, resolved, forbidden)
    if phase == "A":
        reference = freeze_reviewed_source_facts(out / "source-facts.json")
        facts = read_source_facts(reference)
        (out / "source-facts-canonical.json").write_bytes(canonical_json(wire(asdict(facts))).encode("utf-8"))
        auth = PgBrowserAuth(dsn, 3600)
        scope = auth.resolve(auth.register("cold_" + uuid4().hex[:12], "pytest42", "owned-cold-test"))
        env = assemble_owned_planning(
            dsn, checkpoint, snapshot=reference, actor_id=scope.actor_id, **factory_options
        )
        project = scope.learning_project_scope[0]
        run = env.service.submit_owned_v2(scope=scope, project_id=project, goal_spec=GoalSpec("学习MCP"))
        manifest = env.jobs.read_submission(project, run)["manifest"]
        assert manifest["source_facts_hash"] == reference.source_facts_hash
        assert counts(migrator, run)["provider_attempts"] == 0
        assert not provider.calls and not resolved and not forbidden.calls
        receipt = {
            "phase": "A",
            "pid": os.getpid(),
            "cwd": str(Path.cwd()),
            "snapshot": asdict(reference),
            "run_id": run,
            "actor_id": scope.actor_id,
            "project_id": project,
            "facts": facts_summary(facts),
            "state": counts(migrator, run),
            "mock_calls": 0,
            "external_invocations": 0,
            "network_denied_probe_count": len(denied),
        }
    else:
        assert phase == "B"
        first = json.loads((out / "phase-a.json").read_bytes())
        reference = FrozenSourceFactsRef.from_payload(first["snapshot"])
        env = assemble_owned_planning(
            dsn, checkpoint, snapshot=reference, actor_id=first["actor_id"], **factory_options
        )
        manifest = env.jobs.read_submission(first["project_id"], first["run_id"])["manifest"]
        facts = read_source_facts(reference, manifest=manifest)
        assert (
            canonical_json(wire(asdict(facts))).encode("utf-8")
            == (out / "source-facts-canonical.json").read_bytes()
        )
        assert facts_summary(facts) == first["facts"]
        scope = AuthContext(
            first["actor_id"], "trusted-cold-test", datetime.now(timezone.utc), (first["project_id"],)
        )
        negatives = negative_matrix(
            out, reference, manifest, scope, dsn, checkpoint, factory_options, provider, resolved, forbidden
        )
        assert not resolved and not provider.calls and not forbidden.calls
        assert counts(migrator, first["run_id"])["provider_attempts"] == 0
        assert env.worker.tick()
        review = env.factory.reviews().read(
            scope=scope, project_id=first["project_id"], run_id=first["run_id"]
        )
        assert review["review"]["stage"] == "goal_analysis"
        assert review["manifest"] == manifest
        state = counts(migrator, first["run_id"])
        assert state == {
            "status": "waiting_user",
            "next_action": "review_draft",
            "error_class": "owned_acceptance_review",
            "provider_attempts": 1,
            "draft_count": 0,
            "job_status": "completed",
            "job_claims": 1,
        }
        assert len(provider.calls) == len(resolved) == 1
        assert provider.calls[0]["purpose"] == "planning.goal_requirement_analysis"
        assert not forbidden.calls and denied == ["socket.connect"]
        receipt = {
            "phase": "B",
            "pid": os.getpid(),
            "cwd": str(Path.cwd()),
            "snapshot": asdict(reference),
            "run_id": first["run_id"],
            "facts": facts_summary(facts),
            "state": state,
            "review_stage": review["review"]["stage"],
            "mock_calls": len(provider.calls),
            "external_invocations": len(forbidden.calls),
            "search_body_calls": len(forbidden.calls),
            "reader_calls": sum(call["purpose"] == "planning.research_reader" for call in provider.calls),
            "metadata_transport_configured": False,
            "unconfigured_external_ports": ["web", "project_index", "domain_sources", "metadata"],
            "negative_matrix": negatives,
            "network_denied_probe_count": len(denied),
            "durable_manifest_hash": manifest["manifest_hash"],
        }
    with (out / ("phase-" + phase.lower() + ".json")).open("x", encoding="utf-8") as stream:
        stream.write(canonical_json(receipt))
    print(
        canonical_json(
            {
                "phase": phase,
                "result": "PASS",
                "pid": os.getpid(),
                "source_facts_hash": receipt["facts"]["source_facts_hash"],
            }
        )
    )


if __name__ == "__main__":
    main()
