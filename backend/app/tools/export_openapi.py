"""导出 OpenAPI 契约。

由 ``scripts/export_openapi.sh`` 调用；也可直接运行::

    python -m app.tools.export_openapi

输出路径取 ``STUDYPLAN_OPENAPI_OUT``，默认 ``contracts/openapi.json``。
"""

from __future__ import annotations

import json
import os
from pathlib import Path


def _default_out() -> Path:
    # backend/app/tools/export_openapi.py -> 仓库根/contracts/openapi.json
    return Path(__file__).resolve().parents[3] / "contracts" / "openapi.json"


def render_openapi() -> str:
    """生成 OpenAPI 契约文本（确定性：同一代码 → 同一字节）。"""
    from app.main import create_app

    schema = create_app().openapi()
    return json.dumps(schema, ensure_ascii=False, indent=2) + "\n"


def main() -> None:
    out = Path(os.environ.get("STUDYPLAN_OPENAPI_OUT") or _default_out())
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_openapi(), encoding="utf-8")
    print(f"[export] 已写入 {out}")


if __name__ == "__main__":
    main()
