"""``/api/v1`` 业务 DTO 契约测试（Goal §5）。

覆盖：

- OpenAPI ``components.schemas`` 必须包含全部注册 DTO（否则前端拿不到类型）；
- 提交的 ``contracts/openapi.json`` 与**重新导出**结果逐字节一致（防契约漂移）；
- ``contracts/examples/`` 的每个示例都由对应 DTO 机械校验（不是手写假数据）；
- 硬约束：``AuthContext`` 永不出现在可写请求体；``null`` 与 ``[]`` 语义分开。
"""

from __future__ import annotations

import json
from pathlib import Path

from app.api.v1.schemas import V1_SCHEMAS
from app.main import create_app
from app.tools.export_openapi import render_openapi

REPO_ROOT = Path(__file__).resolve().parents[3]
OPENAPI = REPO_ROOT / "contracts" / "openapi.json"
EXAMPLES = REPO_ROOT / "contracts" / "examples" / "v1_examples.json"
FRONTEND_SCHEMA = REPO_ROOT / "frontend" / "src" / "api" / "generated" / "schema.d.ts"

#: 可写请求体里绝对不得出现的授权字段（由服务端会话派生，ADR-0004 第 4 条）。
FORBIDDEN_REQUEST_FIELDS = frozenset(
    {
        "auth_context",
        "actor_id",
        "session_id",
        "tenant_id",
        "learning_project_scope",
        "owner_actor_id",
    }
)

REQUEST_MODEL_NAMES = frozenset(
    {
        "PlanGenerateRequest",
        "PrefsSnapshot",
        "DraftDecisionRequest",
        "ProgressPatchRequest",
        "PreferenceUpdateRequest",
        "SummaryCreateRequest",
        "PromptRevisionCreateRequest",
    }
)


def _examples() -> dict[str, object]:
    return json.loads(EXAMPLES.read_text(encoding="utf-8"))


# ------------------------------------------------------------------ OpenAPI 覆盖


def test_openapi_contains_every_registered_schema() -> None:
    schemas = create_app().openapi()["components"]["schemas"]
    missing = [m.__name__ for m in V1_SCHEMAS if m.__name__ not in schemas]
    assert not missing, f"以下 DTO 未进入 OpenAPI 契约：{missing}"


def test_committed_openapi_matches_fresh_export() -> None:
    """契约漂移门禁：改了 DTO 却忘记重新导出，本测试失败。"""
    committed = OPENAPI.read_text(encoding="utf-8")
    fresh = render_openapi()
    assert committed == fresh, (
        "contracts/openapi.json 与当前代码不一致；请运行 "
        "`bash scripts/export_openapi.sh && (cd frontend && npm run gen:api)` 后提交。"
    )


def test_frontend_generated_types_cover_business_dtos() -> None:
    """生成物必须包含业务 DTO（否则前端拿不到类型）。"""
    text = FRONTEND_SCHEMA.read_text(encoding="utf-8")
    missing = [m.__name__ for m in V1_SCHEMAS if f"{m.__name__}:" not in text]
    assert not missing, f"前端生成类型缺少 DTO：{missing}"


# ------------------------------------------------------------------ 示例有效性


def test_every_example_has_a_dto_mapping() -> None:
    data = _examples()
    mapping = data["$schema_map"]
    assert isinstance(mapping, dict)
    example_keys = {k for k in data if not k.startswith("$")}
    assert example_keys == set(mapping), (
        f"示例与 $schema_map 不匹配：缺少映射 {example_keys - set(mapping)}，"
        f"多余映射 {set(mapping) - example_keys}"
    )


def test_examples_validate_against_their_dtos() -> None:
    data = _examples()
    mapping = data["$schema_map"]
    assert isinstance(mapping, dict)
    by_name = {m.__name__: m for m in V1_SCHEMAS}
    for key, dto_name in mapping.items():
        assert dto_name in by_name, f"示例 {key} 指向未注册 DTO：{dto_name}"
        by_name[dto_name].model_validate(data[key])  # 不合法即抛 ValidationError


# --------------------------------------------------------------------- 硬约束


def test_auth_context_never_appears_in_writable_request_bodies() -> None:
    """AuthContext 由服务端会话派生，**永不**出现在可写请求体。"""
    by_name = {m.__name__: m for m in V1_SCHEMAS}
    offenders: list[str] = []
    for name in sorted(REQUEST_MODEL_NAMES):
        model = by_name[name]
        leaked = FORBIDDEN_REQUEST_FIELDS & set(model.model_fields)
        if leaked:
            offenders.append(f"{name}: {sorted(leaked)}")
    assert not offenders, "可写请求体泄露授权字段：\n" + "\n".join(offenders)


def test_optional_list_fields_default_to_empty_list_not_null() -> None:
    """``null`` 与 ``[]`` 语义分开：可选集合字段必须默认 ``[]``，不得为 ``null``。"""
    offenders: list[str] = []
    for model in V1_SCHEMAS:
        for field_name, info in model.model_fields.items():
            annotation = info.annotation
            if getattr(annotation, "__origin__", None) is not list:
                continue
            if info.is_required():
                continue
            if info.default_factory is not list:
                offenders.append(f"{model.__name__}.{field_name}")
    assert not offenders, f"以下可选集合字段默认不是 []：{offenders}"


def test_run_view_never_exposes_graph_internals() -> None:
    """RunView 只暴露稳定 status/next_action，不含图内部节点名。"""
    run_view = next(m for m in V1_SCHEMAS if m.__name__ == "RunView")
    assert set(run_view.model_fields) == {
        "run_id",
        "status",
        "next_action",
        "version",
        "result_ref",
        "error",
    }
