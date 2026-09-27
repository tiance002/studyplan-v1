"""规划结构校验器测试：逐条对应设计 §4 的校验清单。

    规划验证包含依赖无环、顺序一致、任务知识关联合法、数量软上限、
    必填验收标准。

每条规则都用一个"违反它的最小输入"来证明规则真的生效 ——
未被违反测试过的校验约等于没有校验。
"""

from __future__ import annotations

import pytest
from app.agent_workflows.validators import (
    SOFT_LIMIT_NODES,
    SOFT_LIMIT_UNITS,
    validate_plan_structure,
)


def _nodes(*keys: str) -> list[dict[str, object]]:
    return [{"stable_key": k, "title": k} for k in keys]


def test_valid_structure_passes() -> None:
    outcome = validate_plan_structure(
        nodes=_nodes("a", "b"),
        units=[{"stable_key": "u1", "order_index": 0}],
        relations=[
            {"from_stable_key": "a", "to_stable_key": "b", "relation_type": "prerequisite"}
        ],
        tasks=[{"stable_key": "t1", "order_index": 0, "acceptance": ["可验证"]}],
        task_knowledge_links=[
            {"task_stable_key": "t1", "node_stable_key": "a", "role": "core"}
        ],
    )
    assert outcome.ok, outcome.errors
    assert outcome.warnings == []


def test_cycle_is_rejected() -> None:
    outcome = validate_plan_structure(
        nodes=_nodes("a", "b", "c"),
        units=[],
        relations=[
            {"from_stable_key": "a", "to_stable_key": "b", "relation_type": "prerequisite"},
            {"from_stable_key": "b", "to_stable_key": "c", "relation_type": "prerequisite"},
            {"from_stable_key": "c", "to_stable_key": "a", "relation_type": "prerequisite"},
        ],
        tasks=[],
    )
    assert not outcome.ok
    assert any("环" in e for e in outcome.errors)


def test_duplicate_stable_key_is_rejected() -> None:
    outcome = validate_plan_structure(
        nodes=_nodes("a", "a"), units=[], relations=[], tasks=[]
    )
    assert not outcome.ok
    assert any("重复" in e for e in outcome.errors)


def test_empty_stable_key_is_rejected() -> None:
    outcome = validate_plan_structure(
        nodes=[{"stable_key": "  ", "title": "x"}], units=[], relations=[], tasks=[]
    )
    assert not outcome.ok


def test_duplicate_order_index_is_rejected() -> None:
    outcome = validate_plan_structure(
        nodes=[],
        units=[
            {"stable_key": "u1", "order_index": 0},
            {"stable_key": "u2", "order_index": 0},
        ],
        relations=[],
        tasks=[],
    )
    assert not outcome.ok
    assert any("order_index" in e for e in outcome.errors)


def test_negative_order_index_is_rejected() -> None:
    outcome = validate_plan_structure(
        nodes=[], units=[{"stable_key": "u1", "order_index": -1}], relations=[], tasks=[]
    )
    assert not outcome.ok




@pytest.mark.parametrize("bad", [3.7, 2.0, True, False, "3.0", "3.7", "abc", [3], {"v": 3}])
def test_non_integer_order_index_is_rejected_not_coerced(bad: object) -> None:
    """非整数 order_index 必须被拒绝，**不得静默截断**（Goal §9.1）。

    ``int(3.7) == 3``、``int(True) == 1`` 这类隐式转换会掩盖模型输出错误，
    必须显式报错。
    """
    outcome = validate_plan_structure(
        nodes=[],
        units=[{"stable_key": "u1", "order_index": bad}],
        relations=[],
        tasks=[],
    )
    assert not outcome.ok
    assert any("order_index" in e for e in outcome.errors)


