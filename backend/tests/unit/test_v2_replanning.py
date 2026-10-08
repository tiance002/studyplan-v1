"""Item8 bounded changes reuse the frozen compiler and exact lineage."""

from dataclasses import replace

import pytest
from app.core.errors import ValidationAppError
from app.domain.enums import OutlineSectionKind
from app.domain.planning.models import PlanStage
from app.domain.planning.revisions import LocalStageEdit, classify_change, local_candidate
from app.domain.planning.v2_execution import V2ExecutionSnapshot, compiler_packet

from backend.tests.unit.test_curriculum_compiler import inputs


def snapshot(*, systematic=False, prepared=None):
    from app.domain.planning.curriculum_compiler import compile_curriculum

    curriculum, args = prepared or inputs(systematic=systematic)
    result = compile_curriculum(curriculum, **args)
    c = result.to_payload()
    bindings = {
        "project_id": "project", "run_id": "", "practice_project_id": "practice",
        "stages": {s["stage_id"]: "db_" + s["stage_id"] for s in c["stages"]},
        "nodes": {n["stable_key"]: "db_" + n["stable_key"] for n in c["nodes"]},
        "units": {u["stable_key"]: "db_" + u["stable_key"] for u in c["units"]},
        "tasks": {t["stable_key"]: "db_" + t["stable_key"] for t in c["practice"]["tasks"]},
        "materials": {},
    }
    from app.core.ids import content_hash
    for a in c["resource_assignments"]:
        bindings["materials"][a["material_id"]] = {
            "material_digest": content_hash(a["source_snapshot"]), "resource_id": "resource",
            "public_source_ref": "", "public_source_version": 0,
        }
    frozen = V2ExecutionSnapshot.create(result, bindings=bindings, packet=compiler_packet(args["context"], args["source_facts"]))
    stages = tuple(PlanStage(bindings["stages"][s["stage_id"]], s["stable_key"], s["title"],
        OutlineSectionKind.V2_CURRICULUM, s["order_index"], s["what_to_learn"]) for s in c["stages"])
    return frozen, stages


def test_local_description_recompiles_current_hash_and_keeps_frozen_authorities():
    frozen, stages = snapshot()
    candidate = local_candidate(frozen, stages, (LocalStageEdit(stages[0].stage_id, what_to_learn="检查并解释本阶段全部目标"),))
    updated = frozen.recompile_local(candidate)
    before, after = frozen.to_payload(), updated.to_payload()
    assert before["manifest"] != after["manifest"]
    assert before["original_curriculum_hash"] == after["original_curriculum_hash"]
    for field in ("goal_requirement_profile", "capability_plan"):
        assert before["compiled"]["source_snapshots"][field] == after["compiled"]["source_snapshots"][field]
    assert before["compiled"]["resource_assignments"] == after["compiled"]["resource_assignments"]


def test_local_reorder_uses_real_prerequisite_validator():
    frozen, stages = snapshot(systematic=True)
    order = (stages[2].stage_id, stages[1].stage_id, stages[0].stage_id)
    candidate = local_candidate(frozen, stages, (), stage_order=order)
    with pytest.raises(ValidationAppError):
        frozen.recompile_local(candidate)
    legal = (stages[0].stage_id, stages[2].stage_id, stages[1].stage_id)
    updated = frozen.recompile_local(local_candidate(frozen, stages, (), stage_order=legal))
    assert [s["stage_id"] for s in updated.to_payload()["compiled"]["stages"]] == [
        "stage_llm_api", "stage_tool_calling", "stage_mcp"]


@pytest.mark.parametrize("kind", ["started", "removed", "duplicate", "unknown"])
def test_local_protection_rejects_structural_or_started_edits(kind):
    frozen, stages = snapshot()
    edits = (LocalStageEdit(stages[0].stage_id, title="新说明"),)
    kw = {"protected_stage_ids": {stages[0].stage_id}} if kind == "started" else {}
    if kind == "removed":
        kw["stage_order"] = ()
    elif kind == "duplicate":
        edits += edits
    elif kind == "unknown":
        edits = (replace(edits[0], stage_id="not-owned"),)
    with pytest.raises(ValidationAppError):
        local_candidate(frozen, stages, edits, **kw)


def test_unstructured_request_keeps_clarification_and_never_accepts_client_semantic_flag():
    assert classify_change(change_text="只插入RAG项目，不改变目标") == {
        "status": "needs_clarification", "clarification_questions": ["请明确是调整未来阶段的说明或顺序，还是提交新的学习目标。"]}


def test_unknown_domain_local_requires_original_trusted_approval_without_new_verification():
    from app.domain.planning.curriculum import prepare_curriculum, validate_curriculum_output
    from app.domain.planning.curriculum_compiler import CurriculumSourceFacts

    from backend.tests.unit.test_curriculum import output
    from backend.tests.unit.test_domain_verification import researched_domain
    p, capabilities, approval, index, coverage, _, research, *_ = researched_domain()
    context = prepare_curriculum(p, capabilities, coverage, research, index, domain_approvals=(approval,))
    curriculum = validate_curriculum_output(output(context), context.to_payload(), domain_approvals=(approval,))
    args = dict(context=context, profile=p, capability_plan=capabilities, source_facts=CurriculumSourceFacts(index))
    frozen, stages = snapshot(prepared=(curriculum, args))
    candidate = local_candidate(frozen, stages, (LocalStageEdit(stages[0].stage_id, title="已审核专项的合法说明"),))
    with pytest.raises(ValidationAppError):
        frozen.recompile_local(candidate)
    updated = frozen.recompile_local(candidate, domain_approvals=(approval,))
    assert updated.to_payload()["compiled"]["stages"][0]["title"] == "已审核专项的合法说明"
    assert updated.to_payload()["compiled"]["source_snapshots"]["capability_plan"] == frozen.to_payload()["compiled"]["source_snapshots"]["capability_plan"]
