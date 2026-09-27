"""契约测试：新仓库必须**独立于 E 盘旧工程**。

对应验收条款：

- 「D 盘不依赖 E 盘环境、密钥和本地数据库，骨架能独立执行基本测试」
- 「不得创建指向 E 盘源码/数据库的软链接/目录联接」

这些测试是**机械的**：它们扫描本仓库内容，一旦有人把旧路径、
旧密钥或旧 env 前缀写进来，测试立刻失败。这比"评审时记得检查"可靠。
"""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_DIR = REPO_ROOT / "backend"

#: 旧工程路径特征。出现即视为依赖泄漏。
LEGACY_PATH_MARKERS = (
    "codex_workspace",
    "study-plan-prototype",
    "tiance002",
)

#: 旧工程 env 前缀（新工程统一用 STUDYPLAN_）。
LEGACY_ENV_PREFIXES = ("STUDY_PLATFORM_",)

#: 不应出现在仓库中的目录/文件名（本地运行数据与工具缓存）。
FORBIDDEN_DIR_NAMES = {
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".serena",
    ".trae",
    ".codex",
    ".agents",
    "var",
}

#: 允许提及旧路径的文件。
#: **文档必须能引用来源** —— 设计基线写明了 LEGACY_ROOT 路径，
#: 审计文档要记录旧 HEAD 与未推送分支。若禁止文档提及，
#: 这些交付物就无法写出来。
#: 关键区别：文档里出现旧路径是**引用**，代码里出现旧路径是**依赖**。
DOC_ALLOWLIST = ("docs/",)

#: 自身与安全断言文件必须提及这些标记（用于"断言其不存在"），故排除。
SELF_REFERENTIAL = (
    "backend/tests/contract/test_isolation_contract.py",
    "backend/tests/unit/test_security_boundaries.py",
)

#: 代码文件后缀（只有这些会被扫描"是否依赖旧路径"）。
CODE_SUFFIXES = {".py", ".toml", ".json", ".ts", ".tsx", ".cfg", ".ini", ".js", ".mjs", ".sh"}


def _is_code(rel: str, suffix: str) -> bool:
    """判断该文件是否参与"代码是否依赖旧工程"的扫描。

    排除：文档（需引用来源）、自指测试文件（需声明标记以断言其不存在）、
    非代码后缀。
    """
    if rel.startswith(DOC_ALLOWLIST):
        return False
    if rel in SELF_REFERENTIAL:
        return False
    return suffix in CODE_SUFFIXES


def _iter_source_files():
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(REPO_ROOT).as_posix()
        if any(part in FORBIDDEN_DIR_NAMES for part in path.relative_to(REPO_ROOT).parts):
            continue
        if rel.startswith(".git/"):
            continue
        yield path, rel


def test_no_legacy_path_references_in_code() -> None:
    """源码中不得引用 E 盘旧工程路径。

    迁移/审计文档中作为「来源引用」出现属正常，故排除白名单。
    """
    offenders: list[str] = []
    for path, rel in _iter_source_files():
        if not _is_code(rel, path.suffix):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for marker in LEGACY_PATH_MARKERS:
            if marker in text:
                offenders.append(f"{rel}: 含旧路径标记 {marker!r}")
    assert not offenders, "发现代码中的旧工程路径引用：\n" + "\n".join(offenders)


def test_no_legacy_env_prefix_in_code() -> None:
    """不得使用旧工程的 env 变量前缀。"""
    offenders: list[str] = []
    for path, rel in _iter_source_files():
        if not _is_code(rel, path.suffix):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for prefix in LEGACY_ENV_PREFIXES:
            if prefix in text:
                offenders.append(f"{rel}: 含旧 env 前缀 {prefix!r}")
    assert not offenders, "发现代码中的旧工程 env 前缀：\n" + "\n".join(offenders)


def test_no_local_runtime_data_committed() -> None:
    """本地运行数据（var/数据库/日志）不得出现在工作树中。

    排除工具链缓存目录（`.mypy_cache` / `.pytest_cache` / `.ruff_cache`）——
    它们由静态检查/测试工具生成，含 `.db` 缓存文件但与业务运行数据无关，
    且均已被 `.gitignore` 忽略。
    """
    ignored_dirs = {
        ".venv", "venv", "node_modules", "__pycache__",
        ".mypy_cache", ".pytest_cache", ".ruff_cache",
    }
    leaks: list[str] = []
    for path in REPO_ROOT.rglob("*"):
        rel = path.relative_to(REPO_ROOT).as_posix()
        if rel.startswith(".git/"):
            continue
        parts = path.relative_to(REPO_ROOT).parts
        if any(part in ignored_dirs for part in parts):
            continue
        if path.is_file() and path.suffix in {".sqlite", ".sqlite3", ".db"}:
            leaks.append(rel)
    assert not leaks, f"发现本地数据库文件：{leaks}"


def test_no_symlink_or_junction_to_legacy() -> None:
    """不得存在指向旧工程的软链接/目录联接。"""
    offenders: list[str] = []
    for path in REPO_ROOT.rglob("*"):
        rel = path.relative_to(REPO_ROOT).as_posix()
        if rel.startswith(".git/"):
            continue
        if path.is_symlink():
            target = os.readlink(path)
            offenders.append(f"{rel} -> {target}")
    assert not offenders, "发现软链接：\n" + "\n".join(offenders)


def test_env_example_uses_only_placeholder_values() -> None:
    """`.env.example` 只能含占位值，不得含真实密钥。

    只检查**真正承载凭据**的键（以 ``_SECRET`` / ``_API_KEY`` / ``_TOKEN``
    结尾），而不是任何含 "KEY"/"TOKEN" 子串的键 ——
    ``LLM_MAX_OUTPUT_TOKENS`` 这类上限配置是正常取值，不应误报。
    """
    env_example = REPO_ROOT / ".env.example"
    assert env_example.exists(), "缺少 .env.example"
    text = env_example.read_text(encoding="utf-8")
    for prefix in LEGACY_ENV_PREFIXES:
        assert prefix not in text

    secret_suffixes = ("_SECRET", "_API_KEY", "_TOKEN", "_PASSWORD")
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if not key.endswith(secret_suffixes):
            continue
        assert value.strip().startswith("CHANGE_ME") or value.strip() == "", (
            f"{key} 必须是占位值，实际为 {value!r}"
        )


def test_gitignore_covers_sensitive_paths() -> None:
    """.gitignore 必须覆盖 .env / .venv / var / node_modules。"""
    text = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    for required in (".env", ".venv", "var/", "node_modules/"):
        assert required in text, f".gitignore 缺少 {required!r}"


def test_readme_exists_and_describes_skeleton_state() -> None:
    """README 必须存在。"""
    readme = REPO_ROOT / "README.md"
    assert readme.exists()
    assert len(readme.read_text(encoding="utf-8")) > 200
