#!/usr/bin/env bash
# 统一测试入口（Goal §9.5）：覆盖 unit / contract / integration 三层。
#
# 用法：
#   bash scripts/test.sh              # 全部默认测试（unit + contract + integration）
#   bash scripts/test.sh unit         # 只跑 unit
#   bash scripts/test.sh contract     # 只跑 contract
#   bash scripts/test.sh integration  # 只跑 integration（PG 相关测试在不可达时自动跳过）
#   bash scripts/test.sh all          # 显式跑全部三层
#
# 环境说明：
#   - 不需要 Postgres / 网络 / langgraph / E 盘旧工程即可跑 unit + contract。
#   - integration 中标记 `postgres` 的用例在本地 PG 不可达时**整组跳过**（非失败）。
#   - 若 backend/.venv 不存在则自动创建（隔离在仓库内，不影响系统 Python）。
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

# 三层测试目录。
ALL_TARGETS=(backend/tests/unit backend/tests/contract backend/tests/integration)

case "${1:-}" in
  unit|contract|integration)
    echo "[test] 运行 backend/tests/$1"
    exec "$PY" -m pytest "backend/tests/$1" "${@:2}"
    ;;
  all|"")
    echo "[test] 运行全部测试（unit + contract + integration）"
    exec "$PY" -m pytest "${ALL_TARGETS[@]}" "$@"
    ;;
  *)
    echo "[test] 未知目标：$1" >&2
    echo "[test] 可用：unit | contract | integration | all" >&2
    exit 2
    ;;
esac
