"""Exact SourceFacts roundtrip and a complete owned freeze rejection matrix."""

import hashlib
import json
import os
import subprocess
import sys
from dataclasses import asdict, fields, replace
from datetime import datetime
from pathlib import Path

import pytest
from app.core.errors import ValidationAppError
from app.core.ids import canonical_json, content_hash
from app.domain.enums import ResourceSourceVisibility
from app.domain.planning.curriculum import ProjectCase
from app.domain.planning.v2_runtime import wire
from app.domain.resources.curation import PublicResourceSource

from scripts.planning_v2_owned_source_facts import (
    FrozenOwnedV2PlanningRuntimeFactory,
    FrozenSourceFactsRef,
    freeze_reviewed_source_facts,
    freeze_source_facts,
    read_source_facts,
)

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def frozen(tmp_path):
    first = freeze_reviewed_source_facts(tmp_path / "reviewed.json")
    facts = read_source_facts(first)
    case = ProjectCase(
        "synthetic_case",
        "https://github.com/example/synthetic",
        "pinned-test-v1",
        "slices",
        ("mcp.roles",),
        (("fixture:metadata-only", "a" * 64),),
        "bounded_reviewed",
        ("Synthetic metadata only; no repository execution.",),
    )
    facts = replace(facts, project_cases=(case,))
    reference = freeze_source_facts(tmp_path / "full.json", facts)
    return reference, facts


def rewritten(reference, mutate, *, facts_hash=True):
    payload = json.loads(Path(reference.path).read_bytes())
    mutate(payload)
    if facts_hash:
        payload["source_facts_hash"] = content_hash(payload["source_facts"])
    payload["snapshot_hash"] = content_hash({k: v for k, v in payload.items() if k != "snapshot_hash"})
    raw = canonical_json(payload).encode("utf-8")
    Path(reference.path).write_bytes(raw)
    return FrozenSourceFactsRef(reference.path, hashlib.sha256(raw).hexdigest(), payload["source_facts_hash"])


def manifest_for(reference):
    from app.domain.planning.intent import GoalSpec
    from app.domain.planning.resource_research import ResearchBudget
    from app.domain.planning.v2_runtime import build_v2_manifest

    return build_v2_manifest(
        GoalSpec("学习MCP"),
        model_ref="test:frozen",
        source_facts=read_source_facts(reference),
        budget=ResearchBudget(),
        checked_at="2026-10-10T00:00:00+00:00",
        expected_version=0,
    )


def test_full_real_reviewed_catalog_access_and_synthetic_case_roundtrip(frozen):
    reference, original = frozen
    restored = read_source_facts(reference, manifest=manifest_for(reference))
    assert restored == original
    assert canonical_json(wire(asdict(restored))).encode() == canonical_json(wire(asdict(original))).encode()
    assert reference.source_facts_hash == content_hash(wire(asdict(original)))
    source = restored.catalog_sources[0]
    assert type(source.created_at) is datetime and source.created_at.tzinfo is not None
    assert type(source.visibility) is ResourceSourceVisibility
    assert (
        restored.reviewed_index.sections
        and restored.reviewed_index.mappings
        and restored.reviewed_index.evidence
    )
    assert restored.access_proofs[0].reference == original.access_proofs[0].reference
    assert type(restored.project_cases[0].evidence_refs[0]) is tuple
    assert asdict(restored.project_cases[0]) == asdict(original.project_cases[0])


def test_cold_process_restores_same_canonical_facts_from_different_cwd(frozen, tmp_path):
    reference, facts = frozen
    code = """
import json, sys
from dataclasses import asdict
from app.core.ids import canonical_json, content_hash
from app.domain.planning.v2_runtime import wire
from scripts.planning_v2_owned_source_facts import FrozenSourceFactsRef, read_source_facts
r = FrozenSourceFactsRef.from_payload(json.loads(sys.argv[1]))
f = read_source_facts(r)
print(json.dumps({'hash': content_hash(wire(asdict(f))), 'canonical': canonical_json(wire(asdict(f)))}))
"""
    env = dict(
        os.environ, PYTHONPATH=os.pathsep.join((str(ROOT), str(ROOT / "backend"))), PYTHONIOENCODING="utf-8"
    )
    for cwd in (ROOT, tmp_path):
        value = json.loads(
            subprocess.check_output(
                [sys.executable, "-c", code, json.dumps(asdict(reference))], cwd=cwd, env=env, text=True
            )
        )
        assert value == {
            "hash": reference.source_facts_hash,
            "canonical": canonical_json(wire(asdict(facts))),
        }


@pytest.mark.parametrize("field", [f.name for f in fields(PublicResourceSource)])
def test_all_catalog_fields_required_even_defaults(frozen, field):
    reference, _ = frozen
    changed = rewritten(reference, lambda p: p["source_facts"]["catalog_sources"][0].pop(field))
    with pytest.raises(ValidationAppError):
        read_source_facts(changed)


@pytest.mark.parametrize(
    "path",
    [
        ("source_facts", "catalog_sources"),
        ("source_facts", "access_proofs"),
        ("source_facts", "project_cases"),
        ("source_facts", "reviewed_index", "policy_version"),
        ("source_facts", "reviewed_index", "sections", 0, "review_refs"),
        ("source_facts", "reviewed_index", "mappings", 0, "source_version"),
        ("source_facts", "reviewed_index", "evidence", 0, "limitations"),
        ("source_facts", "access_proofs", 0, "reference"),
        ("source_facts", "project_cases", 0, "evidence_refs"),
        ("source_facts", "project_cases", 0, "qualification"),
        ("source_facts", "project_cases", 0, "limitations"),
    ],
)
def test_missing_nested_and_default_fields_fail_closed(frozen, path):
    reference, _ = frozen

    def remove(payload):
        current = payload
        for part in path[:-1]:
            current = current[part]
        current.pop(path[-1])

    with pytest.raises(ValidationAppError):
        read_source_facts(rewritten(reference, remove))


