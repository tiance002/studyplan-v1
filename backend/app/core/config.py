"""应用配置。

唯一读取环境变量的地方。领域层与 ports 不感知配置来源。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


def _env(key: str, default: str | None = None) -> str:
    value = os.environ.get(key, default)
    if value is None:
        raise RuntimeError(f"missing required environment variable: {key}")
    return value


def _env_bool(key: str, default: bool = False) -> bool:
    raw = os.environ.get(key)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(key: str, default: int) -> int:
    raw = os.environ.get(key)
    if raw is None or not raw.strip():
        return default
    return int(raw)


@dataclass(frozen=True, slots=True)
class Settings:
    """进程级不可变配置快照。"""

    app_env: str
    app_name: str
    app_host: str
    app_port: int
    log_level: str

    database_url: str
    database_url_sync: str
    checkpoint_database_url: str

    session_secret: str
    session_cookie_name: str
    session_cookie_secure: bool
    session_ttl_seconds: int
    csrf_enabled: bool
    allow_origins: tuple[str, ...]

    llm_provider: str
    llm_base_url: str
    llm_api_key: str
    llm_model_id: str
    llm_timeout_seconds: int
    llm_max_output_tokens: int

    github_token: str
    rag_base_url: str
    rag_api_key: str
    rag_timeout_seconds: int

    worker_poll_interval_seconds: int
    worker_lease_seconds: int
    worker_max_attempts: int

    graph_max_repair_attempts: int
    graph_version: str

    # 骨架运行开关：允许在无 Postgres / 无云模型时启动
    repository_backend: str
    cors_allow_credentials: bool = True

    @property
    def is_development(self) -> bool:
        return self.app_env.lower() in {"development", "dev", "local"}

    @property
    def use_memory_repository(self) -> bool:
        return self.repository_backend.lower() == "memory"

    @property
    def use_fake_llm(self) -> bool:
        return self.llm_provider.lower() == "fake"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    raw_origins = os.environ.get("ALLOW_ORIGINS", "http://localhost:5173")
    return Settings(
        app_env=_env("APP_ENV", "development"),
        app_name=_env("APP_NAME", "studyplan"),
        app_host=_env("APP_HOST", "127.0.0.1"),
        app_port=_env_int("APP_PORT", 8000),
        log_level=_env("LOG_LEVEL", "INFO").upper(),
        database_url=_env("DATABASE_URL", ""),
        database_url_sync=_env("DATABASE_URL_SYNC", ""),
        checkpoint_database_url=_env("CHECKPOINT_DATABASE_URL", ""),
        session_secret=_env("SESSION_SECRET", "dev-only-insecure-secret"),
        session_cookie_name=_env("SESSION_COOKIE_NAME", "studyplan_session"),
        session_cookie_secure=_env_bool("SESSION_COOKIE_SECURE", False),
        session_ttl_seconds=_env_int("SESSION_TTL_SECONDS", 1209600),
        csrf_enabled=_env_bool("CSRF_ENABLED", True),
        allow_origins=tuple(o.strip() for o in raw_origins.split(",") if o.strip()),
        llm_provider=_env("LLM_PROVIDER", "fake"),
        llm_base_url=_env("LLM_BASE_URL", ""),
        llm_api_key=_env("LLM_API_KEY", ""),
        llm_model_id=_env("LLM_MODEL_ID", ""),
        llm_timeout_seconds=_env_int("LLM_TIMEOUT_SECONDS", 120),
        llm_max_output_tokens=_env_int("LLM_MAX_OUTPUT_TOKENS", 8000),
        github_token=_env("GITHUB_TOKEN", ""),
        rag_base_url=_env("RAG_BASE_URL", ""),
        rag_api_key=_env("RAG_API_KEY", ""),
        rag_timeout_seconds=_env_int("RAG_TIMEOUT_SECONDS", 10),
        worker_poll_interval_seconds=_env_int("WORKER_POLL_INTERVAL_SECONDS", 2),
        worker_lease_seconds=_env_int("WORKER_LEASE_SECONDS", 300),
        worker_max_attempts=_env_int("WORKER_MAX_ATTEMPTS", 3),
        graph_max_repair_attempts=_env_int("GRAPH_MAX_REPAIR_ATTEMPTS", 2),
        graph_version=_env("GRAPH_VERSION", "1"),
        repository_backend=_env("STUDYPLAN_REPOSITORY_BACKEND", "memory"),
    )


def reset_settings_cache() -> None:
    """测试用：清空配置缓存以便重新读取环境变量。"""
    get_settings.cache_clear()
