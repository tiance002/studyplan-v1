"""跨进程 Checkpoint 持久化验收（真实 PostgreSQL Checkpointer）。

对应 Goal §4 条款 **H / I / J / L**，并复用 §7 的独立临时库约束：

- **H**：同一 ``thread_id`` 真实恢复；
- **I**：重复 resume 不产生重复副作用；
- **J**：**杀掉进程、重新启动后仍能恢复 waiting_user** —— 这是本文件的
  核心：第一阶段在**独立子进程**里跑图直到 interrupt 并落盘，进程退出后
  第二阶段在**当前进程**用同一 thread 恢复。只有真正持久化了 checkpoint
  才可能通过。
- **L**：checkpoint 与业务草案不一致时，不得对外宣称可以确认。

Checkpointer 使用 ``langgraph-checkpoint-postgres``，库与表建立在
``studyplan_test_*`` 临时库中，测试结束即删库。
"""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

pytestmark = pytest.mark.postgres

psycopg = pytest.importorskip("psycopg")

BACKEND_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND_DIR))

from tests.pg_harness import PgTestDatabase, create_test_database  # noqa: E402

# ---------------------------------------------------------------------------
# 子进程脚本：在**独立进程**里跑图，验证跨进程恢复
# ---------------------------------------------------------------------------

CHILD_SCRIPT = textwrap.dedent(
    '''
    """在独立进程中执行 planning_graph 直到 interrupt，并把关键信息写回。"""
    import json, sys
    sys.path.insert(0, {backend!r})

    from app.agent_workflows.graphs import build_planning_graph, graph_thread_id, LANGGRAPH_AVAILABLE
    from app.agent_workflows.nodes import PlanningNodes
    from app.infrastructure.providers.fake import FakeLLM
    from langgraph.checkpoint.postgres import PostgresSaver

    dsn = sys.argv[1]
    thread_id = sys.argv[2]
    out_path = sys.argv[3]

    GOOD_NODES = [{{"stable_key": "n_python", "title": "Python"}}, {{"stable_key": "n_rag", "title": "RAG"}}]
    GOOD_UNITS = [{{"stable_key": "u1", "title": "基础", "order_index": 0}}]
    GOOD_RELATIONS = []
    GOOD_TASKS = [{{"stable_key": "t1", "title": "PDF", "order_index": 0, "acceptance": ["可抽取"]}}]
    GOOD_LINKS = [{{"task_stable_key": "t1", "node_stable_key": "n_rag", "role": "core"}}]

    saved = []

    def outline(purpose, payload):
        return {{"outline_ref": "o:1", "sections": ["core"]}}

    def structure(purpose, payload):
        return {{"nodes": GOOD_NODES, "units": GOOD_UNITS, "relations": GOOD_RELATIONS}}

    def practice(purpose, payload):
        return {{"tasks": GOOD_TASKS, "task_knowledge_links": GOOD_LINKS}}

    llm = FakeLLM({{"planning.outline": outline, "planning.structure": structure, "planning.practice": practice}})
    nodes = PlanningNodes(
        llm=llm,
        save_draft=lambda s: (saved.append(1), "draft:persisted")[1],
        commit_plan=lambda s: "plan:rev1",
    )

    with PostgresSaver.from_conn_string(dsn) as saver:
        saver.setup()
        graph = build_planning_graph(nodes, checkpointer=saver)
        cfg = {{"configurable": {{"thread_id": thread_id}}}}
        result = graph.invoke(
            {{"run_id": "run-1", "project_id": "proj-1", "goal": "学会 Agent"}}, cfg
        )
        interrupted = "__interrupt__" in result
        state = graph.get_state(cfg)
        payload = {{
            "interrupted": interrupted,
            "saved_count": len(saved),
            "draft_ref": state.values.get("draft_ref"),
            "next": list(state.next),
            "has_generation_errors": bool(state.values.get("generation_errors")),
        }}
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False)
    print("CHILD_OK")
    '''
)


@pytest.fixture(scope="module")
def checkpoint_db() -> PgTestDatabase:
    db = create_test_database(prefix="studyplan_test_ckpt")
    try:
        yield db
    finally:
        db.drop()


def _child_dsn(db: PgTestDatabase) -> str:
    # langgraph 的 PostgresSaver 用 psycopg，接受原生 postgresql:// 串。
    return db.migrator_dsn


