"""Graph 层测试：三张 Fake 图的状态转移、修复上限、interrupt 与取消语义。

对应验收条款：
- 「结构有效/无效与两次修复上限」
- 「interrupt/edit/approve/cancel」
- 「fake provider」
- 「run 越权拒绝」（见 test_security_boundaries.py）

**不依赖** langgraph（用 `graphs.run_planning_graph` 解释器）、
**不依赖** Postgres、**不依赖**网络。

解释器是**快速单元测试工具**；真实 StateGraph 的行为断言见
``backend/tests/integration/test_real_langgraph.py``。两者共用同一批
测试场景，出现分歧时**以真实 Graph 为准**。
"""

from __future__ import annotations

from app.agent_workflows.graphs import (
    LANGGRAPH_AVAILABLE,
    run_planning_graph,
    run_review_graph,
)
from app.agent_workflows.nodes import (
    PlanningNodes,
    route_after_decision,
    route_after_generate,
    route_after_normalize,
    route_after_validate,
)
from app.agent_workflows.validators import MAX_REPAIR_ATTEMPTS
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
    edits: list | None = None,
    cancelled: list | None = None,
    edit_result: dict | None = None,
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
    edits = edits if edits is not None else []
    cancelled = cancelled if cancelled is not None else []
    return PlanningNodes(
        llm=llm,
        save_draft=lambda state: (saved.append(state), f"draft:{len(saved)}")[1],
        commit_plan=lambda state: (committed.append(state), "plan:rev1")[1],
        # 正式契约：返回编辑后的草案结构（mapping），至少含 draft_ref。
        apply_edit=lambda state: (
            edits.append(state),
            edit_result
            if edit_result is not None
            else {"draft_ref": f"draft:edited:{len(edits)}"},
        )[1],
        cancel_draft=lambda state: cancelled.append(state),
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
    assert trace.state.get("structure_errors") == []
    assert trace.state.get("generation_errors") == []
    assert trace.state.get("input_errors") == []


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
# 2.1 错误通道：input / generation / structure 互不覆盖
# ---------------------------------------------------------------------------


def test_empty_goal_fails_without_calling_model() -> None:
    """空学习目标必须直接失败，**不得继续调用模型**。"""
    llm = FakeLLM({})  # 未注册任何 handler：一旦被调用就会返回 LLMFailure
    nodes = PlanningNodes(llm=llm, on_failure=lambda s, e: None)
    trace = run_planning_graph(nodes, {"run_id": "r1", "project_id": "p1", "goal": "  "})
    assert trace.stopped_at == "failed_validation"
    assert llm.calls == [], "空目标不得产生任何模型调用"
    assert any("不能为空" in e for e in (trace.failed_errors or []))
    # 不得进入生成节点
    assert "generate_outline" not in trace.visited


def test_generation_failure_not_masked_by_empty_structure() -> None:
    """模型生成失败不得被后续空结构校验覆盖成"看起来有效"。"""

    def failing_structure(purpose: str, payload: dict) -> dict:
        raise RuntimeError("boom")

    trace = run_planning_graph(
        _build_nodes(structure_handler=failing_structure),
        {"run_id": "r1", "project_id": "p1", "goal": "g"},
    )
    assert trace.stopped_at == "failed_validation"
    # generation 错误必须保留，且结构错误不得"洗掉"它
    assert trace.state.get("generation_errors"), "生成失败必须被保留"
    assert any("生成失败" in e for e in (trace.failed_errors or []))


def test_missing_outline_fails_validation() -> None:
    """空纲要不得被标记为有效计划。"""

    def empty_outline(purpose: str, payload: dict) -> dict:
        return {}

    llm = FakeLLM(
        {
            "planning.outline": empty_outline,
            "planning.structure": _good_structure_handler,
            "planning.practice": _good_practice_handler,
        }
    )
    nodes = PlanningNodes(llm=llm, on_failure=lambda s, e: None)
    trace = run_planning_graph(nodes, {"run_id": "r1", "project_id": "p1", "goal": "g"})
    assert trace.stopped_at == "failed_validation"
    assert trace.state.get("generation_errors")


def test_empty_nodes_fails_validation() -> None:
    """空知识节点不得被标记为有效计划。"""

    def empty_structure(purpose: str, payload: dict) -> dict:
        return {"nodes": [], "units": [], "relations": []}

    trace = run_planning_graph(
        _build_nodes(structure_handler=empty_structure),
        {"run_id": "r1", "project_id": "p1", "goal": "g"},
    )
    assert trace.stopped_at == "failed_validation"
    assert trace.state.get("generation_errors")


def test_repair_clears_old_structure_errors() -> None:
    """修复成功后**旧结构错误必须消失**（覆盖语义，不是累加）。"""

    def broken_first(purpose: str, payload: dict) -> dict:
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

    llm = FakeLLM(
        {
            "planning.outline": _good_outline_handler,
            "planning.structure": broken_first,
            "planning.practice": _good_practice_handler,
            "planning.repair": _good_structure_handler,
        }
    )
    nodes = PlanningNodes(llm=llm, save_draft=lambda s: "draft:1")
    trace = run_planning_graph(nodes, {"run_id": "r1", "project_id": "p1", "goal": "g"})
    assert trace.stopped_at == "await_approval", "第一次修复成功后必须能进入待确认"
    assert trace.state.get("structure_errors") == [], "旧结构错误必须被清除"
    assert trace.state.get("validation_errors") == [], "聚合视图也必须干净"


def test_history_does_not_affect_latest_validation() -> None:
    """历史错误不得影响最新校验结果。"""

    def broken_first(purpose: str, payload: dict) -> dict:
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

    llm = FakeLLM(
        {
            "planning.outline": _good_outline_handler,
            "planning.structure": broken_first,
            "planning.practice": _good_practice_handler,
            "planning.repair": _good_structure_handler,
        }
    )
    nodes = PlanningNodes(llm=llm, save_draft=lambda s: "draft:1")
    trace = run_planning_graph(nodes, {"run_id": "r1", "project_id": "p1", "goal": "g"})
    assert trace.stopped_at == "await_approval"
    # 最新校验为空 => 路由必须判定为通过
    assert route_after_validate(trace.state) == "save_draft_projection"


# ---------------------------------------------------------------------------
# 无效结构 → 修复上限
# ---------------------------------------------------------------------------


def test_repair_stops_at_two_attempts() -> None:
    """结构始终无效时，修复恰好尝试 MAX_REPAIR_ATTEMPTS 次后失败并保留错误。

    修复**成功返回**但结构依旧非法（引用不存在的节点）=> 校验持续失败 =>
    用完 2 次配额后失败。这验证的是"配额上限"，不是"模型失败"。
    """

    def broken(purpose: str, payload: dict) -> dict:
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

    llm = FakeLLM(
        {
            "planning.outline": _good_outline_handler,
            "planning.structure": broken,
            "planning.practice": _good_practice_handler,
            "planning.repair": broken,  # 修复也返回同样的非法结构
        }
    )
    failures: list = []
    nodes = PlanningNodes(
        llm=llm,
        on_failure=lambda s, e: failures.append(list(e)),
    )
    trace = run_planning_graph(nodes, {"run_id": "r1", "project_id": "p1", "goal": "g"})
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
    state = {"structure_errors": ["e"], "repair_count": MAX_REPAIR_ATTEMPTS}
    assert route_after_validate(state) == "fail_validation"
    state2 = {"structure_errors": ["e"], "repair_count": 0}
    assert route_after_validate(state2) == "repair_content"
    state3 = {"structure_errors": [], "repair_count": 0}
    assert route_after_validate(state3) == "save_draft_projection"


def test_route_prioritizes_generation_errors_over_empty_structure() -> None:
    """generation 错误必须先于"结构为空即通过"判定。"""
    state = {"generation_errors": ["boom"], "structure_errors": [], "repair_count": 0}
    assert route_after_validate(state) == "fail_validation"


def test_route_after_normalize_and_generate() -> None:
    assert route_after_normalize({"input_errors": []}) == "generate_outline"
    assert route_after_normalize({"input_errors": ["x"]}) == "fail_validation"
    assert route_after_generate({"generation_errors": []}) == "validate"
    assert route_after_generate({"generation_errors": ["x"]}) == "fail_validation"


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


def test_unknown_result_paid_call_is_not_redistributed() -> None:
    """结果未知的付费调用不得自动重新派发（repair 失败不自动重试）。

    真实实现里 retryable=False；这里断言图在 repair 失败后**立即失败**，
    而不是继续发起第二次同 attempt 的调用。
    """
    calls: list[str] = []

    def failing_repair(purpose: str, payload: dict) -> dict:
        calls.append("repair")
        raise RuntimeError("uncertain upstream")

    def broken_structure(purpose: str, payload: dict) -> dict:
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

    llm = FakeLLM(
        {
            "planning.outline": _good_outline_handler,
            "planning.structure": broken_structure,
            "planning.practice": _good_practice_handler,
            "planning.repair": failing_repair,
        }
    )
    nodes = PlanningNodes(llm=llm, on_failure=lambda s, e: None)
    trace = run_planning_graph(nodes, {"run_id": "r1", "project_id": "p1", "goal": "g"})
    assert trace.stopped_at == "failed_validation"
    # 失败即停，不因 generation 错误继续发起下一次 repair
    assert trace.visited.count("repair_content") == 1


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
    # 确认流程必须经过 apply_decision
    assert "apply_decision" in trace.visited


def test_cancel_does_not_commit_and_persists_cancellation() -> None:
    """取消后的草案绝不可被发布，且取消态必须被持久化。"""
    committed: list = []
    cancelled: list = []
    trace = run_planning_graph(
        _build_nodes(committed=committed, cancelled=cancelled),
        {"run_id": "r1", "project_id": "p1", "goal": "g"},
        resume_decision="cancel",
    )
    assert committed == []
    assert trace.state.get("result_id") == ""
    assert "commit_plan_idempotently" not in trace.visited
    assert len(cancelled) == 1, "取消必须被持久化"


def test_edit_applies_edits_and_revalidates_without_publishing() -> None:
    """编辑后必须重新校验；不得自动发布。"""
    committed: list = []
    edits: list = []
    trace = run_planning_graph(
        _build_nodes(committed=committed, edits=edits),
        {
            "run_id": "r1",
            "project_id": "p1",
            "goal": "g",
            "edited_stages": [
                {"stable_key": "s1", "title": "改后的阶段", "section_kind": "core", "order_index": 0}
            ],
        },
        resume_decision="edit",
    )
    assert edits, "edit 必须应用实际编辑内容"
    assert "validate" in trace.visited
    # 编辑通过后重新等待确认，不得自动发布
    assert trace.stopped_at == "await_approval"
    assert committed == []


# ---------------------------------------------------------------------------
# 真实编辑流程（B1.2 §二）：validate 校验新内容、save 保存新内容
# ---------------------------------------------------------------------------

NEW_NODES = [{"stable_key": "n_new", "title": "编辑后新节点"}]
NEW_UNITS = [{"stable_key": "u_new", "title": "编辑后新单元", "order_index": 0}]


def test_edit_validates_and_saves_the_edited_content() -> None:
    """编辑后的**新结构**必须被校验，且保存的就是新内容（不是旧结构）。"""
    saved: list = []
    edit_result = {
        "draft_ref": "draft:edited:1",
        "nodes": NEW_NODES,
        "units": NEW_UNITS,
        "relations": [],
    }
    trace = run_planning_graph(
        _build_nodes(saved=saved, edit_result=edit_result),
        {
            "run_id": "r1",
            "project_id": "p1",
            "goal": "g",
            "edited_stages": [
                {"stable_key": "s1", "title": "新阶段", "section_kind": "core", "order_index": 0}
            ],
        },
        resume_decision="edit",
    )
    assert trace.stopped_at == "await_approval"
    # 重新校验后保存的草案内容必须是编辑后的新结构
    assert saved, "编辑后必须重新保存草案"
    assert saved[-1].get("units") == NEW_UNITS, "保存的必须是编辑后的新单元"
    assert saved[-1].get("nodes") == NEW_NODES


def test_edit_to_invalid_structure_fails_and_never_reaches_confirmation() -> None:
    """把结构改成非法时：不得进入可确认状态，且**不得**用模型静默修复覆盖编辑。"""
    committed: list = []
    failures: list = []
    # 非法：单元 order_index 重复。
    bad_units = [
        {"stable_key": "u_a", "title": "A", "order_index": 0},
        {"stable_key": "u_b", "title": "B", "order_index": 0},
    ]
    edit_result = {
        "draft_ref": "draft:edited:1",
        "nodes": NEW_NODES,
        "units": bad_units,
        "relations": [],
    }
    trace = run_planning_graph(
        _build_nodes(committed=committed, failures=failures, edit_result=edit_result),
        {
            "run_id": "r1",
            "project_id": "p1",
            "goal": "g",
            "edited_stages": [
                {"stable_key": "s1", "title": "新阶段", "section_kind": "core", "order_index": 0}
            ],
        },
        resume_decision="edit",
    )
    assert trace.stopped_at == "failed_validation", "非法编辑不得停在确认点"
    assert "repair_content" not in trace.visited, "编辑后的非法结构不得被模型静默修复"
    assert committed == []
    assert failures, "失败必须被记录（保留错误）"


def test_edit_missing_content_fails() -> None:
    """edit 缺少实际编辑内容 -> 失败（不默认放行）。"""
    committed: list = []
    trace = run_planning_graph(
        _build_nodes(committed=committed),
        {"run_id": "r1", "project_id": "p1", "goal": "g"},
        resume_decision="edit",
    )
    assert trace.state.get("input_errors")
    assert committed == []
    assert trace.stopped_at == "failed_validation"


def test_illegal_decision_fails_and_never_publishes() -> None:
    """非法 decision 不得默认 approve，不得误发布。"""
    committed: list = []
    for bad in ("", "APPPROVE", "delete", "publish"):
        trace = run_planning_graph(
            _build_nodes(committed=committed),
            {"run_id": "r1", "project_id": "p1", "goal": "g"},
            resume_decision=bad,
        )
        assert trace.stopped_at == "failed_validation", f"非法决定 {bad!r} 必须失败"
        assert trace.visited.count("commit_plan_idempotently") == 0
    assert committed == []


def test_edit_without_content_fails() -> None:
    """edit 必须携带实际编辑内容，否则失败。"""
    trace = run_planning_graph(
        _build_nodes(),
        {"run_id": "r1", "project_id": "p1", "goal": "g"},
        resume_decision="edit",
    )
    assert trace.stopped_at == "failed_validation"


def test_route_after_decision_mapping() -> None:
    assert route_after_decision({"decision": "approve"}) == "commit_plan_idempotently"
    assert route_after_decision({"decision": "edit"}) == "validate"
    assert route_after_decision({"decision": "cancel"}) == "cancel_draft"
    # 非法/缺失不得默认 approve
    assert route_after_decision({"decision": ""}) == "fail_validation"
    assert route_after_decision({}) == "fail_validation"


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
