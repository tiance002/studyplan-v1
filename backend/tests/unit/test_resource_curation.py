"""resources.curation 领域（V1.2）确定性校验测试。

对应 Goal §「确定性校验」与 §「最小领域模型」：

- **连续章节顺序 / 主线数量**：每阶段至多一条 ``PRIMARY`` 主线，章节引用非空且不重复。
- **每阶段扩展软上限**：超出只警告、不阻断。
- **链接结构安全**：已核验链接必须过 ``require_safe_url``（防 SSRF / 假链接）。
- **知识/任务关联**：扩展/资源分配必须指向计划内真实存在的阶段。
- **绝不做重复率计算**：以「负能力」护栏固定 V1 边界。

本文件不依赖 Postgres / 网络 / langgraph。
"""

from __future__ import annotations

from pathlib import Path

import pytest
from app.core.errors import ValidationAppError
from app.domain.domain_packs.models import DomainPack
from app.domain.enums import (
    DomainPackStatus,
    OutlineSectionKind,
    ResourceSourceVisibility,
    StageResourceRole,
)
from app.domain.planning.models import PlanRevision, PlanStage
from app.domain.resources import curation
from app.domain.resources.curation import (
    EXTENSION_SOFT_LIMIT,
    MAINLINE_PRIMARY_MAX,
    KnowledgeExtension,
    PublicResourceSection,
    PublicResourceSource,
    StageResourceAssignment,
    validate_extension_soft_limit,
    validate_extensions,
    validate_mainline_continuity,
)

# --------------------------------------------------------------------------- 公共资源


def test_public_source_rejects_private_network_url() -> None:
    """公共资源来源 URL 必须过安全校验（拒绝私网 / 非法 scheme）。"""
    with pytest.raises(ValidationAppError):
        PublicResourceSource.create(canonical_url="http://127.0.0.1/course", title="T")
    with pytest.raises(ValidationAppError):
        PublicResourceSource.create(canonical_url="file:///etc/passwd", title="T")


def test_public_source_is_curated_by_default() -> None:
    source = PublicResourceSource.create(
        canonical_url="https://example.com/course", title="某课程"
    )
    assert source.visibility is ResourceSourceVisibility.CURATED
    assert source.source_version == 1


def test_same_url_can_back_multiple_sections() -> None:
    """同 URL 可有多个章节（不同 anchor）：章节**不**以 URL 唯一。"""
    source = PublicResourceSource.create(
        canonical_url="https://example.com/course", title="某课程"
    )
    url = "https://example.com/course/lesson-1"
    s1 = PublicResourceSection.create(
        source_id=source.source_id, order_index=0, title="第 1 节", url=url, anchor="intro"
    )
    s2 = PublicResourceSection.create(
        source_id=source.source_id, order_index=1, title="第 1 节（练习）", url=url, anchor="exercise"
    )
    assert s1.url == s2.url
    assert s1.section_id != s2.section_id
    assert s1.anchor != s2.anchor


def test_section_requires_source_and_safe_url() -> None:
    with pytest.raises(ValidationAppError):
        PublicResourceSection.create(source_id="", order_index=0, title="t", url="https://e.com/a")
    with pytest.raises(ValidationAppError):
        PublicResourceSection.create(
            source_id="src1", order_index=0, title="t", url="http://10.0.0.1/a"
        )


# --------------------------------------------------------------- 阶段主线连续性校验


def _primary(stage_id: str, *, refs: tuple[str, ...], order: int = 0, **kw: object):
    return StageResourceAssignment.create(
        project_id="p1",
        stage_id=stage_id,
        role=StageResourceRole.PRIMARY,
        section_refs=refs,
        order_index=order,
        **kw,  # type: ignore[arg-type]
    )


def test_mainline_allows_single_primary_per_stage() -> None:
    errors = validate_mainline_continuity([_primary("stg1", refs=("sec1", "sec2", "sec3"))])
    assert errors == []


def test_mainline_rejects_two_primaries_in_one_stage() -> None:
    errors = validate_mainline_continuity(
        [
            _primary("stg1", refs=("sec1",), order=0),
            _primary("stg1", refs=("sec2",), order=1),
        ]
    )
    assert any(f"至多 {MAINLINE_PRIMARY_MAX} 条" in e for e in errors)


