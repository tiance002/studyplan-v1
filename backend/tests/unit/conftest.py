"""B1 骨架测试共享夹具。

**关键约束**：本文件**不得**依赖 E 盘（`LEGACY_ROOT`）的任何路径、
环境变量或数据库。测试必须能在只装了本仓库的干净环境里跑通。

标记约定：
- 默认测试：不需要 Postgres、不需要网络、不需要 langgraph。
- ``@pytest.mark.postgres``：需要本地 PostgreSQL；不可达时整组跳过。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

#: 让测试无需安装包即可 import app（与 pyproject 的 pythonpath 双保险）。
BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "postgres: 需要本地 PostgreSQL 才能运行")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Postgres 不可达时，跳过所有 postgres 标记的测试而不是失败。"""
    if _postgres_reachable():
        return
    skip = pytest.mark.skip(reason="本地 PostgreSQL 不可达；跳过 postgres 组")
    for item in items:
        if "postgres" in item.keywords:
            item.add_marker(skip)


def _postgres_reachable() -> bool:
    import os
    import socket

    dsn = os.environ.get("STUDYPLAN_TEST_DSN", "")
    host, port = "127.0.0.1", 5432
    if dsn:
        try:
            from urllib.parse import urlparse

            parsed = urlparse(dsn)
            host = parsed.hostname or host
            port = parsed.port or port
        except Exception:  # noqa: BLE001
            pass
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except OSError:
        return False
