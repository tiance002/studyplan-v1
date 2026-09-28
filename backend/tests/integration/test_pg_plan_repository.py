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

from app.core.errors import ConflictError  # noqa: E402
from app.domain.enums import OutlineSectionKind, StageResourceRole  # noqa: E402
from app.domain.planning.models import (  # noqa: E402
    PlanDraft,
    PlanRevision,
    PlanStage,
    PlanTaskKnowledgeLink,
    PlanTaskLink,
    PlanUnitLink,
    revision_from_draft,
)
from app.domain.resources.curation import (  # noqa: E402
    KnowledgeExtension,
    StageResourceAssignment,
)
from app.infrastructure.db.plan_repository import PgPlanRepository  # noqa: E402

from tests.pg_harness import PgTestDatabase, create_test_database  # noqa: E402

PROJECT = "p1"

#: 公共资源来源/章节（B2-V §五：``source_ref`` 必须真实存在）。
PUBLIC_SOURCE = "src_public_1"
PUBLIC_SECTIONS = ("sec_public_1", "sec_public_2")


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
    _seed_public_resources(db)
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
            "TRUNCATE plan_task_knowledge_links, summary_attempts, plan_publications, "
            "plan_drafts, plan_revisions, knowledge_extensions, "
            "stage_resource_assignments, plan_stages, "
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
        "node_python": f"nod_python_{project_id}",
        "node_rag": f"nod_rag_{project_id}",
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
            "INSERT INTO knowledge_nodes"
            "(node_id,project_id,stable_key,title,node_type,source_status) "
            "VALUES (%s,%s,%s,'Python 节点','concept','ai_draft'), "
            "(%s,%s,%s,'RAG 节点','concept','ai_draft') ON CONFLICT DO NOTHING",
            (
                ids["node_python"], project_id, f"sk-np-{project_id}",
                ids["node_rag"], project_id, f"sk-nr-{project_id}",
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


def _seed_public_resources(db: PgTestDatabase) -> None:
    """植入公共资源来源与章节（B2-V §五：``source_ref`` FK 要求真实存在）。"""
    with psycopg.connect(db.migrator_dsn, autocommit=True) as conn:
        conn.execute(
            "INSERT INTO public_resource_sources"
            "(source_id,canonical_url,title,creator,media_type,language,source_version) "
            "VALUES (%s,'https://example.com/course','示例课程','示例作者','course','zh',1) "
            "ON CONFLICT DO NOTHING",
            (PUBLIC_SOURCE,),
        )
        conn.execute(
            "INSERT INTO public_resource_sections"
            "(section_id,source_id,order_index,title,url,anchor) VALUES "
            "(%s,%s,0,'第一章','https://example.com/course#1','c1'), "
            "(%s,%s,1,'第二章','https://example.com/course#2','c2') "
            "ON CONFLICT DO NOTHING",
            (PUBLIC_SECTIONS[0], PUBLIC_SOURCE, PUBLIC_SECTIONS[1], PUBLIC_SOURCE),
        )


def _build_draft(
    *,
    project_id: str = PROJECT,
    draft_id: str = "drf_1",
    run_id: str | None = None,
    stages: tuple[PlanStage, ...] | None = None,
) -> PlanDraft:
    ids = _catalog_ids(project_id)
    # ``plan_drafts_run_unique``：一个 run 至多一个草案，故默认按草案派生 run_id。
    run = run_id or f"run_{project_id}_{draft_id}"
    stgs = stages or (
        PlanStage.create(
            stable_key="sk-a", title="阶段一", section_kind=OutlineSectionKind.CORE, order_index=0
        ),
        PlanStage.create(
            stable_key="sk-b", title="阶段二", section_kind=OutlineSectionKind.PRACTICE, order_index=1
        ),
    )
    s0, s1 = stgs
    return PlanDraft(
        draft_id=draft_id,
        project_id=project_id,
        run_id=run,
        goal_snapshot="学会 Python 并做出一个小工具",
        revision_candidate=1,
        stages=stgs,
        unit_refs=(f"u_basic_{project_id}", f"u_rag_{project_id}"),
        task_refs=(f"t_pdf_{project_id}",),
        node_stable_keys=("n_python", "n_rag"),
        unit_links=(
            PlanUnitLink(stage_id=s0.stage_id, unit_id=ids["unit_basic"], order_index=0),
            PlanUnitLink(stage_id=s1.stage_id, unit_id=ids["unit_rag"], order_index=0),
        ),
        task_links=(PlanTaskLink(stage_id=s1.stage_id, task_id=ids["task_pdf"], order_index=0),),
        task_knowledge_links=(
            PlanTaskKnowledgeLink(task_id=ids["task_pdf"], node_id=ids["node_rag"]),
        ),
        stage_resources=(
            StageResourceAssignment.create(
                project_id=project_id,
                stage_id=s0.stage_id,
                role=StageResourceRole.PRIMARY,
                source_ref=PUBLIC_SOURCE,
                section_refs=PUBLIC_SECTIONS,
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
                unit_id=ids["unit_rag"],
            ),
        ),
        source_pack_key="agent_app_dev",
        source_pack_version=1,
    )


def _build_revision(draft: PlanDraft, *, revision_no: int) -> PlanRevision:
    """从草案构造一个**已冻结**的候选版本。

    B2-V §三：**不再**各自实现版本构造，直接复用生产路径的唯一入口
    :func:`revision_from_draft`（它会重新生成 stage_id 并按稳定键重映射
    链接/资源/扩展）。测试与生产共用同一实现，因此「同路由不同 ID」
    在两边得到同一结构指纹。
    """
    candidate = revision_from_draft(draft, revision=revision_no)
    candidate.stage_resources = tuple(
        a.bound_to_plan(candidate.plan_id) for a in candidate.stage_resources
    )
    candidate.extensions = tuple(
        e.bound_to_plan(candidate.plan_id) for e in candidate.extensions
    )
    candidate.freeze()
    return candidate


def _publish(
    repo: PgPlanRepository,
    draft: PlanDraft,
    *,
    revision_no: int,
    idempotency_key: str,
    superseded: PlanRevision | None = None,
    body_fingerprint: str = "bf",
) -> PlanRevision:
    """测试助手：从草案构造版本并**原子发布**（走真实端口路径）。"""
    revision = _build_revision(draft, revision_no=revision_no)
    repo.publish_revision(
        draft=draft,
        revision=revision,
        superseded=superseded,
        idempotency_key=idempotency_key,
        body_fingerprint=body_fingerprint,
    )
    return revision


# --------------------------------------------------------------------- 往返读回


def test_publish_then_read_back_full_route(
    migrated_db: PgTestDatabase, repo: PgPlanRepository
) -> None:
    """发布完整结构 → 读回：阶段/单元链接/任务链接/任务-知识/资源/扩展一个不少。"""
    _clean(migrated_db)
    draft = _build_draft()
    repo.save_draft(draft)
    revision = _publish(repo, draft, revision_no=1, idempotency_key="k1", body_fingerprint="bf1")

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
    assert [(x.task_id, x.node_id) for x in current.task_knowledge_links] == [
        (ids["task_pdf"], ids["node_rag"])
    ]
    assert len(current.stage_resources) == 1
    assert current.stage_resources[0].section_refs == PUBLIC_SECTIONS
    assert current.stage_resources[0].source_ref == PUBLIC_SOURCE
    assert current.stage_resources[0].role is StageResourceRole.PRIMARY
    assert current.stage_resources[0].plan_id == revision.plan_id, "资源快照必须绑定到发布版本"
    assert len(current.extensions) == 1
    assert current.extensions[0].topic == "关系型数据库认识与对比"
    assert current.extensions[0].plan_id == revision.plan_id
    assert current.extensions[0].unit_id == ids["unit_rag"], "扩展绑定的单元必须读回"
    assert current.source_pack_key == "agent_app_dev"
    assert current.source_pack_version == 1
    assert current.approved_at is not None


def test_publish_supersedes_previous_revision(
    migrated_db: PgTestDatabase, repo: PgPlanRepository
) -> None:
    """每个版本来自**自己的**草案；发布 v2 后 v1 变 superseded。"""
    _clean(migrated_db)
    d1 = _build_draft()
    repo.save_draft(d1)
    rev1 = _publish(repo, d1, revision_no=1, idempotency_key="k1", body_fingerprint="bf1")

    d2 = _build_draft(draft_id="drf_2")
    repo.save_draft(d2)
    rev2 = _publish(
        repo, d2, revision_no=2, idempotency_key="k2", superseded=rev1, body_fingerprint="bf2"
    )

    assert repo.get_current(project_id=PROJECT).plan_id == rev2.plan_id  # type: ignore[union-attr]
    old = repo.get_revision(project_id=PROJECT, revision=1)
    assert old is not None and old.status.value == "superseded"
    assert [r.revision for r in repo.list_revisions(project_id=PROJECT)] == [1, 2]


def test_consecutive_revisions_have_distinct_stage_ids(
    migrated_db: PgTestDatabase, repo: PgPlanRepository
) -> None:
    """连续两版不得复用 stage_id（``plan_stages.stage_id`` 是全局主键，B2-V §三）。"""
    _clean(migrated_db)
    d1 = _build_draft()
    repo.save_draft(d1)
    rev1 = _publish(repo, d1, revision_no=1, idempotency_key="k1")
    d2 = _build_draft(draft_id="drf_2")
    repo.save_draft(d2)
    _publish(repo, d2, revision_no=2, idempotency_key="k2", superseded=rev1)

    v1 = repo.get_revision(project_id=PROJECT, revision=1)
    v2 = repo.get_revision(project_id=PROJECT, revision=2)
    assert v1 is not None and v2 is not None
    assert {s.stage_id for s in v1.stages}.isdisjoint({s.stage_id for s in v2.stages})
    # 同结构 → 同指纹（指纹不依赖 stage_id）
    assert v1.structure_fingerprint() == v2.structure_fingerprint()


# --------------------------------------------------------------------- 幂等


def test_idempotency_record_is_readable(
    migrated_db: PgTestDatabase, repo: PgPlanRepository
) -> None:
    _clean(migrated_db)
    draft = _build_draft()
    repo.save_draft(draft)
    revision = _publish(repo, draft, revision_no=1, idempotency_key="k-idem", body_fingerprint="bf")
    record = repo.find_publish_by_idempotency_key(project_id=PROJECT, idempotency_key="k-idem")
    assert record is not None
    assert record.plan_id == revision.plan_id
    assert record.revision == 1
    assert record.body_fingerprint == "bf"
    assert record.structure_fingerprint == revision.structure_fingerprint()
    assert repo.find_publish_by_idempotency_key(project_id=PROJECT, idempotency_key="nope") is None


def test_reuse_publication_is_persisted(
    migrated_db: PgTestDatabase, repo: PgPlanRepository
) -> None:
    """B2-V §四：``created=False``（复用当前版本）也必须落库幂等记录。"""
    _clean(migrated_db)
    draft = _build_draft()
    repo.save_draft(draft)
    rev1 = _publish(repo, draft, revision_no=1, idempotency_key="k1", body_fingerprint="bf1")

    d2 = _build_draft(draft_id="drf_2")
    repo.save_draft(d2)
    repo.publish_revision(
        draft=d2,
        revision=rev1,
        superseded=None,
        idempotency_key="k2",
        body_fingerprint="bf2",
        created=False,
    )
    record = repo.find_publish_by_idempotency_key(project_id=PROJECT, idempotency_key="k2")
    assert record is not None
    assert record.plan_id == rev1.plan_id
    assert record.revision == 1
    # 复用不产生新版本
    assert [r.revision for r in repo.list_revisions(project_id=PROJECT)] == [1]
    # 且草案状态被置为 approved
    assert repo.get_draft(project_id=PROJECT, draft_id="drf_2").status.value == "approved"  # type: ignore[union-attr]


def test_duplicate_idempotency_key_is_rejected_by_db(
    migrated_db: PgTestDatabase, repo: PgPlanRepository
) -> None:
    """幂等靠 DB 唯一约束（非「先查后写」）：同键第二次发布必须失败。"""
    _clean(migrated_db)
    d1 = _build_draft()
    repo.save_draft(d1)
    rev1 = _publish(repo, d1, revision_no=1, idempotency_key="k-dup", body_fingerprint="bf")
    d2 = _build_draft(draft_id="drf_2")
    repo.save_draft(d2)
    rev2 = _build_revision(d2, revision_no=2)
    with pytest.raises(psycopg.errors.UniqueViolation):
        repo.publish_revision(
            draft=d2,
            revision=rev2,
            superseded=rev1,
            idempotency_key="k-dup",
            body_fingerprint="bf",
        )


def test_failed_publish_rolls_back_entirely(
    migrated_db: PgTestDatabase, repo: PgPlanRepository
) -> None:
    """失败必须整体回滚：不留半发布状态，被替代版本**不得**被错误留在 superseded。"""
    _clean(migrated_db)
    d1 = _build_draft()
    repo.save_draft(d1)
    rev1 = _publish(repo, d1, revision_no=1, idempotency_key="k-roll", body_fingerprint="bf")

    d2 = _build_draft(draft_id="drf_2")
    repo.save_draft(d2)
    rev2 = _build_revision(d2, revision_no=2)
    with pytest.raises(psycopg.errors.UniqueViolation):
        repo.publish_revision(
            draft=d2,
            revision=rev2,
            superseded=rev1,
            idempotency_key="k-roll",
            body_fingerprint="bf",
        )

    # 新版本未落库
    assert repo.get_revision(project_id=PROJECT, revision=2) is None
    # 旧版本仍是当前（回滚恢复了它的 approved 状态，未被错误地留成 superseded）
    current = repo.get_current(project_id=PROJECT)
    assert current is not None and current.plan_id == rev1.plan_id
    # 失败发布不得改写草案状态
    assert repo.get_draft(project_id=PROJECT, draft_id="drf_2").status.value == "awaiting_approval"  # type: ignore[union-attr]
    with psycopg.connect(migrated_db.migrator_dsn) as conn:
        count = conn.execute(
            "SELECT count(*) FROM plan_publications WHERE project_id='p1'"
        ).fetchone()[0]
        stages = conn.execute("SELECT count(*) FROM plan_stages WHERE project_id='p1'").fetchone()[0]
    assert count == 1, "失败发布不得留下第二条发布记录"
    assert stages == 2, "失败发布不得留下孤儿阶段行"


def test_concurrent_publish_same_key_exactly_one_wins(migrated_db: PgTestDatabase) -> None:
    """并发：两个事务用同一幂等键发布，**恰好一个**成功（另一个整体回滚）。

    使用**两个不同的草案**（真实世界里同一草案不可能产生两个版本），
    因此唯一能仲裁的就是数据库约束（幂等唯一索引 / 当前版本唯一索引）。
    """
    _clean(migrated_db)
    repo0 = PgPlanRepository(migrated_db.app_dsn)
    d0 = _build_draft()
    repo0.save_draft(d0)
    rev1 = _publish(repo0, d0, revision_no=1, idempotency_key="k0", body_fingerprint="bf0")

    drafts = []
    for i in (2, 3):
        d = _build_draft(draft_id=f"drf_c{i}")
        repo0.save_draft(d)
        drafts.append(d)

    results: list[str] = []
    barrier = threading.Barrier(2, timeout=20)

    def worker(draft: PlanDraft, revision_no: int) -> None:
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
        except (psycopg.Error, ConflictError):
            results.append("conflict")

    threads = [
        threading.Thread(target=worker, args=(d, n)) for d, n in zip(drafts, (2, 3), strict=True)
    ]
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


# ------------------------------------------------------------- 发布原子性（B2-V §二）


def test_publish_rejects_stale_object_after_cancel(
    migrated_db: PgTestDatabase, repo: PgPlanRepository
) -> None:
    """取消后，调用方持有的**旧对象**不得把已取消的草案发布出去。"""
    _clean(migrated_db)
    draft = _build_draft()
    repo.save_draft(draft)
    repo.cancel_draft(project_id=PROJECT, draft_id=draft.draft_id)

    # 调用方对象仍是 awaiting_approval（陈旧）
    assert draft.status.value == "awaiting_approval"
    revision = _build_revision(draft, revision_no=1)
    with pytest.raises(ConflictError) as exc:
        repo.publish_revision(
            draft=draft,
            revision=revision,
            superseded=None,
            idempotency_key="k-stale",
            body_fingerprint="bf",
        )
    assert exc.value.details.get("reason") == "draft_not_publishable"
    assert repo.get_current(project_id=PROJECT) is None
    assert repo.find_publish_by_idempotency_key(
        project_id=PROJECT, idempotency_key="k-stale"
    ) is None


def test_publish_rejects_unknown_draft(migrated_db: PgTestDatabase, repo: PgPlanRepository) -> None:
    """草案未落库 → 拒绝发布（不产生任何版本）。"""
    _clean(migrated_db)
    draft = _build_draft()
    revision = _build_revision(draft, revision_no=1)
    with pytest.raises(ConflictError) as exc:
        repo.publish_revision(
            draft=draft,
            revision=revision,
            superseded=None,
            idempotency_key="k-missing",
            body_fingerprint="bf",
        )
    assert exc.value.details.get("reason") == "draft_not_found"
    assert repo.get_current(project_id=PROJECT) is None


def test_publish_rejects_stale_content_hash(
    migrated_db: PgTestDatabase, repo: PgPlanRepository
) -> None:
    """草案在库内容与调用方对象不一致（被后台改写）→ 拒绝发布过期内容。"""
    _clean(migrated_db)
    draft = _build_draft()
    repo.save_draft(draft)
    # 库里换成另一份内容（同一个 draft_id）。
    changed = _build_draft()
    changed.goal_snapshot = "完全不同的目标陈述"
    repo.save_draft(changed, expected_hash=draft.content_hash)

    revision = _build_revision(draft, revision_no=1)
    with pytest.raises(ConflictError) as exc:
        repo.publish_revision(
            draft=draft,
            revision=revision,
            superseded=None,
            idempotency_key="k-stale-hash",
            body_fingerprint="bf",
        )
    assert exc.value.details.get("reason") == "draft_hash_mismatch"
    assert repo.get_current(project_id=PROJECT) is None


def test_successful_publish_reads_back_consistent_draft_and_plan(
    migrated_db: PgTestDatabase, repo: PgPlanRepository
) -> None:
    """成功发布后立即回读：草案 APPROVED、当前版本 APPROVED、状态一致（B2-V §二.5）。"""
    _clean(migrated_db)
    draft = _build_draft()
    repo.save_draft(draft)
    revision = _publish(repo, draft, revision_no=1, idempotency_key="k-ok")

    stored = repo.get_draft(project_id=PROJECT, draft_id=draft.draft_id)
    current = repo.get_current(project_id=PROJECT)
    assert stored is not None and stored.status.value == "approved"
    assert current is not None and current.status.value == "approved"
    assert current.plan_id == revision.plan_id


def test_cancel_after_publish_is_rejected(
    migrated_db: PgTestDatabase, repo: PgPlanRepository
) -> None:
    """已发布（approved）的草案不能再被取消（状态条件更新，行数为 0 → 冲突）。"""
    _clean(migrated_db)
    draft = _build_draft()
    repo.save_draft(draft)
    _publish(repo, draft, revision_no=1, idempotency_key="k1")

    with pytest.raises(ConflictError) as exc:
        repo.cancel_draft(project_id=PROJECT, draft_id=draft.draft_id)
    assert exc.value.details.get("reason") == "draft_not_cancellable"
    assert repo.get_draft(project_id=PROJECT, draft_id=draft.draft_id).status.value == "approved"  # type: ignore[union-attr]


def test_cancel_vs_publish_concurrency_exactly_one_wins(migrated_db: PgTestDatabase) -> None:
    """取消与发布并发：恰好一个成功，绝不同时生效（B2-V §二）。"""
    _clean(migrated_db)
    setup = PgPlanRepository(migrated_db.app_dsn)
    draft = _build_draft()
    setup.save_draft(draft)
    revision = _build_revision(draft, revision_no=1)

    results: list[str] = []
    barrier = threading.Barrier(2, timeout=20)

    def publish() -> None:
        r = PgPlanRepository(migrated_db.app_dsn)
        try:
            barrier.wait()
            r.publish_revision(
                draft=draft,
                revision=revision,
                superseded=None,
                idempotency_key="k-race",
                body_fingerprint="bf",
            )
            results.append("published")
        except (psycopg.Error, ConflictError):
            results.append("publish-rejected")

    def cancel() -> None:
        r = PgPlanRepository(migrated_db.app_dsn)
        try:
            barrier.wait()
            r.cancel_draft(project_id=PROJECT, draft_id=draft.draft_id)
            results.append("cancelled")
        except (psycopg.Error, ConflictError):
            results.append("cancel-rejected")

    threads = [threading.Thread(target=publish), threading.Thread(target=cancel)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    assert len(results) == 2, f"并发结果缺失：{results}"
    succeeded = [r for r in results if r in {"published", "cancelled"}]
    assert len(succeeded) == 1, f"取消与发布必须恰好一个成功：{results}"

    with psycopg.connect(migrated_db.migrator_dsn) as conn:
        draft_status = conn.execute(
            "SELECT status FROM plan_drafts WHERE project_id='p1' AND draft_id=%s",
            (draft.draft_id,),
        ).fetchone()[0]
        approved = conn.execute(
            "SELECT count(*) FROM plan_revisions WHERE project_id='p1' AND status='approved'"
        ).fetchone()[0]
    if "published" in results:
        assert draft_status == "approved" and approved == 1
    else:
        assert draft_status == "cancelled" and approved == 0


# --------------------------------------------------------------------- RLS 隔离


def test_repository_cannot_read_other_project(
    migrated_db: PgTestDatabase, repo: PgPlanRepository
) -> None:
    """RLS：p1 的仓储读不到 p2 的版本。"""
    _clean(migrated_db)
    other = PgPlanRepository(migrated_db.app_dsn)
    draft_p2 = _build_draft(project_id="p2", draft_id="drf_p2", run_id="run_p2")
    other.save_draft(draft_p2)
    _publish(other, draft_p2, revision_no=1, idempotency_key="k-p2")

    assert other.get_current(project_id="p2") is not None
    assert repo.get_current(project_id=PROJECT) is None, "p1 不得看到 p2 的当前版本"
    assert repo.find_publish_by_idempotency_key(project_id=PROJECT, idempotency_key="k-p2") is None


# ----------------------------------------------------------- save_draft 状态条件


def test_republish_preserves_historical_completion_records(
    migrated_db: PgTestDatabase, repo: PgPlanRepository
) -> None:
    """重规划/重新发布**不得删除**历史完成记录（Goal §1「历史完成记录不丢失」）。"""
    _clean(migrated_db)
    ids = _catalog_ids(PROJECT)
    with psycopg.connect(migrated_db.migrator_dsn, autocommit=True) as conn:
        conn.execute(
            "INSERT INTO summary_attempts"
            "(attempt_id,project_id,unit_id,content,attempt_no,rubric_version) "
            "VALUES ('sat_hist','p1',%s,'历史总结原文',1,1)",
            (ids["unit_basic"],),
        )

    d1 = _build_draft()
    repo.save_draft(d1)
    rev1 = _publish(repo, d1, revision_no=1, idempotency_key="k1", body_fingerprint="bf1")
    d2 = _build_draft(draft_id="drf_2")
    repo.save_draft(d2)
    _publish(repo, d2, revision_no=2, idempotency_key="k2", superseded=rev1, body_fingerprint="bf2")

    # 历史版本仍可完整读回（阶段/单元/资源/扩展都在）
    v1 = repo.get_revision(project_id=PROJECT, revision=1)
    assert v1 is not None
    assert len(v1.stages) == 2 and len(v1.unit_links) == 2
    assert len(v1.stage_resources) == 1 and len(v1.extensions) == 1
    with psycopg.connect(migrated_db.migrator_dsn) as conn:
        rows = conn.execute(
            "SELECT attempt_id, content FROM summary_attempts WHERE project_id='p1'"
        ).fetchall()
    assert rows == [("sat_hist", "历史总结原文")], "重新发布不得删除历史完成记录"


def test_save_draft_does_not_resurrect_cancelled(
    migrated_db: PgTestDatabase, repo: PgPlanRepository
) -> None:
    """已取消的草案不得被 worker 稍后覆盖为可发布（设计 §3 C6 / B2-V §二.4）。"""
    from app.domain.enums import PlanDraftStatus

    _clean(migrated_db)
    draft = _build_draft()
    repo.save_draft(draft)
    draft.status = PlanDraftStatus.CANCELLED
    repo.save_draft(draft)
    assert repo.get_draft(project_id=PROJECT, draft_id=draft.draft_id).status is PlanDraftStatus.CANCELLED  # type: ignore[union-attr]

    # 试图把已取消的草案改回可发布 → 被状态条件挡住并**显式报错**。
    draft.status = PlanDraftStatus.AWAITING_APPROVAL
    with pytest.raises(ConflictError) as exc:
        repo.save_draft(draft)
    assert exc.value.details.get("reason") == "draft_terminal"
    still = repo.get_draft(project_id=PROJECT, draft_id=draft.draft_id)
    assert still is not None and still.status is PlanDraftStatus.CANCELLED


def test_save_draft_rejects_rewrite_of_approved(
    migrated_db: PgTestDatabase, repo: PgPlanRepository
) -> None:
    """已发布的草案不得被改写（否则会与已发布版本脱节）。"""
    _clean(migrated_db)
    draft = _build_draft()
    repo.save_draft(draft)
    _publish(repo, draft, revision_no=1, idempotency_key="k1")
    with pytest.raises(ConflictError):
        repo.save_draft(draft)