def test_integer_valued_string_is_rejected() -> None:
    """连 "0"（整数字符串）也拒绝——校验器只接受真正的 int。"""
    outcome = validate_plan_structure(
        nodes=[],
        units=[{"stable_key": "u1", "order_index": "0"}],
        relations=[],
        tasks=[],
    )
    assert not outcome.ok



def test_missing_acceptance_is_rejected() -> None:
    """必填验收标准：任务是可验证交付物，没有验收标准无法验收。"""
    outcome = validate_plan_structure(
        nodes=[], units=[], relations=[], tasks=[{"stable_key": "t1", "order_index": 0, "acceptance": []}]
    )
    assert not outcome.ok
    assert any("验收标准" in e for e in outcome.errors)


def test_whitespace_only_acceptance_is_rejected() -> None:
    outcome = validate_plan_structure(
        nodes=[], units=[], relations=[], tasks=[{"stable_key": "t1", "order_index": 0, "acceptance": ["   "]}]
    )
    assert not outcome.ok


def test_task_link_to_unknown_node_is_rejected() -> None:
    outcome = validate_plan_structure(
        nodes=_nodes("a"),
        units=[],
        relations=[],
        tasks=[{"stable_key": "t1", "order_index": 0, "acceptance": ["ok"]}],
        task_knowledge_links=[
            {"task_stable_key": "t1", "node_stable_key": "ghost", "role": "core"}
        ],
    )
    assert not outcome.ok
    assert any("不存在的节点" in e for e in outcome.errors)


def test_task_link_with_bad_role_is_rejected() -> None:
    outcome = validate_plan_structure(
        nodes=_nodes("a"),
        units=[],
        relations=[],
        tasks=[{"stable_key": "t1", "order_index": 0, "acceptance": ["ok"]}],
        task_knowledge_links=[
            {"task_stable_key": "t1", "node_stable_key": "a", "role": "mandatory"}
        ],
    )
    assert not outcome.ok
    assert any("role" in e for e in outcome.errors)


def test_relation_to_unknown_node_is_rejected() -> None:
    outcome = validate_plan_structure(
        nodes=_nodes("a"),
        units=[],
        relations=[
            {"from_stable_key": "a", "to_stable_key": "ghost", "relation_type": "prerequisite"}
        ],
        tasks=[],
    )
    assert not outcome.ok


def test_self_relation_is_rejected() -> None:
    outcome = validate_plan_structure(
        nodes=_nodes("a"),
        units=[],
        relations=[{"from_stable_key": "a", "to_stable_key": "a", "relation_type": "prerequisite"}],
        tasks=[],
    )
    assert not outcome.ok


def test_bad_relation_type_is_rejected() -> None:
    outcome = validate_plan_structure(
        nodes=_nodes("a", "b"),
        units=[],
        relations=[
            {"from_stable_key": "a", "to_stable_key": "b", "relation_type": "depends_on"}
        ],
        tasks=[],
    )
    assert not outcome.ok


def test_soft_limit_produces_warning_not_error() -> None:
    """数量软上限：超限只警告，不阻断发布。"""
    outcome = validate_plan_structure(
        nodes=_nodes(*[f"n{i}" for i in range(SOFT_LIMIT_NODES + 5)]),
        units=[{"stable_key": f"u{i}", "order_index": i} for i in range(SOFT_LIMIT_UNITS + 3)],
        relations=[],
        tasks=[{"stable_key": "t1", "order_index": 0, "acceptance": ["ok"]}],
    )
    assert outcome.ok, "软上限不得阻断发布"
    assert any("建议上限" in w for w in outcome.warnings)


def test_related_relation_does_not_trigger_cycle_error() -> None:
    outcome = validate_plan_structure(
        nodes=_nodes("a", "b"),
        units=[],
        relations=[
            {"from_stable_key": "a", "to_stable_key": "b", "relation_type": "related"},
            {"from_stable_key": "b", "to_stable_key": "a", "relation_type": "related"},
        ],
        tasks=[],
    )
    assert outcome.ok, outcome.errors
