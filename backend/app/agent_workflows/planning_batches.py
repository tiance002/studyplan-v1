"""B3-F2 batched planning protocol.

Batch generation and repair keep their ``b3f2-batch-v1`` content protocol.
The ``b3f2-short-v2`` lifecycle reuses those nodes and ends at saved draft;
the current builder completes without a user interrupt.

Core ideas (design spec §数据与流程, §输出预算与模型适配, §失败、修复与恢复):

- **Frozen manifest**: at submission time the reviewed domain pack, per-purpose
  budgets, batch list and request/output caps are frozen into an immutable JSON
  manifest. The model may personalise stage titles/objectives and fill unreviewed nodes, but
  it can never re-key, re-assign or replace authoritative facts.
- **One request per node**: the graph dispatches exactly one model request per
  node (outline, each structure batch, each practice batch, bounded repairs).
- **Local validation**: each batch is validated against its own frozen slice, not
  against the whole route. Global relations are checked only after merge.
- **Deterministic merge**: batches are re-ordered by the skeleton; duplicates,
  missing stages or missing required nodes are rejected, never silently merged.
- **Fail fast**: a model failure, truncation or empty result stops the run
  immediately; only localisable content errors may consume the shared repair
  budget (at most two repairs per run).
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import replace
from typing import Any

from app.agent_workflows.planning_outline import STAGE_SKELETON_V1, frozen_pack_is_intact
from app.agent_workflows.planning_structure import (
    FOCUS_FORMAT,
    REVIEWED_STRUCTURE_V1,
    check_frozen_structure,
    has_canonical_inventory,
    presentation_payload,
    reviewed_stage_keys,
    uses_reviewed_structure,
    validate_presentation_entry,
)
from app.agent_workflows.state import PlanningState
from app.application.planning_budget import BudgetPolicy
from app.domain.enums import TaskKnowledgeRole
from app.domain.planning.guidance import guidance_payload, stage_guidance
from app.domain.planning.intent import (
    GoalSpec,
    goal_spec_from_payload,
    goal_spec_payload,
    purpose_requirements,
    required_module_closure,
)

PROTOCOL_VERSION = "b3f2-batch-v1"
SHORT_GENERATION_VERSION = "b3f2-short-v2"
DEFAULT_GENERIC_STAGE_COUNT = 4
MAX_REPAIR_TOTAL = 2

OUTLINE_PURPOSE = "planning.outline"
STRUCTURE_PURPOSE = "planning.structure"
PRACTICE_PURPOSE = "planning.practice"
REPAIR_PURPOSE = "planning.repair"

#: Deployment default used by the deterministic Fake demo and the interpreter
#: when no frozen policy is supplied. Real runs always pass the frozen policy.
DEFAULT_BUDGET = BudgetPolicy(4096, 8192, 4096, 8192, 8192, 393216)

#: Route targets for the batched graph.
ROUTE_FAIL = "fail_batched"
ROUTE_NEXT_STRUCTURE = "next_structure"
ROUTE_NEXT_PRACTICE = "next_practice"
ROUTE_PRACTICE = "practice"
ROUTE_MERGE = "merge"
ROUTE_REPAIR = "repair_batch"
ROUTE_DRAFT = "save_draft_projection"
ROUTE_ADVANCE_STRUCTURE = "advance_structure_batch"
ROUTE_ADVANCE_PRACTICE = "advance_practice_batch"
ROUTE_GENERATE_STRUCTURE = "generate_structure_batch"
ROUTE_GENERATE_PRACTICE = "generate_practice_batch"


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _canonical_hash(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def freeze_manifest(
    pack: dict[str, Any],
    policy: BudgetPolicy,
    model_ref: str,
    generic_stage_count: int = DEFAULT_GENERIC_STAGE_COUNT,
    goal_spec: GoalSpec | None = None,
    route_change_hash: str = '',
    *,
    outline_input_format: str | None = None,
    structure_input_format: str | None = None,
) -> dict[str, Any]:
    """Freeze the reviewed pack + budget into an immutable execution manifest.

    Reviewed packs keep every stage/node key from the pack. Unsupported
    directions fall back to ``search_only`` generic stage slots whose count is a
    fixed batch/request budget boundary, **not** a claim of domain coverage.
    """
    if outline_input_format is not None and outline_input_format != STAGE_SKELETON_V1:
        raise ValueError("unsupported outline_input_format")
    if structure_input_format is not None and structure_input_format != REVIEWED_STRUCTURE_V1:
        raise ValueError('unsupported structure_input_format')
    if structure_input_format is not None and not has_canonical_inventory(pack):
        raise ValueError('reviewed structure requires a complete frozen knowledge catalog')
    if outline_input_format == STAGE_SKELETON_V1:
        # Existing PlanTaskLink has no optional completion-gate semantics.
        # Reject unsupported blueprint semantics before a Run can be submitted.
        if any(p.get("optional") is True or p.get("required") is False
               for p in pack.get("practice_blueprints") or []):
            raise ValueError("optional practice blueprint is unsupported by the completion gate")
    stages = deepcopy(pack.get("stage_blueprints") or [])
    reviewed = bool(stages) and pack.get("resource_support") != "search_only"
    blueprints = {b.get("stable_key"): b for b in (pack.get("knowledge_blueprints") or [])}

    if reviewed:
        stage_specs = [{
            "stage_key": stage["stable_key"],
            "title": stage.get("title", ""),
            "section_kind": stage.get("section_kind", "core"),
            "objective": stage.get("objective", ""),
            "node_keys": list(stage.get("node_keys") or []),
        } for stage in stages]
        required_node_keys = list(required_module_closure(
            pack.get("knowledge_blueprints") or [], pack.get("required_node_keys") or []))
        resource_support = pack.get("resource_support", "reviewed_index")
        for index, spec in enumerate(stage_specs):
            spec["learning_guidance"] = guidance_payload(stage_guidance(pack, stages[index], stages[index - 1] if index else None))
        outputs = purpose_requirements(goal_spec)
        if outputs:
            guide = stage_guidance(pack, stages[-1], stages[-2] if len(stages) > 1 else None)
            guide = replace(guide, practice_delta=replace(guide.practice_delta,
                validation=tuple(dict.fromkeys((*guide.practice_delta.validation[:17], *outputs)))))
            stage_specs[-1]["learning_guidance"] = guidance_payload(guide)
    else:
        stage_specs = [{
            "stage_key": f"stage.general.{index}",
            "title": f"通用阶段 {index + 1}",
            "section_kind": "general",
            "objective": "",
            "node_keys": [],
        } for index in range(generic_stage_count)]
        required_node_keys = []
        resource_support = "search_only"

    structure_batches: list[dict[str, Any]] = []
    for index, spec in enumerate(stage_specs):
        stage_nodes = set(spec["node_keys"])
        external: set[str] = set()
        for key in spec["node_keys"]:
            blueprint = blueprints.get(key) or {}
            for dependency in blueprint.get("prerequisite_keys") or []:
                if dependency not in stage_nodes:
                    external.add(str(dependency))
            if blueprint.get("parent_key") and blueprint["parent_key"] not in stage_nodes:
                external.add(blueprint["parent_key"])
        structure_batches.append({
            "batch_index": index,
            "stage_key": spec["stage_key"],
            "scope": "stage",
            "node_keys": list(spec["node_keys"]),
            "declared_external_prerequisite_keys": sorted(external),
            **({'structure_input_format': REVIEWED_STRUCTURE_V1}
               if structure_input_format and spec['stage_key'] in reviewed_stage_keys(pack) else {}),
        })

    practice_batches = [{"batch_index": index, "stage_key": spec["stage_key"]}
                        for index, spec in enumerate(stage_specs)]

    budget = policy.as_dict()
    max_requests = 1 + len(structure_batches) + len(practice_batches) + MAX_REPAIR_TOTAL
    max_output_budget = (
        policy.outline
        + len(structure_batches) * policy.structure
        + len(practice_batches) * policy.practice
        + MAX_REPAIR_TOTAL * policy.repair
    )

    manifest: dict[str, Any] = {
        "protocol": PROTOCOL_VERSION,
        "model_ref": str(model_ref),
        "pack_key": pack.get("pack_key", ""),
        "pack_version": pack.get("version", 0),
        "pack_hash": _canonical_hash(pack),
        "resource_support": resource_support,
        "reviewed": reviewed,
        "stages": stage_specs,
        "required_node_keys": required_node_keys,
        **({"goal_spec": goal_spec_payload(goal_spec)} if goal_spec else {}),
        **({"route_change_hash": route_change_hash} if route_change_hash else {}),
        "required_root_keys": list(pack.get("required_node_keys") or []) if reviewed else [],
        "structure_batches": structure_batches,
        "practice_batches": practice_batches,
        "structure_batches_count": len(structure_batches),
        "practice_batches_count": len(practice_batches),
        "budget": budget,
        "max_repairs": MAX_REPAIR_TOTAL,
        "max_requests": max_requests,
        "max_output_budget": max_output_budget,
    }
    if outline_input_format is not None:
        manifest["outline_input_format"] = outline_input_format
    if structure_input_format is not None:
        manifest['structure_input_format'] = structure_input_format
        manifest['structure_focus_format'] = FOCUS_FORMAT
    manifest["manifest_hash"] = _canonical_hash(manifest)
    return manifest


def manifest_is_intact(manifest: dict[str, Any]) -> bool:
    """Verify a manifest was not tampered with after freezing."""
    if not isinstance(manifest, dict) or "manifest_hash" not in manifest:
        return False
    body = {key: value for key, value in manifest.items() if key != "manifest_hash"}
    return _canonical_hash(body) == manifest["manifest_hash"]


def stage_spec(manifest: dict[str, Any], stage_key: str) -> dict[str, Any]:
    for spec in manifest.get("stages") or []:
        if spec.get("stage_key") == stage_key:
            return spec
    raise KeyError(f"unknown stage key: {stage_key}")


def attempt_key(
    run_id: str,
    purpose: str,
    stage_key: str = "",
    batch_index: int = 0,
    repair_index: int = 0,
) -> str:
    """Stable, deterministic attempt id (never a random retry key)."""
    return f"{run_id}:{PROTOCOL_VERSION}:{purpose}:{stage_key or 'root'}:{batch_index}:{repair_index}"


# ---------------------------------------------------------------------------
# Local payloads (what a single request may see)
# ---------------------------------------------------------------------------


def structure_payload(state: PlanningState, batch: dict[str, Any]) -> dict[str, Any]:
    """Local context for one structure batch: this stage only, plus declared deps."""
    check_frozen_structure(state)
    manifest = state["manifest"]
    spec = stage_spec(manifest, batch["stage_key"])
    if uses_reviewed_structure(manifest, batch):
        return presentation_payload(state, batch, spec)
    pack = state.get("domain_pack") or {}
    owned = set(spec.get("node_keys") or [])
    blueprints = []
    for blueprint in pack.get("knowledge_blueprints") or []:
        if blueprint.get("stable_key") in owned:
            blueprints.append({
                "stable_key": blueprint["stable_key"],
                "title": blueprint.get("title", ""),
                "node_type": blueprint.get("node_type", "concept"),
                "objectives": list(blueprint.get("objectives") or []),
                "parent_key": blueprint.get("parent_key", ""),
                "prerequisite_keys": list(blueprint.get("prerequisite_keys") or []),
            })
    stage_blueprint: dict[str, Any] = next(
        (s for s in (pack.get("stage_blueprints") or []) if s.get("stable_key") == spec["stage_key"]),
        {},
    )
    return {
        "goal": state.get("goal"),
        "goal_spec": deepcopy(manifest.get("goal_spec")),
        "learning_guidance": deepcopy(spec.get("learning_guidance")),
        "stage": {
            "stable_key": spec["stage_key"],
            "title": spec.get("title", ""),
            "section_kind": spec.get("section_kind", "core"),
            "objective": spec.get("objective", ""),
        },
        "node_blueprints": blueprints,
        "required_unit_node_keys": list(spec.get("node_keys") or []),
        "resources": deepcopy(stage_blueprint.get("resources") or []),
        "declared_external_prerequisite_keys": list(batch.get("declared_external_prerequisite_keys") or []),
        "resource_support": manifest["resource_support"],
    }


def practice_payload(state: PlanningState, stage_key: str) -> dict[str, Any]:
    """Local context for one practice batch: only this stage's validated structure."""
    manifest = state["manifest"]
    spec = stage_spec(manifest, stage_key)
    pack = state.get("domain_pack") or {}
    stage_structure = next(
        (b for b in (state.get("structure_batches") or []) if b.get("stage_key") == stage_key),
        {},
    )
    practice_blueprint: dict[str, Any] = next(
        (p for p in (pack.get("practice_blueprints") or []) if p.get("section_key") == stage_key),
        {},
    )
    return {
        "goal": state.get("goal"),
        "goal_spec": deepcopy(manifest.get("goal_spec")),
        "required_outputs": list(purpose_requirements(goal_spec_from_payload(manifest.get("goal_spec"))))
            if stage_key == manifest["stages"][-1]["stage_key"] else [],
        "stage": {
            "stable_key": spec["stage_key"],
            "title": spec.get("title", ""),
            "objective": spec.get("objective", ""),
        },
        "structure": {
            "nodes": deepcopy(stage_structure.get("nodes") or []),
            "units": deepcopy(stage_structure.get("units") or []),
        },
        "practice_blueprint": deepcopy(practice_blueprint),
        "learning_guidance": deepcopy(spec.get("learning_guidance")),
        "resource_support": manifest["resource_support"],
    }


