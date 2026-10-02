"""Pinned transport rejects alternate destinations and connects checked IPs."""
import importlib
import socket

import httpcore
import pytest


@pytest.mark.parametrize("url", ["http://api.github.com/search/repositories", "https://api.github.com:444/search/repositories",
    "https://user@api.github.com/search/repositories", "https://api.github.com.evil/search/repositories",
    "https://api.github.com/repos/o/r/contents/../secret", "https://api.github.com/repos/o/r/contents/a%2Fb",
    "https://api.github.com/search/repositories?page=2", "https://api.github.com/repos/o/r/contents/a?ref=main&token=secret"])
def test_fixed_api_destination_rejects_unsafe_or_unbounded_requests(url):
    transport = importlib.import_module("app.infrastructure.resources.github_transport")
    with pytest.raises(ValueError):
        transport.validate_github_url(url)


def test_private_dns_answer_rejected_before_connect():
    transport = importlib.import_module("app.infrastructure.resources.github_transport")
    backend = transport.PinnedGitHubBackend(resolver=lambda *_: [
        (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("127.0.0.1", 443))])
    with pytest.raises(httpcore.ConnectError):
        backend.connect_tcp("api.github.com", 443, timeout=1)


def test_socket_connect_uses_pinned_ip_without_a_second_dns_resolution(monkeypatch):
    transport = importlib.import_module("app.infrastructure.resources.github_transport")
    destinations = []
    dns_calls = []
    class Socket:
        def settimeout(self, _): pass
        def setsockopt(self, *_): pass
        def connect(self, address): destinations.append(address)
        def close(self): pass
    monkeypatch.setattr(transport.socket, "socket", lambda *_: Socket())
    def resolve(*args):
        dns_calls.append(args)
        return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("140.82.112.5", 443))]
    backend = transport.PinnedGitHubBackend(resolver=resolve)
    backend.connect_tcp("api.github.com", 443, timeout=1)
    assert destinations == [("140.82.112.5", 443)] and len(dns_calls) == 1
