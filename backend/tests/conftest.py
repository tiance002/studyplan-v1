"""全测试共享夹具（unit / contract / integration 三层通用）。

**关键约束**：本文件**不得**依赖 E 盘（`LEGACY_ROOT`）的任何路径、
环境变量或数据库。测试必须能在只装了本仓库的干净环境里跑通。

标记约定：
- 默认测试：不需要 Postgres、不需要网络、不需要 langgraph。
- ``@pytest.mark.postgres``：需要本地 PostgreSQL；不可达或**无法安全运行**时整组跳过。
- ``@pytest.mark.langgraph``：需要安装 langgraph；缺失时整组跳过。

## postgres 组的"安全跳过"（B1.2 §一）

``pg_harness`` 只允许在**专用实例**上创建/修改全局角色。若实例是共享的
且所需角色缺失/属性不符，harness 会安全拒绝。此时 postgres 组必须
**跳过**而不是失败——安全属性优先于"跑满测试"。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

#: 让测试无需安装包即可 import app（与 pyproject 的 pythonpath 双保险）。
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "postgres: 需要本地 PostgreSQL 才能运行")
    config.addinivalue_line("markers", "langgraph: 需要安装 langgraph 才能运行")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """PG 不可达 / 无法安全运行时，跳过所有 postgres 标记的测试而不是失败。"""
    reason = _postgres_skip_reason()
    if reason is None:
        return
    skip = pytest.mark.skip(reason=reason)
    for item in items:
        if "postgres" in item.keywords:
            item.add_marker(skip)


def _postgres_skip_reason() -> str | None:
    """惰性探测 PG 可用性与角色安全性（只读，无副作用）。"""
    try:
        from tests.pg_harness import harness_skip_reason
    except Exception as exc:  # noqa: BLE001 - 缺 psycopg 等依赖时同样跳过
        return f"无法加载 pg_harness：{exc}"
    return harness_skip_reason()


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """收尾：只删除**本进程创建**的测试角色，绝不触碰已有角色。"""
    try:
        from tests.pg_harness import drop_roles_created_by_harness
    except Exception:  # noqa: BLE001
        return
    dropped = drop_roles_created_by_harness()
    if dropped:
        reporter = session.config.pluginmanager.get_plugin("terminalreporter")
        if reporter is not None:
            reporter.write_line(f"[pg_harness] 已清理本进程创建的角色：{dropped}")
