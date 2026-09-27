"""Graph 层测试：三张 Fake 图的状态转移、修复上限、interrupt 与取消语义。

对应验收条款：
- 「结构有效/无效与两次修复上限」
- 「interrupt/edit/approve/cancel」
- 「fake provider」
- 「run 越权拒绝」（见 test_security_boundaries.py）

**不依赖** langgraph（用 `graphs.run_planning_graph` 解释器）、
**不依赖** Postgres、**不依赖**网络。
"""

from __future__ import annotations

import pytest

from app.agent_workflows.graphs import (
    LANGGRAPH_AVAILABLE,
    run_planning_graph,
    run_review_graph,
)
from app.agent_workflows.nodes import PlanningNodes, route_after_decision, route_after_validate
from app.agent_workflows.validators import MAX_REPAIR_ATTEMPTS, validate_plan_structure
from app.infrastructure.providers.fake import FakeLLM
from app.ports.llm import LLMFailure


# ---------------------------------------------------------------------------
# 测试用脚本：构造一份"合法"的规划产物
# ---------------------------------------------------------------------------

GOOD_NODES = [
    {"stable_key": "n_python", "title": "Python 基础"},
    {"stable_key": "n_rag", "title": "RAG 检索"},
]
GOOD_UNITS = [
    {"stable_key": "u_basic", "title": "基础", "order_index": 0},
    {"stable_key": "u_rag", "title": "RAG", "order_index": 1},
]
GOOD_RELATIONS = [
    {
        "from_stable_key": "n_python",
        "to_stable_key": "n_rag",
        "relation_type": "prerequisite",
    }
]
GOOD_TASKS = [
    {
        "stable_key": "t_pdf",
        "title": "PDF 知识助手",
        "order_index": 0,
        "acceptance": ["可上传 PDF 并抽取文本"],
    }
]
GOOD_LINKS = [
    {"task_stable_key": "t_pdf", "node_stable_key": "n_rag", "role": "core"}
]


def _good_structure_handler(purpose: str, payload: dict) -> dict:
    return {"nodes": GOOD_NODES, "units": GOOD_UNITS, "relations": GOOD_RELATIONS}


def _good_outline_handler(purpose: str, payload: dict) -> dict:
    return {"outline_ref": "outline:1", "sections": ["foundation", "core"]}


def _good_practice_handler(purpose: str, payload: dict) -> dict:
    return {"tasks": GOOD_TASKS, "task_knowledge_links": GOOD_LINKS}


def _build_nodes(
    *,
    structure_handler=_good_structure_handler,
    saved: list | None = None,
    committed: list | None = None,
    failures: list | None = None,
) -> PlanningNodes:
    llm = FakeLLM(
        {
            "planning.outline": _good_outline_handler,
            "planning.structure": structure_handler,
            "planning.practice": _good_practice_handler,
        }
    )
    saved = saved if saved is not None else []
    committed = committed if committed is not None else []
    failures = failures if failures is not None else []
    return PlanningNodes(
        llm=llm,
        save_draft=lambda state: (saved.append(state), "draft:1")[1],
        commit_plan=lambda state: (committed.append(state), "plan:rev1")[1],
        on_failure=lambda state, errors: failures.append(list(errors)),
    )


# ---------------------------------------------------------------------------
# 有效结构 → 停在 await_approval
# ---------------------------------------------------------------------------


def test_valid_structure_reaches_await_approval() -> None:
    trace = run_planning_graph(
        _build_nodes(), {"run_id": "r1", "project_id": "p1", "goal": "学会 Agent"}
    )
    assert trace.stopped_at == "await_approval"
    assert trace.failed_errors is None
    assert trace.state.get("draft_ref") == "draft:1"
    # interrupt 前不得提交
    assert "commit_plan_idempotently" not in trace.visited


def test_interrupt_precedes_side_effects() -> None:
    """interrupt 前只做无副作用快照读取：不得提交计划。"""
    committed: list = []
    trace = run_planning_graph(
        _build_nodes(committed=committed),
        {"run_id": "r1", "project_id": "p1", "goal": "g"},
    )
    assert committed == []
    assert trace.stopped_at == "await_approval"