# ---------------------------------------------------------------------------
# Local validation
# ---------------------------------------------------------------------------


def _stable_keys(items: Any, label: str, errors: list[str]) -> set[str]:
    keys: set[str] = set()
    if not isinstance(items, list):
        errors.append(f"{label}必须是列表")
        return keys
    for item in items:
        if not isinstance(item, dict):
            errors.append(f"{label}包含非对象项")
            continue
        key = str(item.get("stable_key", "")).strip()
        if not key:
            errors.append(f"{label}存在空 stable_key")
            continue
        if key in keys:
            errors.append(f"{label}稳定键重复：{key}")
        keys.add(key)
    return keys


def validate_structure_batch(
    payload: dict[str, Any],
    batch: dict[str, Any],
    pack: dict[str, Any],
) -> list[str]:
    """Validate one structure batch against its frozen slice. No model call."""
    errors: list[str] = []
    stage_key = batch["stage_key"]
    for field in ("nodes", "units", "relations"):
        if field not in payload:
            errors.append(f"KnowledgeStructureV1 缺少必需字段：{field}（{stage_key}）")
    nodes = payload.get("nodes") if isinstance(payload, dict) else None
    units = payload.get("units") if isinstance(payload, dict) else None
    relations = payload.get("relations")
    if not isinstance(relations, list):
        errors.append(f"结构批次 relations 必须是列表：{stage_key}")
    if not isinstance(nodes, list) or not nodes:
        errors.append(f"结构批次缺少知识节点：{stage_key}")
    if not isinstance(units, list) or not units:
        errors.append(f"结构批次缺少学习单元：{stage_key}")

    node_keys = _stable_keys(nodes, "知识节点", errors)
    unit_keys = _stable_keys(units, "学习单元", errors)
    attached_nodes: set[str] = set()
    for unit in units if isinstance(units, list) else []:
        if not isinstance(unit, dict):
            continue
        if unit.get("section_key") != stage_key:
            errors.append(f"学习单元归属未知阶段：{unit.get('section_key')}")
        if not [o for o in (unit.get("objectives") or []) if str(o).strip()]:
            errors.append(f"学习单元缺少目标：{unit.get('stable_key')}")
        owned = unit.get("node_keys")
        if not isinstance(owned, list) or not owned:
            errors.append(f"学习单元未关联知识节点：{unit.get('stable_key')}")
            continue
        attached_nodes.update(key for key in owned if isinstance(key, str))
        for key in owned:
            if key not in node_keys:
                errors.append(f"学习单元引用未知知识节点：{key}")
    for key in sorted(node_keys - attached_nodes):
        errors.append(f"结构批次知识节点未关联到学习单元：{key}（{stage_key}）")

    allowed = node_keys | set(batch.get("declared_external_prerequisite_keys") or [])
    for relation in relations if isinstance(relations, list) else []:
        if not isinstance(relation, dict):
            errors.append("关系包含非对象项")
            continue
        if str(relation.get("relation_type", "")) not in {"prerequisite", "contains"}:
            errors.append(f"关系类型非法：{relation.get('relation_type')!r}")
        for side in ("from_stable_key", "to_stable_key"):
            if relation.get(side) not in allowed:
                errors.append(f"关系引用未声明节点：{relation.get(side)}")

    # Check completeness while the owning batch can still use local repair.
    # Match the final route validator's exact direction and type; do not insert
    # missing edges or require relations owned by a different frozen batch.
    relation_keys = {
        (r.get("from_stable_key"), r.get("to_stable_key"), r.get("relation_type"))
        for r in relations if isinstance(r, dict)
        and all(isinstance(r.get(field), str) for field in
                ("from_stable_key", "to_stable_key", "relation_type"))
    } if isinstance(relations, list) else set()
    declared_owned = set(batch.get("node_keys") or [])
    for blueprint in pack.get("knowledge_blueprints") or []:
        key = blueprint["stable_key"]
        if key not in declared_owned:
            continue
        parent = blueprint.get("parent_key")
        if parent and (parent, key, "contains") not in relation_keys:
            errors.append(f"缺少子知识关联：{key}（{stage_key}）")
        for dependency in blueprint.get("prerequisite_keys") or []:
            if (dependency, key, "prerequisite") not in relation_keys:
                errors.append(f"缺少领域前置依赖：{dependency} -> {key}（{stage_key}）")

    # The reviewed pack owns authoritative keys: reject invented nodes that are
    # not part of the pack's declared node set for this stage.
    #
    # A stage that declares **no** node inventory reviews its resources/stages but
    # not the node list (for example the Python pack); there is nothing
    # authoritative to protect, so the model may author nodes there. Only a
    # declared inventory is protected from invention.
    reviewed = (pack.get("resource_support") or "") != "search_only" and bool(pack.get("stage_blueprints"))
    if reviewed:
        declared_owned = set(batch.get("node_keys") or [])
        if declared_owned:
            forged = node_keys - declared_owned
            if forged:
                errors.append("结构批次新增未审核知识节点：" + ", ".join(sorted(forged)))
    if not unit_keys and units:
        errors.append("学习单元稳定键无效")
    return errors