def test_mainline_rejects_empty_and_duplicate_section_refs() -> None:
    dup = validate_mainline_continuity([_primary("stg1", refs=("sec1", "sec1"))])
    assert any("重复引用" in e for e in dup)
    empty = validate_mainline_continuity(
        [
            StageResourceAssignment(
                assignment_id="asg-x",
                project_id="p1",
                plan_id="",
                stage_id="stg1",
                role=StageResourceRole.PRIMARY,
                section_refs=("sec1", ""),
            )
        ]
    )
    assert any("空的章节引用" in e for e in empty)


def test_mainline_rejects_duplicate_order_index_in_stage() -> None:
    """补充/对照分配在同一阶段内 order_index 不得重复。"""
    errors = validate_mainline_continuity(
        [
            _primary("stg1", refs=("sec1",), order=0),
            StageResourceAssignment.create(
                project_id="p1", stage_id="stg1", role=StageResourceRole.SUPPLEMENT, order_index=0
            ),
        ]
    )
    assert any("顺序索引重复" in e for e in errors)


def test_primary_requires_sections_or_search_terms() -> None:
    """主线必须至少给出有序章节，或（索引不可用时）明确的搜索建议。"""
    with pytest.raises(ValidationAppError):
        StageResourceAssignment.create(
            project_id="p1", stage_id="stg1", role=StageResourceRole.PRIMARY
        )
    ok = StageResourceAssignment.create(
        project_id="p1",
        stage_id="stg1",
        role=StageResourceRole.PRIMARY,
        fallback_search_terms=("pytorch tutorial",),
    )
    assert ok.fallback_search_terms == ("pytorch tutorial",)


# ------------------------------------------------------------------ 扩展软上限与安全


def _ext(stage_id: str, topic: str, *, order: int = 0, links: tuple[str, ...] = (), **kw: object):
    return KnowledgeExtension.create(
        project_id="p1",
        stage_id=stage_id,
        topic=topic,
        order_index=order,
        links=links,
        **kw,  # type: ignore[arg-type]
    )


def test_extension_soft_limit_warns_but_does_not_block() -> None:
    """超出软上限只产生 warning（不阻断发布）。"""
    exts = [_ext("stg1", f"topic-{i}", order=i) for i in range(EXTENSION_SOFT_LIMIT + 1)]
    assert validate_extensions(exts) == [], "软上限不应产生 error"
    warnings = validate_extension_soft_limit(exts)
    assert warnings and "超过建议上限" in warnings[0]


def test_extension_within_limit_has_no_warning() -> None:
    exts = [_ext("stg1", f"topic-{i}", order=i) for i in range(EXTENSION_SOFT_LIMIT)]
    assert validate_extension_soft_limit(exts) == []


def test_extension_requires_topic() -> None:
    with pytest.raises(ValidationAppError):
        KnowledgeExtension.create(project_id="p1", stage_id="stg1", topic="   ")


def test_extension_rejects_unsafe_verified_link() -> None:
    """已核验链接必须过安全校验：私网地址直接拒绝。"""
    with pytest.raises(ValidationAppError):
        _ext("stg1", "t", links=("http://192.168.1.1/x",))


def test_validate_extensions_flags_duplicate_order_and_bad_link() -> None:
    exts = [
        _ext("stg1", "a", order=0),
        _ext("stg1", "b", order=0),  # 同阶段 order 重复
    ]
    errors = validate_extensions(exts)
    assert any("顺序索引重复" in e for e in errors)


# ------------------------------------------------------------------- 发布时绑定 plan


def test_stage_resource_assignment_binds_to_plan() -> None:
    """草案期 plan_id 为空；发布时 ``bound_to_plan`` 绑定且**不修改原对象**。"""
    original = _primary("stg1", refs=("sec1",))
    assert original.plan_id == ""
    bound = original.bound_to_plan("pln-new")
    assert bound.plan_id == "pln-new"
    assert original.plan_id == "", "原草案快照不得被就地修改"


def test_knowledge_extension_binds_to_plan() -> None:
    original = _ext("stg1", "topic")
    assert original.plan_id == ""
    bound = original.bound_to_plan("pln-new")
    assert bound.plan_id == "pln-new"
    assert original.plan_id == ""


def test_plan_rejects_extension_pointing_to_unknown_stage() -> None:
    """知识/任务关联安全：扩展必须指向计划内真实存在的阶段。"""
    stage = PlanStage.create(
        stable_key="sk-1", title="阶段一", section_kind=OutlineSectionKind.CORE, order_index=0
    )
    with pytest.raises(ValidationAppError):
        PlanRevision.create(
            project_id="p1",
            revision=1,
            goal_snapshot="g",
            stages=[stage],
            extensions=[_ext("stg-does-not-exist", "topic")],
        )


