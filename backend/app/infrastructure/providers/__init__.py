"""providers：LLM 适配器装配。

**唯一出口**（对应旧工程 `providers_factory.py` 的教训，
见 module-reuse-matrix.md §3 C7）：

- 凭据缺失时**拒绝启动**，绝不静默退回模拟器；
- "provider 怎么选"只在一处定义，每个分支都必须显式判定，
  不允许出现"某个分支忘了判 fake"。

⚠️ 当前 B1 阶段只有 Fake 实现。真实云适配器属 B3 范围。
真实适配器必须遵守：**不自动重试**（C8），结果未知时不清洗为成功。
"""

from __future__ import annotations

from app.core.config import Settings
from app.infrastructure.providers.fake import FakeLLM
from app.ports.llm import LLMPort

#: 目前受支持的 provider 名称闭集。
SUPPORTED_PROVIDERS = frozenset({"fake"})


class ProviderConfigurationError(RuntimeError):
    """provider 配置非法。**启动期抛出**，不允许延迟到首次调用。"""


def build_llm(settings: Settings) -> LLMPort:
    """按配置装配 LLM 端口。

    Raises:
        ProviderConfigurationError: provider 名未知，或真实 provider 缺少凭据。
    """
    provider = settings.llm_provider.strip().lower()

    if provider == "fake":
        # 骨架模式：Fake 仅供测试与本地演示。settings.use_fake_llm 由调用方检查，
        # 生产启动路径应拒绝 fake（见 assert_not_fake_in_production）。
        return FakeLLM()

    if provider not in SUPPORTED_PROVIDERS:
        # 真实 provider 尚未实现（B3）。此处**拒绝启动**而不是悄悄用 Fake ——
        # "配置了云模型但实际跑 Fake"是最危险的失败模式。
        raise ProviderConfigurationError(
            f"provider={provider!r} 尚未实现（真实云适配器属 B3）。"
            "当前仅支持 fake；请勿在生产配置真实 provider 后期望其可用。"
        )

    raise ProviderConfigurationError(f"未知的 LLM provider：{provider!r}")  # pragma: no cover


def assert_not_fake_in_production(settings: Settings) -> None:
    """生产环境禁止使用 Fake。由启动路径调用。"""
    if not settings.is_development and settings.use_fake_llm:
        raise ProviderConfigurationError(
            "非开发环境禁止使用 fake provider —— "
            "Fake 不允许部署为真实评审能力（SOFTWARE_DESIGN.md §2）"
        )


__all__ = [
    "SUPPORTED_PROVIDERS",
    "ProviderConfigurationError",
    "assert_not_fake_in_production",
    "build_llm",
]