def validate_practice_batch(
    payload: dict[str, Any],
    stage_key: str,
    structure: dict[str, Any],
) -> list[str]:
    """Validate one practice batch against its stage's validated structure."""
    errors: list[str] = []
    for field in ("stable_key", "title", "idea", "tasks", "task_knowledge_links"):
        if field not in payload:
            errors.append(f"PracticeProposalV1 缺少必需字段：{field}（{stage_key}）")
    for field in ("stable_key", "title", "idea"):
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"实践批次 {field} 必须是非空字符串：{stage_key}")
    links = payload.get("task_knowledge_links")
    if not isinstance(links, list):
        errors.append(f"实践批次 task_knowledge_links 必须是列表：{stage_key}")
    tasks = payload.get("tasks") if isinstance(payload, dict) else None
    if not isinstance(tasks, list) or not tasks:
        errors.append(f"实践批次缺少任务：{stage_key}")
        return errors
    node_keys = {str(n.get("stable_key", "")) for n in (structure.get("nodes") or []) if isinstance(n, dict)}
    task_keys = _stable_keys(tasks, "实践任务", errors)
    for task in tasks:
        if not isinstance(task, dict):
            continue
        if task.get("section_key") != stage_key:
            errors.append(f"实践任务归属未知阶段：{task.get('section_key')}")
        if not str(task.get("goal", "")).strip():
            errors.append(f"实践任务缺少目标：{task.get('stable_key')}")
        if not [a for a in (task.get("acceptance") or []) if str(a).strip()]:
            errors.append(f"实践任务缺少验收标准：{task.get('stable_key')}")
        if not isinstance(task.get("in_scope"), list) or not isinstance(task.get("out_scope"), list):
            errors.append(f"实践任务缺少范围/排除项：{task.get('stable_key')}")
        for link in task.get("knowledge_links") or []:
            if not isinstance(link, dict) or link.get("node_stable_key") not in node_keys:
                errors.append(f"实践任务引用未知知识节点：{task.get('stable_key')}")
    for index, link in enumerate(links if isinstance(links, list) else []):
        if not isinstance(link, dict):
            errors.append("任务知识关联包含非对象项")
            continue
        if link.get("task_stable_key") not in task_keys:
            errors.append(f"任务知识关联引用未知任务：{link.get('task_stable_key')}")
        if link.get("node_stable_key") not in node_keys:
            errors.append(f"任务知识关联引用未知节点：{link.get('node_stable_key')}")
        # Use the final validator's domain enum and missing-role default.
        role = link.get("role", TaskKnowledgeRole.CORE.value)
        try:
            TaskKnowledgeRole(str(role))
        except ValueError:
            errors.append(f"实践批次第 {index} 条任务知识关联的 role 非法：{role!r}（{stage_key}）")
    return errors


