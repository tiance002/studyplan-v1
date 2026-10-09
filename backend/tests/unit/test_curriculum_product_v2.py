"""Versioned curriculum facts; fixtures prove bindings, not teaching quality."""
from copy import deepcopy
from dataclasses import replace

import pytest
from app.core.errors import ValidationAppError
from app.domain.planning.content_coverage import CoverageEvaluator, ReviewedContentIndex
from app.domain.planning.curriculum import (
    prepare_curriculum,
    valid_curriculum_input,
    validate_curriculum_output,
)
from app.domain.planning.curriculum_compiler import CurriculumSourceFacts, compile_curriculum
from app.domain.planning.resource_gaps import extract

from backend.tests.unit.test_capability_planning import cap, plan, profile, wire
from backend.tests.unit.test_curriculum import output
from backend.tests.unit.test_resource_research import run
from backend.tests.unit.test_v2_execution_persistence import snapshot

SCOPE = "工具仅操作用户明确允许的本地任务范围"
CASES = ("allowed", "unauthorized", "out_of_scope", "invalid_parameters", "execution_failure", "json_protection")


def fixture(*, constraints=(), recommended=False, semantics_version=2):
    p = replace(profile("学习LLM与MCP", constraints=constraints), project_context="原CLI和JSON任务文件")
    items = [cap(p, "llm.api")]
    if SCOPE in constraints:
        items.append(cap(p, "tool.calling"))
    if recommended:
        items.append(cap(p, "mcp", learning_requirement="recommended", project_usage="excluded"))
    frozen = plan(p, wire(p, *items))
    index = ReviewedContentIndex("empty", (), (), ())
    coverage = CoverageEvaluator().evaluate(frozen, index)
    if SCOPE in constraints and semantics_version == 2:
        from backend.tests.unit.test_research_comparison_v2 import execute
        research, *_ = execute(values=(p, frozen, coverage, extract(frozen, coverage)))
    else:
        research, *_ = run((p, frozen, coverage, extract(frozen, coverage)))
    ctx = prepare_curriculum(p, frozen, coverage, research, index, semantics_version=semantics_version)
    raw = output(ctx)
    if semantics_version == 2:
        raw.update(schema_version=2, semantics_version=2, permission_obligations=[])
    return ctx, raw, dict(context=ctx, profile=p, capability_plan=frozen, source_facts=CurriculumSourceFacts(index))


def arrange_scope(raw, ctx):
    stage = next(s for s in raw["stages"] if "tool.calling" in s["capability_ids"])
    task = stage["tasks"][0]
    task.update(title="给现有待办CLI增加授权边界与受限工具派发", goal="用户先授权任务ID与操作列表；未授权默认拒绝，校验参数并保留JSON文件",
        in_scope=["现有CLI与JSON任务文件", "用户显式允许的任务ID和操作", "输入合同与拒绝路径"],
        out_scope=["未授权任务、任意本地文件与网络操作", "重建演示项目"])
    checks = (
        "授权记录列明允许的任务ID和操作；有效参数仅改变获准任务，其他JSON字段保持原样",
        "没有授权记录时拒绝执行，返回未授权错误，JSON字节不变",
        "已授权任务A时访问任务B被拒绝，输出越权错误且JSON字节不变",
        "缺少任务ID或参数类型非法时输入校验拒绝，不调用工具、不写JSON",
        "模拟工具执行失败，CLI返回可检查错误，不产生部分JSON写入",
        "逐例比较执行前后JSON；拒绝和失败路径完全不变，成功只修改授权任务字段",
    )
    task["acceptance"] = [{"text": text, "outcome_refs": task["outcome_refs"]} for text in checks]
    refs = [task["stable_key"] + ".acceptance." + str(i) for i in range(6)]
    c = ctx.to_payload()["constraints"][0]
    raw["permission_obligations"] = [{"constraint_ref": c["constraint_id"], "source_refs": c["source_refs"],
        "project_context_hash": ctx.to_payload()["profile_context"]["project_context_hash"],
        "task_ref": task["stable_key"], "outcome_refs": task["outcome_refs"], "acceptance_refs": refs,
        "authorization_before_execution": True, "default_deny": True, "allowed_scope": "user_authorized_local_tasks",
        "input_validation": True, "cases": [{"kind": kind, "acceptance_ref": refs[i], "artifact": kind + "输入输出及文件差异记录"}
                                               for i, kind in enumerate(CASES)],
        "practice_artifact": "用户授权记录、六例验收日志、执行前后JSON内容差异"}]
    raw["status"] = "complete"
    return raw


