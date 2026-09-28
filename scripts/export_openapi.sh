#!/usr/bin/env bash
# 导出 OpenAPI 契约到 contracts/openapi.json（契约真相源是 Pydantic DTO，ADR-0004）。
#
# 用法：
#   bash scripts/export_openapi.sh
#
# 生成后前端用 `npm run gen:api` 重新生成 src/api/generated/schema.d.ts。
# 契约测试会校验「重新导出后与提交物无差异」，因此**必须提交**本脚本的产物。
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$REPO_ROOT/.venv/Scripts/python.exe"
[ -x "$PY" ] || PY="$REPO_ROOT/.venv/bin/python"

if [ ! -x "$PY" ]; then
  echo "[export] 缺少虚拟环境，请先运行：bash scripts/test.sh" >&2
  exit 1
fi

cd "$REPO_ROOT/backend"
export APP_ENV="${APP_ENV:-development}"
export LLM_PROVIDER="${LLM_PROVIDER:-fake}"
export STUDYPLAN_REPOSITORY_BACKEND="${STUDYPLAN_REPOSITORY_BACKEND:-memory}"
export STUDYPLAN_OPENAPI_OUT="$REPO_ROOT/contracts/openapi.json"

exec "$PY" -m app.tools.export_openapi
