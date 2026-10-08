"""V2 compiler -> catalog entities + exact bindings + Draft in one transaction.

Research metadata stays project scoped; it never writes the reviewed public
catalog. Catalog-backed assignments retain normalized FK references. Other V2
materials have an explicit private resource identity and versioned source data
in the typed execution snapshot, consumed by the V2 resource projection.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import psycopg
from app.core.errors import ConflictError, ForbiddenError, IdempotencyConflictError, ValidationAppError
from app.core.ids import content_hash, new_id
from app.domain.enums import OutlineSectionKind, StageResourceRole
from app.domain.planning.curriculum_compiler import compile_curriculum, knowledge_definition_hash
from app.domain.planning.models import PlanDraft, PlanStage, PlanTaskKnowledgeLink, PlanTaskLink, PlanUnitLink
from app.domain.planning.v2_execution import V2ExecutionSnapshot, compiler_packet, validate_v2_structure
from app.domain.resources.curation import StageResourceAssignment
from app.infrastructure.db.learning_exposures import _json
from app.infrastructure.db.plan_repository import PgPlanRepository, to_psycopg_dsn
from app.infrastructure.db.planning_catalog import PgPlanningCatalog
from app.infrastructure.db.planning_fence import lock_plan_version, lock_planning_write
from app.infrastructure.db.resource_changes import capture_resource_snapshots
from psycopg.rows import dict_row


def _public_catalog(conn, material):
    source = conn.execute(
        "SELECT * FROM public_resource_sources WHERE source_id=%s", (material["source_id"],)
    ).fetchone()
    if source is None or material["source_version"] != "source:" + str(source["source_version"]):
        raise ValidationAppError("V2 public material catalog identity/version mismatch")
    conn.execute("SELECT public.lock_reviewed_resource_index(%s)", (source["source_id"],))
    source = conn.execute(
        "SELECT * FROM public_resource_sources WHERE source_id=%s", (source["source_id"],)
    ).fetchone()
    if material["source_version"] != "source:" + str(source["source_version"]):
        raise ValidationAppError("V2 public material catalog changed while locking")
    sections = conn.execute(
        "SELECT * FROM public_resource_sections WHERE source_id=%s ORDER BY order_index,section_id",
        (source["source_id"],),
    ).fetchall()
    selected = [s for s in sections if s["section_id"] in material["section_refs"]]
    if (
        source["verification_status"] != "reviewed"
        or not source["checked_at"]
        or [s["section_id"] for s in selected] != material["section_refs"]
        or any(s["verification_status"] != "reviewed" or not s["checked_at"] for s in selected)
    ):
        raise ValidationAppError("V2 public material has no current reviewed catalog binding")
    # The material's pinned review-record references provide independent frozen
    # source/section metadata. A new digest of today's catalog cannot legitimize
    # a same-ID/same-version source substitution at the first binding.
    expected_source, expected_sections = _frozen_review_catalog(material)
    for field in (
        "source_id",
        "canonical_url",
        "title",
        "creator",
        "media_type",
        "language",
        "source_version",
        "documentation_version",
        "verification_status",
    ):
        if source[field] != expected_source.get(field, "" if field == "documentation_version" else None):
            raise ValidationAppError("V2 public source differs from frozen review record", field=field)
    if material["url"] != expected_source["canonical_url"] or material["title"] != expected_source["title"]:
        raise ValidationAppError("V2 frozen material metadata mismatch")
    for section in selected:
        expected = expected_sections[section["section_id"]]
        for field in (
            "section_id",
            "order_index",
            "title",
            "url",
            "anchor",
            "verification_status",
            "review_note",
        ):
            if section[field] != expected.get(field, ""):
                raise ValidationAppError("V2 public section differs from frozen review record", field=field)
        if section["checked_at"] != datetime.fromisoformat(expected["checked_at"]):
            raise ValidationAppError("V2 public section review timestamp mismatch")
    if source["checked_at"] != datetime.fromisoformat(expected_source["checked_at"]):
        raise ValidationAppError("V2 public source review timestamp mismatch")
    return source, content_hash(_json({"source": source, "sections": sections}))


def _frozen_review_catalog(material):
    root = Path(__file__).resolve().parents[4]
    source_record = None
    sections = {}
    for evidence in material["evidence_refs"]:
        match = re.fullmatch(
            r"repo:(backend/app/infrastructure/content/[A-Za-z0-9_-]+\.json)#/resources/(\d+)/sections/(\d+)",
            evidence["reference"],
        )
        if not match or evidence["hash_scope"] != "review_record":
            continue
        path, source_index, section_index = match.groups()
        blob = (root / path).read_bytes()
        if hashlib.sha256(blob).hexdigest() != material["content_hash"]:
            raise ValidationAppError("V2 pinned public source bytes changed")
        record = json.loads(blob.decode("utf-8-sig"))["resources"][int(source_index)]
        section = record["sections"][int(section_index)]
        if (
            record["source_id"] != material["source_id"]
            or "source:" + str(record["source_version"]) != material["source_version"]
            or content_hash(section) != evidence["sha256"]
            or section["section_id"] != evidence["location"]
        ):
            raise ValidationAppError("V2 pinned public section evidence mismatch")
        if source_record is not None and record != source_record:
            raise ValidationAppError("V2 frozen public source conflict")
        source_record = record
        sections[section["section_id"]] = section
    if source_record is None or set(sections) != set(material["section_refs"]):
        raise ValidationAppError("V2 public source requires exact frozen section metadata")
    return source_record, sections


def _register_materials(conn, project_id, compiled):
    result = {}
    for assignment in compiled["resource_assignments"]:
        material = assignment["source_snapshot"]
        key = material["material_id"]
        if key in result:
            continue
        row = conn.execute(
            "SELECT resource_id,url,verification_status FROM resource_records WHERE project_id=%s AND url=%s FOR SHARE",
            (project_id, material["url"]),
        ).fetchone()
        if row is None:
            row = conn.execute(
                "INSERT INTO resource_records(resource_id,project_id,url,title,verification_status,provenance) "
                "VALUES(%s,%s,%s,%s,%s,%s) RETURNING resource_id,url,verification_status",
                (
                    new_id("res"),
                    project_id,
                    material["url"],
                    material["title"],
                    "v2_source_metadata",
                    "planning_v2",
                ),
            ).fetchone()
        binding = {
            "resource_id": row["resource_id"],
            "resource_url": row["url"],
            "material_digest": content_hash(material),
            "public_source_ref": None,
            "public_source_version": None,
            "catalog_digest": None,
        }
        if material["qualification"] == "public_reviewed":
            source, digest = _public_catalog(conn, material)
            binding.update(
                public_source_ref=source["source_id"],
                public_source_version=source["source_version"],
                catalog_digest=digest,
            )
        result[key] = binding
    return result


def validate_database_bindings(conn, owner):
    """Read the exact DB identities/versions and entity/link definitions, never titles as identities."""
    validate_v2_structure(owner)
    if owner.stage_resources:
        from app.infrastructure.db.resource_changes import require_snapshot_bindings

        require_snapshot_bindings(owner.stage_resources, owner.resource_snapshots)
    raw = owner.v2_execution.to_payload()
    c, b, project = raw["compiled"], raw["bindings"], owner.project_id
    for node in c["nodes"]:
        row = conn.execute(
            "SELECT stable_key,title,objectives,content_version FROM knowledge_nodes WHERE project_id=%s AND node_id=%s FOR SHARE",
            (project, b["nodes"][node["stable_key"]]),
        ).fetchone()
        version = node.get("public_binding", {}).get("public_version", "1")
        if (
            row is None
            or row["stable_key"] != node["stable_key"]
            or str(row["content_version"]) != version
            or row["title"] != node["title"]
            or row["objectives"] != node["objectives"]
        ):
            raise ConflictError("V2 knowledge identity/version/definition mismatch")
    for unit in c["units"]:
        row = conn.execute(
            "SELECT stable_key,title,objectives,rubric,rubric_version FROM learning_units WHERE project_id=%s AND unit_id=%s FOR SHARE",
            (project, b["units"][unit["stable_key"]]),
        ).fetchone()
        if (
            row is None
            or row["stable_key"] != unit["stable_key"]
            or row["title"] != unit["title"]
            or row["objectives"] != unit["objectives"]
            or row["rubric"] != unit["rubric"]
            or row["rubric_version"] != 1
        ):
            raise ConflictError("V2 learning unit definition mismatch")
        rows = conn.execute(
            "SELECT node_id,order_index,role FROM unit_node_links WHERE project_id=%s AND unit_id=%s ORDER BY order_index",
            (project, b["units"][unit["stable_key"]]),
        ).fetchall()
        if [(r["node_id"], r["order_index"], r["role"]) for r in rows] != [
            (b["nodes"][key], i, "core") for i, key in enumerate(unit["knowledge_refs"])
        ]:
            raise ConflictError("V2 unit knowledge binding mismatch")
    for task in c["practice"]["tasks"]:
        row = conn.execute(
            "SELECT * FROM practice_tasks WHERE project_id=%s AND task_id=%s FOR SHARE",
            (project, b["tasks"][task["stable_key"]]),
        ).fetchone()
        expected = (
            task["stable_key"],
            task["title"],
            task["goal"],
            task["in_scope"],
            task["out_scope"],
            [a["text"] for a in task["acceptance"]],
            b["practice_project_id"],
        )
        if (
            row is None
            or tuple(
                row[k]
                for k in (
                    "stable_key",
                    "title",
                    "goal",
                    "in_scope",
                    "out_scope",
                    "acceptance",
                    "practice_project_id",
                )
            )
            != expected
        ):
            raise ConflictError("V2 practice task definition mismatch")
        links = conn.execute(
            "SELECT node_id,role FROM task_knowledge_links WHERE project_id=%s AND task_id=%s ORDER BY node_id",
            (project, b["tasks"][task["stable_key"]]),
        ).fetchall()
        if [(r["node_id"], r["role"]) for r in links] != sorted(
            (b["nodes"][key], "core") for key in task["knowledge_refs"]
        ):
            raise ConflictError("V2 task knowledge binding mismatch")
    row = conn.execute(
        "SELECT title,idea FROM practice_projects WHERE project_id=%s AND practice_project_id=%s FOR SHARE",
        (project, b["practice_project_id"]),
    ).fetchone()
    if row is None or row["idea"] != c["practice"]["carrier"]["description"]:
        raise ConflictError("V2 practice carrier binding mismatch")
    # Exact stage prerequisites stay typed; no guessed Cartesian knowledge
    # edges are materialized. They are independently validated by the Compiler.
    materials = {a["material_id"]: a["source_snapshot"] for a in c["resource_assignments"]}
    for key, fact in b["materials"].items():
        row = conn.execute(
            "SELECT url FROM resource_records WHERE project_id=%s AND resource_id=%s FOR SHARE",
            (project, fact["resource_id"]),
        ).fetchone()
        if row is None or row["url"] != fact["resource_url"] or row["url"] != materials[key]["url"]:
            raise ConflictError("V2 private material binding mismatch")
        if isinstance(owner, PlanDraft) and fact["public_source_ref"]:
            _, digest = _public_catalog(conn, materials[key])
            if digest != fact["catalog_digest"]:
                raise ConflictError("V2 reviewed material catalog changed")


def _previous_node_definition(conn, project_id, node_id, stable_key, definition):
    rows = conn.execute(
        "SELECT payload->'v2_execution' AS snapshot FROM plan_drafts WHERE project_id=%s "
        "AND payload->'v2_execution'->'bindings'->'nodes'->>%s=%s UNION ALL "
        "SELECT structure->'v2_execution' AS snapshot FROM plan_revisions WHERE project_id=%s "
        "AND structure->'v2_execution'->'bindings'->'nodes'->>%s=%s",
        (project_id, stable_key, node_id, project_id, stable_key, node_id),
    ).fetchall()
    for prior in rows:
        snapshot = V2ExecutionSnapshot.from_payload(prior["snapshot"])
        if snapshot is not None and any(
            n["stable_key"] == stable_key and knowledge_definition_hash(n) == definition
            for n in snapshot.to_payload()["compiled"]["nodes"]
        ):
            return True
    return False


class PgV2PlanningPersistence:
    def __init__(self, dsn, *, domain_approvals=(), allow_unbound_preview=False):
        self.dsn = to_psycopg_dsn(dsn)
        self.domain_approvals = domain_approvals
        self.allow_unbound_preview = allow_unbound_preview

    def persist(
        self,
        *,
        scope,
        project_id,
        run_id,
        expected_version,
        curriculum,
        context,
        profile,
        capability_plan,
        source_facts,
        public_knowledge_bindings=(),
        write_fence=None,
    ):
        scope.require_project(project_id)
        if run_id:
            if (
                write_fence is None
                or write_fence.actor_id != scope.actor_id
                or write_fence.run_id != run_id
                or write_fence.project_id != project_id
            ):
                raise ConflictError("V2 Run persistence requires its current owner fence")
        elif write_fence is not None or not self.allow_unbound_preview:
            raise ConflictError("Unbound V2 persistence requires an explicit server preview dependency")
        result = compile_curriculum(
            curriculum,
            context=context,
            profile=profile,
            capability_plan=capability_plan,
            source_facts=source_facts,
            public_knowledge_bindings=public_knowledge_bindings,
        )
        c = result.to_payload()
        draft_id = "drf_" + uuid5(NAMESPACE_URL, f"studyplan:v2draft:{project_id}:{run_id}").hex
        with psycopg.connect(self.dsn, row_factory=dict_row) as conn:
            conn.execute(
                "SELECT set_config('app.project_id',%s,true),set_config('app.actor_id',%s,true)",
                (project_id, scope.actor_id),
            )
            lock_plan_version(conn, project_id, expected_version)
            owner = conn.execute(
                "SELECT project_id FROM learning_projects WHERE project_id=%s AND owner_actor_id=%s AND archived_at IS NULL FOR UPDATE",
                (project_id, scope.actor_id),
            ).fetchone()
            if owner is None:
                raise ForbiddenError()
            if write_fence:
                lock_planning_write(conn, project_id=project_id, run_id=run_id, fence=write_fence)
            repo = PgPlanRepository(self.dsn, connection=conn)
            existing = repo.get_draft(project_id=project_id, draft_id=draft_id)
            if existing:
                if (
                    existing.run_id != run_id
                    or not existing.v2_execution
                    or existing.v2_execution.to_payload()["manifest"] != result.manifest.to_payload()
                ):
                    raise IdempotencyConflictError("V2 draft identity already has different content")
                if write_fence:
                    lock_planning_write(conn, project_id=project_id, run_id=run_id, fence=write_fence)
                return existing
            reuse = {}
            for node in c["nodes"]:
                if node["identity_kind"] == "public_knowledge":
                    binding = node["public_binding"]
                    row = conn.execute(
                        "SELECT node_id,stable_key,content_version,title,objectives,source_status FROM knowledge_nodes WHERE project_id=%s AND node_id=%s FOR SHARE",
                        (project_id, binding["public_identity"]),
                    ).fetchone()
                    if (
                        row is None
                        or row["stable_key"] != node["stable_key"]
                        or str(row["content_version"]) != binding["public_version"]
                        or row["title"] != node["title"]
                        or row["objectives"] != node["objectives"]
                        or not _previous_node_definition(
                            conn, project_id, row["node_id"], node["stable_key"], binding["definition_hash"]
                        )
                    ):
                        raise ValidationAppError(
                            "Public Knowledge exact database identity/version/definition required"
                        )
                    reuse[node["stable_key"]] = {
                        "node_id": row["node_id"],
                        "content_version": row["content_version"],
                    }
            nodes = [n | {"node_type": "concept"} for n in c["nodes"]]
            units = [u | {"node_keys": u["knowledge_refs"]} for u in c["units"]]
            carrier = c["practice"]["carrier"]
            practice = {
                "stable_key": "v2.carrier",
                "title": profile.target_summary,
                "idea": carrier["description"],
                "tasks": [
                    t
                    | {
                        "acceptance": [a["text"] for a in t["acceptance"]],
                        "knowledge_links": [
                            {"node_stable_key": key, "role": "core"} for key in t["knowledge_refs"]
                        ],
                    }
                    for t in c["practice"]["tasks"]
                ],
            }
            ids = PgPlanningCatalog(self.dsn, connection=conn).materialize(
                project_id=project_id,
                nodes=nodes,
                units=units,
                relations=[],
                practice=practice,
                existing_node_ids=reuse,
            )
            stages = tuple(
                PlanStage.create(
                    stable_key=s["stable_key"],
                    title=s["title"],
                    section_kind=OutlineSectionKind.V2_CURRICULUM,
                    order_index=s["order_index"],
                    objective=s["what_to_learn"],
                )
                for s in c["stages"]
            )
            stage_ids = {s["stage_id"]: stage.stage_id for s, stage in zip(c["stages"], stages, strict=True)}
            materials = _register_materials(conn, project_id, c)
            bindings = {
                "project_id": project_id,
                "run_id": run_id,
                "stages": stage_ids,
                "nodes": ids.node_ids,
                "units": ids.unit_ids,
                "tasks": ids.task_ids,
                "practice_project_id": ids.practice_project_id,
                "materials": materials,
            }
            assignments = []
            for a in c["resource_assignments"]:
                fact = materials[a["material_id"]]
                if fact["public_source_ref"]:
                    knowledge = tuple(
                        ids.node_ids[n["stable_key"]]
                        for n in c["nodes"]
                        if n["stage_ref"] == a["stage_ref"] and a["material_id"] in n["material_refs"]
                    )
                    assignments.append(
                        StageResourceAssignment.create(
                            project_id=project_id,
                            stage_id=stage_ids[a["stage_ref"]],
                            role=StageResourceRole(a["role"]),
                            source_ref=fact["public_source_ref"],
                            source_version=fact["public_source_version"],
                            section_refs=tuple(a["source_snapshot"]["section_refs"]),
                            order_index=a["order_index"],
                            node_ids=knowledge,
                        )
                    )
            draft = PlanDraft(
                draft_id=draft_id,
                project_id=project_id,
                run_id=run_id,
                goal_snapshot=profile.target_summary,
                revision_candidate=expected_version + 1,
                stages=stages,
                unit_refs=tuple(ids.unit_ids),
                task_refs=tuple(ids.task_ids),
                node_stable_keys=tuple(ids.node_ids),
                unit_links=tuple(
                    PlanUnitLink(stage_ids[s["stage_id"]], ids.unit_ids[key], i)
                    for s in c["stages"]
                    for i, key in enumerate(s["unit_refs"])
                ),
                task_links=tuple(
                    PlanTaskLink(stage_ids[s["stage_id"]], ids.task_ids[key], i)
                    for s in c["stages"]
                    for i, key in enumerate(s["task_refs"])
                ),
                task_knowledge_links=tuple(
                    PlanTaskKnowledgeLink(ids.task_ids[t["stable_key"]], ids.node_ids[key])
                    for t in c["practice"]["tasks"]
                    for key in t["knowledge_refs"]
                ),
                stage_resources=tuple(assignments),
                practice_project_idea=carrier["description"],
                v2_execution=V2ExecutionSnapshot.create(
                    result, bindings=bindings, packet=compiler_packet(context, source_facts)
                ),
            )
            if assignments:
                draft.resource_snapshots = capture_resource_snapshots(
                    conn, draft.stage_resources, draft.stages
                )
            validate_database_bindings(conn, draft)
            if write_fence:
                lock_planning_write(conn, project_id=project_id, run_id=run_id, fence=write_fence)
            repo.save_draft(draft, expected_version=expected_version, write_fence=write_fence)
            return draft

    def edit_descriptions(self, *, scope, project_id, draft_id, expected_version, expected_hash, stages):
        scope.require_project(project_id)
        with psycopg.connect(self.dsn, row_factory=dict_row) as conn:
            conn.execute(
                "SELECT set_config('app.project_id',%s,true),set_config('app.actor_id',%s,true)",
                (project_id, scope.actor_id),
            )
            lock_plan_version(conn, project_id, expected_version)
            if (
                conn.execute(
                    "SELECT 1 FROM learning_projects WHERE project_id=%s AND owner_actor_id=%s AND archived_at IS NULL FOR UPDATE",
                    (project_id, scope.actor_id),
                ).fetchone()
                is None
            ):
                raise ForbiddenError()
            repo = PgPlanRepository(self.dsn, connection=conn)
            draft = repo.get_draft(project_id=project_id, draft_id=draft_id)
            if draft is None or not draft.v2_execution:
                raise ValidationAppError("V2 draft required")
            draft.verify_hash(expected_hash)
            updated = draft.v2_execution.recompile_descriptions(
                stages, domain_approvals=self.domain_approvals
            )
            draft.apply_edit(stages=stages)
            draft.v2_execution = updated
            from app.domain.enums import PlanDraftStatus

            draft.status = PlanDraftStatus.AWAITING_APPROVAL
            validate_database_bindings(conn, draft)
            repo.save_draft(draft, expected_hash=expected_hash, expected_version=expected_version)
            return draft
