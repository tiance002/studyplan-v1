#!/usr/bin/env bash
# 安全测试入口：不需要 Postgres / 网络 / langgraph / E 盘旧工程。
#
# 用法：
#   bash scripts/test.sh              # 全部默认测试
#   bash scripts/test.sh unit         # 只跑 unit
#   bash scripts/test.sh contract     # 只跑 contract
#
# 若 backend/.venv 不存在则自动创建（隔离在仓库内，不影响系统 Python）。
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

VENV=".venv"
PY="$VENV/Scripts/python.exe"
[ -x "$PY" ] || PY="$VENV/bin/python"

if [ ! -x "$PY" ]; then
  echo "[test] 未找到 $VENV，正在创建隔离虚拟环境…"
  python -m venv "$VENV"
  PY="$VENV/Scripts/python.exe"
  [ -x "$PY" ] || PY="$VENV/bin/python"
  "$PY" -m pip install -q --upgrade pip
  "$PY" -m pip install -q pytest
fi

TARGET="${1:-}"
if [ -z "$TARGET" ]; then
  echo "[test] 运行全部默认测试（unit + contract）"
  exec "$PY" -m pytest backend/tests/unit backend/tests/contract "$@"
fi

echo "[test] 运行 backend/tests/$TARGET"
exec "$PY" -m pytest "backend/tests/$TARGET" "${@:2}"
