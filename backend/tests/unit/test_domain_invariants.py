"""领域层不变量测试。

这些测试直接对应 `SOFTWARE_DESIGN.md` 与 `docs/adr/` 中冻结的决策，
**不依赖** Postgres、网络、langgraph。

命名约定：``test_<不变量>``，使失败信息本身就能说明被违反的规则。
"""

from __future__ import annotations

import pytest
from app.core.errors import NotFoundError, ValidationAppError
from app.domain.catalog.models import (
    KnowledgeNode,
    KnowledgeRelation,
    LearningUnit,
    build_dependency_graph,
    validate_relations,
)
from app.domain.enums import (
    AiRunStatus,
    KnowledgeNodeType,
    MediaType,
    PreferenceScope,
    RelationType,
    ResourceProvenance,
    UnitProgress,
    can_transition_progress,
)
from app.domain.planning.models import validate_soft_limits
from app.domain.resources.models import (
    ResourcePreference,
    ResourceRecord,
    require_safe_url,
    resolve_preference,
)
from app.domain.workspace.models import DEFAULT_CREDENTIAL_POLICY

# ---------------------------------------------------------------------------
# enums（契约的一部分，改值即破坏 API）
# ---------------------------------------------------------------------------


def test_unit_progress_terminal_states_are_distinct() -> None:
    """跳过 ≠ 完成 ≠ 掌握。"""
    assert UnitProgress.SKIPPED != UnitProgress.COMPLETED
    assert UnitProgress.SKIPPED.value == "skipped"
    assert UnitProgress.COMPLETED.value == "completed"


def test_progress_can_return_from_skipped() -> None:
    """用户可返回已跳过的单元（设计 §1：「用户可跳过、返回」）。"""
    assert can_transition_progress(UnitProgress.SKIPPED, UnitProgress.IN_PROGRESS)
    assert can_transition_progress(UnitProgress.COMPLETED, UnitProgress.IN_PROGRESS)


def test_ai_run_status_covers_design_enum() -> None:
    """AiRun 状态枚举必须与设计 §8 完全一致。"""
    assert {s.value for s in AiRunStatus} == {
        "queued",
        "running",
        "waiting_user",
        "succeeded",
        "failed",
        "cancelled",
        "reconciliation_required",
    }


# ---------------------------------------------------------------------------
# catalog：依赖图无环
# ---------------------------------------------------------------------------


def test_dependency_graph_detects_cycle() -> None:
    """前置依赖成环必须被检出，且给出具体环路径。"""
    graph = build_dependency_graph(
        [
            KnowledgeRelation.create(
                scope="p1", from_id="a", to_id="b", relation_type=RelationType.PREREQUISITE
            ),
            KnowledgeRelation.create(
                scope="p1", from_id="b", to_id="c", relation_type=RelationType.PREREQUISITE
            ),
            KnowledgeRelation.create(
                scope="p1", from_id="c", to_id="a", relation_type=RelationType.PREREQUISITE
            ),
        ]
    )
    cycle = graph.find_cycle()
    assert cycle, "三元环必须被检出"
    assert not graph.is_acyclic()


def test_dependency_graph_acyclic_passes() -> None:
    graph = build_dependency_graph(
        [
            KnowledgeRelation.create(
                scope="p1", from_id="a", to_id="b", relation_type=RelationType.PREREQUISITE
            ),
            KnowledgeRelation.create(
                scope="p1", from_id="b", to_id="c", relation_type=RelationType.PREREQUISITE
            ),
        ]
    )
    assert graph.is_acyclic()
    assert graph.topological_order() == ["a", "b", "c"]


def test_related_relation_does_not_create_cycle() -> None:
    """`related` 不参与环判定（设计 §3：related/alternative 允许非树形）。"""
    graph = build_dependency_graph(
        [
            KnowledgeRelation.create(
                scope="p1", from_id="a", to_id="b", relation_type=RelationType.RELATED
            ),
            KnowledgeRelation.create(
                scope="p1", from_id="b", to_id="a", relation_type=RelationType.RELATED
            ),
        ]
    )
    assert graph.is_acyclic()


def test_validate_relations_rejects_cross_project() -> None:
    """跨项目关系必须拒绝。"""
    with pytest.raises(ValidationAppError):
        validate_relations(
            project_id="p1",
            relations=[
                KnowledgeRelation.create(
                    scope="p2", from_id="a", to_id="b", relation_type=RelationType.PREREQUISITE
                )
            ],
        )


def test_validate_relations_rejects_unknown_node() -> None:
    with pytest.raises(NotFoundError):
        validate_relations(
            project_id="p1",
            relations=[
                KnowledgeRelation.create(
                    scope="p1", from_id="a", to_id="ghost", relation_type=RelationType.PREREQUISITE
                )
            ],
            known_node_ids={"a", "b"},
        )


def test_node_stable_key_is_independent_of_title() -> None:
    """稳定键 ≠ 标题：改标题不改键（局部重规划依赖此性质）。"""
    node = KnowledgeNode.create(
        project_id="p1",
        stable_key="",
        title="向量检索",
        node_type=KnowledgeNodeType.CONCEPT,
    )
    original_key = node.stable_key
    node.revise_content(title="向量检索与近似最近邻")
    assert node.stable_key == original_key
    assert node.content_version == 2


