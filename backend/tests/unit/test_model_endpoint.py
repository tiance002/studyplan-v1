import socket

import pytest
from app.core.errors import AppError
from app.infrastructure.providers.endpoint_policy import ModelEndpointPolicy


def test_approved_public_https_only(monkeypatch):
    monkeypatch.setattr(socket,"getaddrinfo",lambda *a,**k:[(socket.AF_INET,socket.SOCK_STREAM,6,"",("8.8.8.8",443))])
    policy = ModelEndpointPolicy(("api.deepseek.com","api.openai.com"))
    assert policy.validate("https://api.deepseek.com/") == "https://api.deepseek.com"
    assert policy.validate("https://api.openai.com/v1") == "https://api.openai.com/v1"
    for url in ("http://api.deepseek.com","https://api.deepseek.com:8443","https://user:secret@api.deepseek.com",
                "https://api.deepseek.com?token=secret","https://api.deepseek.com/#fragment","https://127.0.0.1",
                "https://169.254.169.254","https://api.deepseek.com.evil.example"):
        with pytest.raises(AppError):
            policy.validate(url)
    monkeypatch.setattr(socket,"getaddrinfo",lambda *a,**k:[(socket.AF_INET,socket.SOCK_STREAM,6,"",("10.0.0.1",443))])
    with pytest.raises(AppError):
        policy.validate("https://api.deepseek.com")


def test_unresolvable_endpoint_fails_closed(monkeypatch):
    def missing(*a,**k):
        raise socket.gaierror()
    monkeypatch.setattr(socket,"getaddrinfo",missing)
    with pytest.raises(AppError):
        ModelEndpointPolicy(("api.deepseek.com",)).validate("https://api.deepseek.com")


def test_provider_rechecks_endpoint_before_sending_api_key():
    import httpx
    from app.core.errors import ValidationAppError
    from app.infrastructure.providers.openai_compatible import OpenAICompatibleLLM
    from app.ports.llm import LLMNotDispatchedError

    calls = []
    client = httpx.Client(transport=httpx.MockTransport(lambda request: calls.append(request) or httpx.Response(200)))
    provider = OpenAICompatibleLLM(base_url="https://api.deepseek.com",model="test",api_key="secret",
                                   client=client,endpoint_guard=lambda value: (_ for _ in ()).throw(ValidationAppError("bad DNS")))
    with pytest.raises(LLMNotDispatchedError):
        provider.generate_structured(purpose="planning.outline",payload={},schema_name="OutlineV1",run_id="r",attempt_id="a")
    assert calls == []
