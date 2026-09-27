#!/usr/bin/env bash
# 安全启动入口（骨架模式：内存仓储 + Fake 模型，不需要 Postgres）。
#
# ⚠️ 本脚本**不连接** E 盘旧工程、不使用旧密钥、不读取旧数据库。
#
# 用法：
#   bash scripts/dev.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT/backend"

VENV="$REPO_ROOT/.venv"
PY="$VENV/Scripts/python.exe"
[ -x "$PY" ] || PY="$VENV/bin/python"

if [ ! -x "$PY" ]; then
  echo "[dev] 缺少虚拟环境，请先运行：bash scripts/test.sh" >&2
  exit 1
fi

# 骨架模式：Fake 模型 + 内存仓储。**不要**在生产设置这两个值。
export APP_ENV="${APP_ENV:-development}"
export LLM_PROVIDER="${LLM_PROVIDER:-fake}"
export STUDYPLAN_REPOSITORY_BACKEND="${STUDYPLAN_REPOSITORY_BACKEND:-memory}"
# 必须在 import langgraph 之前生效（由 app.agent_workflows 保证）。
export LANGGRAPH_STRICT_MSGPACK="${LANGGRAPH_STRICT_MSGPACK:-true}"

echo "[dev] APP_ENV=$APP_ENV LLM_PROVIDER=$LLM_PROVIDER REPO=$STUDYPLAN_REPOSITORY_BACKEND"
echo "[dev] LANGGRAPH_STRICT_MSGPACK=$LANGGRAPH_STRICT_MSGPACK"
echo "[dev] 启动 uvicorn（骨架阶段无业务路由，B2 补齐）"

exec "$PY" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