def test_node_ai_draft_is_not_shared_by_default() -> None:
    """AI 生成先是项目草稿，不自动成为全局共享知识。"""
    node = KnowledgeNode.create(
        project_id="p1", stable_key="k", title="t", node_type=KnowledgeNodeType.TOOL
    )
    assert node.source_status == "ai_draft"


def test_unit_rubric_snapshot_carries_version() -> None:
    """rubric 快照必须携带版本，使旧总结可追溯。"""
    unit = LearningUnit.create(
        project_id="p1",
        stable_key="u1",
        title="RAG 基础",
        objectives=["理解检索"],
        rubric={"criteria": ["能解释召回率"]},
    )
    snapshot = unit.snapshot_rubric()
    assert snapshot["rubric_version"] == unit.rubric_version
    assert snapshot["stable_key"] == "u1"


# ---------------------------------------------------------------------------
# resources：SSRF 防护 + 偏好优先级
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/x",
        "http://10.0.0.1/x",
        "http://192.168.1.1/x",
        "http://169.254.169.254/latest/meta-data/",
        "http://localhost/x",
        "file:///etc/passwd",
        "javascript:alert(1)",
    ],
)
def test_require_safe_url_blocks_ssrf_and_bad_schemes(url: str) -> None:
    """私网地址 / 非 http(s) scheme 必须拒绝（防 SSRF）。"""
    with pytest.raises(ValidationAppError):
        require_safe_url(url)


@pytest.mark.parametrize(
    "url",
    ["https://fastapi.tiangolo.com/", "http://example.com/a/b?c=1#d"],
)
def test_require_safe_url_allows_public_http(url: str) -> None:
    assert require_safe_url(url) == url


def test_require_safe_url_rejects_embedded_credentials() -> None:
    with pytest.raises(ValidationAppError):
        require_safe_url("https://user:pass@example.com/x")


def test_preference_priority_node_beats_unit_beats_project() -> None:
    """节点 > 单元 > 项目默认 > 系统默认。"""
    project = ResourcePreference(scope=PreferenceScope.PROJECT, scope_ref="p1")
    unit = ResourcePreference(scope=PreferenceScope.UNIT, scope_ref="u1")
    node = ResourcePreference(scope=PreferenceScope.NODE, scope_ref="n1")
    assert resolve_preference(project=project, unit=unit, node=node).scope is PreferenceScope.NODE
    assert resolve_preference(project=project, unit=unit).scope is PreferenceScope.UNIT
    assert resolve_preference(project=project).scope is PreferenceScope.PROJECT
    assert resolve_preference().scope is PreferenceScope.SYSTEM


def test_unavailable_resource_keeps_record() -> None:
    """探测失败如实标记，**不删除记录**（保留历史与出处）。"""
    record = ResourceRecord.create(
        url="https://example.com/x",
        title="某教程",
        media_type=MediaType.TEXT,
        provenance=ResourceProvenance.CURATED_POOL,
        project_id="p1",
    )
    record.mark_unavailable()
    assert record.verification_status.value == "unavailable"


def test_resource_record_requires_project_id() -> None:
    """P1-07：``resource_records`` 是**项目私有**记录，``project_id`` 必填。

    公共受审核资源另设 ``PublicResourceSource``（只读、跨用户可读），
    两者不混成一张表；缺 project_id 的私有资源记录必须被拒绝。
    """
    with pytest.raises(ValidationAppError):
        ResourceRecord.create(
            url="https://example.com/x",
            title="某教程",
            media_type=MediaType.TEXT,
            provenance=ResourceProvenance.CURATED_POOL,
            project_id="",
        )


# ---------------------------------------------------------------------------
# planning：软上限只警告
# ---------------------------------------------------------------------------


def test_soft_limits_warn_but_do_not_block() -> None:
    """数量超限只产生 warning，不阻断发布（设计 §4）。"""
    warnings = validate_soft_limits(unit_count=999, node_count=1, task_count=1)
    assert warnings
    assert all("建议" in w for w in warnings)


# ---------------------------------------------------------------------------
# workspace：产品约束
# ---------------------------------------------------------------------------


def test_credential_policy_matches_product_constraint() -> None:
    """开放注册 / 中文用户名 / 6–12 位密码 / 无邀请码。"""
    policy = DEFAULT_CREDENTIAL_POLICY
    assert (policy.password_min, policy.password_max) == (6, 12)
    assert policy.require_invite_code is False


def test_credential_policy_accepts_chinese_username() -> None:
    assert DEFAULT_CREDENTIAL_POLICY.validate_username("学习规划者") == "学习规划者"


def test_credential_policy_accepts_short_chinese_username() -> None:
    assert DEFAULT_CREDENTIAL_POLICY.validate_username("张三") == "张三"


def test_credential_policy_rejects_bad_password_length() -> None:
    with pytest.raises(ValidationAppError):
        DEFAULT_CREDENTIAL_POLICY.validate_password("12345")
    with pytest.raises(ValidationAppError):
        DEFAULT_CREDENTIAL_POLICY.validate_password("1234567890123")


def test_credential_policy_rejects_whitespace_username() -> None:
    with pytest.raises(ValidationAppError):
        DEFAULT_CREDENTIAL_POLICY.validate_username("张 三")
