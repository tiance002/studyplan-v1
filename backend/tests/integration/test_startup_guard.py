"""启动安全门禁（Goal §8）。

关键：测试必须调用**真实应用工厂** `create_app()` 验证失败行为，
而不是孤立地测守卫函数本身——否则"守卫被引用"这件事没有被证明。
"""

from __future__ import annotations

import pytest
from app.core.config import get_settings, reset_settings_cache
from app.core.startup_guard import (
    StartupSecurityError,
    validate_startup_security,
)


@pytest.fixture(autouse=True)
def _fresh_settings():
    reset_settings_cache()
    yield
    reset_settings_cache()


def _production_env(**overrides: str) -> None:
    import os

    base = {
        "APP_ENV": "production",
        "SESSION_SECRET": "a-very-strong-production-secret-value",
        "DATABASE_URL": "postgresql://app:pw@db:5432/studyplan",
        "DATABASE_URL_SYNC": "postgresql://app:pw@db:5432/studyplan",
        "CHECKPOINT_DATABASE_URL": "postgresql://ckpt:pw@db:5432/studyplan_checkpoint",
        "STUDYPLAN_REPOSITORY_BACKEND": "postgres",
        "LLM_PROVIDER": "fake",  # NOTE: 默认 fake，各测试自行覆盖
    }
    for key, value in {**base, **overrides}.items():
        os.environ[key] = value
    reset_settings_cache()


# ----------------------------------------------------- 开发环境放行

def test_development_allows_skeleton_defaults() -> None:
    import os

    os.environ["APP_ENV"] = "development"
    reset_settings_cache()
    # 不抛错
    validate_startup_security(get_settings())


# ----------------------------------------------------- 真实应用工厂：生产拒绝

def test_create_app_rejects_fake_llm_in_production() -> None:
    _production_env(LLM_PROVIDER="fake")
    from app.main import create_app

    with pytest.raises(StartupSecurityError, match="fake"):
        create_app()


def test_create_app_rejects_default_dev_secret() -> None:
    _production_env(
        LLM_PROVIDER="openai",
        SESSION_SECRET="dev-only-insecure-secret",
    )
    from app.main import create_app

    with pytest.raises(StartupSecurityError, match="SESSION_SECRET|密钥"):
        create_app()


def test_create_app_rejects_missing_database() -> None:
    _production_env(LLM_PROVIDER="openai", DATABASE_URL="")
    from app.main import create_app

    with pytest.raises(StartupSecurityError, match="DATABASE_URL"):
        create_app()


def test_create_app_rejects_memory_checkpointer() -> None:
    _production_env(
        LLM_PROVIDER="openai",
        CHECKPOINT_DATABASE_URL="memory://",
    )
    from app.main import create_app

    with pytest.raises(StartupSecurityError, match="Checkpointer|内存"):
        create_app()


def test_create_app_rejects_checkpointer_sharing_business_db() -> None:
    _production_env(LLM_PROVIDER="openai")
    import os

    os.environ["CHECKPOINT_DATABASE_URL"] = os.environ["DATABASE_URL"]
    reset_settings_cache()
    from app.main import create_app

    with pytest.raises(StartupSecurityError, match="独立"):
        create_app()


def test_create_app_rejects_memory_repository_in_production() -> None:
    _production_env(LLM_PROVIDER="openai", STUDYPLAN_REPOSITORY_BACKEND="memory")
    from app.main import create_app

    with pytest.raises(StartupSecurityError, match="memory"):
        create_app()


def test_create_app_rejects_declared_but_unimplemented_provider() -> None:
    """声明可用但未实现的真实 provider（B3 范围）→ 拒绝启动。"""
    _production_env(LLM_PROVIDER="anthropic")
    from app.main import create_app

    with pytest.raises(StartupSecurityError, match="anthropic|尚未实现"):
        create_app()


def test_production_failure_never_silently_falls_back_to_fake() -> None:
    """失败必须显式，绝不静默降级为 Fake。"""
    _production_env(LLM_PROVIDER="fake")
    from app.main import create_app

    with pytest.raises(StartupSecurityError):
        create_app()