def test_J_cross_process_recovery_of_waiting_user(checkpoint_db: PgTestDatabase, tmp_path: Path) -> None:
    """J：杀掉进程后，新进程仍能恢复 waiting_user 并完成发布。

    阶段 1：子进程跑图到 interrupt，写 checkpoint 到 PG，然后**退出**。
    阶段 2：主进程用同一 thread 恢复，断言不重新生成、且能正常 approve。
    """
    dsn = _child_dsn(checkpoint_db)
    thread_id = "run-cross-proc::1"
    out_path = tmp_path / "child.json"

    # ---- 阶段 1：独立进程执行 ----
    child = subprocess.run(
        [sys.executable, "-c", CHILD_SCRIPT.format(backend=str(BACKEND_DIR)), dsn, thread_id, str(out_path)],
        capture_output=True,
        text=True,
        cwd=str(BACKEND_DIR),
    )
    assert child.returncode == 0, f"子进程失败：{child.stderr[-800:]}"
    assert out_path.exists(), "子进程必须写出结果"
    info = json.loads(out_path.read_text(encoding="utf-8"))
    assert info["interrupted"] is True, "子进程必须停在 interrupt"
    assert info["saved_count"] == 1
    assert info["draft_ref"] == "draft:persisted"

    # ---- 阶段 2：主进程恢复（新进程，状态只可能来自 PG）----
    from app.agent_workflows.graphs import build_planning_graph
    from app.agent_workflows.nodes import PlanningNodes
    from app.infrastructure.providers.fake import FakeLLM
    from langgraph.checkpoint.postgres import PostgresSaver
    from langgraph.types import Command

    committed: list = []
    saved_again: list = []

    GOOD_NODES = [{"stable_key": "n_python", "title": "Python"}, {"stable_key": "n_rag", "title": "RAG"}]
    GOOD_UNITS = [{"stable_key": "u1", "title": "基础", "order_index": 0}]
    GOOD_TASKS = [{"stable_key": "t1", "title": "PDF", "order_index": 0, "acceptance": ["可抽取"]}]
    GOOD_LINKS = [{"task_stable_key": "t1", "node_stable_key": "n_rag", "role": "core"}]

    llm = FakeLLM(
        {
            "planning.outline": lambda p, x: {"outline_ref": "o:1", "sections": ["core"]},
            "planning.structure": lambda p, x: {"nodes": GOOD_NODES, "units": GOOD_UNITS, "relations": []},
            "planning.practice": lambda p, x: {"tasks": GOOD_TASKS, "task_knowledge_links": GOOD_LINKS},
        }
    )
    nodes = PlanningNodes(
        llm=llm,
        save_draft=lambda s: (saved_again.append(1), "draft:2")[1],
        commit_plan=lambda s: (committed.append(dict(s)), "plan:rev1")[1],
    )

    with PostgresSaver.from_conn_string(dsn) as saver:
        graph = build_planning_graph(nodes, checkpointer=saver)
        cfg = {"configurable": {"thread_id": thread_id}}
        # 恢复前先确认状态确实来自 checkpoint
        pre = graph.get_state(cfg)
        assert pre.values.get("draft_ref") == "draft:persisted", "必须从 PG 恢复出草案引用"
        assert pre.next, "必须记录恢复点"

        graph.invoke(Command(resume="approve"), cfg)
        after = graph.get_state(cfg)
        assert len(committed) == 1, "恢复后必须完成发布"
        assert not after.next, "approve 后必须到终态"
        assert saved_again == [], "恢复不得重新生成草案"


def test_I_repeated_resume_no_duplicate_side_effects(checkpoint_db: PgTestDatabase) -> None:
    """I：对同一 thread 重复 resume 不得重复发布。"""
    from app.agent_workflows.graphs import build_planning_graph
    from app.agent_workflows.nodes import PlanningNodes
    from app.infrastructure.providers.fake import FakeLLM
    from langgraph.checkpoint.postgres import PostgresSaver
    from langgraph.types import Command

    committed: list = []
    GOOD_NODES = [{"stable_key": "n1", "title": "N"}]
    GOOD_UNITS = [{"stable_key": "u1", "title": "U", "order_index": 0}]
    GOOD_TASKS = [{"stable_key": "t1", "title": "T", "order_index": 0, "acceptance": ["a"]}]
    GOOD_LINKS = [{"task_stable_key": "t1", "node_stable_key": "n1", "role": "core"}]
    llm = FakeLLM(
        {
            "planning.outline": lambda p, x: {"outline_ref": "o:1", "sections": ["core"]},
            "planning.structure": lambda p, x: {"nodes": GOOD_NODES, "units": GOOD_UNITS, "relations": []},
            "planning.practice": lambda p, x: {"tasks": GOOD_TASKS, "task_knowledge_links": GOOD_LINKS},
            "planning.repair": lambda p, x: {"nodes": GOOD_NODES, "units": GOOD_UNITS, "relations": []},
        }
    )
    nodes = PlanningNodes(
        llm=llm,
        save_draft=lambda s: "draft:1",
        commit_plan=lambda s: (committed.append(1), "plan:rev1")[1],
    )
    with PostgresSaver.from_conn_string(_child_dsn(checkpoint_db)) as saver:
        graph = build_planning_graph(nodes, checkpointer=saver)
        cfg = {"configurable": {"thread_id": "run-repeat::1"}}
        graph.invoke({"run_id": "r", "project_id": "p", "goal": "g"}, cfg)
        graph.invoke(Command(resume="approve"), cfg)
        assert len(committed) == 1
        # 再次 resume：图已终态，不得再提交
        graph.invoke(Command(resume="approve"), cfg)
        assert len(committed) == 1, "重复 resume 不得重复发布"


