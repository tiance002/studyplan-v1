"""集成测试：应用可独立启动 + OpenAPI 契约可导出。

对应验收条款：

- 「目录不依赖 E 盘而启动」
- 「OpenAPI 无重复 operationId」
- 「前端可生成 TypeScript client」

这些测试**不需要 Postgres / 网络**（骨架模式）。
"""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi", reason="需要 fastapi 才能运行 HTTP 集成测试")


@pytest.fixture()
def app():
    from app.main import create_app

    return create_app()


def test_app_boots_without_database_or_network(app) -> None:
    """骨架必须能在无 Postgres、无云模型的环境启动。"""
    assert app is not None
    assert app.title == "studyplan API"


def test_healthz_reports_provider_honestly(app) -> None:
    """健康检查如实报告当前 provider，避免"以为在用云模型"。"""
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        resp = client.get("/healthz")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "llm_provider" in body and "repository_backend" in body
    assert "graph_version" in body


def test_openapi_has_no_duplicate_operation_ids(app) -> None:
    """验收条款：OpenAPI 无重复 operationId。"""
    spec = app.openapi()
    operation_ids: list[str] = []
    for path_item in spec.get("paths", {}).values():
        for operation in path_item.values():
            if isinstance(operation, dict) and "operationId" in operation:
                operation_ids.append(operation["operationId"])
    assert len(operation_ids) == len(set(operation_ids)), (
        f"存在重复 operationId：{operation_ids}"
    )


def test_openapi_is_exportable_for_client_generation(app) -> None:
    """OpenAPI 必须可 JSON 序列化（TS client 生成的前提）。"""
    import json

    spec = app.openapi()
    text = json.dumps(spec, ensure_ascii=False)
    assert len(text) > 100
    reloaded = json.loads(text)
    assert reloaded["info"]["title"] == "studyplan API"


def test_healthz_is_outside_api_prefix_by_design(app) -> None:
    """/healthz 是运维端点，不占用 /api/v1 业务命名空间。"""
    paths = set(app.openapi()["paths"].keys())
    assert "/healthz" in paths
    assert all(not p.startswith("/healthz/") for p in paths)


def _route_paths(app) -> set[str]:
    """收集应用**实际暴露**的路由路径。

    FastAPI 0.141 起 ``include_router`` 会插入惰性 ``_IncludedRouter`` 对象
    （它在运行期解析为真实路由），因此不能假定 ``app.routes`` 的每一项都有
    ``path``。这里对两种形态都做遍历：直接取 ``path``，或递归其
    ``original_router.routes``。这样断言与 FastAPI 内部实现解耦。
    """
    paths: set[str] = set()
    stack = list(app.routes)
    while stack:
        route = stack.pop()
        path = getattr(route, "path", None)
        if isinstance(path, str) and path:
            paths.add(path)
        nested = getattr(route, "original_router", None)
        if nested is not None:
            stack.extend(getattr(nested, "routes", ()) or ())
    return paths


def test_no_legacy_unprefixed_business_routes(app) -> None:
    """不得暴露旧的无前缀业务路由（设计 §7：消除重复路径）。"""
    paths = _route_paths(app)
    legacy_shapes = ("/plan/generate", "/projects", "/teaching", "/library", "/product")
    for path in paths:
        for shape in legacy_shapes:
            assert not path.startswith(shape), f"发现旧形态路由：{path}"


def test_business_routes_live_under_api_prefix(app) -> None:
    """业务端点必须统一挂在 ``/api/v1`` 命名空间下（运维/文档端点例外）。"""
    infra = {"/healthz", "/docs", "/docs/oauth2-redirect", "/redoc"}
    paths = _route_paths(app) - infra
    offenders = sorted(p for p in paths if not p.startswith("/api/v1/"))
    assert not offenders, f"发现未挂在 /api/v1 下的业务路由：{offenders}"
