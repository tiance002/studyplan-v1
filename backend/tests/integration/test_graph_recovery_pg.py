"""跨进程 Checkpoint 持久化验收（真实 PostgreSQL Checkpointer）。

对应 Goal §4 条款 **H / I / J / J2 / L**，并复用 §7 的独立临时库约束：

- **H**：同一 ``thread_id`` 真实恢复；
- **I**：重复 resume 不产生重复副作用；
- **J（正常退出后的跨进程恢复）**：第一阶段在**独立子进程**里跑图直到
  interrupt 并落盘，子进程**正常退出**（``subprocess.run`` 返回 0，走完
  ``with`` 块的优雅收尾）后，第二阶段在**当前进程**用同一 thread 恢复。
- **J2（强制崩溃恢复）**：子进程跑到 interrupt 并把 sentinel 写出后**阻塞**，
  父进程用 ``Popen.kill()`` **强制终止**它（Windows 为 TerminateProcess，
  POSIX 为 SIGKILL）——**不执行任何清理钩子、不优雅关闭连接**；随后在
  新进程恢复。只有 checkpoint 已**独立于进程生命周期**持久化到 PG 才能通过。
- **L**：checkpoint 与业务草案不一致时，不得对外宣称可以确认。

> **口径说明**：J 与 J2 是两类不同的证据，**分别记录**，不得混为一谈。
> J 证明「正常退出后状态可跨进程恢复」；J2 证明「进程被强杀、无任何清理
> 动作后状态仍可恢复」。二者都只覆盖 **Fake provider** 的图，不代表真实
> 外部核验或真实模型已接入。

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

    from app.agent_workflows.graphs import graph_thread_id, LANGGRAPH_AVAILABLE
    from tests.helpers.retained_planning_graph import build_planning_graph
    from tests.helpers.retained_planning_graph import TransitionNodes as PlanningNodes
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

# ---------------------------------------------------------------------------
# 强制崩溃子进程脚本：跑到 interrupt、写出 sentinel 后**阻塞**等待被强杀。
# 与 CHILD_SCRIPT 的关键区别：本脚本**不会**优雅退出——父进程会在
# ``with PostgresSaver...`` 块仍打开时用 kill() 强制终止它，因此任何
# 依赖「进程正常收尾 / 连接优雅关闭 / atexit 钩子」的持久化都会失败。
# ---------------------------------------------------------------------------

CRASH_CHILD_SCRIPT = textwrap.dedent(
    '''
    """跑图到 interrupt，落盘 checkpoint，写 sentinel 后阻塞等待被强杀。"""
    import json, sys, time
    sys.path.insert(0, {backend!r})

    from tests.helpers.retained_planning_graph import build_planning_graph
    from tests.helpers.retained_planning_graph import TransitionNodes as PlanningNodes
    from app.infrastructure.providers.fake import FakeLLM
    from langgraph.checkpoint.postgres import PostgresSaver

    dsn = sys.argv[1]
    thread_id = sys.argv[2]
    out_path = sys.argv[3]

    GOOD_NODES = [{{"stable_key": "n_python", "title": "Python"}}, {{"stable_key": "n_rag", "title": "RAG"}}]
    GOOD_UNITS = [{{"stable_key": "u1", "title": "基础", "order_index": 0}}]
    GOOD_TASKS = [{{"stable_key": "t1", "title": "PDF", "order_index": 0, "acceptance": ["可抽取"]}}]
    GOOD_LINKS = [{{"task_stable_key": "t1", "node_stable_key": "n_rag", "role": "core"}}]

    saved = []
    llm = FakeLLM({{
        "planning.outline": lambda p, x: {{"outline_ref": "o:1", "sections": ["core"]}},
        "planning.structure": lambda p, x: {{"nodes": GOOD_NODES, "units": GOOD_UNITS, "relations": []}},
        "planning.practice": lambda p, x: {{"tasks": GOOD_TASKS, "task_knowledge_links": GOOD_LINKS}},
    }})
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
        state = graph.get_state(cfg)
        payload = {{
            "interrupted": "__interrupt__" in result,
            "saved_count": len(saved),
            "draft_ref": state.values.get("draft_ref"),
            "next": list(state.next),
        }}
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False)
        print("CHILD_READY", flush=True)
        # 阻塞：父进程读到 sentinel 后会强杀本进程，此处**不执行任何清理**。
        time.sleep(600)
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
    """J（**正常退出**后的跨进程恢复）：子进程跑图到 interrupt、落盘后**正常退出**，
    新进程用同一 thread 恢复并完成发布。

    阶段 1：子进程跑图到 interrupt，写 checkpoint 到 PG，然后**正常退出**
    （``subprocess.run`` 返回 0，走完 ``with`` 块的优雅收尾）。
    阶段 2：主进程用同一 thread 恢复，断言不重新生成、且能正常 approve。

    > 这是「正常退出」路径。**强制崩溃**路径见 ``test_J2_forced_crash_recovery_of_waiting_user``，
    > 两者证据分别记录、不得混用。
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
    from tests.helpers.retained_planning_graph import build_planning_graph
    from tests.helpers.retained_planning_graph import TransitionNodes as PlanningNodes
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


