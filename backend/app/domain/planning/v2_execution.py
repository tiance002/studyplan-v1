"""Typed, consumed V2 execution snapshot and exact normalized identity bindings.

Only the persistence bridge creates this snapshot after the real Compiler runs.
The immutable source packet allows description edits to run the same Compiler;
process-local domain approvals must still come from trusted server dependencies.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields, is_dataclass
from datetime import datetime
from typing import get_args, get_origin, get_type_hints

from app.core.errors import ValidationAppError
from app.core.ids import canonical_json, content_hash
from app.domain.enums import OutlineSectionKind
from app.domain.planning.content_coverage import ReviewedContentIndex
from app.domain.planning.curriculum import (
    CurriculumContext,
    CurriculumPlan,
    ProjectCase,
    validate_curriculum_output,
)
from app.domain.planning.curriculum_compiler import (
    COMPILED_CONTRACT_VERSION,
    COMPILER_VERSION,
    CompiledPlan,
    CurriculumSourceFacts,
    PublicKnowledgeBinding,
    _compile_validated,
    _normalized_mapping_document,
    compile_curriculum,
)
from app.domain.planning.domain_verification import _plan_from_payload
from app.domain.planning.goal_requirements import GoalRequirementProfile
from app.domain.planning.resource_research import ResourceResearchResult, ReviewedAccessProof
from app.domain.resources.curation import PublicResourceSource


def reject(field):
    raise ValidationAppError("V2 execution snapshot rejected", field=field)


def _decode(kind, value):
    """Local decoder for the fixed existing dataclasses, never class names from JSON."""
    if value is None:
        return None
    origin, args = get_origin(kind), get_args(kind)
    if origin is tuple:
        item = args[0] if args else object
        if args and args[-1] is not Ellipsis:
            return tuple(_decode(t, v) for t, v in zip(args, value, strict=True))
        return tuple(_decode(item, v) for v in value)
    if origin is not None:
        for option in args:
            if option is not type(None):
                return _decode(option, value)
    if kind is datetime:
        return datetime.fromisoformat(value)
    if is_dataclass(kind):
        hints = get_type_hints(kind)
        return kind(
            **{
                f.name: _decode(hints.get(f.name, object), value[f.name])
                for f in fields(kind)
                if f.name in value
            }
        )
    return value


def compiler_packet(context, source_facts):
    def value(item):
        if isinstance(item, datetime):
            return item.isoformat()
        if isinstance(item, dict):
            return {key: value(v) for key, v in item.items()}
        if isinstance(item, (list, tuple)):
            return [value(v) for v in item]
        return item

    return json.loads(
        canonical_json(value({"research": asdict(context.research), "source_facts": asdict(source_facts)}))
    )


def compiler_arguments(compiled, packet, *, domain_approvals=()):
    source = compiled["source_snapshots"]
    profile = _decode(
        GoalRequirementProfile,
        {k: v for k, v in source["goal_requirement_profile"].items() if k != "profile_hash"},
    )
    facts = packet["source_facts"]
    source_facts = CurriculumSourceFacts(
        _decode(ReviewedContentIndex, facts["reviewed_index"]),
        tuple(_decode(PublicResourceSource, s) for s in facts["catalog_sources"]),
        tuple(_decode(ReviewedAccessProof, s) for s in facts["access_proofs"]),
        tuple(_decode(ProjectCase, s) for s in facts["project_cases"]),
    )
    context = CurriculumContext(
        canonical_json(source["curriculum_context"]),
        _decode(ResourceResearchResult, packet["research"]),
        tuple(domain_approvals),
    )
    return dict(
        context=context,
        profile=profile,
        capability_plan=_plan_from_payload(source["capability_plan"]),
        source_facts=source_facts,
        public_knowledge_bindings=tuple(
            PublicKnowledgeBinding(**n["public_binding"]) for n in compiled["nodes"] if "public_binding" in n
        ),
    )


@dataclass(frozen=True, slots=True)
class V2ExecutionSnapshot:
    _json: str

    @classmethod
    def create(cls, compiled: CompiledPlan, *, bindings, packet, original_curriculum_hash=None):
        return cls.from_payload(
            {
                "version": "V2ExecutionSnapshotV1",
                "compiled": compiled.to_payload(),
                "manifest": compiled.manifest.to_payload(),
                "bindings": bindings,
                "compiler_packet": packet,
                "original_curriculum_hash": original_curriculum_hash
                or compiled.manifest.to_payload()["input_curriculum_plan_hash"],
            }
        )

    @classmethod
    def from_payload(cls, raw):
        if raw is None:
            return None
        try:
            if set(raw) != {
                "version",
                "compiled",
                "manifest",
                "bindings",
                "compiler_packet",
                "original_curriculum_hash",
            }:
                reject("fields")
            c, m, b = raw["compiled"], raw["manifest"], raw["bindings"]
            # Reuse the actual Compiler mapping, rather than trusting a digest
            # supplied beside a modified output. This only verifies mechanical
            # consistency of already frozen facts, and grants no domain approval.
            source = c["source_snapshots"]
            frozen = source["curriculum"]
            curriculum = CurriculumPlan(
                canonical_json({k: v for k, v in frozen.items() if k not in {"plan_hash", "case_findings"}}),
                canonical_json(frozen["case_findings"]),
            )
            if curriculum.plan_hash != frozen["plan_hash"]:
                reject("curriculum_digest")
            args = compiler_arguments(c, raw["compiler_packet"])
            context = source["curriculum_context"]
            sources = context["sources"]
            if (
                context["input_hash"] != content_hash({k: v for k, v in context.items() if k != "input_hash"})
                or frozen["compile_sources"] != sources
                or sources["profile_hash"] != args["profile"].profile_hash
                or sources["capability_plan_hash"] != args["capability_plan"].plan_hash
                or args["capability_plan"].source_goal_profile_hash != args["profile"].profile_hash
                or sources["research_hash"] != args["context"].research.result_hash
                or sources["reviewed_index_hash"] != args["source_facts"].reviewed_index.index_hash
            ):
                reject("upstream_source_binding")
            from app.domain.planning.curriculum import _validate_output

            _validate_output(
                {
                    k: v
                    for k, v in frozen.items()
                    if k
                    not in {
                        "compile_sources",
                        "compile_materials",
                        "compile_cases",
                        "compile_context",
                        "case_findings",
                        "plan_hash",
                    }
                },
                context,
            )
            rebuilt = _compile_validated(
                _normalized_mapping_document(frozen, context),
                curriculum=curriculum,
                payload=source["curriculum_context"],
                profile=args["profile"],
                capability_plan=args["capability_plan"],
                context=args["context"],
                public_knowledge_bindings=args["public_knowledge_bindings"],
            )
            if rebuilt.to_payload() != c or rebuilt.manifest.to_payload() != m:
                reject("compiler_projection_binding")
            if (
                raw["version"] != "V2ExecutionSnapshotV1"
                or c["contract_version"] != COMPILED_CONTRACT_VERSION
                or c["compiler_version"] != COMPILER_VERSION
                or m["compiled_payload_digest"] != content_hash(c)
                or m["contract_version"] != c["contract_version"]
                or m["compiler_version"] != c["compiler_version"]
                or m["input_curriculum_plan_hash"] != c["source_snapshots"]["curriculum"]["plan_hash"]
            ):
                reject("digest")
            if set(b) != {
                "project_id",
                "run_id",
                "stages",
                "nodes",
                "units",
                "tasks",
                "practice_project_id",
                "materials",
            }:
                reject("bindings")
            for group, rows, key in (
                ("stages", c["stages"], "stage_id"),
                ("nodes", c["nodes"], "stable_key"),
                ("units", c["units"], "stable_key"),
                ("tasks", c["practice"]["tasks"], "stable_key"),
            ):
                if set(b[group]) != {row[key] for row in rows} or len(set(b[group].values())) != len(
                    b[group]
                ):
                    reject("identity_mapping")
            materials = {a["material_id"]: a["source_snapshot"] for a in c["resource_assignments"]}
            if set(b["materials"]) != set(materials):
                reject("material_mapping")
            for key, fact in b["materials"].items():
                if fact["material_digest"] != content_hash(materials[key]) or not fact["resource_id"]:
                    reject("material_binding")
            if c["unresolved"] or any(
                m["validation"][k] != "PASS" for k in ("completeness", "source_binding", "upstream_authority")
            ):
                reject("incomplete")
            return cls(canonical_json(raw))
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            raise ValidationAppError("V2 execution snapshot shape rejected") from exc

    def to_payload(self):
        return json.loads(self._json)

    def semantic_payload(self):
        raw = self.to_payload()
        # Revision construction remaps stages only. Hash stable semantic stage
        # keys while retaining exact node/unit/task/material identity/version.
        raw["bindings"]["stages"] = {s["stage_id"]: s["stable_key"] for s in raw["compiled"]["stages"]}
        raw["bindings"].pop("run_id")
        return raw

    def remap_stages(self, remap):
        raw = self.to_payload()
        raw["bindings"]["stages"] = {key: remap[value] for key, value in raw["bindings"]["stages"].items()}
        return self.from_payload(raw)

    def validate_structure(self, owner):
        raw = self.to_payload()
        c, b = raw["compiled"], raw["bindings"]
        if b["project_id"] != owner.project_id:
            reject("project")
        if hasattr(owner, "run_id") and b["run_id"] != owner.run_id:
            reject("run_binding")
        revision = getattr(owner, "v2_revision", None)
        if owner.goal_spec is not None:
            from app.domain.planning.intent import goal_spec_payload
            if revision is None:
                reject("uncompiled_goal")
            ctx = revision.to_payload()
            if ctx["change_kind"] == "semantic" and content_hash(goal_spec_payload(owner.goal_spec)) != content_hash(ctx["approved_goal_spec"]):
                reject("revision_goal")
            profile = c["source_snapshots"]["goal_requirement_profile"]
            for field in ("scope", "desired_depth", "starting_point", "outcome_purpose", "project_context"):
                if content_hash(profile[field]) != content_hash(getattr(owner.goal_spec, field)):
                    reject("revision_goal_profile")
        elif revision is not None and revision.to_payload()["change_kind"] == "semantic":
            reject("missing_revision_goal")
        if (
            owner.goal_snapshot != c["source_snapshots"]["goal_requirement_profile"]["target_summary"]
            or owner.extensions
            or owner.source_pack_key
            or owner.source_pack_version
            or any(s.learning_guidance is not None for s in owner.stages)
        ):
            reject("uncompiled_structure")
        expected = [
            (b["stages"][s["stage_id"]], s["stable_key"], s["title"], s["order_index"], s["what_to_learn"])
            for s in c["stages"]
        ]
        actual = [(s.stage_id, s.stable_key, s.title, s.order_index, s.objective) for s in owner.stages]
        if actual != expected or any(
            s.section_kind != OutlineSectionKind.V2_CURRICULUM for s in owner.stages
        ):
            reject("stages")
        units = [
            (b["stages"][s["stage_id"]], b["units"][key], i)
            for s in c["stages"]
            for i, key in enumerate(s["unit_refs"])
        ]
        tasks = [
            (b["stages"][s["stage_id"]], b["tasks"][key], i)
            for s in c["stages"]
            for i, key in enumerate(s["task_refs"])
        ]
        if units != [(link.stage_id, link.unit_id, link.order_index) for link in owner.unit_links]:
            reject("unit_links")
        if tasks != [(link.stage_id, link.task_id, link.order_index) for link in owner.task_links]:
            reject("task_links")
        links = [
            (b["tasks"][t["stable_key"]], b["nodes"][key], "core")
            for t in c["practice"]["tasks"]
            for key in t["knowledge_refs"]
        ]
        if links != [(link.task_id, link.node_id, str(link.role)) for link in owner.task_knowledge_links]:
            reject("task_knowledge_links")
        expected_resources = []
        for assignment in c["resource_assignments"]:
            material = b["materials"][assignment["material_id"]]
            if material["public_source_ref"]:
                expected_resources.append(
                    (
                        b["stages"][assignment["stage_ref"]],
                        assignment["role"],
                        assignment["order_index"],
                        material["public_source_ref"],
                        material["public_source_version"],
                        tuple(assignment["source_snapshot"]["section_refs"]),
                        tuple(
                            b["nodes"][n["stable_key"]]
                            for n in c["nodes"]
                            if n["stage_ref"] == assignment["stage_ref"]
                            and assignment["material_id"] in n["material_refs"]
                        ),
                    )
                )
        actual_resources = [
            (
                a.stage_id,
                str(a.role),
                a.order_index,
                a.source_ref,
                a.source_version,
                a.section_refs,
                a.node_ids,
            )
            for a in owner.stage_resources
        ]
        if expected_resources != actual_resources or any(
            a.fallback_search_terms for a in owner.stage_resources
        ):
            reject("public_resource_assignments")

    def recompile_descriptions(self, stages, *, domain_approvals=()):
        raw = self.to_payload()
        c, b = raw["compiled"], raw["bindings"]
        current = c["source_snapshots"]["curriculum"]
        arguments = compiler_arguments(c, raw["compiler_packet"], domain_approvals=domain_approvals)
        by_id = {s.stage_id: s for s in stages}
        for prior, logical in zip(current["stages"], c["stages"], strict=True):
            edited = by_id.get(b["stages"][logical["stage_id"]])
            if (
                edited is None
                or edited.stable_key != logical["stable_key"]
                or edited.order_index != logical["order_index"]
                or edited.section_kind != OutlineSectionKind.V2_CURRICULUM
            ):
                reject("semantic_edit_requires_replanning")
            prior["title"], prior["what_to_learn"] = edited.title, edited.objective
        if len(by_id) != len(current["stages"]):
            reject("stage_count")
        server_fields = {
            "compile_sources",
            "compile_materials",
            "compile_cases",
            "compile_context",
            "case_findings",
            "plan_hash",
        }
        candidate = validate_curriculum_output(
            {k: v for k, v in current.items() if k not in server_fields},
            arguments["context"].to_payload(),
            domain_approvals=domain_approvals,
        )
        from app.domain.planning.curriculum import CaseFinding, record_case_findings

        findings = tuple(_decode(CaseFinding, f) for f in current["case_findings"])
        candidate = record_case_findings(candidate, findings)
        result = compile_curriculum(candidate, **arguments)
        return self.create(
            result,
            bindings=b,
            packet=raw["compiler_packet"],
            original_curriculum_hash=raw["original_curriculum_hash"],
        )

    def recompile_local(self, stages, *, domain_approvals=()):
        """Recompile a complete permutation with only title/description edits.

        The unchanged Item6 validator proves outcome coverage and actual
        prerequisites; all source, project, task and capability facts stay frozen.
        """
        raw = self.to_payload()
        c, b = raw["compiled"], raw["bindings"]
        current = c["source_snapshots"]["curriculum"]
        arguments = compiler_arguments(c, raw["compiler_packet"], domain_approvals=domain_approvals)
        by_db = {b["stages"][s["stage_id"]]: (s, p) for s, p in zip(c["stages"], current["stages"], strict=True)}
        if len(stages) != len(by_db) or {s.stage_id for s in stages} != set(by_db):
            reject("local_required_stage_set")
        reordered = []
        for index, edited in enumerate(stages):
            logical, prior = by_db[edited.stage_id]
            if (edited.stable_key != logical["stable_key"] or edited.order_index != index
                    or edited.section_kind != OutlineSectionKind.V2_CURRICULUM or edited.learning_guidance is not None):
                reject("local_immutable_stage_identity")
            prior["title"], prior["what_to_learn"], prior["order_index"] = edited.title, edited.objective, index
            reordered.append(prior)
        current["stages"] = reordered
        server_fields = {"compile_sources", "compile_materials", "compile_cases", "compile_context", "case_findings", "plan_hash"}
        candidate = validate_curriculum_output({k: v for k, v in current.items() if k not in server_fields},
            arguments["context"].to_payload(), domain_approvals=domain_approvals)
        from app.domain.planning.curriculum import CaseFinding, record_case_findings
        candidate = record_case_findings(candidate, tuple(_decode(CaseFinding, f) for f in current["case_findings"]))
        compiled = compile_curriculum(candidate, **arguments)
        return self.create(compiled, bindings=b, packet=raw["compiler_packet"], original_curriculum_hash=raw["original_curriculum_hash"])

    def user_content(self):
        raw = self.to_payload()
        c, b = raw["compiled"], raw["bindings"]
        return {
            "profile": c["source_snapshots"]["goal_requirement_profile"],
            "capabilities": c["source_snapshots"]["capability_plan"],
            "stages": [
                s
                | {
                    "database_stage_id": b["stages"][s["stage_id"]],
                    "guidance": next(g for g in c["guidance"] if g["stage_ref"] == s["stage_id"]),
                }
                for s in c["stages"]
            ],
            "knowledge": c["nodes"],
            "units": c["units"],
            "materials": c["resource_assignments"],
            "practice": c["practice"],
            "project_study": c["project_study"],
            "constraints": c["constraints"],
            "unresolved": c["unresolved"],
            "source_limitations": c["source_limitations"],
        }

    def stage_content(self, stage_id, *, unit_id=None, task_id=None):
        raw = self.to_payload()
        c, b = raw["compiled"], raw["bindings"]
        ref = next((key for key, value in b["stages"].items() if value == stage_id), None)
        if ref is None:
            reject("stage_projection")
        stage = next(s for s in c["stages"] if s["stage_id"] == ref)
        if unit_id is not None and unit_id not in {b["units"][key] for key in stage["unit_refs"]}:
            reject("unit_projection")
        if task_id is not None and task_id not in {b["tasks"][key] for key in stage["task_refs"]}:
            reject("task_projection")
        return {
            "stage": stage,
            "guidance": next(g for g in c["guidance"] if g["stage_ref"] == ref),
            "knowledge": [n for n in c["nodes"] if n["stage_ref"] == ref],
            "units": [
                u
                for u in c["units"]
                if u["stage_ref"] == ref and (unit_id is None or b["units"][u["stable_key"]] == unit_id)
            ],
            "tasks": [
                t
                for t in c["practice"]["tasks"]
                if t["stage_ref"] == ref and (task_id is None or b["tasks"][t["stable_key"]] == task_id)
            ],
            "materials": [a for a in c["resource_assignments"] if a["stage_ref"] == ref],
            "project_study": [
                s
                for s in c["project_study"]
                if s["requirement"]["requirement_id"] in stage["project_study_refs"]
            ],
            "carrier": c["practice"]["carrier"],
            "constraints": c["constraints"],
            "source_limitations": c["source_limitations"],
        }


def validate_v2_structure(owner):
    marker = any(s.section_kind == OutlineSectionKind.V2_CURRICULUM for s in owner.stages)
    if marker != (owner.v2_execution is not None):
        reject("marker_snapshot_binding")
    if owner.v2_execution is not None:
        owner.v2_execution.validate_structure(owner)
