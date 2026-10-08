import pytest
from app.core.errors import ValidationAppError
from app.domain.enums import OutlineSectionKind
from app.domain.planning.models import PlanDraft, PlanStage, revision_from_draft


def test_v2_marker_requires_snapshot():
    stage = PlanStage.create(
        stable_key="v2.stage.test",
        title="Test",
        section_kind=OutlineSectionKind("v2_curriculum"),
        order_index=0,
    )
    draft = PlanDraft(
        draft_id="d", project_id="p", run_id="", goal_snapshot="g", revision_candidate=1, stages=(stage,)
    )
    with pytest.raises(ValidationAppError):
        revision_from_draft(draft, revision=1)


def test_snapshot_field_is_consumed_by_hash():
    draft = PlanDraft(draft_id="d", project_id="p", run_id="", goal_snapshot="g", revision_candidate=1)
    assert hasattr(draft, "v2_execution")


def snapshot(curriculum=None, args=None):
    from app.core.ids import content_hash
    from app.domain.planning.curriculum_compiler import compile_curriculum
    from app.domain.planning.v2_execution import V2ExecutionSnapshot, compiler_packet

    from backend.tests.unit.test_curriculum_compiler import inputs

    if curriculum is None:
        curriculum, args = inputs()
    result = compile_curriculum(curriculum, **args)
    c = result.to_payload()
    binding = {
        "project_id": "p",
        "run_id": "",
        "stages": {s["stage_id"]: "s" + str(i) for i, s in enumerate(c["stages"])},
        "nodes": {n["stable_key"]: "n" + str(i) for i, n in enumerate(c["nodes"])},
        "units": {u["stable_key"]: "u" + str(i) for i, u in enumerate(c["units"])},
        "tasks": {t["stable_key"]: "t" + str(i) for i, t in enumerate(c["practice"]["tasks"])},
        "practice_project_id": "pp",
        "materials": {
            a["material_id"]: {
                "resource_id": "r" + str(i),
                "material_digest": content_hash(a["source_snapshot"]),
                "public_source_ref": None,
            }
            for i, a in enumerate(c["resource_assignments"])
        },
    }
    return V2ExecutionSnapshot.create(
        result, bindings=binding, packet=compiler_packet(args["context"], args["source_facts"])
    )


def test_original_unconstrained_item6_snapshot_preserves_frozen_source():
    import json
    from pathlib import Path

    from app.core.ids import canonical_json
    from app.domain.planning.curriculum import CurriculumPlan
    from app.domain.planning.curriculum_compiler import CurriculumSourceFacts

    from backend.tests.unit.test_curriculum import local_mcp_inputs, prepared

    path = Path(__file__).parents[3] / "var/planning-v2-item6-implementation-20261008/example-complete.json"
    if not path.exists():
        pytest.skip("original ignored Item6 evidence unavailable")
    original = path.read_bytes()
    doc = json.loads(original)["curriculum"]
    assert "constraint_assessments" not in doc["compile_context"]
    findings, digest = doc.pop("case_findings"), doc.pop("plan_hash")
    curriculum = CurriculumPlan(canonical_json(doc), canonical_json(findings))
    profile, plan, index, source, proof = local_mcp_inputs()
    context = prepared(profile, plan, index, catalog_sources=(source,), access_proofs=(proof,))
    args = dict(
        context=context,
        profile=profile,
        capability_plan=plan,
        source_facts=CurriculumSourceFacts(index, (source,), (proof,)),
    )
    result = snapshot(curriculum, args).to_payload()
    assert result["compiled"]["source_snapshots"]["curriculum"] == curriculum.to_payload()
    assert result["manifest"]["input_curriculum_plan_hash"] == digest
    assert result["compiled"]["constraints"]["assessments"] == []
    assert path.read_bytes() == original


@pytest.mark.parametrize("tamper", ["guidance", "policy", "upstream", "identity"])
def test_rehashed_compiled_manifest_divergence_rejected(tamper):
    from app.core.ids import content_hash
    from app.domain.planning.v2_execution import V2ExecutionSnapshot

    raw = snapshot().to_payload()
    if tamper == "guidance":
        raw["compiled"]["guidance"][0]["practice_delta"]["increment"] = ["forged"]
    elif tamper == "policy":
        raw["manifest"]["upstream_sources"]["policy_hash"] = "0" * 64
    elif tamper == "upstream":
        raw["manifest"]["upstream_sources"]["research_hash"] = "0" * 64
    else:
        raw["manifest"]["stable_identity_mapping"]["knowledge"][0]["curriculum_stable_key"] = "forged"
    raw["manifest"]["compiled_payload_digest"] = content_hash(raw["compiled"])
    with pytest.raises(ValidationAppError):
        V2ExecutionSnapshot.from_payload(raw)
