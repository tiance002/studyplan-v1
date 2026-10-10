"""Local, owned-only SourceFacts freeze and future owned planning assembly.

Use an absolute snapshot path shared by submission and worker processes on this
machine. Its directory and reference receipt must be readable only by the owner
and the service account: hashes bind integrity, they do not encrypt or authenticate
an attacker-replaced receipt. No ACLs, formal runtime configuration, source bodies,
credentials or auth state are written here. Missing snapshots never reconstruct.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import asdict, dataclass, fields, is_dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from types import SimpleNamespace
from typing import get_args, get_origin, get_type_hints

from app.core.errors import ValidationAppError
from app.core.ids import canonical_json, content_hash
from app.domain.planning.content_coverage import ReviewedContentIndex
from app.domain.planning.curriculum import ProjectCase
from app.domain.planning.curriculum_compiler import CurriculumSourceFacts
from app.domain.planning.resource_research import ReviewedAccessProof
from app.domain.planning.v2_runtime import manifest_intact, wire
from app.domain.resources.curation import PublicResourceSource
from app.infrastructure.providers.runtime_factory import OwnedV2PlanningRuntimeFactory

SNAPSHOT_VERSION = "owned-source-facts-v1"
_PACK = "backend/app/infrastructure/content/agent-application-v8.json"
_HASH = re.compile(r"[0-9a-f]{64}\Z")


def _reject(field):
    raise ValidationAppError("Owned SourceFacts snapshot rejected", field=field)


def _keys(value, expected, field):
    if type(value) is not dict or set(value) != set(expected):
        _reject(field)


def _digest(value, field):
    if type(value) is not str or not _HASH.fullmatch(value):
        _reject(field)
    return value


def _absolute_path(value):
    path = Path(value)
    if not path.is_absolute() or path.is_symlink():
        _reject("snapshot_path")
    return path


def _strict_decode(kind, value, field):
    """Fixed schema only, with all defaulted fields required on the wire."""
    origin, args = get_origin(kind), get_args(kind)
    if origin is tuple:
        if type(value) is not list:
            _reject(field)
        if args and args[-1] is not Ellipsis:
            if len(value) != len(args):
                _reject(field)
            return tuple(_strict_decode(t, v, field) for t, v in zip(args, value, strict=True))
        if not args:
            _reject(field)
        return tuple(_strict_decode(args[0], v, field) for v in value)
    if origin is not None and type(None) in args:
        if value is None:
            return None
        choices = tuple(t for t in args if t is not type(None))
        if len(choices) != 1:
            _reject(field)
        return _strict_decode(choices[0], value, field)
    if kind is datetime:
        if type(value) is not str:
            _reject(field)
        result = datetime.fromisoformat(value)
        if result.tzinfo is None:
            _reject(field)
        return result
    if isinstance(kind, type) and issubclass(kind, Enum):
        if type(value) is not str:
            _reject(field)
        return kind(value)
    if is_dataclass(kind):
        _keys(value, (f.name for f in fields(kind)), field)
        hints = get_type_hints(kind)
        return kind(
            **{
                f.name: _strict_decode(hints[f.name], value[f.name], field + "." + f.name)
                for f in fields(kind)
            }
        )
    if kind in {str, int, bool, float} and type(value) is kind:
        return value
    _reject(field)


def _decode_facts(value):
    _keys(value, (f.name for f in fields(CurriculumSourceFacts)), "source_facts")
    for name in ("catalog_sources", "access_proofs", "project_cases"):
        if type(value[name]) is not list:
            _reject(name)
    facts = CurriculumSourceFacts(
        _strict_decode(ReviewedContentIndex, value["reviewed_index"], "reviewed_index"),
        tuple(_strict_decode(PublicResourceSource, v, "catalog_sources") for v in value["catalog_sources"]),
        tuple(_strict_decode(ReviewedAccessProof, v, "access_proofs") for v in value["access_proofs"]),
        tuple(_strict_decode(ProjectCase, v, "project_cases") for v in value["project_cases"]),
    )
    # Dataclass normalizers may reorder/deduplicate; never silently accept that.
    if wire(asdict(facts)) != value:
        _reject("source_facts_canonical_roundtrip")
    return facts


def _identity(facts):
    return {
        "reviewed_index": {"version": facts.reviewed_index.version, "hash": facts.reviewed_index.index_hash},
        "catalog_sources": [
            {"source_id": s.source_id, "source_version": s.source_version} for s in facts.catalog_sources
        ],
        "access_proofs": [
            {
                "source_id": p.source_id,
                "source_version": p.source_version,
                "content_hash": p.content_hash,
                "reference": p.reference,
            }
            for p in facts.access_proofs
        ],
        "project_cases": [
            {"case_id": c.case_id, "version": c.version, "repo_url": c.repo_url} for c in facts.project_cases
        ],
    }


@dataclass(frozen=True, slots=True)
class FrozenSourceFactsRef:
    """Keep this trusted receipt beside the frozen submission, outside the snapshot."""

    path: str
    sha256: str
    source_facts_hash: str

    def __post_init__(self):
        if type(self.path) is not str:
            _reject("snapshot_path")
        _absolute_path(self.path)
        _digest(self.sha256, "snapshot_sha256")
        _digest(self.source_facts_hash, "source_facts_hash")

    @classmethod
    def from_payload(cls, value):
        _keys(value, (f.name for f in fields(cls)), "snapshot_reference")
        return cls(**value)


def freeze_source_facts(path, facts):
    """Exclusive immutable write before build_submission; never overwrite a receipt."""
    path = _absolute_path(path)
    if type(facts) is not CurriculumSourceFacts:
        _reject("source_facts")
    value = wire(asdict(facts))
    restored = _decode_facts(value)
    envelope = {
        "snapshot_version": SNAPSHOT_VERSION,
        "source_facts": value,
        "source_facts_hash": content_hash(value),
        "source_identity": _identity(restored),
    }
    envelope["snapshot_hash"] = content_hash(envelope)
    raw = canonical_json(envelope).encode("utf-8")
    try:
        with path.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    except OSError:
        _reject("snapshot_exclusive_write")
    return FrozenSourceFactsRef(str(path), hashlib.sha256(raw).hexdigest(), content_hash(value))


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _reject("duplicate_json_key")
        result[key] = value
    return result


def read_source_facts(reference, *, manifest=None):
    """Strict restore using a trusted byte/hash reference and optional DB manifest."""
    if type(reference) is not FrozenSourceFactsRef:
        _reject("snapshot_reference")
    path = _absolute_path(reference.path)
    try:
        if not path.is_file():
            _reject("snapshot_missing")
        raw = path.read_bytes()
        if len(raw) > 4 * 1024 * 1024 or hashlib.sha256(raw).hexdigest() != reference.sha256:
            _reject("snapshot_sha256")
        envelope = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
        _keys(
            envelope,
            ("snapshot_version", "source_facts", "source_facts_hash", "source_identity", "snapshot_hash"),
            "snapshot_envelope",
        )
        if raw != canonical_json(envelope).encode("utf-8"):
            _reject("snapshot_canonical_json")
        if envelope["snapshot_version"] != SNAPSHOT_VERSION:
            _reject("snapshot_version")
        if _digest(envelope["snapshot_hash"], "snapshot_hash") != content_hash(
            {k: v for k, v in envelope.items() if k != "snapshot_hash"}
        ):
            _reject("snapshot_hash")
        facts = _decode_facts(envelope["source_facts"])
        digest = content_hash(wire(asdict(facts)))
        if (
            digest != _digest(envelope["source_facts_hash"], "source_facts_hash")
            or digest != reference.source_facts_hash
        ):
            _reject("source_facts_hash")
        # Python considers True == 1 and 1.0 == 1. Canonical JSON preserves the
        # number/boolean wire types used by this frozen identity contract.
        if canonical_json(envelope["source_identity"]) != canonical_json(_identity(facts)):
            _reject("source_identity")
        if manifest is not None and (
            not manifest_intact(manifest) or manifest["source_facts_hash"] != digest
        ):
            _reject("manifest_source_facts_hash")
        return facts
    except (OSError, ValueError, TypeError, KeyError, UnicodeError, OverflowError):
        _reject("snapshot_decode")


def freeze_reviewed_source_facts(path, *, root=None):
    """Future owned acceptance source construction, invoked only once before submit."""
    from app.infrastructure.reviewed_content_coverage import load_reviewed_content_index

    root = Path(root) if root is not None else Path(__file__).resolve().parents[1]
    index = load_reviewed_content_index(root=root)
    record = json.loads((root / _PACK).read_text(encoding="utf-8-sig"))["resources"][13]
    if record["content_access"] != "free_public":
        _reject("source_access")
    # Preserve the existing owned constructor's complete defaults, including its
    # once-created timestamp; do not claim extra catalog qualification.
    source = PublicResourceSource(
        record["source_id"],
        record["canonical_url"],
        record["title"],
        record["creator"],
        record["media_type"],
        record["language"],
        source_version=record["source_version"],
    )
    section = index.sections[0]
    if (source.source_id, source.source_version) != (section.source_id, section.source_version):
        _reject("catalog_source_identity")
    proof = ReviewedAccessProof(
        section.source_id,
        section.source_version,
        section.content_hash,
        "repo:" + _PACK + "@sha256:" + section.content_hash + "#/resources/13/content_access",
        "free_public",
    )
    return freeze_source_facts(path, CurriculumSourceFacts(index, (source,), (proof,)))


class FrozenOwnedV2PlanningRuntimeFactory(OwnedV2PlanningRuntimeFactory):
    """Tracked owned entry: submission and worker both restore the same snapshot."""

    def __init__(self, dsn, checkpoint_dsn, *, snapshot, **kwargs):
        if "source_facts" in kwargs:
            _reject("caller_source_facts")
        self.snapshot = snapshot
        super().__init__(dsn, checkpoint_dsn, source_facts=read_source_facts(snapshot), **kwargs)

    def build_submission(self, scope, project_id, goal_spec, expected_version):
        self.source_facts = read_source_facts(self.snapshot)
        manifest = super().build_submission(scope, project_id, goal_spec, expected_version)
        read_source_facts(self.snapshot, manifest=manifest)
        return manifest

    def __call__(self, scope, project_id, run_id, *, manifest, **kwargs):
        # This happens before provider_resolver, attempts, reserve or dispatch.
        self.source_facts = read_source_facts(self.snapshot, manifest=manifest)
        return super().__call__(scope, project_id, run_id, manifest=manifest, **kwargs)


def assemble_owned_planning(dsn, checkpoint_dsn, *, snapshot, actor_id, **factory_options):
    """Usable future owned harness assembly; credentials remain caller-local."""
    from app.application.plan_service import PlanService
    from app.infrastructure.db.job_repository import PgPlanningJobRepository
    from app.infrastructure.db.plan_repository import PgPlanRepository
    from app.infrastructure.db.public_resource_catalog import PgPublicResourceCatalog
    from app.infrastructure.db.run_repository import PgRunRepository
    from app.infrastructure.worker.planning_worker import PlanningWorker

    class ForbiddenLegacyPort:
        def __getattr__(self, name):
            raise AssertionError("Legacy planning port forbidden: " + name)

    factory = FrozenOwnedV2PlanningRuntimeFactory(dsn, checkpoint_dsn, snapshot=snapshot, **factory_options)
    jobs = PgPlanningJobRepository(dsn, actor_ids=(actor_id,), max_attempts=4)
    service = PlanService(
        repository=PgPlanRepository(dsn),
        runs=PgRunRepository(dsn),
        catalog=ForbiddenLegacyPort(),
        resources=PgPublicResourceCatalog(dsn),
        llm=ForbiddenLegacyPort(),
        graph_version="",
        planning_jobs=jobs,
        v2_runtime_factory=factory,
    )
    worker = PlanningWorker(jobs=jobs, execute=service.execute_generation, actor_ids=(actor_id,))
    return SimpleNamespace(factory=factory, jobs=jobs, service=service, worker=worker)
