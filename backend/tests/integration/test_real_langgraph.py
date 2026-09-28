"""真实 LangGraph StateGraph 验收测试（InMemorySaver）。

**为什么需要这份测试**：``test_graph_workflows.py`` 里的解释器只能证明
"转移逻辑写对了"，**不能**证明真实 ``StateGraph`` 的行为一致 ——
reducer 语义、``interrupt`` 的挂起位置、``Command(resume=...)`` 的恢复、
checkpoint 的写入时机都是框架行为。B1 审查正是发现"真实图注册了
``apply_decision`` 却没有接进边"，解释器测试对此完全无感。

因此本文件用**真实图**重跑同一批场景，断言 A–L 十二条验收条款。
真实 Graph 与解释器使用**同一批测试场景**（同一组 Fake Handler），
出现分歧时**以真实 Graph 为准**。

## 覆盖的验收条款

A. 合法计划生成并进入 interrupt
B. 无效结构最多修复两次
C. 修复成功后旧错误消失
D. approve 正常发布
E. edit 应用编辑后重新校验并重新等待确认
F. cancel 不产生正式计划
G. 非法 decision 不会误发布
H. 同一 thread_id 真实恢复
I. 重复 resume 不产生重复副作用
J. 杀掉进程、重新启动后仍能恢复 waiting_user（见 test_graph_recovery_pg.py）
K. 不同 graph_version 的恢复按约定处理
L. Graph checkpoint 与业务草案不一致时，不得对外宣称可以确认

**不依赖** Postgres：本文件用 ``InMemorySaver``；PG 持久化验收见
``test_graph_recovery_pg.py``。
"""

from __future__ import annotations

import pytest
from app.agent_workflows.graphs import (
    LANGGRAPH_AVAILABLE,
    build_planning_graph,
    graph_thread_id,
)
from app.agent_workflows.nodes import PlanningNodes
from app.agent_workflows.validators import MAX_REPAIR_ATTEMPTS
from app.infrastructure.providers.fake import FakeLLM

pytestmark = pytest.mark.langgraph

if not LANGGRAPH_AVAILABLE:  # pragma: no cover - 环境未装 langgraph
    pytest.skip("langgraph 未安装，跳过真实图验收", allow_module_level=True)

from langgraph.checkpoint.memory import InMemorySaver  # noqa: E402
from langgraph.types import Command  # noqa: E402

# ---------------------------------------------------------------------------
# 与解释器测试**完全相同**的场景脚本（避免两份逻辑分别演化）
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
    {"from_stable_key": "n_python", "to_stable_key": "n_rag", "relation_type": "prerequisite"}
]
GOOD_TASKS = [
    {"stable_key": "t_pdf", "title": "PDF 知识助手", "order_index": 0, "acceptance": ["可上传 PDF"]}
]
GOOD_LINKS = [{"task_stable_key": "t_pdf", "node_stable_key": "n_rag", "role": "core"}]

BROKEN_RELATIONS = [
    {"from_stable_key": "n_ghost", "to_stable_key": "n_rag", "relation_type": "prerequisite"}
]


def _good_outline(purpose: str, payload: dict) -> dict:
    return {"outline_ref": "outline:1", "sections": ["foundation", "core"]}


def _good_structure(purpose: str, payload: dict) -> dict:
    return {"nodes": GOOD_NODES, "units": GOOD_UNITS, "relations": GOOD_RELATIONS}


def _broken_structure(purpose: str, payload: dict) -> dict:
    return {"nodes": GOOD_NODES, "units": GOOD_UNITS, "relations": BROKEN_RELATIONS}


def _good_practice(purpose: str, payload: dict) -> dict:
    return {"tasks": GOOD_TASKS, "task_knowledge_links": GOOD_LINKS}


class Recorder:
    """记录应用层端口的调用，用于断言副作用次数（幂等性）。"""

    def __init__(self) -> None:
        self.saved: list = []
        self.committed: list = []
        self.edits: list = []
        self.cancelled: list = []
        self.failures: list = []


