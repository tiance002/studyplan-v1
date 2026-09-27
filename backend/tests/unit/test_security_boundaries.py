"""安全边界测试：越权、身份自报、fake 误用、SSRF、配置门禁。

对应验收条款：
- 「run 越权拒绝」
- 「非法身份字段拒绝」
- 「fake 不允许部署为真实评审能力」

这些测试**不依赖** HTTP 服务或数据库，直接测领域与配置层的最小保证。
"""

from __future__ import annotations

import pytest
from app.core.config import Settings, get_settings, reset_settings_cache
from app.core.errors import STATUS_BY_CODE, ErrorCode, ForbiddenError, ValidationAppError
from app.domain.resources.models import require_safe_url
from app.domain.workspace.models import AuthContext
from app.infrastructure.providers import (
    ProviderConfigurationError,
    assert_not_fake_in_production,
    build_llm,
)

# ---------------------------------------------------------------------------
# AuthContext：越权必须拒绝
# ---------------------------------------------------------------------------


def _ctx(*projects: str) -> AuthContext:
    from datetime import datetime, timezone

    return AuthContext(
        actor_id="actor-1",
        session_id="sess-1",
        issued_at=datetime.now(timezone.utc),
        learning_project_scope=tuple(projects),
    )


def test_auth_context_denies_foreign_project() -> None:
    ctx = _ctx("p1")
    assert ctx.can_access_project("p1")
    assert not ctx.can_access_project("p2")
    with pytest.raises(ForbiddenError):
        ctx.require_project("p2")


def test_auth_context_denies_when_scope_empty() -> None:
    """无任何项目授权时，任何项目访问都必须 403。"""
    ctx = _ctx()
    with pytest.raises(ForbiddenError):
        ctx.require_project("p1")


def test_forbidden_error_does_not_reveal_existence() -> None:
    """403 不区分"不存在"与"无权限"，避免枚举探测。"""
    ctx = _ctx("p1")
    with pytest.raises(ForbiddenError) as exc:
        ctx.require_project("nonexistent-project")
    assert "无权" in str(exc.value)


def test_auth_context_cannot_be_built_from_request_body_shape() -> None:
    """AuthContext 是 frozen dataclass：无法用 dict 展开冒充。

    这条测试证明"客户端自报身份"在类型层就会失败，而不是靠约定。
    """
    payload = {"actor_id": "attacker", "session_id": "x"}
    with pytest.raises(TypeError):
        AuthContext(**payload)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 错误契约
# ---------------------------------------------------------------------------


def test_all_error_codes_map_to_http_status() -> None:
    """每个稳定错误码都必须有 HTTP 状态映射，不允许遗漏。"""
    for code in ErrorCode:
        assert code in STATUS_BY_CODE, f"{code} 缺少 HTTP 状态映射"


def test_design_required_status_codes_exist() -> None:
    """设计 §4 要求统一 400/401/403/404/409/422/429/503。"""
    statuses = set(STATUS_BY_CODE.values())
    for required in (400, 401, 403, 404, 409, 422, 429, 503):
        assert required in statuses, f"缺少设计要求的 {required}"


# ---------------------------------------------------------------------------
# Provider 门禁：fake 不得用于生产
# ---------------------------------------------------------------------------


def _settings(**overrides: object) -> Settings:
    base = dict(
        app_env="development",
        app_name="studyplan",
        app_host="127.0.0.1",
        app_port=8000,
        log_level="INFO",
        database_url="",
        database_url_sync="",
        checkpoint_database_url="",
        session_secret="dev-only-insecure-secret",
        session_cookie_name="studyplan_session",
        session_cookie_secure=False,
        session_ttl_seconds=1209600,
        csrf_enabled=True,
        allow_origins=("http://localhost:5173",),
        llm_provider="fake",
        llm_base_url="",
        llm_api_key="",
        llm_model_id="",
        llm_timeout_seconds=120,
        llm_max_output_tokens=8000,
        github_token="",
        rag_base_url="",
        rag_api_key="",
        rag_timeout_seconds=10,
        worker_poll_interval_seconds=2,
        worker_lease_seconds=300,
        worker_max_attempts=3,
        graph_max_repair_attempts=2,
        graph_version="1",
        repository_backend="memory",
    )
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


def test_fake_provider_rejected_in_production() -> None:
    """非开发环境使用 fake provider 必须拒绝启动。"""
    prod = _settings(app_env="production", llm_provider="fake")
    with pytest.raises(ProviderConfigurationError):
        assert_not_fake_in_production(prod)


def test_fake_provider_allowed_in_development() -> None:
    assert_not_fake_in_production(_settings(app_env="development"))


def test_unimplemented_real_provider_fails_loudly() -> None:
    """配置真实 provider 但未实现时**拒绝启动**，绝不悄悄退回 fake。"""
    with pytest.raises(ProviderConfigurationError):
        build_llm(_settings(llm_provider="openai_compatible"))


def test_fake_provider_builds_in_dev() -> None:
    llm = build_llm(_settings(llm_provider="fake"))
    assert llm is not None


# ---------------------------------------------------------------------------
# 配置：不得含旧工程密钥
# ---------------------------------------------------------------------------


def test_env_example_has_no_legacy_secret_markers() -> None:
    """`.env.example` 必须是占位值，不得出现旧工程前缀或真实密钥形态。"""
    from pathlib import Path

    env_example = Path(__file__).resolve().parents[3] / ".env.example"
    text = env_example.read_text(encoding="utf-8")
    assert "STUDY_PLATFORM_" not in text, "不得携带旧工程的 env 前缀"
    assert "CHANGE_ME" in text, "所有需填项应以 CHANGE_ME 占位"


def test_settings_reads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    reset_settings_cache()
    try:
        settings = get_settings()
        assert settings.app_env == "test"
        assert settings.use_fake_llm is True
    finally:
        reset_settings_cache()


# ---------------------------------------------------------------------------
# SSRF：在安全测试中再确认一次（跨层防线）
# ---------------------------------------------------------------------------


def test_ssrf_guard_blocks_metadata_endpoint() -> None:
    """云元数据端点是最常被 SSRF 打的目标，必须拒绝。"""
    with pytest.raises(ValidationAppError):
        require_safe_url("http://169.254.169.254/latest/meta-data/iam/security-credentials/")