@pytest.mark.parametrize(
    "invalid",
    [
        "missing",
        "bytes",
        "version",
        "unknown",
        "bad_enum",
        "naive_datetime",
        "null_datetime",
        "bool_version",
        "wrong_tuple",
        "unknown_catalog",
        "identity",
        "facts_hash",
        "invalid_json",
        "noncanonical",
        "duplicate_key",
    ],
)
def test_snapshot_errors_fail_closed(frozen, invalid):
    reference, _ = frozen
    path = Path(reference.path)
    if invalid == "missing":
        path.unlink()
    elif invalid == "bytes":
        path.write_bytes(path.read_bytes() + b" ")
    elif invalid in {"invalid_json", "noncanonical", "duplicate_key"}:
        raw = (
            b"{"
            if invalid == "invalid_json"
            else path.read_bytes() + b" "
            if invalid == "noncanonical"
            else b'{"x":1,"x":2}'
        )
        path.write_bytes(raw)
        reference = replace(reference, sha256=hashlib.sha256(raw).hexdigest())
    else:

        def alter(p):
            source = p["source_facts"]["catalog_sources"][0]
            if invalid == "version":
                p["snapshot_version"] = "unknown-v99"
            elif invalid == "unknown":
                p["credentials"] = "forbidden"
            elif invalid == "bad_enum":
                source["visibility"] = "unknown"
            elif invalid == "naive_datetime":
                source["created_at"] = "2026-10-10T12:00:00"
            elif invalid == "null_datetime":
                source["created_at"] = None
            elif invalid == "bool_version":
                source["source_version"] = True
            elif invalid == "wrong_tuple":
                p["source_facts"]["catalog_sources"] = {}
            elif invalid == "unknown_catalog":
                source["body"] = "forbidden"
            elif invalid == "identity":
                p["source_identity"]["catalog_sources"][0]["source_id"] = "changed"
            elif invalid == "facts_hash":
                p["source_facts_hash"] = "a" * 64

        reference = rewritten(reference, alter, facts_hash=invalid != "facts_hash")
    with pytest.raises(ValidationAppError):
        read_source_facts(reference)


@pytest.mark.parametrize("field,value", [("created_at", "2026-10-11T00:00:00+00:00"), ("source_version", 99)])
def test_corehashed_tamper_cannot_change_trusted_manifest_or_reference(frozen, field, value):
    reference, _ = frozen
    manifest = manifest_for(reference)

    def alter(p):
        p["source_facts"]["catalog_sources"][0][field] = value
        if field == "source_version":
            p["source_identity"]["catalog_sources"][0][field] = value

    changed = rewritten(reference, alter)
    with pytest.raises(ValidationAppError):
        read_source_facts(reference)
    assert read_source_facts(changed).catalog_sources[0] != frozen[1].catalog_sources[0]
    with pytest.raises(ValidationAppError):
        read_source_facts(changed, manifest=manifest)


def test_freeze_is_exclusive_and_requires_absolute_path(frozen):
    reference, facts = frozen
    with pytest.raises(ValidationAppError):
        freeze_source_facts(reference.path, facts)
    with pytest.raises(ValidationAppError):
        freeze_source_facts("relative.json", facts)


@pytest.mark.parametrize("number", [True, 1.0])
def test_source_identity_rejects_equal_but_different_number_types(frozen, number):
    reference, facts = frozen
    facts = replace(facts, catalog_sources=(replace(facts.catalog_sources[0], source_version=1),))
    reference = freeze_source_facts(Path(reference.path).with_name("identity-test.json"), facts)

    def alter(p):
        p["source_identity"]["catalog_sources"][0]["source_version"] = number

    changed = rewritten(reference, alter)
    with pytest.raises(ValidationAppError):
        read_source_facts(changed)


def test_forbidden_external_ports_record_attempt_before_rejection():
    from backend.tests.integration.owned_source_facts_cold_process import ForbiddenPort

    port = ForbiddenPort()
    assert not hasattr(port, "_transport") and not port.calls
    for method in ("find", "read", "metadata"):
        with pytest.raises(AssertionError):
            getattr(port, method)()
    assert port.calls == ["search", "body", "unconfigured:metadata"]


def test_factory_rechecks_before_binding_or_provider_resolution(frozen):
    from types import SimpleNamespace

    from app.domain.planning.intent import GoalSpec
    from app.domain.planning.resource_research import ResearchBudget

    reference, _ = frozen
    invocations = []
    factory = FrozenOwnedV2PlanningRuntimeFactory(
        "postgresql://user@127.0.0.1/studyplan_test_local",
        "postgresql://user@127.0.0.1/studyplan_test_checkpoint",
        snapshot=reference,
        budget=ResearchBudget(),
        binding_resolver=lambda *a: invocations.append("binding"),
        provider_resolver=lambda *a: invocations.append("provider"),
    )
    Path(reference.path).unlink()
    with pytest.raises(ValidationAppError):
        factory.build_submission(SimpleNamespace(), "project", GoalSpec("MCP"), 0)
    with pytest.raises(ValidationAppError):
        factory(SimpleNamespace(), "project", "run", manifest={})
    assert invocations == []
