"""启动期安全门禁（Goal §8）。

`assert_not_fake_in_production` 之类的守卫必须被**真实启动路径**调用，
否则形同虚设。本模块把生产配置校验收敛到 __一处__，由组合根
(`create_app`) 在构建应用时调用；任何不合法配置都会在启动期**显式抛错**，
绝不静默退回 Fake / 内存实现。

生产必须拒绝：
1. Fake LLM（`llm_provider=fake`）
2. 默认开发会话密钥（`dev-only-insecure-secret`）
3. 非法数据库配置（生产不得使用空 DSN）
4. 不安全的 Checkpointer 配置（生产必须使用 Postgres Checkpointer）
5. 被误开启的内存持久化后端（`repository_backend=memory`）
6. 声明可用但尚未实现的真实 Provider（凭据缺失 / 未知 provider）

开发环境全部放行（骨架模式需要能在无 PG / 无云模型时启动）。
"""

from __future__ import annotations

from app.core.config import Settings

#: 开发默认密钥，生产出现即为致命错误。
INSECURE_SESSION_SECRETS = frozenset(
    {"dev-only-insecure-secret", "changeme", "secret", ""}
)

#: 当前**实际实现**的 provider 名称闭集。core 层不得 import infrastructure，
#: 因此这里独立声明（infrastructure.providers.SUPPORTED_PROVIDERS 必须与本集合一致，
#: 由契约测试机械校验，避免两处漂移）。
SUPPORTED_PROVIDERS = frozenset({"fake"})

#: 声明"已支持"但**实际未实现**的真实 provider（B3 范围）。
DECLARED_BUT_UNIMPLEMENTED = frozenset(
    {"openai", "anthropic", "deepseek", "qwen", "azure", "bedrock", "gemini"}
)


class StartupSecurityError(RuntimeError):
    """生产配置非法。启动期抛出，禁止延迟到运行期。"""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise StartupSecurityError(message)


def validate_startup_security(settings: Settings) -> None:
    """校验启动配置。生产环境任一违规 → 抛错，进程不得启动。

    开发环境直接返回（骨架允许 Fake / 内存后端）。
    """
    if settings.is_development:
        return

    # 1) 生产禁止 Fake LLM。
    _require(
        not settings.use_fake_llm,
        "非开发环境禁止使用 fake LLM provider —— "
        "Fake 不得作为真实评审能力部署（SOFTWARE_DESIGN.md §2）",
    )

    # 2) 生产禁止默认开发密钥。
    _require(
        settings.session_secret not in INSECURE_SESSION_SECRETS,
        "非开发环境禁止使用默认/空会话密钥 SESSION_SECRET —— "
        "请配置强随机密钥",
    )

    # 3) 数据库配置必须完整。
    _require(
        bool(settings.database_url.strip()),
        "非开发环境必须配置 DATABASE_URL",
    )
    _require(
        bool(settings.database_url_sync.strip()),
        "非开发环境必须配置 DATABASE_URL_SYNC",
    )

    # 4) Checkpointer 必须是独立的 Postgres DSN，不得使用内存 Saver。
    _require(
        bool(settings.checkpoint_database_url.strip()),
        "非开发环境必须配置独立的 CHECKPOINT_DATABASE_URL "
        "（禁止使用仅驻内存的 Checkpointer）",
    )
    _require(
        settings.checkpoint_database_url != settings.database_url,
        "Checkpointer 必须使用**独立的**数据库，不得与业务库共用同一 DSN",
    )
    _require(
        "memory" not in settings.checkpoint_database_url.lower(),
        "非开发环境不得使用内存 Checkpointer",
    )

    # 5) 禁止误开启的内存持久化后端。
    _require(
        not settings.use_memory_repository,
        "非开发环境禁止使用 memory 仓储后端 —— 业务事实必须落 Postgres",
    )

    # 6) provider 必须真实受支持且非未实现集。
    provider = settings.llm_provider.strip().lower()
    _require(
        provider not in DECLARED_BUT_UNIMPLEMENTED,
        f"provider={provider!r} 已声明但尚未实现（B3 范围）—— "
        "不得在生产配置后期望其可用",
    )
    _require(
        provider in SUPPORTED_PROVIDERS,
        f"未知的 LLM provider：{provider!r}，受支持集合为 {sorted(SUPPORTED_PROVIDERS)}",
    )


__all__ = [
    "DECLARED_BUT_UNIMPLEMENTED",
    "INSECURE_SESSION_SECRETS",
    "SUPPORTED_PROVIDERS",
    "StartupSecurityError",
    "validate_startup_security",
]
