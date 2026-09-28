"""真实 PostgreSQL 端口契约验收：``PgPlanRepository``（B2-C §「真实 PG 端口契约」）。

## 与 fake-repo 测试的区分（Goal §「区分假仓储与 PG 结果」）

- **fake-repo 测试**：``tests/unit/test_plan_publication.py`` 用
  ``FakePlanRepository`` 验证**领域规则与发布编排**（不碰数据库）。
- **本文件**：验证**数据库层真实语义**——单事务原子性、DB 唯一约束幂等、
  并发下只有一个事务胜出、RLS 隔离。这些是内存 fake **无法**证明的属性，
  因此必须以真实 PG 为准。

所有操作限定在 ``studyplan_test_*`` 临时库，结束即删库。
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
from pathlib import Path

import pytest

pytestmark = pytest.mark.postgres

psycopg = pytest.importorskip("psycopg")

BACKEND_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND_DIR))

from app.domain.enums import OutlineSectionKind, StageResourceRole  # noqa: E402
from app.domain.planning.models import (  # noqa: E402
    PlanDraft,
    PlanRevision,
    PlanStage,
    PlanTaskLink,
    PlanUnitLink,
)
from app.domain.resources.curation import (  # noqa: E402
    KnowledgeExtension,
    StageResourceAssignment,
)
from app.infrastructure.db.plan_repository import PgPlanRepository  # noqa: E402

from tests.pg_harness import PgTestDatabase, create_test_database  # noqa: E402

PROJECT = "p1"


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
    db = create_test_database(prefix="studyplan_test_b2d")
    assert _run_alembic(db, "upgrade", "head").returncode == 0
    with psycopg.connect(db.migrator_dsn, autocommit=True) as conn:
        conn.execute(
            "INSERT INTO learning_projects(project_id,owner_actor_id,title,goal_statement,stable_key) "
            "VALUES ('p1','a1','t1','g1','sk-p1'), ('p2','a2','t2','g2','sk-p2')"
        )
    _seed_catalog(db, "p1")
    _seed_catalog(db, "p2")
    try:
        yield db
    finally:
        db.drop()


@pytest.fixture()
def repo(migrated_db: PgTestDatabase) -> PgPlanRepository:
    return PgPlanRepository(migrated_db.app_dsn)


def _clean(db: PgTestDatabase) -> None:
    with psycopg.connect(db.migrator_dsn, autocommit=True) as conn:
        conn.execute(
            "TRUNCATE plan_publications, plan_drafts, plan_revisions, "
            "knowledge_extensions, stage_resource_assignments, plan_stages, "
            "plan_unit_links, plan_task_links CASCADE"
        )


def _catalog_ids(project_id: str) -> dict[str, str]:
    """按项目派生被引用的稳定实体 ID。

    ``learning_units.unit_id`` 是**全局主键**，同一 unit_id 不能属于两个项目；
    而复合 FK 要求 ``(project_id, unit_id)`` 同属，因此每个项目需要自己的实体。
    """
    return {
        "unit_basic": f"unt_basic_{project_id}",
        "unit_rag": f"unt_rag_{project_id}",
        "practice_project": f"ppj_{project_id}",
        "task_pdf": f"ptk_pdf_{project_id}",
    }


def _seed_catalog(db: PgTestDatabase, project_id: str) -> None:
    """植入计划所引用的既有稳定实体（复合 FK 要求同项目存在）。"""
    ids = _catalog_ids(project_id)
    with psycopg.connect(db.migrator_dsn, autocommit=True) as conn:
        conn.execute(
            "INSERT INTO learning_units(unit_id,project_id,stable_key,title,objectives,rubric) "
            "VALUES (%s,%s,%s,'基础单元','[]'::jsonb,'{}'::jsonb), "
            "(%s,%s,%s,'RAG 单元','[]'::jsonb,'{}'::jsonb) ON CONFLICT DO NOTHING",
            (
                ids["unit_basic"], project_id, f"sk-ub-{project_id}",
                ids["unit_rag"], project_id, f"sk-ur-{project_id}",
            ),
        )
        conn.execute(
            "INSERT INTO practice_projects(practice_project_id,project_id,title,idea,status) "
            "VALUES (%s,%s,'实践项目','做一个 PDF 助手','idea') ON CONFLICT DO NOTHING",
            (ids["practice_project"], project_id),
        )
        conn.execute(
            "INSERT INTO practice_tasks"
            "(task_id,project_id,practice_project_id,stable_key,title,goal,acceptance,status) "
            "VALUES (%s,%s,%s,%s,'PDF 任务','实现 PDF 解析','[\"能解析\"]'::jsonb,'pending') "
            "ON CONFLICT DO NOTHING",
            (ids["task_pdf"], project_id, ids["practice_project"], f"sk-tp-{project_id}"),
        )


def _build_draft(*, project_id: str = PROJECT, draft_id: str = "drf_1", run_id: str = "run_1") -> PlanDraft:
    ids = _catalog_ids(project_id)
    stages = (
        PlanStage.create(
            stable_key="sk-a", title="阶段一", section_kind=OutlineSectionKind.CORE, order_index=0
        ),
        PlanStage.create(
            stable_key="sk-b", title="阶段二", section_kind=OutlineSectionKind.PRACTICE, order_index=1
        ),
    )
    s0, s1 = stages
    return PlanDraft(
        draft_id=draft_id,
        project_id=project_id,
        run_id=run_id,
        goal_snapshot="学会 Python 并做出一个小工具",
        revision_candidate=1,
        stages=stages,
        unit_refs=(f"u_basic_{project_id}", f"u_rag_{project_id}"),
        task_refs=(f"t_pdf_{project_id}",),
        node_stable_keys=("n_python", "n_rag"),
        unit_links=(
            PlanUnitLink(stage_id=s0.stage_id, unit_id=ids["unit_basic"], order_index=0),
            PlanUnitLink(stage_id=s1.stage_id, unit_id=ids["unit_rag"], order_index=0),
        ),
        task_links=(PlanTaskLink(stage_id=s1.stage_id, task_id=ids["task_pdf"], order_index=0),),
        stage_resources=(
            StageResourceAssignment.create(
                project_id=project_id,
                stage_id=s0.stage_id,
                role=StageResourceRole.PRIMARY,
                source_ref="src_1",
                section_refs=("sec_1", "sec_2"),
            ),
        ),
        extensions=(
            KnowledgeExtension.create(
                project_id=project_id,
                stage_id=s1.stage_id,
                topic="关系型数据库认识与对比",
                concepts=("基本特点", "典型适用场景"),
                guidance="了解基本特点及典型适用场景",
                search_hints=("关系型数据库对比 入门",),
                thinking_prompts=("多人同时写入？",),
            ),
        ),
        source_pack_key="agent_app_dev",
        source_pack_version=1,
    )


def _build_revision(draft: PlanDraft, *, revision_no: int) -> PlanRevision:
    """从草案构造一个**已冻结**的候选版本（结构完整）。

    每个版本是**独立快照**：``plan_stages.stage_id`` 是全局主键，
    因此阶段必须重新生成 ID，并把链接/资源/扩展按旧→新映射重写。
    """
    new_stages = tuple(
        PlanStage.create(
            stable_key=s.stable_key,
            title=s.title,
            section_kind=s.section_kind,
            order_index=s.order_index,
            objective=s.objective,
        )
        for s in draft.stages
    )
    remap = {
        old.stage_id: new.stage_id
        for old, new in zip(draft.stages, new_stages, strict=True)
    }

    def _sid(stage_id: str) -> str:
        return remap.get(stage_id, stage_id)

    candidate = PlanRevision.create(
        project_id=draft.project_id,
        revision=revision_no,
        goal_snapshot=draft.goal_snapshot,
        stages=new_stages,
        unit_links=tuple(
            PlanUnitLink(stage_id=_sid(x.stage_id), unit_id=x.unit_id, order_index=x.order_index)
            for x in draft.unit_links
        ),
        task_links=tuple(
            PlanTaskLink(stage_id=_sid(x.stage_id), task_id=x.task_id, order_index=x.order_index)
            for x in draft.task_links
        ),
        stage_resources=tuple(
            StageResourceAssignment.create(
                project_id=draft.project_id,
                stage_id=_sid(a.stage_id),
                role=a.role,
                source_ref=a.source_ref,
                section_refs=a.section_refs,
                order_index=a.order_index,
                source_version=a.source_version,
                fallback_search_terms=a.fallback_search_terms,
            )
            for a in draft.stage_resources
        ),
        extensions=tuple(
            KnowledgeExtension.create(
                project_id=draft.project_id,
                stage_id=_sid(e.stage_id),
                topic=e.topic,
                concepts=e.concepts,
                guidance=e.guidance,
                links=e.links,
                search_hints=e.search_hints,
                thinking_prompts=e.thinking_prompts,
                required=e.required,
                order_index=e.order_index,
                unit_id=e.unit_id,
            )
            for e in draft.extensions
        ),
        source_pack_key=draft.source_pack_key,
        source_pack_version=draft.source_pack_version,
    )
    candidate.stage_resources = tuple(
        a.bound_to_plan(candidate.plan_id) for a in candidate.stage_resources
    )
    candidate.extensions = tuple(
        e.bound_to_plan(candidate.plan_id) for e in candidate.extensions
    )
    candidate.freeze()
    return candidate


# --------------------------------------------------------------------- 往返读回


def test_publish_then_read_back_full_route(migrated_db: PgTestDatabase, repo: PgPlanRepository) -> None:
    """发布完整结构 → 读回：阶段/单元链接/任务链接/资源/扩展一个不少。"""
    _clean(migrated_db)
    draft = _build_draft()
    repo.save_draft(draft)
    revision = _build_revision(draft, revision_no=1)
    repo.publish_revision(
        draft=draft,
        revision=revision,
        superseded=None,
        idempotency_key="k1",
        body_fingerprint="bf1",
    )

    current = repo.get_current(project_id=PROJECT)
    assert current is not None
    assert current.plan_id == revision.plan_id
    assert current.status.value == "approved"
    assert [s.stable_key for s in current.stages] == ["sk-a", "sk-b"]
    ids = _catalog_ids(PROJECT)
    assert [(x.stage_id, x.unit_id) for x in current.unit_links] == [
        (revision.stages[0].stage_id, ids["unit_basic"]),
        (revision.stages[1].stage_id, ids["unit_rag"]),
    ]
    assert [(x.stage_id, x.task_id) for x in current.task_links] == [
        (revision.stages[1].stage_id, ids["task_pdf"])
    ]
    assert len(current.stage_resources) == 1
    assert current.stage_resources[0].section_refs == ("sec_1", "sec_2")
    assert current.stage_resources[0].role is StageResourceRole.PRIMARY
    assert current.stage_resources[0].plan_id == revision.plan_id, "资源快照必须绑定到发布版本"
    assert len(current.extensions) == 1
    assert current.extensions[0].topic == "关系型数据库认识与对比"
    assert current.extensions[0].plan_id == revision.plan_id
    assert current.source_pack_key == "agent_app_dev"
    assert current.source_pack_version == 1
    assert current.approved_at is not None


def test_publish_supersedes_previous_revision(migrated_db: PgTestDatabase, repo: PgPlanRepository) -> None:
    _clean(migrated_db)
    draft = _build_draft()
    repo.save_draft(draft)
    rev1 = _build_revision(draft, revision_no=1)
    repo.publish_revision(
        draft=draft, revision=rev1, superseded=None, idempotency_key="k1", body_fingerprint="bf1"
    )
    rev2 = _build_revision(draft, revision_no=2)
    repo.publish_revision(
        draft=draft, revision=rev2, superseded=rev1, idempotency_key="k2", body_fingerprint="bf2"
    )

    assert repo.get_current(project_id=PROJECT).plan_id == rev2.plan_id  # type: ignore[union-attr]
    old = repo.get_revision(project_id=PROJECT, revision=1)
    assert old is not None and old.status.value == "superseded"
    assert [r.revision for r in repo.list_revisions(project_id=PROJECT)] == [1, 2]


# --------------------------------------------------------------------- 幂等


def test_idempotency_record_is_readable(migrated_db: PgTestDatabase, repo: PgPlanRepository) -> None:
    _clean(migrated_db)
    draft = _build_draft()
    repo.save_draft(draft)
    revision = _build_revision(draft, revision_no=1)
    repo.publish_revision(
        draft=draft, revision=revision, superseded=None, idempotency_key="k-idem", body_fingerprint="bf"
    )
    record = repo.find_publish_by_idempotency_key(project_id=PROJECT, idempotency_key="k-idem")
    assert record is not None
    assert record.plan_id == revision.plan_id
    assert record.revision == 1
    assert record.body_fingerprint == "bf"
    assert record.structure_fingerprint == revision.structure_fingerprint()
    assert repo.find_publish_by_idempotency_key(project_id=PROJECT, idempotency_key="nope") is None


def test_duplicate_idempotency_key_is_rejected_by_db(
    migrated_db: PgTestDatabase, repo: PgPlanRepository
) -> None:
    """幂等靠 DB 唯一约束（非「先查后写」）：同键第二次发布必须失败。"""
    _clean(migrated_db)
    draft = _build_draft()
    repo.save_draft(draft)
    rev1 = _build_revision(draft, revision_no=1)
    repo.publish_revision(
        draft=draft, revision=rev1, superseded=None, idempotency_key="k-dup", body_fingerprint="bf"
    )
    rev2 = _build_revision(draft, revision_no=2)
    with pytest.raises(psycopg.errors.UniqueViolation):
        repo.publish_revision(
            draft=draft, revision=rev2, superseded=rev1, idempotency_key="k-dup", body_fingerprint="bf"
        )


def test_failed_publish_rolls_back_entirely(
    migrated_db: PgTestDatabase, repo: PgPlanRepository
) -> None:
    """失败必须整体回滚：不留半发布状态，被替代版本**不得**被错误留在 superseded。"""
    _clean(migrated_db)
    draft = _build_draft()
    repo.save_draft(draft)
    rev1 = _build_revision(draft, revision_no=1)
    repo.publish_revision(
        draft=draft, revision=rev1, superseded=None, idempotency_key="k-roll", body_fingerprint="bf"
    )

    rev2 = _build_revision(draft, revision_no=2)
    with pytest.raises(psycopg.errors.UniqueViolation):
        repo.publish_revision(
            draft=draft, revision=rev2, superseded=rev1, idempotency_key="k-roll", body_fingerprint="bf"
        )

    # 新版本未落库
    assert repo.get_revision(project_id=PROJECT, revision=2) is None
    # 旧版本仍是当前（回滚恢复了它的 approved 状态，未被错误地留成 superseded）
    current = repo.get_current(project_id=PROJECT)
    assert current is not None and current.plan_id == rev1.plan_id
    # 只存在一条发布记录
    with psycopg.connect(migrated_db.migrator_dsn) as conn:
        count = conn.execute(
            "SELECT count(*) FROM plan_publications WHERE project_id='p1'"
        ).fetchone()[0]
        stages = conn.execute(
            "SELECT count(*) FROM plan_stages WHERE project_id='p1'"
        ).fetchone()[0]
    assert count == 1, "失败发布不得留下第二条发布记录"
    assert stages == 2, "失败发布不得留下孤儿阶段行"


def test_concurrent_publish_same_key_exactly_one_wins(migrated_db: PgTestDatabase) -> None:
    """并发：两个事务用同一幂等键发布，**恰好一个**成功（另一个整体回滚）。"""
    _clean(migrated_db)
    repo0 = PgPlanRepository(migrated_db.app_dsn)
    draft = _build_draft()
    repo0.save_draft(draft)
    rev1 = _build_revision(draft, revision_no=1)
    repo0.publish_revision(
        draft=draft, revision=rev1, superseded=None, idempotency_key="k0", body_fingerprint="bf0"
    )

    results: list[str] = []
    barrier = threading.Barrier(2, timeout=20)

    def worker(revision_no: int) -> None:
        worker_repo = PgPlanRepository(migrated_db.app_dsn)
        candidate = _build_revision(draft, revision_no=revision_no)
        try:
            barrier.wait()
            worker_repo.publish_revision(
                draft=draft,
                revision=candidate,
                superseded=rev1,
                idempotency_key="k-conc",
                body_fingerprint="bfc",
            )
            results.append("ok")
        except psycopg.Error:
            results.append("conflict")

    threads = [threading.Thread(target=worker, args=(n,)) for n in (2, 3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    assert sorted(results) == ["conflict", "ok"], f"并发结果异常：{results}"
    with psycopg.connect(migrated_db.migrator_dsn) as conn:
        publications = conn.execute(
            "SELECT count(*) FROM plan_publications WHERE project_id='p1' AND idempotency_key='k-conc'"
        ).fetchone()[0]
        approved = conn.execute(
            "SELECT count(*) FROM plan_revisions WHERE project_id='p1' AND status='approved'"
        ).fetchone()[0]
    assert publications == 1, "同一幂等键只允许一条发布记录"
    assert approved == 1, "同一项目至多一个当前版本"


# --------------------------------------------------------------------- RLS 隔离


def test_repository_cannot_read_other_project(migrated_db: PgTestDatabase, repo: PgPlanRepository) -> None:
    """RLS：p1 的仓储读不到 p2 的版本。"""
    _clean(migrated_db)
    other = PgPlanRepository(migrated_db.app_dsn)
    draft_p2 = _build_draft(project_id="p2", draft_id="drf_p2", run_id="run_p2")
    other.save_draft(draft_p2)
    rev = _build_revision(draft_p2, revision_no=1)
    other.publish_revision(
        draft=draft_p2, revision=rev, superseded=None, idempotency_key="k-p2", body_fingerprint="bf"
    )

    assert other.get_current(project_id="p2") is not None
    assert repo.get_current(project_id=PROJECT) is None, "p1 不得看到 p2 的当前版本"
    assert repo.find_publish_by_idempotency_key(
        project_id=PROJECT, idempotency_key="k-p2"
    ) is None


# ----------------------------------------------------------- save_draft 状态过滤


def test_save_draft_does_not_resurrect_cancelled(migrated_db: PgTestDatabase, repo: PgPlanRepository) -> None:
    """已取消的草案不得被 worker 稍后覆盖为可发布（设计 §3 C6）。"""
    from app.domain.enums import PlanDraftStatus

    _clean(migrated_db)
    draft = _build_draft()
    repo.save_draft(draft)
    draft.status = PlanDraftStatus.CANCELLED
    repo.save_draft(draft)
    assert repo.get_draft(project_id=PROJECT, draft_id=draft.draft_id).status is PlanDraftStatus.CANCELLED  # type: ignore[union-attr]

    # 试图把已取消的草案改回可发布 → 被状态过滤挡住
    draft.status = PlanDraftStatus.AWAITING_APPROVAL
    repo.save_draft(draft)
    still = repo.get_draft(project_id=PROJECT, draft_id=draft.draft_id)
    assert still is not None and still.status is PlanDraftStatus.CANCELLED
