"""ID、稳定键与内容哈希。

设计约束：
- 内部主键为不透明 UUID（对外只作为字符串 ID 传递）。
- ``stable_key`` 是跨版本可精确映射的语义键，**不等于标题**：
  标题可以改，stable_key 一旦发布不得随文案变化。
- ``content_hash`` 用于草案校验与幂等比对。
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from typing import Any, Iterable

#: 稳定键字符集：小写字母、数字、点、下划线、连字符。不含空格与大小写歧义。
_STABLE_KEY_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")

_OPERATION_KEY_RE = re.compile(r"^[A-Za-z0-9._:-]{1,200}$")


def new_id(prefix: str) -> str:
    """生成带类型前缀的不透明 ID，例如 ``pln_3f2a...``。

    前缀只用于人类排查；业务逻辑不得解析前缀含义。
    """
    if not prefix or not prefix.isalpha():
        raise ValueError("id prefix must be non-empty alphabetic")
    return f"{prefix}_{uuid.uuid4().hex}"


def is_valid_stable_key(key: str) -> bool:
    return bool(_STABLE_KEY_RE.match(key))


def require_stable_key(key: str, *, field: str = "stable_key") -> str:
    if not is_valid_stable_key(key):
        raise ValueError(
            f"{field} must match [a-z0-9][a-z0-9._-]{{0,127}}, got {key!r}"
        )
    return key


def slugify_stable_key(raw: str, *, fallback_prefix: str = "k") -> str:
    """把标题类文本转成候选 stable_key。

    仅用于**首次生成**候选键；已发布的键不得用此函数重算后再做映射。
    非 ASCII（如中文）会被剥离，因此调用方应显式传入英文语义键；
    当结果为空时用 hash 兜底，保证键稳定且唯一。
    """
    lowered = raw.strip().lower()
    lowered = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    lowered = lowered[:96]
    if not lowered or not lowered[0].isalnum():
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
        return f"{fallback_prefix}-{digest}"
    return lowered


def is_valid_operation_key(key: str) -> bool:
    return bool(_OPERATION_KEY_RE.match(key))


def canonical_json(payload: Any) -> str:
    """确定性 JSON 序列化：键排序、紧凑分隔、统一 UTF-8。

    任何参与哈希或幂等比对的内容都必须先经过此函数，
    否则字段顺序或空格差异会导致「同体」被误判为「异体」。
    """
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def content_hash(payload: Any) -> str:
    """对任意可序列化对象取 sha256（十六进制）。"""
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def content_hash_stable(payload: Any) -> str:
    """哈希但忽略易变字段（时间戳、版本号、生成元数据）。

    用于判断「草案内容是否实质变化」，避免仅因 created_at 变化就判定不一致。
    """
    return content_hash(_strip_volatile(payload))


_VOLATILE_KEYS: frozenset[str] = frozenset(
    {
        "created_at",
        "updated_at",
        "checked_at",
        "generated_at",
        "latency_ms",
        "run_id",
        "attempt_id",
        "request_id",
    }
)


def _strip_volatile(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            k: _strip_volatile(v)
            for k, v in value.items()
            if k not in _VOLATILE_KEYS
        }
    if isinstance(value, (list, tuple)):
        return [_strip_volatile(v) for v in value]
    return value


def set_hash(items: Iterable[str]) -> str:
    """对集合取哈希：与顺序无关，重复项折叠。"""
    return content_hash(sorted(set(items)))