def test_plan_rejects_stage_resource_pointing_to_unknown_stage() -> None:
    stage = PlanStage.create(
        stable_key="sk-1", title="阶段一", section_kind=OutlineSectionKind.CORE, order_index=0
    )
    with pytest.raises(ValidationAppError):
        PlanRevision.create(
            project_id="p1",
            revision=1,
            goal_snapshot="g",
            stages=[stage],
            stage_resources=[_primary("stg-does-not-exist", refs=("sec1",))],
        )


# --------------------------------------------------- 确定性校验接入 PlanRevision 边界


def _stage(order: int = 0) -> PlanStage:
    return PlanStage.create(
        stable_key=f"sk-{order}", title=f"阶段{order}", section_kind=OutlineSectionKind.CORE,
        order_index=order,
    )


def test_plan_revision_rejects_two_mainlines_in_one_stage() -> None:
    """主线数量硬约束：一个阶段两条 PRIMARY 时**发布边界直接失败**。"""
    stage = _stage()
    with pytest.raises(ValidationAppError) as exc:
        PlanRevision.create(
            project_id="p1",
            revision=1,
            goal_snapshot="g",
            stages=[stage],
            stage_resources=[
                _primary(stage.stage_id, refs=("sec1",), order=0),
                _primary(stage.stage_id, refs=("sec2",), order=1),
            ],
        )
    assert "主线" in str(exc.value)


def test_plan_revision_rejects_duplicate_section_refs() -> None:
    stage = _stage()
    with pytest.raises(ValidationAppError):
        PlanRevision.create(
            project_id="p1",
            revision=1,
            goal_snapshot="g",
            stages=[stage],
            stage_resources=[_primary(stage.stage_id, refs=("sec1", "sec1"))],
        )


def test_plan_revision_rejects_unsafe_extension_link() -> None:
    stage = _stage()
    with pytest.raises(ValidationAppError):
        PlanRevision.create(
            project_id="p1",
            revision=1,
            goal_snapshot="g",
            stages=[stage],
            extensions=[_ext(stage.stage_id, "topic", links=("http://169.254.1.1/x",))],
        )


def test_plan_revision_soft_limit_is_warning_not_error() -> None:
    """扩展软上限只进 ``validation_warnings``，不阻断构造/发布。"""
    stage = _stage()
    exts = [_ext(stage.stage_id, f"topic-{i}", order=i) for i in range(EXTENSION_SOFT_LIMIT + 1)]
    revision = PlanRevision.create(
        project_id="p1", revision=1, goal_snapshot="g", stages=[stage], extensions=exts
    )
    warnings = revision.validation_warnings()
    assert warnings and "超过建议上限" in warnings[0]


def test_plan_revision_within_limit_has_no_warnings() -> None:
    stage = _stage()
    revision = PlanRevision.create(
        project_id="p1",
        revision=1,
        goal_snapshot="g",
        stages=[stage],
        extensions=[_ext(stage.stage_id, "topic", order=0)],
    )
    assert revision.validation_warnings() == []


# ----------------------------------------------------------------------- 领域包最小模型


def test_domain_pack_published_only_usable_for_planning() -> None:
    draft = DomainPack.create(
        pack_key="agent_app_dev", version=1, supported_scope="agent 应用开发", title="Agent 应用开发"
    )
    assert not draft.is_published
    with pytest.raises(ValidationAppError):
        draft.require_published()
    published = DomainPack.create(
        pack_key="agent_app_dev",
        version=2,
        supported_scope="agent 应用开发",
        title="Agent 应用开发",
        status=DomainPackStatus.PUBLISHED,
    )
    published.require_published()  # 不抛错即通过


# ------------------------------------------------------------------- 「负能力」护栏


def test_curation_module_does_not_compute_duplicate_ratios() -> None:
    """V1 明确**不做**章节重叠率 / 覆盖率 / 作者选型分析（设计 §2.1）。

    这是「负能力」护栏：一旦有人往 curation 里加入比值/相似度计算，测试失败。
    """
    source = Path(curation.__file__).read_text(encoding="utf-8").lower()
    forbidden = (
        "overlap_ratio",
        "coverage_ratio",
        "duplicate_ratio",
        "jaccard",
        "similarity",
        "cosine",
    )
    hits = [token for token in forbidden if token in source]
    assert not hits, f"curation 模块不得包含重复度/覆盖率计算：{hits}"
