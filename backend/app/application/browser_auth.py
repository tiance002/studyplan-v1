"""Shared credential policy and Argon2id verification (no framework dependencies)."""

import re
import unicodedata

from app.core.errors import UnauthenticatedError, ValidationAppError
from app.domain.workspace.models import DEFAULT_CREDENTIAL_POLICY
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

HASHER = PasswordHasher(memory_cost=19456, time_cost=2, parallelism=1)
DUMMY_HASH = HASHER.hash("dummy-secret")


def credentials(username: str, password: str) -> tuple[str, str]:
    username = unicodedata.normalize("NFKC", username).strip()
    DEFAULT_CREDENTIAL_POLICY.validate_username(username)
    DEFAULT_CREDENTIAL_POLICY.validate_password(password)
    if not re.fullmatch(r"[A-Za-z\u3400-\u9fff][A-Za-z0-9_\u3400-\u9fff-]*", username):
        raise ValidationAppError("用户名须以字母或汉字开头，仅支持汉字、字母、数字、下划线和短横线")
    try:
        password.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValidationAppError("密码含非法字符") from exc
    return username, username.casefold()


def verify_password(password: str, password_hash: str | None):
    try:
        HASHER.verify(password_hash or DUMMY_HASH, password)
    except (VerificationError, InvalidHashError, UnicodeEncodeError) as exc:
        raise UnauthenticatedError("用户名或密码错误") from exc
    if password_hash is None:
        raise UnauthenticatedError("用户名或密码错误")