# ---------------------------------------------------------------------------
# Deterministic merge
# ---------------------------------------------------------------------------


def merge_batches(
    outline: dict[str, Any],
    structure_batches: list[dict[str, Any]],
    practice_batches: list[dict[str, Any]],
    pack: dict[str, Any],
    *,
    manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Merge validated batches in skeleton order into the current projection shape.

    Rejects duplicate business keys, missing stages and missing required nodes.
    The returned ``errors`` list is non-empty when the merge must fail.
    """
    if (not manifest or not manifest_is_intact(manifest)
            or manifest.get("outline_input_format") != STAGE_SKELETON_V1
            or not frozen_pack_is_intact(pack, manifest)):
        return {"errors": ["冻结清单或内容完整性校验失败"], "outline": {}, "nodes": [], "units": [],
                "relations": [], "practice_proposal": {"tasks": [], "task_knowledge_links": []}}
    state = {'manifest': manifest, 'domain_pack': pack}
    try:
        check_frozen_structure(state)
    except ValueError as exc:
        return {"errors": [str(exc)], "outline": {}, "nodes": [], "units": [],
                "relations": [], "practice_proposal": {"tasks": [], "task_knowledge_links": []}}
    errors: list[str] = []
    for batch in manifest['structure_batches']:
        if not uses_reviewed_structure(manifest, batch):
            continue
        entry = next((s for s in structure_batches if s.get('stage_key') == batch['stage_key']), {})
        errors.extend(validate_presentation_entry(entry, state, batch))
    outline = deepcopy(outline)
    sections = list((outline or {}).get("sections") or [])
    blueprints = {s["stable_key"]: s for s in pack.get("stage_blueprints", [])}
    for index, section in enumerate(sections):
        blueprint = blueprints.get(section.get("stable_key"))
        # The model cannot invent previously learned relationships or source proof.
        section.pop("learning_guidance", None)
        if blueprint is not None:
            allowed_sources = set(pack.get("resource_refs") or [])
            for resource in section.get("resources") or []:
                if resource.get("source_ref") and resource["source_ref"] not in allowed_sources:
                    errors.append("资源来源未在受审核清单中：" + str(resource["source_ref"]))
            # Curated facts survive omitted/rewritten model output. Personal
            # titles/objectives remain; model-authored material cannot replace
            # the pack's primary/comparison/case study or extension instructions.
            section["section_kind"] = blueprint.get("section_kind", "core")
            section["resources"] = deepcopy(blueprint.get("resources") or [])
            section["extensions"] = deepcopy(blueprint.get("extensions") or [])
            previous = blueprints.get(sections[index - 1].get("stable_key")) if index else None
            frozen: dict[str, Any] = next((s for s in (manifest or {}).get("stages", [])
                           if s["stage_key"] == section.get("stable_key")), {})
            section["learning_guidance"] = deepcopy(frozen.get("learning_guidance")) or guidance_payload(stage_guidance(pack, blueprint, previous))
    stage_order = [section.get("stable_key") for section in sections]

    by_stage_structure = {b.get("stage_key"): b for b in structure_batches}
    by_stage_practice = {b.get("stage_key"): b for b in practice_batches}
    node_blueprints = {n["stable_key"]: n for n in pack.get("knowledge_blueprints", [])}
    reviewed = (pack.get("resource_support") or "") != "search_only" and bool(blueprints)

    nodes: list[dict[str, Any]] = []
    units: list[dict[str, Any]] = []
    relations: list[dict[str, Any]] = []
    tasks: list[dict[str, Any]] = []
    task_links: list[dict[str, Any]] = []

    seen_node: set[str] = set()
    seen_unit: set[str] = set()
    seen_task: set[str] = set()
    node_stage: dict[str, str] = {}
    seen_relation: set[tuple[str, str, str]] = set()

    for stage_key in stage_order:
        structure = by_stage_structure.get(stage_key)
        if structure is None:
            errors.append(f"缺少结构批次：{stage_key}")
            continue
        blueprint = blueprints.get(stage_key) or {}
        guidance = blueprint.get("learning_guidance") or {}
        declared_repeats = set(guidance.get("knowledge_keys") or []) & set(blueprint.get("node_keys") or [])
        repeat_keys: set[str] = set()
        for node in structure.get("nodes") or []:
            key = str(node.get("stable_key", ""))
            if key in seen_node:
                # Exact stable-key reuse is allowed only by curated per-exposure
                # relationships. This is not semantic deduplication of tutorials.
                if (pack.get("resource_support") != "search_only" and key in node_blueprints
                        and node_stage[key] != stage_key and key in declared_repeats
                        and guidance.get("exposure_relation") in {"review", "compare", "deepen", "version_context"}):
                    repeat_keys.add(key)
                    continue
                errors.append(f"知识节点重复：{key}")
                continue
            seen_node.add(key)
            node_stage[key] = stage_key
            canonical = deepcopy(node)
            if reviewed and key in node_blueprints:
                # Every reviewed definition is local authority, even if it has
                # only one exposure. Missing optional canonical fields cannot
                # be supplied by the model as new truth.
                for field in ("title", "node_type", "objectives", "scope", "acceptance",
                              "parent_key", "prerequisite_keys"):
                    if field in node_blueprints[key]:
                        canonical[field] = deepcopy(node_blueprints[key][field])
                    else:
                        canonical.pop(field, None)
            nodes.append(canonical)
        for unit in structure.get("units") or []:
            key = str(unit.get("stable_key", ""))
            if key in seen_unit:
                errors.append(f"学习单元重复：{key}")
                continue
            seen_unit.add(key)
            units.append(deepcopy(unit))
        for relation in structure.get("relations") or []:
            identity = (relation.get("from_stable_key", ""), relation.get("to_stable_key", ""), relation.get("relation_type", ""))
            if identity in seen_relation and identity[1] in repeat_keys:
                continue
            seen_relation.add(identity)
            relations.append(deepcopy(relation))

        practice = by_stage_practice.get(stage_key)
        if practice is None:
            errors.append(f"缺少实践批次：{stage_key}")
            continue
        payload = practice.get("payload") or {}
        curated_tasks = [p for p in pack.get("practice_blueprints", [])
                         if p.get("section_key") == stage_key] if reviewed else []
        stage_tasks = payload.get("tasks") or []
        stage_links = payload.get("task_knowledge_links") or []
        if curated_tasks:
            # Blueprint identity/count and completion gates are authoritative.
            # Extra model tasks cannot become an alternative completion gate.
            supplied = {t.get("stable_key"): t for t in stage_tasks}
            stage_tasks, stage_links = [], []
            for curated in curated_tasks:
                key = curated["stable_key"]
                candidate = supplied.get(key) or {}
                saved = {field: deepcopy(candidate[field]) for field in ("description", "hints")
                         if field in candidate}
                saved.update(stable_key=key, section_key=stage_key,
                             title=curated.get("title") or blueprint.get("title", ""),
                             goal=curated.get("goal") or blueprint.get("objective", ""),
                             in_scope=deepcopy(curated.get("in_scope") or [curated.get("goal") or blueprint.get("objective", "")]),
                             out_scope=deepcopy(curated.get("out_scope") or []),
                             acceptance=deepcopy(curated.get("acceptance") or []))
                for field in ("required", "optional", "deliverable", "required_deliverable", "scope"):
                    if field in curated:
                        saved[field] = deepcopy(curated[field])
                links = deepcopy(curated.get("knowledge_links")) if "knowledge_links" in curated else [
                    {"node_stable_key": key, "role": TaskKnowledgeRole.CORE.value}
                    for key in curated.get("node_keys") or []]
                saved["knowledge_links"] = links
                stage_tasks.append(saved)
                stage_links.extend({**link, "task_stable_key": key} for link in links)
        for task_index, task in enumerate(stage_tasks):
            key = str(task.get("stable_key", ""))
            if key in seen_task:
                errors.append(f"实践任务重复：{key}")
                continue
            seen_task.add(key)
            saved_task = deepcopy(task)
            if manifest and stage_key == stage_order[-1] and task_index == 0:
                outputs = purpose_requirements(goal_spec_from_payload(manifest.get("goal_spec")))
                if outputs:
                    saved_task["acceptance"] = list(dict.fromkeys([*(saved_task.get("acceptance") or []), *outputs]))
            tasks.append(saved_task)
        task_links.extend(deepcopy(stage_links))

    if reviewed:
        # Incoming parent/prerequisite edges are canonical node facts. Model
        # edges must not strengthen or erase the reviewed dependency graph.
        canonical_keys = seen_node & set(node_blueprints)
        relations = [r for r in relations if not (
            r.get("to_stable_key") in canonical_keys
            and r.get("relation_type") in {"contains", "prerequisite"})]
        for key in sorted(canonical_keys):
            source = node_blueprints[key]
            if source.get("parent_key"):
                relations.append({"from_stable_key": source["parent_key"], "to_stable_key": key,
                                  "relation_type": "contains"})
            relations.extend({"from_stable_key": dependency, "to_stable_key": key,
                              "relation_type": "prerequisite"}
                             for dependency in source.get("prerequisite_keys") or [])

    # Re-order units and tasks deterministically by skeleton order.
    for index, unit in enumerate(units):
        unit["order_index"] = index
    for index, task in enumerate(tasks):
        task["order_index"] = index

    if reviewed:
        for unit in units:
            # Keep full canonical facts through existing catalog persistence:
            # knowledge_nodes has no scope/acceptance columns; units.rubric is
            # versioned JSONB already saved with the owned catalog snapshot.
            teaching = deepcopy((unit.get('rubric') or {}).get('teaching'))
            unit["rubric"] = {
                **({'teaching': teaching} if teaching and (manifest or {}).get('structure_focus_format') == FOCUS_FORMAT else {}),
                "canonical_knowledge": {key: deepcopy(node_blueprints[key])
                    for key in unit.get("node_keys") or [] if key in node_blueprints},
                "canonical_practice": {task["stable_key"]: {
                    field: deepcopy(value) for field, value in task.items()
                    if field not in {"description", "hints"}} for task in tasks
                    if task.get("section_key") == unit.get("section_key")},
            }

    required = set((manifest or {}).get("required_node_keys") or pack.get("required_node_keys") or [])
    missing = required - seen_node
    if missing:
        errors.append("缺少必要知识节点：" + ", ".join(sorted(missing)))

    for stage_key in stage_order:
        if not any(u.get("section_key") == stage_key for u in units):
            errors.append(f"阶段缺少学习单元：{stage_key}")
        if not any(t.get("section_key") == stage_key for t in tasks):
            errors.append(f"阶段缺少实践任务：{stage_key}")

    return {
        "errors": errors,
        "outline": outline,
        "nodes": nodes,
        "units": units,
        "relations": relations,
        "practice_proposal": {
            "stable_key": "practice.route",
            "title": (("用户项目：" if pack['semantic_context']['carrier_kind'] == 'user_project' else "默认项目候选（可替换）：")
                      + pack['semantic_context']['carrier_title']) if pack.get('semantic_context') else (pack.get("title") or "学习路线") + "实践",
            "idea": pack['semantic_context']['carrier_slice'] if pack.get('semantic_context') else (pack.get("title") or ""),
            "tasks": tasks,
            "task_knowledge_links": task_links,
        },
        "route_scope": "reviewed" if reviewed else "search_only",
        "route_status": "reviewed" if reviewed else "generic_unverified",
        "resource_support": "reviewed_index" if reviewed else "needs_resource_review",
    }


# ---------------------------------------------------------------------------
# Budget guard (pure; the ledger enforces it under a run advisory lock)
# ---------------------------------------------------------------------------


_PURPOSE_BUDGET_KEY = {
    OUTLINE_PURPOSE: "outline",
    STRUCTURE_PURPOSE: "structure",
    PRACTICE_PURPOSE: "practice",
    REPAIR_PURPOSE: "repair",
}


def output_budget_for(manifest: dict[str, Any], purpose: str) -> int:
    """Reserved output budget for one purpose from the frozen manifest."""
    key = _PURPOSE_BUDGET_KEY.get(purpose)
    if key is None:
        return int(manifest["max_output_budget"])
    return int((manifest.get("budget") or {}).get(key, 0))


def attempt_purpose(attempt_id: str) -> str:
    """Parse the purpose back out of a stable attempt id."""
    parts = attempt_id.split(":")
    return parts[-4] if len(parts) >= 5 else ""


def attempt_stage(attempt_id: str) -> str:
    """Parse the stage key back out of a stable attempt id (``root`` -> "")."""
    parts = attempt_id.split(":")
    if len(parts) < 5:
        return ""
    stage = parts[-3]
    return "" if stage == "root" else stage


def allowed_attempt_keys(run_id: str, manifest: dict[str, Any]) -> set[str]:
    """The frozen attempt catalog: no dispatch may use a key outside this set."""
    keys = {attempt_key(run_id, OUTLINE_PURPOSE, "", 0, 0)}
    repairs = int(manifest.get("max_repairs", 0))
    structure = manifest.get("structure_batches") or []
    practice = manifest.get("practice_batches") or []
    for spec in structure:
        index = int(spec["batch_index"])
        keys.add(attempt_key(run_id, STRUCTURE_PURPOSE, spec["stage_key"], index, 0))
        for repair_index in range(1, repairs + 1):
            keys.add(attempt_key(run_id, REPAIR_PURPOSE, spec["stage_key"], index, repair_index))
    offset = len(structure)
    for spec in practice:
        index = int(spec["batch_index"])
        keys.add(attempt_key(run_id, PRACTICE_PURPOSE, spec["stage_key"], index, 0))
        for repair_index in range(1, repairs + 1):
            keys.add(attempt_key(run_id, REPAIR_PURPOSE, spec["stage_key"], offset + index, repair_index))
    return keys


def planned_output_budget(manifest: dict[str, Any]) -> int:
    return int(manifest["max_output_budget"])


def recursion_limit(manifest: dict[str, Any]) -> int:
    """Explicit, finite LangGraph recursion limit for a full batched run.

    Derived from the frozen batch counts (never the framework default of 25, which
    a 19-request Agent run would exceed) with a small fixed margin. Not unlimited.

    Super-step accounting for the real ``StateGraph`` (one node execution each):

    - per structure/practice batch: ``generate_*_batch`` + ``validate_*_batch`` +
      ``advance_*_batch`` = 3, **including** the last batch of each phase — the
      phase transition is decided *after* ``advance_*_batch``, so the completed
      index reaches the full batch count (matching the interpreter and the
      business progress projection);
    - each bounded repair re-runs ``repair_batch`` + ``validate_*_batch`` = 2;
    - fixed steps: ``normalize`` + ``generate_skeleton`` + ``merge_and_validate`` +
      ``save_draft_projection`` (the saved draft ends the run).

    The interpreter (``run_batched_planning_graph``) uses its own ``max_steps``, so
    this cap only bounds the real framework path; keeping it derived (not the
    default 25) is what lets a full 9-stage run reach saved draft completion.
    """
    structure = len(manifest.get("structure_batches") or [])
    practice = len(manifest.get("practice_batches") or [])
    repairs = int(manifest.get("max_repairs", 0))
    batch_steps = 3 * (structure + practice)
    repair_steps = 2 * repairs
    fixed = 4 + 10  # normalize/skeleton/merge/save + safety margin
    return batch_steps + repair_steps + fixed


def budget_violation(
    manifest: dict[str, Any],
    *,
    request_count: int,
    reserved_output: int,
    stage_key: str,
    purpose: str,
) -> str | None:
    """Return a reason string when a dispatch would exceed the frozen budget."""
    if request_count >= int(manifest["max_requests"]):
        return "run_budget_exhausted"
    if reserved_output > int(manifest["max_output_budget"]):
        return "run_budget_exhausted"
    if purpose in {STRUCTURE_PURPOSE, PRACTICE_PURPOSE, REPAIR_PURPOSE}:
        allowed_stages = {spec["stage_key"] for spec in manifest.get("stages") or []}
        if stage_key and stage_key not in allowed_stages:
            return "run_manifest_violation"
    return None


# ---------------------------------------------------------------------------
# Business progress projection
# ---------------------------------------------------------------------------

PHASE_OUTLINE = "outline"
PHASE_STRUCTURE = "structure"
PHASE_PRACTICE = "practice"
PHASE_VALIDATION = "validation"
PHASE_DONE = "done"

#: Closed set of phases the API may expose. Anything else is refused, not guessed.
PROGRESS_PHASES = frozenset({PHASE_OUTLINE, PHASE_STRUCTURE, PHASE_PRACTICE, PHASE_VALIDATION, PHASE_DONE})


def derive_progress(state: PlanningState) -> dict[str, Any]:
    """Project graph state into a **business-only** progress payload.

    Only stable business fields are produced. Thread ids, LangGraph node names,
    raw checkpoints and model prompts are deliberately absent: the projection is
    the single authorised progress view.

    Completed indices are **absolute** (not deltas), so writing the same
    checkpoint twice can never double count. Token counts are *not* derived here
    — the API layer corrects them from the paid-attempt ledger, keeping missing
    usage ``NULL`` instead of pretending it is ``0``.
    """
    manifest = state.get("manifest") or {}
    stages = manifest.get("stages") or []
    total_stages = len(stages)
    total_structure = int(
        manifest.get("structure_batches_count") or len(manifest.get("structure_batches") or [])
    )
    total_practice = int(
        manifest.get("practice_batches_count") or len(manifest.get("practice_batches") or [])
    )
    completed_structure = min(max(int(state.get("current_structure_index") or 0), 0), total_structure)
    completed_practice = min(max(int(state.get("current_practice_index") or 0), 0), total_practice)

    def stage_at(index: int) -> tuple[int | None, str]:
        if 0 <= index < total_stages:
            return index, str(stages[index].get("title") or "")
        return None, ""

    if not state.get("outline_ref"):
        phase = PHASE_OUTLINE
        stage_index, stage_title = (stage_at(0) if total_stages else (None, ""))
    elif completed_structure < total_structure:
        phase = PHASE_STRUCTURE
        stage_index, stage_title = stage_at(completed_structure)
    elif completed_practice < total_practice:
        phase = PHASE_PRACTICE
        stage_index, stage_title = stage_at(completed_practice)
    elif state.get("draft_ref"):
        phase = PHASE_DONE
        stage_index, stage_title = (None, "")
    else:
        phase = PHASE_VALIDATION
        stage_index, stage_title = (None, "")

    failure_stage = str(state.get("failure_stage") or "")
    failure_phase = ""
    if failure_stage:
        # Structure batches run first; a failure after every structure batch has
        # committed is therefore a practice-phase failure.
        failure_phase = PHASE_PRACTICE if completed_structure >= total_structure else PHASE_STRUCTURE

    return {
        "kind": "run_progress",
        "phase": phase,
        "current_stage_index": stage_index,
        "current_stage_title": stage_title,
        "total_stages": total_stages,
        "completed_structure_batches": completed_structure,
        "total_structure_batches": total_structure,
        "completed_practice_batches": completed_practice,
        "total_practice_batches": total_practice,
        "completed_batches": completed_structure + completed_practice,
        "max_requests": int(manifest.get("max_requests") or 0),
        "failure_phase": failure_phase,
        "failure_stage": failure_stage,
    }


# ---------------------------------------------------------------------------
# Interpreter (mirrors the real StateGraph routing node-for-node)
# ---------------------------------------------------------------------------


def _merge_state(state: PlanningState, delta: dict[str, Any]) -> None:
    mutable: dict[str, Any] = state  # type: ignore[assignment]
    mutable.update(delta)


def _initial_state(initial: PlanningState, manifest: dict[str, Any] | None) -> PlanningState:
    state: PlanningState = dict(initial)  # type: ignore[assignment]
    if manifest is not None:
        state["manifest"] = manifest  # type: ignore[typeddict-unknown-key]
    if not state.get("manifest"):
        raise ValueError("Current planning requires a frozen manifest")
    check_frozen_structure(state)
    state.setdefault("protocol", PROTOCOL_VERSION)  # type: ignore[typeddict-item]
    return state


def run_batched_planning_graph(
    nodes: Any,
    initial: PlanningState,
    *,
    manifest: dict[str, Any] | None = None,
    max_repair_total: int = MAX_REPAIR_TOTAL,
    max_steps: int = 400,
    progress: Any = None,
) -> Any:
    """Deterministic interpreter for the batched graph.

    Mirrors ``build_short_planning_graph`` node-for-node so routing can be
    mechanically proven without a real framework. Completion stops at saved draft.

    ``progress`` is an optional ``Callable[[PlanningState], None]`` invoked only
    at stable points (after each committed batch / merge / draft), never
    mid-batch. It exists so the in-process path reports the same business
    progress as the checkpointed one.
    """
    from app.agent_workflows.graphs import PlanningTrace  # local import avoids a cycle

    state = _initial_state(initial, manifest)
    # Bind caller-supplied frozen input outside the mutable interpreter state.
    if getattr(nodes, 'frozen_input', None) is None:
        nodes.frozen_input = deepcopy(state)
    frozen = state["manifest"]  # type: ignore[typeddict-item]
    visited: list[str] = []

    def emit() -> None:
        if progress is not None:
            progress(state)

    def fail() -> Any:
        visited.append("record_failure")
        _merge_state(state, nodes.record_failure_node(state))
        emit()
        return PlanningTrace(visited=visited, state=state, stopped_at="failed",
                             failed_errors=list(state.get("validation_errors") or []))

    steps = 0

    def guard_steps() -> None:
        nonlocal steps
        steps += 1
        if steps > max_steps:
            raise RuntimeError("batched planning graph step limit exceeded")

    # ---- normalize ----
    visited.append("normalize")
    _merge_state(state, nodes.normalize(state))
    if state.get("input_errors"):
        return fail()

    # ---- skeleton ----
    guard_steps()
    visited.append("generate_skeleton")
    _merge_state(state, nodes.generate_skeleton(state))
    if state.get("generation_errors"):
        return fail()
    emit()

    # ---- structure batches ----
    structure_count = len(frozen["structure_batches"])
    while True:
        index = int(state.get("current_structure_index", 0))
        if index >= structure_count:
            break
        guard_steps()
        visited.append("generate_structure_batch")
        _merge_state(state, nodes.generate_structure_batch(state))
        if state.get("generation_errors"):
            return fail()
        while True:
            guard_steps()
            visited.append("validate_structure_batch")
            _merge_state(state, nodes.validate_structure_batch_node(state))
            if not state.get("structure_errors"):
                break
            if int(state.get("repair_count", 0)) >= max_repair_total:
                return fail()
            guard_steps()
            visited.append("repair_batch")
            _merge_state(state, nodes.repair_batch(state))
            if state.get("generation_errors"):
                return fail()
        visited.append("advance_structure_batch")
        _merge_state(state, nodes.advance_structure_batch(state))
        emit()

    # ---- practice batches ----
    practice_count = len(frozen["practice_batches"])
    while True:
        index = int(state.get("current_practice_index", 0))
        if index >= practice_count:
            break
        guard_steps()
        visited.append("generate_practice_batch")
        _merge_state(state, nodes.generate_practice_batch(state))
        if state.get("generation_errors"):
            return fail()
        while True:
            guard_steps()
            visited.append("validate_practice_batch")
            _merge_state(state, nodes.validate_practice_batch_node(state))
            if not state.get("structure_errors"):
                break
            if int(state.get("repair_count", 0)) >= max_repair_total:
                return fail()
            guard_steps()
            visited.append("repair_batch")
            _merge_state(state, nodes.repair_batch(state))
            if state.get("generation_errors"):
                return fail()
        visited.append("advance_practice_batch")
        _merge_state(state, nodes.advance_practice_batch(state))
        emit()

    # ---- merge + global validation ----
    guard_steps()
    visited.append("merge_and_validate")
    _merge_state(state, nodes.merge_and_validate(state))
    if state.get("structure_errors") or state.get("generation_errors"):
        return fail()
    emit()

    # ---- draft completion ----
    guard_steps()
    visited.append("save_draft_projection")
    _merge_state(state, nodes.save_draft_projection(state))
    emit()
    return PlanningTrace(visited=visited, state=state, stopped_at=None)


def build_short_planning_graph(nodes: Any, *, checkpointer: Any = None) -> Any:
    """Generate and persist a draft, then finish without a user interrupt."""
    from app.agent_workflows.graphs import LANGGRAPH_AVAILABLE
    from app.agent_workflows.state import PlanningState as _PlanningState

    if not LANGGRAPH_AVAILABLE:
        raise RuntimeError(
            "langgraph 未安装，无法装配 StateGraph；请使用 run_batched_planning_graph 解释器"
        )
    from langgraph.graph import END, START, StateGraph  # type: ignore[import-not-found]

    graph = StateGraph(_PlanningState)
    graph.add_node("normalize", nodes.normalize)
    graph.add_node("generate_skeleton", nodes.generate_skeleton)
    graph.add_node("generate_structure_batch", nodes.generate_structure_batch)
    graph.add_node("validate_structure_batch", nodes.validate_structure_batch_node)
    graph.add_node("advance_structure_batch", nodes.advance_structure_batch)
    graph.add_node("generate_practice_batch", nodes.generate_practice_batch)
    graph.add_node("validate_practice_batch", nodes.validate_practice_batch_node)
    graph.add_node("advance_practice_batch", nodes.advance_practice_batch)
    graph.add_node("repair_batch", nodes.repair_batch)
    graph.add_node("merge_and_validate", nodes.merge_and_validate)
    graph.add_node("save_draft_projection", nodes.save_draft_projection)
    graph.add_node("record_failure", nodes.record_failure_node)

    graph.add_edge(START, "normalize")
    graph.add_conditional_edges("normalize", route_after_normalize,
                                {"generate_skeleton": "generate_skeleton", ROUTE_FAIL: "record_failure"})
    graph.add_conditional_edges("generate_skeleton", route_after_skeleton,
                                {"generate_structure_batch": "generate_structure_batch", ROUTE_FAIL: "record_failure"})
    graph.add_edge("generate_structure_batch", "validate_structure_batch")
    graph.add_conditional_edges("validate_structure_batch", route_after_structure_validate, {
        ROUTE_REPAIR: "repair_batch", ROUTE_ADVANCE_STRUCTURE: "advance_structure_batch",
        ROUTE_FAIL: "record_failure"})
    # The last structure batch advances too, then the phase transition is decided
    # from the completed index (never from a "is this the last batch?" shortcut),
    # so ``current_structure_index`` ends at the full batch count.
    graph.add_conditional_edges("advance_structure_batch", route_after_advance_structure, {
        ROUTE_GENERATE_STRUCTURE: "generate_structure_batch", ROUTE_GENERATE_PRACTICE: "generate_practice_batch"})
    graph.add_conditional_edges("repair_batch", route_after_batch_repair, {
        "validate_structure_batch": "validate_structure_batch",
        "validate_practice_batch": "validate_practice_batch",
        ROUTE_FAIL: "record_failure"})
    graph.add_edge("generate_practice_batch", "validate_practice_batch")
    graph.add_conditional_edges("validate_practice_batch", route_after_practice_validate, {
        ROUTE_REPAIR: "repair_batch", ROUTE_ADVANCE_PRACTICE: "advance_practice_batch",
        ROUTE_FAIL: "record_failure"})
    graph.add_conditional_edges("advance_practice_batch", route_after_advance_practice, {
        ROUTE_GENERATE_PRACTICE: "generate_practice_batch", ROUTE_MERGE: "merge_and_validate"})
    graph.add_conditional_edges("merge_and_validate", route_after_merge,
                                {ROUTE_DRAFT: "save_draft_projection", ROUTE_FAIL: "record_failure"})
    graph.add_edge("save_draft_projection", END)
    graph.add_edge("record_failure", END)
    return graph.compile(checkpointer=checkpointer)


def route_after_normalize(state: PlanningState) -> str:
    return ROUTE_FAIL if state.get("input_errors") else "generate_skeleton"


def route_after_skeleton(state: PlanningState) -> str:
    if state.get("generation_errors") or state.get("structure_errors"):
        return ROUTE_FAIL
    return "generate_structure_batch"


def route_after_structure_validate(state: PlanningState) -> str:
    if state.get("generation_errors"):
        return ROUTE_FAIL
    if not state.get("structure_errors"):
        return ROUTE_ADVANCE_STRUCTURE
    if int(state.get("repair_count", 0)) >= int(state["manifest"]["max_repairs"]):
        return ROUTE_FAIL
    return ROUTE_REPAIR


def route_after_batch_repair(state: PlanningState) -> str:
    """Revalidate the repaired batch kind; refuse failed or unknown targets."""
    if state.get("generation_errors"):
        return ROUTE_FAIL
    kind = (state.get("repair_target") or {}).get("kind")
    if kind == "structure":
        return "validate_structure_batch"
    if kind == "practice":
        return "validate_practice_batch"
    return ROUTE_FAIL


def route_after_advance_structure(state: PlanningState) -> str:
    """After a structure batch is committed, decide the next phase by index."""
    index = int(state.get("current_structure_index", 0))
    if index < int(state["manifest"]["structure_batches_count"]):
        return ROUTE_GENERATE_STRUCTURE
    return ROUTE_GENERATE_PRACTICE


def route_after_practice_validate(state: PlanningState) -> str:
    if state.get("generation_errors"):
        return ROUTE_FAIL
    if not state.get("structure_errors"):
        return ROUTE_ADVANCE_PRACTICE
    if int(state.get("repair_count", 0)) >= int(state["manifest"]["max_repairs"]):
        return ROUTE_FAIL
    return ROUTE_REPAIR


def route_after_advance_practice(state: PlanningState) -> str:
    """After a practice batch is committed, decide merge vs next batch by index."""
    index = int(state.get("current_practice_index", 0))
    if index < int(state["manifest"]["practice_batches_count"]):
        return ROUTE_GENERATE_PRACTICE
    return ROUTE_MERGE


def route_after_merge(state: PlanningState) -> str:
    if state.get("generation_errors") or state.get("structure_errors"):
        return ROUTE_FAIL
    return ROUTE_DRAFT


__all__ = [
    "DEFAULT_BUDGET",
    "DEFAULT_GENERIC_STAGE_COUNT",
    "MAX_REPAIR_TOTAL",
    "PHASE_DONE",
    "PHASE_OUTLINE",
    "PHASE_PRACTICE",
    "PHASE_STRUCTURE",
    "PHASE_VALIDATION",
    "PROGRESS_PHASES",
    "PROTOCOL_VERSION",
    "SHORT_GENERATION_VERSION",
    "allowed_attempt_keys",
    "attempt_key",
    "attempt_purpose",
    "attempt_stage",
    "budget_violation",
    "derive_progress",
    "output_budget_for",
    "build_short_planning_graph",
    "freeze_manifest",
    "manifest_is_intact",
    "merge_batches",
    "planned_output_budget",
    "practice_payload",
    "recursion_limit",
    "route_after_merge",
    "route_after_batch_repair",
    "route_after_normalize",
    "route_after_practice_validate",
    "route_after_skeleton",
    "route_after_structure_validate",
    "route_after_advance_practice",
    "route_after_advance_structure",
    "run_batched_planning_graph",
    "stage_spec",
    "structure_payload",
    "validate_practice_batch",
    "validate_structure_batch",
]