def test_H_same_thread_recovers_and_isolated(checkpoint_db: PgTestDatabase) -> None:
    """H：同一 thread 恢复；不同 thread 相互隔离（真实 PG）。"""
    from app.agent_workflows.graphs import build_planning_graph
    from app.agent_workflows.nodes import PlanningNodes
    from app.infrastructure.providers.fake import FakeLLM
    from langgraph.checkpoint.postgres import PostgresSaver

    saved: list = []
    GOOD_NODES = [{"stable_key": "n1", "title": "N"}]
    GOOD_UNITS = [{"stable_key": "u1", "title": "U", "order_index": 0}]
    GOOD_TASKS = [{"stable_key": "t1", "title": "T", "order_index": 0, "acceptance": ["a"]}]
    GOOD_LINKS = [{"task_stable_key": "t1", "node_stable_key": "n1", "role": "core"}]
    llm = FakeLLM(
        {
            "planning.outline": lambda p, x: {"outline_ref": "o:1", "sections": ["core"]},
            "planning.structure": lambda p, x: {"nodes": GOOD_NODES, "units": GOOD_UNITS, "relations": []},
            "planning.practice": lambda p, x: {"tasks": GOOD_TASKS, "task_knowledge_links": GOOD_LINKS},
        }
    )
    nodes = PlanningNodes(
        llm=llm,
        save_draft=lambda s: (saved.append(1), f"draft:{len(saved)}")[1],
    )
    with PostgresSaver.from_conn_string(_child_dsn(checkpoint_db)) as saver:
        graph = build_planning_graph(nodes, checkpointer=saver)
        cfg_a = {"configurable": {"thread_id": "run-iso-a::1"}}
        cfg_b = {"configurable": {"thread_id": "run-iso-b::1"}}
        graph.invoke({"run_id": "a", "project_id": "p", "goal": "g"}, cfg_a)
        graph.invoke({"run_id": "b", "project_id": "p", "goal": "g"}, cfg_b)
        assert len(saved) == 2
        assert graph.get_state(cfg_a).values.get("run_id") == "a"
        assert graph.get_state(cfg_b).values.get("run_id") == "b"


def test_L_stale_draft_cannot_be_confirmed(checkpoint_db: PgTestDatabase) -> None:
    """L：checkpoint 与业务草案不一致时，不得宣称可以确认。

    以"提交端口检测到草案 hash 不一致即抛冲突"模拟应用层契约：
    图必须把冲突**冒泡**出去，而不是吞掉冲突当作成功。
    """
    from app.agent_workflows.graphs import build_planning_graph
    from app.agent_workflows.nodes import PlanningNodes
    from app.infrastructure.providers.fake import FakeLLM
    from langgraph.checkpoint.postgres import PostgresSaver
    from langgraph.types import Command

    GOOD_NODES = [{"stable_key": "n1", "title": "N"}]
    GOOD_UNITS = [{"stable_key": "u1", "title": "U", "order_index": 0}]
    GOOD_TASKS = [{"stable_key": "t1", "title": "T", "order_index": 0, "acceptance": ["a"]}]
    GOOD_LINKS = [{"task_stable_key": "t1", "node_stable_key": "n1", "role": "core"}]
    llm = FakeLLM(
        {
            "planning.outline": lambda p, x: {"outline_ref": "o:1", "sections": ["core"]},
            "planning.structure": lambda p, x: {"nodes": GOOD_NODES, "units": GOOD_UNITS, "relations": []},
            "planning.practice": lambda p, x: {"tasks": GOOD_TASKS, "task_knowledge_links": GOOD_LINKS},
        }
    )

    def conflicting_commit(state):
        raise RuntimeError("draft_hash_mismatch: 草案已变化，请重新加载")

    nodes = PlanningNodes(
        llm=llm,
        save_draft=lambda s: "draft:1",
        commit_plan=conflicting_commit,
    )
    with PostgresSaver.from_conn_string(_child_dsn(checkpoint_db)) as saver:
        graph = build_planning_graph(nodes, checkpointer=saver)
        cfg = {"configurable": {"thread_id": "run-stale::1"}}
        graph.invoke({"run_id": "r", "project_id": "p", "goal": "g"}, cfg)
        with pytest.raises(RuntimeError, match="draft_hash_mismatch"):
            graph.invoke(Command(resume="approve"), cfg)