def test_v2_permission_planning_has_no_runtime_grant_and_survives_snapshot():
    ctx, raw, args = fixture(constraints=(SCOPE,))
    curriculum = validate_curriculum_output(arrange_scope(raw, ctx), ctx.to_payload())
    result = compile_curriculum(curriculum, **args).to_payload()
    assert result["contract_version"] == "CompiledCurriculumV2"
    assessment = result["constraints"]["assessments"][0]
    assert assessment["planning_status"] == "arranged" and assessment["runtime_status"] == "unverified"
    assert result["constraints"]["permission_obligations"] == curriculum.to_payload()["permission_obligations"]
    saved = snapshot(curriculum, args).to_payload()
    assert saved["version"] == "V2ExecutionSnapshotV2"
    assert saved["compiled"] == result


@pytest.mark.parametrize("tamper", ["missing", "constraint", "sources", "project", "task", "outcome", "acceptance", "case",
                                   "deny", "authorization", "scope", "input", "generic", "assertion"])
def test_permission_binding_counterexamples_rejected(tamper):
    ctx, raw, _ = fixture(constraints=(SCOPE,))
    arrange_scope(raw, ctx)
    item = raw["permission_obligations"][0]
    if tamper == "missing":
        raw["permission_obligations"] = []
    elif tamper == "constraint":
        item["constraint_ref"] = "invented"
    elif tamper == "sources":
        item["source_refs"] = ["goal.target"]
    elif tamper == "project":
        item["project_context_hash"] = "a" * 64
    elif tamper == "task":
        item["task_ref"] = "task_unknown"
    elif tamper == "outcome":
        item["outcome_refs"] = ["mcp.roles"]
    elif tamper == "acceptance":
        item["cases"][0]["acceptance_ref"] = "task_unknown.acceptance.0"
    elif tamper == "case":
        item["cases"].pop()
    elif tamper == "generic":
        for case in item["cases"]:
            case["artifact"] = "承诺通过"
    elif tamper == "assertion":
        item["runtime_status"] = "verified"
    else:
        field = {"deny": "default_deny", "authorization": "authorization_before_execution", "scope": "allowed_scope",
                 "input": "input_validation"}[tamper]
        item[field] = "all_local_files" if tamper == "scope" else False
    with pytest.raises(ValidationAppError):
        validate_curriculum_output(raw, ctx.to_payload())


def test_unselected_recommended_unresolved_visible_complete_v2_only():
    ctx, raw, args = fixture(recommended=True)
    assert raw["unresolved"]
    optional = raw["stages"].pop()
    optional_refs = set(optional["outcome_refs"])
    raw["carrier"]["final_artifact"]["acceptance"][0]["outcome_refs"] = [r for r in raw["carrier"]["final_artifact"]["acceptance"][0]["outcome_refs"]
                                                                        if r not in optional_refs]
    raw["status"] = "complete"
    curriculum = validate_curriculum_output(raw, ctx.to_payload())
    result = snapshot(curriculum, args).to_payload()
    assert result["compiled"]["unresolved"] == raw["unresolved"]
    assert result["compiled"]["source_snapshots"]["curriculum_context"]["capabilities"][1]["importance"] == "recommended"
    legacy_ctx, legacy, _ = fixture(recommended=True, semantics_version=1)
    legacy["stages"] = deepcopy(raw["stages"])
    legacy["carrier"] = deepcopy(raw["carrier"])
    legacy["status"] = "complete"
    with pytest.raises(ValidationAppError):
        validate_curriculum_output(legacy, legacy_ctx.to_payload())


def test_staged_recommended_unresolved_remains_blocking():
    ctx, raw, _ = fixture(recommended=True)
    raw["status"] = "complete"
    with pytest.raises(ValidationAppError):
        validate_curriculum_output(raw, ctx.to_payload())


def test_version_markers_cannot_upgrade_legacy_input():
    ctx, raw, _ = fixture(semantics_version=1)
    assert "semantics_version" not in ctx.to_payload()
    assert valid_curriculum_input(ctx.to_payload(), "CurriculumPlanV1")
    assert not valid_curriculum_input(ctx.to_payload(), "CurriculumPlanV2")
    raw.update(schema_version=2, semantics_version=2, permission_obligations=[])
    with pytest.raises(ValidationAppError):
        validate_curriculum_output(raw, ctx.to_payload())


@pytest.mark.parametrize("constraint", ["只读，不允许代码修改", "禁止联网", "私有内容不可外发"])
def test_other_constraint_cannot_be_released_by_v2_scope_plan(constraint):
    ctx, raw, _ = fixture(constraints=(SCOPE, constraint))
    arrange_scope(raw, ctx)
    with pytest.raises(ValidationAppError):
        validate_curriculum_output(raw, ctx.to_payload())