def test_J2_forced_crash_recovery_of_waiting_user(checkpoint_db: PgTestDatabase, tmp_path: Path) -> None:
    """J2（**强制崩溃**恢复）：进程被强杀、无任何清理动作后仍能恢复 waiting_user。

    与 J 的区别：子进程跑到 interrupt 并写出 sentinel 后**阻塞**，父进程用
    ``Popen.kill()`` 强制终止它（POSIX 为 SIGKILL，Windows 为 TerminateProcess）。
    被强杀的进程**不会**执行 ``with PostgresSaver`` 的收尾、不会优雅关闭连接、
    不跑任何 atexit 钩子。因此本测试证明：checkpoint 的持久化**独立于进程生命周期**，
    恢复所需状态全部来自 PG，而非任何进程内残留。
    """
    import time

    dsn = _child_dsn(checkpoint_db)
    thread_id = "run-crash-proc::1"
    out_path = tmp_path / "crash_child.json"

    # ---- 阶段 1：独立进程跑到 interrupt，写出 sentinel 后阻塞 ----
    proc = subprocess.Popen(
        [sys.executable, "-c", CRASH_CHILD_SCRIPT.format(backend=str(BACKEND_DIR)), dsn, thread_id, str(out_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(BACKEND_DIR),
    )
    try:
        deadline = time.time() + 90
        while time.time() < deadline and not out_path.exists():
            time.sleep(0.2)
        assert out_path.exists(), "子进程未在超时内写出 sentinel（可能提前失败）"
        info = json.loads(out_path.read_text(encoding="utf-8"))
        assert info["interrupted"] is True, "子进程必须停在 interrupt"
        assert info["draft_ref"] == "draft:persisted", "checkpoint 必须已落盘"

        # 强制终止：无优雅退出、无清理钩子。
        assert proc.poll() is None, "此刻进程应仍在阻塞，尚未退出"
        proc.kill()
        proc.wait(timeout=30)
        assert proc.returncode != 0, "被强杀的进程必须返回非零退出码"
    finally:
        if proc.poll() is None:
            proc.kill()

    # ---- 阶段 2：新进程恢复（状态只可能来自 PG，且上一位进程未做任何清理）----
    from tests.helpers.retained_planning_graph import build_planning_graph
    from tests.helpers.retained_planning_graph import TransitionNodes as PlanningNodes
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
        pre = graph.get_state(cfg)
        assert pre.values.get("draft_ref") == "draft:persisted", "必须从 PG 恢复出草案引用"
        assert pre.next, "必须记录恢复点"

        graph.invoke(Command(resume="approve"), cfg)
        after = graph.get_state(cfg)
        assert len(committed) == 1, "崩溃后恢复仍必须完成发布"
        assert not after.next, "approve 后必须到终态"
        assert saved_again == [], "恢复不得重新生成草案"


def test_I_repeated_resume_no_duplicate_side_effects(checkpoint_db: PgTestDatabase) -> None:
    """I：对同一 thread 重复 resume 不得重复发布。"""
    from tests.helpers.retained_planning_graph import build_planning_graph
    from tests.helpers.retained_planning_graph import TransitionNodes as PlanningNodes
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
    from tests.helpers.retained_planning_graph import build_planning_graph
    from tests.helpers.retained_planning_graph import TransitionNodes as PlanningNodes
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
    from tests.helpers.retained_planning_graph import build_planning_graph
    from tests.helpers.retained_planning_graph import TransitionNodes as PlanningNodes
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
