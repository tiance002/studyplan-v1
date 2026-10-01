"""V2 G1 replacement: new secrets are long; existing hashes remain usable."""

import pytest
from app.application import browser_auth
from app.core.errors import UnauthenticatedError, ValidationAppError
from app.domain.workspace.models import DEFAULT_CREDENTIAL_POLICY


@pytest.mark.parametrize("password", ["a" * 15, "a" * 128, "😀" * 15, "😀" * 128, "  long passphrase  ", "e\u0301" * 8])
def test_registration_accepts_code_points_and_preserves_password(password):
    assert DEFAULT_CREDENTIAL_POLICY.validate_password(password) == password
    assert browser_auth.credentials("学习者", password) == ("学习者", "学习者")


@pytest.mark.parametrize("password", ["", "a" * 14, "a" * 129, "😀" * 14, "😀" * 129, "\ud800" + "a" * 15])
def test_registration_rejects_out_of_policy_or_invalid_unicode_without_secret(password):
    with pytest.raises(ValidationAppError) as error:
        browser_auth.credentials("学习者", password)
    if password:
        assert password not in str(error.value)


@pytest.mark.parametrize("password", ["a", "123456", "😀" * 128, "  legacy  "])
def test_login_validation_accepts_legacy_short_and_preserves_secret(password):
    assert DEFAULT_CREDENTIAL_POLICY.validate_login_password(password) == password
    assert browser_auth.login_credentials("学习者", password) == ("学习者", "学习者")
    browser_auth.verify_password(password, browser_auth.HASHER.hash(password))


@pytest.mark.parametrize("password", ["", "a" * 129, "😀" * 129, "\udfff"])
def test_login_validation_rejects_empty_oversized_and_invalid_unicode(password):
    with pytest.raises(ValidationAppError):
        browser_auth.login_credentials("学习者", password)


def test_password_verification_does_not_normalize_or_strip():
    password = "  e\u0301 long passphrase  "
    stored = browser_auth.HASHER.hash(password)
    browser_auth.verify_password(password, stored)
    for changed in (password.strip(), "  é long passphrase  "):
        with pytest.raises(UnauthenticatedError):
            browser_auth.verify_password(changed, stored)
