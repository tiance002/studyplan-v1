"""架构边界测试：严格依赖方向必须被机械保证。

对应 `SOFTWARE_DESIGN.md` §1：

    api -> application -> domain & ports <- infrastructure

    严格依赖方向：`agent_workflows` 只通过应用服务/Ports 读写业务实体。
    **Domain 不得 import FastAPI、LangGraph、ORM、SDK。**

这条约束只写进文档是没有用的 —— 一次便利的 `import` 就会破坏它。
因此本测试用 AST 解析**每个源文件**的 import 语句，机械断言方向。

这与旧工程 `test_import_direction.py` 的立场一致
（见 docs/migration/module-reuse-matrix.md §3）。
"""

from __future__ import annotations

import ast
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[2] / "app"

#: domain 层**绝对禁止** import 的模块（含前缀匹配）。
DOMAIN_FORBIDDEN = (
    "fastapi",
    "starlette",
    "uvicorn",
    "langgraph",
    "langchain",
    "sqlalchemy",
    "alembic",
    "psycopg",
    "pydantic",  # domain 用 dataclass，不用 pydantic；DTO 校验在 api 层
    "argon2",
    "httpx",
    "requests",
    "app.api",
    "app.application",
    "app.infrastructure",
)

#: ports 层禁止 import（协议只依赖 domain 与标准库）。
PORTS_FORBIDDEN = (
    "fastapi",
    "starlette",
    "langgraph",
    "sqlalchemy",
    "psycopg",
    "app.infrastructure",
)

#: core 层禁止 import。
CORE_FORBIDDEN = (
    "fastapi",
    "starlette",
    "langgraph",
    "sqlalchemy",
    "app.domain",
    "app.api",
    "app.application",
    "app.infrastructure",
)


def _iter_modules():
    for path in APP_DIR.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        yield path


def _imports(path: Path) -> list[str]:
    """用 AST 提取所有 import 的模块名（不执行文件）。"""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.level == 0:
                names.append(node.module)
            elif node.level > 0:
                # 相对导入：解析为绝对路径便于统一判断
                names.append(f"__relative__{node.module or ''}")
    return names


def _violations(layer_dir: Path, forbidden: tuple[str, ...]) -> list[str]:
    found: list[str] = []
    for path in layer_dir.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        rel = path.relative_to(APP_DIR).as_posix()
        for name in _imports(path):
            for banned in forbidden:
                if name == banned or name.startswith(banned + "."):
                    found.append(f"{rel}: import {name!r} 违反依赖方向（禁止 {banned!r}）")
    return found


def test_domain_does_not_import_frameworks() -> None:
    """domain 层不得 import FastAPI / LangGraph / ORM / SDK。"""
    violations = _violations(APP_DIR / "domain", DOMAIN_FORBIDDEN)
    assert not violations, "domain 层依赖泄漏：\n" + "\n".join(violations)


def test_ports_do_not_import_infrastructure() -> None:
    """ports 层不得 import 基础设施实现。"""
    violations = _violations(APP_DIR / "ports", PORTS_FORBIDDEN)
    assert not violations, "ports 层依赖泄漏：\n" + "\n".join(violations)


def test_core_does_not_import_domain_or_frameworks() -> None:
    """core 层不得 import domain 或框架。"""
    violations = _violations(APP_DIR / "core", CORE_FORBIDDEN)
    assert not violations, "core 层依赖泄漏：\n" + "\n".join(violations)


def test_agent_workflows_does_not_import_infrastructure() -> None:
    """图只通过 Ports 与领域交互，不得直接 import 基础设施 DB 实现。

    ⚠️ 例外：`infrastructure.providers` 是**装配层**（组合根的一部分），
    图本身不 import 它；这里断言图不 import `db` / `worker` / `checkpointer`。
    """
    violations = _violations(
        APP_DIR / "agent_workflows",
        ("app.infrastructure.db", "app.infrastructure.worker", "app.infrastructure.checkpointer"),
    )
    assert not violations, "图层依赖泄漏：\n" + "\n".join(violations)


def test_agent_workflows_imports_msgpack_guard_first() -> None:
    """`_msgpack_guard` 必须在 langgraph 之前被执行。

    断言 `agent_workflows/__init__.py` 的第一条 import 语句是 guard，
    因为只有这样才能保证 `LANGGRAPH_STRICT_MSGPACK` 在 langgraph
    被任何模块加载前就位（SOFTWARE_DESIGN.md §5）。
    """
    init = APP_DIR / "agent_workflows" / "__init__.py"
    tree = ast.parse(init.read_text(encoding="utf-8"), filename=str(init))
    first_import: str | None = None
    for node in tree.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            continue  # 允许前面的 docstring
        if isinstance(node, ast.ImportFrom):
            if node.module == "__future__":
                continue  # `from __future__ import annotations` 不加载任何模块
            first_import = node.module or ""
            break
        if isinstance(node, ast.Import):
            first_import = node.names[0].name
            break
    assert first_import is not None, "未找到 import 语句"
    assert "msgpack_guard" in first_import, (
        f"第一条 import 必须是 _msgpack_guard，实际为 {first_import!r}"
    )


def test_no_module_imports_langgraph_before_guard() -> None:
    """除 graphs.py 的受控 try-import 外，不得有模块在 guard 之前 import langgraph。

    本测试扫描所有源文件，若某文件 import langgraph 但**没有**先 import
    `app.agent_workflows`（从而触发 guard），即视为违反。
    """
    offenders: list[str] = []
    for path in _iter_modules():
        rel = path.relative_to(APP_DIR).as_posix()
        if rel.startswith("agent_workflows/"):
            continue  # 该包自身由 __init__ 保证顺序
        names = _imports(path)
        if any(n == "langgraph" or n.startswith("langgraph.") for n in names):
            offenders.append(rel)
    assert not offenders, (
        "以下模块直接 import langgraph，绕过了 strict-msgpack guard："
        + "\n".join(offenders)
        + "\n请改为通过 app.agent_workflows 间接使用。"
    )