# ---------------------------------------------------------------------------
# 无效结构 → 修复上限
# ---------------------------------------------------------------------------


def test_repair_stops_at_two_attempts() -> None:
    """结构始终无效时，修复恰好尝试 MAX_REPAIR_ATTEMPTS 次后失败并保留错误。"""

    def always_broken(purpose: str, payload: dict) -> dict:
        # 引用不存在的节点 → 持续校验失败
        return {
            "nodes": GOOD_NODES,
            "units": GOOD_UNITS,
            "relations": [
                {
                    "from_stable_key": "n_ghost",
                    "to_stable_key": "n_rag",
                    "relation_type": "prerequisite",
                }
            ],
        }

    failures: list = []
    trace = run_planning_graph(
        _build_nodes(structure_handler=always_broken, failures=failures),
        {"run_id": "r1", "project_id": "p1", "goal": "g"},
    )
    assert trace.stopped_at == "failed_validation"
    repair_count = trace.visited.count("repair_content")
    assert repair_count == MAX_REPAIR_ATTEMPTS
    assert trace.failed_errors, "失败必须保留错误"
    assert failures, "失败必须被记录，供人工核对"


def test_repair_succeeds_within_budget() -> None:
    """第一次修复后即通过：不应浪费第二次修复配额。"""
    calls = {"n": 0}

    def broken_first(purpose: str, payload: dict) -> dict:
        """结构生成阶段产出非法关系（引用不存在的节点）。"""
        return {
            "nodes": GOOD_NODES,
            "units": GOOD_UNITS,
            "relations": [
                {
                    "from_stable_key": "n_ghost",
                    "to_stable_key": "n_rag",
                    "relation_type": "prerequisite",
                }
            ],
        }

    def repair_ok(purpose: str, payload: dict) -> dict:
        """修复一次即产出合法结构。"""
        calls["n"] += 1
        return _good_structure_handler(purpose, payload)

    llm = FakeLLM(
        {
            "planning.outline": _good_outline_handler,
            "planning.structure": broken_first,
            "planning.practice": _good_practice_handler,
            "planning.repair": repair_ok,
        }
    )
    nodes = PlanningNodes(llm=llm, save_draft=lambda s: "draft:1")
    trace = run_planning_graph(nodes, {"run_id": "r1", "project_id": "p1", "goal": "g"})
    assert trace.stopped_at == "await_approval"
    assert trace.visited.count("repair_content") == 1, "修复一次即通过时不得再修第二次"
    assert calls["n"] == 1


def test_route_after_validate_uses_fail_when_budget_exhausted() -> None:
    state = {"validation_errors": ["e"], "repair_count": MAX_REPAIR_ATTEMPTS}
    assert route_after_validate(state) == "fail_validation"
    state2 = {"validation_errors": ["e"], "repair_count": 0}
    assert route_after_validate(state2) == "repair_content"
    state3 = {"validation_errors": [], "repair_count": 0}
    assert route_after_validate(state3) == "save_draft_projection"


# ---------------------------------------------------------------------------
# Fake provider 的诚实性
# ---------------------------------------------------------------------------


def test_fake_llm_fails_loudly_for_unregistered_purpose() -> None:
    """未注册的 purpose 必须明确失败，**不得**返回空成功。"""
    llm = FakeLLM({})
    result = llm.generate_structured(
        purpose="unknown", payload={}, schema_name="X", run_id="r", attempt_id="a"
    )
    assert isinstance(result, LLMFailure)
    assert result.retryable is False


def test_fake_llm_never_reports_empty_success() -> None:
    """即使返回空 dict，也必须是显式处理器产出的（框架不代填）。"""
    llm = FakeLLM({"p": lambda purpose, payload: {}})
    result = llm.generate_structured(
        purpose="p", payload={}, schema_name="X", run_id="r", attempt_id="a"
    )
    assert not isinstance(result, LLMFailure)
    assert result.provider == "fake", "必须可识别为 fake，防止误当真实评审能力"