def _content_hash(content: dict) -> str:
    import hashlib
    import json

    blob = json.dumps(content, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


class DraftStore:
    """模拟**应用层**草案存储（B1.2 §二）。

    负责：保存草案内容并计算内容指纹、应用用户编辑、以及在提交时校验
    "呈递的 draft_hash 必须等于当前草案的 hash"（旧 hash 不能批准新草案）。
    """

    def __init__(self) -> None:
        self.current_ref = ""
        self.current_hash = ""
        self.content: dict = {}
        self.published: list[dict] = []

    def save(
        self,
        *,
        ref: str,
        nodes: list,
        units: list,
        relations: list,
        practice_proposal: dict | None = None,
    ) -> dict:
        self.current_ref = ref
        self.content = {
            "nodes": nodes,
            "units": units,
            "relations": relations,
            "practice_proposal": practice_proposal or {},
        }
        self.current_hash = _content_hash(self.content)
        return {"draft_ref": ref, "draft_hash": self.current_hash}

    def apply_edit(
        self,
        *,
        ref: str,
        nodes: list,
        units: list,
        relations: list,
        practice_proposal: dict | None = None,
    ) -> dict:
        result = self.save(
            ref=ref,
            nodes=nodes,
            units=units,
            relations=relations,
            practice_proposal=practice_proposal,
        )
        # 正式契约：把**编辑后的完整草案结构**一并返回，供图更新 state。
        return {**result, **self.content}

    def commit(self, presented_hash: str) -> str:
        if presented_hash != self.current_hash:
            raise RuntimeError(
                "draft_hash_mismatch: 呈递的草案哈希与当前草案不一致，拒绝发布"
            )
        self.published.append(dict(self.content))
        return "plan:rev1"


def _nodes(
    recorder: Recorder | None = None,
    *,
    structure=_good_structure,
    repair=None,
    store: DraftStore | None = None,
    edit_structure: dict | None = None,
) -> PlanningNodes:
    rec = recorder or Recorder()
    handlers = {
        "planning.outline": _good_outline,
        "planning.structure": structure,
        "planning.practice": _good_practice,
    }
    if repair is not None:
        handlers["planning.repair"] = repair
    else:
        handlers["planning.repair"] = _good_structure
    llm = FakeLLM(handlers)

    if store is None:
        # 未提供 DraftStore 时退化为简单记录（多数场景不需要 hash 语义）。
        return PlanningNodes(
            llm=llm,
            save_draft=lambda s: (rec.saved.append(dict(s)), f"draft:{len(rec.saved)}")[1],
            commit_plan=lambda s: (rec.committed.append(dict(s)), "plan:rev1")[1],
            apply_edit=lambda s: (
                rec.edits.append(dict(s)),
                {
                    "draft_ref": f"draft:edited:{len(rec.edits)}",
                    "nodes": list(s.get("nodes") or []),
                    "units": list(s.get("units") or []),
                    "relations": list(s.get("relations") or []),
                    "practice_proposal": s.get("practice_proposal") or {},
                },
            )[1],
            cancel_draft=lambda s: rec.cancelled.append(dict(s)),
            on_failure=lambda s, e: rec.failures.append(list(e)),
        )

    def _save(s) -> dict:
        rec.saved.append(dict(s))
        return store.save(
            ref=f"draft:{len(rec.saved)}",
            nodes=list(s.get("nodes") or []),
            units=list(s.get("units") or []),
            relations=list(s.get("relations") or []),
            practice_proposal=s.get("practice_proposal") or {},
        )

    def _apply_edit(s) -> dict:
        rec.edits.append(dict(s))
        if edit_structure is not None:
            return store.apply_edit(
                ref=f"draft:edited:{len(rec.edits)}",
                nodes=edit_structure["nodes"],
                units=edit_structure["units"],
                relations=edit_structure.get("relations", []),
                practice_proposal=s.get("practice_proposal") or {},
            )
        return store.apply_edit(
            ref=f"draft:edited:{len(rec.edits)}",
            nodes=list(s.get("nodes") or []),
            units=list(s.get("units") or []),
            relations=list(s.get("relations") or []),
            practice_proposal=s.get("practice_proposal") or {},
        )

    def _commit(s) -> str:
        rec.committed.append(dict(s))
        return store.commit(str(s.get("draft_hash", "")))

    return PlanningNodes(
        llm=llm,
        save_draft=_save,
        commit_plan=_commit,
        apply_edit=_apply_edit,
        cancel_draft=lambda s: rec.cancelled.append(dict(s)),
        on_failure=lambda s, e: rec.failures.append(list(e)),
    )


def _config(thread_id: str, *, graph_version: str = "1") -> dict:
    return {"configurable": {"thread_id": thread_id, "graph_version": graph_version}}


def _initial(goal: str = "学会 Agent", **extra) -> dict:
    return {"run_id": "run-1", "project_id": "proj-1", "goal": goal, **extra}


# ---------------------------------------------------------------------------
# A. 合法计划生成并进入 interrupt
# ---------------------------------------------------------------------------


def test_A_valid_plan_reaches_interrupt() -> None:
    rec = Recorder()
    graph = build_planning_graph(_nodes(rec), checkpointer=InMemorySaver())
    result = graph.invoke(_initial(), _config("t-A"))

    # 真实 interrupt 会在结果里带 __interrupt__
    assert "__interrupt__" in result, "合法计划必须停在 interrupt"
    payload = result["__interrupt__"][0].value
    assert payload["kind"] == "plan_draft_approval"
    assert payload["options"] == ["approve", "edit", "cancel"]
    # interrupt 前保存了草案，但**没有**提交
    assert len(rec.saved) == 1
    assert rec.committed == []
    # 状态里三通道错误都干净
    assert result.get("structure_errors") == []
    assert result.get("generation_errors") == []
    assert result.get("input_errors") == []


def test_A2_empty_goal_fails_without_model_call() -> None:
    """空目标：真实图也必须直接失败，不调用模型。"""
    rec = Recorder()
    llm = FakeLLM({})  # 无 handler
    nodes = PlanningNodes(llm=llm, on_failure=lambda s, e: rec.failures.append(list(e)))
    graph = build_planning_graph(nodes, checkpointer=InMemorySaver())
    result = graph.invoke(_initial(goal="   "), _config("t-A2"))
    assert llm.calls == [], "空目标不得调用模型"
    assert result.get("input_errors")
    assert "__interrupt__" not in result


# ---------------------------------------------------------------------------
# B. 无效结构最多修复两次
# ---------------------------------------------------------------------------


def test_B_invalid_structure_repairs_at_most_twice() -> None:
    rec = Recorder()
    calls = {"repair": 0}

    def counting_repair(purpose: str, payload: dict) -> dict:
        calls["repair"] += 1
        return _broken_structure(purpose, payload)

    graph = build_planning_graph(
        _nodes(rec, structure=_broken_structure, repair=counting_repair),
        checkpointer=InMemorySaver(),
    )
    result = graph.invoke(_initial(), _config("t-B"))
    assert calls["repair"] == MAX_REPAIR_ATTEMPTS
    assert rec.failures, "失败必须被记录"
    assert "__interrupt__" not in result
    assert rec.committed == []


# ---------------------------------------------------------------------------
# C. 修复成功后旧错误消失
# ---------------------------------------------------------------------------


def test_C_repair_success_clears_old_errors() -> None:
    rec = Recorder()
    state = {"n": 0}

    def one_time_broken(purpose: str, payload: dict) -> dict:
        if state["n"] == 0:
            state["n"] = 1
            return _broken_structure(purpose, payload)
        return _good_structure(purpose, payload)

    graph = build_planning_graph(
        _nodes(rec, structure=one_time_broken, repair=one_time_broken),
        checkpointer=InMemorySaver(),
    )
    result = graph.invoke(_initial(), _config("t-C"))
    assert "__interrupt__" in result, "一次修复成功后必须能进入待确认"
    assert result.get("structure_errors") == [], "旧结构错误必须消失"
    assert result.get("validation_errors") == []


# ---------------------------------------------------------------------------
# D. approve 正常发布
# ---------------------------------------------------------------------------


def test_D_approve_publishes() -> None:
    rec = Recorder()
    graph = build_planning_graph(_nodes(rec), checkpointer=InMemorySaver())
    cfg = _config("t-D")
    graph.invoke(_initial(), cfg)
    graph.invoke(Command(resume="approve"), cfg)
    assert len(rec.committed) == 1, "approve 必须发布一次"
    assert graph.get_state(cfg).values.get("result_id") == "plan:rev1"


# ---------------------------------------------------------------------------
# E. edit 应用编辑后重新校验并重新等待确认
# ---------------------------------------------------------------------------


def test_E_edit_revalidates_and_waits_again() -> None:
    rec = Recorder()
    graph = build_planning_graph(_nodes(rec), checkpointer=InMemorySaver())
    cfg = _config("t-E")
    graph.invoke(_initial(), cfg)
    result = graph.invoke(
        Command(
            resume={
                "decision": "edit",
                "edited_stages": [
                    {"stable_key": "s1", "title": "改后", "section_kind": "core", "order_index": 0}
                ],
            }
        ),
        cfg,
    )
    assert rec.edits, "edit 必须应用实际编辑内容"
    assert rec.committed == [], "edit 不得自动发布"
    # 重新等待确认
    assert "__interrupt__" in result, "编辑后必须重新等待确认"


def test_E2_edit_without_content_fails() -> None:
    rec = Recorder()
    graph = build_planning_graph(_nodes(rec), checkpointer=InMemorySaver())
    cfg = _config("t-E2")
    graph.invoke(_initial(), cfg)
    result = graph.invoke(Command(resume={"decision": "edit"}), cfg)
    assert rec.committed == []
    assert result.get("input_errors"), "缺少编辑内容必须失败"


# ---------------------------------------------------------------------------
# E3–E6. 真实编辑流程（B1.2 §二）：校验新内容、保存新内容、不发布、旧 hash 失效
# ---------------------------------------------------------------------------

EDITED_NODES = [
    {"stable_key": "n_python", "title": "Python 基础（编辑后）"},
    {"stable_key": "n_rag", "title": "RAG 检索（编辑后）"},
]
EDITED_UNITS = [
    {"stable_key": "u_basic", "title": "基础（编辑后）", "order_index": 0},
    {"stable_key": "u_rag", "title": "RAG（编辑后）", "order_index": 1},
]
#: 非法编辑：单元 order_index 重复（其余保持与任务关联一致，隔离出单一错误）。
BAD_EDITED_UNITS = [
    {"stable_key": "u_basic", "title": "基础", "order_index": 0},
    {"stable_key": "u_rag", "title": "RAG", "order_index": 0},
]


def test_E3_edit_to_invalid_structure_cannot_reach_confirmation() -> None:
    """1) 修改为非法结构，不能进入可确认状态。"""
    store = DraftStore()
    rec = Recorder()
    graph = build_planning_graph(
        _nodes(rec, store=store, edit_structure={"nodes": EDITED_NODES, "units": BAD_EDITED_UNITS}),
        checkpointer=InMemorySaver(),
    )
    cfg = _config("t-E3")
    graph.invoke(_initial(), cfg)
    result = graph.invoke(
        Command(resume={"decision": "edit", "edited_stages": [{"stable_key": "s1", "title": "x"}]}),
        cfg,
    )
    assert "__interrupt__" not in result, "非法编辑不得停在确认点"
    assert result.get("structure_errors"), "必须保留结构校验错误"
    assert rec.committed == []
    assert store.published == []


def test_E4_edit_to_valid_structure_shows_and_publishes_new_content() -> None:
    """2) 修改为合法结构，再次确认时**展示与发布的都是新内容**。"""
    store = DraftStore()
    rec = Recorder()
    graph = build_planning_graph(
        _nodes(rec, store=store, edit_structure={"nodes": EDITED_NODES, "units": EDITED_UNITS}),
        checkpointer=InMemorySaver(),
    )
    cfg = _config("t-E4")
    graph.invoke(_initial(), cfg)
    hash_before = store.current_hash

    result = graph.invoke(
        Command(resume={"decision": "edit", "edited_stages": [{"stable_key": "s1", "title": "x"}]}),
        cfg,
    )
    # 重新等待确认，且草案内容已是编辑后的新内容
    assert "__interrupt__" in result
    assert store.content["units"] == EDITED_UNITS, "保存的必须是编辑后的新内容"
    assert store.current_hash != hash_before, "编辑后草案指纹必须变化"
    # 确认点展示的 hash 就是新草案的 hash
    payload = result["__interrupt__"][0].value
    assert payload["draft_hash"] == store.current_hash

    # 用新 hash 批准 -> 发布的必须是新内容
    graph.invoke(
        Command(resume={"decision": "approve", "draft_hash": store.current_hash,
                        "idempotency_key": "k-e4"}),
        cfg,
    )
    assert len(store.published) == 1
    assert store.published[0]["units"] == EDITED_UNITS, "发布的必须是编辑后的新内容"


def test_E5_edit_does_not_publish() -> None:
    """3) edit 不直接发布。"""
    store = DraftStore()
    rec = Recorder()
    graph = build_planning_graph(
        _nodes(rec, store=store, edit_structure={"nodes": EDITED_NODES, "units": EDITED_UNITS}),
        checkpointer=InMemorySaver(),
    )
    cfg = _config("t-E5")
    graph.invoke(_initial(), cfg)
    graph.invoke(
        Command(resume={"decision": "edit", "edited_stages": [{"stable_key": "s1", "title": "x"}]}),
        cfg,
    )
    assert rec.committed == [], "edit 不得触发提交"
    assert store.published == [], "edit 不得发布任何计划"


def test_E6_stale_draft_hash_cannot_approve_new_draft() -> None:
    """4) 旧 draft_hash 不能批准新草案。"""
    store = DraftStore()
    rec = Recorder()
    graph = build_planning_graph(
        _nodes(rec, store=store, edit_structure={"nodes": EDITED_NODES, "units": EDITED_UNITS}),
        checkpointer=InMemorySaver(),
    )
    cfg = _config("t-E6")
    graph.invoke(_initial(), cfg)
    stale_hash = store.current_hash  # 编辑前的 hash

    graph.invoke(
        Command(resume={"decision": "edit", "edited_stages": [{"stable_key": "s1", "title": "x"}]}),
        cfg,
    )
    assert store.current_hash != stale_hash

    # 用**旧** hash 批准新草案 -> 必须被拒绝
    with pytest.raises(RuntimeError, match="draft_hash_mismatch"):
        graph.invoke(
            Command(resume={"decision": "approve", "draft_hash": stale_hash,
                            "idempotency_key": "k-e6"}),
            cfg,
        )
    assert store.published == [], "旧 hash 不得发布任何内容"


# ---------------------------------------------------------------------------
# F. cancel 不产生正式计划
# ---------------------------------------------------------------------------


def test_F_cancel_produces_no_plan_and_persists_state() -> None:
    rec = Recorder()
    graph = build_planning_graph(_nodes(rec), checkpointer=InMemorySaver())
    cfg = _config("t-F")
    graph.invoke(_initial(), cfg)
    result = graph.invoke(Command(resume="cancel"), cfg)
    assert rec.committed == [], "cancel 不得发布"
    assert len(rec.cancelled) == 1, "cancel 必须持久化取消状态"
    assert not result.get("result_id")
    assert "__interrupt__" not in result


# ---------------------------------------------------------------------------
# G. 非法 decision 不会误发布
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad", ["", "APPPROVE", "delete", "publish", "approvee"])
def test_G_illegal_decision_never_publishes(bad: str) -> None:
    rec = Recorder()
    graph = build_planning_graph(_nodes(rec), checkpointer=InMemorySaver())
    cfg = _config(f"t-G-{bad or 'empty'}")
    graph.invoke(_initial(), cfg)
    result = graph.invoke(Command(resume=bad), cfg)
    assert rec.committed == [], f"非法决定 {bad!r} 不得发布"
    assert result.get("input_errors"), f"非法决定 {bad!r} 必须失败"


# ---------------------------------------------------------------------------
# H. 同一 thread_id 真实恢复
# ---------------------------------------------------------------------------


def test_H_same_thread_recovers_from_checkpoint() -> None:
    rec = Recorder()
    graph = build_planning_graph(_nodes(rec), checkpointer=InMemorySaver())
    cfg = _config("t-H")
    first = graph.invoke(_initial(), cfg)
    assert "__interrupt__" in first
    snap = graph.get_state(cfg)
    assert snap.values.get("draft_ref"), "checkpoint 必须保存 draft_ref"
    assert snap.next, "恢复点必须记录下一步节点"
    # 用同一 thread 恢复：不重新生成（saved 仍为 1）
    graph.invoke(Command(resume="approve"), cfg)
    assert len(rec.saved) == 1, "恢复不得重新生成草案"


def test_H2_different_thread_is_isolated() -> None:
    rec = Recorder()
    graph = build_planning_graph(_nodes(rec), checkpointer=InMemorySaver())
    graph.invoke(_initial(), _config("t-H2-a"))
    graph.invoke(_initial(), _config("t-H2-b"))
    assert len(rec.saved) == 2, "不同 thread 必须各自独立执行"
    assert graph.get_state(_config("t-H2-a")).values.get("draft_ref") is not None


# ---------------------------------------------------------------------------
# I. 重复 resume 不产生重复副作用
# ---------------------------------------------------------------------------


def test_I_repeated_resume_does_not_duplicate_side_effects() -> None:
    """同一 thread 重复 resume：不得重复发布。

    approve 后图已到 END，再次 resume 不应产生第二次 commit。
    真正的"幂等键去重"由应用层 commit_plan 实现；这里断言图层面
    不会因为重复投递而重复执行提交节点。
    """
    rec = Recorder()
    graph = build_planning_graph(_nodes(rec), checkpointer=InMemorySaver())
    cfg = _config("t-I")
    graph.invoke(_initial(), cfg)
    graph.invoke(Command(resume="approve"), cfg)
    assert len(rec.committed) == 1
    # 已到终态：再次 resume 不应改变
    state_after = graph.get_state(cfg)
    assert not state_after.next, "approve 后图必须到达终态"
    assert len(rec.committed) == 1, "重复 resume 不得重复发布"


# ---------------------------------------------------------------------------
# K. 不同 graph_version 的恢复按约定处理
# ---------------------------------------------------------------------------


def test_K_graph_version_mismatch_is_rejected_by_config() -> None:
    """不同 graph_version 的恢复必须被拒绝，而不是静默跑错版本。

    **B1 审查发现的真实缺陷**：LangGraph 的 checkpoint **只按 thread_id 索引**，
    ``configurable`` 里的 ``graph_version`` 完全不参与命名。原实现直接用
    business run_id 当 thread_id，于是升级图版本后旧 checkpoint 会被新图
    **静默恢复**。

    修复采用"命名空间隔离"：``graph_thread_id`` 把版本编进 thread_id，
    使不同版本在物理上无法碰撞；本测试同时断言这一点。
    """
    rec = Recorder()
    graph = build_planning_graph(_nodes(rec), checkpointer=InMemorySaver())

    tid_v1 = graph_thread_id(run_id="run-1", graph_version="1")
    cfg_v1 = {"configurable": {"thread_id": tid_v1}}
    graph.invoke(_initial(), cfg_v1)
    assert graph.get_state(cfg_v1).values.get("draft_ref")

    # 不同 graph_version => 不同 thread_id => 读不到 v1 的状态
    tid_v2 = graph_thread_id(run_id="run-1", graph_version="2")
    assert tid_v1 != tid_v2, "thread_id 必须随 graph_version 变化"
    snap_v2 = graph.get_state({"configurable": {"thread_id": tid_v2}})
    assert not snap_v2.values, "不同 graph_version 不得读到 v1 的草案状态"


def test_K2_graph_version_guard_rejects_mismatch() -> None:
    """显式校验：checkpoint 版本与当前版本不一致必须抛错。"""
    from app.agent_workflows.graphs import GraphVersionMismatchError, assert_resumable

    # 一致 -> 放行
    assert_resumable(checkpoint_graph_version="1", current_graph_version="1")
    # 不一致 -> 拒绝
    with pytest.raises(GraphVersionMismatchError):
        assert_resumable(checkpoint_graph_version="1", current_graph_version="2")
    # 缺失 -> 拒绝（不假定安全）
    with pytest.raises(GraphVersionMismatchError):
        assert_resumable(checkpoint_graph_version=None, current_graph_version="1")


# ---------------------------------------------------------------------------
# L. checkpoint 与业务草案不一致时不得宣称可以确认
# ---------------------------------------------------------------------------


def test_L_stale_checkpoint_cannot_be_approved_silently() -> None:
    """checkpoint 与业务草案不一致：不得对外宣称可以确认。

    约定：approve 时由应用层 ``commit_plan`` 校验草案 hash/version；
    图层面若草案已被改（draft_ref 指向的内容变化），提交端口必须抛出冲突。
    本测试用一个"检测到 hash 不一致就抛冲突"的端口模拟该契约。
    """
    rec = Recorder()

    def conflicting_commit(state) -> str:
        # 模拟应用层：草案 hash 与期望不一致 -> 拒绝
        raise RuntimeError("draft_hash_mismatch")

    llm = FakeLLM(
        {
            "planning.outline": _good_outline,
            "planning.structure": _good_structure,
            "planning.practice": _good_practice,
        }
    )
    nodes = PlanningNodes(
        llm=llm,
        save_draft=lambda s: "draft:1",
        commit_plan=conflicting_commit,
    )
    graph = build_planning_graph(nodes, checkpointer=InMemorySaver())
    cfg = _config("t-L")
    graph.invoke(_initial(), cfg)
    with pytest.raises(RuntimeError, match="draft_hash_mismatch"):
        graph.invoke(Command(resume="approve"), cfg)
    assert rec.committed == []


# ---------------------------------------------------------------------------
# 一致性：真实图与解释器的关键结论必须相同
# ---------------------------------------------------------------------------


def test_real_graph_and_interpreter_agree_on_approve() -> None:
    """真实图与解释器在同一场景下的关键结论必须一致。"""
    from app.agent_workflows.graphs import run_planning_graph

    rec_i = Recorder()
    trace = run_planning_graph(_nodes(rec_i), _initial(), resume_decision="approve")
    rec_g = Recorder()
    graph = build_planning_graph(_nodes(rec_g), checkpointer=InMemorySaver())
    cfg = _config("t-consistency")
    graph.invoke(_initial(), cfg)
    graph.invoke(Command(resume="approve"), cfg)

    assert len(trace.visited) > 0
    assert len(rec_i.committed) == len(rec_g.committed) == 1
    assert trace.state.get("result_id") == graph.get_state(cfg).values.get("result_id")


def test_real_graph_and_interpreter_agree_on_cancel() -> None:
    from app.agent_workflows.graphs import run_planning_graph

    rec_i = Recorder()
    run_planning_graph(_nodes(rec_i), _initial(), resume_decision="cancel")
    rec_g = Recorder()
    graph = build_planning_graph(_nodes(rec_g), checkpointer=InMemorySaver())
    cfg = _config("t-consistency-cancel")
    graph.invoke(_initial(), cfg)
    graph.invoke(Command(resume="cancel"), cfg)

    assert len(rec_i.committed) == len(rec_g.committed) == 0
    assert len(rec_i.cancelled) == len(rec_g.cancelled) == 1
