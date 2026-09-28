"""pg_harness 角色安全测试（B1.2 §一）。

核心安全属性：**绝不在共享实例上修改已有的全局角色**（密码 / CREATEDB /
BYPASSRLS 等）。不能证明实例专用时必须安全拒绝，且测试结束不遗留角色变更。

纯函数部分（``plan_role_action``）不需要数据库；带 ``postgres`` 标记的用例
在实例不安全时整组跳过。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from tests import pg_harness  # noqa: E402
from tests.pg_harness import (  # noqa: E402
    APP_ROLE,
    DEDICATED_ENV,
    MIGRATOR_ROLE,
    ROLE_SPECS,
    RoleSpec,
    UnsafeSharedInstanceError,
    instance_is_dedicated,
    plan_role_action,
    role_satisfies,
)

MIGRATOR_SPEC = ROLE_SPECS[MIGRATOR_ROLE]
APP_SPEC = ROLE_SPECS[APP_ROLE]


# ---------------------------------------------------------------------------
# 纯函数：动作决策
# ---------------------------------------------------------------------------


def test_role_satisfies_matches_exact_attributes() -> None:
    good = {
        "can_login": True,
        "superuser": False,
        "createdb": True,
        "createrole": False,
        "bypassrls": True,
    }
    assert role_satisfies(good, MIGRATOR_SPEC)
    bad = dict(good, bypassrls=False)
    assert not role_satisfies(bad, MIGRATOR_SPEC)


def test_plan_role_action_keeps_matching_role() -> None:
    existing = {
        "can_login": True,
        "superuser": False,
        "createdb": False,
        "createrole": False,
        "bypassrls": False,
    }
    assert plan_role_action(existing, APP_SPEC, dedicated=False) == "keep"


def test_plan_role_action_refuses_create_on_shared_instance() -> None:
    """共享实例上，角色缺失 -> 安全拒绝（不创建）。"""
    with pytest.raises(UnsafeSharedInstanceError):
        plan_role_action(None, MIGRATOR_SPEC, dedicated=False)


def test_plan_role_action_refuses_alter_on_shared_instance() -> None:
    """共享实例上，属性不符 -> 安全拒绝（不修改）。"""
    mismatched = {
        "can_login": True,
        "superuser": False,
        "createdb": False,  # 期望 True
        "createrole": False,
        "bypassrls": False,  # 期望 True
    }
    with pytest.raises(UnsafeSharedInstanceError):
        plan_role_action(mismatched, MIGRATOR_SPEC, dedicated=False)


def test_plan_role_action_allows_management_on_dedicated_instance() -> None:
    """专用实例上允许创建/修正。"""
    assert plan_role_action(None, MIGRATOR_SPEC, dedicated=True) == "create"
    mismatched = {
        "can_login": True,
        "superuser": False,
        "createdb": False,
        "createrole": False,
        "bypassrls": False,
    }
    assert plan_role_action(mismatched, MIGRATOR_SPEC, dedicated=True) == "alter"


def test_dedicated_flag_defaults_to_false(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(DEDICATED_ENV, raising=False)
    assert instance_is_dedicated() is False
    monkeypatch.setenv(DEDICATED_ENV, "1")
    assert instance_is_dedicated() is True


# ---------------------------------------------------------------------------
# 数据库级：不修改既有角色 / 拒绝创建未知角色
# ---------------------------------------------------------------------------


def _roles_present_and_satisfied() -> bool:
    for spec in ROLE_SPECS.values():
        state = pg_harness.fetch_role_state(spec.name)
        if state is None or not role_satisfies(state, spec):
            return False
    return True


@pytest.mark.postgres
def test_ensure_roles_is_noop_for_satisfied_existing_roles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """既有角色属性已满足时，``ensure_roles`` 必须**完全不修改**它们。

    以"调用前后属性快照完全一致" + "未记录任何自建角色"双重断言。
    """
    if not _roles_present_and_satisfied():
        pytest.skip("所需角色不存在或不满足；共享实例下无法安全建立，跳过")
    monkeypatch.delenv(DEDICATED_ENV, raising=False)

    before = {spec.name: pg_harness.fetch_role_state(spec.name) for spec in ROLE_SPECS.values()}
    assert before, "快照不得为空"

    pg_harness.ensure_roles()

    after = {spec.name: pg_harness.fetch_role_state(spec.name) for spec in ROLE_SPECS.values()}
    assert before == after, "ensure_roles 不得修改既有角色属性"
    assert pg_harness.roles_created_by_harness() == set(), "不得把既有角色记为自建"


@pytest.mark.postgres
def test_ensure_roles_refuses_to_create_missing_role_on_shared(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """共享实例上缺少角色时必须拒绝，且**确实没有创建**该角色。"""
    monkeypatch.delenv(DEDICATED_ENV, raising=False)
    fake_name = "studyplan_test_should_never_exist"
    fake_specs = {fake_name: RoleSpec(name=fake_name, password="x")}
    monkeypatch.setattr(pg_harness, "ROLE_SPECS", fake_specs)

    assert pg_harness.fetch_role_state(fake_name) is None, "前置：该角色不应存在"
    with pytest.raises(UnsafeSharedInstanceError):
        pg_harness.ensure_roles()
    assert pg_harness.fetch_role_state(fake_name) is None, "拒绝后不得创建角色"


@pytest.mark.postgres
def test_ensure_roles_refuses_to_alter_mismatched_role_on_shared(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """共享实例上属性不符时必须拒绝，且**属性保持不变**。"""
    monkeypatch.delenv(DEDICATED_ENV, raising=False)
    # 用一个已存在但属性必然不符的规格（把应用角色当成需要 CREATEDB 的角色）。
    wrong_spec = RoleSpec(
        name=APP_ROLE,
        password="x",
        createdb=True,      # 应用角色实际 NOCREATEDB
        bypassrls=True,     # 应用角色实际 NOBYPASSRLS
    )
    monkeypatch.setattr(pg_harness, "ROLE_SPECS", {APP_ROLE: wrong_spec})

    before = pg_harness.fetch_role_state(APP_ROLE)
    if before is None:
        pytest.skip("应用角色不存在，跳过")
    with pytest.raises(UnsafeSharedInstanceError):
        pg_harness.ensure_roles()
    after = pg_harness.fetch_role_state(APP_ROLE)
    assert before == after, "拒绝后不得修改角色属性"


@pytest.mark.postgres
def test_harness_skip_reason_is_readonly_and_consistent() -> None:
    """探测函数只读：调用前后角色集合不变。"""
    roles_before = _all_studyplan_roles()
    reason = pg_harness.harness_skip_reason()
    roles_after = _all_studyplan_roles()
    assert roles_before == roles_after, "探测不得创建/删除角色"
    # 本机既有角色满足要求时，应可安全运行
    if _roles_present_and_satisfied() and not instance_is_dedicated():
        assert reason is None


def _all_studyplan_roles() -> set[str]:
    with pg_harness.admin_connect("postgres") as conn:
        rows = conn.execute(
            "SELECT rolname FROM pg_roles WHERE rolname LIKE 'studyplan%'"
        ).fetchall()
    return {r[0] for r in rows}