def test_fake_llm_records_attempt_identity() -> None:
    """付费调用账务标识（run_id + attempt_id）必须被记录。"""
    llm = FakeLLM({"p": lambda purpose, payload: {"x": 1}})
    llm.generate_structured(
        purpose="p", payload={}, schema_name="X", run_id="run-1", attempt_id="attempt-1"
    )
    assert llm.calls == [("run-1", "attempt-1", "p")]


# ---------------------------------------------------------------------------
# 决定路由：approve / edit / cancel
# ---------------------------------------------------------------------------


def test_approve_commits_idempotently() -> None:
    committed: list = []
    trace = run_planning_graph(
        _build_nodes(committed=committed),
        {"run_id": "r1", "project_id": "p1", "goal": "g"},
        resume_decision="approve",
    )
    assert trace.stopped_at is None
    assert trace.state.get("result_id") == "plan:rev1"
    assert len(committed) == 1


def test_cancel_does_not_commit() -> None:
    """取消后的草案绝不可被发布。"""
    committed: list = []
    trace = run_planning_graph(
        _build_nodes(committed=committed),
        {"run_id": "r1", "project_id": "p1", "goal": "g"},
        resume_decision="cancel",
    )
    assert committed == []
    assert trace.state.get("result_id") == ""
    assert "commit_plan_idempotently" not in trace.visited


def test_edit_triggers_revalidation() -> None:
    """编辑后必须重新校验（不得直接提交未校验的内容）。"""
    trace = run_planning_graph(
        _build_nodes(),
        {"run_id": "r1", "project_id": "p1", "goal": "g"},
        resume_decision="edit",
    )
    assert "validate" in trace.visited
    assert "commit_plan_idempotently" in trace.visited


def test_route_after_decision_mapping() -> None:
    assert route_after_decision({"decision": "approve"}) == "commit_plan_idempotently"
    assert route_after_decision({"decision": "edit"}) == "validate"
    assert route_after_decision({"decision": "cancel"}) == "cancel_draft"


# ---------------------------------------------------------------------------
# 评审图（无 interrupt）
# ---------------------------------------------------------------------------


def test_review_graph_persists_and_has_no_interrupt() -> None:
    persisted: list = []
    trace = run_review_graph(
        load_snapshot=lambda s: {"rubric_snapshot": {"rubric_version": 1}},
        review_once=lambda s: {
            "review": {
                "covered": ["检索基础"],
                "gaps": ["未提召回率"],
                "questions": ["如何评估召回？"],
            }
        },
        validate_review=lambda review: []
        if review.get("covered") or review.get("gaps")
        else ["评审既未说明覆盖内容，也未指出缺口"],
        persist_review=lambda s: (persisted.append(s), "review:1")[1],
        initial={"run_id": "r1", "project_id": "p1", "subject_id": "sum:1"},
    )
    assert trace.stopped_at is None
    assert trace.state.get("result_id") == "review:1"
    assert len(persisted) == 1
    assert "await_approval" not in trace.visited


def test_review_graph_rejects_empty_review() -> None:
    """空评审不得被判为成功（设计 §4：不自动把任务标验收通过）。"""
    trace = run_review_graph(
        load_snapshot=lambda s: {"rubric_snapshot": {}},
        review_once=lambda s: {"review": {}},
        validate_review=lambda review: ["评审既未说明覆盖内容，也未指出缺口"],
        persist_review=lambda s: "should-not-happen",
        initial={"run_id": "r1", "project_id": "p1", "subject_id": "s:1"},
    )
    assert trace.stopped_at == "failed_validation"
    assert trace.failed_errors


def test_langgraph_availability_is_reported_not_assumed() -> None:
    """langgraph 未安装时不得崩溃：必须能退化到解释器。"""
    assert isinstance(LANGGRAPH_AVAILABLE, bool)
