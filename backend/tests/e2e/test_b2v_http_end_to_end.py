"""B2-V §七 真实端到端验收：TestClient + **真实 PostgreSQL**。

覆盖（Goal §七 逐条）：

1. 建目标 → 生成合法草案 → 运行状态正确 → 查看完整草案 → 编辑 → 重新校验
   → 确认 → 回读完整计划；
2. 过期哈希确认被拒；
3. 重复确认不产生第二份计划（同键同体返回**原结果**）；
4. 同键异体 → 409；
5. 取消与发布互斥（先发布后取消被拒 / 先取消后发布被拒 / 真并发恰好一个成功）；
6. 跨用户、跨项目访问被拒（403）；
7. 进程重启后仍可完成确认（状态在数据库，不在内存）；
8. 缺少公共资源时**显式降级**为搜索建议（不编造已核验章节）；
9. 重规划保留旧版本结构与历史完成记录。

## 关键一致性断言

    HTTP 草案展示内容 == 用户确认内容 == 数据库正式版本 == GET /plans/current 结构

这条断言把「界面看到的」「确认的」「落库的」「读回的」四处对齐，
是 B2-V 最核心的验收点。

所有操作限定在 ``studyplan_test_*`` 临时库，结束即删库。
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.postgres

psycopg = pytest.importorskip("psycopg")

BACKEND_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND_DIR))

from app.application.container import AppContainer  # noqa: E402
from app.application.plan_service import PlanService  # noqa: E402
from app.application.sessions import InMemorySessionStore, SessionRecord  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.infrastructure.db import (  # noqa: E402
    PgPlanningCatalog,
    PgPlanRepository,
    PgPublicResourceCatalog,
    PgRunRepository,
)
from app.infrastructure.providers.fake import FakeLLM  # noqa: E402

from tests.pg_harness import PgTestDatabase, create_test_database  # noqa: E402

# ---------------------------------------------------------------- 固定标识

PROJECT_P1 = "b2v_p1"
PROJECT_P2 = "b2v_p2"
ACTOR_A1 = "b2v_a1"
ACTOR_A2 = "b2v_a2"

SESSION_A1 = "b2v-session-a1"
SESSION_A2 = "b2v-session-a2"

COOKIE = "studyplan_session"

#: 真实存在的公共资源（B2-V §五：``source_ref`` 必须能核验）。
PUBLIC_SOURCE = "src_b2v_public"
PUBLIC_SECTIONS = ("sec_b2v_1", "sec_b2v_2")
#: 受审核清单内、但**故意不写入**测试库的来源：用于验证「显式降级」。
MISSING_SOURCE = "src_b2v_missing"
MISSING_SECTION = "sec_b2v_ghost"

GOAL_A = "我想学会用 Agent 做一个 PDF 知识助手"
GOAL_B = "我想学会用 Python 做数据分析"

V1 = "/api/v1"


# ------------------------------------------------------------------ 夹具


def _run_alembic(db: PgTestDatabase, *args: str) -> subprocess.CompletedProcess[str]:
    dsn = db.migrator_dsn.replace("postgresql://", "postgresql+psycopg://")
    env = dict(os.environ, STUDYPLAN_MIGRATION_DSN=dsn)
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=str(BACKEND_DIR),
        env=env,
        capture_output=True,
        text=True,
    )


@pytest.fixture(scope="module")
def migrated_db() -> PgTestDatabase:
    db = create_test_database(prefix="studyplan_test_b2v")
    result = _run_alembic(db, "upgrade", "head")
    assert result.returncode == 0, f"alembic upgrade 失败：{result.stderr}"
    with psycopg.connect(db.migrator_dsn, autocommit=True) as conn:
        conn.execute(
            "INSERT INTO learning_projects"
            "(project_id,owner_actor_id,title,goal_statement,stable_key) VALUES "
            "(%s,%s,'学习空间一','目标一','sk-b2v-p1'), "
            "(%s,%s,'学习空间二','目标二','sk-b2v-p2')",
            (PROJECT_P1, ACTOR_A1, PROJECT_P2, ACTOR_A2),
        )
        conn.execute(
            "INSERT INTO public_resource_sources"
            "(source_id,canonical_url,title,creator,media_type,language,source_version) "
            "VALUES (%s,'https://example.com/b2v-course','B2V 示例课程','示例作者','course','zh',1)",
            (PUBLIC_SOURCE,),
        )
        conn.execute(
            "INSERT INTO public_resource_sections"
            "(section_id,source_id,order_index,title,url,anchor) VALUES "
            "(%s,%s,0,'第一章 环境','https://example.com/b2v-course#1','c1'), "
            "(%s,%s,1,'第二章 第一个脚本','https://example.com/b2v-course#2','c2')",
            (PUBLIC_SECTIONS[0], PUBLIC_SOURCE, PUBLIC_SECTIONS[1], PUBLIC_SOURCE),
        )
    try:
        yield db
    finally:
        db.drop()


#: 每个测试前清空业务表（保留 learning_projects 与公共资源）。
_PLAN_TABLES = (
    "ai_jobs",
    "ai_runs",
    "plan_task_knowledge_links",
    "summary_attempts",
    "plan_publications",
    "plan_drafts",
    "plan_revisions",
    "knowledge_extensions",
    "stage_resource_assignments",
    "plan_stages",
    "plan_unit_links",
    "plan_task_links",
    "practice_tasks",
    "practice_projects",
    "unit_node_links",
    "knowledge_relations",
    "knowledge_nodes",
    "learning_units",
)


@pytest.fixture()
def db(migrated_db: PgTestDatabase) -> PgTestDatabase:
    with psycopg.connect(migrated_db.migrator_dsn, autocommit=True) as conn:
        conn.execute("TRUNCATE " + ", ".join(_PLAN_TABLES) + " CASCADE")
    return migrated_db


# -------------------------------------------------------------- 测试领域包
#
# 本套用例验收的是「草案 → 确认 → 发布」链路，而不是领域包的规模。因此显式注入
# 一个**两阶段**的受审核包，使生成的批次与断言一一对应；生产组合根仍使用
# ``select_domain_pack``（Agent 方向为九阶段）。
#
# ``MISSING_SOURCE`` 出现在受审核清单与本包 ``resources`` 中，但**不写入**测试库：
# 因此落库前必须显式降级为搜索建议，绝不编造已核验章节。

_B2V_PACK: dict[str, Any] = {
    "pack_key": "b2v.test",
    "version": 1,
    "title": "B2V 测试路线",
    "resource_support": "reviewed_index",
    "resource_refs": [PUBLIC_SOURCE, MISSING_SOURCE],
    "required_node_keys": ["node.python.env", "node.pdf.parse"],
    "stage_blueprints": [
        {
            "stable_key": "stage.foundation",
            "title": "基础准备",
            "section_kind": "foundation",
            "objective": "搭好环境，能跑通第一个脚本",
            "node_keys": ["node.python.env"],
        },
        {
            "stable_key": "stage.core",
            "title": "核心实现",
            "section_kind": "core",
            "objective": "实现 PDF 文本解析",
            "node_keys": ["node.pdf.parse"],
        },
    ],
    "knowledge_blueprints": [
        {
            "stable_key": "node.python.env",
            "title": "环境搭建",
            "node_type": "skill",
            "objectives": ["能安装依赖并运行脚本"],
        },
        {
            "stable_key": "node.pdf.parse",
            "title": "PDF 文本解析",
            "node_type": "skill",
            "objectives": ["能读出示例 PDF 的文本"],
            "prerequisite_keys": ["node.python.env"],
        },
    ],
    "resources": [
        {
            "source_id": PUBLIC_SOURCE,
            "canonical_url": "https://example.com/b2v-course",
            "title": "B2V 示例课程",
            "creator": "示例作者",
            "media_type": "course",
            "language": "zh",
            "source_version": 1,
            "documentation_version": "B2V v1",
            "verification_status": "reviewed",
            "checked_at": "2026-09-29T00:00:00Z",
            "sections": [
                {
                    "section_id": PUBLIC_SECTIONS[0],
                    "title": "第一章 环境",
                    "url": "https://example.com/b2v-course#1",
                    "order_index": 0,
                    "verification_status": "reviewed",
                    "checked_at": "2026-09-29T00:00:00Z",
                    "applicable_node_keys": ["node.python.env"],
                },
                {
                    "section_id": PUBLIC_SECTIONS[1],
                    "title": "第二章 第一个脚本",
                    "url": "https://example.com/b2v-course#2",
                    "order_index": 1,
                    "verification_status": "reviewed",
                    "checked_at": "2026-09-29T00:00:00Z",
                    "applicable_node_keys": ["node.python.env"],
                },
            ],
        },
        {
            "source_id": MISSING_SOURCE,
            "canonical_url": "https://example.com/b2v-missing",
            "title": "不存在的示例来源",
            "creator": "示例作者",
            "media_type": "course",
            "language": "zh",
            "source_version": 0,
            "documentation_version": "",
            "verification_status": "reviewed",
            "checked_at": "2026-09-29T00:00:00Z",
            "sections": [
                {
                    "section_id": MISSING_SECTION,
                    "title": "幽灵章节",
                    "url": "https://example.com/b2v-missing#1",
                    "order_index": 0,
                    "verification_status": "reviewed",
                    "checked_at": "2026-09-29T00:00:00Z",
                    "applicable_node_keys": ["node.pdf.parse"],
                }
            ],
        },
    ],
}


def _select_test_pack(goal: str) -> dict[str, Any]:
    return deepcopy(_B2V_PACK)


# -------------------------------------------------------------- Fake LLM


def _outline_handler(purpose: str, payload: dict[str, object]) -> dict[str, object]:
    """纲要：按冻结清单逐阶段生成骨架；一个阶段的主线来源不存在（验证降级）。"""
    manifest = payload.get("manifest") or {}
    goal = str(payload.get("goal") or "").strip()
    titles = {
        "stage.foundation": f"基础准备·{goal[:8]}",
        "stage.core": f"核心实现·{goal[:8]}",
    }
    resources = {
        "stage.foundation": [
            {
                "role": "primary",
                "source_ref": PUBLIC_SOURCE,
                "section_refs": list(PUBLIC_SECTIONS),
                "order_index": 0,
                "source_version": 1,
                "fallback_search_terms": [],
            }
        ],
        "stage.core": [
            {
                "role": "primary",
                # 该来源在公共目录里**不存在** → 必须降级为搜索建议。
                "source_ref": MISSING_SOURCE,
                "section_refs": [MISSING_SECTION],
                "order_index": 0,
                "source_version": 0,
                "fallback_search_terms": [],
            }
        ],
    }
    extensions = {
        "stage.foundation": [
            {
                "topic": "关系型数据库认识与对比",
                "concepts": ["基本特点", "典型适用场景"],
                "guidance": "了解 SQLite / PostgreSQL / MySQL 的典型适用场景",
                "links": [],
                "search_hints": ["关系型数据库对比 入门"],
                "thinking_prompts": ["多人同时写入？"],
                "required": False,
                "order_index": 0,
            }
        ],
    }
    sections = []
    for spec in manifest.get("stages") or []:
        key = str(spec.get("stage_key") or "")
        sections.append(
            {
                "stable_key": key,
                "title": titles.get(key, str(spec.get("title") or key)),
                "section_kind": spec.get("section_kind") or "core",
                "objective": spec.get("objective") or "",
                "resources": deepcopy(resources.get(key, [])),
                "extensions": deepcopy(extensions.get(key, [])),
            }
        )
    return {"outline_ref": "outline:1", "sections": sections}


def _structure_handler(purpose: str, payload: dict[str, object]) -> dict[str, object]:
    """单个阶段的结构批次（一个请求只回答一个批次）。"""
    stage = payload["stage"]
    if stage["stable_key"] == "stage.foundation":
        return {
            "nodes": [
                {
                    "stable_key": "node.python.env",
                    "title": "环境搭建",
                    "node_type": "skill",
                    "objectives": ["能安装依赖并运行脚本"],
                }
            ],
            "units": [
                {
                    "stable_key": "unit.python.basics",
                    "title": "Python 基础",
                    "section_key": "stage.foundation",
                    "order_index": 0,
                    "node_keys": ["node.python.env"],
                    "objectives": ["能安装依赖并运行脚本"],
                }
            ],
            "relations": [],
        }
    return {
        "nodes": [
            {
                "stable_key": "node.pdf.parse",
                "title": "PDF 文本解析",
                "node_type": "skill",
                "objectives": ["能读出示例 PDF 的文本"],
            }
        ],
        "units": [
            {
                "stable_key": "unit.pdf.parse",
                "title": "PDF 解析",
                "section_key": "stage.core",
                "order_index": 0,
                "node_keys": ["node.pdf.parse"],
                "objectives": ["能读出示例 PDF 的文本"],
            }
        ],
        "relations": [
            {
                "from_stable_key": "node.python.env",
                "to_stable_key": "node.pdf.parse",
                "relation_type": "prerequisite",
            }
        ],
    }


def _practice_handler(purpose: str, payload: dict[str, object]) -> dict[str, object]:
    """单个阶段的实践批次（一个请求只回答一个批次）。"""
    stage = payload["stage"]
    if stage["stable_key"] == "stage.foundation":
        return {
            "stable_key": "practice.foundation",
            "title": "环境实践",
            "idea": "搭好可复现的 Python 环境",
            "tasks": [
                {
                    "stable_key": "task.env",
                    "title": "搭建开发环境",
                    "goal": "安装依赖并跑通第一个脚本",
                    "section_key": "stage.foundation",
                    "order_index": 0,
                    "in_scope": ["虚拟环境与依赖"],
                    "out_scope": ["生产部署"],
                    "acceptance": ["能复现一次依赖安装并运行脚本"],
                    "knowledge_links": [{"node_stable_key": "node.python.env", "role": "core"}],
                }
            ],
            "task_knowledge_links": [
                {"task_stable_key": "task.env", "node_stable_key": "node.python.env", "role": "core"}
            ],
        }
    return {
        "stable_key": "practice.pdf_helper",
        "title": "PDF 知识助手",
        "idea": "做一个能把 PDF 转成问答的助手",
        "tasks": [
            {
                "stable_key": "task.parse",
                "title": "实现 PDF 解析",
                "goal": "读取本地 PDF 并输出纯文本",
                "section_key": "stage.core",
                "order_index": 0,
                "in_scope": ["文本抽取"],
                "out_scope": ["版面还原"],
                "acceptance": ["能对示例 PDF 输出非空文本"],
                "knowledge_links": [{"node_stable_key": "node.pdf.parse", "role": "core"}],
            }
        ],
        "task_knowledge_links": [
            {"task_stable_key": "task.parse", "node_stable_key": "node.pdf.parse", "role": "core"}
        ],
    }


def _fake_llm() -> FakeLLM:
    return FakeLLM(
        {
            "planning.outline": _outline_handler,
            "planning.structure": _structure_handler,
            "planning.practice": _practice_handler,
        }
    )


# ------------------------------------------------------------------ 装配


def _container(db: PgTestDatabase, *, llm: FakeLLM | None = None) -> AppContainer:
    """按真实 PG 装配容器（模拟生产组合根，只是仓储指向临时库）。"""
    settings = get_settings()
    sessions = InMemorySessionStore(
        (
            SessionRecord(
                token=SESSION_A1,
                actor_id=ACTOR_A1,
                session_id="sess_a1",
                learning_project_scope=(PROJECT_P1,),
            ),
            SessionRecord(
                token=SESSION_A2,
                actor_id=ACTOR_A2,
                session_id="sess_a2",
                learning_project_scope=(PROJECT_P2,),
            ),
        )
    )
    from app.infrastructure.db.job_repository import PgPlanningJobRepository
    from app.infrastructure.worker.planning_worker import PlanningWorker

    worker_actors = (ACTOR_A1, ACTOR_A2)
    jobs = PgPlanningJobRepository(db.app_dsn, actor_ids=worker_actors)
    service = PlanService(
        repository=PgPlanRepository(db.app_dsn),
        runs=PgRunRepository(db.app_dsn),
        catalog=PgPlanningCatalog(db.app_dsn),
        resources=PgPublicResourceCatalog(db.app_dsn),
        llm=llm or _fake_llm(),
        graph_version=settings.graph_version,
        planning_jobs=jobs,
        worker_actor_ids=worker_actors,
        domain_pack_selector=_select_test_pack,
    )
    worker = PlanningWorker(jobs=jobs, execute=service.execute_generation,
                            actor_ids=worker_actors, lease_seconds=30)
    return AppContainer(settings=settings, sessions=sessions, plan_service=service, planning_worker=worker)


def _client(db: PgTestDatabase, *, llm: FakeLLM | None = None, cookie: str = SESSION_A1):
    from app.main import create_app
    from fastapi.testclient import TestClient

    app = create_app(_container(db, llm=llm))
    client = TestClient(app)
    client.cookies.set(COOKIE, cookie)
    return client


# --------------------------------------------------------------- 小工具


def _generate(client, *, goal: str = GOAL_A, project_id: str = PROJECT_P1) -> dict[str, Any]:
    resp = client.post(
        f"{V1}/plans/generate",
        params={"project_id": project_id},
        json={"goal": goal, "prefs_snapshot": {"mode": "text_first", "language": "zh"}},
    )
    assert resp.status_code == 202, resp.text
    # Existing synchronous end-to-end scenarios explicitly drive the Worker;
    # the async-generation test posts directly and proves it remains queued.
    worker = getattr(client, "planning_worker", None)
    if worker is None:
        worker = client.app.state.container.planning_worker
    assert worker.tick()
    return resp.json()


def _get_run(client, run_id: str, *, project_id: str = PROJECT_P1) -> dict[str, Any]:
    resp = client.get(f"{V1}/runs/{run_id}", params={"project_id": project_id})
    assert resp.status_code == 200, resp.text
    return resp.json()


def _get_draft(client, draft_id: str, *, project_id: str = PROJECT_P1) -> dict[str, Any]:
    resp = client.get(f"{V1}/plans/drafts/{draft_id}", params={"project_id": project_id})
    assert resp.status_code == 200, resp.text
    return resp.json()


def _decide(
    client,
    draft_id: str,
    body: dict[str, Any],
    *,
    project_id: str = PROJECT_P1,
):
    return client.post(
        f"{V1}/plans/drafts/{draft_id}/decision",
        params={"project_id": project_id},
        json=body,
    )


def _generate_to_draft(client, *, goal: str = GOAL_A, project_id: str = PROJECT_P1):
    """生成并返回 ``(run, draft)``。"""
    run = _generate(client, goal=goal, project_id=project_id)
    run_view = _get_run(client, run["run_id"], project_id=project_id)
    assert run_view["status"] == "waiting_user", run_view
    draft = _get_draft(client, run_view["result_ref"], project_id=project_id)
    return run_view, draft


# ================================================================= 主链路


def test_full_chain_generate_edit_approve_readback(db: PgTestDatabase) -> None:
    """建目标 → 生成 → 查看 → 编辑 → 重新校验 → 确认 → 回读完整计划。"""
    client = _client(db)

    # 1) 生成
    run = _generate(client)
    run_view = _get_run(client, run["run_id"])
    assert run_view["status"] == "waiting_user"
    assert run_view["next_action"] == "review_draft"
    assert run_view["version"] == 3, "create(1) → Worker claim(2) → waiting_user(3)"
    draft_id = run_view["result_ref"]
    assert draft_id.startswith("drf_")

    # 2) 查看完整草案
    draft = _get_draft(client, draft_id)
    assert draft["status"] == "awaiting_approval"
    assert draft["project_id"] == PROJECT_P1
    assert [s["stable_key"] for s in draft["stages"]] == ["stage.foundation", "stage.core"]
    assert len(draft["unit_links"]) == 2 and len(draft["task_links"]) == 2
    assert draft["extensions"][0]["topic"] == "关系型数据库认识与对比"

    # 3) 编辑：改第一个阶段标题（必须完整覆盖全部阶段）
    edited = [dict(s) for s in draft["stages"]]
    edited[0]["title"] = "基础准备（用户已改）"
    resp = _decide(
        client,
        draft_id,
        {"decision": "edit", "expected_version": 0, "draft_hash": draft["draft_hash"], "edited_stages": edited},
    )
    assert resp.status_code == 200, resp.text
    edited_body = resp.json()
    assert edited_body["draft"]["status"] == "awaiting_approval", "编辑后必须重新等待确认"
    assert edited_body["plan"] is None, "编辑不发布"
    new_hash = edited_body["draft"]["draft_hash"]
    assert new_hash != draft["draft_hash"], "编辑必须改变草案哈希"

    # 4) 重新校验后的草案可读回
    draft2 = _get_draft(client, draft_id)
    assert draft2["stages"][0]["title"] == "基础准备（用户已改）"
    assert draft2["draft_hash"] == new_hash

    # 5) 确认发布
    resp = _decide(
        client,
        draft_id,
        {
            "decision": "approve",
            "expected_version": 0,
            "draft_hash": new_hash,
            "idempotency_key": "idem-main",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["draft"]["status"] == "approved"
    plan = body["plan"]
    assert plan is not None and plan["status"] == "approved" and plan["revision"] == 1

    # 6) 运行状态 → succeeded
    run_after = _get_run(client, run["run_id"])
    assert run_after["status"] == "succeeded"
    assert run_after["next_action"] == "none"
    assert run_after["result_ref"] == plan["plan_id"]

    # 7) 当前路线读回，且与「确认的结构」逐字段一致（核心断言）
    current = client.get(f"{V1}/plans/current", params={"project_id": PROJECT_P1}).json()
    assert current["plan_id"] == plan["plan_id"]
    assert current["revision"] == 1
    assert [s["stable_key"] for s in current["stages"]] == ["stage.foundation", "stage.core"]
    assert [s["title"] for s in current["stages"]] == [
        "基础准备（用户已改）",
        "核心实现·我想学会用 Ag",
    ]
    assert len(current["unit_links"]) == 2
    assert len(current["task_links"]) == 2
    assert len(current["extensions"]) == 1
    assert current["goal_snapshot"] == GOAL_A

    # 阶段资源：主线章节按作者原顺序 + 一个显式降级条目
    resources = {r["stage_id"]: r for r in current["stage_resources"]}
    stage_by_key = {s["stable_key"]: s["stage_id"] for s in current["stages"]}
    ok = resources[stage_by_key["stage.foundation"]]
    assert ok["source_ref"] == PUBLIC_SOURCE
    assert [s["title"] for s in ok["ordered_sections"]] == ["第一章 环境", "第二章 第一个脚本"]
    assert ok["fallback_search_terms"] == []


def test_draft_view_and_current_plan_agree_on_resources(db: PgTestDatabase) -> None:
    """HTTP 草案展示的已核验资源 == 发布后读回的正式版本资源（§五 + §七）。"""
    client = _client(db)
    _, draft = _generate_to_draft(client)

    resp = _decide(
        client,
        draft["draft_id"],
        {
            "decision": "approve",
            "expected_version": 0,
            "draft_hash": draft["draft_hash"],
            "idempotency_key": "idem-res",
        },
    )
    assert resp.status_code == 200, resp.text
    published = resp.json()["plan"]

    def links_by_stable_key(items, field, keymap):
        return sorted((keymap[i["stage_id"]], i[field]) for i in items)

    # 阶段 ID 每版重新生成，因此按 ``stable_key`` 对齐后再比较引用。
    draft_stage_key = {s["stage_id"]: s["stable_key"] for s in draft["stages"]}
    plan_stage_key = {s["stage_id"]: s["stable_key"] for s in published["stages"]}

    assert links_by_stable_key(
        draft["unit_links"], "unit_id", draft_stage_key
    ) == links_by_stable_key(published["unit_links"], "unit_id", plan_stage_key)
    assert links_by_stable_key(
        draft["task_links"], "task_id", draft_stage_key
    ) == links_by_stable_key(published["task_links"], "task_id", plan_stage_key)
    # 资源：章节集合与搜索建议必须一致（stage_id 每版重新生成，故按内容比较）
    draft_sections = sorted(
        s["title"] for r in draft["stage_resources"] for s in r["ordered_sections"]
    )
    plan_sections = sorted(
        s["title"] for r in published["stage_resources"] for s in r["ordered_sections"]
    )
    assert draft_sections == plan_sections == ["第一章 环境", "第二章 第一个脚本"]


# =========================================================== 显式降级（§五）


def test_missing_public_resource_degrades_explicitly(db: PgTestDatabase) -> None:
    """缺少公共资源时**只给搜索建议**，绝不编造已核验章节。"""
    client = _client(db)
    _, draft = _generate_to_draft(client)

    stage_by_key = {s["stable_key"]: s["stage_id"] for s in draft["stages"]}
    core_stage = stage_by_key["stage.core"]
    degraded = next(r for r in draft["stage_resources"] if r["stage_id"] == core_stage)

    assert degraded["ordered_sections"] == [], "不得编造未核验章节"
    assert degraded["source_ref"] == "", "不存在的来源不得被写入"
    assert degraded["fallback_search_terms"], "必须给出搜索建议"
    assert "入门教程" in degraded["fallback_search_terms"][0]

    # 落库的正式版本同样是降级结果（不因发布而"变回"已核验）。
    resp = _decide(
        client,
        draft["draft_id"],
        {
            "decision": "approve",
            "expected_version": 0,
            "draft_hash": draft["draft_hash"],
            "idempotency_key": "idem-degraded",
        },
    )
    assert resp.status_code == 200, resp.text
    published = resp.json()["plan"]
    published_core = next(
        r
        for r in published["stage_resources"]
        if r["stage_id"]
        == {s["stable_key"]: s["stage_id"] for s in published["stages"]}["stage.core"]
    )
    assert published_core["ordered_sections"] == []
    assert published_core["fallback_search_terms"] == degraded["fallback_search_terms"]


# ================================================================== 幂等


def test_repeated_confirmation_does_not_republish(db: PgTestDatabase) -> None:
    """同一幂等键 + 同一体：重复确认返回**原结果**，不产生第二份计划。"""
    client = _client(db)
    _, draft = _generate_to_draft(client)
    body = {
        "decision": "approve",
        "expected_version": 0,
        "draft_hash": draft["draft_hash"],
        "idempotency_key": "idem-dup",
    }

    first = _decide(client, draft["draft_id"], body)
    assert first.status_code == 200, first.text
    second = _decide(client, draft["draft_id"], body)
    assert second.status_code == 200, second.text
    assert first.json()["plan"]["plan_id"] == second.json()["plan"]["plan_id"]
    assert first.json()["plan"]["revision"] == second.json()["plan"]["revision"] == 1

    revisions = client.get(f"{V1}/plans/current", params={"project_id": PROJECT_P1}).json()
    assert revisions["revision"] == 1, "重复确认不得产生第二份计划"
    assert revisions["status"] == "approved"


def test_same_key_different_body_is_conflict(db: PgTestDatabase) -> None:
    """同键异体 → 409（幂等冲突）。"""
    client = _client(db)
    _, draft_a = _generate_to_draft(client, goal=GOAL_A)
    _, draft_b = _generate_to_draft(client, goal=GOAL_B)

    ok = _decide(
        client,
        draft_a["draft_id"],
        {
            "decision": "approve",
            "expected_version": 0,
            "draft_hash": draft_a["draft_hash"],
            "idempotency_key": "idem-shared",
        },
    )
    assert ok.status_code == 200, ok.text

    conflict = _decide(
        client,
        draft_b["draft_id"],
        {
            "decision": "approve",
            "expected_version": 1,
            "draft_hash": draft_b["draft_hash"],
            "idempotency_key": "idem-shared",
        },
    )
    assert conflict.status_code == 409, conflict.text
    assert conflict.json()["code"] == "idempotency_conflict"


def test_stale_draft_hash_is_rejected(db: PgTestDatabase) -> None:
    """过期哈希确认被拒（防确认期间草案被改写）。"""
    client = _client(db)
    _, draft = _generate_to_draft(client)

    # 编辑一次，使草案内容变化；旧 hash 立即失效。
    edited = [dict(s) for s in draft["stages"]]
    edited[0]["title"] = "改过的标题"
    assert (
        _decide(
            client, draft["draft_id"], {"decision": "edit", "expected_version": 0, "draft_hash": draft["draft_hash"], "edited_stages": edited}
        ).status_code
        == 200
    )

    stale = _decide(
        client,
        draft["draft_id"],
        {
            "decision": "approve",
            "expected_version": 0,
            "draft_hash": draft["draft_hash"],  # 旧哈希
            "idempotency_key": "idem-stale",
        },
    )
    assert stale.status_code == 409, stale.text
    assert stale.json()["code"] == "conflict"
    # 仍然没有正式路线
    assert client.get(f"{V1}/plans/current", params={"project_id": PROJECT_P1}).status_code == 404


# ============================================================ 取消 / 发布互斥


def test_cancel_then_approve_is_rejected(db: PgTestDatabase) -> None:
    """先取消 → 再发布：发布被拒，且不产生正式路线。"""
    client = _client(db)
    _, draft = _generate_to_draft(client)
    cancelled = _decide(
        client, draft["draft_id"], {"decision": "cancel", "expected_version": 0}
    )
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["draft"]["status"] == "cancelled"

    rejected = _decide(
        client,
        draft["draft_id"],
        {
            "decision": "approve",
            "expected_version": 0,
            "draft_hash": draft["draft_hash"],
            "idempotency_key": "idem-after-cancel",
        },
    )
    assert rejected.status_code == 409, rejected.text
    assert client.get(f"{V1}/plans/current", params={"project_id": PROJECT_P1}).status_code == 404


def test_approve_then_cancel_is_rejected(db: PgTestDatabase) -> None:
    """先发布 → 再取消：取消被拒，正式路线不受影响。"""
    client = _client(db)
    _, draft = _generate_to_draft(client)
    approved = _decide(
        client,
        draft["draft_id"],
        {
            "decision": "approve",
            "expected_version": 0,
            "draft_hash": draft["draft_hash"],
            "idempotency_key": "idem-then-cancel",
        },
    )
    assert approved.status_code == 200, approved.text

    rejected = _decide(client, draft["draft_id"], {"decision": "cancel", "expected_version": 1})
    assert rejected.status_code == 409, rejected.text
    current = client.get(f"{V1}/plans/current", params={"project_id": PROJECT_P1})
    assert current.status_code == 200 and current.json()["status"] == "approved"


def test_concurrent_cancel_and_publish_exactly_one_wins(db: PgTestDatabase) -> None:
    """真并发：取消与发布恰好一个成功。"""
    client = _client(db)
    _, draft = _generate_to_draft(client)

    results: list[str] = []
    barrier = threading.Barrier(2, timeout=20)

    def publish() -> None:
        c = _client(db)
        barrier.wait()
        r = _decide(
            c,
            draft["draft_id"],
            {
                "decision": "approve",
                "expected_version": 0,
                "draft_hash": draft["draft_hash"],
                "idempotency_key": "idem-race",
            },
        )
        results.append("published" if r.status_code == 200 else f"publish-{r.status_code}")

    def cancel() -> None:
        c = _client(db)
        barrier.wait()
        r = _decide(c, draft["draft_id"], {"decision": "cancel", "expected_version": 0})
        results.append("cancelled" if r.status_code == 200 else f"cancel-{r.status_code}")

    threads = [threading.Thread(target=publish), threading.Thread(target=cancel)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    assert len(results) == 2, f"并发结果缺失：{results}"
    succeeded = [r for r in results if r in {"published", "cancelled"}]
    assert len(succeeded) == 1, f"取消与发布必须恰好一个成功：{results}"


# ================================================================== 授权


def test_other_user_cannot_access_project(db: PgTestDatabase) -> None:
    """跨用户：a2 的会话访问 p1 → 403（不区分"不存在"与"无权限"）。"""
    client = _client(db, cookie=SESSION_A2)
    resp = client.get(f"{V1}/plans/current", params={"project_id": PROJECT_P1})
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "forbidden"


def test_owner_cannot_access_other_project(db: PgTestDatabase) -> None:
    """跨项目：a1 的会话访问 p2 → 403。"""
    client = _client(db, cookie=SESSION_A1)
    resp = client.post(
        f"{V1}/plans/generate",
        params={"project_id": PROJECT_P2},
        json={"goal": GOAL_A},
    )
    assert resp.status_code == 403, resp.text


def test_unauthenticated_request_is_rejected(db: PgTestDatabase) -> None:
    """无会话 Cookie → 401（绝不退化为匿名上下文）。"""
    from app.main import create_app
    from fastapi.testclient import TestClient

    app = create_app(_container(db))
    with TestClient(app) as client:  # 不设置 Cookie
        resp = client.get(f"{V1}/plans/current", params={"project_id": PROJECT_P1})
    assert resp.status_code == 401, resp.text
    assert resp.json()["code"] == "unauthenticated"


def test_auth_context_cannot_be_spoofed_from_body(db: PgTestDatabase) -> None:
    """请求体里的 actor_id / 项目授权字段被拒绝（extra=forbid），不产生任何数据。"""
    client = _client(db)
    resp = client.post(
        f"{V1}/plans/generate",
        params={"project_id": PROJECT_P1},
        json={"goal": GOAL_A, "actor_id": ACTOR_A2, "tenant_id": "x"},
    )
    assert resp.status_code == 422, resp.text
    assert client.get(f"{V1}/plans/current", params={"project_id": PROJECT_P1}).status_code == 404


# ============================================================ 进程重启恢复


def test_pending_draft_survives_process_restart(db: PgTestDatabase) -> None:
    """进程重启后仍可完成确认：状态在数据库，不在内存。"""
    client = _client(db)
    run, draft = _generate_to_draft(client)

    # 模拟重启：全新的应用实例与容器（新的 PlanService / 仓储对象 / 会话存储）。
    restarted = _client(db)
    assert _get_run(restarted, run["run_id"])["status"] == "waiting_user"
    revived = _get_draft(restarted, draft["draft_id"])
    assert revived["draft_hash"] == draft["draft_hash"], "重启后草案内容与哈希不变"

    resp = _decide(
        restarted,
        draft["draft_id"],
        {
            "decision": "approve",
            "expected_version": 0,
            "draft_hash": revived["draft_hash"],
            "idempotency_key": "idem-restart",
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["plan"]["revision"] == 1
    assert _get_run(restarted, run["run_id"])["status"] == "succeeded"


# ============================================================ 重规划保留历史


def test_replanning_preserves_history_and_reads_back(db: PgTestDatabase) -> None:
    """重规划：旧版本结构仍可读回，历史完成记录不被删除。"""
    client = _client(db)
    _, draft1 = _generate_to_draft(client, goal=GOAL_A)
    first = _decide(
        client,
        draft1["draft_id"],
        {
            "decision": "approve",
            "expected_version": 0,
            "draft_hash": draft1["draft_hash"],
            "idempotency_key": "idem-v1",
        },
    )
    assert first.status_code == 200, first.text
    plan1 = first.json()["plan"]

    # 植入一条历史完成记录（重规划不得删除它）。
    unit_id = draft1["unit_links"][0]["unit_id"]
    with psycopg.connect(db.migrator_dsn, autocommit=True) as conn:
        conn.execute(
            "INSERT INTO summary_attempts"
            "(attempt_id,project_id,unit_id,content,attempt_no,rubric_version) "
            "VALUES ('sat_b2v_hist',%s,%s,'历史总结原文',1,1)",
            (PROJECT_P1, unit_id),
        )

    # 以不同目标重新规划并发布 v2
    _, draft2 = _generate_to_draft(client, goal=GOAL_B)
    assert draft2["revision"] == 2, "第二个草案应瞄准第 2 版"
    second = _decide(
        client,
        draft2["draft_id"],
        {
            "decision": "approve",
            "expected_version": 1,
            "draft_hash": draft2["draft_hash"],
            "idempotency_key": "idem-v2",
        },
    )
    assert second.status_code == 200, second.text
    plan2 = second.json()["plan"]
    assert plan2["revision"] == 2

    current = client.get(f"{V1}/plans/current", params={"project_id": PROJECT_P1}).json()
    assert current["plan_id"] == plan2["plan_id"] and current["revision"] == 2
    assert current["goal_snapshot"] == GOAL_B
    assert current["plan_id"] != plan1["plan_id"]

    # 历史完成记录仍在
    with psycopg.connect(db.migrator_dsn) as conn:
        rows = conn.execute(
            "SELECT attempt_id, content FROM summary_attempts WHERE project_id=%s",
            (PROJECT_P1,),
        ).fetchall()
    assert rows == [("sat_b2v_hist", "历史总结原文")], "重规划不得删除历史完成记录"

    # 旧版本仍可完整读回（结构不被改写）
    repo = PgPlanRepository(db.app_dsn)
    v1 = repo.get_revision(project_id=PROJECT_P1, revision=1)
    assert v1 is not None and v1.status.value == "superseded"
    assert len(v1.stages) == 2 and len(v1.unit_links) == 2
    assert [r.revision for r in repo.list_revisions(project_id=PROJECT_P1)] == [1, 2]


# ============================================================ 无效输入


def test_empty_goal_is_rejected_without_calling_model(db: PgTestDatabase) -> None:
    """空目标：**不调用模型**、不产生运行与草案，直接 400。"""
    client = _client(db)
    resp = client.post(
        f"{V1}/plans/generate",
        params={"project_id": PROJECT_P1},
        json={"goal": "   "},
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["code"] == "validation_error"
    assert client.get(f"{V1}/plans/current", params={"project_id": PROJECT_P1}).status_code == 404


def test_unknown_draft_and_run_are_not_found(db: PgTestDatabase) -> None:
    client = _client(db)
    assert client.get(f"{V1}/plans/drafts/drf_nope", params={"project_id": PROJECT_P1}).status_code == 404
    assert client.get(f"{V1}/runs/run_nope", params={"project_id": PROJECT_P1}).status_code == 404

# Targeted B2-V regressions: real HTTP + PostgreSQL.
def _approve_body(draft, version, key):
    return dict(decision="approve", expected_version=version,
                draft_hash=draft["draft_hash"], idempotency_key=key)


def test_regression_historical_replay(db):
    client = _client(db)
    _, first = _generate_to_draft(client)
    body = _approve_body(first, 0, "history-v1")
    v1 = _decide(client, first["draft_id"], body).json()["plan"]
    _, second = _generate_to_draft(client, goal=GOAL_B)
    v2 = _decide(client, second["draft_id"], _approve_body(second, 1, "history-v2"))
    assert v2.status_code == 200, v2.text
    assert v2.json()["plan"]["revision"] == 2
    replay = _decide(client, first["draft_id"], body)
    assert replay.status_code == 200, replay.text
    assert replay.json()["plan"]["plan_id"] == v1["plan_id"]
    assert replay.json()["plan"]["revision"] == 1


def test_regression_two_windows_and_old_content(db):
    client = _client(db)
    _, draft = _generate_to_draft(client)
    stages = [dict(s) for s in draft["stages"]]
    stages[0]["title"] = "new window"
    edit = dict(decision="edit", expected_version=0, draft_hash=draft["draft_hash"], edited_stages=stages)
    assert _decide(client, draft["draft_id"], edit).status_code == 200
    edit["edited_stages"] = draft["stages"]
    stale = _decide(client, draft["draft_id"], edit)
    assert stale.status_code == 409, stale.text
    assert _get_draft(client, draft["draft_id"])["stages"][0]["title"] == "new window"


def test_regression_concurrent_edit(db):
    from concurrent.futures import ThreadPoolExecutor
    _, draft = _generate_to_draft(_client(db))
    barrier = threading.Barrier(2)
    def edit(title):
        client = _client(db)
        stages = [dict(s) for s in draft["stages"]]
        stages[0]["title"] = title
        barrier.wait()
        return _decide(client, draft["draft_id"], dict(decision="edit", expected_version=0,
                       draft_hash=draft["draft_hash"], edited_stages=stages)).status_code
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(edit, ["one", "two"]))
    assert sorted(results) == [200, 409]


def test_regression_catalog_history_and_keys(db):
    from app.infrastructure.db.planning_catalog import stable_entity_id
    keys = ["a.b", "a_b", "a" * 80 + "x", "a" * 80 + "y"]
    assert len({stable_entity_id("nod", PROJECT_P1, k) for k in keys}) == 4
    client = _client(db)
    _, first = _generate_to_draft(client)
    assert _decide(client, first["draft_id"], _approve_body(first, 0, "immutable-v1")).status_code == 200
    def snapshot():
        with psycopg.connect(db.migrator_dsn) as conn:
            return {table: conn.execute(f"SELECT * FROM {table} ORDER BY 1").fetchall()
                    for table in ["knowledge_nodes", "learning_units", "practice_tasks", "practice_projects"]}
    before = snapshot()
    def changed_structure(purpose, payload):
        data = _structure_handler(purpose, payload)
        for node in data["nodes"]:
            node["title"] = "changed node"
            node["objectives"] = ["changed objective"]
        for unit in data["units"]:
            unit["title"] = "changed unit"
        return data
    def changed_practice(purpose, payload):
        data = _practice_handler(purpose, payload)
        data["title"] = "changed practice"
        data["tasks"][0]["goal"] = "changed task goal"
        data["tasks"][0]["acceptance"] = ["changed acceptance"]
        return data
    changed = FakeLLM(handlers={"planning.outline": _outline_handler,
                               "planning.structure": changed_structure,
                               "planning.practice": changed_practice})
    _, second = _generate_to_draft(_client(db, llm=changed), goal=GOAL_B)
    assert _decide(client, second["draft_id"], dict(decision="cancel", expected_version=1)).status_code == 200
    after = snapshot()
    for table, rows in before.items():
        by_id = {row[0]: row for row in after[table]}
        assert all(by_id[row[0]] == row for row in rows), table
    assert PgPlanRepository(db.app_dsn).get_revision(project_id=PROJECT_P1, revision=1) is not None


def test_regression_generation_exception_and_run_cas(db):
    from app.core.errors import ConflictError
    service = _container(db).plan_service
    def fail(**kwargs):
        raise RuntimeError("catalog write failed")
    service._catalog.materialize = fail
    from datetime import datetime, timezone

    from app.domain.workspace.models import AuthContext
    scope = AuthContext(actor_id=ACTOR_A1, session_id=SESSION_A1, issued_at=datetime.now(timezone.utc), learning_project_scope=(PROJECT_P1,))
    with pytest.raises(RuntimeError):
        service.generate(scope=scope, project_id=PROJECT_P1, goal=GOAL_A)
    with psycopg.connect(db.migrator_dsn) as conn:
        run_id, status, version = conn.execute("SELECT run_id,status,version FROM ai_runs").fetchone()
    assert status in {"failed", "reconciliation_required"}
    repo = PgRunRepository(db.app_dsn)
    with pytest.raises(ConflictError):
        repo.update_run(project_id=PROJECT_P1, run_id=run_id, expected_version=version-1,
                        status="running", next_action="wait")


def test_regression_unknown_dispatch_stops_and_reconciles(db):
    from datetime import datetime, timezone

    from app.domain.workspace.models import AuthContext
    from app.ports.llm import LLMDispatchUnknownError, LLMFailure
    llm = _fake_llm()
    def unknown(**kwargs):
        llm.calls.append((kwargs["run_id"], kwargs["attempt_id"], kwargs["purpose"]))
        return LLMFailure("timeout", "unknown", dispatch_unknown=True)
    llm.generate_structured = unknown
    service = _container(db, llm=llm).plan_service
    scope = AuthContext(ACTOR_A1, SESSION_A1, datetime.now(timezone.utc), (PROJECT_P1,))
    with pytest.raises(LLMDispatchUnknownError):
        service.generate(scope=scope, project_id=PROJECT_P1, goal=GOAL_A)
    with psycopg.connect(db.migrator_dsn) as conn:
        assert conn.execute("SELECT status,next_action FROM ai_runs").fetchone() == ("reconciliation_required", "reconcile")
    assert len(llm.calls) == 1


def test_regression_long_keys_and_legacy_ids_real_pg(db):
    keys = ["a.b", "a_b", "a" * 80 + "x", "a" * 80 + "y"]
    with psycopg.connect(db.migrator_dsn) as conn:
        conn.execute("INSERT INTO knowledge_nodes(node_id,project_id,stable_key,title,node_type,source_status) VALUES ('legacy_a_b',%s,'a.b','Confirmed legacy','concept','verified')", (PROJECT_P1,))
    result = PgPlanningCatalog(db.app_dsn).materialize(project_id=PROJECT_P1,
              nodes=[dict(stable_key=k, title=k) for k in keys], units=[], relations=[])
    assert len(set(result.node_ids.values())) == 4
    with psycopg.connect(db.migrator_dsn) as conn:
        assert conn.execute("SELECT stable_key,title,source_status FROM knowledge_nodes WHERE node_id='legacy_a_b'").fetchone() == ('a.b', 'Confirmed legacy', 'verified')
        assert conn.execute("SELECT count(*) FROM knowledge_nodes").fetchone()[0] == 5
